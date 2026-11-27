"""Seno de Taylor en LC10 (asm/opt10/g21_senotaylor_subrutina.asm) contra las cuentas exactas del original.

    python bench/equivalencia_seno_lc10.py [asm/opt10]

Prueba LOS 65.536 valores posibles de R0 (no una muestra): compara R0 con `modelo()` de
`bench/equivalencia_seno.py` (las cuentas con enteros del módulo LC-3 de la cátedra, que esa otra prueba
verifica contra el módulo real en el simulador de la cátedra para 0..3699 y 4 ángulos fuera de rango),
y comprueba que R1 a R5, R6 y R7 queden como estaban. Informa instrucciones por llamada.
"""
import importlib.util
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent))
from lc10.assembler import assemble  # noqa: E402
from lc10.simulator import Machine  # noqa: E402


def cargar(ruta):
    spec = importlib.util.spec_from_file_location("eq_seno", ruta)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    carpeta = Path(sys.argv[1] if len(sys.argv) > 1 else AQUI.parent / "asm" / "opt10")
    modelo = cargar(AQUI / "equivalencia_seno.py").modelo
    fuente = (carpeta / "g21_senotaylor_subrutina.asm").read_text(encoding="utf-8")
    main_asm = ".ORIG x3000\n.EXTERNAL G21_SENOTAYLOR_SUBRUTINA-CALCULAR_SENO\nENTRY .FILL G21_SENOTAYLOR_SUBRUTINA-CALCULAR_SENO\nHLT HALT\n.END\n"
    res = assemble([("t_main.asm", main_asm), ("g21_senotaylor_subrutina.asm", fuente)])
    entrada = int.from_bytes(res.image.data[0:2], "little")
    malos, pasos, no_preserva = [], [], 0
    for ang in range(65536):
        m = Machine()
        m.load(res.image)
        m.regs[:] = [ang, 0x1111, 0x2222, 0x3333, 0x4444, 0x5555, 0xFE00, 0x3002]
        m.pc = entrada
        r = m.run(10_000, stop_at=0x3002)                      # se detiene al volver, antes del HALT del SO
        assert r.reason == "halt", (ang, r.reason, r.message)
        pasos.append(r.user_instructions)
        if m.regs[0] != modelo(ang):
            malos.append((ang, m.regs[0], modelo(ang)))
        if m.regs[1:8] != [0x1111, 0x2222, 0x3333, 0x4444, 0x5555, 0xFE00, 0x3002]:
            no_preserva += 1
    print(f"valores de R0 probados: 65536 | distintos del modelo exacto: {len(malos)} | "
          f"sin preservar R1-R5/R6/R7: {no_preserva}")
    print(f"instrucciones por llamada (CALCULAR_SENO ... RET): mín {min(pasos)}, máx {max(pasos)}, "
          f"ángulo 600: {pasos[600]}")
    for x in malos[:10]:
        print("  R0=%d: LC10 %d, modelo %d" % x)
    return 1 if malos or no_preserva else 0


if __name__ == "__main__":
    raise SystemExit(main())
