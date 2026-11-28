"""Pruebas de assembler/assembler.py (ejecutar desde la carpeta raíz Lab3C).

El orquestador solo coordina, así que las pruebas se dividen en dos tipos:
  - de COMPORTAMIENTO: programas reales ensamblados de punta a punta, con bytes
    calculados a mano (no generados con el código que se prueba);
  - de COORDINACIÓN: con unittest.mock se comprueba QUÉ etapas se llaman, con qué
    objetos y que no se llame a la siguiente cuando una falla.
"""

import ast
import inspect
import io
import unittest
from pathlib import Path
from types import MappingProxyType
from unittest import mock

from assembler import assembler as assembler_module
from assembler.assembler import ASSEMBLY_ERRORS, assemble
from assembler.encoder import EncodedProgram, EncodeErrors
from assembler.parser import ParseErrors, Program
from assembler.symbols import SymbolErrors, SymbolTable
from simulator.cpu import CPU
from simulator.traps import ConsoleIO


def source(*lines):
    return "\n".join(lines)


def cpu_with(encoded, io_in=""):
    console = ConsoleIO(io.StringIO(io_in), io.StringIO())
    cpu = CPU(io=console)
    cpu.load_program(encoded.data, encoded.origin)
    return cpu, console


class AssemblerTestCase(unittest.TestCase):

    def assertErrorLines(self, exception_type, text, expected, externals=None):
        """assemble(text) debe lanzar `exception_type` con (línea, fragmento) en ese orden."""
        with self.assertRaises(exception_type) as context:
            assemble(text, externals)
        errors = context.exception.errors
        self.assertEqual([e.line_number for e in errors], [line for line, _ in expected],
                         [str(e) for e in errors])
        for error, (_, fragment) in zip(errors, expected):
            self.assertIn(fragment, error.message)
        return context.exception


# ----------------------------------------------------------------------
# A. Programa válido
# ----------------------------------------------------------------------
class TestValidProgram(AssemblerTestCase):

    SIMPLE = source(".ORIG x3000", "ADD R0, R0, #1", "HALT", ".END")

    def test_returns_an_encoded_program(self):
        self.assertIsInstance(assemble(self.SIMPLE), EncodedProgram)

    def test_bytes_origin_end_and_size(self):
        # ADD R0,R0,#1 = 00000_000_000_1_0001 = 0x0011 -> 11 00 ; HALT = 0xC000 -> 00 C0
        result = assemble(self.SIMPLE)
        self.assertEqual(result.data, b"\x11\x00\x00\xC0")
        self.assertEqual((result.origin, result.size, result.end_address),
                         (0x3000, 4, 0x3004))

    def test_the_result_loads_and_runs_in_the_cpu(self):
        cpu, _ = cpu_with(assemble(self.SIMPLE))
        self.assertEqual(cpu.registers.pc, 0x3000)
        cpu.run()
        self.assertEqual(cpu.registers.read(0), 1)
        self.assertTrue(cpu.halted)
        self.assertEqual(cpu.instruction_count, 2)

    def test_a_program_that_generates_no_bytes(self):
        result = assemble(source(".ORIG x4000", ".END"))
        self.assertEqual((result.data, result.origin, result.end_address), (b"", 0x4000, 0x4000))

    def test_line_endings_and_comments_do_not_change_the_result(self):
        plain = assemble(self.SIMPLE)
        for text in (self.SIMPLE.replace("\n", "\r\n"),
                     self.SIMPLE.replace("\n", "\r"),
                     "; comentario\n\n" + self.SIMPLE + "\n\n",
                     ".orig x3000\nadd r0, r0, #1 ; suma\nhalt\n.end"):
            with self.subTest(repr(text[:25])):
                self.assertEqual(assemble(text), plain)

    def test_it_is_deterministic(self):
        self.assertEqual(assemble(self.SIMPLE), assemble(self.SIMPLE))

    def test_the_source_must_be_text(self):
        for bad in (None, 5, b".ORIG x3000", [".ORIG x3000"]):
            with self.subTest(repr(bad)), self.assertRaises(TypeError):
                assemble(bad)


# ----------------------------------------------------------------------
# B. Errores del parser
# ----------------------------------------------------------------------
class TestParserErrors(AssemblerTestCase):

    def test_unknown_mnemonic(self):
        self.assertErrorLines(ParseErrors, source(".ORIG x3000", "FOO R1", ".END"),
                              [(2, "mnemónico desconocido 'FOO'")])

    def test_wrong_operand_count(self):
        self.assertErrorLines(ParseErrors, source(".ORIG x3000", "ADD R1, R2", ".END"),
                              [(2, "faltan operandos")])
        self.assertErrorLines(ParseErrors, source(".ORIG x3000", "NOP R1", ".END"),
                              [(2, "NOP")])

    def test_invalid_register(self):
        self.assertErrorLines(ParseErrors, source(".ORIG x3000", "ADD R8, R1, R2", ".END"),
                              [(2, "registro inexistente 'R8'")])

    def test_bad_syntax(self):
        self.assertErrorLines(ParseErrors, source(".ORIG x3000", "ADD R1,, R2", ".END"),
                              [(2, "operando vacío")])

    def test_a_duplicate_label_is_caught_by_the_parser(self):
        # La detección vive en parse_program: llega como ParseErrors, no como SymbolErrors.
        self.assertErrorLines(ParseErrors, source(".ORIG x3000", "A: NOP", "A: NOP", ".END"),
                              [(3, "etiqueta 'A' duplicada")])

    def test_every_parser_error_is_reported_together(self):
        error = self.assertErrorLines(
            ParseErrors, source(".ORIG x3000", "FOO", "NOP", "ADD R8, R1, R2", "BAR", ".END"),
            [(2, "FOO"), (4, "R8"), (5, "BAR")])
        self.assertEqual(error.errors[0].source, "FOO")       # se conserva el texto original

    def test_parse_errors_stop_the_pipeline_even_if_later_stages_would_fail(self):
        # Además del error de sintaxis hay una etiqueta inexistente (error de symbols):
        # solo se informa la primera etapa que falla.
        text = source(".ORIG x3000", "FOO", "BR NOWHERE", ".END")
        self.assertErrorLines(ParseErrors, text, [(2, "FOO")])


# ----------------------------------------------------------------------
# C. Errores de la tabla de símbolos
# ----------------------------------------------------------------------
class TestSymbolTableErrors(AssemblerTestCase):

    def test_reference_to_an_undefined_label(self):
        error = self.assertErrorLines(
            SymbolErrors, source(".ORIG x3000", "BR NOWHERE", ".END"),
            [(2, "referencia a un símbolo no definido: 'NOWHERE'")])
        self.assertEqual(error.errors[0].source, "BR NOWHERE")

    def test_odd_orig(self):
        self.assertErrorLines(SymbolErrors, source(".ORIG x3001", "NOP", ".END"),
                              [(1, ".ORIG debe recibir una dirección par")])

    def test_missing_orig_is_a_global_error(self):
        error = self.assertErrorLines(SymbolErrors, source("NOP", ".END"),
                                      [(None, "falta la directiva .ORIG")])
        self.assertIsNone(error.errors[0].line_number)

    def test_layout_overflow(self):
        self.assertErrorLines(SymbolErrors, source(".ORIG xFFFE", "NOP", "NOP", ".END"),
                              [(3, "desbordamiento de memoria")])

    def test_a_label_clashing_with_an_external_declaration(self):
        self.assertErrorLines(
            SymbolErrors, source(".ORIG x3000", ".EXTERNAL X", "X: NOP", ".END"),
            [(3, "entra en conflicto con el símbolo externo")])

    def test_all_symbol_errors_are_reported_together(self):
        self.assertErrorLines(
            SymbolErrors, source(".ORIG x3000", "BR A", "BR B", ".END"),
            [(2, "'A'"), (3, "'B'")])

    def test_the_encoder_does_not_run_after_a_symbol_error(self):
        with mock.patch.object(assembler_module, "encode_program") as encoder:
            with self.assertRaises(SymbolErrors):
                assemble(source(".ORIG x3000", "BR NOWHERE", ".END"))
        encoder.assert_not_called()

    def test_neither_symbols_nor_encoder_run_after_a_parse_error(self):
        with mock.patch.object(assembler_module, "build_symbol_table") as symbols, \
                mock.patch.object(assembler_module, "encode_program") as encoder:
            with self.assertRaises(ParseErrors):
                assemble(source(".ORIG x3000", "FOO", ".END"))
        symbols.assert_not_called()
        encoder.assert_not_called()


# ----------------------------------------------------------------------
# D. Errores del encoder
# ----------------------------------------------------------------------
class TestEncoderErrors(AssemblerTestCase):

    def test_branch_out_of_reach_preserves_the_original_error(self):
        error = self.assertErrorLines(
            EncodeErrors, source(".ORIG x3000", "BR T", ".BLKW #128", "T: NOP", ".END"),
            [(2, "fuera de alcance")])
        self.assertIn("128 palabras", error.errors[0].message)
        self.assertIn("-128 a 127", error.errors[0].message)
        self.assertEqual(error.errors[0].source, "BR T")

    def test_branch_reach_boundaries_through_the_whole_pipeline(self):
        # +127 palabras: último destino válido; +128: primero inválido.
        ok = assemble(source(".ORIG x3000", "BR T", ".BLKW #127", "T: NOP", ".END"))
        self.assertEqual(ok.data[:2], b"\x7F\x87")            # 10000_111_01111111 = 0x877F
        self.assertEqual(ok.size, 2 + 254 + 2)
        with self.assertRaises(EncodeErrors):
            assemble(source(".ORIG x3000", "BR T", ".BLKW #128", "T: NOP", ".END"))

    def test_backward_boundaries(self):
        ok = assemble(source(".ORIG x3000", "T: NOP", ".BLKW #126", "BR T", ".END"))
        self.assertEqual(ok.data[-2:], b"\x80\x87")           # 10000_111_10000000 = 0x8780
        self.assertErrorLines(
            EncodeErrors, source(".ORIG x3000", "T: NOP", ".BLKW #127", "BR T", ".END"),
            [(4, "-129 palabras")])

    def test_branch_to_an_odd_address(self):
        self.assertErrorLines(
            EncodeErrors,
            source(".ORIG x3000", "BR S", "HALT", '.STRINGZ ""', 'S: .STRINGZ "Z"', ".END"),
            [(2, "dirección impar")])

    def test_independent_encoder_errors_are_reported_together(self):
        self.assertErrorLines(
            EncodeErrors,
            source(".ORIG x3000", "JSR T", "BR T", ".BLKW #2000", "T: NOP", ".END"),
            [(2, "fuera de alcance"), (3, "fuera de alcance")])

    def test_the_encoder_error_is_the_object_the_encoder_raised(self):
        sentinel = EncodeErrors([])
        with mock.patch.object(assembler_module, "encode_program", side_effect=sentinel):
            with self.assertRaises(EncodeErrors) as context:
                assemble(source(".ORIG x3000", "NOP", ".END"))
        self.assertIs(context.exception, sentinel)            # no se envuelve ni se copia


# ----------------------------------------------------------------------
# E. Símbolos externos
# ----------------------------------------------------------------------
class TestExternalSymbols(AssemblerTestCase):

    CALL = source(".ORIG x3000", ".EXTERNAL ROUTINE", "JSR ROUTINE", "HALT", ".END")

    def test_declared_and_used_external(self):
        # JSR en x3000, ROUTINE = x3010: PC siguiente x3002, +14 bytes = +7 palabras:
        # 10001_00000000111 = 0x8807 -> 07 88.
        result = assemble(self.CALL, {"ROUTINE": 0x3010})
        self.assertEqual(result.data, b"\x07\x88\x00\xC0")

    def test_external_symbols_can_be_given_by_keyword_or_position(self):
        by_position = assemble(self.CALL, {"ROUTINE": 0x3010})
        by_keyword = assemble(self.CALL, external_symbols={"ROUTINE": 0x3010})
        self.assertEqual(by_position, by_keyword)

    def test_the_mapping_reaches_the_encoder_unchanged(self):
        # Se transmite el MISMO objeto, y con el nombre de parámetro real del encoder.
        externals = MappingProxyType({"ROUTINE": 0x3010})
        with mock.patch.object(assembler_module, "encode_program",
                               wraps=assembler_module.encode_program) as encoder:
            assemble(self.CALL, externals)
        (program, table), keywords = encoder.call_args
        self.assertIsInstance(program, Program)
        self.assertIsInstance(table, SymbolTable)
        self.assertEqual(list(keywords), ["external_symbols"])
        self.assertIs(keywords["external_symbols"], externals)

    def test_without_external_symbols_none_is_forwarded(self):
        with mock.patch.object(assembler_module, "encode_program",
                               wraps=assembler_module.encode_program) as encoder:
            assemble(source(".ORIG x3000", "NOP", ".END"))
        self.assertIsNone(encoder.call_args.kwargs["external_symbols"])

    def test_a_missing_definition_is_an_encoder_error(self):
        for externals in (None, {}):
            with self.subTest(externals):
                self.assertErrorLines(EncodeErrors, self.CALL,
                                      [(3, "'ROUTINE' no tiene una dirección válida")],
                                      externals)

    def test_an_unreachable_external(self):
        self.assertErrorLines(EncodeErrors, self.CALL, [(3, "fuera de alcance")],
                              {"ROUTINE": 0x9000})

    def test_a_key_that_was_not_declared(self):
        self.assertErrorLines(
            EncodeErrors, source(".ORIG x3000", "NOP", ".END"),
            [(None, "'GHOST' no fue declarado con .EXTERNAL")], {"GHOST": 0x3000})

    def test_a_declared_but_unused_external_needs_no_address(self):
        result = assemble(source(".ORIG x3000", ".EXTERNAL UNUSED", "NOP", ".END"))
        self.assertEqual(result.data, b"\x00\xB8")

    def test_an_undeclared_name_in_the_source_is_a_symbol_error_not_an_encoder_one(self):
        # Sin .EXTERNAL, el nombre no existe para la tabla de símbolos: ni se llega al encoder.
        self.assertErrorLines(
            SymbolErrors, source(".ORIG x3000", "JSR ROUTINE", ".END"),
            [(2, "'ROUTINE'")], {"ROUTINE": 0x3010})

    def test_fill_with_an_external_is_its_absolute_address(self):
        result = assemble(source(".ORIG x3000", ".EXTERNAL BUF", ".FILL BUF", ".END"),
                          {"BUF": 0xABCD})
        self.assertEqual(result.data, b"\xCD\xAB")

    def test_linking_an_external_routine_and_running_it(self):
        library = assemble(source(".ORIG x3100", "ADD R0, R0, #1", "JMP LR", ".END"))
        main = assemble(source(".ORIG x3000", ".EXTERNAL INC", "JSR INC", "JSR INC",
                               "HALT", ".END"), {"INC": library.origin})
        cpu, _ = cpu_with(main)
        cpu.load_program(library.data, library.origin, set_pc=False)
        cpu.run()
        self.assertEqual(cpu.registers.read(0), 2)


# ----------------------------------------------------------------------
# F. Flujo completo
# ----------------------------------------------------------------------
FULL_PROGRAM = source(
    ".ORIG x3000",
    "START: LEA R0, MSG        ; x3000",
    "       TRAP x22           ; x3002",
    "       BR DONE            ; x3004",
    "VAL:   .FILL #-2          ; x3006",
    "BUF:   .BLKW #2           ; x3008",
    'MSG:   .STRINGZ "Hi"      ; x300C (3 bytes)',
    "DONE:  HALT               ; x300F es impar: relleno, HALT en x3010",
    ".END",
)
# Bytes calculados a mano:
#   LEA R0, MSG   MSG=x300C, PC sig.=x3002 -> +10 bytes: 10011_000_00001010 = 0x980A -> 0A 98
#   TRAP x22      10110_00100010_000 = 0xB110 -> 10 B1
#   BR DONE       DONE=x3010, PC sig.=x3006 -> +10 bytes = +5 palabras:
#                 10000_111_00000101 = 0x8705 -> 05 87
#   .FILL #-2     0xFFFE -> FE FF
#   .BLKW #2      4 bytes en cero
#   .STRINGZ "Hi" 48 69 00
#   relleno       00
#   HALT          0xC000 -> 00 C0
FULL_BYTES = (b"\x0A\x98" b"\x10\xB1" b"\x05\x87" b"\xFE\xFF" b"\x00\x00\x00\x00"
              b"Hi\x00" b"\x00" b"\x00\xC0")


class TestFullFlow(AssemblerTestCase):

    def test_bytes_and_layout(self):
        result = assemble(FULL_PROGRAM)
        self.assertEqual(result.data, FULL_BYTES)
        self.assertEqual((result.origin, result.size, result.end_address),
                         (0x3000, 18, 0x3012))

    def test_the_orchestrator_matches_calling_the_three_stages_by_hand(self):
        from assembler.encoder import encode_program
        from assembler.parser import parse_program
        from assembler.symbols import build_symbol_table
        program = parse_program(FULL_PROGRAM)
        by_hand = encode_program(program, build_symbol_table(program))
        self.assertEqual(assemble(FULL_PROGRAM), by_hand)

    def test_execution_in_the_cpu(self):
        encoded = assemble(FULL_PROGRAM)
        cpu, console = cpu_with(encoded)
        cpu.run()
        self.assertEqual(console.stdout.getvalue(), "Hi")
        self.assertTrue(cpu.halted)
        self.assertEqual(cpu.instruction_count, 4)             # LEA, TRAP, BR, HALT
        self.assertEqual(cpu.memory.read_word(0x3006), 0xFFFE)  # .FILL #-2

    def test_every_stage_receives_the_object_the_previous_one_produced(self):
        with mock.patch.object(assembler_module, "parse_program",
                               wraps=assembler_module.parse_program) as parse, \
                mock.patch.object(assembler_module, "build_symbol_table",
                                  wraps=assembler_module.build_symbol_table) as symbols, \
                mock.patch.object(assembler_module, "encode_program",
                                  wraps=assembler_module.encode_program) as encoder:
            result = assemble(FULL_PROGRAM)
        parse.assert_called_once_with(FULL_PROGRAM)
        symbols.assert_called_once()
        encoder.assert_called_once()
        (symbols_program,), _ = symbols.call_args
        (encoder_program, encoder_table), _ = encoder.call_args
        self.assertIs(encoder_program, symbols_program)           # mismo AST, sin copiar
        self.assertIsInstance(encoder_table, SymbolTable)
        self.assertEqual(result.size, encoder_table.size)         # el resultado es el del encoder

    def test_stages_run_in_order(self):
        order = []

        def tracing(name, function):
            def wrapper(*args, **kwargs):
                order.append(name)
                return function(*args, **kwargs)
            return wrapper

        with mock.patch.object(assembler_module, "parse_program",
                               tracing("parse", assembler_module.parse_program)), \
                mock.patch.object(assembler_module, "build_symbol_table",
                                  tracing("symbols", assembler_module.build_symbol_table)), \
                mock.patch.object(assembler_module, "encode_program",
                                  tracing("encode", assembler_module.encode_program)):
            assemble(FULL_PROGRAM)
        self.assertEqual(order, ["parse", "symbols", "encode"])


# ----------------------------------------------------------------------
# G. Errores: propagación y captura conjunta
# ----------------------------------------------------------------------
class TestErrorPropagation(AssemblerTestCase):

    BAD = {
        ParseErrors: source(".ORIG x3000", "FOO", ".END"),
        SymbolErrors: source(".ORIG x3000", "BR NOWHERE", ".END"),
        EncodeErrors: source(".ORIG x3000", "BR T", ".BLKW #128", "T: NOP", ".END"),
    }

    def test_each_stage_error_keeps_its_own_type(self):
        for expected, text in self.BAD.items():
            with self.subTest(expected.__name__), self.assertRaises(expected) as context:
                assemble(text)
            self.assertIs(type(context.exception), expected)

    def test_any_assembler_error_is_caught_with_assembly_errors(self):
        for expected, text in self.BAD.items():
            with self.subTest(expected.__name__):
                try:
                    assemble(text)
                except ASSEMBLY_ERRORS as error:
                    self.assertIsInstance(error, expected)
                else:
                    self.fail("debía fallar")

    def test_assembly_errors_lists_the_three_stage_exceptions(self):
        self.assertEqual(ASSEMBLY_ERRORS, (ParseErrors, SymbolErrors, EncodeErrors))

    def test_a_valid_program_raises_nothing_and_type_errors_are_not_assembly_errors(self):
        assemble(source(".ORIG x3000", ".END"))
        with self.assertRaises(TypeError):
            try:
                assemble(None)
            except ASSEMBLY_ERRORS:
                self.fail("un TypeError de uso no es un error de ensamblado")

    def test_the_message_of_the_original_error_is_not_altered(self):
        with self.assertRaises(ParseErrors) as via_assemble:
            assemble(self.BAD[ParseErrors])
        from assembler.parser import parse_program
        with self.assertRaises(ParseErrors) as direct:
            parse_program(self.BAD[ParseErrors])
        self.assertEqual(str(via_assemble.exception), str(direct.exception))


# ----------------------------------------------------------------------
# H. Estructura del módulo
# ----------------------------------------------------------------------
class TestModuleStructure(unittest.TestCase):

    @staticmethod
    def tree():
        return ast.parse(Path(assembler_module.__file__).read_text(encoding="utf-8"))

    def test_it_depends_only_on_the_three_stages(self):
        imported = set()
        for node in ast.walk(self.tree()):
            if isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)
            elif isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
        self.assertEqual({n for n in imported if n.startswith(("simulator", "assembler"))},
                         {"assembler.parser", "assembler.symbols", "assembler.encoder"})

    def test_it_neither_catches_nor_raises_exceptions(self):
        # Solo coordina: las excepciones de las etapas se propagan sin tocarse.
        for node in ast.walk(self.tree()):
            if isinstance(node, (ast.Try, ast.Raise)):
                self.fail(f"try/raise en la línea {node.lineno}")

    def test_it_has_no_branching_logic(self):
        for node in ast.walk(self.tree()):
            if isinstance(node, (ast.If, ast.For, ast.While)):
                self.fail(f"lógica de control en la línea {node.lineno}")

    def test_the_public_api(self):
        self.assertEqual(sorted(assembler_module.__all__), ["ASSEMBLY_ERRORS", "assemble"])
        parameters = inspect.signature(assemble).parameters
        self.assertEqual(list(parameters), ["source", "external_symbols"])
        self.assertIsNone(parameters["external_symbols"].default)


if __name__ == "__main__":
    unittest.main()
