import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, simpledialog, ttk

from CPU import CPU
from ensamblador import AssemblyError, LC3Assembler


MAX_INSTRUCTIONS = 1000_000
SAMPLE_PROGRAM = ".ORIG x3000\n\tADD R0, R0, #2\n\tADD R1, R0, #3\n\tHALT\n.END\n"


class ISAWorkbench:
    def __init__(self, root):
        self.root = root
        self.root.title("AC-12")
        self.root.geometry("1100x720")
        self.root.minsize(850, 560)
        self.root.configure(bg="#eef2f4")

        self.assembler = LC3Assembler()
        self.last_assembly = None
        self.current_path = None
        self.run_results = queue.Queue()
        self.run_active = False
        self.stop_event = None
        self.run_thread = None
        self.fractional_bits = 0

        self._configure_style()
        self._build_interface()
        self._set_editor(SAMPLE_PROGRAM)
        self._set_machine_code("Ensamble el programa para ver el código máquina.")
        self._set_execution("La ejecución y el estado de la CPU aparecerán aquí.")

    def _configure_style(self):
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("App.TFrame", background="#eef2f4")
        style.configure("Panel.TFrame", background="#ffffff")
        style.configure("Title.TLabel", background="#eef2f4", foreground="#172d32", font=("Segoe UI Semibold", 19))
        style.configure("Hint.TLabel", background="#eef2f4", foreground="#617477", font=("Segoe UI", 10))
        style.configure("PanelTitle.TLabel", background="#ffffff", foreground="#263c40", font=("Segoe UI Semibold", 10))
        style.configure("Status.TLabel", background="#dce6e6", foreground="#31494d", padding=(10, 6), font=("Segoe UI", 9))
        style.configure("TButton", font=("Segoe UI Semibold", 9), padding=(10, 7))
        style.configure("Accent.TButton", background="#087e75", foreground="#ffffff")
        style.map("Accent.TButton", background=[("active", "#066b64"), ("disabled", "#9bbab6")])
        style.configure("Machine.Treeview", font=("Cascadia Code", 12), rowheight=28)
        style.configure("Machine.Treeview.Heading", font=("Segoe UI Semibold", 11))
    def _build_interface(self):
        outer = ttk.Frame(self.root, style="App.TFrame", padding=(18, 14))
        outer.pack(fill="both", expand=True)
        outer.rowconfigure(1, weight=1)
        outer.columnconfigure(0, weight=1)

        header = ttk.Frame(outer, style="App.TFrame")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 14))
        header.columnconfigure(0, weight=1)
        heading = ttk.Frame(header, style="App.TFrame")
        heading.grid(row=0, column=0, sticky="w")
        ttk.Label(heading, text="AC-12", style="Title.TLabel").pack(anchor="w")
        ttk.Label(heading, text="Ensamblador y simulador de CPU", style="Hint.TLabel").pack(anchor="w", pady=(2, 0))

        actions = ttk.Frame(header, style="App.TFrame")
        actions.grid(row=0, column=1, sticky="e")
        ttk.Label(actions, text="Formato Q:", style="Hint.TLabel").pack(side="left", padx=(0, 5))
        self.q_format_var = tk.StringVar(value="Q15.0")
        self.q_format_selector = ttk.Combobox(
            actions,
            textvariable=self.q_format_var,
            values=tuple(f"Q{15 - bits}.{bits}" for bits in range(16)),
            state="readonly",
            width=7,
        )
        self.q_format_selector.pack(side="left", padx=(0, 7))
        self.q_format_selector.bind("<<ComboboxSelected>>", self._q_format_changed)
        ttk.Button(actions, text="Abrir archivo", command=self.open_file).pack(side="left", padx=(0, 7))
        ttk.Button(actions, text="Guardar", command=self.save_file).pack(side="left", padx=(0, 7))
        ttk.Button(actions, text="Guardar como", command=self.save_as_file).pack(side="left", padx=(0, 7))
        ttk.Button(actions, text="Ensamblar", style="Accent.TButton", command=self.assemble).pack(side="left", padx=(0, 7))
        self.run_button = ttk.Button(actions, text="Ejecutar", command=self.run_program, state="disabled")
        self.run_button.pack(side="left")
        self.stop_button = ttk.Button(actions, text="Detener", command=self.stop_program, state="disabled")
        self.stop_button.pack(side="left", padx=(7, 0))

        workspace = ttk.Panedwindow(outer, orient="horizontal")
        workspace.grid(row=1, column=0, sticky="nsew")
        source_panel = ttk.Frame(workspace, style="Panel.TFrame", padding=12)
        result_panel = ttk.Frame(workspace, style="Panel.TFrame", padding=12)
        workspace.add(source_panel, weight=3)
        workspace.add(result_panel, weight=2)

        source_panel.rowconfigure(1, weight=1)
        source_panel.columnconfigure(0, weight=1)
        ttk.Label(source_panel, text="CÓDIGO FUENTE", style="PanelTitle.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 9))
        editor_frame = ttk.Frame(source_panel, style="Panel.TFrame")
        editor_frame.grid(row=1, column=0, sticky="nsew")
        editor_frame.rowconfigure(0, weight=1)
        editor_frame.columnconfigure(0, weight=1)
        self.editor = tk.Text(
            editor_frame,
            wrap="none",
            undo=True,
            font=("Cascadia Code", 11),
            bg="#15292e",
            fg="#e5eeee",
            insertbackground="#f3c969",
            selectbackground="#176e68",
            relief="flat",
            padx=12,
            pady=12,
            spacing1=2,
        )
        editor_scroll_y = ttk.Scrollbar(editor_frame, orient="vertical", command=self.editor.yview)
        editor_scroll_x = ttk.Scrollbar(editor_frame, orient="horizontal", command=self.editor.xview)
        self.editor.configure(yscrollcommand=editor_scroll_y.set, xscrollcommand=editor_scroll_x.set)
        self.editor.grid(row=0, column=0, sticky="nsew")
        editor_scroll_y.grid(row=0, column=1, sticky="ns")
        editor_scroll_x.grid(row=1, column=0, sticky="ew")
        self.editor.bind("<KeyRelease>", self._source_changed)

        result_panel.rowconfigure(1, weight=1)
        result_panel.columnconfigure(0, weight=1)
        ttk.Label(result_panel, text="RESULTADOS", style="PanelTitle.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 9))
        results_content = ttk.Frame(result_panel, style="Panel.TFrame")
        results_content.grid(row=1, column=0, sticky="nsew")
        results_content.rowconfigure(1, weight=0)
        results_content.rowconfigure(3, weight=1)
        results_content.columnconfigure(0, weight=1)

        ttk.Label(results_content, text="EJECUCIÓN", style="PanelTitle.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 6)
        )
        execution_frame = ttk.Frame(results_content, style="Panel.TFrame")
        execution_frame.grid(row=1, column=0, sticky="nsew", pady=(0, 12))
        self.execution_output = self._make_output(
            execution_frame,
            show_scrollbar=True,
            height=17,
        )

        ttk.Label(results_content, text="CÓDIGO MÁQUINA", style="PanelTitle.TLabel").grid(
            row=2, column=0, sticky="w", pady=(0, 6)
        )
        machine_section = ttk.Frame(results_content, style="Panel.TFrame")
        machine_section.grid(row=3, column=0, sticky="nsew")
        machine_section.rowconfigure(0, weight=1)
        machine_section.columnconfigure(0, weight=1)
        self.machine_text_frame = ttk.Frame(machine_section, style="Panel.TFrame")
        self.machine_text_frame.grid(row=0, column=0, sticky="nsew")
        self.machine_text_frame.rowconfigure(0, weight=1)
        self.machine_text_frame.columnconfigure(0, weight=1)
        self.machine_output = self._make_output(self.machine_text_frame)
        self.machine_listing_frame = ttk.Frame(machine_section, style="Panel.TFrame")
        self.machine_listing_frame.rowconfigure(0, weight=1)
        self.machine_listing_frame.columnconfigure(0, weight=1)
        self.machine_listing = ttk.Treeview(
            self.machine_listing_frame,
            columns=("address", "word", "instruction"),
            show="headings",
            style="Machine.Treeview",
        )
        self.machine_listing.heading("address", text="Dirección de memoria")
        self.machine_listing.heading("word", text="Código máquina")
        self.machine_listing.heading("instruction", text="Instrucción")
        self.machine_listing.column("address", width=125, minwidth=105, anchor="center", stretch=False)
        self.machine_listing.column("word", width=115, minwidth=100, anchor="center", stretch=False)
        self.machine_listing.column("instruction", width=220, minwidth=150, anchor="w", stretch=True)
        listing_scroll_y = ttk.Scrollbar(
            self.machine_listing_frame,
            orient="vertical",
            command=self.machine_listing.yview,
        )
        self.machine_listing.configure(yscrollcommand=listing_scroll_y.set)
        self.machine_listing.grid(row=0, column=0, sticky="nsew")
        listing_scroll_y.grid(row=0, column=1, sticky="ns")
        self.status_var = tk.StringVar(value="Listo")
        ttk.Label(outer, textvariable=self.status_var, style="Status.TLabel", anchor="w").grid(row=2, column=0, sticky="ew", pady=(12, 0))

    @staticmethod
    def _make_output(parent, show_scrollbar=True, height=24):
        parent.rowconfigure(0, weight=1)
        parent.columnconfigure(0, weight=1)
        output = tk.Text(
            parent,
            wrap="word",
            state="disabled",
            font=("Cascadia Code", 10),
            height=height,
            bg="#f5f8f7",
            fg="#263c40",
            relief="flat",
            padx=10,
            pady=10,
        )
        output.grid(row=0, column=0, sticky="nsew")
        if show_scrollbar:
            scrollbar = ttk.Scrollbar(parent, orient="vertical", command=output.yview)
            output.configure(yscrollcommand=scrollbar.set)
            scrollbar.grid(row=0, column=1, sticky="ns")
        return output

    def _set_editor(self, text):
        self.editor.delete("1.0", "end")
        self.editor.insert("1.0", text)
        self.last_assembly = None
        self.run_button.configure(state="disabled")

    @staticmethod
    def _set_text(widget, text):
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", text)
        widget.configure(state="disabled")

    def _set_machine_code(self, text):
        if self.machine_listing_frame.winfo_manager():
            self.machine_listing_frame.grid_remove()
        if not self.machine_text_frame.winfo_manager():
            self.machine_text_frame.grid(row=0, column=0, sticky="nsew")
        self._set_text(self.machine_output, text)

    def _set_machine_listing(self, listing):
        if self.machine_text_frame.winfo_manager():
            self.machine_text_frame.grid_remove()
        self.machine_listing_frame.grid(row=0, column=0, sticky="nsew")
        self.machine_listing.delete(*self.machine_listing.get_children())
        for address, word, instruction in listing:
            self.machine_listing.insert(
                "",
                "end",
                values=(f"x{address:04X}", f"x{word:04X}", instruction),
            )

    def _set_execution(self, text):
        self._set_text(self.execution_output, text)

    def _source_changed(self, _event=None):
        if self.last_assembly is not None:
            source = self.editor.get("1.0", "end-1c")
            if source != self.last_assembly[0]:
                self.last_assembly = None
                self.run_button.configure(state="disabled")
                self.status_var.set("El código cambió; vuelva a ensamblar antes de ejecutar.")

    def open_file(self):
        path = filedialog.askopenfilename(
            title="Abrir código ensamblador",
            filetypes=(("Archivos ensamblador", "*.asm *.s *.txt"), ("Todos los archivos", "*.*")),
        )
        if not path:
            return
        try:
            source = Path(path).read_text(encoding="utf-8-sig")
        except OSError as error:
            self.status_var.set(f"No se pudo abrir el archivo: {error}")
            return
        self.current_path = Path(path)
        self._set_editor(source)
        self.status_var.set(f"Archivo abierto: {self.current_path.name}")

    def save_file(self):
        if self.current_path is None:
            self.save_as_file()
            return
        try:
            self.current_path.write_text(self.editor.get("1.0", "end-1c"), encoding="utf-8")
        except OSError as error:
            self.status_var.set(f"No se pudo guardar el archivo: {error}")
            return
        self.status_var.set(f"Archivo guardado: {self.current_path.name}")

    def save_as_file(self):
        path = filedialog.asksaveasfilename(
            title="Guardar código ensamblador como",
            defaultextension=".asm",
            filetypes=(("Archivos ensamblador", "*.asm"), ("Archivos de texto", "*.txt"), ("Todos los archivos", "*.*")),
        )
        if not path:
            return
        self.current_path = Path(path)
        self.save_file()

    def assemble(self):
        source = self.editor.get("1.0", "end-1c")
        try:
            origin, words = self.assembler.assemble(
                source,
                self.fractional_bits,
                source_path=self.current_path,
            )
        except AssemblyError as error:
            diagnostics = "\n".join(f"Línea {line}: {message}" for line, message in error.diagnostics)
            self.last_assembly = None
            self.run_button.configure(state="disabled")
            self._set_machine_code("El ensamblado encontró errores:\n\n" + diagnostics)
            self.status_var.set("Ensamblado fallido; revise los errores.")
            return
        self.last_assembly = (source, origin, words, self.fractional_bits)
        self.run_button.configure(state="disabled" if self.run_active else "normal")
        self._set_machine_listing(self.assembler.last_listing)
        self._set_execution("Ensamblado correctamente. Pulse Ejecutar para iniciar la CPU.")
        q_format = self.q_format_var.get()
        self.status_var.set(f"Formato {self.assembler.last_format}, {q_format}: {len(words)} palabras desde x{origin:04X}.")

    def _q_format_changed(self, _event=None):
        selected = self.q_format_var.get()
        self.fractional_bits = int(selected.split(".")[-1])
        if self.last_assembly is not None and self.last_assembly[3] != self.fractional_bits:
            self.last_assembly = None
            self.run_button.configure(state="disabled")
            self.status_var.set("Cambió el formato Q; vuelva a ensamblar antes de ejecutar.")

    def run_program(self):
        if self.run_active:
            self.status_var.set("La CPU ya está ejecutando un programa.")
            return
        if self.last_assembly is None:
            self.status_var.set("Ensamble el código antes de ejecutarlo.")
            return

        _source, origin, words, fractional_bits = self.last_assembly
        needs_character_input = False
        word_index = 0
        while word_index < len(words):
            word = words[word_index]
            opcode = word >> 11
            if opcode in (0b10010, 0b11010, 0b11011):
                word_index += 2
                continue
            if opcode == 0b01111 and (word & 0xFF) in (0x20, 0x23):
                needs_character_input = True
                break
            word_index += 1
        trap_input = ""
        if needs_character_input:
            trap_input = simpledialog.askstring(
                "Entrada de TRAP",
                "Escriba los caracteres que leerán GETC e IN:",
                parent=self.root,
            )
            if trap_input is None:
                self.status_var.set("Ejecución cancelada.")
                return

        self.run_active = True
        self.stop_event = threading.Event()
        self.run_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self._set_execution("Ejecución en curso...")
        self.run_thread = threading.Thread(
            target=self._execute_program,
            args=(origin, list(words), self.stop_event, trap_input, fractional_bits),
            daemon=True,
        )
        self.run_thread.start()
        self.root.after(30, self._poll_run_result)

    def stop_program(self):
        if self.stop_event is not None:
            self.stop_event.set()
            self.status_var.set("Deteniendo la CPU...")

    def _execute_program(self, origin, words, stop_event, trap_input="", fractional_bits=0):
        cpu = CPU()
        cpu.trap_input = trap_input
        try:
            cpu.load_program(origin, words)
        except ValueError as error:
            self.run_results.put(
                (f"Error al cargar el programa: {error}", "Error al cargar el programa.")
            )
            return

        result = cpu.run(max_instructions=MAX_INSTRUCTIONS, stop_event=stop_event)
        outcome = result["outcome"]
        status = result["status"]
        steps = result["steps"]
        memory_usage = result["memory_usage"]

        q_integer_bits = 15 - fractional_bits
        scale = 1 << fractional_bits
        register_state = "\n".join(
            f"R{index} = x{value:04X}  ({value})  "
            f"Q{q_integer_bits}.{fractional_bits} = "
            f"{((value - 0x10000) if value & 0x8000 else value) / scale:.{fractional_bits}f}"
            for index, value in enumerate(cpu.R)
        )
        details = (
            f"{outcome}\n"
            f"Instrucciones ejecutadas: {steps}\n"
            f"PC = x{cpu.PC:04X}    IR = x{cpu.IR:04X}\n"
            f"CC = {cpu.CC:03b}  V = {cpu.V}  C = {cpu.C}\n\n"
            f"Registros\n{register_state}"
        )
        written_addresses = sorted(cpu.memory_write_addresses)
        memory_details = (
            f"\n\nUso de memoria\n"
            f"Programa cargado (código + datos): {memory_usage['loaded_bytes']} bytes "
            f"({memory_usage['loaded_words']} palabras, "
            f"x{memory_usage['loaded_min']:04X}-x{memory_usage['loaded_max']:04X})\n"
            f"Lecturas: {memory_usage['read_bytes']} direcciones distintas | "
            f"Escrituras: {memory_usage['write_bytes']} direcciones distintas\n"
            f"Memoria accedida en ejecución: {memory_usage['execution_bytes']} bytes\n"
            f"Total de memoria utilizada: {memory_usage['total_used_bytes']} bytes "
            f"de {memory_usage['total_memory']} bytes ({memory_usage['usage_percent']:.2f}%)"
        )
        if written_addresses:
            memory_details += (
                "\nDirecciones modificadas: "
                + ", ".join(f"x{address:04X}" for address in written_addresses[:32])
            )
            if len(written_addresses) > 32:
                memory_details += f" ... (+{len(written_addresses) - 32})"
        details += memory_details
        if cpu.trap_output:
            details += "\n\nSalida de TRAP\n" + "".join(cpu.trap_output)
        self.run_results.put((details, status))

    def _poll_run_result(self):
        try:
            details, status = self.run_results.get_nowait()
        except queue.Empty:
            if self.run_thread is not None and self.run_thread.is_alive():
                self.root.after(30, self._poll_run_result)
                return
            details = "La ejecución terminó sin devolver un resultado."
            status = "Error inesperado durante la ejecución."

        self.run_active = False
        self.stop_event = None
        self.run_thread = None
        self.stop_button.configure(state="disabled")
        source = self.editor.get("1.0", "end-1c")
        can_run = (
            self.last_assembly is not None
            and self.last_assembly[0] == source
            and self.last_assembly[3] == self.fractional_bits
        )
        self.run_button.configure(state="normal" if can_run else "disabled")
        self.status_var.set(status)
        self._set_execution(details)


def main():
    root = tk.Tk()
    ISAWorkbench(root)
    root.mainloop()


if __name__ == "__main__":
    main()
