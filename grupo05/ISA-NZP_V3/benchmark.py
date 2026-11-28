#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
benchmark.py - Pasa TODOS los .asm de una carpeta (p. ej. lib/) por el
ensamblador y después por el simulador, y deja un informe.

Uso:
    python benchmark.py lib                      # lo básico (ejecuta también los
                                                 # main*.asm de la carpeta madre)
    python benchmark.py lib --main main_grupo27.asm   # un principal explícito
    python benchmark.py lib -d build -r          # con subcarpetas
    python benchmark.py lib --casos casos.json   # entradas/esperados por archivo
    python benchmark.py lib --regs R0=6,R1=3     # entradas por defecto a módulos

Modo de cada archivo (columna "modo"): los fuentes escritos para el LC-3
CLÁSICO (usan LD/ST/LDR/STR, direcciones de palabra, ADD con inmediato de 5
bits...) se ensamblan y simulan en modo clásico; los de la ISA nueva
(LDH/STH/LDB/MUL/SHF...) en modo nuevo. Se detecta solo; --modo lo fuerza.

PROGRAMAS PRINCIPALES (principal): un .asm que llama a los módulos por
.EXTERNAL (p. ej. main_grupo27.asm). Se ensambla junto con los módulos que
pide, buscándolos en la carpeta lib, y se simula completo.

Qué hace con cada archivo
  1. Lo ensambla solo (igual que `ensamblador.py archivo.asm`). Los .EXTERNAL
     se resuelven buscando en la misma carpeta.
  2. Según lo que sea:
       PROGRAMA  (usa HALT)      -> simula el .bin tal cual.
       MÓDULO    (subrutina: no tiene HALT, termina en RET) -> arma un
                  ARNÉS: un programa mínimo que carga R0..R5, hace JSRR a la
                  rutina y luego HALT. Se ensambla junto con el módulo, queda
                  en build/<nombre>.arnes.bin (+ .lst) y se simula ese.
       SOLO DATOS (sin instrucciones) -> se omite.
  3. Simula, y clasifica el resultado:
       OK            terminó con HALT (y cumplió lo esperado, si lo hay)
       FALLA         terminó pero no dio lo esperado (casos.json)
       ENSAMBLADO    no ensambló (el informe agrupa los errores por tipo)
       EXCEPCION     el simulador paró por error (instrucción inválida,
                     acceso impar, división por cero, ...)
       LIMITE        llegó al máximo de instrucciones (¿bucle infinito?)
       ENTRADA       el programa pidió GETC/IN y no hay entrada (use casos.json
                     o --entrada)
       OMITIDO       solo datos / sin código

casos.json (opcional; la clave es el nombre del archivo sin .asm, o "*" para
valores por defecto de todos):
  {
    "*":               {"regs": {"R0": 6, "R1": 3}},
    "Mul_Sucesiva_POW": {"regs":     {"R0": "0x0180", "R1": 5},
                         "entry":    "Mul_Sucesiva_POW",
                         "esperado": {"R0": "0x0798"},
                         "mem":      {"0x4000": 7},
                         "salida":   "texto exacto",
                         "entrada":  "texto para GETC/IN",
                         "max":      200000,
                         "tipo":     "modulo"}      <- fuerza modulo|programa
  }

Códigos de salida: 0 si todo OK/OMITIDO, 1 si hubo algún problema.
"""
import argparse
import csv
import json
import os
import re
import sys
import time
from collections import Counter, defaultdict

import isa
import ensamblador as ens
import simulador as sim_mod

ARNES_DESPLAZAMIENTO = {"nuevo": 0x80,      # bytes antes del módulo
                        "clasico": 0x40}    # palabras antes del módulo
REGS_ENTRADA = range(0, 6)       # R6 es la pila (la pone el simulador), R7 la llamada


# ---------------------------------------------------------------------------
# casos.json
# ---------------------------------------------------------------------------
def _valor(v):
    return int(v, 0) if isinstance(v, str) else int(v)


def cargar_casos(ruta):
    if not ruta:
        return {}
    with open(ruta, encoding="utf-8") as f:
        crudo = json.load(f)
    return {k.lower(): v for k, v in crudo.items()}


def caso_de(casos, r):
    """Mezcla el caso por defecto '*' con el específico del archivo."""
    c = dict(casos.get("*", {}))
    for clave in (r["stem"].lower(), os.path.splitext(r["nombre"])[0].lower(),
                  os.path.basename(r["stem"]).lower()):
        if clave in casos:
            c.update(casos[clave])
            break
    return c


# ---------------------------------------------------------------------------
# Arnés para módulos
# ---------------------------------------------------------------------------
def texto_arnes(origen_arnes, regs, direccion_entrada, clasico=False):
    L = [f"        .ORIG x{origen_arnes:04X}"]
    if clasico:
        for r in sorted(regs):
            L.append(f"        LD R{r}, __H_R{r}")
        L += ["        LD R7, __H_ENT", "        JSRR R7", "        HALT"]
    else:
        for r in sorted(regs):
            L += [f"        LEA R{r}, __H_R{r}", f"        LDH R{r}, R{r}, #0"]
        L += ["        LEA R7, __H_ENT", "        LDH R7, R7, #0",
              "        JSRR R7", "        HALT"]
    for r in sorted(regs):
        L.append(f"__H_R{r}   .FILL x{regs[r] & 0xFFFF:04X}")
    L.append(f"__H_ENT   .FILL x{direccion_entrada:04X}")
    L.append("        .END")
    return L


def armar_arnes(r, regs, entrada_forzada=None, dirs=None):
    """Ensambla arnés + módulo juntos. Devuelve el Ensamblador ya listo.
    Lanza ens.ErrorEnsamblador / ValueError con un mensaje legible."""
    base_asm = r["asm"]
    origen = base_asm.origen
    etq, addr = r["entrada"]
    if entrada_forzada:
        encontrado = [(n, a) for n, a in base_asm.tabla_simbolos.items()
                      if n.lower() == entrada_forzada.lower()]
        if not encontrado:
            raise ValueError(f"la etiqueta de entrada '{entrada_forzada}' "
                             f"no existe en {r['nombre']}")
        etq, addr = encontrado[0]
    if addr is None:
        raise ValueError("no se encontró el punto de entrada del módulo")
    modo = r["modo"]
    h = origen - ARNES_DESPLAZAMIENTO[modo]
    if h < 0:
        raise ValueError(f"el módulo empieza en x{origen:04X}: no hay lugar "
                         f"para el arnés antes de él")

    asm = ens.Ensamblador(modo, dirs)
    arnes = asm.cargar_unidad("<arnes>",
                              texto_arnes(h, regs, addr, modo == "clasico"))
    modulo = asm.cargar_unidad(r["ruta"])
    if not any(l.op == ".ORIG" for l in modulo.lineas):
        modulo.lineas.insert(0, ens.Linea(r["ruta"], 0, "", [], ".ORIG",
                                          f"x{origen:04X}"))
    asm.ensamblar_unidades([arnes, modulo])
    return asm


# ---------------------------------------------------------------------------
# Resultado por archivo
# ---------------------------------------------------------------------------
def nuevo_resultado(r):
    return {"nombre": r["nombre"], "modo": r.get("modo", "?"), "tipo": "?",
            "estado": "?", "instr": 0,
            "detalle": "", "salida": "", "regs": None, "segundos": 0.0,
            "errores": r["errores"], "avisos": r["avisos"],
            "bin": None, "extra": ""}


def comprobar_esperado(sim, caso):
    """Devuelve lista de diferencias respecto de lo esperado en casos.json."""
    dif = []
    for reg, val in (caso.get("esperado") or {}).items():
        m = re.fullmatch(r"[Rr]([0-7])", reg)
        if not m:
            dif.append(f"registro desconocido '{reg}' en esperado")
            continue
        got, want = sim.registros[int(m.group(1))], _valor(val) & 0xFFFF
        if got != want:
            dif.append(f"{reg.upper()}=x{got:04X}({isa.a_signed16(got)}) "
                       f"esperado x{want:04X}({isa.a_signed16(want)})")
    for dir_, val in (caso.get("mem") or {}).items():
        d, want = _valor(dir_), _valor(val) & 0xFFFF
        try:
            got = sim.leer_palabra(d)
        except sim_mod.ErrorSimulador:
            dif.append(f"mem x{d:04X}: dirección impar")
            continue
        if got != want:
            dif.append(f"mem x{d:04X}=x{got:04X} esperado x{want:04X}")
    if "salida" in caso:
        got = "".join(sim.salida)
        if got != caso["salida"]:
            dif.append(f"salida {got!r} esperada {caso['salida']!r}")
    return dif


def procesar(r, args, casos, regs_defecto, principal=False):
    res = nuevo_resultado(r)
    if not r["ok"]:
        res["tipo"], res["estado"] = "-", "ENSAMBLADO"
        res["detalle"] = f"{len(r['errores'])} error(es)"
        return res

    caso = caso_de(casos, r)
    if caso.get("omitir"):
        res["estado"], res["tipo"], res["detalle"] = "OMITIDO", "-", \
            "omitido por casos.json"
        return res
    if r["n_instr"] == 0:
        res["estado"], res["tipo"], res["detalle"] = "OMITIDO", "datos", \
            "no tiene instrucciones"
        return res

    tipo = (caso.get("tipo") or ("programa" if r["es_programa"] else "modulo"))
    if principal:
        tipo = "programa"
    res["tipo"] = "principal" if principal else tipo
    regs_caso = {int(k.lstrip("Rr")): _valor(v)
                 for k, v in (caso.get("regs") or {}).items()}
    regs = dict(regs_defecto)           # solo para módulos
    regs.update(regs_caso)
    entrada = caso.get("entrada", args.entrada or "")
    maxi = int(caso.get("max", args.max_principal if principal else args.max))

    ruta_bin = r.get("rutas", {}).get("bin", r["base"] + ".bin")
    if tipo == "modulo":
        try:
            asm = armar_arnes(r, {k: v for k, v in regs.items()
                                  if k in REGS_ENTRADA}, caso.get("entry"),
                             args.lib)
        except ens.ErrorEnsamblador as e:
            res["estado"], res["detalle"] = "ENSAMBLADO", "falló el arnés"
            res["errores"] = list(r["errores"]) + list(e.errores)
            return res
        except (ValueError, OSError) as e:
            res["estado"], res["detalle"] = "ENSAMBLADO", f"arnés: {e}"
            res["errores"] = [f"{r['ruta']}: arnés: {e}"]
            return res
        ruta_base = r["base"] + ".arnes"
        rutas_arnes = ens.escribir_salidas(asm, ruta_base, organizar_formatos=not args.sin_organizar)
        ruta_bin = rutas_arnes["bin"]
        res["extra"] = "entrada=" + (r["entrada"][0] or f"x{r['entrada'][1]:04X}")
    res["bin"] = ruta_bin

    t0 = time.time()
    try:
        sim = sim_mod.simular_archivo(
            ruta_bin, entrada, maxi, args.pila,
            regs_caso if tipo == "programa" else None,
            perfil=False)
    except (sim_mod.ErrorSimulador, OSError) as e:
        res["estado"], res["detalle"] = "EXCEPCION", f"no cargó: {e}"
        return res
    res["segundos"] = time.time() - t0
    res["instr"] = sim.instrucciones
    res["salida"] = "".join(sim.salida)
    res["regs"] = list(sim.registros)

    estado = sim_mod.clasificar(sim)
    if estado == "OK":
        dif = comprobar_esperado(sim, caso)
        if dif:
            estado, res["detalle"] = "FALLA", "; ".join(dif)
    else:
        res["detalle"] = sim.error or ""
    res["estado"] = estado
    return res


# ---------------------------------------------------------------------------
# Informe
# ---------------------------------------------------------------------------
def normalizar_error(txt):
    """Reduce un mensaje de error a su 'tipo' para poder contarlos."""
    m = re.search(r"error: (.*)", txt)
    msg = m.group(1) if m else txt.splitlines()[0]
    if "desconocid" in msg or "no definido" in msg:
        return msg.strip()          # aquí importa QUÉ nombre es
    msg = re.sub(r"'[^']*'", "'…'", msg)
    msg = re.sub(r"x[0-9A-Fa-f]{2,4}\b", "xN", msg)
    msg = re.sub(r"-?\d+", "N", msg)
    return msg.strip()


def grupos_de_errores(resultados):
    g = defaultdict(list)
    for res in resultados:
        for e in res["errores"]:
            g[normalizar_error(e)].append(res["nombre"])
    return sorted(g.items(), key=lambda kv: -len(kv[1]))


def imprimir_tabla(resultados):
    w = max([len(r["nombre"]) for r in resultados] + [8])
    print(f"{'archivo':<{w}}  {'tipo':<9} {'modo':<8} {'estado':<10} "
          f"{'instr':>9}  detalle")
    print("-" * (w + 70))
    for r in resultados:
        det = r["detalle"] or (
            ("salida " + repr(r["salida"][:30])) if r["salida"] else r["extra"])
        print(f"{r['nombre']:<{w}}  {r['tipo']:<9} {r['modo']:<8} "
              f"{r['estado']:<10} {r['instr']:>9}  {det[:90]}")


def resumen(resultados):
    c = Counter(r["estado"] for r in resultados)
    orden = ["OK", "FALLA", "ENSAMBLADO", "EXCEPCION", "LIMITE", "ENTRADA",
             "OMITIDO"]
    return ", ".join(f"{k}={c[k]}" for k in orden if c[k]), c


def escribir_informe_md(ruta, carpeta, resultados, tiempo):
    txt, c = resumen(resultados)
    L = [f"# Informe de benchmark: `{carpeta}`", "",
         f"- Archivos: **{len(resultados)}**   ({txt})",
         f"- Tiempo total: {tiempo:.1f} s", "",
         "## Resultado por archivo", "",
         "| archivo | tipo | modo | estado | instr | detalle |",
         "|---|---|---|---|---:|---|"]
    for r in resultados:
        det = (r["detalle"] or r["extra"]).replace("|", "\\|")
        L.append(f"| {r['nombre']} | {r['tipo']} | {r['modo']} | "
                 f"{r['estado']} | {r['instr']} | {det[:120]} |")
    g = grupos_de_errores(resultados)
    if g:
        L += ["", "## Errores de ensamblado agrupados por tipo", ""]
        for msg, archivos in g:
            L.append(f"- **{len(archivos)}x** {msg}  \n"
                     f"  en: {', '.join(sorted(set(archivos))[:8])}")
    for r in resultados:
        if r["tipo"] == "principal" and r["salida"]:
            L += ["", f"## Salida de {r['nombre']}", "", "```",
                  r["salida"][:4000].rstrip(), "```"]
    malos = [r for r in resultados
             if r["estado"] in ("ENSAMBLADO", "EXCEPCION", "LIMITE", "FALLA",
                                "ENTRADA")]
    if malos:
        L += ["", "## Detalle de los que no corrieron", ""]
        for r in malos:
            L += [f"### {r['nombre']} ({r['estado']})", ""]
            if r["errores"]:
                L += ["```"] + [e for e in r["errores"][:6]] + ["```"]
            else:
                L += [r["detalle"], ""]
    with open(ruta, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")


def escribir_csv(ruta, resultados):
    with open(ruta, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["archivo", "tipo", "modo", "estado", "instrucciones",
                    "segundos", "detalle", "salida"])
        for r in resultados:
            w.writerow([r["nombre"], r["tipo"], r["modo"], r["estado"],
                        r["instr"],
                        f"{r['segundos']:.3f}", r["detalle"], r["salida"]])


# ---------------------------------------------------------------------------
def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Ensambla y simula todos los .asm de una carpeta")
    ap.add_argument("carpeta", nargs="?", default="lib",
                    help="carpeta con los .asm (por defecto: lib)")
    ap.add_argument("-d", "--salida-dir", default="build",
                    help="dónde dejar .bin/.lst/.sym/informe (def.: build)")
    ap.add_argument("-r", "--recursivo", action="store_true")
    ap.add_argument("--casos", default="casos.json" if os.path.isfile("casos.json") else None,
                    help="casos.json con entradas/esperados (def.: casos.json si existe)")
    ap.add_argument("--regs", default="R0=6,R1=3",
                    help="registros iniciales de los MÓDULOS "
                         "(def.: R0=6,R1=3)")
    ap.add_argument("--entrada", default=None,
                    help="texto para GETC/IN de todos los programas")
    ap.add_argument("--max", type=int, default=2_000_000,
                    help="límite de instrucciones por archivo")
    ap.add_argument("--max-principal", type=int, default=50_000_000,
                    help="límite de instrucciones de los programas principales")
    ap.add_argument("--modo", choices=["auto", "nuevo", "clasico"],
                    default="auto",
                    help="ISA de los fuentes (def.: auto = se detecta)")
    ap.add_argument("--lib", action="append", default=[], metavar="DIR",
                    help="carpeta extra de módulos para .EXTERNAL (repetible)")
    ap.add_argument("--main", action="append", default=[], metavar="ARCHIVO",
                    help="programa principal a ejecutar (repetible). Si no "
                         "se indica ninguno, se usan los .asm de la carpeta "
                         "madre de la carpeta de módulos")
    ap.add_argument("--sin-principal", action="store_true",
                    help="no buscar programas principales")
    ap.add_argument("--pila", type=lambda s: int(s, 0), default=isa.PILA_INICIAL)
    ap.add_argument("--permitir-sqr", action="store_true")
    ap.add_argument("--sin-organizar", action="store_true",
                    help="guarda todo plano en <salida-dir> sin subcarpetas por tipo/formato")
    ap.add_argument("--informe", default=os.path.join("informes", "informe_benchmark.md"),
                    help="ruta del informe .md (def.: informes/informe_benchmark.md)")
    ap.add_argument("--csv", default=None, help="además, escribe un CSV")
    ap.add_argument("-v", "--verboso", action="store_true",
                    help="muestra también avisos y errores completos")
    args = ap.parse_args(argv)

    if args.permitir_sqr:
        isa.CONFIG["sqr"] = True
    if args.entrada is not None:
        args.entrada = args.entrada.encode().decode("unicode_escape")
    if not os.path.isdir(args.carpeta):
        print(f"No existe la carpeta '{args.carpeta}'.", file=sys.stderr)
        return 2
    try:
        casos = cargar_casos(args.casos)
        regs_defecto = sim_mod._parsear_regs(args.regs)
    except (OSError, ValueError, json.JSONDecodeError) as e:
        print(f"Error en la configuración: {e}", file=sys.stderr)
        return 2

    t0 = time.time()
    organizar = not args.sin_organizar
    dir_modulos = os.path.join(args.salida_dir, "modulos") if organizar else args.salida_dir
    dir_principales = os.path.join(args.salida_dir, "principales") if organizar else args.salida_dir
    print(f"[1/2] Ensamblando {args.carpeta} ...")
    ensamblados = ens.ensamblar_carpeta(args.carpeta, dir_modulos,
                                        args.recursivo, args.modo, args.lib,
                                        organizar_formatos=organizar)
    if not ensamblados:
        print("No hay archivos .asm.", file=sys.stderr)
        return 2
    n_ok = sum(1 for r in ensamblados if r["ok"])
    print(f"      {n_ok}/{len(ensamblados)} módulos ensamblaron.")

    principales = []
    mains = list(args.main)
    if not mains and not args.sin_principal:
        madre = os.path.dirname(os.path.abspath(args.carpeta))
        carpetas_main = [madre, os.path.join(madre, "principales")]
        for cm in carpetas_main:
            if os.path.isdir(cm):
                mains.extend(
                    os.path.join(cm, f) for f in sorted(os.listdir(cm))
                    if f.lower().startswith("main") and f.lower().endswith(".asm")
                )
    for m in mains:
        if not os.path.isfile(m):
            print(f"      (no existe el principal {m})", file=sys.stderr)
            continue
        principales.append(ens.ensamblar_principal(
            m, dir_principales, args.modo, [args.carpeta] + args.lib,
            organizar_formatos=organizar))
    if principales:
        print(f"      {sum(1 for p in principales if p['ok'])}/"
              f"{len(principales)} programas principales ensamblaron "
              f"({', '.join(p['nombre'] for p in principales)}).")
    print("[2/2] Simulando ...\n")

    resultados = [procesar(r, args, casos, regs_defecto) for r in ensamblados]
    resultados += [procesar(p, args, casos, regs_defecto, principal=True)
                   for p in principales]
    tiempo = time.time() - t0

    imprimir_tabla(resultados)
    txt, c = resumen(resultados)
    print(f"\nResumen: {txt}   ({tiempo:.1f} s)")

    g = grupos_de_errores(resultados)
    if g:
        print("\nErrores de ensamblado más comunes:")
        for msg, archivos in g[:8]:
            print(f"  {len(archivos):>3}x  {msg}")
    if args.verboso:
        for r in resultados:
            for a in r["avisos"]:
                print("  aviso:", a)
            for e in r["errores"]:
                print(e)

    os.makedirs(args.salida_dir, exist_ok=True)
    informe = args.informe or os.path.join("informes", "informe_benchmark.md")
    if os.path.dirname(informe):
        os.makedirs(os.path.dirname(informe), exist_ok=True)
    escribir_informe_md(informe, args.carpeta, resultados, tiempo)
    print(f"\nInforme: {informe}")
    if args.csv:
        escribir_csv(args.csv, resultados)
        print(f"CSV:     {args.csv}")
    malos = sum(v for k, v in c.items() if k not in ("OK", "OMITIDO"))
    return 0 if malos == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
