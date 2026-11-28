#!/usr/bin/python3
import contextlib
import io
import math
import queue
import re
import tempfile
import time
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from tkinter import font as tkfont

import benchmark_metrics
import real_benchmark
import scientific_closure
from assembler import Assembler, AssemblyError, write_output
from simulator import Simulator, ExecutionError


ROOT = Path(__file__).resolve().parent


def _mix_hex(first, second, factor):
    start = [int(first[i:i + 2], 16) for i in (1, 3, 5)]
    end = [int(second[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02X%02X%02X" % tuple(
        round(a + (b - a) * max(0.0, min(1.0, factor))) for a, b in zip(start, end)
    )


def _rounded_points(x0, y0, x1, y1, radius):
    radius = min(radius, (x1 - x0) / 2, (y1 - y0) / 2)
    points = []
    corners = (
        (x1 - radius, y0 + radius, -90),
        (x1 - radius, y1 - radius, 0),
        (x0 + radius, y1 - radius, 90),
        (x0 + radius, y0 + radius, 180),
    )
    for center_x, center_y, start in corners:
        for step in range(7):
            angle = math.radians(start + step * 15)
            points.extend((
                center_x + radius * math.cos(angle),
                center_y + radius * math.sin(angle),
            ))
    return points


class RoundedButton(tk.Canvas):
    def __init__(self, master, colors, text, command=None, kind="ghost", width=None,
                 height=34, font_size=9, padx=15, radius=10, bg_color=None):
        super().__init__(master, height=height, highlightthickness=0, bd=0,
                         bg=bg_color or colors["surface"], cursor="hand2")
        self.colors = colors
        self.command = command
        self.font = tkfont.Font(family="Segoe UI", size=font_size, weight="bold")
        self.button_width = width or max(76, int(self.font.measure(text)) + padx * 2)
        self.button_height = height
        self.configure(width=self.button_width)

        if kind == "primary":
            self.normal = colors["primary"]
            self.hover = colors["primary_light"]
            self.active = colors["accent_dark"]
            self.foreground = "#FFFFFF"
            self.outline_color = colors["primary_light"]
        elif kind == "segment":
            self.normal = colors["surface2"]
            self.hover = colors["surface3"]
            self.active = colors["border"]
            self.foreground = colors["muted"]
            self.outline_color = colors["border"]
        else:
            self.normal = colors["surface2"]
            self.hover = colors["surface3"]
            self.active = colors["border"]
            self.foreground = colors["text"]
            self.outline_color = colors["border"]

        self.current_color = self.normal
        self.target_color = self.normal
        self.pressed = False
        self.animation = None

        shape = _rounded_points(1, 1, self.button_width - 1, self.button_height - 1, radius)
        self.shape = self.create_polygon(shape, fill=self.current_color,
                                         outline=self.outline_color, width=1)
        self.label = self.create_text(self.button_width / 2, self.button_height / 2,
                                      text=text, fill=self.foreground, font=self.font)

        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<Return>", lambda _event: self.invoke())
        self.bind("<space>", lambda _event: self.invoke())

    def _paint(self):
        self.itemconfigure(self.shape, fill=self.current_color, outline=self.outline_color)
        self.itemconfigure(self.label, fill=self.foreground)

    def _animate(self):
        if self.animation is not None:
            self.after_cancel(self.animation)
        start = self.current_color
        end = self.target_color
        step = [0]

        def tick():
            if not self.winfo_exists():
                return
            step[0] += 1
            progress = min(1.0, step[0] / 7)
            self.current_color = _mix_hex(start, end, progress)
            self._paint()
            if progress < 1.0:
                self.animation = self.after(18, tick)
            else:
                self.animation = None

        tick()

    def set_colors(self, normal, hover, active, foreground=None, outline=None):
        self.normal = normal
        self.hover = hover
        self.active = active
        if foreground:
            self.foreground = foreground
        if outline:
            self.outline_color = outline
        self.current_color = self.active if self.pressed else self.normal
        self.target_color = self.current_color
        self._paint()

    def _on_enter(self, _event):
        self.target_color = self.hover
        self._animate()

    def _on_leave(self, _event):
        if not self.pressed:
            self.target_color = self.normal
            self._animate()

    def _on_press(self, _event):
        self.pressed = True
        self.target_color = self.active
        self.coords(self.label, self.button_width / 2, self.button_height / 2 + 1)
        self._animate()

    def _on_release(self, _event):
        was_pressed = self.pressed
        self.pressed = False
        self.target_color = self.hover
        self.coords(self.label, self.button_width / 2, self.button_height / 2)
        self._animate()
        if was_pressed and self.command:
            self.command()

    def invoke(self):
        if self.command:
            self.command()


class Lab3GUI(tk.Tk):
    KEYWORDS = {
        "ADD", "SUB", "AND", "OR", "XOR", "NOT", "CMP", "MOV", "SHL", "SHR",
        "ASR", "SWAP", "MUL", "MULH", "DIV", "REM", "LOADL", "LOADH", "LOAD",
        "STOREL", "STOREH", "STORE", "BR", "BRN", "BRZ", "BRP", "JSR", "JSRR",
        "JMP", "RET", "TRAP", "NOP", "SIGN", "SE", "TEST", "HALT", "GETC",
        "OUT", "PUTS", "IN", "PUTSP",
    }
    TOKEN_PATTERN = re.compile(
        r";[^\n]*|\"(?:\\.|[^\"\\])*\"|#-?\d+|0[xX][0-9A-Fa-f]+|\b\d+\b|\.[A-Za-z][A-Za-z0-9]*|\b[A-Za-z][A-Za-z0-9]*\b"
    )

    def __init__(self):
        super().__init__()
        self.title("Laboratorio 3 — ISA 16 bits")
        self.geometry("1360x860")
        self.minsize(1020, 700)

        self.colors = {
            "bg": "#070B14", "surface": "#0E1424", "surface2": "#141D31",
            "surface3": "#1D2A44", "border": "#25324B", "text": "#E8EEF9",
            "muted": "#8FA3BF", "accent": "#38BDF8", "accent_dark": "#0891B2",
            "primary": "#6D5EF6", "primary_light": "#8B7CF8", "success": "#34D399",
            "danger": "#FB7185", "warning": "#FBBF24", "editor": "#090F1D",
        }
        self.configure(bg=self.colors["bg"])

        self.source_path = None
        self.image_path = None
        self.current_simulator = None
        self.benchmark_running = False
        self.benchmark_queue = queue.Queue()
        self.benchmark_poll_job = None
        self.format_var = tk.StringVar(value="hex")
        self.busy_depth = 0
        self.status_phase = 0
        self.status_base = "Sistema listo"
        self.status_state = "accent"
        self.highlight_job = None
        self.flash_jobs = {}

        style = ttk.Style(self)
        if "clam" in style.theme_names():
            style.theme_use("clam")
        self._configure_styles(style)

        self._build_progress()
        self._build_toolbar()
        self._build_main()
        self._build_status()

        self.bind("<Control-o>", lambda _event: self.open_source())
        self.bind("<F5>", lambda _event: self.assemble_and_run())

        self.animate_status()
        self.animate_progress()
        self._fade_in()

    def _configure_styles(self, style):
        c = self.colors
        style.configure(".", background=c["bg"], foreground=c["text"],
                        fieldbackground=c["surface2"], bordercolor=c["border"],
                        font=("Segoe UI", 9))
        style.configure("Title.TLabel", background=c["surface"], foreground=c["text"],
                        font=("Segoe UI", 16, "bold"))
        style.configure("Eyebrow.TLabel", background=c["surface"], foreground=c["accent"],
                        font=("Segoe UI", 8, "bold"))
        style.configure("Section.TLabel", background=c["surface"], foreground=c["text"],
                        font=("Segoe UI", 10, "bold"))
        style.configure("Hint.TLabel", background=c["surface"], foreground=c["muted"],
                        font=("Segoe UI", 8))
        style.configure("Field.TLabel", background=c["surface2"], foreground=c["muted"],
                        font=("Segoe UI", 8, "bold"))
        style.configure("Badge.TLabel", background=c["surface2"], foreground=c["muted"],
                        font=("Segoe UI", 8, "bold"), padding=(8, 4))
        style.configure("TFrame", background=c["surface"])
        style.configure("TNotebook", background=c["surface"], borderwidth=0, tabmargins=(0, 0, 0, 0))
        style.configure("TNotebook.Tab", background=c["surface"], foreground=c["muted"],
                        padding=(18, 10), font=("Segoe UI", 9, "bold"), borderwidth=0)
        style.map("TNotebook.Tab",
                  background=[("selected", c["surface2"]), ("active", c["surface3"])],
                  foreground=[("selected", c["accent"]), ("active", c["text"])])
        style.configure("TEntry", fieldbackground=c["editor"], foreground=c["text"],
                        insertcolor=c["accent"], bordercolor=c["border"], padding=(8, 6))
        style.configure("TRadiobutton", background=c["surface2"], foreground=c["muted"],
                        font=("Segoe UI", 8, "bold"))
        style.map("TRadiobutton", foreground=[("selected", c["accent"])],
                  background=[("selected", c["surface2"])])
        style.configure("Treeview", background=c["editor"], foreground=c["text"],
                        fieldbackground=c["editor"], borderwidth=0, rowheight=30,
                        font=("JetBrains Mono", 9))
        style.configure("Treeview.Heading", background=c["surface2"], foreground=c["accent"],
                        borderwidth=0, padding=(8, 7), font=("Segoe UI", 8, "bold"))
        style.map("Treeview", background=[("selected", "#1E3A5F")],
                  foreground=[("selected", "#FFFFFF")])
        style.configure("TScrollbar", background=c["surface3"], troughcolor=c["editor"],
                        arrowcolor=c["muted"], borderwidth=0, arrowsize=11)
        style.map("TScrollbar", background=[("active", c["border"])])
        for name, color_key in (("Idle", "accent"), ("Working", "warning"),
                                ("Success", "success"), ("Error", "danger")):
            style.configure("Status%s.TLabel" % name, background=c["surface"],
                            foreground=c[color_key], font=("Segoe UI", 9, "bold"))

    def _fade_in(self):
        try:
            self.attributes("-alpha", 0.0)
        except tk.TclError:
            return

        def step(value):
            if not self.winfo_exists():
                return
            self.attributes("-alpha", value)
            if value < 1.0:
                self.after(20, lambda: step(min(1.0, value + 0.09)))

        step(0.0)

    def _build_progress(self):
        c = self.colors
        self.progress = tk.Canvas(self, height=3, bg=c["bg"], highlightthickness=0, bd=0)
        self.progress.pack(fill="x", side="top")
        self.progress_active = False
        self.progress_step = 0

    def animate_progress(self):
        if not self.winfo_exists():
            return
        c = self.colors
        self.progress.delete("all")
        if self.progress_active:
            width = max(self.progress.winfo_width(), 1)
            offset = (self.progress_step * 14) % (width + 220) - 110
            self.progress.create_rectangle(offset, 0, offset + 140, 3, fill=c["accent"], outline="")
            self.progress.create_rectangle(offset + 140, 0, offset + 210, 3,
                                           fill=c["primary"], outline="")
            self.progress_step += 1
        self.after(35, self.animate_progress)

    def start_busy(self, message=None):
        self.busy_depth += 1
        self.progress_active = True
        if message:
            self.set_status(message, "working")

    def stop_busy(self):
        self.busy_depth = max(0, self.busy_depth - 1)
        if self.busy_depth == 0:
            self.progress_active = False

    def animate_status(self):
        if not self.winfo_exists():
            return
        c = self.colors
        if hasattr(self, "status_dot") and self.status_dot.winfo_exists():
            self.status_phase += 0.11
            dot_color = self.colors.get(self.status_state, c["accent"])
            self.status_dot.delete("all")
            self.status_dot.create_oval(2, 2, 16, 16,
                                        fill=_mix_hex(c["surface"], dot_color, 0.10), outline="")
            self.status_dot.create_oval(4, 4, 14, 14,
                                        fill=_mix_hex(c["surface"], dot_color, 0.28), outline="")
            radius = 4.2 + 0.9 * math.sin(self.status_phase)
            self.status_dot.create_oval(9 - radius, 9 - radius, 9 + radius, 9 + radius,
                                        fill=dot_color, outline="")
        self.after(60, self.animate_status)

    def set_status(self, text, state="idle"):
        self.status_base = text
        state_colors = {"idle": "accent", "working": "warning",
                        "success": "success", "error": "danger"}
        self.status_state = state_colors.get(state, "accent")
        if hasattr(self, "status") and self.status.winfo_exists():
            self.status.configure(text=text, style="Status%s.TLabel" % state.title())

    def _create_action_button(self, parent, text, command, primary=False):
        return RoundedButton(parent, self.colors, text, command,
                             kind="primary" if primary else "ghost",
                             bg_color=self.colors["surface"])

    def _bind_card_focus(self, card, widget):
        normal = self.colors["border"]
        widget.bind("<FocusIn>", lambda _event: card.configure(highlightbackground=self.colors["accent"]))
        widget.bind("<FocusOut>", lambda _event: card.configure(highlightbackground=normal))

    def _build_toolbar(self):
        c = self.colors
        toolbar = tk.Frame(self, bg=c["surface"], highlightthickness=1,
                           highlightbackground=c["border"], padx=16, pady=11)
        toolbar.pack(fill="x", padx=10, pady=(8, 6))

        brand = tk.Canvas(toolbar, width=44, height=44, bg=c["surface"],
                          highlightthickness=0, bd=0)
        brand.pack(side="left", padx=(0, 12))
        brand.create_polygon(_rounded_points(2, 2, 42, 42, 12),
                             fill=c["primary"], outline=c["primary_light"])
        brand.create_line(12, 35, 32, 35, fill=c["accent"], width=2)
        brand.create_text(22, 21, text="L3", fill="#FFFFFF",
                          font=("Segoe UI", 13, "bold"))

        titles = tk.Frame(toolbar, bg=c["surface"])
        titles.pack(side="left")
        ttk.Label(titles, text="LABORATORIO 3", style="Eyebrow.TLabel").pack(anchor="w")
        ttk.Label(titles, text="Ensamblador y simulador ISA", style="Title.TLabel").pack(anchor="w")

        separator = tk.Frame(toolbar, bg=c["border"], width=1)
        separator.pack(side="left", fill="y", padx=16, pady=4)

        self._create_action_button(toolbar, "Abrir", self.open_source).pack(side="left", padx=3)
        self._create_action_button(toolbar, "Guardar", self.save_source).pack(side="left", padx=3)
        self._create_action_button(toolbar, "Ensamblar", self.assemble).pack(side="left", padx=3)
        self._create_action_button(toolbar, "Ejecutar", self.assemble_and_run,
                                   primary=True).pack(side="left", padx=(8, 4))

        input_card = tk.Frame(toolbar, bg=c["surface2"], padx=10, pady=5,
                              highlightthickness=1, highlightbackground=c["border"])
        input_card.pack(side="left", padx=(14, 4))
        ttk.Label(input_card, text="ENTRADA", style="Field.TLabel").pack(side="left", padx=(0, 8))
        self.input_var = tk.StringVar(value="")
        input_entry = ttk.Entry(input_card, textvariable=self.input_var, width=10)
        input_entry.pack(side="left")
        self._bind_card_focus(input_card, input_entry)

        format_card = tk.Frame(toolbar, bg=c["surface2"], padx=10, pady=5,
                               highlightthickness=1, highlightbackground=c["border"])
        format_card.pack(side="right")
        ttk.Label(format_card, text="FORMATO", style="Field.TLabel").pack(side="left", padx=(0, 8))
        segment = tk.Frame(format_card, bg=c["surface2"])
        segment.pack(side="left")
        self.format_buttons = {}
        for value, label in (("hex", "HEX"), ("bin", "BIN")):
            button = RoundedButton(segment, c, label,
                                   command=lambda selected=value: self.set_format(selected),
                                   kind="segment", width=50, height=26, font_size=8,
                                   radius=8, bg_color=c["surface2"])
            button.pack(side="left", padx=2)
            self.format_buttons[value] = button
        self.set_format("hex")

    def set_format(self, value):
        c = self.colors
        self.format_var.set(value)
        for key, button in self.format_buttons.items():
            if key == value:
                button.set_colors(c["primary"], c["primary_light"], c["accent_dark"],
                                  "#FFFFFF", c["primary_light"])
            else:
                button.set_colors(c["surface2"], c["surface3"], c["border"],
                                  c["muted"], c["border"])

    def _build_main(self):
        c = self.colors
        paned = ttk.Panedwindow(self, orient="horizontal")
        paned.pack(fill="both", expand=True, padx=10, pady=(0, 6))

        left = tk.Frame(paned, bg=c["surface"], highlightthickness=1,
                        highlightbackground=c["border"])
        right = tk.Frame(paned, bg=c["surface"], highlightthickness=1,
                         highlightbackground=c["border"])
        paned.add(left, weight=3)
        paned.add(right, weight=2)

        self._build_editor(left)
        self._build_output(right)

    def _build_editor(self, left):
        c = self.colors
        header = tk.Frame(left, bg=c["surface"], padx=12, pady=10)
        header.pack(fill="x")
        heading = tk.Frame(header, bg=c["surface"])
        heading.pack(side="left")
        ttk.Label(heading, text="CÓDIGO FUENTE", style="Section.TLabel").pack(anchor="w")
        self.cursor_label = ttk.Label(heading, text="Ln 1 · Col 1", style="Hint.TLabel")
        self.cursor_label.pack(anchor="w")
        self.source_label = ttk.Label(header, text="Sin archivo", style="Badge.TLabel")
        self.source_label.pack(side="right")

        editor_frame = tk.Frame(left, bg=c["editor"], highlightthickness=1,
                                highlightbackground=c["border"])
        editor_frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.editor_frame = editor_frame

        self.gutter = tk.Canvas(editor_frame, width=52, bg=c["editor"],
                                highlightthickness=0, bd=0)
        self.gutter.pack(side="left", fill="y")
        self.editor_scroll = ttk.Scrollbar(editor_frame, orient="vertical")
        self.editor_scroll.pack(side="right", fill="y")

        self.source_text = tk.Text(
            editor_frame, wrap="none", undo=True, yscrollcommand=self._on_editor_scroll,
            font=("JetBrains Mono", 11), bg=c["editor"], fg=c["text"],
            insertbackground=c["accent"], selectbackground="#1E3A5F",
            selectforeground="#FFFFFF", highlightthickness=0,
            padx=14, pady=12, spacing1=2, spacing3=2,
        )
        self.source_text.pack(side="left", fill="both", expand=True)
        self.editor_scroll.configure(command=self.source_text.yview)

        self.source_text.tag_configure("currentline", background="#111C30")
        for tag, color in (
            ("tok_comment", "#5C6F8A"), ("tok_string", "#FDBA74"),
            ("tok_number", "#FBBF24"), ("tok_directive", "#38BDF8"),
            ("tok_keyword", "#C084FC"), ("tok_register", "#7DD3FC"),
            ("tok_label", "#34D399"),
        ):
            self.source_text.tag_configure(tag, foreground=color)

        self.source_text.bind("<KeyRelease>", self._on_source_change)
        self.source_text.bind("<ButtonRelease-1>", self._on_source_change)
        self.source_text.bind("<MouseWheel>", lambda _event: self.after(18, self._draw_gutter))
        self.gutter.bind("<MouseWheel>", self._scroll_gutter)
        self.gutter.bind("<Button-4>", lambda _event: self._scroll_units(-1))
        self.gutter.bind("<Button-5>", lambda _event: self._scroll_units(1))

    def _on_editor_scroll(self, first, last):
        self.editor_scroll.set(first, last)
        self._draw_gutter()

    def _scroll_gutter(self, event):
        self._scroll_units(-1 if event.delta > 0 else 1)
        return "break"

    def _scroll_units(self, direction):
        self.source_text.yview_scroll(direction, "units")
        self.after(18, self._draw_gutter)

    def _on_source_change(self, _event=None):
        self._update_cursor_label()
        self._draw_gutter()
        self._schedule_highlight()

    def _update_cursor_label(self):
        line, column = self.source_text.index("insert").split(".")
        self.cursor_label.configure(text="Ln %s · Col %d" % (line, int(column) + 1))

    def _draw_gutter(self):
        if not hasattr(self, "gutter") or not self.gutter.winfo_exists():
            return
        self.gutter.delete("all")
        try:
            total = int(self.source_text.index("end-1c").split(".")[0])
            current = int(self.source_text.index("insert").split(".")[0])
            height = self.gutter.winfo_height()
            mono = tkfont.Font(font=("JetBrains Mono", 9))
            for number in range(1, total + 1):
                info = self.source_text.dlineinfo("%d.0" % number)
                if info is None or info[1] > height or info[1] + info[3] < 0:
                    continue
                top = info[1]
                middle = top + info[3] / 2
                if number == current:
                    self.gutter.create_rectangle(0, top, 52, top + info[3],
                                                 fill=self.colors["surface2"], outline="")
                    self.gutter.create_polygon((52, top + 3, 52, top + info[3] - 3,
                                                46, middle), fill=self.colors["accent"])
                self.gutter.create_text(
                    42, middle, text=str(number), anchor="e", font=mono,
                    fill=self.colors["accent"] if number == current else self.colors["muted"],
                )
        except (tk.TclError, ValueError):
            pass

    def _schedule_highlight(self):
        if self.highlight_job is not None:
            self.after_cancel(self.highlight_job)
        self.highlight_job = self.after(90, self._highlight_source)

    def _highlight_source(self):
        self.highlight_job = None
        if not self.source_text.winfo_exists():
            return
        tags = ("tok_comment", "tok_string", "tok_number", "tok_directive",
                "tok_keyword", "tok_register", "tok_label")
        for tag in tags:
            self.source_text.tag_remove(tag, "1.0", "end")

        lines = self.source_text.get("1.0", "end-1c").split("\n")
        for number, line in enumerate(lines, 1):
            stripped = line.lstrip()
            first_token = len(line) - len(stripped)
            for match in self.TOKEN_PATTERN.finditer(line):
                token = match.group(0)
                upper = token.upper()
                if token.startswith(";"):
                    tag = "tok_comment"
                elif token.startswith('"'):
                    tag = "tok_string"
                elif token.startswith("#") or token.startswith("0x") or token.isdigit():
                    tag = "tok_number"
                elif token.startswith("."):
                    tag = "tok_directive"
                elif re.fullmatch(r"R[0-7]", upper):
                    tag = "tok_register"
                elif upper in self.KEYWORDS:
                    tag = "tok_keyword"
                elif match.start() == first_token:
                    tag = "tok_label"
                else:
                    continue
                self.source_text.tag_add(tag, "%d.%d" % (number, match.start()),
                                         "%d.%d" % (number, match.end()))

        self.source_text.tag_remove("currentline", "1.0", "end")
        line_number = int(self.source_text.index("insert").split(".")[0])
        self.source_text.tag_add("currentline", "%d.0" % line_number, "%d.end" % line_number)
        self._draw_gutter()

    def _build_output(self, right):
        c = self.colors
        tabs = ttk.Notebook(right)
        tabs.pack(fill="both", expand=True, padx=8, pady=8)

        console_frame = tk.Frame(tabs, bg=c["surface"])
        result_frame = tk.Frame(tabs, bg=c["surface"])
        memory_frame = tk.Frame(tabs, bg=c["surface"])
        benchmark_frame = tk.Frame(tabs, bg=c["surface"])
        report_frame = tk.Frame(tabs, bg=c["surface"])
        tabs.add(console_frame, text="  CONSOLA  ")
        tabs.add(result_frame, text="  REGISTROS  ")
        tabs.add(memory_frame, text="  MEMORIA  ")
        tabs.add(benchmark_frame, text="  BENCHMARKS  ")
        tabs.add(report_frame, text="  REPORTES  ")

        console_head = tk.Frame(console_frame, bg=c["surface"], padx=8, pady=7)
        console_head.pack(fill="x")
        ttk.Label(console_head, text="Salida del sistema", style="Section.TLabel").pack(side="left")
        ttk.Label(console_head, text="EN VIVO", style="Badge.TLabel").pack(side="right")

        console_border = tk.Frame(console_frame, bg=c["editor"], highlightthickness=1,
                                  highlightbackground=c["border"])
        console_border.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.console_border = console_border
        self.console = tk.Text(
            console_border, wrap="word", state="disabled", font=("JetBrains Mono", 9),
            bg=c["editor"], fg="#A7F3D0", insertbackground=c["accent"],
            selectbackground="#1E3A5F", highlightthickness=0, padx=12, pady=10,
        )
        self.console.pack(fill="both", expand=True)
        for tag, color in (("error", c["danger"]), ("success", c["success"]),
                           ("info", c["accent"]), ("output", "#C7D2FE")):
            self.console.tag_configure(tag, foreground=color)

        self._build_registers(result_frame)
        self._build_memory(memory_frame)
        self._build_benchmarks(benchmark_frame)
        self._build_reports(report_frame)

    def _build_registers(self, parent):
        c = self.colors
        head = tk.Frame(parent, bg=c["surface"], padx=8, pady=8)
        head.pack(fill="x")
        ttk.Label(head, text="BANCO DE REGISTROS", style="Section.TLabel").pack(side="left")
        ttk.Label(head, text="Decimal o 0x hexadecimal", style="Hint.TLabel").pack(side="right")

        register_frame = tk.Frame(parent, bg=c["surface"])
        register_frame.pack(fill="x", padx=8, pady=4)
        self.register_entries = {}
        self.register_cards = {}
        for index in range(8):
            cell = tk.Frame(register_frame, bg=c["surface2"], padx=8, pady=7,
                            highlightthickness=1, highlightbackground=c["border"])
            cell.grid(row=index // 4, column=index % 4, padx=4, pady=4, sticky="ew")
            tk.Label(cell, text="R%d" % index, bg=c["surface2"], fg=c["accent"],
                     font=("Segoe UI", 9, "bold")).pack(side="left")
            entry = ttk.Entry(cell, width=8, justify="center",
                              font=("JetBrains Mono", 10))
            entry.insert(0, "0")
            entry.pack(side="right")
            self.register_entries[index] = entry
            self.register_cards[index] = cell
            self._bind_card_focus(cell, entry)
        for column in range(4):
            register_frame.columnconfigure(column, weight=1)

        ttk.Label(parent, text="Estado de ejecución", style="Section.TLabel").pack(
            anchor="w", padx=8, pady=(12, 5))
        self.metrics = ttk.Treeview(parent, columns=("valor",), show="headings", height=11)
        self.metrics.heading("#0", text="ELEMENTO")
        self.metrics.heading("valor", text="VALOR")
        self.metrics.column("#0", width=170, anchor="w")
        self.metrics.column("valor", width=170, anchor="e")
        self.metrics.tag_configure("oddrow", background=c["surface2"])
        self.metrics.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    def _build_memory(self, parent):
        c = self.colors
        header = tk.Frame(parent, bg=c["surface"], padx=8, pady=8)
        header.pack(fill="x")
        ttk.Label(header, text="DIRECCIÓN", style="Section.TLabel").pack(side="left")
        address_card = tk.Frame(header, bg=c["surface2"], padx=6, pady=3,
                                highlightthickness=1, highlightbackground=c["border"])
        address_card.pack(side="left", padx=8)
        self.memory_address = ttk.Entry(address_card, width=10, justify="center",
                                        font=("JetBrains Mono", 10))
        self.memory_address.insert(0, "4000")
        self.memory_address.pack(side="left")
        self._bind_card_focus(address_card, self.memory_address)
        self._create_action_button(header, "Mostrar", self.show_memory).pack(side="left")

        memory_border = tk.Frame(parent, bg=c["editor"], highlightthickness=1,
                                 highlightbackground=c["border"])
        memory_border.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.memory_border = memory_border
        self.memory_text = tk.Text(
            memory_border, wrap="none", state="disabled", font=("JetBrains Mono", 9),
            bg=c["editor"], fg="#C7D2FE", insertbackground=c["accent"],
            selectbackground="#1E3A5F", highlightthickness=0, padx=12, pady=10,
        )
        self.memory_text.pack(fill="both", expand=True)
        self.memory_text.tag_configure("addr", foreground=c["accent"])
        self.memory_text.tag_configure("ascii", foreground=c["muted"])

    def _create_tree(self, parent, columns, headings, widths):
        c = self.colors
        frame = tk.Frame(parent, bg=c["surface"])
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        tree = ttk.Treeview(frame, columns=columns, show="headings", height=12)
        for key, heading, width in zip(columns, headings, widths):
            tree.heading(key, text=heading)
            tree.column(key, width=width, anchor="center")
        tree.tag_configure("pass", foreground=c["success"])
        tree.tag_configure("fail", foreground=c["danger"])
        vertical = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        horizontal = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        tree.grid(row=0, column=0, sticky="nsew")
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal.grid(row=1, column=0, sticky="ew")
        return tree

    def _build_benchmarks(self, parent):
        c = self.colors
        header = tk.Frame(parent, bg=c["surface"], padx=8, pady=8)
        header.pack(fill="x")
        ttk.Label(header, text="BENCHMARKS REALES Y MIGRADOS",
                  style="Section.TLabel").pack(side="left")
        actions = tk.Frame(header, bg=c["surface"])
        actions.pack(side="right")
        self._create_action_button(actions, "Reales 31", self.run_real_benchmarks,
                                   primary=True).pack(side="left", padx=3)
        self._create_action_button(actions, "Migrados 7",
                                   self.run_migrated_benchmarks).pack(side="left", padx=3)
        self._create_action_button(actions, "Cierre", self.run_scientific_closure).pack(
            side="left", padx=3)

        self.benchmark_summary = ttk.Label(
            parent, text="Sin ejecutar", style="Hint.TLabel", wraplength=520,
            justify="left")
        self.benchmark_summary.pack(fill="x", padx=8, pady=(0, 6))

        self.benchmark_tabs = ttk.Notebook(parent)
        self.benchmark_tabs.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        real_page = tk.Frame(self.benchmark_tabs, bg=c["surface"])
        migrated_page = tk.Frame(self.benchmark_tabs, bg=c["surface"])
        self.benchmark_tabs.add(real_page, text="REALES (31)")
        self.benchmark_tabs.add(migrated_page, text="MIGRADOS (7)")

        real_columns = ("num", "interface", "format", "input", "expected", "actual",
                        "instructions", "image", "data", "peak", "error", "state")
        real_headings = ("#", "Interfaz", "Formato", "Entrada", "Esperado", "Ejecutado",
                         "Instr", "Img", "Datos", "Pico", "Error", "Estado")
        real_widths = (36, 165, 90, 70, 70, 70, 60, 55, 55, 60, 55, 65)
        self.real_tree = self._create_tree(real_page, real_columns, real_headings,
                                           real_widths)

        migrated_columns = ("benchmark", "instructions", "image", "memory", "peak",
                            "pc", "error", "state")
        migrated_headings = ("Benchmark", "Instr", "Imagen", "Observada", "Pico",
                             "PC", "Error", "Estado")
        migrated_widths = (180, 60, 70, 80, 60, 70, 60, 65)
        self.migrated_tree = self._create_tree(migrated_page, migrated_columns,
                                               migrated_headings, migrated_widths)

    def _build_reports(self, parent):
        c = self.colors
        header = tk.Frame(parent, bg=c["surface"], padx=8, pady=8)
        header.pack(fill="x")
        self.report_label = ttk.Label(header, text="Sin reporte", style="Section.TLabel")
        self.report_label.pack(side="left")
        self.optimization_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(header, text="Comparar optimización",
                        variable=self.optimization_var,
                        command=self._toggle_optimization_report).pack(side="right", padx=6)
        self._create_action_button(header, "Cargar .md", self.load_report).pack(
            side="right", padx=3)
        self._create_action_button(header, "Regenerar todo", self.regenerate_reports,
                                   primary=True).pack(side="right", padx=3)

        report_border = tk.Frame(parent, bg=c["editor"], highlightthickness=1,
                                 highlightbackground=c["border"])
        report_border.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.report_border = report_border
        self.report_text = tk.Text(
            report_border, wrap="word", state="disabled", font=("JetBrains Mono", 9),
            bg=c["editor"], fg="#C7D2FE", insertbackground=c["accent"],
            selectbackground="#1E3A5F", highlightthickness=0, padx=12, pady=10,
        )
        self.report_text.pack(fill="both", expand=True)
        for tag, color in (("heading", c["accent"]), ("pass", c["success"]),
                           ("fail", c["danger"]), ("muted", c["muted"])):
            self.report_text.tag_configure(tag, foreground=color)

        for name in ("SCIENTIFIC_CLOSURE.md", "REAL_BENCHMARK.md", "BENCHMARK_METRICS.md"):
            path = ROOT / name
            if path.exists():
                self._set_report_text(path.read_text(encoding="utf-8"), name)
                break

    def _toggle_optimization_report(self):
        if self.optimization_var.get():
            path = ROOT / "ISA_OPTIMIZATION.md"
            if path.exists():
                self._set_report_text(path.read_text(encoding="utf-8"), path.name)
                return
        for name in ("SCIENTIFIC_CLOSURE.md", "REAL_BENCHMARK.md", "BENCHMARK_METRICS.md"):
            path = ROOT / name
            if path.exists():
                self._set_report_text(path.read_text(encoding="utf-8"), name)
                return

    def _set_report_text(self, text, title):
        self.report_text.configure(state="normal")
        self.report_text.delete("1.0", "end")
        self.report_text.insert("1.0", text)
        for number, line in enumerate(text.splitlines(), 1):
            if line.startswith("#"):
                tag = "heading"
            elif "FAIL" in line:
                tag = "fail"
            elif line.startswith("|") or line.startswith("- "):
                tag = "muted"
            else:
                continue
            self.report_text.tag_add(tag, "%d.0" % number, "%d.end" % number)
        self.report_text.see("1.0")
        self.report_text.configure(state="disabled")
        self.report_label.configure(text=title)
        self._flash_border(self.report_border)

    def _build_status(self):
        c = self.colors
        status = tk.Frame(self, bg=c["surface"], highlightthickness=1,
                          highlightbackground=c["border"], padx=12, pady=7)
        status.pack(fill="x", padx=10, pady=(0, 10))

        self.status_dot = tk.Canvas(status, width=18, height=18, bg=c["surface"],
                                    highlightthickness=0, bd=0)
        self.status_dot.pack(side="left", padx=(0, 8))
        self.status = ttk.Label(status, text="Sistema listo", style="StatusIdle.TLabel")
        self.status.pack(side="left")

        right = tk.Frame(status, bg=c["surface"])
        right.pack(side="right")
        ttk.Label(right, text="ISA 16-BIT", style="Badge.TLabel").pack(side="left", padx=(0, 10))
        ttk.Label(right, text="Ctrl+O  Abrir   ·   F5  Ejecutar",
                  style="Hint.TLabel").pack(side="left")

    def _flash_border(self, widget):
        key = str(widget)
        if key in self.flash_jobs:
            self.after_cancel(self.flash_jobs.pop(key))
        steps = [0, 1, 2, 3, 4, 5]

        def tick():
            if not steps or not widget.winfo_exists():
                self.flash_jobs.pop(key, None)
                return
            index = steps.pop(0)
            color = _mix_hex(self.colors["border"], self.colors["accent"],
                             max(0.0, 1.0 - index / 5))
            widget.configure(highlightbackground=color)
            if steps:
                self.flash_jobs[key] = self.after(45, tick)
            else:
                self.flash_jobs.pop(key, None)

        tick()

    def _flash_cards(self):
        c = self.colors
        for index, card in self.register_cards.items():
            def animate(target, delay=index * 35):
                if not card.winfo_exists():
                    return
                target.configure(highlightbackground=c["accent"])
                self.after(160 + delay,
                           lambda: target.winfo_exists() and target.configure(
                               highlightbackground=c["border"]))
            animate(card)

    def append_console(self, text, tag=None):
        self.console.configure(state="normal")
        self.console.insert("end", text + "\n", tag)
        self.console.see("end")
        self.console.configure(state="disabled")
        self._flash_border(self.console_border)

    def clear_console(self):
        self.console.configure(state="normal")
        self.console.delete("1.0", "end")
        self.console.configure(state="disabled")

    def open_source(self):
        path = filedialog.askopenfilename(filetypes=[("Assembly", "*.asm"), ("Todos", "*")])
        if not path:
            return
        self.source_path = Path(path)
        self.source_text.delete("1.0", "end")
        self.source_text.insert("1.0", self.source_path.read_text(encoding="utf-8-sig"))
        self.source_label.configure(text=self.source_path.name)
        self.source_text.mark_set("insert", "1.0")
        self._on_source_change()
        self._flash_border(self.editor_frame)
        self.set_status("Abierto: %s" % self.source_path.name, "success")

    def save_source(self):
        if self.source_path:
            path = self.source_path
        else:
            path = filedialog.asksaveasfilename(defaultextension=".asm",
                                                filetypes=[("Assembly", "*.asm")])
            if not path:
                return
            path = Path(path)
        path.write_text(self.source_text.get("1.0", "end-1c"), encoding="utf-8")
        self.source_path = path
        self.source_label.configure(text=path.name)
        self.set_status("Guardado: %s" % path.name, "success")

    def assemble(self):
        self.save_source()
        if not self.source_path:
            return None
        self.start_busy("Ensamblando…")
        try:
            self.clear_console()
            assembler = Assembler()
            memory = assembler.assemble([self.source_path])
            if not assembler.origins:
                raise AssemblyError("no se encontró .ORIG")
            origin = assembler.origins[0]
            output = self.source_path.with_suffix("." + self.format_var.get())
            write_output(output, memory, origin, self.format_var.get())
            self.image_path = output
            self.append_console("Ensamblado correctamente: %s" % output.name, "success")
            self.append_console("Origen: 0x%04X" % origin, "info")
            self.append_console("Código y datos: %d bytes" % len(memory))
            for address, path, line in assembler.paddings:
                self.append_console("Alineación: padding en 0x%04X (%s:%d)" %
                                    (address, path.name, line), "info")
            self.set_status("Ensamblado correctamente", "success")
            return assembler, memory, origin
        except (AssemblyError, OSError) as exc:
            self.append_console("Error de ensamblado: %s" % exc, "error")
            self.set_status("Error de ensamblado", "error")
            messagebox.showerror("Error de ensamblado", str(exc))
            return None
        finally:
            self.stop_busy()

    def assemble_and_run(self):
        self.start_busy("Ejecutando…")
        try:
            assembled = self.assemble()
            if assembled is None:
                return
            assembler, memory, origin = assembled
            self.set_status("Ejecutando…", "working")
            input_text = self.input_var.get().strip()
            simulator = Simulator(batch=True, input_chars=list(input_text) if input_text else [])
            simulator.load_memory(memory, origin)

            for index, entry in self.register_entries.items():
                try:
                    value = self.parse_register_value(entry.get())
                    simulator.registers[index] = value
                except ValueError as exc:
                    messagebox.showerror("Error de valor de registro", "Registro R%d: %s" % (index, exc))
                    return

            self.current_simulator = simulator
            program_output = io.StringIO()
            with contextlib.redirect_stdout(program_output):
                simulator.execute(1000000)

            captured = program_output.getvalue()
            if captured:
                self.append_console(captured.rstrip("\n"), "output")

            data_bytes = len(simulator.written -
                             set(range(origin, origin + simulator.image_bytes)))
            flags = "".join(key for key, enabled in simulator.flags.items() if enabled) or "-"
            self.append_console("HALT" if simulator.halted else "STOP", "success")
            self.append_console("PC final: 0x%04X" % simulator.pc, "info")
            self.append_console("Instrucciones dinámicas: %d" % simulator.instructions, "info")
            self.append_console("Memoria observada: %d bytes" % len(simulator.occupied), "info")
            self.append_console("Pico de memoria: %d bytes" % simulator.peak_occupied, "info")
            self.append_console("Bytes de imagen: %d" % simulator.image_bytes, "info")
            self.append_console("Bytes de código: %d" % simulator.code_bytes, "info")
            self.append_console("Bytes de datos: %d" % data_bytes, "info")

            for item in self.metrics.get_children():
                self.metrics.delete(item)
            rows = [
                ("Estado", "HALT" if simulator.halted else "STOP"),
                ("PC", "0x%04X" % simulator.pc),
                ("Instrucciones", str(simulator.instructions)),
                ("Memoria", "%d bytes" % len(simulator.occupied)),
                ("Pico memoria", "%d bytes" % simulator.peak_occupied),
                ("Bytes imagen", "%d bytes" % simulator.image_bytes),
                ("Bytes código", "%d bytes" % simulator.code_bytes),
                ("Bytes datos", "%d bytes" % data_bytes),
                ("Flags", flags),
                ("Origen", "0x%04X" % origin),
            ]
            for index, value in enumerate(simulator.registers):
                rows.append(("R%d" % index, "0x%04X" % value))
                self.register_entries[index].delete(0, "end")
                self.register_entries[index].insert(0, "0x%04X" % value)
            for position, (label, value) in enumerate(rows):
                self.metrics.insert("", "end", text=label, values=(value,),
                                    tags=("oddrow",) if position % 2 else ())
            self._flash_cards()
            self.set_status("Ejecución completada", "success")
        except ExecutionError as exc:
            self.append_console("Error de ejecución: %s" % exc, "error")
            self.set_status("Error de ejecución", "error")
            messagebox.showerror("Error de simulación", str(exc))
        finally:
            self.stop_busy()

    def parse_register_value(self, text):
        text = text.strip()
        if not text:
            return 0
        value = int(text, 16) if text.lower().startswith("0x") else int(text, 10)
        if value < -32768 or value > 65535:
            raise ValueError("valor fuera de rango de 16 bits")
        return value & 0xffff

    def show_memory(self):
        try:
            address = int(self.memory_address.get(), 16)
        except ValueError:
            messagebox.showerror("Dirección inválida", "Ingrese una dirección hexadecimal de 4 dígitos.")
            return
        if not hasattr(self, "current_simulator"):
            messagebox.showinfo("Memoria", "Primero ensamble y ejecute un programa.")
            return
        if address < 0 or address > 65535:
            messagebox.showerror("Dirección inválida", "La dirección debe estar entre 0000 y FFFF.")
            return
        lines = []
        start = address & 0xFFF0
        simulator = self.current_simulator
        for row in range(start, min(65536, start + 128), 16):
            values = " ".join("%02X" % simulator.memory[row + offset]
                              for offset in range(16) if row + offset < 65536)
            ascii_values = "".join(
                chr(simulator.memory[row + offset])
                if 32 <= simulator.memory[row + offset] <= 126 else "."
                for offset in range(16) if row + offset < 65536
            )
            lines.append("0x%04X  %-47s  |%s|" % (row, values, ascii_values))
        self.memory_text.configure(state="normal")
        self.memory_text.delete("1.0", "end")
        self.memory_text.insert("1.0", "\n".join(lines))
        for number, line in enumerate(lines, 1):
            self.memory_text.tag_add("addr", "%d.0" % number, "%d.6" % number)
            pipe = line.find("|")
            if pipe >= 0:
                self.memory_text.tag_add("ascii", "%d.%d" % (number, pipe),
                                         "%d.%d" % (number, len(line)))
        self.memory_text.configure(state="disabled")
        self._flash_border(self.memory_border)
        self.set_status("Memoria actualizada en 0x%04X" % start, "success")

    def _begin_benchmark(self, message):
        if self.benchmark_running:
            messagebox.showinfo("Benchmark", "Ya hay una ejecución en curso.")
            return False
        self.benchmark_running = True
        self.start_busy(message)
        self.benchmark_summary.configure(text=message)
        if self.benchmark_poll_job is None:
            self.benchmark_poll_job = self.after(80, self._poll_benchmark_queue)
        return True

    def _end_benchmark(self):
        self.benchmark_running = False
        self.stop_busy()

    def _poll_benchmark_queue(self):
        try:
            callback, payload, error = self.benchmark_queue.get_nowait()
        except queue.Empty:
            pass
        else:
            if self.winfo_exists():
                try:
                    callback(payload, error)
                except Exception as exc:
                    self._end_benchmark()
                    self.set_status("Error al actualizar benchmark", "error")
                    messagebox.showerror("Benchmark", str(exc))
        if self.benchmark_running or not self.benchmark_queue.empty():
            self.benchmark_poll_job = self.after(80, self._poll_benchmark_queue)
        else:
            self.benchmark_poll_job = None

    def _failed_real_row(self, case, exc):
        name, qformat, _routine, input_word, reference = case
        try:
            expected = reference(input_word) & 0xffff
        except Exception:
            expected = 0
        return {
            "name": name,
            "format": qformat,
            "input": input_word,
            "expected": expected,
            "actual": 0,
            "absolute_error": max(1, expected),
            "instructions": 0,
            "halted": False,
            "pc": 0,
            "image_bytes": 0,
            "code_bytes": 0,
            "data_bytes": 0,
            "memory_observed": 0,
            "peak_memory": 0,
            "error": str(exc),
        }

    def run_real_benchmarks(self):
        if not self._begin_benchmark("Ejecutando 31 interfaces reales…"):
            return
        threading.Thread(target=self._real_benchmark_worker, daemon=True).start()

    def _real_benchmark_worker(self):
        try:
            routines_text = real_benchmark.ROUTINES.read_text(encoding="utf-8")
            rows = []
            with tempfile.TemporaryDirectory() as directory:
                for case in real_benchmark.CASES:
                    try:
                        row = real_benchmark.run_case(case, directory, routines_text)
                    except Exception as exc:
                        row = self._failed_real_row(case, exc)
                    rows.append(row)
            result = real_benchmark.summarize_rows(rows)
            self.benchmark_queue.put((self._finish_real_benchmarks, result, None))
        except Exception as exc:
            self.benchmark_queue.put((self._finish_real_benchmarks, None, exc))

    def _finish_real_benchmarks(self, result, error):
        self._end_benchmark()
        if error is not None:
            self.append_console("Error en benchmarks reales: %s" % error, "error")
            self.benchmark_summary.configure(text="Error en benchmarks reales")
            self.set_status("Error en benchmarks reales", "error")
            messagebox.showerror("Benchmarks reales", str(error))
            return
        self._populate_real_benchmarks(result)
        self._set_report_text(real_benchmark.format_report(result), "REAL_BENCHMARK.md (memoria)")
        failures = [row["name"] for row in result["rows"]
                    if not row["halted"] or row["absolute_error"] != 0]
        for row in result["rows"]:
            if "error" in row:
                self.append_console("%s: %s" % (row["name"], row["error"]), "error")
        self.benchmark_summary.configure(
            text="31 interfaces · %d instrucciones · pico %d bytes · error máximo %d · %s" %
                 (result["global_instructions"], result["peak_memory"],
                  result["max_absolute_error"], "PASS" if not failures else "FAIL"))
        self.append_console("Benchmark real: 31 interfaces, %d instrucciones, error máximo %d" %
                            (result["global_instructions"], result["max_absolute_error"]),
                            "success" if not failures else "error")
        self.set_status("Benchmarks reales completados", "success" if not failures else "error")
        self.benchmark_tabs.select(0)
        self.real_tree.see(self.real_tree.get_children()[-1])

    def _populate_real_benchmarks(self, result):
        for item in self.real_tree.get_children():
            self.real_tree.delete(item)
        for index, row in enumerate(result["rows"], 1):
            state = "PASS" if row["halted"] and row["absolute_error"] == 0 else "FAIL"
            self.real_tree.insert("", "end", values=(
                index,
                row["name"],
                row["format"],
                "0x%04X" % row["input"],
                "0x%04X" % row["expected"],
                "0x%04X" % row["actual"],
                row["instructions"],
                row["image_bytes"],
                row["data_bytes"],
                row["peak_memory"],
                row["absolute_error"],
                state,
            ), tags=(state.lower(),))

    def run_migrated_benchmarks(self):
        if not self._begin_benchmark("Ejecutando 7 benchmarks migrados…"):
            return
        threading.Thread(target=self._migrated_benchmark_worker, daemon=True).start()

    def _migrated_benchmark_worker(self):
        try:
            with tempfile.TemporaryDirectory() as directory:
                results = benchmark_metrics.run_all(directory)
            self.benchmark_queue.put((self._finish_migrated_benchmarks, results, None))
        except Exception as exc:
            self.benchmark_queue.put((self._finish_migrated_benchmarks, None, exc))

    def _finish_migrated_benchmarks(self, results, error):
        self._end_benchmark()
        if error is not None:
            self.append_console("Error en benchmarks migrados: %s" % error, "error")
            self.benchmark_summary.configure(text="Error en benchmarks migrados")
            self.set_status("Error en benchmarks migrados", "error")
            messagebox.showerror("Benchmarks migrados", str(error))
            return
        self._populate_migrated_benchmarks(results)
        self._set_report_text(benchmark_metrics.format_markdown(results),
                              "BENCHMARK_METRICS.md (memoria)")
        failures = [name for name, row in results.items()
                    if not row["halted"] or row["max_absolute_error"] != 0]
        instructions = sum(row["instructions"] for row in results.values())
        for name, row in results.items():
            if "error" in row:
                self.append_console("%s: %s" % (name, row["error"]), "error")
        self.benchmark_summary.configure(
            text="7 benchmarks migrados · %d instrucciones · error máximo %d · %s" %
                 (instructions, max(row["max_absolute_error"] for row in results.values()),
                  "PASS" if not failures else "FAIL"))
        self.append_console("Benchmarks migrados: 7 cases, %d instrucciones" % instructions,
                            "success" if not failures else "error")
        self.set_status("Benchmarks migrados completados", "success" if not failures else "error")
        self.benchmark_tabs.select(1)
        self.migrated_tree.see(self.migrated_tree.get_children()[-1])

    def _populate_migrated_benchmarks(self, results):
        for item in self.migrated_tree.get_children():
            self.migrated_tree.delete(item)
        for name, row in results.items():
            state = "PASS" if row["halted"] and row["max_absolute_error"] == 0 else "FAIL"
            self.migrated_tree.insert("", "end", values=(
                name,
                row["instructions"],
                row["image_bytes"],
                row["memory_observed"],
                row["peak_memory"],
                "0x%04X" % row["pc"],
                row["max_absolute_error"],
                state,
            ), tags=(state.lower(),))

    def run_scientific_closure(self):
        if not self._begin_benchmark("Ejecutando cierre científico…"):
            return
        threading.Thread(target=self._scientific_closure_worker, daemon=True).start()

    def _scientific_closure_worker(self):
        try:
            with tempfile.TemporaryDirectory() as directory:
                result = scientific_closure.run_closure(directory)
            self.benchmark_queue.put((self._finish_scientific_closure, result, None))
        except Exception as exc:
            self.benchmark_queue.put((self._finish_scientific_closure, None, exc))

    def _finish_scientific_closure(self, result, error):
        self._end_benchmark()
        if error is not None:
            self.append_console("Error en cierre científico: %s" % error, "error")
            self.benchmark_summary.configure(text="Error en cierre científico")
            self.set_status("Error en cierre científico", "error")
            messagebox.showerror("Cierre científico", str(error))
            return
        self._populate_real_benchmarks(result["benchmark"])
        self._set_report_text(scientific_closure.format_report(result),
                              "SCIENTIFIC_CLOSURE.md (memoria)")
        self.benchmark_summary.configure(
            text="Cierre científico · 31 interfaces · %d instrucciones · pico %d bytes · error %d" %
                 (result["instructions"], result["peak_memory"], result["max_absolute_error"]))
        self.append_console("Cierre científico: 31 interfaces, error máximo %d" %
                            result["max_absolute_error"],
                            "success" if result["max_absolute_error"] == 0 else "error")
        self.set_status("Cierre científico completado",
                        "success" if result["max_absolute_error"] == 0 else "error")
        self.benchmark_tabs.select(0)

    def load_report(self):
        path = filedialog.askopenfilename(
            initialdir=str(ROOT),
            filetypes=[("Markdown", "*.md"), ("Todos", "*")])
        if not path:
            return
        try:
            text = Path(path).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            messagebox.showerror("Reporte", str(exc))
            return
        self._set_report_text(text, Path(path).name)
        self.set_status("Reporte cargado: %s" % Path(path).name, "success")

    def regenerate_reports(self):
        if not self._begin_benchmark("Regenerando reportes…"):
            return
        threading.Thread(target=self._regenerate_reports_worker, daemon=True).start()

    def _regenerate_reports_worker(self):
        try:
            sources = ROOT / "benchmark" / "real"
            real_result = real_benchmark.run_all(sources)
            closure_result = scientific_closure.run_closure(sources)
            with tempfile.TemporaryDirectory() as directory:
                migrated_results = benchmark_metrics.run_all(directory)
            texts = {
                "REAL_BENCHMARK.md": real_benchmark.format_report(real_result),
                "SCIENTIFIC_CLOSURE.md": scientific_closure.format_report(closure_result),
                "BENCHMARK_METRICS.md": benchmark_metrics.format_markdown(migrated_results),
            }
            for name, text in texts.items():
                (ROOT / name).write_text(text, encoding="utf-8")
            self.benchmark_queue.put((self._finish_regenerate_reports, texts, None))
        except Exception as exc:
            self.benchmark_queue.put((self._finish_regenerate_reports, None, exc))

    def _finish_regenerate_reports(self, texts, error):
        self._end_benchmark()
        if error is not None:
            self.append_console("Error al regenerar reportes: %s" % error, "error")
            self.benchmark_summary.configure(text="Error al regenerar reportes")
            self.set_status("Error al regenerar reportes", "error")
            messagebox.showerror("Reportes", str(error))
            return
        self._set_report_text(texts["SCIENTIFIC_CLOSURE.md"], "SCIENTIFIC_CLOSURE.md")
        self.benchmark_summary.configure(text="Reportes regenerados: 3 archivos")
        self.append_console("Reportes regenerados: REAL_BENCHMARK.md, "
                            "SCIENTIFIC_CLOSURE.md, BENCHMARK_METRICS.md", "success")
        self.set_status("Reportes regenerados", "success")

    def run(self):
        self.mainloop()


if __name__ == "__main__":
    import sys
    if "--smoke" in sys.argv:
        app = Lab3GUI()
        app.update_idletasks()
        app.destroy()
        print("GUI smoke test: OK")
    elif "--smoke-benchmarks" in sys.argv:
        app = Lab3GUI()
        app.update_idletasks()

        def wait_for_benchmark():
            deadline = time.monotonic() + 30
            while app.benchmark_running and time.monotonic() < deadline:
                app.update()
                time.sleep(0.01)
            if app.benchmark_running:
                raise RuntimeError("timeout esperando benchmark")

        app.run_real_benchmarks()
        wait_for_benchmark()
        rows = len(app.real_tree.get_children())
        app.run_migrated_benchmarks()
        wait_for_benchmark()
        migrated_rows = len(app.migrated_tree.get_children())
        app.run_scientific_closure()
        wait_for_benchmark()
        app.update_idletasks()
        app.destroy()
        print("GUI benchmark smoke test: OK; filas=%d; migrados=%d" %
              (rows, migrated_rows))
    else:
        Lab3GUI().run()
