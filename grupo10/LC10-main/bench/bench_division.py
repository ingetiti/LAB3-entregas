"""Compara DIV_LONG en LC-3 (emulador propio) y en LC10 sobre los MISMOS casos.

Uso (desde la raíz del proyecto):  python bench/bench_division.py
Las cifras salen de emuladores propios (bench/lc3sim.py para la LC-3 y lc10/simulator.py
para la LC10), no del simulador del curso.
"""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "bench"))
from lc3sim import Sim, assemble as lc3_assemble
from tests.test_division import Harness, cases, esperado
from lc10 import isa

CASOS = cases(20000, seed=11)

# ---- LC10
h = Harness()
c10 = []
for a, b in CASOS:
    m, r = h.call(a, b)
    exp, st = esperado(a, b)
    assert isa.to_s16(m.regs[0]) == exp and m.mem[h.sym["DIVISION-ESTADO"]] == st
    c10.append(r.instructions - 1)               # sin el JSR del main (la corrida para antes del HALT)

# ---- LC-3 (la version entregada en grupo10: division.asm con DIV_LONG)
M, SENT, SP0 = 0xFFFF, 0x6000, 0xFE00
src = (RAIZ / "bench" / "lc3_division.asm").read_text(encoding="utf-8")
mem, lab = lc3_assemble(src, base=0x4000)
c3 = []
for a, b in CASOS:
    sm = Sim(dict(mem))
    sm.r = [a & M, b & M, 0x1234, 0xA1A1, 0xB2B2, 0xC3C3, SP0, SENT]
    sm.run(lab["DIV_LONG"], stop=SENT)
    exp, st = esperado(a, b)
    got = sm.r[0] - 0x10000 if sm.r[0] >= 0x8000 else sm.r[0]
    assert got == exp and sm.mem[lab["ESTADO"]] == st, (a, b, got, exp)
    c3.append(sm.steps)
words3 = lab["GUARDADO_DL_R7"] - lab["DIVIDIR"] + 1

def resumen(x):
    xs = sorted(x)
    return dict(min=xs[0], max=xs[-1], prom=round(sum(xs) / len(xs), 1), mediana=xs[len(xs) // 2], p95=xs[int(len(xs) * .95)])

print("casos:", len(CASOS))
print("LC-3 :", resumen(c3), "| modulo completo:", words3, "palabras =", 2 * words3, "bytes")
print("LC10 :", resumen(c10), "| modulo:", h.module_bytes, "bytes =", h.module_bytes // 2, "palabras")
print("reduccion de instrucciones (promedio): %.1f %%" % (100 * (1 - sum(c10) / sum(c3))))
print("reduccion de memoria del modulo: %.1f %%" % (100 * (1 - h.module_bytes / (2 * words3))))
# casos tipicos (no extremos): a y b con magnitud "normal"
tip = [(a, b) for a, b in CASOS if 256 <= abs(a) <= 20000 and 128 <= abs(b) <= 20000]
i3 = [c3[CASOS.index(x)] for x in tip[:3000]]
i10 = [c10[CASOS.index(x)] for x in tip[:3000]]
print("casos tipicos (n=%d): LC-3 prom %.1f, LC10 prom %.1f" % (len(i3), sum(i3) / len(i3), sum(i10) / len(i10)))
