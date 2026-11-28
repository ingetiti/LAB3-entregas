"""Pruebas de assembler/encoder.py (ejecutar desde la carpeta raíz Lab3C).

Las palabras esperadas están calculadas a mano y escritas como literales binarios
agrupados por campo (por ejemplo "00000_001_010_0_0011" = ADD R1, R2, R3); ninguna
expectativa se genera con el código que se prueba. Además el codificador se
contrasta con DOS módulos independientes de él:
  - el decoder real (el codificador debe ser su inverso exacto), y
  - la CPU real (los programas ensamblados se ejecutan).
Los programas se escriben de dos formas: como texto, pasando por parse_program y
build_symbol_table, o armados a mano (ParsedLine) para casos que el parser ya
rechaza y que el codificador debe seguir detectando por su cuenta.
"""

import ast
import dataclasses
import inspect
import io
import unittest
from pathlib import Path
from types import MappingProxyType

from assembler import encoder as encoder_module
from assembler.encoder import (
    EncodedProgram,
    EncodeError,
    EncodeErrors,
    encode_program,
)
from assembler.parser import (
    BlkwDirective,
    FillDirective,
    Immediate,
    Instruction,
    LabelRef,
    OrigDirective,
    ParsedLine,
    Program,
    Register,
    Statement,
    StringzDirective,
    normalize_mnemonic,
    parse_program,
)
from assembler.symbols import Padding, build_symbol_table
from simulator.cpu import CPU
from simulator.decoder import decode
from simulator.isa import INSTRUCTIONS_BY_MNEMONIC
from simulator.traps import ConsoleIO


# ----------------------------------------------------------------------
# Utilidades
# ----------------------------------------------------------------------
def bits(text):
    """'00000_001_010_0_0011' -> 0b0000000100100011 (los '_' solo separan campos)."""
    value = int(text.replace("_", ""), 2)
    assert len(text.replace("_", "")) == 16, f"se esperaban 16 bits: {text}"
    return value


def source(*lines):
    return "\n".join(lines)


def assemble(*lines, externals=None):
    """Texto -> parse_program -> build_symbol_table -> encode_program."""
    program = parse_program(source(*lines))
    return encode_program(program, build_symbol_table(program), externals)


def words(encoded):
    """Palabras Little Endian completas del programa (un byte final suelto se ignora)."""
    data = encoded.data
    return [data[i] | (data[i + 1] << 8) for i in range(0, len(data) - 1, 2)]


def one(line, origin="x3000", externals=None):
    """Palabra de UNA instrucción escrita en Assembly."""
    declarations = [f".EXTERNAL {name}" for name in (externals or {})]
    result = words(assemble(f".ORIG {origin}", *declarations, line, ".END",
                            externals=externals))
    assert len(result) == 1, result
    return result[0]


def prog(*items):
    """Program armado a mano. items = (etiqueta o None, sentencia o None)."""
    return Program(tuple(
        ParsedLine(number, f"<línea {number}>", label, statement)
        for number, (label, statement) in enumerate(items, start=1)
    ))


def encode_items(*items, externals=None):
    program = prog(*items)
    return encode_program(program, build_symbol_table(program), externals)


def R(number):
    return Register(number)


def I(value):  # noqa: E741 (nombre corto a propósito: es un helper de pruebas)
    return Immediate(value)


def L(name):
    return LabelRef(name)


ORIG = (None, OrigDirective(0x3000))


def encode_instruction(instruction, origin=0x3000):
    """Palabra de una Instruction armada a mano (sin pasar por el parser)."""
    result = encode_items((None, OrigDirective(origin)), (None, instruction))
    return words(result)[0]


class EncoderTestCase(unittest.TestCase):

    def assertEncodeErrors(self, call, expected):
        """`call()` debe lanzar EncodeErrors con (línea, fragmento) en ESE orden."""
        with self.assertRaises(EncodeErrors) as context:
            call()
        errors = context.exception.errors
        self.assertEqual([e.line_number for e in errors], [line for line, _ in expected],
                         f"líneas de los errores: {[str(e) for e in errors]}")
        for error, (_, fragment) in zip(errors, expected):
            self.assertIn(fragment, error.message)
        return errors

    def assertSingleError(self, call, line, fragment):
        return self.assertEncodeErrors(call, [(line, fragment)])[0]


# ----------------------------------------------------------------------
# 1. Formato A (palabras calculadas a mano)
# ----------------------------------------------------------------------
FORMAT_A_CASES = (
    ("ADD R1, R2, R3", "00000_001_010_0_0011"),
    ("ADD R1, R2, #-1", "00000_001_010_1_1111"),
    ("ADD R0, R0, #0", "00000_000_000_1_0000"),
    ("ADD R3, R3, #7", "00000_011_011_1_0111"),
    ("ADD R3, R3, #-8", "00000_011_011_1_1000"),
    ("SUB R7, R0, #7", "00001_111_000_1_0111"),
    ("SUB R4, R5, R6", "00001_100_101_0_0110"),
    ("AND R0, R0, #-8", "00010_000_000_1_1000"),
    ("OR R3, R4, R5", "00011_011_100_0_0101"),
    ("XOR R5, R6, R7", "00100_101_110_0_0111"),
    ("NOT R2, R3", "00101_010_011_0_0000"),
    ("SHL R1, R2, #15", "00110_001_010_1_1111"),
    ("SHR R1, R2, #0", "00111_001_010_1_0000"),
    ("SAR R4, R4, #8", "01000_100_100_1_1000"),     # 8 SIN signo: no es -8
    ("CMP R3, R4", "01001_000_011_0_0100"),
    ("CMP R3, #-2", "01001_000_011_1_1110"),
    ("CMP R0, #7", "01001_000_000_1_0111"),
    ("ADD SP, SP, #-2", "00000_110_110_1_1110"),    # SP = R6
    ("ADD LR, LR, #1", "00000_111_111_1_0001"),     # LR = R7
    ("add r1, r2, r3", "00000_001_010_0_0011"),     # sin distinguir mayúsculas
)

FORMAT_B_CASES = (
    ("LDW R1, R2, #0", "01010_001_010_00000"),
    ("STW R3, R4, #-16", "01011_011_100_10000"),
    ("LDBL R0, R7, #15", "01100_000_111_01111"),
    ("LDBH R5, R6, #-1", "01101_101_110_11111"),
    ("STBL R1, R1, #1", "01110_001_001_00001"),
    ("STBH R2, R3, #2", "01111_010_011_00010"),
    ("LDI R6, R5, #-2", "10100_110_101_11110"),
    ("STI R0, R0, #3", "10101_000_000_00011"),
)

CONTROL_CASES = (
    ("JMP R3", "10010_011_00000000"),
    ("JMP LR", "10010_111_00000000"),
    ("JSRR R7", "11001_111_00000000"),
    ("TRAP x25", "10110_00100101_000"),
    ("TRAP x00", "10110_00000000_000"),
    ("TRAP xFF", "10110_11111111_000"),
    ("NOP", "10111_00000000000"),
    ("HALT", "11000_00000000000"),
    ("BR #0", "10000_111_00000000"),
    ("BRn #-1", "10000_100_11111111"),
    ("BRz #127", "10000_010_01111111"),
    ("BRp #-128", "10000_001_10000000"),
    ("BRnz #1", "10000_110_00000001"),
    ("BRzp #2", "10000_011_00000010"),
    ("BRnp #3", "10000_101_00000011"),
    ("BRnzp #4", "10000_111_00000100"),
    ("JSR #0", "10001_00000000000"),
    ("JSR #-1", "10001_11111111111"),
    ("JSR #1023", "10001_01111111111"),
    ("JSR #-1024", "10001_10000000000"),
    ("LEA R7, #0", "10011_111_00000000"),
    ("LEA R2, #127", "10011_010_01111111"),
    ("LEA R2, #-128", "10011_010_10000000"),
)


class TestInstructionWords(EncoderTestCase):

    def test_format_a(self):
        for line, expected in FORMAT_A_CASES:
            with self.subTest(line):
                self.assertEqual(one(line), bits(expected))

    def test_format_b(self):
        for line, expected in FORMAT_B_CASES:
            with self.subTest(line):
                self.assertEqual(one(line), bits(expected))

    def test_control_system_and_numeric_offsets(self):
        for line, expected in CONTROL_CASES:
            with self.subTest(line):
                self.assertEqual(one(line), bits(expected))

    def test_every_instruction_of_the_isa_has_an_example(self):
        covered = set()
        for line, _ in FORMAT_A_CASES + FORMAT_B_CASES + CONTROL_CASES:
            covered.add(normalize_mnemonic(line.split()[0])[0])
        self.assertEqual(covered, set(INSTRUCTIONS_BY_MNEMONIC))
        self.assertEqual(len(covered), 26)

    def test_the_word_is_emitted_little_endian(self):
        # HALT = 0xC000 -> primero el byte bajo (0x00) y luego el alto (0xC0).
        self.assertEqual(assemble(".ORIG x3000", "HALT").data, b"\x00\xC0")
        # ADD R1, R2, R3 = 00000_001_010_0_0011 = 0x0143 -> 43 01
        self.assertEqual(assemble(".ORIG x3000", "ADD R1, R2, R3").data, b"\x43\x01")

    def test_unused_fields_are_zero_so_the_decoder_accepts_them(self):
        # NOT: M y OP2 en 0. CMP: DR en 0. JMP/JSRR/TRAP/NOP/HALT: reservados en 0.
        for line in ("NOT R1, R2", "CMP R1, R2", "CMP R1, #3", "JMP R1", "JSRR R1",
                     "TRAP x20", "NOP", "HALT"):
            with self.subTest(line):
                decode(one(line))            # lanza ReservedFieldError si falla


# ----------------------------------------------------------------------
# 2. El codificador es el INVERSO del decoder (verificación cruzada)
# ----------------------------------------------------------------------
def encode_many(instructions):
    """Todas las instrucciones en un solo programa; devuelve la lista de palabras."""
    items = [ORIG] + [(None, instruction) for instruction in instructions]
    return words(encode_items(*items))


class TestRoundTripWithDecoder(EncoderTestCase):

    def test_format_a_register_and_immediate_modes_exhaustively(self):
        for mnemonic in ("ADD", "SUB", "AND", "OR", "XOR"):
            cases = []
            for dr in range(8):
                for sr1 in range(8):
                    for sr2 in range(8):
                        cases.append(("reg", dr, sr1, sr2,
                                      Instruction(mnemonic, (R(dr), R(sr1), R(sr2)))))
                    for imm in range(-8, 8):
                        cases.append(("imm", dr, sr1, imm,
                                      Instruction(mnemonic, (R(dr), R(sr1), I(imm)))))
            for (kind, dr, sr1, last, _), word in zip(cases, encode_many(c[4] for c in cases)):
                decoded = decode(word)
                self.assertEqual((decoded.mnemonic, decoded.dr, decoded.sr1),
                                 (mnemonic, dr, sr1), hex(word))
                if kind == "reg":
                    self.assertEqual((decoded.mode, decoded.sr2), (0, last), hex(word))
                else:
                    self.assertEqual((decoded.mode, decoded.imm), (1, last), hex(word))

    def test_not_shifts_and_cmp_exhaustively(self):
        cases = [Instruction("NOT", (R(d), R(s))) for d in range(8) for s in range(8)]
        for decoded, case in zip(map(decode, encode_many(cases)), cases):
            self.assertEqual((decoded.mnemonic, decoded.dr, decoded.sr1),
                             ("NOT", case.operands[0].number, case.operands[1].number))
        for mnemonic in ("SHL", "SHR", "SAR"):
            cases = [(d, s, n) for d in range(8) for s in range(8) for n in range(16)]
            built = [Instruction(mnemonic, (R(d), R(s), I(n))) for d, s, n in cases]
            for (d, s, n), word in zip(cases, encode_many(built)):
                decoded = decode(word)
                self.assertEqual((decoded.mnemonic, decoded.dr, decoded.sr1, decoded.imm),
                                 (mnemonic, d, s, n))
        cases = [Instruction("CMP", (R(s), R(t))) for s in range(8) for t in range(8)]
        cases += [Instruction("CMP", (R(s), I(n))) for s in range(8) for n in range(-8, 8)]
        for case, word in zip(cases, encode_many(cases)):
            decoded = decode(word)
            self.assertEqual(decoded.mnemonic, "CMP")
            self.assertIsNone(decoded.dr)
            self.assertEqual(decoded.sr1, case.operands[0].number)
            second = case.operands[1]
            if isinstance(second, Register):
                self.assertEqual((decoded.mode, decoded.sr2), (0, second.number))
            else:
                self.assertEqual((decoded.mode, decoded.imm), (1, second.value))

    def test_format_b_exhaustively(self):
        for mnemonic in ("LDW", "STW", "LDBL", "LDBH", "STBL", "STBH", "LDI", "STI"):
            cases = [(r, b, o) for r in range(8) for b in range(8) for o in range(-16, 16)]
            built = [Instruction(mnemonic, (R(r), R(b), I(o))) for r, b, o in cases]
            for (r, b, o), word in zip(cases, encode_many(built)):
                decoded = decode(word)
                self.assertEqual((decoded.mnemonic, decoded.reg, decoded.base, decoded.offset),
                                 (mnemonic, r, b, o), hex(word))

    def test_jumps_lea_trap_and_branch_masks_exhaustively(self):
        for mnemonic in ("JMP", "JSRR"):
            built = [Instruction(mnemonic, (R(b),)) for b in range(8)]
            for b, word in enumerate(encode_many(built)):
                decoded = decode(word)
                self.assertEqual((decoded.mnemonic, decoded.base), (mnemonic, b))
        built = [Instruction("TRAP", (I(v),)) for v in range(256)]
        for v, word in enumerate(encode_many(built)):
            self.assertEqual(decode(word).vector, v)
        cases = [(d, o) for d in range(8) for o in range(-128, 128)]
        built = [Instruction("LEA", (R(d), I(o))) for d, o in cases]
        for (d, o), word in zip(cases, encode_many(built)):
            decoded = decode(word)
            self.assertEqual((decoded.mnemonic, decoded.dr, decoded.offset), ("LEA", d, o))
        cases = [(n, o) for n in range(8) for o in range(-128, 128)]
        built = [Instruction("BR", (I(o),), nzp=n) for n, o in cases]
        for (n, o), word in zip(cases, encode_many(built)):
            decoded = decode(word)
            self.assertEqual((decoded.mnemonic, decoded.nzp, decoded.offset), ("BR", n, o))
        built = [Instruction("JSR", (I(o),)) for o in range(-1024, 1024)]
        for o, word in zip(range(-1024, 1024), encode_many(built)):
            decoded = decode(word)
            self.assertEqual((decoded.mnemonic, decoded.offset), ("JSR", o))

    def test_no_operand_instructions(self):
        for mnemonic in ("NOP", "HALT"):
            self.assertEqual(decode(encode_many([Instruction(mnemonic, ())])[0]).mnemonic,
                             mnemonic)


# ----------------------------------------------------------------------
# 3. Etiquetas y desplazamientos relativos al PC (calculados a mano)
# ----------------------------------------------------------------------
class TestPcRelativeLabels(EncoderTestCase):

    def test_branch_forward_backward_and_to_itself(self):
        # BR en x3000, L en x3004: PC siguiente = x3002, +2 bytes = +1 palabra.
        forward = assemble(".ORIG x3000", "BR L", "NOP", "L: HALT", ".END")
        self.assertEqual(words(forward)[0], bits("10000_111_00000001"))
        # L: BR L -> destino = x3000, PC siguiente = x3002: -2 bytes = -1 palabra.
        self_loop = assemble(".ORIG x3000", "L: BR L", ".END")
        self.assertEqual(words(self_loop)[0], bits("10000_111_11111111"))
        # BRz en x3006, L en x3002: PC siguiente = x3008, -6 bytes = -3 palabras.
        backward = assemble(".ORIG x3000", "NOP", "L: ADD R1, R1, #1", "NOP",
                            "BRz L", ".END")
        self.assertEqual(words(backward)[3], bits("10000_010_11111101"))

    def test_jsr_forward_and_backward(self):
        forward = assemble(".ORIG x3000", "JSR F", "HALT", "F: NOP", ".END")
        self.assertEqual(words(forward)[0], bits("10001_00000000001"))
        backward = assemble(".ORIG x3000", "F: NOP", "JSR F", ".END")
        self.assertEqual(words(backward)[1], bits("10001_11111111110"))

    def test_lea_offset_is_in_bytes(self):
        # D en x3004; PC siguiente = x3002 -> +2 BYTES (no palabras).
        result = assemble(".ORIG x3000", "LEA R3, D", "HALT", "D: .FILL #7", ".END")
        self.assertEqual(words(result)[0], bits("10011_011_00000010"))

    def test_lea_accepts_an_odd_target(self):
        # S queda en x3005 (dirección impar, es un dato): offset = x3005 - x3002 = 3.
        result = assemble(".ORIG x3000", "LEA R0, S", "HALT", '.STRINGZ ""',
                          'S: .STRINGZ "Z"', ".END")
        self.assertEqual(words(result)[0], bits("10011_000_00000011"))

    def test_a_label_on_an_aligned_instruction_points_past_the_padding(self):
        # "AB" ocupa x3002..x3004; el relleno está en x3005; START queda en x3006.
        # BR START en x3000: PC siguiente x3002, +4 bytes = +2 palabras.
        result = assemble(".ORIG x3000", "BR START", 'MSG: .STRINGZ "AB"',
                          "START: HALT", ".END")
        self.assertEqual(words(result)[0], bits("10000_111_00000010"))

    def test_branch_reach_limits(self):
        # BR: 8 bits con signo en palabras: -128..+127.
        far = assemble(".ORIG x3000", "BR T", ".BLKW #127", "T: NOP", ".END")      # T=x3100
        self.assertEqual(words(far)[0], bits("10000_111_01111111"))
        near = assemble(".ORIG x3000", "T: NOP", ".BLKW #126", "BR T", ".END")     # -128
        self.assertEqual(words(near)[-1], bits("10000_111_10000000"))
        too_far = source(".ORIG x3000", "BR T", ".BLKW #128", "T: NOP", ".END")    # +128
        error = self.assertSingleError(lambda: assemble(too_far), 2, "fuera de alcance")
        self.assertIn("128 palabras", error.message)
        self.assertIn("-128 a 127", error.message)
        too_near = source(".ORIG x3000", "T: NOP", ".BLKW #127", "BR T", ".END")   # -129
        self.assertSingleError(lambda: assemble(too_near), 4, "-129 palabras")

    def test_jsr_reach_limits(self):
        # JSR: 11 bits con signo en palabras: -1024..+1023.
        far = assemble(".ORIG x3000", "JSR T", ".BLKW #1023", "T: NOP", ".END")
        self.assertEqual(words(far)[0], bits("10001_01111111111"))
        near = assemble(".ORIG x3000", "T: NOP", ".BLKW #1022", "JSR T", ".END")
        self.assertEqual(words(near)[-1], bits("10001_10000000000"))
        self.assertSingleError(
            lambda: assemble(".ORIG x3000", "JSR T", ".BLKW #1024", "T: NOP", ".END"),
            2, "1024 palabras")
        self.assertSingleError(
            lambda: assemble(".ORIG x3000", "T: NOP", ".BLKW #1023", "JSR T", ".END"),
            4, "-1025 palabras")

    def test_lea_reach_limits(self):
        # LEA: 8 bits con signo en BYTES: -128..+127.
        far = assemble(".ORIG x3000", "LEA R0, T", ".BLKW #63", '.STRINGZ ""',
                       'T: .STRINGZ "Z"', ".END")                                  # T=x3081
        self.assertEqual(words(far)[0], bits("10011_000_01111111"))
        near = assemble(".ORIG x3000", "T: .BLKW #63", "LEA R0, T", ".END")         # -128
        self.assertEqual(words(near)[-1], bits("10011_000_10000000"))
        too_far = source(".ORIG x3000", "LEA R0, T", ".BLKW #63", '.STRINGZ "A"',
                         'T: .STRINGZ "Z"', ".END")                                # T=x3082
        error = self.assertSingleError(lambda: assemble(too_far), 2, "128 bytes")
        self.assertIn("-128 a 127", error.message)
        self.assertSingleError(
            lambda: assemble(".ORIG x3000", "T: .BLKW #64", "LEA R0, T", ".END"),
            3, "-130 bytes")

    def test_branch_and_jsr_to_an_odd_address_are_rejected(self):
        for mnemonic in ("BR", "JSR"):
            with self.subTest(mnemonic):
                text = source(".ORIG x3000", f"{mnemonic} S", "HALT", '.STRINGZ ""',
                              'S: .STRINGZ "Z"', ".END")                           # S=x3005
                error = self.assertSingleError(lambda: assemble(text), 2, "dirección impar")
                self.assertIn("x3005", error.message)

    def test_numeric_offsets_are_used_as_they_are(self):
        self.assertEqual(one("BR #-5"), bits("10000_111_11111011"))
        self.assertEqual(one("JSR #100"), bits("10001_00001100100"))
        self.assertEqual(one("LEA R1, #-2"), bits("10011_001_11111110"))

    def test_the_result_matches_the_cpu_formula_for_every_reachable_offset(self):
        # Oráculo independiente: se elige el offset k, se calcula el destino con la
        # fórmula de la CPU y se comprueba que el codificador recupere k. Incluye
        # orígenes cerca del final de la memoria, donde el PC siguiente da la vuelta.
        for origin in (0x0000, 0x3000, 0xFFFC, 0xFFFE):
            next_pc = (origin + 2) & 0xFFFF
            for mnemonic, unit, limit, step in (("BR", 2, 128, 1), ("JSR", 2, 1024, 7),
                                                ("LEA", 1, 128, 1)):
                for k in range(-limit - 3, limit + 3, step):
                    target = (next_pc + unit * k) & 0xFFFF
                    if unit == 2 and target % 2:
                        continue
                    line = "LEA R0, X" if mnemonic == "LEA" else f"{mnemonic} X"
                    inside = -limit <= k < limit
                    with self.subTest(origin=origin, mnemonic=mnemonic, k=k):
                        if inside:
                            decoded = decode(self._assemble_with_x(line, origin, target))
                            self.assertEqual(decoded.offset, k)
                        else:
                            with self.assertRaises(EncodeErrors):
                                self._assemble_with_x(line, origin, target)

    @staticmethod
    def _assemble_with_x(line, origin, target):
        result = assemble(f".ORIG x{origin:04X}", ".EXTERNAL X", line, ".END",
                          externals={"X": target})
        return words(result)[0]

    def test_pc_wraps_around_at_the_end_of_memory(self):
        # En xFFFE el PC siguiente es x0000 (módulo 65536), igual que en la CPU.
        for target, expected in ((0x0000, "10000_111_00000000"),
                                 (0x0010, "10000_111_00001000"),
                                 (0xFFF0, "10000_111_11111000")):
            with self.subTest(hex(target)):
                result = assemble(".ORIG xFFFE", ".EXTERNAL X", "BR X", ".END",
                                  externals={"X": target})
                self.assertEqual(words(result)[0], bits(expected))
        # Desde x0000 (PC siguiente x0002) hasta xFFF0: -18 bytes = -9 palabras.
        result = assemble(".ORIG x0000", ".EXTERNAL X", "BR X", ".END",
                          externals={"X": 0xFFF0})
        self.assertEqual(words(result)[0], bits("10000_111_11110111"))
        # Una etiqueta local en la última instrucción: L: BR L en xFFFE.
        result = assemble(".ORIG xFFFE", "L: BR L", ".END")
        self.assertEqual(words(result)[0], bits("10000_111_11111111"))
        self.assertEqual(result.end_address, 0x10000)


# ----------------------------------------------------------------------
# 4. Directivas
# ----------------------------------------------------------------------
class TestDirectives(EncoderTestCase):

    def test_fill_numbers(self):
        for text, expected in (("#5", b"\x05\x00"), ("#-1", b"\xFF\xFF"),
                               ("x1234", b"\x34\x12"), ("#-32768", b"\x00\x80"),
                               ("xFFFF", b"\xFF\xFF"), ("#0", b"\x00\x00"),
                               ("#32767", b"\xFF\x7F")):
            with self.subTest(text):
                self.assertEqual(assemble(".ORIG x3000", f".FILL {text}").data, expected)

    def test_fill_out_of_range_is_detected_even_without_the_parser(self):
        for value in (65536, -32769, 1 << 20):
            with self.subTest(value):
                self.assertSingleError(
                    lambda: encode_items(ORIG, (None, FillDirective(I(value)))),
                    2, "fuera de rango")

    def test_fill_with_a_local_label_is_the_absolute_address(self):
        result = assemble(".ORIG x3000", ".FILL L", "L: HALT", ".END")
        self.assertEqual(result.data, b"\x02\x30\x00\xC0")      # L = x3002

    def test_fill_with_an_external_label(self):
        result = assemble(".ORIG x3000", ".EXTERNAL X", ".FILL X", externals={"X": 0xABCD})
        self.assertEqual(result.data, b"\xCD\xAB")

    def test_fill_with_a_label_at_the_end_of_a_full_memory_is_rejected(self):
        # L vale x10000: dirección exclusiva, no cabe en 16 bits.
        error = self.assertSingleError(
            lambda: assemble(".ORIG xFFFE", ".FILL L", "L: .END"), 2, "x10000")
        self.assertIn("'L'", error.message)

    def test_blkw_reserves_zeroed_words(self):
        self.assertEqual(assemble(".ORIG x3000", ".BLKW #3").data, bytes(6))
        self.assertEqual(assemble(".ORIG x3000", ".BLKW #1").data, bytes(2))

    def test_stringz(self):
        for text, expected in (('"Hi"', b"Hi\x00"), ('""', b"\x00"), ('"A"', b"A\x00"),
                               ('"a\\nb"', b"a\nb\x00"), ('"\\""', b'"\x00')):
            with self.subTest(text):
                self.assertEqual(assemble(".ORIG x3000", f".STRINGZ {text}").data, expected)

    def test_stringz_characters_must_fit_in_one_nonzero_byte(self):
        self.assertEqual(
            encode_items(ORIG, (None, StringzDirective("\xFF"))).data, b"\xFF\x00")
        for text in ("\u20AC", "\u0100", "a\x00b"):
            with self.subTest(repr(text)):
                self.assertSingleError(
                    lambda: encode_items(ORIG, (None, StringzDirective(text))),
                    2, ".STRINGZ")

    def test_alignment_padding_is_a_zero_byte_before_the_instruction(self):
        # "AB" + 0 = 3 bytes (x3000..x3002); relleno en x3003; NOP = x00B8 en x3004.
        result = assemble(".ORIG x3000", '.STRINGZ "AB"', "NOP", ".END")
        self.assertEqual(result.data, b"AB\x00" + b"\x00" + b"\x00\xB8")
        self.assertEqual(result.size, 6)

    def test_data_is_not_aligned(self):
        # Un .FILL después de una cadena impar empieza en dirección impar, sin relleno.
        result = assemble(".ORIG x3000", '.STRINGZ "AB"', ".FILL #1", ".END")
        self.assertEqual(result.data, b"AB\x00" + b"\x01\x00")

    def test_orig_end_and_external_generate_no_bytes(self):
        result = assemble(".ORIG x4000", ".EXTERNAL X", ".END")
        self.assertEqual(result.data, b"")
        self.assertEqual((result.origin, result.size, result.end_address),
                         (0x4000, 0, 0x4000))

    def test_labels_alone_and_blank_lines_do_not_generate_bytes(self):
        result = assemble(".ORIG x3000", "A:", "", "; comentario", "B: NOP", ".END")
        self.assertEqual(result.data, b"\x00\xB8")

    def test_a_program_mixing_everything(self):
        result = assemble(
            ".ORIG x3000",
            "START: LEA R0, MSG",     # x3000
            "       TRAP x22",        # x3002
            "       HALT",            # x3004
            'MSG:   .STRINGZ "Ok"',   # x3006..x3008
            "TAIL:  .FILL TAIL",      # x3009 (dato, sin alinear)
            ".END")
        self.assertEqual(result.data,
                         b"\x04\x98"          # LEA R0,#4  (x3006 - x3002) -> 10011_000_00000100
                         b"\x10\xB1"          # TRAP x22
                         b"\x00\xC0"          # HALT
                         b"Ok\x00"
                         b"\x09\x30")         # TAIL = x3009


# ----------------------------------------------------------------------
# 5. Símbolos externos (política cerrada en 5.3.2)
# ----------------------------------------------------------------------
class TestExternalSymbols(EncoderTestCase):

    def test_branch_jsr_and_lea_with_externals(self):
        # BR en x3000, X = x3010: PC siguiente x3002, +14 bytes = +7 palabras.
        self.assertEqual(one("BR X", externals={"X": 0x3010}), bits("10000_111_00000111"))
        self.assertEqual(one("JSR X", externals={"X": 0x3000}), bits("10001_11111111111"))
        # LEA a una dirección impar: X = x3003, PC siguiente x3002 -> +1 byte.
        self.assertEqual(one("LEA R0, X", externals={"X": 0x3003}),
                         bits("10011_000_00000001"))

    def assemble_with_x(self, line, address):
        return assemble(".ORIG x3000", ".EXTERNAL X", line, ".END", externals={"X": address})

    def test_an_unreachable_external_is_a_range_error(self):
        error = self.assertSingleError(lambda: self.assemble_with_x("JSR X", 0x9000),
                                       3, "fuera de alcance")
        self.assertIn("'X'", error.message)
        self.assertIn("x9000", error.message)
        self.assertSingleError(lambda: self.assemble_with_x("BR X", 0x3200), 3, "palabras")
        self.assertSingleError(lambda: self.assemble_with_x("LEA R0, X", 0x3200), 3, "bytes")

    def test_branch_to_an_odd_external_is_rejected_but_lea_accepts_it(self):
        self.assertSingleError(lambda: self.assemble_with_x("BR X", 0x3011), 3,
                               "dirección impar")
        self.assertSingleError(lambda: self.assemble_with_x("JSR X", 0x3011), 3,
                               "dirección impar")
        self.assemble_with_x("LEA R0, X", 0x3011)

    def test_a_used_external_without_an_address_is_an_error(self):
        text = (".ORIG x3000", ".EXTERNAL X", "BR X", ".END")
        for externals in (None, {}, {"Y": 1}):
            with self.subTest(externals):
                program = parse_program(source(*text))
                table = build_symbol_table(program)
                with self.assertRaises(EncodeErrors) as context:
                    encode_program(program, table, externals)
                self.assertTrue(any("'X'" in e.message and e.line_number == 3
                                    for e in context.exception.errors))

    def test_a_declared_but_unused_external_needs_no_address(self):
        result = assemble(".ORIG x3000", ".EXTERNAL UNUSED", "NOP", ".END")
        self.assertEqual(result.data, b"\x00\xB8")
        result = assemble(".ORIG x3000", ".EXTERNAL UNUSED", "NOP", ".END", externals={})
        self.assertEqual(result.data, b"\x00\xB8")

    def test_an_address_for_an_unused_external_is_harmless(self):
        result = assemble(".ORIG x3000", ".EXTERNAL U", "NOP", ".END", externals={"U": 5})
        self.assertEqual(result.data, b"\x00\xB8")

    def test_undeclared_keys_are_rejected(self):
        error = self.assertSingleError(
            lambda: assemble(".ORIG x3000", "NOP", ".END", externals={"GHOST": 0x3000}),
            None, "GHOST")
        self.assertIn(".EXTERNAL", error.message)

    def test_keys_that_override_local_symbols_are_rejected(self):
        error = self.assertSingleError(
            lambda: assemble(".ORIG x3000", ".EXTERNAL X", "L: NOP", ".END",
                             externals={"L": 0x4000}), None, "'L'")
        self.assertIn("local", error.message)

    def test_invalid_addresses_are_rejected(self):
        for bad in (True, False, -1, 0x10000, 1.5, "x3000", None, 3 + 0j):
            with self.subTest(repr(bad)):
                text = (".ORIG x3000", ".EXTERNAL X", "NOP", ".END")
                error = self.assertSingleError(
                    lambda: assemble(*text, externals={"X": bad}), None, "'X'")
                self.assertIn("x0000 a xFFFF", error.message)

    def test_valid_boundary_addresses_are_accepted(self):
        for address in (0, 1, 0xFFFF):
            with self.subTest(address):
                self.assertEqual(
                    assemble(".ORIG x3000", ".EXTERNAL X", ".FILL X", externals={"X": address}
                             ).data, address.to_bytes(2, "little"))

    def test_a_non_string_key_is_rejected(self):
        self.assertSingleError(
            lambda: assemble(".ORIG x3000", "NOP", ".END", externals={5: 1}), None, "5")

    def test_a_non_mapping_argument_is_a_type_error(self):
        program = parse_program(".ORIG x3000")
        table = build_symbol_table(program)
        for bad in ([("X", 1)], ("X", 1), "X", 5, {"X"}):
            with self.subTest(repr(bad)), self.assertRaises(TypeError):
                encode_program(program, table, bad)

    def test_any_read_only_mapping_is_accepted_and_not_modified(self):
        original = {"X": 0x3010}
        proxy = MappingProxyType(original)
        result = assemble(".ORIG x3000", ".EXTERNAL X", "BR X", ".END", externals=proxy)
        self.assertEqual(words(result)[0], bits("10000_111_00000111"))
        self.assertEqual(original, {"X": 0x3010})


# ----------------------------------------------------------------------
# 6. Errores: acumulación y mensajes
# ----------------------------------------------------------------------
class TestErrorReporting(EncoderTestCase):

    def test_independent_errors_are_all_reported_globals_first(self):
        text = source(
            ".ORIG x3000",            # 1
            ".EXTERNAL FAR",          # 2
            ".EXTERNAL NOADDR",       # 3
            "JSR FAR",                # 4  fuera de alcance
            "BR NOADDR",              # 5  sin dirección
            "NOP",                    # 6  (sin error)
            ".FILL NOADDR",           # 7  sin dirección
            ".END")                   # 8
        errors = self.assertEncodeErrors(
            lambda: assemble(text, externals={"FAR": 0x9000, "GHOST": 1}),
            [(None, "GHOST"), (4, "fuera de alcance"), (5, "NOADDR"), (7, "NOADDR")])
        self.assertEqual(errors[1].source, "JSR FAR")
        self.assertTrue(str(errors[1]).startswith("línea 4: "))
        self.assertFalse(str(errors[0]).startswith("línea"))

    def test_errors_exception_lists_every_error_in_its_message(self):
        with self.assertRaises(EncodeErrors) as context:
            encode_items(ORIG, (None, Instruction("ADD", (R(1), R(2), I(99)))),
                         (None, Instruction("SHL", (R(1), R(2), I(-1)))))
        text = str(context.exception)
        self.assertIn("2 error(es)", text)
        self.assertIn("línea 2", text)
        self.assertIn("línea 3", text)
        self.assertEqual(len(context.exception.errors), 2)

    def test_nothing_is_returned_when_there_are_errors(self):
        result = None
        with self.assertRaises(EncodeErrors):
            result = encode_items(ORIG, (None, Instruction("NOP", ())),
                                  (None, Instruction("TRAP", (I(256),))))
        self.assertIsNone(result)

    def test_errors_do_not_hide_errors_in_later_lines(self):
        # Un error en una línea no debe desordenar la verificación de las siguientes.
        self.assertEncodeErrors(
            lambda: encode_items(
                ORIG,
                (None, Instruction("ADD", (R(1), R(2), I(99)))),    # 2
                (None, Instruction("NOP", ())),                     # 3 ok
                (None, Instruction("TRAP", (I(-1),))),              # 4
                (None, FillDirective(I(70000))),                    # 5
            ),
            [(2, "fuera de rango"), (4, "fuera de rango"), (5, "fuera de rango")])

    def test_operand_range_errors_name_the_valid_range(self):
        cases = (
            (Instruction("ADD", (R(1), R(2), I(8))), "-8 a 7"),
            (Instruction("SUB", (R(1), R(2), I(-9))), "-8 a 7"),
            (Instruction("CMP", (R(1), I(8))), "-8 a 7"),
            (Instruction("SHL", (R(1), R(2), I(16))), "0 a 15"),
            (Instruction("SAR", (R(1), R(2), I(-1))), "0 a 15"),
            (Instruction("LDW", (R(1), R(2), I(16))), "-16 a 15"),
            (Instruction("STI", (R(1), R(2), I(-17))), "-16 a 15"),
            (Instruction("BR", (I(128),), nzp=7), "-128 a 127"),
            (Instruction("BR", (I(-129),), nzp=7), "-128 a 127"),
            (Instruction("JSR", (I(1024),)), "-1024 a 1023"),
            (Instruction("JSR", (I(-1025),)), "-1024 a 1023"),
            (Instruction("LEA", (R(0), I(128))), "-128 a 127"),
            (Instruction("LEA", (R(0), I(-129))), "-128 a 127"),
            (Instruction("TRAP", (I(256),)), "0 a 255"),
            (Instruction("TRAP", (I(-1),)), "0 a 255"),
        )
        for instruction, fragment in cases:
            with self.subTest(instruction):
                self.assertSingleError(
                    lambda: encode_items(ORIG, (None, instruction)), 2, fragment)

    def test_malformed_operands_are_detected_without_the_parser(self):
        cases = (
            Instruction("ADD", (R(8), R(1), R(2))),                     # registro inexistente
            Instruction("ADD", (R(-1), R(1), R(2))),
            Instruction("ADD", (R(True), R(1), R(2))),                  # bool no es entero
            Instruction("ADD", (I(1), R(1), R(2))),                     # inmediato por registro
            Instruction("SHL", (R(1), R(2), R(3))),                     # shift con registro
            Instruction("LDW", (R(1), R(2), R(3))),                     # offset registro
            Instruction("JMP", (I(3),)),
            Instruction("TRAP", (R(1),)),
            Instruction("BR", (R(1),), nzp=7),
            Instruction("JSR", (R(1),)),
            Instruction("LEA", (R(1), R(2))),
            Instruction("ADD", (R(1), R(2))),                           # faltan operandos
            Instruction("NOP", (R(0),)),                                # sobran operandos
            Instruction("FOO", ()),                                     # mnemónico inexistente
            Instruction("BR", (I(0),)),                                 # BR sin máscara nzp
            Instruction("BR", (I(0),), nzp=8),                          # máscara fuera de rango
            Instruction("BR", (I(0),), nzp=-1),
        )
        for instruction in cases:
            with self.subTest(instruction):
                self.assertSingleError(
                    lambda: encode_items(ORIG, (None, instruction)), 2, "")

    def test_a_label_where_a_register_or_number_is_expected_is_rejected(self):
        for instruction in (Instruction("ADD", (R(1), R(2), L("T"))),
                            Instruction("LDW", (R(1), R(2), L("T"))),
                            Instruction("SHL", (R(1), R(2), L("T"))),
                            Instruction("TRAP", (L("T"),)),
                            Instruction("JMP", (L("T"),))):
            with self.subTest(instruction):
                self.assertSingleError(
                    lambda: encode_items(ORIG, (None, instruction), ("T", Instruction("NOP", ()))),
                    2, "")

    def test_an_unknown_label_is_reported(self):
        # La tabla se calcula con la etiqueta L; el programa a codificar pide otra (M).
        table = build_symbol_table(prog(ORIG, (None, Instruction("BR", (L("L"),), nzp=7)),
                                        ("L", Instruction("NOP", ()))))
        other = prog(ORIG, (None, Instruction("BR", (L("M"),), nzp=7)),
                     ("L", Instruction("NOP", ())))
        error = self.assertSingleError(lambda: encode_program(other, table), 2, "no definido")
        self.assertIn("'M'", error.message)

    def test_an_unrecognized_statement_is_reported(self):
        class Strange(Statement):
            pass
        program = prog(ORIG, (None, Strange()))
        table = build_symbol_table(prog(ORIG))        # el layout no la conoce
        self.assertSingleError(lambda: encode_program(program, table), 2, "Strange")

    def test_blkw_with_a_bad_count_is_reported(self):
        # La tabla se calcula con un .BLKW válido; la sentencia a codificar está corrupta.
        table = build_symbol_table(prog(ORIG, (None, BlkwDirective(1))))
        for count in (0, -1, True, 1.5):
            with self.subTest(repr(count)):
                self.assertSingleError(
                    lambda: encode_program(prog(ORIG, (None, BlkwDirective(count))), table),
                    2, ".BLKW")


# ----------------------------------------------------------------------
# 7. Consistencia con el layout de SymbolTable (tablas alteradas a mano)
# ----------------------------------------------------------------------
class TestLayoutConsistency(EncoderTestCase):

    def setUp(self):
        self.two_nops = prog(ORIG, (None, Instruction("NOP", ())),
                             (None, Instruction("NOP", ())))
        self.two_table = build_symbol_table(self.two_nops)
        self.padded = prog(ORIG, (None, StringzDirective("AB")),
                           (None, Instruction("NOP", ())))
        self.padded_table = build_symbol_table(self.padded)

    def test_the_real_tables_are_consistent(self):
        self.assertEqual(encode_program(self.two_nops, self.two_table).size, 4)
        self.assertEqual(encode_program(self.padded, self.padded_table).size, 6)

    def test_a_table_built_from_a_shorter_program_is_rejected(self):
        shorter = build_symbol_table(prog(ORIG, (None, Instruction("NOP", ()))))
        self.assertSingleError(lambda: encode_program(self.two_nops, shorter),
                               3, "no tiene dirección")

    def test_a_table_built_from_a_longer_program_is_rejected(self):
        shorter_program = prog(ORIG, (None, Instruction("NOP", ())))
        self.assertEncodeErrors(
            lambda: encode_program(shorter_program, self.two_table),
            [(None, "línea 3"), (None, "termina")])

    def test_a_different_origin_is_rejected(self):
        table = dataclasses.replace(self.two_table, origin=0x4000)
        with self.assertRaises(EncodeErrors) as context:
            encode_program(self.two_nops, table)
        self.assertTrue(any(".ORIG" in e.message and e.line_number == 1
                            for e in context.exception.errors))

    def test_a_missing_padding_entry_is_rejected(self):
        table = dataclasses.replace(self.padded_table, padding=())
        self.assertSingleError(lambda: encode_program(self.padded, table), 3,
                               "sin relleno")

    def test_a_padding_entry_of_the_wrong_size_is_rejected(self):
        # El hueco real es de 1 byte (x3003); la tabla dice que el relleno son 2.
        table = dataclasses.replace(self.padded_table, padding=(Padding(0x3003, 2, 3),))
        self.assertSingleError(lambda: encode_program(self.padded, table), 3,
                               "sin relleno")

    def test_an_unused_padding_entry_is_rejected(self):
        table = dataclasses.replace(self.two_table, padding=(Padding(0x3004, 1, 3),))
        error = self.assertSingleError(lambda: encode_program(self.two_nops, table),
                                       3, "relleno")
        self.assertIn("x3004", error.message)

    def test_an_instruction_at_an_odd_address_is_rejected(self):
        table = dataclasses.replace(
            self.two_table, padding=(Padding(0x3002, 1, 3),),
            line_addresses={2: 0x3000, 3: 0x3003}, end_address=0x3005)
        self.assertSingleError(lambda: encode_program(self.two_nops, table), 3,
                               "dirección impar")

    def test_overlapping_statements_are_rejected(self):
        table = dataclasses.replace(self.two_table, line_addresses={2: 0x3000, 3: 0x3000})
        self.assertSingleError(lambda: encode_program(self.two_nops, table), 3,
                               "se superponen")

    def test_a_wrong_end_address_is_rejected(self):
        table = dataclasses.replace(self.two_table, end_address=0x3010)
        self.assertSingleError(lambda: encode_program(self.two_nops, table), None,
                               "termina en x3004")

    def test_a_gap_before_a_data_directive_is_rejected(self):
        # Los datos no se alinean: un hueco antes de un .FILL no puede ser relleno.
        program = prog(ORIG, (None, StringzDirective("AB")), (None, FillDirective(I(1))))
        table = build_symbol_table(program)
        bad = dataclasses.replace(
            table, line_addresses={2: 0x3000, 3: 0x3004},
            padding=(Padding(0x3003, 1, 3),), end_address=0x3006)
        self.assertSingleError(lambda: encode_program(program, bad), 3, "solo las instrucciones")
        self.assertEqual(encode_program(program, table).data, b"AB\x00\x01\x00")


# ----------------------------------------------------------------------
# 8. EncodedProgram y la API
# ----------------------------------------------------------------------
class TestEncodedProgram(EncoderTestCase):

    def test_fields_and_derived_values(self):
        result = EncodedProgram(0x3000, b"\x01\x02\x03\x04")
        self.assertEqual((result.origin, result.data, result.size, result.end_address),
                         (0x3000, b"\x01\x02\x03\x04", 4, 0x3004))

    def test_the_result_is_immutable(self):
        result = assemble(".ORIG x3000", "NOP")
        for name in ("origin", "data", "size", "end_address"):
            with self.subTest(name), self.assertRaises((dataclasses.FrozenInstanceError,
                                                        AttributeError)):
                setattr(result, name, 1)
        self.assertIsInstance(result.data, bytes)

    def test_a_bytearray_is_copied_into_immutable_bytes(self):
        buffer = bytearray(b"\x01\x02")
        result = EncodedProgram(0x3000, buffer)
        buffer[0] = 0xFF
        self.assertEqual(result.data, b"\x01\x02")
        self.assertIsInstance(result.data, bytes)

    def test_equality_and_hash(self):
        first = assemble(".ORIG x3000", "NOP")
        second = assemble(".ORIG x3000", "NOP")
        self.assertEqual(first, second)
        self.assertEqual(hash(first), hash(second))
        self.assertNotEqual(first, assemble(".ORIG x3000", "HALT"))
        self.assertNotEqual(first, assemble(".ORIG x3002", "NOP"))

    def test_invalid_construction_is_rejected(self):
        for origin in (0x3001, -2, 0x10000, 0xFFFF):
            with self.subTest(origin), self.assertRaises(ValueError):
                EncodedProgram(origin, b"")
        for origin in (True, 1.5, "x3000", None):
            with self.subTest(repr(origin)), self.assertRaises(TypeError):
                EncodedProgram(origin, b"")
        for data in ("ab", [1, 2], None, 5):
            with self.subTest(repr(data)), self.assertRaises(TypeError):
                EncodedProgram(0x3000, data)
        with self.assertRaises(ValueError):
            EncodedProgram(0xFFFE, b"\x00\x00\x00\x00")      # no cabe en memoria

    def test_a_program_that_fills_the_memory_exactly(self):
        result = EncodedProgram(0xFFFE, b"\x00\xB8")
        self.assertEqual(result.end_address, 0x10000)
        self.assertEqual(assemble(".ORIG xFFFE", "NOP", ".END").end_address, 0x10000)

    def test_size_and_end_address_match_the_symbol_table(self):
        program = parse_program(source(".ORIG x3000", 'S: .STRINGZ "AB"', "NOP",
                                       ".BLKW #3", ".FILL #1", ".END"))
        table = build_symbol_table(program)
        result = encode_program(program, table)
        self.assertEqual((result.origin, result.size, result.end_address),
                         (table.origin, table.size, table.end_address))

    def test_argument_types_are_checked(self):
        program = parse_program(".ORIG x3000")
        table = build_symbol_table(program)
        with self.assertRaises(TypeError):
            encode_program(".ORIG x3000", table)
        with self.assertRaises(TypeError):
            encode_program(None, table)
        with self.assertRaises(TypeError):
            encode_program(program, None)
        with self.assertRaises(TypeError):
            encode_program(program, {"A": 1})
        with self.assertRaises(TypeError):
            encode_program(table, program)

    def test_inputs_are_not_modified_and_the_result_is_deterministic(self):
        program = parse_program(source(".ORIG x3000", ".EXTERNAL X", "BR X", "L: .FILL L",
                                       ".END"))
        table = build_symbol_table(program)
        externals = {"X": 0x3010}
        before = (repr(program), repr(table), dict(externals))
        first = encode_program(program, table, externals)
        second = encode_program(program, table, externals)
        self.assertEqual((repr(program), repr(table), externals), before)
        self.assertEqual(first, second)

    def test_the_signature(self):
        parameters = inspect.signature(encode_program).parameters
        self.assertEqual(list(parameters), ["program", "symbol_table", "external_symbols"])
        self.assertIsNone(parameters["external_symbols"].default)

    def test_the_errors_have_the_same_shape_as_the_other_stages(self):
        error = EncodeError("algo", 7, "NOP")
        self.assertEqual((error.message, error.line_number, error.source),
                         ("algo", 7, "NOP"))
        self.assertEqual(str(error), "línea 7: algo")
        self.assertEqual(str(EncodeError("global")), "global")
        group = EncodeErrors([error, EncodeError("global")])
        self.assertEqual(len(group.errors), 2)
        self.assertIsInstance(group.errors, tuple)


# ----------------------------------------------------------------------
# 9. Integración: ensamblar y EJECUTAR en la CPU real
# ----------------------------------------------------------------------
def run_program(text, stdin="", externals=None):
    program = parse_program(text)
    table = build_symbol_table(program)
    encoded = encode_program(program, table, externals)
    console = ConsoleIO(io.StringIO(stdin), io.StringIO())
    cpu = CPU(io=console)
    cpu.load_program(encoded.data, encoded.origin)
    cpu.run()
    return cpu, table, console.stdout.getvalue()


class TestIntegrationWithTheCpu(EncoderTestCase):

    def test_hello_world(self):
        cpu, _, output = run_program(source(
            ".ORIG x3000", "LEA R0, MSG", "TRAP x22", "HALT",
            'MSG: .STRINGZ "Hola"', ".END"))
        self.assertEqual(output, "Hola")
        self.assertTrue(cpu.halted)
        self.assertEqual(cpu.instruction_count, 3)

    def test_a_counting_loop(self):
        cpu, _, _ = run_program(source(
            ".ORIG x3000",
            "ADD R1, R1, #5", "ADD R2, R2, #0",
            "LOOP: ADD R2, R2, R1", "SUB R1, R1, #1", "BRp LOOP",
            "HALT", ".END"))
        self.assertEqual(cpu.registers.read(2), 15)         # 5+4+3+2+1
        self.assertEqual(cpu.registers.read(1), 0)
        self.assertEqual(cpu.instruction_count, 2 + 5 * 3 + 1)

    def test_a_subroutine_call_and_return(self):
        cpu, _, _ = run_program(source(
            ".ORIG x3000",
            "ADD R0, R0, #3", "JSR DOUBLE", "HALT",
            "DOUBLE: ADD R0, R0, R0", "JMP LR", ".END"))
        self.assertEqual(cpu.registers.read(0), 6)
        self.assertEqual(cpu.registers.read(7), 0x3004)     # dirección de retorno
        self.assertEqual(cpu.instruction_count, 5)

    def test_data_access_through_lea_ldw_and_stw(self):
        cpu, table, _ = run_program(source(
            ".ORIG x3000",
            "LEA R1, DATA", "LDW R0, R1, #0", "ADD R0, R0, #1", "STW R0, R1, #2", "HALT",
            "DATA: .FILL #41", "OUT: .BLKW #1", ".END"))
        self.assertEqual(cpu.memory.read_word(table.symbols["OUT"]), 42)

    def test_padding_after_odd_data_keeps_the_code_executable(self):
        cpu, _, output = run_program(source(
            ".ORIG x3000",
            "BR START", 'MSG: .STRINGZ "Hi"',
            "START: LEA R0, MSG", "TRAP x22", "HALT", ".END"))
        self.assertEqual(output, "Hi")

    def test_a_label_after_an_odd_string_is_reachable_with_lea(self):
        cpu, _, output = run_program(source(
            ".ORIG x3000",
            "LEA R0, B", "TRAP x22", "HALT",
            'A: .STRINGZ "xy"', 'B: .STRINGZ "yz"', ".END"))       # B = x3009 (impar)
        self.assertEqual(output, "yz")

    def test_linking_an_external_subroutine(self):
        library = assemble(".ORIG x3100", "ADD R0, R0, #1", "JMP LR", ".END")
        main = parse_program(source(".ORIG x3000", ".EXTERNAL INC", "JSR INC", "JSR INC",
                                    "HALT", ".END"))
        encoded = encode_program(main, build_symbol_table(main), {"INC": 0x3100})
        cpu = CPU(io=ConsoleIO(io.StringIO(""), io.StringIO()))
        cpu.load_program(library.data, library.origin, set_pc=False)
        cpu.load_program(encoded.data, encoded.origin)
        cpu.run()
        self.assertEqual(cpu.registers.read(0), 2)

    def test_fill_with_an_external_address_is_a_usable_pointer(self):
        # R0 = [PTR] = x3100; el valor externo se guarda como dirección absoluta.
        program = parse_program(source(".ORIG x3000", ".EXTERNAL BUF", "LEA R1, PTR",
                                       "LDW R0, R1, #0", "HALT", "PTR: .FILL BUF", ".END"))
        encoded = encode_program(program, build_symbol_table(program), {"BUF": 0x3100})
        cpu = CPU(io=ConsoleIO(io.StringIO(""), io.StringIO()))
        cpu.load_program(encoded.data, encoded.origin)
        cpu.run()
        self.assertEqual(cpu.registers.read(0), 0x3100)

    def test_the_last_instruction_of_memory_wraps_like_the_cpu(self):
        # En xFFFE: ADD R0,R0,#1; el PC siguiente da la vuelta a x0000, donde está HALT.
        main = assemble(".ORIG xFFFE", "ADD R0, R0, #1", ".END")
        start = assemble(".ORIG x0000", "HALT", ".END")
        cpu = CPU(io=ConsoleIO(io.StringIO(""), io.StringIO()))
        cpu.load_program(start.data, start.origin, set_pc=False)
        cpu.load_program(main.data, main.origin)
        cpu.step()
        self.assertEqual(cpu.registers.read(0), 1)
        self.assertEqual(cpu.registers.pc, 0)


# ----------------------------------------------------------------------
# 10. Estructura del módulo
# ----------------------------------------------------------------------
class TestModuleStructure(unittest.TestCase):

    @staticmethod
    def tree():
        return ast.parse(Path(encoder_module.__file__).read_text(encoding="utf-8"))

    def test_encoder_depends_only_on_the_parser_symbols_and_isa(self):
        imported = set()
        for node in ast.walk(self.tree()):
            if isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)
            elif isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
        project = {n for n in imported if n.startswith(("simulator", "assembler"))}
        self.assertEqual(project, {"assembler.parser", "assembler.symbols", "simulator.isa"})

    def test_encoder_has_no_instruction_table_of_its_own(self):
        tree = self.tree()
        docstrings = {id(n.value) for n in ast.walk(tree) if isinstance(n, ast.Expr)}
        literals = {n.value for n in ast.walk(tree)
                    if isinstance(n, ast.Constant) and isinstance(n.value, str)
                    and id(n) not in docstrings}
        self.assertEqual(literals & set(INSTRUCTIONS_BY_MNEMONIC), set())

    def test_encoder_has_no_hard_coded_bit_positions(self):
        # Todo desplazamiento usa un ancho o una posición CONSULTADOS (get_field,
        # WORD_BITS...), nunca un número escrito a mano: la posición de los campos
        # vive solo en isa.FORMAT_FIELDS.
        for node in ast.walk(self.tree()):
            if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.LShift, ast.RShift)):
                self.assertNotIsInstance(node.right, ast.Constant,
                                         f"desplazamiento fijo en la línea {node.lineno}")

    def test_the_public_api(self):
        self.assertEqual(sorted(encoder_module.__all__),
                         ["EncodeError", "EncodeErrors", "EncodedProgram", "encode_program"])
        for name in encoder_module.__all__:
            self.assertTrue(hasattr(encoder_module, name))


if __name__ == "__main__":
    unittest.main()