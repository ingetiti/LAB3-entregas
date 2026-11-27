"""SUMOVER y CIRCLSH en LC10 (asm/opt10) contra su definición, con muchos casos.

    python bench/equivalencia_chicos_lc10.py [asm/opt10] [--solo SUMOVER|CIRCLSH] [--parte K/N]

Con --parte K/N (K de 0 a N-1) se recorre solo cada N-esimo caso, empezando por el K-esimo.

Las definiciones son las cuentas del módulo LC-3 de la cátedra (que bench/equivalencia_modulos.py contrasta
con el módulo real en el simulador de la cátedra con miles de casos al azar):
  * SUMOVER: (A + B + c) mod 2^16 y el acarreo de salida, con c en {0, 1}.
  * CIRCLSH: giro a la izquierda de 32 bits [B:A], n veces, solo si n > 0 con signo (n vale 1 a 32767: el
    original hace n pasadas, acá se compara con girar n mod 32).
Prueba todos los n de 16 bits con A y B al azar y todos los A, B extremos, y comprueba R2 a R5.
"""
import random
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent))
from lc10.assembler import assemble  # noqa: E402
from lc10.simulator import Machine  # noqa: E402


def preparar(carpeta, archivo, etiqueta):
    stem = archivo[:-4].upper()
    main = f".ORIG x3000\n.EXTERNAL {stem}-{etiqueta}\nENTRY .FILL {stem}-{etiqueta}\nHLT HALT\n.END\n"
    res = assemble([("t_main.asm", main), (archivo, (carpeta / archivo).read_text(encoding="utf-8"))])
    return res.image, int.from_bytes(res.image.data[0:2], "little")


def llamar(img, entrada, regs):
    m = Machine()
    m.load(img)
    m.regs[:] = regs
    m.pc = entrada
    r = m.run(1000, stop_at=0x3002)                  # se detiene al volver, antes del HALT del SO
    assert r.reason == "halt", r.message
    return m.regs[:8], r.user_instructions


def main():
    solo = sys.argv[sys.argv.index("--solo") + 1].upper() if "--solo" in sys.argv else None
    parte, partes = 0, 1
    if "--parte" in sys.argv:
        parte, partes = (int(x) for x in sys.argv[sys.argv.index("--parte") + 1].split("/"))
    args = [a for a in sys.argv[1:] if not a.startswith("--") and a.upper() != solo
            and a != (sys.argv[sys.argv.index("--parte") + 1] if "--parte" in sys.argv else None)]
    visto = [0]
    carpeta = Path(args[0] if args else AQUI.parent / "asm" / "opt10")
    azar = random.Random(7)
    extremos = [0, 1, 2, 0x7FFF, 0x8000, 0x8001, 0xFFFE, 0xFFFF, 0x1234, 0xAAAA, 0x5555]
    malos = 0

    malos2 = 0
    if solo in (None, "SUMOVER"):
        img, ent = preparar(carpeta, "g27_sumover.asm", "SUMOVER")
        casos, pasos = 0, []
        pares = [(a, b) for a in extremos for b in extremos] + [(azar.randrange(65536), azar.randrange(65536)) for _ in range(100_000)]
        for a, b in pares:
            for c in (0, 1):
                visto[0] += 1
                if visto[0] % partes != parte:
                    continue
                regs, n = llamar(img, ent, [a, b, c, 0x3333, 0x4444, 0x5555, 0xFE00, 0x3002])
                total = a + b + c
                esperado = [total & 0xFFFF, b, total >> 16, 0x3333, 0x4444, 0x5555, 0xFE00, 0x3002]
                casos, pasos = casos + 1, pasos + [n]
                if regs != esperado:
                    malos += 1
                    if malos < 5:
                        print("SUMOVER", a, b, c, regs, esperado)
        print(f"SUMOVER: {casos} casos, distintos: {malos}, instrucciones por llamada: {min(pasos)}")

    if solo in (None, "CIRCLSH"):
        img, ent = preparar(carpeta, "g27_circlsh.asm", "CIRCLSH")
        casos, malos2, pasos = 0, 0, []
        for n in range(65536):
            for _ in range(3):
                a, b = azar.randrange(65536), azar.randrange(65536)
                for aa, bb in ((a, b),) if n > 40 and n % 97 else [(a, b)] + [(x, y) for x in (0, 0xFFFF, 0x8000, 1) for y in (0, 0xFFFF, 0x8001)][:2]:
                    visto[0] += 1
                    if visto[0] % partes != parte:
                        continue
                    regs, k = llamar(img, ent, [aa, bb, n, 0x3333, 0x4444, 0x5555, 0xFE00, 0x3002])
                    s = n - 65536 if n >= 32768 else n
                    v = (bb << 16) | aa
                    if s > 0:
                        r = s % 32
                        v = ((v << r) | (v >> (32 - r))) & 0xFFFFFFFF
                    esperado = [v & 0xFFFF, v >> 16, n, 0x3333, 0x4444, 0x5555, 0xFE00, 0x3002]
                    casos, pasos = casos + 1, pasos + [k]
                    if regs != esperado:
                        malos2 += 1
                        if malos2 < 5:
                            print("CIRCLSH", aa, bb, n, regs, esperado)
        print(f"CIRCLSH: {casos} casos, distintos: {malos2}, instrucciones por llamada: mín {min(pasos)}, máx {max(pasos)}")
    return 1 if malos or malos2 else 0


if __name__ == "__main__":
    raise SystemExit(main())
