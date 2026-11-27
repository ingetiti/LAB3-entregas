"""Pruebas de assembler/symbols.py (ejecutar desde la carpeta raíz Lab3C).

Las direcciones esperadas están calculadas a mano; ninguna expectativa se
genera con el código que se prueba. Los programas se escriben de dos formas:
  - como texto, pasando por parse_program (integración con el parser real);
  - armados a mano con ParsedLine, para casos que el parser ya rechaza
    (.ORIG duplicado, etiquetas repetidas...) y que symbols.py debe seguir
    detectando por su cuenta.
"""

import ast
import dataclasses
import hashlib
import inspect
import itertools
import unittest
from pathlib import Path

from assembler import symbols as symbols_module
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
    Program,
    StringzDirective,
    parse_program,
)
from assembler.symbols import (
    Padding,
    SymbolError,
    SymbolErrors,
    SymbolTable,
    build_symbol_table,
)


def source(*lines):
    return "\n".join(lines)


def build(*lines):
    """Texto -> parse_program -> build_symbol_table."""
    return build_symbol_table(parse_program(source(*lines)))


def prog(*items):
    """Program armado a mano. items = (etiqueta o None, sentencia o None)."""
    return Program(tuple(
        ParsedLine(number, f"<línea {number}>", label, statement)
        for number, (label, statement) in enumerate(items, start=1)
    ))


NOP = Instruction("NOP", ())
ORIG = OrigDirective(0x3000)


def fill(value=1):
    return FillDirective(Immediate(value))


# ----------------------------------------------------------------------
# Corpus de regresión (etapa 5.3.2)
# ----------------------------------------------------------------------
# Todos los programas del corpus tienen origen PAR. La huella se calculó con la
# implementación anterior a la regla ".ORIG debe ser par": que siga valiendo lo
# mismo demuestra que las direcciones de las etiquetas, el relleno y los errores
# de memoria NO cambiaron para orígenes pares.
CORPUS_DIGEST = "bdd8147ab4a23c93d1781443151f523d39bd67ba24c27465563ac7f59b8a3c3b"
CORPUS_SIZE = 37448

# (clase de sentencia, ¿lleva etiqueta?). Instrucciones y datos de longitud par e
# impar (para provocar relleno), etiquetas solas y .EXTERNAL.
CORPUS_KINDS = (
    ("instruction", False), ("instruction", True), ("fill", True), ("blkw", False),
    ("string3", True), ("string0", False), ("label_only", True), ("external", False),
)
CORPUS_ORIGINS = (0x0000, 0x3000, 0xFFF8, 0xFFFE)
CORPUS_MAX_LENGTH = 4


def _corpus_statement(kind, position):
    if kind == "instruction":
        return Instruction("NOP", ())
    if kind == "fill":
        return FillDirective(Immediate(1))
    if kind == "blkw":
        return BlkwDirective(1)
    if kind == "string3":
        return StringzDirective("AB")           # 3 bytes: deja el contador impar
    if kind == "string0":
        return StringzDirective("")             # 1 byte
    if kind == "external":
        return ExternalDirective(f"E{position}")
    return None                                 # label_only


def corpus_programs():
    """Todas las secuencias de hasta CORPUS_MAX_LENGTH sentencias, con y sin .END."""
    for origin in CORPUS_ORIGINS:
        for length in range(CORPUS_MAX_LENGTH + 1):
            for sequence in itertools.product(range(len(CORPUS_KINDS)), repeat=length):
                for with_end in (False, True):
                    items = [(None, OrigDirective(origin))]
                    for position, index in enumerate(sequence):
                        kind, labeled = CORPUS_KINDS[index]
                        label = f"L{position}" if labeled else None
                        items.append((label, _corpus_statement(kind, position)))
                    if with_end:
                        items.append(("FIN", EndDirective()))
                    yield Program(tuple(
                        ParsedLine(n, f"<{n}>", label, statement)
                        for n, (label, statement) in enumerate(items, start=1)))


def corpus_digest(build, error_type):
    """(SHA-256, cantidad) del resultado de `build` sobre todo el corpus."""
    digest = hashlib.sha256()
    count = 0
    for program in corpus_programs():
        count += 1
        try:
            table = build(program)
            result = ("ok", sorted(table.symbols.items()), sorted(table.externals),
                      sorted(table.line_addresses.items()),
                      [(p.address, p.size, p.line_number) for p in table.padding],
                      table.origin, table.end_address, table.size)
        except error_type as error:
            result = ("error", [(e.line_number, e.message) for e in error.errors])
        digest.update(repr(result).encode())
    return digest.hexdigest(), count


class SymbolTestCase(unittest.TestCase):

    def assertErrors(self, subject, expected):
        """`expected`: lista de (línea o None, fragmento del mensaje), en orden."""
        program = subject if isinstance(subject, Program) else parse_program(subject)
        with self.assertRaises(SymbolErrors) as context:
            build_symbol_table(program)
        actual = [(e.line_number, e.message) for e in context.exception.errors]
        self.assertEqual([line for line, _ in actual], [line for line, _ in expected],
                         f"líneas distintas: {actual}")
        for (_, message), (_, fragment) in zip(actual, expected):
            self.assertIn(fragment, message)
        return context.exception


# ----------------------------------------------------------------------
# 1-2, 26. Programas sencillos y direcciones desde .ORIG
# ----------------------------------------------------------------------
class TestSimpleLayout(SymbolTestCase):

    def test_consecutive_instructions(self):
        table = build(".ORIG x3000",            # 1
                      "ADD R1, R2, #5",          # 2
                      "SUB R1, R1, R2",          # 3
                      "HALT",                    # 4
                      ".END")                    # 5
        self.assertEqual(dict(table.line_addresses), {2: 0x3000, 3: 0x3002, 4: 0x3004})
        self.assertEqual(dict(table.symbols), {})
        self.assertEqual(table.externals, frozenset())
        self.assertEqual(table.padding, ())
        self.assertEqual(table.origin, 0x3000)
        self.assertEqual(table.end_address, 0x3006)
        self.assertEqual(table.size, 6)

    def test_addresses_start_at_the_origin(self):
        for origin, first in ((0x0000, 0), (0x0100, 0x100), (0x4000, 0x4000),
                              (0xFF00, 0xFF00)):
            with self.subTest(origin=hex(origin)):
                table = build(f".ORIG x{origin:X}", "NOP", "NOP")
                self.assertEqual(dict(table.line_addresses), {2: first, 3: first + 2})
                self.assertEqual(table.origin, origin)
                self.assertEqual(table.end_address, origin + 4)

    def test_orig_only_program_is_valid_and_empty(self):
        for text in (".ORIG x3000", ".ORIG x3000\n.END", ".ORIG x3000\n; nada\n\n"):
            with self.subTest(text=repr(text)):
                table = build_symbol_table(parse_program(text))
                self.assertEqual((table.origin, table.end_address, table.size),
                                 (0x3000, 0x3000, 0))
                self.assertEqual(dict(table.line_addresses), {})
                self.assertEqual(table.padding, ())

    def test_end_is_optional(self):
        with_end = build(".ORIG x3000", "NOP", "HALT", ".END")
        without_end = build(".ORIG x3000", "NOP", "HALT")
        self.assertEqual(with_end, without_end)

    def test_orig_and_end_do_not_occupy_memory(self):
        table = build(".ORIG x3000", ".END")
        self.assertEqual(table.size, 0)

    def test_only_memory_lines_have_a_line_address(self):
        table = build(".ORIG x3000",              # 1
                      ".EXTERNAL PRINTF",         # 2
                      "A:",                       # 3
                      "NOP",                      # 4
                      "B: .FILL #1",              # 5
                      "C: .BLKW #1",              # 6
                      'D: .STRINGZ "x"',          # 7
                      "E: .END")                  # 8
        self.assertEqual(set(table.line_addresses), {4, 5, 6, 7})


# ----------------------------------------------------------------------
# 3-8. Etiquetas y tamaños
# ----------------------------------------------------------------------
class TestLabelsAndSizes(SymbolTestCase):

    def test_labels_on_instructions(self):
        table = build(".ORIG x3000", "START: NOP", "LOOP: ADD R1, R1, #1", "BR LOOP")
        self.assertEqual(dict(table.symbols), {"START": 0x3000, "LOOP": 0x3002})

    def test_label_on_fill(self):
        table = build(".ORIG x3000", "VAL: .FILL #5", "NEXT: NOP")
        self.assertEqual(dict(table.symbols), {"VAL": 0x3000, "NEXT": 0x3002})
        self.assertEqual(dict(table.line_addresses), {2: 0x3000, 3: 0x3002})

    def test_fill_occupies_two_bytes(self):
        table = build(".ORIG x3000", ".FILL #1", ".FILL #2", ".FILL x3")
        self.assertEqual(table.end_address, 0x3006)

    def test_label_on_blkw(self):
        table = build(".ORIG x3000", "BUF: .BLKW #4", "AFTER: NOP")
        self.assertEqual(dict(table.symbols), {"BUF": 0x3000, "AFTER": 0x3008})

    def test_blkw_reserves_two_bytes_per_position(self):
        for count in (1, 2, 3, 10, 100):
            with self.subTest(count=count):
                table = build(".ORIG x3000", f".BLKW #{count}")
                self.assertEqual(table.size, 2 * count)

    def test_label_on_stringz_points_to_the_first_character(self):
        table = build(".ORIG x3000", 'MSG: .STRINGZ "HOLA"', "NEXT: .FILL #0")
        self.assertEqual(table.symbols["MSG"], 0x3000)
        self.assertEqual(table.symbols["NEXT"], 0x3005)

    def test_stringz_length_includes_the_null_terminator(self):
        cases = ((r'""', 1), (r'"A"', 2), (r'"HOLA"', 5), (r'"a b"', 4),
                 (r'"a;b,c"', 6), (r'"a\nb"', 4), (r'"\t\\"', 3), ('"ñ"', 2),
                 (r'"0123456789"', 11))
        for literal, size in cases:
            with self.subTest(literal=literal):
                table = build(".ORIG x3000", f".STRINGZ {literal}", "END: .END")
                self.assertEqual(table.size, size)
                self.assertEqual(table.symbols["END"], 0x3000 + size)

    def test_label_alone_on_its_line_binds_to_the_next_statement(self):
        table = build(".ORIG x3000",          # 1
                      "FIRST:",                # 2
                      "NOP",                   # 3
                      "SECOND:",               # 4
                      "",                      # 5
                      "; comentario",          # 6
                      "NOP")                   # 7
        self.assertEqual(dict(table.symbols), {"FIRST": 0x3000, "SECOND": 0x3002})
        self.assertEqual(dict(table.line_addresses), {3: 0x3000, 7: 0x3002})

    def test_consecutive_labels_share_one_address(self):
        table = build(".ORIG x3000", "A:", "B:", "C: NOP")
        self.assertEqual(dict(table.symbols), {"A": 0x3000, "B": 0x3000, "C": 0x3000})

    def test_pending_label_binds_to_data_without_alignment(self):
        table = build(".ORIG x3000", '.STRINGZ "AB"', "L:", ".FILL #1")
        self.assertEqual(table.symbols["L"], 0x3003)
        self.assertEqual(table.padding, ())

    def test_pending_label_skips_directives_that_use_no_memory(self):
        table = build(".ORIG x3000", "A:", ".EXTERNAL X", "NOP")
        self.assertEqual(table.symbols["A"], 0x3000)

    def test_a_label_before_orig_binds_to_the_first_statement_after_it(self):
        table = build("START:", ".ORIG x3000", "NOP")
        self.assertEqual(table.symbols["START"], 0x3000)

    def test_labels_are_case_sensitive(self):
        table = build(".ORIG x3000", "a: NOP", "A: NOP")
        self.assertEqual(dict(table.symbols), {"a": 0x3000, "A": 0x3002})


# ----------------------------------------------------------------------
# 9-12. Alineación y relleno
# ----------------------------------------------------------------------
class TestAlignment(SymbolTestCase):

    def test_padding_before_an_instruction_at_an_odd_address(self):
        table = build(".ORIG x3000",            # 1
                      '.STRINGZ "AB"',           # 2: x3000..x3002
                      "NOP")                     # 3: relleno en x3003, NOP en x3004
        self.assertEqual(table.padding, (Padding(0x3003, 1, 3),))
        self.assertEqual(dict(table.line_addresses), {2: 0x3000, 3: 0x3004})
        self.assertEqual(table.end_address, 0x3006)
        self.assertEqual(table.size, 6)

    def test_label_on_the_same_line_points_to_the_aligned_address(self):
        table = build(".ORIG x3000", '.STRINGZ "AB"', "START: NOP")
        self.assertEqual(table.symbols["START"], 0x3004)        # no x3003

    def test_pending_label_points_to_the_aligned_address(self):
        table = build(".ORIG x3000",            # 1
                      '.STRINGZ "AB"',           # 2
                      "LABEL:",                  # 3
                      "NOP")                     # 4
        self.assertEqual(table.symbols["LABEL"], 0x3004)
        self.assertEqual(table.padding, (Padding(0x3003, 1, 4),))

    def test_pending_and_same_line_labels_share_the_aligned_address(self):
        table = build(".ORIG x3000", '.STRINGZ "AB"', "A:", "B:", "C: NOP")
        self.assertEqual([table.symbols[n] for n in "ABC"], [0x3004] * 3)

    def test_no_padding_when_the_instruction_is_already_aligned(self):
        table = build(".ORIG x3000", '.STRINGZ "ABC"', "NOP")    # 4 bytes: par
        self.assertEqual(table.padding, ())
        self.assertEqual(dict(table.line_addresses), {2: 0x3000, 3: 0x3004})
        self.assertEqual(table.size, 6)

    def test_consecutive_instructions_never_need_padding(self):
        table = build(".ORIG x3000", *["NOP"] * 10)
        self.assertEqual(table.padding, ())

    def test_every_misaligned_instruction_gets_its_own_padding(self):
        table = build(".ORIG x3000",            # 1
                      '.STRINGZ "AB"',           # 2: counter x3003
                      "NOP",                     # 3: relleno x3003, NOP x3004 -> x3006
                      '.STRINGZ "AB"',           # 4: x3006..x3008 -> x3009
                      "NOP")                     # 5: relleno x3009, NOP x300A -> x300C
        self.assertEqual(table.padding, (Padding(0x3003, 1, 3), Padding(0x3009, 1, 5)))
        self.assertEqual(dict(table.line_addresses),
                         {2: 0x3000, 3: 0x3004, 4: 0x3006, 5: 0x300A})
        self.assertEqual((table.end_address, table.size), (0x300C, 12))

    def test_data_may_start_at_odd_addresses_without_padding(self):
        table = build(".ORIG x3000",            # 1
                      '.STRINGZ "AB"',           # 2: x3000..x3002
                      "W1: .FILL #1",            # 3: x3003 (impar)
                      "W2: .FILL #2",            # 4: x3005 (impar)
                      "B: .BLKW #1",             # 5: x3007 (impar)
                      '.STRINGZ "A"')            # 6: x3009
        self.assertEqual([table.symbols[n] for n in ("W1", "W2", "B")],
                         [0x3003, 0x3005, 0x3007])
        self.assertEqual(table.padding, ())
        self.assertEqual(table.end_address, 0x300B)

    def test_no_padding_is_added_after_data_directives(self):
        table = build(".ORIG x3000", '.STRINGZ "AB"', ".FILL #1", '.STRINGZ "C"')
        self.assertEqual(table.padding, ())
        self.assertEqual(table.size, 3 + 2 + 2)

    def test_size_includes_the_padding(self):
        table = build(".ORIG x3000", '.STRINGZ "AB"', "NOP")
        self.assertEqual(table.size, 3 + 1 + 2)
        self.assertEqual(table.size, table.end_address - table.origin)

    def test_padding_records_address_size_and_line(self):
        (pad,) = build(".ORIG x3000", '.STRINGZ "AB"', "NOP").padding
        self.assertEqual((pad.address, pad.size, pad.line_number), (0x3003, 1, 3))


# ----------------------------------------------------------------------
# 13. .END con etiquetas
# ----------------------------------------------------------------------
class TestEndDirective(SymbolTestCase):

    def test_label_on_the_end_line(self):
        table = build(".ORIG x3000", "NOP", "FIN: .END")
        self.assertEqual(table.symbols["FIN"], 0x3002)
        self.assertEqual(table.end_address, 0x3002)

    def test_pending_label_resolves_at_end(self):
        table = build(".ORIG x3000", "NOP", "FIN:", ".END")
        self.assertEqual(table.symbols["FIN"], 0x3002)

    def test_pending_label_at_the_end_of_a_program_without_end(self):
        table = build(".ORIG x3000", "NOP", "FIN:")
        self.assertEqual(table.symbols["FIN"], 0x3002)

    def test_end_label_is_not_aligned_like_an_instruction(self):
        table = build(".ORIG x3000", '.STRINGZ "AB"', "FIN: .END")
        self.assertEqual(table.symbols["FIN"], 0x3003)
        self.assertEqual(table.end_address, 0x3003)
        self.assertEqual(table.padding, ())

    def test_pending_and_end_labels_share_the_counter(self):
        table = build(".ORIG x3000", "NOP", "A:", "B: .END")
        self.assertEqual((table.symbols["A"], table.symbols["B"]), (0x3002, 0x3002))

    def test_end_line_has_no_line_address(self):
        table = build(".ORIG x3000", "NOP", "FIN: .END")
        self.assertEqual(set(table.line_addresses), {2})


# ----------------------------------------------------------------------
# 14-18. Símbolos externos y referencias
# ----------------------------------------------------------------------
class TestExternalsAndReferences(SymbolTestCase):

    def test_externals_are_collected_separately(self):
        table = build(".ORIG x3000", ".EXTERNAL PRINTF", ".EXTERNAL scanf", "NOP")
        self.assertEqual(table.externals, frozenset({"PRINTF", "scanf"}))
        self.assertEqual(dict(table.symbols), {})
        self.assertEqual(table.size, 2)

    def test_external_may_be_declared_before_orig(self):
        table = build(".EXTERNAL X", ".ORIG x3000", "JSR X")
        self.assertEqual(table.externals, frozenset({"X"}))

    def test_repeating_an_external_declaration_is_harmless(self):
        table = build(".ORIG x3000", ".EXTERNAL X", ".EXTERNAL X", "JSR X")
        self.assertEqual(table.externals, frozenset({"X"}))

    def test_external_names_are_case_sensitive(self):
        table = build(".ORIG x3000", "a: NOP", ".EXTERNAL A", "JSR A", "BR a")
        self.assertEqual(table.externals, frozenset({"A"}))
        self.assertEqual(table.symbols["a"], 0x3000)

    def test_local_label_then_external_with_the_same_name(self):
        self.assertErrors(source(".ORIG x3000",        # 1
                                 "PRINTF: NOP",         # 2
                                 ".EXTERNAL PRINTF"),   # 3
                          [(3, "entra en conflicto con la etiqueta definida en la línea 2")])

    def test_external_then_local_label_with_the_same_name(self):
        self.assertErrors(source(".ORIG x3000",        # 1
                                 ".EXTERNAL PRINTF",    # 2
                                 "PRINTF: NOP"),        # 3
                          [(3, "entra en conflicto con el símbolo externo declarado en la línea 2")])

    def test_label_alone_conflicting_with_an_external(self):
        self.assertErrors(source(".ORIG x3000", ".EXTERNAL X", "X:", "NOP"),
                          [(3, "conflicto")])

    def test_valid_local_references_forward_and_backward(self):
        table = build(".ORIG x3000",            # 1
                      "BR LATER",                # 2: referencia hacia adelante
                      "BACK: NOP",               # 3
                      "LEA R0, MSG",             # 4
                      "BR BACK",                 # 5: referencia hacia atrás
                      "LATER: HALT",             # 6
                      'MSG: .STRINGZ "x"',       # 7
                      "PTR: .FILL LATER")        # 8
        self.assertEqual(set(table.symbols), {"BACK", "LATER", "MSG", "PTR"})

    def test_valid_external_references(self):
        table = build(".ORIG x3000", ".EXTERNAL PRINTF", ".EXTERNAL DATA",
                      "JSR PRINTF", "LEA R0, DATA", "PTR: .FILL PRINTF")
        self.assertEqual(table.externals, frozenset({"PRINTF", "DATA"}))

    def test_numeric_operands_are_not_references(self):
        table = build(".ORIG x3000", "BR #3", "LEA R0, #-4", ".FILL #5")
        self.assertEqual(dict(table.symbols), {})

    def test_undefined_reference_in_an_instruction(self):
        error = self.assertErrors(source(".ORIG x3000", "BR NOWHERE"),
                                  [(2, "símbolo no definido")])
        self.assertIn("'NOWHERE'", error.errors[0].message)
        self.assertIn(".EXTERNAL", error.errors[0].message)

    def test_undefined_reference_in_fill(self):
        self.assertErrors(source(".ORIG x3000", ".FILL MISSING"),
                          [(2, "'MISSING'")])

    def test_undefined_reference_in_lea_and_jsr(self):
        self.assertErrors(source(".ORIG x3000", "LEA R0, MSG", "JSR SUBRUT"),
                          [(2, "'MSG'"), (3, "'SUBRUT'")])

    def test_references_are_case_sensitive(self):
        self.assertErrors(source(".ORIG x3000", "Loop: NOP", "BR LOOP"),
                          [(3, "'LOOP'")])

    def test_every_undefined_reference_is_reported(self):
        self.assertErrors(source(".ORIG x3000", "BR A", "BR B", "BR A"),
                          [(2, "'A'"), (3, "'B'"), (4, "'A'")])

    def test_references_are_found_anywhere_in_the_statement(self):
        # recorrido genérico: tupla de operandos y campo `value` de .FILL
        program = prog((None, ORIG),
                       (None, Instruction("LEA", (Immediate(0), LabelRef("IN_TUPLE")))),
                       (None, FillDirective(LabelRef("IN_FIELD"))))
        self.assertErrors(program, [(2, "'IN_TUPLE'"), (3, "'IN_FIELD'")])


# ----------------------------------------------------------------------
# 19-21, 26. Reglas de .ORIG
# ----------------------------------------------------------------------
class TestOrigRules(SymbolTestCase):

    def test_missing_orig(self):
        error = self.assertErrors(source("NOP", "HALT"), [(None, "falta la directiva .ORIG")])
        self.assertTrue(str(error.errors[0]).startswith("falta"))      # sin "línea N"

    def test_missing_orig_in_an_empty_program(self):
        self.assertErrors(parse_program(""), [(None, "falta la directiva .ORIG")])
        self.assertErrors(parse_program("; solo un comentario\n\n"),
                          [(None, "falta la directiva .ORIG")])

    def test_missing_orig_with_only_non_memory_statements(self):
        self.assertErrors(source(".EXTERNAL X", ".END"), [(None, "falta la directiva .ORIG")])

    def test_missing_orig_is_reported_once_not_per_statement(self):
        error = self.assertErrors(source("NOP", "NOP", "NOP"),
                                  [(None, "falta la directiva .ORIG")])
        self.assertEqual(len(error.errors), 1)

    def test_orig_after_a_statement_that_occupies_memory(self):
        cases = {
            "instrucción": ["NOP", ".ORIG x3000"],
            "con etiqueta": ["L: NOP", ".ORIG x3000"],
            ".FILL": [".FILL #1", ".ORIG x3000"],
            ".BLKW": [".BLKW #2", ".ORIG x3000"],
            ".STRINGZ": ['.STRINGZ "x"', ".ORIG x3000"],
        }
        for name, lines in cases.items():
            with self.subTest(case=name):
                error = self.assertErrors(source(*lines),
                                          [(2, ".ORIG debe aparecer antes")])
                self.assertIn("línea 1", error.errors[0].message)

    def test_orig_after_memory_statement_does_not_also_report_a_missing_orig(self):
        error = self.assertErrors(source("NOP", ".ORIG x3000", "NOP"),
                                  [(2, ".ORIG debe aparecer antes")])
        self.assertEqual(len(error.errors), 1)

    def test_orig_after_statements_that_do_not_occupy_memory_is_fine(self):
        for lines in ([".EXTERNAL X", ".ORIG x3000"],
                      ["A:", ".ORIG x3000"],
                      ["; comentario", ".ORIG x3000"]):
            with self.subTest(lines=lines):
                table = build(*lines, "NOP")
                self.assertEqual(table.origin, 0x3000)

    def test_more_than_one_orig(self):
        program = prog((None, ORIG), (None, NOP), (None, OrigDirective(0x4000)))
        error = self.assertErrors(program, [(3, "solo se admite un .ORIG")])
        self.assertIn("línea 1", error.errors[0].message)

    def test_orig_with_a_label_is_rejected(self):
        self.assertErrors(prog(("START", ORIG), (None, NOP)),
                          [(1, ".ORIG no admite etiqueta")])

    def test_orig_out_of_range_is_rejected(self):
        for address in (-1, 0x10000, 0x20000, True, "x3000", None):
            with self.subTest(address=address):
                self.assertErrors(prog((None, OrigDirective(address))),
                                  [(1, ".ORIG fuera de rango")])

    def test_orig_at_the_edges_of_the_range(self):
        self.assertEqual(build_symbol_table(prog((None, OrigDirective(0)))).origin, 0)
        table = build_symbol_table(prog((None, OrigDirective(0xFFFE))))      # (5.3.2) borde PAR
        self.assertEqual((table.origin, table.end_address, table.size), (0xFFFE, 0xFFFE, 0))

    def test_statements_after_end_are_rejected(self):
        program = prog((None, ORIG), (None, NOP), (None, EndDirective()),
                       (None, NOP), ("L", None))
        self.assertErrors(program, [(4, "después de .END"), (5, "después de .END")])


# ----------------------------------------------------------------------
# 22-24. Límites de memoria
# ----------------------------------------------------------------------
class TestMemoryLimits(SymbolTestCase):

    def test_last_two_bytes_can_hold_an_instruction(self):
        table = build(".ORIG xFFFE", "NOP")
        self.assertEqual(dict(table.line_addresses), {2: 0xFFFE})
        self.assertEqual((table.end_address, table.size), (0x10000, 2))

    def test_the_last_byte_can_be_used(self):
        table = build(".ORIG xFFFE",                              # 1   (5.3.2: origen par)
                      '.STRINGZ ""',                               # 2   1 byte en xFFFE
                      '.STRINGZ ""')                               # 3   1 byte en xFFFF: el último
        self.assertEqual(dict(table.line_addresses), {2: 0xFFFE, 3: 0xFFFF})
        self.assertEqual((table.end_address, table.size), (0x10000, 2))

    def test_the_whole_memory_can_be_filled(self):
        table = build(".ORIG x0000", ".BLKW #32768")
        self.assertEqual((table.origin, table.end_address, table.size), (0, 0x10000, 65536))

    def test_blkw_one_word_too_many(self):
        self.assertErrors(source(".ORIG x0000", ".BLKW #32769"),
                          [(2, "desbordamiento de memoria")])

    def test_stringz_that_fills_memory_exactly(self):
        text = "A" * 65535
        table = build(".ORIG x0000", f'.STRINGZ "{text}"')
        self.assertEqual((table.end_address, table.size), (0x10000, 65536))

    def test_stringz_one_byte_too_long(self):
        text = "A" * 65536
        self.assertErrors(source(".ORIG x0000", f'.STRINGZ "{text}"'),
                          [(2, "desbordamiento de memoria")])

    def test_exclusive_end_address_x10000_is_allowed(self):
        table = build(".ORIG xFFFC", "NOP", "NOP")
        self.assertEqual(table.end_address, 0x10000)

    def test_a_label_may_point_to_the_exclusive_end(self):
        table = build(".ORIG xFFFE", "NOP", "END_L:", ".END")
        self.assertEqual(table.symbols["END_L"], 0x10000)

    def test_instruction_past_the_end(self):
        self.assertErrors(source(".ORIG xFFFE", "NOP", "NOP"),
                          [(3, "desbordamiento de memoria")])

    def test_fill_does_not_fit_in_the_last_byte(self):
        self.assertErrors(source(".ORIG xFFFE", '.STRINGZ ""', ".FILL #1"),   # (5.3.2)
                          [(3, "desbordamiento de memoria")])

    def test_instruction_at_the_last_byte_overflows_because_of_its_padding(self):
        error = self.assertErrors(source(".ORIG xFFFE", '.STRINGZ ""', "NOP"),   # (5.3.2)
                                  [(3, "desbordamiento de memoria")])
        self.assertIn("necesita 3 byte(s)", error.errors[0].message)
        self.assertIn("relleno", error.errors[0].message)

    def test_only_the_first_overflow_is_reported(self):
        error = self.assertErrors(source(".ORIG xFFFE", "NOP", "NOP", "NOP", "NOP"),
                                  [(3, "desbordamiento")])
        self.assertEqual(len(error.errors), 1)

    def test_overflow_does_not_cause_false_undefined_references(self):
        # LATER se define DESPUÉS del desbordamiento: no debe figurar como no definido.
        self.assertErrors(source(".ORIG xFFFE", "NOP", "BR LATER", "LATER: NOP"),   # (5.3.2)
                          [(3, "desbordamiento")])

    def test_overflow_and_other_errors_are_accumulated(self):
        self.assertErrors(source(".ORIG xFFFE", "NOP", "NOP", "BR NOWHERE"),   # (5.3.2)
                          [(3, "desbordamiento"), (4, "'NOWHERE'")])

    def test_no_table_is_returned_after_an_overflow(self):
        with self.assertRaises(SymbolErrors):
            build(".ORIG xFFFE", "NOP", "NOP")

    def test_message_mentions_the_address_and_the_size_needed(self):
        error = self.assertErrors(source(".ORIG xFFFE", "NOP", "NOP"),
                                  [(3, "desde x10000")])
        self.assertIn("necesita 2 byte(s)", error.errors[0].message)


# ----------------------------------------------------------------------
# Comprobaciones defensivas (Programas que el parser nunca produciría)
# ----------------------------------------------------------------------
class TestDefensiveChecks(SymbolTestCase):

    def test_duplicate_labels(self):
        error = self.assertErrors(prog((None, ORIG), ("A", NOP), ("A", NOP)),
                                  [(3, "duplicada")])
        self.assertIn("línea 2", error.errors[0].message)

    def test_every_repeated_definition_is_reported(self):
        self.assertErrors(prog((None, ORIG), ("A", NOP), ("A", NOP), ("A", NOP)),
                          [(3, "duplicada"), (4, "duplicada")])

    def test_duplicate_label_between_label_only_and_statement_lines(self):
        self.assertErrors(prog((None, ORIG), ("A", None), ("A", NOP)),
                          [(3, "duplicada")])

    def test_external_with_a_label_is_rejected(self):
        self.assertErrors(prog((None, ORIG), ("L", ExternalDirective("X"))),
                          [(2, ".EXTERNAL no admite etiqueta")])

    def test_invalid_blkw_counts(self):
        for count in (0, -1, True, 2.5, "3", None):
            with self.subTest(count=count):
                self.assertErrors(prog((None, ORIG), (None, BlkwDirective(count))),
                                  [(2, ".BLKW requiere")])

    def test_unknown_statement_type(self):
        self.assertErrors(prog((None, ORIG), (None, object())),
                          [(2, "sentencia no reconocida")])

    def test_program_must_be_a_Program(self):
        for bad in (None, "NOP", [], parse_program(".ORIG x0").lines):
            with self.subTest(value=bad):
                with self.assertRaises(TypeError):
                    build_symbol_table(bad)


# ----------------------------------------------------------------------
# Errores: formato y acumulación
# ----------------------------------------------------------------------
class TestErrorReporting(SymbolTestCase):

    def test_error_carries_line_number_and_source(self):
        with self.assertRaises(SymbolErrors) as context:
            build(".ORIG x3000", "BR NOWHERE   ; salto roto")
        (error,) = context.exception.errors
        self.assertIsInstance(error, SymbolError)
        self.assertEqual((error.line_number, error.source), (2, "BR NOWHERE   ; salto roto"))
        self.assertTrue(str(error).startswith("línea 2: "))

    def test_global_errors_come_first_then_by_line(self):
        error = self.assertErrors(source("BR X", "BR Y"),
                                  [(None, "falta la directiva .ORIG"), (1, "'X'"), (2, "'Y'")])
        text = str(error)
        self.assertIn("3 error(es)", text)
        self.assertLess(text.index("falta"), text.index("línea 1"))

    def test_errors_from_every_pass_are_accumulated(self):
        program = prog((None, ORIG),                          # 1
                       ("A", NOP),                            # 2
                       ("A", NOP),                            # 3 duplicada
                       (None, ExternalDirective("B")),        # 4
                       ("B", NOP),                            # 5 conflicto
                       (None, Instruction("BR", (LabelRef("NOWHERE"),), 7)),  # 6 no definido
                       (None, BlkwDirective(40000)))          # 7 desbordamiento
        self.assertErrors(program, [(3, "duplicada"), (5, "conflicto"),
                                    (6, "'NOWHERE'"), (7, "desbordamiento")])

    def test_symbol_errors_has_the_same_shape_as_parse_errors(self):
        from assembler.parser import ParseError, ParseErrors
        self.assertEqual(list(SymbolError("m", 3, "src").__dict__),
                         list(ParseError("m", 3, "src").__dict__))
        with self.assertRaises(SymbolErrors) as context:
            build("NOP")
        self.assertIsInstance(context.exception.errors, tuple)
        self.assertTrue(hasattr(ParseErrors([]), "errors"))

    def test_a_program_with_errors_never_yields_a_table(self):
        for lines in (["NOP"], [".ORIG x3000", "BR X"], [".ORIG xFFFE", "NOP", "NOP"],
                      [".ORIG x3001", "NOP"], ["NOP", ".ORIG x3000"]):       # (5.3.2)
            with self.subTest(lines=lines):
                with self.assertRaises(SymbolErrors):
                    build(*lines)


# ----------------------------------------------------------------------
# 25. Inmutabilidad
# ----------------------------------------------------------------------
class TestImmutability(SymbolTestCase):

    def setUp(self):
        self.table = build(".ORIG x3000", ".EXTERNAL X", '.STRINGZ "AB"',
                           "START: JSR X", "BR START")

    def test_the_table_is_a_frozen_dataclass(self):
        self.assertTrue(dataclasses.is_dataclass(SymbolTable))
        for field in ("origin", "end_address", "symbols", "externals",
                      "line_addresses", "padding"):
            with self.subTest(field=field):
                with self.assertRaises(dataclasses.FrozenInstanceError):
                    setattr(self.table, field, None)

    def test_size_is_derived_and_cannot_be_assigned(self):
        self.assertEqual(self.table.size, self.table.end_address - self.table.origin)
        with self.assertRaises(AttributeError):
            self.table.size = 0

    def test_symbols_mapping_is_read_only(self):
        with self.assertRaises(TypeError):
            self.table.symbols["NEW"] = 1
        with self.assertRaises(TypeError):
            del self.table.symbols["START"]
        self.assertFalse(hasattr(self.table.symbols, "update"))
        self.assertEqual(self.table.symbols["START"], 0x3004)

    def test_line_addresses_mapping_is_read_only(self):
        with self.assertRaises(TypeError):
            self.table.line_addresses[99] = 0
        with self.assertRaises(TypeError):
            del self.table.line_addresses[3]

    def test_externals_is_a_frozenset(self):
        self.assertIsInstance(self.table.externals, frozenset)
        self.assertFalse(hasattr(self.table.externals, "add"))

    def test_padding_is_a_tuple_of_frozen_records(self):
        self.assertIsInstance(self.table.padding, tuple)
        (pad,) = self.table.padding
        with self.assertRaises(dataclasses.FrozenInstanceError):
            pad.size = 5

    def test_the_constructor_copies_and_freezes_its_arguments(self):
        symbols, externals = {"A": 1}, {"X"}
        line_addresses, padding = {1: 0}, [Padding(1, 1, 2)]
        table = SymbolTable(symbols, externals, line_addresses, padding, 0, 4)
        symbols["B"], line_addresses[2] = 2, 2
        externals.add("Y")
        padding.append(Padding(9, 1, 9))
        self.assertEqual(dict(table.symbols), {"A": 1})
        self.assertEqual(table.externals, frozenset({"X"}))
        self.assertEqual(dict(table.line_addresses), {1: 0})
        self.assertEqual(table.padding, (Padding(1, 1, 2),))
        with self.assertRaises(TypeError):
            table.symbols["C"] = 3

    def test_tables_compare_and_hash_by_content(self):
        again = build(".ORIG x3000", ".EXTERNAL X", '.STRINGZ "AB"', "START: JSR X", "BR START")
        other = build(".ORIG x3000", "START: NOP")
        self.assertEqual(self.table, again)
        self.assertEqual(hash(self.table), hash(again))
        self.assertNotEqual(self.table, other)
        self.assertEqual(len({self.table, again, other}), 2)

    def test_the_input_program_is_not_modified(self):
        text = source(".ORIG x3000", '.STRINGZ "AB"', "L: NOP", "BR L")
        program, reference = parse_program(text), parse_program(text)
        build_symbol_table(program)
        self.assertEqual(program, reference)

    def test_building_twice_gives_the_same_result(self):
        program = parse_program(source(".ORIG x3000", '.STRINGZ "AB"', "NOP"))
        self.assertEqual(build_symbol_table(program), build_symbol_table(program))


# ----------------------------------------------------------------------
# Integración con el parser real
# ----------------------------------------------------------------------
class TestIntegration(SymbolTestCase):

    def test_complete_program(self):
        table = build(
            "; programa completo",            # 1
            "        .ORIG x3000",             # 2
            "        .EXTERNAL PRINTF",        # 3
            "START:  LEA R0, MSG",             # 4   x3000
            "        JSR PRINTF",              # 5   x3002
            "        LDW R1, R2, #0",          # 6   x3004
            "LOOP:   ADD R1, R1, #-1",         # 7   x3006
            "        BRp LOOP",                # 8   x3008
            "        HALT",                    # 9   x300A
            'MSG:    .STRINGZ "Hola"',         # 10  x300C..x3010 (5 bytes)
            "COUNT:  .FILL #3",                # 11  x3011 (impar)
            "TABLE:  .FILL MSG",               # 12  x3013
            "BUF:    .BLKW #2",                # 13  x3015..x3018 (4 bytes)
            "LAST:   NOP",                     # 14  relleno x3019, NOP x301A
            "        .END")                    # 15
        self.assertEqual(dict(table.symbols), {
            "START": 0x3000, "LOOP": 0x3006, "MSG": 0x300C, "COUNT": 0x3011,
            "TABLE": 0x3013, "BUF": 0x3015, "LAST": 0x301A,
        })
        self.assertEqual(table.externals, frozenset({"PRINTF"}))
        self.assertEqual(dict(table.line_addresses), {
            4: 0x3000, 5: 0x3002, 6: 0x3004, 7: 0x3006, 8: 0x3008, 9: 0x300A,
            10: 0x300C, 11: 0x3011, 12: 0x3013, 13: 0x3015, 14: 0x301A,
        })
        self.assertEqual(table.padding, (Padding(0x3019, 1, 14),))
        self.assertEqual((table.origin, table.end_address, table.size), (0x3000, 0x301C, 28))

    def test_errors_from_a_real_parse_are_accumulated(self):
        self.assertErrors(source("NOP",               # 1
                                 ".ORIG x3000",        # 2  mal ubicado
                                 "BR NOWHERE",         # 3  no definido
                                 ".EXTERNAL X",        # 4
                                 "X: NOP"),            # 5  conflicto
                          [(2, ".ORIG debe aparecer antes"), (3, "'NOWHERE'"), (5, "conflicto")])

    def test_symbols_never_depend_on_the_parser_being_called(self):
        # El mismo resultado con un Program armado a mano que con uno parseado.
        parsed = build_symbol_table(parse_program(source(".ORIG x3000", "A: NOP", "B: .FILL #1")))
        manual = build_symbol_table(prog((None, ORIG), ("A", NOP), ("B", fill(1))))
        self.assertEqual(dict(parsed.symbols), dict(manual.symbols))
        self.assertEqual(parsed.end_address, manual.end_address)


# ----------------------------------------------------------------------
# Etapa 5.3.2: .ORIG debe ser par
# ----------------------------------------------------------------------
class TestOrigParity(SymbolTestCase):

    def test_even_origins_are_valid(self):
        for origin in (0x0000, 0x0002, 0x1234, 0x3000, 0xFFFC, 0xFFFE):
            with self.subTest(origin=hex(origin)):
                table = build(f".ORIG x{origin:04X}")
                self.assertEqual((table.origin, table.end_address, table.size),
                                 (origin, origin, 0))

    def test_x3000_with_code_is_valid(self):
        table = build(".ORIG x3000", "NOP", "HALT")
        self.assertEqual((table.origin, table.end_address), (0x3000, 0x3004))

    def test_x0000_with_code_is_valid(self):
        table = build(".ORIG x0000", "START: NOP")
        self.assertEqual(table.symbols["START"], 0)

    def test_odd_origins_are_rejected(self):
        for origin in (0x0001, 0x3001, 0x3003, 0x7FFF, 0xFFFD, 0xFFFF):
            with self.subTest(origin=hex(origin)):
                error = self.assertErrors(source(f".ORIG x{origin:04X}", "NOP"),
                                          [(1, "dirección par")])
                self.assertIn("es impar", error.errors[0].message)
                self.assertIn(f"x{origin:04X}", error.errors[0].message)

    def test_x3001_and_xFFFF_are_rejected(self):
        self.assertErrors(source(".ORIG x3001"), [(1, "dirección par")])
        self.assertErrors(source(".ORIG xFFFF"), [(1, "dirección par")])

    def test_the_error_identifies_the_line_of_orig(self):
        error = self.assertErrors(source("; comentario",         # 1
                                         ".EXTERNAL X",           # 2
                                         "",                      # 3
                                         ".ORIG x3001",           # 4
                                         "NOP"),                  # 5
                                  [(4, "dirección par")])
        (found,) = error.errors
        self.assertEqual(found.line_number, 4)
        self.assertEqual(found.source, ".ORIG x3001")
        self.assertTrue(str(found).startswith("línea 4: "))

    def test_the_message_explains_the_rule_and_suggests_an_address(self):
        (found,) = self.assertErrors(source(".ORIG x3001"), [(1, "dirección par")]).errors
        for fragment in ("debe recibir una dirección par", "x3001", "es impar",
                         "2 bytes", "PC", "use x3000"):
            self.assertIn(fragment, found.message)

    def test_odd_origin_is_rejected_even_if_only_data_follows(self):
        # La regla es sobre el ORIGEN del programa, no sobre el tipo de contenido.
        self.assertErrors(source(".ORIG x3001", "D: .FILL #1"), [(1, "dirección par")])
        self.assertErrors(source(".ORIG x3001", ".BLKW #2"), [(1, "dirección par")])
        self.assertErrors(source(".ORIG x3001", '.STRINGZ "x"'), [(1, "dirección par")])

    def test_odd_origin_never_produces_silent_padding(self):
        # Antes se insertaba un relleno al comienzo; ahora es un error y no hay tabla.
        error = self.assertErrors(source(".ORIG x3001", "L: NOP"), [(1, "dirección par")])
        self.assertEqual(len(error.errors), 1)
        with self.assertRaises(SymbolErrors):
            build(".ORIG x3001", "L: NOP")

    def test_an_odd_origin_does_not_cascade_into_more_errors(self):
        error = self.assertErrors(
            source(".ORIG x3001", "START: NOP", "BR START", ".FILL #1",
                   '.STRINGZ "A"', ".EXTERNAL X", "JSR X"),
            [(1, "dirección par")])
        self.assertEqual(len(error.errors), 1)

    def test_an_odd_origin_does_not_hide_other_errors(self):
        self.assertErrors(source(".ORIG x3001", "BR NOWHERE"),
                          [(1, "dirección par"), (2, "'NOWHERE'")])
        self.assertErrors(prog((None, OrigDirective(0x3001)), ("A", NOP), ("A", NOP)),
                          [(1, "dirección par"), (3, "duplicada")])

    def test_a_hand_built_odd_origin_is_rejected(self):
        self.assertErrors(prog((None, OrigDirective(0x3001)), (None, NOP)),
                          [(1, "dirección par")])

    def test_range_is_checked_before_parity(self):
        for address in (-1, -3, 0x10001, 0x10000):
            with self.subTest(address=address):
                self.assertErrors(prog((None, OrigDirective(address))),
                                  [(1, ".ORIG fuera de rango")])

    def test_a_misplaced_odd_orig_reports_only_the_misplacement(self):
        self.assertErrors(source("NOP", ".ORIG x3001"),
                          [(2, ".ORIG debe aparecer antes")])

    def test_a_second_odd_orig_reports_only_the_duplicate(self):
        program = prog((None, ORIG), (None, NOP), (None, OrigDirective(0x3001)))
        self.assertErrors(program, [(3, "solo se admite un .ORIG")])

    def test_an_orig_with_a_label_and_an_odd_address_reports_both(self):
        self.assertErrors(prog(("S", OrigDirective(0x3001))),
                          [(1, ".ORIG no admite etiqueta"), (1, "dirección par")])

    def test_the_parity_rule_belongs_to_this_stage_not_to_the_parser(self):
        program = parse_program(".ORIG x3001\nNOP")          # el parser sigue aceptándolo
        self.assertEqual(program.lines[0].statement, OrigDirective(0x3001))
        with self.assertRaises(SymbolErrors):
            build_symbol_table(program)

    def test_data_can_still_start_at_odd_addresses_after_an_even_origin(self):
        table = build(".ORIG x3000", '.STRINGZ "AB"', "W: .FILL #1")
        self.assertEqual(table.symbols["W"], 0x3003)
        self.assertEqual(table.padding, ())

    def test_fill_blkw_and_stringz_keep_their_sizes_and_addresses(self):
        table = build(".ORIG x3000",            # 1
                      "F: .FILL #1",             # 2: x3000..x3001
                      "B: .BLKW #3",             # 3: x3002..x3007 (3 palabras)
                      'S: .STRINGZ "AB"',        # 4: x3008..x300A (3 bytes)
                      "E: .FILL #2")             # 5: x300B..x300C (impar: sin relleno)
        self.assertEqual(dict(table.symbols),
                         {"F": 0x3000, "B": 0x3002, "S": 0x3008, "E": 0x300B})
        self.assertEqual(dict(table.line_addresses),
                         {2: 0x3000, 3: 0x3002, 4: 0x3008, 5: 0x300B})
        self.assertEqual((table.padding, table.end_address, table.size),
                         ((), 0x300D, 13))


# ----------------------------------------------------------------------
# Etapa 5.3.2: política de .EXTERNAL
# ----------------------------------------------------------------------
class TestExternalPolicy(SymbolTestCase):

    def test_a_declaration_without_references(self):
        table = build(".ORIG x3000", ".EXTERNAL RUTINA_EXTERNA", "NOP")
        self.assertEqual(table.externals, frozenset({"RUTINA_EXTERNA"}))
        self.assertEqual(dict(table.symbols), {})
        self.assertEqual(table.size, 2)

    def test_a_reference_to_a_declared_external(self):
        table = build(".ORIG x3000",                  # 1
                      ".EXTERNAL RUTINA_EXTERNA",       # 2
                      ".EXTERNAL DATOS_EXTERNOS",       # 3
                      "JSR RUTINA_EXTERNA",             # 4
                      "LEA R0, DATOS_EXTERNOS",         # 5
                      "PTR: .FILL DATOS_EXTERNOS")      # 6
        self.assertEqual(table.externals,
                         frozenset({"RUTINA_EXTERNA", "DATOS_EXTERNOS"}))
        self.assertEqual(table.symbols["PTR"], 0x3004)

    def test_an_external_declared_more_than_once_and_referenced(self):
        table = build(".ORIG x3000", ".EXTERNAL X", "JSR X", ".EXTERNAL X",
                      "BR X", ".EXTERNAL X")
        self.assertEqual(table.externals, frozenset({"X"}))
        self.assertEqual(table.size, 4)

    def test_an_undeclared_symbol_still_fails(self):
        self.assertErrors(source(".ORIG x3000", ".EXTERNAL X", "JSR Y"),
                          [(3, "'Y'")])
        self.assertErrors(source(".ORIG x3000", "JSR Y"), [(2, "símbolo no definido")])

    def test_an_external_must_match_the_exact_name(self):
        self.assertErrors(source(".ORIG x3000", ".EXTERNAL printf", "JSR PRINTF"),
                          [(3, "'PRINTF'")])

    def test_declaring_an_external_does_not_define_other_names(self):
        self.assertErrors(source(".ORIG x3000", ".EXTERNAL A", "BR A", "BR B", "BR A"),
                          [(4, "'B'")])

    def test_an_external_is_not_a_local_symbol_and_has_no_address(self):
        table = build(".ORIG x3000", ".EXTERNAL X", ".EXTERNAL Y", "JSR X", "LOCAL: NOP")
        self.assertNotIn("X", table.symbols)
        self.assertNotIn("Y", table.symbols)
        self.assertIsNone(table.symbols.get("X"))
        self.assertEqual(set(table.symbols), {"LOCAL"})
        self.assertFalse(set(table.symbols) & table.externals)
        self.assertEqual(set(table.line_addresses), {4, 5})      # solo las líneas que ocupan memoria

    def test_an_external_declaration_does_not_move_any_address(self):
        plain = build(".ORIG x3000", '.STRINGZ "AB"', "A: NOP", "B: .FILL #1")
        with_externals = build(".ORIG x3000", ".EXTERNAL X", '.STRINGZ "AB"',
                               ".EXTERNAL Y", "A: NOP", "B: .FILL #1", "JSR X")
        # (con "JSR X" extra no se compara el tamaño: solo direcciones previas)
        self.assertEqual(plain.symbols["A"], with_externals.symbols["A"])
        self.assertEqual(plain.symbols["B"], with_externals.symbols["B"])
        self.assertEqual(plain.padding[0].address, with_externals.padding[0].address)
        self.assertEqual(with_externals.end_address - plain.end_address, 2)   # solo el JSR

    def test_externals_alone_add_no_bytes(self):
        base = build(".ORIG x3000", "NOP")
        extra = build(".ORIG x3000", ".EXTERNAL A", ".EXTERNAL B", "NOP", ".EXTERNAL C")
        self.assertEqual((extra.origin, extra.end_address, extra.size),
                         (base.origin, base.end_address, base.size))
        self.assertEqual(extra.externals, frozenset({"A", "B", "C"}))

    def test_a_local_label_cannot_take_an_external_name(self):
        self.assertErrors(source(".ORIG x3000", ".EXTERNAL X", "X: NOP"),
                          [(3, "conflicto")])
        self.assertErrors(source(".ORIG x3000", "X: NOP", ".EXTERNAL X"),
                          [(3, "conflicto")])

    def test_the_table_stays_immutable_with_externals(self):
        table = build(".ORIG x3000", ".EXTERNAL X", "JSR X")
        self.assertIsInstance(table.externals, frozenset)
        self.assertFalse(hasattr(table.externals, "add"))
        with self.assertRaises(TypeError):
            table.symbols["X"] = 0x4000                 # no se puede inyectar una dirección
        with self.assertRaises(dataclasses.FrozenInstanceError):
            table.externals = frozenset()
        copy = SymbolTable({}, {"X"}, {}, (), 0, 0)      # el constructor también congela
        self.assertIsInstance(copy.externals, frozenset)

    def test_there_is_no_api_for_external_addresses_yet(self):
        self.assertEqual(list(inspect.signature(build_symbol_table).parameters), ["program"])
        self.assertEqual({f.name for f in dataclasses.fields(SymbolTable)},
                         {"symbols", "externals", "line_addresses", "padding",
                          "origin", "end_address"})

    def test_the_unresolved_address_is_documented(self):
        documentation = symbols_module.__doc__
        self.assertIn("SÍMBOLOS EXTERNOS", documentation)
        self.assertIn("SIN RESOLVER", documentation)
        self.assertIn("mapping nombre -> dirección", documentation)
        self.assertIn("SIN dirección", SymbolTable.__doc__)


# ----------------------------------------------------------------------
# Etapa 5.3.2: integración con origen par
# ----------------------------------------------------------------------
class TestIntegrationEvenOrigin(SymbolTestCase):

    def test_even_origin_with_instructions_and_data(self):
        table = build(".ORIG x4000",                 # 1
                      "START: LEA R0, MSG",            # 2   x4000
                      "       LDW R1, R0, #0",         # 3   x4002
                      "       HALT",                   # 4   x4004
                      "MSG:   .FILL #7",               # 5   x4006
                      "TBL:   .BLKW #2",               # 6   x4008..x400B
                      'NAME:  .STRINGZ "OK"',          # 7   x400C..x400E
                      "       .END")                   # 8
        self.assertEqual(dict(table.symbols),
                         {"START": 0x4000, "MSG": 0x4006, "TBL": 0x4008, "NAME": 0x400C})
        self.assertEqual(dict(table.line_addresses),
                         {2: 0x4000, 3: 0x4002, 4: 0x4004, 5: 0x4006, 6: 0x4008, 7: 0x400C})
        self.assertEqual(table.padding, ())
        self.assertEqual((table.origin, table.end_address, table.size), (0x4000, 0x400F, 15))

    def test_external_symbols_and_local_labels_together(self):
        table = build(".ORIG x3000",                 # 1
                      ".EXTERNAL PRINTF",              # 2
                      ".EXTERNAL BUFFER",              # 3
                      "START: LEA R0, MSG",            # 4   x3000
                      "       JSR PRINTF",             # 5   x3002
                      "       LEA R1, BUFFER",         # 6   x3004
                      "       BRnzp START",            # 7   x3006
                      'MSG:   .STRINGZ "Hi"',          # 8   x3008..x300A
                      "PTR:   .FILL BUFFER",           # 9   x300B..x300C
                      "       .END")                   # 10
        self.assertEqual(dict(table.symbols), {"START": 0x3000, "MSG": 0x3008, "PTR": 0x300B})
        self.assertEqual(table.externals, frozenset({"PRINTF", "BUFFER"}))
        self.assertEqual(dict(table.line_addresses),
                         {4: 0x3000, 5: 0x3002, 6: 0x3004, 7: 0x3006, 8: 0x3008, 9: 0x300B})
        self.assertEqual((table.end_address, table.size), (0x300D, 13))

    def test_odd_length_data_followed_by_an_instruction_produces_padding(self):
        table = build(".ORIG x3000",                 # 1
                      'FLAG: .STRINGZ "AB"',           # 2   x3000..x3002 -> contador x3003
                      "AFTER:",                        # 3   pendiente
                      "RUN: NOP",                      # 4   relleno x3003, NOP en x3004
                      "     .END")                     # 5
        self.assertEqual(table.padding, (Padding(0x3003, 1, 4),))
        self.assertEqual((table.symbols["AFTER"], table.symbols["RUN"]), (0x3004, 0x3004))
        self.assertEqual((table.end_address, table.size), (0x3006, 6))

    def test_labels_keep_their_addresses_for_every_even_origin_in_the_corpus(self):
        digest, count = corpus_digest(build_symbol_table, SymbolErrors)
        self.assertEqual(count, CORPUS_SIZE)
        self.assertEqual(digest, CORPUS_DIGEST)

    def test_the_corpus_exercises_padding_errors_and_externals(self):
        valid = padded = failed = with_externals = 0
        for program in corpus_programs():
            try:
                table = build_symbol_table(program)
            except SymbolErrors:
                failed += 1
                continue
            valid += 1
            padded += bool(table.padding)
            with_externals += bool(table.externals)
        self.assertEqual(valid + failed, CORPUS_SIZE)
        self.assertGreater(padded, 1000)
        self.assertGreater(failed, 1000)
        self.assertGreater(with_externals, 1000)


# ----------------------------------------------------------------------
# Estructura del módulo
# ----------------------------------------------------------------------
class TestModuleStructure(unittest.TestCase):

    def test_symbols_depends_only_on_the_parser_and_isa(self):
        tree = ast.parse(Path(symbols_module.__file__).read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)
            elif isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
        project = {n for n in imported if n.startswith(("simulator", "assembler"))}
        self.assertEqual(project, {"assembler.parser", "simulator.isa"})

    def test_symbols_has_no_instruction_table_of_its_own(self):
        tree = ast.parse(Path(symbols_module.__file__).read_text(encoding="utf-8"))
        docstrings = {id(n.value) for n in ast.walk(tree) if isinstance(n, ast.Expr)}
        literals = {n.value for n in ast.walk(tree)
                    if isinstance(n, ast.Constant) and isinstance(n.value, str)
                    and id(n) not in docstrings}
        mnemonics = {"ADD", "SUB", "AND", "OR", "XOR", "NOT", "SHL", "SHR", "SAR", "CMP",
                     "LDW", "STW", "LDBL", "LDBH", "STBL", "STBH", "BR", "JSR", "JMP",
                     "LEA", "LDI", "STI", "TRAP", "NOP", "HALT", "JSRR"}
        self.assertEqual(literals & mnemonics, set())

    def test_the_public_api(self):
        self.assertEqual(sorted(symbols_module.__all__),
                         ["Padding", "SymbolError", "SymbolErrors", "SymbolTable",
                          "build_symbol_table"])


if __name__ == "__main__":
    unittest.main()