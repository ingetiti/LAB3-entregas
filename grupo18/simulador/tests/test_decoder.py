"""Pruebas de simulator/decoder.py (ejecutar desde la carpeta raíz Lab3C).

Las palabras de prueba se arman a mano con desplazamientos de bits propios
(sin usar el decodificador) y se comparan con lo que dice la especificación.
"""

import dataclasses
import unittest

from simulator.decoder import (
    MODE_IMMEDIATE,
    MODE_REGISTER,
    NZP_N,
    NZP_P,
    NZP_Z,
    DecodedInstruction,
    Format,
    InvalidInstructionError,
    ReservedFieldError,
    ReservedOpcodeError,
    decode,
    get_bits,
    sign_extend,
)
from simulator.memory import Memory
from simulator.registers import Registers

# Tabla de opcodes escrita a mano desde la especificación (independiente del módulo).
OPCODES = {
    "ADD": 0b00000, "SUB": 0b00001, "AND": 0b00010, "OR": 0b00011,
    "XOR": 0b00100, "NOT": 0b00101, "SHL": 0b00110, "SHR": 0b00111,
    "SAR": 0b01000, "CMP": 0b01001, "LDW": 0b01010, "STW": 0b01011,
    "LDBL": 0b01100, "LDBH": 0b01101, "STBL": 0b01110, "STBH": 0b01111,
    "BR": 0b10000, "JSR": 0b10001, "JMP": 0b10010, "LEA": 0b10011,
    "LDI": 0b10100, "STI": 0b10101, "TRAP": 0b10110, "NOP": 0b10111,
    "HALT": 0b11000, "JSRR": 0b11001,
}

BINARY_MNEMONICS = ("ADD", "SUB", "AND", "OR", "XOR")
SHIFT_MNEMONICS = ("SHL", "SHR", "SAR")
MEMORY_MNEMONICS = ("LDW", "STW", "LDBL", "LDBH", "STBL", "STBH", "LDI", "STI")


# ----------------------------------------------------------------------
# Constructores de palabras (codificadores mínimos solo para las pruebas)
# ----------------------------------------------------------------------
def word_a(mnemonic, dr, sr1, m, op2):
    return (OPCODES[mnemonic] << 11) | (dr << 8) | (sr1 << 5) | (m << 4) | op2


def word_b(mnemonic, reg, base, offset5):
    return (OPCODES[mnemonic] << 11) | (reg << 8) | (base << 5) | offset5


def word_br(nzp, offset8):
    return (OPCODES["BR"] << 11) | (nzp << 8) | offset8


def word_jsr(offset11):
    return (OPCODES["JSR"] << 11) | offset11


def word_jump_reg(mnemonic, base, zeros=0):
    return (OPCODES[mnemonic] << 11) | (base << 8) | zeros


def word_lea(dr, offset8):
    return (OPCODES["LEA"] << 11) | (dr << 8) | offset8


def word_trap(vector, zeros=0):
    return (OPCODES["TRAP"] << 11) | (vector << 3) | zeros


def word_implicit(mnemonic, zeros=0):
    return (OPCODES[mnemonic] << 11) | zeros


def sample_word(mnemonic):
    """Una codificación válida (con campos no triviales) para cada instrucción."""
    if mnemonic == "NOT":
        return word_a("NOT", 5, 3, 0, 0)
    if mnemonic == "CMP":
        return word_a("CMP", 0, 3, 0, 0b0010)
    if mnemonic in SHIFT_MNEMONICS:
        return word_a(mnemonic, 5, 3, 1, 0b0100)
    if mnemonic in BINARY_MNEMONICS:
        return word_a(mnemonic, 5, 3, 0, 0b0010)
    if mnemonic in MEMORY_MNEMONICS:
        return word_b(mnemonic, 5, 3, 0b00110)
    if mnemonic == "BR":
        return word_br(0b101, 0x0A)
    if mnemonic == "JSR":
        return word_jsr(0x123)
    if mnemonic in ("JMP", "JSRR"):
        return word_jump_reg(mnemonic, 6)
    if mnemonic == "LEA":
        return word_lea(2, 0x10)
    if mnemonic == "TRAP":
        return word_trap(0x25)
    return word_implicit(mnemonic)      # NOP, HALT


def present_fields(decoded):
    """Nombres de los campos opcionales que NO son None."""
    names = ("dr", "sr1", "sr2", "mode", "imm", "reg", "base",
             "offset", "nzp", "vector")
    return {name for name in names if getattr(decoded, name) is not None}


# ----------------------------------------------------------------------
# Utilidades de bits
# ----------------------------------------------------------------------
class TestGetBits(unittest.TestCase):

    def test_extracts_fields(self):
        word = 0b1010_0110_1100_0011
        self.assertEqual(get_bits(word, 15, 11), 0b10100)
        self.assertEqual(get_bits(word, 10, 8), 0b110)
        self.assertEqual(get_bits(word, 7, 5), 0b110)
        self.assertEqual(get_bits(word, 4, 4), 0)
        self.assertEqual(get_bits(word, 3, 0), 0b0011)
        self.assertEqual(get_bits(word, 15, 0), word)


class TestSignExtend(unittest.TestCase):

    def test_4_bits(self):
        for raw, expected in ((0b0000, 0), (0b0111, 7), (0b1000, -8), (0b1111, -1)):
            with self.subTest(raw=bin(raw)):
                self.assertEqual(sign_extend(raw, 4), expected)

    def test_5_bits(self):
        for raw, expected in ((0b00000, 0), (0b01111, 15), (0b10000, -16), (0b11111, -1)):
            with self.subTest(raw=bin(raw)):
                self.assertEqual(sign_extend(raw, 5), expected)

    def test_8_bits(self):
        for raw, expected in ((0x00, 0), (0x7F, 127), (0x80, -128), (0xFF, -1)):
            with self.subTest(raw=hex(raw)):
                self.assertEqual(sign_extend(raw, 8), expected)

    def test_11_bits(self):
        for raw, expected in ((0x000, 0), (0x3FF, 1023), (0x400, -1024), (0x7FF, -1)):
            with self.subTest(raw=hex(raw)):
                self.assertEqual(sign_extend(raw, 11), expected)


# ----------------------------------------------------------------------
# Validación de la palabra de entrada
# ----------------------------------------------------------------------
class TestWordValidation(unittest.TestCase):

    def test_accepts_zero_word(self):
        # 0x0000 es ADD R0, R0, R0: una instrucción válida.
        d = decode(0x0000)
        self.assertEqual(d.mnemonic, "ADD")

    def test_rejects_non_integer_types(self):
        for bad in ("0x0000", 1.0, 1.5, None, [0], b"\x00"):
            with self.subTest(value=bad):
                with self.assertRaises(InvalidInstructionError):
                    decode(bad)

    def test_rejects_booleans(self):
        for bad in (True, False):
            with self.subTest(value=bad):
                with self.assertRaises(InvalidInstructionError):
                    decode(bad)

    def test_rejects_negative_values(self):
        for bad in (-1, -32768):
            with self.subTest(value=bad):
                with self.assertRaises(InvalidInstructionError):
                    decode(bad)

    def test_rejects_values_above_16_bits(self):
        for bad in (0x10000, 0x12345):
            with self.subTest(value=bad):
                with self.assertRaises(InvalidInstructionError):
                    decode(bad)


# ----------------------------------------------------------------------
# Opcode
# ----------------------------------------------------------------------
class TestOpcode(unittest.TestCase):

    def test_all_26_instructions_identified(self):
        self.assertEqual(len(OPCODES), 26)
        for mnemonic, opcode in OPCODES.items():
            with self.subTest(mnemonic=mnemonic):
                word = sample_word(mnemonic)
                d = decode(word)
                self.assertEqual(d.mnemonic, mnemonic)
                self.assertEqual(d.opcode, opcode)
                self.assertEqual(d.word, word)

    def test_opcode_is_top_five_bits_only(self):
        # El formato B admite cualquier valor en los 11 bits bajos.
        for low in (0x000, 0x7FF, 0x2AA, 0x555):
            with self.subTest(low=hex(low)):
                d = decode((0b01010 << 11) | low)
                self.assertEqual(d.opcode, 0b01010)
                self.assertEqual(d.mnemonic, "LDW")

    def test_reserved_opcodes_rejected(self):
        for opcode in range(26, 32):
            for low in (0x000, 0x555, 0x7FF):
                word = (opcode << 11) | low
                with self.subTest(word=hex(word)):
                    with self.assertRaises(ReservedOpcodeError):
                        decode(word)
        with self.assertRaises(ReservedOpcodeError):
            decode(0xFFFF)


# ----------------------------------------------------------------------
# Formato A
# ----------------------------------------------------------------------
class TestFormatA(unittest.TestCase):

    def test_register_mode(self):
        d = decode(word_a("ADD", 1, 2, 0, 0b0011))     # ADD R1, R2, R3
        self.assertEqual(d.mnemonic, "ADD")
        self.assertEqual(d.fmt, Format.A)
        self.assertEqual(d.dr, 1)
        self.assertEqual(d.sr1, 2)
        self.assertEqual(d.mode, MODE_REGISTER)
        self.assertEqual(d.sr2, 3)
        self.assertIsNone(d.imm)

    def test_all_binary_operations_register_mode(self):
        for mnemonic in BINARY_MNEMONICS:
            with self.subTest(mnemonic=mnemonic):
                d = decode(word_a(mnemonic, 7, 6, 0, 0b0101))
                self.assertEqual(d.mnemonic, mnemonic)
                self.assertEqual((d.dr, d.sr1, d.sr2), (7, 6, 5))

    def test_all_register_combinations(self):
        for dr in range(8):
            for sr1 in range(8):
                for sr2 in range(8):
                    d = decode(word_a("ADD", dr, sr1, 0, sr2))
                    self.assertEqual((d.dr, d.sr1, d.sr2), (dr, sr1, sr2))

    def test_immediate_positive(self):
        d = decode(word_a("ADD", 1, 2, 1, 0b0101))     # ADD R1, R2, #5
        self.assertEqual(d.mode, MODE_IMMEDIATE)
        self.assertEqual(d.imm, 5)
        self.assertIsNone(d.sr2)

    def test_immediate_negative(self):
        raw = (-3) & 0xF                               # 0b1101
        d = decode(word_a("SUB", 4, 4, 1, raw))        # SUB R4, R4, #-3
        self.assertEqual(d.imm, -3)

    def test_immediate_limits(self):
        cases = ((0b0000, 0), (0b0001, 1), (0b0111, 7),
                 (0b1000, -8), (0b1110, -2), (0b1111, -1))
        for raw, expected in cases:
            with self.subTest(raw=bin(raw)):
                d = decode(word_a("ADD", 0, 0, 1, raw))
                self.assertEqual(d.imm, expected)

    def test_add_immediate_1111_is_minus_one(self):
        d = decode(word_a("ADD", 1, 2, 1, 0b1111))
        self.assertEqual(d.imm, -1)

    def test_shl_immediate_1111_is_fifteen(self):
        d = decode(word_a("SHL", 1, 2, 1, 0b1111))
        self.assertEqual(d.imm, 15)

    def test_shift_amounts_0_to_15(self):
        for mnemonic in SHIFT_MNEMONICS:
            for amount in range(16):
                with self.subTest(mnemonic=mnemonic, amount=amount):
                    d = decode(word_a(mnemonic, 3, 5, 1, amount))
                    self.assertEqual((d.dr, d.sr1, d.mode, d.imm),
                                     (3, 5, MODE_IMMEDIATE, amount))
                    self.assertIsNone(d.sr2)

    def test_shift_register_mode_rejected(self):
        for mnemonic in SHIFT_MNEMONICS:
            with self.subTest(mnemonic=mnemonic):
                with self.assertRaises(InvalidInstructionError):
                    decode(word_a(mnemonic, 1, 2, 0, 0b0011))

    def test_register_mode_reserved_bit_must_be_zero(self):
        for mnemonic in BINARY_MNEMONICS + ("CMP",):
            for op2 in (0b1000, 0b1011, 0b1111):
                with self.subTest(mnemonic=mnemonic, op2=bin(op2)):
                    with self.assertRaises(ReservedFieldError):
                        decode(word_a(mnemonic, 0, 1, 0, op2))

    def test_not_fields(self):
        d = decode(word_a("NOT", 1, 2, 0, 0))          # NOT R1, R2
        self.assertEqual((d.dr, d.sr1), (1, 2))
        self.assertIsNone(d.mode)
        self.assertIsNone(d.sr2)
        self.assertIsNone(d.imm)

    def test_not_unused_fields_must_be_zero(self):
        for m, op2 in ((1, 0), (0, 0b0001), (0, 0b1000), (1, 0b0101)):
            with self.subTest(m=m, op2=bin(op2)):
                with self.assertRaises(ReservedFieldError):
                    decode(word_a("NOT", 1, 2, m, op2))

    def test_cmp_register_mode(self):
        d = decode(word_a("CMP", 0, 3, 0, 0b0101))     # CMP R3, R5
        self.assertIsNone(d.dr)
        self.assertEqual(d.sr1, 3)
        self.assertEqual(d.mode, MODE_REGISTER)
        self.assertEqual(d.sr2, 5)
        self.assertIsNone(d.imm)

    def test_cmp_immediate_mode(self):
        d = decode(word_a("CMP", 0, 3, 1, 0b1110))     # CMP R3, #-2
        self.assertIsNone(d.dr)
        self.assertEqual(d.sr1, 3)
        self.assertEqual(d.mode, MODE_IMMEDIATE)
        self.assertEqual(d.imm, -2)
        self.assertIsNone(d.sr2)

    def test_cmp_dr_must_be_zero(self):
        for dr in range(1, 8):
            with self.subTest(dr=dr):
                with self.assertRaises(ReservedFieldError):
                    decode(word_a("CMP", dr, 3, 0, 0b0001))


# ----------------------------------------------------------------------
# Formato B
# ----------------------------------------------------------------------
class TestFormatB(unittest.TestCase):

    def test_ldw_fields(self):
        d = decode(word_b("LDW", 1, 2, 0b00100))       # LDW R1, R2, #4
        self.assertEqual(d.mnemonic, "LDW")
        self.assertEqual(d.fmt, Format.B)
        self.assertEqual((d.reg, d.base, d.offset), (1, 2, 4))

    def test_all_memory_instructions_share_layout(self):
        for mnemonic in MEMORY_MNEMONICS:
            with self.subTest(mnemonic=mnemonic):
                d = decode(word_b(mnemonic, 3, 6, 0b01111))
                self.assertEqual(d.mnemonic, mnemonic)
                self.assertEqual((d.reg, d.base, d.offset), (3, 6, 15))

    def test_offset_limits(self):
        cases = ((0b00000, 0), (0b00001, 1), (0b01111, 15),
                 (0b10000, -16), (0b11110, -2), (0b11111, -1))
        for raw, expected in cases:
            with self.subTest(raw=bin(raw)):
                d = decode(word_b("LDW", 0, 0, raw))
                self.assertEqual(d.offset, expected)

    def test_offset_11111_is_minus_one(self):
        d = decode(word_b("STW", 3, 2, 0b11111))
        self.assertEqual(d.offset, -1)


# ----------------------------------------------------------------------
# Formato C (BR)
# ----------------------------------------------------------------------
class TestBranch(unittest.TestCase):

    def test_nzp_constants(self):
        self.assertEqual(NZP_N, 0b100)
        self.assertEqual(NZP_Z, 0b010)
        self.assertEqual(NZP_P, 0b001)

    def test_nzp_masks_0_to_7(self):
        for nzp in range(8):
            with self.subTest(nzp=bin(nzp)):
                d = decode(word_br(nzp, 0x05))
                self.assertEqual(d.mnemonic, "BR")
                self.assertEqual(d.fmt, Format.C)
                self.assertEqual(d.nzp, nzp)
                self.assertEqual(d.offset, 5)
        self.assertEqual(decode(word_br(0b010, 0)).nzp, NZP_Z)
        self.assertEqual(decode(word_br(0b111, 0)).nzp, NZP_N | NZP_Z | NZP_P)

    def test_offset_limits(self):
        cases = ((0x00, 0), (0x01, 1), (0x7F, 127),
                 (0x80, -128), (0xFE, -2), (0xFF, -1))
        for raw, expected in cases:
            with self.subTest(raw=hex(raw)):
                d = decode(word_br(0b111, raw))
                self.assertEqual(d.offset, expected)

    def test_offset_10000000_is_minus_128(self):
        d = decode(word_br(0b111, 0b10000000))
        self.assertEqual(d.offset, -128)

    def test_nzp_zero_is_accepted(self):
        d = decode(word_br(0b000, 3))
        self.assertEqual(d.nzp, 0)
        self.assertEqual(d.offset, 3)


# ----------------------------------------------------------------------
# JSR
# ----------------------------------------------------------------------
class TestJsr(unittest.TestCase):

    def test_offset_limits(self):
        cases = ((0x000, 0), (0x001, 1), (0x3FF, 1023),
                 (0x400, -1024), (0x7FE, -2), (0x7FF, -1))
        for raw, expected in cases:
            with self.subTest(raw=hex(raw)):
                d = decode(word_jsr(raw))
                self.assertEqual(d.mnemonic, "JSR")
                self.assertEqual(d.fmt, Format.JSR)
                self.assertEqual(d.offset, expected)

    def test_offset_all_ones_is_minus_one(self):
        d = decode(word_jsr(0b111_1111_1111))
        self.assertEqual(d.offset, -1)


# ----------------------------------------------------------------------
# JMP y JSRR
# ----------------------------------------------------------------------
class TestJumpReg(unittest.TestCase):

    def test_jmp_base_register(self):
        for base in range(8):
            with self.subTest(base=base):
                d = decode(word_jump_reg("JMP", base))
                self.assertEqual(d.mnemonic, "JMP")
                self.assertEqual(d.fmt, Format.JUMP_REG)
                self.assertEqual(d.base, base)

    def test_jsrr_base_register(self):
        for base in range(8):
            with self.subTest(base=base):
                d = decode(word_jump_reg("JSRR", base))
                self.assertEqual(d.mnemonic, "JSRR")
                self.assertEqual(d.base, base)

    def test_zero_field_must_be_zero(self):
        for mnemonic in ("JMP", "JSRR"):
            for zeros in (0x01, 0x10, 0x80, 0xFF):
                with self.subTest(mnemonic=mnemonic, zeros=hex(zeros)):
                    with self.assertRaises(ReservedFieldError):
                        decode(word_jump_reg(mnemonic, 7, zeros))


# ----------------------------------------------------------------------
# LEA
# ----------------------------------------------------------------------
class TestLea(unittest.TestCase):

    def test_lea_fields(self):
        d = decode(word_lea(2, 0x10))
        self.assertEqual(d.mnemonic, "LEA")
        self.assertEqual(d.fmt, Format.LEA)
        self.assertEqual((d.dr, d.offset), (2, 16))

    def test_lea_offset_limits(self):
        for raw, expected in ((0x00, 0), (0x7F, 127), (0x80, -128), (0xFF, -1)):
            with self.subTest(raw=hex(raw)):
                d = decode(word_lea(1, raw))
                self.assertEqual(d.offset, expected)


# ----------------------------------------------------------------------
# TRAP
# ----------------------------------------------------------------------
class TestTrap(unittest.TestCase):

    def test_known_vectors(self):
        for vector in (0x20, 0x21, 0x22, 0x25):
            with self.subTest(vector=hex(vector)):
                d = decode(word_trap(vector))
                self.assertEqual(d.mnemonic, "TRAP")
                self.assertEqual(d.fmt, Format.TRAP)
                self.assertEqual(d.vector, vector)

    def test_all_256_vectors_decode(self):
        # El decodificador no valida que el servicio exista (eso es de la CPU).
        for vector in range(256):
            self.assertEqual(decode(word_trap(vector)).vector, vector)

    def test_zero_field_must_be_zero(self):
        for zeros in range(1, 8):
            with self.subTest(zeros=bin(zeros)):
                with self.assertRaises(ReservedFieldError):
                    decode(word_trap(0x25, zeros))


# ----------------------------------------------------------------------
# NOP y HALT
# ----------------------------------------------------------------------
class TestNopHalt(unittest.TestCase):

    def test_literal_encodings(self):
        nop = decode(0xB800)       # 10111 00000000000
        halt = decode(0xC000)      # 11000 00000000000
        self.assertEqual(nop.mnemonic, "NOP")
        self.assertEqual(halt.mnemonic, "HALT")
        self.assertEqual(nop.fmt, Format.NO_OPERANDS)
        self.assertEqual(halt.fmt, Format.NO_OPERANDS)

    def test_zero_field_must_be_zero(self):
        for mnemonic in ("NOP", "HALT"):
            for zeros in (0x001, 0x010, 0x400, 0x7FF):
                with self.subTest(mnemonic=mnemonic, zeros=hex(zeros)):
                    with self.assertRaises(ReservedFieldError):
                        decode(word_implicit(mnemonic, zeros))


# ----------------------------------------------------------------------
# Solo se informan los campos que existen
# ----------------------------------------------------------------------
class TestFieldPresence(unittest.TestCase):

    def test_only_relevant_fields_are_present(self):
        cases = [
            (0x0000, {"dr", "sr1", "mode", "sr2"}),   # ADD R0,R0,R0: ceros != None
            (word_a("ADD", 1, 2, 0, 0b0011), {"dr", "sr1", "mode", "sr2"}),
            (word_a("ADD", 1, 2, 1, 0b0101), {"dr", "sr1", "mode", "imm"}),
            (word_a("NOT", 1, 2, 0, 0), {"dr", "sr1"}),
            (word_a("CMP", 0, 2, 0, 0b0011), {"sr1", "mode", "sr2"}),
            (word_a("CMP", 0, 2, 1, 0b0101), {"sr1", "mode", "imm"}),
            (word_a("SHL", 1, 2, 1, 0b0011), {"dr", "sr1", "mode", "imm"}),
            (word_b("LDW", 1, 2, 4), {"reg", "base", "offset"}),
            (word_br(0b101, 3), {"nzp", "offset"}),
            (word_jsr(3), {"offset"}),
            (word_jump_reg("JMP", 7), {"base"}),
            (word_jump_reg("JSRR", 2), {"base"}),
            (word_lea(1, 3), {"dr", "offset"}),
            (word_trap(0x21), {"vector"}),
            (word_implicit("NOP"), set()),
            (word_implicit("HALT"), set()),
        ]
        for word, expected in cases:
            with self.subTest(word=hex(word)):
                self.assertEqual(present_fields(decode(word)), expected)


# ----------------------------------------------------------------------
# El decodificador no tiene efectos secundarios
# ----------------------------------------------------------------------
class TestPurity(unittest.TestCase):

    def test_does_not_modify_registers_or_memory(self):
        regs = Registers()
        for i in range(8):
            regs.write(i, 0x1111 * (i + 1))
        regs.pc = 0x3000
        regs.ir = 0xABCD
        regs.update_nzp(0x8000)
        mem = Memory()
        mem.write_word(0x3000, 0x1234)
        mem.write_byte(0x4001, 0x7F)

        def snapshot():
            return (
                (regs.values(), regs.pc, regs.ir, regs.condition_codes),
                (mem.used_bytes, mem.written_addresses,
                 mem.read_word(0x3000), mem.read_byte(0x4001)),
            )

        before = snapshot()
        for mnemonic in OPCODES:
            decode(sample_word(mnemonic))
        for bad in (0xFFFF, 0xD000, word_a("CMP", 1, 0, 0, 0)):
            with self.assertRaises(InvalidInstructionError):
                decode(bad)
        self.assertEqual(snapshot(), before)

    def test_result_is_immutable(self):
        d = decode(0x0000)
        self.assertIsInstance(d, DecodedInstruction)
        with self.assertRaises(dataclasses.FrozenInstanceError):
            d.dr = 5

    def test_is_deterministic(self):
        for mnemonic in OPCODES:
            with self.subTest(mnemonic=mnemonic):
                word = sample_word(mnemonic)
                self.assertEqual(decode(word), decode(word))

    def test_exhaustive_all_65536_words(self):
        # Ninguna palabra debe provocar una excepción distinta de
        # InvalidInstructionError. Cantidad de codificaciones válidas:
        #   ADD SUB AND OR XOR : 5 x (8 DR x 8 SR1 x (8 reg + 16 imm)) = 7680
        #   NOT                : 8 x 8                                  =   64
        #   SHL SHR SAR        : 3 x (8 x 8 x 16)                       = 3072
        #   CMP                : 8 SR1 x (8 reg + 16 imm)               =  192
        #   LDW STW LDBL LDBH STBL STBH LDI STI : 8 x (8 x 8 x 32)      =16384
        #   BR JSR LEA         : 3 x 2048                               = 6144
        #   JMP JSRR           : 2 x 8                                  =   16
        #   TRAP               : 256                                    =  256
        #   NOP HALT           : 2                                      =    2
        #   Total                                                       =33810
        valid = 0
        for word in range(0x10000):
            try:
                d = decode(word)
            except InvalidInstructionError:
                continue
            valid += 1
            self.assertEqual(d.word, word)
            self.assertEqual(d.opcode, word >> 11)
            self.assertLessEqual(d.opcode, 25)
        self.assertEqual(valid, 33810)


if __name__ == "__main__":
    unittest.main()
