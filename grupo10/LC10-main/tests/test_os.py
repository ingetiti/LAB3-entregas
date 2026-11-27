"""El sistema operativo de LC10 (lc10/os_lc10.asm): las rutinas de los TRAP se ejecutan como código y se cuentan.

El contador de instrucciones suma las del usuario y las del SO (como el contador actualizado del grupo 8 para
la LC-3: 357.505 usuario + 22.074 SO = 379.579). Acá se fijan el mapa de memoria, el costo de cada rutina y su
comportamiento (registros, banderas, fin de la entrada, dispositivos).
"""
import unittest

from lc10 import isa, system
from lc10.assembler import assemble
from lc10.session import Session
from lc10.simulator import Fault, Machine, summary_line


def correr(src, inp="", regs=None, stop_at=None, eof_fault=False, max_instr=100_000):
    res = assemble([("prog.asm", src)])
    m = Machine()
    m.eof_fault = eof_fault
    m.load(res.image)
    m.set_input(inp)
    if regs:
        m.regs[:] = regs
    r = m.run(max_instr, stop_at=res.symbols["PROG-" + stop_at.upper()] if stop_at else None)
    return m, r, res


class TestLayout(unittest.TestCase):
    def test_devices_and_routines_are_where_the_isa_says(self):
        sym = system.symbols()
        self.assertEqual((sym["KBSR"], sym["KBDR"], sym["DSR"], sym["DDR"], sym["MCR"]),
                         (isa.IO_KBSR, isa.IO_KBDR, isa.IO_DSR, isa.IO_DDR, isa.IO_MCR))
        origin, data, vectors = system.build()
        self.assertEqual(origin, isa.OS_BASE)
        self.assertLessEqual(origin + len(data), isa.IO_END)
        self.assertEqual(set(vectors), {isa.TRAP_GETC, isa.TRAP_OUT, isa.TRAP_PUTS, isa.TRAP_IN, isa.TRAP_HALT})
        for addr in vectors.values():
            self.assertTrue(isa.OS_BASE <= addr < isa.IO_BASE and addr % 2 == 0, hex(addr))

    def test_vector_table_is_installed_in_a_new_machine(self):
        m = Machine()
        for vect, addr in system.build()[2].items():
            at = isa.TRAP_TABLE + 2 * vect
            self.assertEqual(m.mem[at] | m.mem[at + 1] << 8, addr)
        self.assertEqual(m.mem[isa.TRAP_TABLE + 2 * 0x24:isa.TRAP_TABLE + 2 * 0x24 + 2], b"\x00\x00")   # sin rutina

    def test_the_system_area_does_not_overlap_the_user_stack_or_programs(self):
        self.assertGreater(isa.SYS_LO, 0xF000)          # los programas empiezan en x3000; la pila baja desde xFFFE
        self.assertLess(isa.SYS_HI, 0xFFE0)


class TestSystemAreaIsProtected(unittest.TestCase):
    def test_a_program_cannot_be_assembled_over_the_system_area(self):
        from lc10.assembler import AsmError
        for orig in ("xFB00", "xFD40", "xFDFE", "xFE00", "xF800"):
            n = 400 if orig == "xF800" else 1
            with self.assertRaises(AsmError, msg=orig) as cm:
                assemble([("p.asm", f".ORIG {orig}\nHALT\n.BLKW {n}\n.END\n")])
            self.assertIn("zona del sistema", str(cm.exception))
        assemble([("p.asm", ".ORIG xFE10\nHALT\n.END\n")])           # justo después de los dispositivos: se puede
        assemble([("p.asm", ".ORIG xFA00\nHALT\n.END\n")])           # y justo antes de la tabla

    def test_an_image_over_the_system_area_is_not_loaded(self):
        from lc10.image import Image, ImageError
        with self.assertRaises(ImageError):
            Machine().load(Image(0xFD40, b"\x00\x00"))
        Machine().load(Image(0x3000, b"\x00\x00"))


class TestTrap(unittest.TestCase):
    def test_trap_saves_the_return_address_in_r7_and_jumps_to_the_routine(self):
        m = Machine()
        m.load(assemble([("p.asm", ".ORIG x3000\nOUT\nHALT\n.END\n")]).image)
        m.regs[0] = ord("A")
        m.step()
        self.assertEqual(m.regs[7], 0x3002)
        self.assertEqual(m.pc, system.build()[2][isa.TRAP_OUT])
        self.assertEqual((m.count, m.os_count), (1, 0))      # el TRAP es del usuario; la rutina todavía no corrió

    def test_a_vector_without_routine_faults(self):
        m, r, _ = correr(".ORIG x3000\nTRAP x30\nHALT\n.END\n")
        self.assertEqual(r.reason, "fault")
        self.assertIn("TRAP x30 no implementado", r.message)
        self.assertEqual(m.regs[7], 0)                       # no se llegó a tocar R7

    def test_routines_return_with_ret_and_keep_everything_but_r7_and_r0_results(self):
        regs = [0x1111, 0x2222, 0x3333, 0x4444, 0x5555, 0x6666, 0x7777, 0x8888]
        src = ".ORIG x3000\nLEA R0, T\nPUTS\nMOVI R0, #65\nOUT\nFIN HALT\nT .STRINGZ \"ab\"\n.END\n"
        m, r, res = correr(src, regs=regs, stop_at="FIN")
        self.assertEqual(r.output, "abA")
        t = res.symbols["PROG-T"]
        self.assertEqual(m.regs, [65, 0x2222, 0x3333, 0x4444, 0x5555, 0x6666, 0x7777, res.symbols["PROG-FIN"]])
        self.assertNotEqual(t, 0)


class TestCosts(unittest.TestCase):
    """Cuántas instrucciones del SO cuesta cada llamada (la pantalla siempre está lista: cada espera da una vuelta)."""

    def os_cost(self, call, inp="", setup="", data=""):
        src = f".ORIG x3000\n{setup}{call}\nHALT\n{data}.END\n"
        _, r, _ = correr(src, inp)
        self.assertTrue(r.ok, r.message)
        return r.os_instructions - 2                         # sin HALT (MOVI + ST)

    def test_halt_costs_two(self):
        _, r, _ = correr(".ORIG x3000\nHALT\n.END\n")
        self.assertEqual((r.user_instructions, r.os_instructions, r.instructions), (1, 2, 3))

    def test_out_costs_six(self):
        self.assertEqual(self.os_cost("OUT"), 6)

    def test_getc_costs_four_and_in_ten_or_five_at_the_end_of_the_input(self):
        self.assertEqual(self.os_cost("GETC", "x"), 4)
        self.assertEqual(self.os_cost("IN", "x"), 10)         # GETC + el eco, que es OUT
        self.assertEqual(self.os_cost("IN", ""), 5)           # sin entrada: xFFFF y sin eco

    def test_puts_costs_nine_plus_six_per_character(self):
        for n in (0, 1, 2, 10, 37):
            text = "a" * n
            cost = self.os_cost("PUTS", setup="LEA R0, T\n", data=f'T .STRINGZ "{text}"\n')
            self.assertEqual(cost, 9 + 6 * n, n)

    def test_user_and_os_instructions_add_up(self):
        src = ".ORIG x3000\nLEA R0, T\nPUTS\nMOVI R0, #10\nOUT\nHALT\nT .STRINGZ \"hola\"\n.END\n"
        _, r, _ = correr(src)
        self.assertEqual((r.user_instructions, r.os_instructions), (5, (9 + 6 * 4) + 6 + 2))
        self.assertEqual(r.instructions, r.user_instructions + r.os_instructions)
        self.assertEqual(sum(r.os_histogram.values()), r.os_instructions)
        self.assertEqual(r.histogram["TRAP"], 3)

    def test_summary_line_shows_the_split(self):
        _, r, _ = correr(".ORIG x3000\nHALT\n.END\n")
        self.assertEqual(r.summary(), "1 usuario + 2 SO = 3 instrucciones · 1 palabras · x3000–x3001")
        self.assertEqual(summary_line(5, 10, 0x3000), "5 instrucciones · 5 palabras · x3000–x3009")   # sin SO: solo el total


class TestRoutines(unittest.TestCase):
    def test_out_writes_only_the_low_byte(self):
        _, r, _ = correr(".ORIG x3000\nOUT\nHALT\n.END\n", regs=[0x1241, 0, 0, 0, 0, 0, 0, 0])
        self.assertEqual(r.output, "A")

    def test_puts_writes_bytes_above_x7f_as_latin_1(self):
        src = ".ORIG x3000\nLEA R0, T\nPUTS\nHALT\nT .BYTE 0xF1, 0x41, 0\n.END\n"
        _, r, _ = correr(src)
        self.assertEqual(r.output, "ñA")

    def test_getc_returns_the_next_character_and_minus_one_at_the_end(self):
        src = ".ORIG x3000\nGETC\nADD R1, R0, #0\nGETC\nADD R2, R0, #0\nGETC\nFIN HALT\n.END\n"
        m, r, _ = correr(src, "ab", stop_at="FIN")
        self.assertEqual((m.regs[1], m.regs[2], m.regs[0]), (ord("a"), ord("b"), 0xFFFF))

    def test_in_echoes_the_character_but_not_the_end_of_the_input(self):
        _, r, _ = correr(".ORIG x3000\nIN\nIN\nHALT\n.END\n", "z")
        self.assertEqual(r.output, "z")

    def test_waiting_for_a_key_stops_without_completing_the_read_and_can_resume(self):
        res = assemble([("p.asm", ".ORIG x3000\nGETC\nOUT\nHALT\n.END\n")])
        m = Machine()
        m.eof_fault = True
        m.load(res.image)
        r = m.run(1000)
        self.assertEqual(r.reason, "fault")
        self.assertIn("no hay más caracteres disponibles en la entrada", r.message)
        self.assertEqual((r.user_instructions, r.os_instructions), (1, 0))   # el TRAP sí; la lectura pendiente, no
        m.set_input("q")                                                      # llega la tecla: se sigue desde la espera
        r = m.run(1000)
        self.assertTrue(r.ok, r.message)
        self.assertEqual(r.output, "q")
        self.assertEqual((r.user_instructions, r.os_instructions), (3, 4 + 6 + 2))

    def test_the_system_is_not_counted_in_the_user_memory_metrics(self):
        _, r, _ = correr(".ORIG x3000\nLEA R0, T\nPUTS\nHALT\nT .STRINGZ \"hi\"\n.END\n")
        self.assertEqual(r.fetched_bytes, 6)                  # LEA, PUTS, HALT: las del usuario
        self.assertEqual(r.bytes_written, 0)                  # el SO guarda sus registros en su zona
        self.assertEqual(r.outside_ranges, [])
        self.assertEqual((r.min_addr, r.max_addr), (0x3000, 0x3008))


class TestDevices(unittest.TestCase):
    def test_a_program_can_drive_the_display_and_the_machine_directly(self):
        src = """.ORIG x3000
            LD   R1, DDRP
            MOVI R0, #72
            STW  R0, R1, #0          ; DDR
            LD   R1, MCRP
            MOVI R0, #0
            STW  R0, R1, #0          ; MCR: bit 15 en 0 detiene la máquina
            MOVI R0, #1              ; no se ejecuta
            HALT
        DDRP .FILL xFE06
        MCRP .FILL xFE08
        .END"""
        m, r, _ = correr(src)
        self.assertEqual(r.output, "H")
        self.assertTrue(r.ok)
        self.assertEqual((m.regs[0], r.os_instructions), (0, 0))

    def test_status_registers_read_as_ready_and_mcr_as_running(self):
        m = Machine()
        self.assertEqual(m.rw(isa.IO_DSR), 0x8000)
        self.assertEqual(m.rw(isa.IO_KBSR), 0x8000)
        self.assertEqual(m.rw(isa.IO_MCR), 0x8000)
        self.assertEqual(m.rw(isa.IO_KBDR), 0xFFFF)           # sin entrada
        m.set_input("k")
        self.assertEqual(m.rw(isa.IO_KBDR), ord("k"))


class TestSession(unittest.TestCase):
    def sesion(self, src):
        s = Session()
        s.assemble([("prog.asm", src)])
        return s

    def test_a_trap_is_a_single_step_and_the_counter_adds_the_os(self):
        s = self.sesion(".ORIG x3000\nMOVI R0, #65\nOUT\nMOVI R0, #66\nOUT\nHALT\n.END\n")
        s.step()
        self.assertEqual(s.step(), "ready")                   # OUT: el TRAP y toda la rutina
        self.assertEqual(s.machine.pc, 0x3004)                # vuelve al usuario
        self.assertEqual((s.machine.user_count, s.machine.os_count), (2, 6))
        self.assertEqual(s.take_output(), "A")
        s.step(); s.step()
        self.assertEqual(s.step(), "halted")
        self.assertEqual(s.summary(), "5 usuario + 14 SO = 19 instrucciones · 5 palabras · x3000–x3009")
        self.assertEqual(s.location_of(s.last_pc), ("prog.asm", 6))      # la última del usuario: el HALT


if __name__ == "__main__":
    unittest.main()
