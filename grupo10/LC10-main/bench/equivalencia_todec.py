"""Prueba de equivalencia de TODEC (grupo 27): módulo real vs. modelo de sus cuentas.

    python bench/equivalencia_todec.py RUTA\\lc3-project [--casos N]

Corre TODEC (con SUMOVER) con el simulador de la cátedra sobre casos de borde y aleatorios (entero, fracción
y formato) y compara el texto con un modelo. El modelo reproduce lo que hace el original con la fracción:
suma, por cada bit k encendido, (10^9 << k) >> 16 truncado. NO es floor(frac * 10^9 / 65536): ese cálculo
exacto da otro noveno decimal en la mayoría de las fracciones (se informa cuántas).
"""
import argparse
import importlib.util
import random
import sys
import tempfile
from pathlib import Path


def cargar(nombre, ruta):
    spec = importlib.util.spec_from_file_location(nombre, ruta)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[nombre] = mod
    spec.loader.exec_module(mod)
    return mod


def suma_original(f):
    """Parte fraccionaria como 9 dígitos, tal como la acumula TODEC."""
    return sum((10 ** 9 << k) >> 16 for k in range(16) if f >> k & 1)


def modelo(ent16, frac16, fmt):
    out, e, f = "", ent16 & 0xFFFF, frac16 & 0xFFFF
    if e & 0x8000:
        out += "-"
        e2 = (~e) & 0xFFFF
        if f == 0:
            e2 = (e2 + 1) & 0xFFFF
        e, f = e2, (-f) & 0xFFFF
    elif fmt & 1:
        out += "+"
    for k in (4, 3, 2, 1, 0):                          # restas sucesivas con 16 bits, como el original
        cnt = 0
        while True:
            aux = (e - 10 ** k) & 0xFFFF
            if aux & 0x8000:
                break
            cnt, e = cnt + 1, aux
        if fmt & 2 or cnt:
            fmt |= 2
            out += chr(48 + cnt)
    if not fmt & 2:
        out += "0"
    if f == 0:
        return out + ("." + "0" * 9 if fmt & 4 else "")
    out += "."
    s = suma_original(f)
    for k in range(8, -1, -1):
        d, s = divmod(s, 10 ** k)
        out += chr(48 + d)
        if not fmt & 4 and s == 0:
            break
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("carpeta")
    ap.add_argument("--casos", type=int, default=5000)
    args = ap.parse_args()
    base = Path(args.carpeta).resolve()
    asm = cargar("asm_lc3_catedra", base / "assembler_LC3.py")
    sim = cargar("sim_lc3_catedra", base / "simulador.py")

    with tempfile.TemporaryDirectory() as tmp:
        principal = Path(tmp) / "t_main.asm"
        principal.write_text(".ORIG x3000\n.EXTERNAL TODEC-TODEC\nsub .FILL TODEC-TODEC\nHALT\n.END\n")
        enlazador = asm.ProjectLinker(base / "lib")
        obj = enlazador.assemble_file(principal, "obj")
        entrada = enlazador._external_addresses(enlazador.units[principal.resolve()])["TODEC-TODEC"]
    centinela, buf = 0x6000, 0x5000

    def lc3(r0, r1, fmt):
        m = sim.LC3()
        m.load_object(obj)
        m.registers = [r0, r1, buf, fmt, 0x4444, 0x5555, 0xFE00, centinela]
        m.pc, s0 = entrada, m.steps
        while m.pc != centinela:
            m.step()
        txt, a = "", buf
        while m.memory[a]:
            txt, a = txt + chr(m.memory[a] & 0xFF), a + 1
        return txt, m.steps - s0

    rnd = random.Random(7)
    casos = [(0, 0, 0), (1, 0, 0), (0xFFFF, 0, 0), (0x8000, 0, 0), (0x8000, 1, 0), (0x7FFF, 0xFFFF, 7),
             (0, 0xFFFF, 0), (0, 1, 4), (5, 0x8000, 3), (0xFFFF, 0xFFFF, 1), (0x8000, 0xFFFF, 6)]
    for _ in range(args.casos):
        casos.append((rnd.choice([rnd.randrange(65536), rnd.randrange(300), (-rnd.randrange(300)) & 0xFFFF]),
                      rnd.choice([rnd.randrange(65536), rnd.randrange(256) << 8, rnd.randrange(4096) << 4, 0]),
                      rnd.randrange(8)))
    malos, pasos = [], []
    for c in casos:
        txt, n = lc3(*c)
        pasos.append(n)
        if txt != modelo(*c):
            malos.append((c, txt, modelo(*c)))
    print(f"casos: {len(casos)} | distintos del modelo: {len(malos)} | "
          f"instrucciones LC-3 por llamada: prom {sum(pasos) / len(pasos):.0f}, máx {max(pasos)}")
    for m in malos[:10]:
        print("  ", m)
    difieren = sum(suma_original(f) != f * 10 ** 9 // 65536 for f in range(65536))
    print(f"fracciones (de 65536) donde el cálculo exacto floor(f*10^9/2^16) daría otro noveno decimal: {difieren}")
    cerrada = sum(suma_original(f) != 1953125 * (f >> 7) + sum((10 ** 9 << k) >> 16 for k in range(7) if f >> k & 1)
                  for f in range(65536))
    print(f"fórmula cerrada 1953125*(f>>7) + tabla de 7 constantes: {cerrada} diferencias de 65536")
    return 1 if malos or cerrada else 0


if __name__ == "__main__":
    raise SystemExit(main())
