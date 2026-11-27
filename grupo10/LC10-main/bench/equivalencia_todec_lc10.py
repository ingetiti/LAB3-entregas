"""TODEC en LC10 (asm/opt10/g27_todec.asm) contra el modelo exacto de las cuentas del original.

    python bench/equivalencia_todec_lc10.py [asm/opt10] [--parte K/N]

Con --parte K/N (K de 0 a N-1) se recorre solo cada N-esimo caso, empezando por el K-esimo: correr las N
partes equivale a la prueba completa (sirve para repartirla en varias tandas o procesos).

Usa `modelo()` de `bench/equivalencia_todec.py`, que esa otra prueba contrasta con el módulo real en el
simulador de la cátedra. Acá se recorre, sin muestreo:
  * las 65.536 fracciones, con entero positivo (formato 4, con ceros a la derecha) y negativo (formato 0),
    y cada fracción también con formato 7 y entero 0;
  * los 65.536 enteros, con fracción 0 y con una fracción fija, y los 8 formatos.
Comprueba además que R0 a R5 y R7 se preserven y que no se escriba fuera de los 17 bytes del buffer (dentro
de ellos, después del 0 final, el módulo puede dejar dígitos sobrantes: es memoria suya).
"""
import importlib.util
import random
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent))
from lc10.assembler import assemble  # noqa: E402
from lc10.simulator import Machine  # noqa: E402

BUF = 0x7000


def cargar(ruta):
    spec = importlib.util.spec_from_file_location("eq_todec", ruta)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    parte, partes = 0, 1
    if "--parte" in sys.argv:
        parte, partes = (int(x) for x in sys.argv[sys.argv.index("--parte") + 1].split("/"))
        args = [a for a in args if a != sys.argv[sys.argv.index("--parte") + 1]]
    carpeta = Path(args[0] if args else AQUI.parent / "asm" / "opt10")
    modelo = cargar(AQUI / "equivalencia_todec.py").modelo
    fuente = (carpeta / "g27_todec.asm").read_text(encoding="utf-8")
    main_asm = ".ORIG x3000\n.EXTERNAL G27_TODEC-TODEC\nENTRY .FILL G27_TODEC-TODEC\nHLT HALT\n.END\n"
    res = assemble([("t_main.asm", main_asm), ("g27_todec.asm", fuente)])
    entrada = int.from_bytes(res.image.data[0:2], "little")
    base = Machine()
    base.load(res.image)

    malos, pasos, no_preserva, fuera, n = [], [], 0, 0, 0
    visto = [0]

    def probar(e, f, fmt):
        nonlocal no_preserva, fuera, n
        visto[0] += 1
        if visto[0] % partes != parte:
            return
        m = Machine()
        m.load(res.image)
        for i in range(24):
            m.mem[BUF + i] = 0xAA                           # centinela: detecta escrituras de más
        m.regs[:] = [e & 0xFFFF, f, BUF, fmt, 0x4444, 0x5555, 0xFE00, 0x3002]
        m.pc = entrada
        r = m.run(10_000, stop_at=0x3002)                   # se detiene al volver, antes del HALT del SO
        assert r.reason == "halt", (e, f, fmt, r.message)
        txt = ""
        i = 0
        while m.mem[BUF + i]:
            txt += chr(m.mem[BUF + i])
            i += 1
        esperado = modelo(e & 0xFFFF, f, fmt)
        pasos.append(r.user_instructions)
        n += 1
        if m.regs[:8] != [e & 0xFFFF, f, BUF, fmt, 0x4444, 0x5555, 0xFE00, 0x3002]:
            no_preserva += 1
        if i > 16 or any(m.mem[BUF + k] != 0xAA for k in range(17, 24)):
            fuera += 1
        if txt != esperado:
            malos.append((e, f, fmt, txt, esperado))

    for f in range(65536):
        probar(7, f, 4)
        probar(-7, f, 0)
        probar(0, f, 7)
    azar = random.Random(1)
    for e in range(65536):
        probar(e, 0, azar.randrange(8))
        probar(e, azar.randrange(1, 65536), azar.randrange(8))
    for fmt in range(8):
        for e in (0, 1, 9, 10, 99, 100, 999, 1000, 9999, 10000, 32767, 32768, 65535, 55536, 33000):
            for f in (0, 1, 32768, 65535):
                probar(e, f, fmt)

    print(f"parte {parte}/{partes} | llamadas probadas: {n} | distintas del modelo exacto: {len(malos)} | "
          f"registros sin preservar: {no_preserva} | escrituras fuera del buffer de 17 bytes: {fuera}")
    print(f"instrucciones por llamada (TODEC ... RET): mín {min(pasos)}, máx {max(pasos)}, "
          f"promedio {sum(pasos) / len(pasos):.0f}")
    for x in malos[:10]:
        print("  e=%d f=%d fmt=%d: LC10 %r, modelo %r" % x)
    return 1 if malos or no_preserva or fuera else 0


if __name__ == "__main__":
    raise SystemExit(main())
