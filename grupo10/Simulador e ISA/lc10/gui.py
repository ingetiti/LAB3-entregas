"""Ventana del LC10: editor, ensamblador y simulador en una sola pantalla (tkinter).

    python -m lc10.gui [programa.asm [modulo.asm ...]]

La ventana no tiene lógica propia de ISA: llama al mismo ensamblador y al mismo simulador
que la línea de comandos (a través de `lc10.session.Session`). Los archivos de imagen
siguen existiendo: "Programa > Exportar imagen..." guarda el .hex/.bin/.dec/.bits y
"Programa > Abrir imagen y simular..." ejecuta una imagen ya ensamblada sin pasar por el fuente.

Pestañas: la primera (marcada con ★ cuando hay varias) es el programa principal; las demás
son módulos que se enlazan con `.EXTERNAL`, igual que `python -m lc10.assembler principal.asm modulo.asm`.
"""
from __future__ import annotations

import re
import sys
import time
from pathlib import Path

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, simpledialog, ttk
    from tkinter import font as tkfont
except ImportError:                                            # pragma: no cover
    if __name__ == "__main__":
        sys.exit("Este Python no incluye tkinter. En Windows y macOS viene con el instalador de "
                 "python.org; en Linux: sudo apt install python3-tk")
    raise

from . import isa
from .assembler import AsmError, is_mnemonic, parse_number, strip_comment
from .image import FORMATS, Image, ImageError
from .session import Session
from .syntax import highlight_spans, parse_input_escapes

# ---------------------------------------------------------------------------- aspecto
T = dict(
    bg="#f3f4f6", panel="#ffffff", border="#d0d7de", fg="#1f2328", muted="#6e7781", accent="#0969da",
    accent_dark="#0757b5", gutter_bg="#f6f8fa", gutter_fg="#8c959f", sel="#b6d6ff",
    pc_bg="#fff1a8", err_bg="#ffd7d5", changed="#ffd479", bp="#d1242f", ok="#1a7f37", err="#cf222e",
    flag_on="#1a7f37", flag_off="#e6e9ed", mem_pc="#c8e1ff",
    comment="#6e7781", string="#0a3069", directive="#953800", reg="#8250df", number="#0a7a3d",
    mnemonic="#0550ae", label_def="#116329", label_ref="#116329", unknown="#cf222e",
)
MONO_CANDIDATES = ("Cascadia Mono", "Consolas", "DejaVu Sans Mono", "Menlo", "Liberation Mono", "Courier New")
ASM_TYPES = [("Assembly LC10", "*.asm"), ("Todos los archivos", "*.*")]
IMAGE_TYPES = [("Hexadecimal", "*.hex"), ("Binario", "*.bin"), ("Decimal", "*.dec"), ("Bits", "*.bits")]

EJEMPLO_SUMA = """\
; Ejemplo LC10: suma 5+4+3+2+1 y escribe un saludo.
        .ORIG x3000
        MOVI  R1, #0            ; suma = 0
        MOVI  R2, #5            ; contador = 5
LAZO    ADD   R1, R1, R2        ; suma += contador
        ADD   R2, R2, #-1       ; contador--
        BRp   LAZO              ; mientras contador > 0
        ST    R1, SUMA          ; guarda el resultado (15)
        LEA   R0, MSG           ; R0 = dirección del texto
        PUTS                    ; escribe la cadena
        HALT
SUMA    .FILL 0
MSG     .STRINGZ "Hola LC10\\n"
        .END
"""
EJEMPLO_HOLA = """\
; Ejemplo mínimo para LC10: escribe un texto (bytes, terminado en 0) y termina.
        .ORIG x3000
        LEA   R0, MSG           ; LEA llega también a direcciones impares
        PUTS
        HALT
MSG     .STRINGZ "Hola LC10\\n"
        .END
"""
PLANTILLA_PRINCIPAL = """\
; Programa principal LC10
        .ORIG x3000

        HALT
        .END
"""
PLANTILLA_MODULO = """\
; Módulo LC10 (sin .ORIG). Desde el programa principal:
;   .EXTERNAL NOMBRE-ETIQUETA     y luego     JSR NOMBRE-ETIQUETA
; (NOMBRE es el nombre de este archivo en mayúsculas, sin .asm)

        .END
"""
REFERENCIA = """\
LC10: referencia

La descripción de la ISA se entrega aparte, junto con el informe.
Para correr y ensamblar programas ver INSTRUCTIVO.md.
"""
ATAJOS = """\
F7             Ensamblar
F5             Ejecutar (ensambla antes si el código cambió)
F10            Un paso
Mayús+F5       Detener
F6             Reiniciar (vuelve al principio del programa)
F9             Punto de parada en la línea del cursor (o clic en el margen izquierdo)

Ctrl+N / Ctrl+O / Ctrl+S    Nuevo / Abrir / Guardar
Ctrl+W                      Cerrar pestaña
Ctrl+Tab / Ctrl+Mayús+Tab   Archivo siguiente / anterior (también Ctrl+Av Pág / Ctrl+Re Pág)
Ctrl+B                      Mostrar u ocultar la lista de archivos (con buscador)
Ctrl++ / Ctrl+-             Agrandar / achicar la letra del código

F5 se detiene solo a las 20 millones de instrucciones sin HALT (un bucle infinito); F5 de nuevo
sigue otro tanto. Programa > Límite de instrucciones... cambia ese tope (0 = sin tope).

Programa > Velocidad de ejecución limita F5 a 100, 1.000, 2.000, 5.000 o 10.000 instrucciones por
segundo como máximo (para ver correr el programa: se mueve la línea actual, los registros y la
memoria). Se puede cambiar mientras corre. Por defecto no hay límite.
Archivo > Abrir benchmark abre el benchmark del curso (main_grupo27.asm como principal y todos
sus módulos) y deja todo listo para F5.

La entrada para GETC e IN se toma al ensamblar o reiniciar.

El contador de la barra muestra "usuario + SO = total": las instrucciones del SO son las de las rutinas
de los TRAP (lc10/os_lc10.asm), que el simulador ejecuta como cualquier código. F10 con un TRAP
ejecuta la rutina entera en un solo paso.
Las instrucciones deben empezar con sangría o ser mnemónicos: una palabra en la primera
columna que no sea instrucción se toma como etiqueta.
"""

_UI_FONTS: dict = {}


def ui_font(size: int = 9, weight: str = "normal", slant: str = "roman") -> tkfont.Font:
    """Copia de la fuente por defecto de Tk con otro tamaño/estilo (se reutilizan las ya creadas)."""
    key = (size, weight, slant)
    if key not in _UI_FONTS:
        f = tkfont.nametofont("TkDefaultFont").copy()
        f.configure(size=size, weight=weight, slant=slant)
        _UI_FONTS[key] = f
    return _UI_FONTS[key]


def pick_mono(root) -> str:
    fams = set(tkfont.families(root))
    for f in MONO_CANDIDATES:
        if f in fams:
            return f
    return tkfont.nametofont("TkFixedFont").actual("family")


# ---------------------------------------------------------------------------- piezas
class Card(tk.Frame):
    """Marco con título y borde fino."""

    def __init__(self, master, title: str):
        super().__init__(master, bg=T["bg"])
        tk.Label(self, text=title, bg=T["bg"], fg=T["muted"], anchor="w",
                 font=ui_font(9, "bold")).pack(fill="x", padx=2)
        self.body = tk.Frame(self, bg=T["panel"], highlightthickness=1, highlightbackground=T["border"])
        self.body.pack(fill="both", expand=True)


class Viewer(tk.Frame):
    """Texto de solo lectura con barras de desplazamiento."""

    def __init__(self, master, font, wrap: str = "none"):
        super().__init__(master, bg=T["panel"])
        self.text = tk.Text(self, font=font, wrap=wrap, state="disabled", bg=T["panel"], fg=T["fg"],
                            relief="flat", bd=0, highlightthickness=0, padx=8, pady=6,
                            selectbackground=T["sel"], selectforeground=T["fg"])
        self.vsb = ttk.Scrollbar(self, orient="vertical", command=self.text.yview)
        self.text.configure(yscrollcommand=self.vsb.set)
        self.vsb.pack(side="right", fill="y")
        if wrap == "none":
            hsb = ttk.Scrollbar(self, orient="horizontal", command=self.text.xview)
            self.text.configure(xscrollcommand=hsb.set)
            hsb.pack(side="bottom", fill="x")
        self.text.pack(side="left", fill="both", expand=True)

    def set(self, content: str) -> None:
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.insert("1.0", content)
        self.text.configure(state="disabled")

    def append(self, content: str, tag: str | None = None, max_chars: int = 400_000) -> None:
        if not content:
            return
        t = self.text
        t.configure(state="normal")
        t.insert("end", content, tag or ())
        extra = len(t.get("1.0", "end-1c")) - max_chars
        if extra > 0:                                   # se descarta lo más viejo, línea completa
            t.delete("1.0", f"1.0+{extra}c lineend +1c")
        t.configure(state="disabled")
        t.see("end")

    def ends_with_newline(self) -> bool:
        s = self.text.get("end-2c", "end-1c")
        return s in ("", "\n")

    def clear(self) -> None:
        self.set("")


class CodeEditor(tk.Frame):
    """Una pestaña: texto con colores, números de línea y puntos de parada."""

    def __init__(self, master, app: "App", name: str, text: str = "", path: Path | None = None):
        super().__init__(master, bg=T["panel"])
        self.app, self.name, self.path = app, name, path
        self.modified = False
        self.pc_line: int | None = None
        self._hl_job = self._gutter_job = None
        self._loading = True
        self.text = tk.Text(self, wrap="none", undo=True, maxundo=-1, autoseparators=True, font=app.mono,
                            bg=T["panel"], fg=T["fg"], insertbackground=T["fg"], relief="flat", bd=0,
                            highlightthickness=0, padx=6, pady=4, selectbackground=T["sel"],
                            selectforeground=T["fg"], inactiveselectbackground=T["sel"])
        self.gutter = tk.Canvas(self, bg=T["gutter_bg"], highlightthickness=0, bd=0)
        self.vsb = ttk.Scrollbar(self, orient="vertical", command=self.text.yview)
        self.hsb = ttk.Scrollbar(self, orient="horizontal", command=self.text.xview)
        self.text.configure(yscrollcommand=self._yscroll, xscrollcommand=self.hsb.set)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)
        self.gutter.grid(row=0, column=0, sticky="ns")
        self.text.grid(row=0, column=1, sticky="nsew")
        self.vsb.grid(row=0, column=2, sticky="ns")
        self.hsb.grid(row=1, column=0, columnspan=2, sticky="ew")
        self._configure_tags()
        self.update_metrics()
        self.text.insert("1.0", text)
        self.text.edit_reset()
        self.text.edit_modified(False)
        self._loading = False
        self.rehighlight()
        self._bind()

    def destroy_jobs(self) -> None:
        for job in (self._hl_job, self._gutter_job):
            if job is not None:
                try:
                    self.after_cancel(job)
                except tk.TclError:
                    pass
        self._hl_job = self._gutter_job = None

    def destroy(self) -> None:
        self.destroy_jobs()
        super().destroy()

    # ---- apariencia
    def _configure_tags(self) -> None:
        t, a = self.text, self.app
        t.tag_configure("comment", foreground=T["comment"])
        t.tag_configure("string", foreground=T["string"])
        t.tag_configure("directive", foreground=T["directive"])
        t.tag_configure("reg", foreground=T["reg"])
        t.tag_configure("number", foreground=T["number"])
        t.tag_configure("mnemonic", foreground=T["mnemonic"], font=a.mono_bold)
        t.tag_configure("label_def", foreground=T["label_def"], font=a.mono_bold)
        t.tag_configure("label_ref", foreground=T["label_ref"])
        t.tag_configure("unknown", foreground=T["unknown"], underline=True)
        t.tag_configure("errline", background=T["err_bg"])
        t.tag_configure("pcline", background=T["pc_bg"])
        t.tag_raise("sel")
        t.configure(tabs=(a.mono.measure(" " * 8),))

    def update_metrics(self) -> None:
        self.gutter.configure(width=34 + self.app.mono.measure("0000") + 8)
        self.text.configure(tabs=(self.app.mono.measure(" " * 8),))
        self.schedule_gutter()

    def _bind(self) -> None:
        t = self.text
        t.bind("<<Modified>>", self._on_modified)
        t.bind("<Tab>", self._on_tab)
        t.bind("<Return>", self._on_return)
        t.bind("<Control-a>", lambda e: (t.tag_add("sel", "1.0", "end-1c"), "break")[1])
        t.bind("<Control-y>", lambda e: (t.event_generate("<<Redo>>"), "break")[1])
        for seq, fn in self.app.nav_bindings():                                  # Ctrl+Tab: sin esto lo toma <Tab>
            try:
                t.bind(seq, fn)
            except tk.TclError:
                pass
        t.bind("<Control-o>", lambda e: (self.app.cmd_open(), "break")[1])       # sustituyen a los atajos de Emacs de Tk
        t.bind("<Control-n>", lambda e: (self.app.cmd_new(), "break")[1])
        t.bind("<Configure>", lambda e: self.schedule_gutter())
        self.gutter.bind("<Button-1>", self._gutter_click)
        for w in (t, self.gutter):
            w.bind("<MouseWheel>", lambda e: self.schedule_gutter(), add="+")
            w.bind("<Button-4>", lambda e: self.schedule_gutter(), add="+")
            w.bind("<Button-5>", lambda e: self.schedule_gutter(), add="+")

    # ---- edición
    def _on_modified(self, _e=None) -> None:
        if self._loading or not self.text.edit_modified():
            return
        self.text.edit_modified(False)
        self.set_error_line(None)
        self.set_pc_line(None)
        self.set_modified(True)
        self.app.on_source_changed(self)
        self.schedule_highlight()
        self.schedule_gutter()

    def _delete_selection(self) -> None:
        if self.text.tag_ranges("sel"):
            self.text.delete("sel.first", "sel.last")

    def _on_tab(self, _e) -> str:
        self._delete_selection()
        col = int(self.text.index("insert").split(".")[1])
        self.text.insert("insert", " " * (8 - col % 8))
        return "break"

    def _on_return(self, _e) -> str:
        self._delete_selection()
        indent = re.match(r"[ \t]*", self.text.get("insert linestart", "insert")).group()
        self.text.insert("insert", "\n" + indent)
        self.text.see("insert")
        return "break"

    def set_modified(self, value: bool) -> None:
        if self.modified != value:
            self.modified = value
            self.app.update_tab_title(self)

    def get_text(self) -> str:
        return self.text.get("1.0", "end-1c")

    # ---- colores
    def schedule_highlight(self) -> None:
        if self._hl_job is None:
            self._hl_job = self.after(150, self.rehighlight)

    def rehighlight(self) -> None:
        self._hl_job = None
        t = self.text
        for tag in ("comment", "string", "directive", "reg", "number", "mnemonic", "label_def", "label_ref", "unknown"):
            t.tag_remove(tag, "1.0", "end")
        for tag, ln, a, b in highlight_spans(self.get_text()):
            t.tag_add(tag, f"{ln}.{a}", f"{ln}.{b}")

    # ---- márgenes, puntos de parada y marcas de ejecución
    def schedule_gutter(self) -> None:
        if self._gutter_job is None:
            self._gutter_job = self.after_idle(self.redraw_gutter)

    def _yscroll(self, first, last) -> None:
        self.vsb.set(first, last)
        self.schedule_gutter()

    def redraw_gutter(self) -> None:
        self._gutter_job = None
        g, t = self.gutter, self.text
        g.delete("all")
        bps = self.breakpoint_lines()
        right = g.winfo_width() - 8 if g.winfo_width() > 1 else int(g.cget("width")) - 8
        idx, prev = t.index("@0,0"), None
        while idx != prev:
            info = t.dlineinfo(idx)
            if info is None:
                break
            y, h = info[1], info[3]
            line = int(idx.split(".")[0])
            cy = y + h / 2
            g.create_text(right, cy, text=str(line), anchor="e", fill=T["gutter_fg"], font=self.app.mono)
            if line in bps:
                g.create_oval(4, cy - 5, 14, cy + 5, fill=T["bp"], outline="")
            if line == self.pc_line:
                g.create_polygon(18, cy - 6, 18, cy + 6, 30, cy, fill=T["accent"], outline="")
            prev, idx = idx, t.index(f"{idx}+1line")

    def _gutter_click(self, e) -> None:
        line = int(self.text.index(f"@0,{e.y}").split(".")[0])
        self.toggle_breakpoint(line)

    def has_code(self, line: int) -> bool:
        return bool(strip_comment(self.text.get(f"{line}.0", f"{line}.end")).strip())

    def breakpoint_lines(self) -> set[int]:
        r = self.text.tag_ranges("bp")
        return {int(str(r[i]).split(".")[0]) for i in range(0, len(r), 2)}

    def toggle_breakpoint(self, line: int) -> None:
        if line in self.breakpoint_lines():
            self.text.tag_remove("bp", f"{line}.0", f"{line}.0 lineend +1c")
        elif self.has_code(line):
            self.text.tag_add("bp", f"{line}.0", f"{line}.0 +1c")
        else:
            self.bell()
        self.schedule_gutter()

    def clear_breakpoints(self) -> None:
        self.text.tag_remove("bp", "1.0", "end")
        self.schedule_gutter()

    def _mark_line(self, tag: str, line: int | None) -> None:
        self.text.tag_remove(tag, "1.0", "end")
        if line:
            self.text.tag_add(tag, f"{line}.0", f"{line + 1}.0")

    def set_pc_line(self, line: int | None) -> None:
        self.pc_line = line
        self._mark_line("pcline", line)
        self.schedule_gutter()

    def set_error_line(self, line: int | None) -> None:
        self._mark_line("errline", line)

    def goto(self, line: int) -> None:
        self.text.mark_set("insert", f"{line}.0")
        self.text.see(f"{line}.0")
        self.text.focus_set()


class RegisterPanel(Card):
    def __init__(self, master, app: "App"):
        super().__init__(master, "REGISTROS")
        self.app = app
        b = self.body
        for c, txt in enumerate(("", "hex", "dec", "binario")):
            tk.Label(b, text=txt, bg=T["panel"], fg=T["muted"], font=ui_font(8)).grid(row=0, column=c, sticky="w", padx=6)
        self.hex, self.dec, self.bin = {}, {}, {}
        self.keys = ["PC"] + [f"R{i}" for i in range(8)]
        for r, k in enumerate(self.keys, 1):
            tk.Label(b, text=k, bg=T["panel"], fg=T["fg"], font=app.mono_bold, anchor="w").grid(row=r, column=0, sticky="w", padx=(8, 4))
            self.hex[k] = tk.Label(b, text="", bg=T["panel"], fg=T["fg"], font=app.mono, anchor="w", width=6)
            self.dec[k] = tk.Label(b, text="", bg=T["panel"], fg=T["fg"], font=app.mono, anchor="e", width=6)
            self.bin[k] = tk.Label(b, text="", bg=T["panel"], fg=T["muted"], font=app.mono, anchor="w")
            self.hex[k].grid(row=r, column=1, sticky="we", padx=4)
            self.dec[k].grid(row=r, column=2, sticky="we", padx=4)
            self.bin[k].grid(row=r, column=3, sticky="we", padx=(4, 8))
        n = len(self.keys) + 1
        tk.Label(b, text="sigue", bg=T["panel"], fg=T["muted"], font=ui_font(8), anchor="w").grid(row=n, column=0, padx=(8, 4), sticky="w", pady=(4, 0))
        self.next = tk.Label(b, text="", bg=T["panel"], fg=T["fg"], font=app.mono, anchor="w")
        self.next.grid(row=n, column=1, columnspan=3, sticky="we", padx=4, pady=(4, 0))
        fr = tk.Frame(b, bg=T["panel"])
        fr.grid(row=n + 1, column=0, columnspan=4, sticky="w", padx=8, pady=(6, 8))
        tk.Label(fr, text="Banderas", bg=T["panel"], fg=T["muted"], font=ui_font(8)).pack(side="left", padx=(0, 8))
        self.flags = {}
        for f in ("N", "Z", "P", "C", "V"):
            lb = tk.Label(fr, text=f, width=3, font=app.mono_bold, bg=T["flag_off"], fg=T["muted"],
                          highlightthickness=2, highlightbackground=T["panel"])
            lb.pack(side="left", padx=2)
            self.flags[f] = lb
        b.columnconfigure(3, weight=1)
        self.update(None)

    def update(self, m, changed_regs=(), changed_flags=(), next_text: str = "") -> None:
        for i, k in enumerate(self.keys):
            if m is None:
                self.hex[k].configure(text="----", bg=T["panel"])
                self.dec[k].configure(text="", bg=T["panel"])
                self.bin[k].configure(text="", bg=T["panel"])
                continue
            v = m.pc if k == "PC" else m.regs[i - 1]
            bg = T["changed"] if (i - 1) in changed_regs and k != "PC" else T["panel"]
            self.hex[k].configure(text=f"x{v:04X}", bg=bg)
            self.dec[k].configure(text=str(v if k == "PC" else isa.to_s16(v)), bg=bg)
            self.bin[k].configure(text=" ".join(f"{v:016b}"[j:j + 4] for j in range(0, 16, 4)), bg=bg)
        self.next.configure(text=next_text)
        vals = {} if m is None else dict(N=m.n, Z=m.z, P=m.p, C=m.c, V=m.v)
        for f, lb in self.flags.items():
            on = bool(vals.get(f))
            lb.configure(bg=T["flag_on"] if on else T["flag_off"], fg="#ffffff" if on else T["muted"],
                         highlightbackground=T["changed"] if f in changed_flags else T["panel"])


class MemoryPanel(Card):
    PER_ROW, ROWS = 8, 32

    def __init__(self, master, app: "App"):
        super().__init__(master, "MEMORIA")
        self.app = app
        self.base = 0x3000
        top = tk.Frame(self.body, bg=T["panel"])
        top.pack(fill="x", padx=6, pady=(6, 0))
        top2 = tk.Frame(self.body, bg=T["panel"])
        top2.pack(fill="x", padx=6, pady=(2, 2))
        self.addr_var = tk.StringVar(value="x3000")
        self.entry = ttk.Entry(top, textvariable=self.addr_var, width=14)
        self.entry.pack(side="left")
        self.entry.bind("<Return>", lambda e: self.go())
        ttk.Button(top, text="Ir", width=3, command=self.go).pack(side="left", padx=(4, 8))
        ttk.Button(top, text="◀", width=3, command=lambda: self.page(-1)).pack(side="left")
        ttk.Button(top, text="▶", width=3, command=lambda: self.page(1)).pack(side="left", padx=(2, 8))
        ttk.Button(top, text="PC", width=4, command=self.go_pc).pack(side="left")
        self.follow = tk.BooleanVar(value=True)
        ttk.Checkbutton(top2, text="Seguir PC", variable=self.follow, command=self.render).pack(side="left")
        self.mode = tk.StringVar(value="Bytes")
        cb = ttk.Combobox(top2, textvariable=self.mode, values=("Bytes", "Palabras"), width=9, state="readonly")
        cb.pack(side="right")
        cb.bind("<<ComboboxSelected>>", lambda e: self.render())
        width = 7 + self.PER_ROW * 3 + 4 + self.PER_ROW
        self.text = tk.Text(self.body, height=6, width=width, font=app.mono, state="disabled", wrap="none",
                            bg=T["panel"], fg=T["fg"], relief="flat", bd=0, highlightthickness=0, padx=8, pady=4,
                            selectbackground=T["sel"], selectforeground=T["fg"])
        vsb = ttk.Scrollbar(self.body, orient="vertical", command=self.text.yview)
        self.text.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y", pady=(0, 4))
        self.text.pack(fill="both", expand=True, padx=2, pady=(0, 4))
        self.text.tag_configure("addr", foreground=T["muted"])
        self.text.tag_configure("ascii", foreground=T["muted"])
        self.text.tag_configure("pc", background=T["mem_pc"])
        self.text.tag_configure("chg", background=T["changed"])
        self.last_changed: set[int] = set()
        self.render()

    @property
    def window(self) -> int:
        return self.PER_ROW * self.ROWS

    def set_base(self, addr: int) -> None:
        self.base = max(0, min(addr & ~(self.PER_ROW - 1), 0x10000 - self.window))
        self.addr_var.set(f"x{self.base:04X}")

    def go(self) -> None:
        try:
            self.set_base(self.app.resolve_address(self.addr_var.get()))
        except ValueError as e:
            self.app.status(str(e), error=True)
            return
        self.follow.set(False)                      # el usuario eligió dónde mirar
        self.last_changed = set()
        self.render()

    def go_pc(self) -> None:
        self.follow.set(True)
        self.render()

    def page(self, direction: int) -> None:
        self.follow.set(False)
        self.set_base(self.base + direction * self.window)
        self.last_changed = set()
        self.render()

    def render(self, changed=None) -> None:
        if changed is not None:
            self.last_changed = set(changed)
        s = self.app.session
        m = s.machine
        t = self.text
        old_view = t.yview()[0]
        t.configure(state="normal")
        t.delete("1.0", "end")
        if m is None:
            t.insert("1.0", "\n  Sin programa cargado.\n  Ensamble (F7) o ejecute (F5).")
            t.configure(state="disabled")
            return
        words = self.mode.get() == "Palabras"
        pc = m.pc
        old_base = self.base
        if self.follow.get() and not (self.base <= pc < self.base + self.window):
            self.set_base(pc - self.PER_ROW * 4)
        lines, spans = [], []
        for r in range(self.ROWS):
            a = self.base + r * self.PER_ROW
            row = m.mem[a:a + self.PER_ROW]
            line = f"x{a:04X}  "
            spans.append(("addr", r, 0, 5))
            step = 2 if words else 1
            for i in range(0, self.PER_ROW, step):
                ad = a + i
                cell = f"{row[i] | row[i + 1] << 8:04X}" if words else f"{row[i]:02X}"
                start = len(line)
                line += cell
                size = step
                if any(x in (pc, pc + 1) for x in range(ad, ad + size)):
                    spans.append(("pc", r, start, start + len(cell)))
                if any(x in self.last_changed for x in range(ad, ad + size)):
                    spans.append(("chg", r, start, start + len(cell)))
                line += " " if i + step < self.PER_ROW else ""
                if words and i + step == self.PER_ROW // 2:
                    line += " "
                if not words and i + 1 == self.PER_ROW // 2:
                    line += " "
            start = len(line) + 2
            line += "  " + "".join(chr(b) if 32 <= b < 127 else "." for b in row)
            spans.append(("ascii", r, start, len(line)))
            lines.append(line)
        t.insert("1.0", "\n".join(lines))
        for tag, r, a, b in spans:
            t.tag_add(tag, f"{r + 1}.{a}", f"{r + 1}.{b}")
        t.tag_raise("chg")
        if self.follow.get() and self.base <= pc < self.base + self.window:
            t.see(f"{(pc - self.base) // self.PER_ROW + 1}.0")
        elif self.base == old_base:
            t.yview_moveto(old_view)
        t.configure(state="disabled")


MAX_RUN_DEFAULT = 20_000_000          # unos 20 s de simulación; Programa > Límite de instrucciones... lo cambia
BASE_TITLE = "LC10 · Grupo 10"
BENCHMARK_DIR = Path(__file__).resolve().parent.parent / "asm" / "opt10"   # el benchmark del curso portado a LC10
BENCHMARK_MAIN = "main_grupo27.asm"
SPEEDS = (0, 100, 1000, 2000, 5000, 10000)    # instrucciones por segundo como máximo; 0 = sin límite
BURST_S = 0.05                                # el regulador nunca junta más de 50 ms de instrucciones atrasadas


def fmt_int(n: int) -> str:
    """Entero con punto de miles, como en las cifras del resto del programa (17.791)."""
    return f"{n:,}".replace(",", ".")
AUTO_LIST_FROM = 4                    # la lista de archivos aparece sola al abrir más de 4 archivos
NAV_KEYS = (("<Control-Tab>", 1), ("<Control-Next>", 1),                              # archivo siguiente
            ("<Control-Shift-Tab>", -1), ("<Control-ISO_Left_Tab>", -1), ("<Control-Prior>", -1))   # anterior
NAME_SHORT = 20                       # largo máximo del nombre en los botones ◀ ▶


def short_name(name: str, width: int = NAME_SHORT) -> str:
    return name if len(name) <= width else name[: width - 1] + "…"


# ---------------------------------------------------------------------------- aplicación
class App:
    def __init__(self, root: tk.Tk, files=()):
        self.root = root
        _UI_FONTS.clear()                 # las fuentes pertenecen a una ventana raíz concreta
        self.session = Session()
        self.editors: list[CodeEditor] = []
        self.main_editor: CodeEditor | None = None
        self.stale = True                 # el fuente cambió desde el último ensamblado
        self.origin = "source"            # 'source' | 'image'
        self.image_name = ""
        self.running = False
        self._job = None
        self.max_run = MAX_RUN_DEFAULT    # instrucciones por pulsación de Ejecutar (0 = sin límite)
        self.run_limit: int | None = None # valor de machine.count donde se detiene la ejecución en curso
        self.speed = tk.IntVar(root, value=0)    # tope de instrucciones por segundo (0 = lo más rápido posible)
        self._credit = 0.0                       # instrucciones que el regulador de velocidad permite ejecutar ya
        self._last_t = 0.0
        self._resumed = False                    # la ejecución en curso ya corrió una tanda (ver run_chunk)
        self.snap = None
        self.bp_addrs: set[int] = set()
        self.font_size = 11
        self._counter = 0
        self.show_files = tk.BooleanVar(root, value=False)   # panel lateral con la lista de archivos
        self._files_shown = False
        self._files_auto_done = False                        # ya se mostró solo (o el usuario eligió): no insistir
        self._file_sig = None                                # qué muestra hoy la lista (para no rehacerla de balde)
        self._list_editors: list[CodeEditor] = []
        root.title(BASE_TITLE)
        self._setup_style()
        self.mono = tkfont.Font(root, family=pick_mono(root), size=self.font_size)
        self.mono_bold = tkfont.Font(root, family=self.mono.actual("family"), size=self.font_size, weight="bold")
        self._build_menu()
        self._build_ui()
        self._bind_keys()
        root.protocol("WM_DELETE_WINDOW", self.on_close)
        if files:
            self.open_paths([Path(f) for f in files])
        if not self.editors:
            self.new_editor("ejemplo.asm", EJEMPLO_SUMA)
        self.status("Listo. F7 ensambla, F5 ejecuta, F10 avanza de a un paso.")
        self.refresh_buttons()
        self._sash_job = root.after(60, self._place_sashes)

    # ------------------------------------------------------------------ estilo
    def _setup_style(self) -> None:
        r = self.root
        r.configure(bg=T["bg"])
        st = ttk.Style(r)
        if "clam" in st.theme_names():
            st.theme_use("clam")
        st.configure(".", background=T["bg"], foreground=T["fg"], bordercolor=T["border"], focuscolor=T["bg"])
        st.configure("TButton", padding=(10, 4), background="#ffffff", relief="flat", borderwidth=1)
        st.map("TButton", background=[("disabled", T["bg"]), ("active", "#e8edf3")], foreground=[("disabled", "#a0a7ae")])
        st.configure("Nav.TButton", padding=(8, 3))
        st.configure("Run.TButton", background=T["accent"], foreground="#ffffff")
        st.map("Run.TButton", background=[("disabled", "#9ec3ee"), ("active", T["accent_dark"])],
               foreground=[("disabled", "#ffffff")])
        st.configure("TNotebook", background=T["bg"], borderwidth=0)
        st.configure("TNotebook.Tab", padding=(12, 5), background="#e6e9ed", foreground=T["muted"])
        st.map("TNotebook.Tab", background=[("selected", T["panel"])], foreground=[("selected", T["fg"])])
        st.configure("TEntry", fieldbackground="#ffffff")
        st.configure("TCombobox", fieldbackground="#ffffff")
        st.configure("TCheckbutton", background=T["bg"])
        st.configure("TPanedwindow", background=T["bg"])
        st.configure("TScrollbar", background="#e6e9ed", troughcolor=T["bg"], bordercolor=T["bg"], arrowsize=12)

    # ------------------------------------------------------------------ menús
    def _build_menu(self) -> None:
        r = self.root
        bar = tk.Menu(r)
        f = tk.Menu(bar, tearoff=False)
        f.add_command(label="Nuevo", accelerator="Ctrl+N", command=self.cmd_new)
        f.add_command(label="Abrir...", accelerator="Ctrl+O", command=self.cmd_open)
        f.add_command(label="Abrir benchmark", command=self.cmd_open_benchmark)
        f.add_command(label="Guardar", accelerator="Ctrl+S", command=self.cmd_save)
        f.add_command(label="Guardar como...", command=lambda: self.cmd_save(as_new=True))
        f.add_separator()
        f.add_command(label="Cerrar pestaña", accelerator="Ctrl+W", command=self.cmd_close_tab)
        f.add_command(label="Usar esta pestaña como programa principal", command=self.cmd_make_main)
        f.add_separator()
        ex = tk.Menu(f, tearoff=False)
        ex.add_command(label="Suma y saludo", command=lambda: self.new_editor("ejemplo.asm", EJEMPLO_SUMA))
        ex.add_command(label="Hola mundo", command=lambda: self.new_editor("hola.asm", EJEMPLO_HOLA))
        ex.add_command(label="División Q7.8 (programa + módulo)", command=self.open_division_example)
        f.add_cascade(label="Ejemplos", menu=ex)
        f.add_separator()
        f.add_command(label="Salir", command=self.on_close)
        bar.add_cascade(label="Archivo", menu=f)

        p = tk.Menu(bar, tearoff=False)
        p.add_command(label="Ensamblar", accelerator="F7", command=self.cmd_assemble)
        p.add_command(label="Ejecutar", accelerator="F5", command=self.cmd_run)
        p.add_command(label="Un paso", accelerator="F10", command=self.cmd_step)
        p.add_command(label="Detener", accelerator="Mayús+F5", command=self.cmd_stop)
        p.add_command(label="Reiniciar", accelerator="F6", command=self.cmd_reset)
        p.add_command(label="Límite de instrucciones por ejecución...", command=self.cmd_set_limit)
        sp = tk.Menu(p, tearoff=False)
        for v in SPEEDS:
            sp.add_radiobutton(label=self.speed_label(v), variable=self.speed, value=v, command=self.on_speed_changed)
        p.add_cascade(label="Velocidad de ejecución", menu=sp)
        p.add_separator()
        p.add_command(label="Punto de parada en esta línea", accelerator="F9", command=self.cmd_toggle_bp)
        p.add_command(label="Quitar todos los puntos de parada", command=self.cmd_clear_bps)
        p.add_separator()
        p.add_command(label="Exportar imagen (.hex .bin .dec .bits)...", command=self.cmd_export)
        p.add_command(label="Abrir imagen y simular...", command=self.cmd_open_image)
        bar.add_cascade(label="Programa", menu=p)

        v = tk.Menu(bar, tearoff=False)
        v.add_command(label="Letra más grande", accelerator="Ctrl++", command=lambda: self.zoom(1))
        v.add_command(label="Letra más chica", accelerator="Ctrl+-", command=lambda: self.zoom(-1))
        v.add_separator()
        v.add_checkbutton(label="Lista de archivos", accelerator="Ctrl+B", variable=self.show_files,
                          command=lambda: self.set_files_panel(self.show_files.get()))
        v.add_command(label="Archivo siguiente", accelerator="Ctrl+Tab", command=lambda: self.cmd_file_step(1))
        v.add_command(label="Archivo anterior", accelerator="Ctrl+Mayús+Tab", command=lambda: self.cmd_file_step(-1))
        bar.add_cascade(label="Ver", menu=v)

        h = tk.Menu(bar, tearoff=False)
        h.add_command(label="Referencia de instrucciones", command=lambda: self.show_text("Referencia LC10", REFERENCIA))
        h.add_command(label="Atajos de teclado", command=lambda: self.show_text("Atajos", ATAJOS))
        h.add_separator()
        h.add_command(label="Acerca de", command=self.cmd_about)
        bar.add_cascade(label="Ayuda", menu=h)
        r.configure(menu=bar)

    # --------------------------------------------------------------- interfaz
    def _build_ui(self) -> None:
        r = self.root
        bar = tk.Frame(r, bg=T["bg"])
        bar.pack(side="top", fill="x", padx=8, pady=(8, 4))
        self.btn = {}
        for key, text, cmd, style in (("asm", "Ensamblar", self.cmd_assemble, "TButton"),
                                      ("run", "▶  Ejecutar", self.cmd_run, "Run.TButton"),
                                      ("step", "⤵  Paso", self.cmd_step, "TButton"),
                                      ("stop", "■  Detener", self.cmd_stop, "TButton"),
                                      ("reset", "↺  Reiniciar", self.cmd_reset, "TButton")):
            b = ttk.Button(bar, text=text, command=cmd, style=style)
            b.pack(side="left", padx=(0, 6))
            self.btn[key] = b
        self.input_var = tk.StringVar()
        ttk.Entry(bar, textvariable=self.input_var, width=22).pack(side="right")
        tk.Label(bar, text="Entrada (GETC / IN):", bg=T["bg"], fg=T["muted"]).pack(side="right", padx=(0, 6))

        self.statusbar = tk.Frame(r, bg=T["bg"])
        self.statusbar.pack(side="bottom", fill="x", padx=10, pady=(2, 6))
        self.status_var = tk.StringVar()
        self.status_lbl = tk.Label(self.statusbar, textvariable=self.status_var, bg=T["bg"], fg=T["muted"], anchor="w")
        self.status_lbl.pack(side="left", fill="x", expand=True)
        self.counter_var = tk.StringVar(value="")
        tk.Label(self.statusbar, textvariable=self.counter_var, bg=T["bg"], fg=T["muted"]).pack(side="right")

        self.vpaned = ttk.PanedWindow(r, orient="vertical")
        self.vpaned.pack(fill="both", expand=True, padx=8, pady=(0, 2))
        self.hpaned = ttk.PanedWindow(self.vpaned, orient="horizontal")
        left = tk.Frame(self.hpaned, bg=T["bg"])
        self._build_filebar(left)
        self.editor_split = ttk.PanedWindow(left, orient="horizontal")      # [lista de archivos] | pestañas
        self.editor_split.pack(side="top", fill="both", expand=True)
        self.notebook = ttk.Notebook(self.editor_split)
        self.notebook.bind("<<NotebookTabChanged>>", lambda e: self._on_editor_tab_changed())
        self.editor_split.add(self.notebook, weight=1)
        self._build_files_panel()
        right = tk.Frame(self.hpaned, bg=T["bg"])
        self.regs = RegisterPanel(right, self)
        self.regs.pack(fill="x", padx=(6, 0))
        self.mem = MemoryPanel(right, self)
        self.mem.pack(fill="both", expand=True, padx=(6, 0), pady=(8, 0))
        self.hpaned.add(left, weight=3)
        self.hpaned.add(right, weight=2)

        self.bottom = ttk.Notebook(self.vpaned)
        self.console = Viewer(self.bottom, self.mono, wrap="word")
        self.console.text.tag_configure("sys", foreground=T["muted"], font=ui_font(9, "normal", "italic"))
        self.console.text.tag_configure("bad", foreground=T["err"])
        self.messages = Viewer(self.bottom, self.mono, wrap="none")
        self.messages.text.tag_configure("ok", foreground=T["ok"], font=self.mono_bold)
        self.messages.text.tag_configure("bad", foreground=T["err"], font=self.mono_bold)
        self.listing = Viewer(self.bottom, self.mono)
        self.listing.text.tag_configure("pc", background=T["pc_bg"])
        self.symbols = Viewer(self.bottom, self.mono)
        self.metrics = Viewer(self.bottom, self.mono)
        trace_box = tk.Frame(self.bottom, bg=T["panel"])
        self.trace_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(trace_box, text="Registrar traza de ejecución (más lento; se guardan las últimas 5000)",
                        variable=self.trace_var, command=self.on_trace_toggle).pack(anchor="w", padx=8, pady=(6, 0))
        self.trace = Viewer(trace_box, self.mono)
        self.trace.pack(fill="both", expand=True)
        for w, name in ((self.console, "Consola"), (self.messages, "Mensajes"), (self.listing, "Listado"),
                        (self.symbols, "Símbolos"), (self.metrics, "Métricas"), (trace_box, "Traza")):
            self.bottom.add(w, text=name)
        self.bottom.bind("<<NotebookTabChanged>>", lambda e: self.refresh_bottom_tab())
        self.vpaned.add(self.hpaned, weight=4)
        self.vpaned.add(self.bottom, weight=2)

    def _place_sashes(self) -> None:
        self._sash_job = None
        self.root.update_idletasks()
        try:
            self.hpaned.sashpos(0, int(self.hpaned.winfo_width() * 0.60))
            self.vpaned.sashpos(0, int(self.vpaned.winfo_height() * 0.70))
        except tk.TclError:
            pass

    def _bind_keys(self) -> None:
        r = self.root
        for seq, fn in (("<F7>", self.cmd_assemble), ("<F5>", self.cmd_run), ("<F10>", self.cmd_step),
                        ("<Shift-F5>", self.cmd_stop), ("<F6>", self.cmd_reset), ("<F9>", self.cmd_toggle_bp),
                        ("<Control-s>", self.cmd_save), ("<Control-o>", self.cmd_open), ("<Control-n>", self.cmd_new),
                        ("<Control-w>", self.cmd_close_tab)):
            r.bind_all(seq, lambda e, fn=fn: (fn(), "break")[1])
        for seq, fn in self.nav_bindings():                # los Text de Tk usan estas teclas (Emacs): se las pisa
            try:
                r.bind_all(seq, fn)
                r.bind_class("Text", seq, fn)
            except tk.TclError:                            # una tecla que este Tk no conoce
                pass
        for seq, d in (("<Control-plus>", 1), ("<Control-equal>", 1), ("<Control-minus>", -1), ("<Control-KP_Add>", 1),
                       ("<Control-KP_Subtract>", -1)):
            r.bind_all(seq, lambda e, d=d: (self.zoom(d), "break")[1])

    # ------------------------------------------------------------------ pestañas
    def current_editor(self) -> CodeEditor | None:
        sel = self.notebook.select()
        return self.root.nametowidget(sel) if sel else None

    def editor_by_name(self, name: str) -> CodeEditor | None:
        return next((e for e in self.editors if e.name == name), None)

    def unique_name(self, name: str) -> str:
        names = {e.name.lower() for e in self.editors}
        if name.lower() not in names:
            return name
        stem, ext = Path(name).stem, Path(name).suffix
        n = 2
        while f"{stem}{n}{ext}".lower() in names:
            n += 1
        return f"{stem}{n}{ext}"

    def new_editor(self, name: str, text: str = "", path: Path | None = None) -> CodeEditor:
        name = self.unique_name(name)
        ed = CodeEditor(self.notebook, self, name, text, path)
        self.editors.append(ed)
        if self.main_editor is None:
            self.main_editor = ed
        self.notebook.add(ed, text=name)
        self.notebook.select(ed)
        self.mark_stale()
        self.update_all_titles()
        if len(self.editors) > AUTO_LIST_FROM and not self._files_auto_done:
            self.set_files_panel(True)
        return ed

    def tab_title(self, ed: CodeEditor) -> str:
        star = "★ " if ed is self.main_editor and len(self.editors) > 1 else ""
        return f"{star}{ed.name}{' ●' if ed.modified else ''}"

    def update_tab_title(self, ed: CodeEditor) -> None:
        self.notebook.tab(ed, text=self.tab_title(ed))
        self.update_nav()

    def update_all_titles(self) -> None:
        for e in self.editors:
            self.notebook.tab(e, text=self.tab_title(e))
        self.update_nav()

    def on_source_changed(self, ed: CodeEditor) -> None:
        self.mark_stale()

    def mark_stale(self) -> None:
        self.stale = True
        if not self.running and self.session.state != "empty" and self.origin == "source":
            self.status("El código cambió: se reensamblará al ejecutar.")

    def _on_editor_tab_changed(self) -> None:
        self.update_nav()

    # ------------------------------------------------- orientarse entre muchos archivos
    def _build_filebar(self, parent) -> None:
        """Franja sobre el editor: ☰ lista · ◀ anterior · nombre del archivo y posición · siguiente ▶."""
        bar = tk.Frame(parent, bg=T["bg"])
        bar.pack(side="top", fill="x", pady=(0, 4))
        self.filebar = bar
        self.btn_files = ttk.Button(bar, text="☰  Archivos", style="Nav.TButton", command=self.toggle_files_panel)
        self.btn_files.pack(side="left", padx=(0, 8))
        self.btn_prev = ttk.Button(bar, style="Nav.TButton", width=NAME_SHORT + 4,
                                   command=lambda: self.cmd_file_step(-1))
        self.btn_prev.pack(side="left")
        self.btn_next = ttk.Button(bar, style="Nav.TButton", width=NAME_SHORT + 4,
                                   command=lambda: self.cmd_file_step(1))
        self.btn_next.pack(side="right")
        mid = tk.Frame(bar, bg=T["bg"])
        mid.pack(side="left", expand=True)
        self.file_name_var = tk.StringVar()
        self.file_info_var = tk.StringVar()
        tk.Label(mid, textvariable=self.file_name_var, bg=T["bg"], fg=T["fg"], font=ui_font(10, "bold")).pack(side="left")
        tk.Label(mid, textvariable=self.file_info_var, bg=T["bg"], fg=T["muted"]).pack(side="left", padx=(8, 0))

    def _build_files_panel(self) -> None:
        """Lista de los archivos abiertos con buscador. No se agrega a la ventana hasta set_files_panel(True)."""
        p = tk.Frame(self.editor_split, bg=T["bg"])
        self.files_panel = p
        self.files_head_var = tk.StringVar()
        tk.Label(p, textvariable=self.files_head_var, bg=T["bg"], fg=T["muted"], anchor="w",
                 font=ui_font(9, "bold")).pack(fill="x", padx=2)
        row = tk.Frame(p, bg=T["bg"])
        row.pack(fill="x", pady=(2, 4))
        tk.Label(row, text="Buscar:", bg=T["bg"], fg=T["muted"]).pack(side="left", padx=(2, 4))
        self.file_filter = tk.StringVar()
        self.file_filter.trace_add("write", lambda *_: self.refresh_file_list())
        self.file_filter_entry = ttk.Entry(row, textvariable=self.file_filter, width=12)
        self.file_filter_entry.pack(side="left", fill="x", expand=True)
        body = tk.Frame(p, bg=T["panel"], highlightthickness=1, highlightbackground=T["border"])
        body.pack(fill="both", expand=True)
        self.file_list = tk.Listbox(body, width=26, activestyle="none", exportselection=False, relief="flat", bd=0,
                                    highlightthickness=0, bg=T["panel"], fg=T["fg"], selectbackground=T["sel"],
                                    selectforeground=T["fg"], font=ui_font(10))
        sb = ttk.Scrollbar(body, orient="vertical", command=self.file_list.yview)
        self.file_list.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.file_list.pack(side="left", fill="both", expand=True)
        self.file_list.bind("<<ListboxSelect>>", self._on_file_pick)
        self.file_list.bind("<Return>", lambda e: (self._focus_editor(), "break")[1])
        self.file_list.bind("<Double-Button-1>", lambda e: self._focus_editor())
        self.file_filter_entry.bind("<Return>", self._on_filter_enter)
        self.file_filter_entry.bind("<Down>", self._on_filter_down)
        self.file_filter_entry.bind("<Escape>", lambda e: (self.file_filter.set(""), "break")[1])

    def nav_bindings(self) -> list:
        """(secuencia, función) de las teclas de archivo siguiente / anterior y de la lista de archivos."""
        out = [(seq, lambda e, d=d: (self.cmd_file_step(d), "break")[1]) for seq, d in NAV_KEYS]
        out.append(("<Control-b>", lambda e: (self.toggle_files_panel(), "break")[1]))
        return out

    def cmd_file_step(self, d: int) -> None:
        """Pasa al archivo siguiente (d=1) o anterior (d=-1); del último se vuelve al primero."""
        n = len(self.editors)
        if n < 2:
            return
        cur = self.current_editor()
        i = self.editors.index(cur) if cur in self.editors else 0
        ed = self.editors[(i + d) % n]
        self.notebook.select(ed)
        ed.text.focus_set()                    # si no, lo que se escriba iría al editor que quedó oculto

    def update_nav(self) -> None:
        """Pone al día la franja, el título de la ventana y la lista con el archivo que está a la vista."""
        if not hasattr(self, "file_name_var"):
            return
        try:
            ed = self.current_editor()
        except tk.TclError:                    # la ventana se está cerrando
            return
        n = len(self.editors)
        if ed is None or ed not in self.editors:
            self.file_name_var.set("")
            self.file_info_var.set("")
            self.root.title(BASE_TITLE)
            for b, t in ((self.btn_prev, "◀"), (self.btn_next, "▶")):
                b.configure(text=t)
                b.state(["disabled"])
        else:
            i = self.editors.index(ed)
            main = ed is self.main_editor
            star = "★ " if main and n > 1 else ""
            self.file_name_var.set(f"{star}{ed.name}{' ●' if ed.modified else ''}")
            self.file_info_var.set(f"{'programa principal' if main else 'módulo'} · {i + 1} de {n}" if n > 1 else "")
            if n > 1:
                self.btn_prev.configure(text="◀  " + short_name(self.editors[(i - 1) % n].name))
                self.btn_next.configure(text=short_name(self.editors[(i + 1) % n].name) + "  ▶")
                self.btn_prev.state(["!disabled"])
                self.btn_next.state(["!disabled"])
            else:
                for b, t in ((self.btn_prev, "◀"), (self.btn_next, "▶")):
                    b.configure(text=t)
                    b.state(["disabled"])
            pos = f" ({i + 1} de {n})" if n > 1 else ""
            self.root.title(f"{ed.name}{pos} — {BASE_TITLE}")
        self.refresh_file_list()

    def refresh_file_list(self) -> None:
        if not hasattr(self, "file_list"):
            return
        q = self.file_filter.get().strip().lower()
        shown = [e for e in self.editors if q in e.name.lower()]
        labels = [self.tab_title(e) for e in shown]
        sig = (tuple(shown), tuple(labels))
        lb = self.file_list
        if sig != self._file_sig:
            self._file_sig = sig
            self._list_editors = shown
            lb.delete(0, "end")
            for t in labels:
                lb.insert("end", t)
        total = len(self.editors)
        self.files_head_var.set(f"ARCHIVOS · {total}" if not q else f"ARCHIVOS · {len(shown)} de {total}")
        lb.selection_clear(0, "end")
        try:
            cur = self.current_editor()
        except tk.TclError:
            return
        if cur in shown:
            i = shown.index(cur)
            lb.selection_set(i)
            lb.see(i)

    def _on_file_pick(self, _e=None) -> None:
        sel = self.file_list.curselection()
        if sel and sel[0] < len(self._list_editors):
            ed = self._list_editors[sel[0]]
            if ed is not self.current_editor():
                self.notebook.select(ed)

    def _on_filter_enter(self, _e=None):
        if self._list_editors:
            self.notebook.select(self._list_editors[0])
            self._focus_editor()
        return "break"

    def _on_filter_down(self, _e=None):
        lb = self.file_list
        lb.focus_set()
        if self._list_editors and not lb.curselection():
            lb.selection_set(0)
            self._on_file_pick()
        return "break"

    def _focus_editor(self) -> None:
        ed = self.current_editor()
        if ed:
            ed.text.focus_set()

    def toggle_files_panel(self) -> None:
        self.set_files_panel(not self._files_shown)

    def set_files_panel(self, show: bool) -> None:
        show = bool(show)
        self._files_auto_done = True           # elegido a mano o mostrado solo: no se vuelve a decidir por el usuario
        self.show_files.set(show)
        if show == self._files_shown:
            return
        self._files_shown = show
        if show:
            self.editor_split.insert(0, self.files_panel, weight=0)
            self.refresh_file_list()
            self.root.after_idle(self._place_files_sash)
        else:
            self.editor_split.forget(self.files_panel)
            self._focus_editor()

    def _place_files_sash(self) -> None:
        try:
            self.root.update_idletasks()
            self.editor_split.sashpos(0, max(170, self.files_panel.winfo_reqwidth()))
        except tk.TclError:
            pass

    def cmd_new(self) -> None:
        if self.main_editor is None:
            self.new_editor("sin_titulo.asm", PLANTILLA_PRINCIPAL)
        else:
            self.new_editor("modulo.asm", PLANTILLA_MODULO)

    def cmd_open(self) -> None:
        paths = filedialog.askopenfilenames(parent=self.root, title="Abrir", filetypes=ASM_TYPES)
        if paths:
            self.open_paths([Path(p) for p in paths])

    def open_paths(self, paths: list[Path]) -> None:
        for p in paths:
            for e in self.editors:
                if e.path and e.path.resolve() == p.resolve():
                    self.notebook.select(e)
                    break
            else:
                try:
                    text = p.read_text(encoding="utf-8", errors="replace")
                except OSError as err:
                    messagebox.showerror("No se pudo abrir", f"{p}\n\n{err}", parent=self.root)
                    continue
                self.new_editor(p.name, text, p)

    def open_division_example(self) -> None:
        base = Path(__file__).resolve().parent.parent / "asm"
        files = [base / "main_division.asm", base / "division.asm"]
        if not all(f.exists() for f in files):
            messagebox.showinfo("Ejemplo no disponible", f"No se encontraron los archivos en {base}", parent=self.root)
            return
        for e in list(self.editors):                       # el ejemplo reemplaza lo que haya (si no hay cambios sin guardar)
            if e.modified:
                messagebox.showinfo("Hay cambios sin guardar", "Guarde o cierre las pestañas modificadas antes de abrir este ejemplo.", parent=self.root)
                return
        for e in list(self.editors):
            self.close_editor(e, ask=False)
        self.main_editor = None
        self.open_paths(files)
        self.mark_stale()
        self.update_all_titles()

    def cmd_open_benchmark(self) -> None:
        """Abre el benchmark del curso: main_grupo27.asm (principal) y todos los módulos de asm/opt10."""
        main = BENCHMARK_DIR / BENCHMARK_MAIN
        if not main.exists():
            messagebox.showinfo("Benchmark no disponible", f"No se encontró {main}", parent=self.root)
            return
        if any(e.modified for e in self.editors):
            messagebox.showinfo("Hay cambios sin guardar",
                                "Guarde o cierre las pestañas modificadas antes de abrir el benchmark.", parent=self.root)
            return
        mods = sorted((p for p in BENCHMARK_DIR.glob("*.asm") if p.name.lower() != BENCHMARK_MAIN.lower()),
                      key=lambda p: p.name.lower())
        self._stop_running()
        for e in list(self.editors):                       # el benchmark reemplaza lo que haya
            self.close_editor(e, ask=False)
        self.main_editor = None
        self.open_paths([main] + mods)                     # el primero que se abre es el programa principal
        ed = self.editor_by_name(BENCHMARK_MAIN)
        if ed:
            self.main_editor = ed
            self.notebook.select(ed)
        self.mark_stale()
        self.update_all_titles()
        self.status(f"Benchmark abierto: {BENCHMARK_MAIN} (principal) y {len(mods)} módulos. "
                    "F7 ensambla, F5 ejecuta.")

    def cmd_save(self, as_new: bool = False) -> None:
        ed = self.current_editor()
        if ed:
            self.save_editor(ed, as_new)

    def save_editor(self, ed: CodeEditor, as_new: bool = False) -> bool:
        path = ed.path
        if as_new or path is None:
            p = filedialog.asksaveasfilename(parent=self.root, title="Guardar", defaultextension=".asm",
                                             initialfile=ed.name, filetypes=ASM_TYPES)
            if not p:
                return False
            path = Path(p)
        try:
            Path(path).write_text(ed.get_text(), encoding="utf-8")
        except OSError as err:
            messagebox.showerror("No se pudo guardar", f"{path}\n\n{err}", parent=self.root)
            return False
        ed.path = Path(path)
        if ed.path.name != ed.name and self.editor_by_name(ed.path.name) in (None, ed):
            ed.name = ed.path.name
            self.mark_stale()
        ed.set_modified(False)
        self.update_tab_title(ed)
        self.status(f"Guardado: {ed.path}")
        return True

    def cmd_close_tab(self) -> None:
        ed = self.current_editor()
        if ed:
            self.close_editor(ed)

    def close_editor(self, ed: CodeEditor, ask: bool = True) -> bool:
        if ask and ed.modified:
            ans = messagebox.askyesnocancel("Cerrar", f"¿Guardar los cambios de {ed.name}?", parent=self.root)
            if ans is None or (ans and not self.save_editor(ed)):
                return False
        self.notebook.forget(ed)
        self.editors.remove(ed)
        ed.destroy()
        if ed is self.main_editor:
            self.main_editor = self.editors[0] if self.editors else None
        self.mark_stale()
        self.update_all_titles()
        return True

    def cmd_make_main(self) -> None:
        ed = self.current_editor()
        if ed:
            self.main_editor = ed
            self.mark_stale()
            self.update_all_titles()
            self.status(f"{ed.name} es ahora el programa principal.")

    def on_close(self) -> None:
        for e in list(self.editors):
            if e.modified and not self.close_editor(e):
                return
        self._stop_running()
        self.cancel_pending()
        self.root.destroy()

    def cancel_pending(self) -> None:
        if getattr(self, "_sash_job", None) is not None:
            self.root.after_cancel(self._sash_job)
            self._sash_job = None
        for e in self.editors:
            e.destroy_jobs()

    # --------------------------------------------------------------- utilidades
    def status(self, text: str, error: bool = False) -> None:
        self.status_var.set(text)
        self.status_lbl.configure(fg=T["err"] if error else T["muted"])

    def input_text(self) -> str:
        return parse_input_escapes(self.input_var.get())

    def sources(self) -> list[tuple[str, str]]:
        order = ([self.main_editor] if self.main_editor else []) + [e for e in self.editors if e is not self.main_editor]
        return [(e.name, e.get_text()) for e in order]

    def all_breakpoints(self) -> set[tuple[str, int]]:
        return {(e.name, ln) for e in self.editors for ln in e.breakpoint_lines()}

    def resolve_address(self, text: str) -> int:
        t = text.strip()
        if not t:
            raise ValueError("Escriba una dirección (x3000, 12288) o el nombre de una etiqueta.")
        v = parse_number(t)
        if v is not None:
            return v & 0xFFFF
        syms = self.session.asm.symbols if self.session.asm else {}
        key = t.upper()
        if key in syms:
            return syms[key]
        found = [a for k, a in syms.items() if k.endswith("-" + key)]
        if len(found) == 1:
            return found[0]
        raise ValueError(f"No es un número ni una etiqueta conocida: {t}")

    def zoom(self, d: int) -> None:
        self.font_size = max(7, min(28, self.font_size + d))
        self.mono.configure(size=self.font_size)
        self.mono_bold.configure(size=self.font_size)
        for e in self.editors:
            e.update_metrics()

    def show_text(self, title: str, content: str) -> None:
        win = tk.Toplevel(self.root)
        win.title(title)
        win.configure(bg=T["panel"])
        v = Viewer(win, self.mono)
        v.pack(fill="both", expand=True)
        v.set(content)
        win.geometry("860x460")

    def cmd_about(self) -> None:
        messagebox.showinfo("LC10", "LC10: ISA del Grupo 10 (Laboratorio 3c)\nArquitectura de Computadoras, UNaM\n\n"
                            "Esta ventana usa el mismo ensamblador y simulador que la línea de comandos.\n"
                            "Instrucciones de uso: INSTRUCTIVO.md", parent=self.root)

    # ------------------------------------------------------------- ensamblar
    def cmd_assemble(self) -> None:
        self.assemble(then="messages")

    def assemble(self, then: str = "console") -> bool:
        self._stop_running()
        for e in self.editors:
            e.set_error_line(None)
        self.messages.clear()
        try:
            res = self.session.assemble(self.sources(), self.input_text())
        except AsmError as err:
            self.show_error(err)
            return False
        self.stale, self.origin, self.snap = False, "source", None
        self.console.clear()
        self.messages.append("✔ Ensamblado sin errores\n", "ok")
        img = res.image
        self.messages.append(f"  Origen x{img.origin:04X} · {len(img.data)} bytes ({len(img.data) // 2} palabras)"
                             f" · relleno {res.pad_bytes} byte(s)\n\n")
        for name, base, size in res.modules:
            self.messages.append(f"  {name:<20} x{base:04X}   {size} bytes\n")
        self.after_load()
        self.status(f"Ensamblado: {len(img.data)} bytes desde x{img.origin:04X}.")
        if then == "messages":
            self.bottom.select(self.messages)
        return True

    def show_error(self, err: AsmError) -> None:
        self.messages.append("✖ Error de ensamblado\n", "bad")
        where = f"{err.file}:{err.line}" if err.file and err.line else (err.file or "")
        t = self.messages.text
        t.configure(state="normal")
        if where:
            tag = f"link{id(err)}"
            t.tag_configure(tag, foreground=T["accent"], underline=True)
            t.tag_bind(tag, "<Button-1>", lambda e, f=err.file, ln=err.line: self.goto(f, ln))
            t.tag_bind(tag, "<Enter>", lambda e: t.configure(cursor="hand2"))
            t.tag_bind(tag, "<Leave>", lambda e: t.configure(cursor=""))
            t.insert("end", "  " + where, tag)
            t.insert("end", f": {err.msg}\n")
        else:
            t.insert("end", f"  {err.msg}\n")
        t.configure(state="disabled")
        self.bottom.select(self.messages)
        self.status(f"Error de ensamblado: {err}", error=True)
        if err.file and err.line:
            self.goto(err.file, err.line, error=True)

    def goto(self, file: str, line: int, error: bool = False) -> None:
        ed = self.editor_by_name(file)
        if not ed or not line:
            return
        self.notebook.select(ed)
        if error:
            ed.set_error_line(line)
        ed.goto(line)

    def after_load(self) -> None:
        s = self.session
        self.listing.set("\n".join(s.listing_lines))
        self.symbols.set(s.symbols_text())
        self.mem.follow.set(True)
        self.mem.set_base(s.image.origin)
        self.mem.last_changed = set()
        self.refresh()

    # ------------------------------------------------------------- ejecución
    def ensure_ready(self) -> bool:
        if self.origin == "image" and self.session.state != "empty":
            return True
        if self.session.state == "empty" or self.stale:
            return self.assemble()
        return True

    def cmd_run(self) -> None:
        if self.running or not self.ensure_ready():
            return
        s = self.session
        if s.state in ("halted", "fault"):
            self.restart()
        self.snap = s.snapshot()
        self.bp_addrs = s.breakpoint_addrs(self.all_breakpoints()) if self.origin == "source" else set()
        self.run_limit = s.machine.count + self.max_run if self.max_run > 0 else None
        self.running = True
        self._resumed = False
        self._credit, self._last_t = 1.0, time.perf_counter()     # la primera instrucción sale sin esperar
        self.refresh_buttons()
        self.status(self.running_status())
        self.bottom.select(self.console)
        self._tick()

    def _tick(self) -> None:
        self._job = None
        if not self.running:
            return
        s = self.session
        rate = self.speed.get()
        if rate <= 0:                                          # lo más rápido posible
            r = s.run_chunk(self.bp_addrs, budget_s=0.03, limit=self.run_limit, check_first=self._resumed)
            self._resumed = True
            self.console.append(s.take_output())
            if r == "running":
                self.regs.update(s.machine)
                self.counter_var.set(self.session.summary())
                self._job = self.root.after(1, self._tick)
                return
        else:                                                  # a lo sumo `rate` instrucciones por segundo
            now = time.perf_counter()
            self._credit = min(self._credit + (now - self._last_t) * rate, max(1.0, rate * BURST_S))
            self._last_t = now
            n = int(self._credit)
            if n < 1:                                          # todavía no toca: esperar lo que falta
                self._job = self.root.after(self._wait_ms(rate), self._tick)
                return
            before = s.machine.count
            self.snap = s.snapshot()
            r = s.run_chunk(self.bp_addrs, budget_s=0.03, limit=self.run_limit, max_steps=n,
                            check_first=self._resumed)
            self._resumed = True
            self._credit -= s.machine.count - before
            self.console.append(s.take_output())
            if r == "running":                                 # se ve avanzar la línea, los registros y la memoria
                self.refresh(change=s.diff(self.snap))
                self._job = self.root.after(self._wait_ms(rate), self._tick)
                return
        self.running = False
        self.on_stopped(r)

    def _wait_ms(self, rate: int) -> int:
        """Cuánto esperar hasta que el regulador permita la próxima instrucción (entre 1 y 20 ms)."""
        missing = max(0.0, 1.0 - self._credit) / rate
        return max(1, min(20, int(missing * 1000 + 0.999)))

    @staticmethod
    def speed_label(v: int) -> str:
        return "Sin límite (lo más rápido posible)" if v <= 0 else f"{fmt_int(v)} instrucciones por segundo como máximo"

    def running_status(self) -> str:
        v = self.speed.get()
        return "Ejecutando..." if v <= 0 else f"Ejecutando a {fmt_int(v)} instrucciones por segundo como máximo..."

    def on_speed_changed(self) -> None:
        v = self.speed.get()
        if self.running:
            self.status(self.running_status())
        else:
            self.status("Velocidad: sin límite." if v <= 0
                        else f"Velocidad: como máximo {fmt_int(v)} instrucciones por segundo (F5).")

    def _stop_running(self) -> None:
        if self._job is not None:
            self.root.after_cancel(self._job)
            self._job = None
        was = self.running
        self.running = False
        if was:
            self.refresh_buttons()

    def cmd_stop(self) -> None:
        if self.running:
            self._stop_running()
            self.on_stopped("paused")

    def cmd_set_limit(self) -> None:
        n = simpledialog.askinteger(
            "Límite de instrucciones",
            "Cantidad máxima de instrucciones por cada pulsación de Ejecutar (F5).\n"
            "Si se alcanza sin llegar a HALT, el programa se detiene y F5 sigue otro tanto.\n"
            "0 = sin límite.",
            parent=self.root, initialvalue=self.max_run, minvalue=0, maxvalue=10**12)
        if n is not None:
            self.max_run = n
            self.status("Sin límite de instrucciones por ejecución." if n == 0
                        else f"Límite: {n} instrucciones por ejecución (F5).")

    def cmd_step(self) -> None:
        if self.running or not self.ensure_ready():
            return
        s = self.session
        if s.state in ("halted", "fault"):
            self.status("El programa ya terminó. Reinicie (F6) para volver a empezar.")
            return
        self.snap = s.snapshot()
        r = s.step()
        self.console.append(s.take_output())
        if r == "ready":
            self.refresh(change=s.diff(self.snap))
            self.status(self.step_status())
        else:
            self.on_stopped(r)

    def step_status(self) -> str:
        loc = self.session.pc_location()
        where = f"  ·  siguiente: línea {loc[1]} de {loc[0]}" if loc else ""
        return f"Paso ejecutado{where}"

    def on_stopped(self, reason: str) -> None:
        s = self.session
        self.refresh(change=s.diff(self.snap) if self.snap else None)
        self.refresh_buttons()
        n = s.machine.count
        desglose = f" ({s.machine.user_count} usuario + {s.machine.os_count} SO)" if s.machine.os_count else ""
        if reason == "halted":
            self._console_note(f"[Programa terminado: {n} instrucciones{desglose}]")
            self.status(f"Terminó (HALT) tras {n} instrucciones{desglose}.")
        elif reason == "fault":
            self._console_note(f"[EXCEPCIÓN: {s.message}]", bad=True)
            self.status(f"EXCEPCIÓN: {s.message}", error=True)
        elif reason == "limit":
            self._console_note(f"[Detenido: {self.max_run} instrucciones sin terminar]", bad=True)
            self.status(f"Se alcanzó el límite de {self.max_run} instrucciones sin llegar a HALT (¿bucle infinito?). "
                        f"F5 sigue otras {self.max_run}; F6 reinicia.", error=True)
        elif reason == "breakpoint":
            loc = s.pc_location()
            self.status(f"Punto de parada" + (f" en {loc[0]}:{loc[1]}" if loc else "") + f" (x{s.machine.pc:04X}) tras {n} instrucciones.")
        else:
            self.status(f"Detenido tras {n} instrucciones.")

    def _console_note(self, text: str, bad: bool = False) -> None:
        if not self.console.ends_with_newline():
            self.console.append("\n")
        self.console.append(text + "\n", "bad" if bad else "sys")

    def restart(self) -> None:
        self.session.start(self.input_text())
        self.console.clear()
        self.snap = None

    def cmd_reset(self) -> None:
        self._stop_running()
        if self.origin == "source" and (self.stale or self.session.state == "empty"):
            self.assemble()
            return
        if self.session.state == "empty":
            return
        self.restart()
        self.mem.last_changed = set()
        self.refresh()
        self.status("Reiniciado: el programa vuelve a su primera instrucción.")

    # ------------------------------------------------------- puntos de parada
    def cmd_toggle_bp(self) -> None:
        ed = self.current_editor()
        if ed:
            ed.toggle_breakpoint(int(ed.text.index("insert").split(".")[0]))

    def cmd_clear_bps(self) -> None:
        for e in self.editors:
            e.clear_breakpoints()

    # ---------------------------------------------------------------- imágenes
    def cmd_export(self) -> None:
        if self.origin == "source" and not self.ensure_ready():
            return
        if self.session.image is None:
            self.status("No hay nada para exportar: ensamble primero.", error=True)
            return
        default = (self.main_editor.name if self.main_editor else "programa").rsplit(".", 1)[0]
        p = filedialog.asksaveasfilename(parent=self.root, title="Exportar imagen", defaultextension=".hex",
                                         initialfile=default, filetypes=IMAGE_TYPES)
        if not p:
            return
        fmt = Path(p).suffix.lstrip(".").lower()
        if fmt not in FORMATS:
            messagebox.showerror("Formato", f"Use una de estas extensiones: {', '.join('.' + f for f in FORMATS)}", parent=self.root)
            return
        try:
            self.session.image.save(Path(p), fmt)
        except OSError as err:
            messagebox.showerror("No se pudo guardar", str(err), parent=self.root)
            return
        self.status(f"Imagen guardada: {p}")

    def cmd_open_image(self) -> None:
        p = filedialog.askopenfilename(parent=self.root, title="Abrir imagen", filetypes=IMAGE_TYPES + [("Todos", "*.*")])
        if p:
            self.load_image_path(Path(p))

    def load_image_path(self, p: Path) -> bool:
        self._stop_running()
        try:
            image = Image.load(p)
        except (ImageError, OSError, UnicodeDecodeError) as err:
            messagebox.showerror("Imagen no válida", f"{p}\n\n{err}", parent=self.root)
            return False
        try:
            self.session.load_image(image, self.input_text())
        except ImageError as err:                              # invade la zona del sistema (SO y dispositivos)
            messagebox.showerror("Imagen no válida", f"{p}\n\n{err}", parent=self.root)
            return False
        self.origin, self.image_name, self.snap = "image", p.name, None
        for e in self.editors:
            e.set_pc_line(None)
        self.console.clear()
        self.messages.clear()
        self.messages.append(f"Imagen cargada: {p.name}\n", "ok")
        self.messages.append(f"  Origen x{image.origin:04X} · {len(image.data)} bytes ({len(image.data) // 2} palabras)\n"
                             "  El listado se obtiene desensamblando: los datos pueden verse como instrucciones.\n")
        self.after_load()
        self.status(f"Imagen {p.name} cargada: se simula sin pasar por el fuente (F5 ejecuta, F10 avanza).")
        return True

    # ------------------------------------------------------------ actualización
    def refresh(self, change=None) -> None:
        s = self.session
        m = s.machine
        if m is None:
            self.regs.update(None)
            self.mem.render()
            self.counter_var.set("")
            return
        nxt = ""
        if s.state == "ready":
            w = m.mem[m.pc] | m.mem[(m.pc + 1) & 0xFFFF] << 8
            nxt = isa.disassemble(w, m.pc)
        self.regs.update(m, change.regs if change else (), change.flags if change else (), nxt)
        changed = s.changed_bytes(self.snap, self.mem.base, self.mem.base + self.mem.window) if self.snap else set()
        self.mem.render(changed)
        self.counter_var.set(s.summary())
        self.update_pc_marks()
        self.refresh_bottom_tab()

    def update_pc_marks(self) -> None:
        s = self.session
        for e in self.editors:
            e.set_pc_line(None)
        addr = s.machine.pc if s.state == "ready" else s.last_pc
        loc = s.location_of(addr) if addr is not None else None
        if loc:
            ed = self.editor_by_name(loc[0])
            if ed:
                ed.set_pc_line(loc[1])
                self.notebook.select(ed)
                ed.text.see(f"{loc[1]}.0")
        lt = self.listing.text
        lt.configure(state="normal")
        lt.tag_remove("pc", "1.0", "end")
        idx = s.listing_line_for(addr) if addr is not None else None
        if idx is not None:
            lt.tag_add("pc", f"{idx + 1}.0", f"{idx + 2}.0")
            lt.see(f"{idx + 1}.0")
        lt.configure(state="disabled")

    def refresh_bottom_tab(self) -> None:
        sel = self.bottom.tab(self.bottom.select(), "text")
        if sel == "Métricas":
            self.metrics.set(self.session.metrics_text())
        elif sel == "Traza":
            self.trace.set(self.session.trace_text())
            self.trace.text.see("end")

    def on_trace_toggle(self) -> None:
        self.session.set_trace(self.trace_var.get())
        self.refresh_bottom_tab()

    def refresh_buttons(self) -> None:
        run = self.running
        self.btn["run"].state(["disabled"] if run else ["!disabled"])
        self.btn["step"].state(["disabled"] if run else ["!disabled"])
        self.btn["asm"].state(["disabled"] if run else ["!disabled"])
        self.btn["reset"].state(["!disabled"])
        self.btn["stop"].state(["!disabled"] if run else ["disabled"])


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if sys.platform == "win32":                                # texto nítido en pantallas de alta resolución
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass
    root = tk.Tk()
    w, h = min(1320, root.winfo_screenwidth() - 80), min(840, root.winfo_screenheight() - 100)
    root.geometry(f"{w}x{h}+40+30")
    root.minsize(900, 600)
    App(root, argv)
    root.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
