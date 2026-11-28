"""Pruebas de BitField, FORMAT_FIELDS y su uso en decoder.py (etapa 5.3.1).

Archivo aparte: no modifica ninguna prueba existente. Las tablas y palabras
esperadas están escritas a mano; ninguna expectativa sale del código probado.
"""

import ast
import dataclasses
import hashlib
import unittest
from pathlib import Path

from assembler import parser as parser_module
from simulator import decoder, isa
from simulator.decoder import (
    InvalidInstructionError,
    ReservedFieldError,
    ReservedOpcodeError,
    decode,
    extract_field,
    extract_signed_field,
)
from simulator.isa import (
    FORMAT_FIELDS,
    INSTRUCTIONS,
    OPCODE_FIELD,
    BitField,
    InstructionFormat,
    OperandKind,
    get_field,
)

F = InstructionFormat
K = OperandKind

# Descripción esperada de cada formato: (nombre, bit alto, bit bajo), de mayor a menor.
EXPECTED_LAYOUTS = {
    F.A: [("opcode", 15, 11), ("dr", 10, 8), ("sr1", 7, 5), ("mode", 4, 4),
          ("operand2", 3, 0)],
    F.B: [("opcode", 15, 11), ("reg", 10, 8), ("base", 7, 5), ("offset", 4, 0)],
    F.C: [("opcode", 15, 11), ("nzp", 10, 8), ("offset", 7, 0)],
    F.JSR: [("opcode", 15, 11), ("offset", 10, 0)],
    F.JUMP_REG: [("opcode", 15, 11), ("base", 10, 8), ("reserved", 7, 0)],
    F.LEA: [("opcode", 15, 11), ("dr", 10, 8), ("offset", 7, 0)],
    F.TRAP: [("opcode", 15, 11), ("vector", 10, 3), ("reserved", 2, 0)],
    F.NO_OPERANDS: [("opcode", 15, 11), ("reserved", 10, 0)],
}

# Huella SHA-256 del comportamiento del decodificador ANTERIOR a esta etapa,
# calculada sobre las 65.536 palabras (resultado completo si es válida, nombre
# de la excepción si no). Si cambia, cambió el comportamiento observable.
DECODER_DIGEST = "ede372fb6cafdd67f00da75e1b0e82b91c195b531e2e495275a5010e455ccf59"


def fields(*specs):
    return tuple(BitField(*spec) for spec in specs)


def decode_digest(decode_function):
    lines = []
    for word in range(0x10000):
        try:
            d = decode_function(word)
            lines.append(f"{word}:{d.opcode}:{d.mnemonic}:{d.fmt.name}:{d.dr}:{d.sr1}:"
                         f"{d.sr2}:{d.mode}:{d.imm}:{d.reg}:{d.base}:{d.offset}:{d.nzp}:"
                         f"{d.vector}")
        except Exception as error:
            lines.append(f"{word}:{type(error).__name__}")
    return hashlib.sha256("\n".join(lines).encode()).hexdigest()


def signed_range(bits):
    return -(1 << (bits - 1)), (1 << (bits - 1)) - 1


def unsigned_range(bits):
    return 0, (1 << bits) - 1


# ----------------------------------------------------------------------
# BitField
# ----------------------------------------------------------------------
class TestBitField(unittest.TestCase):

    def test_width(self):
        cases = ((15, 11, 5), (10, 8, 3), (7, 5, 3), (4, 4, 1), (3, 0, 4),
                 (10, 0, 11), (15, 0, 16), (0, 0, 1), (15, 15, 1), (10, 3, 8))
        for high, low, width in cases:
            with self.subTest(high=high, low=low):
                self.assertEqual(BitField("x", high, low).width, width)

    def test_valid_limits(self):
        for high, low in ((15, 0), (0, 0), (15, 15), (15, 14), (1, 0)):
            with self.subTest(high=high, low=low):
                field = BitField("x", high, low)
                self.assertEqual((field.high, field.low), (high, low))

    def test_stores_its_name(self):
        self.assertEqual(BitField("operand2", 3, 0).name, "operand2")

    def test_is_immutable(self):
        field = BitField("x", 7, 4)
        for attribute in ("name", "high", "low"):
            with self.subTest(attribute=attribute):
                with self.assertRaises(dataclasses.FrozenInstanceError):
                    setattr(field, attribute, 1)
        with self.assertRaises(AttributeError):
            field.width = 9

    def test_equality_and_hash(self):
        self.assertEqual(BitField("a", 3, 0), BitField("a", 3, 0))
        for other in (BitField("b", 3, 0), BitField("a", 4, 0), BitField("a", 3, 1)):
            self.assertNotEqual(BitField("a", 3, 0), other)
        self.assertEqual(len({BitField("a", 3, 0), BitField("a", 3, 0)}), 1)

    def test_bounds_outside_the_16_bits_are_rejected(self):
        for high, low in ((16, 0), (20, 10), (15, 16), (5, -1), (-1, -1), (16, 16)):
            with self.subTest(high=high, low=low):
                with self.assertRaises(ValueError):
                    BitField("x", high, low)

    def test_high_below_low_is_rejected(self):
        for high, low in ((3, 4), (0, 15), (10, 11)):
            with self.subTest(high=high, low=low):
                with self.assertRaises(ValueError):
                    BitField("x", high, low)

    def test_wrong_types_are_rejected(self):
        for name in ("", None, 5, b"x"):
            with self.subTest(name=name):
                with self.assertRaises(TypeError):
                    BitField(name, 3, 0)
        for bad in ("3", 3.0, None, True, False):
            with self.subTest(bound=bad):
                with self.assertRaises(TypeError):
                    BitField("x", bad, 0)
                with self.assertRaises(TypeError):
                    BitField("x", 3, bad)

    def test_the_error_names_the_field(self):
        with self.assertRaisesRegex(ValueError, "campo 'zeta'"):
            BitField("zeta", 20, 0)


# ----------------------------------------------------------------------
# Validación de la distribución de campos (cobertura exacta de 16 bits)
# ----------------------------------------------------------------------
class TestLayoutValidation(unittest.TestCase):

    def test_valid_layouts_are_accepted(self):
        isa._check_layout("t", fields(("a", 15, 0)))
        isa._check_layout("t", fields(("a", 15, 8), ("b", 7, 0)))
        isa._check_layout("t", fields(*[(f"b{i}", i, i) for i in range(15, -1, -1)]))
        for fmt, specs in EXPECTED_LAYOUTS.items():
            with self.subTest(fmt=fmt.name):
                isa._check_layout(fmt.name, fields(*specs))

    def test_empty_layout(self):
        with self.assertRaisesRegex(ValueError, "no tiene campos"):
            isa._check_layout("t", ())

    def test_overlapping_fields(self):
        cases = (fields(("a", 15, 8), ("b", 10, 0)),
                 fields(("a", 15, 0), ("b", 3, 0)),
                 fields(("a", 15, 11), ("b", 11, 0)),
                 fields(("a", 15, 8), ("b", 8, 0)))
        for layout in cases:
            with self.subTest(layout=layout):
                with self.assertRaisesRegex(ValueError, "superpone"):
                    isa._check_layout("t", layout)

    def test_gap_in_the_middle(self):
        with self.assertRaisesRegex(ValueError, "10..10 no pertenecen"):
            isa._check_layout("t", fields(("a", 15, 11), ("b", 9, 0)))
        with self.assertRaisesRegex(ValueError, "9..5 no pertenecen"):
            isa._check_layout("t", fields(("a", 15, 10), ("b", 4, 0)))

    def test_bits_missing_at_the_top(self):
        with self.assertRaisesRegex(ValueError, "15..15 no pertenecen"):
            isa._check_layout("t", fields(("a", 14, 0)))
        with self.assertRaisesRegex(ValueError, "15..12 no pertenecen"):
            isa._check_layout("t", fields(("a", 11, 0)))

    def test_bits_missing_at_the_bottom(self):
        with self.assertRaisesRegex(ValueError, "1..0 no pertenecen"):
            isa._check_layout("t", fields(("a", 15, 2)))
        with self.assertRaisesRegex(ValueError, "0..0 no pertenecen"):
            isa._check_layout("t", fields(("a", 15, 8), ("b", 7, 1)))

    def test_fields_must_be_declared_from_high_to_low(self):
        with self.assertRaisesRegex(ValueError, "de mayor a menor"):
            isa._check_layout("t", fields(("b", 7, 0), ("a", 15, 8)))

    def test_repeated_names(self):
        with self.assertRaisesRegex(ValueError, "repetidos"):
            isa._check_layout("t", fields(("a", 15, 8), ("a", 7, 0)))

    def test_items_must_be_bitfields(self):
        for bad in ((("a", 15, 0),), (None,), (3,)):
            with self.subTest(bad=bad):
                with self.assertRaises(TypeError):
                    isa._check_layout("t", bad)

    def test_the_error_names_the_format(self):
        with self.assertRaisesRegex(ValueError, "^MIFORMATO:"):
            isa._check_layout("MIFORMATO", fields(("a", 14, 0)))

    def test_the_table_builder_rejects_incomplete_or_wrong_tables(self):
        def layouts():
            return {fmt: list(specs) for fmt, specs in EXPECTED_LAYOUTS.items()}

        isa._build_format_fields(layouts())                     # la base es válida

        missing = layouts()
        del missing[F.TRAP]
        with self.assertRaisesRegex(ValueError, "faltan: \\['TRAP'\\]"):
            isa._build_format_fields(missing)

        extra = layouts()
        extra["INVENTADO"] = [("opcode", 15, 11), ("x", 10, 0)]
        with self.assertRaisesRegex(ValueError, "sobran"):
            isa._build_format_fields(extra)

        gap = layouts()
        gap[F.B] = [("opcode", 15, 11), ("reg", 10, 8), ("base", 7, 5), ("offset", 3, 0)]
        with self.assertRaisesRegex(ValueError, "^B:"):
            isa._build_format_fields(gap)

        no_opcode = layouts()
        no_opcode[F.JSR] = [("tipo", 15, 12), ("offset", 11, 0)]
        with self.assertRaisesRegex(ValueError, "primer campo debe ser el opcode"):
            isa._build_format_fields(no_opcode)


# ----------------------------------------------------------------------
# FORMAT_FIELDS
# ----------------------------------------------------------------------
class TestFormatFields(unittest.TestCase):

    def test_every_format_is_present(self):
        self.assertEqual(len(F), 8)
        self.assertEqual(set(FORMAT_FIELDS), set(F))
        self.assertEqual(set(FORMAT_FIELDS), set(EXPECTED_LAYOUTS))

    def test_layouts_match_the_specification(self):
        for fmt, expected in EXPECTED_LAYOUTS.items():
            with self.subTest(fmt=fmt.name):
                actual = [(f.name, f.high, f.low) for f in FORMAT_FIELDS[fmt]]
                self.assertEqual(actual, expected)

    def test_every_layout_covers_the_16_bits_exactly_once(self):
        for fmt, layout in FORMAT_FIELDS.items():
            with self.subTest(fmt=fmt.name):
                bits = [bit for field in layout for bit in range(field.low, field.high + 1)]
                self.assertEqual(sorted(bits), list(range(16)))
                self.assertEqual(sum(field.width for field in layout), 16)

    def test_widths_of_every_field(self):
        expected = {
            F.A: [5, 3, 3, 1, 4], F.B: [5, 3, 3, 5], F.C: [5, 3, 8], F.JSR: [5, 11],
            F.JUMP_REG: [5, 3, 8], F.LEA: [5, 3, 8], F.TRAP: [5, 8, 3],
            F.NO_OPERANDS: [5, 11],
        }
        for fmt, widths in expected.items():
            with self.subTest(fmt=fmt.name):
                self.assertEqual([f.width for f in FORMAT_FIELDS[fmt]], widths)

    def test_the_opcode_is_the_first_field_of_every_format(self):
        self.assertEqual((OPCODE_FIELD.name, OPCODE_FIELD.high, OPCODE_FIELD.low),
                         ("opcode", 15, 11))
        self.assertEqual(OPCODE_FIELD.width, isa.OPCODE_BITS)
        for fmt, layout in FORMAT_FIELDS.items():
            with self.subTest(fmt=fmt.name):
                self.assertEqual(layout[0], OPCODE_FIELD)

    def test_field_names_are_unique_within_a_format(self):
        for fmt, layout in FORMAT_FIELDS.items():
            names = [field.name for field in layout]
            with self.subTest(fmt=fmt.name):
                self.assertEqual(len(set(names)), len(names))

    def test_the_table_is_read_only(self):
        with self.assertRaises(TypeError):
            FORMAT_FIELDS[F.A] = ()
        with self.assertRaises(TypeError):
            del FORMAT_FIELDS[F.A]
        self.assertFalse(hasattr(FORMAT_FIELDS, "update"))
        self.assertFalse(hasattr(FORMAT_FIELDS, "pop"))

    def test_each_layout_is_an_immutable_tuple_of_frozen_fields(self):
        for fmt, layout in FORMAT_FIELDS.items():
            with self.subTest(fmt=fmt.name):
                self.assertIsInstance(layout, tuple)
                with self.assertRaises(TypeError):
                    layout[0] = BitField("x", 15, 11)
                for field in layout:
                    with self.assertRaises(dataclasses.FrozenInstanceError):
                        field.high = 0

    def test_get_field(self):
        for fmt, layout in FORMAT_FIELDS.items():
            for field in layout:
                with self.subTest(fmt=fmt.name, field=field.name):
                    self.assertIs(get_field(fmt, field.name), field)

    def test_get_field_with_unknown_names_or_formats(self):
        with self.assertRaisesRegex(KeyError, "formato A no tiene un campo 'reserved'"):
            get_field(F.A, "reserved")
        with self.assertRaises(KeyError):
            get_field(F.JSR, "dr")
        with self.assertRaises(KeyError):
            get_field("A", "opcode")
        with self.assertRaises(KeyError):
            get_field(None, "opcode")

    def test_nothing_that_existed_was_removed_from_isa(self):
        for name in ("WORD_BITS", "WORD_MASK", "BYTE_BITS", "BYTE_MASK", "OPCODE_BITS",
                     "REGISTER_COUNT", "REGISTER_MASK", "SP_REGISTER", "LINK_REGISTER",
                     "MEMORY_SIZE", "PC_INCREMENT", "NZP_N", "NZP_Z", "NZP_P",
                     "MODE_REGISTER", "MODE_IMMEDIATE", "TRAP_GETC", "TRAP_OUT",
                     "TRAP_PUTS", "TRAP_HALT", "InstructionFormat", "OperandKind",
                     "InstructionSpec", "INSTRUCTIONS", "INSTRUCTIONS_BY_OPCODE",
                     "INSTRUCTIONS_BY_MNEMONIC", "RESERVED_OPCODES"):
            with self.subTest(name=name):
                self.assertTrue(hasattr(isa, name))
        self.assertEqual(len(INSTRUCTIONS), 26)
        self.assertEqual(len(isa.INSTRUCTIONS_BY_OPCODE), 26)
        self.assertEqual(len(OperandKind), 7)


# ----------------------------------------------------------------------
# Coherencia entre los campos, las constantes de isa.py y los rangos del parser
# ----------------------------------------------------------------------
class TestFieldsAgreeWithTheRestOfTheArchitecture(unittest.TestCase):

    def test_register_fields_are_as_wide_as_a_register_number(self):
        self.assertEqual(isa.REGISTER_MASK.bit_length(), 3)
        self.assertEqual(isa.REGISTER_COUNT, 2 ** 3)
        for fmt, layout in FORMAT_FIELDS.items():
            for field in layout:
                if field.name in ("dr", "sr1", "reg", "base"):
                    with self.subTest(fmt=fmt.name, field=field.name):
                        self.assertEqual(field.width, 3)

    def test_the_nzp_field_holds_the_three_condition_bits(self):
        self.assertEqual(get_field(F.C, "nzp").width, 3)
        self.assertEqual(isa.NZP_N | isa.NZP_Z | isa.NZP_P, 2 ** 3 - 1)

    def test_the_mode_field_holds_the_two_addressing_modes(self):
        self.assertEqual(get_field(F.A, "mode").width, 1)
        self.assertLessEqual(max(isa.MODE_REGISTER, isa.MODE_IMMEDIATE), 1)

    def test_operand_ranges_of_the_parser_match_the_field_widths(self):
        """Los rangos que valida el parser deben ser los que caben en los campos."""
        for spec in INSTRUCTIONS:
            for kind in spec.operands:
                if kind is K.REGISTER:
                    continue
                if kind is K.REG_OR_IMM4:
                    expected = signed_range(get_field(F.A, "operand2").width)
                elif kind is K.SHIFT_AMOUNT:
                    expected = unsigned_range(get_field(F.A, "operand2").width)
                elif kind is K.OFFSET5:
                    expected = signed_range(get_field(F.B, "offset").width)
                elif kind is K.VECTOR:
                    expected = unsigned_range(get_field(F.TRAP, "vector").width)
                else:                                   # LABEL_WORDS / LABEL_BYTES
                    expected = signed_range(get_field(spec.fmt, "offset").width)
                with self.subTest(mnemonic=spec.mnemonic, kind=kind.name):
                    self.assertEqual(parser_module._immediate_range(kind, spec), expected)


# ----------------------------------------------------------------------
# Extracción por nombre (palabras armadas a mano)
# ----------------------------------------------------------------------
class TestFieldExtraction(unittest.TestCase):

    def test_extract_field(self):
        cases = [
            # A: 00000 001 010 1 0101
            (0x0155, F.A, "opcode", 0), (0x0155, F.A, "dr", 1), (0x0155, F.A, "sr1", 2),
            (0x0155, F.A, "mode", 1), (0x0155, F.A, "operand2", 5),
            (0xFFFF, F.A, "opcode", 31), (0xFFFF, F.A, "dr", 7), (0xFFFF, F.A, "sr1", 7),
            (0xFFFF, F.A, "mode", 1), (0xFFFF, F.A, "operand2", 15),
            # B: 01010 011 101 10110
            (0x53B6, F.B, "opcode", 10), (0x53B6, F.B, "reg", 3), (0x53B6, F.B, "base", 5),
            (0x53B6, F.B, "offset", 22),
            # C: 10000 101 10000001
            (0x8581, F.C, "opcode", 16), (0x8581, F.C, "nzp", 5), (0x8581, F.C, "offset", 129),
            # JSR: 10001 11111111111
            (0x8FFF, F.JSR, "opcode", 17), (0x8FFF, F.JSR, "offset", 2047),
            # JUMP_REG: 10010 110 00000000  y con ceros reservados
            (0x9600, F.JUMP_REG, "base", 6), (0x9600, F.JUMP_REG, "reserved", 0),
            (0x96FF, F.JUMP_REG, "reserved", 255),
            # LEA: 10011 010 10000000
            (0x9A80, F.LEA, "dr", 2), (0x9A80, F.LEA, "offset", 128),
            # TRAP: 10110 00100101 000  y 101 en los bits reservados
            (0xB128, F.TRAP, "vector", 0x25), (0xB128, F.TRAP, "reserved", 0),
            (0xB12D, F.TRAP, "reserved", 5), (0xB12D, F.TRAP, "vector", 0x25),
            # NO_OPERANDS: 10111 00000000101
            (0xB805, F.NO_OPERANDS, "opcode", 23), (0xB805, F.NO_OPERANDS, "reserved", 5),
        ]
        for word, fmt, name, expected in cases:
            with self.subTest(word=hex(word), fmt=fmt.name, field=name):
                self.assertEqual(extract_field(word, fmt, name), expected)

    def test_extract_signed_field(self):
        cases = [
            (0x0158, F.A, "operand2", -8), (0x015F, F.A, "operand2", -1),
            (0x0157, F.A, "operand2", 7), (0x0150, F.A, "operand2", 0),
            (0x53B6, F.B, "offset", -10), (0x501F, F.B, "offset", -1),
            (0x500F, F.B, "offset", 15), (0x5010, F.B, "offset", -16),
            (0x8581, F.C, "offset", -127), (0x8580, F.C, "offset", -128),
            (0x857F, F.C, "offset", 127),
            (0x8FFF, F.JSR, "offset", -1), (0x8800, F.JSR, "offset", 0),
            (0x8BFF, F.JSR, "offset", 1023), (0x8C00, F.JSR, "offset", -1024),
            (0x9A80, F.LEA, "offset", -128), (0x9A7F, F.LEA, "offset", 127),
        ]
        for word, fmt, name, expected in cases:
            with self.subTest(word=hex(word), fmt=fmt.name, field=name):
                self.assertEqual(extract_signed_field(word, fmt, name), expected)

    def test_unsigned_and_signed_extraction_differ_only_by_interpretation(self):
        self.assertEqual(extract_field(0x8581, F.C, "offset"), 129)
        self.assertEqual(extract_signed_field(0x8581, F.C, "offset"), 129 - 256)

    def test_unknown_field_or_format(self):
        with self.assertRaises(KeyError):
            extract_field(0x0155, F.A, "base")
        with self.assertRaises(KeyError):
            extract_signed_field(0x0155, "A", "dr")


# ----------------------------------------------------------------------
# El decodificador usa la descripción y conserva su comportamiento
# ----------------------------------------------------------------------
class TestDecoderUsesTheFieldTable(unittest.TestCase):

    @staticmethod
    def _decoder_tree():
        return ast.parse(Path(decoder.__file__).read_text(encoding="utf-8"))

    def test_no_bit_position_or_width_is_written_by_hand(self):
        """get_bits / sign_extend nunca reciben números literales en decoder.py."""
        calls = 0
        for node in ast.walk(self._decoder_tree()):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                    and node.func.id in ("get_bits", "sign_extend")):
                calls += 1
                for argument in node.args:
                    self.assertFalse(
                        isinstance(argument, ast.Constant)
                        and isinstance(argument.value, int),
                        f"línea {node.lineno}: número literal en {node.func.id}()")
        self.assertGreater(calls, 0)

    def test_the_decoder_depends_only_on_isa(self):
        imported = set()
        for node in ast.walk(self._decoder_tree()):
            if isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)
        self.assertEqual({m for m in imported if m.startswith(("simulator", "assembler"))},
                         {"simulator.isa"})

    def test_behaviour_is_identical_to_the_previous_decoder(self):
        self.assertEqual(decode_digest(decode), DECODER_DIGEST)

    def test_exact_error_messages_are_preserved(self):
        cases = [
            (0x0008, ReservedFieldError,
             "ADD (0x0008): el campo bit 3 de OP2 debe ser 0, se encontró 0b1"),
            (0x0108, ReservedFieldError,
             "ADD (0x0108): el campo bit 3 de OP2 debe ser 0, se encontró 0b1"),
            (0x2810, ReservedFieldError, "NOT (0x2810): el campo M debe ser 0, se encontró 0b1"),
            (0x4900, ReservedFieldError, "CMP (0x4900): el campo DR debe ser 0, se encontró 0b1"),
            (0x3000, InvalidInstructionError,
             "SHL (0x3000): solo admite modo inmediato (M=1), se encontró M=0"),
            (0x9001, ReservedFieldError, "JMP (0x9001): el campo CEROS debe ser 0, se encontró 0b1"),
            (0xB001, ReservedFieldError, "TRAP (0xB001): el campo CEROS debe ser 0, se encontró 0b1"),
            (0xB801, ReservedFieldError, "NOP (0xB801): el campo CEROS debe ser 0, se encontró 0b1"),
            (0xD000, ReservedOpcodeError, "Opcode reservado 0b11010 en la instrucción 0xD000"),
        ]
        for word, error_class, message in cases:
            with self.subTest(word=hex(word)):
                with self.assertRaises(error_class) as context:
                    decode(word)
                self.assertEqual(type(context.exception), error_class)
                self.assertEqual(str(context.exception), message)

    def test_each_explicit_semantic_rule_is_still_enforced(self):
        rules = {
            "NOT exige M=0": (0x2810, ReservedFieldError),
            "NOT exige OP2=0": (0x2801, ReservedFieldError),
            "CMP exige DR=0": (0x4900, ReservedFieldError),
            "SHL solo con M=1": (0x3000, InvalidInstructionError),
            "SHR solo con M=1": (0x3800, InvalidInstructionError),
            "SAR solo con M=1": (0x4000, InvalidInstructionError),
            "modo registro: bit 3 de OP2 = 0": (0x0008, ReservedFieldError),
            "JMP: 8 bits inferiores en 0": (0x9001, ReservedFieldError),
            "JSRR: 8 bits inferiores en 0": (0xC880, ReservedFieldError),
            "TRAP: 3 bits inferiores en 0": (0xB004, ReservedFieldError),
            "NOP: 11 bits inferiores en 0": (0xBC00, ReservedFieldError),
            "HALT: 11 bits inferiores en 0": (0xC400, ReservedFieldError),
            "opcode reservado": (0xFFFF, ReservedOpcodeError),
        }
        for rule, (word, error_class) in rules.items():
            with self.subTest(rule=rule):
                with self.assertRaises(error_class):
                    decode(word)

    def test_immediates_and_offsets_are_interpreted_as_before(self):
        self.assertEqual(decode(0x015F).imm, -1)          # ADD imm4 = 1111 -> -1
        self.assertEqual(decode(0x315F).imm, 15)          # SHL imm4 = 1111 -> 15 (sin signo)
        self.assertEqual(decode(0x501F).offset, -1)       # LDW offset5 = 11111 -> -1
        self.assertEqual(decode(0x8580).offset, -128)     # BR offset8 = 10000000 -> -128
        self.assertEqual(decode(0x8FFF).offset, -1)       # JSR offset11 = 11111111111 -> -1
        self.assertEqual(decode(0x9A80).offset, -128)     # LEA offset8 = 10000000 -> -128
        self.assertEqual(decode(0xB128).vector, 0x25)     # TRAP x25

    def test_public_api_and_hierarchies_are_preserved(self):
        for name in ("decode", "get_bits", "sign_extend", "DecodedInstruction", "Format",
                     "OPCODE_TABLE", "InvalidInstructionError", "ReservedOpcodeError",
                     "ReservedFieldError", "MODE_REGISTER", "MODE_IMMEDIATE", "NZP_N",
                     "NZP_Z", "NZP_P", "WORD_MASK"):
            with self.subTest(name=name):
                self.assertTrue(hasattr(decoder, name))
        self.assertTrue(issubclass(ReservedOpcodeError, InvalidInstructionError))
        self.assertTrue(issubclass(ReservedFieldError, InvalidInstructionError))
        self.assertIs(decoder.Format, isa.InstructionFormat)
        self.assertEqual(len(decoder.OPCODE_TABLE), 26)
        self.assertEqual(decoder.get_bits(0b1010_0110_1100_0011, 15, 11), 0b10100)
        self.assertEqual(decoder.sign_extend(0b11111, 5), -1)

    def test_decoded_instruction_keeps_all_its_attributes(self):
        names = [f.name for f in dataclasses.fields(decoder.DecodedInstruction)]
        self.assertEqual(names, ["word", "opcode", "mnemonic", "fmt", "dr", "sr1", "sr2",
                                 "mode", "imm", "reg", "base", "offset", "nzp", "vector"])


if __name__ == "__main__":
    unittest.main()