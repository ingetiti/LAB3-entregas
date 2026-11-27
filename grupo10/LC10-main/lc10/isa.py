"""LC10: definición de la ISA del Grupo 10.

Es la fuente única de verdad: el ensamblador, el desensamblador y el simulador
leen esta misma tabla. Para agregar o cambiar una instrucción se edita aquí.

Resumen (detalle en docs/ISA.md):
  * instrucciones de 16 bits, opcode fijo de 5 bits en [15:11]
  * 8 registros de 16 bits (R0..R7), R7 = registro de enlace (JSR/JSRR)
  * memoria direccionable por byte, 2**16 direcciones, little-endian
  * el PC avanza de a 2 bytes; las instrucciones empiezan siempre en dirección par
  * banderas N, Z, P, C (acarreo) y V (desborde con signo)
  * MUL/MULH/MULHU y DIV/DIVU/REM/REMU: enteros de 16 bits; el punto fijo (Q) lo escala el programa
  * opcode 31: PUSH/POP de varios registros a la vez (pila en R6) y DIVREMU/DIVREM (cociente y resto juntos)
"""
from __future__ import annotations

M16 = 0xFFFF
N_REGS = 8
MEM_SIZE = 1 << 16

# nombres de las condiciones de la instrucción BRX (campo [10:8])
COND_NAMES = ["C", "NC", "V", "NV", "LT", "GE", "GT", "LE"]


def sext(value: int, bits: int) -> int:
    """Extiende el signo de un campo de `bits` bits."""
    value &= (1 << bits) - 1
    return value - (1 << bits) if value >> (bits - 1) else value


def to_s16(value: int) -> int:
    return sext(value, 16)


# (mnemónico, opcode, formato)
INSTRUCTIONS = [
    ("BR",   0, "BR"),     # salto condicional por N, Z, P (0x0000 = NOP)
    ("BRX",  1, "BRX"),    # salto condicional por C, V o comparaciones con signo
    ("ADD",  2, "ALU"),
    ("SUB",  3, "ALU"),
    ("AND",  4, "ALU"),
    ("OR",   5, "ALU"),
    ("XOR",  6, "ALU"),
    ("NOT",  7, "UN"),
    ("NEG",  8, "UN"),
    ("ADC",  9, "ALU"),
    ("SBC", 10, "ALU"),
    ("CMP", 11, "CMP"),
    ("SHL", 12, "SH"),
    ("SHR", 13, "SH"),
    ("SAR", 14, "SH"),
    ("ROTC", 15, "ROTC"),  # rotación de 1 bit a través del acarreo
    ("LDW", 16, "MEMW"),   # carga palabra (offset en palabras)
    ("LDL", 17, "MEMB"),   # carga byte en la parte baja (extiende el signo)
    ("LDH", 18, "MEMB"),   # carga byte en la parte alta (conserva la parte baja)
    ("STW", 19, "MEMW"),   # guarda palabra
    ("STL", 20, "MEMB"),   # guarda el byte bajo
    ("STH", 21, "MEMB"),   # guarda el byte alto
    ("LD",  22, "PCREL"),  # carga palabra relativa al PC
    ("ST",  23, "PCREL"),  # guarda palabra relativa al PC
    ("LEA", 24, "PCREL"),  # dirección relativa al PC (offset en bytes: llega a datos en direcciones impares)
    ("MOVI", 25, "MOVI"),  # constante de 8 bits con signo
    ("JSR", 26, "JSR"),    # llamada relativa, guarda PC+2 en R7
    ("JR",  27, "JR"),     # salto por registro; con enlace = JSRR, sin enlace = JMP/RET
    ("TRAP", 28, "TRAP"),
    # multiplicación y división enteras de 16 bits (sin punto flotante). Comparten opcode: la variante
    # va en el campo fn de los bits [4:3] (ver MD_FN). El escalado de punto fijo (Q) lo hace el programa.
    ("MUL",   29, "MD"),   # DR = parte baja del producto (con o sin signo es la misma)
    ("MULH",  29, "MD"),   # DR = parte alta del producto con signo
    ("MULHU", 29, "MD"),   # DR = parte alta del producto sin signo
    ("DIV",   30, "MD"),   # DR = cociente con signo, truncado hacia cero
    ("DIVU",  30, "MD"),   # DR = cociente sin signo
    ("REM",   30, "MD"),   # DR = resto con signo (signo del dividendo): a = DIV*b + REM
    ("REMU",  30, "MD"),   # DR = resto sin signo
    # opcode 31 (formato X): la variante va en fn, bits [10:9]
    ("PUSH",    31, "X"),  # guarda en la pila (R6) los registros de la máscara [7:0]
    ("POP",     31, "X"),  # los vuelve a cargar (orden inverso)
    ("DIVREMU", 31, "X"),  # DR = SR1 / SR2 y SR1 = SR1 % SR2, sin signo
    ("DIVREM",  31, "X"),  # lo mismo con signo (truncado hacia cero; el resto lleva el signo del dividendo)
]
RESERVED_FROM = 32          # ya no quedan opcodes libres

# variante (campo fn, bits [10:9]) del opcode 31
X_FN = {"PUSH": 0, "POP": 1, "DIVREMU": 2, "DIVREM": 3}
X_NAMES = ["PUSH", "POP", "DIVREMU", "DIVREM"]
SP = 6                      # registro que PUSH y POP usan como puntero de pila

# variante (campo fn, bits [4:3]) de cada instrucción del formato MD; fn = 3 del opcode 29 está reservado
MD_FN = {"MUL": 0, "MULH": 1, "MULHU": 2, "DIV": 0, "DIVU": 1, "REM": 2, "REMU": 3}
MD_NAMES = {29: ["MUL", "MULH", "MULHU", None], 30: ["DIV", "DIVU", "REM", "REMU"]}

BY_NAME = {n: (op, fmt) for n, op, fmt in INSTRUCTIONS}
BY_CODE = {}
for _n, _op, _fmt in INSTRUCTIONS:
    BY_CODE.setdefault(_op, (_n, _fmt))                # en los formatos MD y X el nombre lo da el campo fn

IMM4_RANGE = (-8, 7)
IMM5_RANGE = (-16, 15)
IMM8_RANGE = (-128, 127)
IMM11_RANGE = (-1024, 1023)


class IsaError(ValueError):
    """Instrucción mal formada (campo fuera de rango, opcode reservado, ...)."""


def _check(value: int, lo: int, hi: int, what: str) -> int:
    if not lo <= value <= hi:
        raise IsaError(f"{what} = {value} fuera de rango [{lo}, {hi}]")
    return value


def _reg(value: int, what: str) -> int:
    return _check(value, 0, N_REGS - 1, what)


def encode(name: str, **f) -> int:
    """Codifica una instrucción. Los campos dependen del formato (ver `decode`)."""
    name = name.upper()
    if name not in BY_NAME:
        raise IsaError(f"instrucción desconocida: {name}")
    op, fmt = BY_NAME[name]
    w = op << 11
    if fmt == "BR":
        for k in ("n", "z", "p"):
            _check(f[k], 0, 1, k)
        w |= f["n"] << 10 | f["z"] << 9 | f["p"] << 8 | _check(f["off"], *IMM8_RANGE, "offset8") & 0xFF
    elif fmt == "BRX":
        w |= _check(f["cond"], 0, 7, "cond") << 8 | _check(f["off"], *IMM8_RANGE, "offset8") & 0xFF
    elif fmt in ("ALU", "CMP"):
        dr = 0 if fmt == "CMP" else _reg(f["dr"], "DR")
        w |= dr << 8 | _reg(f["sr1"], "SR1") << 5
        if f["mode"] == "i":
            w |= 1 << 4 | _check(f["src"], *IMM4_RANGE, "imm4") & 0xF
        else:
            w |= _reg(f["src"], "SR2")
    elif fmt == "UN":
        w |= _reg(f["dr"], "DR") << 8 | _reg(f["sr"], "SR") << 5
    elif fmt == "MD":
        w |= _reg(f["dr"], "DR") << 8 | _reg(f["sr1"], "SR1") << 5 | MD_FN[name] << 3 | _reg(f["sr2"], "SR2")
    elif fmt == "SH":
        w |= _reg(f["dr"], "DR") << 8 | _reg(f["sr1"], "SR1") << 5
        if f["mode"] == "i":
            w |= _check(f["src"], 0, 15, "cantidad de desplazamiento")
        else:
            w |= 1 << 4 | _reg(f["src"], "SR2")
    elif fmt == "ROTC":
        w |= _reg(f["dr"], "DR") << 8 | _reg(f["sr"], "SR") << 5 | _check(f["right"], 0, 1, "right") << 4
    elif fmt == "MEMW":
        w |= _reg(f["reg"], "reg") << 8 | _reg(f["base"], "BaseR") << 5 | _check(f["off"], *IMM5_RANGE, "offset5") & 0x1F
    elif fmt == "MEMB":
        w |= _reg(f["reg"], "reg") << 8 | _reg(f["base"], "BaseR") << 5 | _check(f["off"], *IMM5_RANGE, "offset5") & 0x1F
    elif fmt == "PCREL":
        w |= _reg(f["reg"], "reg") << 8 | _check(f["off"], *IMM8_RANGE, "offset8") & 0xFF
    elif fmt == "MOVI":
        w |= _reg(f["dr"], "DR") << 8 | _check(f["imm"], *IMM8_RANGE, "imm8") & 0xFF
    elif fmt == "JSR":
        w |= _check(f["off"], *IMM11_RANGE, "offset11") & 0x7FF
    elif fmt == "JR":
        w |= _check(f["link"], 0, 1, "link") << 10 | _reg(f["base"], "BaseR") << 5
    elif fmt == "TRAP":
        w |= _check(f["vect"], 0, 255, "trapvect8")
    elif fmt == "X":
        w |= X_FN[name] << 9
        if name in ("PUSH", "POP"):
            mask = _check(f["mask"], 1, 0xFF, "máscara de registros")
            if mask >> SP & 1:
                raise IsaError(f"{name} no puede incluir R{SP}: es el puntero de pila")
            w |= mask
        else:
            dr, sr1 = _reg(f["dr"], "DR"), _reg(f["sr1"], "SR1")
            if dr == sr1:
                raise IsaError(f"{name}: DR y SR1 tienen que ser distintos (DR recibe el cociente y SR1 el resto)")
            w |= dr << 6 | sr1 << 3 | _reg(f["sr2"], "SR2")
    else:  # pragma: no cover
        raise IsaError(f"formato desconocido: {fmt}")
    return w & M16


def decode(word: int) -> tuple[str, dict]:
    """Decodifica una palabra. Devuelve (mnemónico, campos)."""
    word &= M16
    op = word >> 11
    if op not in BY_CODE:
        raise IsaError(f"opcode reservado: {op}")
    name, fmt = BY_CODE[op]
    dr = word >> 8 & 7
    r1 = word >> 5 & 7
    f: dict = {}
    if fmt == "X":
        name = X_NAMES[word >> 9 & 3]
        if name in ("PUSH", "POP"):
            mask = word & 0xFF
            if word >> 8 & 1 or mask == 0 or mask >> SP & 1:
                raise IsaError(f"variante reservada del opcode 31: palabra x{word:04X}")
            return name, {"mask": mask}
        dr, sr1 = word >> 6 & 7, word >> 3 & 7
        if dr == sr1:
            raise IsaError(f"variante reservada del opcode 31: {name} con DR = SR1")
        return name, {"dr": dr, "sr1": sr1, "sr2": word & 7}
    if fmt == "MD":
        name = MD_NAMES[op][word >> 3 & 3]
        if name is None:
            raise IsaError(f"variante reservada del opcode {op}: fn = {word >> 3 & 3}")
        return name, {"dr": dr, "sr1": r1, "sr2": word & 7}
    if fmt == "BR":
        f = {"n": word >> 10 & 1, "z": word >> 9 & 1, "p": word >> 8 & 1, "off": sext(word, 8)}
    elif fmt == "BRX":
        f = {"cond": dr, "off": sext(word, 8)}
    elif fmt in ("ALU", "CMP"):
        if fmt == "ALU":
            f["dr"] = dr
        f["sr1"] = r1
        if word >> 4 & 1:
            f["mode"], f["src"] = "i", sext(word, 4)
        else:
            f["mode"], f["src"] = "r", word & 7
    elif fmt == "UN":
        f = {"dr": dr, "sr": r1}
    elif fmt == "SH":
        f = {"dr": dr, "sr1": r1}
        if word >> 4 & 1:
            f["mode"], f["src"] = "r", word & 7
        else:
            f["mode"], f["src"] = "i", word & 15
    elif fmt == "ROTC":
        f = {"dr": dr, "sr": r1, "right": word >> 4 & 1}
    elif fmt in ("MEMW", "MEMB"):
        f = {"reg": dr, "base": r1, "off": sext(word, 5)}
    elif fmt == "PCREL":
        f = {"reg": dr, "off": sext(word, 8)}
    elif fmt == "MOVI":
        f = {"dr": dr, "imm": sext(word, 8)}
    elif fmt == "JSR":
        f = {"off": sext(word, 11)}
    elif fmt == "JR":
        f = {"link": word >> 10 & 1, "base": r1}
    elif fmt == "TRAP":
        f = {"vect": word & 0xFF}
    return name, f


def _br_suffix(f: dict) -> str:
    s = ("n" if f["n"] else "") + ("z" if f["z"] else "") + ("p" if f["p"] else "")
    return s


def disassemble(word: int, pc: int | None = None) -> str:
    """Texto assembly de una palabra. Con `pc` (dirección de la instrucción) agrega destinos."""
    word &= M16
    try:
        name, f = decode(word)
    except IsaError:
        return f".FILL x{word:04X}"
    _, fmt = BY_NAME[name]

    def tgt(off: int, scale_pc: int = 2) -> str:
        if pc is None:
            return f"#{off}"
        return f"#{off} ; -> x{(pc + 2 + 2 * off) & M16:04X}"

    def src(f: dict) -> str:
        return f"R{f['src']}" if f["mode"] == "r" else f"#{f['src']}"

    if fmt == "BR":
        s = _br_suffix(f)
        if not s:                                        # nzp = 000: nunca salta
            return "NOP" if f["off"] == 0 else f".FILL x{word:04X}"
        return f"BR{s} {tgt(f['off'])}"
    if fmt == "BRX":
        return f"BR{COND_NAMES[f['cond']]} {tgt(f['off'])}"
    if fmt == "ALU":
        return f"{name} R{f['dr']}, R{f['sr1']}, {src(f)}"
    if fmt == "CMP":
        return f"CMP R{f['sr1']}, {src(f)}"
    if fmt == "UN":
        return f"{name} R{f['dr']}, R{f['sr']}"
    if fmt == "MD":
        return f"{name} R{f['dr']}, R{f['sr1']}, R{f['sr2']}"
    if fmt == "SH":
        return f"{name} R{f['dr']}, R{f['sr1']}, {src(f)}"
    if fmt == "ROTC":
        return f"{'RCR' if f['right'] else 'RCL'} R{f['dr']}, R{f['sr']}"
    if fmt in ("MEMW", "MEMB"):
        off = f["off"] * 2 if fmt == "MEMW" else f["off"]      # en el assembly el offset va en bytes
        return f"{name} R{f['reg']}, R{f['base']}, #{off}"
    if fmt == "PCREL":
        if name == "LEA":                                # LEA: el offset va en bytes
            return f"LEA R{f['reg']}, #{f['off']}" + (f" ; -> x{(pc + 2 + f['off']) & M16:04X}" if pc is not None else "")
        return f"{name} R{f['reg']}, {tgt(f['off'])}"
    if fmt == "MOVI":
        return f"MOVI R{f['dr']}, #{f['imm']}"
    if fmt == "JSR":
        return f"JSR {tgt(f['off'])}"
    if fmt == "JR":
        if f["link"]:
            return f"JSRR R{f['base']}"
        return "RET" if f["base"] == 7 else f"JMP R{f['base']}"
    if fmt == "TRAP":
        return f"TRAP x{f['vect']:02X}"
    if fmt == "X":
        if name in ("PUSH", "POP"):
            return f"{name} {format_mask(f['mask'])}"
        return f"{name} R{f['dr']}, R{f['sr1']}, R{f['sr2']}"
    return f".FILL x{word:04X}"  # pragma: no cover


def format_mask(mask: int) -> str:
    """Máscara de registros como lista con rangos: 0b00111110 -> 'R1-R5'; 0b10000101 -> 'R0, R2, R7'."""
    regs = [r for r in range(N_REGS) if mask >> r & 1]
    parts, i = [], 0
    while i < len(regs):
        j = i
        while j + 1 < len(regs) and regs[j + 1] == regs[j] + 1:
            j += 1
        parts.append(f"R{regs[i]}" if j == i else f"R{regs[i]}-R{regs[j]}" if j > i + 1 else f"R{regs[i]}, R{regs[j]}")
        i = j + 1
    return ", ".join(parts)


# llamadas al sistema (TRAP). TRAP vv hace R7 = PC y PC = palabra en TRAP_TABLE + 2·vv; esa dirección es
# una rutina del sistema operativo (lc10/os_lc10.asm), que se ejecuta como cualquier otro código.
TRAP_GETC, TRAP_OUT, TRAP_PUTS, TRAP_IN, TRAP_HALT = 0x20, 0x21, 0x22, 0x23, 0x25
TRAP_ALIASES = {"GETC": TRAP_GETC, "OUT": TRAP_OUT, "PUTS": TRAP_PUTS, "IN": TRAP_IN, "HALT": TRAP_HALT}

# mapa de la zona del sistema (arriba de la memoria; la pila de usuario baja desde xFFFE y no llega hasta acá)
TRAP_TABLE = 0xFB00             # xFB00–xFCFF: 256 palabras, una por vector TRAP (0 = vector sin rutina)
OS_BASE = 0xFD40                # xFD40–xFDFF: rutinas del sistema y sus palabras de datos
IO_BASE = 0xFE00                # xFE00–xFE0F: registros de los dispositivos (mapeados en memoria)
IO_KBSR, IO_KBDR, IO_DSR, IO_DDR, IO_MCR = 0xFE00, 0xFE02, 0xFE04, 0xFE06, 0xFE08
IO_END = 0xFE10
SYS_LO, SYS_HI = TRAP_TABLE, IO_END      # todo lo que hay en [SYS_LO, SYS_HI) es del sistema, no del usuario
