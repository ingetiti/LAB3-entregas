"""Pruebas de los colores del editor y de la entrada de GETC/IN (no necesitan pantalla)."""
import unittest

from lc10.syntax import highlight_spans, parse_input_escapes


def spans(line):
    """[(etiqueta, texto)] de una sola línea."""
    return [(tag, line[a:b]) for tag, _ln, a, b in highlight_spans(line)]


class TestHighlight(unittest.TestCase):
    def test_label_mnemonic_registers_and_comment(self):
        self.assertEqual(spans("LAZO    ADD   R1, R1, R2   ; suma"),
                         [("label_def", "LAZO"), ("mnemonic", "ADD"), ("reg", "R1"), ("reg", "R1"),
                          ("reg", "R2"), ("comment", "; suma")])

    def test_directive_and_hex_number(self):
        self.assertEqual(spans("        .ORIG x3000"), [("directive", ".ORIG"), ("number", "x3000")])

    def test_semicolon_inside_string_is_not_a_comment(self):
        self.assertEqual(spans('MSG  .STRINGZ "a;b\\n"  ; fin'),
                         [("label_def", "MSG"), ("directive", ".STRINGZ"), ("string", '"a;b\\n"'), ("comment", "; fin")])

    def test_branch_target_is_a_label_reference(self):
        self.assertEqual(spans("        BRp   LAZO"), [("mnemonic", "BRp"), ("label_ref", "LAZO")])
        self.assertEqual(spans("        BRnzp FIN"), [("mnemonic", "BRnzp"), ("label_ref", "FIN")])

    def test_qualified_symbol_is_one_token(self):
        self.assertEqual(spans("        JSR   DIVISION-DIV_LONG"), [("mnemonic", "JSR"), ("label_ref", "DIVISION-DIV_LONG")])
        self.assertEqual(spans("        .EXTERNAL DIVISION-DIV_LONG"), [("directive", ".EXTERNAL"), ("label_ref", "DIVISION-DIV_LONG")])

    def test_numbers(self):
        self.assertEqual(spans("        ADD R1, R1, #-1"), [("mnemonic", "ADD"), ("reg", "R1"), ("reg", "R1"), ("number", "#-1")])
        self.assertEqual(spans("        .FILL -5"), [("directive", ".FILL"), ("number", "-5")])
        self.assertEqual(spans("        .FILL 0b101"), [("directive", ".FILL"), ("number", "0b101")])
        self.assertEqual(spans("        .FILL xFF"), [("directive", ".FILL"), ("number", "xFF")])

    def test_label_with_colon_and_instruction_on_the_same_line(self):
        self.assertEqual(spans("FIN:    HALT"), [("label_def", "FIN:"), ("mnemonic", "HALT")])

    def test_instruction_at_column_zero_is_not_a_label(self):
        self.assertEqual(spans("ADD R1, R1, R2")[0], ("mnemonic", "ADD"))

    def test_trap_aliases_and_pseudo_ops_are_mnemonics(self):
        for m in ("OUT", "PUTS", "HALT", "RET", "NOP", "MOV", "RCL", "BRC", "BRlt"):
            self.assertEqual(spans(f"        {m}")[0], ("mnemonic", m), m)

    def test_unknown_instruction_after_a_label_is_flagged(self):
        self.assertEqual(spans("LAZO    FOO R1"), [("label_def", "LAZO"), ("unknown", "FOO"), ("reg", "R1")])

    def test_comment_only_and_blank_lines(self):
        self.assertEqual(spans("; solo un comentario"), [("comment", "; solo un comentario")])
        self.assertEqual(spans(""), [])
        self.assertEqual(spans("      "), [])

    def test_line_numbers_are_one_based_and_multiline(self):
        found = highlight_spans("; a\n        HALT\n")
        self.assertEqual([(t, ln) for t, ln, _a, _b in found], [("comment", 1), ("mnemonic", 2)])

    def test_unterminated_string_does_not_hang_or_crash(self):
        self.assertEqual(spans('        .STRINGZ "abc')[-1], ("string", '"abc'))


class TestInputEscapes(unittest.TestCase):
    def test_escapes(self):
        self.assertEqual(parse_input_escapes("hola\\n"), "hola\n")
        self.assertEqual(parse_input_escapes("a\\tb"), "a\tb")
        self.assertEqual(parse_input_escapes("a\\\\n"), "a\\n")          # \\n -> barra y n, no salto de línea
        self.assertEqual(parse_input_escapes("sin escapes 123"), "sin escapes 123")
        self.assertEqual(parse_input_escapes(""), "")


if __name__ == "__main__":
    unittest.main()
