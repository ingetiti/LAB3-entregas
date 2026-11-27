"""Línea de comandos: el simulador con entradas y el resumen como la cátedra, y `benchmark.py`."""
import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from lc10 import simulator
from lc10.assembler import assemble
from lc10.simulator import Machine, summary_line

ROOT = Path(__file__).resolve().parent.parent
ECO = """\
        .ORIG x3000
        GETC
        OUT
        GETC
        OUT
        HALT
        .END
"""


def correr_cli(argv):
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
        code = simulator.main(argv)
    return code, out.getvalue()


def cargar_benchmark():
    import importlib.util
    spec = importlib.util.spec_from_file_location("benchmark_lc10", ROOT / "benchmark.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestSummary(unittest.TestCase):
    def test_same_format_as_the_course_simulator(self):
        self.assertEqual(summary_line(17791, 10704, 0x3000), "17.791 instrucciones · 5352 palabras · x3000–x59CF")
        self.assertEqual(summary_line(0, 0, None), "0 instrucciones · 0 palabras")
        # con el contador actualizado del grupo 8: "357.505 usuario + 22.074 SO = 379.579 instrucciones"
        self.assertEqual(summary_line(26_723, 9926, 0x3000, 10_901),
                         "15.822 usuario + 10.901 SO = 26.723 instrucciones · 4963 palabras · x3000–x56C5")

    def test_result_carries_origin_and_size(self):
        res = assemble([("eco.asm", ECO)])
        m = Machine()
        m.load(res.image)
        m.set_input("ab")
        r = m.run()
        self.assertEqual(r.summary(), "5 usuario + 22 SO = 27 instrucciones · 5 palabras · x3000–x3009")


class TestSimulatorCli(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.hex = self.tmp / "eco.hex"
        assemble([("eco.asm", ECO)]).image.save(self.hex)

    def test_input_with_escapes_and_accents(self):
        code, out = correr_cli([str(self.hex), "--input", "ñ\\n", "--no-regs"])
        self.assertEqual(code, 0)
        self.assertIn("--- salida ---\nñ\n", out)
        self.assertIn("LC10 · 5 usuario + 22 SO = 27 instrucciones · 5 palabras · x3000–x3009", out)

    def test_input_file(self):
        f = self.tmp / "teclas.txt"
        f.write_text("xy", encoding="utf-8")
        code, out = correr_cli([str(self.hex), "--input-file", str(f), "--no-regs"])
        self.assertEqual(code, 0)
        self.assertIn("xy", out)

    def test_running_out_of_input_stops_like_the_course_simulator(self):
        code, out = correr_cli([str(self.hex), "--input", "a", "--no-regs"])
        self.assertEqual(code, 2)
        self.assertIn("no hay más caracteres disponibles en la entrada", out)
        # GETC, OUT y el GETC que se queda esperando: 3 TRAP; del SO, GETC (4) y OUT (6) completos; la lectura
        # del estado del teclado que no se completó no cuenta
        self.assertIn("LC10 · 3 usuario + 10 SO = 13 instrucciones", out)

    def test_running_out_of_input_can_return_minus_one(self):
        code, out = correr_cli([str(self.hex), "--input", "a", "--fin-entrada", "menos1", "--no-regs"])
        self.assertEqual(code, 0)

    def test_exit_code_3_on_instruction_limit(self):
        code, out = correr_cli([str(self.hex), "--input", "ab", "--max", "2", "--no-regs"])
        self.assertEqual(code, 3)


class TestBenchmarkScript(unittest.TestCase):
    def setUp(self):
        self.mod = cargar_benchmark()
        self.tmp = Path(tempfile.mkdtemp())

    def correr(self, argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            code = self.mod.main(argv)
        return code, out.getvalue()

    def test_default_run_prints_the_summary_and_saves_an_image(self):
        img = self.tmp / "programa.hex"
        code, out = self.correr(["-o", str(img)])
        self.assertEqual(code, 0)
        self.assertIn("LC10 · 15.822 usuario + 10.901 SO = 26.723 instrucciones · 4963 palabras · x3000–x56C5", out)
        code, out = correr_cli([str(img), "--no-regs"])            # la imagen la corre el simulador solo
        self.assertEqual(code, 0)
        self.assertIn("LC10 · 15.822 usuario + 10.901 SO = 26.723 instrucciones · 4963 palabras · x3000–x56C5", out)

    def test_main_in_lc3_syntax_without_commas_assembles_as_is(self):
        texto = (ROOT / "asm" / "opt10" / "main_grupo27.asm").read_text(encoding="utf-8").replace(",", " ")
        principal = self.tmp / "main_grupo27.asm"
        principal.write_text(texto.replace(".FILL x3396", ".FILL x0100"), encoding="utf-8")
        code, out = self.correr([str(principal)])
        self.assertEqual(code, 0)
        self.assertIn("LC10 · ", out)

    def test_interactive_mode_reads_the_keys(self):
        code, out = self.correr(["--interactivo", "--entrada", "7213.265625\\n-7.23828125\\n d"])
        self.assertEqual(code, 0)                                  # "d" sale del menú: termina con HALT
        self.assertIn("(Q7.8) -96.0234375", out)                   # 13,265625 * -7,23828125 en Q7.8 (Booth)
        code, out = self.correr(["--interactivo", "--entrada", "72"])
        self.assertEqual(code, 2)
        self.assertIn("no hay más caracteres disponibles en la entrada", out)

    def test_automatic_block_detection(self):
        texto = "        LEA   R0, programa_del_menu_completo; <- ptr\n        LD R1, X\n"
        self.assertTrue(self.mod.sin_modo_automatico(texto).startswith(";"))


if __name__ == "__main__":
    unittest.main()
