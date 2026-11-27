"""Pruebas de la lógica de la ventana (lc10/session.py), sin tkinter."""
import tempfile
import unittest
from pathlib import Path

from lc10 import isa
from lc10.assembler import AsmError, assemble
from lc10.image import Image
from lc10.session import Session

ROOT = Path(__file__).resolve().parent.parent

HOLA = """\
        .ORIG x3000
        LEA   R0, MSG
        PUTS
        HALT
MSG     .STRINGZ "Hola\\n"
        .END
"""

CONTAR = """\
        .ORIG x3000
        MOVI  R1, #3          ; línea 2
LAZO    ADD   R1, R1, #-1     ; línea 3
        BRp   LAZO            ; línea 4
        MOVI  R2, #7          ; línea 5
        ST    R2, DATO        ; línea 6
        HALT                  ; línea 7
DATO    .FILL 0
        .END
"""


def sesion(src, name="prog.asm", **kw):
    s = Session()
    s.assemble([(name, src)], **kw)
    return s


class TestLoad(unittest.TestCase):
    def test_assemble_leaves_program_ready(self):
        s = sesion(HOLA)
        self.assertEqual(s.state, "ready")
        self.assertEqual(s.machine.pc, 0x3000)
        self.assertEqual(s.machine.count, 0)

    def test_assemble_error_keeps_previous_session(self):
        s = sesion(HOLA)
        old_image = s.image
        with self.assertRaises(AsmError) as cm:
            s.assemble([("mal.asm", ".ORIG x3000\n  FOO R1\n.END\n")])
        self.assertEqual((cm.exception.file, cm.exception.line), ("mal.asm", 2))
        self.assertIs(s.image, old_image)
        self.assertEqual(s.state, "ready")

    def test_load_image_from_file_and_disassembly_listing(self):
        res = assemble([("prog.asm", CONTAR)])
        with tempfile.TemporaryDirectory() as d:
            for ext in ("hex", "bin", "dec", "bits"):
                p = Path(d) / f"p.{ext}"
                res.image.save(p, ext)
                s = Session()
                s.load_image(Image.load(p))
                self.assertEqual(s.state, "ready")
                self.assertEqual(s.machine.pc, 0x3000)
                self.assertIn("MOVI R1, #3", s.listing_lines[0])
                self.assertIsNone(s.pc_location())            # una imagen no tiene fuente
                self.assertEqual(s.run_chunk(budget_s=1), "halted")
                self.assertEqual(s.machine.regs[2], 7)

    def test_start_resets_everything(self):
        s = sesion(CONTAR)
        s.run_chunk(budget_s=1)
        self.assertEqual(s.state, "halted")
        s.start()
        self.assertEqual((s.state, s.machine.count, s.machine.regs[2], s.machine.pc), ("ready", 0, 0, 0x3000))
        self.assertEqual(s.take_output(), "")


class TestRun(unittest.TestCase):
    def test_run_to_halt_and_output(self):
        s = sesion(HOLA)
        self.assertEqual(s.run_chunk(budget_s=1), "halted")
        self.assertEqual(s.take_output(), "Hola\n")
        self.assertEqual(s.take_output(), "")                  # ya se entregó
        self.assertEqual(s.machine.user_count, 3)

    def test_output_is_incremental(self):
        s = sesion("""\
        .ORIG x3000
        MOVI R0, #65
        OUT
        MOVI R0, #66
        OUT
        HALT
        .END
""")
        s.step(); s.step()
        self.assertEqual(s.take_output(), "A")
        s.step(); s.step()
        self.assertEqual(s.take_output(), "B")

    def test_input_feeds_getc(self):
        s = sesion("""\
        .ORIG x3000
        GETC
        ADD R1, R0, #1
        HALT
        .END
""", input_text="a")
        s.run_chunk(budget_s=1)
        self.assertEqual(s.machine.regs[1], ord("a") + 1)

    def test_step_reports_changes(self):
        s = sesion(CONTAR)
        snap = s.snapshot()
        s.step()                                               # MOVI R1, #3
        ch = s.diff(snap)
        self.assertEqual(ch.regs, {1})
        self.assertEqual(ch.flags, {"Z", "P"})                 # Z=1 -> P=1
        self.assertEqual((ch.pc_from, ch.count), (0x3000, 1))
        snap = s.snapshot()
        s.step()                                               # ADD R1, R1, #-1 -> 2
        self.assertEqual(s.diff(snap).regs, {1})
        self.assertEqual(s.diff(snap).flags, {"C"})            # 3 + (-1) deja acarreo

    def test_changed_bytes_in_window(self):
        s = sesion(CONTAR)
        self.assertEqual(s.run_chunk(s.breakpoint_addrs({("prog.asm", 6)}), budget_s=1), "breakpoint")
        snap = s.snapshot()                                    # justo antes de ST R2, DATO
        s.step()                                               # ST R2, DATO
        dato = s.asm.symbols["PROG-DATO"]
        self.assertEqual(s.changed_bytes(snap, dato - 2, dato + 4), {dato})   # 7 = 0x0007: solo cambia el byte bajo
        self.assertEqual(s.changed_bytes(snap, 0x3000, 0x3004), set())

    def test_step_on_finished_program_does_nothing(self):
        s = sesion(HOLA)
        s.run_chunk(budget_s=1)
        n = s.machine.count
        self.assertEqual(s.step(), "halted")
        self.assertEqual(s.run_chunk(), "halted")
        self.assertEqual(s.machine.count, n)

    def test_last_pc_tracks_the_instruction_just_executed(self):
        s = sesion(CONTAR)
        self.assertIsNone(s.last_pc)
        s.step()
        self.assertEqual(s.last_pc, 0x3000)
        s.run_chunk(budget_s=1)                                # termina en el HALT
        self.assertEqual(s.state, "halted")
        self.assertEqual(s.pc_location(), None)                # el PC ya pasó el HALT (dato)
        self.assertEqual(s.location_of(s.last_pc), ("prog.asm", 7))

    def test_last_pc_after_fault_is_the_faulting_instruction(self):
        s = sesion("""\
        .ORIG x3000
        MOVI R1, #1
        JMP  R1
        .END
""")
        s.run_chunk(budget_s=1)
        self.assertEqual(s.state, "fault")
        self.assertEqual(s.last_pc, 0x3002)

    def test_fault_state_and_message(self):
        s = sesion("""\
        .ORIG x3000
        MOVI R1, #1
        JMP  R1
        .END
""")
        self.assertEqual(s.run_chunk(budget_s=1), "fault")
        self.assertEqual(s.state, "fault")
        self.assertIn("impar", s.message)
        self.assertEqual(s.step(), "fault")

    def test_infinite_loop_returns_running_and_can_continue(self):
        s = sesion("""\
        .ORIG x3000
AQUI    BR AQUI
        .END
""")
        self.assertEqual(s.run_chunk(budget_s=0.01), "running")
        n = s.machine.count
        self.assertGreater(n, 100)
        self.assertEqual(s.run_chunk(budget_s=0.01), "running")
        self.assertGreater(s.machine.count, n)
        self.assertEqual(s.state, "ready")

    def test_instruction_limit_stops_at_the_exact_count_and_can_continue(self):
        s = sesion("""\
        .ORIG x3000
AQUI    BR AQUI
        .END
""")
        self.assertEqual(s.run_chunk(budget_s=5, limit=1000), "limit")
        self.assertEqual(s.machine.count, 1000)
        self.assertEqual(s.state, "ready")
        self.assertEqual(s.run_chunk(budget_s=5, limit=1000), "limit")      # ya está en el tope: no ejecuta nada
        self.assertEqual(s.machine.count, 1000)
        self.assertEqual(s.run_chunk(budget_s=5, limit=1301), "limit")      # no es múltiplo del bloque de 256
        self.assertEqual(s.machine.count, 1301)
        self.assertEqual(s.run_chunk(budget_s=0.01), "running")             # sin límite sigue como siempre
        self.assertGreater(s.machine.count, 1301)

    def test_max_steps_runs_exactly_that_many_instructions_and_can_continue(self):
        s = sesion("""\
        .ORIG x3000
AQUI    BR AQUI
        .END
""")
        self.assertEqual(s.run_chunk(budget_s=5, max_steps=5), "running")
        self.assertEqual(s.machine.count, 5)
        self.assertEqual(s.run_chunk(budget_s=5, max_steps=3, check_first=True), "running")
        self.assertEqual(s.machine.count, 8)
        self.assertEqual(s.run_chunk(budget_s=5, max_steps=300), "running")      # más que el bloque de 256
        self.assertEqual(s.machine.count, 308)
        self.assertEqual(s.state, "ready")

    def test_max_steps_does_not_hide_halt_or_the_instruction_limit(self):
        s = sesion("""\
        .ORIG x3000
        MOVI R0, #1
        HALT
        .END
""")
        self.assertEqual(s.run_chunk(budget_s=1, max_steps=10), "halted")
        self.assertEqual(s.machine.user_count, 2)
        t = sesion("""\
        .ORIG x3000
AQUI    BR AQUI
        .END
""")
        self.assertEqual(t.run_chunk(budget_s=1, limit=4, max_steps=10), "limit")
        self.assertEqual(t.machine.count, 4)

    def test_a_program_that_halts_before_the_limit_reports_halted(self):
        s = sesion("""\
        .ORIG x3000
        MOVI R0, #1
        HALT
        .END
""")
        self.assertEqual(s.run_chunk(budget_s=1, limit=1000), "halted")
        self.assertEqual(s.machine.user_count, 2)
        self.assertEqual(s.state, "halted")


class TestSourceMap(unittest.TestCase):
    def test_pc_location_follows_execution(self):
        s = sesion(CONTAR)
        self.assertEqual(s.pc_location(), ("prog.asm", 2))
        s.step()
        self.assertEqual(s.pc_location(), ("prog.asm", 3))
        s.step(); s.step()
        self.assertEqual(s.pc_location(), ("prog.asm", 3))     # vuelve a LAZO

    def test_addr_of_line_only_for_instructions(self):
        s = sesion(CONTAR)
        self.assertEqual(s.addr_of_line("prog.asm", 3), 0x3002)
        self.assertIsNone(s.addr_of_line("prog.asm", 8))       # .FILL: es dato
        self.assertIsNone(s.addr_of_line("prog.asm", 1))       # .ORIG
        self.assertIsNone(s.addr_of_line("prog.asm", 99))

    def test_padding_does_not_break_the_map(self):
        s = sesion("""\
        .ORIG x3000
        LEA  R0, TXT
        PUTS
        HALT
TXT     .STRINGZ "abc"      ; 4 bytes: queda alineado
ODD     .STRINGZ "ab"       ; 3 bytes: deja un byte suelto
        MOVI R1, #1         ; relleno antes de esta instrucción
        .END
""")
        self.assertEqual(s.asm.pad_bytes, 1)
        self.assertEqual(s.location_of(s.addr_of_line("prog.asm", 7)), ("prog.asm", 7))

    def test_modules_map_to_their_own_files(self):
        main = """\
        .ORIG x3000
        .EXTERNAL DIVISION-DIV_LONG
        LD   R0, A
        LD   R1, B
        JSR  DIVISION-DIV_LONG
        HALT
A       .FILL #1408
B       .FILL #512
        .END
"""
        div = (ROOT / "asm" / "division.asm").read_text(encoding="utf-8")
        s = Session()
        s.assemble([("main.asm", main), ("division.asm", div)])
        self.assertEqual(s.pc_location(), ("main.asm", 3))
        files = set()
        while s.step() == "ready":
            files.add(s.pc_location()[0])
        self.assertEqual(files, {"main.asm", "division.asm"})
        self.assertEqual(isa.to_s16(s.machine.regs[0]), 704)    # 5,5 / 2 = 2,75 en Q7.8

    def test_breakpoint_addrs(self):
        s = sesion(CONTAR)
        self.assertEqual(s.breakpoint_addrs({("prog.asm", 5), ("prog.asm", 8), ("otro.asm", 1)}), {0x3006})

    def test_listing_line_for_address(self):
        s = sesion(CONTAR)
        i = s.listing_line_for(0x3002)
        self.assertIn("LAZO", s.listing_lines[i])
        self.assertIsNone(s.listing_line_for(0x2FFE))


class TestBreakpoints(unittest.TestCase):
    def test_stops_before_the_instruction_and_resumes(self):
        s = sesion(CONTAR)
        bp = s.breakpoint_addrs({("prog.asm", 5)})              # MOVI R2, #7
        self.assertEqual(s.run_chunk(bp, budget_s=1), "breakpoint")
        self.assertEqual(s.machine.pc, 0x3006)
        self.assertEqual(s.machine.regs[2], 0)                  # todavía no se ejecutó
        self.assertEqual(s.run_chunk(bp, budget_s=1), "halted")  # continúa sin quedarse trabado
        self.assertEqual(s.machine.regs[2], 7)

    def test_loop_breakpoint_hits_every_iteration(self):
        s = sesion(CONTAR)
        bp = s.breakpoint_addrs({("prog.asm", 3)})              # ADD dentro del lazo
        hits = 0
        while True:
            r = s.run_chunk(bp, budget_s=1)
            if r != "breakpoint":
                break
            hits += 1
        self.assertEqual((r, hits), ("halted", 3))              # el lazo da 3 vueltas

    def test_a_chunk_cut_right_before_a_breakpoint_does_not_skip_it(self):
        """Ejecutando de a una instrucción (como a velocidad limitada), el punto de parada tiene que saltar."""
        s = sesion(CONTAR)
        bp = s.breakpoint_addrs({("prog.asm", 5)})              # MOVI R2, #7
        r, first = "running", True
        while r == "running":
            r = s.run_chunk(bp, max_steps=1, check_first=not first)
            first = False
        self.assertEqual(r, "breakpoint")
        self.assertEqual(s.machine.pc, 0x3006)
        self.assertEqual(s.machine.regs[2], 0)                  # todavía no se ejecutó
        self.assertEqual(s.run_chunk(bp, max_steps=1), "running")    # arrancar desde el punto de parada sí lo pasa
        self.assertEqual(s.machine.regs[2], 7)

    def test_without_check_first_the_first_instruction_always_runs(self):
        s = sesion(CONTAR)
        bp = s.breakpoint_addrs({("prog.asm", 5)})
        while s.machine.pc != 0x3006:
            s.step()
        self.assertEqual(s.run_chunk(bp, max_steps=1), "running")    # comportamiento de siempre: sale del punto de parada
        self.assertEqual(s.machine.regs[2], 7)
        t = sesion(CONTAR)
        while t.machine.pc != 0x3006:
            t.step()
        self.assertEqual(t.run_chunk(bp, max_steps=1, check_first=True), "breakpoint")
        self.assertEqual(t.machine.regs[2], 0)

    def test_breakpoint_on_first_instruction_does_not_block_start(self):
        s = sesion(CONTAR)
        bp = s.breakpoint_addrs({("prog.asm", 2)})
        self.assertEqual(s.run_chunk(bp, budget_s=1), "halted")


class TestTraceAndMetrics(unittest.TestCase):
    def test_trace_only_when_enabled_and_is_trimmed(self):
        s = sesion(CONTAR)
        s.run_chunk(budget_s=1)
        self.assertEqual(s.trace_text(), "")
        s.start()
        s.set_trace(True)
        s.run_chunk(budget_s=1)
        self.assertIn("MOVI R1, #3", s.trace_text())
        s2 = sesion("""\
        .ORIG x3000
AQUI    BR AQUI
        .END
""")
        s2.trace_keep = 50
        s2.set_trace(True)
        s2.run_chunk(budget_s=0.05)
        self.assertLessEqual(len(s2.machine.trace_log), 100 + 256)

    def test_metrics_text(self):
        s = sesion(CONTAR)
        self.assertIn("no terminó", s.metrics_text())
        s.run_chunk(budget_s=1)
        t = s.metrics_text()
        self.assertIn("terminó con HALT", t)
        self.assertIn(f"Instrucciones ejecutadas: {s.machine.count}", t)
        self.assertIn("ADD", t)
        self.assertIn("bytes de datos escritos:         2", t)

    def test_symbols_text(self):
        s = sesion(CONTAR)
        self.assertIn("PROG-LAZO", s.symbols_text())
        s.load_image(s.image)
        self.assertIn("sin símbolos", s.symbols_text())


if __name__ == "__main__":
    unittest.main()
