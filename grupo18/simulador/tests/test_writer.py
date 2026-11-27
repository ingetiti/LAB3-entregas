"""Pruebas de assembler/writer.py (ejecutar desde la carpeta raíz Lab3C).

Formato B: 2 bytes de origen (Little Endian) + payload copiado tal cual.
Todos los bytes esperados están calculados a mano y escritos como literales; ninguno
se genera con la función que se prueba. Para "leer" los archivos se usa código propio
de las pruebas (índices y rebanadas), independiente del writer.
"""

import ast
import inspect
import io
import os
import pathlib
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from assembler import writer as writer_module
from assembler.assembler import assemble
from assembler.encoder import EncodedProgram
from assembler.writer import serialize_binary, write_binary
from simulator.cpu import CPU
from simulator.traps import ConsoleIO


def source(*lines):
    return "\n".join(lines)


class WriterTestCase(unittest.TestCase):

    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name)

    def path(self, name="program.bin"):
        return self.directory / name

    @staticmethod
    def read(path):
        return Path(path).read_bytes()


# ----------------------------------------------------------------------
# F. Formato: función pura (origen LE + payload)
# ----------------------------------------------------------------------
class TestFormat(WriterTestCase):

    def test_the_documented_example(self):
        # ADD R0,R0,#1 = 0x0011 -> 11 00 ; HALT = 0xC000 -> 00 C0 ; origen x3000 -> 00 30
        program = EncodedProgram(0x3000, b"\x11\x00\x00\xC0")
        self.assertEqual(serialize_binary(program), b"\x00\x30\x11\x00\x00\xC0")

    def test_origin_is_two_bytes_little_endian(self):
        # (origen, bytes esperados): primero el byte BAJO, después el ALTO.
        for origin, expected in ((0x0000, b"\x00\x00"), (0x0002, b"\x02\x00"),
                                 (0x00FE, b"\xFE\x00"), (0x0100, b"\x00\x01"),
                                 (0x1234, b"\x34\x12"), (0x3000, b"\x00\x30"),
                                 (0xFF00, b"\x00\xFF"), (0xFFFE, b"\xFE\xFF")):
            with self.subTest(hex(origin)):
                result = serialize_binary(EncodedProgram(origin, b""))
                self.assertEqual(result, expected)
                self.assertEqual(result[0], origin & 0xFF)          # byte bajo primero
                self.assertEqual(result[1], origin >> 8)            # byte alto después

    def test_an_empty_program_is_just_the_origin(self):
        self.assertEqual(serialize_binary(EncodedProgram(0x4000, b"")), b"\x00\x40")

    def test_the_payload_is_copied_verbatim_after_the_origin(self):
        payload = bytes(range(256))                    # todos los valores de byte
        result = serialize_binary(EncodedProgram(0x3000, payload))
        self.assertEqual(result[:2], b"\x00\x30")
        self.assertEqual(result[2:], payload)
        self.assertEqual(len(result), 2 + 256)

    def test_the_payload_is_not_reordered_or_interpreted(self):
        # Una palabra 0x1234 ya está en memoria como 34 12; el writer no la toca.
        self.assertEqual(serialize_binary(EncodedProgram(0x3000, b"\x34\x12")),
                         b"\x00\x30\x34\x12")

    def test_odd_length_payloads(self):
        self.assertEqual(serialize_binary(EncodedProgram(0x3000, b"Hi\x00")),
                         b"\x00\x30Hi\x00")

    def test_the_largest_possible_program(self):
        # Origen x0000 con la memoria llena: 65.536 bytes de payload + 2 del origen.
        result = serialize_binary(EncodedProgram(0, bytes(0x10000)))
        self.assertEqual(len(result), 0x10002)
        self.assertEqual(result[:2], b"\x00\x00")

    def test_the_result_is_immutable_bytes(self):
        self.assertIs(type(serialize_binary(EncodedProgram(0x3000, b"\x01\x02"))), bytes)

    def test_it_does_not_modify_the_program(self):
        program = EncodedProgram(0x3000, b"\x11\x00\x00\xC0")
        before = (program, program.origin, program.data, program.size, program.end_address)
        serialize_binary(program)
        serialize_binary(program)
        self.assertEqual((program, program.origin, program.data, program.size,
                          program.end_address), before)

    def test_it_is_deterministic(self):
        program = EncodedProgram(0x3000, b"\x11\x00\x00\xC0")
        self.assertEqual(serialize_binary(program), serialize_binary(program))
        self.assertEqual(serialize_binary(program),
                         serialize_binary(EncodedProgram(0x3000, b"\x11\x00\x00\xC0")))

    def test_only_an_encoded_program_is_accepted(self):
        class Lookalike:                               # tiene los mismos atributos...
            origin = 0x3000
            data = b"\x11\x00"
        for bad in (b"\x11\x00", bytearray(b"\x11\x00"), None, 0x3000, "program",
                    (0x3000, b"\x11\x00"), {"origin": 0x3000, "data": b""}, Lookalike()):
            with self.subTest(type(bad).__name__), self.assertRaises(TypeError):
                serialize_binary(bad)                  # ...pero no es un EncodedProgram


# ----------------------------------------------------------------------
# A. Escritura básica
# ----------------------------------------------------------------------
class TestBasicWriting(WriterTestCase):

    def test_the_file_contains_exactly_the_expected_bytes(self):
        write_binary(EncodedProgram(0x3000, b"\x11\x00\x00\xC0"), self.path())
        self.assertEqual(self.read(self.path()), b"\x00\x30\x11\x00\x00\xC0")

    def test_it_returns_none(self):
        self.assertIsNone(write_binary(EncodedProgram(0x3000, b"\x00\xC0"), self.path()))

    def test_no_bytes_are_added_or_removed(self):
        for payload in (b"", b"\x00", b"\xFF", b"\x00\x00\x00\x00", bytes(range(256)) * 4):
            with self.subTest(len(payload)):
                write_binary(EncodedProgram(0x3000, payload), self.path())
                data = self.read(self.path())
                self.assertEqual(len(data), 2 + len(payload))
                self.assertEqual(data[2:], payload)

    def test_binary_mode_preserves_newline_like_bytes(self):
        # 0A, 0D y 1A no deben traducirse (en modo texto de Windows se alterarían), ni en
        # el payload ni en el origen: x0D0A es par (válido) y se guarda como 0A 0D.
        payload = b"\x0A\x0D\x0A\x0D\x1A\x00\x0D\x0D\x0A"
        write_binary(EncodedProgram(0x0D0A, payload), self.path())
        self.assertEqual(self.read(self.path()), b"\x0A\x0D" + payload)

    def test_the_origin_is_stored_in_the_file_for_any_valid_value(self):
        for origin in (0x0000, 0x0002, 0x3000, 0xFF00, 0xFFFE):
            with self.subTest(hex(origin)):
                write_binary(EncodedProgram(origin, b""), self.path())
                data = self.read(self.path())
                self.assertEqual(data[0] | (data[1] << 8), origin)


# ----------------------------------------------------------------------
# B. Integración con assemble()
# ----------------------------------------------------------------------
class TestIntegrationWithAssemble(WriterTestCase):

    def test_the_example_of_the_assignment(self):
        program = assemble(source(".ORIG x3000", "ADD R0, R0, #1", "HALT", ".END"))
        write_binary(program, self.path())
        self.assertEqual(self.read(self.path()), b"\x00\x30\x11\x00\x00\xC0")
        self.assertEqual(self.path().stat().st_size, 6)

    def test_the_file_can_be_read_back_and_run_in_the_cpu(self):
        # Mini-lector escrito en la prueba (el loader real no existe todavía):
        # origen = 2 primeros bytes LE; payload = el resto.
        write_binary(assemble(source(".ORIG x3000", "ADD R0, R0, #1", "HALT", ".END")),
                     self.path())
        content = self.read(self.path())
        origin, payload = content[0] | (content[1] << 8), content[2:]
        cpu = CPU(io=ConsoleIO(io.StringIO(""), io.StringIO()))
        cpu.load_program(payload, origin)
        self.assertEqual(cpu.registers.pc, 0x3000)
        cpu.run()
        self.assertEqual(cpu.registers.read(0), 1)

    def test_a_program_not_at_x3000(self):
        program = assemble(source(".ORIG x0200", "HALT", ".END"))
        write_binary(program, self.path())
        self.assertEqual(self.read(self.path()), b"\x00\x02\x00\xC0")


# ----------------------------------------------------------------------
# C. Programas de distinto tamaño y con datos
# ----------------------------------------------------------------------
FULL_PROGRAM = source(
    ".ORIG x3000",
    "START: LEA R0, MSG",
    "       TRAP x22",
    "       BR DONE",
    "VAL:   .FILL #-2",
    "BUF:   .BLKW #2",
    'MSG:   .STRINGZ "Hi"',
    "DONE:  HALT",
    ".END",
)
# Bytes calculados a mano (misma cuenta que en test_assembler): LEA R0,MSG = 0x980A,
# TRAP x22 = 0xB110, BR DONE = 0x8705, .FILL #-2 = FE FF, .BLKW #2 = 4 ceros,
# "Hi\0" = 48 69 00, relleno 00, HALT = 0xC000.
FULL_PAYLOAD = (b"\x0A\x98\x10\xB1\x05\x87\xFE\xFF\x00\x00\x00\x00Hi\x00\x00\x00\xC0")


class TestProgramSizes(WriterTestCase):

    def check(self, text, expected_file):
        write_binary(assemble(text), self.path())
        self.assertEqual(self.read(self.path()), expected_file)

    def test_empty_program(self):
        self.check(source(".ORIG x3000", ".END"), b"\x00\x30")

    def test_one_instruction(self):
        self.check(source(".ORIG x3000", "HALT", ".END"), b"\x00\x30\x00\xC0")

    def test_several_instructions(self):
        # ADD R0,R0,#1 = 0x0011 ; ADD R1,R1,#1 = 00000_001_001_1_0001 = 0x0131 ; HALT
        self.check(source(".ORIG x3000", "ADD R0, R0, #1", "ADD R1, R1, #1", "HALT", ".END"),
                   b"\x00\x30" b"\x11\x00" b"\x31\x01" b"\x00\xC0")

    def test_fill_directives(self):
        self.check(source(".ORIG x3000", ".FILL #-2", ".FILL x1234", ".END"),
                   b"\x00\x30\xFE\xFF\x34\x12")

    def test_stringz_with_odd_payload_length(self):
        self.check(source(".ORIG x3000", '.STRINGZ "Hi"', ".END"), b"\x00\x30Hi\x00")
        self.assertEqual(self.path().stat().st_size, 5)

    def test_stringz_with_a_newline_is_not_translated(self):
        self.check(source(".ORIG x3000", '.STRINGZ "a\\nb"', ".END"),
                   b"\x00\x30\x61\x0A\x62\x00")

    def test_blkw(self):
        self.check(source(".ORIG x3000", ".BLKW #3", ".END"), b"\x00\x30" + bytes(6))

    def test_padding_before_an_instruction_is_part_of_the_payload(self):
        # "AB\0" (3 bytes) + 1 de relleno + NOP (0xB800 -> 00 B8).
        self.check(source(".ORIG x3000", '.STRINGZ "AB"', "NOP", ".END"),
                   b"\x00\x30AB\x00\x00\x00\xB8")

    def test_a_program_mixing_everything(self):
        self.check(FULL_PROGRAM, b"\x00\x30" + FULL_PAYLOAD)
        self.assertEqual(self.path().stat().st_size, 2 + 18)

    def test_the_file_size_is_two_plus_the_program_size(self):
        program = assemble(FULL_PROGRAM)
        write_binary(program, self.path())
        self.assertEqual(self.path().stat().st_size, 2 + program.size)


# ----------------------------------------------------------------------
# D. Rutas
# ----------------------------------------------------------------------
class TestPaths(WriterTestCase):

    PROGRAM = EncodedProgram(0x3000, b"\x00\xC0")
    EXPECTED = b"\x00\x30\x00\xC0"

    def test_a_str_path(self):
        write_binary(self.PROGRAM, str(self.path()))
        self.assertEqual(self.read(self.path()), self.EXPECTED)

    def test_a_pathlib_path(self):
        write_binary(self.PROGRAM, pathlib.Path(self.path()))
        self.assertEqual(self.read(self.path()), self.EXPECTED)

    def test_a_relative_path(self):
        previous = os.getcwd()
        self.addCleanup(os.chdir, previous)
        os.chdir(self.directory)
        write_binary(self.PROGRAM, "relative.bin")
        self.assertEqual(self.read(self.directory / "relative.bin"), self.EXPECTED)

    def test_a_file_in_an_existing_subdirectory(self):
        (self.directory / "out").mkdir()
        write_binary(self.PROGRAM, self.directory / "out" / "p.bin")
        self.assertEqual(self.read(self.directory / "out" / "p.bin"), self.EXPECTED)

    def test_any_extension_or_none_is_accepted(self):
        for name in ("p.bin", "p.obj", "p", "p.dat.bin"):
            with self.subTest(name):
                write_binary(self.PROGRAM, self.path(name))
                self.assertEqual(self.read(self.path(name)), self.EXPECTED)

    def test_an_existing_file_is_overwritten_completely(self):
        self.path().write_bytes(b"\xAA" * 100)               # contenido previo, más largo
        write_binary(self.PROGRAM, self.path())
        self.assertEqual(self.read(self.path()), self.EXPECTED)   # sin restos del anterior

    def test_overwriting_with_a_longer_program(self):
        self.path().write_bytes(b"\xAA")
        write_binary(EncodedProgram(0x3000, bytes(range(50))), self.path())
        self.assertEqual(self.read(self.path()), b"\x00\x30" + bytes(range(50)))

    def test_writing_twice_gives_identical_files(self):
        write_binary(self.PROGRAM, self.path("a.bin"))
        write_binary(self.PROGRAM, self.path("b.bin"))
        write_binary(self.PROGRAM, self.path("a.bin"))
        self.assertEqual(self.read(self.path("a.bin")), self.read(self.path("b.bin")))

    def test_a_missing_directory_is_an_error_and_is_not_created(self):
        target = self.directory / "missing" / "p.bin"
        with self.assertRaises(FileNotFoundError):
            write_binary(self.PROGRAM, target)
        self.assertFalse((self.directory / "missing").exists())

    def test_an_empty_path_is_an_os_error(self):
        with self.assertRaises(OSError):
            write_binary(self.PROGRAM, "")

    def test_a_directory_instead_of_a_file(self):
        # POSIX: IsADirectoryError. Windows: PermissionError.
        with self.assertRaises((IsADirectoryError, PermissionError)):
            write_binary(self.PROGRAM, self.directory)

    def test_a_path_of_the_wrong_type(self):
        for bad in (None, 3.5, ["p.bin"], object()):
            with self.subTest(repr(bad)), self.assertRaises(TypeError):
                write_binary(self.PROGRAM, bad)

    @unittest.skipIf(os.name == "nt" or (hasattr(os, "geteuid") and os.geteuid() == 0),
                     "los permisos POSIX no se aplican en Windows ni al usuario root")
    def test_a_read_only_file_raises_permission_error(self):
        self.path().write_bytes(b"keep")
        self.path().chmod(0o444)
        self.addCleanup(self.path().chmod, 0o644)
        with self.assertRaises(PermissionError):
            write_binary(self.PROGRAM, self.path())
        self.assertEqual(self.read(self.path()), b"keep")


# ----------------------------------------------------------------------
# E. Integridad y errores
# ----------------------------------------------------------------------
class TestIntegrityAndErrors(WriterTestCase):

    def test_the_writer_does_not_modify_the_program(self):
        program = assemble(FULL_PROGRAM)
        snapshot = (program, program.origin, program.data, program.size, program.end_address)
        write_binary(program, self.path())
        write_binary(program, self.path("again.bin"))
        self.assertEqual((program, program.origin, program.data, program.size,
                          program.end_address), snapshot)
        self.assertEqual(program.data, FULL_PAYLOAD)

    def test_an_invalid_program_does_not_touch_the_disk(self):
        for bad in (b"\x00\xC0", None, "program", object()):
            with self.subTest(type(bad).__name__):
                with self.assertRaises(TypeError):
                    write_binary(bad, self.path("new.bin"))
                self.assertFalse(self.path("new.bin").exists())

    def test_an_invalid_program_does_not_truncate_an_existing_file(self):
        self.path().write_bytes(b"precious data")
        with self.assertRaises(TypeError):
            write_binary(b"\x00\xC0", self.path())
        self.assertEqual(self.read(self.path()), b"precious data")

    def test_operating_system_errors_propagate_unchanged(self):
        failure = OSError(28, "No space left on device")
        with mock.patch("builtins.open", side_effect=failure):
            with self.assertRaises(OSError) as context:
                write_binary(EncodedProgram(0x3000, b"\x00\xC0"), self.path())
        self.assertIs(context.exception, failure)             # el mismo objeto: sin envolver

    def test_a_failure_while_writing_propagates_unchanged(self):
        failure = OSError(28, "No space left on device")
        opened = mock.mock_open()
        opened.return_value.write.side_effect = failure
        with mock.patch("builtins.open", opened):
            with self.assertRaises(OSError) as context:
                write_binary(EncodedProgram(0x3000, b"\x00\xC0"), self.path())
        self.assertIs(context.exception, failure)

    def test_the_file_is_opened_for_binary_writing_with_the_whole_content_at_once(self):
        opened = mock.mock_open()
        with mock.patch("builtins.open", opened):
            write_binary(EncodedProgram(0x3000, b"\x11\x00\x00\xC0"), self.path())
        opened.assert_called_once_with(self.path(), "wb")
        opened.return_value.write.assert_called_once_with(b"\x00\x30\x11\x00\x00\xC0")

    def test_the_file_is_closed_even_if_writing_fails(self):
        opened = mock.mock_open()
        opened.return_value.write.side_effect = OSError("boom")
        with mock.patch("builtins.open", opened), self.assertRaises(OSError):
            write_binary(EncodedProgram(0x3000, b"\x00\xC0"), self.path())
        opened.return_value.__exit__.assert_called_once()


# ----------------------------------------------------------------------
# Estructura del módulo
# ----------------------------------------------------------------------
class TestModuleStructure(unittest.TestCase):

    @staticmethod
    def tree():
        return ast.parse(Path(writer_module.__file__).read_text(encoding="utf-8"))

    def test_it_depends_only_on_the_encoder_result_type_and_the_isa(self):
        imported = set()
        for node in ast.walk(self.tree()):
            if isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)
            elif isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
        self.assertEqual({n for n in imported if n.startswith(("simulator", "assembler"))},
                         {"assembler.encoder", "simulator.isa"})

    def test_it_does_not_swallow_errors(self):
        for node in ast.walk(self.tree()):
            if isinstance(node, ast.Try):
                self.fail(f"try/except en la línea {node.lineno}")

    def test_the_file_is_opened_in_binary_write_mode(self):
        modes = [call.args[1].value for call in ast.walk(self.tree())
                 if isinstance(call, ast.Call) and getattr(call.func, "id", None) == "open"
                 and len(call.args) > 1 and isinstance(call.args[1], ast.Constant)]
        self.assertEqual(modes, ["wb"])

    def test_the_public_api(self):
        self.assertEqual(sorted(writer_module.__all__), ["serialize_binary", "write_binary"])
        self.assertEqual(list(inspect.signature(write_binary).parameters),
                         ["program", "path"])
        self.assertEqual(list(inspect.signature(serialize_binary).parameters), ["program"])


if __name__ == "__main__":
    unittest.main()
