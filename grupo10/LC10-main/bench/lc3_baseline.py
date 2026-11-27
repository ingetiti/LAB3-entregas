"""Línea base del benchmark del curso en LC-3 (carpeta lc3-project de la cátedra).

Usa el ensamblador y el simulador de la cátedra TAL CUAL (no los reimplementa):

    python bench/lc3_baseline.py RUTA\\lc3-project

Hace cuatro cosas:
  1. ensambla `main_grupo27.asm` con sus módulos de `lib/` y verifica que la imagen sea idéntica a
     `programa.obj` (si ese archivo está);
  2. la ejecuta en el simulador de la cátedra y cuenta las instrucciones;
  3. reparte memoria e instrucciones ejecutadas por módulo;
  4. compara el texto impreso con `bench/lc3_baseline_salida.txt` (la salida de referencia que el puerto
     a LC10 tiene que reproducir). Con `--guardar` regenera ese archivo.

Cifras que informó el tutor: 357.505 instrucciones y 7896 palabras (modo verboso).
El grupo 8 actualizó el contador del simulador para sumar las instrucciones del SO (las rutinas de los TRAP):
357.505 usuario + 22.074 SO = 379.579. Ese contador no es el simulador que está en `lc3-project`, que sigue
contando cada TRAP como una instrucción; acá se muestran los dos números y los TRAP de la corrida (cuántos y
qué hacen), que son los que el SO tiene que resolver.
"""
import argparse
import collections
import importlib.util
import io
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
REFERENCIA = AQUI / "lc3_baseline_salida.txt"
INSTRUCCIONES_TUTOR = 357_505
SO_GRUPO_8 = 22_074                                   # instrucciones del SO según el contador actualizado del grupo 8
TOTAL_GRUPO_8 = INSTRUCCIONES_TUTOR + SO_GRUPO_8      # 379.579
PALABRAS_TUTOR = 7896
OPCODES = "BR ADD LD ST JSR AND LDR STR RTI NOT LDI STI JMP res LEA TRAP".split()


def cargar(nombre, ruta):
    spec = importlib.util.spec_from_file_location(nombre, ruta)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[nombre] = mod
    spec.loader.exec_module(mod)
    return mod


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("carpeta", help="carpeta lc3-project (con simulador.py, assembler_LC3.py, lib/)")
    ap.add_argument("--programa", default="main_grupo27.asm", help="programa principal dentro de la carpeta")
    ap.add_argument("--guardar", action="store_true", help="guarda la salida como referencia")
    args = ap.parse_args(argv)

    base = Path(args.carpeta).resolve()
    asm = cargar("asm_lc3_catedra", base / "assembler_LC3.py")
    sim = cargar("sim_lc3_catedra", base / "simulador.py")

    # 1. ensamblar con el enlazador de la cátedra
    enlazador = asm.ProjectLinker(base / "lib")
    obj = enlazador.assemble_file(base / args.programa, "obj")
    palabras = len(obj) // 2 - 1
    print(f"imagen ensamblada: {palabras} palabras (informado por el tutor: {PALABRAS_TUTOR})")
    previo = base / "programa.obj"
    if previo.exists():
        print("coincide con programa.obj:", "sí" if previo.read_bytes() == obj else "NO")

    # 2. ejecutar y perfilar (misma lógica que LC3.run, instrucción por instrucción)
    modulos = sorted((u.base, u.size, u.path.name) for u in enlazador.unit_order)

    def modulo_de(pc):
        for b, s, n in modulos:
            if b <= pc < b + s:
                return n
        return "?"

    salida = io.StringIO()
    m = sim.LC3(input_stream=io.StringIO(""), output_stream=salida)
    m.load_object(obj)
    por_modulo, por_opcode = collections.Counter(), collections.Counter()
    traps, caracteres_puts = collections.Counter(), 0
    while not m.halted and m.steps < 5_000_000:
        por_modulo[modulo_de(m.pc)] += 1
        por_opcode[m.memory[m.pc] >> 12] += 1
        if m.memory[m.pc] >> 12 == 0xF:                       # TRAP: qué servicio pide
            vect = m.memory[m.pc] & 0xFF
            traps[vect] += 1
            if vect == 0x22:                                  # PUTS: cuántos caracteres escribe (un carácter por palabra)
                a = m.registers[0]
                while m.memory[a]:
                    caracteres_puts += 1
                    a += 1
        m.step()
    print(f"instrucciones ejecutadas: {m.steps:,} (informado por el tutor: {INSTRUCCIONES_TUTOR:,})".replace(",", "."))
    nombres = {0x20: "GETC", 0x21: "OUT", 0x22: "PUTS", 0x23: "IN", 0x25: "HALT"}
    print("TRAP de la corrida: " + ", ".join(f"{nombres.get(v, hex(v))} {n}" for v, n in sorted(traps.items()))
          + f"; PUTS escribe {caracteres_puts} caracteres")
    print(f"con el SO (contador actualizado del grupo 8): {INSTRUCCIONES_TUTOR:,} usuario + {SO_GRUPO_8:,} SO"
          f" = {TOTAL_GRUPO_8:,} instrucciones".replace(",", "."))

    # 3. reparto por módulo
    tam = {n: s for _, s, n in modulos}
    print(f"\n{'módulo':40s} {'palabras':>8s} {'ejecutadas':>10s} {'%':>6s}")
    for n, c in sorted(por_modulo.items(), key=lambda x: -x[1]):
        print(f"{n:40s} {tam.get(n, 0):8d} {c:10d} {100 * c / m.steps:6.1f}")
    for n, s in sorted(tam.items(), key=lambda x: -x[1]):
        if n not in por_modulo:
            print(f"{n:40s} {s:8d} {'-':>10s}")
    print("\npor opcode:", {OPCODES[k]: v for k, v in sorted(por_opcode.items())})

    # 4. salida de referencia
    texto = salida.getvalue()
    if args.guardar:
        REFERENCIA.write_text(texto, encoding="utf-8", newline="\n")
        print(f"\nsalida guardada en {REFERENCIA}")
    elif REFERENCIA.exists():
        igual = REFERENCIA.read_text(encoding="utf-8") == texto
        print(f"\nsalida idéntica a {REFERENCIA.name}:", "sí" if igual else "NO")
    ok = m.steps == INSTRUCCIONES_TUTOR and palabras == PALABRAS_TUTOR
    print("\nLÍNEA BASE", "REPRODUCIDA" if ok else "NO COINCIDE con lo informado")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
