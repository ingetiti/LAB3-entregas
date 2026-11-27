"""Ensamblador de la ISA LC10 (separado del simulador).

Entrada: uno o más archivos de texto con assembly.
Salida: una imagen (origen + bytes) en binario, hexadecimal, decimal o texto binario.
Los primeros dos bytes del archivo de salida son la dirección de origen.

Programa y módulos (.EXTERNAL)
  * El primer archivo es el programa principal: lleva `.ORIG` y `.END`.
  * Los demás son módulos de subrutinas: no llevan `.ORIG`, terminan con `.END` y se
    ubican uno detrás de otro a continuación del programa principal.
  * El nombre del módulo es el del archivo en mayúsculas (division.asm -> DIVISION).
  * Un módulo declara lo que usa de otro con `.EXTERNAL MODULO-ETIQUETA` y luego usa
    ese mismo símbolo (por ejemplo `JSR DIVISION-DIV_LONG` o `.FILL DIVISION-DIV_LONG`).

Alineación
  Las instrucciones y las palabras (`.FILL`, `.BLKW`) siempre empiezan en dirección par.
  Si un dato de bytes (`.BYTE`, `.STRINGZ`, `.BLKB`) deja el contador en una dirección
  impar, el ensamblador inserta automáticamente un byte de relleno (0x00) antes de la
  siguiente instrucción o palabra. Una etiqueta que precede a una instrucción apunta a
  la instrucción, no al relleno.
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

from . import isa
from .image import FORMATS, Image

REG_RE = re.compile(r"^R([0-7])$", re.I)
LABEL_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
QUAL_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)-([A-Za-z_][A-Za-z0-9_]*)$")
BR_RE = re.compile(r"^BR([NZP]*)$", re.I)

BRX_NAMES = {"C": 0, "HS": 0, "NC": 1, "LO": 1, "V": 2, "NV": 3, "LT": 4, "GE": 5, "GT": 6, "LE": 7}
PSEUDO = {"NOP", "RET", "JMP", "JSRR", "RCL", "RCR", "MOV", "CLR", "TST", *isa.TRAP_ALIASES}
DIRECTIVES = {".ORIG", ".END", ".FILL", ".BYTE", ".BLKW", ".BLKB", ".STRINGZ", ".EXTERNAL", ".ALIGN"}


class AsmError(Exception):
    def __init__(self, msg: str, file: str | None = None, line: int | None = None):
        self.msg, self.file, self.line = msg, file, line
        where = f"{file}:{line}: " if file and line else (f"{file}: " if file else "")
        super().__init__(f"{where}{msg}")


def is_mnemonic(tok: str) -> bool:
    t = tok.upper()
    if t in isa.BY_NAME or t in PSEUDO or t.startswith("."):
        return True
    if t.startswith("BR") and (BR_RE.match(t) or t[2:] in BRX_NAMES):
        return True
    return False


def strip_comment(line: str) -> str:
    out, in_str, esc = [], False, False
    for ch in line:
        if in_str:
            out.append(ch)
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
        elif ch == '"':
            in_str = True
            out.append(ch)
        elif ch == ";":
            break
        else:
            out.append(ch)
    return "".join(out)


def is_literal(tok: str) -> bool:
    """¿El token es un número literal (y no una etiqueta)?"""
    return bool(tok) and (tok[0] in "#+-" or tok[0].isdigit() or re.fullmatch(r"[xX][0-9A-Fa-f]+", tok) is not None)


def parse_number(tok: str) -> int | None:
    """Número literal (#-5, 12, x1F, 0x1F, 0b101) o None si no es un número."""
    t = tok.strip()
    hashed = t.startswith("#")
    if hashed:
        t = t[1:]
    v = _parse_plain_number(t)
    if v is None and hashed:
        raise ValueError(tok)
    return v


def _parse_plain_number(t: str) -> int | None:
    if re.fullmatch(r"[+-]?\d+", t):
        return int(t, 10)
    m = re.fullmatch(r"([+-]?)(?:0[xX]|[xX])([0-9A-Fa-f]+)", t)
    if m:
        v = int(m.group(2), 16)
        return -v if m.group(1) == "-" else v
    m = re.fullmatch(r"([+-]?)0[bB]([01]+)", t)
    if m:
        v = int(m.group(2), 2)
        return -v if m.group(1) == "-" else v
    return None


def unescape(s: str) -> bytes:
    out = bytearray()
    i = 0
    while i < len(s):
        c = s[i]
        if c == "\\" and i + 1 < len(s):
            i += 1
            c = {"n": "\n", "t": "\t", "r": "\r", "0": "\0", "\\": "\\", '"': '"'}.get(s[i], None)
            if c is None:
                raise ValueError(f"escape desconocido: \\{s[i]}")
        out += c.encode("latin-1")
        i += 1
    return bytes(out)


@dataclass
class Item:
    kind: str                 # 'instr' | 'word' | 'bytes'
    offset: int               # relativo al inicio del módulo
    size: int
    line: int
    text: str = ""            # línea fuente (para el listado)
    mnem: str = ""
    args: list = field(default_factory=list)
    raw: bytes = b""
    pad: bool = False


@dataclass
class Module:
    name: str
    file: str
    items: list = field(default_factory=list)
    symbols: dict = field(default_factory=dict)      # etiqueta -> offset
    externals: set = field(default_factory=set)      # {"MODULO-ETIQUETA"}
    ext_lines: dict = field(default_factory=dict)
    orig: int | None = None
    size: int = 0
    base: int = 0


@dataclass
class Result:
    image: Image
    symbols: dict            # "MODULO-ETIQUETA" -> dirección absoluta
    modules: list            # [(nombre, base, tamaño)]
    listing: list            # [(dirección, bytes, texto fuente, tipo)]
    pad_bytes: int
    srcmap: list = field(default_factory=list)   # [(dirección, tamaño, archivo, línea, tipo)]; línea 0 = relleno final


# ------------------------------------------------------------------------ pasada 1
def first_pass(file: str, text: str, is_main: bool) -> Module:
    mod = Module(name=Path(file).stem.upper(), file=file)
    lc = 0
    pending: list[tuple[str, int]] = []
    ended = False

    def err(msg, ln):
        return AsmError(msg, file, ln)

    def bind(label: str, ln: int):
        key = label.upper()
        if key in mod.symbols:
            raise err(f"etiqueta repetida: {label}", ln)
        mod.symbols[key] = lc

    def flush_pending():
        for lab, ln in pending:
            bind(lab, ln)
        pending.clear()

    def place(kind, size, ln, text, aligned, **kw):
        nonlocal lc
        if aligned and lc % 2:
            mod.items.append(Item("bytes", lc, 1, ln, text="(relleno)", raw=b"\0", pad=True))
            lc += 1
        flush_pending()
        mod.items.append(Item(kind, lc, size, ln, text=text, **kw))
        lc += size

    for ln, raw_line in enumerate(text.splitlines(), 1):
        s = strip_comment(raw_line).strip()
        if not s:
            continue
        label = None
        first = s.split(None, 1)[0]
        rest = s[len(first):].strip()
        if first.endswith(":"):
            label, s2 = first[:-1], rest
        elif is_mnemonic(first) and not first.startswith(".") and rest.startswith("."):
            raise err(f"{first} es el nombre de una instrucción: no se puede usar como etiqueta", ln)
        elif not is_mnemonic(first):
            label, s2 = first, rest
        else:
            s2 = s
        if label is not None:
            if not LABEL_RE.match(label) or REG_RE.match(label):
                raise err(f"etiqueta inválida: {label!r}", ln)
            pending.append((label, ln))
        if not s2:
            continue
        parts = s2.split(None, 1)
        op = parts[0].upper()
        operands = parts[1].strip() if len(parts) > 1 else ""
        src_text = raw_line.rstrip()

        if ended:
            raise err("hay texto después de .END", ln)
        if op.startswith("."):
            if op not in DIRECTIVES:
                raise err(f"directiva desconocida: {op}", ln)
            if op == ".ORIG":
                if not is_main:
                    raise err("un módulo no lleva .ORIG (solo el programa principal)", ln)
                v = parse_number(operands) if operands else None
                if v is None or not 0 <= v <= 0xFFFF:
                    raise err(".ORIG necesita una dirección numérica", ln)
                if v % 2:
                    raise err(f".ORIG debe ser una dirección par (x{v:04X})", ln)
                if mod.items or mod.orig is not None or pending:
                    raise err(".ORIG tiene que ser lo primero del archivo (sin etiquetas antes)", ln)
                mod.orig = v
            elif op == ".END":
                ended = True
            elif op == ".EXTERNAL":
                for sym in re.split(r"[,\s]+", operands.strip()):
                    if not sym:
                        continue
                    m = QUAL_RE.match(sym)
                    if not m:
                        raise err(f".EXTERNAL espera MODULO-ETIQUETA, no {sym!r}", ln)
                    mod.externals.add(sym.upper())
                    mod.ext_lines[sym.upper()] = ln
            elif op == ".ALIGN":
                if lc % 2:
                    mod.items.append(Item("bytes", lc, 1, ln, text="(relleno)", raw=b"\0", pad=True))
                    lc += 1
                flush_pending()
            elif op == ".FILL":
                if not operands:
                    raise err(".FILL necesita un valor", ln)
                place("word", 2, ln, src_text, True, args=[operands])
            elif op == ".BLKW":
                n = parse_number(operands) if operands else None
                if n is None or n < 0:
                    raise err(".BLKW necesita una cantidad de palabras", ln)
                place("bytes", 2 * n, ln, src_text, True, raw=bytes(2 * n))
            elif op == ".BLKB":
                n = parse_number(operands) if operands else None
                if n is None or n < 0:
                    raise err(".BLKB necesita una cantidad de bytes", ln)
                place("bytes", n, ln, src_text, False, raw=bytes(n))
            elif op == ".BYTE":
                vals = [v for v in re.split(r"[,\s]+", operands) if v]
                if not vals:
                    raise err(".BYTE necesita al menos un valor", ln)
                data = bytearray()
                for v in vals:
                    n = parse_number(v)
                    if n is None or not -128 <= n <= 255:
                        raise err(f".BYTE: valor inválido {v!r} (de -128 a 255)", ln)
                    data.append(n & 0xFF)
                place("bytes", len(data), ln, src_text, False, raw=bytes(data))
            elif op == ".STRINGZ":
                m = re.fullmatch(r'"(.*)"', operands, re.S)
                if not m:
                    raise err('.STRINGZ espera un texto entre comillas: "..."', ln)
                try:
                    data = unescape(m.group(1)) + b"\0"
                except (ValueError, UnicodeEncodeError) as e:
                    raise err(f".STRINGZ: {e}", ln) from None
                place("bytes", len(data), ln, src_text, False, raw=data)
            continue

        if not is_mnemonic(op):
            raise err(f"instrucción desconocida: {op}", ln)
        args = [a for a in re.split(r"[,\s]+", operands) if a]
        place("instr", 2, ln, src_text, True, mnem=op, args=args)

    if not ended:
        raise AsmError("falta .END", file)
    if is_main and mod.orig is None:
        raise AsmError("el programa principal necesita .ORIG", file)
    flush_pending()
    if lc % 2:
        mod.items.append(Item("bytes", lc, 1, 0, text="(relleno)", raw=b"\0", pad=True))
        lc += 1
    mod.size = lc
    return mod


# ------------------------------------------------------------------------ pasada 2
class Linker:
    def __init__(self, modules: list[Module]):
        self.modules = {m.name: m for m in modules}
        if len(self.modules) != len(modules):
            raise AsmError("hay dos archivos con el mismo nombre de módulo")

    def symbol(self, mod: Module, tok: str, ln: int) -> int:
        m = QUAL_RE.match(tok)
        if m:
            key = tok.upper()
            tmod, tlab = m.group(1).upper(), m.group(2).upper()
            if key not in mod.externals:
                raise AsmError(f"{tok} se usa sin declarar: falta `.EXTERNAL {tok}`", mod.file, ln)
            target = self.modules.get(tmod)
            if target is None:
                raise AsmError(f"no se cargó el módulo {tmod} (falta el archivo {tmod.lower()}.asm)", mod.file, ln)
            if tlab not in target.symbols:
                raise AsmError(f"el módulo {tmod} no tiene la etiqueta {tlab}", mod.file, ln)
            return target.base + target.symbols[tlab]
        if not LABEL_RE.match(tok):
            raise AsmError(f"operando inválido: {tok!r}", mod.file, ln)
        key = tok.upper()
        if key not in mod.symbols:
            raise AsmError(f"etiqueta no definida: {tok}", mod.file, ln)
        return mod.base + mod.symbols[key]


def assemble_module_item(link: Linker, mod: Module, it: Item) -> bytes:
    ln, file = it.line, mod.file

    def err(msg):
        return AsmError(msg, file, ln)

    addr = mod.base + it.offset

    def reg(tok: str) -> int:
        m = REG_RE.match(tok)
        if not m:
            raise err(f"se esperaba un registro (R0..R7), no {tok!r}")
        return int(m.group(1))

    def num(tok: str) -> int:
        try:
            v = parse_number(tok)
        except ValueError:
            v = None
        if v is None:
            raise err(f"se esperaba un número, no {tok!r}")
        return v

    def rel(tok: str) -> int:
        """Offset en palabras desde PC+2: etiqueta (se calcula) o número (offset crudo)."""
        if is_literal(tok):
            return num(tok)
        target = link.symbol(mod, tok, ln)
        if target % 2:
            raise err(f"{tok} está en una dirección impar (x{target:04X}): use .ALIGN antes del dato")
        delta = target - (addr + 2)
        return delta // 2

    def rel_bytes(tok: str) -> int:
        """Offset en bytes desde PC+2 (solo LEA): etiqueta (se calcula) o número (offset crudo)."""
        if is_literal(tok):
            return num(tok)
        return link.symbol(mod, tok, ln) - (addr + 2)

    def nargs(n: int, usage: str):
        if len(it.args) != n:
            raise err(f"{it.mnem} espera {usage}")

    def reg_mask(toks: list[str]) -> int:
        """'R1', 'R2-R5', ... -> máscara de 8 bits. Sin repetidos."""
        mask = 0
        for tok in toks:
            lo, sep, hi = tok.partition("-")
            a_, b_ = reg(lo.strip()), reg(hi.strip()) if sep else None
            rs = range(a_, (b_ if b_ is not None else a_) + 1)
            if b_ is not None and b_ < a_:
                raise err(f"rango de registros al revés: {tok}")
            for r in rs:
                if mask >> r & 1:
                    raise err(f"registro repetido en la lista: R{r}")
                mask |= 1 << r
        return mask

    def src_operand(tok: str):
        if REG_RE.match(tok):
            return "r", reg(tok)
        return "i", num(tok)

    m = it.mnem
    a = it.args
    try:
        if it.kind == "word":
            tok = a[0]
            v = num(tok) if is_literal(tok) else link.symbol(mod, tok, ln)
            if not -32768 <= v <= 0xFFFF:
                raise err(f".FILL: valor fuera de 16 bits: {tok}")
            return bytes([v & 0xFF, v >> 8 & 0xFF])
        if it.kind == "bytes":
            return it.raw

        # --- pseudo-instrucciones
        if m == "NOP":
            nargs(0, "ningún operando")
            w = isa.encode("BR", n=0, z=0, p=0, off=0)
        elif m == "RET":
            nargs(0, "ningún operando")
            w = isa.encode("JR", link=0, base=7)
        elif m == "JMP":
            nargs(1, "un registro")
            w = isa.encode("JR", link=0, base=reg(a[0]))
        elif m == "JSRR":
            nargs(1, "un registro")
            w = isa.encode("JR", link=1, base=reg(a[0]))
        elif m in ("RCL", "RCR"):
            nargs(2, "DR, SR")
            w = isa.encode("ROTC", dr=reg(a[0]), sr=reg(a[1]), right=1 if m == "RCR" else 0)
        elif m == "MOV":
            nargs(2, "DR, SR")
            w = isa.encode("OR", dr=reg(a[0]), sr1=reg(a[1]), mode="r", src=reg(a[1]))
        elif m == "CLR":
            nargs(1, "DR")
            w = isa.encode("MOVI", dr=reg(a[0]), imm=0)
        elif m == "TST":
            nargs(1, "SR")
            w = isa.encode("OR", dr=reg(a[0]), sr1=reg(a[0]), mode="r", src=reg(a[0]))
        elif m in isa.TRAP_ALIASES:
            nargs(0, "ningún operando")
            w = isa.encode("TRAP", vect=isa.TRAP_ALIASES[m])
        elif m == "TRAP":
            nargs(1, "un número (trapvect8)")
            w = isa.encode("TRAP", vect=num(a[0]))
        elif m == "BR" or BR_RE.match(m):
            nargs(1, "una etiqueta o un offset")
            flags = m[2:] or "NZP"
            w = isa.encode("BR", n=int("N" in flags), z=int("Z" in flags), p=int("P" in flags), off=rel(a[0]))
        elif m.startswith("BR") and m[2:] in BRX_NAMES:
            nargs(1, "una etiqueta o un offset")
            w = isa.encode("BRX", cond=BRX_NAMES[m[2:]], off=rel(a[0]))
        elif m in ("ADD", "SUB", "AND", "OR", "XOR", "ADC", "SBC"):
            nargs(3, "DR, SR1, SR2|#imm4")
            mode, s = src_operand(a[2])
            w = isa.encode(m, dr=reg(a[0]), sr1=reg(a[1]), mode=mode, src=s)
        elif m == "CMP":
            nargs(2, "SR1, SR2|#imm4")
            mode, s = src_operand(a[1])
            w = isa.encode("CMP", sr1=reg(a[0]), mode=mode, src=s)
        elif m in ("PUSH", "POP"):
            if not a:
                raise err(f"{m} espera una lista de registros: R1, R2, R5 o R1-R5")
            w = isa.encode(m, mask=reg_mask(a))
        elif m in ("DIVREMU", "DIVREM"):
            nargs(3, "DR, SR1, SR2 (DR = cociente, SR1 = resto)")
            w = isa.encode(m, dr=reg(a[0]), sr1=reg(a[1]), sr2=reg(a[2]))
        elif m in isa.MD_FN:
            nargs(3, "DR, SR1, SR2")
            w = isa.encode(m, dr=reg(a[0]), sr1=reg(a[1]), sr2=reg(a[2]))
        elif m in ("NOT", "NEG"):
            nargs(2, "DR, SR")
            w = isa.encode(m, dr=reg(a[0]), sr=reg(a[1]))
        elif m in ("SHL", "SHR", "SAR"):
            nargs(3, "DR, SR1, #cantidad|Rn")
            mode, s = src_operand(a[2])
            w = isa.encode(m, dr=reg(a[0]), sr1=reg(a[1]), mode=mode, src=s)
        elif m in ("LDW", "LDL", "LDH", "STW", "STL", "STH"):
            if len(a) not in (2, 3):
                raise err(f"{m} espera REG, BaseR[, #offset en bytes]")
            off = num(a[2]) if len(a) == 3 else 0
            if m in ("LDW", "STW"):
                if off % 2:
                    raise err(f"{m}: el offset de una palabra debe ser par (está en bytes)")
                off //= 2
            w = isa.encode(m, reg=reg(a[0]), base=reg(a[1]), off=off)
        elif m in ("LD", "ST"):
            nargs(2, "REG, etiqueta|offset")
            w = isa.encode(m, reg=reg(a[0]), off=rel(a[1]))
        elif m == "LEA":
            nargs(2, "REG, etiqueta|offset en bytes")
            w = isa.encode("LEA", reg=reg(a[0]), off=rel_bytes(a[1]))
        elif m == "MOVI":
            nargs(2, "DR, #imm8")
            w = isa.encode("MOVI", dr=reg(a[0]), imm=num(a[1]))
        elif m == "JSR":
            nargs(1, "una etiqueta o un offset")
            off = rel(a[0])
            if not isa.IMM11_RANGE[0] <= off <= isa.IMM11_RANGE[1]:
                raise err(f"JSR {a[0]}: destino fuera de alcance (±2 KiB); use LEA/LD + JSRR")
            w = isa.encode("JSR", off=off)
        else:
            raise err(f"instrucción no soportada: {m}")
    except isa.IsaError as e:
        hint = ""
        if "offset8" in str(e) and m not in ("MOVI",):
            hint = " (el destino está demasiado lejos; use LD/LEA con otra etiqueta cercana o JSRR)"
        raise err(f"{m} {' '.join(a)}: {e}{hint}") from None
    return bytes([w & 0xFF, w >> 8])


def assemble(sources: list[tuple[str, str]], system_area: bool = False) -> Result:
    """Ensambla [(nombre_de_archivo, texto), ...]. El primero es el programa principal.

    El programa no puede invadir la zona del sistema (tabla de vectores, rutinas del SO y dispositivos:
    xFB00–xFE0F); solo el propio SO se ensambla ahí (`system_area=True`)."""
    if not sources:
        raise AsmError("no hay archivos para ensamblar")
    mods = [first_pass(name, text, is_main=(i == 0)) for i, (name, text) in enumerate(sources)]
    link = Linker(mods)
    origin = mods[0].orig
    addr = origin
    for m in mods:
        m.base = addr
        addr += m.size
    if addr > 0x10000:
        raise AsmError(f"el programa no entra en memoria (termina en x{addr:04X})")
    if not system_area and addr > isa.SYS_LO and origin < isa.SYS_HI:
        raise AsmError(f"el programa invade la zona del sistema (x{isa.SYS_LO:04X}–x{isa.SYS_HI - 1:04X}: tabla de "
                       f"vectores TRAP, rutinas del SO y dispositivos); ocupa x{origin:04X}–x{addr - 1:04X}")
    data = bytearray()
    listing = []
    srcmap = []
    pad = 0
    for m in mods:
        for ext in sorted(m.externals):
            mm = QUAL_RE.match(ext)
            tmod, tlab = mm.group(1), mm.group(2)
            if tmod not in link.modules:
                raise AsmError(f".EXTERNAL {ext}: no se cargó el módulo {tmod}", m.file, m.ext_lines[ext])
            if tlab not in link.modules[tmod].symbols:
                raise AsmError(f".EXTERNAL {ext}: el módulo {tmod} no tiene la etiqueta {tlab}", m.file, m.ext_lines[ext])
        for it in m.items:
            b = assemble_module_item(link, m, it)
            assert len(b) == it.size, (it, b)
            if it.pad:
                pad += 1
            listing.append((m.base + it.offset, b, it.text.strip(), it.kind))
            srcmap.append((m.base + it.offset, it.size, m.file, it.line, "pad" if it.pad else it.kind))
            data += b
    symbols = {f"{m.name}-{lab}": m.base + off for m in mods for lab, off in m.symbols.items()}
    return Result(Image(origin, bytes(data)), symbols, [(m.name, m.base, m.size) for m in mods], listing, pad, srcmap)


def format_listing(res: Result) -> str:
    out = []
    for addr, b, text, kind in res.listing:
        if kind in ("instr", "word"):
            out.append(f"x{addr:04X}  {b[0] | b[1] << 8:04X}  {text}")
        else:
            shown = " ".join(f"{x:02X}" for x in b[:6]) + (" ..." if len(b) > 6 else "")
            out.append(f"x{addr:04X}  [{shown}]  {text}")
    return "\n".join(out)


def format_map(res: Result) -> str:
    lines = ["Módulos:"]
    for name, base, size in res.modules:
        lines.append(f"  {name:<20} x{base:04X}  {size} bytes")
    lines.append("Símbolos:")
    for sym, a in sorted(res.symbols.items(), key=lambda kv: kv[1]):
        lines.append(f"  x{a:04X}  {sym}")
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="lc10.assembler", description="Ensamblador de la ISA LC10")
    ap.add_argument("sources", nargs="+", help="programa principal y luego los módulos (.asm)")
    ap.add_argument("-o", "--output", help="archivo de salida (por defecto: <principal>.hex)")
    ap.add_argument("-f", "--format", choices=FORMATS, help="formato de salida (por defecto, el de la extensión de -o, o hex)")
    ap.add_argument("--listing", action="store_true", help="muestra el listado dirección / palabra / fuente")
    ap.add_argument("--map", action="store_true", help="muestra módulos y símbolos con sus direcciones")
    args = ap.parse_args(argv)
    try:
        sources = [(p, Path(p).read_text(encoding="utf-8")) for p in args.sources]
        res = assemble(sources)
    except (AsmError, OSError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    fmt = args.format or (Path(args.output).suffix.lstrip(".").lower() if args.output else "hex")
    out = Path(args.output) if args.output else Path(args.sources[0]).with_suffix("." + fmt)
    res.image.save(out, fmt)
    print(f"{out}: origen x{res.image.origin:04X}, {len(res.image.data)} bytes"
          f" ({len(res.image.data) // 2} palabras), relleno {res.pad_bytes} byte(s)")
    if args.listing:
        print(format_listing(res))
    if args.map:
        print(format_map(res))
    return 0


if __name__ == "__main__":
    sys.exit(main())
