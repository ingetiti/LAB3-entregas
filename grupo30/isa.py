"""
isa.py - Definición de la ISA Skynet (16 bits)
============================================================
Única fuente de verdad: constantes, 32 opcodes, formatos de instrucción,
codificadores, decodificadores, utilidades numéricas y desensamblador.
Lo importan core.py, sim.py, assembler.py, debugger.py y los tests.
"""

from typing import Dict, Optional

# ---------------- Constantes de la máquina ----------------
MEM_SIZE = 1 << 16          # 65.536 bytes (byte-addressable, Little-Endian)
INSTR_SIZE = 2              # bytes por instrucción; PC avanza de a 2
NUM_REGS = 8                # R0..R7 de 16 bits
SP_REG = 6                  # R6 es el puntero de pila (SP)
SP_INIT = 0xFE00            # Valor inicial de R6 al reset
LINK_REG = 7                # R7 recibe PC+2 en JSR/JSRR/TRAP
DEFAULT_ORIGIN = 0x3000     # Dirección de inicio por defecto
OPCODE_SHIFT = 11           # Opcode de 5 bits en [15:11]
MASK8 = 0xFF
MASK16 = 0xFFFF
MASK32 = 0xFFFFFFFF

NOP_INSTR = 0x0000          # BR nzp=000, off8=0 (no salta, no altera NZP)
RET_INSTR = 0x60E0          # JMP R7 (01100 000 111 00000)

# ---------------- Mapa definitivo de los 32 opcodes (5 bits) ----------------
# Bloque A (00000 - 01111)
OP_BR    = 0   # 00000: BR / NOP
OP_ADD   = 1   # 00001: ADD (registro o imm4)
OP_LD    = 2   # 00010: LD (PCoffset8)
OP_ST    = 3   # 00011: ST (PCoffset8)
OP_JSR   = 4   # 00100: JSR / JSRR
OP_AND   = 5   # 00101: AND (registro o imm4)
OP_LDR   = 6   # 00110: LDR (BaseR + 2*off5, alineado)
OP_STR   = 7   # 00111: STR (BaseR + 2*off5, alineado)
OP_LDB   = 8   # 01000: LDB (BaseR + off5, sign-extend)
OP_NOT   = 9   # 01001: NOT (~SR1)
OP_LDH   = 10  # 01010: LDH (BaseR + off5 -> DR[15:8], conserva DR[7:0])
OP_STH   = 11  # 01011: STH (SR[15:8] -> BaseR + off5)
OP_JMP   = 12  # 01100: JMP / RET (RET = JMP R7)
OP_STB   = 13  # 01101: STB (SR[7:0] -> BaseR + off5)
OP_LEA   = 14  # 01110: LEA (PCoffset8, no modifica NZP)
OP_TRAP  = 15  # 01111: TRAP (trapvect7, no modifica NZP)

# Bloque B (10000 - 11111)
OP_SUB   = 16  # 10000: SUB (registro o imm4)
OP_OR    = 17  # 10001: OR (registro o imm4)
OP_XOR   = 18  # 10010: XOR (registro o imm4)
OP_CMP   = 19  # 10011: CMP (17 bits, solo actualiza NZP)
OP_ADDI  = 20  # 10100: ADDI / MOVI (M=0: ADDI, M=1: MOVI, imm7)
OP_SHL   = 21  # 10101: SHL (registro o uimm4)
OP_ASR   = 22  # 10110: ASR (registro o uimm4)
OP_LSR   = 23  # 10111: LSR (registro o uimm4)
OP_MULL  = 24  # 11000: MULL (x=0) / MULH (x=1)
OP_DIV   = 25  # 11001: DIV (x=0) / REM (x=1)
OP_MULQ  = 26  # 11010: MULQ (punto fijo, n=0..31)
OP_DIVQ  = 27  # 11011: DIVQ (punto fijo, n=0..16)
OP_PUSHM = 28  # 11100: PUSHM (D=0) / POPM (D=1)
OP_NEG   = 29  # 11101: NEG (-SR1, satura -32768 a +32767)
OP_ABS   = 30  # 11110: ABS (|SR1|, satura -32768 a +32767)
OP_LDBU  = 31  # 11111: LDBU (BaseR + off5, zero-extend)

OPCODE_NAMES = {
    OP_BR: "BR", OP_ADD: "ADD", OP_LD: "LD", OP_ST: "ST",
    OP_JSR: "JSR", OP_AND: "AND", OP_LDR: "LDR", OP_STR: "STR",
    OP_LDB: "LDB", OP_NOT: "NOT", OP_LDH: "LDH", OP_STH: "STH",
    OP_JMP: "JMP", OP_STB: "STB", OP_LEA: "LEA", OP_TRAP: "TRAP",
    OP_SUB: "SUB", OP_OR: "OR", OP_XOR: "XOR", OP_CMP: "CMP",
    OP_ADDI: "ADDI", OP_SHL: "SHL", OP_ASR: "ASR", OP_LSR: "LSR",
    OP_MULL: "MULL", OP_DIV: "DIV", OP_MULQ: "MULQ", OP_DIVQ: "DIVQ",
    OP_PUSHM: "PUSHM", OP_NEG: "NEG", OP_ABS: "ABS", OP_LDBU: "LDBU",
}

# ---------------- Vectores de TRAP ----------------
TRAP_GETC = 0x20
TRAP_OUT  = 0x21
TRAP_PUTS = 0x22
TRAP_IN   = 0x23
TRAP_HALT = 0x25
TRAP_PUTI = 0x26                     # Imprime R0 como entero con signo

TRAP_NAMES = {
    TRAP_GETC: "GETC", TRAP_OUT: "OUT", TRAP_PUTS: "PUTS",
    TRAP_IN: "IN", TRAP_HALT: "HALT", TRAP_PUTI: "PUTI",
}

# ---------------- Constantes de OS y E/S mapeada en memoria (MMIO) ----------------
OS_TVT_BASE  = 0x0000                # Tabla de Vectores de TRAP (entrada en vec * 2)
OS_CODE_ORIG = 0x0400                # Origen de las rutinas del Sistema Operativo
MMIO_KBSR    = 0xFE00                # Keyboard Status Register (bit 15 = tecla lista)
MMIO_KBDR    = 0xFE02                # Keyboard Data Register (byte ASCII en [7:0])
MMIO_DSR     = 0xFE04                # Display Status Register (bit 15 = pantalla lista)
MMIO_DDR     = 0xFE06                # Display Data Register (escritura emite carácter)
MMIO_MCR     = 0xFFFE                # Machine Control Register (bit 15 = 0 detiene CPU)

# ---------------- Códigos de condición NZP ----------------
FL_P, FL_Z, FL_N = 0b001, 0b010, 0b100   # Bits [10:8] de BR


# ---------------- Utilidades numéricas ----------------
def sign_extend(x: int, bits: int) -> int:
    x &= (1 << bits) - 1
    return x - (1 << bits) if (x >> (bits - 1)) else x

def to_uint16(x: int) -> int:
    return x & MASK16

def to_int16(x: int) -> int:
    return sign_extend(x, 16)

def to_uint8(x: int) -> int:
    return x & MASK8

def to_int8(x: int) -> int:
    return sign_extend(x, 8)

def get_cc_name(cc: int) -> str:
    return "".join(n for f, n in ((FL_N, "N"), (FL_Z, "Z"), (FL_P, "P")) if cc & f) or "-"


# ---------------- DECODIFICACIÓN de campos (formatos) ----------------
def f_opcode(i: int) -> int: return (i >> OPCODE_SHIFT) & 0x1F
def f_dr(i: int) -> int:     return (i >> 8) & 7
def f_sr1(i: int) -> int:    return (i >> 5) & 7
def f_sr2(i: int) -> int:    return i & 7
def f_base(i: int) -> int:   return (i >> 5) & 7
def f_nzp(i: int) -> int:    return (i >> 8) & 7
def f_bit4(i: int) -> int:   return (i >> 4) & 1
def f_bit3(i: int) -> int:   return (i >> 3) & 1
def f_bit7(i: int) -> int:   return (i >> 7) & 1
def f_bit10(i: int) -> int:  return (i >> 10) & 1
def f_imm4(i: int) -> int:   return sign_extend(i & 0x0F, 4)
def f_uimm4(i: int) -> int:  return i & 0x0F
def f_off5(i: int) -> int:   return sign_extend(i & 0x1F, 5)
def f_imm7(i: int) -> int:   return sign_extend(i & 0x7F, 7)
def f_off8(i: int) -> int:   return sign_extend(i & 0xFF, 8)
def f_off10(i: int) -> int:  return sign_extend(i & 0x3FF, 10)
def f_trap7(i: int) -> int:  return i & 0x7F
def f_n5(i: int) -> int:     return i & 0x1F
def f_mask8(i: int) -> int:  return i & 0xFF


# ---------------- CODIFICACIÓN (para ensamblador y tests) ----------------
def _chk(val: int, bits: int, what: str = "valor") -> int:
    lo = -(1 << (bits - 1))
    hi = (1 << (bits - 1)) - 1
    if not (lo <= val <= hi):
        raise ValueError(f"{what}={val} fuera de rango con signo [{lo}, {hi}]")
    return val & ((1 << bits) - 1)

def _chk_u(val: int, bits: int, what: str = "valor") -> int:
    lo = 0
    hi = (1 << bits) - 1
    if not (lo <= val <= hi):
        raise ValueError(f"{what}={val} fuera de rango sin signo [{lo}, {hi}]")
    return val & hi

def enc_nop() -> int:
    return NOP_INSTR

def enc_ret() -> int:
    return RET_INSTR

def enc_br(nzp: int, off8: int) -> int:
    return (OP_BR << OPCODE_SHIFT) | ((nzp & 7) << 8) | _chk(off8, 8, "off8")

def enc_add_reg(dr: int, sr1: int, sr2: int) -> int:
    return (OP_ADD << OPCODE_SHIFT) | ((dr & 7) << 8) | ((sr1 & 7) << 5) | (sr2 & 7)

def enc_add_imm(dr: int, sr1: int, imm4: int) -> int:
    return (OP_ADD << OPCODE_SHIFT) | ((dr & 7) << 8) | ((sr1 & 7) << 5) | (1 << 4) | _chk(imm4, 4, "imm4")

def enc_ld(dr: int, off8: int) -> int:
    return (OP_LD << OPCODE_SHIFT) | ((dr & 7) << 8) | _chk(off8, 8, "off8")

def enc_st(sr: int, off8: int) -> int:
    return (OP_ST << OPCODE_SHIFT) | ((sr & 7) << 8) | _chk(off8, 8, "off8")

def enc_jsr(off10: int) -> int:
    return (OP_JSR << OPCODE_SHIFT) | (1 << 10) | _chk(off10, 10, "off10")

def enc_jsrr(base: int) -> int:
    return (OP_JSR << OPCODE_SHIFT) | (0 << 10) | ((base & 7) << 5)

def enc_and_reg(dr: int, sr1: int, sr2: int) -> int:
    return (OP_AND << OPCODE_SHIFT) | ((dr & 7) << 8) | ((sr1 & 7) << 5) | (sr2 & 7)

def enc_and_imm(dr: int, sr1: int, imm4: int) -> int:
    return (OP_AND << OPCODE_SHIFT) | ((dr & 7) << 8) | ((sr1 & 7) << 5) | (1 << 4) | _chk(imm4, 4, "imm4")

def enc_ldr(dr: int, base: int, off5: int) -> int:
    return (OP_LDR << OPCODE_SHIFT) | ((dr & 7) << 8) | ((base & 7) << 5) | _chk(off5, 5, "off5")

def enc_str(sr: int, base: int, off5: int) -> int:
    return (OP_STR << OPCODE_SHIFT) | ((sr & 7) << 8) | ((base & 7) << 5) | _chk(off5, 5, "off5")

def enc_ldb(dr: int, base: int, off5: int) -> int:
    return (OP_LDB << OPCODE_SHIFT) | ((dr & 7) << 8) | ((base & 7) << 5) | _chk(off5, 5, "off5")

def enc_not(dr: int, sr1: int) -> int:
    return (OP_NOT << OPCODE_SHIFT) | ((dr & 7) << 8) | ((sr1 & 7) << 5) | 0x1F

def enc_ldh(dr: int, base: int, off5: int) -> int:
    return (OP_LDH << OPCODE_SHIFT) | ((dr & 7) << 8) | ((base & 7) << 5) | _chk(off5, 5, "off5")

def enc_sth(sr: int, base: int, off5: int) -> int:
    return (OP_STH << OPCODE_SHIFT) | ((sr & 7) << 8) | ((base & 7) << 5) | _chk(off5, 5, "off5")

def enc_jmp(base: int) -> int:
    return (OP_JMP << OPCODE_SHIFT) | ((base & 7) << 5)

def enc_stb(sr: int, base: int, off5: int) -> int:
    return (OP_STB << OPCODE_SHIFT) | ((sr & 7) << 8) | ((base & 7) << 5) | _chk(off5, 5, "off5")

def enc_lea(dr: int, off8: int) -> int:
    return (OP_LEA << OPCODE_SHIFT) | ((dr & 7) << 8) | _chk(off8, 8, "off8")

def enc_trap(vec7: int) -> int:
    return (OP_TRAP << OPCODE_SHIFT) | (vec7 & 0x7F)

def enc_sub_reg(dr: int, sr1: int, sr2: int) -> int:
    return (OP_SUB << OPCODE_SHIFT) | ((dr & 7) << 8) | ((sr1 & 7) << 5) | (sr2 & 7)

def enc_sub_imm(dr: int, sr1: int, imm4: int) -> int:
    return (OP_SUB << OPCODE_SHIFT) | ((dr & 7) << 8) | ((sr1 & 7) << 5) | (1 << 4) | _chk(imm4, 4, "imm4")

def enc_or_reg(dr: int, sr1: int, sr2: int) -> int:
    return (OP_OR << OPCODE_SHIFT) | ((dr & 7) << 8) | ((sr1 & 7) << 5) | (sr2 & 7)

def enc_or_imm(dr: int, sr1: int, imm4: int) -> int:
    return (OP_OR << OPCODE_SHIFT) | ((dr & 7) << 8) | ((sr1 & 7) << 5) | (1 << 4) | _chk(imm4, 4, "imm4")

def enc_xor_reg(dr: int, sr1: int, sr2: int) -> int:
    return (OP_XOR << OPCODE_SHIFT) | ((dr & 7) << 8) | ((sr1 & 7) << 5) | (sr2 & 7)

def enc_xor_imm(dr: int, sr1: int, imm4: int) -> int:
    return (OP_XOR << OPCODE_SHIFT) | ((dr & 7) << 8) | ((sr1 & 7) << 5) | (1 << 4) | _chk(imm4, 4, "imm4")

def enc_cmp_reg(sr1: int, sr2: int) -> int:
    return (OP_CMP << OPCODE_SHIFT) | ((sr1 & 7) << 5) | (sr2 & 7)

def enc_cmp_imm(sr1: int, imm4: int) -> int:
    return (OP_CMP << OPCODE_SHIFT) | ((sr1 & 7) << 5) | (1 << 4) | _chk(imm4, 4, "imm4")

def enc_addi(rd: int, imm7: int) -> int:
    return (OP_ADDI << OPCODE_SHIFT) | ((rd & 7) << 8) | (0 << 7) | _chk(imm7, 7, "imm7")

def enc_movi(rd: int, imm7: int) -> int:
    return (OP_ADDI << OPCODE_SHIFT) | ((rd & 7) << 8) | (1 << 7) | _chk(imm7, 7, "imm7")

def enc_shl_reg(dr: int, sr1: int, sr2: int) -> int:
    return (OP_SHL << OPCODE_SHIFT) | ((dr & 7) << 8) | ((sr1 & 7) << 5) | (sr2 & 7)

def enc_shl_imm(dr: int, sr1: int, uimm4: int) -> int:
    return (OP_SHL << OPCODE_SHIFT) | ((dr & 7) << 8) | ((sr1 & 7) << 5) | (1 << 4) | _chk_u(uimm4, 4, "uimm4")

def enc_asr_reg(dr: int, sr1: int, sr2: int) -> int:
    return (OP_ASR << OPCODE_SHIFT) | ((dr & 7) << 8) | ((sr1 & 7) << 5) | (sr2 & 7)

def enc_asr_imm(dr: int, sr1: int, uimm4: int) -> int:
    return (OP_ASR << OPCODE_SHIFT) | ((dr & 7) << 8) | ((sr1 & 7) << 5) | (1 << 4) | _chk_u(uimm4, 4, "uimm4")

def enc_lsr_reg(dr: int, sr1: int, sr2: int) -> int:
    return (OP_LSR << OPCODE_SHIFT) | ((dr & 7) << 8) | ((sr1 & 7) << 5) | (sr2 & 7)

def enc_lsr_imm(dr: int, sr1: int, uimm4: int) -> int:
    return (OP_LSR << OPCODE_SHIFT) | ((dr & 7) << 8) | ((sr1 & 7) << 5) | (1 << 4) | _chk_u(uimm4, 4, "uimm4")

def enc_mull(dr: int, sr1: int, sr2: int) -> int:
    return (OP_MULL << OPCODE_SHIFT) | ((dr & 7) << 8) | ((sr1 & 7) << 5) | (0 << 3) | (sr2 & 7)

def enc_mulh(dr: int, sr1: int, sr2: int) -> int:
    return (OP_MULL << OPCODE_SHIFT) | ((dr & 7) << 8) | ((sr1 & 7) << 5) | (1 << 3) | (sr2 & 7)

def enc_div(dr: int, sr1: int, sr2: int) -> int:
    return (OP_DIV << OPCODE_SHIFT) | ((dr & 7) << 8) | ((sr1 & 7) << 5) | (0 << 3) | (sr2 & 7)

def enc_rem(dr: int, sr1: int, sr2: int) -> int:
    return (OP_DIV << OPCODE_SHIFT) | ((dr & 7) << 8) | ((sr1 & 7) << 5) | (1 << 3) | (sr2 & 7)

def enc_mulq(rd: int, rs: int, n5: int) -> int:
    return (OP_MULQ << OPCODE_SHIFT) | ((rd & 7) << 8) | ((rs & 7) << 5) | _chk_u(n5, 5, "n5")

def enc_divq(rd: int, rs: int, n5: int) -> int:
    if not (0 <= n5 <= 16):
        raise ValueError(f"DIVQ n={n5} fuera de rango permitido [0, 16] (17..31 reservado)")
    return (OP_DIVQ << OPCODE_SHIFT) | ((rd & 7) << 8) | ((rs & 7) << 5) | (n5 & 0x1F)

def enc_pushm(mask8: int) -> int:
    return (OP_PUSHM << OPCODE_SHIFT) | (0 << 10) | (mask8 & MASK8)

def enc_popm(mask8: int) -> int:
    return (OP_PUSHM << OPCODE_SHIFT) | (1 << 10) | (mask8 & MASK8)

def enc_neg(dr: int, sr1: int) -> int:
    return (OP_NEG << OPCODE_SHIFT) | ((dr & 7) << 8) | ((sr1 & 7) << 5)

def enc_abs(dr: int, sr1: int) -> int:
    return (OP_ABS << OPCODE_SHIFT) | ((dr & 7) << 8) | ((sr1 & 7) << 5)

def enc_ldbu(dr: int, base: int, off5: int) -> int:
    return (OP_LDBU << OPCODE_SHIFT) | ((dr & 7) << 8) | ((base & 7) << 5) | _chk(off5, 5, "off5")

# Codificadores genéricos de compatibilidad
def enc_reg(op: int, dr: int, sr1: int, sr2: int) -> int:
    return (op << OPCODE_SHIFT) | ((dr & 7) << 8) | ((sr1 & 7) << 5) | (sr2 & 7)

def enc_imm(op: int, dr: int, sr1: int, imm: int) -> int:
    if op == OP_ADDI:
        return enc_addi(dr, imm)
    return (op << OPCODE_SHIFT) | ((dr & 7) << 8) | ((sr1 & 7) << 5) | (1 << 4) | _chk(imm, 4, "imm4")


# ---------------- Desensamblador ----------------
def disassemble(instr: int, pc: int = 0, symbols: Optional[Dict[int, str]] = None) -> str:
    """`pc` = dirección de la instrucción. `symbols` = {dirección: etiqueta}."""
    instr &= MASK16
    if instr == NOP_INSTR:
        return "NOP"
    if instr == RET_INSTR:
        return "RET"

    op = f_opcode(instr)
    dr = f_dr(instr)
    sr1 = f_sr1(instr)
    sr2 = f_sr2(instr)
    nxt = (pc + INSTR_SIZE) & MASK16

    def addr(a: int) -> str:
        a &= MASK16
        return f"{symbols[a]} (x{a:04X})" if symbols and a in symbols else f"x{a:04X}"

    if op == OP_BR:
        n = f_nzp(instr)
        cond = ("n" if n & 4 else "") + ("z" if n & 2 else "") + ("p" if n & 1 else "")
        target = (nxt + f_off8(instr) * INSTR_SIZE) & MASK16
        return f"BR{cond:<4} {addr(target)}"

    if op in (OP_ADD, OP_AND, OP_SUB, OP_OR, OP_XOR):
        name = OPCODE_NAMES[op]
        if f_bit4(instr) == 0:
            return f"{name:<5} R{dr}, R{sr1}, R{sr2}"
        return f"{name:<5} R{dr}, R{sr1}, #{f_imm4(instr)}"

    if op == OP_LD:
        target = (nxt + f_off8(instr) * INSTR_SIZE) & MASK16
        return f"LD    R{dr}, {addr(target)}"

    if op == OP_ST:
        target = (nxt + f_off8(instr) * INSTR_SIZE) & MASK16
        return f"ST    R{dr}, {addr(target)}"

    if op == OP_JSR:
        if f_bit10(instr) == 1:
            target = (nxt + f_off10(instr) * INSTR_SIZE) & MASK16
            return f"JSR   {addr(target)}"
        return f"JSRR  R{sr1}"

    if op == OP_LDR:
        return f"LDR   R{dr}, R{sr1}, #{f_off5(instr)}"

    if op == OP_STR:
        return f"STR   R{dr}, R{sr1}, #{f_off5(instr)}"

    if op == OP_LDB:
        return f"LDB   R{dr}, R{sr1}, #{f_off5(instr)}"

    if op == OP_NOT:
        return f"NOT   R{dr}, R{sr1}"

    if op == OP_LDH:
        return f"LDH   R{dr}, R{sr1}, #{f_off5(instr)}"

    if op == OP_STH:
        return f"STH   R{dr}, R{sr1}, #{f_off5(instr)}"

    if op == OP_JMP:
        return "RET" if sr1 == LINK_REG else f"JMP   R{sr1}"

    if op == OP_STB:
        return f"STB   R{dr}, R{sr1}, #{f_off5(instr)}"

    if op == OP_LEA:
        target = (nxt + f_off8(instr) * INSTR_SIZE) & MASK16
        return f"LEA   R{dr}, {addr(target)}"

    if op == OP_TRAP:
        v = f_trap7(instr)
        return TRAP_NAMES.get(v, f"TRAP  x{v:02X}")

    if op == OP_CMP:
        if f_bit4(instr) == 0:
            return f"CMP   R{sr1}, R{sr2}"
        return f"CMP   R{sr1}, #{f_imm4(instr)}"

    if op == OP_ADDI:
        if f_bit7(instr) == 0:
            return f"ADDI  R{dr}, #{f_imm7(instr)}"
        return f"MOVI  R{dr}, #{f_imm7(instr)}"

    if op in (OP_SHL, OP_ASR, OP_LSR):
        name = OPCODE_NAMES[op]
        if f_bit4(instr) == 0:
            return f"{name:<5} R{dr}, R{sr1}, R{sr2}"
        return f"{name:<5} R{dr}, R{sr1}, #{f_uimm4(instr)}"

    if op == OP_MULL:
        name = "MULH" if f_bit3(instr) == 1 else "MULL"
        return f"{name:<5} R{dr}, R{sr1}, R{sr2}"

    if op == OP_DIV:
        name = "REM" if f_bit3(instr) == 1 else "DIV"
        return f"{name:<5} R{dr}, R{sr1}, R{sr2}"

    if op == OP_MULQ:
        return f"MULQ  R{dr}, R{sr1}, #{f_n5(instr)}"

    if op == OP_DIVQ:
        return f"DIVQ  R{dr}, R{sr1}, #{f_n5(instr)}"

    if op == OP_PUSHM:
        is_pop = f_bit10(instr) == 1
        name = "POPM" if is_pop else "PUSHM"
        mask = f_mask8(instr)
        regs = [f"R{r}" for r in range(NUM_REGS) if (mask & (1 << r)) and r != SP_REG]
        return f"{name:<5} {{{', '.join(regs)}}}"

    if op == OP_NEG:
        return f"NEG   R{dr}, R{sr1}"

    if op == OP_ABS:
        return f"ABS   R{dr}, R{sr1}"

    if op == OP_LDBU:
        return f"LDBU  R{dr}, R{sr1}, #{f_off5(instr)}"

    return f".FILL x{instr:04X}"
