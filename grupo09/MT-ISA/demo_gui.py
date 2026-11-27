"""Interfaz de escritorio para ejecutar y examinar binarios del Lab 3c."""

import argparse
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, font, messagebox, ttk

from disassembler import instruction_mnemonic
from simulator import Machine, MachineError, TARGETS


ROOT = Path(__file__).resolve().parent
DEMO_IMAGES = {"lc3": "lc3.bin", "lab3c": "opt.bin", "lab3c-v2": "v2.bin"}
TARGET_LABELS = {"lc3": "LC-3 de 4 bits", "lab3c": "Lab 3c de 5 bits", "lab3c-v2": "Lab 3c v2 de 5 bits"}
SPEEDS = {"Lenta": (1, 180), "Media": (32, 45), "Rápida": (600, 16)}
MEMORY_ROWS = 8
MEMORY_BASE_ZOOM = 125
MEMORY_COLUMNS = (
    ("address", "Dirección", 85, "xFFFF"),
    ("word", "Palabra", 75, "xFFFF"),
    ("bytes", "Bytes", 60, "FF FF"),
    ("marks", "Marca", 90, "PC · Escrita"),
)
ZOOM_LEVELS = (100, 125, 150, 175, 200)
BG = "#101821"
PANEL = "#182531"
FIELD = "#111D28"
BORDER = "#304454"
TEXT = "#E8F2F5"
MUTED = "#ACC0CB"
ACCENT = "#82E1BD"
ERROR = "#FF9F9F"
MONO = ("TkFixedFont", 11)


def demo_image(target):
    binary = ROOT / "build" / "complete" / DEMO_IMAGES[target]
    if binary.is_file():
        return binary.read_bytes()

    from assembler import assemble

    if target == "lc3":
        return assemble(ROOT / "original" / "main_grupo27.asm", target="lc3").image
    modules = ("optimized_v2", "optimized", "ported") if target == "lab3c-v2" else ("optimized", "ported")
    return assemble(
        ROOT / "ported" / "main_grupo27.asm",
        target=target,
        module_dirs=tuple(ROOT / module for module in modules),
    ).image


def format_count(value):
    return f"{value:,}".replace(",", ".")


def memory_address(text):
    text = text.strip().lower().removeprefix("0x").removeprefix("x")
    if not 1 <= len(text) <= 4 or any(char not in "0123456789abcdef" for char in text):
        raise ValueError("Escribí una dirección hexadecimal entre x0000 y xFFFF.")
    return int(text, 16)


def instruction_preview(machine):
    if machine.halted:
        return "-", "-"
    try:
        word = machine.read_word(machine.pc)
    except MachineError:
        return "Dirección impar", "-"
    width = 4 if machine.legacy else 5
    opcode = word >> (16 - width)
    mnemonic = instruction_mnemonic(word, target=machine.target)
    return f"x{word:04X}   ·   opcode {opcode:0{width}b}", mnemonic or "no canónico"


class ZoomControls(ttk.Frame):
    def __init__(self, parent, on_change, *, initial=100, caption=None, panel=False):
        super().__init__(parent, style="Panel.TFrame" if panel else "TFrame")
        self.index = ZOOM_LEVELS.index(initial)
        self.on_change = on_change
        self.text = tk.StringVar(self)
        label_style = "PanelMuted.TLabel" if panel else "Muted.TLabel"
        if caption:
            ttk.Label(self, text=caption, style=label_style).pack(side="left", padx=(0, 6))
        self.smaller = ttk.Button(self, text="-", width=2, command=lambda: self.adjust(-1))
        self.smaller.pack(side="left")
        ttk.Label(self, textvariable=self.text, width=6, anchor="center", style=label_style).pack(side="left")
        self.larger = ttk.Button(self, text="+", width=2, command=lambda: self.adjust(1))
        self.larger.pack(side="left")
        self._sync()

    @property
    def value(self):
        return ZOOM_LEVELS[self.index]

    def _sync(self):
        self.text.set(f"{self.value} %")
        self.smaller.state(["disabled"] if self.index == 0 else ["!disabled"])
        self.larger.state(["disabled"] if self.index == len(ZOOM_LEVELS) - 1 else ["!disabled"])

    def adjust(self, direction):
        self.index = min(len(ZOOM_LEVELS) - 1, max(0, self.index + direction))
        self._sync()
        self.on_change(self.value)


class SimulatorDemo:
    def __init__(
        self, root, image_path=None, *, target="lab3c-v2", max_steps=10_000_000, input_data=""
    ):
        self.root = root
        self.max_steps = max_steps
        self.input_data = input_data
        self.machine = None
        self.image = None
        self.image_name = ""
        self.benchmark_loaded = False
        self.running = False
        self.job = None
        self.fault = ""
        self.console_length = 0
        self.memory_base = 0

        root.title("Simulador Lab 3c · Grupo 9")
        root.geometry("1140x780")
        root.minsize(900, 640)
        root.configure(bg=BG)
        self._configure_style()
        self._build_controls(target)

        root.bind("<F5>", lambda _: self.pause() if self.running else self.play())
        root.bind("<F10>", lambda _: self.single_step())
        root.protocol("WM_DELETE_WINDOW", self.close)

        if image_path is None:
            self.open_demo()
        else:
            self._open_path(Path(image_path), target)

    def _configure_style(self):
        style = ttk.Style(self.root)
        style.theme_use("clam")
        self.register_font = font.nametofont("TkFixedFont", root=self.root).copy()
        style.configure(".", background=BG, foreground=TEXT, font=("TkDefaultFont", 11))
        style.configure("TFrame", background=BG)
        style.configure("Panel.TFrame", background=PANEL)
        style.configure("TLabel", background=BG, foreground=TEXT)
        style.configure("Title.TLabel", font=("TkDefaultFont", 23, "bold"))
        style.configure("Muted.TLabel", foreground=MUTED)
        style.configure("Error.TLabel", foreground=ERROR)
        style.configure("Panel.TLabel", background=PANEL, foreground=TEXT)
        style.configure("PanelMuted.TLabel", background=PANEL, foreground=MUTED)
        style.configure("Metric.TLabel", background=PANEL, foreground=TEXT)
        style.configure("Section.TLabel", background=PANEL, foreground=TEXT, font=("TkDefaultFont", 12, "bold"))
        style.configure("Preview.TLabel", background=PANEL, foreground=ACCENT, font=self.register_font)
        style.configure("TButton", background=PANEL, bordercolor=BORDER, padding=(10, 6))
        style.map("TButton", background=[("active", BORDER)], foreground=[("disabled", MUTED)])
        style.configure("Run.TButton", background=ACCENT, foreground=BG)
        style.map("Run.TButton", background=[("disabled", PANEL), ("active", "#A5F3D1")])
        style.configure("TCheckbutton", background=PANEL, foreground=TEXT)
        style.map("TCheckbutton", background=[("active", PANEL)])
        style.configure("TEntry", fieldbackground=FIELD, foreground=TEXT, bordercolor=BORDER)
        style.configure("TCombobox", fieldbackground=FIELD, foreground=TEXT, bordercolor=BORDER)
        style.map("TCombobox", fieldbackground=[("readonly", FIELD)])
        style.configure("Treeview", background=FIELD, fieldbackground=FIELD, bordercolor=BORDER,
                        foreground=TEXT)
        style.configure("Treeview.Heading", background=PANEL, foreground=MUTED, padding=(6, 4))
        style.map("Treeview.Heading", background=[("active", PANEL)])
        style.map("Treeview", background=[("selected", BORDER)], foreground=[("selected", TEXT)])
        style.configure("TPanedwindow", background=BG)

    def _build_controls(self, target):
        content = ttk.Frame(self.root, padding=(20, 16))
        content.pack(fill="both", expand=True)
        content.columnconfigure(0, weight=1)
        content.rowconfigure(3, weight=1)

        heading = ttk.Frame(content)
        heading.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        ttk.Label(heading, text="Simulador Lab 3c", style="Title.TLabel").pack(side="left")
        self.loaded = tk.StringVar(self.root, "Sin imagen")
        ttk.Label(heading, textvariable=self.loaded, style="Muted.TLabel").pack(side="right", pady=(8, 0))

        toolbar = ttk.Frame(content)
        toolbar.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        self.play_button = ttk.Button(toolbar, text="Ejecutar", command=self.play, style="Run.TButton")
        self.play_button.pack(side="left")
        self.pause_button = ttk.Button(toolbar, text="Pausar", command=self.pause)
        self.pause_button.pack(side="left", padx=(4, 0))
        self.step_button = ttk.Button(toolbar, text="Paso", command=self.single_step)
        self.step_button.pack(side="left", padx=(4, 0))
        self.reset_button = ttk.Button(toolbar, text="Reiniciar", command=self.reset)
        self.reset_button.pack(side="left", padx=(4, 8))
        self.speed = tk.StringVar(self.root, "Rápida")
        ttk.Combobox(toolbar, textvariable=self.speed, values=tuple(SPEEDS), state="readonly", width=8).pack(side="left")

        self.target = tk.StringVar(self.root, target)
        ttk.Button(toolbar, text="Cargar benchmark", command=self.open_demo).pack(side="right")
        ttk.Button(toolbar, text="Abrir binario", command=self.open_file).pack(side="right", padx=(4, 8))
        self.format_selector = ttk.Combobox(
            toolbar, textvariable=self.target, state="readonly", values=TARGETS, width=10
        )
        self.format_selector.pack(side="right")
        self.format_selector.bind("<<ComboboxSelected>>", self._change_format)
        self.format_label = tk.StringVar(self.root, "Formato del archivo")
        ttk.Label(toolbar, textvariable=self.format_label, style="Muted.TLabel").pack(side="right", padx=(0, 6))

        self._build_metrics(content)

        panes = ttk.Panedwindow(content, orient="horizontal")
        panes.grid(row=3, column=0, sticky="nsew")
        inspector = ttk.Frame(panes, padding=10, style="Panel.TFrame")
        console_panel = ttk.Frame(panes, padding=10, style="Panel.TFrame")
        panes.add(inspector, weight=3)
        panes.add(console_panel, weight=4)
        self._build_inspector(inspector)
        self._build_console(console_panel)

        self.status = tk.StringVar(self.root)
        self.status_label = ttk.Label(content, textvariable=self.status, style="Muted.TLabel")
        self.status_label.grid(row=4, column=0, sticky="ew", pady=(7, 0))
        self._refresh()

    def _build_metrics(self, content):
        section = ttk.Frame(content)
        section.grid(row=2, column=0, sticky="ew", pady=(0, 10))

        self.metric_zoom = ZoomControls(section, self._resize_metrics, initial=200, caption="Tamaño de métricas")
        self.metric_zoom.pack(anchor="e", pady=(0, 4))

        self.metric_title_font = font.nametofont("TkDefaultFont", root=self.root).copy()
        self.metric_value_font = self.metric_title_font.copy()
        self.metric_value_font.configure(weight="bold")

        self.metrics_panel = ttk.Frame(section)
        self.metrics_panel.pack(fill="x")
        titles = (
            ("instructions", "Instrucciones ejecutadas"),
            ("image", "Programa cargado [bytes]"),
            ("memory", "Datos distintos [bytes]"),
            ("traffic", "Tráfico de datos [bytes]"),
        )
        self.metrics = {}
        self.metric_cards = []
        self.metric_titles = tuple(title for _, title in titles)
        self.metric_columns = len(titles)
        for column, (key, title) in enumerate(titles):
            self.metrics_panel.columnconfigure(column, weight=1, uniform="metrics")
            card = ttk.Frame(self.metrics_panel, style="Panel.TFrame")
            card.grid(row=0, column=column, sticky="nsew", padx=(0, 4 if column < len(titles) - 1 else 0))
            label = ttk.Label(card, text=title, style="PanelMuted.TLabel", font=self.metric_title_font)
            label.pack(anchor="w")
            value = tk.StringVar(self.root, "-")
            ttk.Label(card, textvariable=value, style="Metric.TLabel", font=self.metric_value_font).pack(side="bottom", anchor="w")
            self.metric_cards.append((card, label))
            self.metrics[key] = value

        self.metrics_panel.bind("<Configure>", lambda event: self._layout_metrics(event.width))
        self._resize_metrics(self.metric_zoom.value)

    def _resize_metrics(self, zoom):
        self.metric_title_font.configure(size=round(11 * zoom / 100))
        self.metric_value_font.configure(size=round(16 * zoom / 100))
        self.metric_padding = round(10 * zoom / 100)
        for card, _ in self.metric_cards:
            card.configure(padding=(self.metric_padding, round(5 * zoom / 100)))
        self._layout_metrics(self.metrics_panel.winfo_width())

    def _layout_metrics(self, width):
        if width <= 1:
            return
        title_width = max(self.metric_title_font.measure(title) for title in self.metric_titles)
        card_width = title_width + 2 * self.metric_padding + 8
        columns = 4 if width >= 4 * card_width else 2
        if columns != self.metric_columns:
            self.metric_columns = columns
            for column in range(4):
                self.metrics_panel.columnconfigure(
                    column, weight=int(column < columns), uniform="metrics" if column < columns else ""
                )
            for index, (card, _) in enumerate(self.metric_cards):
                row, column = divmod(index, columns)
                card.grid_configure(
                    row=row, column=column, padx=(0, 4 if column < columns - 1 else 0),
                    pady=(0, 4 if row == 0 and columns == 2 else 0),
                )

        available = max(1, width // columns - 2 * self.metric_padding - 8)
        for title, (_, label) in zip(self.metric_titles, self.metric_cards):
            lines = [""]
            for word in title.split():
                candidate = f"{lines[-1]} {word}" if lines[-1] else word
                if lines[-1] and self.metric_title_font.measure(candidate) > available:
                    lines.append(word)
                else:
                    lines[-1] = candidate
            wrapped_title = "\n".join(lines)
            if label.cget("text") != wrapped_title:
                label.configure(text=wrapped_title)

    def _build_state(self, panel):
        state = ttk.Frame(panel, style="Panel.TFrame")
        state.pack(side="top", fill="x", pady=(0, 6))
        state.columnconfigure(0, weight=1)
        state.columnconfigure(2, weight=3)

        self.pc = tk.StringVar(self.root, "PC -")
        self.flags = tk.StringVar(self.root, "N -   Z -   P -   C -")
        self.next_word = tk.StringVar(self.root, "Próxima instrucción -")
        self.mnemonic = tk.StringVar(self.root, "Mnemónico -")
        ttk.Label(state, textvariable=self.pc, style="Preview.TLabel").grid(row=0, column=0, sticky="w", padx=(0, 12))
        flags = ttk.Label(state, textvariable=self.flags, style="Preview.TLabel")
        flags.grid(row=0, column=1, columnspan=2, sticky="ew")
        flags.bind("<Configure>", lambda event: flags.configure(wraplength=event.width))
        for row, value in enumerate((self.next_word, self.mnemonic), start=1):
            preview = ttk.Label(state, textvariable=value, style="Preview.TLabel")
            preview.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(4, 0))
            preview.bind("<Configure>", lambda event: event.widget.configure(wraplength=event.width))

    def _build_inspector(self, panel):
        self._build_state(panel)
        inspector = ttk.Frame(panel, style="Panel.TFrame")
        inspector.pack(side="bottom", fill="x")
        inspector.columnconfigure(0, weight=1)
        inspector.rowconfigure(5, weight=1)
        self._build_registers(inspector)

        ttk.Label(inspector, text="Memoria", style="Section.TLabel").grid(row=2, column=0, sticky="w")
        controls = ttk.Frame(inspector, style="Panel.TFrame")
        controls.grid(row=3, column=0, sticky="ew", pady=(3, 4))
        self.address = tk.StringVar(self.root, "x3000")
        field = ttk.Entry(controls, textvariable=self.address, width=9, font=MONO)
        field.pack(side="left")
        field.bind("<Return>", lambda _: self.seek())
        ttk.Button(controls, text="Ir", command=self.seek).pack(side="left", padx=(3, 7))
        ttk.Button(controls, text="Ant.", width=4, command=lambda: self.turn_page(-1)).pack(side="left")
        ttk.Button(controls, text="Sig.", width=4, command=lambda: self.turn_page(1)).pack(side="left", padx=(3, 0))
        self.follow_pc = tk.BooleanVar(self.root, True)
        ttk.Checkbutton(
            controls, text="Seguir PC", variable=self.follow_pc, command=self._refresh_memory,
        ).pack(side="right")
        self.memory_note = tk.StringVar(self.root, "Direcciones hexadecimales")
        ttk.Label(inspector, textvariable=self.memory_note, style="PanelMuted.TLabel").grid(
            row=4, column=0, sticky="w", pady=(0, 4)
        )

        self._build_memory_table(inspector)

    def _build_memory_table(self, inspector):
        frame = ttk.Frame(inspector, style="Panel.TFrame")
        frame.grid(row=5, column=0, sticky="nsew")
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)

        self.memory_value_font = font.nametofont("TkFixedFont", root=self.root).copy()
        self.memory_heading_font = font.nametofont("TkDefaultFont", root=self.root).copy()
        self.memory_heading_font.configure(size=round(10 * MEMORY_BASE_ZOOM / 100))
        self.memory_value_font.configure(size=round(11 * MEMORY_BASE_ZOOM / 100))
        row_height = max(round(23 * MEMORY_BASE_ZOOM / 100), self.memory_value_font.metrics("linespace") + 6)
        style = ttk.Style(self.root)
        style.configure("Memory.Treeview", font=self.memory_value_font, rowheight=row_height)
        style.configure("Memory.Treeview.Heading", font=self.memory_heading_font)
        self.memory_table = ttk.Treeview(
            frame, columns=tuple(key for key, _, _, _ in MEMORY_COLUMNS),
            show="headings", height=MEMORY_ROWS, style="Memory.Treeview",
        )
        self.memory_table.grid(row=0, column=0, sticky="nsew")
        vertical = ttk.Scrollbar(frame, orient="vertical", command=self.memory_table.yview)
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal = ttk.Scrollbar(frame, orient="horizontal", command=self.memory_table.xview)
        horizontal.grid(row=1, column=0, sticky="ew")
        self.memory_table.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        for key, name, width, sample in MEMORY_COLUMNS:
            minimum = max(self.memory_heading_font.measure(name), self.memory_value_font.measure(sample)) + 16
            self.memory_table.heading(key, text=name)
            self.memory_table.column(
                key, minwidth=minimum, width=max(minimum, round(width * MEMORY_BASE_ZOOM / 100)), anchor="center"
            )
        for index in range(MEMORY_ROWS):
            self.memory_table.insert("", "end", iid=f"memory{index}", values=("-", "-", "-", ""))
        self.memory_table.tag_configure("pc", background="#234439", foreground="#BBF5DE")
        self.memory_table.tag_configure("write", foreground="#FFD5A0")

    def _reveal_memory_pc(self):
        index = (self.machine.pc - self.memory_base) // self.machine.stride
        if 0 <= index < MEMORY_ROWS:
            self.memory_table.see(f"memory{index}")

    def _build_registers(self, inspector):
        heading = ttk.Frame(inspector, style="Panel.TFrame")
        heading.grid(row=0, column=0, sticky="ew")
        self.register_title_font = font.nametofont("TkDefaultFont", root=self.root).copy()
        self.register_title_font.configure(weight="bold")
        ttk.Label(heading, text="Registros", font=self.register_title_font, style="Panel.TLabel").pack(side="left")
        self.register_zoom = ZoomControls(heading, self._resize_registers, initial=200, panel=True)
        self.register_zoom.pack(side="right")

        self.register_panel = ttk.Frame(inspector, style="Panel.TFrame")
        self.register_panel.grid(row=1, column=0, sticky="ew", pady=(3, 10))
        self.register_columns = 4
        self.register_values = []
        self.register_cells = []
        for column in range(4):
            self.register_panel.columnconfigure(column, weight=1, uniform="registers")
        for index in range(8):
            value = tk.StringVar(self.root, f"R{index}  -")
            label = ttk.Label(self.register_panel, textvariable=value, font=self.register_font, style="Panel.TLabel")
            label.grid(row=index // 4, column=index % 4, sticky="w", pady=2)
            self.register_values.append(value)
            self.register_cells.append(label)

        self.register_panel.bind("<Configure>", lambda event: self._layout_registers(event.width))
        self._resize_registers(self.register_zoom.value)

    def _resize_registers(self, zoom):
        self.register_title_font.configure(size=round(12 * zoom / 100))
        self.register_font.configure(size=round(11 * zoom / 100))
        self._layout_registers(self.register_panel.winfo_width())

    def _layout_registers(self, width):
        if width <= 1:
            return
        cell_width = self.register_font.measure("R0  x0000") + 12
        columns = 4 if width >= 4 * cell_width else 2 if width >= 2 * cell_width else 1
        if columns == self.register_columns:
            return
        self.register_columns = columns
        for column in range(4):
            self.register_panel.columnconfigure(
                column, weight=int(column < columns), uniform="registers" if column < columns else ""
            )
        for index, cell in enumerate(self.register_cells):
            cell.grid_configure(row=index // columns, column=index % columns)

    def _build_console(self, console_panel):
        console_panel.columnconfigure(0, weight=1)
        console_panel.rowconfigure(1, weight=1)
        ttk.Label(console_panel, text="Consola del programa", style="Section.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 6)
        )
        self.console = tk.Text(
            console_panel, font=MONO, wrap="word", bg=FIELD, fg=TEXT, relief="flat",
            padx=10, pady=8, state="disabled", height=16, width=38, selectbackground=BORDER,
        )
        self.console.grid(row=1, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(console_panel, orient="vertical", command=self.console.yview)
        scrollbar.grid(row=1, column=1, sticky="ns")
        self.console.configure(yscrollcommand=scrollbar.set)

    def _load(self, image, target, name, *, benchmark=False):
        candidate = Machine(image, target=target, input_data=self.input_data)
        self.pause()
        self.image, self.image_name = image, name
        self.benchmark_loaded = benchmark
        self.format_label.set("Formato del benchmark" if benchmark else "Formato al abrir")
        self.machine = candidate
        self.target.set(target)
        self.fault = ""
        self.memory_base = candidate.origin
        self.follow_pc.set(True)
        self.address.set(f"x{candidate.origin:04X}")
        self.loaded.set(f"{name} · {TARGET_LABELS[target]}")
        self.console.configure(state="normal")
        self.console.delete("1.0", "end")
        self.console.configure(state="disabled")
        self.console_length = 0
        self._refresh()

    def _change_format(self, _event):
        if self.benchmark_loaded:
            self.open_demo()

    def open_demo(self):
        target = self.target.get()
        name = "Benchmark completo original" if target == "lc3" else "Benchmark completo optimizado"
        try:
            self._load(demo_image(target), target, name, benchmark=True)
        except (OSError, ValueError, MachineError) as error:
            if self.benchmark_loaded:
                self.target.set(self.machine.target)
            messagebox.showerror("No se pudo cargar el benchmark", str(error), parent=self.root)

    def _open_path(self, path, target):
        try:
            self._load(path.read_bytes(), target, path.name)
        except (OSError, MachineError) as error:
            messagebox.showerror("No se pudo abrir el binario", str(error), parent=self.root)

    def open_file(self):
        self.pause()
        path = filedialog.askopenfilename(
            parent=self.root, title="Abrir código máquina",
            filetypes=(("Binarios", ("*.bin", "*.obj")), ("Todos los archivos", "*")),
        )
        if path:
            self._open_path(Path(path), self.target.get())

    def reset(self):
        if self.machine is not None:
            self._load(self.image, self.machine.target, self.image_name, benchmark=self.benchmark_loaded)

    def play(self):
        if self.machine is None or self.machine.halted or self.running or self.fault:
            return
        self.running = True
        self._refresh()
        self.job = self.root.after(0, self._tick)

    def pause(self):
        self.running = False
        if self.job is not None:
            self.root.after_cancel(self.job)
            self.job = None
        self._refresh()

    def _advance(self, count):
        machine = self.machine
        try:
            for _ in range(count):
                if machine.halted:
                    self.running = False
                    break
                if machine.steps >= self.max_steps:
                    raise MachineError(f"Límite de {format_count(self.max_steps)} instrucciones.")
                machine.step()
        except MachineError as error:
            self.fault = str(error)
            self.running = False
        if machine.halted:
            self.running = False

    def _tick(self):
        self.job = None
        if self.running:
            count, delay = SPEEDS[self.speed.get()]
            self._advance(count)
            self._refresh()
            if self.running:
                self.job = self.root.after(delay, self._tick)

    def single_step(self):
        if self.machine is not None and not self.running and not self.machine.halted and not self.fault:
            self._advance(1)
            self._refresh()

    def seek(self):
        if self.machine is None:
            return
        try:
            address = memory_address(self.address.get())
        except ValueError as error:
            self.memory_note.set(str(error))
            return

        self.follow_pc.set(False)
        self.memory_base = address
        self._refresh_memory()
        self.memory_table.yview_moveto(0)

    def turn_page(self, direction):
        if self.machine is not None:
            self.follow_pc.set(False)
            self.memory_base += direction * MEMORY_ROWS * self.machine.stride
            self._refresh_memory()
            self.memory_table.yview_moveto(0)

    def _refresh_memory(self):
        machine = self.machine
        if machine is None:
            return
        stride = machine.stride
        page_size = MEMORY_ROWS * stride
        if self.follow_pc.get():
            self.memory_base = machine.pc - machine.pc % page_size
            self.address.set(f"x{machine.pc:04X}")
        limit = 0x10000 - page_size
        self.memory_base = max(0, min(self.memory_base, limit))
        self.memory_base -= self.memory_base % stride
        self.memory_note.set("Direcciones de palabra" if machine.legacy else "Direcciones de byte · palabras alineadas")
        for index in range(MEMORY_ROWS):
            address = self.memory_base + stride * index
            physical = address * 2 if machine.legacy else address
            high, low = machine.memory[physical:physical + 2]
            changed = physical in machine.written_bytes or physical + 1 in machine.written_bytes
            is_pc = address == machine.pc and not machine.halted
            labels = ("PC" if is_pc else "", "Escrita" if changed else "")
            self.memory_table.item(
                f"memory{index}", values=(
                    f"x{address:04X}", f"x{high:02X}{low:02X}", f"{high:02X} {low:02X}", " · ".join(filter(None, labels))
                ), tags=(("pc",) if is_pc else ("write",) if changed else ()),
            )

        if self.follow_pc.get() and not machine.halted:
            self._reveal_memory_pc()

    def _refresh(self):
        machine = self.machine
        enabled = machine is not None and not machine.halted and not self.fault
        self.play_button.configure(state="normal" if enabled and not self.running else "disabled")
        self.step_button.configure(state="normal" if enabled and not self.running else "disabled")
        self.pause_button.configure(state="normal" if self.running else "disabled")
        self.reset_button.configure(state="normal" if machine is not None else "disabled")
        if machine is None:
            self.status.set("Abrí un binario o cargá el benchmark optimizado.")
            return

        self.pc.set(f"PC x{machine.pc:04X}")
        flags = "   ".join(f"{label} {int(bool(machine.cc & bit))}" for label, bit in zip("NZP", (4, 2, 1)))
        self.flags.set(f"{flags}   C {machine.carry}" if not machine.legacy else flags)
        word, mnemonic = instruction_preview(machine)
        self.next_word.set(f"Próxima instrucción {word}")
        self.mnemonic.set(f"Mnemónico {mnemonic}")
        for index, value in enumerate(machine.registers):
            self.register_values[index].set(f"R{index}  x{value:04X}")

        self.metrics["instructions"].set(format_count(machine.steps))
        self.metrics["image"].set(format_count(machine.image_bytes))
        self.metrics["memory"].set(format_count(len(machine.read_bytes | machine.written_bytes)))
        self.metrics["traffic"].set(format_count(machine.data_bytes_read + machine.data_bytes_written))
        self._refresh_memory()

        output = machine.output
        if len(output) > self.console_length:
            self.console.configure(state="normal")
            self.console.insert("end", output[self.console_length:])
            self.console.configure(state="disabled")
            self.console.see("end")
            self.console_length = len(output)

        status = self.fault
        if not status:
            if machine.halted:
                status = "HALT · Ejecución finalizada"
            elif self.running:
                status = "En ejecución"
            elif machine.steps:
                status = "En pausa"
            else:
                status = f"Listo · Origen x{machine.origin:04X} · F5 ejecutar · F10 paso"
        self.status.set(status)
        self.status_label.configure(style="Error.TLabel" if self.fault else "Muted.TLabel")

    def close(self):
        if self.job is not None:
            self.root.after_cancel(self.job)
        self.root.destroy()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path, nargs="?", help="Binario con encabezado de origen.")
    parser.add_argument("--target", choices=TARGETS)
    parser.add_argument("--input-file", type=Path, help="Entrada para GETC e IN.")
    parser.add_argument("--max-steps", type=int, default=10_000_000)
    args = parser.parse_args()
    if args.max_steps < 1:
        parser.error("--max-steps tiene que ser mayor que cero")
    try:
        input_data = args.input_file.read_text(encoding="utf-8") if args.input_file else ""
        root = tk.Tk()
    except (OSError, tk.TclError) as error:
        parser.exit(1, f"No se pudo abrir la interfaz: {error}\n")
    target = args.target or ("lab3c" if args.image else "lab3c-v2")
    SimulatorDemo(root, args.image, target=target, max_steps=args.max_steps, input_data=input_data)
    root.mainloop()


if __name__ == "__main__":
    main()
