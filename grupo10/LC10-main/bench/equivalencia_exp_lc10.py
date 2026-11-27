"""EXP_Q3_12 (g6): LC10 optimizado contra el puerto directo, con TODAS las entradas Q3.12 (65.536).

    python bench/equivalencia_exp_lc10.py [--opt asm/opt10] [--ref asm/bench10] [--desde 0 --hasta 65536]

Se compara R0..R5 y R7 (la rutina los preserva) y las palabras EST_EXP y NUM_ITER. El puerto directo
(bench10) ya se comparó contra el módulo LC-3 real en bench/equivalencia_modulos.py.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent))
from lc10.assembler import assemble  # noqa: E402
from lc10.simulator import Machine  # noqa: E402

MAIN = ".ORIG x3000\n.EXTERNAL g6_EXP-EXP_Q3_12\nENTRY .FILL g6_EXP-EXP_Q3_12\nHLT HALT\n.END\n"
SENT = [0x1111, 0x2222, 0x3333, 0x4444, 0x5555]


def armar(carpeta: Path):
    fu = [(p.name, p.read_text(encoding="utf-8")) for p in sorted(carpeta.glob("*.asm")) if p.name != "main_grupo27.asm"]
    r = assemble([("t_main.asm", MAIN)] + fu)
    entry = int.from_bytes(r.image.data[0:2], "little")
    return r, entry


def correr(r, entry, x):
    m = Machine()
    m.load(r.image)
    for i, v in enumerate(SENT):
        m.regs[i + 1] = v
    m.regs[0] = x
    m.regs[7] = 0x3002
    m.pc = entry
    res = m.run(200_000)
    est = int.from_bytes(bytes(m.mem[r.symbols["G6_EXP-EST_EXP"]:r.symbols["G6_EXP-EST_EXP"] + 2]), "little")
    it = int.from_bytes(bytes(m.mem[r.symbols["G6_EXP-NUM_ITER"]:r.symbols["G6_EXP-NUM_ITER"] + 2]), "little")
    return (res.reason, [m.regs[i] for i in range(8)], est, it, m.flags if hasattr(m, "flags") else None), res.user_instructions


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--opt", default=str(AQUI.parent / "asm" / "opt10"))
    ap.add_argument("--ref", default=str(AQUI.parent / "asm" / "bench10"))
    ap.add_argument("--desde", type=int, default=0)
    ap.add_argument("--hasta", type=int, default=65536)
    a = ap.parse_args()
    ro, eo = armar(Path(a.opt))
    rr, er = armar(Path(a.ref))
    malos = pa = pb = 0
    for x in range(a.desde, a.hasta):
        xs = x - 65536 if x >= 32768 else x
        (so, io), (sr, ir) = correr(ro, eo, x), correr(rr, er, x)
        pa += io
        pb += ir
        if so != sr:
            malos += 1
            if malos <= 10:
                print("DIFERENCIA", x, xs, "opt:", so, "ref:", sr)
    n = a.hasta - a.desde
    print(f"{n} entradas [{a.desde}, {a.hasta}), {malos} diferencias; instrucciones medias ref {pb // n} / opt {pa // n}")
    return 1 if malos else 0


if __name__ == "__main__":
    raise SystemExit(main())
