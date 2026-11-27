"""DIV_LONG en LC10 contra el modelo exacto: resultado, ESTADO, registros y escrituras."""
import random
import unittest
from pathlib import Path

from lc10 import isa
from lc10.assembler import assemble
from lc10.simulator import Machine

ROOT = Path(__file__).resolve().parent.parent
BORDES = [-32768, -32767, -16385, -16384, -256, -95, -2, -1, 0, 1, 2, 95, 255, 256, 16383, 16384, 20000, 32766, 32767]
SENT = [0xA1A1, 0xB2B2, 0xC3C3, 0xD4D4, 0xE5E5]          # R2..R6 antes de llamar


def esperado(a, b, s=8):
    """Division larga exacta: (|a| << s) // |b| truncado, con saturacion y estado."""
    if b == 0:
        return 0, 1
    q = (abs(a) << s) // abs(b)
    if (a < 0) != (b < 0):
        q = -q
    if q > 32767:
        return 32767, 2
    if q < -32768:
        return -32768, 2
    return q, 0


def cases(n_random=20000, seed=11):
    rnd = random.Random(seed)
    out = [(a, b) for a in BORDES for b in BORDES]
    for _ in range(n_random):
        a = isa.to_s16(rnd.getrandbits(rnd.randint(0, 16)) * rnd.choice((-1, 1)))
        b = isa.to_s16(rnd.getrandbits(rnd.randint(0, 16)) * rnd.choice((-1, 1)))
        out.append((a, b))
    return out


class Harness:
    """main (JSR + HALT) + division.asm enlazados con .EXTERNAL."""

    def __init__(self, division_path=ROOT / "asm" / "division.asm"):
        main = ".ORIG x3000\n.EXTERNAL DIVISION-DIV_LONG\nJSR DIVISION-DIV_LONG\nHALT\n.END\n"
        self.res = assemble([("main.asm", main), ("division.asm", Path(division_path).read_text(encoding="utf-8"))])
        self.sym = self.res.symbols
        base = Machine()
        base.load(self.res.image)
        self.base = bytes(base.mem)
        self.data = {self.sym["DIVISION-" + k] for k in ("ESTADO", "GUARDADO_R1", "GUARDADO_R2", "GUARDADO_R3", "GUARDADO_R4", "GUARDADO_R5")}
        self.image_bytes = len(self.res.image.data)
        self.module_bytes = dict((n, size) for n, _, size in self.res.modules)["DIVISION"]

    def call(self, a, b):
        m = Machine()
        m.mem[:] = self.base
        m.pc = self.res.image.origin
        m.image_bytes = self.image_bytes
        m.regs[:] = [a & 0xFFFF, b & 0xFFFF, *SENT, 0]
        r = m.run(10000, stop_at=self.res.image.origin + 2)      # se detiene ante el HALT: sin tocar R7 ni las banderas
        return m, r


class TestDivLong(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.h = Harness()

    def test_known_examples(self):
        for a, b, exp, st in [(1408, 512, 704, 0), (-1408, 512, -704, 0), (256, 768, 85, 0), (25600, 128, 32767, 2),
                              (804, 95, 2166, 0), (256, 0, 0, 1), (-32768, 256, -32768, 0), (32767, -256, -32767, 0),
                              (-32768, -1, 32767, 2), (-32768, 1, -32768, 2), (0, -5, 0, 0)]:
            m, r = self.h.call(a, b)
            self.assertTrue(r.ok, r.message)
            self.assertEqual((isa.to_s16(m.regs[0]), m.mem[self.h.sym["DIVISION-ESTADO"]]), (exp, st), (a, b))
            self.assertEqual((exp, st), esperado(a, b), "el caso de prueba coincide con el modelo")

    def test_all_edge_and_random_cases(self):
        pc_ret = 0x3000 + 2                                      # direccion que guarda JSR
        stats = []
        for a, b in cases():
            m, r = self.h.call(a, b)
            exp, st = esperado(a, b)
            self.assertTrue(r.ok, (a, b, r.message))
            self.assertEqual(isa.to_s16(m.regs[0]), exp, (a, b))
            self.assertEqual(m.mem[self.h.sym["DIVISION-ESTADO"]], st, (a, b))
            # R1..R6 vuelven como entraron; R7 conserva la direccion de retorno que dejo JSR (se mira antes del HALT)
            self.assertEqual(m.regs[1:7], [b & 0xFFFF, *SENT], (a, b, m.regs))
            self.assertEqual(m.regs[7], pc_ret)
            # solo escribe en sus propias palabras de datos
            changed = {i for i in range(0x3000, 0x3000 + self.h.image_bytes) if m.mem[i] != self.h.base[i]}
            self.assertLessEqual(changed, self.h.data | {x + 1 for x in self.h.data}, (a, b))
            self.assertTrue(m.write_set <= self.h.data | {x + 1 for x in self.h.data})
            stats.append(r.instructions - 1)                     # sin el JSR del main (la corrida para antes del HALT)
        type(self).stats = (min(stats), max(stats), sum(stats) / len(stats), len(stats))

    def test_module_has_no_orig_and_ends_with_end(self):
        text = (ROOT / "asm" / "division.asm").read_text(encoding="utf-8")
        self.assertNotIn(".ORIG", text.upper())
        self.assertEqual(text.strip().splitlines()[-1].strip().upper(), ".END")
        # no usa R6 ni R7 como operandos (plantilla de subrutinas)
        import re
        code = "\n".join(l.split(";", 1)[0] for l in text.splitlines())
        self.assertIsNone(re.search(r"\bR[67]\b", code))


if __name__ == "__main__":
    unittest.main()
