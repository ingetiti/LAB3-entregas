"""Benchmark del curso en LC10: ensambla el puerto, lo ejecuta y lo compara con la línea base LC-3.

    python bench/lc10_bench.py [asm/bench10] [--main main_grupo27.asm] [--ref bench/lc3_baseline_salida.txt]

Qué mide (con el simulador funcional de este proyecto):
  * instrucciones ejecutadas (cada una cuenta 1, incluidas MUL/DIV), las del usuario y las del SO (las rutinas
    de los TRAP, que el simulador ejecuta como código de LC10: lc10/os_lc10.asm);
  * palabras de memoria = bytes de la imagen / 2, con el relleno que pide la alineación incluido;
  * reparto de ambas por módulo;
  * si el texto que imprime es idéntico al de la línea base (la salida de referencia se generó con el
    simulador de la cátedra; ese simulador agrega "\\nHALT\\n" al final, que acá se descarta).
Cifras de la línea base LC-3: 357.505 instrucciones de usuario (informadas por el tutor) y 7896 palabras; con
el contador actualizado del grupo 8, que suma el SO: 357.505 usuario + 22.074 SO = 379.579 instrucciones.
"""
from __future__ import annotations

import argparse
import collections
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent))
from lc10.assembler import AsmError, assemble  # noqa: E402
from lc10 import system  # noqa: E402
from lc10.simulator import Fault, Machine  # noqa: E402

LC3_USUARIO, LC3_SO, LC3_PALABRAS = 357_505, 22_074, 7896
LC3_INSTR = LC3_USUARIO + LC3_SO                      # 379.579: lo que cuenta el simulador actualizado (usuario + SO)


def cargar_fuentes(carpeta: Path, principal: str):
    nombres = [principal] + sorted(p.name for p in carpeta.glob("*.asm") if p.name != principal)
    return [(n, (carpeta / n).read_text(encoding="utf-8")) for n in nombres]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("carpeta", nargs="?", default=str(AQUI.parent / "asm" / "bench10"))
    ap.add_argument("--main", default="main_grupo27.asm")
    ap.add_argument("--ref", default=str(AQUI / "lc3_baseline_salida.txt"))
    ap.add_argument("--max", type=int, default=5_000_000)
    ap.add_argument("--por-modulo", action="store_true", help="tabla por módulo")
    args = ap.parse_args(argv)

    try:
        res = assemble(cargar_fuentes(Path(args.carpeta), args.main))
    except AsmError as e:
        print(f"error de ensamblado: {e}")
        return 1
    palabras = len(res.image.data) // 2
    m = Machine()
    m.load(res.image)
    m.set_input("")
    mods = sorted((b, s, n) for n, b, s in res.modules)

    def modulo(pc):
        if system.in_system(pc):
            return "SO (rutinas de TRAP)"
        for b, s, n in mods:
            if b <= pc < b + s:
                return n
        return "?"

    por_mod = collections.Counter()
    try:
        while not m.halted and m.count < args.max:
            por_mod[modulo(m.pc)] += 1
            m.step()
    except Fault as e:
        print("EXCEPCIÓN:", e)
        return 2
    salida = "".join(m.out)
    ref = Path(args.ref).read_text(encoding="utf-8") if Path(args.ref).exists() else None
    if ref is not None and ref.endswith("\nHALT\n"):
        ref = ref[:-len("\nHALT\n")]
    print(f"módulos: {len(mods)}   imagen: {len(res.image.data)} bytes = {palabras} palabras (relleno {res.pad_bytes} byte)")
    pt = lambda n: f"{n:,}".replace(",", ".")      # noqa: E731  (separador de miles de la cátedra)
    print(f"instrucciones ejecutadas: {pt(m.count)} = {pt(m.user_count)} usuario + {pt(m.os_count)} SO")
    d_i = 100 * (m.count - LC3_INSTR) / LC3_INSTR
    d_u = 100 * (m.user_count - LC3_USUARIO) / LC3_USUARIO
    d_p = 100 * (palabras - LC3_PALABRAS) / LC3_PALABRAS
    print(f"LC-3: {pt(LC3_USUARIO)} usuario + {pt(LC3_SO)} SO = {pt(LC3_INSTR)} instrucciones y {LC3_PALABRAS} palabras"
          f"   ->   instrucciones {d_i:+.1f} % (solo usuario {d_u:+.1f} %), palabras {d_p:+.1f} %")
    if ref is None:
        print("(no hay salida de referencia)")
    else:
        igual = salida.rstrip("\n") == ref.rstrip("\n")
        print("salida idéntica a la de la línea base LC-3:", "sí" if igual else "NO")
        if not igual:
            a, b = salida.splitlines(), ref.splitlines()
            for i, (x, y) in enumerate(zip(a, b), 1):
                if x != y:
                    print(f"  primera diferencia en la línea {i}:\n    LC10: {x!r}\n    LC-3: {y!r}")
                    break
            else:
                print(f"  una salida es prefijo de la otra ({len(a)} vs {len(b)} líneas)")
    if args.por_modulo:
        tam = {n: s for _, s, n in mods}
        print(f"\n{'módulo':40s} {'bytes':>6s} {'palabras':>8s} {'ejecutadas':>10s} {'%':>6s}")
        for n, s in sorted(tam.items(), key=lambda x: -por_mod.get(x[0], 0)):
            c = por_mod.get(n, 0)
            print(f"{n:40s} {s:6d} {s // 2:8d} {c:10d} {100 * c / m.count:6.1f}")
        so = por_mod.get("SO (rutinas de TRAP)", 0)
        print(f"{'SO (rutinas de TRAP)':40s} {'-':>6s} {'-':>8s} {so:10d} {100 * so / m.count:6.1f}   (memoria aparte, como la ROM de la LC-3)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
