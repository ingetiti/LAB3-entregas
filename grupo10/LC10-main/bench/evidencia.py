"""Corre todas las comparaciones contra la cátedra y guarda las salidas como evidencia.

    python bench/evidencia.py RUTA\\lc3-project [--solo NOMBRE ...] [--lista]

Escribe en `bench/resultados/`:
  * un archivo `NN_nombre.txt` por prueba, con el comando, la salida completa, el código de salida y la duración;
  * `LEEME.md`: un índice con la fecha, la versión de Python, el sistema, una huella (SHA-256) de los módulos
    de `asm/opt10` y de `lc10/` (para saber con qué versión del código se obtuvo cada resultado) y una tabla con
    el resultado de cada prueba.

Las pruebas largas tardan varios minutos (en total, del orden de media hora o más, según la máquina).
Con `--solo` se corren solo algunas (por nombre, ver `--lista`); el índice se rehace con lo que haya.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import platform
import re
import subprocess
import sys
import time
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent
SALIDA = AQUI / "resultados"

# (nombre, argumentos después de "python", usa la carpeta de la cátedra, qué compara)
PRUEBAS = [
    ("pruebas", ["-m", "unittest", "discover", "-s", "tests", "-t", "."], False,
     "pruebas automáticas (ISA, ensamblador, simulador, ventana si hay pantalla, benchmark)"),
    ("linea_base_lc3", ["bench/lc3_baseline.py", "{lc3}"], True,
     "el benchmark en LC-3 con el ensamblador y el simulador de la cátedra"),
    ("benchmark_lc10", ["benchmark.py", "{lc3}/main_grupo27.asm", "--lc3", "{lc3}"], True,
     "el main de la cátedra en LC10 y en LC-3: misma salida, instrucciones y palabras"),
    ("benchmark_por_modulo", ["bench/lc10_bench.py", "asm/opt10", "--por-modulo"], False,
     "reparto de instrucciones y palabras por módulo (puerto optimizado)"),
    ("benchmark_puerto_directo", ["bench/lc10_bench.py", "asm/bench10"], False,
     "puerto directo (traducción sin optimizar): misma salida"),
    ("modulos", ["bench/equivalencia_modulos.py", "{lc3}", "asm/opt10", "--casos", "150"], True,
     "las 39 subrutinas contra los módulos reales de la cátedra y 17 sesiones del menú"),
    ("entradas", ["bench/equivalencia_entradas.py", "{lc3}", "--casos", "40", "--semilla", "2"], True,
     "el main de la cátedra con operandos al azar, operación por operación"),
    ("entradas_dominio", ["bench/equivalencia_entradas.py", "{lc3}", "--solo", "3", "5", "--casos", "150",
                          "--rango", "dominio"], True,
     "seno y coseno por tabla con el ángulo dentro de 0..2π"),
    ("seno_modelo", ["bench/equivalencia_seno.py", "{lc3}"], True,
     "seno de Taylor de la cátedra contra el modelo de sus cuentas"),
    ("seno_lc10", ["bench/equivalencia_seno_lc10.py"], False,
     "seno de Taylor en LC10, las 65.536 entradas, contra ese modelo"),
    ("todec_modelo", ["bench/equivalencia_todec.py", "{lc3}"], True,
     "TODEC de la cátedra contra el modelo de sus cuentas"),
    ("todec_lc10", ["bench/equivalencia_todec_lc10.py"], False,
     "TODEC en LC10: 328.160 llamadas contra ese modelo"),
    ("sumover_circlsh", ["bench/equivalencia_chicos_lc10.py"], False,
     "SUMOVER y CIRCLSH en LC10, unas 400.000 llamadas"),
    ("div_newton", ["bench/equivalencia_div_lc10.py", "{lc3}"], True,
     "DIV_NEWTON en LC10 contra el módulo real"),
    ("exp", ["bench/equivalencia_exp_lc10.py"], False,
     "EXP_Q3_12 en LC10, las 65.536 entradas, contra el puerto directo"),
    ("division_larga", ["bench/bench_division.py"], False,
     "división larga del grupo: LC-3 contra LC10"),
]


def huella(*carpetas: Path) -> str:
    h = hashlib.sha256()
    for carpeta in carpetas:
        for p in sorted(carpeta.rglob("*")):
            if p.is_file() and p.suffix in (".asm", ".py"):
                h.update(p.relative_to(RAIZ).as_posix().encode())
                h.update(p.read_bytes())
    return h.hexdigest()[:16]


CLAVE = re.compile(r"distint|diferencia|idéntica|coincide|REPRODUCIDA|^OK|^FAILED|reduccion de instrucciones|^Ran |"
                   r"^LC10 · |^LC-3 · ")
IGNORAR = ("op ", "memoria:", "detalle:")


def ultima_linea(texto: str) -> str:
    """Las líneas que dicen el resultado (hasta 4); si no hay ninguna, la última línea con texto."""
    claves = [ln.strip() for ln in texto.splitlines()
              if CLAVE.search(ln.strip()) and not ln.strip().startswith(IGNORAR)]
    if claves:
        return " · ".join(claves[-4:])
    for ln in reversed(texto.strip().splitlines()):
        if ln.strip() and not set(ln.strip()) <= {"-", "="}:
            return ln.strip()
    return ""


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("lc3", nargs="?", help="carpeta lc3-project de la cátedra")
    ap.add_argument("--solo", nargs="*", default=[], help="correr solo estas pruebas (por nombre)")
    ap.add_argument("--lista", action="store_true", help="muestra las pruebas y sale")
    args = ap.parse_args(argv)
    if args.lista:
        for i, (nombre, _, usa, que) in enumerate(PRUEBAS, 1):
            print(f"{i:2d}  {nombre:26s} {'(necesita lc3-project) ' if usa else ''}{que}")
        return 0
    lc3 = Path(args.lc3).resolve() if args.lc3 else None
    SALIDA.mkdir(exist_ok=True)
    fallas = 0
    for i, (nombre, argumentos, usa, que) in enumerate(PRUEBAS, 1):
        if args.solo and nombre not in args.solo:
            continue
        archivo = SALIDA / f"{i:02d}_{nombre}.txt"
        if usa and lc3 is None:
            print(f"{nombre:26s} se saltea: falta la carpeta lc3-project")
            continue
        cmd = [sys.executable] + [a.replace("{lc3}", str(lc3)) for a in argumentos]
        print(f"{nombre:26s} ...", end="", flush=True)
        t = time.time()
        p = subprocess.run(cmd, cwd=RAIZ, capture_output=True, text=True, encoding="utf-8", errors="replace")
        dt = time.time() - t
        mostrado = " ".join(["python"] + [a.replace("{lc3}", "RUTA") for a in argumentos])
        archivo.write_text(f"$ {mostrado}\n# {que}\n# código de salida: {p.returncode}   duración: {dt:.0f} s\n\n"
                           + p.stdout + (("\n--- stderr ---\n" + p.stderr) if p.stderr.strip() else ""),
                           encoding="utf-8")
        fallas += p.returncode != 0
        print(f" código {p.returncode} ({dt:.0f} s)")
    escribir_indice(lc3)
    print(f"\nresultados en {SALIDA}")
    return 1 if fallas else 0


def escribir_indice(lc3: Path | None) -> None:
    filas = []
    for i, (nombre, argumentos, usa, que) in enumerate(PRUEBAS, 1):
        archivo = SALIDA / f"{i:02d}_{nombre}.txt"
        if not archivo.exists():
            filas.append(f"| {i} | {que} | (no se corrió) | |")
            continue
        texto = archivo.read_text(encoding="utf-8")
        cabecera = texto.splitlines()[2]                       # "# código de salida: N   duración: S s"
        codigo = cabecera.split(":")[1].split()[0]
        filas.append(f"| {i} | {que} | `{ultima_linea(texto.split(chr(10) * 2, 1)[1]).replace('|', '/')}` "
                     f"| [{archivo.name}]({archivo.name}) (código {codigo}) |")
    LEEME = SALIDA / "LEEME.md"
    LEEME.write_text(
        "# Evidencia: LC10 contra la cátedra\n\n"
        f"Generado con `python bench/evidencia.py RUTA` el {datetime.datetime.now():%d/%m/%Y %H:%M}, "
        f"Python {platform.python_version()} en {platform.system()} {platform.release()}.\n\n"
        f"Huella del código usado: `asm/opt10` = `{huella(RAIZ / 'asm' / 'opt10')}`, "
        f"`lc10/` = `{huella(RAIZ / 'lc10')}`. Si cambia un módulo o el simulador, la huella cambia y "
        "esta evidencia hay que regenerarla.\n\n"
        "Código de salida 0 = sin diferencias (en `entradas`, 1 indica las diferencias conocidas de seno y coseno "
        "por tabla fuera de 0..2π; ver `docs/ISA.md`, sección 12).\n\n"
        "| # | Qué compara | Resultado (líneas de la salida) | Archivo |\n| --- | --- | --- | --- |\n"
        + "\n".join(filas) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
