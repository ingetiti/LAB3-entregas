"""Pruebas de la CLI del simulador, simulator/__main__.py (ejecutar desde la raíz Lab3C).

La mayoría corre EN PROCESO: se llama a main(argv, stdin=..., stdout=..., stderr=...) con
flujos en memoria, lo que es rápido y no depende de la terminal. Unas pocas usan
subprocess para comprobar el cableado real de `python3 -m simulator` (siempre con
stdin=DEVNULL o con una tubería explícita, y con timeout, para que nada pueda bloquearse).

Los programas son BYTES escritos a mano (palabras de 16 bits en Little Endian) dentro de
un archivo formato B: dos bytes de origen (x3000 = 00 30) más las instrucciones. Se crean en
un directorio temporal: no hay archivos externos. Ninguna expectativa se calcula con el
código que se prueba.

Referencia de codificación:
  ADD R0,R0,#1 = 0x0011   HALT = 0xC000   NOP = 0xB800   TRAP xNN = 0xB000 | NN << 3
  LEA Rd,#N    = 10011_ddd_NNNNNNNN (offset en BYTES desde el PC siguiente)
  BR #N        = 10000_111_NNNNNNNN (offset en palabras desde el PC siguiente)
"""

import ast
import inspect
import io
import os
import subprocess
import sys
import tempfile
import unittest
from collections import namedtuple
from pathlib import Path
from unittest import mock

from assembler.assembler import assemble
from assembler.writer import write_binary
from simulator import __main__ as cli_module
from simulator.__main__ import main
from simulator.cpu import DEFAULT_MAX_STEPS
from simulator.loader import LoadedProgram, read_binary
from simulator.runner import run_program

PROJECT_ROOT = Path(__file__).resolve().parent.parent

ORIGIN = b"\x00\x30"           # origen x3000, Little Endian
ADD_R0_1 = b"\x11\x00"         # ADD R0,R0,#1 = 0x0011
ADD_R1_1 = b"\x31\x01"         # ADD R1,R1,#1 = 0x0131
ADD_R1_M1 = b"\x3F\x01"        # ADD R1,R1,#-1 = 0x013F
ADD_R1_3 = b"\x33\x01"         # ADD R1,R1,#3 = 0x0133
SUB_R1_1 = b"\x31\x09"         # SUB R1,R1,#1 = 0x0931
BRP_BACK_2 = b"\xFE\x81"       # BRp #-2 = 0x81FE
HALT = b"\x00\xC0"             # 0xC000
NOP = b"\x00\xB8"              # 0xB800
GETC = b"\x00\xB1"             # TRAP x20
OUT = b"\x08\xB1"              # TRAP x21
PUTS = b"\x10\xB1"             # TRAP x22
TRAP_X23 = b"\x18\xB1"         # TRAP x23 (sin servicio)
TRAP_X25 = b"\x28\xB1"         # TRAP x25 (HALT por TRAP)
BR_SELF = b"\xFF\x87"          # BR #-1 = 0x87FF
BR_BACK_3 = b"\xFD\x87"        # BR #-3 = 0x87FD
JMP_R1 = b"\x00\x91"           # JMP R1 = 0x9100
LDW_R0_R1 = b"\x20\x50"        # LDW R0,R1,#0 = 0x5020
LEA_R0_4 = b"\x04\x98"         # LEA R0,#4 = 0x9804
LEA_R0_6 = b"\x06\x98"         # LEA R0,#6 = 0x9806
LEA_R0_70 = b"\x46\x98"        # LEA R0,#70 = 0x9846 -> R0 = PC siguiente + 70
RESERVED_OPCODE = b"\x00\xD0"  # 0xD000
RESERVED_FIELD = b"\x01\x90"   # 0x9001

# Programas reutilizados (sin el origen). Cada uno se comenta con su efecto.
PRINT_HOLA = (LEA_R0_4, PUTS, HALT, b"Hola\x00")           # imprime "Hola": 3 instr., 11 bytes
ECHO = (GETC, OUT, HALT)                                    # GETC -> OUT
COUNTING_LOOP = (ADD_R1_3, SUB_R1_1, BRP_BACK_2, HALT)      # exactamente 8 instrucciones

CliResult = namedtuple("CliResult", "code out err")


def binary(*chunks, origin=ORIGIN):
    return origin + b"".join(chunks)


def summary_fields(err):
    """Campos 'Clave: valor' del resumen de stderr (robusto a los espacios de alineación)."""
    fields = {}
    for line in err.splitlines():
        key, separator, value = line.partition(":")
        if separator and key in ("Estado", "Instrucciones", "Memoria escrita", "PC final"):
            fields[key] = value.strip()
    return fields


class ExplodingStdin:
    """Un stdin que falla si alguien lo toca: prueba que NO se lee cuando no corresponde."""

    def read(self, *args):
        raise AssertionError("se leyó el stdin")

    readline = read

    @property
    def buffer(self):
        raise AssertionError("se accedió al buffer del stdin")


class CliTestCase(unittest.TestCase):

    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name)

    def write(self, name, content):
        path = self.directory / name
        path.write_bytes(content)
        return str(path)

    def program(self, *chunks, name="program.bin"):
        return self.write(name, binary(*chunks))

    def cli(self, *argv, stdin=None, stdin_text=""):
        out, err = io.StringIO(), io.StringIO()
        code = main(list(argv), stdin=stdin if stdin is not None else io.StringIO(stdin_text),
                    stdout=out, stderr=err)
        return CliResult(code, out.getvalue(), err.getvalue())

    def assertNothingExecuted(self, *argv, **kwargs):
        """La CLI no debe llegar a ejecutar nada (el runner no se llama)."""
        with mock.patch.object(cli_module, "run_program") as runner:
            result = self.cli(*argv, **kwargs)
        runner.assert_not_called()
        return result


# ----------------------------------------------------------------------
# Ejecución correcta
# ----------------------------------------------------------------------
class TestSuccessfulRun(CliTestCase):

    def test_a_program_that_halts_exits_with_zero(self):
        result = self.cli(self.program(ADD_R0_1, HALT))
        self.assertEqual(result.code, 0)
        self.assertEqual(result.out, "")

    def test_the_summary_reports_state_instructions_memory_and_pc(self):
        fields = summary_fields(self.cli(self.program(ADD_R0_1, HALT)).err)
        self.assertEqual(fields, {"Estado": "HALTED (HALT)", "Instrucciones": "2",
                                  "Memoria escrita": "4 de 65536 bytes", "PC final": "0x3004"})

    def test_a_program_finishing_with_trap_x25(self):
        result = self.cli(self.program(ADD_R0_1, TRAP_X25))
        self.assertEqual(result.code, 0)
        self.assertEqual(summary_fields(result.err)["Estado"], "HALTED (TRAP x25)")

    def test_the_output_of_the_program_is_exact(self):
        result = self.cli(self.program(*PRINT_HOLA))
        self.assertEqual((result.code, result.out), (0, "Hola"))      # sin salto de línea añadido
        self.assertEqual(summary_fields(result.err),
                         {"Estado": "HALTED (HALT)", "Instrucciones": "3",
                          "Memoria escrita": "11 de 65536 bytes", "PC final": "0x3006"})

    def test_a_program_without_output_writes_nothing_to_stdout(self):
        self.assertEqual(self.cli(self.program(HALT)).out, "")

    def test_the_summary_is_always_shown(self):
        for chunks in ((HALT,), PRINT_HOLA, (NOP, HALT)):
            with self.subTest(len(chunks)):
                self.assertIn("Resumen de la simulación", self.cli(self.program(*chunks)).err)

    def test_the_summary_appears_once(self):
        err = self.cli(self.program(*PRINT_HOLA)).err
        self.assertEqual(err.count("Resumen de la simulación"), 1)

    def test_a_nul_character_is_written_verbatim(self):
        # OUT con R0 = 0 escribe el carácter NUL.
        self.assertEqual(self.cli(self.program(OUT, HALT)).out, "\x00")

    def test_characters_between_128_and_255_are_written_as_text(self):
        # La cadena guarda el byte 0xE9; el carácter U+00E9 se escribe como texto.
        self.assertEqual(self.cli(self.program(LEA_R0_4, PUTS, HALT, b"\xE9\x00")).out, "\xE9")

    def test_options_can_come_before_or_after_the_program(self):
        path = self.program(HALT)
        self.assertEqual(self.cli("--max-steps", "5", path).code, 0)
        self.assertEqual(self.cli(path, "--max-steps", "5").code, 0)
        self.assertEqual(self.cli(path, "--max-steps=5").code, 0)


# ----------------------------------------------------------------------
# Separación de stdout y stderr (incluido el salto de línea de cortesía)
# ----------------------------------------------------------------------
class TestStreamSeparation(CliTestCase):

    def test_stdout_contains_exclusively_the_program_output_in_every_scenario(self):
        scenarios = (
            ("halt", self.program(*PRINT_HOLA), []),
            ("limit", self.program(LEA_R0_70, OUT, BR_BACK_3), ["--max-steps", "9"]),
            ("error", self.program(LEA_R0_6, PUTS, TRAP_X23, HALT, b"antes\x00"), []),
        )
        for name, path, extra in scenarios:
            with self.subTest(name):
                result = self.cli(path, *extra)
                for fragment in ("Resumen", "Estado", "Instrucciones", "error", "aviso"):
                    self.assertNotIn(fragment, result.out)
                self.assertIn("Resumen de la simulación", result.err)

    def test_load_errors_do_not_contaminate_stdout(self):
        result = self.cli(str(self.directory / "missing.bin"))
        self.assertEqual((result.code, result.out), (3, ""))
        self.assertNotEqual(result.err, "")

    def test_a_newline_is_added_to_stderr_only_when_the_output_does_not_end_with_one(self):
        no_newline = self.cli(self.program(*PRINT_HOLA))
        self.assertEqual(no_newline.out, "Hola")
        self.assertTrue(no_newline.err.startswith("\n--- Resumen"))
        with_newline = self.cli(self.program(LEA_R0_4, PUTS, HALT, b"Hola\n\x00"))
        self.assertEqual(with_newline.out, "Hola\n")
        self.assertTrue(with_newline.err.startswith("--- Resumen"))
        no_output = self.cli(self.program(HALT))
        self.assertTrue(no_output.err.startswith("--- Resumen"))

    def test_the_injected_streams_receive_everything_and_the_real_ones_nothing(self):
        real_out, real_err = io.StringIO(), io.StringIO()
        paths = (self.program(*PRINT_HOLA, name="a.bin"),
                 self.program(BR_SELF, name="b.bin"),
                 self.program(NOP, RESERVED_OPCODE, name="c.bin"),
                 str(self.directory / "missing.bin"))
        with mock.patch("sys.stdout", real_out), mock.patch("sys.stderr", real_err):
            for path in paths:
                self.cli(path, "--max-steps", "5")
            self.cli()                                     # error de uso
            self.cli("--help")
        self.assertEqual((real_out.getvalue(), real_err.getvalue()), ("", ""))

    def test_stdout_is_flushed_before_the_summary_is_written(self):
        log = []

        class Recording(io.StringIO):
            def __init__(self, name):
                super().__init__()
                self.name = name

            def write(self, text):
                log.append((self.name, "write"))
                return super().write(text)

            def flush(self):
                log.append((self.name, "flush"))
                super().flush()

        main([self.program(*PRINT_HOLA)], stdin=io.StringIO(""),
             stdout=Recording("out"), stderr=Recording("err"))
        self.assertLess(log.index(("out", "write")), log.index(("out", "flush")))
        self.assertLess(log.index(("out", "flush")), log.index(("err", "write")))


# ----------------------------------------------------------------------
# Límite de instrucciones
# ----------------------------------------------------------------------
class TestInstructionLimit(CliTestCase):

    def test_an_infinite_loop_exits_with_five(self):
        result = self.cli(self.program(BR_SELF), "--max-steps", "10")
        self.assertEqual(result.code, 5)
        self.assertEqual(result.out, "")
        fields = summary_fields(result.err)
        self.assertEqual(fields["Estado"], "INSTRUCTION_LIMIT")
        self.assertEqual(fields["Instrucciones"], "10")
        self.assertEqual(fields["PC final"], "0x3000")

    def test_the_notice_points_to_the_option_that_raises_the_limit(self):
        err = self.cli(self.program(BR_SELF), "--max-steps", "10").err
        self.assertIn("límite de instrucciones", err)
        self.assertIn("--max-steps", err)

    def test_the_exact_limit_boundary_with_a_real_loop(self):
        # El bucle ejecuta exactamente 8 instrucciones: con 8 termina, con 7 no.
        path = self.program(*COUNTING_LOOP)
        finished = self.cli(path, "--max-steps", "8")
        self.assertEqual(finished.code, 0)
        self.assertEqual(summary_fields(finished.err)["Instrucciones"], "8")
        interrupted = self.cli(path, "--max-steps", "7")
        self.assertEqual(interrupted.code, 5)
        self.assertEqual(summary_fields(interrupted.err)["Instrucciones"], "7")

    def test_the_smallest_limit(self):
        self.assertEqual(self.cli(self.program(HALT), "--max-steps", "1").code, 0)
        self.assertEqual(self.cli(self.program(NOP, HALT), "--max-steps", "1").code, 5)

    def test_output_written_before_the_limit_is_kept(self):
        # LEA R0,#70 -> 'H' ; OUT ; BR atrás: tres instrucciones por vuelta, 9 pasos = 3 vueltas.
        result = self.cli(self.program(LEA_R0_70, OUT, BR_BACK_3), "--max-steps", "9")
        self.assertEqual((result.code, result.out), (5, "HHH"))

    def test_the_default_limit_applies_when_the_option_is_omitted(self):
        # Sin HALT el programa cae en ceros y llega al límite por defecto de run_program.
        result = self.cli(self.program(ADD_R0_1))
        self.assertEqual(result.code, 5)
        self.assertEqual(summary_fields(result.err)["Instrucciones"], str(DEFAULT_MAX_STEPS))

    def test_an_empty_program_runs_into_the_limit(self):
        # Archivo con solo el origen: es válido para el loader y la CPU ejecuta ceros.
        result = self.cli(self.write("empty.bin", ORIGIN), "--max-steps", "20")
        self.assertEqual(result.code, 5)
        fields = summary_fields(result.err)
        self.assertEqual((fields["Instrucciones"], fields["Memoria escrita"]),
                         ("20", "0 de 65536 bytes"))


# ----------------------------------------------------------------------
# Errores de ejecución
# ----------------------------------------------------------------------
class TestExecutionErrors(CliTestCase):

    def check(self, chunks, error_type, fragment, instructions, pc):
        result = self.cli(self.program(*chunks))
        self.assertEqual(result.code, 4)
        fields = summary_fields(result.err)
        self.assertEqual(fields["Estado"], "ERROR")
        self.assertEqual(fields["Instrucciones"], str(instructions))
        self.assertEqual(fields["PC final"], f"0x{pc:04X}")
        line = [l for l in result.err.splitlines() if l.startswith("error de ejecución:")]
        self.assertEqual(len(line), 1)
        self.assertIn(error_type, line[0])
        self.assertIn(fragment, line[0])
        return result

    def test_reserved_opcode(self):
        self.check((NOP, RESERVED_OPCODE), "ReservedOpcodeError", "0xD000", 1, 0x3002)

    def test_reserved_field(self):
        self.check((NOP, RESERVED_FIELD), "ReservedFieldError", "0x9001", 1, 0x3002)

    def test_unknown_trap(self):
        self.check((TRAP_X23, HALT), "UnknownTrapError", "x23", 0, 0x3000)

    def test_a_jump_to_an_odd_address(self):
        self.check((ADD_R1_1, JMP_R1, HALT), "MisalignedAddressError", "0x0001", 1, 0x3002)

    def test_a_memory_access_outside_the_address_space(self):
        self.check((ADD_R1_M1, LDW_R0_R1, HALT), "MemoryAccessError", "0xFFFF", 1, 0x3002)

    def test_output_written_before_the_error_is_preserved_in_stdout(self):
        # x3000 LEA R0,#6 -> "antes" ; x3002 PUTS ; x3004 TRAP x23 (falla)
        result = self.check((LEA_R0_6, PUTS, TRAP_X23, HALT, b"antes\x00"),
                            "UnknownTrapError", "x23", 2, 0x3004)
        self.assertEqual(result.out, "antes")
        self.assertNotIn("UnknownTrapError", result.out)

    def test_the_error_message_shows_the_type_and_the_cpu_message(self):
        result = self.cli(self.program(TRAP_X23))
        self.assertIn("error de ejecución: UnknownTrapError:", result.err)


# ----------------------------------------------------------------------
# Errores de archivo o de carga
# ----------------------------------------------------------------------
class TestLoadErrors(CliTestCase):

    def check(self, content_or_path, fragment, name="bad.bin"):
        path = content_or_path if isinstance(content_or_path, str) else self.write(name, content_or_path)
        result = self.assertNothingExecuted(path)
        self.assertEqual(result.code, 3)
        self.assertEqual(result.out, "")
        self.assertIn(path, result.err)
        self.assertIn(fragment, result.err)
        # No hay resumen de una ejecución que nunca ocurrió.
        for absent in ("Resumen", "Instrucciones", "Estado", "PC final"):
            self.assertNotIn(absent, result.err)
        return result

    def test_a_missing_file(self):
        self.check(str(self.directory / "missing.bin"), "error: no se pudo abrir")

    def test_a_directory(self):
        self.check(str(self.directory), "error: no se pudo abrir")

    def test_an_empty_file(self):
        self.check(b"", "vacío")

    def test_a_one_byte_file(self):
        self.check(b"\x30", "incompleto")

    def test_an_odd_origin(self):
        self.check(b"\x01\x30" + HALT, "impar")

    def test_a_program_that_does_not_fit_in_memory(self):
        self.check(b"\xFE\xFF\x01\x02\x03", "no cabe")

    def test_a_file_that_is_too_large(self):
        self.check(bytes(65539), "demasiado grande")

    @unittest.skipIf(os.name == "nt" or (hasattr(os, "geteuid") and os.geteuid() == 0),
                     "los permisos POSIX no se aplican en Windows ni al usuario root")
    def test_a_file_without_read_permission(self):
        path = self.write("secret.bin", binary(HALT))
        os.chmod(path, 0)
        self.addCleanup(os.chmod, path, 0o644)
        self.check(path, "error: no se pudo abrir")

    def test_the_program_is_loaded_before_the_input_file_is_read(self):
        missing_program = str(self.directory / "no_program.bin")
        missing_input = str(self.directory / "no_input.txt")
        result = self.cli(missing_program, "--input-file", missing_input)
        self.assertEqual(result.code, 3)
        self.assertIn("no_program.bin", result.err)
        self.assertNotIn("no_input.txt", result.err)


# ----------------------------------------------------------------------
# Argumentos
# ----------------------------------------------------------------------
class TestArguments(CliTestCase):

    def assertUsageError(self, *argv, fragment=None):
        result = self.assertNothingExecuted(*argv)
        self.assertEqual(result.code, 2)
        self.assertEqual(result.out, "")                     # los errores no van a stdout
        self.assertIn("usage", result.err.lower())
        if fragment is not None:
            self.assertIn(fragment, result.err)
        return result

    def test_no_arguments(self):
        self.assertUsageError(fragment="programa")

    def test_an_additional_file(self):
        self.assertUsageError("a.bin", "b.bin", fragment="b.bin")

    def test_an_unknown_option(self):
        self.assertUsageError("p.bin", "--nope", fragment="--nope")

    def test_max_steps_without_a_value(self):
        self.assertUsageError("p.bin", "--max-steps", fragment="--max-steps")

    def test_invalid_max_steps_values(self):
        for bad in ("abc", "0", "-1", "-100", "1.5", "", "1e3", "diez"):
            with self.subTest(repr(bad)):
                self.assertUsageError("p.bin", "--max-steps", bad, fragment="--max-steps")

    def test_the_input_file_option_requires_a_value(self):
        self.assertUsageError("p.bin", "--input-file", fragment="--input-file")

    def test_the_cli_rejects_the_same_limits_the_runner_rejects(self):
        # Paridad con el runner: lo que la CLI rechaza lo rechazaría también run_program.
        program = LoadedProgram(0x3000, HALT)
        for bad in (0, -1):
            with self.subTest(bad), self.assertRaises(ValueError):
                run_program(program, max_steps=bad)
        self.assertEqual(run_program(program, max_steps=1).status.name, "HALTED")

    def test_help_exits_with_zero_and_writes_to_the_injected_stdout(self):
        for flag in ("--help", "-h"):
            with self.subTest(flag):
                result = self.cli(flag)
                self.assertEqual(result.code, 0)
                self.assertEqual(result.err, "")
                for text in ("usage", "programa", "--max-steps", "--input-file"):
                    self.assertIn(text, result.out)

    def test_help_documents_the_default_limit_without_duplicating_it(self):
        self.assertIn(str(DEFAULT_MAX_STEPS), self.cli("--help").out)

    def test_help_documents_the_exit_codes(self):
        out = self.cli("--help").out
        for line in ("0  ", "2  ", "3  ", "4  ", "5  "):
            self.assertIn(line, out)

    def test_usage_errors_name_the_program_to_run(self):
        self.assertIn("python3 -m simulator", self.cli().err)

    def test_main_returns_the_code_instead_of_exiting(self):
        for argv in ([], ["--help"], ["p.bin", "--max-steps", "0"], ["--nope"]):
            with self.subTest(argv):
                code = main(argv, stdin=io.StringIO(""), stdout=io.StringIO(), stderr=io.StringIO())
                self.assertIs(type(code), int)

    def test_argv_defaults_to_sys_argv(self):
        path = self.program(*PRINT_HOLA)
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(sys, "argv", ["simulator", path]):
            code = main(stdin=io.StringIO(""), stdout=out, stderr=err)
        self.assertEqual((code, out.getvalue()), (0, "Hola"))

    def test_an_explicit_empty_argv_is_not_replaced_by_sys_argv(self):
        with mock.patch.object(sys, "argv", ["simulator", "something.bin"]):
            self.assertEqual(self.cli().code, 2)


# ----------------------------------------------------------------------
# Entrada (GETC)
# ----------------------------------------------------------------------
class TestInput(CliTestCase):

    def test_an_input_file(self):
        result = self.cli(self.program(*ECHO), "--input-file", self.write("in.txt", b"A"))
        self.assertEqual((result.code, result.out), (0, "A"))

    def test_successive_reads_consume_successive_characters(self):
        path = self.program(GETC, OUT, GETC, OUT, HALT)
        result = self.cli(path, "--input-file", self.write("in.txt", b"xy"))
        self.assertEqual(result.out, "xy")

    def test_dash_reads_the_injected_stdin(self):
        result = self.cli(self.program(*ECHO), "--input-file", "-", stdin_text="Q")
        self.assertEqual((result.code, result.out), (0, "Q"))

    def test_dash_reads_utf8_bytes_from_a_binary_backed_stdin(self):
        stdin = io.TextIOWrapper(io.BytesIO(b"Z"), encoding="utf-8")
        self.assertEqual(self.cli(self.program(*ECHO), "--input-file", "-", stdin=stdin).out, "Z")

    def test_without_the_option_getc_receives_eof_and_stdin_is_never_read(self):
        # EOF = 0xFFFF; OUT escribe su byte bajo (0xFF) como el carácter U+00FF.
        result = self.cli(self.program(*ECHO), stdin=ExplodingStdin())
        self.assertEqual((result.code, result.out), (0, "\xFF"))

    def test_the_real_stdin_is_not_read_without_the_option(self):
        with mock.patch("sys.stdin", ExplodingStdin()):
            out, err = io.StringIO(), io.StringIO()
            code = main([self.program(*ECHO)], stdout=out, stderr=err)     # stdin real (parcheado)
        self.assertEqual((code, out.getvalue()), (0, "\xFF"))

    def test_an_empty_input_file_gives_eof(self):
        result = self.cli(self.program(*ECHO), "--input-file", self.write("empty.txt", b""))
        self.assertEqual(result.out, "\xFF")

    def test_the_input_file_is_read_as_utf8(self):
        # "é" en UTF-8 son dos bytes (C3 A9) pero un único carácter U+00E9 para GETC.
        result = self.cli(self.program(*ECHO), "--input-file", self.write("in.txt", "é".encode()))
        self.assertEqual(result.out, "\xE9")

    def test_a_character_wider_than_a_byte_becomes_a_question_mark(self):
        result = self.cli(self.program(*ECHO), "--input-file", self.write("in.txt", "€".encode()))
        self.assertEqual(result.out, "?")

    def test_line_endings_are_not_translated(self):
        path = self.program(GETC, OUT, GETC, OUT, HALT)
        result = self.cli(path, "--input-file", self.write("crlf.txt", b"\r\n"))
        self.assertEqual(result.out, "\r\n")

    def test_a_missing_input_file(self):
        missing = str(self.directory / "missing.txt")
        result = self.assertNothingExecuted(self.program(*ECHO), "--input-file", missing)
        self.assertEqual((result.code, result.out), (3, ""))
        self.assertIn(missing, result.err)
        self.assertIn("entrada", result.err)
        self.assertNotIn("Resumen", result.err)

    def test_an_input_directory(self):
        result = self.assertNothingExecuted(self.program(*ECHO), "--input-file", str(self.directory))
        self.assertEqual(result.code, 3)

    def test_an_input_file_that_is_not_utf8(self):
        bad = self.write("bad.txt", b"\xFF\xFE")
        result = self.assertNothingExecuted(self.program(*ECHO), "--input-file", bad)
        self.assertEqual((result.code, result.out), (3, ""))
        self.assertIn("UTF-8", result.err)
        self.assertIn(bad, result.err)
        self.assertNotIn("Resumen", result.err)

    def test_invalid_utf8_on_stdin_is_a_controlled_error(self):
        stdin = io.TextIOWrapper(io.BytesIO(b"\xFF"), encoding="utf-8")
        result = self.assertNothingExecuted(self.program(*ECHO), "--input-file", "-", stdin=stdin)
        self.assertEqual(result.code, 3)
        self.assertIn("stdin", result.err)
        self.assertIn("UTF-8", result.err)

    def test_the_input_file_is_not_read_if_the_option_is_absent(self):
        self.write("in.txt", b"A")
        self.assertEqual(self.cli(self.program(*ECHO)).out, "\xFF")


# ----------------------------------------------------------------------
# Salida que la terminal no puede representar
# ----------------------------------------------------------------------
class TestOutputEncoding(CliTestCase):

    @staticmethod
    def ascii_stream():
        raw = io.BytesIO()
        return io.TextIOWrapper(raw, encoding="ascii"), raw        # estricto: no admite 'é'

    def test_an_unencodable_program_output_is_replaced_instead_of_crashing(self):
        stdout, raw = self.ascii_stream()
        err = io.StringIO()
        code = main([self.program(LEA_R0_4, PUTS, HALT, b"\xE9\x00")], stdin=io.StringIO(""),
                    stdout=stdout, stderr=err)
        self.assertEqual(code, 0)
        self.assertEqual(raw.getvalue(), b"?")
        self.assertIn("Resumen", err.getvalue())

    def test_unencodable_diagnostics_are_replaced_instead_of_crashing(self):
        stderr, raw = self.ascii_stream()
        out = io.StringIO()
        code = main([self.program(*PRINT_HOLA)], stdin=io.StringIO(""), stdout=out, stderr=stderr)
        self.assertEqual((code, out.getvalue()), (0, "Hola"))
        self.assertIn(b"simulaci?n", raw.getvalue())               # 'ó' no representable

    def test_a_load_error_message_with_non_ascii_characters(self):
        stderr, raw = self.ascii_stream()
        code = main([str(self.directory / "ñandú.bin")], stdin=io.StringIO(""),
                    stdout=io.StringIO(), stderr=stderr)
        self.assertEqual(code, 3)
        self.assertIn(b"error:", raw.getvalue())

    def test_replacement_never_changes_the_exit_code(self):
        stdout, _ = self.ascii_stream()
        stderr, _ = self.ascii_stream()
        code = main([self.program(LEA_R0_4, PUTS, TRAP_X23, b"\xE9\x00")], stdin=io.StringIO(""),
                    stdout=stdout, stderr=stderr)
        self.assertEqual(code, 4)


# ----------------------------------------------------------------------
# Códigos de salida
# ----------------------------------------------------------------------
class TestExitCodeTable(CliTestCase):

    def test_every_scenario_maps_to_its_documented_code(self):
        scenarios = (
            (0, "halt", [self.program(HALT, name="a.bin")]),
            (0, "trap x25", [self.program(TRAP_X25, name="b.bin")]),
            (2, "sin argumentos", []),
            (2, "opción desconocida", ["--nope"]),
            (2, "límite inválido", [self.program(HALT, name="c.bin"), "--max-steps", "0"]),
            (3, "archivo inexistente", [str(self.directory / "missing.bin")]),
            (3, "archivo vacío", [self.write("empty.bin", b"")]),
            (3, "entrada inexistente", [self.program(HALT, name="d.bin"), "--input-file",
                                        str(self.directory / "missing.txt")]),
            (4, "opcode reservado", [self.program(RESERVED_OPCODE, name="e.bin")]),
            (4, "trap desconocido", [self.program(TRAP_X23, name="f.bin")]),
            (5, "límite alcanzado", [self.program(BR_SELF, name="g.bin"), "--max-steps", "3"]),
        )
        observed = set()
        for expected, name, argv in scenarios:
            with self.subTest(name):
                code = self.cli(*argv).code
                self.assertEqual(code, expected)
                observed.add(code)
        self.assertEqual(observed, {0, 2, 3, 4, 5})

    def test_code_one_is_never_used(self):
        # El 1 queda para las excepciones internas no controladas de Python.
        for code in (cli_module.EXIT_OK, cli_module.EXIT_USAGE, cli_module.EXIT_LOAD,
                     cli_module.EXIT_EXECUTION_ERROR, cli_module.EXIT_INSTRUCTION_LIMIT):
            self.assertNotEqual(code, 1)


# ----------------------------------------------------------------------
# Integración Loader + Runner (+ ensamblador y writer solo como generadores de archivos)
# ----------------------------------------------------------------------
class TestIntegration(CliTestCase):

    def test_the_cli_delegates_to_the_loader_and_the_runner(self):
        path = self.program(ADD_R0_1, HALT)
        with mock.patch.object(cli_module, "read_binary", wraps=read_binary) as load, \
                mock.patch.object(cli_module, "run_program", wraps=run_program) as execute:
            result = self.cli(path)
        self.assertEqual(result.code, 0)
        load.assert_called_once_with(path)
        execute.assert_called_once()
        (program,), options = execute.call_args
        self.assertIsInstance(program, LoadedProgram)
        self.assertEqual(options, {"stdin": "", "max_steps": DEFAULT_MAX_STEPS})

    def test_the_input_text_and_the_limit_reach_the_runner(self):
        path = self.program(*ECHO)
        with mock.patch.object(cli_module, "run_program", wraps=run_program) as execute:
            self.cli(path, "--max-steps", "7", "--input-file", self.write("in.txt", b"Hi"))
        self.assertEqual(execute.call_args.kwargs, {"stdin": "Hi", "max_steps": 7})

    def test_the_summary_matches_the_runner_result_for_the_same_file(self):
        path = self.program(*PRINT_HOLA)
        expected = run_program(read_binary(path))
        fields = summary_fields(self.cli(path).err)
        self.assertEqual(fields["Instrucciones"], str(expected.instruction_count))
        self.assertEqual(fields["Memoria escrita"],
                         f"{expected.memory_bytes_written} de {expected.memory_size} bytes")
        self.assertEqual(fields["PC final"], f"0x{expected.pc:04X}")

    def test_assemble_write_and_run(self):
        text = "\n".join((".ORIG x3000", "LEA R0, MSG", "TRAP x22", "HALT",
                          'MSG: .STRINGZ "Hi"', ".END"))
        path = self.directory / "hello.bin"
        write_binary(assemble(text), path)
        result = self.cli(str(path))
        self.assertEqual((result.code, result.out), (0, "Hi"))

    def test_assembled_program_with_input(self):
        path = self.directory / "echo.bin"
        write_binary(assemble("\n".join((".ORIG x3000", "TRAP x20", "TRAP x21", "HALT", ".END"))),
                     path)
        result = self.cli(str(path), "--input-file", self.write("in.txt", b"k"))
        self.assertEqual(result.out, "k")

    def test_a_program_at_another_origin(self):
        path = self.write("p.bin", binary(ADD_R0_1, HALT, origin=b"\x00\x02"))     # x0200
        self.assertEqual(summary_fields(self.cli(path).err)["PC final"], "0x0204")

    def test_the_final_pc_is_shown_in_uppercase_hexadecimal_with_four_digits(self):
        # Origen xAB00: ADD en xAB00, HALT en xAB02, PC final xAB04 (letras en mayúscula).
        path = self.write("high.bin", binary(ADD_R0_1, HALT, origin=b"\x00\xAB"))
        self.assertEqual(summary_fields(self.cli(path).err)["PC final"], "0xAB04")


# ----------------------------------------------------------------------
# Ejecución real: python3 -m simulator
# ----------------------------------------------------------------------
class TestRealProcess(CliTestCase):

    def run_module(self, *args, stdin_bytes=None, env_extra=None):
        env = dict(os.environ)
        env["PYTHONIOENCODING"] = "utf-8"
        env.update(env_extra or {})
        options = {"input": stdin_bytes} if stdin_bytes is not None else {"stdin": subprocess.DEVNULL}
        return subprocess.run([sys.executable, "-B", "-m", "simulator", *args],
                              cwd=PROJECT_ROOT, env=env, capture_output=True, timeout=60, **options)

    def test_a_successful_run(self):
        completed = self.run_module(self.program(*PRINT_HOLA))
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(completed.stdout, b"Hola")
        self.assertIn("HALTED (HALT)", completed.stderr.decode())

    def test_the_exit_status_of_the_process_is_the_code_returned_by_main(self):
        cases = ((4, self.program(NOP, RESERVED_OPCODE, name="err.bin"), []),
                 (5, self.program(BR_SELF, name="loop.bin"), ["--max-steps", "5"]),
                 (3, str(self.directory / "missing.bin"), []))
        for expected, path, extra in cases:
            with self.subTest(expected):
                self.assertEqual(self.run_module(path, *extra).returncode, expected)

    def test_output_before_an_error_goes_to_stdout_and_the_diagnosis_to_stderr(self):
        completed = self.run_module(self.program(LEA_R0_6, PUTS, TRAP_X23, HALT, b"antes\x00"))
        self.assertEqual((completed.returncode, completed.stdout), (4, b"antes"))
        self.assertIn("UnknownTrapError", completed.stderr.decode())

    def test_a_load_error_writes_only_to_stderr(self):
        completed = self.run_module(str(self.directory / "missing.bin"))
        self.assertEqual((completed.returncode, completed.stdout), (3, b""))
        self.assertIn(b"error:", completed.stderr)

    def test_usage_errors(self):
        completed = self.run_module()
        self.assertEqual((completed.returncode, completed.stdout), (2, b""))
        self.assertIn("usage", completed.stderr.decode().lower())

    def test_help(self):
        completed = self.run_module("--help")
        self.assertEqual((completed.returncode, completed.stderr), (0, b""))
        self.assertIn("--max-steps", completed.stdout.decode())

    def test_stdin_dash_reads_a_pipe(self):
        completed = self.run_module(self.program(*ECHO), "--input-file", "-", stdin_bytes=b"A")
        self.assertEqual((completed.returncode, completed.stdout), (0, b"A"))

    def test_invalid_utf8_on_a_pipe_is_a_controlled_error(self):
        completed = self.run_module(self.program(*ECHO), "--input-file", "-", stdin_bytes=b"\xFF")
        self.assertEqual((completed.returncode, completed.stdout), (3, b""))
        self.assertIn("UTF-8", completed.stderr.decode())
        self.assertNotIn(b"Traceback", completed.stderr)

    def test_without_the_option_a_closed_stdin_is_never_read(self):
        completed = self.run_module(self.program(*ECHO))
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(completed.stdout, "\xFF".encode("utf-8"))

    def test_the_output_is_utf8_text(self):
        completed = self.run_module(self.program(LEA_R0_4, PUTS, HALT, b"\xE9\x00"))
        self.assertEqual(completed.stdout, b"\xC3\xA9")

    def test_an_unencodable_stdout_does_not_produce_a_traceback(self):
        completed = self.run_module(self.program(LEA_R0_4, PUTS, HALT, b"\xE9\x00"),
                                    env_extra={"PYTHONIOENCODING": "ascii"})
        self.assertEqual((completed.returncode, completed.stdout), (0, b"?"))
        self.assertNotIn(b"Traceback", completed.stderr)

    def test_importing_the_module_does_not_run_the_cli(self):
        completed = subprocess.run([sys.executable, "-B", "-c", "import simulator.__main__"],
                                   cwd=PROJECT_ROOT, stdin=subprocess.DEVNULL,
                                   capture_output=True, timeout=60)
        self.assertEqual((completed.returncode, completed.stdout, completed.stderr), (0, b"", b""))


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

    def test_the_cli_uses_only_the_loader_and_the_runner(self):
        project = {name for name in self.imported_modules()
                   if name.startswith(("simulator", "assembler"))}
        self.assertEqual(project, {"simulator.loader", "simulator.runner"})

    def test_the_cli_does_not_import_the_assembler_the_writer_or_the_cpu(self):
        for name in self.imported_modules():
            self.assertNotEqual(name.split(".")[0], "assembler", name)
            self.assertNotIn(name, ("simulator.cpu", "simulator.traps", "simulator.memory",
                                    "simulator.registers", "simulator.decoder"), name)

    def test_importing_the_cli_does_not_load_the_assembler_at_runtime(self):
        script = ("import sys; import simulator.__main__; "
                  "print(sorted(m for m in sys.modules if m.split('.')[0] == 'assembler'))")
        completed = subprocess.run([sys.executable, "-B", "-c", script], cwd=PROJECT_ROOT,
                                   stdin=subprocess.DEVNULL, capture_output=True, text=True,
                                   timeout=60, check=True)
        self.assertEqual(completed.stdout.strip(), "[]")

    def test_exceptions_are_handled_specifically_and_never_broadly(self):
        handled = set()
        for node in ast.walk(self.tree()):
            if isinstance(node, ast.ExceptHandler):
                self.assertIsNotNone(node.type, "except desnudo")
                types = node.type.elts if isinstance(node.type, ast.Tuple) else [node.type]
                handled.update(item.id for item in types)
        self.assertNotIn("Exception", handled)
        self.assertNotIn("BaseException", handled)
        self.assertEqual(handled, {"SystemExit", "LoadError", "OSError", "UnicodeDecodeError",
                                   "UnicodeEncodeError", "ValueError"})

    def test_the_default_limit_is_not_duplicated(self):
        source = self.source()
        self.assertNotIn("100000", source)
        self.assertNotIn("100_000", source)
        self.assertEqual(cli_module._DEFAULT_MAX_STEPS, DEFAULT_MAX_STEPS)
        self.assertEqual(cli_module._DEFAULT_MAX_STEPS,
                         inspect.signature(run_program).parameters["max_steps"].default)

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
        self.assertEqual(list(parameters), ["argv", "stdin", "stdout", "stderr"])
        self.assertEqual(parameters["argv"].kind, inspect.Parameter.POSITIONAL_OR_KEYWORD)
        for name in ("stdin", "stdout", "stderr"):
            self.assertEqual(parameters[name].kind, inspect.Parameter.KEYWORD_ONLY)
        for name in parameters:
            self.assertIsNone(parameters[name].default)

    def test_the_public_api(self):
        self.assertEqual(cli_module.__all__, ["main"])

    def test_the_source_is_compatible_with_python_3_10(self):
        ast.parse(self.source(), feature_version=(3, 10))      # falla ante sintaxis posterior


if __name__ == "__main__":
    unittest.main()
