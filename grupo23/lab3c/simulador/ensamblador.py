#!/usr/bin/env python3
"""
Ensamblador y enlazador de la ISA LOVELACE (Lab 3c, Grupo 23).

  * Dos pasadas por modulo; contador de posicion en BYTES.
  * Instrucciones y palabras siempre en direcciones pares: si un dato de byte
    deja la posicion impar, se inserta un byte de relleno (NOP de 8 bits).
  * .EXTERNAL MODULO-ETIQUETA con las mismas reglas que el simulador web del
    Grupo 8 (nombre de modulo sin distinguir mayusculas; dentro de un grupo se
    puede omitir el prefijo gN_; el .ORIG de los modulos se ignora).
  * Acepta los mnemonicos de la LC-3 (ADD/AND/NOT/JSRR/RET...) y los nuevos.

Salidas (junto a la salida indicada):
  .hex  imagen en hexadecimal: los dos primeros bytes son la direccion de
        origen; luego los bytes del programa (16 por linea)
  .bin  la misma imagen en binario
  .sym  tabla de simbolos  (direccion  modulo:etiqueta)
  .map  mapa de enlace     (desde  hasta  bytes  modulo)

Uso:
  python ensamblador.py <entrada.asm> [-L carpeta_lib] [-o salida(sin extension)] [-O] [-D]
                        [-S cadenas.json]

  -O  optimizacion de mirilla (ver optimizador.py): fusiona pares de
      instrucciones LC-3 en las instrucciones nuevas DBP y BRR cuando es
      seguro hacerlo.
  -D  eliminacion de codigo y datos muertos (ver eliminar_muerto.py): borra lo
      que el programa no puede alcanzar ni nombrar; deja el detalle en
      <salida>_muerto.txt.
  -S  empaqueta las cadenas .STRINGZ de la lista (generada por
      buscar_cadenas.py) como .STRINGP: dos caracteres por palabra y una
      palabra 0 al final. El servicio PUTS imprime los dos formatos.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from isa import OP, ALU_F, LOG_F, SHL_F, SHA_F, BRX_C, TRAP_ALIAS, MUL_F, DIV_F

DIRECTIVES = {".ORIG", ".FILL", ".BLKW", ".STRINGZ", ".STRINGB", ".STRINGP", ".BYTE",
              ".ALIGN", ".END", ".EXTERNAL"}
SIMPLE = {"ADD", "SUB", "ADC", "ADDX", "AND", "OR", "XOR", "NOT", "LD", "ST",
          "LDR", "STR", "LDB", "LDBH", "STB", "STBH", "LEA", "JSR", "JSRR",
          "JMP", "RET", "RTI", "TRAP", "LSL", "LSR", "ASR", "RLC", "DBP",
          "PUSH", "POP", "NOP"} | set(TRAP_ALIAS) | set(BRX_C) | set(MUL_F) | set(DIV_F)
LC3_OPS = {"ADD", "AND", "NOT", "LD", "ST", "LDR", "STR", "LEA", "JSR", "JSRR",
           "JMP", "RET", "RTI", "TRAP"} | set(TRAP_ALIAS)
NUEVOS = SIMPLE - LC3_OPS
SIN_OPERANDOS = {"NOP"}          # solo en una linea siempre es la instruccion
BR_RE = re.compile(r"^BR(N?Z?P?)$")
BRR_RE = re.compile(r"^BRR(N?Z?P?)$")
REG_RE = re.compile(r"^R([0-7])$")


class AsmError(Exception):
    pass


def is_op(tok):
    t = tok.upper()
    return t in SIMPLE or t in DIRECTIVES or BR_RE.match(t) or BRR_RE.match(t)


# ---------------------------------------------------------------- lexico ----
def strip_comment(line):
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
        else:
            if ch == ";":
                break
            if ch == '"':
                in_str = True
            out.append(ch)
    return "".join(out)


def tokenize(line):
    toks, i, n = [], 0, len(line)
    while i < n:
        ch = line[i]
        if ch in " \t,\r\n":
            i += 1
        elif ch == '"':
            j, esc = i + 1, False
            while j < n:
                if esc:
                    esc = False
                elif line[j] == "\\":
                    esc = True
                elif line[j] == '"':
                    break
                j += 1
            toks.append(line[i:j + 1])
            i = j + 1
        else:
            j = i
            while j < n and line[j] not in " \t,\r\n":
                j += 1
            toks.append(line[i:j])
            i = j
    return toks


def parse_number(tok):
    t = tok.strip()
    if t.startswith("#"):
        return int(t[1:], 10)
    if t[:1] in "xX" and len(t) > 1:
        body = t[1:]
        neg = body.startswith("-")
        v = int(body.lstrip("-"), 16)
        return -v if neg else v
    if t[:2].lower() == "0x":
        return int(t[2:], 16)
    if t[:1] in "bB" and len(t) > 1 and set(t[1:]) <= {"0", "1"}:
        return int(t[1:], 2)
    if re.fullmatch(r"-?\d+", t):
        return int(t, 10)
    raise ValueError(tok)


def unescape(s):
    body = s[1:-1]
    res, i = [], 0
    while i < len(body):
        c = body[i]
        if c == "\\" and i + 1 < len(body):
            nxt = body[i + 1]
            res.append({"n": "\n", "t": "\t", "r": "\r", "0": "\0",
                        '"': '"', "\\": "\\"}.get(nxt, nxt))
            i += 2
        else:
            res.append(c)
            i += 1
    return "".join(res)


# ---------------------------------------------------------------- modulo ----
class Module:
    def __init__(self, key, path, is_entry=False):
        self.key, self.path, self.is_entry = key, path, is_entry
        m = re.match(r"g(\d+)_", key)
        self.group = int(m.group(1)) if m else None
        self.items = []          # (linea, op, args, offset, tamano, relleno_previo)
        self.labels = {}
        self.externals = []
        self.orig = None
        self._parse()

    def _parse(self):
        with open(self.path, encoding="utf-8", errors="replace") as fh:
            lines = fh.read().splitlines()
        off, pending = 0, []
        for ln, raw in enumerate(lines, 1):
            toks = tokenize(strip_comment(raw))
            if not toks:
                continue
            first = toks[0].rstrip(":").upper()
            es_etiqueta = not is_op(first) or toks[0].endswith(":")
            # mnemonicos nuevos de la ISA LOVELACE usados como etiqueta en codigo LC-3
            # (p. ej. una subrutina llamada ASR): solo, o seguido de otra instruccion
            if (not es_etiqueta and first in NUEVOS and first not in SIN_OPERANDOS
                    and (len(toks) == 1 or is_op(toks[1]))):
                es_etiqueta = True
            if es_etiqueta:
                pending.append(toks[0].rstrip(":").upper())
                toks = toks[1:]
            if not toks:
                continue
            op, args = toks[0].upper(), toks[1:]
            if not is_op(op):
                raise AsmError(f"{self.path}:{ln}: instruccion desconocida '{toks[0]}'")
            if op == ".END":
                break
            if op == ".EXTERNAL":
                self.externals += [a.upper() for a in args]
                continue
            if op == ".ORIG":
                if self.orig is None:
                    self.orig = parse_number(args[0])
                continue
            byte_data = op in (".STRINGB", ".BYTE")
            pad = 0
            if not byte_data and off % 2:
                pad = 1                       # NOP de 8 bits para alinear
            if op == ".ALIGN":
                pad = (-off) % 2
            off += pad
            for p in pending:
                if p in self.labels:
                    raise AsmError(f"{self.path}:{ln}: etiqueta duplicada {p}")
                self.labels[p] = off
            size = self._size(op, args)
            # item: [linea, op, args, offset, tamano, relleno, etiquetas]
            self.items.append([ln, op, args, off, size, pad, pending])
            pending = []
            off += size
        for p in pending:
            self.labels[p] = off
        self.tail_labels = pending
        self.size = off + (off % 2)

    def relayout(self):
        """Recalcula offsets y etiquetas despues de modificar la lista de items."""
        off, self.labels = 0, {}
        for it in self.items:
            op = it[1]
            pad = 0
            if op not in (".STRINGB", ".BYTE") and off % 2:
                pad = 1
            if op == ".ALIGN":
                pad = (-off) % 2
            off += pad
            it[3], it[5] = off, pad
            for p in it[6]:
                self.labels[p] = off
            off += it[4]
        for p in self.tail_labels:
            self.labels[p] = off
        self.size = off + (off % 2)

    @staticmethod
    def _size(op, args):
        if op == ".BLKW":
            return 2 * parse_number(args[0])
        if op == ".STRINGZ":
            return 2 * sum(len(unescape(a)) + 1 for a in args)
        if op == ".STRINGB":
            return sum(len(unescape(a)) + 1 for a in args)
        if op == ".STRINGP":
            n = len(unescape(args[0]))
            return n + n % 2 + 2                # bytes del texto, relleno par y palabra 0
        if op == ".BYTE":
            return len(args)
        if op == ".ALIGN":
            return 0
        return 2


# --------------------------------------------------------------- enlazador --
class Program:
    def __init__(self, entry_path, lib_dir=None, own_group=23, optimizar=False, sin_muerto=False,
                 empaquetar=None):
        self.lib = {}
        for fn in sorted(os.listdir(lib_dir)) if lib_dir else []:
            if fn.lower().endswith(".asm"):
                key = fn[:-4].lower()
                if not re.match(r"g\d+_", key):
                    key = f"g{own_group}_{key}"
                self.lib[key] = os.path.join(lib_dir, fn)
        self.entry = Module("entrada", entry_path, True)
        self.modules, self.by_key = [self.entry], {"entrada": self.entry}
        self._collect(self.entry)
        self.fusiones = {}
        self.quitados = []
        self.empaquetadas = self._empaquetar(empaquetar) if empaquetar else (0, 0)
        if sin_muerto:
            from eliminar_muerto import eliminar
            self.quitados = eliminar(self)
        if optimizar:
            from optimizador import optimizar_modulo
            tipos = tuple(optimizar) if isinstance(optimizar, (set, tuple, list)) else ("DBP", "BRR")
            for m in self.modules:
                self.fusiones[m.key] = optimizar_modulo(m, tipos)
        addr = self.entry.orig if self.entry.orig is not None else 0x3000
        if addr % 2:
            raise AsmError(".ORIG debe ser una direccion par")
        self.origin = addr
        for m in self.modules:
            m.base = addr
            addr += m.size
        self.end = addr
        self.image = bytearray(self.end - self.origin)
        self.owner = {}
        for m in self.modules:
            for it in m.items:
                self._emit(m, it)

    def _empaquetar(self, lista):
        """Convierte en .STRINGP las cadenas .STRINGZ de la lista [(modulo, etiqueta)]."""
        pedidas = {(k.lower(), e.upper()) for k, e in lista}
        n = ahorro = 0
        for m in self.modules:
            cambio = False
            for it in m.items:
                if it[1] != ".STRINGZ" or len(it[2]) != 1:
                    continue
                if not any((m.key, e) in pedidas for e in it[6]):
                    continue
                texto = unescape(it[2][0])
                if any(ord(c) == 0 or ord(c) > 0xFF for c in texto):
                    raise AsmError(f"{m.path}:{it[0]}: la cadena no se puede empaquetar")
                nuevo = Module._size(".STRINGP", it[2])
                ahorro += it[4] - nuevo
                it[1], it[4] = ".STRINGP", nuevo
                n += 1
                cambio = True
            if cambio:
                m.relayout()
        return n, ahorro

    def resolve_key(self, mod, ref):
        for c in [ref] + ([f"g{mod.group}_{ref}"] if mod.group is not None
                          and not re.match(r"g\d+_", ref) else []):
            if c in self.lib or c in self.by_key:
                return c
        raise AsmError(f"{mod.path}: no se encuentra el modulo '{ref}'")

    def _collect(self, mod):
        for ext in mod.externals:
            key = self.resolve_key(mod, ext.partition("-")[0].lower())
            if key not in self.by_key:
                m = Module(key, self.lib[key])
                self.by_key[key] = m
                self.modules.append(m)
                self._collect(m)

    def symbol(self, mod, name):
        u = name.upper()
        if u in mod.labels:
            return mod.base + mod.labels[u]
        if u in mod.externals:
            ref, _, lab = u.partition("-")
            tgt = self.by_key[self.resolve_key(mod, ref.lower())]
            if lab not in tgt.labels:
                raise AsmError(f"{mod.path}: '{lab}' no existe en {tgt.key}")
            return tgt.base + tgt.labels[lab]
        raise AsmError(f"{mod.path}: etiqueta no definida '{name}'")

    def value(self, mod, tok):
        u = tok.upper()
        if u in mod.labels or u in mod.externals:
            return self.symbol(mod, tok)
        try:
            return parse_number(tok)
        except ValueError:
            return self.symbol(mod, tok)

    def _put_word(self, addr, w, m, ln):
        i = addr - self.origin
        self.image[i] = w & 0xFF              # little-endian
        self.image[i + 1] = (w >> 8) & 0xFF
        self.owner[addr] = (m.key, ln)

    def _emit(self, m, it):
        ln, op, args, off, size, pad = it[:6]
        addr = m.base + off
        try:
            if op == ".FILL":
                self._put_word(addr, self.value(m, args[0]), m, ln)
            elif op == ".BLKW":
                fill = self.value(m, args[1]) if len(args) > 1 else 0
                for k in range(size // 2):
                    self._put_word(addr + 2 * k, fill, m, ln)
            elif op == ".STRINGZ":
                k = 0
                for s in args:
                    for c in unescape(s) + "\0":
                        self._put_word(addr + 2 * k, ord(c), m, ln)
                        k += 1
            elif op == ".STRINGP":
                b = [ord(c) for c in unescape(args[0])]
                b += [0] * (len(b) % 2) + [0, 0]
                for k in range(0, len(b), 2):
                    self._put_word(addr + k, b[k] | (b[k + 1] << 8), m, ln)
            elif op == ".STRINGB":
                k = 0
                for s in args:
                    for c in unescape(s) + "\0":
                        self.image[addr - self.origin + k] = ord(c) & 0xFF
                        k += 1
            elif op == ".BYTE":
                for k, a in enumerate(args):
                    self.image[addr - self.origin + k] = self.value(m, a) & 0xFF
            elif op == ".ALIGN":
                pass
            else:
                self._put_word(addr, self.encode(m, addr, op, args), m, ln)
        except (ValueError, IndexError, AsmError) as e:
            raise AsmError(f"{m.path}:{ln}: {op} {' '.join(args)} -> {e}")

    # ---- codificacion ----
    @staticmethod
    def reg(t):
        mm = REG_RE.match(t.upper())
        if not mm:
            raise ValueError(f"registro invalido {t}")
        return int(mm.group(1))

    @staticmethod
    def imm(v, bits, signed=True):
        lo, hi = (-(1 << (bits - 1)), (1 << (bits - 1)) - 1) if signed else (0, (1 << bits) - 1)
        if not lo <= v <= hi:
            raise ValueError(f"valor {v} fuera de rango ({bits} bits)")
        return v & ((1 << bits) - 1)

    def pcoff(self, m, addr, tok, bits):
        """Desplazamiento relativo al PC en palabras: (destino - (dir+2)) / 2."""
        u = tok.upper()
        if u not in m.labels and u not in m.externals:
            try:
                return self.imm(parse_number(tok), bits)
            except ValueError:
                pass
        d = self.symbol(m, tok) - (addr + 2)
        if d % 2:
            raise ValueError("destino en direccion impar")
        return self.imm(d // 2, bits)

    def encode(self, m, addr, op, a):
        R, I = self.reg, self.imm
        o = lambda name: OP[name] << 11
        if op in ("ADD", "AND"):
            if REG_RE.match(a[2].upper()):
                f = ALU_F["ADD"] if op == "ADD" else LOG_F["AND"]
                return o("ALU" if op == "ADD" else "LOG") | R(a[0]) << 8 | R(a[1]) << 5 | R(a[2]) << 2 | f
            return o("ADDI" if op == "ADD" else "ANDI") | R(a[0]) << 8 | R(a[1]) << 5 | I(parse_number(a[2]), 5)
        if op in MUL_F:
            return o("MUL") | R(a[0]) << 8 | R(a[1]) << 5 | R(a[2]) << 2 | MUL_F[op]
        if op in DIV_F:
            return o("DIV") | R(a[0]) << 8 | R(a[1]) << 5 | R(a[2]) << 2 | DIV_F[op]
        if op in ("SUB", "ADC", "ADDX"):
            return o("ALU") | R(a[0]) << 8 | R(a[1]) << 5 | R(a[2]) << 2 | ALU_F[op]
        if op in ("OR", "XOR"):
            return o("LOG") | R(a[0]) << 8 | R(a[1]) << 5 | R(a[2]) << 2 | LOG_F[op]
        if op == "NOT":
            return o("LOG") | R(a[0]) << 8 | R(a[1]) << 5 | LOG_F["NOT"]
        if op in SHL_F or op in SHA_F:
            n = parse_number(a[2])
            if not 1 <= n <= 16:
                raise ValueError("cantidad de corrimiento entre 1 y 16")
            f = SHL_F.get(op, SHA_F.get(op))
            return o("SHL" if op in SHL_F else "SHA") | R(a[0]) << 8 | R(a[1]) << 5 | f << 4 | (n - 1)
        mb = BR_RE.match(op)
        if mb:
            fl = mb.group(1) or "NZP"
            nzp = (4 if "N" in fl else 0) | (2 if "Z" in fl else 0) | (1 if "P" in fl else 0)
            return nzp << 9 | self.pcoff(m, addr, a[0], 9)
        mr = BRR_RE.match(op)
        if mr:
            fl = mr.group(1) or "NZP"
            nzp = (4 if "N" in fl else 0) | (2 if "Z" in fl else 0) | (1 if "P" in fl else 0)
            return o("BRR") | R(a[0]) << 8 | nzp << 5 | self.pcoff(m, addr, a[1], 5)
        if op in BRX_C:
            return o("BRX") | BRX_C[op] << 8 | self.pcoff(m, addr, a[0], 8)
        if op == "DBP":
            return o("DBP") | R(a[0]) << 8 | self.pcoff(m, addr, a[1], 8)
        if op in ("LD", "ST", "LEA"):
            base = {"LD": 0x2000, "ST": 0x3000, "LEA": 0xE000}[op]
            return base | R(a[0]) << 9 | self.pcoff(m, addr, a[1], 9)
        if op in ("LDR", "STR"):
            base = 0x6000 if op == "LDR" else 0x7000
            return base | R(a[0]) << 9 | R(a[1]) << 6 | I(parse_number(a[2]), 6)
        if op in ("LDB", "LDBH", "STB", "STBH"):
            return o(op) | R(a[0]) << 8 | R(a[1]) << 5 | I(parse_number(a[2]), 5)
        if op == "JSR":
            return o("JSR") | self.pcoff(m, addr, a[0], 11)
        if op == "JMP":
            return o("JMP") | R(a[0]) << 5
        if op == "JSRR":
            return o("JMP") | 0x400 | R(a[0]) << 5
        if op == "RET":
            return o("JMP") | 7 << 5
        if op == "RTI":
            return o("RTI")
        if op in ("PUSH", "POP"):
            mask = 0
            for t in a:
                r = R(t)
                if r == 6:
                    raise ValueError("R6 es el puntero de pila")
                mask |= 1 << r
            return o("PUSHPOP") | (0x400 if op == "POP" else 0) | mask
        if op == "TRAP":
            return o("TRAP") | I(parse_number(a[0]), 8, signed=False)
        if op in TRAP_ALIAS:
            return o("TRAP") | TRAP_ALIAS[op]
        if op == "NOP":
            return 0x0000                 # BR sin condiciones
        raise ValueError(f"instruccion no soportada {op}")

    # ---- salidas ----
    def write(self, base_out):
        img = bytes([self.origin >> 8, self.origin & 0xFF]) + bytes(self.image)
        with open(base_out + ".bin", "wb") as fh:
            fh.write(img)
        with open(base_out + ".hex", "w") as fh:
            for i in range(0, len(img), 16):
                fh.write(" ".join(f"{b:02X}" for b in img[i:i + 16]) + "\n")
        with open(base_out + ".sym", "w", encoding="utf-8") as fh:
            for m in self.modules:
                for lab, off in sorted(m.labels.items(), key=lambda x: x[1]):
                    fh.write(f"x{m.base + off:04X} {m.key}:{lab}\n")
        with open(base_out + ".map", "w", encoding="utf-8") as fh:
            for m in self.modules:
                fh.write(f"x{m.base:04X} x{m.base + m.size - 1:04X} {m.size:6d} {m.key}\n")
            fh.write(f"TOTAL {self.end - self.origin} bytes x{self.origin:04X}-x{self.end - 1:04X}\n")


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    entry = argv[1]
    lib = argv[argv.index("-L") + 1] if "-L" in argv else None
    out = argv[argv.index("-o") + 1] if "-o" in argv else os.path.splitext(entry)[0]
    try:
        lista = None
        if "-S" in argv:
            import json
            lista = [(c["modulo"], c["etiqueta"]) for c in
                     json.load(open(argv[argv.index("-S") + 1], encoding="utf-8"))["cadenas"]]
        prog = Program(entry, lib, optimizar="-O" in argv, sin_muerto="-D" in argv, empaquetar=lista)
    except AsmError as e:
        print("ERROR:", e)
        return 1
    prog.write(out)
    if prog.fusiones:
        tot = {}
        for k, d in prog.fusiones.items():
            for t, n in d.items():
                tot[t] = tot.get(t, 0) + n
        print("Optimizacion de mirilla (-O):", ", ".join(f"{t}: {n}" for t, n in sorted(tot.items())))
    if "-D" in argv:
        with open(out + "_muerto.txt", "w", encoding="utf-8") as fh:
            for k, a, b, nb, labs in prog.quitados:
                fh.write(f"{k}:{a}-{b} {nb} bytes {' '.join(labs)}\n")
        print(f"Eliminacion de codigo muerto (-D): {len(prog.quitados)} bloques, "
              f"{sum(q[3] for q in prog.quitados)} bytes -> {out}_muerto.txt")
    if "-S" in argv:
        print(f"Cadenas empaquetadas (-S): {prog.empaquetadas[0]}, {prog.empaquetadas[1]} bytes menos")
    n = prog.end - prog.origin
    print(f"OK: {len(prog.modules)} modulos, {n} bytes ({n // 2} palabras) "
          f"x{prog.origin:04X}-x{prog.end - 1:04X} -> {out}.hex")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
