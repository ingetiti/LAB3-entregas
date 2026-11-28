# -*- coding: utf-8 -*-
"""
isa_lc3.py - LC-3 CLÁSICO (modo de compatibilidad).

Los módulos de la carpeta lib/ (y los programas principales que los llaman)
están escritos para el LC-3 original, no para ISA-NZP byte-addressable:

  - memoria de 65536 PALABRAS de 16 bits; toda dirección es una dirección de
    palabra (PC, punteros, R6...). PC += 1.
  - ADD/AND con inmediato de 5 bits (-16..15)
  - LD/ST/LDI/STI/LEA con PCoffset9 (±256 palabras), LDR/STR con offset6
  - JSR con PCoffset11, TRAP con vector de 8 bits
  - .STRINGZ guarda un carácter por palabra

Por eso no se pueden traducir 1 a 1 a la ISA nueva (los punteros y la pila
cambian de unidad). El ensamblador y el simulador tienen un modo clásico que
los ejecuta fielmente. Esos binarios llevan la cabecera MAGIC, y el simulador
elige el modo mirando esa cabecera.

Formatos (bits 15..12 = opcode):
  ADD 0001 DR SR1 0 00 SR2     ADD 0001 DR SR1 1 imm5
  AND 0101 ...                 NOT 1001 DR SR 111111
  BR  0000 nzp off9            JMP 1100 000 Base 000000  (RET = JMP R7)
  JSR 0100 1 off11             JSRR 0100 0 00 Base 000000
  LD  0010 DR off9             ST  0011 SR off9
  LDI 1010 DR off9             STI 1011 SR off9
  LDR 0110 DR Base off6        STR 0111 SR Base off6
  LEA 1110 DR off9             TRAP 1111 0000 vect8        RTI 1000 ...
"""
from isa import Instr, InstruccionInvalida, sext, pack_word  # noqa: F401

MAGIC = b"LC3C"            # primeros 4 bytes de un .bin clásico
LEA_FIJA_CC = False        # LEA no modifica N,Z,P (como en el LC-3 2ª ed.)

OPCODES = {"BR": 0, "ADD": 1, "LD": 2, "ST": 3, "JSR": 4, "JSRR": 4,
           "AND": 5, "LDR": 6, "STR": 7, "RTI": 8, "NOT": 9, "LDI": 10,
           "STI": 11, "JMP": 12, "RET": 12, "LEA": 14, "TRAP": 15}
MNEMONICOS = set(OPCODES) | {"NOP"}


def _rango(nombre, v, lo, hi):
    if not lo <= v <= hi:
        raise ValueError(f"{nombre} = {v} fuera de rango ({lo}..{hi})")
    return v


def _reg(nombre, v):
    return _rango(nombre, v, 0, 7)


def codificar(mn, dr=0, sr1=0, sr2=0, imm=None, off=0, nzp=0, vect=0):
    mn = mn.upper()
    if mn == "RET":
        return codificar("JMP", sr1=7)
    op = OPCODES[mn] << 12
    if mn in ("ADD", "AND"):
        w = op | (_reg("DR", dr) << 9) | (_reg("SR1", sr1) << 6)
        if imm is not None:
            return w | 0x20 | (_rango("imm5", imm, -16, 15) & 0x1F)
        return w | _reg("SR2", sr2)
    if mn == "NOT":
        return op | (_reg("DR", dr) << 9) | (_reg("SR", sr1) << 6) | 0x3F
    if mn == "BR":
        return (op | (_rango("nzp", nzp, 0, 7) << 9)
                | (_rango("PCoffset9", off, -256, 255) & 0x1FF))
    if mn == "JMP":
        return op | (_reg("BaseR", sr1) << 6)
    if mn == "JSRR":
        return op | (_reg("BaseR", sr1) << 6)
    if mn == "JSR":
        return op | 0x800 | (_rango("PCoffset11", off, -1024, 1023) & 0x7FF)
    if mn in ("LD", "ST", "LDI", "STI", "LEA"):
        return (op | (_reg("DR/SR", dr) << 9)
                | (_rango("PCoffset9", off, -256, 255) & 0x1FF))
    if mn in ("LDR", "STR"):
        return (op | (_reg("DR/SR", dr) << 9) | (_reg("BaseR", sr1) << 6)
                | (_rango("offset6", off, -32, 31) & 0x3F))
    if mn == "TRAP":
        return op | _rango("trapvect8", vect, 0, 255)
    if mn == "RTI":
        return op
    raise ValueError(f"instrucción desconocida: {mn}")


def decodificar(w):
    w &= 0xFFFF
    op, dr, sr1 = w >> 12, (w >> 9) & 7, (w >> 6) & 7
    if op in (1, 5):
        mn = "ADD" if op == 1 else "AND"
        if w & 0x20:
            return Instr(mn, dr=dr, sr1=sr1, imm=sext(w & 0x1F, 5))
        return Instr(mn, dr=dr, sr1=sr1, sr2=w & 7)
    if op == 9:
        return Instr("NOT", dr=dr, sr1=sr1)
    if op == 0:
        return Instr("BR", nzp=dr, off=sext(w & 0x1FF, 9))
    if op == 12:
        return Instr("JMP", sr1=sr1)
    if op == 4:
        if w & 0x800:
            return Instr("JSR", off=sext(w & 0x7FF, 11))
        return Instr("JSRR", sr1=sr1)
    if op in (2, 3, 10, 11, 14):
        mn = {2: "LD", 3: "ST", 10: "LDI", 11: "STI", 14: "LEA"}[op]
        return Instr(mn, dr=dr, off=sext(w & 0x1FF, 9))
    if op in (6, 7):
        return Instr("LDR" if op == 6 else "STR", dr=dr, sr1=sr1,
                     off=sext(w & 0x3F, 6))
    if op == 15:
        return Instr("TRAP", vect=w & 0xFF)
    if op == 8:
        return Instr("RTI")
    raise InstruccionInvalida(f"opcode reservado 1101 (0x{w:04X})")


def desensamblar(w, pc=None):
    """pc = dirección de palabra de la instrucción (opcional)."""
    from isa import TRAPS_INV
    w &= 0xFFFF
    try:
        i = decodificar(w)
    except InstruccionInvalida as e:
        return f".FILL x{w:04X}   ; inválida: {e}"
    mn = i.mn
    dest = (lambda: f"   ; -> x{(pc + 1 + i.off) & 0xFFFF:04X}") \
        if pc is not None else (lambda: "")
    if mn in ("ADD", "AND"):
        if i.imm is not None:
            return f"{mn} R{i.dr}, R{i.sr1}, #{i.imm}"
        return f"{mn} R{i.dr}, R{i.sr1}, R{i.sr2}"
    if mn == "NOT":
        return f"NOT R{i.dr}, R{i.sr1}"
    if mn == "BR":
        if i.nzp == 0:
            return "NOP" if i.off == 0 else f".FILL x{w:04X}"
        letras = ("n" if i.nzp & 4 else "") + ("z" if i.nzp & 2 else "") + \
                 ("p" if i.nzp & 1 else "")
        return f"BR{letras} #{i.off}" + dest()
    if mn == "JMP":
        return "RET" if i.sr1 == 7 else f"JMP R{i.sr1}"
    if mn == "JSR":
        return f"JSR #{i.off}" + dest()
    if mn == "JSRR":
        return f"JSRR R{i.sr1}"
    if mn in ("LD", "ST", "LDI", "STI", "LEA"):
        return f"{mn} R{i.dr}, #{i.off}" + dest()
    if mn in ("LDR", "STR"):
        return f"{mn} R{i.dr}, R{i.sr1}, #{i.off}"
    if mn == "TRAP":
        return TRAPS_INV.get(i.vect, f"TRAP x{i.vect:02X}")
    return mn
