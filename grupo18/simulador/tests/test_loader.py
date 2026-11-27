"""Pruebas de simulator/loader.py (ejecutar desde la carpeta raíz Lab3C).

Formato B: 2 bytes de origen (Little Endian) + payload. Todos los bytes esperados
están escritos a mano como literales; ninguno se genera con la función que se prueba.
El loader NO puede importar al ensamblador, pero estas pruebas sí lo usan en la
sección de ida y vuelta: ahí se comprueba que ambos lados del formato coincidan.
"""

import ast
import dataclasses
import inspect
import io
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from assembler.assembler import assemble
from assembler.encoder import EncodedProgram
from assembler.writer import serialize_binary, write_binary
from simulator import loader as loader_module
from simulator.cpu import CPU
from simulator.loader import LoadedProgram, LoadError, parse_binary, read_binary
from simulator.traps import ConsoleIO

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def source(*lines):
    return "\n".join(lines)


class LoaderTestCase(unittest.TestCase):

    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name)

    def path(self, name="program.bin"):
        return self.directory / name

    def assertLoadError(self, content, fragment):
        with self.assertRaises(LoadError) as context:
            parse_binary(content)
        self.assertIn(fragment, str(context.exception))
        return context.exception


# ----------------------------------------------------------------------
# parse_binary: interpretación del formato
# ----------------------------------------------------------------------
class TestParseBinary(LoaderTestCase):

    def test_the_documented_example(self):
        # ADD R0,R0,#1 = 11 00 ; HALT = 00 C0 ; origen x3000 = 00 30 (Little Endian)
        result = parse_binary(b"\x00\x30\x11\x00\x00\xC0")
        self.assertEqual((result.origin, result.data), (0x3000, b"\x11\x00\x00\xC0"))

    def test_the_result_is_a_loaded_program(self):
        self.assertIsInstance(parse_binary(b"\x00\x30"), LoadedProgram)

    def test_origin_is_little_endian(self):
        # (bytes del archivo, origen esperado): el PRIMER byte es el BAJO.
        for content, origin in ((b"\x00\x00", 0x0000), (b"\x02\x00", 0x0002),
                                (b"\xFE\x00", 0x00FE), (b"\x00\x01", 0x0100),
                                (b"\x34\x12", 0x1234), (b"\x00\x30", 0x3000),
                                (b"\x0A\x0D", 0x0D0A), (b"\x00\xFF", 0xFF00),
                                (b"\xFE\xFF", 0xFFFE)):
            with self.subTest(content.hex()):
                result = parse_binary(content)
                self.assertEqual(result.origin, origin)
                self.assertEqual(result.origin, content[0] + 256 * content[1])
                self.assertEqual(result.data, b"")

    def test_a_two_byte_file_is_valid_and_has_an_empty_payload(self):
        result = parse_binary(b"\x00\x40")
        self.assertEqual((result.origin, result.data), (0x4000, b""))

    def test_the_payload_is_kept_exactly(self):
        payload = bytes(range(256))                    # todos los valores de byte
        self.assertEqual(parse_binary(b"\x00\x30" + payload).data, payload)

    def test_the_payload_is_not_reordered_or_interpreted(self):
        # Una palabra 0x1234 ya está en memoria como 34 12; el loader no la toca.
        self.assertEqual(parse_binary(b"\x00\x30\x34\x12").data, b"\x34\x12")

    def test_newline_like_bytes_in_the_payload_survive(self):
        self.assertEqual(parse_binary(b"\x00\x30\x0A\x0D\x0D\x0A\x1A\x00").data,
                         b"\x0A\x0D\x0D\x0A\x1A\x00")

    def test_an_odd_length_payload_is_valid(self):
        self.assertEqual(parse_binary(b"\x00\x30Hi\x00").data, b"Hi\x00")

    def test_a_bytearray_is_accepted_and_copied(self):
        content = bytearray(b"\x00\x30\x11\x00")
        result = parse_binary(content)
        content[2] = 0xFF
        self.assertEqual(result.data, b"\x11\x00")
        self.assertIs(type(result.data), bytes)

    def test_the_input_is_not_modified_and_the_result_is_deterministic(self):
        content = bytearray(b"\x00\x30\x11\x00\x00\xC0")
        before = bytes(content)
        first, second = parse_binary(content), parse_binary(content)
        self.assertEqual(bytes(content), before)
        self.assertEqual(first, second)

    def test_the_argument_must_be_bytes(self):
        for bad in ("\x00\x30", None, 0x3000, [0, 0x30], (0, 0x30), memoryview(b"\x00\x30")):
            with self.subTest(type(bad).__name__), self.assertRaises(TypeError):
                parse_binary(bad)


# ----------------------------------------------------------------------
# parse_binary: límites de memoria (la memoria tiene 65.536 bytes)
# ----------------------------------------------------------------------
class TestMemoryLimits(LoaderTestCase):

    def test_valid_origins_at_the_limits(self):
        for content, origin in ((b"\x00\x00\x00\xC0", 0x0000), (b"\x02\x00\x00\xC0", 0x0002),
                                (b"\x00\x30\x00\xC0", 0x3000), (b"\xFE\xFF\x00\xC0", 0xFFFE)):
            with self.subTest(hex(origin)):
                self.assertEqual(parse_binary(content).origin, origin)

    def test_the_largest_program_from_origin_zero_fits(self):
        # 65.536 bytes de payload desde x0000 ocupan toda la memoria: archivo de 65.538 bytes.
        content = b"\x00\x00" + bytes(65536)
        result = parse_binary(content)
        self.assertEqual((result.origin, len(result.data)), (0, 65536))

    def test_a_program_that_ends_exactly_at_the_last_address_fits(self):
        self.assertEqual(len(parse_binary(b"\xFE\xFF\x00\xC0").data), 2)       # xFFFE + 2
        self.assertEqual(len(parse_binary(b"\xFE\xFF\x41").data), 1)           # xFFFE + 1
        self.assertEqual(len(parse_binary(b"\x00\x30" + bytes(0xD000)).data),  # x3000 + xD000
                         0xD000)

    def test_origin_xfffe_with_three_bytes_does_not_fit(self):
        error = self.assertLoadError(b"\xFE\xFF\x01\x02\x03", "no cabe")
        self.assertIn("xFFFE", str(error))
        self.assertIn("3 bytes", str(error))

    def test_one_byte_more_than_fits_is_rejected(self):
        self.assertLoadError(b"\x00\x30" + bytes(0xD001), "no cabe")
        self.assertLoadError(b"\x02\x00" + bytes(65536), "no cabe")          # x0002 + 65.536
        self.assertLoadError(b"\xFE\xFF" + bytes(65536), "no cabe")

    def test_a_file_larger_than_origin_plus_memory_is_too_large(self):
        # 2 + 65.536 = 65.538 es el máximo posible; un byte más ya no puede ser válido.
        self.assertLoadError(b"\x00\x00" + bytes(65537), "demasiado grande")
        self.assertLoadError(b"\x00\x30" + bytes(1_000_000), "demasiado grande")

    def test_the_too_large_message_states_the_limit(self):
        self.assertIn("65538", str(self.assertLoadError(bytes(65539), "demasiado grande")))


# ----------------------------------------------------------------------
# parse_binary: contenidos inválidos
# ----------------------------------------------------------------------
class TestInvalidContent(LoaderTestCase):

    def test_an_empty_file(self):
        self.assertLoadError(b"", "vacío")

    def test_a_one_byte_file_has_an_incomplete_origin(self):
        for byte in (b"\x00", b"\x30", b"\xFF"):
            with self.subTest(byte.hex()):
                self.assertLoadError(byte, "incompleto")

    def test_odd_origins_are_rejected(self):
        for content, origin in ((b"\x01\x00", "x0001"), (b"\x03\x00", "x0003"),
                                (b"\x01\x30", "x3001"), (b"\xFF\x00", "x00FF"),
                                (b"\xFF\xFF", "xFFFF")):
            with self.subTest(origin):
                error = self.assertLoadError(content + b"\x00\xC0", "impar")
                self.assertIn(origin, str(error))

    def test_an_odd_origin_is_rejected_even_without_payload(self):
        self.assertLoadError(b"\x01\x30", "impar")

    def test_the_errors_are_load_errors_and_nothing_else(self):
        for bad in (b"", b"\x00", b"\x01\x30", b"\xFE\xFF\x01\x02\x03", bytes(65539)):
            with self.subTest(len(bad)), self.assertRaises(LoadError) as context:
                parse_binary(bad)
            self.assertNotIsInstance(context.exception, (OSError, ValueError, TypeError))

    def test_load_error_is_an_exception_with_a_message(self):
        self.assertTrue(issubclass(LoadError, Exception))
        self.assertEqual(str(LoadError("algo")), "algo")


# ----------------------------------------------------------------------
# LoadedProgram
# ----------------------------------------------------------------------
class TestLoadedProgram(LoaderTestCase):

    def test_fields(self):
        result = LoadedProgram(0x3000, b"\x11\x00")
        self.assertEqual((result.origin, result.data), (0x3000, b"\x11\x00"))

    def test_it_is_immutable(self):
        result = LoadedProgram(0x3000, b"\x11\x00")
        for name in ("origin", "data"):
            with self.subTest(name), self.assertRaises(dataclasses.FrozenInstanceError):
                setattr(result, name, 0)

    def test_a_bytearray_is_copied_into_immutable_bytes(self):
        buffer = bytearray(b"\x01\x02")
        result = LoadedProgram(0x3000, buffer)
        buffer[0] = 0xFF
        self.assertEqual(result.data, b"\x01\x02")
        self.assertIs(type(result.data), bytes)

    def test_equality_and_hash(self):
        first, second = LoadedProgram(0x3000, b"\x00\xC0"), LoadedProgram(0x3000, b"\x00\xC0")
        self.assertEqual(first, second)
        self.assertEqual(hash(first), hash(second))
        self.assertNotEqual(first, LoadedProgram(0x3002, b"\x00\xC0"))
        self.assertNotEqual(first, LoadedProgram(0x3000, b"\x00\xB8"))

    def test_an_invalid_placement_cannot_exist(self):
        for origin, data in ((0x3001, b""), (-2, b""), (0x10000, b""), (0x20000, b""),
                             (0xFFFE, b"\x01\x02\x03"), (0, bytes(65537))):
            with self.subTest(origin=origin, size=len(data)), self.assertRaises(ValueError):
                LoadedProgram(origin, data)

    def test_the_largest_valid_placements(self):
        LoadedProgram(0, bytes(65536))
        LoadedProgram(0xFFFE, b"\x00\xC0")
        LoadedProgram(0xFFFE, b"")

    def test_wrong_types_are_rejected(self):
        for origin in (True, False, 1.5, "x3000", None):
            with self.subTest(repr(origin)), self.assertRaises(TypeError):
                LoadedProgram(origin, b"")
        for data in ("ab", [1, 2], None, 5):
            with self.subTest(repr(data)), self.assertRaises(TypeError):
                LoadedProgram(0x3000, data)


# ----------------------------------------------------------------------
# read_binary: archivos
# ----------------------------------------------------------------------
class TestReadBinary(LoaderTestCase):

    def test_it_reads_a_file(self):
        self.path().write_bytes(b"\x00\x30\x11\x00\x00\xC0")
        result = read_binary(self.path())
        self.assertEqual((result.origin, result.data), (0x3000, b"\x11\x00\x00\xC0"))

    def test_str_and_pathlib_paths(self):
        self.path().write_bytes(b"\x00\x30\x00\xC0")
        self.assertEqual(read_binary(str(self.path())), read_binary(self.path()))

    def test_it_reads_in_binary_mode(self):
        # 0D 0A 1A no se traducen ni cortan la lectura.
        self.path().write_bytes(b"\x00\x30\x0D\x0A\x1A\x00")
        self.assertEqual(read_binary(self.path()).data, b"\x0D\x0A\x1A\x00")

    def test_the_largest_valid_file(self):
        self.path().write_bytes(b"\x00\x00" + bytes(65536))
        self.assertEqual(len(read_binary(self.path()).data), 65536)

    def test_format_errors_in_files_are_load_errors(self):
        for name, content, fragment in (("empty", b"", "vacío"),
                                        ("short", b"\x30", "incompleto"),
                                        ("odd", b"\x01\x30\x00\xC0", "impar"),
                                        ("nofit", b"\xFE\xFF\x01\x02\x03", "no cabe"),
                                        ("huge", bytes(65539), "demasiado grande")):
            with self.subTest(name):
                self.path(name).write_bytes(content)
                with self.assertRaises(LoadError) as context:
                    read_binary(self.path(name))
                self.assertIn(fragment, str(context.exception))

    def test_a_missing_file_is_an_os_error_not_a_load_error(self):
        with self.assertRaises(FileNotFoundError) as context:
            read_binary(self.path("missing.bin"))
        self.assertNotIsInstance(context.exception, LoadError)

    def test_a_directory_instead_of_a_file(self):
        # POSIX: IsADirectoryError. Windows: PermissionError.
        with self.assertRaises((IsADirectoryError, PermissionError)):
            read_binary(self.directory)

    def test_paths_of_the_wrong_type(self):
        for bad in (None, 3.5, ["p.bin"], object()):
            with self.subTest(repr(bad)), self.assertRaises(TypeError):
                read_binary(bad)

    def test_operating_system_errors_propagate_unchanged(self):
        failure = OSError(5, "Input/output error")
        with mock.patch("builtins.open", side_effect=failure):
            with self.assertRaises(OSError) as context:
                read_binary(self.path())
        self.assertIs(context.exception, failure)             # el mismo objeto: sin envolver

    def test_a_failure_while_reading_propagates_unchanged(self):
        failure = OSError(5, "Input/output error")
        opened = mock.mock_open()
        opened.return_value.read.side_effect = failure
        with mock.patch("builtins.open", opened), self.assertRaises(OSError) as context:
            read_binary(self.path())
        self.assertIs(context.exception, failure)

    def test_the_file_is_opened_in_binary_read_mode_and_read_with_a_bound(self):
        # Se piden como máximo 2 + 65.536 + 1 = 65.539 bytes: basta para detectar un
        # archivo demasiado grande sin cargarlo entero en memoria.
        opened = mock.mock_open(read_data=b"\x00\x30\x00\xC0")
        with mock.patch("builtins.open", opened):
            result = read_binary(self.path())
        opened.assert_called_once_with(self.path(), "rb")
        opened.return_value.read.assert_called_once_with(65539)
        self.assertEqual(result.data, b"\x00\xC0")

    def test_the_file_is_closed_even_if_the_content_is_invalid(self):
        opened = mock.mock_open(read_data=b"")
        with mock.patch("builtins.open", opened), self.assertRaises(LoadError):
            read_binary(self.path())
        opened.return_value.__exit__.assert_called_once()

    def test_reading_does_not_modify_the_file(self):
        self.path().write_bytes(b"\x00\x30\x11\x00\x00\xC0")
        before = self.path().stat().st_mtime_ns
        read_binary(self.path())
        self.assertEqual(self.path().read_bytes(), b"\x00\x30\x11\x00\x00\xC0")
        self.assertEqual(self.path().stat().st_mtime_ns, before)


# ----------------------------------------------------------------------
# Ida y vuelta: ensamblar -> escribir -> leer
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
FULL_PAYLOAD = b"\x0A\x98\x10\xB1\x05\x87\xFE\xFF\x00\x00\x00\x00Hi\x00\x00\x00\xC0"


class TestRoundTrip(LoaderTestCase):

    CASES = (
        ("add_halt", source(".ORIG x3000", "ADD R0, R0, #1", "HALT", ".END"),
         0x3000, b"\x11\x00\x00\xC0"),
        ("mixed", FULL_PROGRAM, 0x3000, FULL_PAYLOAD),
        ("other_origin", source(".ORIG x0200", "HALT", ".END"), 0x0200, b"\x00\xC0"),
        ("empty", source(".ORIG x4000", ".END"), 0x4000, b""),
        ("last_slot", source(".ORIG xFFFE", "NOP", ".END"), 0xFFFE, b"\x00\xB8"),
        ("odd_payload", source(".ORIG x3000", '.STRINGZ "Hi"', ".END"), 0x3000, b"Hi\x00"),
        ("padding", source(".ORIG x3000", '.STRINGZ "AB"', "NOP", ".END"),
         0x3000, b"AB\x00\x00\x00\xB8"),
    )

    def test_assemble_write_read(self):
        for name, text, origin, payload in self.CASES:
            with self.subTest(name):
                encoded = assemble(text)
                write_binary(encoded, self.path(name))
                loaded = read_binary(self.path(name))
                self.assertEqual((loaded.origin, loaded.data), (origin, payload))
                self.assertEqual((loaded.origin, loaded.data), (encoded.origin, encoded.data))

    def test_serialize_then_parse_without_touching_the_disk(self):
        for name, text, origin, payload in self.CASES:
            with self.subTest(name):
                loaded = parse_binary(serialize_binary(assemble(text)))
                self.assertEqual((loaded.origin, loaded.data), (origin, payload))

    def test_the_largest_program_survives_the_round_trip(self):
        write_binary(EncodedProgram(0, bytes(range(256)) * 256), self.path())
        loaded = read_binary(self.path())
        self.assertEqual((loaded.origin, len(loaded.data)), (0, 65536))
        self.assertEqual(loaded.data, bytes(range(256)) * 256)

    def test_a_loaded_program_runs_in_the_cpu(self):
        write_binary(assemble(source(".ORIG x3000", "ADD R0, R0, #1", "HALT", ".END")),
                     self.path())
        loaded = read_binary(self.path())
        cpu = CPU(io=ConsoleIO(io.StringIO(""), io.StringIO()))
        cpu.load_program(loaded.data, loaded.origin)
        self.assertEqual(cpu.registers.pc, 0x3000)
        cpu.run()
        self.assertEqual(cpu.registers.read(0), 1)
        self.assertTrue(cpu.halted)

    def test_the_mixed_program_prints_through_the_cpu(self):
        write_binary(assemble(FULL_PROGRAM), self.path())
        loaded = read_binary(self.path())
        output = io.StringIO()
        cpu = CPU(io=ConsoleIO(io.StringIO(""), output))
        cpu.load_program(loaded.data, loaded.origin)
        cpu.run()
        self.assertEqual(output.getvalue(), "Hi")
        self.assertEqual(cpu.instruction_count, 4)               # LEA, TRAP, BR, HALT

    def test_the_loader_agrees_with_the_documented_file_bytes(self):
        # Contrato del Writer (escrito a mano): 00 30 | 11 00 00 C0
        write_binary(assemble(source(".ORIG x3000", "ADD R0, R0, #1", "HALT", ".END")),
                     self.path())
        self.assertEqual(self.path().read_bytes(), b"\x00\x30\x11\x00\x00\xC0")
        self.assertEqual(parse_binary(self.path().read_bytes()).origin, 0x3000)


# ----------------------------------------------------------------------
# Estructura del módulo
# ----------------------------------------------------------------------
class TestModuleStructure(unittest.TestCase):

    @staticmethod
    def tree():
        return ast.parse(Path(loader_module.__file__).read_text(encoding="utf-8"))

    def imported_modules(self):
        imported = set()
        for node in ast.walk(self.tree()):
            if isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)
            elif isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
        return imported

    def test_the_loader_only_depends_on_the_isa_constants(self):
        project = {n for n in self.imported_modules() if n.startswith(("simulator", "assembler"))}
        self.assertEqual(project, {"simulator.isa"})

    def test_the_loader_does_not_import_the_assembler(self):
        for name in self.imported_modules():
            self.assertFalse(name.split(".")[0] == "assembler", name)

    def test_importing_the_loader_does_not_load_the_assembler_at_runtime(self):
        # Comprobación dinámica en un proceso limpio: nada de `assembler` en sys.modules.
        script = ("import sys; import simulator.loader; "
                  "print(sorted(m for m in sys.modules if m.split('.')[0] == 'assembler'))")
        result = subprocess.run([sys.executable, "-B", "-c", script], cwd=PROJECT_ROOT,
                                capture_output=True, text=True, check=True)
        self.assertEqual(result.stdout.strip(), "[]")

    def test_it_does_not_swallow_errors(self):
        for node in ast.walk(self.tree()):
            if isinstance(node, ast.Try):
                self.fail(f"try/except en la línea {node.lineno}")

    def test_the_file_is_opened_in_binary_read_mode(self):
        modes = [call.args[1].value for call in ast.walk(self.tree())
                 if isinstance(call, ast.Call) and getattr(call.func, "id", None) == "open"
                 and len(call.args) > 1 and isinstance(call.args[1], ast.Constant)]
        self.assertEqual(modes, ["rb"])

    def test_the_public_api(self):
        self.assertEqual(sorted(loader_module.__all__),
                         ["LoadError", "LoadedProgram", "parse_binary", "read_binary"])
        self.assertEqual(list(inspect.signature(parse_binary).parameters), ["content"])
        self.assertEqual(list(inspect.signature(read_binary).parameters), ["path"])


if __name__ == "__main__":
    unittest.main()