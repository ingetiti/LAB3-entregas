#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ensamblador.py - Ensamblador de la ISA-NZP (LC-3 expandida, byte-addressable).

Uso:
    python ensamblador.py principal.asm [modulo.asm ...] [-o BASE] [--permitir-sqr]
    python ensamblador.py --carpeta lib [-d build] [-r]      (modo lote, v2)

Modo carpeta (--carpeta): ensambla CADA .asm de la carpeta por separado (un
error en un archivo no detiene a los demás), deja BASE.bin/.hex/.lst/.sym de
cada uno en la carpeta de salida (-d, por defecto ./build) y muestra un
resumen. -r busca también en subcarpetas. Devuelve 0 solo si todos
ensamblaron.

Genera BASE.bin (los 2 primeros bytes = origen, después la imagen), BASE.hex
(texto hexadecimal con el mismo contenido), BASE.lst (listado) y BASE.sym
(tabla de símbolos, la usa el simulador para el perfil por etiqueta).

Sintaxis
  - Comentarios con ';'. Etiquetas con o sin ':' (estilo LC-3), solas en una
    línea o delante de la instrucción.
  - Números: #-5, x2D, 0x2D, 25, 'A'. Expresiones simples: etq+2, etq-otra.
  - Registros R0..R7.
  - Instrucciones: ADD AND NOT BR[nzp] JMP RET JSR JSRR LEA RTI TRAP
    LDB STB LDH STH LD ST MUL DIV MOD SHF SQR   (formatos en isa.py)
    LD/ST Rx, etiqueta: palabra PC-relativa (alcance ±128 palabras).
    LDR/STR Rx, Rbase, #off: alias de LDH/STH.
  - Alias: GETC OUT PUTS IN PUTSP HALT (TRAP x20..x25), NOP, MOV Rd,Rs,
    SHL/SHR/SAR Rd,Rs,#n, LDBL/LDBH/STBL/STBH (LDB/STB con H=0/1; también
    se acepta  LDB Rd,Rb,#off,H  y  LDB Rd,Rb,#off,L).
  - Directivas: .ORIG .END .FILL .BLKW .BLKB .BYTE .STRINGZ .ALIGN .EXTERNAL

Alineación: toda instrucción, .FILL, .BLKW y .STRINGZ empieza en dirección
par. Si hace falta, el ensamblador inserta 1 byte de relleno (0x00) y avisa.

.EXTERNAL:  .EXTERNAL archivo-etiqueta   (o solo  .EXTERNAL etiqueta)
  El nombre completo se puede usar luego en .FILL:
        .FILL archivo-etiqueta     ; dirección de 'etiqueta' en archivo.asm
  El módulo se busca entre los archivos pasados por línea de comandos y, si
  no está, en el directorio del archivo que lo declara: primero como
  archivo.asm y, si no existe, cualquier .asm de esa carpeta que defina la
  etiqueta (avisa cuál usó; si hay más de uno, da error).
  Todos los archivos se ensamblan juntos: el principal en su .ORIG y cada
  módulo a continuación (o en su propio .ORIG).
"""
import argparse
import os
import re
import sys

import isa
import isa_lc3

REGS = {f"R{i}": i for i in range(8)}
EXTRAS = {"NOP", "MOV", "SHL", "SHR", "SAR", "LDBL", "LDBH", "STBL", "STBH",
          "LDR", "STR"}
MNEMONICOS = set(isa.OPCODES) | EXTRAS | set(isa.TRAPS)
DIRECTIVAS = {".ORIG", ".END", ".FILL", ".BLKW", ".BLKB", ".BYTE",
              ".STRINGZ", ".ALIGN", ".EXTERNAL"}
ALINEAN = {".FILL", ".BLKW", ".STRINGZ", ".ALIGN"}
CLASICOS = set(isa_lc3.MNEMONICOS) | set(isa.TRAPS)
# marcas para detectar en qué ISA está escrito un archivo
MARCAS_CLASICO = {"LD", "ST", "LDR", "STR", "LDI", "STI"}
MARCAS_NUEVO = {"LDB", "LDH", "STB", "STH", "MUL", "DIV", "MOD", "SHF", "SHL",
                "SHR", "SAR", "MOV", "SQR", "LDBL", "LDBH", "STBL", "STBH"}
RE_BR = re.compile(r"^BR([NZP]*)$")
RE_IDENT = re.compile(r"^[A-Za-z_]\w*$")
RE_HEX = re.compile(r"^[xX][0-9A-Fa-f]+$")
RE_TOKEN = re.compile(
    r"#-?\d+|0[xX][0-9A-Fa-f]+(?!\w)|0[bB][01]+(?!\w)|[xX][0-9A-Fa-f]+(?!\w)"
    r"|\d+(?!\w)"
    r"|'(?:\\.|[^'\\])'|[A-Za-z_]\w*|[+\-]")
ESCAPES = {"n": 10, "r": 13, "t": 9, "0": 0, "\\": 92, '"': 34}


class ErrorEnsamblador(Exception):
    def __init__(self, errores):
        self.errores = errores
        super().__init__("\n".join(errores))


class Linea:
    def __init__(self, archivo, nro, crudo, etiquetas, op, resto):
        self.archivo, self.nro, self.crudo = archivo, nro, crudo
        self.etiquetas, self.op, self.resto = etiquetas, op, resto
        self.args = [a for a in re.split(r"[,\s]+", resto) if a] if op else []


class Unidad:
    def __init__(self, ruta):
        self.ruta = ruta
        self.lineas = []
        self.externos = []          # [(nombre, linea)]
        self.etiquetas_def = set()
        self.simbolos = {}          # etiquetas de ESTE archivo -> dirección
        self.def_en = {}            # etiqueta -> Linea donde se definió
        self.stem = os.path.splitext(os.path.basename(ruta))[0]
        self.externa = False        # True si se cargó por .EXTERNAL


class Item:
    def __init__(self, addr, size, tipo, linea=None, datos=None):
        self.addr, self.size, self.tipo = addr, size, tipo
        self.linea, self.datos = linea, datos
        self.bytes = b""


def _sin_comentario(s):
    """Quita el comentario ';' respetando lo que está entre comillas."""
    salida, comillas, i = [], False, 0
    while i < len(s):
        c = s[i]
        if c == "\\" and comillas and i + 1 < len(s):
            salida.append(c + s[i + 1])
            i += 2
            continue
        if c == '"':
            comillas = not comillas
        if c == ";" and not comillas:
            break
        salida.append(c)
        i += 1
    return "".join(salida).rstrip()


def _es_numero(tok):
    return tok[0] in "#0123456789'" or bool(RE_HEX.match(tok))


def _valor_numero(tok):
    if tok[0] == "#":
        return int(tok[1:])
    if tok[0] == "'":
        c = tok[1:-1]
        if c.startswith("\\"):
            return ESCAPES[c[1]]
        return ord(c)
    if tok[:2].lower() == "0x":
        return int(tok, 16)
    if tok[:2].lower() == "0b":
        return int(tok[2:], 2)
    if RE_HEX.match(tok):
        return int(tok[1:], 16)
    return int(tok)


def marcas_de_texto(texto):
    """Conjunto de mnemónicos 'distintivos' que aparecen en un fuente
    (primer o segundo token de cada línea, o sea tras una posible etiqueta)."""
    vistas = set()
    for linea in texto.splitlines():
        s = _sin_comentario(linea).strip().replace(":", " ")
        for tok in s.split()[:2]:
            t = tok.upper().rstrip(",")
            if t in MARCAS_CLASICO or t in MARCAS_NUEVO:
                vistas.add(t)
                break
            if t in MNEMONICOS or t.startswith("."):
                break
    return vistas


def modo_de_marcas(marcas):
    """'clasico' | 'nuevo' | None (ambiguo)."""
    nuevo, clasico = marcas & MARCAS_NUEVO, marcas & MARCAS_CLASICO
    if nuevo:
        return "nuevo"
    return "clasico" if clasico else None


def leer_texto(ruta):
    with open(ruta, "rb") as f:
        crudo = f.read()
    if crudo.startswith(b"\xef\xbb\xbf"):       # BOM de UTF-8
        crudo = crudo[3:]
    try:                                      # UTF-8...
        return crudo.decode("utf-8")
    except UnicodeDecodeError:                # ...o, si no, Latin-1
        return crudo.decode("latin-1")


def detectar_modo(rutas):
    """Modo de uno o varios .asm: 'clasico' | 'nuevo' | None (ambiguo)."""
    marcas = set()
    for r in ([rutas] if isinstance(rutas, str) else rutas):
        try:
            marcas |= marcas_de_texto(leer_texto(r))
        except OSError:
            pass
    return modo_de_marcas(marcas)


# caché: (ruta, mtime, modo) -> etiquetas que define ese archivo
_CACHE_ETIQUETAS = {}


class Ensamblador:
    def __init__(self, modo="nuevo", dirs=None):
        """modo: 'nuevo' (ISA byte-addressable), 'clasico' (LC-3 original) o
        'auto' (se decide mirando el fuente). dirs: carpetas extra donde
        buscar los módulos de .EXTERNAL."""
        self.modo_cfg = modo
        self.dirs_cfg = list(dirs or [])
        self.clasico = (modo == "clasico")
        self.mnemonicos = CLASICOS if self.clasico else MNEMONICOS
        self.alias_unidad = {}
        self.pc = isa.ORIGEN_DEFECTO
        self.tabla_simbolos = {}
        self.codigo = bytearray()           # imagen (sin los 2 bytes de origen)
        self.instrucciones = dict(isa.OPCODES)
        self.origen = None
        self.unidades = []
        self.items = []
        self.errores = []
        self.advertencias = []
        self.alias_externos = {}    # nombre completo -> (archivo|None, etq)
        self._def_en = {}
        self.todos_simbolos = []    # [(nombre, dirección)] de todos los archivos
        self._u_actual = None       # unidad que se está resolviendo
        self._por_ruta = {}

    # ------------------------------------------------------------------ util
    def _err(self, linea, msg):
        self.errores.append(f"{linea.archivo}:{linea.nro}: error: {msg}\n"
                            f"    {linea.crudo.strip()}")

    def _adv(self, linea, msg):
        self.advertencias.append(f"{linea.archivo}:{linea.nro}: aviso: {msg}")

    def _reiniciar(self):
        self.__init__(self.modo_cfg if self.modo_cfg != "auto" else "auto",
                      self.dirs_cfg)

    def _fijar_modo(self, modo):
        self.clasico = (modo == "clasico")
        self.mnemonicos = CLASICOS if self.clasico else MNEMONICOS

    def _es_op(self, tok):
        t = tok.upper()
        return t in self.mnemonicos or t in DIRECTIVAS or t.startswith(".") \
            or RE_BR.match(t) is not None

    def _es_instruccion(self, op):
        return op in self.mnemonicos or RE_BR.match(op) is not None

    def _un(self, addr):
        """Dirección interna (bytes) -> unidad de la ISA (palabras en clásico)."""
        return addr // 2 if self.clasico else addr

    # --------------------------------------------------------------- parseo
    def _parsear(self, ruta, lineas):
        u = Unidad(ruta)
        pendientes = []
        for nro, crudo in enumerate(lineas, 1):
            crudo = crudo.rstrip("\r\n")
            s = _sin_comentario(crudo).strip()
            if not s:
                continue
            falso = Linea(ruta, nro, crudo, [], None, "")
            etiquetas = []
            while True:
                m = re.match(r"^([A-Za-z_]\w*)\s*:\s*(.*)$", s)
                if not m:
                    break
                etiquetas.append(m.group(1))
                s = m.group(2).strip()
            if s:
                primero = s.split(None, 1)[0]
                if not self._es_op(primero):
                    if not RE_IDENT.match(primero):
                        self._err(falso, f"no se entiende '{primero}'")
                        continue
                    etiquetas.append(primero)
                    s = s[len(primero):].strip()
                    if s:
                        sig = s.split(None, 1)[0]
                        if not self._es_op(sig):
                            # "LD R0, X": 'LD' no es instrucción (no 'R0,')
                            if re.match(r"^([Rr][0-7]\b|[#xX0-9'\-])", sig):
                                malo = primero
                            else:
                                malo = sig.rstrip(",")
                            self._err(falso, f"instrucción desconocida "
                                             f"'{malo}' (no existe en esta ISA)")
                            continue
            if not s:
                pendientes += etiquetas
                continue
            partes = s.split(None, 1)
            op = partes[0].upper()
            resto = partes[1].strip() if len(partes) > 1 else ""
            linea = Linea(ruta, nro, crudo, pendientes + etiquetas, op, resto)
            pendientes = []
            for e in linea.etiquetas:
                u.etiquetas_def.add(e)
            if op == ".END":
                if linea.etiquetas:
                    u.lineas.append(Linea(ruta, nro, crudo, linea.etiquetas,
                                          None, ""))
                break
            if op == ".EXTERNAL":
                if len(linea.args) != 1:
                    self._err(linea, ".EXTERNAL espera 1 nombre")
                else:
                    u.externos.append((linea.args[0], linea))
                continue
            u.lineas.append(linea)
        if pendientes:
            u.lineas.append(Linea(ruta, 0, "", pendientes, None, ""))
            u.etiquetas_def.update(pendientes)
        return u

    def _cargar_archivo(self, ruta):
        return self._parsear(ruta, leer_texto(ruta).splitlines())

    # ------------------------------------------------------------ .EXTERNAL
    def _dirs_busqueda(self, desde):
        """Dónde buscar módulos: la carpeta del archivo que los pide, su
        subcarpeta lib/, las carpetas extra (--lib) y el directorio actual."""
        base = os.path.dirname(os.path.abspath(desde))
        dirs = [base, os.path.join(base, "lib")] + [
            os.path.abspath(d) for d in self.dirs_cfg] + [
            os.getcwd(), os.path.join(os.getcwd(), "lib")]
        vistos, out = set(), []
        for d in dirs:
            if os.path.isdir(d) and os.path.realpath(d) not in vistos:
                vistos.add(os.path.realpath(d))
                out.append(d)
        return out

    def _buscar_archivo(self, nombre, desde):
        objetivo = {nombre.lower(), nombre.lower() + ".asm"}
        for d in self._dirs_busqueda(desde):
            try:
                for f in sorted(os.listdir(d)):
                    if f.lower() in objetivo:
                        return os.path.join(d, f)
            except OSError:
                pass
        return None

    def _etiquetas_de(self, ruta):
        """Etiquetas que define un archivo (con caché: la carpeta lib puede
        tener decenas de archivos y se consulta muchas veces)."""
        try:
            clave = (os.path.realpath(ruta), os.path.getmtime(ruta),
                     self.clasico)
        except OSError:
            return set()
        if clave not in _CACHE_ETIQUETAS:
            aux = Ensamblador("clasico" if self.clasico else "nuevo")
            try:
                _CACHE_ETIQUETAS[clave] = aux._cargar_archivo(ruta).etiquetas_def
            except OSError:
                _CACHE_ETIQUETAS[clave] = set()
        return _CACHE_ETIQUETAS[clave]

    def _buscar_por_etiqueta(self, nombre, arch, etq, u, l, cargadas):
        """Si no existe arch.asm, busca en las carpetas de búsqueda algún .asm
        que defina la etiqueta (el nombre del archivo puede no coincidir)."""
        cand = []
        for d in self._dirs_busqueda(u.ruta):
            try:
                nombres = sorted(os.listdir(d))
            except OSError:
                continue
            for f in nombres:
                ruta = os.path.join(d, f)
                if not f.lower().endswith(".asm") or \
                        os.path.realpath(ruta) in cargadas or ruta in cand:
                    continue
                if etq in self._etiquetas_de(ruta):
                    cand.append(ruta)
        if len(cand) == 1:
            falta = f"no existe '{arch}.asm'; " if arch else ""
            self._adv(l, f".EXTERNAL {nombre}: {falta}se usó "
                         f"{os.path.basename(cand[0])}, que define '{etq}'")
            return cand[0]
        if len(cand) > 1:
            self._err(l, f".EXTERNAL {nombre}: '{etq}' está definida en "
                         f"varios archivos ("
                         f"{', '.join(os.path.basename(c) for c in cand)}); "
                         f"pase el módulo correcto como argumento")
        return None

    def _resolver_externos(self):
        cargadas = {os.path.realpath(u.ruta) for u in self.unidades}
        i = 0
        while i < len(self.unidades):
            u = self.unidades[i]
            i += 1
            for nombre, l in u.externos:
                arch, etq = (nombre.rsplit("-", 1) if "-" in nombre
                             else (None, nombre))
                self.alias_externos[nombre] = (arch, etq)
                ya = [x for x in self.unidades if etq in x.etiquetas_def]
                if ya:
                    elegida = next((x for x in ya if arch and
                                    x.stem.lower() == arch.lower()), ya[0])
                    self.alias_unidad[nombre] = elegida
                    continue
                ruta = self._buscar_archivo(arch, u.ruta) if arch else None
                if ruta is None:
                    ruta = self._buscar_por_etiqueta(nombre, arch, etq, u, l,
                                                     cargadas)
                if ruta and os.path.realpath(ruta) not in cargadas:
                    cargadas.add(os.path.realpath(ruta))
                    nueva = self._cargar_archivo(ruta)
                    nueva.externa = True
                    self.unidades.append(nueva)
                    self.alias_unidad[nombre] = nueva

    # ------------------------------------------------------------ expresiones
    def _simbolo(self, nombre):
        """Primero las etiquetas del propio archivo; si no, las de otros
        archivos (que se cargaron por .EXTERNAL o por línea de comandos)."""
        u = self._u_actual
        if u is not None and nombre in u.simbolos:
            return u.simbolos[nombre]
        if nombre not in self.tabla_simbolos:
            raise ValueError(f"símbolo no definido: '{nombre}' "
                             f"(¿falta .EXTERNAL o pasar el módulo?)")
        return self.tabla_simbolos[nombre]

    def _simbolo_externo(self, nombre):
        """Resuelve  archivo-etiqueta  (o solo  etiqueta) de un .EXTERNAL.
        Con varios archivos que definan la misma etiqueta elige el que se
        llama como el archivo indicado."""
        arch, etq = self.alias_externos[nombre]
        u_alias = self.alias_unidad.get(nombre)
        if u_alias is not None and etq in u_alias.simbolos:
            return u_alias.simbolos[etq]
        if arch:
            for x in self.unidades:
                if x.stem.lower() == arch.lower() and etq in x.simbolos:
                    return x.simbolos[etq]
        for x in self.unidades:
            if x is not self._u_actual and etq in x.simbolos:
                return x.simbolos[etq]
        return self._simbolo(etq)

    def _evaluar(self, expr, simbolos=True):
        """Devuelve (valor, usa_simbolos)."""
        e = re.sub(r"\s+", "", expr)
        if not e:
            raise ValueError("operando vacío")
        if e in self.alias_externos:
            if not simbolos:
                raise ValueError("aquí se esperaba un número, no un símbolo")
            return self._simbolo_externo(e), True
        toks = RE_TOKEN.findall(e)
        if "".join(toks) != e:
            raise ValueError(f"expresión inválida '{expr}'")
        total, signo, espera, usa = 0, 1, True, False
        for t in toks:
            if t in "+-" and len(t) == 1:
                if espera:
                    if t == "-":
                        signo = -signo
                else:
                    signo = 1 if t == "+" else -1
                    espera = True
                continue
            if not espera:
                raise ValueError(f"expresión inválida '{expr}'")
            if _es_numero(t):
                v = _valor_numero(t)
            else:
                if not simbolos:
                    raise ValueError(
                        f"aquí se esperaba un número, no el símbolo '{t}'")
                v = self._simbolo(t)
                usa = True
            total += signo * v
            signo, espera = 1, False
        if espera:
            raise ValueError(f"expresión incompleta '{expr}'")
        return total, usa

    def _num(self, tok):
        return self._evaluar(tok, simbolos=False)[0]

    def _reg(self, tok):
        t = tok.upper()
        if t not in REGS:
            raise ValueError(f"se esperaba un registro R0..R7, no '{tok}'")
        return REGS[t]

    @staticmethod
    def _nargs(l, n):
        if len(l.args) != n:
            raise ValueError(f"{l.op} espera {n} operando(s) y recibió "
                             f"{len(l.args)}")

    def _pcrel(self, l, addr, tok, bits, campo):
        valor, usa = self._evaluar(tok)
        if not usa:
            return valor                    # offset numérico crudo
        if self.clasico:
            off = valor - (addr // 2 + 1)   # direcciones de palabra
        else:
            d = valor - (addr + 2)
            if d % 2:
                raise ValueError(
                    f"'{tok}' está en la dirección impar x{valor:04X}: no se "
                    f"puede alcanzar con offsets en palabras (alinee el dato)")
            off = d // 2
        lo, hi = -(1 << (bits - 1)), (1 << (bits - 1)) - 1
        if not lo <= off <= hi:
            raise ValueError(
                f"'{tok}' queda a {off} palabras: el campo {campo} admite "
                f"{lo}..{hi}. Acerque la etiqueta (por ejemplo, coloque las "
                f"constantes junto a la rutina que las usa)")
        return off

    # --------------------------------------------------------------- pasada 1
    def _definir(self, nombre, addr, l, u):
        if nombre.upper() in REGS:
            self._err(l, f"'{nombre}' no puede ser etiqueta (es un registro)")
        elif nombre in u.simbolos:
            a = u.def_en[nombre]
            self._err(l, f"etiqueta '{nombre}' repetida (ya definida en "
                         f"{a.archivo}:{a.nro})")
        else:
            addr = self._un(addr)
            u.simbolos[nombre] = addr
            u.def_en[nombre] = l
            self.todos_simbolos.append((nombre, addr))
            # tabla global: gana la primera definición (las demás solo se
            # alcanzan desde su propio archivo o con archivo-etiqueta)
            if nombre not in self.tabla_simbolos:
                self.tabla_simbolos[nombre] = addr
                self._def_en[nombre] = l

    def _cadena(self, l):
        m = re.match(r'^"(.*)"$', l.resto)
        if not m:
            raise ValueError('.STRINGZ espera una cadena entre comillas')
        s, out, i = m.group(1), bytearray(), 0
        while i < len(s):
            c = s[i]
            if c == "\\":
                if i + 1 >= len(s) or s[i + 1] not in ESCAPES:
                    raise ValueError(f"secuencia de escape inválida en "
                                     f"'{s}'")
                out.append(ESCAPES[s[i + 1]])
                i += 2
                continue
            if ord(c) > 255:
                raise ValueError(f"el carácter '{c}' no entra en 1 byte")
            out.append(ord(c))
            i += 1
        return bytes(out)

    def _pasada1(self):
        self.items, self.tabla_simbolos, self._def_en = [], {}, {}
        self.todos_simbolos = []
        self._por_ruta = {u.ruta: u for u in self.unidades}
        addr = isa.ORIGEN_DEFECTO * (2 if self.clasico else 1)
        fin = None                          # fin de lo ya emitido (bytes)
        for u in self.unidades:
            u.simbolos, u.def_en = {}, {}
            self._u_actual = u
            for l in u.lineas:
                op = l.op
                try:
                    if op == ".ORIG":
                        v = self._num(l.resto)
                        if not 0 <= v <= 0xFFFF:
                            raise ValueError(".ORIG debe estar en 0..xFFFF")
                        if v % 2 and not self.clasico:
                            raise ValueError(".ORIG debe ser par")
                        vb = v * 2 if self.clasico else v
                        if fin is not None and vb < fin:
                            if u.externa:
                                # módulo enlazado: lo ubica el enlazador a
                                # continuación de lo ya ensamblado
                                self._adv(l, f"módulo enlazado: se ignora "
                                             f".ORIG x{v:04X} (se ubica a "
                                             f"continuación)")
                                continue
                            raise ValueError(
                                f".ORIG x{v:04X} se solapa con lo ya "
                                f"ensamblado (llega hasta x{self._un(fin):04X})")
                        addr = vb
                    alinea = op in ALINEAN or (op and self._es_instruccion(op))
                    if alinea and addr % 2:
                        self.items.append(Item(addr, 1, "pad", l))
                        self._adv(l, f"relleno de 1 byte en x{addr:04X} para "
                                     f"alinear a dirección par")
                        addr += 1
                    for e in l.etiquetas:
                        self._definir(e, addr, l, u)
                    if op is None or op == ".ORIG" or op == ".ALIGN":
                        continue
                    if self.clasico and op in (".BLKB", ".BYTE"):
                        raise ValueError(f"{op} no existe en LC-3 clásico "
                                         f"(la memoria es de palabras)")
                    if op == ".FILL":
                        sz, dat = 2, None
                    elif op == ".BLKW":
                        sz, dat = 2 * self._num(l.resto), None
                    elif op == ".BLKB":
                        sz, dat = self._num(l.resto), None
                    elif op == ".BYTE":
                        dat = [x for x in re.split(r"\s*,\s*", l.resto) if x]
                        sz = len(dat)
                    elif op == ".STRINGZ":
                        dat = self._cadena(l)
                        sz = (len(dat) + 1) * (2 if self.clasico else 1)
                    elif self._es_instruccion(op):
                        sz, dat = 2, None
                    else:
                        raise ValueError(f"directiva/instrucción desconocida "
                                         f"'{op}'")
                    if sz < 0:
                        raise ValueError("tamaño negativo")
                    self.items.append(Item(addr, sz, op, l, dat))
                    addr += sz
                    fin = addr
                except ValueError as e:
                    self._err(l, str(e))
        for u in self.unidades:
            for nombre, l in u.externos:
                etq = self.alias_externos.get(nombre, (None, nombre))[1]
                if etq not in self.tabla_simbolos:
                    self._err(l, f".EXTERNAL {nombre}: no se encontró la "
                                 f"etiqueta '{etq}' en ningún archivo "
                                 f"(pase el módulo como argumento)")

    # --------------------------------------------------------------- pasada 2
    def _memoria(self, l, addr):
        """LDB/STB/LDH/STH y variantes."""
        op, a = l.op, l.args
        op = {"LDR": "LDH", "STR": "STH"}.get(op, op)
        h = None
        if op in ("LDBL", "LDBH", "STBL", "STBH"):
            h = 1 if op.endswith("H") else 0
            op = op[:3]
            self._nargs(l, 3)
        elif op in ("LDB", "STB"):
            if len(a) not in (3, 4):
                raise ValueError(f"{op} espera 3 o 4 operandos")
            h = 0
            if len(a) == 4:
                t = a[3].upper()
                h = {"H": 1, "L": 0, "#1": 1, "#0": 0}.get(t)
                if h is None:
                    raise ValueError("el 4º operando de LDB/STB es H o L")
        else:
            self._nargs(l, 3)
        r, base, off = self._reg(a[0]), self._reg(a[1]), self._num(a[2])
        if op in ("LDB", "STB"):
            return isa.codificar(op, dr=r, sr1=base, off=off, h=h)
        return isa.codificar(op, dr=r, sr1=base, off=off)

    def _instr_clasico(self, l, addr):
        op, a = l.op, l.args
        cod = isa_lc3.codificar
        if op in isa.TRAPS:
            self._nargs(l, 0)
            return cod("TRAP", vect=isa.TRAPS[op])
        m = RE_BR.match(op)
        if m:
            self._nargs(l, 1)
            letras = m.group(1)
            nzp = 7 if letras == "" else (
                (4 if "N" in letras else 0) | (2 if "Z" in letras else 0) |
                (1 if "P" in letras else 0))
            return cod("BR", nzp=nzp, off=self._pcrel(l, addr, a[0], 9,
                                                      "PCoffset9"))
        if op == "NOP":
            self._nargs(l, 0)
            return cod("BR", nzp=0, off=0)
        if op in ("ADD", "AND"):
            self._nargs(l, 3)
            if a[2].upper() in REGS:
                return cod(op, dr=self._reg(a[0]), sr1=self._reg(a[1]),
                           sr2=self._reg(a[2]))
            return cod(op, dr=self._reg(a[0]), sr1=self._reg(a[1]),
                       imm=self._num(a[2]))
        if op == "NOT":
            self._nargs(l, 2)
            return cod("NOT", dr=self._reg(a[0]), sr1=self._reg(a[1]))
        if op == "RET":
            self._nargs(l, 0)
            return cod("RET")
        if op in ("JMP", "JSRR"):
            self._nargs(l, 1)
            return cod(op, sr1=self._reg(a[0]))
        if op == "JSR":
            self._nargs(l, 1)
            return cod("JSR", off=self._pcrel(l, addr, a[0], 11, "PCoffset11"))
        if op in ("LD", "ST", "LDI", "STI", "LEA"):
            self._nargs(l, 2)
            return cod(op, dr=self._reg(a[0]),
                       off=self._pcrel(l, addr, a[1], 9, "PCoffset9"))
        if op in ("LDR", "STR"):
            self._nargs(l, 3)
            return cod(op, dr=self._reg(a[0]), sr1=self._reg(a[1]),
                       off=self._num(a[2]))
        if op == "TRAP":
            self._nargs(l, 1)
            return cod("TRAP", vect=self._num(a[0]))
        if op == "RTI":
            self._nargs(l, 0)
            return cod("RTI")
        raise ValueError(f"la instrucción '{op}' no existe en LC-3 clásico")

    def _instr(self, l, addr):
        if self.clasico:
            return self._instr_clasico(l, addr)
        op, a = l.op, l.args
        cod = isa.codificar
        if op in isa.TRAPS:
            self._nargs(l, 0)
            return cod("TRAP", vect=isa.TRAPS[op])
        m = RE_BR.match(op)
        if m:
            self._nargs(l, 1)
            f = m.group(1)
            nzp = 7 if not f else ((4 if "N" in f else 0) |
                                   (2 if "Z" in f else 0) |
                                   (1 if "P" in f else 0))
            return cod("BR", nzp=nzp,
                       off=self._pcrel(l, addr, a[0], 8, "PCoffset8"))
        if op == "NOP":
            self._nargs(l, 0)
            return cod("BR", nzp=0, off=0)
        if op in ("ADD", "AND"):
            self._nargs(l, 3)
            dr, s1 = self._reg(a[0]), self._reg(a[1])
            if a[2].upper() in REGS:
                return cod(op, dr=dr, sr1=s1, sr2=REGS[a[2].upper()])
            return cod(op, dr=dr, sr1=s1, imm=self._num(a[2]))
        if op == "MOV":
            self._nargs(l, 2)
            return cod("ADD", dr=self._reg(a[0]), sr1=self._reg(a[1]), imm=0)
        if op == "NOT":
            self._nargs(l, 2)
            return cod("NOT", dr=self._reg(a[0]), sr1=self._reg(a[1]))
        if op == "JMP":
            self._nargs(l, 1)
            return cod("JMP", sr1=self._reg(a[0]))
        if op == "RET":
            self._nargs(l, 0)
            return cod("RET")
        if op == "JSRR":
            self._nargs(l, 1)
            return cod("JSRR", sr1=self._reg(a[0]))
        if op == "JSR":
            self._nargs(l, 1)
            return cod("JSR", off=self._pcrel(l, addr, a[0], 10, "PCoffset10"))
        if op == "LEA":
            self._nargs(l, 2)
            return cod("LEA", dr=self._reg(a[0]),
                       off=self._pcrel(l, addr, a[1], 8, "PCoffset8"))
        if op == "RTI":
            self._nargs(l, 0)
            return cod("RTI")
        if op == "TRAP":
            self._nargs(l, 1)
            return cod("TRAP", vect=self._num(a[0]))
        if op in ("LDB", "STB", "LDBL", "LDBH", "STBL", "STBH", "LDH", "STH",
                  "LDR", "STR"):
            return self._memoria(l, addr)
        if op in ("LD", "ST"):
            self._nargs(l, 2)
            return cod(op, dr=self._reg(a[0]),
                       off=self._pcrel(l, addr, a[1], 8, "PCoffset8"))
        if op in ("MUL", "DIV", "MOD"):
            self._nargs(l, 3)
            return cod(op, dr=self._reg(a[0]), sr1=self._reg(a[1]),
                       sr2=self._reg(a[2]))
        if op == "SQR":
            self._nargs(l, 2)
            return cod("SQR", dr=self._reg(a[0]), sr1=self._reg(a[1]))
        if op == "SHF":
            self._nargs(l, 4)
            t = a[2].upper()
            if t not in isa.TIPOS_SHF:
                raise ValueError("tipo de SHF: SHL, SHR o SAR")
            return cod("SHF", dr=self._reg(a[0]), sr1=self._reg(a[1]),
                       tipo=isa.TIPOS_SHF.index(t), cant=self._num(a[3]))
        if op in ("SHL", "SHR", "SAR"):
            self._nargs(l, 3)
            return cod("SHF", dr=self._reg(a[0]), sr1=self._reg(a[1]),
                       tipo=isa.TIPOS_SHF.index(op), cant=self._num(a[2]))
        raise ValueError(f"instrucción desconocida '{op}'")

    def _pasada2(self):
        for it in self.items:
            l = it.linea
            self._u_actual = self._por_ruta.get(l.archivo)
            try:
                if it.tipo == "pad":
                    it.bytes = b"\x00"
                elif it.tipo == ".FILL":
                    v, _ = self._evaluar(l.resto)
                    if not -32768 <= v <= 0xFFFF:
                        raise ValueError(f".FILL {v} no entra en 16 bits")
                    it.bytes = isa.pack_word(v)
                elif it.tipo in (".BLKW", ".BLKB"):
                    it.bytes = bytes(it.size)
                elif it.tipo == ".BYTE":
                    out = bytearray()
                    for x in it.datos:
                        v, _ = self._evaluar(x)
                        if not -128 <= v <= 255:
                            raise ValueError(f".BYTE {v} no entra en 8 bits")
                        out.append(v & 0xFF)
                    it.bytes = bytes(out)
                elif it.tipo == ".STRINGZ":
                    if self.clasico:     # un carácter por palabra
                        it.bytes = b"".join(isa.pack_word(c) for c in it.datos
                                            ) + b"\x00\x00"
                    else:
                        it.bytes = it.datos + b"\x00"
                else:
                    it.bytes = isa.pack_word(self._instr(l, it.addr))
            except ValueError as e:
                self._err(l, str(e))
                it.bytes = bytes(it.size)

    # ------------------------------------------------------------------ API
    def _construir(self):
        if self.errores:
            raise ErrorEnsamblador(self.errores)
        self._resolver_externos()
        self._pasada1()
        if not self.items and not self.errores:
            self.errores.append("el programa no genera ningún byte")
        if not self.errores:
            self._pasada2()
        if self.errores:
            raise ErrorEnsamblador(self.errores)
        origen_b = self.items[0].addr
        self.origen = self._un(origen_b)
        fin = max(i.addr + i.size for i in self.items)
        self.codigo = bytearray(fin - origen_b)
        for it in self.items:
            self.codigo[it.addr - origen_b:
                        it.addr - origen_b + it.size] = it.bytes
        self.pc = fin

    def ensamblar(self, lineas, nombre="<texto>", verbose=False):
        """Compatible con el esqueleto: recibe una lista de líneas."""
        self._reiniciar()
        if self.modo_cfg == "auto":
            m = modo_de_marcas(marcas_de_texto("\n".join(lineas)))
            self._fijar_modo(m or "nuevo")
        self.unidades = [self._parsear(nombre, list(lineas))]
        self._construir()
        if verbose:
            print("Tabla de Símbolos:", self.tabla_simbolos)
            print("Tamaño del programa:", len(self.codigo), "bytes")
        return self.a_binario()

    def ensamblar_archivos(self, rutas):
        self._reiniciar()
        if self.modo_cfg == "auto":
            self._fijar_modo(detectar_modo(rutas) or "nuevo")
        for r in rutas:
            self.unidades.append(self._cargar_archivo(r))
        self._construir()
        return self.a_binario()

    def cargar_unidad(self, ruta, lineas=None):
        """Parsea un archivo (o las líneas dadas) y devuelve su Unidad; los
        errores de sintaxis quedan en self.errores."""
        if lineas is None:
            return self._cargar_archivo(ruta)
        return self._parsear(ruta, list(lineas))

    def ensamblar_unidades(self, unidades):
        """Ensambla juntas unidades ya parseadas (cargar_unidad). Se usa
        para el arnés de prueba del modo benchmark."""
        errores_previos = list(self.errores)
        modo = "clasico" if self.clasico else "nuevo"
        self.__init__(modo, self.dirs_cfg)
        self.errores = errores_previos
        self.unidades = list(unidades)
        self._construir()
        return self.a_binario()

    # ------------------------------------------------- información útil
    def items_instruccion(self):
        """Items que son instrucciones (no directivas ni relleno)."""
        return [it for it in self.items
                if it.tipo not in DIRECTIVAS and it.tipo != "pad"]

    def usa_halt(self):
        for it in self.items_instruccion():
            op, a = it.linea.op, it.linea.args
            if op == "HALT":
                return True
            if op == "TRAP" and a:
                try:
                    if self._num(a[0]) == isa.TRAPS["HALT"]:
                        return True
                except ValueError:
                    pass
        return False

    def usa_ret(self):
        """¿Tiene RET / JMP (o sea, vuelve a quien lo llamó)?"""
        return any(it.linea.op in ("RET", "JMP")
                   for it in self.items_instruccion())

    def entrada_modulo(self, stem=None):
        """(etiqueta, dirección) del punto de entrada de un módulo: la
        etiqueta que se llama como el archivo; si no hay, la de la primera
        instrucción; si tampoco, solo la dirección de la primera instrucción."""
        if stem:
            for nombre, addr in self.tabla_simbolos.items():
                if nombre.lower() == stem.lower():
                    return nombre, addr
        ins = self.items_instruccion()
        if not ins:
            return None, None
        for nombre in ins[0].linea.etiquetas:
            return nombre, self._un(ins[0].addr)
        return None, self._un(ins[0].addr)

    # -------------------------------------------------------------- salidas
    def a_binario(self):
        cab = isa_lc3.MAGIC if self.clasico else b""
        return cab + isa.pack_word(self.origen) + bytes(self.codigo)

    def a_hex(self):
        datos = self.a_binario()
        lineas = []
        if self.clasico:
            lineas.append("%s    ; LC-3 clásico (cabecera)"
                          % datos[:4].hex().upper())
            datos = datos[4:]
        lineas.append("%s    ; origen" % datos[:2].hex().upper())
        cuerpo = datos[2:]
        for i in range(0, len(cuerpo), 16):
            trozo = cuerpo[i:i + 16]
            grupos = [trozo[j:j + 2].hex().upper()
                      for j in range(0, len(trozo), 2)]
            lineas.append(" ".join(grupos))
        return "\n".join(lineas) + "\n"

    def listado(self):
        out = []
        desens = isa_lc3.desensamblar if self.clasico else isa.desensamblar
        for it in self.items:
            if it.tipo == "pad":
                out.append(f"{self._un(it.addr):04X}  00            ; relleno (alineación)")
                continue
            b = it.bytes
            fuente = it.linea.crudo.strip()
            if it.tipo in ("instr",) or (it.tipo not in DIRECTIVAS):
                texto = desens(isa.unpack_word(b[0], b[1]), self._un(it.addr))
                out.append(f"{self._un(it.addr):04X}  {b.hex().upper():<12}  "
                           f"{texto:<32} | {fuente}")
            else:
                for k in range(0, max(len(b), 1), 6):
                    trozo = b[k:k + 6].hex().upper()
                    out.append(f"{self._un(it.addr + k):04X}  {trozo:<12}  "
                               f"{'':<32} | {fuente if k == 0 else ''}")
        return "\n".join(out) + "\n"

    def simbolos_texto(self):
        return "".join(f"{n} {a:04X}\n" for n, a in
                       sorted(set(self.todos_simbolos),
                              key=lambda x: (x[1], x[0])))


def buscar_asm(carpeta, recursivo=False):
    """Lista ordenada de los .asm de una carpeta."""
    rutas = []
    if recursivo:
        for raiz, _, archivos in os.walk(carpeta):
            rutas += [os.path.join(raiz, f) for f in archivos
                      if f.lower().endswith(".asm")]
    else:
        rutas = [os.path.join(carpeta, f) for f in os.listdir(carpeta)
                 if f.lower().endswith(".asm")]
    return sorted(rutas, key=lambda r: r.lower())


def escribir_salidas(asm, base, organizar_formatos=False):
    """Escribe BASE.bin/.hex/.lst/.sym.
    Si organizar_formatos=True, separa en subcarpetas bin/, hex/, lst/, sym/
    dentro del directorio padre de `base`."""
    d = os.path.dirname(base)
    nombre = os.path.basename(base)
    if organizar_formatos:
        rutas = {}
        for ext in ("bin", "hex", "lst", "sym"):
            sub = os.path.join(d, ext) if d else ext
            os.makedirs(sub, exist_ok=True)
            rutas[ext] = os.path.join(sub, f"{nombre}.{ext}")
    else:
        if d:
            os.makedirs(d, exist_ok=True)
        rutas = {ext: f"{base}.{ext}" for ext in ("bin", "hex", "lst", "sym")}
    with open(rutas["bin"], "wb") as f:
        f.write(asm.a_binario())
    with open(rutas["hex"], "w", encoding="utf-8") as f:
        f.write(asm.a_hex())
    with open(rutas["lst"], "w", encoding="utf-8") as f:
        f.write(asm.listado())
    with open(rutas["sym"], "w", encoding="utf-8") as f:
        f.write(asm.simbolos_texto())
    return rutas


def modos_por_archivo(rutas, modo="auto"):
    """{ruta: 'nuevo'|'clasico'}. Con 'auto' se mira el fuente de cada
    archivo; los ambiguos (sin ninguna instrucción distintiva) adoptan el
    modo mayoritario de los demás archivos de la carpeta."""
    if modo in ("nuevo", "clasico"):
        return {r: modo for r in rutas}
    det = {r: detectar_modo(r) for r in rutas}
    votos = [m for m in det.values() if m]
    mayoria = max(set(votos), key=votos.count) if votos else "nuevo"
    return {r: (det[r] or mayoria) for r in rutas}


def ensamblar_principal(ruta, salida="build", modo="auto", dirs=None, organizar_formatos=False):
    """Ensambla UN programa principal; sus .EXTERNAL se buscan junto al
    archivo, en su subcarpeta lib/ y en `dirs`. Mismo formato de resultado
    que ensamblar_carpeta (una sola entrada)."""
    stem = os.path.splitext(os.path.basename(ruta))[0]
    m = modo if modo in ("nuevo", "clasico") else (
        detectar_modo(ruta) or "nuevo")
    r = {"nombre": os.path.basename(ruta), "ruta": ruta, "stem": stem,
         "ok": False, "errores": [], "avisos": [],
         "base": os.path.join(salida, stem), "origen": None, "tamano": 0,
         "es_programa": True, "n_instr": 0, "entrada": (None, None),
         "asm": None, "modo": m}
    asm = Ensamblador(m, dirs)
    try:
        asm.ensamblar_archivos([ruta])
        r["ok"] = True
    except ErrorEnsamblador as e:
        r["errores"] = list(e.errores)
    except OSError as e:
        r["errores"] = [f"{ruta}: no se pudo leer: {e}"]
    except Exception as e:
        r["errores"] = [f"{ruta}: excepción interna del ensamblador: "
                        f"{type(e).__name__}: {e}"]
    r["avisos"] = list(asm.advertencias)
    if r["ok"]:
        r["asm"] = asm
        r["origen"], r["tamano"] = asm.origen, len(asm.codigo)
        r["n_instr"] = len(asm.items_instruccion())
        r["rutas"] = escribir_salidas(asm, r["base"], organizar_formatos=organizar_formatos)
    return r


def ensamblar_carpeta(carpeta, salida="build", recursivo=False,
                      modo="auto", dirs=None, organizar_formatos=False):
    """Ensambla cada .asm de `carpeta` POR SEPARADO. Un fallo en un archivo
    (incluso una excepción interna) no detiene el lote.

    Devuelve una lista de dicts, uno por archivo:
      nombre, ruta, ok, errores, avisos, base (ruta sin extensión de salida),
      origen, tamano, es_programa (usa HALT), n_instr, entrada (etiqueta,
      dirección), asm (el Ensamblador, para quien quiera más detalle).
    """
    resultados = []
    rutas = buscar_asm(carpeta, recursivo)
    modos = modos_por_archivo(rutas, modo)
    for ruta in rutas:
        rel = os.path.relpath(ruta, carpeta)
        stem = os.path.splitext(rel)[0].replace(os.sep, "__")
        r = {"nombre": rel, "ruta": ruta, "stem": stem, "ok": False,
             "errores": [], "avisos": [], "base": os.path.join(salida, stem),
             "origen": None, "tamano": 0, "es_programa": False,
             "n_instr": 0, "entrada": (None, None), "asm": None,
             "modo": modos[ruta]}
        asm = Ensamblador(modos[ruta], dirs)
        try:
            asm.ensamblar_archivos([ruta])
            r["ok"] = True
        except ErrorEnsamblador as e:
            r["errores"] = list(e.errores)
        except OSError as e:
            r["errores"] = [f"{ruta}: no se pudo leer: {e}"]
        except Exception as e:             # bug del ensamblador: no matar el lote
            r["errores"] = [f"{ruta}: excepción interna del ensamblador: "
                            f"{type(e).__name__}: {e}"]
        r["avisos"] = list(asm.advertencias)
        if r["ok"]:
            r["asm"] = asm
            r["origen"], r["tamano"] = asm.origen, len(asm.codigo)
            r["n_instr"] = len(asm.items_instruccion())
            # módulo = subrutina (vuelve con RET y no tiene HALT)
            r["es_programa"] = asm.usa_halt() or not asm.usa_ret()
            r["entrada"] = asm.entrada_modulo(os.path.basename(stem))
            r["rutas"] = escribir_salidas(asm, r["base"], organizar_formatos=organizar_formatos)
        resultados.append(r)
    return resultados


def _main_carpeta(args):
    if not os.path.isdir(args.carpeta):
        print(f"No existe la carpeta: {args.carpeta}", file=sys.stderr)
        return 1
    res = ensamblar_carpeta(args.carpeta, args.salida_dir, args.recursivo,
                            args.modo, args.lib, organizar_formatos=args.organizar)
    if not res:
        print(f"No hay archivos .asm en {args.carpeta}", file=sys.stderr)
        return 1
    ok = 0
    print(f"{'archivo':<34} {'estado':<8} {'origen':<7} {'bytes':>6}  detalle")
    for r in res:
        if r["ok"]:
            ok += 1
            tipo = ("solo datos" if r["n_instr"] == 0 else
                    "programa" if r["es_programa"] else "módulo")
            print(f"{r['nombre']:<34} {'OK':<8} x{r['origen']:04X}   "
                  f"{r['tamano']:>6}  {tipo} [{r['modo']}], "
                  f"{len(r['avisos'])} aviso(s)")
        else:
            print(f"{r['nombre']:<34} {'ERROR':<8} {'-':<7} {'-':>6}  "
                  f"{len(r['errores'])} error(es)")
            for e in r["errores"][:3]:
                print("      " + e.replace("\n", "\n      "))
            if len(r["errores"]) > 3:
                print(f"      ... y {len(r['errores']) - 3} más")
    print(f"\n{ok}/{len(res)} ensamblados. Salidas en {args.salida_dir}/")
    return 0 if ok == len(res) else 1


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Ensamblador de la ISA-NZP (LC-3 expandida, byte-addressable)")
    ap.add_argument("archivos", nargs="*",
                    help="principal.asm seguido de los módulos .asm")
    ap.add_argument("-o", "--salida", help="nombre base de la salida")
    ap.add_argument("--carpeta", metavar="DIR",
                    help="modo lote: ensambla cada .asm de la carpeta")
    ap.add_argument("-d", "--salida-dir", default="build",
                    help="carpeta de salida del modo lote (def.: build)")
    ap.add_argument("-r", "--recursivo", action="store_true",
                    help="en modo lote, incluir subcarpetas")
    ap.add_argument("--modo", choices=["auto", "nuevo", "clasico"],
                    default="auto",
                    help="ISA del fuente: nuevo (byte-addressable), clasico "
                         "(LC-3 original) o auto (por defecto: se detecta)")
    ap.add_argument("--lib", action="append", default=[], metavar="DIR",
                    help="carpeta extra donde buscar los módulos de "
                         ".EXTERNAL (se puede repetir; ya se busca en la "
                         "carpeta del archivo y en su subcarpeta lib/)")
    ap.add_argument("--organizar", action="store_true",
                    help="separa las salidas en subcarpetas bin/, hex/, lst/, sym/")
    ap.add_argument("--permitir-sqr", action="store_true",
                    help="habilita SQR (prohibida por el enunciado)")
    args = ap.parse_args(argv)
    if args.permitir_sqr:
        isa.CONFIG["sqr"] = True
    if args.carpeta:
        return _main_carpeta(args)
    if not args.archivos:
        ap.error("indique archivos .asm o --carpeta DIR")
    asm = Ensamblador(args.modo, args.lib)
    try:
        asm.ensamblar_archivos(args.archivos)
    except ErrorEnsamblador as e:
        print("\n".join(e.errores), file=sys.stderr)
        print(f"\n{len(e.errores)} error(es). No se generó salida.",
              file=sys.stderr)
        return 1
    except OSError as e:
        print(f"No se pudo leer el archivo: {e}", file=sys.stderr)
        return 1
    for a in asm.advertencias:
        print(a, file=sys.stderr)
    base = args.salida or os.path.splitext(args.archivos[0])[0]
    rutas = escribir_salidas(asm, base, organizar_formatos=args.organizar)
    print(f"Modo: {'LC-3 clásico' if asm.clasico else 'ISA-NZP'}   "
          f"Origen: x{asm.origen:04X}   Tamaño: {len(asm.codigo)} bytes   "
          f"Símbolos: {len(asm.tabla_simbolos)}")
    print("Generados: " + "  ".join(rutas[e] for e in ("bin", "hex", "lst", "sym")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
