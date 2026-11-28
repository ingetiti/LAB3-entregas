#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Interfaz grafica del simulador ISA-G11.

Abre el benchmark ya ensamblado (benchmark/benchmark_g11.hex), lo ejecuta y muestra la salida
del programa junto con las instrucciones de usuario, las del sistema operativo (estimadas, ver
costo_so.py) y el total, comparado con el de la LC-3 que informo la catedra.

Uso:
    python gui.py                     # abre la ventana con el benchmark cargado
    python gui.py programa.hex        # otro programa (.hex / .bin / .dec / .asm principal)
    python gui.py --ejecutar          # lo ejecuta apenas abre

Solo usa la biblioteca estandar (tkinter).
"""
import codecs
import contextlib
import io
import json
import os
import queue
import sys
import tempfile
import threading
import time
import tkinter as tk
from tkinter import filedialog, font as tkfont, messagebox, ttk

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import costo_so          # noqa: E402
import simulador         # noqa: E402

BENCHMARK = os.path.join(AQUI, 'benchmark', 'benchmark_g11.hex')

# ---------------------------------------------------------------- estilo
FONDO, CARD, CARD2, BORDE = '#12151a', '#1a1e25', '#232935', '#2b3240'
TEXTO, MUTED = '#dde2ea', '#8892a3'
ACENTO, USUARIO, SO = '#5fd3c4', '#7aa7ff', '#e7b866'
OK, ERR = '#7bd88f', '#ff8080'

F = {}                                   # fuentes, se crean con la ventana


def fmt(n):
    return f'{int(n):,}'.replace(',', '.')


def pct(x):
    return f'{x:.2f}'.replace('.', ',')


def elegir(candidatas, defecto):
    disp = set(tkfont.families())
    for c in candidatas:
        if c in disp:
            return c
    return defecto


def crear_fuentes():
    ui = elegir(['Segoe UI Variable Text', 'Segoe UI', 'SF Pro Text', 'Helvetica Neue', 'Ubuntu',
                 'Noto Sans', 'DejaVu Sans'], 'Helvetica')
    mono = elegir(['Cascadia Mono', 'Consolas', 'Menlo', 'DejaVu Sans Mono', 'Courier New'], 'Courier')
    F['ui'] = (ui, 10)
    F['peq'] = (ui, 9)
    F['cap'] = (ui, 8, 'bold')
    F['tit'] = (ui, 15, 'bold')
    F['sub'] = (ui, 10)
    F['grande'] = (ui, 34, 'bold')
    F['medio'] = (ui, 14, 'bold')
    F['btn'] = (ui, 10, 'bold')
    F['mono'] = (mono, 10)
    F['monop'] = (mono, 9)


class Boton(tk.Label):
    """Boton plano con hover (igual en Windows, Linux y macOS)."""

    def __init__(self, master, texto, comando, primario=False):
        self.primario = primario
        self.base = ACENTO if primario else CARD2
        self.hover = '#7fe3d6' if primario else '#2d3544'
        super().__init__(master, text=texto, bg=self.base, fg='#0b1d1a' if primario else TEXTO,
                         font=F['btn'], padx=16, pady=8, cursor='hand2')
        self.comando = comando
        self.activo = True
        self.bind('<Enter>', lambda e: self.activo and self.config(bg=self.hover))
        self.bind('<Leave>', lambda e: self.config(bg=self.base))
        self.bind('<Button-1>', self._click)

    def _click(self, _e):
        if self.activo:
            self.comando()

    def poner(self, texto=None, activo=None):
        if texto is not None:
            self.config(text=texto)
        if activo is not None:
            self.activo = activo
            self.config(cursor='hand2' if activo else 'arrow',
                        fg=(('#0b1d1a' if self.primario else TEXTO) if activo else MUTED))


class Tarjeta(tk.Frame):
    def __init__(self, master, titulo, pady=(0, 10)):
        super().__init__(master, bg=CARD, highlightthickness=1, highlightbackground=BORDE)
        self.pack(fill='x', pady=pady)
        self.cuerpo = tk.Frame(self, bg=CARD)
        self.cuerpo.pack(fill='both', expand=True, padx=16, pady=(12, 14))
        tk.Label(self.cuerpo, text=titulo.upper(), bg=CARD, fg=MUTED, font=F['cap']).pack(anchor='w', pady=(0, 8))


class Barra(tk.Canvas):
    """Barra apilada fina, se redibuja al cambiar de tamano."""

    def __init__(self, master, alto=8):
        super().__init__(master, height=alto, bg=CARD, highlightthickness=0, bd=0)
        self.partes, self.maximo, self.alto = [], 1, alto
        self.bind('<Configure>', lambda e: self.dibujar())

    def poner(self, partes, maximo):
        self.partes, self.maximo = partes, max(1, maximo)
        self.dibujar()

    def dibujar(self):
        self.delete('all')
        w = self.winfo_width()
        self.create_rectangle(0, 0, w, self.alto, fill=CARD2, outline='')
        x = 0.0
        for valor, color in self.partes:
            ancho = w * valor / self.maximo
            if ancho > 0:
                self.create_rectangle(x, 0, x + ancho, self.alto, fill=color, outline='')
            x += ancho


class Salida:
    """Archivo falso que recibe los bytes del programa y los pasa a la ventana."""

    def __init__(self, q):
        self.q = q

    def write(self, b):
        self.q.put(('txt', bytes(b)))
        return len(b)

    def flush(self):
        pass


# ---------------------------------------------------------------- aplicacion
class App:
    def __init__(self, root, programa=None, autoejecutar=False):
        self.root = root
        crear_fuentes()
        root.title('ISA Grupo 11 · Benchmark')
        root.configure(bg=FONDO)
        alto = min(740, max(640, root.winfo_screenheight() - 100))
        root.minsize(980, 640)
        root.geometry(f'1100x{alto}')
        self.estilo()

        self.ruta = None                 # imagen cargada (.hex/.bin/.dec)
        self.nombre = ''
        self.stats = None
        self.maq = None
        self.cola = queue.Queue()
        self.hilo = None
        self.corriendo = False
        self.t0 = 0.0
        self.salida_txt = ''
        self.decodificador = None
        self.coef = dict(costo_so.COEF_CATEDRA)
        self.vars_coef = {}
        self.silenciar = False

        self.construir()
        root.bind('<F5>', lambda e: self.alternar())
        root.bind('<Control-r>', lambda e: self.alternar())
        root.bind('<Escape>', lambda e: self.detener())

        self.cargar_programa(programa or BENCHMARK, inicial=True)
        if autoejecutar:
            root.after(300, self.ejecutar)

    # ------------------------------------------------------------ estilo / layout
    def estilo(self):
        st = ttk.Style(self.root)
        try:
            st.theme_use('clam')
        except tk.TclError:
            pass
        st.configure('TCombobox', fieldbackground=CARD2, background=CARD2, foreground=TEXTO,
                     arrowcolor=MUTED, bordercolor=BORDE, lightcolor=CARD2, darkcolor=CARD2, padding=4)
        st.map('TCombobox', fieldbackground=[('readonly', CARD2)], foreground=[('readonly', TEXTO)],
               selectbackground=[('readonly', CARD2)], selectforeground=[('readonly', TEXTO)])
        st.configure('Vertical.TScrollbar', background=BORDE, troughcolor=CARD, bordercolor=CARD,
                     arrowcolor=MUTED, lightcolor=BORDE, darkcolor=BORDE, relief='flat')
        st.map('Vertical.TScrollbar', background=[('disabled', CARD), ('active', '#3a4354'), ('!active', BORDE)])
        self.root.option_add('*TCombobox*Listbox.background', CARD2)
        self.root.option_add('*TCombobox*Listbox.foreground', TEXTO)
        self.root.option_add('*TCombobox*Listbox.selectBackground', BORDE)
        self.root.option_add('*TCombobox*Listbox.selectForeground', TEXTO)

    def construir(self):
        r = self.root
        r.grid_columnconfigure(0, weight=0)
        r.grid_columnconfigure(1, weight=1)
        r.grid_rowconfigure(1, weight=1)

        # --- cabecera
        cab = tk.Frame(r, bg=FONDO)
        cab.grid(row=0, column=0, columnspan=2, sticky='ew', padx=24, pady=(20, 14))
        tit = tk.Frame(cab, bg=FONDO)
        tit.pack(side='left')
        tk.Label(tit, text='ISA Grupo 11', bg=FONDO, fg=TEXTO, font=F['tit']).pack(anchor='w')
        self.lbl_sub = tk.Label(tit, text='', bg=FONDO, fg=MUTED, font=F['sub'])
        self.lbl_sub.pack(anchor='w')
        bt = tk.Frame(cab, bg=FONDO)
        bt.pack(side='right')
        self.btn_guardar = Boton(bt, 'Guardar informe', self.guardar)
        self.btn_guardar.pack(side='right', padx=(8, 0))
        self.btn_abrir = Boton(bt, 'Abrir programa…', self.abrir)
        self.btn_abrir.pack(side='right', padx=(8, 0))
        self.btn_run = Boton(bt, 'Ejecutar benchmark', self.alternar, primario=True)
        self.btn_run.pack(side='right')

        # --- columna izquierda: numeros
        izq = tk.Frame(r, bg=FONDO, width=470)
        izq.grid(row=1, column=0, sticky='nsw', padx=(24, 12), pady=(0, 6))
        izq.pack_propagate(False)
        izq.config(width=470)
        self.construir_total(izq)
        self.construir_clases(izq)
        self.construir_modelo(izq)

        # --- columna derecha: consola, servicios del SO y memoria
        der = tk.Frame(r, bg=FONDO)
        der.grid(row=1, column=1, sticky='nsew', padx=(0, 24), pady=(0, 6))
        self.construir_consola(der)
        self.construir_servicios(der)
        self.construir_memoria(der)

        # --- barra de estado
        est = tk.Frame(r, bg=FONDO)
        est.grid(row=2, column=0, columnspan=2, sticky='ew', padx=24, pady=(4, 14))
        self.lbl_estado = tk.Label(est, text='', bg=FONDO, fg=MUTED, font=F['peq'], anchor='w')
        self.lbl_estado.pack(side='left')
        self.lbl_tiempo = tk.Label(est, text='', bg=FONDO, fg=MUTED, font=F['peq'])
        self.lbl_tiempo.pack(side='right')

    def construir_total(self, padre):
        t = Tarjeta(padre, 'Instrucciones · usuario + SO')
        c = t.cuerpo
        self.lbl_total = tk.Label(c, text='—', bg=CARD, fg=TEXTO, font=F['grande'])
        self.lbl_total.pack(anchor='w')
        self.lbl_total_cap = tk.Label(c, text='Ejecutá el benchmark para ver los resultados', bg=CARD,
                                      fg=MUTED, font=F['peq'])
        self.lbl_total_cap.pack(anchor='w', pady=(0, 10))

        fila = tk.Frame(c, bg=CARD)
        fila.pack(fill='x', pady=(0, 12))
        self.lbl_usuario = self.mini(fila, 'Usuario', USUARIO)
        self.lbl_so = self.mini(fila, 'SO (estimado)', SO)

        # comparacion con la LC-3
        g = tk.Frame(c, bg=CARD)
        g.pack(fill='x')
        g.grid_columnconfigure(1, weight=1)
        self.barras = {}
        for i, (clave, nombre) in enumerate((('g11', 'ISA-G11'), ('lc3', 'LC-3 (cátedra)'))):
            tk.Label(g, text=nombre, bg=CARD, fg=MUTED, font=F['peq'], width=13, anchor='w').grid(
                row=i, column=0, sticky='w', pady=3)
            b = Barra(g)
            b.grid(row=i, column=1, sticky='ew', padx=8, pady=3)
            v = tk.Label(g, text='', bg=CARD, fg=TEXTO, font=F['peq'], width=9, anchor='e')
            v.grid(row=i, column=2, sticky='e', pady=3)
            self.barras[clave] = (b, v)
        self.lbl_delta = tk.Label(c, text='', bg=CARD, fg=MUTED, font=F['peq'], anchor='w')
        self.lbl_delta.pack(anchor='w', pady=(8, 0))

    def mini(self, padre, nombre, color):
        f = tk.Frame(padre, bg=CARD)
        f.pack(side='left', expand=True, fill='x')
        tk.Frame(f, bg=color, width=8, height=8).pack(side='left', padx=(0, 8))
        col = tk.Frame(f, bg=CARD)
        col.pack(side='left')
        tk.Label(col, text=nombre, bg=CARD, fg=MUTED, font=F['peq']).pack(anchor='w')
        v = tk.Label(col, text='—', bg=CARD, fg=TEXTO, font=F['medio'])
        v.pack(anchor='w')
        return v

    def construir_clases(self, padre):
        t = Tarjeta(padre, 'Instrucciones de usuario por clase')
        c = t.cuerpo
        c.grid_columnconfigure(0, weight=1)
        self.clases = {}
        g = tk.Frame(c, bg=CARD)
        g.pack(fill='x')
        g.grid_columnconfigure(1, weight=1)
        nombres = (('aritmetico-logicas', 'Aritmético-lógicas'), ('memoria', 'Memoria'), ('control', 'Control'))
        for i, (k, n) in enumerate(nombres):
            tk.Label(g, text=n, bg=CARD, fg=MUTED, font=F['peq'], width=17, anchor='w').grid(row=i, column=0, pady=3)
            b = Barra(g, 6)
            b.grid(row=i, column=1, sticky='ew', padx=8, pady=3)
            v = tk.Label(g, text='', bg=CARD, fg=TEXTO, font=F['peq'], width=15, anchor='e')
            v.grid(row=i, column=2, pady=3, sticky='e')
            self.clases[k] = (b, v)

    def construir_servicios(self, padre):
        t = Tarjeta(padre, 'Servicios del sistema operativo')
        g = tk.Frame(t.cuerpo, bg=CARD)
        g.pack(fill='x')
        g.grid_columnconfigure(0, weight=1)
        for j, h in enumerate(('Servicio', 'Llamadas', 'Caracteres', 'Instr. SO')):
            tk.Label(g, text=h, bg=CARD, fg=MUTED, font=F['peq'], anchor='w' if j == 0 else 'e',
                     width=0 if j == 0 else 12).grid(row=0, column=j, sticky='ew', pady=(0, 3))
        self.filas_so = {}
        for i, nombre in enumerate(costo_so.SERVICIOS + ('Total',), start=1):
            fuente = F['peq'] if nombre != 'Total' else (F['peq'][0], F['peq'][1], 'bold')
            celdas = []
            for j in range(4):
                lab = tk.Label(g, text=nombre if j == 0 else '', bg=CARD, fg=TEXTO, font=fuente,
                               anchor='w' if j == 0 else 'e')
                lab.grid(row=i, column=j, sticky='ew', pady=1)
                celdas.append(lab)
            self.filas_so[nombre] = celdas

    def construir_memoria(self, padre):
        t = Tarjeta(padre, 'Memoria', pady=(0, 0))
        self.lbl_mem = tk.Label(t.cuerpo, text='', bg=CARD, fg=TEXTO, font=F['peq'], justify='left', anchor='w')
        self.lbl_mem.pack(anchor='w')

    def construir_consola(self, padre):
        caja = tk.Frame(padre, bg=CARD, highlightthickness=1, highlightbackground=BORDE)
        caja.pack(fill='both', expand=True, pady=(0, 10))
        cab = tk.Frame(caja, bg=CARD)
        cab.pack(fill='x', padx=16, pady=(12, 6))
        tk.Label(cab, text='SALIDA DEL PROGRAMA', bg=CARD, fg=MUTED, font=F['cap']).pack(side='left')
        self.var_entrada = tk.StringVar()
        ent = tk.Entry(cab, textvariable=self.var_entrada, bg=CARD2, fg=TEXTO, insertbackground=TEXTO,
                       relief='flat', highlightthickness=1, highlightbackground=BORDE,
                       highlightcolor=ACENTO, font=F['monop'], width=22)
        ent.pack(side='right')
        tk.Label(cab, text='Teclado (GETC/IN)', bg=CARD, fg=MUTED, font=F['peq']).pack(side='right', padx=(0, 8))
        cuerpo = tk.Frame(caja, bg=CARD)
        cuerpo.pack(fill='both', expand=True, padx=(16, 4), pady=(0, 12))
        self.txt = tk.Text(cuerpo, bg=CARD, fg=TEXTO, font=F['mono'], relief='flat', wrap='none',
                           highlightthickness=0, insertbackground=TEXTO, padx=0, pady=0, state='disabled', height=8, width=40,
                           selectbackground=BORDE, spacing1=1, cursor='arrow')
        sb = ttk.Scrollbar(cuerpo, orient='vertical', command=self.txt.yview)
        self.txt.configure(yscrollcommand=sb.set)
        sb.pack(side='right', fill='y')
        self.txt.pack(side='left', fill='both', expand=True)
        self.txt.tag_configure('titulo', foreground=ACENTO)
        self.txt.tag_configure('aviso', foreground=SO)
        self.txt.tag_configure('error', foreground=ERR)

    def construir_modelo(self, padre):
        t = Tarjeta(padre, 'Modelo del SO', pady=(0, 0))
        c = t.cuerpo
        fila = tk.Frame(c, bg=CARD)
        fila.pack(fill='x')
        self.var_modelo = tk.StringVar(value=list(costo_so.MODELOS)[0])
        self.cmb = ttk.Combobox(fila, textvariable=self.var_modelo, state='readonly', width=29,
                                values=list(costo_so.MODELOS) + ['Personalizado'], font=F['peq'])
        self.cmb.pack(side='left')
        self.cmb.bind('<<ComboboxSelected>>', lambda e: self.elegir_modelo())
        ed = tk.Label(fila, text='Editar coeficientes…', bg=CARD, fg=ACENTO, font=F['peq'], cursor='hand2')
        ed.pack(side='right')
        ed.bind('<Button-1>', lambda e: self.dialogo_coef())
        tk.Label(c, text='El SO es una estimación: la cátedra solo publicó el total de la LC-3.', bg=CARD,
                 fg=MUTED, font=F['peq'], anchor='w').pack(anchor='w', pady=(8, 0))
        for k, v in self.coef.items():
            sv = tk.StringVar(value=str(v))
            sv.trace_add('write', lambda *a, k=k: self.editar_coef(k))
            self.vars_coef[k] = sv
        self.dlg = None

    # ------------------------------------------------------------ modelo del SO
    def dialogo_coef(self):
        if self.dlg is not None and self.dlg.winfo_exists():
            self.dlg.lift()
            return
        d = tk.Toplevel(self.root)
        self.dlg = d
        d.title('Coeficientes del SO')
        d.configure(bg=CARD)
        d.resizable(False, False)
        d.transient(self.root)
        d.geometry(f'+{self.root.winfo_rootx() + 90}+{self.root.winfo_rooty() + 130}')
        cuerpo = tk.Frame(d, bg=CARD)
        cuerpo.pack(padx=22, pady=18)
        tk.Label(cuerpo, text='INSTRUCCIONES DE SO POR LLAMADA', bg=CARD, fg=MUTED, font=F['cap']).grid(
            row=0, column=0, columnspan=3, sticky='w', pady=(0, 10))
        etiquetas = (('OUT', 'OUT'), ('PUTS_fijo', 'PUTS fijo'), ('PUTS_por_caracter', 'PUTS por carácter'),
                     ('GETC', 'GETC'), ('IN', 'IN'), ('HALT', 'HALT'))
        for i, (k, n) in enumerate(etiquetas):
            fila, col = 1 + i // 3 * 2, i % 3
            tk.Label(cuerpo, text=n, bg=CARD, fg=MUTED, font=F['peq']).grid(row=fila, column=col, sticky='w',
                                                                           padx=(0, 18))
            tk.Entry(cuerpo, textvariable=self.vars_coef[k], width=8, bg=CARD2, fg=TEXTO, insertbackground=TEXTO,
                     relief='flat', highlightthickness=1, highlightbackground=BORDE, highlightcolor=ACENTO,
                     font=F['monop']).grid(row=fila + 1, column=col, sticky='w', padx=(0, 18), pady=(2, 10))
        nota = ('En esta ISA los servicios los resuelve el simulador: cada TRAP ya cuenta 1 instrucción de usuario '
                'y no se simula el código del SO. La cátedra solo informó el total para la LC-3 (22.074). Los '
                'coeficientes del modelo "calibrado" reproducen ese total con la misma secuencia de servicios del '
                'benchmark (76 OUT, 133 PUTS, 1.541 caracteres, 1 HALT); no es una medición del SO real.')
        tk.Label(cuerpo, text=nota, bg=CARD, fg=MUTED, font=F['peq'], wraplength=420, justify='left',
                 anchor='w').grid(row=5, column=0, columnspan=3, sticky='w', pady=(4, 12))
        Boton(cuerpo, 'Cerrar', d.destroy).grid(row=6, column=0, columnspan=3, sticky='e')

    def elegir_modelo(self):
        nombre = self.var_modelo.get()
        if nombre in costo_so.MODELOS:
            self.coef = dict(costo_so.MODELOS[nombre])
            self.silenciar = True
            for k, v in self.coef.items():
                self.vars_coef[k].set(str(v))
            self.silenciar = False
            self.refrescar()

    def editar_coef(self, k):
        if self.silenciar:
            return
        try:
            valor = int(self.vars_coef[k].get())
            if valor < 0:
                raise ValueError
        except ValueError:
            return
        self.coef[k] = valor
        for nombre, c in costo_so.MODELOS.items():
            if c == self.coef:
                self.var_modelo.set(nombre)
                break
        else:
            self.var_modelo.set('Personalizado')
        self.refrescar()

    # ------------------------------------------------------------ programa
    def abrir(self):
        if self.corriendo:
            return
        ruta = filedialog.askopenfilename(
            title='Abrir programa', initialdir=os.path.join(AQUI, 'benchmark'),
            filetypes=[('Programas ISA-G11', '*.hex *.bin *.dec *.asm'), ('Todos', '*.*')])
        if ruta:
            self.cargar_programa(ruta)

    def cargar_programa(self, ruta, inicial=False):
        """Carga una imagen (.hex/.bin/.dec); un .asm se ensambla antes (con ./lib como biblioteca)."""
        self.stats = None
        self.limpiar_consola()
        self.refrescar()
        elegido = ruta
        try:
            if ruta.lower().endswith('.asm'):
                ruta = self.ensamblar(ruta)
            origen, datos = simulador.leer_imagen(ruta)
        except Exception as e:                                       # noqa: BLE001
            self.ruta = None
            self.escribir(f'No se pudo cargar el programa:\n{e}\n', 'error')
            self.estado(f'Error al cargar {os.path.basename(elegido)}', ERR)
            self.btn_run.poner(activo=False)
            return
        self.ruta = ruta
        self.nombre = os.path.basename(elegido)
        self.btn_run.poner(activo=True)
        es_bench = os.path.abspath(ruta) == os.path.abspath(BENCHMARK)
        self.lbl_sub.config(text=f'{self.nombre}  ·  {len(datos) // 2:,} palabras en x{origen:04X}'.replace(',', '.'))
        self.btn_run.poner('Ejecutar benchmark' if es_bench else 'Ejecutar')
        self.estado('Listo para ejecutar · F5')

    def ensamblar(self, asm):
        import ensamblador
        carpeta = os.path.dirname(os.path.abspath(asm))
        salida = os.path.join(tempfile.mkdtemp(prefix='isa_g11_'), 'programa')
        argv = [asm, '-o', salida, '--formato', 'hex', '--lib', carpeta]
        if os.path.isdir(os.path.join(carpeta, 'lib')):
            argv += ['--lib', os.path.join(carpeta, 'lib')]
        err = io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(err):
            rc = ensamblador.main(argv)
        if rc not in (0, None):
            raise RuntimeError(err.getvalue().strip() or 'error de ensamblado')
        self.escribir(err.getvalue(), 'aviso')
        return salida + '.hex'

    # ------------------------------------------------------------ ejecucion
    def alternar(self):
        self.detener() if self.corriendo else self.ejecutar()

    def ejecutar(self):
        if self.corriendo or not self.ruta:
            return
        try:
            origen, datos = simulador.leer_imagen(self.ruta)
        except Exception as e:                                       # noqa: BLE001
            messagebox.showerror('Error', str(e))
            return
        entrada = self.var_entrada.get().replace('\\n', '\n').encode('latin-1', 'replace')
        self.maq = simulador.Maquina(entrada=entrada, salida=Salida(self.cola))
        self.maq.usar_stdin = False
        self.maq.cargar(origen, datos)
        self.stats = None
        self.salida_txt = ''
        self.decodificador = codecs.getincrementaldecoder('utf-8')(errors='replace')
        self.limpiar_consola()
        self.refrescar()
        self.corriendo = True
        self.t0 = time.time()
        self.btn_run.poner('Detener')
        self.btn_abrir.poner(activo=False)
        self.btn_guardar.poner(activo=False)
        self.lbl_total_cap.config(text='ejecutando… instrucciones de usuario hasta ahora', fg=ACENTO)
        self.estado('Ejecutando…', ACENTO)
        self.hilo = threading.Thread(target=self._correr, daemon=True)
        self.hilo.start()
        self.root.after(40, self.sondear)

    def _correr(self):
        m = self.maq
        try:
            m.correr()
            self.cola.put(('fin', m.estadisticas()))
        except Exception as e:                                       # noqa: BLE001
            self.cola.put(('error', repr(e)))

    def detener(self):
        if self.corriendo and self.maq and not self.maq.detenida:
            self.maq.detenida = True
            self.maq.motivo = 'detenido por el usuario'

    def sondear(self):
        fin = None
        try:
            while True:
                tipo, dato = self.cola.get_nowait()
                if tipo == 'txt':
                    self.escribir(self.decodificador.decode(dato))
                elif tipo == 'fin':
                    fin = dato
                elif tipo == 'error':
                    self.escribir(f'\nError interno: {dato}\n', 'error')
                    fin = False
        except queue.Empty:
            pass
        if fin is None:
            self.lbl_total.config(text=fmt(self.maq.total))
            self.lbl_tiempo.config(text=f'{time.time() - self.t0:.1f} s')
            self.root.after(40, self.sondear)
            return
        self.terminar(fin or None)

    def terminar(self, stats):
        self.corriendo = False
        dt = time.time() - self.t0
        self.btn_run.poner('Ejecutar benchmark' if os.path.abspath(self.ruta) == os.path.abspath(BENCHMARK)
                           else 'Ejecutar')
        self.btn_abrir.poner(activo=True)
        self.btn_guardar.poner(activo=stats is not None)
        self.colorear_titulos()
        if stats is None:
            self.estado('La ejecución falló', ERR)
            return
        self.stats = stats
        self.refrescar()
        motivo = stats['motivo_parada']
        self.lbl_tiempo.config(text=f'{dt:.1f} s · {fmt(stats["instrucciones_ejecutadas"] / max(dt, 1e-9))} instr/s')
        self.estado(f'Parada: {motivo}', OK if motivo == 'HALT' else SO)

    # ------------------------------------------------------------ vista
    def limpiar_consola(self):
        self.salida_txt = ''
        self.txt.config(state='normal')
        self.txt.delete('1.0', 'end')
        self.txt.config(state='disabled')

    def escribir(self, texto, tag=None):
        if not texto:
            return
        self.salida_txt += texto
        self.txt.config(state='normal')
        self.txt.insert('end', texto, tag) if tag else self.txt.insert('end', texto)
        self.txt.see('end')
        self.txt.config(state='disabled')

    def colorear_titulos(self):
        n = int(self.txt.index('end-1c').split('.')[0])
        for i in range(1, n + 1):
            if self.txt.get(f'{i}.0', f'{i}.2') == '==':
                self.txt.tag_add('titulo', f'{i}.0', f'{i}.end')

    def estado(self, texto, color=MUTED):
        self.lbl_estado.config(text=texto, fg=color)

    def refrescar(self):
        s = self.stats
        if s is None:
            for k in ('g11', 'lc3'):
                self.barras[k][0].poner([], 1)
                self.barras[k][1].config(text='')
            self.lbl_total.config(text='—')
            self.lbl_total_cap.config(text='Ejecutá el programa para ver los resultados', fg=MUTED)
            self.lbl_usuario.config(text='—')
            self.lbl_so.config(text='—')
            self.lbl_delta.config(text='')
            for b, v in self.clases.values():
                b.poner([], 1)
                v.config(text='')
            for nombre, celdas in self.filas_so.items():
                for lab in celdas:
                    lab.grid() if nombre == 'Total' else lab.grid_remove()
                for lab in celdas[1:]:
                    lab.config(text='')
            self.lbl_mem.config(text='')
            return
        r = costo_so.calcular(s, self.coef)
        self.lbl_total.config(text=fmt(r['total']))
        self.lbl_total_cap.config(text='instrucciones ejecutadas en total (usuario + SO estimado)', fg=MUTED)
        self.lbl_usuario.config(text=fmt(r['usuario']))
        self.lbl_so.config(text=fmt(r['so']))

        es_bench = costo_so.es_benchmark(s)
        lc3 = costo_so.LC3_TOTAL if es_bench else 0
        maximo = max(r['total'], lc3, 1)
        b, v = self.barras['g11']
        b.poner([(r['usuario'], USUARIO), (r['so'], SO)], maximo)
        v.config(text=fmt(r['total']))
        b, v = self.barras['lc3']
        if es_bench:
            b.poner([(costo_so.LC3_USUARIO, USUARIO), (costo_so.LC3_SO, SO)], maximo)
            v.config(text=fmt(costo_so.LC3_TOTAL))
            d = r['total'] - costo_so.LC3_TOTAL
            signo = '−' if d < 0 else '+'
            self.lbl_delta.config(
                text=f'{signo}{fmt(abs(d))} instrucciones ({signo}{pct(abs(d) / costo_so.LC3_TOTAL * 100)} %) '
                     f'respecto de la LC-3')
        else:
            b.poner([], 1)
            v.config(text='—')
            self.lbl_delta.config(text='Sin comparación: no es el benchmark de la cátedra')

        uso = max(r['usuario'], 1)
        for k, (barra, lab) in self.clases.items():
            n = s['por_clase'].get(k, 0)
            barra.poner([(n, USUARIO)], uso)
            lab.config(text=f'{fmt(n)}  ·  {pct(n / uso * 100)} %')

        for nombre, llamadas, chars, instr in r['filas']:
            c = self.filas_so[nombre]
            for lab in c:
                lab.grid() if llamadas else lab.grid_remove()
            c[1].config(text=fmt(llamadas))
            c[2].config(text=fmt(chars) if chars else '·', fg=TEXTO if chars else MUTED)
            c[3].config(text=fmt(instr), fg=SO)
        t = self.filas_so['Total']
        for lab in t:
            lab.grid()
        t[1].config(text=fmt(sum(f[1] for f in r['filas'])))
        t[2].config(text=fmt(sum(f[2] for f in r['filas'])))
        t[3].config(text=fmt(r['so']), fg=SO)

        m = s['memoria']
        self.lbl_mem.config(text=(
            f'Imagen: {fmt(m["imagen_palabras"])} palabras ({fmt(m["imagen_bytes"])} bytes) en {m["origen"]}'
            f'  ·  código ejecutado: {fmt(m["bytes_de_instrucciones_ejecutados_distintos"])} bytes\n'
            f'Datos leídos: {fmt(m["bytes_de_datos_leidos_distintos"])} bytes  ·  '
            f'escritos: {fmt(m["bytes_escritos_distintos"])} bytes'))

    # ------------------------------------------------------------ informe
    def informe(self):
        s = self.stats
        r = costo_so.calcular(s, self.coef)
        L = [f'ISA Grupo 11 - informe de ejecucion', f'Programa: {self.nombre}',
             f'Parada: {s["motivo_parada"]}', '',
             f'Instrucciones de usuario : {fmt(r["usuario"])}',
             f'Instrucciones del SO (est.): {fmt(r["so"])}',
             f'Total                    : {fmt(r["total"])}']
        if costo_so.es_benchmark(s):
            d = r['total'] - costo_so.LC3_TOTAL
            L.append(f'LC-3 (catedra)           : {fmt(costo_so.LC3_USUARIO)} + {fmt(costo_so.LC3_SO)} = '
                     f'{fmt(costo_so.LC3_TOTAL)}  (diferencia {d:+,})'.replace(',', '.'))
        L += ['', 'Modelo del SO (instrucciones por llamada): ' + ', '.join(f'{k}={v}' for k, v in self.coef.items()),
              'Servicios:']
        for n, ll, ch, ins in r['filas']:
            if ll:
                L.append(f'  {n:5} llamadas={fmt(ll)} caracteres={fmt(ch)} instr.SO={fmt(ins)}')
        L += ['', 'Usuario por clase:'] + [f'  {k:20} {fmt(v)}' for k, v in s['por_clase'].items() if v]
        m = s['memoria']
        L += ['', f'Memoria: {m["imagen_palabras"]} palabras en {m["origen"]}; '
                  f'codigo ejecutado {m["bytes_de_instrucciones_ejecutados_distintos"]} bytes; '
                  f'datos leidos {m["bytes_de_datos_leidos_distintos"]}, escritos {m["bytes_escritos_distintos"]}',
              '', '--- Salida del programa ---', self.salida_txt]
        return '\n'.join(L)

    def guardar(self):
        if not self.stats:
            return
        ruta = filedialog.asksaveasfilename(
            title='Guardar informe', defaultextension='.txt', initialfile='informe_g11.txt',
            filetypes=[('Texto', '*.txt'), ('JSON (estadísticas)', '*.json')])
        if not ruta:
            return
        with open(ruta, 'w', encoding='utf-8') as f:
            if ruta.lower().endswith('.json'):
                r = costo_so.calcular(self.stats, self.coef)
                json.dump({'estadisticas': self.stats, 'so_modelo': self.coef,
                           'so_estimado': r['so'], 'total': r['total']}, f, indent=2, ensure_ascii=False)
            else:
                f.write(self.informe())
        self.estado(f'Informe guardado en {ruta}', OK)


def dpi_windows():
    if sys.platform == 'win32':
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:                                            # noqa: BLE001
            pass


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    auto = '--ejecutar' in argv
    args = [a for a in argv if not a.startswith('--')]
    dpi_windows()
    root = tk.Tk()
    App(root, programa=args[0] if args else None, autoejecutar=auto)
    root.mainloop()
    return 0


if __name__ == '__main__':
    sys.exit(main())
