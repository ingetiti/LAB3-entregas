#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ensamblador y enlazador de la ISA-G11.

Uso:
    python ensamblador.py principal.asm [modulo.asm ...] -o salida
                          [--lib CARPETA ...] [--formato bin hex dec] [--lst]

* El primer archivo es el programa principal (lleva .ORIG).  Los demas son
  modulos (subrutinas) que se ubican a continuacion.  El nombre de un modulo
  es el nombre del archivo, sin extension y en mayusculas.
* .EXTERNAL MODULO-ETIQUETA declara un simbolo definido en otro modulo; se
  puede usar en .FILL, LI, etc.  Con --lib los modulos que falten se buscan
  automaticamente en esas carpetas.
* Salidas: <salida>.bin (los 2 primeros bytes = direccion de origen, big-endian),
  <salida>.hex (una palabra de 4 digitos hex por linea, la primera es el
  origen) y <salida>.dec (idem en decimal).  --lst agrega <salida>.lst y .sym.
"""
import argparse
import os
import re
import sys

from isa import (COND, OPCODES, SHIFT_TYPES, UN_OPS,
                 TRAP_GETC, TRAP_OUT, TRAP_PUTS, TRAP_IN, TRAP_HALT, cond_inversa)


class ErrorAsm(Exception):
    pass


# ------------------------------------------------------------- mnemonicos
ALIAS_BR = {
    'BR': 'AL', 'BRNZP': 'AL', 'BRN': 'LT', 'BRZ': 'EQ', 'BRP': 'GT',
    'BRNZ': 'LE', 'BRNP': 'NE', 'BRZP': 'GE',
    'BAL': 'AL', 'BRL': 'AL', 'BEQ': 'EQ', 'BNE': 'NE', 'BLT': 'LT', 'BGE': 'GE',
    'BGT': 'GT', 'BLE': 'LE', 'BVS': 'VS', 'BVC': 'VC', 'BCS': 'CS',
    'BCC': 'CC', 'BSLT': 'SLT', 'BSGE': 'SGE', 'BSGT': 'SGT', 'BSLE': 'SLE',
    'BUGT': 'UGT',
}
R3 = {'ADD', 'ADC', 'SUB', 'SBC', 'AND', 'BIC', 'OR', 'XOR'}
# la ISA no tiene multiplicacion ni division por hardware
SIN_HARDWARE = {'MUL', 'MULH', 'MULHU', 'DIV', 'REM', 'DIVU', 'REMU'}
SHIFTS = set(SHIFT_TYPES)
UNARIAS = set(UN_OPS)
MEMBASE = {'LDW': 'LDW', 'LDBL': 'LDBL', 'LDBH': 'LDBH', 'STW': 'STW',
           'STBL': 'STBL', 'STBH': 'STBH', 'LDB': 'LDBL', 'STB': 'STBL'}
MEMX = {'LDX': 0, 'STX': 1, 'LDBX': 2, 'STBX': 3}
PCREL = {'LD', 'ST', 'LEA'}
OTROS = {'CMP', 'MOVI', 'MOVHI', 'LI', 'JSR', 'JSRR', 'JMP', 'RET', 'TRAP',
         'GETC', 'OUT', 'PUTS', 'IN', 'HALT', 'PUSH', 'POP', 'NOP'}
TODOS_MN = R3 | SHIFTS | UNARIAS | set(MEMBASE) | set(MEMX) | PCREL | OTROS | set(ALIAS_BR)
DIRECTIVAS = {'.ORIG', '.END', '.FILL', '.FILLB', '.BLKW', '.BLKB', '.STRINGZ',
              '.STRINGW', '.ALIGN', '.EXTERNAL'}
SIN_OPERANDOS = {'NOP', 'RET', 'GETC', 'OUT', 'PUTS', 'IN', 'HALT'}

REG_RE = re.compile(r'^R([0-7])$', re.I)


class Stmt:
    def __init__(self, mod, archivo, linea, texto):
        self.mod = mod
        self.archivo = archivo
        self.linea = linea
        self.texto = texto
        self.labels = []
        self.mnem = None
        self.ops = []
        self.kind = 'none'      # instr, fill, fillb, blkw, blkb, stringz, stringw, align, none
        self.n = 0
        self.addr = 0
        self.pad = 0
        self.size = 0
        self.larga = False      # salto condicional expandido (BRinv + BRL)

    def error(self, msg):
        return ErrorAsm(f'{self.archivo}:{self.linea}: {msg}\n    {self.texto.strip()}')


class Modulo:
    def __init__(self, nombre, archivo):
        self.nombre = nombre
        self.archivo = archivo
        self.stmts = []
        self.labels = {}
        self.externos = {}      # nombre completo -> (modulo, etiqueta)
        self.origen = None


# ----------------------------------------------------------------- parseo
def quitar_comentario(s):
    out = []
    q = None
    i = 0
    while i < len(s):
        ch = s[i]
        if q:
            out.append(ch)
            if ch == '\\' and i + 1 < len(s):
                out.append(s[i + 1])
                i += 1
            elif ch == q:
                q = None
        elif ch in '"\'':
            q = ch
            out.append(ch)
        elif ch == ';':
            break
        else:
            out.append(ch)
        i += 1
    return ''.join(out)


def tokenizar(s):
    toks, cur, q, i = [], [], None, 0
    while i < len(s):
        ch = s[i]
        if q:
            cur.append(ch)
            if ch == '\\' and i + 1 < len(s):
                cur.append(s[i + 1])
                i += 1
            elif ch == q:
                q = None
        elif ch in '"\'':
            q = ch
            cur.append(ch)
        elif ch in ' \t,':
            if cur:
                toks.append(''.join(cur))
                cur = []
        else:
            cur.append(ch)
        i += 1
    if cur:
        toks.append(''.join(cur))
    return toks


def es_mnem(t):
    u = t.upper()
    return u in TODOS_MN or u in DIRECTIVAS


def decodificar_cadena(tok, st):
    if len(tok) < 2 or tok[0] != '"' or tok[-1] != '"':
        raise st.error('se esperaba una cadena entre comillas')
    s = tok[1:-1]
    out, i = [], 0
    esc = {'n': '\n', 't': '\t', 'r': '\r', '0': '\0', '\\': '\\', '"': '"', "'": "'"}
    while i < len(s):
        if s[i] == '\\' and i + 1 < len(s):
            out.append(esc.get(s[i + 1], s[i + 1]))
            i += 2
        else:
            out.append(s[i])
            i += 1
    return ''.join(out)


def literal(tok):
    """Valor entero si `tok` es un literal numerico; si no, None."""
    t = tok.strip()
    m = re.fullmatch(r"'(\\.|[^\\])'", t)
    if m:
        c = m.group(1)
        if c.startswith('\\'):
            return ord({'n': '\n', 't': '\t', 'r': '\r', '0': '\0'}.get(c[1], c[1]))
        return ord(c)
    t = t.lstrip('#')
    m = re.fullmatch(r'([+-]?)(?:0[xX]([0-9A-Fa-f]+)|[xX]([0-9A-Fa-f]+)|0[bB]([01]+)|(\d+))', t)
    if not m:
        return None
    signo = -1 if m.group(1) == '-' else 1
    if m.group(2) or m.group(3):
        return signo * int(m.group(2) or m.group(3), 16)
    if m.group(4):
        return signo * int(m.group(4), 2)
    return signo * int(m.group(5), 10)


def parsear_modulo(texto, archivo, nombre):
    mod = Modulo(nombre, archivo)
    pend = []
    for nl, raw in enumerate(texto.splitlines(), 1):
        s = quitar_comentario(raw).strip()
        if not s:
            continue
        st = Stmt(mod, archivo, nl, raw)
        toks = tokenizar(s)
        # etiquetas
        while toks:
            t0 = toks[0]
            if t0.endswith(':') and len(t0) > 1:
                pend.append(t0[:-1].upper())
                toks = toks[1:]
                continue
            if t0.upper() in SIN_HARDWARE:
                raise st.error(f'{t0.upper()}: la ISA-G11 no tiene multiplicacion ni division por hardware '
                               '(se hacen por software)')
            if not es_mnem(t0):
                # etiqueta sin ':' -> debe ir sola o seguida de una instruccion/directiva; si lo que
                # sigue no se reconoce, la linea tiene un mnemonico mal escrito (no se descarta en silencio)
                if len(toks) > 1 and not (toks[1].endswith(':') or es_mnem(toks[1])
                                          or toks[1].upper() in SIN_HARDWARE):
                    raise st.error(f'instruccion o directiva desconocida: {t0}')
                pend.append(t0.upper())
                toks = toks[1:]
                continue
            break      # (una etiqueta con nombre de mnemonico debe llevar ':' -> "ASR: ...")
        if not toks:
            continue
        m = toks[0].upper()
        ops = toks[1:]
        st.mnem, st.ops = m, ops
        st.labels, pend = pend, []
        if m == '.END':
            mod.stmts_pendientes = st.labels
            if st.labels:
                st.kind = 'none'
                mod.stmts.append(st)
            break
        if m == '.ORIG':
            v = literal(ops[0]) if ops else None
            if v is None:
                raise st.error('.ORIG necesita una direccion numerica')
            mod.origen = v & 0xFFFF
            pend = st.labels
            continue
        if m == '.EXTERNAL':
            for o in ops:
                nom = o.upper()
                if '-' not in nom:
                    raise st.error('.EXTERNAL espera MODULO-ETIQUETA')
                mm, ll = nom.rsplit('-', 1)
                mod.externos[nom] = (mm, ll)
            pend = st.labels
            continue
        if m in DIRECTIVAS:
            st.kind = {'.FILL': 'fill', '.FILLB': 'fillb', '.BLKW': 'blkw', '.BLKB': 'blkb',
                       '.STRINGZ': 'stringz', '.STRINGW': 'stringw', '.ALIGN': 'align'}[m]
            if st.kind in ('blkw', 'blkb', 'align'):
                v = literal(ops[0]) if ops else None
                if v is None or v < 0:
                    raise st.error(f'{m} necesita una cantidad numerica')
                st.n = v
            if st.kind in ('stringz', 'stringw'):
                st.cadena = decodificar_cadena(ops[0], st) if ops else ''
        else:
            st.kind = 'instr'
        mod.stmts.append(st)
    if pend:
        st = Stmt(mod, archivo, 0, '')
        st.labels = pend
        mod.stmts.append(st)
    return mod


# --------------------------------------------------------------- programa
class Programa:
    def __init__(self):
        self.mods = []
        self.por_nombre = {}
        self.pcrel = set()        # (modulo, etiqueta) usados por LD/ST/LEA
        self.origen = 0x3000
        self.fin = 0

    def agregar(self, mod):
        if mod.nombre in self.por_nombre:
            raise ErrorAsm(f'modulo repetido: {mod.nombre}')
        self.mods.append(mod)
        self.por_nombre[mod.nombre] = mod

    # ---- valores
    def buscar(self, nombre, mod, st):
        n = nombre.upper()
        if n in mod.labels:
            return mod.labels[n]
        if n in mod.externos:
            mm, ll = mod.externos[n]
            if mm not in self.por_nombre:
                raise st.error(f'modulo no encontrado: {mm}')
            otro = self.por_nombre[mm]
            if ll not in otro.labels:
                raise st.error(f'el modulo {mm} no define {ll}')
            return otro.labels[ll]
        return None

    def evaluar(self, texto, mod, st):
        t = texto.strip()
        ph = {}
        for i, ext in enumerate(sorted(mod.externos, key=len, reverse=True)):
            pat = re.compile(re.escape(ext), re.I)
            if pat.search(t):
                t = pat.sub(f'@{i}@', t)
                ph[f'@{i}@'] = ext
        t = re.sub(r'#\s*', '', t)
        partes = re.findall(r'([+-]?)([^+-]+)', t)
        if not partes:
            raise st.error(f'expresion vacia: {texto!r}')
        total = 0
        for signo, term in partes:
            term = term.strip()
            if term in ph:
                v = self.buscar(ph[term], mod, st)
            else:
                v = self.buscar(term, mod, st) if not re.fullmatch(r"\d+|'.*'", term) else None
                if v is None:
                    v = literal(term)
                if v is None:
                    raise st.error(f'simbolo no definido: {term}')
            total += -v if signo == '-' else v
        return total

    # ---- tamanos
    def tam_instr(self, st):
        m = st.mnem
        o = st.ops
        if m in ALIAS_BR and ALIAS_BR[m] != 'AL' and st.larga:
            return 4
        if m == 'LI':
            v = literal(o[1]) if len(o) > 1 else None
            if v is not None:
                v &= 0xFFFF
                s = v - 0x10000 if v & 0x8000 else v
                return 2 if -128 <= s <= 127 else 4
            return 4
        if m == 'MOV' and len(o) == 2 and not REG_RE.match(o[1]):
            v = literal(o[1])
            if v is not None:
                v &= 0xFFFF
                s = v - 0x10000 if v & 0x8000 else v
                return 2 if -128 <= s <= 127 else 4
            return 4
        if m in SHIFTS and len(o) >= 2 and not REG_RE.match(o[-1]):
            v = literal(o[-1])
            if v is not None and v > 8:
                return 4
        return 2

    def tam(self, st):
        k = st.kind
        if k == 'instr':
            return self.tam_instr(st)
        if k == 'fill':
            return 2
        if k == 'fillb':
            return len(st.ops)
        if k == 'blkw':
            return 2 * st.n
        if k == 'blkb':
            return st.n
        if k == 'stringz':
            return len(st.cadena.encode('utf-8')) + 1
        if k == 'stringw':
            return 2 * (len(st.cadena) + 1)
        return 0

    # ---- registro de etiquetas con LD/ST/LEA
    def detectar_pcrel(self):
        for mod in self.mods:
            for st in mod.stmts:
                if st.kind == 'instr' and st.mnem in PCREL and len(st.ops) >= 2:
                    t = st.ops[1].strip()
                    for ext in mod.externos:
                        if t.upper().startswith(ext):
                            mm, ll = mod.externos[ext]
                            self.pcrel.add((mm, ll))
                            break
                    else:
                        ident = re.match(r'[A-Za-z_][\w$]*', t)
                        if ident:
                            self.pcrel.add((mod.nombre, ident.group(0).upper()))

    # ---- disposicion en memoria
    def disponer(self):
        self.detectar_pcrel()
        if self.mods and self.mods[0].origen is not None:
            self.origen = self.mods[0].origen
        for _ in range(50):
            addr = self.origen
            for mod in self.mods:
                mod.labels = {}
                for st in mod.stmts:
                    k = st.kind
                    ali = 1
                    if k in ('instr', 'fill', 'blkw', 'stringw'):
                        ali = 2
                    elif k == 'align':
                        ali = max(1, st.n)
                    if any((mod.nombre, l) in self.pcrel for l in st.labels):
                        ali = max(ali, 4)
                    pad = (-addr) % ali
                    addr += pad
                    st.pad, st.addr = pad, addr
                    for l in st.labels:
                        if l in mod.labels:
                            raise st.error(f'etiqueta repetida: {l}')
                        mod.labels[l] = addr
                    st.size = self.tam(st)
                    addr += st.size
            if addr % 2:
                addr += 1
            self.fin = addr
            cambio = False
            for mod in self.mods:
                for st in mod.stmts:
                    if (st.kind == 'instr' and st.mnem in ALIAS_BR
                            and ALIAS_BR[st.mnem] != 'AL' and not st.larga):
                        if not st.ops:
                            raise st.error('falta el destino del salto')
                        dest = self.evaluar(st.ops[0], mod, st)
                        off = (dest - (st.addr + 2)) // 2
                        if (dest - (st.addr + 2)) % 2 or not -64 <= off <= 63:
                            if (dest - (st.addr + 2)) % 2 == 0:
                                if COND[ALIAS_BR[st.mnem]] == COND['UGT']:
                                    raise st.error('BUGT fuera de rango (no se puede invertir)')
                                st.larga = True
                                cambio = True
            if not cambio:
                return
        raise ErrorAsm('no converge la expansion de saltos')

    # ---- codificacion
    def codificar(self, st, mod):
        m = st.mnem
        o = list(st.ops)
        A = st.addr

        def reg(t):
            mm = REG_RE.match(t.strip())
            if not mm:
                raise st.error(f'se esperaba un registro, se encontro {t!r}')
            return int(mm.group(1))

        def es_reg(t):
            return REG_RE.match(t.strip()) is not None

        def val(t):
            return self.evaluar(t, mod, st)

        def rango(v, lo, hi, que):
            if not lo <= v <= hi:
                raise st.error(f'{que} fuera de rango: {v} (permitido {lo}..{hi})')
            return v

        def n_ops(n, *otros):
            if len(o) not in (n,) + otros:
                raise st.error(f'{m} espera {n} operando(s), recibio {len(o)}')

        def R(op, dr, s1, s2, f):
            return (OPCODES[op] << 11) | (dr << 8) | (s1 << 5) | (s2 << 2) | f

        def I5(op, dr, s1, imm):
            return (OPCODES[op] << 11) | (dr << 8) | (s1 << 5) | (imm & 31)

        def I8(op, dr, imm):
            return (OPCODES[op] << 11) | (dr << 8) | (imm & 255)

        if m == 'NOP':
            return [0]
        if m in R3:
            if len(o) == 2:
                o = [o[0], o[0], o[1]]
            n_ops(3)
            dr, s1 = reg(o[0]), reg(o[1])
            if es_reg(o[2]):
                s2 = reg(o[2])
                tabla = {'ADD': ('ADD', 0), 'ADC': ('ADD', 1), 'SUB': ('SUB', 0), 'SBC': ('SUB', 1),
                         'AND': ('AND', 0), 'BIC': ('AND', 1), 'OR': ('OR', 0), 'XOR': ('OR', 1)}
                op, f = tabla[m]
                return [R(op, dr, s1, s2, f)]
            v = val(o[2])
            if m == 'ADD':
                return [I5('ADDI', dr, s1, rango(v, -16, 15, 'inmediato'))]
            if m == 'SUB':
                return [I5('ADDI', dr, s1, rango(-v, -16, 15, 'inmediato (negado)'))]
            if m == 'AND':
                return [I5('ANDI', dr, s1, rango(v, -16, 15, 'inmediato'))]
            raise st.error(f'{m} no admite inmediato: cargue la constante con LI y use registros')
        if m in SHIFTS:
            if len(o) == 2:
                o = [o[0], o[0], o[1]]
            n_ops(3)
            dr, s1 = reg(o[0]), reg(o[1])
            tipo = SHIFT_TYPES[m]
            if es_reg(o[2]):
                return [R('SHR', dr, s1, reg(o[2]), tipo)]
            v = rango(val(o[2]), 0, 16, 'cantidad de desplazamiento')
            if v == 0:
                return [(OPCODES['UN'] << 11) | (dr << 8) | (s1 << 5) | UN_OPS['MOV']]
            words, src = [], s1
            while v > 0:
                paso = min(8, v)
                words.append((OPCODES['SHI'] << 11) | (dr << 8) | (src << 5) | (tipo << 3) | (paso - 1))
                src = dr
                v -= paso
            return words
        if m in UNARIAS:
            if m == 'MOV' and len(o) == 2 and not es_reg(o[1]):
                m = 'LI'
            else:
                if len(o) == 1:
                    o = [o[0], o[0]]
                n_ops(2)
                dr, s1 = reg(o[0]), reg(o[1])
                return [(OPCODES['UN'] << 11) | (dr << 8) | (s1 << 5) | UN_OPS[m]]
        if m == 'CMP':
            n_ops(2)
            s1 = reg(o[0])
            if es_reg(o[1]):
                return [R('CMP', 0, s1, reg(o[1]), 0)]
            return [I8('CMPI', s1, rango(val(o[1]), -128, 127, 'inmediato'))]
        if m == 'MOVI':
            n_ops(2)
            return [I8('MOVI', reg(o[0]), rango(val(o[1]), -128, 127, 'inmediato'))]
        if m == 'MOVHI':
            n_ops(2)
            return [I8('MOVHI', reg(o[0]), rango(val(o[1]), -128, 255, 'inmediato'))]
        if m == 'LI':
            n_ops(2)
            dr = reg(o[0])
            v = val(o[1])
            rango(v, -32768, 65535, 'valor')
            if st.size == 2:
                return [I8('MOVI', dr, v)]
            v &= 0xFFFF
            return [I8('MOVI', dr, v & 255), I8('MOVHI', dr, (v >> 8) & 255)]
        if m in MEMBASE:
            n_ops(3)
            op = MEMBASE[m]
            dr, b = reg(o[0]), reg(o[1])
            off = val(o[2])
            if op in ('LDW', 'STW'):
                if off % 2:
                    raise st.error(f'el desplazamiento de {m} debe ser par (es {off})')
                rango(off // 2, -16, 15, 'desplazamiento/2')
                return [I5(op, dr, b, off // 2)]
            return [I5(op, dr, b, rango(off, -16, 15, 'desplazamiento'))]
        if m in MEMX:
            n_ops(3)
            return [R('LDWX', reg(o[0]), reg(o[1]), reg(o[2]), MEMX[m])]
        if m in PCREL:
            n_ops(2)
            dr = reg(o[0])
            dest = val(o[1])
            base = (A + 2) & ~3
            if dest % 4:
                raise st.error(f'destino {dest:#06x} no alineado a 4 bytes (use una etiqueta)')
            off = (dest - base) // 4
            rango(off, -128, 127, 'desplazamiento PC-relativo')
            return [I8(m, dr, off)]
        if m in ALIAS_BR:
            n_ops(1)
            dest = val(o[0])
            if dest % 2:
                raise st.error('destino de salto en direccion impar')
            cond = COND[ALIAS_BR[m]]
            if cond == COND['AL']:
                off = (dest - (A + 2)) // 2
                return [(OPCODES['BRL'] << 11) | (rango(off, -1024, 1023, 'desplazamiento de salto') & 0x7FF)]
            if not st.larga:
                off = (dest - (A + 2)) // 2
                return [(OPCODES['BR'] << 11) | (cond << 7) | (off & 127)]
            inv = cond_inversa(cond)
            w1 = (OPCODES['BR'] << 11) | (inv << 7) | 1          # salta la BRL siguiente
            off = (dest - (A + 4)) // 2
            w2 = (OPCODES['BRL'] << 11) | (rango(off, -1024, 1023, 'desplazamiento de salto') & 0x7FF)
            return [w1, w2]
        if m == 'JSR':
            n_ops(1)
            dest = val(o[0])
            if dest % 2:
                raise st.error('destino de JSR en direccion impar')
            off = (dest - (A + 2)) // 2
            return [(OPCODES['JSR'] << 11) | (rango(off, -1024, 1023, 'desplazamiento de JSR') & 0x7FF)]
        if m == 'JSRR':
            n_ops(1)
            return [(OPCODES['JR'] << 11) | (reg(o[0]) << 8) | 0x80]
        if m == 'JMP':
            n_ops(1)
            return [(OPCODES['JR'] << 11) | (reg(o[0]) << 8)]
        if m == 'RET':
            n_ops(0)
            return [(OPCODES['JR'] << 11) | (7 << 8)]
        if m in ('PUSH', 'POP'):
            n_ops(1)
            return [(OPCODES['STK'] << 11) | (reg(o[0]) << 8) | (0x80 if m == 'POP' else 0)]
        if m == 'TRAP':
            n_ops(1)
            return [(OPCODES['TRAP'] << 11) | (rango(val(o[0]), 0, 255, 'vector') & 255)]
        if m in ('GETC', 'OUT', 'PUTS', 'IN', 'HALT'):
            n_ops(0)
            v = {'GETC': TRAP_GETC, 'OUT': TRAP_OUT, 'PUTS': TRAP_PUTS, 'IN': TRAP_IN, 'HALT': TRAP_HALT}[m]
            return [(OPCODES['TRAP'] << 11) | v]
        raise st.error(f'instruccion desconocida: {m}')

    def datos(self, st, mod):
        k = st.kind
        o = st.ops
        if k == 'fill':
            if len(o) != 1:
                raise st.error('.FILL espera un valor')
            v = self.evaluar(o[0], mod, st)
            if not -32768 <= v <= 65535:
                raise st.error(f'.FILL fuera de rango: {v}')
            v &= 0xFFFF
            return bytes([v >> 8, v & 255])
        if k == 'fillb':
            out = bytearray()
            for t in o:
                v = self.evaluar(t, mod, st)
                if not -128 <= v <= 255:
                    raise st.error(f'.FILLB fuera de rango: {v}')
                out.append(v & 255)
            return bytes(out)
        if k == 'blkw':
            return bytes(2 * st.n)
        if k == 'blkb':
            return bytes(st.n)
        if k == 'stringz':
            return st.cadena.encode('utf-8') + b'\0'
        if k == 'stringw':
            out = bytearray()
            for c in st.cadena + '\0':
                out += bytes([(ord(c) >> 8) & 255, ord(c) & 255])
            return bytes(out)
        return b''

    def ensamblar(self):
        self.disponer()
        img = bytearray(self.fin - self.origen)
        self.lst = []
        self.estad = {'codigo': 0, 'datos': 0, 'relleno': 0, 'instr': 0, 'por_modulo': {}}
        for mod in self.mods:
            cod = dat = 0
            for st in mod.stmts:
                self.estad['relleno'] += st.pad
                if st.kind == 'instr':
                    ws = self.codificar(st, mod)
                    if len(ws) * 2 != st.size:
                        raise st.error(f'tamano inconsistente ({len(ws) * 2} vs {st.size})')
                    b = b''.join(bytes([w >> 8, w & 255]) for w in ws)
                    cod += st.size
                    self.estad['instr'] += len(ws)
                elif st.kind == 'none' or st.kind == 'align':
                    b = b''
                else:
                    b = self.datos(st, mod)
                    dat += st.size
                if b:
                    img[st.addr - self.origen: st.addr - self.origen + len(b)] = b
                if st.linea or b:
                    self.lst.append((st.addr, b, st))
            self.estad['codigo'] += cod
            self.estad['datos'] += dat
            self.estad['por_modulo'][mod.nombre] = (cod, dat)
        self.imagen = bytes(img)
        return self.imagen

    # ---- salidas
    def escribir(self, base, formatos, lst):
        origen = self.origen
        palabras = [(self.imagen[i] << 8) | self.imagen[i + 1] for i in range(0, len(self.imagen), 2)]
        salidas = []
        if 'bin' in formatos:
            with open(base + '.bin', 'wb') as f:
                f.write(bytes([origen >> 8, origen & 255]) + self.imagen)
            salidas.append(base + '.bin')
        if 'hex' in formatos:
            with open(base + '.hex', 'w') as f:
                f.write(f'{origen:04X}\n')
                f.write(''.join(f'{w:04X}\n' for w in palabras))
            salidas.append(base + '.hex')
        if 'dec' in formatos:
            with open(base + '.dec', 'w') as f:
                f.write(f'{origen}\n')
                f.write(''.join(f'{w}\n' for w in palabras))
            salidas.append(base + '.dec')
        if lst:
            with open(base + '.lst', 'w', encoding='utf-8') as f:
                for addr, b, st in self.lst:
                    f.write(f'{addr:04X}  {b[:6].hex().upper():<12}  {st.mod.nombre}:{st.linea:<4} {st.texto.rstrip()}\n')
            with open(base + '.sym', 'w', encoding='utf-8') as f:
                for mod in self.mods:
                    for l, a in sorted(mod.labels.items(), key=lambda x: x[1]):
                        f.write(f'{a:04X}  {mod.nombre}-{l}\n')
            salidas += [base + '.lst', base + '.sym']
        return salidas


def cargar(archivos, libs):
    prog = Programa()
    for i, ruta in enumerate(archivos):
        nombre = os.path.splitext(os.path.basename(ruta))[0].upper()
        with open(ruta, encoding='utf-8', errors='replace') as f:
            prog.agregar(parsear_modulo(f.read(), ruta, nombre))
    # modulos que faltan: buscarlos en --lib
    cambio = True
    while cambio:
        cambio = False
        for mod in list(prog.mods):
            for mm, _ in list(mod.externos.values()):
                if mm in prog.por_nombre:
                    continue
                for d in libs:
                    for fn in os.listdir(d):
                        stem, ext = os.path.splitext(fn)
                        if ext.lower() == '.asm' and stem.upper() == mm:
                            ruta = os.path.join(d, fn)
                            with open(ruta, encoding='utf-8', errors='replace') as f:
                                prog.agregar(parsear_modulo(f.read(), ruta, mm))
                            cambio = True
                            break
                    if mm in prog.por_nombre:
                        break
    return prog


def main(argv=None):
    ap = argparse.ArgumentParser(description='Ensamblador/enlazador de la ISA-G11')
    ap.add_argument('archivos', nargs='+', help='principal.asm [modulos.asm ...]')
    ap.add_argument('-o', '--salida', help='nombre base de salida (por defecto, el del principal)')
    ap.add_argument('--lib', action='append', default=[], help='carpeta donde buscar modulos .EXTERNAL')
    ap.add_argument('--formato', nargs='+', default=['bin', 'hex'], choices=['bin', 'hex', 'dec'])
    ap.add_argument('--lst', action='store_true', help='genera listado (.lst) y tabla de simbolos (.sym)')
    a = ap.parse_args(argv)
    try:
        prog = cargar(a.archivos, a.lib)
        prog.ensamblar()
    except ErrorAsm as e:
        print('ERROR:', e, file=sys.stderr)
        return 1
    base = a.salida or os.path.splitext(a.archivos[0])[0]
    salidas = prog.escribir(base, a.formato, a.lst)
    e = prog.estad
    print(f'Ensamblado: origen x{prog.origen:04X}, {len(prog.imagen)} bytes ({len(prog.imagen) // 2} palabras)')
    print(f'  instrucciones: {e["instr"]} ({e["codigo"]} bytes) | datos: {e["datos"]} bytes | relleno de alineacion: {e["relleno"]} bytes')
    for n, (c, d) in e['por_modulo'].items():
        print(f'  - {n}: codigo {c} B, datos {d} B')
    print('Salidas:', ', '.join(salidas))
    return 0


if __name__ == '__main__':
    sys.exit(main())
