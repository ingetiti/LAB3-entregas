"""El benchmark del curso en LC10: misma salida que la línea base LC-3 y las cifras informadas.

No necesita la carpeta de la cátedra: la salida de referencia está guardada en
`bench/lc3_baseline_salida.txt` (se generó con el simulador de la cátedra, ver `bench/lc3_baseline.py`).
Si se cambia un módulo de `asm/opt10` y el texto impreso o las cifras cambian, esta prueba falla.
"""
import unittest
from pathlib import Path

from lc10.assembler import assemble
from lc10.simulator import Machine

ROOT = Path(__file__).resolve().parent.parent
REFERENCIA = ROOT / "bench" / "lc3_baseline_salida.txt"
PRINCIPAL = "main_grupo27.asm"


def correr(carpeta: Path):
    nombres = [PRINCIPAL] + sorted(p.name for p in carpeta.glob("*.asm") if p.name != PRINCIPAL)
    res = assemble([(n, (carpeta / n).read_text(encoding="utf-8")) for n in nombres])
    m = Machine()
    m.load(res.image)
    r = m.run(5_000_000)
    return res, r


def referencia() -> str:
    texto = REFERENCIA.read_text(encoding="utf-8")
    return texto[:-len("\nHALT\n")] if texto.endswith("\nHALT\n") else texto   # el simulador de la cátedra agrega HALT


class TestBenchmark(unittest.TestCase):
    def test_optimized_port_prints_the_lc3_output_with_the_reported_figures(self):
        res, r = correr(ROOT / "asm" / "opt10")
        self.assertEqual(r.reason, "halt", r.message)
        self.assertEqual(r.output, referencia())
        self.assertEqual(r.user_instructions, 15_822)
        self.assertEqual(r.os_instructions, 10_901)               # las rutinas de TRAP: 133 PUTS (1541 caracteres), 76 OUT, HALT
        self.assertEqual(r.instructions, 26_723)                  # usuario + SO
        self.assertEqual(len(res.image.data) // 2, 4_963)

    def test_push_pop_keep_the_stack_balanced(self):
        """Cada POP encuentra el marco de su PUSH y la pila termina donde empezó (R6 = 0)."""
        from lc10 import isa
        res, _ = correr(ROOT / "asm" / "opt10")
        from lc10.simulator import Machine
        m = Machine(); m.load(res.image)
        frames, pushes = [], 0
        while not m.halted:
            w = m.mem[m.pc] | m.mem[m.pc + 1] << 8
            name, f = isa.decode(w)
            sp = m.regs[6]
            m.step()
            if name == "PUSH":
                frames.append(m.regs[6]); pushes += 1
            elif name == "POP":
                self.assertTrue(frames, "POP sin PUSH")
                self.assertEqual(frames.pop(), sp, "el POP no encuentra el marco de su PUSH")
        self.assertEqual(frames, [])
        self.assertEqual(m.regs[6], 0)
        self.assertGreater(pushes, 100)

    def test_direct_port_prints_the_same_output(self):
        res, r = correr(ROOT / "asm" / "bench10")
        self.assertEqual(r.reason, "halt", r.message)
        self.assertEqual(r.output, referencia())
        self.assertEqual(r.user_instructions, 358_481)
        self.assertEqual(r.os_instructions, 10_901)
        self.assertEqual(r.instructions, 369_382)
        self.assertEqual(len(res.image.data) // 2, 6_896)


if __name__ == "__main__":
    unittest.main()
