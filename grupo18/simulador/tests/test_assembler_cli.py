"""Pruebas de la CLI del ensamblador, assembler/__main__.py (ejecutar desde la raíz Lab3C).

La mayoría corre EN PROCESO: se llama a main(argv, stdout=..., stderr=...) con flujos en
memoria, lo que es rápido y no depende de la terminal. Unas pocas usan subprocess para
comprobar el cableado real de `python3 -m assembler` y la tubería con `python3 -m simulator`
(siempre con stdin=DEVNULL y con timeout, para que nada pueda bloquearse).

Los programas Assembly se crean en un directorio temporal y los BYTES ESPERADOS están
calculados A MANO a partir del formato de la ISA (palabras de 16 bits en Little Endian), nunca
con el ensamblador que se prueba. El archivo de salida es el formato B: dos bytes de origen
(x3000 = 00 30) y a continuación el payload.

Referencia de codificación (calculada a mano):
  A   [OP:5][DR:3][SR1:3][M:1][OP2:4]    ADD R0,R0,#1 = 00000_000_000_1_0001 = 0x0011
  B   [OP:5][REG:3][BASE:3][OFFSET:5]    LDW R0,R1,#0 = 01010_000_001_00000 = 0x5020
  C   [OP:5][NZP:3][PCOFFSET:8]          BRp #-2      = 10000_001_11111110 = 0x81FE
  JSR [OP:5][OFFSET:11]                  JSR #3       = 10001_00000000011  = 0x8803
  JMP/JSRR [OP:5][BASE:3][0:8]           JMP R1       = 10010_001_00000000 = 0x9100
  LEA [OP:5][DR:3][OFFSET:8] (bytes)     LEA R0,#4    = 10011_000_00000100 = 0x9804
  TRAP [OP:5][VECTOR:8][0:3]             TRAP x22     = 10110_00100010_000 = 0xB110
  NOP = 0xB800    HALT = 0xC000
"""

import ast
import contextlib
import inspect
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from collections import namedtuple
from pathlib import Path
from unittest import mock

from assembler import __main__ as cli_module
from assembler.__main__ import main
from assembler.assembler import assemble
from assembler.encoder import EncodeError, EncodeErrors
from assembler.parser import ParseError, ParseErrors
from assembler.symbols import SymbolError, SymbolErrors
from simulator import __main__ as simulator_cli
from simulator.loader import read_binary
from simulator.runner import RunStatus, run_program

PROJECT_ROOT = Path(__file__).resolve().parent.parent

RUNNING_AS_ROOT = hasattr(os, "geteuid") and os.geteuid() == 0
CAN_USE_PERMISSIONS = os.name != "nt" and not RUNNING_AS_ROOT
PERMISSIONS_REASON = "los permisos POSIX no se aplican en Windows ni al usuario root"

# Palabras de instrucción calculadas a mano (ver la referencia del docstring del módulo).
HALT = 0xC000
NOP = 0xB800
ADD_R0_R0_1 = 0x0011
ADD_R1_R1_1 = 0x0131
ADD_R1_R2_R3 = 0x0143           # 00000_001_010_0_0011 (modo registro: M = 0)
SUB_R1_R1_1 = 0x0931
AND_R2_R2_0 = 0x1250
LDW_R0_R1_0 = 0x5020
STW_R2_R3_M1 = 0x5A7F           # 01011_010_011_11111
BRP_BACK_2 = 0x81FE
JMP_R1 = 0x9100
JSRR_R2 = 0xCA00                # 11001_010_00000000
TRAP_PUTS = 0xB110

CliResult = namedtuple("CliResult", "code out err")


def words(*values):
    """Palabras de 16 bits (hechas a mano) -> bytes en Little Endian."""
    return b"".join(value.to_bytes(2, "little") for value in values)


def program(*lines):
    """Texto Assembly con un salto de línea tras cada línea."""
    return "\n".join(lines) + "\n"


def summary_fields(err):
    """Campos 'Clave: valor' del resumen de stderr (robusto a los espacios de alineación)."""
    fields = {}
    for line in err.splitlines():
        key, separator, value = line.partition(":")
        if separator and key in ("Fuente", "Binario", "Origen", "Tamaño", "Dirección final"):
            fields[key] = value.strip()
    return fields


@contextlib.contextmanager
def working_directory(path):
    previous = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


class CliTestCase(unittest.TestCase):

    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name).resolve()

    def write(self, name, content):
        """Crea `name` en el directorio temporal (str -> UTF-8 sin traducir saltos de línea)."""
        path = self.directory / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content.encode("utf-8") if isinstance(content, str) else content)
        return str(path)

    def cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        code = main(list(argv), stdout=out, stderr=err)
        return CliResult(code, out.getvalue(), err.getvalue())

    def binary_of(self, source_path):
        return Path(os.path.splitext(source_path)[0] + ".bin").read_bytes()

    def assemble_ok(self, text, *extra, name="program.asm"):
        """Ensambla `text` con éxito y devuelve los bytes del binario por defecto."""
        path = self.write(name, text)
        result = self.cli(path, *extra)
        self.assertEqual((result.code, result.out), (0, ""), result.err)
        return self.binary_of(path)

    def assemble_fails(self, text, *extra, name="program.asm", code=4):
        path = self.write(name, text)
        result = self.cli(path, *extra)
        self.assertEqual(result.code, code, result.err)
        self.assertEqual(result.out, "")
        self.assertNotIn("Traceback", result.err)
        self.assertFalse(Path(os.path.splitext(path)[0] + ".bin").exists())
        return path, result

    def make_symlink(self, target, link):
        try:
            os.symlink(target, link)
        except (OSError, NotImplementedError, AttributeError):
            self.skipTest("este sistema no permite crear enlaces simbólicos")

    def listing(self):
        return sorted(str(p.relative_to(self.directory)) for p in self.directory.rglob("*"))


# ----------------------------------------------------------------------
# Argumentos
# ----------------------------------------------------------------------
class TestArguments(CliTestCase):

    def test_help_prints_usage_to_stdout_and_exits_zero(self):
        result = self.cli("--help")
        self.assertEqual((result.code, result.err), (0, ""))
        self.assertIn("usage", result.out)
        self.assertIn("fuente", result.out)

    def test_short_help_is_the_same_as_long_help(self):
        self.assertEqual(self.cli("-h"), self.cli("--help"))

    def test_help_documents_the_options_and_has_examples(self):
        out = self.cli("--help").out
        for text in ("-o", "--output", "--external", "NOMBRE=DIRECCIÓN", "x3100", "0x3100",
                     "python3 -m assembler programa.asm -o build/programa.bin"):
            self.assertIn(text, out)
    def test_help_documents_every_exit_code(self):
        out = self.cli("--help").out
        self.assertIn("códigos de salida", out)
        for code in "02345":
            self.assertRegex(out, rf"(?m)^\s+{code}\s+\S", f"falta el código {code}")
        self.assertRegex(out, r"(?m)^\s+1\s+no se usa")

    def test_help_does_not_assemble_or_touch_the_disk(self):
        self.write("program.asm", program(".ORIG x3000", "HALT"))
        before = self.listing()
        with mock.patch.object(cli_module, "assemble") as assembler:
            self.cli(str(self.directory / "program.asm"), "--help")
        assembler.assert_not_called()
        self.assertEqual(self.listing(), before)

    def test_the_source_is_required(self):
        result = self.cli()
        self.assertEqual((result.code, result.out), (2, ""))
        self.assertIn("usage", result.err.lower())

    def test_a_missing_source_is_a_read_error_not_a_usage_error(self):
        missing = str(self.directory / "missing.asm")
        result = self.cli(missing)
        self.assertEqual((result.code, result.out), (3, ""))
        self.assertIn("missing.asm", result.err)
        self.assertEqual(self.listing(), [])

    def test_unknown_arguments_are_usage_errors(self):
        path = self.write("p.asm", program(".ORIG x3000", "HALT"))
        stray = str(self.directory / "stray.bin")      # absoluta: jamás ensucia el cwd
        for extra in (["--foo"], ["-z"], ["--force"], ["--output-file", stray]):
            with self.subTest(extra=extra):
                result = self.cli(path, *extra)
                self.assertEqual((result.code, result.out), (2, ""))
                self.assertFalse((self.directory / "p.bin").exists())

    def test_abbreviated_long_options_are_rejected(self):
        path = self.write("p.asm", program(".ORIG x3000", "HALT"))
        stray = str(self.directory / "stray.bin")      # absoluta: jamás ensucia el cwd
        for extra in (["--out", stray], ["--ext", "A=1"]):
            with self.subTest(extra=extra):
                self.assertEqual(self.cli(path, *extra).code, 2)
        self.assertEqual(self.listing(), ["p.asm"])

    def test_options_without_their_argument(self):
        path = self.write("p.asm", program(".ORIG x3000", "HALT"))
        for option in ("-o", "--output", "--external"):
            with self.subTest(option=option):
                result = self.cli(path, option)
                self.assertEqual((result.code, result.out), (2, ""))
                self.assertIn(option, result.err)
        self.assertFalse((self.directory / "p.bin").exists())
    def test_more_than_one_source_is_a_usage_error(self):
        first = self.write("a.asm", program(".ORIG x3000", "HALT"))
        second = self.write("b.asm", program(".ORIG x3000", "HALT"))
        result = self.cli(first, second)
        self.assertEqual((result.code, result.out), (2, ""))
        self.assertEqual(self.listing(), ["a.asm", "b.asm"])

    def test_malformed_external_declarations(self):
        path = self.write("p.asm", program(".ORIG x3000", "HALT"))
        for text in ("BUFFER", "BUFFER:x3100", "x3100", "", "BUFFER x3100"):
            with self.subTest(text=text):
                result = self.cli(path, "--external", text)
                self.assertEqual((result.code, result.out), (2, ""))
                self.assertIn("NOMBRE=DIRECCIÓN", result.err)
        self.assertFalse((self.directory / "p.bin").exists())

    def test_an_external_with_an_empty_name(self):
        path = self.write("p.asm", program(".ORIG x3000", "HALT"))
        for text in ("=x3100", "   =x3100", "="):
            with self.subTest(text=text):
                result = self.cli(path, "--external", text)
                self.assertEqual((result.code, result.out), (2, ""))
                self.assertIn("vacío", result.err)

    def test_an_external_with_an_invalid_address(self):
        path = self.write("p.asm", program(".ORIG x3000", "HALT"))
        invalid = ("BUF=", "BUF=   ", "BUF=zz", "BUF=x", "BUF=0x", "BUF=xG1", "BUF=-1",
                   "BUF=+5", "BUF=1.5", "BUF=#10", "BUF=1_000", "BUF=0b11", "BUF=3100h",
                   "BUF=x 31", "BUF=\uff13\uff11\uff10\uff10", "BUF=B=1")
        for text in invalid:
            with self.subTest(text=text):
                result = self.cli(path, "--external", text)
                self.assertEqual((result.code, result.out), (2, ""))
                self.assertIn("dirección inválida", result.err)
        self.assertFalse((self.directory / "p.bin").exists())

    def test_a_huge_decimal_address_is_a_controlled_error_not_a_traceback(self):
        # Según el intérprete, int() rechaza miles de dígitos (la CLI responde 2) o los acepta
        # y el ensamblador informa el rango (4). En ambos casos: error controlado, sin salida.
        path = self.write("p.asm", program(".ORIG x3000", ".EXTERNAL BUF", ".FILL BUF"))
        result = self.cli(path, "--external", "BUF=" + "9" * 5000)
        self.assertIn(result.code, (2, 4))
        self.assertEqual(result.out, "")
        self.assertNotIn("Traceback", result.err)
        self.assertFalse((self.directory / "p.bin").exists())

    def test_duplicate_externals_are_rejected_even_with_the_same_address(self):
        path = self.write("p.asm", program(".ORIG x3000", "HALT"))
        for second in ("BUF=x3100", "BUF=x3200", "BUF=12544"):
            with self.subTest(second=second):
                result = self.cli(path, "--external", "BUF=x3100", "--external", second)
                self.assertEqual((result.code, result.out), (2, ""))
                self.assertIn("BUF", result.err)
        self.assertFalse((self.directory / "p.bin").exists())

    def test_external_names_are_case_sensitive_so_these_are_not_duplicates(self):
        text = program(".ORIG x3000", ".EXTERNAL A", ".EXTERNAL a", ".FILL A", ".FILL a")
        data = self.assemble_ok(text, "--external", "A=x1111", "--external", "a=x2222")
        self.assertEqual(data, b"\x00\x30" + words(0x1111, 0x2222))

    def test_argument_errors_never_assemble_or_write(self):
        path = self.write("p.asm", program(".ORIG x3000", "HALT"))
        with mock.patch.object(cli_module, "assemble") as assembler, \
                mock.patch.object(cli_module, "write_binary") as writer:
            self.cli(path, "--external", "malformed")
            self.cli(path, "--bogus")
            self.cli()
        assembler.assert_not_called()
        writer.assert_not_called()

    def test_a_source_that_starts_with_a_dash_after_double_dash(self):
        self.write("-p.asm", program(".ORIG x3000", "HALT"))
        with working_directory(self.directory):
            result = self.cli("--", "-p.asm")
        self.assertEqual(result.code, 0, result.err)
        self.assertTrue((self.directory / "-p.bin").exists())

    def test_options_before_the_source_and_the_equals_form(self):
        path = self.write("p.asm", program(".ORIG x3000", ".EXTERNAL A", ".FILL A"))
        target = self.directory / "o.bin"
        for argv in (["--external", "A=x0042", "-o", str(target), path],
                     [path, f"--output={target}", "--external=A=x0042"]):
            with self.subTest(argv=argv):
                target.unlink(missing_ok=True)
                result = self.cli(*argv)
                self.assertEqual(result.code, 0, result.err)
                self.assertEqual(target.read_bytes(), b"\x00\x30" + words(0x42))


# ----------------------------------------------------------------------
# Ensamblado correcto: bytes esperados
# ----------------------------------------------------------------------
class TestSuccessfulAssembly(CliTestCase):

    def test_a_program_assembles_with_exit_zero_and_creates_the_binary(self):
        path = self.write("p.asm", program(".ORIG x3000", "ADD R0, R0, #1", "HALT", ".END"))
        result = self.cli(path)
        self.assertEqual((result.code, result.out), (0, ""))
        self.assertEqual((self.directory / "p.bin").read_bytes(),
                         b"\x00\x30" + words(ADD_R0_R0_1, HALT))

    def test_the_file_is_format_b_origin_little_endian_then_payload(self):
        data = self.assemble_ok(program(".ORIG x1234", "NOP", "HALT"))
        self.assertEqual(data[:2], b"\x34\x12")
        self.assertEqual(data[2:], words(NOP, HALT))

    def test_arithmetic_and_logic_instructions(self):
        text = program(".ORIG x3000", "ADD R1, R2, R3", "SUB R1, R1, #1", "AND R2, R2, #0",
                       "ADD R1, R1, #1")
        self.assertEqual(self.assemble_ok(text),
                         b"\x00\x30" + words(ADD_R1_R2_R3, SUB_R1_R1_1, AND_R2_R2_0,
                                             ADD_R1_R1_1))

    def test_register_aliases_and_immediate_limits(self):
        text = program(".ORIG x3000", "ADD SP, SP, #1", "ADD LR, LR, #1", "ADD R0, R0, #7",
                       "ADD R0, R0, #-8")
        self.assertEqual(self.assemble_ok(text),
                         b"\x00\x30" + words(0x06D1, 0x07F1, 0x0017, 0x0018))

    def test_hexadecimal_and_decimal_literal_forms(self):
        text = program(".ORIG x3000", "ADD R0, R0, x1", "ADD R0, R0, 0x1", "ADD R0, R0, X1",
                       "ADD R0, R0, #1", "TRAP #34", "TRAP x22", "TRAP 0X22")
        self.assertEqual(self.assemble_ok(text),
                         b"\x00\x30" + words(*([ADD_R0_R0_1] * 4 + [TRAP_PUTS] * 3)))

    def test_mnemonics_directives_and_registers_ignore_case(self):
        text = program(".orig x3000", "add r1, r2, r3", "Halt", ".End")
        self.assertEqual(self.assemble_ok(text), b"\x00\x30" + words(ADD_R1_R2_R3, HALT))

    def test_memory_jump_and_trap_instructions(self):
        text = program(".ORIG x3000", "LDW R0, R1, #0", "STW R2, R3, #-1", "JMP R1", "JSRR R2",
                       "TRAP x22", "NOP", "HALT")
        self.assertEqual(self.assemble_ok(text),
                         b"\x00\x30" + words(LDW_R0_R1_0, STW_R2_R3_M1, JMP_R1, JSRR_R2,
                                             TRAP_PUTS, NOP, HALT))
    def test_branch_variants_with_numeric_offsets(self):
        text = program(".ORIG x3000", "BR #-1", "BRn #0", "BRz #3", "BRp #-2", "BRnp #1",
                       "BRzp #2", "BRnz #0", "JSR #3")
        self.assertEqual(self.assemble_ok(text),
                         b"\x00\x30" + words(0x87FF, 0x8400, 0x8203, 0x81FE, 0x8501, 0x8302,
                                             0x8600, 0x8803))

    def test_branches_to_labels_forward_and_backward(self):
        backward = program(".ORIG x3000", "ADD R1, R1, #3", "LOOP: SUB R1, R1, #1",
                           "BRp LOOP", "HALT")
        # BRp en x3004: PC siguiente x3006, destino x3002 -> (x3002 - x3006) / 2 = -2
        self.assertEqual(self.assemble_ok(backward, name="back.asm"),
                         b"\x00\x30" + words(0x0133, SUB_R1_R1_1, BRP_BACK_2, HALT))
        forward = program(".ORIG x3000", "BR DONE", "NOP", "DONE: HALT")
        # BR en x3000: PC siguiente x3002, destino x3004 -> offset +1 palabra
        self.assertEqual(self.assemble_ok(forward, name="fwd.asm"),
                         b"\x00\x30" + words(0x8701, NOP, HALT))
    def test_lea_and_stringz(self):
        text = program(".ORIG x3000", "LEA R0, MSG", "TRAP x22", "HALT", 'MSG: .STRINGZ "Hola"')
        # LEA en x3000: PC siguiente x3002, MSG en x3006 -> +4 bytes
        self.assertEqual(self.assemble_ok(text),
                         b"\x00\x30" + words(0x9804, TRAP_PUTS, HALT) + b"Hola\x00")

    def test_fill_blkw_and_stringz_directives(self):
        text = program(".ORIG x3000", ".FILL x1234", ".FILL #-1", ".FILL 0xBEEF", ".BLKW #3",
                       '.STRINGZ "ab"')
        self.assertEqual(self.assemble_ok(text),
                         b"\x00\x30" + b"\x34\x12\xFF\xFF\xEF\xBE" + bytes(6) + b"ab\x00")

    def test_fill_with_a_label_stores_its_absolute_address(self):
        text = program(".ORIG x3000", "TABLE: .FILL TABLE", ".FILL END_MARK", "END_MARK: HALT")
        self.assertEqual(self.assemble_ok(text),
                         b"\x00\x30" + words(0x3000, 0x3004, HALT))

    def test_stringz_escapes_and_empty_string(self):
        text = program(".ORIG x3000", r'.STRINGZ "a\n\t\r\\\"b"', '.STRINGZ ""')
        self.assertEqual(self.assemble_ok(text),
                         b"\x00\x30" + b"a\n\t\r\\\"b\x00" + b"\x00")

    def test_stringz_encodes_each_character_as_one_byte_by_code_point(self):
        text = program(".ORIG x3000", '.STRINGZ "é"')       # U+00E9: un byte 0xE9, no UTF-8
        self.assertEqual(self.assemble_ok(text), b"\x00\x30" + b"\xE9\x00")

    def test_other_origins(self):
        self.assertEqual(self.assemble_ok(program(".ORIG x0000", "HALT")),
                         b"\x00\x00" + words(HALT))
        self.assertEqual(self.assemble_ok(program(".ORIG x4000", "HALT"), name="b.asm"),
                         b"\x00\x40" + words(HALT))
        self.assertEqual(self.assemble_ok(program(".ORIG #12288", "HALT"), name="c.asm"),
                         b"\x00\x30" + words(HALT))

    def test_the_end_directive_is_optional_and_only_comments_may_follow_it(self):
        with_end = self.assemble_ok(program(".ORIG x3000", "ADD R0, R0, #1", "HALT", ".END"),
                                    name="with.asm")
        without_end = self.assemble_ok(program(".ORIG x3000", "ADD R0, R0, #1", "HALT"),
                                       name="without.asm")
        trailing = self.assemble_ok(program(".ORIG x3000", "ADD R0, R0, #1", "HALT", ".END", "",
                                            "; fin", "   ; otro comentario"), name="tail.asm")
        self.assertEqual(with_end, without_end)
        self.assertEqual(with_end, trailing)
        self.assertEqual(with_end, b"\x00\x30" + words(ADD_R0_R0_1, HALT))
    def test_an_instruction_after_odd_length_data_is_padded_with_one_zero_byte(self):
        text = program(".ORIG x3000", 'MSG: .STRINGZ "ab"', "HALT")
        # "ab\0" ocupa x3000-x3002; HALT debe empezar en x3004 -> un byte de relleno
        self.assertEqual(self.assemble_ok(text), b"\x00\x30" + b"ab\x00" + b"\x00" + words(HALT))

    def test_labels_after_padding_point_to_the_aligned_instruction(self):
        text = program(".ORIG x3000", 'MSG: .STRINGZ "ab"', "GO: HALT", ".FILL GO")
        self.assertEqual(self.assemble_ok(text),
                         b"\x00\x30" + b"ab\x00\x00" + words(HALT, 0x3004))

    def test_data_after_odd_length_data_is_not_padded(self):
        text = program(".ORIG x3000", '.STRINGZ "ab"', ".FILL x1234")
        self.assertEqual(self.assemble_ok(text), b"\x00\x30" + b"ab\x00" + b"\x34\x12")

    def test_comments_everywhere_but_inside_strings(self):
        text = program("; cabecera", ".ORIG x3000   ; origen", "  ; solo comentario",
                       "ADD R0, R0, #1 ; suma", "HALT;sin espacio",
                       '.STRINGZ "a;b" ; comentario real', ".END ; fin")
        self.assertEqual(self.assemble_ok(text),
                         b"\x00\x30" + words(ADD_R0_R0_1, HALT) + b"a;b\x00")
    def test_crlf_and_cr_line_endings_give_the_same_bytes_as_lf(self):
        lf = program(".ORIG x3000", "ADD R0, R0, #1", "LOOP: BR LOOP", 'S: .STRINGZ "a b"')
        expected = self.assemble_ok(lf, name="lf.asm")
        for name, ending in (("crlf.asm", "\r\n"), ("cr.asm", "\r")):
            with self.subTest(name):
                data = self.assemble_ok(lf.replace("\n", ending).encode("utf-8"), name=name)
                self.assertEqual(data, expected)
        self.assertEqual(expected[-3:], b" b\x00")        # ningún CR se coló en la cadena
    def test_tabs_and_irregular_spacing(self):
        text = (".ORIG\tx3000\n\tADD\tR0,\tR0,\t#1\n\n   HALT   \t\nLBL:\t.FILL\t#5\n")
        self.assertEqual(self.assemble_ok(text), b"\x00\x30" + words(ADD_R0_R0_1, HALT, 5))

    def test_a_utf8_bom_is_ignored(self):
        text = program(".ORIG x3000", "ADD R0, R0, #1", "HALT")
        with_bom = self.assemble_ok(b"\xEF\xBB\xBF" + text.encode("utf-8"), name="bom.asm")
        self.assertEqual(with_bom, b"\x00\x30" + words(ADD_R0_R0_1, HALT))
        self.assertEqual(with_bom, self.assemble_ok(text, name="nobom.asm"))
        crlf = self.assemble_ok(b"\xEF\xBB\xBF; cabecera\r\n.ORIG x3000\r\nHALT\r\n",
                                name="bomcrlf.asm")
        self.assertEqual(crlf, b"\x00\x30" + words(HALT))
    def test_non_ascii_text_in_comments_is_accepted(self):
        text = program("; Programa de prueba: ñandú, acentuación, 日本語", ".ORIG x3000", "HALT")
        self.assertEqual(self.assemble_ok(text), b"\x00\x30" + words(HALT))

    def test_a_program_without_bytes_produces_a_two_byte_file(self):
        path = self.write("p.asm", program(".ORIG x3000"))
        result = self.cli(path)
        self.assertEqual(result.code, 0, result.err)
        self.assertEqual((self.directory / "p.bin").read_bytes(), b"\x00\x30")
        self.assertEqual(summary_fields(result.err)["Tamaño"], "0 bytes")

    def test_a_large_block_of_reserved_words(self):
        data = self.assemble_ok(program(".ORIG x3000", ".BLKW #100", "HALT"))
        self.assertEqual(data, b"\x00\x30" + bytes(200) + words(HALT))

    def test_the_last_instruction_of_memory(self):
        data = self.assemble_ok(program(".ORIG xFFFE", "HALT"))
        self.assertEqual(data, b"\xFE\xFF" + words(HALT))

    def test_the_source_file_is_never_modified(self):
        content = program(".ORIG x3000", "HALT").encode("utf-8")
        path = self.write("p.asm", content)
        self.assertEqual(self.cli(path).code, 0)
        self.assertEqual(Path(path).read_bytes(), content)


# ----------------------------------------------------------------------
# Nombre y ubicación de la salida
# ----------------------------------------------------------------------
class TestOutputPath(CliTestCase):
    SOURCE = program(".ORIG x3000", "HALT")
    EXPECTED = b"\x00\x30" + words(HALT)

    def test_the_default_output_replaces_the_extension_with_bin(self):
        path = self.write("programa.asm", self.SOURCE)
        self.assertEqual(self.cli(path).code, 0)
        self.assertEqual((self.directory / "programa.bin").read_bytes(), self.EXPECTED)
        self.assertEqual(self.listing(), ["programa.asm", "programa.bin"])

    def test_how_the_default_name_is_derived(self):
        cases = (("programa", "programa.bin"),                  # sin extensión: se agrega
                 ("mi.programa.asm", "mi.programa.bin"),        # solo se reemplaza la última
                 ("a.s", "a.bin"), ("b.ASM", "b.bin"), ("c.txt", "c.bin"),
                 ("dir.d/programa", "dir.d/programa.bin"),      # el punto de un directorio no cuenta
                 (".oculto", ".oculto.bin"))
        for name, expected in cases:
            with self.subTest(name):
                self.assertEqual(self.cli(self.write(name, self.SOURCE)).code, 0)
                self.assertEqual((self.directory / expected).read_bytes(), self.EXPECTED)
    def test_the_default_output_goes_next_to_the_source_not_to_the_cwd(self):
        path = self.write("sub/programa.asm", self.SOURCE)
        other = self.directory / "other"
        other.mkdir()
        with working_directory(other):
            self.assertEqual(self.cli(path).code, 0)
        self.assertTrue((self.directory / "sub" / "programa.bin").exists())
        self.assertEqual(list(other.iterdir()), [])

    def test_a_relative_source_path_gives_a_relative_default_output(self):
        self.write("programa.asm", self.SOURCE)
        with working_directory(self.directory):
            result = self.cli("programa.asm")
        self.assertEqual(result.code, 0, result.err)
        self.assertEqual(summary_fields(result.err)["Binario"], "programa.bin")
        self.assertEqual((self.directory / "programa.bin").read_bytes(), self.EXPECTED)

    def test_a_custom_output_name_short_and_long_option_any_extension(self):
        path = self.write("programa.asm", self.SOURCE)
        for option, name in (("-o", "salida.bin"), ("--output", "largo.bin"), ("-o", "imagen.rom")):
            with self.subTest(option=option, name=name):
                target = self.directory / name
                self.assertEqual(self.cli(path, option, str(target)).code, 0)
                self.assertEqual(target.read_bytes(), self.EXPECTED)
        self.assertFalse((self.directory / "programa.bin").exists())
    def test_an_output_in_another_existing_directory(self):
        path = self.write("programa.asm", self.SOURCE)
        (self.directory / "build").mkdir()
        target = self.directory / "build" / "programa.bin"
        self.assertEqual(self.cli(path, "-o", str(target)).code, 0)
        self.assertEqual(target.read_bytes(), self.EXPECTED)
        self.assertFalse((self.directory / "programa.bin").exists())

    def test_a_relative_output_path_in_a_subdirectory(self):
        self.write("programa.asm", self.SOURCE)
        (self.directory / "build").mkdir()
        with working_directory(self.directory):
            result = self.cli("programa.asm", "-o", "build/programa.bin")
        self.assertEqual(result.code, 0, result.err)
        self.assertEqual((self.directory / "build" / "programa.bin").read_bytes(), self.EXPECTED)

    def test_an_existing_binary_is_overwritten_completely(self):
        path = self.write("programa.asm", self.SOURCE)
        stale = self.write("programa.bin", b"\xAA" * 100)
        self.assertEqual(self.cli(path).code, 0)
        self.assertEqual(Path(stale).read_bytes(), self.EXPECTED)

    def test_the_binary_is_written_with_the_existing_writer(self):
        path = self.write("programa.asm", self.SOURCE)
        target = self.directory / "salida.bin"
        with mock.patch.object(cli_module, "write_binary") as writer:
            result = self.cli(path, "-o", str(target))
        self.assertEqual(result.code, 0, result.err)
        writer.assert_called_once()
        encoded, written_path = writer.call_args.args
        self.assertEqual((encoded.origin, encoded.data), (0x3000, words(HALT)))
        self.assertEqual(written_path, str(target))
        self.assertFalse(target.exists())          # el Writer simulado no escribió nada


# ----------------------------------------------------------------------
# Resumen, stdout y stderr
# ----------------------------------------------------------------------
class TestStreams(CliTestCase):
    SOURCE = program(".ORIG x3000", "ADD R0, R0, #1", "HALT")

    def test_success_leaves_stdout_empty_and_reports_on_stderr(self):
        path = self.write("p.asm", self.SOURCE)
        result = self.cli(path)
        self.assertEqual(result.out, "")
        self.assertIn("Resumen", result.err)

    def test_the_summary_reports_source_binary_origin_size_and_end_address(self):
        path = self.write("p.asm", self.SOURCE)
        fields = summary_fields(self.cli(path).err)
        self.assertEqual(fields, {
            "Fuente": path,
            "Binario": str(self.directory / "p.bin"),
            "Origen": "0x3000",
            "Tamaño": "4 bytes",
            "Dirección final": "0x3004 (primera dirección libre)",
        })

    def test_the_summary_shows_a_custom_output_path(self):
        path = self.write("p.asm", self.SOURCE)
        target = str(self.directory / "otro.bin")
        self.assertEqual(summary_fields(self.cli(path, "-o", target).err)["Binario"], target)

    def test_the_summary_for_odd_sized_programs_and_other_origins(self):
        path = self.write("p.asm", program(".ORIG x4000", '.STRINGZ "a"', ".FILL x1", "HALT"))
        fields = summary_fields(self.cli(path).err)
        self.assertEqual(fields["Origen"], "0x4000")
        self.assertEqual(fields["Tamaño"], "6 bytes")          # 2 + 2 + 2
        self.assertTrue(fields["Dirección final"].startswith("0x4006"))

    def test_summary_edge_cases(self):
        single = self.write("one.asm", program(".ORIG x3000", '.STRINGZ ""'))
        self.assertEqual(summary_fields(self.cli(single).err)["Tamaño"], "1 byte")
        full = self.write("full.asm", program(".ORIG xFFFE", "HALT"))
        self.assertTrue(summary_fields(self.cli(full).err)["Dirección final"].startswith("0x10000"))
    def test_the_size_in_the_summary_matches_the_file(self):
        path = self.write("p.asm", program(".ORIG x3000", ".BLKW #10", "HALT"))
        fields = summary_fields(self.cli(path).err)
        size = int(fields["Tamaño"].split()[0])
        self.assertEqual(size, (self.directory / "p.bin").stat().st_size - 2)

    def test_stdout_is_empty_in_every_outcome(self):
        good = self.write("good.asm", self.SOURCE)
        bad = self.write("bad.asm", "FOO\n")
        outcomes = {
            "ok": [good],
            "assembly error": [bad],
            "missing source": [str(self.directory / "none.asm")],
            "usage": ["--bogus"],
            "no arguments": [],
            "bad external": [good, "--external", "x"],
            "same file": [good, "-o", good],
            "write error": [good, "-o", str(self.directory / "no_dir" / "o.bin")],
        }
        for name, argv in outcomes.items():
            with self.subTest(name):
                self.assertEqual(self.cli(*argv).out, "")

    def test_a_failure_prints_no_summary(self):
        path = self.write("p.asm", "FOO\n")
        self.assertNotIn("Resumen", self.cli(path).err)

    def test_main_writes_only_to_the_streams_it_receives(self):
        path = self.write("p.asm", self.SOURCE)
        real_out, real_err = io.StringIO(), io.StringIO()
        with mock.patch.object(sys, "stdout", real_out), mock.patch.object(sys, "stderr", real_err):
            self.cli(path)
            self.cli("--help")
            self.cli("--bogus")
            self.cli(str(self.directory / "none.asm"))
        self.assertEqual((real_out.getvalue(), real_err.getvalue()), ("", ""))

    def test_without_injected_streams_it_uses_the_real_ones(self):
        path = self.write("p.asm", self.SOURCE)
        real_out, real_err = io.StringIO(), io.StringIO()
        with mock.patch.object(sys, "stdout", real_out), mock.patch.object(sys, "stderr", real_err):
            code = main([path])
        self.assertEqual((code, real_out.getvalue()), (0, ""))
        self.assertIn("Resumen", real_err.getvalue())


# ----------------------------------------------------------------------
# Errores de ensamblado
# ----------------------------------------------------------------------
class TestAssemblyErrors(CliTestCase):

    def test_an_unknown_mnemonic_is_reported_with_file_line_message_and_source(self):
        path, result = self.assemble_fails(program(".ORIG x3000", "NOP", "FOO R0", "HALT"))
        self.assertIn(f"{path}:3: error: mnemónico desconocido 'FOO'", result.err)
        self.assertRegex(result.err, r"(?m)^\s+3 \| FOO R0$")

    def test_exit_code_four_for_every_phase(self):
        cases = {
            "sintaxis": program(".ORIG x3000", "FOO"),
            "mapa de memoria": program(".ORIG x3000", "BR NOWHERE"),
            "codificación": program(".ORIG x3000", "BR FAR", ".BLKW #200", "FAR: HALT"),
        }
        for index, (phase, text) in enumerate(cases.items()):
            with self.subTest(phase):
                _, result = self.assemble_fails(text, name=f"phase{index}.asm")
                self.assertIn(f"fase de {phase}", result.err)

    def test_operand_register_and_literal_errors(self):
        cases = (("ADD R0, R0", "faltan operandos"),
                 ("ADD R0, R9, #1", "registro inexistente 'R9'"),
                 ("ADD R0, R0, #99", "fuera de rango"),
                 ("ADD R0, R0, 5", "literal sin prefijo '5'"),
                 ("TRAP #300", "fuera de rango"),
                 ("LDW R0, R1, #16", "fuera de rango"),
                 ("ADD R0, R0, abc", "la etiqueta 'abc'"))
        for index, (line, message) in enumerate(cases):
            with self.subTest(line=line):
                path, result = self.assemble_fails(program(".ORIG x3000", line),
                                                   name=f"operand{index}.asm")
                self.assertIn(f"{path}:2: error:", result.err)
                self.assertIn(message, result.err)
    def test_duplicate_labels(self):
        path, result = self.assemble_fails(program(".ORIG x3000", "A: NOP", "A: HALT"))
        self.assertIn(f"{path}:3: error: etiqueta 'A' duplicada", result.err)
        self.assertIn("línea 2", result.err)

    def test_undefined_labels(self):
        path, result = self.assemble_fails(program(".ORIG x3000", "BR NOWHERE", "HALT"))
        self.assertIn(f"{path}:2: error: referencia a un símbolo no definido: 'NOWHERE'",
                      result.err)

    def test_invalid_orig_directives(self):
        cases = (("x3001", "dirección par"), ("", "espera 1 operando"),
                 ("x10000", "fuera de rango"), ("#-1", "fuera de rango"),
                 ("HOLA", "se esperaba un literal numérico"))
        for operand, message in cases:
            with self.subTest(operand=operand):
                _, result = self.assemble_fails(program(f".ORIG {operand}".rstrip(), "HALT"))
                self.assertIn(":1: error: .ORIG", result.err)
                self.assertIn(message, result.err)

    def test_other_syntax_errors(self):
        cases = ((program(".ORIG x3000", ".ORIG x4000", "HALT"), 2, "solo se admite un .ORIG"),
                 (program(".ORIG x3000", "HALT", ".END", "NOP"), 4,
                  "después de .END"),
                 (program(".ORIG x3000", ".FOO 1"), 2, "directiva desconocida '.FOO'"),
                 (program(".ORIG x3000", '.STRINGZ "abc'), 2, "cadena sin cerrar"),
                 (program(".ORIG x3000", "R1: NOP"), 2, "es un nombre de registro"))
        for index, (text, line, message) in enumerate(cases):
            with self.subTest(message):
                path, result = self.assemble_fails(text, name=f"s{index}.asm")
                self.assertIn(f"{path}:{line}: error:", result.err)
                self.assertIn(message, result.err)
    def test_a_program_that_does_not_fit_in_memory(self):
        _, result = self.assemble_fails(program(".ORIG xFFFE", "NOP", "NOP"))
        self.assertIn(":3: error: desbordamiento de memoria", result.err)

    def test_a_branch_to_an_odd_address_is_an_encoding_error(self):
        _, result = self.assemble_fails(program(".ORIG x3000", "BR D", "HALT",
                                                '.STRINGZ "ab"', "D: .STRINGZ \"c\""))
        self.assertIn(":2: error:", result.err)
        self.assertIn("fase de codificación", result.err)
    def test_all_the_errors_of_the_phase_are_shown(self):
        text = program(".ORIG x3000", "ADD R0, R0, #99", "ADD R0, R0, abc", "ADD R0, R0, 5",
                       "TRAP #300")
        path, result = self.assemble_fails(text)
        for line in (2, 3, 4, 5):
            self.assertIn(f"{path}:{line}: error:", result.err)
        self.assertIn("4 errores", result.err)
        self.assertEqual(result.err.count(": error:"), 4)

    def test_a_single_error_uses_the_singular(self):
        _, result = self.assemble_fails(program(".ORIG x3000", "FOO"))
        self.assertIn("1 error;", result.err)

    def test_errors_are_listed_in_line_order_each_with_its_source_line(self):
        _, result = self.assemble_fails(program(".ORIG x3000", "FOO R1", "NOP", "BAR R2", "ADD R0"))
        lines = [int(n) for n in re.findall(r"\.asm:(\d+): error", result.err)]
        self.assertEqual(lines, [2, 4, 5])
        for text in ("FOO R1", "BAR R2", "ADD R0"):
            self.assertRegex(result.err, rf"(?m)^\s+\d+ \| {text}$")
    def test_only_the_first_failing_phase_is_reported(self):
        # Un error de sintaxis y una etiqueta no definida: la segunda fase nunca corre.
        _, result = self.assemble_fails(program(".ORIG x3000", "FOO", "BR NOWHERE"))
        self.assertIn("fase de sintaxis", result.err)
        self.assertNotIn("NOWHERE", result.err)

    def test_all_the_errors_of_the_symbol_phase_are_shown(self):
        path, result = self.assemble_fails(program(".ORIG x3000", "BR UNO", "BR DOS", "HALT"))
        self.assertIn(f"{path}:2: error:", result.err)
        self.assertIn(f"{path}:3: error:", result.err)
        self.assertIn("2 errores", result.err)

    def test_all_the_errors_of_the_encoding_phase_are_shown(self):
        text = program(".ORIG x3000", "BR FAR", "JSR FAR", ".BLKW #2000", "FAR: HALT")
        path, result = self.assemble_fails(text)
        self.assertIn(f"{path}:2: error:", result.err)
        self.assertIn(f"{path}:3: error:", result.err)

    def test_a_global_error_has_no_line_number_and_no_source_line(self):
        path, result = self.assemble_fails("")
        self.assertIn(f"{path}: error: falta la directiva .ORIG", result.err)
        self.assertNotRegex(result.err, r"\.asm:\d+")
        self.assertNotIn(" | ", result.err)

    def test_a_program_without_orig_is_a_global_error(self):
        path, result = self.assemble_fails(program("ADD R0, R0, #1", "HALT"))
        self.assertIn(f"{path}: error: falta la directiva .ORIG", result.err)
        self.assertNotRegex(result.err, r"\.asm:\d+")

    def test_global_and_line_errors_are_formatted_by_what_they_carry(self):
        errors = EncodeErrors([EncodeError("global", None, None),
                               EncodeError("con línea y fuente", 7, "  NOP  "),
                               EncodeError("con línea sola", 9, None)])
        path = self.write("p.asm", program(".ORIG x3000", "HALT"))
        with mock.patch.object(cli_module, "assemble", side_effect=errors):
            result = self.cli(path)
        self.assertEqual(result.code, 4)
        self.assertIn(f"{path}: error: global\n", result.err)
        self.assertIn(f"{path}:7: error: con línea y fuente\n      7 |   NOP\n", result.err)
        self.assertIn(f"{path}:9: error: con línea sola\n", result.err)
        self.assertNotIn(f"{path}:0", result.err)
        self.assertEqual(result.err.count(" | "), 1)

    def test_each_exception_family_is_caught(self):
        raised = (ParseErrors([ParseError("p", 1, "x")]),
                  SymbolErrors([SymbolError("s", 2, "y")]),
                  EncodeErrors([EncodeError("e", 3, "z")]))
        path = self.write("p.asm", program(".ORIG x3000", "HALT"))
        for failure in raised:
            with self.subTest(type(failure).__name__):
                with mock.patch.object(cli_module, "assemble", side_effect=failure):
                    result = self.cli(path)
                self.assertEqual((result.code, result.out), (4, ""))
                self.assertNotIn("Traceback", result.err)

    def test_the_file_name_is_shown_as_the_user_typed_it(self):
        self.write("sub/p.asm", "FOO\n")
        with working_directory(self.directory):
            result = self.cli("sub/p.asm")
        self.assertIn("sub/p.asm:1: error:", result.err)

    def test_source_lines_are_shown_without_carriage_returns_or_trailing_whitespace(self):
        path = self.write("p.asm", b".ORIG x3000\r\nFOO R0\r\n")
        result = self.cli(path)
        self.assertEqual(result.code, 4)
        self.assertNotIn("\r", result.err)
        self.assertRegex(result.err, r"(?m)^\s+2 \| FOO R0$")
        _, result = self.assemble_fails(".ORIG x3000\n\tFOO R0   \t\n", name="tabs.asm")
        self.assertRegex(result.err, r"(?m)^\s+2 \| \tFOO R0$")
    def test_no_binary_is_written_after_an_error(self):
        path = self.write("p.asm", "FOO\n")
        with mock.patch.object(cli_module, "write_binary") as writer:
            self.assertEqual(self.cli(path).code, 4)
        writer.assert_not_called()
        self.assertEqual(self.listing(), ["p.asm"])
    def test_a_previous_binary_is_preserved_after_an_error_in_each_phase(self):
        cases = {"sintaxis": "FOO\n", "símbolos": program(".ORIG x3000", "BR NOWHERE"),
                 "codificación": program(".ORIG x3000", "BR FAR", ".BLKW #200", "FAR: HALT"),
                 "global": ""}
        for phase, text in cases.items():
            with self.subTest(phase):
                path = self.write(f"{phase}.asm", text)
                previous = self.write(f"{phase}.bin", b"binario anterior")
                self.assertEqual(self.cli(path).code, 4)
                self.assertEqual(Path(previous).read_bytes(), b"binario anterior")

    def test_a_previous_custom_output_is_preserved_after_an_error(self):
        path = self.write("p.asm", "FOO\n")
        previous = self.write("mio.bin", b"anterior")
        self.assertEqual(self.cli(path, "-o", previous).code, 4)
        self.assertEqual(Path(previous).read_bytes(), b"anterior")

    def test_internal_errors_are_not_hidden(self):
        path = self.write("p.asm", program(".ORIG x3000", "HALT"))
        for name, error in (("assemble", RuntimeError("bug")), ("write_binary", TypeError("bug"))):
            with self.subTest(name):
                with mock.patch.object(cli_module, name, side_effect=error):
                    with self.assertRaises(type(error)):
                        self.cli(path)


# ----------------------------------------------------------------------
# Archivos: lectura, escritura y protección del fuente
# ----------------------------------------------------------------------
class TestFiles(CliTestCase):
    SOURCE = program(".ORIG x3000", "HALT")

    def test_a_directory_as_source(self):
        directory = self.directory / "carpeta"
        directory.mkdir()
        result = self.cli(str(directory))
        self.assertEqual((result.code, result.out), (3, ""))
        self.assertIn("error: no se pudo leer el fuente", result.err)
        self.assertNotIn("Traceback", result.err)

    def test_invalid_utf8_in_the_source(self):
        path = self.write("p.asm", b".ORIG x3000\n; \xFF\xFE\nHALT\n")
        result = self.cli(path)
        self.assertEqual((result.code, result.out), (3, ""))
        self.assertIn("no es UTF-8 válido", result.err)
        self.assertIn("byte 14", result.err)
        self.assertFalse((self.directory / "p.bin").exists())

    def test_other_encodings_are_rejected(self):
        cases = {"latin1": b".ORIG x3000\n; acentuaci\xF3n\nHALT\n",
                 "utf16": program(".ORIG x3000", "HALT").encode("utf-16"),
                 "truncated": b".ORIG x3000\nHALT\n; \xC3"}
        for name, content in cases.items():
            with self.subTest(name):
                path = self.write(f"{name}.asm", content)
                self.assertEqual(self.cli(path).code, 3)
                self.assertFalse((self.directory / f"{name}.bin").exists())
    def test_invalid_utf8_preserves_a_previous_binary(self):
        path = self.write("p.asm", b"\xFF")
        previous = self.write("p.bin", b"anterior")
        self.assertEqual(self.cli(path).code, 3)
        self.assertEqual(Path(previous).read_bytes(), b"anterior")

    def test_an_empty_source_is_an_assembly_error_not_a_read_error(self):
        path = self.write("vacio.asm", b"")
        result = self.cli(path)
        self.assertEqual(result.code, 4)
        self.assertIn("falta la directiva .ORIG", result.err)

    def test_unreachable_source_paths(self):
        parent = self.write("archivo", b"x")
        for path in (parent + "/p.asm", ""):
            with self.subTest(path=path):
                result = self.cli(path)
                self.assertEqual((result.code, result.out), (3, ""))
    def test_an_output_in_a_missing_directory(self):
        path = self.write("p.asm", self.SOURCE)
        result = self.cli(path, "-o", str(self.directory / "no_existe" / "p.bin"))
        self.assertEqual((result.code, result.out), (5, ""))
        self.assertIn("error: no se pudo escribir el binario", result.err)
        self.assertNotIn("Traceback", result.err)
        self.assertNotIn("Resumen", result.err)
        self.assertEqual(self.listing(), ["p.asm"])           # no se creó ningún directorio

    def test_an_output_that_is_a_directory(self):
        path = self.write("p.asm", self.SOURCE)
        target = self.directory / "salida"
        target.mkdir()
        result = self.cli(path, "-o", str(target))
        self.assertEqual((result.code, result.out), (5, ""))
        self.assertTrue(target.is_dir())
        self.assertNotIn("Resumen", result.err)

    def test_an_output_whose_parent_is_a_file(self):
        path = self.write("p.asm", self.SOURCE)
        blocker = self.write("archivo", b"x")
        self.assertEqual(self.cli(path, "-o", blocker + "/p.bin").code, 5)
        self.assertEqual(Path(blocker).read_bytes(), b"x")

    @unittest.skipUnless(os.path.exists("/dev/full"), "requiere /dev/full (Linux)")
    def test_a_full_disk_is_a_write_error(self):
        path = self.write("p.asm", self.SOURCE)
        result = self.cli(path, "-o", "/dev/full")
        self.assertEqual((result.code, result.out), (5, ""))
        self.assertIn("No space left", result.err)
        self.assertNotIn("Resumen", result.err)

    def test_a_write_failure_reports_the_system_reason(self):
        path = self.write("p.asm", self.SOURCE)
        failure = PermissionError(13, "Permission denied")
        with mock.patch.object(cli_module, "write_binary", side_effect=failure):
            result = self.cli(path)
        self.assertEqual((result.code, result.out), (5, ""))
        self.assertIn("Permission denied", result.err)

    @unittest.skipUnless(CAN_USE_PERMISSIONS, PERMISSIONS_REASON)
    def test_a_source_without_read_permission(self):
        path = self.write("p.asm", self.SOURCE)
        os.chmod(path, 0)
        self.addCleanup(os.chmod, path, 0o644)
        result = self.cli(path)
        self.assertEqual((result.code, result.out), (3, ""))
        self.assertIn("error: no se pudo leer el fuente", result.err)
        self.assertFalse((self.directory / "p.bin").exists())

    @unittest.skipUnless(CAN_USE_PERMISSIONS, PERMISSIONS_REASON)
    def test_a_read_only_output_file_is_a_write_error_and_stays_intact(self):
        path = self.write("p.asm", self.SOURCE)
        target = self.write("p.bin", b"intacto")
        os.chmod(target, 0o444)
        self.addCleanup(os.chmod, target, 0o644)
        result = self.cli(path)
        self.assertEqual((result.code, result.out), (5, ""))
        self.assertEqual(Path(target).read_bytes(), b"intacto")

    @unittest.skipUnless(CAN_USE_PERMISSIONS, PERMISSIONS_REASON)
    def test_an_output_directory_without_write_permission(self):
        path = self.write("p.asm", self.SOURCE)
        locked = self.directory / "locked"
        locked.mkdir()
        os.chmod(locked, 0o555)
        self.addCleanup(os.chmod, locked, 0o755)
        result = self.cli(path, "-o", str(locked / "p.bin"))
        self.assertEqual((result.code, result.out), (5, ""))
        self.assertEqual(list(locked.iterdir()), [])

    # --- el fuente nunca se sobrescribe ---------------------------------
    def assertSourceProtected(self, source_path, *argv, expected_content=None):
        content = Path(source_path).read_bytes() if expected_content is None else expected_content
        before = self.listing()
        result = self.cli(*argv)
        self.assertEqual((result.code, result.out), (2, ""), result.err)
        self.assertIn("propio archivo fuente", result.err)
        self.assertEqual(Path(source_path).read_bytes(), content)
        self.assertEqual(self.listing(), before)
        self.assertNotIn("Resumen", result.err)

    def test_the_output_cannot_be_the_source_itself(self):
        path = self.write("p.asm", self.SOURCE)
        self.assertSourceProtected(path, path, "-o", path)

    def test_the_default_output_cannot_be_the_source(self):
        # Un fuente llamado .bin: la salida por defecto sería el propio fuente.
        path = self.write("p.bin", self.SOURCE)
        self.assertSourceProtected(path, path)

    def test_relative_absolute_and_dot_slash_spellings_of_the_same_file(self):
        path = self.write("p.asm", self.SOURCE)
        with working_directory(self.directory):
            self.assertSourceProtected(path, "p.asm", "-o", path)
            self.assertSourceProtected(path, path, "-o", "p.asm")
            self.assertSourceProtected(path, "p.asm", "-o", "./p.asm")
            self.assertSourceProtected(path, "./p.asm", "-o", "p.asm")
    def test_dot_dot_segments_and_redundant_separators(self):
        path = self.write("sub/p.asm", self.SOURCE)
        (self.directory / "other").mkdir()
        sneaky = str(self.directory / "other" / ".." / "sub" / "." / "p.asm")
        self.assertSourceProtected(path, path, "-o", sneaky)
        self.assertSourceProtected(path, sneaky, "-o", path)
        self.assertSourceProtected(path, path, "-o", str(self.directory) + "//sub//p.asm")

    def test_a_symbolic_link_to_the_source_as_the_output(self):
        path = self.write("p.asm", self.SOURCE)
        link = self.directory / "enlace.bin"
        self.make_symlink(path, link)
        self.assertSourceProtected(path, path, "-o", str(link))

    def test_the_source_given_through_a_symbolic_link(self):
        path = self.write("p.asm", self.SOURCE)
        link = self.directory / "enlace.asm"
        self.make_symlink(path, link)
        self.assertSourceProtected(path, str(link), "-o", path)

    def test_a_chain_of_symbolic_links(self):
        path = self.write("p.asm", self.SOURCE)
        first, second = self.directory / "uno", self.directory / "dos"
        self.make_symlink(path, first)
        self.make_symlink(first, second)
        self.assertSourceProtected(path, path, "-o", str(second))

    def test_a_symbolic_link_to_the_directory_of_the_source(self):
        path = self.write("real/p.asm", self.SOURCE)
        alias = self.directory / "alias"
        self.make_symlink(self.directory / "real", alias)
        self.assertSourceProtected(path, path, "-o", str(alias / "p.asm"))

    def test_a_hard_link_to_the_source_as_the_output(self):
        path = self.write("p.asm", self.SOURCE)
        link = self.directory / "duro.bin"
        try:
            os.link(path, link)
        except (OSError, NotImplementedError, AttributeError):
            self.skipTest("este sistema no permite crear enlaces duros")
        self.assertSourceProtected(path, path, "-o", str(link))

    def test_the_resolved_paths_are_compared_even_when_the_source_does_not_exist(self):
        # Sin fuente, os.path.samefile no puede decidir: deben bastar las rutas resueltas.
        with working_directory(self.directory):
            for source, output in (("p.asm", "p.asm"), ("p.asm", "./p.asm"),
                                   ("p.asm", str(self.directory / "p.asm")),
                                   ("sub/../p.asm", "p.asm")):
                with self.subTest(source=source, output=output):
                    result = self.cli(source, "-o", output)
                    self.assertEqual((result.code, result.out), (2, ""))
                    self.assertIn("propio archivo fuente", result.err)
        self.assertEqual(self.listing(), [])

    def test_a_dangling_symbolic_link_as_the_source_is_resolved_to_its_target(self):
        link = self.directory / "enlace.asm"
        self.make_symlink(self.directory / "falta.asm", link)
        result = self.cli(str(link), "-o", str(self.directory / "falta.asm"))
        self.assertEqual((result.code, result.out), (2, ""))
        self.assertFalse((self.directory / "falta.asm").exists())

    def test_the_protection_runs_before_the_source_is_read_or_assembled(self):
        for name, content in (("bad_utf8.asm", b"\xFF\xFE not utf-8"), ("bad_syntax.asm", b"FOO\n")):
            with self.subTest(name):
                path = self.write(name, content)
                self.assertSourceProtected(path, path, "-o", path)
    def test_the_protection_never_calls_the_assembler_or_the_writer(self):
        path = self.write("p.asm", self.SOURCE)
        with mock.patch.object(cli_module, "assemble") as assembler, \
                mock.patch.object(cli_module, "write_binary") as writer:
            self.assertEqual(self.cli(path, "-o", path).code, 2)
        assembler.assert_not_called()
        writer.assert_not_called()

    def test_a_different_file_in_the_same_directory_is_not_confused_with_the_source(self):
        path = self.write("p.asm", self.SOURCE)
        self.write("p.asm.bin", b"x")
        result = self.cli(path, "-o", str(self.directory / "p.asm.bin"))
        self.assertEqual(result.code, 0, result.err)
        self.assertEqual(Path(path).read_bytes(), self.SOURCE.encode())

    def test_a_symbolic_link_to_another_binary_is_not_mistaken_for_the_source(self):
        path = self.write("p.asm", self.SOURCE)
        target = self.write("real.bin", b"viejo")
        link = self.directory / "enlace.bin"
        self.make_symlink(target, link)
        result = self.cli(path, "-o", str(link))
        self.assertEqual(result.code, 0, result.err)
        self.assertEqual(Path(target).read_bytes(), b"\x00\x30" + words(HALT))
        self.assertEqual(Path(path).read_bytes(), self.SOURCE.encode())


# ----------------------------------------------------------------------
# Símbolos externos
# ----------------------------------------------------------------------
class TestExternalSymbols(CliTestCase):
    FILL_BUF = program(".ORIG x3000", ".EXTERNAL BUF", ".FILL BUF")

    def test_hexadecimal_notations(self):
        for value, expected in (("x3100", 0x3100), ("0x3100", 0x3100), ("X3100", 0x3100),
                                ("0X3100", 0x3100), ("xAbCd", 0xABCD)):
            with self.subTest(value=value):
                self.assertEqual(self.assemble_ok(self.FILL_BUF, "--external", f"BUF={value}"),
                                 b"\x00\x30" + words(expected))
    def test_decimal_notation(self):
        # 12544 = 0x3100; los ceros a la izquierda no la vuelven octal ni hexadecimal
        for value, expected in (("12544", 0x3100), ("0010", 10)):
            with self.subTest(value=value):
                self.assertEqual(self.assemble_ok(self.FILL_BUF, "--external", f"BUF={value}"),
                                 b"\x00\x30" + words(expected))
    def test_the_address_limits(self):
        for value, expected in (("0", 0), ("x0000", 0), ("xFFFF", 0xFFFF), ("65535", 0xFFFF)):
            with self.subTest(value=value):
                self.assertEqual(self.assemble_ok(self.FILL_BUF, "--external", f"BUF={value}"),
                                 b"\x00\x30" + words(expected))

    def test_several_externals(self):
        text = program(".ORIG x3000", ".EXTERNAL BUFFER", ".EXTERNAL ROUTINE", ".FILL BUFFER",
                       ".FILL ROUTINE")
        data = self.assemble_ok(text, "--external", "BUFFER=x3100", "--external",
                                "ROUTINE=0x3200")
        self.assertEqual(data, b"\x00\x30" + words(0x3100, 0x3200))

    def test_externals_used_by_jsr_lea_and_br_are_encoded_pc_relative(self):
        cases = (
            # JSR en x3000: PC siguiente x3002; (x3200 - x3002) / 2 = 255 palabras
            ("JSR SYM", "SYM=x3200", 0x88FF),
            # LEA en x3000: PC siguiente x3002; x3010 - x3002 = 14 bytes
            ("LEA R0, SYM", "SYM=x3010", 0x980E),
            # BR en x3000: (x3004 - x3002) / 2 = +1 palabra
            ("BR SYM", "SYM=x3004", 0x8701),
        )
        for line, declaration, word in cases:
            with self.subTest(line):
                text = program(".ORIG x3000", ".EXTERNAL SYM", line, "HALT")
                self.assertEqual(self.assemble_ok(text, "--external", declaration,
                                                  name=f"x{word:04X}.asm"),
                                 b"\x00\x30" + words(word, HALT))
    def test_externals_mix_with_local_labels(self):
        text = program(".ORIG x3000", ".EXTERNAL EXT", "HERE: .FILL EXT", ".FILL HERE")
        self.assertEqual(self.assemble_ok(text, "--external", "EXT=x5000"),
                         b"\x00\x30" + words(0x5000, 0x3000))

    def test_whitespace_around_the_name_and_address_is_ignored(self):
        self.assertEqual(self.assemble_ok(self.FILL_BUF, "--external", "  BUF = x3100  "),
                         b"\x00\x30" + words(0x3100))

    def test_a_declared_external_that_is_never_used_does_not_need_an_address(self):
        text = program(".ORIG x3000", ".EXTERNAL UNUSED", "HALT")
        expected = b"\x00\x30" + words(HALT)
        self.assertEqual(self.assemble_ok(text, name="without.asm"), expected)
        self.assertEqual(self.assemble_ok(text, "--external", "UNUSED=x1234", name="with.asm"),
                         expected)
    def test_a_used_external_without_an_address_is_an_error_with_its_line(self):
        path, result = self.assemble_fails(self.FILL_BUF)
        self.assertIn(f"{path}:3: error:", result.err)
        self.assertIn("'BUF' no tiene una dirección válida", result.err)

    def test_an_address_for_a_symbol_not_declared_with_external(self):
        text = program(".ORIG x3000", "HALT")
        path, result = self.assemble_fails(text, "--external", "BUFFER=x3100")
        self.assertIn(f"{path}: error: external_symbols: 'BUFFER' no fue declarado con "
                      f".EXTERNAL", result.err)
        self.assertNotRegex(result.err, r"\.asm:\d+")

    def test_names_are_case_sensitive(self):
        path, result = self.assemble_fails(self.FILL_BUF, "--external", "buf=x3100")
        self.assertIn("'buf' no fue declarado", result.err)
        self.assertIn("'BUF' no tiene una dirección válida", result.err)

    def test_an_address_above_xffff_is_rejected_by_the_assembler_not_the_cli(self):
        for index, value in enumerate(("x10000", "0x10000", "65536", "99999999999999999999")):
            with self.subTest(value=value):
                path, result = self.assemble_fails(self.FILL_BUF, "--external", f"BUF={value}",
                                                   name=f"range{index}.asm")
                self.assertIn("debe ser un entero de x0000 a xFFFF", result.err)

    def test_an_external_that_is_also_a_local_label_is_an_error(self):
        for index, text in enumerate((program(".ORIG x3000", "BUF: .FILL BUF"),
                                      program(".ORIG x3000", ".EXTERNAL BUF", "BUF: NOP"))):
            with self.subTest(index):
                _, result = self.assemble_fails(text, "--external", "BUF=x3100",
                                                name=f"c{index}.asm")
                self.assertIn("BUF", result.err)
    def test_an_external_that_does_not_reach_with_a_branch(self):
        text = program(".ORIG x3000", ".EXTERNAL FAR", "BR FAR")
        path, result = self.assemble_fails(text, "--external", "FAR=x8000")
        self.assertIn(f"{path}:3: error:", result.err)

    def test_the_dictionary_is_passed_to_assemble_untouched(self):
        path = self.write("p.asm", self.FILL_BUF)
        with mock.patch.object(cli_module, "assemble", wraps=assemble) as assembler:
            self.assertEqual(self.cli(path, "--external", "BUF=x3100").code, 0)
        assembler.assert_called_once()
        self.assertEqual(assembler.call_args.args, (self.FILL_BUF,))
        self.assertEqual(assembler.call_args.kwargs, {"external_symbols": {"BUF": 0x3100}})

    def test_the_cli_forwards_range_and_declaration_problems_to_the_assembler(self):
        path = self.write("p.asm", self.FILL_BUF)
        with mock.patch.object(cli_module, "assemble", wraps=assemble) as assembler:
            self.assertEqual(self.cli(path, "--external", "BUF=x10000").code, 4)
            self.assertEqual(self.cli(path, "--external", "NOPE=1").code, 4)
            self.assertEqual(self.cli(path).code, 4)
        mappings = [call.kwargs["external_symbols"] for call in assembler.call_args_list]
        self.assertEqual(mappings, [{"BUF": 0x10000}, {"NOPE": 1}, {}])
    def test_externals_do_not_leak_between_invocations(self):
        path = self.write("p.asm", self.FILL_BUF)
        self.assertEqual(self.cli(path, "--external", "BUF=x3100").code, 0)
        self.assertEqual(self.cli(path).code, 4)


# ----------------------------------------------------------------------
# Integración con el loader y el simulador
# ----------------------------------------------------------------------
class TestIntegration(CliTestCase):

    def run_binary(self, path, **kwargs):
        return run_program(read_binary(path), **kwargs)

    def test_the_binary_is_read_by_the_loader(self):
        path = self.write("p.asm", program(".ORIG x3000", "ADD R0, R0, #1", "HALT"))
        self.assertEqual(self.cli(path).code, 0)
        loaded = read_binary(self.directory / "p.bin")
        self.assertEqual(loaded.origin, 0x3000)
        self.assertEqual(loaded.data, words(ADD_R0_R0_1, HALT))

    def test_the_loader_gets_the_origin_of_a_different_program(self):
        path = self.write("p.asm", program(".ORIG x4000", "HALT"))
        self.assertEqual(self.cli(path).code, 0)
        self.assertEqual(read_binary(self.directory / "p.bin").origin, 0x4000)

    def test_a_loop_runs_to_halt_with_the_expected_registers(self):
        text = program(".ORIG x3000", "ADD R0, R0, #5", "ADD R1, R1, #3",
                       "LOOP: ADD R0, R0, #1", "SUB R1, R1, #1", "BRp LOOP", "HALT")
        path = self.write("loop.asm", text)
        self.assertEqual(self.cli(path).code, 0)
        result = self.run_binary(self.directory / "loop.bin")
        self.assertEqual(result.status, RunStatus.HALTED)
        self.assertEqual(result.halt_reason, "HALT")
        self.assertEqual(result.registers[0], 8)            # 5 + 3 iteraciones
        self.assertEqual(result.registers[1], 0)
        self.assertEqual(result.instruction_count, 2 + 3 * 3 + 1)

    def test_a_program_prints_its_string(self):
        text = program(".ORIG x3000", "LEA R0, MSG", "TRAP x22", "HALT", 'MSG: .STRINGZ "Hola"')
        path = self.write("hola.asm", text)
        self.assertEqual(self.cli(path).code, 0)
        result = self.run_binary(self.directory / "hola.bin")
        self.assertEqual((result.status, result.output), (RunStatus.HALTED, "Hola"))

    def test_padding_and_negative_lea_offsets_work_when_executed(self):
        text = program(".ORIG x3000", "BR START", 'MSG: .STRINGZ "ab"', "START: LEA R0, MSG",
                       "TRAP x22", "HALT")
        data = self.assemble_ok(text, name="pad.asm")
        # BR +2 palabras | "ab\0" | relleno | LEA -6 bytes | TRAP x22 | HALT
        self.assertEqual(data, b"\x00\x30" + words(0x8702) + b"ab\x00\x00"
                         + words(0x98FA, TRAP_PUTS, HALT))
        result = self.run_binary(self.directory / "pad.bin")
        self.assertEqual((result.status, result.output), (RunStatus.HALTED, "ab"))

    def test_a_subroutine_call_and_return(self):
        text = program(".ORIG x3000", "JSR DOUBLE", "HALT", "DOUBLE: ADD R0, R0, #4",
                       "JMP LR")
        path = self.write("sub.asm", text)
        self.assertEqual(self.cli(path).code, 0)
        result = self.run_binary(self.directory / "sub.bin")
        self.assertEqual(result.status, RunStatus.HALTED)
        self.assertEqual(result.registers[0], 4)

    def test_memory_access_through_a_data_label(self):
        text = program(".ORIG x3000", "LEA R1, VALUE", "LDW R0, R1, #0", "HALT",
                       "VALUE: .FILL x1234")
        path = self.write("mem.asm", text)
        self.assertEqual(self.cli(path).code, 0)
        result = self.run_binary(self.directory / "mem.bin")
        self.assertEqual(result.status, RunStatus.HALTED)
        self.assertEqual(result.registers[0], 0x1234)

    def test_an_external_address_reaches_the_running_program(self):
        text = program(".ORIG x3000", "LEA R1, PTR", "LDW R0, R1, #0", "HALT",
                       ".EXTERNAL BUF", "PTR: .FILL BUF")
        path = self.write("ext.asm", text)
        self.assertEqual(self.cli(path, "--external", "BUF=x3100").code, 0)
        result = self.run_binary(self.directory / "ext.bin")
        self.assertEqual(result.status, RunStatus.HALTED)
        self.assertEqual(result.registers[0], 0x3100)

    def test_the_simulator_cli_runs_the_binary(self):
        text = program(".ORIG x3000", "LEA R0, MSG", "TRAP x22", "HALT", 'MSG: .STRINGZ "Hola"')
        path = self.write("hola.asm", text)
        self.assertEqual(self.cli(path).code, 0)
        out, err = io.StringIO(), io.StringIO()
        code = simulator_cli.main([str(self.directory / "hola.bin")], stdin=io.StringIO(),
                                  stdout=out, stderr=err)
        self.assertEqual((code, out.getvalue()), (0, "Hola"))
        self.assertIn("HALTED (HALT)", err.getvalue())

    def test_a_custom_output_in_another_directory_also_runs(self):
        (self.directory / "build").mkdir()
        path = self.write("p.asm", program(".ORIG x3000", "ADD R0, R0, #1", "HALT"))
        target = self.directory / "build" / "p.bin"
        self.assertEqual(self.cli(path, "-o", str(target)).code, 0)
        self.assertEqual(self.run_binary(target).registers[0], 1)

    def test_a_program_without_halt_hits_the_instruction_limit(self):
        path = self.write("loop.asm", program(".ORIG x3000", "LOOP: BR LOOP"))
        self.assertEqual(self.cli(path).code, 0)
        result = self.run_binary(self.directory / "loop.bin", max_steps=10)
        self.assertEqual(result.status, RunStatus.INSTRUCTION_LIMIT)


# ----------------------------------------------------------------------
# Ejecución real: python3 -m assembler
# ----------------------------------------------------------------------
class TestRealProcess(CliTestCase):
    SOURCE = program(".ORIG x3000", "LEA R0, MSG", "TRAP x22", "HALT", 'MSG: .STRINGZ "Hola"')

    @staticmethod
    def environment(extra=None):
        env = dict(os.environ)
        env["PYTHONIOENCODING"] = "utf-8"
        existing = env.get("PYTHONPATH")
        env["PYTHONPATH"] = str(PROJECT_ROOT) + (os.pathsep + existing if existing else "")
        env.update(extra or {})
        return env

    def run_module(self, module, *args, cwd=None, env_extra=None):
        return subprocess.run([sys.executable, "-B", "-m", module, *args],
                              cwd=cwd or PROJECT_ROOT, env=self.environment(env_extra),
                              stdin=subprocess.DEVNULL, capture_output=True, timeout=60)

    def test_a_successful_run_creates_the_binary(self):
        path = self.write("programa.asm", self.SOURCE)
        completed = self.run_module("assembler", path)
        self.assertEqual((completed.returncode, completed.stdout), (0, b""))
        self.assertIn("Resumen del ensamblado", completed.stderr.decode())
        self.assertEqual((self.directory / "programa.bin").read_bytes(),
                         b"\x00\x30" + words(0x9804, TRAP_PUTS, HALT) + b"Hola\x00")

    def test_a_relative_source_from_another_working_directory(self):
        self.write("programa.asm", self.SOURCE)
        completed = self.run_module("assembler", "programa.asm", cwd=self.directory)
        self.assertEqual((completed.returncode, completed.stdout), (0, b""))
        self.assertTrue((self.directory / "programa.bin").exists())

    def test_a_custom_output(self):
        path = self.write("programa.asm", self.SOURCE)
        (self.directory / "build").mkdir()
        completed = self.run_module("assembler", path, "-o", str(self.directory / "build" / "x.bin"))
        self.assertEqual(completed.returncode, 0)
        self.assertTrue((self.directory / "build" / "x.bin").exists())
        self.assertFalse((self.directory / "programa.bin").exists())

    def test_the_exit_status_of_the_process_is_the_code_returned_by_main(self):
        good = self.write("good.asm", self.SOURCE)
        bad = self.write("bad.asm", "FOO\n")
        cases = ((2, ["--bogus"]),
                 (3, [str(self.directory / "missing.asm")]),
                 (4, [bad]),
                 (5, [good, "-o", str(self.directory / "no_dir" / "o.bin")]),
                 (2, [good, "-o", good]))
        for expected, args in cases:
            with self.subTest(expected=expected, args=args):
                completed = self.run_module("assembler", *args)
                self.assertEqual((completed.returncode, completed.stdout), (expected, b""))
                self.assertNotIn(b"Traceback", completed.stderr)

    def test_help(self):
        completed = self.run_module("assembler", "--help")
        self.assertEqual((completed.returncode, completed.stderr), (0, b""))
        self.assertIn("--external", completed.stdout.decode())

    def test_usage_errors(self):
        completed = self.run_module("assembler")
        self.assertEqual((completed.returncode, completed.stdout), (2, b""))
        self.assertIn("usage", completed.stderr.decode().lower())

    def test_assembly_errors_go_to_stderr_without_a_traceback(self):
        path = self.write("bad.asm", "FOO\n")
        completed = self.run_module("assembler", path)
        self.assertEqual((completed.returncode, completed.stdout), (4, b""))
        self.assertIn("mnemónico desconocido", completed.stderr.decode())
        self.assertNotIn(b"Traceback", completed.stderr)

    def test_an_unencodable_stderr_does_not_produce_a_traceback(self):
        path = self.write("bad.asm", ".ORIG x3000\nFOO é\n")
        for target in ("ascii", "latin-1"):
            with self.subTest(encoding=target):
                completed = self.run_module("assembler", path,
                                            env_extra={"PYTHONIOENCODING": target})
                self.assertEqual(completed.returncode, 4)
                self.assertNotIn(b"Traceback", completed.stderr)

    def test_help_and_usage_survive_an_ascii_terminal(self):
        for args, expected in (((("--help",)), 0), (("--bogus",), 2)):
            with self.subTest(args=args):
                completed = self.run_module("assembler", *args,
                                            env_extra={"PYTHONIOENCODING": "ascii"})
                self.assertEqual(completed.returncode, expected)
                self.assertNotIn(b"Traceback", completed.stderr)

    def test_importing_the_module_does_not_run_the_cli(self):
        completed = subprocess.run([sys.executable, "-B", "-c", "import assembler.__main__"],
                                   cwd=PROJECT_ROOT, stdin=subprocess.DEVNULL,
                                   capture_output=True, timeout=60)
        self.assertEqual((completed.returncode, completed.stdout, completed.stderr), (0, b"", b""))

    def test_the_binary_runs_in_the_simulator_process(self):
        path = self.write("programa.asm", self.SOURCE)
        self.assertEqual(self.run_module("assembler", path).returncode, 0)
        completed = self.run_module("simulator", str(self.directory / "programa.bin"))
        self.assertEqual((completed.returncode, completed.stdout), (0, b"Hola"))
        self.assertIn("HALTED (HALT)", completed.stderr.decode())

    @unittest.skipIf(os.name == "nt" or shutil.which("sh") is None, "requiere un shell POSIX")
    def test_the_shell_pipeline_assembler_then_simulator(self):
        path = self.write("programa.asm", self.SOURCE)
        command = ('"$0" -B -m assembler "$1" && "$0" -B -m simulator "$2"')
        completed = subprocess.run(
            ["sh", "-c", command, sys.executable, path, str(self.directory / "programa.bin")],
            cwd=PROJECT_ROOT, env=self.environment(), stdin=subprocess.DEVNULL,
            capture_output=True, timeout=60)
        self.assertEqual((completed.returncode, completed.stdout), (0, b"Hola"))
        self.assertIn(b"Resumen del ensamblado", completed.stderr)
        self.assertIn(b"Resumen de la simulaci", completed.stderr)

    def test_a_failed_assembly_stops_the_pipeline_and_leaves_the_old_binary_alone(self):
        path = self.write("programa.asm", "FOO\n")
        stale = self.write("programa.bin", b"\x00\x30" + words(HALT))
        command = ('"$0" -B -m assembler "$1" && "$0" -B -m simulator "$2"')
        completed = subprocess.run(
            ["sh", "-c", command, sys.executable, path, stale],
            cwd=PROJECT_ROOT, env=self.environment(), stdin=subprocess.DEVNULL,
            capture_output=True, timeout=60)
        self.assertEqual((completed.returncode, completed.stdout), (4, b""))
        self.assertNotIn(b"Resumen de la simulaci", completed.stderr)
        self.assertEqual(Path(stale).read_bytes(), b"\x00\x30" + words(HALT))


# ----------------------------------------------------------------------
# Independencia y calidad del módulo
# ----------------------------------------------------------------------
class TestModuleStructure(unittest.TestCase):

    @staticmethod
    def source():
        return Path(cli_module.__file__).read_text(encoding="utf-8")

    def tree(self):
        return ast.parse(self.source())

    def imported_modules(self):
        imported = set()
        for node in ast.walk(self.tree()):
            if isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)
            elif isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
        return imported

    def test_the_package_init_is_empty(self):
        init = PROJECT_ROOT / "assembler" / "__init__.py"
        self.assertTrue(init.is_file())
        self.assertEqual(init.read_bytes(), b"")

    def test_the_cli_only_uses_the_existing_assembler_modules(self):
        project = {name for name in self.imported_modules()
                   if name.startswith(("simulator", "assembler"))}
        self.assertEqual(project, {"assembler.assembler", "assembler.encoder",
                                   "assembler.parser", "assembler.symbols",
                                   "assembler.writer"})

    def test_exceptions_are_handled_specifically_and_never_broadly(self):
        handled = set()
        for node in ast.walk(self.tree()):
            if isinstance(node, ast.ExceptHandler):
                self.assertIsNotNone(node.type, "except desnudo")
                types = node.type.elts if isinstance(node.type, ast.Tuple) else [node.type]
                handled.update(item.id for item in types)
        self.assertNotIn("Exception", handled)
        self.assertNotIn("BaseException", handled)
        self.assertEqual(handled, {"SystemExit", "OSError", "UnicodeDecodeError",
                                   "UnicodeEncodeError", "ValueError", "ASSEMBLY_ERRORS"})

    def test_the_cli_never_opens_a_file_for_writing_itself(self):
        opens = [node for node in ast.walk(self.tree()) if isinstance(node, ast.Call)
                 and getattr(node.func, "id", None) == "open"]
        self.assertEqual(len(opens), 1)                     # solo la lectura del fuente
        self.assertEqual(opens[0].args[1].value, "rb")
        source = self.source()
        for forbidden in ("write_bytes", "write_text", ".replace(", "os.rename", "os.remove",
                          "os.unlink", "shutil"):
            self.assertNotIn(forbidden, source)

    def test_the_opcode_table_is_not_duplicated(self):
        source = self.source()
        for forbidden in ("INSTRUCTIONS", "parse_program", "build_symbol_table",
                          "encode_program", "serialize_binary", "to_bytes"):
            self.assertNotIn(forbidden, source)

    def test_the_process_ends_with_system_exit_of_main(self):
        guards = [node for node in self.tree().body if isinstance(node, ast.If)
                  and isinstance(node.test, ast.Compare)
                  and getattr(node.test.left, "id", None) == "__name__"
                  and [c.value for c in node.test.comparators] == ["__main__"]]
        self.assertEqual(len(guards), 1)
        statement = guards[0].body[0]
        self.assertIsInstance(statement, ast.Raise)
        self.assertEqual(statement.exc.func.id, "SystemExit")
        self.assertEqual(statement.exc.args[0].func.id, "main")

    def test_the_main_signature(self):
        parameters = inspect.signature(main).parameters
        self.assertEqual(list(parameters), ["argv", "stdout", "stderr"])
        self.assertEqual(parameters["argv"].kind, inspect.Parameter.POSITIONAL_OR_KEYWORD)
        for name in ("stdout", "stderr"):
            self.assertEqual(parameters[name].kind, inspect.Parameter.KEYWORD_ONLY)
        for name in parameters:
            self.assertIsNone(parameters[name].default)

    def test_the_public_api(self):
        self.assertEqual(cli_module.__all__, ["main"])

    def test_the_exit_code_constants(self):
        self.assertEqual((cli_module.EXIT_OK, cli_module.EXIT_USAGE, cli_module.EXIT_READ,
                          cli_module.EXIT_ASSEMBLY, cli_module.EXIT_WRITE), (0, 2, 3, 4, 5))

    def test_the_module_and_its_tests_are_compatible_with_python_3_10(self):
        for text in (self.source(), Path(__file__).read_text(encoding="utf-8")):
            ast.parse(text, feature_version=(3, 10))      # falla ante sintaxis posterior


if __name__ == "__main__":
    unittest.main()
