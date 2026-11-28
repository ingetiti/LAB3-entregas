"""Corre el benchmark del curso en LC10 con el programa principal que se le pase.

    python benchmark.py                                   # el benchmark tal cual (asm/opt10/main_grupo27.asm)
    python benchmark.py RUTA\\main_grupo27.asm            # el programa principal que entregue la cátedra
    python benchmark.py RUTA\\main_grupo27.asm --lc3 RUTA  # y además lo corre en LC-3 para comparar
    python benchmark.py --interactivo --entrada "7213.25\\n-7.5\\n d"   # el menú con teclas, sin el bloque

El programa principal se ensambla TAL CUAL (el de la cátedra, en LC-3, ensambla sin cambios en LC10: solo
usa BR, AND, LEA, LD, JSRR, HALT, .FILL y .EXTERNAL) y se enlaza con los módulos de LC10 de `asm/opt10`.
Las entradas del benchmark son el bloque `.FILL` del programa principal (modo automático) o, con
`--interactivo`, las teclas de `--entrada` / `--entrada-archivo` (como el cuadro de teclado del simulador de
la cátedra).

Al final muestra, como la barra de estado del simulador de la cátedra (con el contador actualizado que cuenta
también las instrucciones del SO, las rutinas de los TRAP):

    LC10 · 15.822 usuario + 10.901 SO = 26.723 instrucciones · 4963 palabras · x3000–x56C5

Con `-o programa.hex` (o .bin, .dec, .bits) guarda además la imagen, que el simulador ejecuta solo:
`python -m lc10.simulator programa.hex` (el enunciado pide que el simulador reciba un archivo).
"""
from __future__ import annotations

import argparse
import importlib.util
import io
import sys
import tempfile
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
from lc10.assembler import AsmError, assemble  # noqa: E402
from lc10.simulator import Machine, summary_line  # noqa: E402
from lc10.syntax import parse_input_escapes  # noqa: E402

LC3_USUARIO, LC3_SO = 357_505, 22_074                  # LC-3: instrucciones de usuario y del SO (grupo 8, contador actualizado)
PRINCIPAL = AQUI / "asm" / "opt10" / "main_grupo27.asm"
BIBLIOTECA = AQUI / "asm" / "opt10"
MARCA_AUTOMATICO = "programa_del_menu_completo"


def leer(ruta: Path) -> str:
    return ruta.read_text(encoding="utf-8-sig")


def sin_modo_automatico(texto: str) -> str:
    """Comenta el `LEA R0, programa_del_menu_completo` para que el menú lea el teclado (R0 queda en 0)."""
    salida = []
    for ln in texto.splitlines():
        codigo = ln.split(";", 1)[0]
        if codigo.strip().upper().startswith("LEA") and MARCA_AUTOMATICO.upper() in codigo.upper():
            ln = "; " + ln
        salida.append(ln)
    return "\n".join(salida) + "\n"


def fuentes(principal: Path, texto: str, biblioteca: Path):
    modulos = sorted(p for p in biblioteca.glob("*.asm") if p.name.lower() != principal.name.lower()
                     and p.name.lower() != PRINCIPAL.name.lower())
    return [(principal.name, texto)] + [(p.name, leer(p)) for p in modulos]


def correr_lc3(carpeta: Path, principal: Path, texto: str, entrada: str | None, maximo: int):
    """Mismo programa en el ensamblador y el simulador de la cátedra (sin modificarlos)."""
    def cargar(nombre, ruta):
        spec = importlib.util.spec_from_file_location(nombre, ruta)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[nombre] = mod
        spec.loader.exec_module(mod)
        return mod

    asm = cargar("asm_lc3_catedra", carpeta / "assembler_LC3.py")
    sim = cargar("sim_lc3_catedra", carpeta / "simulador.py")
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / principal.name
        src.write_text(texto, encoding="utf-8")
        obj = asm.ProjectLinker(carpeta / "lib").assemble_file(src, "obj")
    salida = io.StringIO()
    m = sim.LC3(input_stream=io.StringIO(entrada or ""), output_stream=salida)
    origen = m.load_object(obj)
    error, fin = None, "halt"
    try:
        m.run(maximo)
    except sim.SimulatorError as e:
        error = str(e)
        fin = "entrada" if "entrada" in error else "límite" if "límite" in error else "error"
    palabras = len(obj) // 2 - 1
    texto_salida = salida.getvalue()
    if texto_salida.endswith("\nHALT\n"):                 # el simulador de la cátedra agrega HALT al terminar
        texto_salida = texto_salida[:-len("\nHALT\n")]
    resumen = f"{m.steps:,}".replace(",", ".") + f" instrucciones · {palabras} palabras · x{origen:04X}–x{origen + palabras - 1:04X}"
    return texto_salida, error, fin, m.steps, palabras, resumen


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("principal", nargs="?", default=str(PRINCIPAL),
                    help="programa principal (por defecto, el del benchmark: asm/opt10/main_grupo27.asm)")
    ap.add_argument("--biblioteca", default=str(BIBLIOTECA), help="carpeta con los módulos LC10 (por defecto asm/opt10)")
    ap.add_argument("--interactivo", action="store_true",
                    help="no usar el bloque automático: el menú lee las teclas de --entrada / --entrada-archivo")
    ap.add_argument("--entrada", help="teclas para GETC/IN (admite \\n, \\t y \\\\)")
    ap.add_argument("--entrada-archivo", metavar="ARCHIVO", help="archivo de texto con las teclas (UTF-8), tal cual")
    ap.add_argument("-o", "--imagen", metavar="ARCHIVO", help="guarda la imagen ensamblada (.hex, .bin, .dec o .bits)")
    ap.add_argument("--lc3", metavar="RUTA", help="carpeta lc3-project de la cátedra: corre lo mismo en LC-3 y compara")
    ap.add_argument("--max", type=int, default=50_000_000, help="máximo de instrucciones")
    args = ap.parse_args(argv)

    principal = Path(args.principal)
    try:
        texto = leer(principal)
        entrada = None
        if args.entrada_archivo:
            entrada = Path(args.entrada_archivo).read_text(encoding="utf-8")
        elif args.entrada is not None:
            entrada = parse_input_escapes(args.entrada)
    except (OSError, UnicodeDecodeError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    if args.interactivo:
        texto = sin_modo_automatico(texto)

    try:
        res = assemble(fuentes(principal, texto, Path(args.biblioteca)))
    except AsmError as e:
        print(f"error de ensamblado: {e}", file=sys.stderr)
        return 1
    if args.imagen:
        destino = Path(args.imagen)
        res.image.save(destino, destino.suffix.lstrip(".").lower() or "hex")

    m = Machine()
    m.eof_fault = True                                  # sin más teclas se detiene, como el simulador de la cátedra
    m.load(res.image)
    m.set_input(entrada or "")
    r = m.run(args.max)
    print(r.output, end="" if r.output.endswith("\n") or not r.output else "\n")
    print("-" * 60)
    if r.reason != "halt":
        print(("EXCEPCIÓN: " if r.reason == "fault" else "DETENIDO: ") + r.message)
    print("LC10 · " + summary_line(r.instructions, len(res.image.data), res.image.origin, r.os_instructions))
    print("memoria: " + r.memory_line())
    if args.imagen:
        print(f"imagen guardada en {args.imagen}: python -m lc10.simulator {args.imagen}")

    if args.lc3:
        try:
            salida3, error3, fin3, instr3, pal3, resumen3 = correr_lc3(Path(args.lc3), principal, texto, entrada, args.max)
        except Exception as e:                          # el ensamblador de la cátedra rechazó el programa, etc.
            print(f"LC-3: no se pudo correr con la carpeta de la cátedra: {e}")
            return 1
        print("LC-3 · " + resumen3 + (f"   ({error3})" if error3 else ""))
        fin10 = "halt" if r.reason == "halt" else "límite" if r.reason == "limit" else \
            "entrada" if "entrada" in r.message else "error"
        print("salida idéntica a la de LC-3:", "sí" if salida3 == r.output else "NO")
        print("terminan igual (HALT, sin más entrada, límite):", "sí" if fin3 == fin10 else f"NO (LC-3 {fin3}, LC10 {fin10})")
        if salida3 != r.output:
            a, b = r.output.splitlines(), salida3.splitlines()
            for i, (x, y) in enumerate(zip(a, b), 1):
                if x != y:
                    print(f"  primera diferencia en la línea {i}:\n    LC10: {x!r}\n    LC-3: {y!r}")
                    break
            else:
                print(f"  una salida es prefijo de la otra ({len(a)} y {len(b)} líneas)")
        # el simulador de la cátedra cuenta cada TRAP como 1 (instrucciones de usuario); el grupo 8 lo amplió para sumar
        # las del SO. Acá se compara usuario con usuario y, para la corrida estándar, el total con el SO informado.
        print(f"diferencia: instrucciones de usuario {100 * (r.user_instructions - instr3) / instr3:+.1f} %, "
              f"palabras {100 * (len(res.image.data) // 2 - pal3) / pal3:+.1f} %")
        if instr3 == LC3_USUARIO:
            total3 = LC3_USUARIO + LC3_SO
            pt = lambda n: f"{n:,}".replace(",", ".")      # noqa: E731  (separador de miles de la cátedra)
            print(f"con el SO (LC-3: {pt(LC3_USUARIO)} usuario + {pt(LC3_SO)} SO = {pt(total3)}, informado por la cátedra; "
                  f"LC10: {pt(r.instructions)}): instrucciones {100 * (r.instructions - total3) / total3:+.1f} %")
        return 0 if (salida3 == r.output and fin3 == fin10) else 2
    return 0 if r.reason == "halt" else 2


if __name__ == "__main__":
    raise SystemExit(main())
