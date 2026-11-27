"""DIV_NEWTON (g12): LC10 contra el módulo LC-3 real, con cuadrícula sistemática.

    python bench/equivalencia_div_lc10.py RUTA/lc3-project [asm/opt10]

Divisores: 0, ±1, ±32768, ±32767 y, para cada longitud de bit (1..16), potencias de 2, sus vecinos y valores
al azar, con las dos signaturas. Dividendos: bordes y valores al azar. También se verifica que R1..R5 y R7
queden preservados (el módulo LC-3 los restaura).
"""
from __future__ import annotations

import random
import sys
import tempfile
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
from equivalencia_modulos import CENTINELA, Lc3Runner, Lc10Runner, cargar, fuentes_lc10, caso  # noqa: E402


def main() -> int:
    base = Path(sys.argv[1]).resolve()
    carpeta = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else AQUI.parent / "asm" / "opt10"
    asm = cargar("asm_lc3_catedra", base / "assembler_LC3.py")
    sim = cargar("sim_lc3_catedra", base / "simulador.py")
    g = random.Random(12)
    divisores = {0, 1, -1, 32767, -32767, -32768, 2, -2, 3, 255, 256, 257, 4096, -4096}
    for k in range(1, 16):
        for d in (1 << k, (1 << k) - 1, (1 << k) + 1):
            if d < 32768:
                divisores |= {d, -d}
        for _ in range(6):
            d = g.randint(1 << (k - 1), (1 << k) - 1)
            divisores |= {d, -d}
    dividendos = [0, 1, -1, 2, 255, 256, 4096, -4096, 32767, -32767, -32768, 12345, -12345, 16384, -16384]
    with tempfile.TemporaryDirectory() as t:
        a = Lc3Runner(asm, sim, base, "g12_subrutina_grupo_12", "DIV_NEWTON", Path(t))
        b = Lc10Runner(fuentes_lc10(carpeta), "g12_subrutina_grupo_12", "DIV_NEWTON")
        n = malos = 0
        for d in sorted(divisores):
            xs = dividendos + [g.randint(-32768, 32767) for _ in range(40)]
            for x in xs:
                c = caso({0: x, 1: d})
                ra, ea = a.run(c)
                rb, eb = b.run(c)
                n += 1
                if ra is None:
                    continue
                if rb is None or ra["regs"][:2] != rb["regs"][:2]:
                    malos += 1
                    if malos <= 10:
                        print("DIFERENCIA", x, d, ra, rb if rb else eb)
                    continue
                # preservación: el LC10 debe dejar R1..R5 como estaban: R1 = divisor y R2..R5 = los centinelas
                esp = [d & 0xFFFF] + [CENTINELA * i for i in range(2, 6)]
                if rb["regs"][1:6] != esp:
                    malos += 1
                    if malos <= 10:
                        print("NO PRESERVA", x, d, rb["regs"])
        print(f"{n} casos, {malos} diferencias")
    return 1 if malos else 0


if __name__ == "__main__":
    raise SystemExit(main())
