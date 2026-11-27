"""Prueba de equivalencia del seno de Taylor (grupo 21): módulo real vs. cuentas exactas.

    python bench/equivalencia_seno.py RUTA\\lc3-project [--paso N]

Corre CALCULAR_SENO tal cual está en `lib/g21_senotaylor_subrutina.asm`, con el simulador de la cátedra,
para cada ángulo (en décimas de grado) de 0 a 3699 y algunos fuera de rango, y lo compara con un modelo
que repite SUS cuentas con enteros exactos: el mismo orden de productos y de divisiones con truncado. Esas
cuentas son las que haría una versión LC10 con MUL/DIV. También comprueba que R1 a R5 se preservan.
Con --paso N prueba un ángulo de cada N (la prueba completa tarda varios minutos).
"""
import argparse
import importlib.util
import sys
from pathlib import Path


def cargar(nombre, ruta):
    spec = importlib.util.spec_from_file_location(nombre, ruta)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[nombre] = mod
    spec.loader.exec_module(mod)
    return mod


def modelo(ang):
    """Cuentas de CALCULAR_SENO con enteros exactos (cada // es un truncado, como en el original)."""
    a16 = ang & 0xFFFF
    s = a16 - 0x10000 if a16 >= 0x8000 else a16
    if s < 0 or s > 3600:
        return 0xFFFF                                  # el original devuelve -1
    if s <= 900:
        r, sg = s, 1
    elif s <= 1800:
        r, sg = 1800 - s, 1
    elif s <= 2700:
        r, sg = s - 1800, -1
    else:
        r, sg = 3600 - s, -1
    x = (r * 12868) // 1800                            # radianes en Q3.12
    x2 = (x * x) // 4096
    x3 = (x2 * x) // 4096
    t2 = -(x3 // 6)
    x5 = (x3 * x2) // 4096
    t3 = x5 // 120
    t4 = ((t3 * x2) // 4096) // 42
    res = x + t2 + t3 - t4
    return (-res if sg < 0 else res) & 0xFFFF


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("carpeta")
    ap.add_argument("--paso", type=int, default=1)
    args = ap.parse_args()
    base = Path(args.carpeta).resolve()
    asm = cargar("asm_lc3_catedra", base / "assembler_LC3.py")
    sim = cargar("sim_lc3_catedra", base / "simulador.py")

    a = asm.Assembler()
    a.reset()
    palabras = a.assemble((base / "lib" / "g21_senotaylor_subrutina.asm").read_text(encoding="utf-8-sig"))
    obj = asm._object_bytes([a.origin] + palabras)
    entrada, centinela = a.symbols["CALCULAR_SENO"], 0x6000

    def lc3(ang):
        m = sim.LC3()
        m.load_object(obj)
        m.registers = [ang & 0xFFFF, 0x1111, 0x2222, 0x3333, 0x4444, 0x5555, 0xFE00, centinela]
        m.pc, s0 = entrada, m.steps
        while m.pc != centinela:
            m.step()
        return m.registers[0], m.steps - s0, m.registers[1:6]

    angulos = list(range(0, 3700, args.paso)) + [0xFFFF, 0x8000, 40000, 65000]
    malos, pasos, preserva = [], [], True
    for ang in angulos:
        r0, n, resto = lc3(ang)
        pasos.append(n)
        preserva &= resto == [0x1111, 0x2222, 0x3333, 0x4444, 0x5555]
        if r0 != modelo(ang):
            malos.append((ang, r0, modelo(ang)))
    print(f"casos: {len(angulos)} | distintos del modelo exacto: {len(malos)} | R1 a R5 preservados: {preserva}")
    print(f"instrucciones LC-3 por llamada: mín {min(pasos)}, prom {sum(pasos) / len(pasos):.0f}, máx {max(pasos)}")
    for m in malos[:10]:
        print("  ángulo %d: módulo real %d, modelo %d" % m)
    return 1 if malos else 0


if __name__ == "__main__":
    raise SystemExit(main())
