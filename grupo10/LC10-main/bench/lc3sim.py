"""Mini ensamblador + simulador de LC-3 base, solo para validar division.asm / main.asm."""
import re

M16 = 0xFFFF
OPS = {"ADD", "AND", "NOT", "JMP", "RET", "JSR", "JSRR", "LD", "LDI", "LDR", "LEA",
       "ST", "STI", "STR", "TRAP", "HALT", "RTI"}
BRS = {"BR": 7, "BRN": 4, "BRZ": 2, "BRP": 1, "BRNZ": 6, "BRNP": 5, "BRZP": 3, "BRNZP": 7}


def num(tok):
    tok = tok.strip()
    if tok[0] == "#":
        return int(tok[1:])
    if tok[0] in "xX":
        return int(tok[1:], 16)
    return int(tok)


def reg(tok):
    assert tok.upper() in {f"R{i}" for i in range(8)}, tok
    return int(tok[1])


def sx(v, bits):
    v &= (1 << bits) - 1
    return v - (1 << bits) if v & (1 << (bits - 1)) else v


def fits(v, bits, what):
    assert -(1 << (bits - 1)) <= v < (1 << (bits - 1)), f"{what}: {v} no entra en {bits} bits"
    return v & ((1 << bits) - 1)


def parse(src):
    lines = []
    for raw in src.splitlines():
        line = raw.split(";")[0].strip()
        if not line:
            continue
        toks = re.split(r"[\s,]+", line)
        label = None
        head = toks[0].upper().rstrip(":")
        if not (head in OPS or head in BRS or head.startswith(".")):
            label, toks = toks[0].rstrip(":"), toks[1:]
        lines.append((label, toks))
    return lines


def assemble(src, base=0x3000):
    lines = parse(src)
    for _, t in lines:                      # primer .ORIG manda
        if t and t[0].upper() == ".ORIG":
            base = num(t[1])
            break
    labels, addr = {}, base
    sizes = []
    for label, toks in lines:
        if label:
            labels[label] = addr
        if not toks:
            sizes.append(0)
            continue
        op = toks[0].upper()
        if op == ".ORIG":
            sizes.append(0)
        elif op in (".END", ".EXTERNAL"):
            sizes.append(0)
        elif op == ".BLKW":
            sizes.append(num(toks[1]))
            addr += num(toks[1])
        elif op == ".STRINGZ":
            n = len(" ".join(toks[1:]).strip('"')) + 1
            sizes.append(n)
            addr += n
        else:
            sizes.append(1)
            addr += 1
    mem, addr = {}, base
    for (label, toks), size in zip(lines, sizes):
        if not toks:
            continue
        op, a = toks[0].upper(), toks[1:]
        if op in (".ORIG", ".END", ".EXTERNAL"):
            continue
        if op == ".BLKW":
            addr += size
            continue
        pc = addr + 1

        def off(tok, bits):
            t = labels[tok] - pc if tok in labels else num(tok)
            return fits(t, bits, f"{op} {tok}")
        if op == ".FILL":
            w = labels[a[0]] if a[0] in labels else num(a[0])
            w &= M16
        elif op in ("ADD", "AND"):
            opc = 1 if op == "ADD" else 5
            if a[2].upper().startswith("R"):
                w = opc << 12 | reg(a[0]) << 9 | reg(a[1]) << 6 | reg(a[2])
            else:
                w = opc << 12 | reg(a[0]) << 9 | reg(a[1]) << 6 | 1 << 5 | fits(num(a[2]), 5, "imm5")
        elif op == "NOT":
            w = 9 << 12 | reg(a[0]) << 9 | reg(a[1]) << 6 | 0x3F
        elif op in BRS:
            w = BRS[op] << 9 | off(a[0], 9)
        elif op == "JMP":
            w = 12 << 12 | reg(a[0]) << 6
        elif op == "RET":
            w = 12 << 12 | 7 << 6
        elif op == "JSR":
            w = 4 << 12 | 1 << 11 | off(a[0], 11)
        elif op == "JSRR":
            w = 4 << 12 | reg(a[0]) << 6
        elif op in ("LD", "LDI", "LEA", "ST", "STI"):
            opc = {"LD": 2, "LDI": 10, "LEA": 14, "ST": 3, "STI": 11}[op]
            w = opc << 12 | reg(a[0]) << 9 | off(a[1], 9)
        elif op in ("LDR", "STR"):
            w = (6 if op == "LDR" else 7) << 12 | reg(a[0]) << 9 | reg(a[1]) << 6 | fits(num(a[2]), 6, "off6")
        elif op == "HALT":
            w = 0xF025
        elif op == "TRAP":
            w = 0xF000 | num(a[0])
        else:
            raise ValueError(op)
        mem[addr] = w
        addr += 1
    return mem, labels


class Sim:
    def __init__(self, mem):
        self.mem = dict(mem)
        self.r = [0] * 8
        self.pc = 0
        self.n = self.z = self.p = False
        self.steps = 0

    def rd(self, a):
        return self.mem.get(a & M16, 0)

    def wr(self, a, v):
        self.mem[a & M16] = v & M16

    def cc(self, v):
        v &= M16
        self.n, self.z, self.p = bool(v & 0x8000), v == 0, v != 0 and not v & 0x8000

    def run(self, pc, stop=None, limit=5_000_000):
        self.pc = pc
        while True:
            if self.pc == stop:
                return
            w = self.rd(self.pc)
            self.pc = (self.pc + 1) & M16
            self.steps += 1
            assert self.steps < limit, "demasiados pasos"
            op, dr, sr1 = w >> 12, (w >> 9) & 7, (w >> 6) & 7
            if op in (1, 5):
                b = sx(w, 5) if w & 0x20 else self.r[w & 7]
                a = self.r[sr1]
                self.r[dr] = ((a + b) if op == 1 else (a & b)) & M16
                self.cc(self.r[dr])
            elif op == 9:
                self.r[dr] = ~self.r[sr1] & M16
                self.cc(self.r[dr])
            elif op == 0:
                if (w >> 9) & 7 & (4 * self.n + 2 * self.z + self.p):
                    self.pc = (self.pc + sx(w, 9)) & M16
            elif op == 12:
                self.pc = self.r[sr1]
            elif op == 4:
                t = self.r[sr1]
                self.r[7] = self.pc
                self.pc = (self.pc + sx(w, 11)) & M16 if w & 0x800 else t
            elif op == 2:
                self.r[dr] = self.rd(self.pc + sx(w, 9)); self.cc(self.r[dr])
            elif op == 10:
                self.r[dr] = self.rd(self.rd(self.pc + sx(w, 9))); self.cc(self.r[dr])
            elif op == 6:
                self.r[dr] = self.rd(self.r[sr1] + sx(w, 6)); self.cc(self.r[dr])
            elif op == 14:
                self.r[dr] = (self.pc + sx(w, 9)) & M16
            elif op == 3:
                self.wr(self.pc + sx(w, 9), self.r[dr])
            elif op == 11:
                self.wr(self.rd(self.pc + sx(w, 9)), self.r[dr])
            elif op == 7:
                self.wr(self.r[sr1] + sx(w, 6), self.r[dr])
            elif op == 15:
                if w & 0xFF == 0x25:
                    return
                raise NotImplementedError(hex(w))
            else:
                raise NotImplementedError(hex(w))
