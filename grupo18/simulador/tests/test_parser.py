"""Pruebas de assembler/parser.py (ejecutar desde la carpeta raíz Lab3C).

Las expectativas están escritas a mano desde la especificación: no se calculan
con las funciones que se están probando.
"""

import ast
import dataclasses
import unittest
from pathlib import Path

from assembler import parser as parser_module
from assembler.parser import (
    BlkwDirective,
    EndDirective,
    ExternalDirective,
    FillDirective,
    Immediate,
    Instruction,
    LabelRef,
    OrigDirective,
    ParsedLine,
    ParseError,
    ParseErrors,
    Program,
    Register,
    StringzDirective,
    normalize_mnemonic,
    parse_line,
    parse_program,
)
from simulator.isa import INSTRUCTIONS_BY_MNEMONIC


def R(number): return Register(number)
def I(value): return Immediate(value)          # noqa: E741
def L(name): return LabelRef(name)


def instruction(mnemonic, *operands, nzp=None):
    return Instruction(mnemonic, tuple(operands), nzp)


def statement_of(text):
    return parse_line(text).statement


# Las 26 instrucciones de la especificación (escritas a mano).
MNEMONICS_26 = {
    "ADD", "SUB", "AND", "OR", "XOR", "NOT", "SHL", "SHR", "SAR", "CMP",
    "LDW", "STW", "LDBL", "LDBH", "STBL", "STBH", "BR", "JSR", "JMP", "LEA",
    "LDI", "STI", "TRAP", "NOP", "HALT", "JSRR",
}

ARITY = {
    "ADD": 3, "SUB": 3, "AND": 3, "OR": 3, "XOR": 3, "NOT": 2,
    "SHL": 3, "SHR": 3, "SAR": 3, "CMP": 2,
    "LDW": 3, "STW": 3, "LDBL": 3, "LDBH": 3, "STBL": 3, "STBH": 3,
    "BR": 1, "JSR": 1, "JMP": 1, "LEA": 2, "LDI": 3, "STI": 3,
    "TRAP": 1, "NOP": 0, "HALT": 0, "JSRR": 1,
}

CASES_26 = [
    ("ADD R1, R2, R3", instruction("ADD", R(1), R(2), R(3))),
    ("SUB R4, R4, #-1", instruction("SUB", R(4), R(4), I(-1))),
    ("AND R0, R1, R2", instruction("AND", R(0), R(1), R(2))),
    ("OR R3, R3, #7", instruction("OR", R(3), R(3), I(7))),
    ("XOR R5, R5, R5", instruction("XOR", R(5), R(5), R(5))),
    ("NOT R1, R2", instruction("NOT", R(1), R(2))),
    ("SHL R1, R2, #4", instruction("SHL", R(1), R(2), I(4))),
    ("SHR R3, R3, #15", instruction("SHR", R(3), R(3), I(15))),
    ("SAR R6, R6, #1", instruction("SAR", R(6), R(6), I(1))),
    ("CMP R1, R2", instruction("CMP", R(1), R(2))),
    ("LDW R1, R2, #4", instruction("LDW", R(1), R(2), I(4))),
    ("STW R3, R2, #0", instruction("STW", R(3), R(2), I(0))),
    ("LDBL R4, R5, #2", instruction("LDBL", R(4), R(5), I(2))),
    ("LDBH R4, R5, #-2", instruction("LDBH", R(4), R(5), I(-2))),
    ("STBL R1, R6, #0", instruction("STBL", R(1), R(6), I(0))),
    ("STBH R1, R6, #15", instruction("STBH", R(1), R(6), I(15))),
    ("BR LOOP", instruction("BR", L("LOOP"), nzp=0b111)),
    ("JSR SUBRUT", instruction("JSR", L("SUBRUT"))),
    ("JMP R7", instruction("JMP", R(7))),
    ("LEA R0, MSG", instruction("LEA", R(0), L("MSG"))),
    ("LDI R1, R2, #0", instruction("LDI", R(1), R(2), I(0))),
    ("STI R3, R2, #-16", instruction("STI", R(3), R(2), I(-16))),
    ("TRAP x25", instruction("TRAP", I(0x25))),
    ("NOP", instruction("NOP")),
    ("HALT", instruction("HALT")),
    ("JSRR R3", instruction("JSRR", R(3))),
]


class ParserTestCase(unittest.TestCase):
    """Utilidades comunes."""

    def assertParseError(self, text, fragment=None, line=1):
        with self.assertRaises(ParseError) as context:
            parse_line(text, line)
        error = context.exception
        self.assertEqual(error.line_number, line)
        if fragment is not None:
            self.assertIn(fragment, error.message)
        return error


# ----------------------------------------------------------------------
# 1-4. Líneas vacías, comentarios y espacios
# ----------------------------------------------------------------------
class TestBlankLinesAndComments(ParserTestCase):

    def test_blank_lines(self):
        for text in ("", "   ", "\t", " \t  \t"):
            with self.subTest(text=repr(text)):
                self.assertEqual(parse_line(text), ParsedLine(1, text, None, None))

    def test_comment_only_lines(self):
        for text in (";", "; comentario", "   ; x", "\t;; y", ";ADD R1, R2, #5"):
            with self.subTest(text=text):
                self.assertEqual(parse_line(text), ParsedLine(1, text, None, None))

    def test_trailing_comment_is_removed_before_parsing(self):
        expected = instruction("ADD", R(1), R(2), I(5))
        for text in ("ADD R1, R2, #5 ; suma de dos valores", "ADD R1,R2,#5;x",
                     "ADD R1, R2, #5 ;;; ADD R9"):
            with self.subTest(text=text):
                self.assertEqual(statement_of(text), expected)

    def test_semicolon_inside_a_string_is_not_a_comment(self):
        self.assertEqual(statement_of('.STRINGZ "a;b" ; fin'), StringzDirective("a;b"))

    def test_comment_after_a_label(self):
        line = parse_line("INICIO: ; solo la etiqueta")
        self.assertEqual((line.label, line.statement), ("INICIO", None))


class TestWhitespace(ParserTestCase):

    def test_spaces_tabs_and_case_do_not_matter(self):
        expected = instruction("ADD", R(1), R(2), I(5))
        for text in ("ADD R1, R2, #5", "ADD R1,R2,#5", "  ADD   R1 ,  R2 ,  #5  ",
                     "\tADD\tR1,\tR2,\t#5\t", "add r1, r2, #5", "AdD R1 , r2,#5"):
            with self.subTest(text=repr(text)):
                self.assertEqual(statement_of(text), expected)

    def test_line_number_and_source_are_preserved(self):
        line = parse_line("  NOP  ", 12)
        self.assertEqual(line.line_number, 12)
        self.assertEqual(line.source, "  NOP  ")


# ----------------------------------------------------------------------
# 5-7. Etiquetas
# ----------------------------------------------------------------------
class TestLabels(ParserTestCase):

    def test_label_on_the_same_line(self):
        for text in ("INICIO: ADD R1, R2, #5", "INICIO:ADD R1, R2, #5",
                     "INICIO : ADD R1, R2, #5", "   INICIO:   ADD R1, R2, #5"):
            with self.subTest(text=text):
                line = parse_line(text)
                self.assertEqual(line.label, "INICIO")
                self.assertEqual(line.statement, instruction("ADD", R(1), R(2), I(5)))

    def test_label_alone_on_its_line(self):
        line = parse_line("INICIO:")
        self.assertEqual((line.label, line.statement), ("INICIO", None))

    def test_label_on_its_own_line_then_instruction_on_the_next(self):
        program = parse_program("INICIO:\n    ADD R1, R2, #5")
        self.assertEqual(program.lines, (
            ParsedLine(1, "INICIO:", "INICIO", None),
            ParsedLine(2, "    ADD R1, R2, #5", None,
                       instruction("ADD", R(1), R(2), I(5))),
        ))

    def test_valid_label_names(self):
        for name in ("a", "_", "_start", "Loop1", "ETIQUETA_LARGA_2", "x", "xyz",
                     "xend", "R", "RA", "Ra1", "R1x", "SPx", "LRX", "BRANCH", "ADDR"):
            with self.subTest(name=name):
                self.assertEqual(parse_line(f"{name}: NOP").label, name)

    def test_invalid_label_names(self):
        for name in ("1ABC", "A-B", "A.B", "R1", "r7", "SP", "lr", "R10", "R8",
                     "ADD", "add", "HALT", "BR", "BRnz", "BRNZP", "x25", "X25",
                     "xFACE", "xb"):
            with self.subTest(name=name):
                self.assertParseError(f"{name}: NOP", "etiqueta inválida")

    def test_missing_label_name(self):
        self.assertParseError(": NOP", "falta el nombre de la etiqueta")

    def test_only_one_label_per_line(self):
        self.assertParseError("A: B: NOP", "una etiqueta por línea")

    def test_labels_are_case_sensitive(self):
        program = parse_program("a: NOP\nA: NOP")
        self.assertEqual([line.label for line in program.lines], ["a", "A"])

    def test_duplicate_label_is_reported_with_both_lines(self):
        with self.assertRaises(ParseErrors) as context:
            parse_program("A: NOP\nB: NOP\nA: HALT")
        (error,) = context.exception.errors
        self.assertEqual(error.line_number, 3)
        self.assertIn("duplicada", error.message)
        self.assertIn("línea 1", error.message)

    def test_duplicate_between_label_only_line_and_statement_line(self):
        with self.assertRaises(ParseErrors) as context:
            parse_program("L:\nL: NOP")
        self.assertEqual([e.line_number for e in context.exception.errors], [2])

    def test_every_repeated_definition_is_reported(self):
        with self.assertRaises(ParseErrors) as context:
            parse_program("A: NOP\nA: NOP\nA: NOP")
        self.assertEqual([e.line_number for e in context.exception.errors], [2, 3])

    def test_label_with_directives(self):
        self.assertEqual(parse_line("DATA: .FILL #5").statement, FillDirective(I(5)))
        self.assertEqual(parse_line("BUF: .BLKW #3").statement, BlkwDirective(3))
        self.assertEqual(parse_line('MSG: .STRINGZ "x"').statement, StringzDirective("x"))
        self.assertEqual(parse_line("FIN: .END").label, "FIN")

    def test_label_not_allowed_on_orig_or_external(self):
        self.assertParseError("INICIO: .ORIG x3000", ".ORIG")
        self.assertParseError("EXT: .EXTERNAL PRINTF", ".EXTERNAL")


# ----------------------------------------------------------------------
# 8. Las 26 instrucciones y mnemónicos
# ----------------------------------------------------------------------
class TestInstructionRecognition(ParserTestCase):

    def test_the_26_instructions_are_recognized(self):
        self.assertEqual(len(CASES_26), 26)
        self.assertEqual({expected.mnemonic for _, expected in CASES_26}, MNEMONICS_26)
        for text, expected in CASES_26:
            with self.subTest(text=text):
                self.assertEqual(statement_of(text), expected)

    def test_the_hand_written_list_matches_isa(self):
        self.assertEqual(MNEMONICS_26, set(INSTRUCTIONS_BY_MNEMONIC))

    def test_mnemonics_ignore_case(self):
        for text in ("add R1, R2, R3", "Add R1, R2, R3", "aDD R1, R2, R3"):
            with self.subTest(text=text):
                self.assertEqual(statement_of(text).mnemonic, "ADD")
        self.assertEqual(statement_of("halt").mnemonic, "HALT")
        self.assertEqual(statement_of("Nop").mnemonic, "NOP")

    def test_unknown_mnemonics(self):
        for text in ("FOO R1, R2, R3", "ADDD R1, R2, R3", "MOV R1, R2", "LD R1, R2",
                     "ADD1 R1", "JMPR R1", "HLT", "BRANCH LOOP", "BRx LOOP"):
            with self.subTest(text=text):
                self.assertParseError(text, "mnemónico desconocido")

    def test_instruction_exposes_its_isa_spec(self):
        parsed = statement_of("ADD R1, R2, #5")
        self.assertIs(parsed.spec, INSTRUCTIONS_BY_MNEMONIC["ADD"])

    def test_nzp_is_none_for_everything_except_br(self):
        for text, expected in CASES_26:
            with self.subTest(text=text):
                if expected.mnemonic != "BR":
                    self.assertIsNone(statement_of(text).nzp)


# ----------------------------------------------------------------------
# 9-10. Variantes de BR
# ----------------------------------------------------------------------
class TestBranchVariants(ParserTestCase):

    def test_all_eight_spellings(self):
        expected_masks = {
            "BR": 0b111, "BRn": 0b100, "BRz": 0b010, "BRp": 0b001,
            "BRnz": 0b110, "BRnp": 0b101, "BRzp": 0b011, "BRnzp": 0b111,
        }
        for spelling, mask in expected_masks.items():
            with self.subTest(spelling=spelling):
                self.assertEqual(statement_of(f"{spelling} LOOP"),
                                 instruction("BR", L("LOOP"), nzp=mask))

    def test_variants_ignore_case(self):
        for spelling, mask in (("brnz", 0b110), ("BRNZ", 0b110), ("BrZp", 0b011),
                               ("bRnZp", 0b111), ("BRN", 0b100), ("brp", 0b001)):
            with self.subTest(spelling=spelling):
                self.assertEqual(statement_of(f"{spelling} X").nzp, mask)

    def test_br_without_suffix_is_brnzp(self):
        self.assertEqual(statement_of("BR LOOP"), statement_of("BRnzp LOOP"))
        self.assertEqual(statement_of("br LOOP").nzp, 0b111)

    def test_out_of_order_or_repeated_suffixes_are_rejected(self):
        for spelling in ("BRzn", "BRpn", "BRpz", "BRnn", "BRnzpp", "BRnpz", "BRzzz"):
            with self.subTest(spelling=spelling):
                self.assertParseError(f"{spelling} LOOP", "variante de BR inválida")

    def test_branch_target_may_be_a_numeric_offset(self):
        self.assertEqual(statement_of("BRz #-3"), instruction("BR", I(-3), nzp=0b010))
        self.assertEqual(statement_of("BR x10"), instruction("BR", I(16), nzp=0b111))

    def test_missing_target(self):
        self.assertParseError("BRnz", "faltan operandos")
        self.assertParseError("BR", "faltan operandos")

    def test_normalize_mnemonic(self):
        cases = {
            "add": ("ADD", None), "HALT": ("HALT", None), "BR": ("BR", 0b111),
            "BRnz": ("BR", 0b110), "brzp": ("BR", 0b011), "BRNZP": ("BR", 0b111),
        }
        for token, expected in cases.items():
            with self.subTest(token=token):
                self.assertEqual(normalize_mnemonic(token), expected)
        for token in ("FOO", "BRzn", "BRx", "", "BRANCH"):
            with self.subTest(token=token):
                self.assertIsNone(normalize_mnemonic(token))

    def test_variants_are_not_separate_instructions_in_isa(self):
        self.assertIn("BR", INSTRUCTIONS_BY_MNEMONIC)
        for spelling in ("BRN", "BRZ", "BRP", "BRNZ", "BRNP", "BRZP", "BRNZP"):
            self.assertNotIn(spelling, INSTRUCTIONS_BY_MNEMONIC)
        self.assertEqual(len(INSTRUCTIONS_BY_MNEMONIC), 26)


# ----------------------------------------------------------------------
# 11-12. Registros y alias
# ----------------------------------------------------------------------
class TestRegisters(ParserTestCase):

    def test_r0_to_r7(self):
        for number in range(8):
            with self.subTest(register=number):
                self.assertEqual(statement_of(f"JMP R{number}"),
                                 instruction("JMP", R(number)))
                self.assertEqual(statement_of(f"jmp r{number}"),
                                 instruction("JMP", R(number)))

    def test_aliases_are_normalized(self):
        cases = [
            ("ADD SP, SP, #-2", instruction("ADD", R(6), R(6), I(-2))),
            ("JMP LR", instruction("JMP", R(7))),
            ("STW LR, SP, #0", instruction("STW", R(7), R(6), I(0))),
            ("LDW LR, SP, #0", instruction("LDW", R(7), R(6), I(0))),
            ("jmp sp", instruction("JMP", R(6))),
            ("JMP Lr", instruction("JMP", R(7))),
            ("JSRR Sp", instruction("JSRR", R(6))),
        ]
        for text, expected in cases:
            with self.subTest(text=text):
                self.assertEqual(statement_of(text), expected)

    def test_alias_equals_its_register(self):
        self.assertEqual(statement_of("JMP SP"), statement_of("JMP R6"))
        self.assertEqual(statement_of("JMP LR"), statement_of("JMP R7"))

    def test_nonexistent_registers(self):
        for name in ("R8", "R9", "R10", "R99", "r8", "R00", "R01", "R08"):
            with self.subTest(name=name):
                error = self.assertParseError(f"ADD {name}, R1, R2", "registro inexistente")
                self.assertIn("ADD, operando 1", error.message)

    def test_misspelled_registers(self):
        for name in ("RO", "R", "RR1", "R1x", "SPP", "LRR"):
            with self.subTest(name=name):
                self.assertParseError(f"ADD R1, R2, {name}",
                                      "se esperaba registro o inmediato")
                self.assertParseError(f"NOT R1, {name}", "registro mal escrito")
        for name in ("R-1", "R 1", "R1.5", "R#1"):
            with self.subTest(name=name):
                self.assertParseError(f"NOT R1, {name}", "operando no reconocido")


# ----------------------------------------------------------------------
# 13-14. Literales
# ----------------------------------------------------------------------
class TestLiterals(ParserTestCase):

    def fill_value(self, token):
        return statement_of(f".FILL {token}").value

    def test_decimal_literals(self):
        for token, value in (("#5", 5), ("#-3", -3), ("#0", 0), ("#-0", 0),
                             ("#007", 7), ("#12345", 12345), ("#-32768", -32768)):
            with self.subTest(token=token):
                self.assertEqual(self.fill_value(token), I(value))

    def test_hexadecimal_literals_in_every_spelling(self):
        for token, value in (("x25", 37), ("X25", 37), ("0x25", 37), ("0X25", 37),
                             ("xFF", 255), ("xff", 255), ("0xFF", 255), ("x0", 0),
                             ("x0025", 37), ("xAbCd", 0xABCD)):
            with self.subTest(token=token):
                self.assertEqual(self.fill_value(token), I(value))

    def test_hexadecimal_is_unsigned(self):
        self.assertEqual(self.fill_value("xFFFF"), I(65535))
        self.assertEqual(self.fill_value("x8000"), I(32768))

    def test_malformed_decimal_literals(self):
        for token in ("#", "#abc", "#5x", "#--3", "#+5", "# 5", "#-", "#1.5", "#x5"):
            with self.subTest(token=token):
                self.assertParseError(f".FILL {token}", "literal decimal mal formado")

    def test_malformed_hexadecimal_literals(self):
        for token in ("0x", "0X", "0xZZ", "0x1G", "0x-5"):
            with self.subTest(token=token):
                self.assertParseError(f".FILL {token}", "literal hexadecimal mal formado")

    def test_numbers_without_prefix_are_rejected(self):
        for token in ("5", "10", "-3", "007"):
            with self.subTest(token=token):
                self.assertParseError(f".FILL {token}", "literal sin prefijo")

    def test_unsupported_numeric_syntaxes(self):
        for token in ("0b101", "1x5", "3abc", "-x5", "-"):
            with self.subTest(token=token):
                self.assertParseError(f".FILL {token}", "operando no reconocido")

    def test_a_hex_literal_is_never_taken_for_a_label(self):
        self.assertEqual(statement_of("LEA R0, X25"), instruction("LEA", R(0), I(37)))
        self.assertEqual(statement_of("LEA R0, xend"), instruction("LEA", R(0), L("xend")))
        self.assertEqual(statement_of("BR x"), instruction("BR", L("x"), nzp=0b111))
        self.assertEqual(statement_of("BR X1"), instruction("BR", I(1), nzp=0b111))
        self.assertEqual(statement_of("BR xG"), instruction("BR", L("xG"), nzp=0b111))

    def test_huge_literals_do_not_crash(self):
        with self.assertRaises(ParseError):          # "demasiado largo" o "fuera de rango"
            parse_line(".FILL #" + "9" * 5000)
        self.assertParseError(".FILL x" + "F" * 5000, "fuera de rango")
        self.assertParseError(".FILL #" + "9" * 30, "fuera de rango")


# ----------------------------------------------------------------------
# 15-16. Operandos válidos/inválidos y cantidad de operandos
# ----------------------------------------------------------------------
class TestOperandKinds(ParserTestCase):

    def test_wrong_kind_of_operand(self):
        cases = [
            ("ADD R1, R2, FOO", "se esperaba registro o inmediato"),
            ("ADD #1, R2, R3", "se esperaba registro"),
            ("ADD R1, #2, R3", "se esperaba registro"),
            ("SUB R1, FOO, R3", "se esperaba registro"),
            ("LDW R1, R2, R3", "se esperaba desplazamiento inmediato"),
            ("LDW R1, #1, #2", "se esperaba registro"),
            ("STW R1, R2, LABEL", "se esperaba desplazamiento inmediato"),
            ("SHL R1, R2, R3", "se esperaba cantidad de desplazamiento"),
            ("SHR R1, R2, FOO", "se esperaba cantidad de desplazamiento"),
            ("SAR R1, #2, #3", "se esperaba registro"),
            ("JMP #5", "se esperaba registro"),
            ("JMP LOOP", "registro mal escrito"),
            ("JSRR #1", "se esperaba registro"),
            ("LEA R1, R2", "se esperaba etiqueta o desplazamiento en bytes"),
            ("LEA LABEL, R1", "se esperaba registro"),
            ("TRAP R1", "se esperaba vector de servicio"),
            ("TRAP FOO", "se esperaba vector de servicio"),
            ("BR R1", "se esperaba etiqueta o desplazamiento en palabras"),
            ("JSR R3", "se esperaba etiqueta o desplazamiento en palabras"),
            ("CMP #1, R2", "se esperaba registro"),
            ("CMP R1, FOO", "se esperaba registro o inmediato"),
            ("NOT R1, #5", "se esperaba registro"),
            ("NOT R1, FOO", "se esperaba registro"),
        ]
        for text, fragment in cases:
            with self.subTest(text=text):
                self.assertParseError(text, fragment)

    def test_mnemonics_cannot_be_used_as_label_references(self):
        self.assertParseError("BR ADD", "es un mnemónico")
        self.assertParseError("JSR halt", "es un mnemónico")

    def test_valid_operand_variants(self):
        cases = [
            ("CMP R1, #-8", instruction("CMP", R(1), I(-8))),
            ("CMP R1, x7", instruction("CMP", R(1), I(7))),
            ("LEA R2, #-128", instruction("LEA", R(2), I(-128))),
            ("JSR #1023", instruction("JSR", I(1023))),
            ("JSR _sub_1", instruction("JSR", L("_sub_1"))),
            ("LDI R1, R2, x0F", instruction("LDI", R(1), R(2), I(15))),
        ]
        for text, expected in cases:
            with self.subTest(text=text):
                self.assertEqual(statement_of(text), expected)

    def test_error_messages_name_the_instruction_and_operand(self):
        error = self.assertParseError("ADD R1, R2, FOO")
        self.assertIn("ADD, operando 3", error.message)
        error = self.assertParseError("BRnz #200")
        self.assertIn("BRnz, operando 1", error.message)


class TestOperandCount(ParserTestCase):

    def test_hand_written_arity_matches_isa(self):
        self.assertEqual(
            ARITY, {m: len(s.operands) for m, s in INSTRUCTIONS_BY_MNEMONIC.items()})

    def test_too_few_operands_for_every_instruction(self):
        for mnemonic, count in ARITY.items():
            if count == 0:
                continue
            with self.subTest(mnemonic=mnemonic):
                text = mnemonic + (" " + ", ".join(["R1"] * (count - 1)) if count > 1 else "")
                self.assertParseError(text, "faltan operandos")

    def test_too_many_operands_for_every_instruction(self):
        for mnemonic, count in ARITY.items():
            with self.subTest(mnemonic=mnemonic):
                self.assertParseError(mnemonic + " " + ", ".join(["R1"] * (count + 1)),
                                      "sobran operandos")

    def test_examples_from_the_specification(self):
        self.assertParseError("ADD R1, R2", "faltan operandos")
        self.assertParseError("ADD R1, R2, #5, R3", "sobran operandos")
        self.assertParseError("JMP R1, R2", "sobran operandos")
        self.assertParseError("BRnz", "faltan operandos")
        self.assertParseError("NOP R1", "sobran operandos")

    def test_message_reports_expected_and_received_counts(self):
        error = self.assertParseError("ADD R1, R2")
        self.assertIn("se esperan 3", error.message)
        self.assertIn("se recibieron 2", error.message)

    def test_empty_operands(self):
        for text in ("ADD R1,,R3", "ADD R1, R2,", "ADD ,R1,R2", "JMP ,"):
            with self.subTest(text=text):
                self.assertParseError(text, "operando vacío")

    def test_operands_glued_to_the_mnemonic(self):
        for text in ("ADD,R1,R2,R3", "TRAP#5", "JMP,R1"):
            with self.subTest(text=text):
                self.assertParseError(text, "falta un espacio")


# ----------------------------------------------------------------------
# Límites de cada tipo de operando
# ----------------------------------------------------------------------
class TestOperandRanges(ParserTestCase):

    def assertAccepted(self, text):
        self.assertIsNotNone(parse_line(text).statement, text)

    def assertOutOfRange(self, text, allowed):
        error = self.assertParseError(text, "fuera de rango")
        self.assertIn(allowed, error.message)

    def test_signed_4_bit_immediate(self):
        for mnemonic in ("ADD", "SUB", "AND", "OR", "XOR"):
            for ok in ("#-8", "#7", "#0", "x7", "0x0"):
                self.assertAccepted(f"{mnemonic} R1, R2, {ok}")
            for bad in ("#-9", "#8", "x8", "0xF", "#20", "#-100"):
                with self.subTest(mnemonic=mnemonic, value=bad):
                    self.assertOutOfRange(f"{mnemonic} R1, R2, {bad}", "-8 a 7")
        for ok in ("#-8", "#7"):
            self.assertAccepted(f"CMP R1, {ok}")
        for bad in ("#-9", "#8"):
            self.assertOutOfRange(f"CMP R1, {bad}", "-8 a 7")

    def test_hex_over_the_signed_range_reports_its_decimal_value(self):
        error = self.assertParseError("ADD R1, R2, x8", "fuera de rango")
        self.assertIn("x8 (= 8)", error.message)

    def test_unsigned_shift_amount(self):
        for mnemonic in ("SHL", "SHR", "SAR"):
            for ok in ("#0", "#15", "x0", "xF", "0xF"):
                self.assertAccepted(f"{mnemonic} R1, R2, {ok}")
            for bad in ("#-1", "#16", "x10", "#100"):
                with self.subTest(mnemonic=mnemonic, value=bad):
                    self.assertOutOfRange(f"{mnemonic} R1, R2, {bad}", "0 a 15")

    def test_signed_5_bit_memory_offset(self):
        for mnemonic in ("LDW", "STW", "LDBL", "LDBH", "STBL", "STBH", "LDI", "STI"):
            for ok in ("#-16", "#15", "#0", "xF"):
                self.assertAccepted(f"{mnemonic} R1, R2, {ok}")
            for bad in ("#-17", "#16", "x10"):
                with self.subTest(mnemonic=mnemonic, value=bad):
                    self.assertOutOfRange(f"{mnemonic} R1, R2, {bad}", "-16 a 15")

    def test_pc_relative_offset_of_br_and_lea_is_8_bits(self):
        for template in ("BR {}", "BRnz {}", "BRp {}", "LEA R1, {}"):
            for ok in ("#-128", "#127", "#0", "x7F"):
                self.assertAccepted(template.format(ok))
            for bad in ("#-129", "#128", "x80", "#1000"):
                with self.subTest(template=template, value=bad):
                    self.assertOutOfRange(template.format(bad), "-128 a 127")

    def test_pc_relative_offset_of_jsr_is_11_bits(self):
        for ok in ("#-1024", "#1023", "#0", "x3FF"):
            self.assertAccepted(f"JSR {ok}")
        for bad in ("#-1025", "#1024", "x400"):
            with self.subTest(value=bad):
                self.assertOutOfRange(f"JSR {bad}", "-1024 a 1023")

    def test_the_same_kind_has_a_different_range_in_br_and_jsr(self):
        self.assertAccepted("JSR #500")
        self.assertOutOfRange("BR #500", "-128 a 127")

    def test_trap_vector(self):
        for ok in ("#0", "#255", "x0", "xFF", "x20", "x21", "x22", "x25", "0xFF"):
            self.assertAccepted(f"TRAP {ok}")
        for bad in ("#-1", "#256", "x100", "0x1FF"):
            with self.subTest(value=bad):
                self.assertOutOfRange(f"TRAP {bad}", "0 a 255")

    def test_label_references_are_not_range_checked_here(self):
        self.assertAccepted("BR FAR_AWAY")
        self.assertAccepted("LEA R0, FAR_AWAY")


# ----------------------------------------------------------------------
# 17-18. Directivas
# ----------------------------------------------------------------------
class TestDirectives(ParserTestCase):

    def test_orig(self):
        for text, address in ((".ORIG x3000", 0x3000), (".ORIG #12288", 12288),
                              (".ORIG 0x3000", 0x3000), (".orig x0", 0),
                              (".ORIG xFFFF", 0xFFFF), (".Orig X10", 16),
                              (".ORIG x3001", 0x3001)):
            with self.subTest(text=text):
                self.assertEqual(statement_of(text), OrigDirective(address))

    def test_end(self):
        self.assertEqual(statement_of(".END"), EndDirective())
        self.assertEqual(statement_of(".end"), EndDirective())

    def test_fill(self):
        cases = ((".FILL #5", I(5)), (".FILL #-5", I(-5)), (".FILL x1234", I(0x1234)),
                 (".FILL xFFFF", I(65535)), (".fill 0x10", I(16)),
                 (".FILL LABEL", L("LABEL")), (".FILL _p", L("_p")))
        for text, value in cases:
            with self.subTest(text=text):
                self.assertEqual(statement_of(text), FillDirective(value))

    def test_blkw(self):
        for text, count in ((".BLKW #10", 10), (".BLKW x10", 16), (".BLKW #1", 1),
                            (".blkw 0x8", 8)):
            with self.subTest(text=text):
                self.assertEqual(statement_of(text), BlkwDirective(count))

    def test_stringz(self):
        cases = [
            ('.STRINGZ "Hola"', "Hola"),
            ('.STRINGZ ""', ""),
            ('.STRINGZ "a, b"', "a, b"),
            ('.STRINGZ "a:b"', "a:b"),
            ('.STRINGZ "  espacios  "', "  espacios  "),
            ('.STRINGZ "línea\\n"', "línea\n"),
            ('.STRINGZ "\\t\\r\\\\\\""', "\t\r\\\""),
            ('.stringz "x"', "x"),
            ('.STRINGZ "ñ"', "ñ"),
            ('.STRINGZ "a"   ; comentario', "a"),
        ]
        for text, value in cases:
            with self.subTest(text=text):
                self.assertEqual(statement_of(text), StringzDirective(value))

    def test_external(self):
        self.assertEqual(statement_of(".EXTERNAL PRINTF"), ExternalDirective("PRINTF"))
        self.assertEqual(statement_of(".external _x1"), ExternalDirective("_x1"))

    def test_unknown_directives(self):
        for text in (".FOO", ".DATA 5", ".ORIGIN x3000", ".", ".fil #1",
                     '.STRING "x"', ".END2", ".WORD #1"):
            with self.subTest(text=text):
                self.assertParseError(text, "directiva desconocida")

    def test_missing_or_extra_directive_operands(self):
        cases = [
            (".ORIG", "espera 1 operando"), (".ORIG x3000, x4000", "espera 1 operando"),
            (".END x1", "espera 0 operandos"),
            (".FILL", "espera 1 operando"), (".FILL #1, #2", "espera 1 operando"),
            (".BLKW", "espera 1 operando"), (".BLKW #1, #2", "espera 1 operando"),
            (".STRINGZ", "espera 1 operando"),
            (".EXTERNAL", "espera 1 operando"), (".EXTERNAL A, B", "espera 1 operando"),
            (".ORIG,", "falta un espacio"), (".FILL#5", "falta un espacio"),
        ]
        for text, fragment in cases:
            with self.subTest(text=text):
                self.assertParseError(text, fragment)

    def test_wrong_kind_of_directive_operand(self):
        cases = [
            (".ORIG FOO", "se esperaba un literal numérico"),
            (".ORIG R1", "se esperaba un literal numérico"),
            (".ORIG 3000", "literal sin prefijo"),
            (".FILL R1", "se esperaba un número o una etiqueta"),
            (".BLKW LABEL", "se esperaba un literal numérico"),
            (".EXTERNAL #5", "se esperaba un nombre de símbolo"),
            (".EXTERNAL R1", "se esperaba un nombre de símbolo"),
            (".EXTERNAL x25", "se esperaba un nombre de símbolo"),
            (".EXTERNAL ADD", "es un mnemónico"),
        ]
        for text, fragment in cases:
            with self.subTest(text=text):
                self.assertParseError(text, fragment)

    def test_string_errors(self):
        cases = [
            ('.STRINGZ Hola', "entre comillas dobles"),
            ('.STRINGZ "Hola', "cadena sin cerrar"),
            ('.STRINGZ "abc\\"', "cadena sin cerrar"),
            ('.STRINGZ "a" "b"', "texto inesperado"),
            ('.STRINGZ "a" x', "texto inesperado"),
            ('.STRINGZ "\\q"', "secuencia de escape desconocida"),
            ('.STRINGZ "a\\', "secuencia de escape desconocida"),
            ('.STRINGZ "€"', "no cabe en un byte"),
            ('.STRINGZ "日本"', "no cabe en un byte"),
        ]
        for text, fragment in cases:
            with self.subTest(text=text):
                self.assertParseError(text, fragment)

    def test_directive_value_limits(self):
        for text in (".ORIG x0", ".ORIG xFFFF", ".FILL #-32768", ".FILL #65535",
                     ".FILL x0", ".FILL xFFFF", ".BLKW #1", ".BLKW #1000"):
            with self.subTest(ok=text):
                self.assertIsNotNone(statement_of(text))
        for text in (".ORIG #-1", ".ORIG x10000", ".ORIG #65536", ".FILL #-32769",
                     ".FILL x10000", ".FILL #65536", ".BLKW #0", ".BLKW #-1"):
            with self.subTest(bad=text):
                self.assertParseError(text, "fuera de rango")

    def test_directive_range_messages_show_the_allowed_range(self):
        self.assertIn("0 a 65535", self.assertParseError(".ORIG #-1").message)
        self.assertIn("-32768 a 65535", self.assertParseError(".FILL #65536").message)
        self.assertIn("a partir de 1", self.assertParseError(".BLKW #0").message)


# ----------------------------------------------------------------------
# 19-21. Programas completos y estructura
# ----------------------------------------------------------------------
class TestPrograms(ParserTestCase):

    def test_empty_programs(self):
        for source in ("", "\n", "\n\n  \n\t\n", "; solo comentarios\n\n   ; otro\n"):
            with self.subTest(source=repr(source)):
                self.assertEqual(parse_program(source), Program(()))

    def test_a_complete_program(self):
        source = "\n".join([
            "; Programa de prueba",                  # 1
            "        .ORIG x3000",                   # 2
            "START:  LEA R0, MSG",                   # 3
            "        TRAP x22",                      # 4
            "LOOP:   ADD R1, R1, #-1   ; baja",      # 5
            "        BRp LOOP",                      # 6
            "        HALT",                          # 7
            'MSG:    .STRINGZ "Hi!"',                # 8
            "PTR:    .FILL MSG",                     # 9
            "BUF:    .BLKW #4",                      # 10
            "        .END",                          # 11
        ])
        program = parse_program(source)
        actual = [(l.line_number, l.label, l.statement) for l in program.lines]
        self.assertEqual(actual, [
            (2, None, OrigDirective(0x3000)),
            (3, "START", instruction("LEA", R(0), L("MSG"))),
            (4, None, instruction("TRAP", I(0x22))),
            (5, "LOOP", instruction("ADD", R(1), R(1), I(-1))),
            (6, None, instruction("BR", L("LOOP"), nzp=0b001)),
            (7, None, instruction("HALT")),
            (8, "MSG", StringzDirective("Hi!")),
            (9, "PTR", FillDirective(L("MSG"))),
            (10, "BUF", BlkwDirective(4)),
            (11, None, EndDirective()),
        ])

    def test_blank_and_comment_lines_are_dropped_but_numbering_is_kept(self):
        program = parse_program("\n; c\n\nNOP\n   \nHALT")
        self.assertEqual([l.line_number for l in program.lines], [4, 6])

    def test_line_endings(self):
        for source in ("NOP\r\nHALT\r\n", "NOP\nHALT\n", "NOP\rHALT\r"):
            with self.subTest(source=repr(source)):
                program = parse_program(source)
                self.assertEqual([(l.line_number, l.statement.mnemonic)
                                  for l in program.lines], [(1, "NOP"), (2, "HALT")])

    def test_result_is_immutable(self):
        program = parse_program("NOP")
        self.assertIsInstance(program.lines, tuple)
        with self.assertRaises(dataclasses.FrozenInstanceError):
            program.lines = ()
        with self.assertRaises(dataclasses.FrozenInstanceError):
            program.lines[0].label = "X"
        with self.assertRaises(dataclasses.FrozenInstanceError):
            program.lines[0].statement.mnemonic = "HALT"

    def test_program_must_be_text(self):
        for bad in (None, b"NOP", ["NOP"], 5):
            with self.subTest(value=bad):
                with self.assertRaises(TypeError):
                    parse_program(bad)

    # --- después de .END --------------------------------------------
    def test_nothing_but_blanks_and_comments_after_end(self):
        program = parse_program(".END\n\n   \n; fin\n\t; otro")
        self.assertEqual(len(program.lines), 1)

    def test_statements_after_end_are_rejected(self):
        cases = {
            "instrucción": ".END\nADD R1, R2, #5",
            "etiqueta sola": ".END\nFIN:",
            "directiva": ".END\n.FILL #1",
            "segundo .END": ".END\n.END",
            "otro .ORIG": ".END\n.ORIG x3000",
        }
        for name, source in cases.items():
            with self.subTest(case=name):
                with self.assertRaises(ParseErrors) as context:
                    parse_program(source)
                (error,) = context.exception.errors
                self.assertEqual(error.line_number, 2)
                self.assertIn("después de .END", error.message)
                self.assertIn("línea 1", error.message)

    def test_a_label_may_share_the_line_with_end(self):
        program = parse_program("NOP\nFIN: .END")
        self.assertEqual(program.lines[-1].label, "FIN")

    # --- .ORIG ------------------------------------------------------
    def test_only_one_orig(self):
        with self.assertRaises(ParseErrors) as context:
            parse_program(".ORIG x3000\nNOP\n.ORIG x4000")
        (error,) = context.exception.errors
        self.assertEqual(error.line_number, 3)
        self.assertIn("un .ORIG", error.message)
        self.assertIn("línea 1", error.message)

    def test_presence_and_position_of_orig_and_end_are_not_checked_here(self):
        self.assertEqual(len(parse_program("NOP\n.ORIG x3000").lines), 2)
        self.assertEqual(len(parse_program("NOP\nHALT").lines), 2)


class TestErrorReporting(ParserTestCase):

    def test_single_line_error_carries_line_number_and_source(self):
        with self.assertRaises(ParseError) as context:
            parse_line("FOO R1", 7)
        error = context.exception
        self.assertEqual((error.line_number, error.source), (7, "FOO R1"))
        self.assertTrue(str(error).startswith("línea 7: "))
        self.assertIn("FOO", str(error))

    def test_default_line_number_is_one(self):
        self.assertParseError("FOO", line=1)

    def test_program_errors_have_the_right_line_numbers(self):
        source = "\n".join([
            "; comentario",            # 1
            "NOP",                     # 2
            "ADD R1, R2",              # 3  <- error
            "",                        # 4
            "HALT",                    # 5
            "ADD R8, R1, R2",          # 6  <- error
        ])
        with self.assertRaises(ParseErrors) as context:
            parse_program(source)
        errors = context.exception.errors
        self.assertEqual([e.line_number for e in errors], [3, 6])
        self.assertEqual(errors[0].source, "ADD R1, R2")
        self.assertIn("faltan operandos", errors[0].message)
        self.assertIn("registro inexistente", errors[1].message)

    def test_all_errors_are_collected_in_order(self):
        source = "FOO\nNOP\nA: NOP\nA: NOP\nADD R1\n.ZZZ\n"
        with self.assertRaises(ParseErrors) as context:
            parse_program(source)
        self.assertEqual([e.line_number for e in context.exception.errors], [1, 4, 5, 6])
        text = str(context.exception)
        self.assertIn("4 error(es)", text)
        for number in (1, 4, 5, 6):
            self.assertIn(f"línea {number}:", text)

    def test_errors_are_specific_not_generic(self):
        for text in ("FOO R1", "ADD R1, R2", "ADD R1, R2, #20", "ADD R8, R1, R2",
                     "SHL R1, R2, R3", ".ZZZ", ".ORIG", "BRnz", "ADD R1, R2, 5"):
            with self.subTest(text=text):
                message = self.assertParseError(text).message
                self.assertNotEqual(message.lower(), "error de sintaxis")
                self.assertGreater(len(message), 15)


# ----------------------------------------------------------------------
# Estructura del módulo
# ----------------------------------------------------------------------
class TestModuleStructure(unittest.TestCase):

    def test_parser_depends_only_on_isa(self):
        tree = ast.parse(Path(parser_module.__file__).read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)
            elif isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
        project = {name for name in imported
                   if name.startswith(("simulator", "assembler"))}
        self.assertEqual(project, {"simulator.isa"})

    def test_parser_has_no_second_mnemonic_table(self):
        tree = ast.parse(Path(parser_module.__file__).read_text(encoding="utf-8"))
        docstrings = {id(node.value) for node in ast.walk(tree)
                      if isinstance(node, ast.Expr)}
        literals = {node.value for node in ast.walk(tree)
                    if isinstance(node, ast.Constant) and isinstance(node.value, str)
                    and id(node) not in docstrings}
        # Único mnemónico que el parser nombra: BR (para sus variantes).
        self.assertEqual(literals & MNEMONICS_26, {"BR"})

    def test_statement_types_are_frozen_dataclasses(self):
        for cls in (Register, Immediate, LabelRef, Instruction, OrigDirective,
                    EndDirective, FillDirective, BlkwDirective, StringzDirective,
                    ExternalDirective, ParsedLine, Program):
            with self.subTest(cls=cls.__name__):
                self.assertTrue(dataclasses.is_dataclass(cls))
                self.assertTrue(cls.__dataclass_params__.frozen)


if __name__ == "__main__":
    unittest.main()