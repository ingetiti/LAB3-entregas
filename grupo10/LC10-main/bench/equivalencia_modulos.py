"""Equivalencia módulo por módulo: cada subrutina LC-3 de la cátedra contra su puerto a LC10.

    python bench/equivalencia_modulos.py RUTA\\lc3-project [asm/bench10] [--casos 40] [--semilla 1]

Para cada subrutina se arma un programa mínimo que solo tiene su dirección y un HALT; se cargan los
registros de entrada (y, si hace falta, texto en memoria o en la entrada del teclado) y se ejecuta en el
simulador de la cátedra (sin tocarlo) y en el de LC10. Se comparan R0..R5, el texto impreso y, cuando la
subrutina escribe una cadena, esa cadena. Las entradas son al azar (con los valores extremos mezclados);
si la versión LC-3 no termina dentro del límite, el caso se descarta.

Después corre sesiones interactivas completas del menú (teclado simulado) en los dos simuladores.
"""
from __future__ import annotations

import argparse
import importlib.util
import io
import random
import sys
import tempfile
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent))
from lc10.assembler import AsmError, assemble  # noqa: E402
from lc10.simulator import Fault, Machine  # noqa: E402

BUF = 0x7000          # zona de datos de las pruebas (arriba de las dos imágenes)
MAXPASOS = 700_000
CENTINELA = 0x1111    # R1..R5 arrancan en 0x1111, 0x2222, ... salvo los que fija el caso


def cargar(nombre, ruta):
    spec = importlib.util.spec_from_file_location(nombre, ruta)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[nombre] = mod
    spec.loader.exec_module(mod)
    return mod


def s16(v):
    v &= 0xFFFF
    return v - 0x10000 if v & 0x8000 else v


# ------------------------------------------------------------------------------ generadores
EDGES = [0, 1, -1, 2, -2, 255, 256, -256, 4096, -4096, 32767, -32768, 12345, -12345]


def r16(g):
    return g.choice(EDGES) if g.random() < 0.15 else g.randint(-32768, 32767)


def rpos(g, hi=32767):
    return g.choice([1, 2, 3, hi]) if g.random() < 0.1 else g.randint(1, hi)


def texto_decimal(g):
    mod = g.random()
    if mod < 0.08:
        return g.choice(["", "-", "+", ".", "abc", "1a2", "--3", "5.5.5"])
    signo = g.choice(["", "", "-", "+"])
    ent = "".join(g.choice("0123456789") for _ in range(g.choice([0, 1, 1, 2, 3, 4, 5, 6])))
    if g.random() < 0.6:
        frac = "".join(g.choice("0123456789") for _ in range(g.choice([1, 2, 3, 5, 9, 10, 11])))
        return signo + ent + g.choice([".", ","]) + frac
    return signo + ent


def texto_hex(g):
    if g.random() < 0.1:
        return g.choice(["", "g", "12x4", "fffff", "FFFF", "0"])
    return "".join(g.choice("0123456789abcdefABCDEF") for _ in range(g.randint(1, 5)))


# cada entrada: (módulo, etiqueta, generador) -> caso = dict(regs, put, stdin, get)
#   put:  [(dirección, texto)]  cadena que se escribe antes de ejecutar
#   get:  [dirección]           cadenas que se leen después y se comparan
def caso(regs=None, put=(), stdin="", get=()):
    return dict(regs=regs or {}, put=list(put), stdin=stdin, get=list(get))


def pareja(lo0, hi0, lo1, hi1):
    return lambda g: caso({0: g.randint(lo0, hi0), 1: g.randint(lo1, hi1)})


def full2(g):
    return caso({0: r16(g), 1: r16(g)})


def qmul(g):
    """Factores Q7.8 cuyo producto entra (o casi) en Q7.8: |a * b| <= 2^23 (+- un poco, para tocar el borde)."""
    a = r16(g)
    tope = max(1, int((2 ** 23) * g.choice([0.5, 0.9, 1.0, 1.0, 1.02, 1.5]) / max(1, abs(a))))
    b = g.randint(-min(tope, 32768), min(tope, 32767))
    return caso({0: a, 1: b}) if g.random() < 0.5 else caso({0: b, 1: a})


ENTRADAS = [
    ("g1_cordic_division", "CORDIC_DIV", lambda g: caso({0: g.randint(0, 0x7FFF), 1: g.randint(1, 0x7FFF)})),
    ("g3_MultiplicacionSHIFTandADD", "MULTIPLICARSHIFTANDADD", full2),
    ("g4_potencia", "EXP_RAPIDA", lambda g: caso({0: g.randint(-12, 12), 1: g.randint(0, 15)})),
    ("g5_Mul_Sucesiva_POW", "Mul_Sucesiva_POW", lambda g: caso({0: g.randint(-1500, 1500), 1: g.randint(0, 9)})),
    ("g6_EXP", "EXP_Q3_12", lambda g: caso({0: r16(g)})),
    ("g7_mcm", "MCM", lambda g: caso({0: g.randint(1, 300), 1: g.randint(1, 300)})),
    ("g7_mcd", "MCD", lambda g: caso({0: g.randint(1, 5000), 1: g.randint(1, 5000)})),
    ("g9_sqrt_nr_q8", "SQRT_NR_Q8", lambda g: caso({0: g.choice([0x0400, 0x1000, 0x03FF, 0x1001, 0, 0x7FFF, g.randint(0x0300, 0x1100)])})),
    ("g9_sqrt_nr_dq16", "SQRT_NR_DQ16", lambda g: caso({0: g.randint(0, 300), 1: g.randint(0, 65535)})),
    ("division_larga", "DIVIDIR", lambda g: caso({0: r16(g), 1: g.choice([-1, 1, 2, 5, 30000, -30000, g.randint(-32768, 32767) or 1])})),
    ("g11_CORDICLog", "CORDIC_LOG_BASE", lambda g: caso({0: rpos(g)})),
    ("g12_subrutina_grupo_12", "DIV_NEWTON", lambda g: caso({0: r16(g), 1: g.choice([1, -1, 256, g.randint(-32768, 32767) or 1])})),
    ("g14_log_borchardt_q8_7", "LN_GENERAL_Q8_7", lambda g: caso({0: rpos(g)})),
    ("g15_G15_Q312_Q78", "G15_Q312_Q78", lambda g: caso({0: r16(g)})),
    ("g18_booth", "MULT_BOOTH", full2),
    ("g18_booth", "MULT_BOOTH", qmul),
    ("g19_cordic_multiplicacion", "CORDIC_MUL", full2),
    ("g19_cordic_multiplicacion", "CORDIC_MUL", qmul),
    ("g3_MultiplicacionSHIFTandADD", "MULTIPLICARSHIFTANDADD", qmul),
    ("g20_Cordic_reduccion_de_argumento", "Reduccion_Argumento", lambda g: caso({0: r16(g)})),
    ("g21_senotaylor_subrutina", "CALCULAR_SENO", lambda g: caso({0: g.randint(-3700, 3700)})),
    # dominio documentado de la tabla: 0..2*pi (25736 en Q3.12). Fuera de ese rango se lee más allá de la tabla,
    # que es lo último del módulo: el resultado depende de qué módulo venga después y no es comparable.
    ("g22_Tabla_SIN_y_COS", "SENO_TABLA", lambda g: caso({0: g.choice([0, 25736, 6434, 12868, g.randint(0, 25736)])})),
    ("g22_Tabla_SIN_y_COS", "COSENO_TABLA", lambda g: caso({0: g.choice([0, 25736, 6434, 12868, g.randint(0, 25736)])})),
    ("g23_modulo_sqrt_nr", "SQRT_NR", lambda g: caso({0: rpos(g)})),
    ("g30_seno_cheb_pade", "SEN_CHEB_PADE", lambda g: caso({0: g.randint(-30000, 30000)})),
    ("g27_sumover", "SUMOVER", lambda g: caso({0: r16(g), 1: r16(g), 2: g.randint(0, 1)})),
    ("g27_circlsh", "CIRCLSH", lambda g: caso({0: r16(g), 1: r16(g), 2: g.randint(0, 33)})),
    ("g27_to_qm_n", "TO_QM_N", lambda g: caso({0: r16(g), 1: r16(g) & 0xFFFF, 2: g.randint(1, 15)})),
    ("g27_from_qm_n", "FROM_QM_N", lambda g: caso({0: r16(g), 1: g.choice([g.randint(1, 15)] * 5 + [0, 16, 17, 31, 32, g.randint(-40, 80)])})),
    ("g27_todec", "TODEC", lambda g: caso({0: r16(g), 1: g.choice([0, g.randint(0, 65535)]), 2: BUF, 3: g.randint(0, 7)}, get=[BUF])),
    ("g27_outval", "OUTVAL", lambda g: caso({0: r16(g), 1: g.randint(0, 65535), 2: g.choice([0, 16, g.randint(1, 15)])})),
    ("g24_conversor_lc3_max", "SUB_BASE_HEX", lambda g: caso({0: r16(g)})),
    ("g24_conversor_lc3_max", "SUB_BASE_BIN", lambda g: caso({0: r16(g)})),
    ("g27_fromdec", "FROMDEC", lambda g: (lambda t: caso({0: BUF}, put=[(BUF, t)]))(texto_decimal(g))),
    ("g27_fromhex", "FROMHEX", lambda g: (lambda t: caso({0: BUF}, put=[(BUF, t)]))(texto_hex(g))),
    ("g27_getline", "GETLINE", lambda g: caso({0: BUF, 1: BUF + 8}, stdin="".join(g.choice("abc 123.-") for _ in range(g.randint(0, 14))) + "\n", get=[BUF])),
    ("g27_getcfiltered", "GETCFILTERED", lambda g: caso({0: BUF}, put=[(BUF, g.choice(["09", "09adAD", "02", "01az"]))],
                                                        stdin="".join(g.choice("xy5ab9zD#") for _ in range(12)))),
    ("g27_getval", "GETVAL", lambda g: caso({0: g.choice([0, 8, 12, 14, 15, 16])},
                                             stdin=texto_decimal(g).replace("abc", "7") + "\n")),
    ("g27_pause", "PAUSE", lambda g: caso({0: 5, 1: 6}, stdin=g.choice("abc "))),
]

# (para getcfiltered, los caracteres que sobran de la entrada no se leen: GETC se queda sin entrada, así que
#  la prueba usa una entrada suficientemente larga y descarta los casos en que no hay un carácter válido)


# ------------------------------------------------------------------------------ ejecutores
class Lc3Runner:
    def __init__(self, asm, sim, base: Path, stem: str, etiqueta: str, tmp: Path):
        self.sim = sim
        src = tmp / f"t_{stem}_{etiqueta}.asm"
        src.write_text(f".ORIG x3000\n.EXTERNAL {stem}-{etiqueta}\nENTRY .FILL {stem}-{etiqueta}\nHLT HALT\n.END\n", encoding="utf-8")
        obj = asm.ProjectLinker(base / "lib").assemble_file(src, "obj")
        proto = sim.LC3(input_stream=io.StringIO(""), output_stream=io.StringIO())
        proto.load_object(obj)
        self.mem0 = list(proto.memory)
        self.entry = self.mem0[0x3000]
        self.palabras = len(obj) // 2 - 1

    def run(self, c):
        out = io.StringIO()
        m = self.sim.LC3(input_stream=io.StringIO(c["stdin"]), output_stream=out)
        m.memory = list(self.mem0)
        for i in range(1, 6):
            m.registers[i] = CENTINELA * i      # lo que el caso no fija arranca con un valor reconocible
        for addr, t in c["put"]:
            for i, ch in enumerate(t + "\0"):
                m.memory[addr + i] = ord(ch)
        for r, v in c["regs"].items():
            m.registers[r] = v & 0xFFFF
        m.registers[7] = 0x3001
        m.pc = self.entry
        try:
            m.run(MAXPASOS)
        except Exception as e:      # límite de instrucciones o fin de la entrada
            return None, f"{type(e).__name__}: {e}"
        texto = out.getvalue()
        if texto.endswith("\nHALT\n"):
            texto = texto[:-6]
        gets = []
        for a in c["get"]:
            s, i = "", 0
            while m.memory[a + i] and i < 64:
                s += chr(m.memory[a + i] & 0xFF)
                i += 1
            gets.append(s)
        return dict(regs=[m.registers[i] for i in range(6)], out=texto, gets=gets, steps=m.steps), None


class Lc10Runner:
    def __init__(self, fuentes, stem: str, etiqueta: str):
        main = f".ORIG x3000\n.EXTERNAL {stem}-{etiqueta}\nENTRY .FILL {stem}-{etiqueta}\nHLT HALT\n.END\n"
        res = assemble([("t_main.asm", main)] + fuentes)
        self.image = res.image
        self.entry = int.from_bytes(res.image.data[0:2], "little")
        self.palabras = len(res.image.data) // 2

    def run(self, c):
        m = Machine()
        m.load(self.image)
        for i in range(1, 6):
            m.regs[i] = CENTINELA * i
        for addr, t in c["put"]:
            for i, ch in enumerate((t + "\0").encode("latin-1")):
                m.mem[addr + i] = ch
        for r, v in c["regs"].items():
            m.regs[r] = v & 0xFFFF
        m.regs[7] = 0x3002
        m.pc = self.entry
        m.set_input(c["stdin"])
        try:
            res = m.run(MAXPASOS * 2)
        except Fault as e:
            return None, f"Fault: {e}"
        if res.reason != "halt":
            return None, f"{res.reason}: {res.message}"
        gets = []
        for a in c["get"]:
            s, i = "", 0
            while m.mem[a + i] and i < 64:
                s += chr(m.mem[a + i])
                i += 1
            gets.append(s)
        return dict(regs=[m.regs[i] for i in range(6)], out=res.output, gets=gets, steps=res.user_instructions), None


def fuentes_lc10(carpeta: Path, excluir=("main_grupo27.asm",)):
    return [(p.name, p.read_text(encoding="utf-8")) for p in sorted(carpeta.glob("*.asm")) if p.name not in excluir]


# ------------------------------------------------------------------------------ sesiones del menú
SESIONES = {
    "booth":        "72" "13.265625\n" "-7.23828125\n" " " "d",
    "seno taylor":  "10" "60\n" " " "d",
    "seno tabla+cheb": "11" "1.0471\n" " " "12" "0.5\n" " " "d",
    "coseno":       "2" "1.0471\n" " " "d",
    "base hex/bin": "30" "1342\n" " " "31" "-1078\n" " " "d",
    "raiz":         "40" "4.35\n" " " "41" "4.2339504128\n" " " "d",
    "exp":          "5" "1.0\n" " " "d",
    "potencias":    "60" "-2\n" "5\n" " " "61" "-2\n" "5\n" " " "d",
    "multiplicaciones": "70" "13.265625\n" "-7.23828125\n" " " "71" "13.265625\n" "-7.23828125\n" " " "d",
    "divisiones":   "80" "6.36\n" "3.23\n" " " "81" "6.36\n" "3.23\n" " " "82" "0.25\n" "0.5\n" " " "d",
    "logaritmos":   "90" "1.0\n" " " "91" "2.0\n" " " "d",
    "mcd mcm":      "a" "48\n" "18\n" " " "b" "16\n" "38\n" " " "d",
    "q3.12->q7.8":  "c" "5.3663844453\n" " " "d",
    "reduccion":    "0" "1.5708\n" " " "d",
    "entradas raras": "72" "abc\n" "99999.5\n" " " "72" "-\n" "+3,5\n" " " "72" ".\n" "1,\n" " " "d",
    "desborda y se corta": "72" "999999999999\n" "1.9999999999999\n" " " "d",
    "teclas invalidas": "xyz!7" "2" "1\n" "2\n" " " "d",
}


def sesion_lc3(asm, sim, base: Path, tmp: Path, texto: str):
    main = (base / "main_grupo27.asm").read_text(encoding="utf-8-sig")
    lineas = []
    for ln in main.splitlines():
        if ln.strip().startswith("LEA R0 programa_del_menu_completo"):
            ln = "; " + ln
        lineas.append(ln)
    src = tmp / "main_interactivo.asm"
    src.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    obj = asm.ProjectLinker(base / "lib").assemble_file(src, "obj")
    out = io.StringIO()
    m = sim.LC3(input_stream=io.StringIO(texto), output_stream=out)
    m.load_object(obj)
    try:
        m.run(5_000_000)
    except Exception as e:
        return out.getvalue(), f"{type(e).__name__}: {e}", m.steps
    t = out.getvalue()
    return (t[:-6] if t.endswith("\nHALT\n") else t), None, m.steps


def sesion_lc10(carpeta: Path, texto: str):
    main = (carpeta / "main_grupo27.asm").read_text(encoding="utf-8")
    lineas = [("; " + ln) if ln.strip().upper().startswith("LEA") and "programa_del_menu_completo" in ln else ln for ln in main.splitlines()]
    res = assemble([("main_grupo27.asm", "\n".join(lineas) + "\n")] + fuentes_lc10(carpeta))
    m = Machine()
    m.load(res.image)
    m.set_input(texto)
    try:
        r = m.run(5_000_000)
    except Fault as e:
        return "".join(m.out), f"Fault: {e}", m.user_count
    return r.output, (None if r.reason == "halt" else f"{r.reason}: {r.message}"), r.user_instructions


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("lc3", help="carpeta lc3-project de la cátedra")
    ap.add_argument("lc10", nargs="?", default=str(AQUI.parent / "asm" / "bench10"), help="carpeta con el puerto a LC10")
    ap.add_argument("--casos", type=int, default=40)
    ap.add_argument("--semilla", type=int, default=1)
    ap.add_argument("--solo", nargs="*", default=[], help="probar solo estas etiquetas")
    ap.add_argument("--sesiones", action="store_true", help="solo las sesiones del menú")
    ap.add_argument("--sin-sesiones", action="store_true", help="solo las subrutinas, sin las sesiones del menú")
    args = ap.parse_args(argv)

    base = Path(args.lc3).resolve()
    carpeta = Path(args.lc10).resolve()
    asm = cargar("asm_lc3_catedra", base / "assembler_LC3.py")
    sim = cargar("sim_lc3_catedra", base / "simulador.py")
    fuentes = fuentes_lc10(carpeta)
    malos = 0
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        if not args.sesiones:
            print(f"{'subrutina':44s} {'casos':>6s} {'iguales':>8s} {'descartados':>11s}   instr. LC-3 / LC10 (media)")
            for stem, etq, gen in ENTRADAS:
                if args.solo and etq not in args.solo:
                    continue
                g = random.Random(f"{args.semilla}-{etq}")
                try:
                    a, b = Lc3Runner(asm, sim, base, stem, etq, tmp), Lc10Runner(fuentes, stem, etq)
                except (AsmError, Exception) as e:
                    print(f"{stem + '-' + etq:44s}  no se pudo armar: {e}")
                    malos += 1
                    continue
                n = ok = desc = 0
                pa = pb = 0
                for _ in range(args.casos):
                    c = gen(g)
                    ra, ea = a.run(c)
                    if ra is None:
                        desc += 1
                        continue
                    rb, eb = b.run(c)
                    n += 1
                    if rb is not None and ra["regs"] == rb["regs"] and ra["out"] == rb["out"] and ra["gets"] == rb["gets"]:
                        ok += 1
                        pa += ra["steps"]
                        pb += rb["steps"]
                    else:
                        malos += 1
                        print(f"  DIFERENCIA en {etq} con {c['regs']} {c['put']} {c['stdin']!r}")
                        print(f"    LC-3: {ra}")
                        print(f"    LC10: {rb if rb is not None else eb}")
                        if malos > 12:
                            return 1
                print(f"{stem + '-' + etq:44s} {n:6d} {ok:8d} {desc:11d}   {pa // max(ok, 1):9d} / {pb // max(ok, 1):<9d}")
        if not args.sin_sesiones:
            print("\nsesiones interactivas del menú")
            for nombre, texto in SESIONES.items():
                ta, ea, sa = sesion_lc3(asm, sim, base, tmp, texto)
                tb, eb, sb = sesion_lc10(carpeta, texto)
                igual = ta == tb and ea is None and eb is None
                malos += 0 if igual else 1
                print(f"  {nombre:20s} {'igual' if igual else 'DISTINTA'}  ({len(ta)} caracteres; {sa} / {sb} instrucciones)")
                if not igual:
                    print(f"    LC-3: {ea}\n    LC10: {eb}")
                    for i, (x, y) in enumerate(zip(ta.splitlines(), tb.splitlines()), 1):
                        if x != y:
                            print(f"    línea {i}: LC-3 {x!r}  LC10 {y!r}")
                            break
    print("\nRESULTADO:", "todo coincide" if malos == 0 else f"{malos} diferencias")
    return 0 if malos == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
