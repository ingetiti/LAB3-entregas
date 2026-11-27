"""
gui.py - Interfaz Grafica interactiva para la ISA Skynet (16 bits) - Grupo 30
=======================================================================
Editor de assembly integrado, carga directa de .hex/.bin, visualizacion de
registros R0..R7, puntero de pila R6, banderas NZP, desensamblado dinamico,
consola de TRAP y ejecucion paso a paso o continua con breakpoints.

Uso: python gui.py [--contar-os] [archivo.asm | archivo.hex | archivo.bin]
"""

import argparse
import glob
import os
import sys
import tempfile
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Optional

from assembler import Assembler, AssemblerError, strip_comment
from core import CPUException
from debugger import Debugger
from isa import FL_N, FL_P, FL_Z, NUM_REGS, SP_REG, get_cc_name, to_int16
from sim import load_hex_symbols, load_image


class ISA16GUI(tk.Tk):
    def __init__(self, initial_path: Optional[str] = None, contar_os: bool = False):
        super().__init__()
        self.title("Simulador Skynet (ISA 16-bit) - Grupo 30")
        self.geometry("1180x760")
        self.minsize(980, 640)

        self.contar_os_var = tk.BooleanVar(value=bool(contar_os))
        self.debugger = Debugger(output_fn=self._append_console_output, contar_os=bool(contar_os))
        self.current_asm_file: Optional[str] = None
        self.running: bool = False
        self.run_after_id: Optional[str] = None
        self.prev_regs = [0] * NUM_REGS
        self._pending_console: list[str] = []
        self._view_start: int = 0x3000
        self._view_count: int = 256
        self._addr_to_iid: dict[int, str] = {}
        self._last_pc_drawn: Optional[int] = None
        self._all_symbol_items: list[str] = []

        self._apply_styles()
        self._build_menu()
        self._build_toolbar()
        self._build_main_layout()

        # Cargar archivo inicial (.asm, .hex o .bin) o plantilla por defecto
        resolved_path = None
        if initial_path:
            if os.path.exists(initial_path):
                resolved_path = initial_path
            else:
                alt = os.path.join(os.path.dirname(os.path.abspath(__file__)), initial_path)
                if os.path.exists(alt):
                    resolved_path = alt

        if resolved_path:
            if resolved_path.lower().endswith((".hex", ".bin")):
                self.load_binary_file(resolved_path)
            else:
                self.load_asm_file(resolved_path)
        else:
            self._load_sample_template()
            if initial_path:
                self.status_var.set(f"Aviso: no se encontró '{initial_path}'. Usá Ctrl+O o Ctrl+B.")

        self.update_ui_state()
        self.after(150, self._show_welcome_dialog)

    def _show_welcome_dialog(self):
        """Muestra una ventana modal minimalista de bienvenida centrada."""
        if not self.winfo_exists():
            return

        win = tk.Toplevel(self)
        win.title("Bienvenida - Simulador Skynet (ISA 16-bit)")
        win.resizable(False, False)
        win.configure(bg="#F8F9FA")
        win.transient(self)

        # Cabecera oscura acorde al editor
        header = tk.Frame(win, bg="#1E1E1E", padx=28, pady=20)
        header.pack(fill=tk.X)

        tk.Label(
            header,
            text="Simulador Skynet (ISA 16-bit) - Grupo 30",
            font=("Segoe UI", 14, "bold"),
            bg="#1E1E1E",
            fg="#FFFFFF",
        ).pack(anchor="w")

        tk.Label(
            header,
            text="IC221 - Arquitectura de Computadoras | FIO-UNaM",
            font=("Segoe UI", 9),
            bg="#1E1E1E",
            fg="#B0BEC5",
        ).pack(anchor="w", pady=(4, 0))

        # Linea de acento azul (mismo color que PC)
        tk.Frame(win, bg="#0055D4", height=3).pack(fill=tk.X)

        # Cuerpo minimalista con atajos utiles
        body = tk.Frame(win, bg="#F8F9FA", padx=28, pady=18)
        body.pack(fill=tk.BOTH, expand=True)

        tk.Label(
            body,
            text="Atajos rapidos",
            font=("Segoe UI", 10, "bold"),
            bg="#F8F9FA",
            fg="#1E1E1E",
        ).pack(anchor="w", pady=(0, 10))

        shortcuts = [
            ("Ctrl+O / F5", "Abrir archivo .asm y ensamblar"),
            ("Ctrl+B", "Cargar binario .hex/.bin (ej. benchmark)"),
            ("F9", "Ejecutar programa en vivo"),
            ("F10 / F8", "Paso a paso / Reiniciar CPU"),
        ]

        grid_frame = tk.Frame(body, bg="#F8F9FA")
        grid_frame.pack(fill=tk.X)

        for idx, (keys, desc) in enumerate(shortcuts):
            tk.Label(
                grid_frame,
                text=keys,
                font=("Consolas", 9, "bold"),
                bg="#E8F0FE",
                fg="#0055D4",
                padx=8,
                pady=3,
                width=12,
                anchor="center",
            ).grid(row=idx, column=0, sticky="w", pady=4, padx=(0, 12))

            tk.Label(
                grid_frame,
                text=desc,
                font=("Segoe UI", 9),
                bg="#F8F9FA",
                fg="#333333",
            ).grid(row=idx, column=1, sticky="w", pady=4)

        def close_welcome(event=None):
            try:
                win.grab_release()
            except tk.TclError:
                pass
            win.destroy()

        btn_frame = tk.Frame(body, bg="#F8F9FA")
        btn_frame.pack(fill=tk.X, pady=(18, 2))

        start_btn = tk.Button(
            btn_frame,
            text="Comenzar",
            command=close_welcome,
            font=("Segoe UI", 10, "bold"),
            bg="#0055D4",
            fg="#FFFFFF",
            activebackground="#0041A8",
            activeforeground="#FFFFFF",
            relief="flat",
            padx=28,
            pady=7,
            cursor="hand2",
        )
        start_btn.pack(anchor="center")

        win.bind("<Return>", close_welcome)
        win.bind("<KP_Enter>", close_welcome)
        win.bind("<Escape>", close_welcome)
        win.protocol("WM_DELETE_WINDOW", close_welcome)

        # Centrar sobre la ventana principal
        self.update_idletasks()
        win.update_idletasks()
        w = win.winfo_reqwidth()
        h = win.winfo_reqheight()
        if self.winfo_viewable():
            x = self.winfo_rootx() + (self.winfo_width() - w) // 2
            y = self.winfo_rooty() + (self.winfo_height() - h) // 2
        else:
            x = (win.winfo_screenwidth() - w) // 2
            y = (win.winfo_screenheight() - h) // 2
        win.geometry(f"{w}x{h}+{max(0, x)}+{max(0, y)}")

        win.lift()
        win.grab_set()
        win.focus_force()
        start_btn.focus_set()

    def _apply_styles(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TLabel", font=("Segoe UI", 9))
        style.configure("TButton", font=("Segoe UI", 9, "bold"))
        style.configure("Header.TLabel", font=("Segoe UI", 10, "bold"))
        style.configure("Title.TLabel", font=("Segoe UI", 12, "bold"))

    def _build_menu(self):
        menubar = tk.Menu(self)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Nuevo", command=self._load_sample_template, accelerator="Ctrl+N")
        file_menu.add_command(label="Abrir archivo .asm...", command=self.open_file_dialog, accelerator="Ctrl+O")
        file_menu.add_command(label="Cargar .hex/.bin...", command=self.open_binary_dialog, accelerator="Ctrl+B")
        file_menu.add_command(label="Guardar", command=self.save_file, accelerator="Ctrl+S")
        file_menu.add_command(label="Guardar como...", command=self.save_file_as)
        file_menu.add_separator()
        file_menu.add_command(label="Salir", command=self.quit)
        menubar.add_cascade(label="Archivo", menu=file_menu)

        exec_menu = tk.Menu(menubar, tearoff=0)
        exec_menu.add_command(label="Ensamblar y Cargar", command=self.assemble_and_load, accelerator="F5")
        exec_menu.add_command(label="Paso a paso (Step)", command=self.step_execution, accelerator="F10")
        exec_menu.add_command(label="Continuar (Run)", command=self.start_run, accelerator="F9")
        exec_menu.add_command(label="Pausa (Stop)", command=self.stop_run)
        exec_menu.add_command(label="Reiniciar (Reset)", command=self.reset_execution, accelerator="F8")
        exec_menu.add_separator()
        exec_menu.add_checkbutton(
            label="Contar rutinas OS (TRAP)",
            variable=self.contar_os_var,
            command=self.toggle_contar_os,
        )
        menubar.add_cascade(label="Ejecución", menu=exec_menu)

        self.config(menu=menubar)
        self.bind("<Control-n>", lambda e: self._load_sample_template())
        self.bind("<Control-o>", lambda e: self.open_file_dialog())
        self.bind("<Control-b>", lambda e: self.open_binary_dialog())
        self.bind("<Control-s>", lambda e: self.save_file())
        self.bind("<F5>", lambda e: self.assemble_and_load())
        self.bind("<F10>", lambda e: self.step_execution())
        self.bind("<F9>", lambda e: self.start_run())
        self.bind("<F8>", lambda e: self.reset_execution())

    def _build_toolbar(self):
        tb = ttk.Frame(self, padding=4)
        tb.pack(side=tk.TOP, fill=tk.X)

        ttk.Button(tb, text="📂 Abrir .asm", command=self.open_file_dialog).pack(side=tk.LEFT, padx=3)
        ttk.Button(tb, text="Cargar .hex/.bin", command=self.open_binary_dialog).pack(side=tk.LEFT, padx=3)
        ttk.Button(tb, text="💾 Guardar", command=self.save_file).pack(side=tk.LEFT, padx=3)

        ttk.Separator(tb, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8)

        ttk.Button(tb, text="⚙️ Ensamblar y Cargar (F5)", command=self.assemble_and_load).pack(side=tk.LEFT, padx=3)
        ttk.Button(tb, text="⏯️ Ejecutar (F9)", command=self.start_run).pack(side=tk.LEFT, padx=3)
        ttk.Button(tb, text="⏸️ Pausa", command=self.stop_run).pack(side=tk.LEFT, padx=3)
        ttk.Button(tb, text="⏭️ Paso a paso (F10)", command=self.step_execution).pack(side=tk.LEFT, padx=3)
        ttk.Button(tb, text="🔄 Reiniciar (F8)", command=self.reset_execution).pack(side=tk.LEFT, padx=3)

        ttk.Separator(tb, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=6)
        ttk.Checkbutton(
            tb,
            text="Contar OS",
            variable=self.contar_os_var,
            command=self.toggle_contar_os,
        ).pack(side=tk.LEFT, padx=3)

        self.status_var = tk.StringVar(value="Listo.")
        ttk.Label(tb, textvariable=self.status_var, font=("Segoe UI", 9, "italic")).pack(side=tk.RIGHT, padx=10)

    def _build_main_layout(self):
        paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=6, pady=4)

        # ================= Panel Izquierdo: Editor + Consola =================
        left_frame = ttk.Frame(paned)
        paned.add(left_frame, weight=3)

        v_left_paned = ttk.PanedWindow(left_frame, orient=tk.VERTICAL)
        v_left_paned.pack(fill=tk.BOTH, expand=True)

        # Editor
        editor_frame = ttk.LabelFrame(v_left_paned, text="Editor Assembly (.asm)", padding=4)
        v_left_paned.add(editor_frame, weight=3)

        self.editor_text = tk.Text(editor_frame, wrap=tk.NONE, font=("Consolas", 11),
                                   undo=True, bg="#1E1E1E", fg="#D4D4D4", insertbackground="white")
        editor_scroll_y = ttk.Scrollbar(editor_frame, orient=tk.VERTICAL, command=self.editor_text.yview)
        editor_scroll_x = ttk.Scrollbar(editor_frame, orient=tk.HORIZONTAL, command=self.editor_text.xview)
        self.editor_text.configure(yscrollcommand=editor_scroll_y.set, xscrollcommand=editor_scroll_x.set)

        editor_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        editor_scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.editor_text.pack(fill=tk.BOTH, expand=True)

        # Consola
        console_frame = ttk.LabelFrame(v_left_paned, text="Consola de Salida (TRAP OUT / PUTS / PUTI)", padding=4)
        v_left_paned.add(console_frame, weight=1)

        self.console_text = tk.Text(console_frame, wrap=tk.CHAR, font=("Consolas", 10),
                                    bg="#0F141C", fg="#00FF66", height=7)
        console_scroll = ttk.Scrollbar(console_frame, orient=tk.VERTICAL, command=self.console_text.yview)
        self.console_text.configure(yscrollcommand=console_scroll.set)
        console_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.console_text.pack(fill=tk.BOTH, expand=True)

        # ================= Panel Derecho: Registros, Banderas, Desensamblado, Métricas =================
        right_frame = ttk.Frame(paned)
        paned.add(right_frame, weight=2)

        # 1. Banderas y PC
        flags_frame = ttk.LabelFrame(right_frame, text="Estado del Procesador (PC & Banderas NZP)", padding=6)
        flags_frame.pack(fill=tk.X, pady=3)

        pc_box = ttk.Frame(flags_frame)
        pc_box.pack(side=tk.LEFT, padx=6)
        ttk.Label(pc_box, text="PC: ", font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT)
        self.pc_val_label = ttk.Label(pc_box, text="x3000", font=("Consolas", 11, "bold"), foreground="#0055D4")
        self.pc_val_label.pack(side=tk.LEFT)

        cc_box = ttk.Frame(flags_frame)
        cc_box.pack(side=tk.RIGHT, padx=6)

        self.lbl_fl_n = tk.Label(cc_box, text=" N ", font=("Segoe UI", 9, "bold"), bg="#E0E0E0", fg="#333333", relief="solid", bd=1)
        self.lbl_fl_n.pack(side=tk.LEFT, padx=2)
        self.lbl_fl_z = tk.Label(cc_box, text=" Z ", font=("Segoe UI", 9, "bold"), bg="#E0E0E0", fg="#333333", relief="solid", bd=1)
        self.lbl_fl_z.pack(side=tk.LEFT, padx=2)
        self.lbl_fl_p = tk.Label(cc_box, text=" P ", font=("Segoe UI", 9, "bold"), bg="#E0E0E0", fg="#333333", relief="solid", bd=1)
        self.lbl_fl_p.pack(side=tk.LEFT, padx=2)

        # 2. Banco de Registros (R0 a R7)
        regs_frame = ttk.LabelFrame(right_frame, text="Banco de Registros (R0 – R7)", padding=6)
        regs_frame.pack(fill=tk.X, pady=3)

        self.reg_labels = {}
        for r in range(NUM_REGS):
            row = r // 2
            col = (r % 2) * 2

            tag = f"R{r}"
            if r == SP_REG: tag += " (SP)"
            elif r == 7: tag += " (LR)"

            ttk.Label(regs_frame, text=f"{tag}:", font=("Segoe UI", 9, "bold")).grid(row=row, column=col, sticky="w", padx=3, pady=2)
            lbl = tk.Label(regs_frame, text="x0000 (     0)", font=("Consolas", 10), bg="#F8F9FA", fg="#000000",
                           relief="sunken", bd=1, width=17, anchor="w", padx=4)
            lbl.grid(row=row, column=col + 1, sticky="w", padx=3, pady=2)
            self.reg_labels[r] = lbl

        # 4. Métricas de Ejecución y Espacio de Memoria (empacado abajo ANTES del mapa para que NUNCA se recorte)
        stats_frame = ttk.LabelFrame(right_frame, text="Métricas de Ejecución y Memoria (Usuario, sin OS)", padding=5)
        stats_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=3)

        self.stats_exec_var = tk.StringVar(value="Instrucciones: 0  |  Fetches: 0")
        ttk.Label(stats_frame, textvariable=self.stats_exec_var, font=("Segoe UI", 8)).pack(anchor="w", padx=4)

        self.stats_io_var = tk.StringVar(value="Lecturas: 0 B  |  Escrituras: 0 B  |  Dir. tocadas: 0")
        ttk.Label(stats_frame, textvariable=self.stats_io_var, font=("Segoe UI", 8)).pack(anchor="w", padx=4, pady=(1, 4))

        mem_box = tk.Frame(stats_frame, bg="#EEF4FC", highlightbackground="#B8D0F0", highlightthickness=1, padx=6, pady=4)
        mem_box.pack(fill=tk.X, padx=2, pady=(0, 1))

        self.mem_prog_var = tk.StringVar(value="Programa cargado: 0 B (0 pal.)  |  Pila / datos: 0 B")
        tk.Label(
            mem_box,
            textvariable=self.mem_prog_var,
            font=("Segoe UI", 8),
            bg="#EEF4FC",
            fg="#1F3B5C",
            anchor="w",
        ).pack(fill=tk.X)

        self.mem_total_var = tk.StringVar(value="Espacio total usuario (sin OS): 0 B  (0.00% de 64 KB)")
        tk.Label(
            mem_box,
            textvariable=self.mem_total_var,
            font=("Segoe UI", 9, "bold"),
            bg="#EEF4FC",
            fg="#0B5394",
            anchor="w",
        ).pack(fill=tk.X, pady=(1, 0))

        # 3. Vista de Desensamblado / Mapa de Memoria Navegable + Breakpoints por Función/Dir
        dis_frame = ttk.LabelFrame(right_frame, text="Mapa de Memoria y Breakpoints (Doble clic: BP)", padding=4)
        dis_frame.pack(fill=tk.BOTH, expand=True, pady=3)

        # Barra 1: Selector / buscador por función (grupo) o dirección hex + botón Ir + botón BP
        nav_row1 = ttk.Frame(dis_frame)
        nav_row1.pack(fill=tk.X, pady=(0, 3))

        ttk.Label(nav_row1, text="Función/Dir:", font=("Segoe UI", 8, "bold")).pack(side=tk.LEFT, padx=(0, 4))
        self.nav_var = tk.StringVar()
        self.nav_combo = ttk.Combobox(nav_row1, textvariable=self.nav_var, width=26, font=("Consolas", 8))
        self.nav_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))
        self.nav_combo.bind("<Return>", lambda e: self.jump_to_query())
        self.nav_combo.bind("<<ComboboxSelected>>", lambda e: self.jump_to_query())
        self.nav_combo.bind("<KeyRelease>", self._filter_symbol_dropdown)

        ttk.Button(nav_row1, text="Ir", width=4, command=self.jump_to_query).pack(side=tk.LEFT, padx=2)
        ttk.Button(nav_row1, text="● BP", width=5, command=self.toggle_breakpoint_from_query).pack(side=tk.LEFT, padx=2)

        # Barra 2: Desplazamiento por todo el mapa de 64 KB + volver a PC + gestión de BPs
        nav_row2 = ttk.Frame(dis_frame)
        nav_row2.pack(fill=tk.X, pady=(0, 3))

        ttk.Button(nav_row2, text="◀ -256", width=7, command=lambda: self.shift_memory_view(-256)).pack(side=tk.LEFT, padx=(0, 2))
        ttk.Button(nav_row2, text="▲ PC", width=6, command=self.jump_to_pc).pack(side=tk.LEFT, padx=2)
        ttk.Button(nav_row2, text="+256 ▶", width=7, command=lambda: self.shift_memory_view(256)).pack(side=tk.LEFT, padx=2)

        self.mem_range_var = tk.StringVar(value="x3000–x31FE")
        ttk.Label(nav_row2, textvariable=self.mem_range_var, font=("Consolas", 8)).pack(side=tk.LEFT, padx=6)

        ttk.Button(nav_row2, text="Limpiar BPs", width=10, command=self.clear_all_breakpoints).pack(side=tk.RIGHT, padx=(2, 0))
        self.bp_count_var = tk.StringVar(value="BPs: 0")
        ttk.Label(nav_row2, textvariable=self.bp_count_var, font=("Segoe UI", 8, "bold")).pack(side=tk.RIGHT, padx=4)

        # Barra de contexto: muestra la subrutina/grupo propietaria de la fila seleccionada o PC
        self.curr_sub_var = tk.StringVar(value="Subrutina: —")
        tk.Label(
            dis_frame,
            textvariable=self.curr_sub_var,
            font=("Consolas", 8, "bold"),
            bg="#EEF4FC",
            fg="#0B5394",
            anchor="w",
            padx=6,
            pady=2,
            relief="flat",
        ).pack(fill=tk.X, pady=(0, 3))

        # Tabla scrollable limpia (4 columnas + encabezados de subrutina integrados)
        tree_container = ttk.Frame(dis_frame)
        tree_container.pack(fill=tk.BOTH, expand=True)

        self.dis_tree = ttk.Treeview(
            tree_container,
            columns=("bp", "addr", "hex", "instr"),
            show="headings",
            height=8,
        )
        self.dis_tree.heading("bp", text="BP")
        self.dis_tree.heading("addr", text="Dir")
        self.dis_tree.heading("hex", text="Código")
        self.dis_tree.heading("instr", text="Instrucción / Subrutina")

        self.dis_tree.column("bp", width=30, minwidth=28, anchor="center", stretch=False)
        self.dis_tree.column("addr", width=58, minwidth=54, anchor="center", stretch=False)
        self.dis_tree.column("hex", width=62, minwidth=56, anchor="center", stretch=False)
        self.dis_tree.column("instr", width=260, minwidth=160, anchor="w")

        self.dis_tree.tag_configure("section", background="#E8F0FE", foreground="#0B5394", font=("Consolas", 9, "bold"))
        self.dis_tree.tag_configure("os_section", background="#FFF4E5", foreground="#9A4A00", font=("Consolas", 9, "bold"))
        self.dis_tree.tag_configure("bp_row", background="#FDECEA", foreground="#9B1C1C")

        dis_scroll_y = ttk.Scrollbar(tree_container, orient=tk.VERTICAL, command=self.dis_tree.yview)
        dis_scroll_x = ttk.Scrollbar(tree_container, orient=tk.HORIZONTAL, command=self.dis_tree.xview)
        self.dis_tree.configure(yscrollcommand=dis_scroll_y.set, xscrollcommand=dis_scroll_x.set)
        dis_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        dis_scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.dis_tree.pack(fill=tk.BOTH, expand=True)
        self.dis_tree.bind("<Double-1>", self._on_tree_double_click)
        self.dis_tree.bind("<<TreeviewSelect>>", self._on_tree_select)

    def _load_sample_template(self):
        sample = r"""; ============================================================
; Simulador Funcional Skynet (ISA 16-bit)
; Grupo 30 | IC221 - Arquitectura de Computadoras (FIO-UNaM)
; ============================================================
.ORIG x3000
    LEA R0, MSG_BIENVENIDA
    PUTS
    HALT

MSG_BIENVENIDA: .STRINGZ "========================================================\n  ¡Bienvenido al Simulador Skynet (ISA 16-bit) - Grupo 30!\n========================================================\n"
.END
"""
        self.editor_text.delete("1.0", tk.END)
        self.editor_text.insert("1.0", sample)
        self.current_asm_file = None
        self.stop_run()
        self.debugger.blob = b""
        self.debugger.symbols.clear()
        self.debugger.addr_labels.clear()
        self.debugger.symbol_map.clear()
        self.debugger.reset()
        self.prev_regs = list(self.debugger.cpu.regs)
        self._refresh_symbol_dropdown()
        self._rebuild_disassembly_for_program()
        self.status_var.set("Plantilla de bienvenida cargada. Presioná F5 para ensamblar y cargar.")

    def open_file_dialog(self):
        path = filedialog.askopenfilename(
            filetypes=[("Archivos Assembly (*.asm)", "*.asm"), ("Todos los archivos", "*.*")]
        )
        if path:
            self.load_asm_file(path)

    def open_binary_dialog(self):
        path = filedialog.askopenfilename(
            filetypes=[
                ("Imagenes binarias/hex (*.hex *.bin)", "*.hex *.bin"),
                ("Archivos Hex (*.hex)", "*.hex"),
                ("Archivos Bin (*.bin)", "*.bin"),
                ("Todos los archivos", "*.*"),
            ]
        )
        if path:
            self.load_binary_file(path)

    @staticmethod
    def _win_sort_key(path: str) -> str:
        """Orden consistente con Windows/PowerShell Sort-Object Name ('.' antes que '_')."""
        return os.path.basename(path).lower().replace(".", "\x00").replace("_", "\x01")

    def _try_load_companion_symbols(self, bin_path: str, origin: int, blob: bytes) -> Optional[dict]:
        """Si existe un fuente .asm (o main_grupo27.asm + lib/*.asm) junto al .hex/.bin
        que ensambla exactamente al mismo binario, devuelve su tabla de símbolos verificada."""
        folder = os.path.dirname(os.path.abspath(bin_path))
        stem = os.path.splitext(os.path.basename(bin_path))[0]
        candidates = []

        # 1. Caso benchmark multi-archivo: main_*.asm + lib/*.asm en la misma carpeta
        lib_dir = os.path.join(folder, "lib")
        if os.path.isdir(lib_dir):
            libs = sorted(glob.glob(os.path.join(lib_dir, "*.asm")), key=self._win_sort_key)
            for main_cand in sorted(glob.glob(os.path.join(folder, "*.asm"))):
                candidates.append([main_cand] + libs)

        # 2. Caso archivo único compañero: <stem>.asm
        same_asm = os.path.join(folder, stem + ".asm")
        if os.path.isfile(same_asm):
            candidates.append([same_asm])

        for sources in candidates:
            try:
                asm = Assembler()
                o, b = asm.assemble(sources)
                if o == origin and b == blob:
                    return asm.symbols
            except (OSError, AssemblerError):
                continue
        return None

    def load_binary_file(self, path: str):
        """Carga una imagen .hex o .bin ya ensamblada directo en la CPU."""
        self.stop_run()
        try:
            origin, blob = load_image(path)
        except (OSError, ValueError) as e:
            messagebox.showerror("Error al cargar binario", str(e))
            self.status_var.set("Error al cargar binario.")
            return

        self.debugger.breakpoints.clear()
        embedded_syms = load_hex_symbols(path)
        companion_syms = embedded_syms or self._try_load_companion_symbols(path, origin, blob)

        # Inicializar CPU (PC=origin, R6=0xFE00, metricas en cero) y consola
        self._pending_console.clear()
        self.console_text.delete("1.0", tk.END)
        self.debugger.load_program(origin, blob, companion_syms)
        self.prev_regs = list(self.debugger.cpu.regs)
        self.current_asm_file = None

        # Aviso breve en el editor (solo lectura logica, sin codigo fuente .asm)
        fname = os.path.basename(path)
        if embedded_syms:
            sym_note = f"; Etiquetas incrustadas en .hex: {len(self.debugger.addr_labels)} subrutinas/etiquetas\n"
        elif companion_syms:
            sym_note = f"; Símbolos detectados desde .asm: {len(self.debugger.addr_labels)} subrutinas/etiquetas\n"
        else:
            sym_note = "; Sin símbolos asociados (podés poner breakpoints por dirección hex).\n"
        notice = (
            "; ============================================================\n"
            f"; Binario cargado en memoria: {fname}\n"
            f"; Ruta: {path}\n"
            f"; Origen (.ORIG): x{origin:04X} | Tamano: {len(blob)} bytes\n"
            "; ============================================================\n"
            f"{sym_note}"
            "; - Presione F9 para ejecutar en vivo\n"
            "; - Presione F10 para avanzar paso a paso\n"
            "; - Presione F8 para reiniciar la CPU\n"
            "; - Usá el selector Función/Dir o doble clic para poner breakpoints\n"
        )
        self.editor_text.delete("1.0", tk.END)
        self.editor_text.insert("1.0", notice)

        self._refresh_symbol_dropdown()
        self._rebuild_disassembly_for_program()
        self.update_ui_state()
        sym_msg = f", {len(self.debugger.addr_labels)} símbolos" if companion_syms else ""
        self.status_var.set(f"Binario cargado: {fname} (origen x{origin:04X}, {len(blob)} bytes{sym_msg}).")

    def load_asm_file(self, path: str):
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            self.stop_run()
            self.editor_text.delete("1.0", tk.END)
            self.editor_text.insert("1.0", content)
            self.current_asm_file = path
            self.debugger.blob = b""
            self.debugger.symbols.clear()
            self.debugger.addr_labels.clear()
            self.debugger.symbol_map.clear()
            self.debugger.reset()
            self.prev_regs = list(self.debugger.cpu.regs)
            self._refresh_symbol_dropdown()
            self._rebuild_disassembly_for_program()
            self.update_ui_state()
            self.status_var.set(f"Cargado: {os.path.basename(path)} (presioná F5 para ensamblar y cargar).")
        except Exception as e:
            messagebox.showerror("Error al abrir archivo", str(e))

    def save_file(self):
        if self.current_asm_file:
            try:
                with open(self.current_asm_file, "w", encoding="utf-8") as f:
                    f.write(self.editor_text.get("1.0", tk.END))
                self.status_var.set(f"Guardado: {os.path.basename(self.current_asm_file)}")
            except Exception as e:
                messagebox.showerror("Error al guardar", str(e))
        else:
            self.save_file_as()

    def save_file_as(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".asm",
            filetypes=[("Archivos Assembly (*.asm)", "*.asm"), ("Todos los archivos", "*.*")]
        )
        if path:
            self.current_asm_file = path
            self.save_file()

    def _collect_external_libs(self, content: str) -> list[str]:
        """Si el código usa .EXTERNAL y existe una carpeta lib/ junto al archivo .asm,
        devuelve los módulos .asm de lib/ para ensamblado multi-archivo automático."""
        if not self.current_asm_file:
            return []
        has_external = any(
            strip_comment(line).strip().upper().startswith(".EXTERNAL")
            for line in content.splitlines()
        )
        if not has_external:
            return []
        curr_abs = os.path.abspath(self.current_asm_file)
        lib_dir = os.path.join(os.path.dirname(curr_abs), "lib")
        if not os.path.isdir(lib_dir):
            return []
        libs = [
            p for p in glob.glob(os.path.join(lib_dir, "*.asm"))
            if os.path.abspath(p) != curr_abs
        ]
        libs.sort(key=self._win_sort_key)
        return libs

    def assemble_and_load(self, silent_empty: bool = False) -> bool:
        """Ensambla el texto actual del editor (y lib/*.asm si usa .EXTERNAL) y carga el binario."""
        self.stop_run()
        content = self.editor_text.get("1.0", tk.END)
        fname = os.path.basename(self.current_asm_file) if self.current_asm_file else "editor.asm"
        lib_files = self._collect_external_libs(content)

        asm = Assembler()
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_path = os.path.join(tmpdir, fname)
            with open(temp_path, "w", encoding="utf-8") as tf:
                tf.write(content)
            sources = [temp_path] + lib_files
            try:
                origin, blob = asm.assemble(sources)
            except AssemblerError as e:
                messagebox.showerror("Error de Ensamblado", str(e))
                self.status_var.set("Error de ensamblado.")
                return False

        if not blob:
            if not silent_empty:
                if self.debugger.blob:
                    self.status_var.set("Binario ya cargado en memoria (usá F9 para ejecutar).")
                else:
                    self.status_var.set("Sin instrucciones en el editor.")
            return False

        # Cargar en el depurador
        self._pending_console.clear()
        self.console_text.delete("1.0", tk.END)
        self.debugger.load_program(origin, blob, asm.symbols)
        self.prev_regs = list(self.debugger.cpu.regs)
        self._refresh_symbol_dropdown()
        self._rebuild_disassembly_for_program()
        self.update_ui_state()
        extra = f" ({1 + len(lib_files)} archivos)" if lib_files else ""
        self.status_var.set(f"Ensamblado exitoso{extra}: origen x{origin:04X}, {len(blob)} bytes.")
        return True

    def _ensure_program_loaded(self) -> bool:
        """Asegura que haya un programa cargado (auto-ensambla .asm si corresponde) sin mostrar carteles."""
        if self.debugger.blob:
            return True
        if self.assemble_and_load(silent_empty=True):
            return True
        self.status_var.set("Sin programa cargado en memoria (usá F5 o Ctrl+B).")
        return False

    def step_execution(self):
        self.stop_run()
        if not self._ensure_program_loaded():
            return
        active, msg = self.debugger.step()
        self.update_ui_state()
        self.status_var.set(msg)

    def start_run(self):
        if self.running or self.debugger.cpu.halted:
            return
        if not self._ensure_program_loaded():
            return
        self.running = True
        self.status_var.set("Ejecutando...")
        self._run_loop()

    def _run_loop(self):
        if not self.running:
            return
        cpu = self.debugger.cpu
        bps = self.debugger.breakpoints
        steps_batch = 2000

        try:
            while steps_batch > 0 and self.running and not cpu.halted:
                active = cpu.step()
                steps_batch -= 1
                if not active:
                    self.running = False
                    self._flush_console()
                    self.update_ui_state()
                    if cpu.contar_os:
                        self.status_var.set(
                            f"Ejecucion finalizada (HALT) - {cpu.instr_count} instr. "
                            f"(Usr: {cpu.user_instr_count} + OS: {cpu.os_instr_count})."
                        )
                    else:
                        self.status_var.set(
                            f"Ejecucion finalizada (HALT) - {cpu.instr_count} instrucciones."
                        )
                    return
                if cpu.pc in bps:
                    self.running = False
                    self._flush_console()
                    self.update_ui_state()
                    lbl = self.debugger.get_addr_label(cpu.pc)
                    extra = f" ({lbl})" if lbl else ""
                    self.status_var.set(f"Pausa: Breakpoint en x{cpu.pc:04X}{extra}")
                    return
        except CPUException as e:
            self.running = False
            self._flush_console()
            self.update_ui_state()
            self.status_var.set(f"Excepcion en x{cpu.pc:04X}: {e}")
            return

        self._flush_console()
        self.update_ui_state()
        if self.running and not cpu.halted:
            self.status_var.set(f"Ejecutando... ({cpu.instr_count} instrucciones)")
            self.run_after_id = self.after(10, self._run_loop)
        else:
            self.running = False
            self.status_var.set("Ejecucion finalizada." if cpu.halted else "En pausa.")

    def stop_run(self):
        self.running = False
        if self.run_after_id:
            self.after_cancel(self.run_after_id)
            self.run_after_id = None
        self._flush_console()
        self.status_var.set("Pausado.")

    def reset_execution(self):
        self.stop_run()
        self.debugger.reset()
        self._pending_console.clear()
        self.console_text.delete("1.0", tk.END)
        self.prev_regs = list(self.debugger.cpu.regs)
        self._rebuild_disassembly_for_program()
        self.update_ui_state()
        self.status_var.set(f"Reiniciado a x{self.debugger.origin:04X}.")

    def toggle_contar_os(self):
        """Alterna entre modo estándar (1 TRAP = 1 instr.) y rutinas OS reales."""
        self.stop_run()
        enabled = bool(self.contar_os_var.get())
        try:
            self.debugger.set_contar_os(enabled)
        except (OSError, CPUException, AssemblerError) as e:
            self.contar_os_var.set(not enabled)
            messagebox.showerror("Error en modo OS", str(e))
            self.status_var.set("Error al cambiar modo OS.")
            return
        self._pending_console.clear()
        self.console_text.delete("1.0", tk.END)
        self.prev_regs = list(self.debugger.cpu.regs)
        self._refresh_symbol_dropdown()
        self._rebuild_disassembly_for_program()
        self.update_ui_state()
        if enabled:
            self.status_var.set("Modo OS activado (contar_os=True). CPU reiniciada.")
        else:
            self.status_var.set("Modo estándar (1 TRAP = 1 instr., contar_os=False). CPU reiniciada.")

    def _append_console_output(self, text: str):
        if self.running:
            self._pending_console.append(text)
        else:
            self.console_text.insert(tk.END, text)
            self.console_text.see(tk.END)

    def _flush_console(self):
        if self._pending_console:
            chunk = "".join(self._pending_console)
            self._pending_console.clear()
            self.console_text.insert(tk.END, chunk)
            self.console_text.see(tk.END)

    # ---------- Navegación de mapa de memoria y breakpoints por función/dir ----------
    def _refresh_symbol_dropdown(self):
        entries = self.debugger.get_symbol_entries()
        self._all_symbol_items = [f"x{addr:04X} | {name}" for addr, name in entries]
        self.nav_combo["values"] = self._all_symbol_items

    def _filter_symbol_dropdown(self, event=None):
        if event is not None and event.keysym in ("Up", "Down", "Left", "Right", "Return", "Escape", "Tab"):
            return
        q = self.nav_var.get().strip().upper()
        if not q:
            self.nav_combo["values"] = self._all_symbol_items
        else:
            self.nav_combo["values"] = [it for it in self._all_symbol_items if q in it.upper()]

    def _update_bp_counter(self):
        self.bp_count_var.set(f"BPs: {len(self.debugger.breakpoints)}")

    def _rebuild_disassembly_for_program(self):
        """Carga en la vista scrollable el rango completo del programa de usuario (o ventana por defecto)."""
        origin = self.debugger.origin & ~1
        if self.debugger.blob:
            words = max(256, (len(self.debugger.blob) + 1) // 2 + 16)
            words = min(words, 8192)
        else:
            words = 256
        self._populate_memory_view(origin, words, focus_addr=self.debugger.cpu.pc)

    @staticmethod
    def _format_label_pretty(label: str) -> str:
        """Formatea 'MODULO-SUBRUTINA' como 'MODULO :: SUBRUTINA' para mejor lectura visual."""
        if "-" in label:
            mod, sub = label.split("-", 1)
            return f"{mod} :: {sub}"
        return label

    def _update_context_bar(self, addr: int):
        lbl = self.debugger.get_addr_label(addr)
        if lbl:
            pretty = self._format_label_pretty(lbl.lstrip("↳ ").strip())
            if lbl.startswith("↳ "):
                self.curr_sub_var.set(f"Subrutina: {pretty}")
            else:
                self.curr_sub_var.set(f"Subrutina: {pretty}  (x{addr:04X})")
        else:
            self.curr_sub_var.set(f"Dirección: x{addr:04X}")

    def _on_tree_select(self, event=None):
        sel = self.dis_tree.selection()
        if not sel:
            return
        vals = self.dis_tree.item(sel[0], "values")
        if vals and len(vals) >= 2:
            try:
                addr = int(vals[1].lstrip("xX"), 16)
                self._update_context_bar(addr)
            except ValueError:
                pass

    def _populate_memory_view(self, start_addr: int, count: int, focus_addr: Optional[int] = None):
        """Rellena la tabla con `count` palabras desde `start_addr` con encabezados visuales
        de subrutina/grupo integrados y scroll libre en los 64 KB."""
        max_start = max(0, (self.debugger.cpu.mem.size - 2) - (count - 1) * 2)
        start = max(0, min(max_start, start_addr & ~1))
        self._view_start = start
        self._view_count = count

        self.dis_tree.delete(*self.dis_tree.get_children())
        self._addr_to_iid.clear()
        self._last_pc_drawn = None

        rows = self.debugger.get_memory_slice(start, count)
        for addr, _ctx_label, code, dis, is_pc, is_bp in rows:
            # Si en esta dirección inicia una etiqueta/subrutina, insertar fila separadora estilizada
            exact_lbl = self.debugger.get_exact_label(addr)
            if exact_lbl:
                is_os_lbl = exact_lbl.startswith("OS_")
                tag = "os_section" if is_os_lbl else "section"
                pretty = self._format_label_pretty(exact_lbl)
                self.dis_tree.insert("", tk.END, values=(
                    "",
                    f"x{addr:04X}",
                    "────",
                    f"▸ {pretty}",
                ), tags=(tag,))

            bp_mark = "●" if is_bp else ""
            prefix = "➜ " if is_pc else "  "
            row_tags = ("bp_row",) if is_bp else ()
            iid = self.dis_tree.insert("", tk.END, values=(
                bp_mark,
                f"x{addr:04X}",
                f"x{code:04X}",
                f"{prefix}{dis}",
            ), tags=row_tags)
            self._addr_to_iid[addr] = iid
            if is_pc:
                self._last_pc_drawn = addr

        end_addr = rows[-1][0] if rows else start
        self.mem_range_var.set(f"x{start:04X}–x{end_addr:04X}")
        self._update_bp_counter()

        target = focus_addr if focus_addr is not None else self.debugger.cpu.pc
        if target in self._addr_to_iid:
            iid = self._addr_to_iid[target]
            self.dis_tree.selection_set(iid)
            self.dis_tree.see(iid)
            self._update_context_bar(target)

    def _refresh_single_row(self, addr: int):
        """Actualiza O(1) una sola fila en la vista de memoria (para PC o breakpoint)."""
        iid = self._addr_to_iid.get(addr)
        if not iid:
            return
        cpu = self.debugger.cpu
        code = cpu.mem.peek16(addr)
        from isa import disassemble
        dis = disassemble(code, addr, cpu.symbols)
        is_pc = (addr == cpu.pc)
        is_bp = (addr in self.debugger.breakpoints)
        bp_mark = "●" if is_bp else ""
        prefix = "➜ " if is_pc else "  "
        row_tags = ("bp_row",) if is_bp else ()
        self.dis_tree.item(iid, values=(bp_mark, f"x{addr:04X}", f"x{code:04X}", f"{prefix}{dis}"), tags=row_tags)

    def focus_memory_address(self, addr: int):
        """Mueve la vista de memoria hasta `addr` (en cualquier punto de los 64 KB) y la selecciona."""
        addr = addr & ~1
        if addr not in self._addr_to_iid:
            win_count = max(256, min(self._view_count, 512))
            new_start = max(0, (addr - 32) & ~1)
            self._populate_memory_view(new_start, win_count, focus_addr=addr)
        else:
            iid = self._addr_to_iid[addr]
            self.dis_tree.selection_set(iid)
            self.dis_tree.see(iid)
            self._update_context_bar(addr)

    def shift_memory_view(self, delta_words: int):
        """Desplaza el mapa de memoria hacia arriba/abajo por bloques dentro de los 64 KB."""
        new_start = max(0, min(0xFFFF - 2, self._view_start + delta_words * 2)) & ~1
        win_count = max(256, min(self._view_count, 512))
        self._populate_memory_view(new_start, win_count, focus_addr=new_start)

    def jump_to_pc(self):
        pc = self.debugger.cpu.pc
        if pc not in self._addr_to_iid:
            if self.debugger.blob and self.debugger.origin <= pc < self.debugger.origin + len(self.debugger.blob):
                self._rebuild_disassembly_for_program()
            else:
                self.focus_memory_address(pc)
        else:
            iid = self._addr_to_iid[pc]
            self.dis_tree.selection_set(iid)
            self.dis_tree.see(iid)

    def jump_to_query(self):
        query = self.nav_var.get().strip()
        if not query:
            self.jump_to_pc()
            return
        addr = self.debugger.resolve_target(query)
        if addr is None:
            self.status_var.set(f"No se encontró función ni dirección para '{query}'.")
            return
        self.focus_memory_address(addr)
        lbl = self.debugger.get_addr_label(addr)
        extra = f" ({lbl})" if lbl else ""
        self.status_var.set(f"Vista en x{addr:04X}{extra}.")

    def toggle_breakpoint_from_query(self):
        query = self.nav_var.get().strip()
        if query:
            addr = self.debugger.resolve_target(query)
            if addr is None:
                self.status_var.set(f"No se encontró función ni dirección para '{query}'.")
                return
        else:
            sel = self.dis_tree.selection()
            if not sel:
                self.status_var.set("Escribí una función/dirección o seleccioná una línea para poner BP.")
                return
            vals = self.dis_tree.item(sel[0], "values")
            addr = int(vals[1].lstrip("xX"), 16)

        added = self.debugger.toggle_breakpoint(addr)
        self.focus_memory_address(addr)
        self._refresh_single_row(addr)
        self._update_bp_counter()
        lbl = self.debugger.get_addr_label(addr)
        extra = f" ({lbl})" if lbl else ""
        action = "agregado" if added else "quitado"
        self.status_var.set(f"Breakpoint {action} en x{addr:04X}{extra}.")

    def clear_all_breakpoints(self):
        old_bps = list(self.debugger.breakpoints)
        self.debugger.breakpoints.clear()
        for a in old_bps:
            self._refresh_single_row(a)
        self._update_bp_counter()
        self.status_var.set("Breakpoints limpiados.")

    def _on_tree_double_click(self, event):
        item = self.dis_tree.selection()
        if not item:
            return
        values = self.dis_tree.item(item[0], "values")
        if values:
            try:
                addr = int(values[1].lstrip("xX"), 16)
                added = self.debugger.toggle_breakpoint(addr)
                self._refresh_single_row(addr)
                self._update_bp_counter()
                lbl = self.debugger.get_addr_label(addr)
                extra = f" ({lbl})" if lbl else ""
                action = "agregado" if added else "quitado"
                self.status_var.set(f"Breakpoint {action} en x{addr:04X}{extra}.")
            except ValueError:
                pass

    def update_ui_state(self):
        cpu = self.debugger.cpu

        # 1. PC
        self.pc_val_label.config(text=f"x{cpu.pc:04X}")

        # 2. Banderas NZP
        self.lbl_fl_n.config(bg="#FF4D4D" if cpu.n else "#E0E0E0", fg="white" if cpu.n else "#333333")
        self.lbl_fl_z.config(bg="#4D79FF" if cpu.z else "#E0E0E0", fg="white" if cpu.z else "#333333")
        self.lbl_fl_p.config(bg="#00CC66" if cpu.p else "#E0E0E0", fg="white" if cpu.p else "#333333")

        # 3. Registros R0..R7
        for r in range(NUM_REGS):
            val = cpu.regs[r]
            signed = to_int16(val)
            changed = (val != self.prev_regs[r])
            lbl = self.reg_labels[r]
            lbl.config(text=f"x{val:04X} ({signed:>6})",
                       bg="#FFF3CD" if changed else "#F8F9FA",
                       fg="#856404" if changed else "#000000")
        self.prev_regs = list(cpu.regs)

        # 4. Desensamblado (actualización incremental O(1) sobre el mapa scrollable)
        self.update_disassembly_view()

        # 5. Métricas de ejecución y espacio de memoria de usuario (sin OS)
        st = cpu.stats()
        if cpu.contar_os:
            self.stats_exec_var.set(
                f"Total: {st['instrucciones']:,} "
                f"(Usr: {st['instrucciones_usuario']:,} + OS: {st['instrucciones_os']:,})  |  "
                f"Fetches: {st['palabras_buscadas']:,}"
            )
        else:
            self.stats_exec_var.set(
                f"Instrucciones: {st['instrucciones']:,}  |  "
                f"Fetches: {st['palabras_buscadas']:,}"
            )
        self.stats_io_var.set(
            f"Lecturas: {st['bytes_leidos']:,} B  |  "
            f"Escrituras: {st['bytes_escritos']:,} B  |  "
            f"Dir. tocadas: {st['direcciones_tocadas']:,}"
        )
        prog_b = st["memoria_programa_bytes"]
        dyn_b = st["memoria_pila_datos_bytes"]
        usr_b = st["memoria_usuario_bytes"]
        pct = (usr_b / cpu.mem.size) * 100.0 if cpu.mem.size else 0.0
        self.mem_prog_var.set(
            f"Programa cargado: {prog_b:,} B ({prog_b // 2:,} pal.)  |  Pila / datos: {dyn_b:,} B"
        )
        self.mem_total_var.set(
            f"Espacio total usuario (sin OS): {usr_b:,} B  ({pct:.2f}% de 64 KB)"
        )

    def update_disassembly_view(self):
        pc = self.debugger.cpu.pc
        if not self._addr_to_iid:
            self._rebuild_disassembly_for_program()
            return

        if pc not in self._addr_to_iid:
            # Si PC salió del rango visible (p. ej. al entrar a OS x0400 o volver a usuario), reposicionar
            if self.debugger.blob and self.debugger.origin <= pc < self.debugger.origin + len(self.debugger.blob):
                self._rebuild_disassembly_for_program()
            else:
                self.focus_memory_address(pc)
            return

        prev_pc = self._last_pc_drawn
        if prev_pc is not None and prev_pc != pc:
            self._refresh_single_row(prev_pc)
        self._refresh_single_row(pc)
        self._last_pc_drawn = pc

        iid = self._addr_to_iid[pc]
        self.dis_tree.selection_set(iid)
        self.dis_tree.see(iid)
        self._update_context_bar(pc)
        self._update_bp_counter()


def main(argv=None):
    parser = argparse.ArgumentParser(description="Interfaz Gráfica del Simulador Skynet (ISA 16-bit) - Grupo 30")
    parser.add_argument("program", nargs="?", default=None, help="archivo .asm, .hex o .bin opcional")
    parser.add_argument("--contar-os", action="store_true", default=False,
                        help="inicia con el conteo de rutinas OS activado (por defecto desactivado)")
    args = parser.parse_args(argv)
    app = ISA16GUI(args.program, contar_os=args.contar_os)
    app.mainloop()


if __name__ == "__main__":
    main()
