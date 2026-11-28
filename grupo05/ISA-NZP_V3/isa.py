# -*- coding: utf-8 -*-
"""
isa.py - Definición ÚNICA de la ISA-NZP (LC-3 expandida, byte-addressable).

Lo usan el ensamblador y el simulador, de modo que los formatos de bits viven
en un solo lugar. Los dos programas siguen siendo independientes: solo se
comunican a través del archivo binario/hex que genera el ensamblador.

Formatos (bits 15..11 = opcode de 5 bits; después, 11 bits):

  ADD reg  00001 DR SR1 00 SR2          ADD imm  00001 DR SR1 1 imm4
  AND reg  00101 DR SR1 00 SR2          AND imm  00101 DR SR1 1 imm4
  NOT      00101 DR SR 01000
  BR       00000 N Z P PCoffset8        JMP      01100 000 BaseR 00000
  JSR      00100 1 PCoffset10           RET      = JMP R7
  JSRR     00100 0 00 BaseR 00000       LEA      01110 DR PCoffset8
  RTI      01000 00000000000            TRAP     01111 0000 trapvect7
  LDB      00010 DR BaseR H offset4     STB      00011 SR BaseR H offset4
  LDH      00110 DR BaseR offset5       STH      00111 SR BaseR offset5
  MUL      01001 DR SR1 SR2 00          DIV      01010 DR SR1 SR2 00
  SHF      01011 DR SR tipo2 cant3      MOD      10001 DR SR1 SR2 00
  SQR      10000 DR SR 00000   (PROHIBIDA por el enunciado: deshabilitada)
  LD       10010 DR PCoffset8           ST       10011 SR PCoffset8
           (v2: carga/guarda una PALABRA en PC+2+2*offset; LD fija N,Z,P)
  LDR/STR  = alias de LDH/STH (misma codificación; offset en palabras)

Modos de direccionamiento:
  - registro / inmediato (ADD, AND: imm4 con signo, -8..7)
  - PC-relativo: BR (off8), LEA (off8), LD/ST (off8), JSR (off10). El offset se cuenta en
    PALABRAS: destino = (PC_de_la_instrucción + 2) + 2*offset
  - base + offset: LDH/STH (off5 en PALABRAS, x2), LDB/STB (off4 en BYTES)
  - registro indirecto: JMP, JSRR
  - vector de trap: TRAP (7 bits)
"""
from collections import namedtuple
from functools import lru_cache

ISA_NOMBRE = "ISA-NZP"

# ---------------------------------------------------------------------------
# Parámetros de la arquitectura
# ---------------------------------------------------------------------------
BIG_ENDIAN = True        # byte de mayor peso en la dirección más baja
ORIGEN_DEFECTO = 0x3000  # origen si el programa no tiene .ORIG
PILA_INICIAL = 0xFE00    # valor inicial de R6 que pone el simulador
SHF_CANT_MIN = 0         # SHF: cantidad = campo + SHF_CANT_MIN (con 1 se codifica 1..8)
CONFIG = {"sqr": False}  # SQR está prohibida por el enunciado: apagada por defecto

OPCODES = {
    "BR": 0b00000, "ADD": 0b00001, "LDB": 0b00010, "STB": 0b00011,
    "JSR": 0b00100, "JSRR": 0b00100, "AND": 0b00101, "NOT": 0b00101,
    "LDH": 0b00110, "STH": 0b00111, "RTI": 0b01000, "MUL": 0b01001,
    "DIV": 0b01010, "SHF": 0b01011, "JMP": 0b01100, "RET": 0b01100,
    "LEA": 0b01110, "TRAP": 0b01111, "SQR": 0b10000, "MOD": 0b10001,
    "LD": 0b10010, "ST": 0b10011,
}
TRAPS = {"GETC": 0x20, "OUT": 0x21, "PUTS": 0x22, "IN": 0x23,
         "PUTSP": 0x24, "HALT": 0x25}
TRAPS_INV = {v: k for k, v in TRAPS.items()}
TIPOS_SHF = ["SHL", "SHR", "SAR"]          # tipo2 = 00, 01, 10 (11 reservado)

Instr = namedtuple(
    "Instr", "mn dr sr1 sr2 imm off nzp h tipo cant vect",
    defaults=(None,) * 10)


class InstruccionInvalida(Exception):
    pass


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------
def sext(valor, bits):
    """Extensión de signo de un campo de `bits` bits."""
    valor &= (1 << bits) - 1
    return valor - (1 << bits) if valor & (1 << (bits - 1)) else valor


def a_signed16(v):
    return sext(v, 16)


def pack_word(w):
    """Palabra de 16 bits -> 2 bytes en el orden de la memoria."""
    w &= 0xFFFF
    hi, lo = w >> 8, w & 0xFF
    return bytes([hi, lo]) if BIG_ENDIAN else bytes([lo, hi])


def unpack_word(b0, b1):
    """b0 = byte en la dirección más baja, b1 = el siguiente."""
    return ((b0 << 8) | b1) if BIG_ENDIAN else ((b1 << 8) | b0)


def _rango(nombre, v, lo, hi):
    if not (lo <= v <= hi):
        raise ValueError(f"{nombre} = {v} fuera de rango ({lo}..{hi})")
    return v


def _reg(nombre, v):
    return _rango(nombre, v, 0, 7)


# ---------------------------------------------------------------------------
# Codificación
# ---------------------------------------------------------------------------
def codificar(mn, dr=0, sr1=0, sr2=0, imm=None, off=0, nzp=0, h=0,
              tipo=0, cant=0, vect=0):
    """Arma la palabra de 16 bits. En STB/STH el registro fuente va en `dr`."""
    mn = mn.upper()
    if mn == "RET":
        return codificar("JMP", sr1=7)
    op = OPCODES[mn] << 11
    if mn in ("ADD", "AND"):
        w = op | (_reg("DR", dr) << 8) | (_reg("SR1", sr1) << 5)
        if imm is not None:
            return w | 0x10 | (_rango("imm4", imm, -8, 7) & 0xF)
        return w | _reg("SR2", sr2)
    if mn == "NOT":
        return op | (_reg("DR", dr) << 8) | (_reg("SR", sr1) << 5) | 0b01000
    if mn == "BR":
        return (op | (_rango("nzp", nzp, 0, 7) << 8)
                | (_rango("PCoffset8", off, -128, 127) & 0xFF))
    if mn in ("JMP", "JSRR"):
        return op | (_reg("BaseR", sr1) << 5)
    if mn == "JSR":
        return op | (1 << 10) | (_rango("PCoffset10", off, -512, 511) & 0x3FF)
    if mn == "LEA":
        return (op | (_reg("DR", dr) << 8)
                | (_rango("PCoffset8", off, -128, 127) & 0xFF))
    if mn in ("LD", "ST"):          # en ST el registro fuente va en `dr`
        return (op | (_reg("DR/SR", dr) << 8)
                | (_rango("PCoffset8", off, -128, 127) & 0xFF))
    if mn == "RTI":
        return op
    if mn == "TRAP":
        return op | _rango("trapvect7", vect, 0, 127)
    if mn in ("LDB", "STB"):
        return (op | (_reg("DR/SR", dr) << 8) | (_reg("BaseR", sr1) << 5)
                | (_rango("H", h, 0, 1) << 4)
                | (_rango("offset4", off, -8, 7) & 0xF))
    if mn in ("LDH", "STH"):
        return (op | (_reg("DR/SR", dr) << 8) | (_reg("BaseR", sr1) << 5)
                | (_rango("offset5", off, -16, 15) & 0x1F))
    if mn in ("MUL", "DIV", "MOD"):
        return (op | (_reg("DR", dr) << 8) | (_reg("SR1", sr1) << 5)
                | (_reg("SR2", sr2) << 2))
    if mn == "SQR":
        if not CONFIG["sqr"]:
            raise ValueError(
                "SQR (raíz cuadrada por hardware) está prohibida por el "
                "enunciado del Lab 3; use --permitir-sqr solo si el grupo "
                "decide habilitarla")
        return op | (_reg("DR", dr) << 8) | (_reg("SR", sr1) << 5)
    if mn == "SHF":
        c = cant - SHF_CANT_MIN
        if not 0 <= c <= 7:
            raise ValueError(
                f"cantidad de desplazamiento {cant} fuera de rango "
                f"({SHF_CANT_MIN}..{SHF_CANT_MIN + 7}): el campo cantidad3 "
                f"tiene 3 bits")
        return (op | (_reg("DR", dr) << 8) | (_reg("SR", sr1) << 5)
                | (_rango("tipo", tipo, 0, 2) << 3) | c)
    raise ValueError(f"instrucción desconocida: {mn}")


# ---------------------------------------------------------------------------
# Decodificación (estricta: los bits que deben ser 0 se verifican)
# ---------------------------------------------------------------------------
@lru_cache(maxsize=None)
def decodificar(w):
    w &= 0xFFFF
    op = w >> 11
    dr = (w >> 8) & 7
    r2 = (w >> 5) & 7

    if op in (OPCODES["ADD"], OPCODES["AND"]):
        mn = "ADD" if op == OPCODES["ADD"] else "AND"
        if (w >> 4) & 1:
            return Instr(mn, dr=dr, sr1=r2, imm=sext(w & 0xF, 4))
        if not (w >> 3) & 1:
            return Instr(mn, dr=dr, sr1=r2, sr2=w & 7)
        if mn == "AND":
            if w & 7:
                raise InstruccionInvalida(
                    f"NOT con bits [2:0] distintos de 000 (0x{w:04X})")
            return Instr("NOT", dr=dr, sr1=r2)
        raise InstruccionInvalida(
            f"ADD con bits [4:3]=01 reservados (0x{w:04X})")
    if op == OPCODES["BR"]:
        return Instr("BR", nzp=(w >> 8) & 7, off=sext(w & 0xFF, 8))
    if op == OPCODES["JSR"]:
        if (w >> 10) & 1:
            return Instr("JSR", off=sext(w & 0x3FF, 10))
        if (w >> 8) & 3 or w & 0x1F:
            raise InstruccionInvalida(f"JSRR con bits reservados (0x{w:04X})")
        return Instr("JSRR", sr1=r2)
    if op == OPCODES["JMP"]:
        if dr or w & 0x1F:
            raise InstruccionInvalida(f"JMP con bits reservados (0x{w:04X})")
        return Instr("JMP", sr1=r2)
    if op == OPCODES["LEA"]:
        return Instr("LEA", dr=dr, off=sext(w & 0xFF, 8))
    if op == OPCODES["LD"]:
        return Instr("LD", dr=dr, off=sext(w & 0xFF, 8))
    if op == OPCODES["ST"]:
        return Instr("ST", dr=dr, off=sext(w & 0xFF, 8))
    if op == OPCODES["RTI"]:
        if w & 0x7FF:
            raise InstruccionInvalida(f"RTI con bits reservados (0x{w:04X})")
        return Instr("RTI")
    if op == OPCODES["TRAP"]:
        if (w >> 7) & 0xF:
            raise InstruccionInvalida(f"TRAP con bits [10:7] != 0 (0x{w:04X})")
        return Instr("TRAP", vect=w & 0x7F)
    if op in (OPCODES["LDB"], OPCODES["STB"]):
        mn = "LDB" if op == OPCODES["LDB"] else "STB"
        return Instr(mn, dr=dr, sr1=r2, h=(w >> 4) & 1, off=sext(w & 0xF, 4))
    if op in (OPCODES["LDH"], OPCODES["STH"]):
        mn = "LDH" if op == OPCODES["LDH"] else "STH"
        return Instr(mn, dr=dr, sr1=r2, off=sext(w & 0x1F, 5))
    if op in (OPCODES["MUL"], OPCODES["DIV"], OPCODES["MOD"]):
        mn = {OPCODES["MUL"]: "MUL", OPCODES["DIV"]: "DIV",
              OPCODES["MOD"]: "MOD"}[op]
        if w & 3:
            raise InstruccionInvalida(f"{mn} con bits [1:0] != 0 (0x{w:04X})")
        return Instr(mn, dr=dr, sr1=r2, sr2=(w >> 2) & 7)
    if op == OPCODES["SHF"]:
        tipo = (w >> 3) & 3
        if tipo == 3:
            raise InstruccionInvalida(
                f"SHF con tipo=11 reservado (0x{w:04X})")
        return Instr("SHF", dr=dr, sr1=r2, tipo=tipo,
                     cant=(w & 7) + SHF_CANT_MIN)
    if op == OPCODES["SQR"]:
        if w & 0x1F:
            raise InstruccionInvalida(f"SQR con bits [4:0] != 0 (0x{w:04X})")
        return Instr("SQR", dr=dr, sr1=r2)
    raise InstruccionInvalida(f"opcode reservado {op:05b} (0x{w:04X})")


# ---------------------------------------------------------------------------
# Desensamblado (el texto producido se puede volver a ensamblar)
# ---------------------------------------------------------------------------
def desensamblar(w, pc=None):
    w &= 0xFFFF
    try:
        i = decodificar(w)
    except InstruccionInvalida as e:
        return f".FILL x{w:04X}   ; inválida: {e}"
    mn = i.mn
    if mn in ("ADD", "AND"):
        if i.imm is not None:
            return f"{mn} R{i.dr}, R{i.sr1}, #{i.imm}"
        return f"{mn} R{i.dr}, R{i.sr1}, R{i.sr2}"
    if mn == "NOT":
        return f"NOT R{i.dr}, R{i.sr1}"
    if mn == "BR":
        if i.nzp == 0:
            if i.off == 0:
                return "NOP"
            return f".FILL x{w:04X}   ; BR con nzp=000 (nunca salta)"
        letras = ("n" if i.nzp & 4 else "") + ("z" if i.nzp & 2 else "") +                  ("p" if i.nzp & 1 else "")
        txt = f"BR{letras} #{i.off}"
        if pc is not None:
            txt += f"   ; -> x{(pc + 2 + 2 * i.off) & 0xFFFF:04X}"
        return txt
    if mn == "JMP":
        return "RET" if i.sr1 == 7 else f"JMP R{i.sr1}"
    if mn == "JSR":
        txt = f"JSR #{i.off}"
        if pc is not None:
            txt += f"   ; -> x{(pc + 2 + 2 * i.off) & 0xFFFF:04X}"
        return txt
    if mn == "JSRR":
        return f"JSRR R{i.sr1}"
    if mn in ("LEA", "LD", "ST"):
        txt = f"{mn} R{i.dr}, #{i.off}"
        if pc is not None:
            txt += f"   ; -> x{(pc + 2 + 2 * i.off) & 0xFFFF:04X}"
        return txt
    if mn == "RTI":
        return "RTI"
    if mn == "TRAP":
        return TRAPS_INV.get(i.vect, f"TRAP x{i.vect:02X}")
    if mn in ("LDB", "STB"):
        return f"{mn}{'H' if i.h else 'L'} R{i.dr}, R{i.sr1}, #{i.off}"
    if mn in ("LDH", "STH"):
        return f"{mn} R{i.dr}, R{i.sr1}, #{i.off}"
    if mn in ("MUL", "DIV", "MOD"):
        return f"{mn} R{i.dr}, R{i.sr1}, R{i.sr2}"
    if mn == "SQR":
        return f"SQR R{i.dr}, R{i.sr1}"
    if mn == "SHF":
        return f"{TIPOS_SHF[i.tipo]} R{i.dr}, R{i.sr1}, #{i.cant}"
    return f".FILL x{w:04X}"
