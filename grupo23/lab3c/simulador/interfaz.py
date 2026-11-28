#!/usr/bin/env python3
"""
Interfaz grafica del simulador de la ISA LOVELACE (Lab 3c, Grupo 23).

Usa el mismo nucleo que simulador.py (clase CPU): las cifras de instrucciones
y memoria son exactamente las mismas que en la linea de comandos.

  * Programa: listado desensamblado con etiquetas; doble clic = punto de parada.
  * Ejecutar / Pausar, Paso (una instruccion; un TRAP cuenta como una),
    Reiniciar, velocidad y "Ejecutar hasta" una etiqueta o direccion.
  * Registros R0-R7, PC, banderas N Z P C V y modo (usuario / SO); los
    registros que cambiaron en el ultimo paso se resaltan.
  * Memoria: palabras desde una direccion o etiqueta, con su texto ASCII; se
    resaltan las palabras escritas en el ultimo paso y se puede seguir la
    ultima escritura (por ejemplo, la pila).
  * Ciclos: el mismo modelo multiciclo de isa_g23/modelo_ciclos.py y del
    informe; Paso muestra los ciclos y las etapas de cada instruccion, y la
    pestana Ciclos los reparte por clase de instruccion.
  * Consola: salida del programa; las teclas que se escriben en ella van al
    teclado del simulador (KBSR/KBDR).
  * Metricas: instrucciones del programa, del SO y total, memoria y
    comparacion con la LC-3; estadisticas por instruccion y por modulo.
  * Verificacion: al terminar el benchmark compara la salida, operacion por
    operacion, con la de la LC-3 (benchmark/salida_referencia_lc3.txt).
  * Abrir: imagen .hex o .bin, o un .asm (se ensambla con ensamblador.py).

Uso:
  python simulador/interfaz.py [programa.hex|.bin|.asm]
  (sin argumento abre benchmark/benchmark_g23.hex)
Requiere Python 3.10 o superior con Tkinter (incluido en Python para Windows).
"""
import os
import subprocess
import sys
import tempfile
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
from isa import KBSR, desensamblar, mnemonico  # noqa: E402
from simulador import CPU, Excepcion, cargar_imagen, cargar_simbolos, perfil_por_modulo  # noqa: E402

LC3_PROGRAMA, LC3_TOTAL, LC3_BYTES = 357_505, 379_579, 15_792   # benchmark definitivo en la LC-3
LC3_CICLOS, LC3_CICLOS_SO = 1_333_071, 101_751                  # mismo modelo de ciclos (modelo_ciclos.py)

# ---- Modelo de ciclos: procesador multiciclo, el mismo de isa_g23/modelo_ciclos.py y del informe.
# Cada instruccion usa solo las etapas que necesita, un ciclo cada una.
CICLOS = {"salto": 3, "alu": 4, "guarda": 4, "carga": 5, "trap": 6, "mul": 19, "div": 20}
ETAPAS = {"salto": "IF ID EX", "alu": "IF ID EX WB", "guarda": "IF ID EX MEM", "carga": "IF ID EX MEM WB",
          "trap": "IF ID + PSR y PC a la pila + vector", "mul": "IF ID 16×EX WB (multiplicador secuencial)",
          "div": "IF ID 17×EX WB (divisor secuencial)", "pila": "IF ID + un MEM por registro + 1"}
NOMBRE_CLASE = {"salto": "Saltos", "alu": "ALU y corrimientos", "guarda": "Guardados", "carga": "Cargas",
                "trap": "TRAP y RTI", "mul": "Multiplicación", "div": "División", "pila": "PUSH y POP"}
CLASE = {}
for _m in ("BR", "BRR", "BRX", "JMP", "RET", "NOP"):
    CLASE[_m] = "salto"
for _m in ("ADD", "ADDI", "SUB", "ADC", "ADDX", "AND", "ANDI", "OR", "XOR", "NOT", "LEA", "LSL", "LSR", "ASR",
           "RLC", "DBP", "JSR", "JSRR"):
    CLASE[_m] = "alu"
for _m in ("ST", "STR", "STB", "STBH"):
    CLASE[_m] = "guarda"
for _m in ("LD", "LDR", "LDB", "LDBH"):
    CLASE[_m] = "carga"
for _m in ("TRAP", "RTI"):
    CLASE[_m] = "trap"
for _m in ("MUL", "MULH", "MULHU"):
    CLASE[_m] = "mul"
for _m in ("DIV", "REM", "DIVU", "REMU"):
    CLASE[_m] = "div"


def secciones(texto):
    """Divide la salida de la calculadora en operaciones: [(titulo, lineas de resultado)]."""
    import re
    partes = re.split(r"(?m)^(==.+?==.*?)\s*$", texto.replace("\r", ""))   # "==LOGARITMO== (CORDIC)"
    res = []
    for i in range(1, len(partes) - 1, 2):
        cuerpo = [x for x in partes[i + 1].split("\n") if x.strip() and x.strip() != "HALT"]
        res.append((" ".join(partes[i].replace("==", " ").split()), cuerpo))
    return res


def buscar_referencia(carpeta):
    """Salida del mismo benchmark en la LC-3 (simulador web), si esta junto al programa."""
    for r in (os.path.join(carpeta, "salida_referencia_lc3.txt"),                       # entrega
              os.path.join(carpeta, "..", "benchmark_lc3", "salida_referencia_web.txt")):  # repositorio
        if os.path.exists(r):
            return r
    return None


def ciclos_de(w):
    """(clase, ciclos) de una instruccion de LOVELACE segun el modelo multiciclo."""
    m = mnemonico(w)
    if m.startswith("BRR"):
        m = "BRR"
    elif m in ("BRC", "BRNC", "BRV", "BRNV", "BRHI", "BRLS"):
        m = "BRX"
    elif m.startswith("BR"):
        m = "BR"
    if m in ("PUSH", "POP"):
        return "pila", 3 + bin(w & 0xFF).count("1")
    clase = CLASE.get(m, "alu")
    return clase, CICLOS[clase]

VELOCIDADES = {             # nombre: (instrucciones del programa por tic, ms entre tics)
    "Lenta (paso a paso visible)": (1, 120),
    "Media": (25, 15),
    "Rápida": (1500, 1),
    "Máxima": (200_000, 1),
}

FONDO, PANEL, BORDE = "#f4f1ea", "#fffdf8", "#d8d1c2"
TINTA, TENUE, ACENTO = "#2b2620", "#7a7163", "#7b2d43"     # bordo: acento LOVELACE
PC_FONDO, PARADA, CAMBIO = "#f3d98b", "#b3261e", "#b3261e"
MOD_FONDO = "#f6d5dc"
OK = "#2e6b3a"
FILAS_MEM = 4                   # lineas de 8 palabras en la vista de memoria
MONO = ("Consolas", 10)


class CPUInterfaz(CPU):
    """CPU del simulador que, si el programa espera una tecla y no hay
    ninguna, corta la ejecucion en ese punto (sin seguir contando el sondeo)."""

    esperando = False
    ultima_escritura = None

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.escritas = set()           # palabras escritas desde la ultima actualizacion de pantalla

    def ww(self, a, v):
        super().ww(a, v)
        a &= 0xFFFE
        if a < 0xFE00:
            self.escritas.add(a)
            self.ultima_escritura = a

    def wb(self, a, v):
        super().wb(a, v)
        a &= 0xFFFE
        self.escritas.add(a)
        self.ultima_escritura = a

    def rw(self, a):
        v = super().rw(a)
        if (a & 0xFFFF) == KBSR and not self.kbd:
            self.esperando = True
            self.max_steps = self.count + self.count_so      # se detiene al terminar la instruccion
        return v


class Interfaz:
    def __init__(self, raiz, ruta=None):
        self.raiz = raiz
        self.ruta = None
        self.imagen = None
        self.sim = {}
        self.map_path = None
        self.cpu = None
        self.corriendo = False
        self.antes = [0] * 8
        self.item_pc = None
        self.out_len = 0
        self.al_terminar = None
        self.referencia = None
        raiz.title("LOVELACE · simulador funcional · Grupo 23")
        raiz.configure(bg=FONDO)
        raiz.geometry("1340x720")
        raiz.minsize(1000, 620)
        try:
            raiz.state("zoomed")            # maximizada en Windows
        except tk.TclError:
            pass
        self._estilos()
        self._armar()
        if ruta:
            self.abrir(ruta)

    # ------------------------------------------------------------ apariencia --
    def _estilos(self):
        s = ttk.Style()
        s.theme_use("clam")
        s.configure(".", background=FONDO, foreground=TINTA, font=("Segoe UI", 10))
        s.configure("Panel.TFrame", background=PANEL)
        s.configure("Panel.TLabel", background=PANEL)
        s.configure("Titulo.TLabel", background=FONDO, foreground=ACENTO, font=("Georgia", 17, "bold"))
        s.configure("Sub.TLabel", background=FONDO, foreground=TENUE)
        s.configure("Seccion.TLabel", background=PANEL, foreground=ACENTO, font=("Segoe UI", 10, "bold"))
        s.configure("Dato.TLabel", background=PANEL, font=("Consolas", 11))
        s.configure("Grande.TLabel", background=PANEL, foreground=TINTA, font=("Segoe UI", 15, "bold"))
        s.configure("Tenue.TLabel", background=PANEL, foreground=TENUE, font=("Segoe UI", 9))
        s.configure("LC3.TLabel", background=PANEL, foreground=ACENTO, font=("Segoe UI", 12, "bold"))
        s.configure("Panel.TCheckbutton", background=PANEL)
        s.configure("TButton", padding=(10, 4))
        s.configure("Acento.TButton", foreground="white", background=ACENTO)
        s.map("Acento.TButton", background=[("active", "#5e2133")])
        s.configure("Treeview", font=MONO, rowheight=20, background=PANEL, fieldbackground=PANEL)
        s.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"))
        s.configure("TNotebook", background=FONDO)
        s.configure("TNotebook.Tab", padding=(12, 4))

    def _panel(self, padre, titulo):
        marco = ttk.Frame(padre, style="Panel.TFrame", padding=(10, 6))
        marco.configure(borderwidth=1, relief="solid")
        ttk.Label(marco, text=titulo, style="Seccion.TLabel").pack(anchor="w", pady=(0, 6))
        return marco

    def _armar(self):
        cab = ttk.Frame(self.raiz, padding=(14, 10, 14, 4))
        cab.pack(fill="x")
        ttk.Label(cab, text="LOVELACE", style="Titulo.TLabel").pack(side="left")
        ttk.Label(cab, text="   ISA de 16 bits del Grupo 23 · homenaje a Ada Lovelace (1843)",
                  style="Sub.TLabel").pack(side="left", pady=(6, 0))
        self.lbl_archivo = ttk.Label(cab, text="", style="Sub.TLabel")
        self.lbl_archivo.pack(side="right", pady=(6, 0))

        barra = ttk.Frame(self.raiz, padding=(14, 4))
        barra.pack(fill="x")
        ttk.Button(barra, text="Abrir…", command=self.dialogo_abrir).pack(side="left")
        ttk.Button(barra, text="Reiniciar", command=self.reiniciar).pack(side="left", padx=(6, 0))
        ttk.Separator(barra, orient="vertical").pack(side="left", fill="y", padx=10)
        self.btn_ejecutar = ttk.Button(barra, text="▶  Ejecutar", style="Acento.TButton",
                                       command=self.alternar)
        self.btn_ejecutar.pack(side="left")
        ttk.Button(barra, text="Paso", command=self.paso).pack(side="left", padx=(6, 0))
        ttk.Button(barra, text="Paso ×10", command=lambda: self.paso(10)).pack(side="left", padx=(6, 0))
        ttk.Label(barra, text="   Velocidad").pack(side="left")
        self.velocidad = tk.StringVar(value="Máxima")
        ttk.Combobox(barra, textvariable=self.velocidad, values=list(VELOCIDADES), state="readonly",
                     width=24).pack(side="left", padx=(6, 0))
        ttk.Separator(barra, orient="vertical").pack(side="left", fill="y", padx=10)
        ttk.Label(barra, text="Ejecutar hasta").pack(side="left")
        self.hasta = tk.StringVar()
        e = ttk.Entry(barra, textvariable=self.hasta, width=18, font=MONO)
        e.pack(side="left", padx=(6, 0))
        e.bind("<Return>", lambda _e: self.ejecutar_hasta())
        ttk.Button(barra, text="Ir", command=self.ejecutar_hasta).pack(side="left", padx=(6, 0))

        self.estado = ttk.Label(self.raiz, text="Abrí un programa (.hex, .bin o .asm).", style="Sub.TLabel",
                                padding=(14, 2, 14, 6))
        self.estado.pack(side="bottom", fill="x")

        cuerpo = ttk.Frame(self.raiz, padding=(14, 6, 14, 6))
        cuerpo.pack(fill="both", expand=True)
        cuerpo.columnconfigure(0, weight=5)
        cuerpo.columnconfigure(1, weight=4, minsize=700)
        cuerpo.rowconfigure(0, weight=1)

        # ---- programa
        p = self._panel(cuerpo, "Programa  (doble clic: punto de parada)")
        p.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        cont = ttk.Frame(p, style="Panel.TFrame")
        cont.pack(fill="both", expand=True)
        self.lista = ttk.Treeview(cont, columns=("bp", "dir", "hex", "etq", "ins"), show="headings",
                                  selectmode="browse")
        for c, t, w, st in (("bp", "", 26, False), ("dir", "Dirección", 80, False), ("hex", "Código", 64, False),
                            ("etq", "Etiqueta", 210, True), ("ins", "Instrucción", 260, True)):
            self.lista.heading(c, text=t, anchor="w")
            self.lista.column(c, width=w, stretch=st, anchor="w")
        self.lista.tag_configure("pc", background=PC_FONDO)
        self.lista.tag_configure("bp", foreground=PARADA)
        sb = ttk.Scrollbar(cont, orient="vertical", command=self.lista.yview)
        self.lista.configure(yscrollcommand=sb.set)
        self.lista.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.lista.bind("<Double-1>", self.alternar_parada)
        self.lista.bind("<<TreeviewSelect>>", self.mostrar_codificacion)
        self.lbl_cod = ttk.Label(p, text="Seleccioná una instrucción para ver su codificación.",
                                 style="Tenue.TLabel", font=("Consolas", 10))
        self.lbl_cod.pack(anchor="w", pady=(6, 0))

        # ---- columna derecha
        der = ttk.Frame(cuerpo)
        der.grid(row=0, column=1, sticky="nsew")
        der.columnconfigure(0, weight=1)
        der.rowconfigure(2, weight=1)

        arriba = ttk.Frame(der)
        arriba.grid(row=0, column=0, sticky="ew")
        arriba.columnconfigure(0, weight=1)
        arriba.columnconfigure(1, weight=1)

        r = self._panel(arriba, "Registros")
        r.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self.lbl_reg = []
        g = ttk.Frame(r, style="Panel.TFrame")
        g.pack(fill="x")
        for i in range(8):
            ttk.Label(g, text=f"R{i}" + (" (SP)" if i == 6 else " (RA)" if i == 7 else ""),
                      style="Tenue.TLabel").grid(row=i % 4, column=2 * (i // 4), sticky="w", padx=(0, 8))
            lb = tk.Label(g, text="x0000", font=("Consolas", 11), bg=PANEL, fg=TINTA, anchor="w")
            lb.grid(row=i % 4, column=2 * (i // 4) + 1, sticky="w", padx=(0, 14))
            self.lbl_reg.append(lb)
        self.lbl_pc = ttk.Label(r, text="PC  x0000", style="Dato.TLabel")
        self.lbl_pc.pack(anchor="w", pady=(6, 0))
        self.lbl_flags = tk.Label(r, text="", font=("Consolas", 11), bg=PANEL, fg=TINTA, anchor="w")
        self.lbl_flags.pack(anchor="w")
        self.lbl_modo = ttk.Label(r, text="", style="Tenue.TLabel")
        self.lbl_modo.pack(anchor="w")

        m = self._panel(arriba, "Métricas")
        m.grid(row=0, column=1, sticky="nsew")
        self.met = {}
        m.columnconfigure(0, weight=1)
        m.columnconfigure(1, weight=1)
        cuadro = ttk.Frame(m, style="Panel.TFrame")
        cuadro.pack(fill="x")
        cuadro.columnconfigure(0, weight=1)
        cuadro.columnconfigure(1, weight=1)
        for n, (clave, titulo) in enumerate((("prog", "Instrucciones (programa)"),
                                             ("cic", "Ciclos (programa)"),
                                             ("so", "SO · total"), ("cicso", "Ciclos del SO · CPI"))):
            celda = ttk.Frame(cuadro, style="Panel.TFrame")
            celda.grid(row=n // 2, column=n % 2, sticky="w", padx=(0, 10))
            ttk.Label(celda, text=titulo, style="Tenue.TLabel").pack(anchor="w")
            lb = ttk.Label(celda, text="—", style="Grande.TLabel" if clave in ("prog", "cic") else "Dato.TLabel")
            lb.pack(anchor="w", pady=(0, 2))
            self.met[clave] = lb
        for clave, titulo in (("mem", "Memoria del programa"), ("lc3", "Frente a la LC-3")):
            ttk.Label(m, text=titulo, style="Tenue.TLabel").pack(anchor="w")
            lb = ttk.Label(m, text="—", style="LC3.TLabel" if clave == "lc3" else "Dato.TLabel")
            lb.pack(anchor="w", pady=(0, 2))
            self.met[clave] = lb
        self.met["ver"] = tk.Label(m, text="", font=("Segoe UI", 10, "bold"), bg=PANEL, fg=OK, anchor="w")
        self.met["ver"].pack(anchor="w")

        mem = self._panel(der, "Memoria  (en rosa: lo que escribió la última instrucción)")
        mem.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        fila = ttk.Frame(mem, style="Panel.TFrame")
        fila.pack(fill="x")
        ttk.Label(fila, text="Desde (dirección o etiqueta)", style="Tenue.TLabel").pack(side="left")
        self.mem_desde = tk.StringVar(value="x3000")
        e = ttk.Entry(fila, textvariable=self.mem_desde, width=22, font=MONO)
        e.pack(side="left", padx=6)
        e.bind("<Return>", lambda _e: self.actualizar_memoria())
        ttk.Button(fila, text="Ver", command=self.actualizar_memoria).pack(side="left")
        ttk.Button(fila, text="Pila (R6)", command=lambda: self.ver_memoria(self.cpu.R[6] if self.cpu else 0)
                   ).pack(side="left", padx=(6, 0))
        self.seguir = tk.BooleanVar(value=False)
        ttk.Checkbutton(fila, text="Seguir escrituras", variable=self.seguir, style="Panel.TCheckbutton",
                        command=self.actualizar_memoria).pack(side="left", padx=(10, 0))
        self.txt_mem = tk.Text(mem, height=FILAS_MEM, font=MONO, bg=PANEL, fg=TINTA, relief="flat", wrap="none")
        self.txt_mem.pack(fill="x", pady=(6, 0))
        self.txt_mem.tag_configure("mod", background=MOD_FONDO, foreground=ACENTO)
        self.txt_mem.tag_configure("tenue", foreground=TENUE)

        nb = self.nb = ttk.Notebook(der)
        nb.grid(row=2, column=0, sticky="nsew", pady=(8, 0))
        con = ttk.Frame(nb, style="Panel.TFrame", padding=6)
        nb.add(con, text="Consola")
        self.consola = tk.Text(con, font=MONO, bg="#1f1b17", fg="#f1e9da", insertbackground="#f1e9da",
                               relief="flat", wrap="word", height=10)
        sbc = ttk.Scrollbar(con, orient="vertical", command=self.consola.yview)
        self.consola.configure(yscrollcommand=sbc.set)
        self.consola.pack(side="left", fill="both", expand=True)
        sbc.pack(side="right", fill="y")
        self.consola.bind("<Key>", self.tecla)
        est = ttk.Frame(nb, style="Panel.TFrame", padding=6)
        nb.add(est, text="Estadísticas")
        est.columnconfigure(0, weight=1)
        est.columnconfigure(1, weight=1)
        est.rowconfigure(0, weight=1)
        self.t_ins = self._tabla(est, ("Instrucción", "Veces", "%"), (90, 80, 60))
        self.t_ins.master.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        self.t_mod = self._tabla(est, ("Módulo", "Instrucciones", "%"), (190, 90, 60))
        self.t_mod.master.grid(row=0, column=1, sticky="nsew")
        ver = ttk.Frame(nb, style="Panel.TFrame", padding=6)
        nb.add(ver, text="Verificación")
        self.tab_ver = ver
        ver.columnconfigure(0, weight=1)
        ver.rowconfigure(1, weight=1)
        self.lbl_ver = tk.Label(ver, text="Al terminar el benchmark se compara su salida, operación por operación, "
                                          "con la de la LC-3.", font=("Segoe UI", 10, "bold"), bg=PANEL, fg=TENUE,
                                anchor="w", justify="left")
        self.lbl_ver.grid(row=0, column=0, sticky="ew", pady=(0, 4))
        self.t_ver = self._tabla(ver, ("Operación", "LC-3", "LOVELACE", ""), (230, 150, 150, 30))
        self.t_ver.tag_configure("ok", foreground=OK)
        self.t_ver.tag_configure("mal", foreground=PARADA)
        self.t_ver.master.grid(row=1, column=0, sticky="nsew")
        cic = ttk.Frame(nb, style="Panel.TFrame", padding=6)
        nb.add(cic, text="Ciclos")
        cic.columnconfigure(0, weight=1)
        cic.rowconfigure(0, weight=1)
        self.t_cic = self._tabla(cic, ("Clase", "Etapas", "Ciclos c/u", "Instrucciones", "Ciclos", "%"),
                                 (130, 230, 70, 90, 80, 55))
        self.t_cic.master.grid(row=0, column=0, sticky="nsew")


    def _tabla(self, padre, cols, anchos):
        marco = ttk.Frame(padre, style="Panel.TFrame")
        t = ttk.Treeview(marco, columns=cols, show="headings", height=8)
        for c, w in zip(cols, anchos):
            t.heading(c, text=c, anchor="w")
            t.column(c, width=w, anchor="e" if c != cols[0] else "w", stretch=c == cols[0])
        sb = ttk.Scrollbar(marco, orient="vertical", command=t.yview)
        t.configure(yscrollcommand=sb.set)
        t.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        return t

    # -------------------------------------------------------------- archivos --
    def dialogo_abrir(self):
        ruta = filedialog.askopenfilename(
            title="Abrir programa", initialdir=os.path.join(AQUI, "..", "benchmark"),
            filetypes=[("Programas LOVELACE", "*.hex *.bin *.asm"), ("Todos", "*.*")])
        if ruta:
            self.abrir(ruta)

    def ensamblar(self, asm):
        """Ensambla un .asm con ensamblador.py (con -L lib y -S si existen junto al .asm)."""
        carpeta = os.path.dirname(os.path.abspath(asm))
        salida = os.path.join(tempfile.mkdtemp(prefix="lovelace_"), os.path.splitext(os.path.basename(asm))[0])
        cmd = [sys.executable, os.path.join(AQUI, "ensamblador.py"), asm, "-o", salida, "-O", "-D"]
        if os.path.isdir(os.path.join(carpeta, "lib")):
            cmd += ["-L", os.path.join(carpeta, "lib")]
        cadenas = os.path.join(carpeta, "cadenas_empaquetadas.json")
        if os.path.exists(cadenas):
            cmd += ["-S", cadenas]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0 or not os.path.exists(salida + ".hex"):
            messagebox.showerror("Error al ensamblar", (r.stdout + r.stderr).strip() or "sin detalle")
            return None
        return salida + ".hex", (r.stdout + r.stderr).strip()

    def abrir(self, ruta):
        self.pausar()
        aviso = ""
        if ruta.lower().endswith(".asm"):
            res = self.ensamblar(ruta)
            if not res:
                return
            imagen, aviso = res
        else:
            imagen = ruta
        try:
            self.imagen = cargar_imagen(imagen)
        except (OSError, ValueError, IndexError) as e:
            messagebox.showerror("No se pudo abrir", str(e))
            return
        base = os.path.splitext(imagen)[0]
        self.sim = cargar_simbolos(base + ".sym")
        self.map_path = base + ".map" if os.path.exists(base + ".map") else None
        self.ruta = ruta
        self.referencia = buscar_referencia(os.path.dirname(os.path.abspath(ruta)))
        self.lbl_archivo.configure(text=os.path.basename(ruta))
        self.reiniciar()
        if aviso:
            self.estado.configure(text="Ensamblado: " + aviso.splitlines()[-1])

    def reiniciar(self):
        if not self.imagen:
            return
        self.pausar()
        so = cargar_imagen(os.path.join(AQUI, "so_g23.hex"))
        paradas = self.cpu.parada if self.cpu else set()
        self.cpu = CPUInterfaz(self.imagen, so, "")
        self.cpu.parada = set(paradas)
        self.cache_ciclos = {}
        self.antes = list(self.cpu.R)
        self.out_len = 0
        self.consola.delete("1.0", "end")
        self.cargar_listado()
        for t in (self.t_ins, self.t_mod, self.t_cic, self.t_ver):
            t.delete(*t.get_children())
        self.met["ver"].configure(text="")
        self.lbl_ver.configure(
            fg=TENUE, text="Al terminar el benchmark se compara su salida, operación por operación, con la de la "
                           "LC-3." if self.referencia else "Este programa no tiene una salida de referencia de la LC-3.")
        self.mem_desde.set(f"x{self.cpu.origin:04X}")
        self.actualizar()
        self.estado.configure(text="Listo. Ejecutar corre el programa; Paso ejecuta una instrucción.")

    def cargar_listado(self):
        self.lista.delete(*self.lista.get_children())
        self.item_pc = None
        cpu = self.cpu
        for a in range(cpu.origin, cpu.origin + cpu.size - 1, 2):
            w = cpu.rw(a)
            etq = self.sim.get(a, "")
            self.lista.insert("", "end", iid=str(a), tags=("bp",) if a in cpu.parada else (),
                              values=("●" if a in cpu.parada else "", f"x{a:04X}", f"{w:04X}",
                                      etq, desensamblar(w, a, self.sim)))

    # ------------------------------------------------------------- ejecucion --
    def alternar(self):
        if self.corriendo:
            self.pausar()
        else:
            self.ejecutar()

    def ejecutar(self):
        if not self.cpu or self.cpu.halted:
            return
        self.corriendo = True
        self.btn_ejecutar.configure(text="⏸  Pausar")
        self.estado.configure(text="Ejecutando…")
        self.raiz.after(1, self.tic)

    def pausar(self):
        self.corriendo = False
        self.btn_ejecutar.configure(text="▶  Ejecutar")

    def correr(self, pasos):
        """Ejecuta hasta 'pasos' instrucciones del programa; devuelve el motivo."""
        cpu = self.cpu
        if cpu.esperando:
            if not cpu.kbd:
                return "teclado"
            cpu.esperando = False
        cpu.max_steps = cpu.count + cpu.count_so + max(pasos, 1) * 400 + 10_000   # sin lazo infinito
        try:
            r = cpu.run(pasos=pasos)
        except Excepcion as e:
            if cpu.esperando:
                return "teclado"
            if "limite de pasos" in str(e):
                return "pasos"
            return "excepcion: " + str(e)
        return r or "halt"

    def tic(self):
        if not self.corriendo:
            return
        pasos, demora = VELOCIDADES[self.velocidad.get()]
        r = self.correr(pasos)
        self.actualizar(liviano=pasos >= 1500 and r == "pasos")
        if r == "pasos":
            self.raiz.after(demora, self.tic)
        elif r == "teclado":
            self.estado.configure(text="El programa espera una tecla: escribí en la consola.")
            self.raiz.after(100, self.tic)
        else:
            self.fin(r)

    def paso(self, n=1):
        if not self.cpu or self.cpu.halted:
            return
        self.pausar()
        cpu = self.cpu
        pc, w = cpu.pc, cpu.rw(cpu.pc)
        c0, s0 = self.ciclos(cpu.hits), self.ciclos(cpu.hits_so)
        r = self.correr(n)
        c1, s1 = self.ciclos(cpu.hits), self.ciclos(cpu.hits_so)
        self.actualizar()
        if r not in ("pasos", "parada"):
            self.fin(r)
        elif r == "parada":
            self.estado.configure(text=f"Punto de parada en x{cpu.pc:04X}.")
        elif n == 1 and cpu.priv:
            clase, ci = ciclos_de(w)
            txt = (f"x{pc:04X}  {desensamblar(w, pc, self.sim)}  →  {ci} ciclos ({NOMBRE_CLASE[clase]}: "
                   f"{ETAPAS[clase]})")
            if s1 > s0:
                txt += f"  + {s1 - s0} ciclos del SO ({cpu.count_so:,} instr. del SO hasta ahora)".replace(",", ".")
            self.estado.configure(text=txt)
        else:
            self.estado.configure(text=f"{n} instrucciones: {c1 - c0} ciclos del programa"
                                       + (f" y {s1 - s0} del SO." if s1 > s0 else "."))

    def ciclos(self, hits, por_clase=None):
        """Ciclos de las instrucciones ejecutadas (direccion -> veces), con el modelo multiciclo."""
        cache, mem, total = self.cache_ciclos, self.cpu.mem, 0
        for a, k in hits.items():
            cc = cache.get(a)
            if cc is None:
                cc = cache[a] = ciclos_de(mem[a] | (mem[a + 1] << 8))
            total += k * cc[1]
            if por_clase is not None:
                d = por_clase.setdefault(cc[0], [0, 0])
                d[0] += k
                d[1] += k * cc[1]
        return total

    def ejecutar_hasta(self):
        t = self.hasta.get().strip()
        a = self.direccion(t)
        if a is None:
            messagebox.showwarning("Ejecutar hasta", f"No encontré la etiqueta o dirección «{t}».")
            return
        self.cpu.parada.add(a)
        self.al_terminar = a
        self.ejecutar()

    def fin(self, motivo):
        self.pausar()
        cpu = self.cpu
        if self.al_terminar is not None:
            if self.al_terminar not in self.paradas_usuario():
                cpu.parada.discard(self.al_terminar)
            self.al_terminar = None
        if motivo == "parada":
            self.estado.configure(text=f"Punto de parada en x{cpu.pc:04X} {self.sim.get(cpu.pc, '')}.")
        elif motivo == "halt":
            self.estado.configure(
                text=f"HALT. Instrucciones ejecutadas: {cpu.count + cpu.count_so:,} "
                     f"(programa {cpu.count:,}, SO {cpu.count_so:,}).".replace(",", "."))
            self.estadisticas()
            self.verificar()
        elif motivo.startswith("excepcion"):
            self.estado.configure(text="Excepción: " + motivo[11:])
            messagebox.showerror("Excepción", motivo[11:])
        self.actualizar()

    def paradas_usuario(self):
        return {int(i) for i in self.lista.tag_has("bp")}

    # ------------------------------------------------------- interaccion ----
    def tecla(self, ev):
        if not self.cpu:
            return "break"
        if ev.char == "\r":
            self.cpu.kbd.append("\n")
        elif ev.char and (ev.char.isprintable() or ev.char in "\b\t"):
            self.cpu.kbd.append(ev.char)
        elif ev.keysym in ("Up", "Down", "Prior", "Next"):
            return None
        return "break"

    def alternar_parada(self, ev):
        item = self.lista.identify_row(ev.y)
        if not item or not self.cpu:
            return
        a = int(item)
        if a in self.cpu.parada:
            self.cpu.parada.discard(a)
            self.lista.set(item, "bp", "")
            self.lista.item(item, tags=("pc",) if item == self.item_pc else ())
        else:
            self.cpu.parada.add(a)
            self.lista.set(item, "bp", "●")
            self.lista.item(item, tags=("bp", "pc") if item == self.item_pc else ("bp",))

    def mostrar_codificacion(self, _ev=None):
        sel = self.lista.selection()
        if not sel or not self.cpu:
            return
        a = int(sel[0])
        w = self.cpu.rw(a)
        b = f"{w:016b}"
        self.lbl_cod.configure(text=f"x{a:04X}: {b[:5]} {b[5:8]} {b[8:11]} {b[11:]}   "
                                    f"opcode {w >> 11:2d}   {mnemonico(w):6s}  {desensamblar(w, a, self.sim)}")

    def direccion(self, t):
        if not t:
            return None
        t2 = t.upper()
        for a, n in self.sim.items():
            if n.upper() == t2 or n.split(":")[-1].upper() == t2:
                return a
        try:
            return int(t2.lstrip("X"), 16) & 0xFFFE
        except ValueError:
            return None

    def ver_memoria(self, a):
        self.mem_desde.set(f"x{a:04X}")
        self.actualizar_memoria()

    # ------------------------------------------------------------ pantalla --
    def actualizar(self, liviano=False):
        cpu = self.cpu
        if not cpu:
            return
        nuevo = "".join(cpu.out[self.out_len:])
        if nuevo:
            self.consola.insert("end", nuevo)
            self.consola.see("end")
            self.out_len = len(cpu.out)
        for i, lb in enumerate(self.lbl_reg):
            v = cpu.R[i]
            s = v - 0x10000 if v & 0x8000 else v
            lb.configure(text=f"x{v:04X}  {s:>7d}", fg=CAMBIO if v != self.antes[i] else TINTA)
        self.antes = list(cpu.R)
        self.lbl_pc.configure(text=f"PC  x{cpu.pc:04X}   {self.sim.get(cpu.pc, '')}")
        self.lbl_flags.configure(text="   ".join(f"{c}={b}" for c, b in
                                               zip("NZPCV", (cpu.n, cpu.z, cpu.p, cpu.c, cpu.v))))
        self.lbl_modo.configure(text="Modo usuario" if cpu.priv else "Modo supervisor (sistema operativo)")
        prog, so = cpu.count, cpu.count_so
        cic, cicso = self.ciclos(cpu.hits), self.ciclos(cpu.hits_so)

        def num(x):
            return f"{x:,}".replace(",", ".")
        self.met["prog"].configure(text=num(prog))
        self.met["cic"].configure(text=num(cic))
        self.met["so"].configure(text=f"{num(so)} · {num(prog + so)}")
        cpi = f"{cic / prog:.2f}".replace(".", ",") if prog else "—"
        self.met["cicso"].configure(text=f"{num(cicso)} · CPI {cpi}")
        self.met["mem"].configure(text=f"{num(cpu.size)} bytes = {num(cpu.size // 2)} palabras")
        if cpu.halted and prog:
            self.met["lc3"].configure(text=f"{LC3_PROGRAMA / prog:.2f}× menos instrucciones\n"
                                           f"{LC3_CICLOS / cic:.2f}× menos ciclos".replace(".", ","))
        else:
            self.met["lc3"].configure(text=f"LC-3: {num(LC3_PROGRAMA)} instrucciones\n{num(LC3_CICLOS)} ciclos")
        if not liviano:
            self.marcar_pc()
            self.actualizar_memoria()

    def marcar_pc(self):
        cpu = self.cpu
        if self.item_pc and self.lista.exists(self.item_pc):
            tags = tuple(t for t in self.lista.item(self.item_pc, "tags") if t != "pc")
            self.lista.item(self.item_pc, tags=tags)
        it = str(cpu.pc)
        if self.lista.exists(it):
            tags = tuple(self.lista.item(it, "tags")) + ("pc",)
            self.lista.item(it, tags=tags)
            self.lista.see(it)
            self.item_pc = it
        else:
            self.item_pc = None

    def actualizar_memoria(self):
        if not self.cpu:
            return
        cpu = self.cpu
        if self.seguir.get() and cpu.ultima_escritura is not None:
            self.mem_desde.set(f"x{max((cpu.ultima_escritura & 0xFFF0) - 16, 0):04X}")
        a = self.direccion(self.mem_desde.get().strip())
        if a is None:
            return
        t = self.txt_mem
        t.delete("1.0", "end")
        for f in range(FILAS_MEM):
            base = (a + 16 * f) & 0xFFFE
            texto = ""
            t.insert("end", f"x{base:04X} ", "tenue")
            for k in range(8):
                d = (base + 2 * k) & 0xFFFF
                w = cpu.mem[d] | (cpu.mem[(d + 1) & 0xFFFF] << 8)
                t.insert("end", " ")
                t.insert("end", f"{w:04X}", "mod" if d in cpu.escritas else ())
                for byte in (w & 0xFF, w >> 8):
                    texto += chr(byte) if 32 <= byte < 127 else "·"
            etq = self.sim.get(base, "")
            t.insert("end", f"  {texto}  {etq[:22]}" + ("\n" if f < FILAS_MEM - 1 else ""))
        cpu.escritas.clear()

    def verificar(self):
        """Compara la salida con la de la LC-3 (misma calculadora, mismos datos)."""
        if not self.referencia:
            return
        nuestra = "".join(self.cpu.out)
        ref = open(self.referencia, encoding="utf-8").read()
        a, b = secciones(nuestra), secciones(ref)
        t = self.t_ver
        t.delete(*t.get_children())
        iguales = 0
        for i in range(max(len(a), len(b))):
            tit, ca = a[i] if i < len(a) else ("(falta)", [])
            _, cb = b[i] if i < len(b) else ("(sobra)", [])
            ok = ca == cb and (i < len(a) and i < len(b) and a[i][0] == b[i][0])
            iguales += ok
            k = -1                                   # resultado (ultima linea) o la primera que difiere
            if not ok:
                k = next((j for j in range(max(len(ca), len(cb)))
                          if (ca[j] if j < len(ca) else None) != (cb[j] if j < len(cb) else None)), -1)
            t.insert("", "end", tags=("ok" if ok else "mal",),
                     values=(f"{i + 1:2d}. {tit.title()}", cb[k] if -len(cb) <= k < len(cb) else "",
                             ca[k] if -len(ca) <= k < len(ca) else "", "✔" if ok else "✗"))
        total = len(b)
        identica = nuestra.replace("\r", "").strip() == ref.replace("\r", "").strip()
        if identica:
            txt = f"✔ Salida idéntica a la LC-3, carácter por carácter: {iguales} de {total} operaciones"
            color = OK
        else:
            txt = f"✗ La salida difiere de la LC-3: {iguales} de {total} operaciones iguales"
            color = PARADA
        self.lbl_ver.configure(text=txt, fg=color)
        self.met["ver"].configure(text=txt.split(":")[0], fg=color)
        self.nb.select(self.tab_ver)

    def estadisticas(self):
        cpu = self.cpu
        for t in (self.t_ins, self.t_mod):
            t.delete(*t.get_children())
        for k, v in cpu.ops.most_common():
            if k != "(SO)":
                self.t_ins.insert("", "end", values=(k, f"{v:,}".replace(",", "."),
                                                     f"{100 * v / cpu.count:.2f}".replace(".", ",")))
        if self.map_path:
            for k, v in perfil_por_modulo(cpu, self.map_path).most_common():
                self.t_mod.insert("", "end", values=(k, f"{v:,}".replace(",", "."),
                                                     f"{100 * v / cpu.count:.2f}".replace(".", ",")))
        self.t_cic.delete(*self.t_cic.get_children())
        por = {}
        total = self.ciclos(cpu.hits, por)
        for clase, (n, c) in sorted(por.items(), key=lambda x: -x[1][1]):
            cu = "3 + k" if clase == "pila" else str(CICLOS[clase])
            self.t_cic.insert("", "end", values=(NOMBRE_CLASE[clase], ETAPAS[clase], cu, f"{n:,}".replace(",", "."),
                                                 f"{c:,}".replace(",", "."),
                                                 f"{100 * c / total:.1f}".replace(".", ",")))
        self.t_cic.insert("", "end", values=("Total del programa", "", "", f"{cpu.count:,}".replace(",", "."),
                                             f"{total:,}".replace(",", "."), "100"))


def main(argv):
    ruta = argv[1] if len(argv) > 1 and not argv[1].startswith("--") else next(
        (r for r in (os.path.join(AQUI, "..", "benchmark", "benchmark_g23.hex"),                 # entrega
                     os.path.join(AQUI, "..", "benchmark_g23", "bench_optimizado_ODS.hex"))     # repositorio
         if os.path.exists(r)), "")
    raiz = tk.Tk()
    app = Interfaz(raiz, ruta if os.path.exists(ruta) else None)
    if "--prueba" in argv:          # prueba automatica: corre todo, informa y cierra
        captura = argv[argv.index("--captura") + 1] if "--captura" in argv else None

        def terminar():
            if app.corriendo:
                raiz.after(200, terminar)
                return
            c = app.cpu
            print(f"PRUEBA halted={c.halted} programa={c.count} so={c.count_so} total={c.count + c.count_so} "
                  f"bytes={c.size} salida_chars={len(''.join(c.out))}")
            if "--pestana" in argv:
                app.nb.select(int(argv[argv.index("--pestana") + 1]))
            if captura:
                from PIL import ImageGrab
                raiz.update()
                x, y = raiz.winfo_rootx(), raiz.winfo_rooty()
                ImageGrab.grab((x, y, x + raiz.winfo_width(), y + raiz.winfo_height())).save(captura)
            raiz.destroy()
        raiz.after(300, app.ejecutar)
        raiz.after(800, terminar)
    raiz.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
