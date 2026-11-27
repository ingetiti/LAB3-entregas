"""El benchmark con OTRAS entradas: LC-3 (cátedra) contra LC10, operación por operación.

    python bench/equivalencia_entradas.py RUTA\\lc3-project [--casos 30] [--semilla 1] [--solo 3 5]
                                          [--rango todo|dominio] [--biblioteca asm/opt10]

Toma el `main_grupo27.asm` de la cátedra y reemplaza su bloque automático por una sola operación con
operandos al azar (los dos primeros `.FILL` de cada grupo). Corre ese programa con el ensamblador y el
simulador de la cátedra (sin modificarlos) y con el de LC10, y compara el texto impreso y cómo termina.

--rango todo     operandos de 16 bits cualesquiera (incluye valores fuera del dominio de cada rutina)
--rango dominio  los operandos de cada operación se toman dentro del rango que la rutina documenta
                 (DOMINIO, más abajo); las demás usan 16 bits cualesquiera

Una diferencia fuera del dominio documentado de una rutina puede venir de que la rutina original lee
memoria fuera de sus tablas: lo que encuentra ahí depende de cómo quedó armada la memoria, que en LC10 es
distinta (otra codificación, direcciones de byte). Esas se informan aparte ("fuera de dominio").
"""
from __future__ import annotations

import argparse
import importlib.util
import io
import random
import re
import sys
import tempfile
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent))
from lc10.assembler import assemble  # noqa: E402
from lc10.simulator import Machine  # noqa: E402

# operación -> (nombre, generador de (a, b) dentro del dominio que documenta la rutina original)
TAU_Q312 = 25736          # 2·pi en Q3.12
DOMINIO = {
    3: ("SENO TABLA", lambda g: (g.randint(0, TAU_Q312), 0)),
    5: ("COSENO TABLA", lambda g: (g.randint(0, TAU_Q312), 0)),
}


def cargar(nombre, ruta):
    spec = importlib.util.spec_from_file_location(nombre, ruta)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[nombre] = mod
    spec.loader.exec_module(mod)
    return mod


def plantilla(principal: str):
    """(antes del bloque, grupos [(op, [5 líneas])], después del bloque)."""
    lineas = principal.splitlines()
    ini = next(i for i, ln in enumerate(lineas) if ln.strip().split(";")[0].strip() == "programa_del_menu_completo")
    fills = [i for i in range(ini + 1, len(lineas)) if re.match(r"\s*\.FILL\b", lineas[i], re.I)]
    grupos, k = [], 1                                          # fills[0] es el modo verboso
    while k < len(fills):
        op = lineas[fills[k]].split()[1]
        if op in ("#0", "x0000", "0"):
            break
        grupos.append((int(op.lstrip("#")), [lineas[j] for j in fills[k:k + 5]]))
        k += 5
    fin = fills[k]
    return lineas[:fills[0] + 1], grupos, lineas[fin:]


def programa(antes, grupo, a: int, b: int, despues) -> str:
    g = list(grupo)
    for idx, val in ((1, a), (2, b)):
        g[idx] = re.sub(r"\.FILL\s+\S+", f".FILL x{val & 0xFFFF:04X}", g[idx], count=1)
    return "\n".join(antes + g + despues) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("lc3", help="carpeta lc3-project de la cátedra")
    ap.add_argument("--biblioteca", default=str(AQUI.parent / "asm" / "opt10"))
    ap.add_argument("--casos", type=int, default=30, help="casos por operación")
    ap.add_argument("--semilla", type=int, default=1)
    ap.add_argument("--solo", nargs="*", type=int, default=[], help="solo estas operaciones (número del menú)")
    ap.add_argument("--rango", choices=("todo", "dominio"), default="todo")
    ap.add_argument("--max", type=int, default=3_000_000)
    args = ap.parse_args(argv)

    base = Path(args.lc3).resolve()
    asm3 = cargar("asm_lc3_catedra", base / "assembler_LC3.py")
    sim3 = cargar("sim_lc3_catedra", base / "simulador.py")
    texto = (base / "main_grupo27.asm").read_text(encoding="utf-8-sig")
    antes, grupos, despues = plantilla(texto)
    bib = Path(args.biblioteca)
    modulos = [(p.name, p.read_text(encoding="utf-8")) for p in sorted(bib.glob("*.asm")) if p.name != "main_grupo27.asm"]
    g = random.Random(args.semilla)
    tmp = Path(tempfile.mkdtemp())
    total_dif = 0
    print(f"{'op':>3}  {'operación':40s} {'casos':>5} {'iguales':>7} {'distintos':>9}")
    for op, grupo in grupos:
        if args.solo and op not in args.solo:
            continue
        nombre = grupo[0].split(";", 1)[1].strip()[:40] if ";" in grupo[0] else f"op {op}"
        iguales, distintos = 0, []
        for _ in range(args.casos):
            if args.rango == "dominio" and op in DOMINIO:
                a, b = DOMINIO[op][1](g)
            else:
                a = g.choice([g.getrandbits(16), g.randint(0, 0x7FF), g.randint(0xF800, 0xFFFF), 0, 1, 0x7FFF, 0x8000])
                b = g.choice([g.getrandbits(16), g.randint(0, 0x7FF), g.randint(0xF800, 0xFFFF), 0, 1, 0x7FFF, 0x8000])
            fuente = programa(antes, grupo, a, b, despues)
            src = tmp / "main_grupo27.asm"
            src.write_text(fuente, encoding="utf-8")
            obj = asm3.ProjectLinker(base / "lib").assemble_file(src, "obj")
            out3 = io.StringIO()
            m3 = sim3.LC3(input_stream=io.StringIO(""), output_stream=out3)
            m3.load_object(obj)
            try:
                m3.run(args.max)
                fin3 = "halt"
            except sim3.SimulatorError as e:
                fin3 = "límite" if "límite" in str(e) else "error"
            t3 = out3.getvalue()
            t3 = t3[:-len("\nHALT\n")] if t3.endswith("\nHALT\n") else t3
            res = assemble([("main_grupo27.asm", fuente)] + modulos)
            m = Machine()
            m.load(res.image)
            r = m.run(args.max)
            fin10 = {"halt": "halt", "limit": "límite"}.get(r.reason, "error")
            if t3 == r.output and fin3 == fin10:
                iguales += 1
            else:
                distintos.append((a, b, fin3, fin10, t3, r.output))
        total_dif += len(distintos)
        print(f"{op:3d}  {nombre:40s} {args.casos:5d} {iguales:7d} {len(distintos):9d}")
        for a, b, f3, f10, t3, t10 in distintos[:3]:
            la, lb = t10.splitlines(), t3.splitlines()
            dif = next(((x, y) for x, y in zip(la, lb) if x != y), (la[-1:] or [""])[0:1] + (lb[-1:] or [""])[0:1])
            print(f"       a=x{a:04X} b=x{b:04X}  fin LC-3 {f3} / LC10 {f10}  LC10 {dif[0]!r}  LC-3 {dif[-1]!r}")
    print("\nRESULTADO:", "todo coincide" if not total_dif else f"{total_dif} casos distintos")
    return 0 if not total_dif else 1


if __name__ == "__main__":
    raise SystemExit(main())
