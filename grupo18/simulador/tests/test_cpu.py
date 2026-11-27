"""Pruebas de simulator/cpu.py y simulator/traps.py (ejecutar desde Lab3C).

Los programas se arman a mano con constructores de instrucciones propios
(independientes del decodificador) y se cargan en START = 0x3000.
"""

import io
import unittest

from simulator.cpu import (
    CPU,
    EXECUTION_ERRORS,
    CPUHaltedError,
    ExecutionLimitError,
    MisalignedAddressError,
)
from simulator.decoder import DecodedInstruction, InvalidInstructionError
from simulator.memory import Memory, MemoryAccessError
from simulator.registers import Registers
from simulator.traps import ConsoleIO, UnknownTrapError

START = 0x3000
N, Z, P = 0b100, 0b010, 0b001          # máscaras NZP de BR (escritas a mano)

OPCODES = {
    "ADD": 0b00000, "SUB": 0b00001, "AND": 0b00010, "OR": 0b00011,
    "XOR": 0b00100, "NOT": 0b00101, "SHL": 0b00110, "SHR": 0b00111,
    "SAR": 0b01000, "CMP": 0b01001, "LDW": 0b01010, "STW": 0b01011,
    "LDBL": 0b01100, "LDBH": 0b01101, "STBL": 0b01110, "STBH": 0b01111,
    "BR": 0b10000, "JSR": 0b10001, "JMP": 0b10010, "LEA": 0b10011,
    "LDI": 0b10100, "STI": 0b10101, "TRAP": 0b10110, "NOP": 0b10111,
    "HALT": 0b11000, "JSRR": 0b11001,
}


# ----------------------------------------------------------------------
# Constructores de instrucciones (mini ensamblador solo para las pruebas)
# ----------------------------------------------------------------------
def _imm4(value):
    assert -8 <= value <= 7
    return value & 0xF


def _a(mnemonic, dr, sr1, mode, op2):
    return (OPCODES[mnemonic] << 11) | (dr << 8) | (sr1 << 5) | (mode << 4) | op2


def ADD(dr, sr1, sr2): return _a("ADD", dr, sr1, 0, sr2)
def ADDI(dr, sr1, imm): return _a("ADD", dr, sr1, 1, _imm4(imm))
def SUB(dr, sr1, sr2): return _a("SUB", dr, sr1, 0, sr2)
def SUBI(dr, sr1, imm): return _a("SUB", dr, sr1, 1, _imm4(imm))
def AND(dr, sr1, sr2): return _a("AND", dr, sr1, 0, sr2)
def ANDI(dr, sr1, imm): return _a("AND", dr, sr1, 1, _imm4(imm))
def OR(dr, sr1, sr2): return _a("OR", dr, sr1, 0, sr2)
def XOR(dr, sr1, sr2): return _a("XOR", dr, sr1, 0, sr2)
def XORI(dr, sr1, imm): return _a("XOR", dr, sr1, 1, _imm4(imm))
def NOT(dr, sr1): return _a("NOT", dr, sr1, 0, 0)
def CMP(sr1, sr2): return _a("CMP", 0, sr1, 0, sr2)
def CMPI(sr1, imm): return _a("CMP", 0, sr1, 1, _imm4(imm))


def _shift(mnemonic, dr, sr1, amount):
    assert 0 <= amount <= 15
    return _a(mnemonic, dr, sr1, 1, amount)


def SHL(dr, sr1, n): return _shift("SHL", dr, sr1, n)
def SHR(dr, sr1, n): return _shift("SHR", dr, sr1, n)
def SAR(dr, sr1, n): return _shift("SAR", dr, sr1, n)


def _mem(mnemonic, reg, base, offset):
    assert -16 <= offset <= 15
    return (OPCODES[mnemonic] << 11) | (reg << 8) | (base << 5) | (offset & 0x1F)


def LDW(reg, base, off): return _mem("LDW", reg, base, off)
def STW(reg, base, off): return _mem("STW", reg, base, off)
def LDBL(reg, base, off): return _mem("LDBL", reg, base, off)
def LDBH(reg, base, off): return _mem("LDBH", reg, base, off)
def STBL(reg, base, off): return _mem("STBL", reg, base, off)
def STBH(reg, base, off): return _mem("STBH", reg, base, off)
def LDI(reg, base, off): return _mem("LDI", reg, base, off)
def STI(reg, base, off): return _mem("STI", reg, base, off)


def BR(nzp, offset):
    assert -128 <= offset <= 127
    return (OPCODES["BR"] << 11) | (nzp << 8) | (offset & 0xFF)


def JSR(offset):
    assert -1024 <= offset <= 1023
    return (OPCODES["JSR"] << 11) | (offset & 0x7FF)


def JMP(base): return (OPCODES["JMP"] << 11) | (base << 8)
def JSRR(base): return (OPCODES["JSRR"] << 11) | (base << 8)


def LEA(dr, offset):
    assert -128 <= offset <= 127
    return (OPCODES["LEA"] << 11) | (dr << 8) | (offset & 0xFF)


def TRAP(vector): return (OPCODES["TRAP"] << 11) | (vector << 3)
def NOP(): return OPCODES["NOP"] << 11
def HALT(): return OPCODES["HALT"] << 11


# ----------------------------------------------------------------------
# Ayudantes
# ----------------------------------------------------------------------
def to_bytes(words):
    """Palabras de 16 bits -> bytes Little Endian."""
    out = bytearray()
    for word in words:
        out += word.to_bytes(2, "little")
    return bytes(out)


def make_cpu(program, data=b"", input_text=""):
    """CPU con el programa cargado en START y E/S sobre StringIO."""
    cpu = CPU(io=ConsoleIO(stdin=io.StringIO(input_text), stdout=io.StringIO()))
    cpu.load_program(to_bytes(program) + data, START)
    return cpu


def output(cpu):
    return cpu.io.stdout.getvalue()


def flags(cpu):
    n, z, p = cpu.registers.condition_codes
    assert n + z + p == 1, "debe haber exactamente una bandera activa"
    return "N" if n else ("Z" if z else "P")


def run_one(instruction, regs=None):
    """Carga una instrucción, fija registros, ejecuta un step() y devuelve la CPU."""
    cpu = make_cpu([instruction])
    for index, value in (regs or {}).items():
        cpu.registers.write(index, value)
    cpu.step()
    return cpu


def put_string(cpu, address, text):
    for offset, char in enumerate(text):
        cpu.memory.write_byte(address + offset, ord(char))
    cpu.memory.write_byte(address + len(text), 0)


# ----------------------------------------------------------------------
# 1. Inicialización y carga
# ----------------------------------------------------------------------
class TestInitializationAndLoading(unittest.TestCase):

    def test_initial_state(self):
        cpu = CPU()
        self.assertEqual(cpu.registers.values(), (0,) * 8)
        self.assertEqual(cpu.registers.pc, 0)
        self.assertFalse(cpu.halted)
        self.assertIsNone(cpu.halt_reason)
        self.assertEqual(cpu.instruction_count, 0)
        self.assertEqual(cpu.memory_used, 0)

    def test_uses_injected_components(self):
        mem, regs = Memory(), Registers()
        console = ConsoleIO(io.StringIO(""), io.StringIO())
        cpu = CPU(memory=mem, registers=regs, io=console)
        self.assertIs(cpu.memory, mem)
        self.assertIs(cpu.registers, regs)
        self.assertIs(cpu.io, console)

    def test_load_program_is_little_endian_and_sets_pc(self):
        cpu = CPU()
        cpu.load_program(b"\x34\x12\x78\x56", START)
        self.assertEqual(cpu.memory.read_word(START), 0x1234)
        self.assertEqual(cpu.memory.read_word(START + 2), 0x5678)
        self.assertEqual(cpu.registers.pc, START)
        self.assertEqual(cpu.memory_used, 4)

    def test_load_program_without_changing_pc(self):
        cpu = CPU()
        cpu.load_program(b"\x01\x02", 0x4000, set_pc=False)
        self.assertEqual(cpu.registers.pc, 0)
        self.assertEqual(cpu.memory.read_byte(0x4000), 0x01)

    def test_load_program_that_does_not_fit_writes_nothing(self):
        cpu = CPU()
        with self.assertRaises(MemoryAccessError):
            cpu.load_program(b"\x01\x02\x03\x04", 0xFFFE)
        self.assertEqual(cpu.memory_used, 0)
        with self.assertRaises(MemoryAccessError):
            cpu.load_program(b"\x01", -1)

    def test_load_program_rejects_invalid_types(self):
        cpu = CPU()
        with self.assertRaises(TypeError):
            cpu.load_program("abc", START)
        with self.assertRaises(MemoryAccessError):
            cpu.load_program(b"\x00\x00", "0x3000")
        with self.assertRaises(MemoryAccessError):
            cpu.load_program(b"\x00\x00", True)


# ----------------------------------------------------------------------
# 2-3. Fetch, avance del PC y step()
# ----------------------------------------------------------------------
class TestFetchAndStep(unittest.TestCase):

    def test_step_fetches_advances_pc_and_counts(self):
        cpu = make_cpu([NOP(), NOP()])
        cpu.step()
        self.assertEqual(cpu.registers.pc, START + 2)
        self.assertEqual(cpu.registers.ir, NOP())
        self.assertEqual(cpu.instruction_count, 1)
        cpu.step()
        self.assertEqual(cpu.registers.pc, START + 4)
        self.assertEqual(cpu.instruction_count, 2)

    def test_step_returns_decoded_instruction(self):
        cpu = make_cpu([ADDI(1, 1, 5)])
        decoded = cpu.step()
        self.assertIsInstance(decoded, DecodedInstruction)
        self.assertEqual(decoded.mnemonic, "ADD")
        self.assertEqual(decoded.imm, 5)

    def test_ir_holds_last_fetched_word(self):
        cpu = make_cpu([ADDI(1, 1, 1), SUBI(1, 1, 1)])
        cpu.step()
        self.assertEqual(cpu.registers.ir, ADDI(1, 1, 1))
        cpu.step()
        self.assertEqual(cpu.registers.ir, SUBI(1, 1, 1))

    def test_pc_wraps_after_last_word_of_memory(self):
        cpu = CPU()
        cpu.memory.write_word(0xFFFE, NOP())
        cpu.registers.pc = 0xFFFE
        cpu.step()
        self.assertEqual(cpu.registers.pc, 0x0000)

    def test_step_on_halted_cpu_raises(self):
        cpu = make_cpu([HALT(), NOP()])
        cpu.step()
        with self.assertRaises(CPUHaltedError):
            cpu.step()
        self.assertEqual(cpu.instruction_count, 1)


# ----------------------------------------------------------------------
# 4. ADD y SUB
# ----------------------------------------------------------------------
class TestAddSub(unittest.TestCase):

    def test_add_register_mode(self):
        cpu = run_one(ADD(3, 1, 2), {1: 5, 2: 7})
        self.assertEqual(cpu.registers.read(3), 12)
        self.assertEqual((cpu.registers.read(1), cpu.registers.read(2)), (5, 7))
        self.assertEqual(flags(cpu), "P")
        self.assertEqual(cpu.registers.pc, START + 2)
        self.assertEqual(cpu.instruction_count, 1)

    def test_add_immediate_positive_and_limits(self):
        for imm, expected in ((5, 15), (7, 17), (-8, 2), (0, 10)):
            with self.subTest(imm=imm):
                cpu = run_one(ADDI(2, 1, imm), {1: 10})
                self.assertEqual(cpu.registers.read(2), expected)

    def test_add_negative_immediate_gives_negative_flag(self):
        cpu = run_one(ADDI(2, 1, -3), {1: 2})
        self.assertEqual(cpu.registers.read(2), 0xFFFF)
        self.assertEqual(flags(cpu), "N")

    def test_add_wraps_to_16_bits(self):
        cpu = run_one(ADDI(1, 1, 1), {1: 0xFFFF})
        self.assertEqual(cpu.registers.read(1), 0)
        self.assertEqual(flags(cpu), "Z")

    def test_add_overflow_into_sign_bit_is_negative(self):
        cpu = run_one(ADDI(1, 1, 1), {1: 0x7FFF})
        self.assertEqual(cpu.registers.read(1), 0x8000)
        self.assertEqual(flags(cpu), "N")

    def test_destination_can_equal_source(self):
        cpu = run_one(ADD(1, 1, 1), {1: 0x0123})
        self.assertEqual(cpu.registers.read(1), 0x0246)

    def test_sub_register_mode(self):
        cpu = run_one(SUB(3, 1, 2), {1: 10, 2: 3})
        self.assertEqual(cpu.registers.read(3), 7)
        self.assertEqual(flags(cpu), "P")

    def test_sub_to_zero(self):
        cpu = run_one(SUB(4, 4, 1), {4: 9, 1: 9})
        self.assertEqual(cpu.registers.read(4), 0)
        self.assertEqual(flags(cpu), "Z")

    def test_sub_immediate(self):
        cpu = run_one(SUBI(2, 1, 7), {1: 5})
        self.assertEqual(cpu.registers.read(2), 0xFFFE)
        self.assertEqual(flags(cpu), "N")
        cpu = run_one(SUBI(2, 1, -3), {1: 5})
        self.assertEqual(cpu.registers.read(2), 8)

    def test_sub_wraps_to_16_bits(self):
        cpu = run_one(SUBI(1, 1, 1), {1: 0})
        self.assertEqual(cpu.registers.read(1), 0xFFFF)
        self.assertEqual(flags(cpu), "N")


# ----------------------------------------------------------------------
# 5. Operaciones lógicas
# ----------------------------------------------------------------------
class TestLogic(unittest.TestCase):

    def test_and_register(self):
        cpu = run_one(AND(3, 1, 2), {1: 0xF0F0, 2: 0xFF00})
        self.assertEqual(cpu.registers.read(3), 0xF000)
        self.assertEqual(flags(cpu), "N")

    def test_and_immediate_is_sign_extended(self):
        cpu = run_one(ANDI(2, 1, -1), {1: 0x1234})      # mascara 0xFFFF
        self.assertEqual(cpu.registers.read(2), 0x1234)
        cpu = run_one(ANDI(2, 1, 7), {1: 0x00FF})       # mascara 0x0007
        self.assertEqual(cpu.registers.read(2), 0x0007)

    def test_or(self):
        cpu = run_one(OR(3, 1, 2), {1: 0x00F0, 2: 0x0F00})
        self.assertEqual(cpu.registers.read(3), 0x0FF0)
        self.assertEqual(flags(cpu), "P")

    def test_xor_same_register_clears(self):
        cpu = run_one(XOR(1, 1, 1), {1: 0xABCD})
        self.assertEqual(cpu.registers.read(1), 0)
        self.assertEqual(flags(cpu), "Z")

    def test_xor_immediate_minus_one_inverts(self):
        cpu = run_one(XORI(2, 1, -1), {1: 0x00FF})
        self.assertEqual(cpu.registers.read(2), 0xFF00)
        self.assertEqual(flags(cpu), "N")

    def test_not_inverts_16_bits(self):
        cpu = run_one(NOT(2, 1), {1: 0x00FF})
        self.assertEqual(cpu.registers.read(2), 0xFF00)
        self.assertEqual(cpu.registers.read(1), 0x00FF)
        self.assertEqual(flags(cpu), "N")
        cpu = run_one(NOT(2, 1), {1: 0xFFFF})
        self.assertEqual(cpu.registers.read(2), 0)
        self.assertEqual(flags(cpu), "Z")


# ----------------------------------------------------------------------
# 6. Desplazamientos
# ----------------------------------------------------------------------
class TestShifts(unittest.TestCase):

    def test_shl(self):
        cpu = run_one(SHL(2, 1, 4), {1: 0x0123})
        self.assertEqual(cpu.registers.read(2), 0x1230)
        self.assertEqual(flags(cpu), "P")

    def test_shl_drops_bits_that_leave_16_bits(self):
        cpu = run_one(SHL(2, 1, 1), {1: 0x8001})
        self.assertEqual(cpu.registers.read(2), 0x0002)

    def test_shl_by_15_amount_is_not_negative(self):
        cpu = run_one(SHL(2, 1, 15), {1: 1})            # inmediato 1111 = 15
        self.assertEqual(cpu.registers.read(2), 0x8000)
        self.assertEqual(flags(cpu), "N")

    def test_shift_by_zero_keeps_value_and_updates_flags(self):
        for build in (SHL, SHR, SAR):
            with self.subTest(op=build.__name__):
                cpu = run_one(build(2, 1, 0), {1: 0x8000})
                self.assertEqual(cpu.registers.read(2), 0x8000)
                self.assertEqual(flags(cpu), "N")

    def test_shr_is_logical(self):
        cpu = run_one(SHR(2, 1, 1), {1: 0x8000})
        self.assertEqual(cpu.registers.read(2), 0x4000)
        self.assertEqual(flags(cpu), "P")
        cpu = run_one(SHR(2, 1, 15), {1: 0xFFFF})
        self.assertEqual(cpu.registers.read(2), 1)

    def test_sar_is_arithmetic(self):
        cpu = run_one(SAR(2, 1, 1), {1: 0x8000})
        self.assertEqual(cpu.registers.read(2), 0xC000)
        self.assertEqual(flags(cpu), "N")
        cpu = run_one(SAR(2, 1, 15), {1: 0x8000})
        self.assertEqual(cpu.registers.read(2), 0xFFFF)

    def test_sar_positive_and_zero_result(self):
        cpu = run_one(SAR(2, 1, 2), {1: 0x4000})
        self.assertEqual(cpu.registers.read(2), 0x1000)
        cpu = run_one(SAR(2, 1, 15), {1: 0x7FFF})
        self.assertEqual(cpu.registers.read(2), 0)
        self.assertEqual(flags(cpu), "Z")

    def test_shift_does_not_change_source(self):
        cpu = run_one(SHL(2, 1, 3), {1: 0x0011})
        self.assertEqual(cpu.registers.read(1), 0x0011)


# ----------------------------------------------------------------------
# 7. CMP
# ----------------------------------------------------------------------
class TestCmp(unittest.TestCase):

    def test_cmp_register_cases(self):
        cases = ((1, 2, "N"), (2, 2, "Z"), (3, 2, "P"),
                 (0xFFFF, 1, "N"), (0x8000, 1, "N"), (0x7FFF, 0xFFFF, "P"),
                 (0x7FFF, 0x8000, "P"), (0x8000, 0x7FFF, "N"))
        for a, b, expected in cases:
            with self.subTest(a=hex(a), b=hex(b)):
                cpu = run_one(CMP(1, 2), {1: a, 2: b})
                self.assertEqual(flags(cpu), expected)

    def test_cmp_immediate_cases(self):
        cases = ((5, 5, "Z"), (5, -1, "P"), (0xFFFF, 0, "N"),
                 (0x8000, -8, "N"), (0, -8, "P"), (3, 7, "N"))
        for value, imm, expected in cases:
            with self.subTest(value=hex(value), imm=imm):
                cpu = run_one(CMPI(1, imm), {1: value})
                self.assertEqual(flags(cpu), expected)

    def test_cmp_does_not_store_a_result(self):
        cpu = make_cpu([CMP(1, 2)])
        for i in range(8):
            cpu.registers.write(i, 0x1111 * (i + 1))
        before = cpu.registers.values()
        cpu.step()
        self.assertEqual(cpu.registers.values(), before)
        self.assertEqual(cpu.registers.pc, START + 2)
        self.assertEqual(cpu.instruction_count, 1)


# ----------------------------------------------------------------------
# Instrucciones que NO modifican las banderas
# ----------------------------------------------------------------------
class TestInstructionsThatKeepFlags(unittest.TestCase):

    def test_flags_are_untouched(self):
        cases = {
            "STW": STW(1, 2, 0), "STBL": STBL(1, 2, 0), "STBH": STBH(1, 2, 0),
            "STI": STI(1, 2, 0), "BR no tomado": BR(Z, 1), "BR tomado": BR(N, 1),
            "JSR": JSR(1), "JMP": JMP(3), "JSRR": JSRR(3), "LEA": LEA(1, 4),
            "NOP": NOP(), "TRAP OUT": TRAP(0x21), "TRAP GETC": TRAP(0x20),
        }
        for name, instruction in cases.items():
            with self.subTest(instruction=name):
                cpu = make_cpu([instruction], input_text="a")
                cpu.registers.write(2, 0x4000)
                cpu.registers.write(3, 0x3100)
                cpu.registers.write(0, 0x41)
                cpu.memory.write_word(0x4000, 0x5000)       # puntero para STI
                cpu.registers.update_nzp(0x8000)            # N activa
                cpu.step()
                self.assertEqual(flags(cpu), "N")


# ----------------------------------------------------------------------
# 8. Carga y almacenamiento
# ----------------------------------------------------------------------
class TestLoadStore(unittest.TestCase):

    def test_ldw_with_offset_and_flags(self):
        for value, expected_flag in ((0xBEEF, "N"), (0x0000, "Z"), (0x1234, "P")):
            with self.subTest(value=hex(value)):
                cpu = make_cpu([LDW(1, 2, 4)])
                cpu.registers.write(2, 0x4000)
                cpu.memory.write_word(0x4004, value)
                cpu.step()
                self.assertEqual(cpu.registers.read(1), value)
                self.assertEqual(flags(cpu), expected_flag)

    def test_ldw_negative_offset(self):
        cpu = make_cpu([LDW(1, 2, -16)])
        cpu.registers.write(2, 0x4010)
        cpu.memory.write_word(0x4000, 0x1234)
        cpu.step()
        self.assertEqual(cpu.registers.read(1), 0x1234)

    def test_stw_writes_little_endian(self):
        cpu = make_cpu([STW(3, 2, 6)])
        cpu.registers.write(2, 0x4000)
        cpu.registers.write(3, 0xCAFE)
        cpu.step()
        self.assertEqual(cpu.memory.read_word(0x4006), 0xCAFE)
        self.assertEqual(cpu.memory.read_byte(0x4006), 0xFE)
        self.assertEqual(cpu.memory.read_byte(0x4007), 0xCA)
        self.assertEqual(cpu.registers.read(3), 0xCAFE)

    def test_effective_address_wraps_modulo_65536(self):
        cpu = make_cpu([LDW(1, 2, 2)])
        cpu.registers.write(2, 0xFFFE)                  # 0xFFFE + 2 -> 0x0000
        cpu.memory.write_word(0x0000, 0x7777)
        cpu.step()
        self.assertEqual(cpu.registers.read(1), 0x7777)

    def test_word_access_at_odd_address(self):
        cpu = make_cpu([LDW(1, 2, 0)])
        cpu.registers.write(2, 0x4001)
        cpu.memory.write_word(0x4001, 0xCAFE)
        cpu.step()
        self.assertEqual(cpu.registers.read(1), 0xCAFE)

    def test_ldbl_sign_extends_low_byte(self):
        for word, expected, flag in ((0x80AB, 0xFFAB, "N"), (0x1234, 0x0034, "P"),
                                     (0x0000, 0x0000, "Z")):
            with self.subTest(word=hex(word)):
                cpu = make_cpu([LDBL(1, 2, 0)])
                cpu.registers.write(2, 0x4000)
                cpu.memory.write_word(0x4000, word)
                cpu.step()
                self.assertEqual(cpu.registers.read(1), expected)
                self.assertEqual(flags(cpu), flag)

    def test_ldbh_sign_extends_high_byte(self):
        for word, expected, flag in ((0x80AB, 0xFF80, "N"), (0x1234, 0x0012, "P"),
                                     (0x0034, 0x0000, "Z")):
            with self.subTest(word=hex(word)):
                cpu = make_cpu([LDBH(1, 2, 0)])
                cpu.registers.write(2, 0x4000)
                cpu.memory.write_word(0x4000, word)
                cpu.step()
                self.assertEqual(cpu.registers.read(1), expected)
                self.assertEqual(flags(cpu), flag)

    def test_stbl_replaces_only_the_byte_at_ea(self):
        cpu = make_cpu([STBL(3, 2, 0)])
        cpu.registers.write(2, 0x4000)
        cpu.registers.write(3, 0x12AB)
        cpu.memory.write_word(0x4000, 0x5566)
        cpu.step()
        self.assertEqual(cpu.memory.read_byte(0x4000), 0xAB)
        self.assertEqual(cpu.memory.read_byte(0x4001), 0x55)

    def test_stbh_replaces_only_the_byte_at_ea_plus_1(self):
        cpu = make_cpu([STBH(3, 2, 0)])
        cpu.registers.write(2, 0x4000)
        cpu.registers.write(3, 0x12AB)
        cpu.memory.write_word(0x4000, 0x5566)
        cpu.step()
        self.assertEqual(cpu.memory.read_byte(0x4000), 0x66)
        self.assertEqual(cpu.memory.read_byte(0x4001), 0xAB)

    def test_last_valid_word_access(self):
        cpu = make_cpu([LDW(1, 2, 0)])
        cpu.registers.write(2, 0xFFFE)
        cpu.memory.write_word(0xFFFE, 0x4321)
        cpu.step()
        self.assertEqual(cpu.registers.read(1), 0x4321)

    def test_out_of_range_accesses_fail_cleanly(self):
        failing = {"LDW": LDW(1, 2, 0), "STW": STW(1, 2, 0),
                   "LDBH": LDBH(1, 2, 0), "STBH": STBH(1, 2, 0)}
        for name, instruction in failing.items():
            with self.subTest(instruction=name):
                cpu = make_cpu([instruction])
                cpu.registers.write(1, 0x1111)
                cpu.registers.write(2, 0xFFFF)
                used_before = cpu.memory_used
                with self.assertRaises(MemoryAccessError):
                    cpu.step()
                self.assertEqual(cpu.registers.read(1), 0x1111)
                self.assertEqual(cpu.registers.pc, START)
                self.assertEqual(cpu.instruction_count, 0)
                self.assertEqual(cpu.memory_used, used_before)

    def test_byte_accesses_at_0xFFFF_are_valid(self):
        cpu = make_cpu([LDBL(1, 2, 0), STBL(3, 2, 0)])
        cpu.registers.write(2, 0xFFFF)
        cpu.registers.write(3, 0x5A)
        cpu.memory.write_byte(0xFFFF, 0x80)
        cpu.step()
        self.assertEqual(cpu.registers.read(1), 0xFF80)
        cpu.step()
        self.assertEqual(cpu.memory.read_byte(0xFFFF), 0x5A)


# ----------------------------------------------------------------------
# 9. Accesos indirectos
# ----------------------------------------------------------------------
class TestIndirect(unittest.TestCase):

    def test_ldi_follows_pointer(self):
        cpu = make_cpu([LDI(1, 2, 2)])
        cpu.registers.write(2, 0x4000)
        cpu.memory.write_word(0x4002, 0x5000)           # puntero
        cpu.memory.write_word(0x5000, 0xABCD)           # dato
        cpu.step()
        self.assertEqual(cpu.registers.read(1), 0xABCD)
        self.assertEqual(flags(cpu), "N")
        self.assertEqual(cpu.memory.read_word(0x4002), 0x5000)

    def test_sti_writes_through_pointer(self):
        cpu = make_cpu([STI(3, 2, 0)])
        cpu.registers.write(2, 0x4000)
        cpu.registers.write(3, 0x1234)
        cpu.memory.write_word(0x4000, 0x5000)
        cpu.step()
        self.assertEqual(cpu.memory.read_word(0x5000), 0x1234)
        self.assertEqual(cpu.memory.read_word(0x4000), 0x5000)

    def test_ldi_with_invalid_pointer_fails_cleanly(self):
        cpu = make_cpu([LDI(1, 2, 0)])
        cpu.registers.write(1, 0x1111)
        cpu.registers.write(2, 0x4000)
        cpu.memory.write_word(0x4000, 0xFFFF)           # palabra en 0xFFFF: inválida
        with self.assertRaises(MemoryAccessError):
            cpu.step()
        self.assertEqual(cpu.registers.read(1), 0x1111)
        self.assertEqual(cpu.registers.pc, START)

    def test_sti_with_invalid_pointer_writes_nothing(self):
        cpu = make_cpu([STI(3, 2, 0)])
        cpu.registers.write(2, 0x4000)
        cpu.memory.write_word(0x4000, 0xFFFF)
        used_before = cpu.memory_used
        with self.assertRaises(MemoryAccessError):
            cpu.step()
        self.assertEqual(cpu.memory_used, used_before)

    def test_ldi_with_invalid_first_address_fails(self):
        cpu = make_cpu([LDI(1, 2, 0)])
        cpu.registers.write(2, 0xFFFF)
        with self.assertRaises(MemoryAccessError):
            cpu.step()


# ----------------------------------------------------------------------
# 10. BR
# ----------------------------------------------------------------------
class TestBranch(unittest.TestCase):

    def test_taken_branch_program(self):
        cpu = make_cpu([ADDI(1, 1, 0),      # R1 = 0 -> Z
                        BR(Z, 1),           # salta la instrucción siguiente
                        ADDI(2, 2, 1),      # (saltada)
                        HALT()])
        cpu.run()
        self.assertEqual(cpu.registers.read(2), 0)
        self.assertEqual(cpu.registers.pc, START + 8)
        self.assertEqual(cpu.instruction_count, 3)

    def test_not_taken_branch_program(self):
        cpu = make_cpu([ADDI(1, 1, 0), BR(Z, 1), ADDI(2, 2, 1), HALT()])
        cpu.registers.write(1, 1)           # ADDI deja R1 = 1 -> P
        cpu.run()
        self.assertEqual(cpu.registers.read(2), 1)
        self.assertEqual(cpu.instruction_count, 4)

    def test_every_mask_against_every_flag(self):
        states = {"N": 0x8000, "Z": 0x0000, "P": 0x0001}
        bits = {"N": N, "Z": Z, "P": P}
        for flag, value in states.items():
            for mask in range(8):
                with self.subTest(flag=flag, mask=bin(mask)):
                    cpu = make_cpu([BR(mask, 2)])
                    cpu.registers.update_nzp(value)
                    cpu.step()
                    taken = bool(mask & bits[flag])
                    self.assertEqual(cpu.registers.pc,
                                     START + 2 + (4 if taken else 0))

    def test_offset_is_relative_to_incremented_pc(self):
        cpu = make_cpu([BR(0b111, 0)])
        cpu.step()
        self.assertEqual(cpu.registers.pc, START + 2)    # offset 0 = siguiente
        cpu = make_cpu([BR(0b111, -1)])
        cpu.step()
        self.assertEqual(cpu.registers.pc, START)        # se salta a sí misma

    def test_offset_limits(self):
        cpu = make_cpu([BR(0b111, 127)])
        cpu.step()
        self.assertEqual(cpu.registers.pc, START + 2 + 254)
        cpu = make_cpu([BR(0b111, -128)])
        cpu.step()
        self.assertEqual(cpu.registers.pc, START + 2 - 256)

    def test_target_wraps_modulo_65536(self):
        cpu = CPU()
        cpu.memory.write_word(0, BR(0b111, -2))          # 2 - 4 = -2 -> 0xFFFE
        cpu.step()
        self.assertEqual(cpu.registers.pc, 0xFFFE)

    def test_countdown_loop(self):
        cpu = make_cpu([ADDI(1, 1, 3),      # 3000: R1 = 3
                        ADDI(2, 2, 1),      # 3002: R2++  (inicio del bucle)
                        SUBI(1, 1, 1),      # 3004: R1--
                        BR(P, -3),          # 3006: vuelve a 3002 mientras R1 > 0
                        HALT()])            # 3008
        cpu.run()
        self.assertEqual(cpu.registers.read(1), 0)
        self.assertEqual(cpu.registers.read(2), 3)
        self.assertEqual(flags(cpu), "Z")
        self.assertEqual(cpu.registers.pc, START + 0x0A)
        self.assertEqual(cpu.instruction_count, 11)


# ----------------------------------------------------------------------
# 11. JSR, JMP, JSRR
# ----------------------------------------------------------------------
class TestSubroutines(unittest.TestCase):

    def test_jsr_saves_incremented_pc_and_jumps(self):
        cpu = run_one(JSR(3))
        self.assertEqual(cpu.registers.read(7), START + 2)
        self.assertEqual(cpu.registers.pc, START + 2 + 6)

    def test_jsr_negative_and_limit_offsets(self):
        for offset, target in ((-2, START + 2 - 4), (1023, START + 2 + 2046),
                               (-1024, START + 2 - 2048)):
            with self.subTest(offset=offset):
                cpu = run_one(JSR(offset))
                self.assertEqual(cpu.registers.pc, target)
                self.assertEqual(cpu.registers.read(7), START + 2)

    def test_jmp_register_does_not_touch_r7(self):
        cpu = run_one(JMP(3), {3: 0x3100, 7: 0x1234})
        self.assertEqual(cpu.registers.pc, 0x3100)
        self.assertEqual(cpu.registers.read(7), 0x1234)

    def test_jsrr_saves_return_and_jumps(self):
        cpu = run_one(JSRR(3), {3: 0x3100})
        self.assertEqual(cpu.registers.pc, 0x3100)
        self.assertEqual(cpu.registers.read(7), START + 2)

    def test_jsrr_through_r7_reads_target_before_overwriting(self):
        cpu = run_one(JSRR(7), {7: 0x3100})
        self.assertEqual(cpu.registers.pc, 0x3100)
        self.assertEqual(cpu.registers.read(7), START + 2)

    def test_call_and_return_program(self):
        cpu = make_cpu([JSR(2),             # 3000: llama a 3006
                        ADDI(2, 2, 1),      # 3002: tras el retorno
                        HALT(),             # 3004
                        ADDI(1, 1, 5),      # 3006: subrutina
                        JMP(7)])            # 3008: retorna a 3002
        cpu.run()
        self.assertEqual(cpu.registers.read(1), 5)
        self.assertEqual(cpu.registers.read(2), 1)
        self.assertEqual(cpu.registers.pc, START + 6)
        self.assertEqual(cpu.instruction_count, 5)

    def test_nested_calls_preserve_r7_with_stack(self):
        cpu = make_cpu([JSR(1),             # 3000: llama a outer (3004)
                        HALT(),             # 3002
                        ADDI(6, 6, -2),     # 3004 outer: apila R7
                        STW(7, 6, 0),       # 3006
                        JSR(4),             # 3008: llama a inner (3012)
                        LDW(7, 6, 0),       # 300A: desapila R7
                        ADDI(6, 6, 2),      # 300C
                        ADDI(1, 1, 1),      # 300E
                        JMP(7),             # 3010: vuelve a 3002
                        ADDI(2, 2, 7),      # 3012 inner
                        JMP(7)])            # 3014: vuelve a 300A
        cpu.registers.write(6, 0x8000)
        cpu.run()
        self.assertEqual(cpu.registers.read(1), 1)
        self.assertEqual(cpu.registers.read(2), 7)
        self.assertEqual(cpu.registers.read(6), 0x8000)
        self.assertEqual(cpu.registers.read(7), START + 2)
        self.assertEqual(cpu.memory.read_word(0x7FFE), START + 2)   # R7 apilado
        self.assertEqual(cpu.registers.pc, START + 4)
        self.assertEqual(cpu.instruction_count, 11)
        self.assertEqual(cpu.memory_used, 22 + 2)       # programa + 1 palabra de pila


# ----------------------------------------------------------------------
# 12. LEA
# ----------------------------------------------------------------------
class TestLea(unittest.TestCase):

    def test_offset_is_in_bytes_from_incremented_pc(self):
        cpu = run_one(LEA(1, 10))
        self.assertEqual(cpu.registers.read(1), START + 2 + 10)

    def test_negative_and_odd_offsets(self):
        cpu = run_one(LEA(1, -2))
        self.assertEqual(cpu.registers.read(1), START)
        cpu = run_one(LEA(1, 1))
        self.assertEqual(cpu.registers.read(1), START + 3)   # impar permitido

    def test_wraps_modulo_65536(self):
        cpu = CPU()
        cpu.memory.write_word(0, LEA(1, -4))
        cpu.step()
        self.assertEqual(cpu.registers.read(1), 0xFFFE)

    def test_lea_does_not_change_flags(self):
        cpu = make_cpu([LEA(1, -2)])                     # resultado 0x3000 (positivo)
        cpu.registers.update_nzp(0)                      # Z
        cpu.step()
        self.assertEqual(flags(cpu), "Z")


# ----------------------------------------------------------------------
# 13-14. NOP y HALT
# ----------------------------------------------------------------------
class TestNopHalt(unittest.TestCase):

    def test_nop_changes_nothing_but_pc_and_counter(self):
        cpu = make_cpu([NOP()])
        for i in range(8):
            cpu.registers.write(i, 0x1111 * (i + 1))
        cpu.registers.update_nzp(0x8000)
        regs_before = cpu.registers.values()
        memory_before = cpu.memory.written_addresses
        cpu.step()
        self.assertEqual(cpu.registers.values(), regs_before)
        self.assertEqual(flags(cpu), "N")
        self.assertEqual(cpu.memory.written_addresses, memory_before)
        self.assertEqual(cpu.registers.pc, START + 2)
        self.assertEqual(cpu.instruction_count, 1)
        self.assertFalse(cpu.halted)

    def test_halt_stops_the_cpu_and_is_counted(self):
        cpu = make_cpu([HALT()])
        cpu.step()
        self.assertTrue(cpu.halted)
        self.assertEqual(cpu.halt_reason, "HALT")
        self.assertEqual(cpu.instruction_count, 1)
        self.assertEqual(cpu.registers.pc, START + 2)

    def test_run_stops_at_halt_and_ignores_following_code(self):
        cpu = make_cpu([ADDI(1, 1, 1), HALT(), ADDI(1, 1, 1)])
        executed = cpu.run()
        self.assertEqual(executed, 2)
        self.assertEqual(cpu.registers.read(1), 1)

    def test_run_on_halted_cpu_returns_zero(self):
        cpu = make_cpu([HALT()])
        self.assertEqual(cpu.run(), 1)
        self.assertEqual(cpu.run(), 0)
        self.assertEqual(cpu.instruction_count, 1)


# ----------------------------------------------------------------------
# 15. TRAP
# ----------------------------------------------------------------------
class TestTrap(unittest.TestCase):

    def test_out_writes_low_byte_of_r0(self):
        cpu = run_one(TRAP(0x21), {0: 0x1241})
        self.assertEqual(output(cpu), "A")
        self.assertEqual(cpu.registers.read(0), 0x1241)

    def test_getc_reads_characters_in_order(self):
        cpu = make_cpu([TRAP(0x20), ADD(1, 0, 6), TRAP(0x20)], input_text="ab")
        cpu.registers.write(0, 0xFFFF)                   # el byte alto debe borrarse
        cpu.step()
        self.assertEqual(cpu.registers.read(0), ord("a"))
        cpu.step()
        cpu.step()
        self.assertEqual(cpu.registers.read(1), ord("a"))
        self.assertEqual(cpu.registers.read(0), ord("b"))

    def test_getc_at_end_of_input_gives_minus_one(self):
        cpu = run_one(TRAP(0x20))
        self.assertEqual(cpu.registers.read(0), 0xFFFF)

    def test_getc_replaces_characters_above_255(self):
        cpu = make_cpu([TRAP(0x20), TRAP(0x20)], input_text="ñ€")
        cpu.step()
        self.assertEqual(cpu.registers.read(0), 0xF1)    # Latin-1
        cpu.step()
        self.assertEqual(cpu.registers.read(0), ord("?"))

    def test_puts_writes_zero_terminated_string(self):
        cpu = make_cpu([TRAP(0x22)])
        put_string(cpu, 0x4000, "Hola")
        cpu.registers.write(0, 0x4000)
        cpu.step()
        self.assertEqual(output(cpu), "Hola")
        self.assertEqual(cpu.registers.read(0), 0x4000)

    def test_puts_empty_string_and_odd_address(self):
        cpu = make_cpu([TRAP(0x22)])
        cpu.registers.write(0, 0x4000)                   # memoria en cero: cadena vacía
        cpu.step()
        self.assertEqual(output(cpu), "")
        cpu = make_cpu([TRAP(0x22)])
        put_string(cpu, 0x4001, "ok")
        cpu.registers.write(0, 0x4001)
        cpu.step()
        self.assertEqual(output(cpu), "ok")

    def test_puts_without_terminator_fails_without_partial_output(self):
        cpu = make_cpu([TRAP(0x22)])
        for address in range(0xFFF0, 0x10000):
            cpu.memory.write_byte(address, ord("A"))
        cpu.registers.write(0, 0xFFF0)
        with self.assertRaises(MemoryAccessError):
            cpu.step()
        self.assertEqual(output(cpu), "")
        self.assertEqual(cpu.registers.pc, START)

    def test_trap_x25_halts(self):
        cpu = run_one(TRAP(0x25))
        self.assertTrue(cpu.halted)
        self.assertEqual(cpu.halt_reason, "TRAP x25")
        self.assertEqual(cpu.instruction_count, 1)

    def test_unknown_vector_fails_cleanly(self):
        cpu = make_cpu([TRAP(0x30)])
        with self.assertRaises(UnknownTrapError):
            cpu.step()
        self.assertEqual(cpu.registers.pc, START)
        self.assertEqual(cpu.instruction_count, 0)
        self.assertFalse(cpu.halted)

    def test_hello_program(self):
        cpu = make_cpu([LEA(0, 4),          # 3000: R0 = 3002 + 4 = 3006
                        TRAP(0x22),         # 3002: imprime la cadena
                        TRAP(0x25)],        # 3004: termina
                       data=b"Hi!\x00")     # 3006
        cpu.run()
        self.assertEqual(output(cpu), "Hi!")
        self.assertEqual(cpu.halt_reason, "TRAP x25")
        self.assertEqual(cpu.instruction_count, 3)
        self.assertEqual(cpu.memory_used, 6 + 4)

    def test_echo_program(self):
        cpu = make_cpu([TRAP(0x20), TRAP(0x21), TRAP(0x25)], input_text="x")
        cpu.run()
        self.assertEqual(output(cpu), "x")

    def test_console_io_defaults_to_standard_streams(self):
        console = ConsoleIO()
        self.assertIsNotNone(console.stdin)
        self.assertIsNotNone(console.stdout)


# ----------------------------------------------------------------------
# 16. Direcciones impares
# ----------------------------------------------------------------------
class TestAlignment(unittest.TestCase):

    def test_fetch_from_odd_address_raises(self):
        cpu = make_cpu([NOP()])
        cpu.registers.pc = START + 1
        with self.assertRaises(MisalignedAddressError):
            cpu.step()
        self.assertEqual(cpu.registers.pc, START + 1)
        self.assertEqual(cpu.instruction_count, 0)

    def test_jmp_to_odd_address_raises_and_keeps_state(self):
        cpu = make_cpu([JMP(3)])
        cpu.registers.write(3, 0x3101)
        cpu.registers.write(7, 0x1234)
        with self.assertRaises(MisalignedAddressError):
            cpu.step()
        self.assertEqual(cpu.registers.pc, START)
        self.assertEqual(cpu.registers.read(7), 0x1234)
        self.assertEqual(cpu.instruction_count, 0)

    def test_jsrr_to_odd_address_does_not_write_r7(self):
        cpu = make_cpu([JSRR(3)])
        cpu.registers.write(3, 0x3101)
        with self.assertRaises(MisalignedAddressError):
            cpu.step()
        self.assertEqual(cpu.registers.read(7), 0)
        self.assertEqual(cpu.registers.pc, START)

    def test_relative_jumps_from_even_pc_are_always_even(self):
        for instruction in (BR(0b111, 7), BR(0b111, -7), JSR(5), JSR(-5)):
            with self.subTest(instruction=hex(instruction)):
                cpu = run_one(instruction)
                self.assertEqual(cpu.registers.pc % 2, 0)

    def test_error_message_mentions_address(self):
        cpu = make_cpu([JMP(3)])
        cpu.registers.write(3, 0x3101)
        with self.assertRaisesRegex(MisalignedAddressError, "0x3101"):
            cpu.step()


# ----------------------------------------------------------------------
# 17. Instrucciones inválidas
# ----------------------------------------------------------------------
class TestInvalidInstructions(unittest.TestCase):

    def test_invalid_words_raise_and_keep_state(self):
        invalid = {
            "opcode reservado": 0xD000,
            "campo reservado de NOP": (OPCODES["NOP"] << 11) | 1,
            "shift en modo registro": _a("SHL", 1, 2, 0, 3),
            "CMP con DR distinto de 0": _a("CMP", 1, 2, 0, 3),
        }
        for name, word in invalid.items():
            with self.subTest(case=name):
                cpu = make_cpu([word])
                with self.assertRaises(InvalidInstructionError):
                    cpu.step()
                self.assertEqual(cpu.registers.ir, word)
                self.assertEqual(cpu.registers.pc, START)
                self.assertEqual(cpu.instruction_count, 0)
                self.assertFalse(cpu.halted)

    def test_run_stops_with_error_at_invalid_instruction(self):
        cpu = make_cpu([ADDI(1, 1, 1), 0xFFFF, HALT()])
        with self.assertRaises(InvalidInstructionError):
            cpu.run()
        self.assertEqual(cpu.registers.read(1), 1)
        self.assertEqual(cpu.registers.pc, START + 2)
        self.assertEqual(cpu.instruction_count, 1)

    def test_zero_word_is_add_r0_r0_r0(self):
        cpu = make_cpu([0x0000])
        decoded = cpu.step()
        self.assertEqual(decoded.mnemonic, "ADD")
        self.assertEqual(cpu.registers.read(0), 0)

    def test_execution_errors_tuple_covers_all_failures(self):
        errors = (MisalignedAddressError("x"), ExecutionLimitError("x"),
                  CPUHaltedError("x"), MemoryAccessError("x"),
                  InvalidInstructionError("x"), UnknownTrapError("x"))
        for error in errors:
            with self.subTest(error=type(error).__name__):
                self.assertIsInstance(error, EXECUTION_ERRORS)


# ----------------------------------------------------------------------
# 18. Límite de ejecución
# ----------------------------------------------------------------------
class TestExecutionLimit(unittest.TestCase):

    def test_infinite_loop_hits_the_limit(self):
        cpu = make_cpu([BR(0b111, -1)])
        with self.assertRaises(ExecutionLimitError):
            cpu.run(max_steps=100)
        self.assertEqual(cpu.instruction_count, 100)
        self.assertFalse(cpu.halted)
        with self.assertRaises(ExecutionLimitError):    # se puede reanudar
            cpu.run(max_steps=10)
        self.assertEqual(cpu.instruction_count, 110)

    def test_limit_boundary(self):
        cpu = make_cpu([NOP(), NOP(), HALT()])
        self.assertEqual(cpu.run(max_steps=3), 3)       # justo alcanza
        cpu = make_cpu([NOP(), NOP(), HALT()])
        with self.assertRaises(ExecutionLimitError):
            cpu.run(max_steps=2)

    def test_run_counts_only_its_own_steps(self):
        cpu = make_cpu([NOP(), NOP(), HALT()])
        cpu.step()
        self.assertEqual(cpu.run(), 2)
        self.assertEqual(cpu.instruction_count, 3)

    def test_invalid_max_steps_rejected(self):
        cpu = make_cpu([HALT()])
        for bad in (0, -1, "5", 1.5, None, True):
            with self.subTest(value=bad):
                with self.assertRaises(ValueError):
                    cpu.run(max_steps=bad)


# ----------------------------------------------------------------------
# 19-20. Conteo de instrucciones y de memoria usada
# ----------------------------------------------------------------------
class TestCounters(unittest.TestCase):

    def test_failed_steps_are_not_counted(self):
        cpu = make_cpu([ADDI(1, 1, 1), LDW(1, 2, 0)])
        cpu.registers.write(2, 0xFFFF)
        cpu.step()
        with self.assertRaises(MemoryAccessError):
            cpu.step()
        self.assertEqual(cpu.instruction_count, 1)

    def test_memory_used_counts_program_and_new_writes(self):
        cpu = make_cpu([STW(1, 2, 0), STW(1, 2, 0), STW(1, 2, 2), HALT()])
        self.assertEqual(cpu.memory_used, 8)
        cpu.registers.write(2, 0x4000)
        cpu.registers.write(1, 0x1234)
        cpu.step()
        self.assertEqual(cpu.memory_used, 10)
        cpu.step()                                      # misma dirección: no suma
        self.assertEqual(cpu.memory_used, 10)
        cpu.step()                                      # 0x4002: dos bytes nuevos
        self.assertEqual(cpu.memory_used, 12)

    def test_reads_do_not_increase_memory_used(self):
        cpu = make_cpu([LDW(1, 2, 0), LDBL(1, 2, 0)])
        cpu.registers.write(2, 0x4000)
        used = cpu.memory_used
        cpu.step()
        cpu.step()
        self.assertEqual(cpu.memory_used, used)

    def test_memory_used_matches_memory_module(self):
        cpu = make_cpu([NOP(), HALT()])
        self.assertEqual(cpu.memory_used, cpu.memory.used_bytes)


if __name__ == "__main__":
    unittest.main()

