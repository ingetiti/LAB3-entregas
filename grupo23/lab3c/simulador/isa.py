"""
ISA LOVELACE - definiciones comunes al ensamblador y al simulador (Lab 3c, Grupo 23).

Instrucciones de 16 bits con opcode fijo de 5 bits (bits 15-11). Las que
necesitan desplazamientos largos ocupan dos codigos consecutivos (el bit 11
forma parte del campo) y conservan el formato de bits de la LC-3.
Ver ESPECIFICACION_ISA.md.
"""

# ---- codigos de 5 bits ------------------------------------------------------
OP = {
    "BR": 0b00000,      # y 00001
    "ADDI": 0b00010,
    "ALU": 0b00011,     # ADD SUB ADC ADDX
    "LD": 0b00100,      # y 00101
    "ST": 0b00110,      # y 00111
    "BRR": 0b01000,
    "JSR": 0b01001,
    "ANDI": 0b01010,
    "LOG": 0b01011,     # AND OR XOR NOT
    "LDR": 0b01100,     # y 01101
    "STR": 0b01110,     # y 01111
    "RTI": 0b10000,
    "SHL": 0b10001,     # LSL LSR
    "SHA": 0b10010,     # ASR RLC
    "LDB": 0b10011,
    "LDBH": 0b10100,
    "STB": 0b10101,
    "STBH": 0b10110,
    "DBP": 0b10111,
    "JMP": 0b11000,     # JMP RET JSRR
    "BRX": 0b11001,
    "PUSHPOP": 0b11010,
    "MUL": 0b11011,     # MUL MULH MULHU
    "LEA": 0b11100,     # y 11101
    "DIV": 0b11110,     # DIV REM DIVU REMU
    "TRAP": 0b11111,
}
ALU_F = {"ADD": 0, "SUB": 1, "ADC": 2, "ADDX": 3}
MUL_F = {"MUL": 0, "MULH": 1, "MULHU": 2}          # f = 3 reservada
DIV_F = {"DIV": 0, "REM": 1, "DIVU": 2, "REMU": 3}
LOG_F = {"AND": 0, "OR": 1, "XOR": 2, "NOT": 3}
SHL_F = {"LSL": 0, "LSR": 1}
SHA_F = {"ASR": 0, "RLC": 1}
BRX_C = {"BRC": 0, "BRNC": 1, "BRV": 2, "BRNV": 3, "BRHI": 4, "BRLS": 5}
TRAP_ALIAS = {"GETC": 0x20, "OUT": 0x21, "PUTS": 0x22, "IN": 0x23,
              "PUTSP": 0x24, "HALT": 0x25}

# PSR: bit 15 = privilegio (1 usuario), bit 4 = C, bit 3 = V, bits 2-0 = N Z P
FLAG_C, FLAG_V = 0x10, 0x08

# Dispositivos mapeados en memoria (direcciones de byte)
KBSR, KBDR, DSR, DDR, MCR = 0xFE00, 0xFE02, 0xFE04, 0xFE06, 0xFFFE

# Nombres para estadisticas (por codigo de 5 bits)
NOMBRE = {}
for k, v in OP.items():
    NOMBRE[v] = k
for k in ("BR", "LD", "ST", "LDR", "STR", "LEA"):
    NOMBRE[OP[k] + 1] = k


def sext(v, bits):
    v &= (1 << bits) - 1
    return v - (1 << bits) if v & (1 << (bits - 1)) else v


def desensamblar(w, addr=None, simbolos=None):
    """Texto en assembly de la instruccion w. Si se da la direccion, los
    destinos relativos al PC se calculan y, si hay tabla de simbolos
    ({direccion: nombre}), se muestran con su etiqueta."""
    op = w >> 11

    def dest(off):
        if addr is None:
            return f"#{off}"
        d = (addr + 2 + 2 * off) & 0xFFFF
        if simbolos and d in simbolos:
            return simbolos[d]
        return f"x{d:04X}"

    R = lambda n: f"R{n}"
    dr, s1, s2 = (w >> 8) & 7, (w >> 5) & 7, (w >> 2) & 7
    if op in (0, 1):
        nzp = (w >> 9) & 7
        if nzp == 0:
            return "NOP"
        c = ("n" if nzp & 4 else "") + ("z" if nzp & 2 else "") + ("p" if nzp & 1 else "")
        return f"BR{c} {dest(sext(w, 9))}"
    if op == OP["ADDI"]:
        return f"ADD {R(dr)}, {R(s1)}, #{sext(w, 5)}"
    if op == OP["ALU"]:
        n = [k for k, v in ALU_F.items() if v == (w & 3)][0]
        return f"{n} {R(dr)}, {R(s1)}, {R(s2)}"
    if op in (OP["LD"], OP["LD"] + 1, OP["ST"], OP["ST"] + 1, OP["LEA"], OP["LEA"] + 1):
        n = {OP["LD"]: "LD", OP["ST"]: "ST", OP["LEA"]: "LEA"}[op & ~1]
        return f"{n} R{(w >> 9) & 7}, {dest(sext(w, 9))}"
    if op == OP["BRR"]:
        nzp = (w >> 5) & 7
        if nzp == 0:
            return f".FILL x{w:04X}"           # BRR sin condiciones: nunca salta
        c = ("n" if nzp & 4 else "") + ("z" if nzp & 2 else "") + ("p" if nzp & 1 else "")
        return f"BRR{c} {R(dr)}, {dest(sext(w, 5))}"
    if op == OP["JSR"]:
        return f"JSR {dest(sext(w, 11))}"
    if op == OP["ANDI"]:
        return f"AND {R(dr)}, {R(s1)}, #{sext(w, 5)}"
    if op == OP["LOG"]:
        f = w & 3
        if f == LOG_F["NOT"]:
            return f"NOT {R(dr)}, {R(s1)}"
        n = [k for k, v in LOG_F.items() if v == f][0]
        return f"{n} {R(dr)}, {R(s1)}, {R(s2)}"
    if op in (OP["LDR"], OP["LDR"] + 1, OP["STR"], OP["STR"] + 1):
        n = "LDR" if op & ~1 == OP["LDR"] else "STR"
        return f"{n} R{(w >> 9) & 7}, R{(w >> 6) & 7}, #{sext(w, 6)}"
    if op == OP["RTI"]:
        return "RTI"
    if op in (OP["SHL"], OP["SHA"]):
        return f"{mnemonico(w)} {R(dr)}, {R(s1)}, #{(w & 0xF) + 1}"
    if op in (OP["LDB"], OP["LDBH"], OP["STB"], OP["STBH"]):
        return f"{NOMBRE[op]} {R(dr)}, {R(s1)}, #{sext(w, 5)}"
    if op == OP["DBP"]:
        return f"DBP {R(dr)}, {dest(sext(w, 8))}"
    if op == OP["JMP"]:
        m = mnemonico(w)
        return "RET" if m == "RET" else f"{m} {R(s1)}"
    if op == OP["BRX"]:
        if mnemonico(w) == "BRX?":
            return f".FILL x{w:04X}"           # condicion reservada
        return f"{mnemonico(w)} {dest(sext(w, 8))}"
    if op == OP["PUSHPOP"]:
        if w & 0x40:
            return f".FILL x{w:04X}"           # R6 en la mascara: reservado
        regs = ", ".join(f"R{r}" for r in range(8) if (w >> r) & 1)
        return f"{mnemonico(w)} {regs}"
    if op == OP["TRAP"]:
        v = w & 0xFF
        alias = {x: k for k, x in TRAP_ALIAS.items()}
        return alias.get(v, f"TRAP x{v:02X}")
    if op in (OP["MUL"], OP["DIV"]):
        m = mnemonico(w)
        if m.endswith("?"):
            return f".FILL x{w:04X}"       # MUL con f = 11: reservado
        return f"{m} {R(dr)}, {R(s1)}, {R(s2)}"
    return f".FILL x{w:04X}"


def mnemonico(w):
    """Nombre del mnemonico de una instruccion (para el perfil)."""
    op = w >> 11
    n = NOMBRE.get(op, "?")
    if n == "ALU":
        return [k for k, v in ALU_F.items() if v == (w & 3)][0]
    if n == "MUL":
        c = [k for k, v in MUL_F.items() if v == (w & 3)]
        return c[0] if c else "MUL?"
    if n == "DIV":
        return [k for k, v in DIV_F.items() if v == (w & 3)][0]
    if n == "LOG":
        return [k for k, v in LOG_F.items() if v == (w & 3)][0]
    if n == "SHL":
        return "LSR" if w & 0x10 else "LSL"
    if n == "SHA":
        return "RLC" if w & 0x10 else "ASR"
    if n == "JMP":
        if w & 0x400:
            return "JSRR"
        return "RET" if ((w >> 5) & 7) == 7 else "JMP"
    if n == "PUSHPOP":
        return "POP" if w & 0x400 else "PUSH"
    if n == "BRX":
        c = [k for k, v in BRX_C.items() if v == ((w >> 8) & 7)]
        return c[0] if c else "BRX?"          # condiciones 110 y 111 reservadas
    return n
