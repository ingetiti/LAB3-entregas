# -*- coding: utf-8 -*-
"""
ernie_runner.py - Lanzador/driver CLI del toolchain Ernie-Core (Laboratorio 3C).

Modos implementados:
  --selftest   Ejecuta de punta a punta el benchmark del Grupo 27 (main_grupo27.asm)
               en modo AUTOMATICO (sin entrada manual por consola), ensamblando el
               modulo principal junto con sus dependencias reales y simulando el
               flujo preprogramado 'programa_del_menu_completo'.

  --verify     Ejecuta la suite de oraculos completa del benchmark (723 vectores)
               seleccionando Standard u Optimized, en un subproceso, y lee el JSON
               de resultados para reportar el resumen global PASS/FAIL/fatal.

Uso:
  python Implementacion_ISA\\ernie_runner.py --selftest [--opt | --standard]
  python Implementacion_ISA\\ernie_runner.py --verify [standard|optimized] [--opt | --standard]

Flujo (coherente con suite_oraculo_benchmark_Standard._run_main_grupo27):
  1. Ensambla main_grupo27.asm + dependencias (lib/*.asm) con Ensamblador (strict=False,
     por dependencias legacy), generando un .bin en Pruebas_ISA/Selftest/.
  2. Simula con Simulador usando input_buffer=[] (modo automatico, sin teclado),
     capturando la salida de consola (PUTS/OUT).
  3. Parsea dinamicamente el bloque de vectores .FILL tras la etiqueta
     'programa_del_menu_completo' del .asm para listar los casos precargados.
  4. Imprime por pantalla: vectores de entrada, resultados por subrutina (consola),
     estado final R0..R5 (hex y decimal con signo) y telemetria (6 metricas).
  5. Devuelve codigo de salida 0 si la corrida es correcta; distinto de 0 si falla.

No modifica ISA_SPEC.md, SIM_SPEC.md ni los .asm del benchmark. No ejecuta Git.
"""

import argparse
import glob
import io
import json
import os
import re
import subprocess
import sys

# --- Rutas base relativas a la ubicacion de este script (portable) ---
IMPL_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if IMPL_DIR not in sys.path:
    sys.path.insert(0, IMPL_DIR)

from ernie_assembler import Ensamblador  # noqa: E402
from ernie_simulator import Simulador, imprimir_reporte_perfilado  # noqa: E402

MASK_16 = 0xFFFF
STACK_BASE = 0xFFFE
MAX_INSTRUCCIONES = 800000

# Titulos .STRINGZ (banners) exactos que produce el flujo automatico del Grupo 27.
# Se usan para verificar que las 23 operaciones se ejecutaron y mostraron su resultado.
BANNERS_GRUPO27 = [
    "==REDUCCION DE ARGUMENTO (CORDIC)==",
    "==SENO TRIGONOMETRICO (TAYLOR)==",
    "==SENO TRIGONOMETRICO (TABLE)==",
    "==SENO TRIGONOMETRICO (CHEVYSHEV-PADE)==",
    "==COSENO TRIGONOMETRICO (TABLE)==",
    "==EXPRESION CON BASE (HEX)==",
    "==EXPRESION CON BASE (BIN)==",
    "==RAIZ CUADRADA (NON RESTORING)==",
    "==RAIZ CUADRADA (NEWTON-RAPHSON)==",
    "==EXPONENCIACION==",
    "==POTENCIACION (MULTIPLICACIONES SUCESIVAS)==",
    "==POTENCIACION (EXPONENCIACION BINARIA)==",
    "==MULTIPLICACION (CORDIC)==",
    "==MULTIPLICACION (BASIC)==",
    "==MULTIPLICACION (BOOTH)==",
    "==DIVISION (LONG DIVISION)==",
    "==DIVISION (NEWTON-RAPHSON)==",
    "==DIVISION (CORDIC)==",
    "==LOGARITMO== (BORCHARDT)",
    "==LOGARITMO== (CORDIC)",
    "==MAXIMO COMUN DIVISOR==",
    "==MINIMO COMUN MULTIPLO==",
    "==Q3.12 -> Q7.8==",
]

ETIQUETA_VECTORES = "programa_del_menu_completo"


def _parse_fill_token(token):
    """Interpreta un operando .FILL (#n, xNNN, -#n, -xNNN, decimal) -> int & 0xFFFF."""
    s = token.strip()
    if s.startswith("-#"):
        val = -int(s[2:], 10)
    elif s.startswith("-x") or s.startswith("-X"):
        val = -int(s[2:], 16)
    elif s.startswith("#"):
        val = int(s[1:], 10)
    elif s.startswith("x") or s.startswith("X"):
        val = int(s[1:], 16)
    else:
        val = int(s, 0)
    return val & MASK_16


def parsear_vectores(ruta_asm):
    """
    Parsea dinamicamente el bloque de datos .FILL que sigue a la etiqueta
    'programa_del_menu_completo'. Devuelve (verbose, operaciones) donde cada
    operacion es un dict con: indice, arg1, arg2, resultado, extra (todos int 16-bit).

    Estructura del bloque (Grupo 27):
        .FILL #verbose
        .FILL #indice   .FILL #arg1   .FILL #arg2   .FILL #resultado   .FILL #extra
        ... (se repite hasta un .FILL #0 que marca SALIR)
    """
    with open(ruta_asm, "r", encoding="utf-8") as archivo:
        lineas = archivo.readlines()

    valores = []
    dentro = False
    for linea_raw in lineas:
        linea = linea_raw.split(";")[0].strip()
        if not linea:
            continue
        # Deteccion de la etiqueta de inicio (con o sin dos puntos).
        sin_colon = linea.rstrip(":").strip()
        if not dentro:
            if sin_colon == ETIQUETA_VECTORES:
                dentro = True
            continue
        # Dentro del bloque: solo nos interesan .FILL; .END / .ORIG / etiquetas cortan.
        if linea.upper().startswith(".END"):
            break
        if linea.startswith("."):
            partes = linea.split()
            if partes[0].upper() == ".FILL" and len(partes) >= 2:
                valores.append(_parse_fill_token(partes[1]))
            # Otras directivas dentro del bloque se ignoran.
            continue
        # Cualquier etiqueta/instruccion nueva termina el bloque de datos.
        break

    if not valores:
        return 1, []

    verbose = valores[0]
    operaciones = []
    idx = 1
    while idx + 4 < len(valores) + 1 and idx < len(valores):
        indice = valores[idx]
        if indice == 0:
            break  # SALIR
        arg1 = valores[idx + 1] if idx + 1 < len(valores) else 0
        arg2 = valores[idx + 2] if idx + 2 < len(valores) else 0
        resultado = valores[idx + 3] if idx + 3 < len(valores) else 0
        extra = valores[idx + 4] if idx + 4 < len(valores) else 0
        operaciones.append({
            "indice": indice,
            "arg1": arg1,
            "arg2": arg2,
            "resultado": resultado,
            "extra": extra,
        })
        idx += 5
    return verbose, operaciones


def _fmt_hex(v):
    return "0x%04X" % (v & MASK_16)


def _fmt_dec(v):
    v &= MASK_16
    return str(v - 0x10000 if (v & 0x8000) else v)


def _resolver_variantes(args):
    """Determina la variante (standard/optimized) a partir de --opt/--standard."""
    if args.opt and args.standard:
        return None
    if args.opt:
        return "Optimized"
    return "Standard"


def _imprimir_vectores(verbose, operaciones):
    print("-" * 70)
    print("VECTORES PRECARGADOS (bloque '%s')" % ETIQUETA_VECTORES)
    print("-" * 70)
    print("Modo verboso: %d  (1 = muestra cada operacion y su resultado)" % verbose)
    print("Operaciones detectadas: %d" % len(operaciones))
    print("{:<4} {:<8} {:<12} {:<12} {:<12} {:<12}".format(
        "#", "INDICE", "ARG1", "ARG2", "RESULT", "EXTRA"))
    for i, op in enumerate(operaciones, start=1):
        print("{:<4} {:<8} {:<12} {:<12} {:<12} {:<12}".format(
            i,
            op["indice"],
            "%s(%s)" % (_fmt_hex(op["arg1"]), _fmt_dec(op["arg1"])),
            "%s(%s)" % (_fmt_hex(op["arg2"]), _fmt_dec(op["arg2"])),
            _fmt_hex(op["resultado"]),
            _fmt_hex(op["extra"]),
        ))
    print()


def _imprimir_consola(console):
    print("-" * 70)
    print("RESULTADOS POR SUBRUTINA (salida de consola del flujo automatico)")
    print("-" * 70)
    if console:
        sys.stdout.write(console)
        if not console.endswith("\n"):
            print()
    else:
        print("(sin salida de consola capturada)")
    print()


def _imprimir_registros(sim):
    print("-" * 70)
    print("ESTADO FINAL DE REGISTROS CLAVE (R0..R5)")
    print("-" * 70)
    for r in range(6):
        print("R%d = %-8s  dec=%s" % (r, _fmt_hex(sim.regs[r]), _fmt_dec(sim.regs[r])))
    print()


def _imprimir_telemetria(t):
    print("-" * 70)
    print("TELEMETRIA")
    print("-" * 70)
    print("Instrucciones ejecutadas : %d" % t["instrucciones_ejecutadas"])
    print("Ciclos estimados         : %d" % t["ciclos_estimados"])
    print("Accesos a memoria        : %d" % t["accesos_memoria"])
    print("Bytes ocupados           : %d" % t["bytes_ocupados"])
    print("Excepciones fatales      : %d" % t["excepciones_fatales"])
    desg = t["desglose_por_familia"]
    print("Desglose por familia     : ARITH=%d SHIFTER=%d MEMORY=%d CONTROL=%d BRANCH=%d" % (
        desg["ARITH"], desg["SHIFTER"], desg["MEMORY"], desg["CONTROL"], desg["BRANCH"]))
    print()


def ejecutar_selftest(variante):
    """Ejecuta el selftest del Grupo 27 para la variante dada. Devuelve codigo de salida."""
    print("=" * 70)
    print("ERNIE-CORE SELFTEST -- Benchmark Grupo 27 (variante %s)" % variante)
    print("=" * 70)

    base_var = os.path.join(BASE_DIR, "Benchmark_Versions", "Benchmark_%s" % variante)
    main_asm = os.path.join(base_var, "main_grupo27.asm")
    lib_dir = os.path.join(base_var, "lib")

    if not os.path.isfile(main_asm):
        print("ERROR: no se encontro %s" % main_asm, file=sys.stderr)
        return 1

    deps = [f for f in sorted(glob.glob(os.path.join(lib_dir, "*.asm")))
            if os.path.basename(f) != "main_grupo27.asm"]

    # 1) Parseo dinamico de vectores precargados.
    try:
        verbose, operaciones = parsear_vectores(main_asm)
    except (OSError, ValueError) as e:
        print("ERROR: no se pudieron parsear los vectores de %s: %s" % (main_asm, e),
              file=sys.stderr)
        return 1

    # 2) Ensamblado + enlazado (strict=False por dependencias legacy).
    out_dir = os.path.join(BASE_DIR, "Pruebas_ISA", "Selftest")
    os.makedirs(out_dir, exist_ok=True)
    bin_salida = os.path.join(out_dir, "selftest_grupo27_%s.bin" % variante.lower())

    print("Ensamblando: %s" % main_asm)
    print("Dependencias: %d modulos en %s" % (len(deps), lib_dir))
    print("Binario de salida: %s" % bin_salida)
    try:
        ensamblador = Ensamblador(main_asm, bin_salida, deps, strict=False)
        ensamblador.ejecutar()
    except (ValueError, OSError) as e:
        print("ERROR de ensamblado: %s" % e, file=sys.stderr)
        return 1
    print("Ensamblado OK")
    print()

    # 3) Simulacion en modo automatico (sin teclado), capturando la consola.
    sim = Simulador(bin_salida)
    sim.input_buffer = []
    buf = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = buf
    try:
        sim.ejecutar(max_instrucciones=MAX_INSTRUCCIONES)
    finally:
        sys.stdout = old_stdout
    console = buf.getvalue()

    t = sim.obtener_telemetria()

    # 4) Salida clara por pantalla.
    _imprimir_vectores(verbose, operaciones)
    _imprimir_consola(console)
    _imprimir_registros(sim)
    _imprimir_telemetria(t)

    # 5) Criterios de exito.
    faltan = [b for b in BANNERS_GRUPO27 if b not in console]
    halt_ok = bool(sim.halted) and (sim.excepciones_fatales == 0) and \
        (t["instrucciones_ejecutadas"] < MAX_INSTRUCCIONES)
    exc_ok = (sim.excepciones_fatales == 0)
    r6_ok = ((sim.regs[6] & MASK_16) == STACK_BASE)
    console_ok = (len(faltan) == 0)
    mem_ok = (t["bytes_ocupados"] > 0)

    print("-" * 70)
    print("VERIFICACION")
    print("-" * 70)
    print("Detenida por HALT (sin timeout) : %s" % ("OK" if halt_ok else "FALLO"))
    print("Excepciones fatales == 0        : %s (%d)" % ("OK" if exc_ok else "FALLO",
                                                          sim.excepciones_fatales))
    print("Pila balanceada R6 == 0xFFFE    : %s (%s)" % ("OK" if r6_ok else "FALLO",
                                                          _fmt_hex(sim.regs[6])))
    print("Banners de las 23 operaciones   : %s" % ("OK" if console_ok else "FALLO"))
    if faltan:
        for b in faltan:
            print("   - FALTA banner: %s" % b)
    print("Memoria ocupada > 0             : %s (%d bytes)" % ("OK" if mem_ok else "FALLO",
                                                               t["bytes_ocupados"]))
    if not console_ok:
        print("   (Nota: %d/%d banners presentes)" % (
            len(BANNERS_GRUPO27) - len(faltan), len(BANNERS_GRUPO27)))
    print()

    ok = halt_ok and exc_ok and r6_ok and console_ok and mem_ok
    print("=" * 70)
    print("RESULTADO SELFTEST (%s): %s" % (variante, "OK" if ok else "FALLIDO"))
    print("=" * 70)
    return 0 if ok else 1


def _identificar_grupo(etiq, mod):
    """
    Deriva el grupo (G<N>) de una subrutina a partir de su etiqueta o, en su
    defecto, del nombre del modulo que la define. Resolucion en cascada:
      1. Prefijo en la etiqueta: patrones 'G<N>_' o '_G<N>' al inicio
         (insensible a mayusculas/minusculas).
      2. Prefijo en el nombre del modulo: patron 'g<N>_' al inicio
         (insensible a mayusculas/minusculas; el nombre de modulo ya viene
         en mayusculas desde el ensamblador).
      3. Fallback: '-' si no se identifica ningun prefijo.
    Devuelve la cadena 'G<N>' en mayusculas o '-'.
    """
    for texto in (etiq, mod):
        if not texto:
            continue
        m = re.match(r'(?i)^G(\d+)_', texto) or re.match(r'(?i)^_G(\d+)', texto)
        if m:
            return "G%s" % m.group(1)
    return "-"


def ejecutar_profile(variante):
    """
    Ejecuta el benchmark del Grupo 27 para la variante dada CON PERFILADO activo
    (instrumentación por subrutina en el Simulador) y muestra el reporte de
    perfilado + pico de profundidad de pila (R6).

    Devuelve 0 si la simulación termina sin excepciones fatales; 1 si hay fallo
    de ensamblado/carga o excepción fatal durante la corrida.
    """
    print("=" * 70)
    print("ERNIE-CORE PROFILE -- Benchmark Grupo 27 (variante %s)" % variante)
    print("=" * 70)

    base_var = os.path.join(BASE_DIR, "Benchmark_Versions", "Benchmark_%s" % variante)
    main_asm = os.path.join(base_var, "main_grupo27.asm")
    lib_dir = os.path.join(base_var, "lib")

    if not os.path.isfile(main_asm):
        print("ERROR: no se encontro %s" % main_asm, file=sys.stderr)
        return 1

    deps = [f for f in sorted(glob.glob(os.path.join(lib_dir, "*.asm")))
            if os.path.basename(f) != "main_grupo27.asm"]

    # Binario dedicado (no sobrescribe artefactos de selftest/verify).
    out_dir = os.path.join(BASE_DIR, "Pruebas_ISA", "Selftest")
    os.makedirs(out_dir, exist_ok=True)
    bin_salida = os.path.join(out_dir, "profile_grupo27_%s.bin" % variante.lower())

    print("Ensamblando: %s" % main_asm)
    print("Dependencias: %d modulos en %s" % (len(deps), lib_dir))
    print("Binario de salida: %s" % bin_salida)
    try:
        ensamblador = Ensamblador(main_asm, bin_salida, deps, strict=False)
        ensamblador.ejecutar()
    except (ValueError, OSError) as e:
        print("ERROR de ensamblado: %s" % e, file=sys.stderr)
        return 1

    # Mapa direccion -> etiqueta para nombrar las subrutinas en el reporte.
    addr_a_nombre = {}
    # Mapa direccion -> grupo (G<N>) para la columna GRUPO del reporte. Se
    # resuelve en cascada (etiqueta -> modulo -> '-') y se prefiere un grupo
    # real por encima del fallback '-' cuando varias etiquetas comparten
    # direccion de entrada.
    addr_a_grupo = {}
    for (_mod, etiq), addr in ensamblador.tabla_simbolos_global.items():
        dir16 = addr & MASK_16
        addr_a_nombre.setdefault(dir16, etiq)
        grupo = _identificar_grupo(etiq, _mod)
        if dir16 not in addr_a_grupo or (addr_a_grupo[dir16] == "-" and grupo != "-"):
            addr_a_grupo[dir16] = grupo
    print("Ensamblado OK")
    print()

    # Simulacion con perfilado activo; la consola del programa se captura y
    # descarta para no contaminar el reporte de perfilado.
    try:
        sim = Simulador(bin_salida)
    except (OSError, ValueError) as e:
        print("ERROR al cargar el binario '%s': %s" % (bin_salida, e), file=sys.stderr)
        return 1
    sim.input_buffer = []
    sim.simbolos_perfil = addr_a_nombre
    sim.simbolos_grupo = addr_a_grupo
    sim.profile_activo = True
    buf = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = buf
    try:
        sim.ejecutar(max_instrucciones=MAX_INSTRUCCIONES)
    finally:
        sys.stdout = old_stdout

    imprimir_reporte_perfilado(
        sim, titulo="BENCHMARK GRUPO 27 (variante %s)" % variante)

    ok = (sim.excepciones_fatales == 0)
    print("=" * 70)
    print("RESULTADO PROFILE (%s): %s" % (variante, "OK" if ok else "FALLIDO"))
    print("=" * 70)
    return 0 if ok else 1


def ejecutar_check_abi(variante):
    """
    Ejecuta el benchmark del Grupo 27 para la variante dada CON AUDITORIA ABI
    activa (instrumentacion JSR/JSRR -> RET en el Simulador) y muestra el reporte
    de violaciones de convencion de llamada y balance de pila (R6).

    Devuelve:
      0 si no hay violaciones ABI ni excepciones fatales,
      1 si se detecta al menos una violacion ABI, fallo de ensamblado/carga o
        excepcion fatal,
      2 ante uso invalido (variante desconocida).
    """
    if variante not in ("Standard", "Optimized"):
        print("ERROR: variante desconocida '%s'." % variante, file=sys.stderr)
        return 2

    print("=" * 70)
    print("ERNIE-CORE ABI CHECK -- Benchmark Grupo 27 (variante %s)" % variante)
    print("=" * 70)

    base_var = os.path.join(BASE_DIR, "Benchmark_Versions", "Benchmark_%s" % variante)
    main_asm = os.path.join(base_var, "main_grupo27.asm")
    lib_dir = os.path.join(base_var, "lib")

    if not os.path.isfile(main_asm):
        print("ERROR: no se encontro %s" % main_asm, file=sys.stderr)
        return 1

    deps = [f for f in sorted(glob.glob(os.path.join(lib_dir, "*.asm")))
            if os.path.basename(f) != "main_grupo27.asm"]

    # Binario dedicado (no sobrescribe artefactos de selftest/verify/profile).
    out_dir = os.path.join(BASE_DIR, "Pruebas_ISA", "Selftest")
    os.makedirs(out_dir, exist_ok=True)
    bin_salida = os.path.join(out_dir, "checkabi_grupo27_%s.bin" % variante.lower())

    print("Ensamblando: %s" % main_asm)
    print("Dependencias: %d modulos en %s" % (len(deps), lib_dir))
    print("Binario de salida: %s" % bin_salida)
    try:
        ensamblador = Ensamblador(main_asm, bin_salida, deps, strict=False)
        ensamblador.ejecutar()
    except (ValueError, OSError) as e:
        print("ERROR de ensamblado: %s" % e, file=sys.stderr)
        return 1

    # Mapa direccion -> etiqueta y direccion -> grupo (G<N>) para el reporte ABI.
    addr_a_nombre = {}
    addr_a_grupo = {}
    for (_mod, etiq), addr in ensamblador.tabla_simbolos_global.items():
        dir16 = addr & MASK_16
        addr_a_nombre.setdefault(dir16, etiq)
        grupo = _identificar_grupo(etiq, _mod)
        if dir16 not in addr_a_grupo or (addr_a_grupo[dir16] == "-" and grupo != "-"):
            addr_a_grupo[dir16] = grupo
    print("Ensamblado OK")
    print()

    # Simulacion con auditoria ABI activa; la consola del programa se captura y
    # descarta para no contaminar el reporte ABI.
    try:
        sim = Simulador(bin_salida)
    except (OSError, ValueError) as e:
        print("ERROR al cargar el binario '%s': %s" % (bin_salida, e), file=sys.stderr)
        return 1
    sim.input_buffer = []
    sim.simbolos_perfil = addr_a_nombre
    sim.simbolos_grupo = addr_a_grupo
    sim.check_abi_activo = True
    buf = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = buf
    try:
        sim.ejecutar(max_instrucciones=MAX_INSTRUCCIONES)
    finally:
        sys.stdout = old_stdout

    sim._reporte_abi(titulo="BENCHMARK GRUPO 27 (variante %s)" % variante)

    hubo_violaciones = len(sim._abi_violaciones) > 0
    ok = (not hubo_violaciones) and (sim.excepciones_fatales == 0)
    print("=" * 70)
    print("RESULTADO CHECK-ABI (%s): %s" % (variante, "OK" if ok else "FALLIDO"))
    print("=" * 70)
    if ok:
        return 0
    return 1


# Mapeo variante -> (script de suite, nombre del JSON de resultados en Pruebas_ISA/).
# Los nombres de archivo son fijos y publicos (no se tocan las suites ni los .asm).
# Líneas 546-551:
SUITES_VERIFY = {
    "Standard": ("suite_oraculo_benchmark_Standard.py",
                 "Resultados_de_Pruebas_STANDARD.json"),
    "Optimized": ("suite_oraculo_benchmark_Optimized.py",
                  "Resultados_de_Pruebas_OPTIMIZED.json"),
}


def _leer_json_resultados(ruta_json):
    """Carga el JSON de resultados de la suite. Devuelve dict o None si falla."""
    try:
        with open(ruta_json, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError) as e:
        print("ERROR: no se pudo leer el JSON de resultados %s: %s" % (ruta_json, e),
              file=sys.stderr)
        return None


def ejecutar_verify(variante):
    """
    Ejecuta la suite de oraculos completa para la variante dada en un SUBPROCESO
    (suite_oraculo_benchmark_<Standard|Optimized>.py) y lee el JSON de resultados
    correspondiente en Pruebas_ISA/ para reportar el resumen global.

    Criterio de exito: total de casos fallidos == 0 Y total_fatal == 0 Y el
    subproceso termina sin excepcion (returncode 0). Devuelve 0 si todo pasa,
    1 si hay fallos/errores/excepciones.
    """
    print("=" * 70)
    print("ERNIE-CORE VERIFY -- Suite de oraculos benchmark (variante %s)" % variante)
    print("=" * 70)

    if variante not in SUITES_VERIFY:
        print("ERROR: variante desconocida '%s'." % variante, file=sys.stderr)
        return 2

    script_name, json_name = SUITES_VERIFY[variante]
    script_path = os.path.join(IMPL_DIR, script_name)
    json_path = os.path.join(BASE_DIR, "Resultados", json_name)

    if not os.path.isfile(script_path):
        print("ERROR: no se encontro la suite %s" % script_path, file=sys.stderr)
        return 1

    # 1) Ejecucion de la suite en un subproceso (no altera este proceso).
    print("Ejecutando suite: %s" % script_path)
    print("JSON de resultados: %s" % json_path)
    print("-" * 70)
    try:
        proc = subprocess.run([sys.executable, script_path])
        rc_suite = proc.returncode
    except OSError as e:
        print("ERROR: no se pudo lanzar el subproceso de la suite: %s" % e,
              file=sys.stderr)
        return 1

    # 2) Lectura del JSON de resultados.
    data = _leer_json_resultados(json_path)
    if data is None:
        return 1

    summary = data.get("summary", {}) or {}
    total_cases = int(data.get("total_cases", 0) or 0)
    total_fatal = int(data.get("total_fatal", 0) or 0)

    total_passed = 0
    total_transversal = 0
    for st in summary.values():
        total_passed += int(st.get("passed", 0) or 0)
        total_transversal += int(st.get("transversal_fail", 0) or 0)
    total_failed = total_cases - total_passed
    if total_failed < 0:
        total_failed = 0

    # 3) Resumen global (PASS/FAIL/fatal).
    print("-" * 70)
    print("RESUMEN VERIFY (%s)" % variante)
    print("-" * 70)
    print("Modulos evaluados        : %d" % len(summary))
    print("Casos totales            : %d" % total_cases)
    print("PASS (pasadas)           : %d" % total_passed)
    print("FAIL (fallidas)          : %d" % total_failed)
    print("Fatal (excepciones)      : %d" % total_fatal)
    print("Transversal_fail         : %d" % total_transversal)
    print("Returncode subproceso    : %d" % rc_suite)

    # Detalle de modulos con fallos o fatales (si los hay).
    con_problemas = [(name, st) for name, st in summary.items()
                     if (int(st.get("passed", 0) or 0) != int(st.get("total", 0) or 0))
                     or (int(st.get("fatal_exceptions", 0) or 0) != 0)
                     or (int(st.get("transversal_fail", 0) or 0) != 0)]
    if con_problemas:
        print("-" * 70)
        print("MODULOS CON FALLOS/FATALES")
        print("-" * 70)
        for name, st in con_problemas:
            print("  %-32s %d/%d PASS, fatal=%d, transversal_fail=%d" % (
                name,
                int(st.get("passed", 0) or 0),
                int(st.get("total", 0) or 0),
                int(st.get("fatal_exceptions", 0) or 0),
                int(st.get("transversal_fail", 0) or 0)))
    print()

    ok = (total_failed == 0) and (total_fatal == 0) and (rc_suite == 0)
    print("=" * 70)
    print("RESULTADO VERIFY (%s): %s" % (variante, "OK" if ok else "FALLIDO"))
    print("=" * 70)
    return 0 if ok else 1


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="ernie_runner.py",
        description="Lanzador/driver CLI del toolchain Ernie-Core (Laboratorio 3C).",
    )
    parser.add_argument("--selftest", action="store_true",
                        help="Ejecuta el benchmark del Grupo 27 en modo automatico.")
    parser.add_argument("--verify", nargs="?", const="__default__", default=None,
                        metavar="{standard|optimized}",
                        help="Ejecuta la suite de oraculos completa (723 vectores) y "
                             "resume PASS/FAIL/fatal. Variante por defecto: Standard.")
    parser.add_argument("--profile", action="store_true",
                        help="Ejecuta el benchmark con perfilado por subrutina y "
                             "rastreo de profundidad de pila (R6).")
    parser.add_argument("--check-abi", action="store_true",
                        help="Audita la convencion de llamada (ABI) y el balance "
                             "de pila (R6) en cada par JSR/JSRR -> RET.")
    grupo = parser.add_mutually_exclusive_group()
    grupo.add_argument("--opt", action="store_true",
                       help="Usa la variante Benchmark_Optimized (por defecto Standard).")
    grupo.add_argument("--standard", action="store_true",
                       help="Usa la variante Benchmark_Standard (por defecto).")
    args = parser.parse_args(argv)

    verify_solicitado = (args.verify is not None)
    valor_verify = args.verify
    profile_solicitado = bool(args.profile)
    checkabi_solicitado = bool(args.check_abi)

    # Regla: --selftest, --verify, --profile y --check-abi son mutuamente
    # excluyentes -> codigo 2.
    modos_activos = sum([bool(args.selftest), verify_solicitado,
                         profile_solicitado, checkabi_solicitado])
    if modos_activos > 1:
        print("ERROR: --selftest, --verify, --profile y --check-abi son "
              "mutuamente excluyentes.", file=sys.stderr)
        return 2

    # Regla: se requiere al menos un modo -> codigo 2.
    if modos_activos == 0:
        parser.print_usage(sys.stderr)
        print("ERROR: se requiere --selftest, --verify, --profile o --check-abi. "
              "Modos disponibles: --selftest [--opt|--standard] | "
              "--verify [standard|optimized] [--opt|--standard] | "
              "--profile [--opt|--standard] | --check-abi [--opt|--standard].",
              file=sys.stderr)
        return 2

    if checkabi_solicitado:
        variante_a = _resolver_variantes(args)
        if variante_a is None:
            print("ERROR: --opt y --standard son mutuamente excluyentes.", file=sys.stderr)
            return 2
        return ejecutar_check_abi(variante_a)

    if profile_solicitado:
        variante_p = _resolver_variantes(args)
        if variante_p is None:
            print("ERROR: --opt y --standard son mutuamente excluyentes.", file=sys.stderr)
            return 2
        return ejecutar_profile(variante_p)

    if verify_solicitado:
        # Validacion del valor posicional opcional de --verify.
        if valor_verify not in ("__default__", "standard", "optimized"):
            print("ERROR: valor invalido para --verify: '%s' (use standard|optimized)."
                  % valor_verify, file=sys.stderr)
            return 2
        # Resolucion de la variante: --opt/--standard tienen prioridad; si no, el
        # valor posicional; si tampoco, Standard por defecto.
        if args.opt:
            variante_v = "Optimized"
        elif args.standard:
            variante_v = "Standard"
        elif valor_verify == "optimized":
            variante_v = "Optimized"
        else:
            variante_v = "Standard"
        return ejecutar_verify(variante_v)

    # Modo --selftest.
    variante = _resolver_variantes(args)
    if variante is None:
        print("ERROR: --opt y --standard son mutuamente excluyentes.", file=sys.stderr)
        return 2

    return ejecutar_selftest(variante)


if __name__ == "__main__":
    sys.exit(main())