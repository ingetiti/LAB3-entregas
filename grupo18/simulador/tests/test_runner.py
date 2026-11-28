"""Pruebas de simulator/runner.py (ejecutar desde la carpeta raíz Lab3C).

Los programas de prueba son BYTES escritos a mano (palabras de 16 bits en Little Endian,
calculadas a mano y comentadas) empaquetados en LoadedProgram, la misma estructura que
entrega el Loader real. Ninguna expectativa se genera con el código que se prueba.

Referencia de codificación (formato OP5 | campos):
  ADD R0,R0,#1 = 00000_000_000_1_0001 = 0x0011      HALT = 11000_00000000000 = 0xC000
  TRAP xNN     = 10110_NNNNNNNN_000   (x20=0xB100, x21=0xB108, x22=0xB110, x25=0xB128)
  LEA Rd,#N    = 10011_ddd_NNNNNNNN   (offset en BYTES, relativo al PC siguiente)
  BR #N        = 10000_111_NNNNNNNN   (offset en palabras, relativo al PC siguiente)
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
from assembler.writer import write_binary
from simulator import runner as runner_module
from simulator.cpu import (
    CPU,
    DEFAULT_MAX_STEPS,
    CPUHaltedError,
    ExecutionLimitError,
    MisalignedAddressError,
)
from simulator.decoder import ReservedFieldError, ReservedOpcodeError
from simulator.loader import LoadedProgram, parse_binary, read_binary
from simulator.memory import MemoryAccessError
from simulator.registers import RegisterAccessError
from simulator.runner import RunResult, RunStatus, run_program
from simulator.traps import UnknownTrapError

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# --- instrucciones (bytes en memoria = palabra en Little Endian) -------------------
ADD_R0_1 = b"\x11\x00"        # ADD R0,R0,#1   = 0x0011
ADD_R1_1 = b"\x31\x01"        # ADD R1,R1,#1   = 00000_001_001_1_0001 = 0x0131
ADD_R1_2 = b"\x32\x01"        # ADD R1,R1,#2   = 0x0132
ADD_R1_M1 = b"\x3F\x01"       # ADD R1,R1,#-1  = 0x013F
ADD_R1_3 = b"\x33\x01"        # ADD R1,R1,#3   = 00000_001_001_1_0011 = 0x0133
SUB_R1_1 = b"\x31\x09"        # SUB R1,R1,#1   = 00001_001_001_1_0001 = 0x0931
BRP_BACK_2 = b"\xFE\x81"      # BRp #-2        = 10000_001_11111110 = 0x81FE
ADD_R2_3 = b"\x53\x02"        # ADD R2,R2,#3   = 00000_010_010_1_0011 = 0x0253
ADD_R2_7 = b"\x57\x02"        # ADD R2,R2,#7   = 0x0257
ADD_R7_M1 = b"\xFF\x07"       # ADD R7,R7,#-1  = 00000_111_111_1_1111 = 0x07FF
HALT = b"\x00\xC0"            # 0xC000
NOP = b"\x00\xB8"             # 0xB800
GETC = b"\x00\xB1"            # TRAP x20 = 0xB100
OUT = b"\x08\xB1"             # TRAP x21 = 0xB108
PUTS = b"\x10\xB1"            # TRAP x22 = 0xB110
TRAP_X23 = b"\x18\xB1"        # 0xB118 (sin servicio)
TRAP_X24 = b"\x20\xB1"        # 0xB120 (sin servicio)
TRAP_X25 = b"\x28\xB1"        # 0xB128 (HALT por TRAP)
BR_SELF = b"\xFF\x87"         # BR #-1  = 10000_111_11111111 = 0x87FF
BR_BACK_3 = b"\xFD\x87"       # BR #-3  = 10000_111_11111101 = 0x87FD
JMP_R1 = b"\x00\x91"          # JMP R1   = 10010_001_00000000 = 0x9100
JSRR_R1 = b"\x00\xC9"         # JSRR R1  = 11001_001_00000000 = 0xC900
LDW_R0_R1 = b"\x20\x50"       # LDW R0,R1,#0 = 01010_000_001_00000 = 0x5020
STW_R2_R1 = b"\x20\x5A"       # STW R2,R1,#0 = 01011_010_001_00000 = 0x5A20
STW_R0_R1 = b"\x20\x58"       # STW R0,R1,#0 = 0x5820
LEA_R0_70 = b"\x46\x98"       # LEA R0,#70  = 0x9846  -> R0 = PC siguiente + 70
LEA_R0_99 = b"\x63\x98"       # LEA R0,#99  = 0x9863
LEA_R0_4 = b"\x04\x98"        # LEA R0,#4   = 0x9804
LEA_R0_6 = b"\x06\x98"        # LEA R0,#6   = 0x9806
LEA_R1_4 = b"\x04\x99"        # LEA R1,#4   = 0x9904
LEA_R1_6 = b"\x06\x99"        # LEA R1,#6   = 0x9906
LEA_R1_126 = b"\x7E\x99"      # LEA R1,#126 = 0x997E
RESERVED_OPCODE = b"\x00\xD0"  # 0xD000: opcode 11010 (26), reservado
RESERVED_FIELD = b"\x01\x90"   # 0x9001: JMP con un 1 en el campo de ceros obligatorios


def make_program(*chunks, origin=0x3000):
    return LoadedProgram(origin, b"".join(chunks))


def run(*chunks, origin=0x3000, **options):
    return run_program(make_program(*chunks, origin=origin), **options)


def source(*lines):
    return "\n".join(lines)


def valid_result(**changes):
    values = dict(status=RunStatus.HALTED, output="", instruction_count=2,
                  memory_bytes_written=4, memory_size=65536, pc=0x3004,
                  halt_reason="HALT", error_type=None, error_message=None,
                  registers=(0,) * 8)
    values.update(changes)
    return RunResult(**values)


# ----------------------------------------------------------------------
# 1-2. Finalización normal
# ----------------------------------------------------------------------
class TestNormalHalt(unittest.TestCase):

    def test_add_and_halt(self):
        result = run(ADD_R0_1, HALT)
        self.assertIsInstance(result, RunResult)
        self.assertIs(result.status, RunStatus.HALTED)
        self.assertTrue(result.ok)
        self.assertEqual(result.halt_reason, "HALT")
        self.assertEqual(result.output, "")
        self.assertEqual(result.instruction_count, 2)
        self.assertEqual(result.memory_bytes_written, 4)
        self.assertEqual(result.memory_size, 65536)
        self.assertEqual(result.pc, 0x3004)
        self.assertIsNone(result.error_type)
        self.assertIsNone(result.error_message)
        self.assertEqual(result.registers, (1, 0, 0, 0, 0, 0, 0, 0))

    def test_finishing_with_trap_x25(self):
        result = run(ADD_R0_1, TRAP_X25)
        self.assertIs(result.status, RunStatus.HALTED)
        self.assertTrue(result.ok)
        self.assertEqual(result.halt_reason, "TRAP x25")
        self.assertEqual((result.instruction_count, result.pc), (2, 0x3004))
        self.assertEqual(result.registers[0], 1)

    def test_a_program_that_is_only_halt(self):
        result = run(HALT)
        self.assertEqual((result.status, result.instruction_count, result.pc),
                         (RunStatus.HALTED, 1, 0x3002))

    def test_the_program_runs_from_its_origin(self):
        result = run(ADD_R0_1, HALT, origin=0x0200)
        self.assertEqual((result.status, result.pc, result.registers[0]),
                         (RunStatus.HALTED, 0x0204, 1))

    def test_the_pc_wraps_after_a_halt_in_the_last_slot(self):
        # HALT en xFFFE: el PC siguiente da la vuelta a x0000 (módulo 65.536).
        result = run(ADD_R0_1, HALT, origin=0xFFFC)
        self.assertEqual((result.status, result.pc, result.instruction_count),
                         (RunStatus.HALTED, 0, 2))

    def test_the_final_state_after_halt_is_halted_for_both_endings(self):
        for ending, reason in ((HALT, "HALT"), (TRAP_X25, "TRAP x25")):
            with self.subTest(reason):
                self.assertEqual(run(NOP, ending).halt_reason, reason)


# ----------------------------------------------------------------------
# 3-4. Salida
# ----------------------------------------------------------------------
class TestOutput(unittest.TestCase):

    def test_out_writes_the_low_byte_of_r0(self):
        # LEA R0,#70 en x3000 -> R0 = x3002 + 70 = x3048 -> 'H' (0x48)
        # LEA R0,#99 en x3004 -> R0 = x3006 + 99 = x3069 -> 'i' (0x69)
        result = run(LEA_R0_70, OUT, LEA_R0_99, OUT, HALT)
        self.assertEqual(result.output, "Hi")
        self.assertEqual((result.status, result.instruction_count), (RunStatus.HALTED, 5))
        self.assertEqual(result.registers[0], 0x3069)
        self.assertEqual(result.memory_bytes_written, 10)

    def test_puts_writes_a_zero_terminated_string(self):
        # LEA R0,#4 en x3000 -> R0 = x3002 + 4 = x3006 (donde empieza la cadena)
        result = run(LEA_R0_4, PUTS, HALT, b"Hola\x00")
        self.assertEqual(result.output, "Hola")
        self.assertEqual((result.status, result.instruction_count), (RunStatus.HALTED, 3))
        self.assertEqual((result.memory_bytes_written, result.pc), (11, 0x3006))
        self.assertEqual(result.registers[0], 0x3006)

    def test_puts_with_an_empty_string_writes_nothing(self):
        self.assertEqual(run(LEA_R0_4, PUTS, HALT, b"\x00").output, "")

    def test_a_program_without_output_has_empty_output(self):
        self.assertEqual(run(ADD_R0_1, HALT).output, "")

    def test_output_is_captured_and_not_written_to_the_real_stdout(self):
        fake_stdout = io.StringIO()
        with mock.patch("sys.stdout", fake_stdout):
            result = run(LEA_R0_4, PUTS, HALT, b"Hola\x00")
        self.assertEqual(result.output, "Hola")
        self.assertEqual(fake_stdout.getvalue(), "")

    def test_output_survives_an_instruction_limit(self):
        # x3000 LEA R0,#70 ('H') ; x3002 OUT ; x3004 BR #-3 -> x3000. Tres instrucciones por vuelta.
        result = run(LEA_R0_70, OUT, BR_BACK_3, max_steps=9)
        self.assertEqual(result.status, RunStatus.INSTRUCTION_LIMIT)
        self.assertEqual((result.output, result.instruction_count, result.pc),
                         ("HHH", 9, 0x3000))


# ----------------------------------------------------------------------
# 5-6. Entrada (GETC)
# ----------------------------------------------------------------------
class TestInput(unittest.TestCase):

    def test_getc_reads_a_character_from_stdin(self):
        result = run(GETC, OUT, HALT, stdin="A")
        self.assertEqual(result.output, "A")
        self.assertEqual(result.registers[0], 0x41)
        self.assertEqual((result.status, result.instruction_count), (RunStatus.HALTED, 3))

    def test_successive_getc_read_successive_characters(self):
        result = run(GETC, OUT, GETC, OUT, HALT, stdin="xy")
        self.assertEqual(result.output, "xy")
        self.assertEqual(result.registers[0], ord("y"))

    def test_getc_without_input_returns_eof(self):
        # Sin `stdin` (valor por defecto) y con "" explícito: fin de entrada = 0xFFFF.
        self.assertEqual(run(GETC, HALT).registers[0], 0xFFFF)
        self.assertEqual(run(GETC, HALT, stdin="").registers[0], 0xFFFF)

    def test_eof_after_the_input_is_exhausted(self):
        result = run(GETC, GETC, HALT, stdin="A")
        self.assertEqual(result.registers[0], 0xFFFF)

    def test_a_character_wider_than_a_byte_becomes_a_question_mark(self):
        self.assertEqual(run(GETC, HALT, stdin="\u20AC").registers[0], ord("?"))

    def test_the_real_stdin_is_never_read(self):
        class ExplodingStdin:
            def read(self, *args):
                raise AssertionError("se leyó el stdin real")

            readline = read

        with mock.patch("sys.stdin", ExplodingStdin()):
            result = run(GETC, GETC, HALT)                  # sin entrada: no debe bloquear
        self.assertEqual(result.registers[0], 0xFFFF)

    def test_the_same_input_gives_the_same_result_every_time(self):
        first = run(GETC, OUT, HALT, stdin="Q")
        second = run(GETC, OUT, HALT, stdin="Q")
        self.assertEqual(first, second)


# ----------------------------------------------------------------------
# 7-8. Límite de instrucciones
# ----------------------------------------------------------------------
class TestInstructionLimit(unittest.TestCase):

    def test_an_infinite_loop_stops_at_the_limit(self):
        result = run(BR_SELF, max_steps=10)
        self.assertIs(result.status, RunStatus.INSTRUCTION_LIMIT)
        self.assertFalse(result.ok)
        self.assertEqual(result.instruction_count, 10)
        self.assertEqual(result.pc, 0x3000)
        self.assertEqual(result.memory_bytes_written, 2)

    def test_a_limit_result_carries_no_halt_reason_and_no_error(self):
        result = run(BR_SELF, max_steps=10)
        self.assertIsNone(result.halt_reason)
        self.assertIsNone(result.error_type)
        self.assertIsNone(result.error_message)

    def test_the_limit_is_not_reported_as_an_error(self):
        # ExecutionLimitError pertenece a EXECUTION_ERRORS: debe clasificarse aparte.
        self.assertIsNot(run(BR_SELF, max_steps=5).status, RunStatus.ERROR)

    def test_halt_exactly_at_the_last_allowed_step_is_a_normal_end(self):
        # NOP, NOP, HALT: tres instrucciones.
        result = run(NOP, NOP, HALT, max_steps=3)
        self.assertEqual((result.status, result.instruction_count, result.pc),
                         (RunStatus.HALTED, 3, 0x3006))
        self.assertEqual(run(NOP, NOP, HALT, max_steps=4).status, RunStatus.HALTED)

    def test_one_step_short_of_the_halt_is_the_limit(self):
        result = run(NOP, NOP, HALT, max_steps=2)
        self.assertEqual((result.status, result.instruction_count, result.pc),
                         (RunStatus.INSTRUCTION_LIMIT, 2, 0x3004))
        result = run(NOP, NOP, HALT, max_steps=1)
        self.assertEqual((result.status, result.instruction_count, result.pc),
                         (RunStatus.INSTRUCTION_LIMIT, 1, 0x3002))

    def test_the_default_limit_is_one_hundred_thousand_steps(self):
        # Sin HALT: tras ADD R0,R0,#1 la CPU ejecuta ceros (0x0000 = ADD R0,R0,R0), que
        # duplican R0 hasta desbordar (1 -> 2 -> ... -> 65.536 = 0) y siguen hasta el límite.
        result = run(ADD_R0_1)
        self.assertIs(result.status, RunStatus.INSTRUCTION_LIMIT)
        self.assertEqual(result.instruction_count, 100_000)
        self.assertEqual(result.registers[0], 0)
        self.assertEqual(DEFAULT_MAX_STEPS, 100_000)

    def test_the_limit_boundary_with_a_real_loop(self):
        # El bucle contado ejecuta exactamente 8 instrucciones (ver TestCountingAndMemory).
        loop = (ADD_R1_3, SUB_R1_1, BRP_BACK_2, HALT)
        self.assertEqual(run(*loop, max_steps=8).status, RunStatus.HALTED)
        interrupted = run(*loop, max_steps=7)
        self.assertEqual((interrupted.status, interrupted.instruction_count),
                         (RunStatus.INSTRUCTION_LIMIT, 7))
        self.assertEqual(interrupted.registers[1], 0)        # SUB ya llegó a 0; falta el HALT

    def test_invalid_max_steps_propagates_the_cpu_value_error(self):
        # Se respeta EXACTAMENTE la validación de CPU.run: mismos valores inválidos.
        for bad in (0, -1, True, False, 1.5, "10", None, [3]):
            with self.subTest(repr(bad)):
                with self.assertRaises(ValueError):
                    CPU().run(bad)                           # comportamiento de referencia
                with self.assertRaises(ValueError):
                    run(HALT, max_steps=bad)

    def test_the_smallest_valid_limit(self):
        self.assertEqual(run(HALT, max_steps=1).status, RunStatus.HALTED)
        self.assertEqual(run(NOP, HALT, max_steps=1).status, RunStatus.INSTRUCTION_LIMIT)


# ----------------------------------------------------------------------
# 18. Programa vacío
# ----------------------------------------------------------------------
class TestEmptyProgram(unittest.TestCase):

    def test_an_empty_program_is_not_rejected_and_reaches_the_limit(self):
        # No hay tratamiento especial: la memoria son ceros (ADD R0,R0,R0) y la CPU los
        # ejecuta de a 2 bytes hasta agotar el límite. 50 pasos desde x3000 -> x3064.
        result = run(max_steps=50)
        self.assertIs(result.status, RunStatus.INSTRUCTION_LIMIT)
        self.assertEqual(result.instruction_count, 50)
        self.assertEqual(result.pc, 0x3064)
        self.assertEqual(result.memory_bytes_written, 0)
        self.assertEqual(result.registers, (0,) * 8)
        self.assertEqual(result.output, "")

    def test_data_only_programs_also_execute_whatever_is_in_memory(self):
        result = run(b"\x00\x00\x00\x00", max_steps=10)
        self.assertEqual(result.status, RunStatus.INSTRUCTION_LIMIT)
        self.assertEqual(result.memory_bytes_written, 4)


# ----------------------------------------------------------------------
# 9-13. Errores de ejecución
# ----------------------------------------------------------------------
class TestExecutionErrors(unittest.TestCase):

    def assertError(self, result, error_type, fragment, count, pc):
        self.assertIs(result.status, RunStatus.ERROR)
        self.assertFalse(result.ok)
        self.assertEqual(result.error_type, error_type)
        self.assertIn(fragment, result.error_message)
        self.assertIsNone(result.halt_reason)
        self.assertEqual(result.instruction_count, count)
        self.assertEqual(result.pc, pc)

    def test_reserved_opcode(self):
        result = run(NOP, RESERVED_OPCODE)
        self.assertError(result, "ReservedOpcodeError", "0xD000", count=1, pc=0x3002)
        self.assertEqual(result.memory_bytes_written, 4)

    def test_reserved_field(self):
        result = run(NOP, RESERVED_FIELD)
        self.assertError(result, "ReservedFieldError", "0x9001", count=1, pc=0x3002)

    def test_unknown_trap_vectors(self):
        for name, trap, vector in (("x23", TRAP_X23, "x23"), ("x24", TRAP_X24, "x24")):
            with self.subTest(name):
                self.assertError(run(trap, HALT), "UnknownTrapError", vector, count=0, pc=0x3000)

    def test_a_jump_to_an_odd_address(self):
        # ADD R1,R1,#1 -> R1 = 1 ; JMP R1 -> destino impar.
        result = run(ADD_R1_1, JMP_R1, HALT)
        self.assertError(result, "MisalignedAddressError", "0x0001", count=1, pc=0x3002)
        self.assertEqual(result.registers[1], 1)

    def test_jsrr_to_an_odd_address_does_not_write_the_return_register(self):
        result = run(ADD_R1_1, JSRR_R1, HALT)
        self.assertError(result, "MisalignedAddressError", "0x0001", count=1, pc=0x3002)
        self.assertEqual(result.registers[7], 0)

    def test_a_memory_access_outside_the_address_space(self):
        # ADD R1,R1,#-1 -> R1 = 0xFFFF ; LDW R0,R1,#0 necesitaría los bytes xFFFF y x10000.
        result = run(ADD_R1_M1, LDW_R0_R1, HALT)
        self.assertError(result, "MemoryAccessError", "0xFFFF", count=1, pc=0x3002)
        self.assertEqual(result.registers[1], 0xFFFF)

    def test_output_before_an_error_is_preserved(self):
        # x3000 LEA R0,#6 -> x3008 ; x3002 PUTS ; x3004 TRAP x23 (falla) ; x3006 HALT ; x3008 "antes"
        result = run(LEA_R0_6, PUTS, TRAP_X23, HALT, b"antes\x00")
        self.assertEqual(result.output, "antes")
        self.assertError(result, "UnknownTrapError", "x23", count=2, pc=0x3004)
        self.assertEqual(result.registers[0], 0x3008)

    def test_the_failing_instruction_is_not_counted(self):
        # Tres instrucciones válidas y una inválida: el contador vale 3.
        result = run(NOP, NOP, NOP, RESERVED_OPCODE)
        self.assertEqual((result.status, result.instruction_count, result.pc),
                         (RunStatus.ERROR, 3, 0x3006))

    def test_the_registers_reflect_the_work_done_before_the_error(self):
        result = run(ADD_R0_1, ADD_R1_2, ADD_R2_3, RESERVED_OPCODE)
        self.assertEqual(result.registers, (1, 2, 3, 0, 0, 0, 0, 0))
        self.assertEqual(result.instruction_count, 3)

    def test_a_running_off_the_end_of_memory_is_not_an_error(self):
        # Sin HALT desde xFFFE el PC da la vuelta y la CPU sigue: termina en el límite.
        self.assertIs(run(NOP, origin=0xFFFE, max_steps=5).status, RunStatus.INSTRUCTION_LIMIT)


# ----------------------------------------------------------------------
# Clasificación con excepciones forzadas (independiente de la CPU real)
# ----------------------------------------------------------------------
class TestClassification(unittest.TestCase):

    def forced(self, error):
        with mock.patch.object(CPU, "run", side_effect=error):
            return run(HALT)

    def test_the_instruction_limit_is_a_status_not_an_error(self):
        result = self.forced(ExecutionLimitError("límite"))
        self.assertIs(result.status, RunStatus.INSTRUCTION_LIMIT)
        self.assertIsNone(result.error_type)
        self.assertIsNone(result.error_message)

    def test_execution_errors_become_results_with_their_type_and_message(self):
        cases = (UnknownTrapError("sin servicio x99"), MisalignedAddressError("impar"),
                 MemoryAccessError("fuera"), ReservedOpcodeError("opcode"),
                 ReservedFieldError("campo"), CPUHaltedError("detenida"))
        for error in cases:
            with self.subTest(type(error).__name__):
                result = self.forced(error)
                self.assertIs(result.status, RunStatus.ERROR)
                self.assertEqual(result.error_type, type(error).__name__)
                self.assertEqual(result.error_message, str(error))

    def test_usage_errors_and_internal_bugs_are_not_swallowed(self):
        for error in (RuntimeError("bug"), ValueError("max_steps"), TypeError("tipo"),
                      RegisterAccessError("registro"), AssertionError("invariante"),
                      ZeroDivisionError(), KeyError("k")):
            with self.subTest(type(error).__name__):
                with self.assertRaises(type(error)):
                    self.forced(error)


# ----------------------------------------------------------------------
# 15-16. Contabilización y memoria
# ----------------------------------------------------------------------
class TestCountingAndMemory(unittest.TestCase):

    def test_every_executed_instruction_counts_including_halt(self):
        self.assertEqual(run(ADD_R0_1, ADD_R0_1, ADD_R0_1, HALT).instruction_count, 4)
        self.assertEqual(run(HALT).instruction_count, 1)

    def test_a_conditional_loop_counts_every_iteration(self):
        # x3000 ADD R1,R1,#3 ; x3002 SUB R1,R1,#1 ; x3004 BRp #-2 (vuelve a x3002) ; x3006 HALT.
        # R1: 3 -> 2 -> 1 -> 0. El BRp se toma dos veces y a la tercera (Z) cae al HALT.
        # Instrucciones: 1 (ADD) + 3 * (SUB + BRp) + 1 (HALT) = 8.
        result = run(ADD_R1_3, SUB_R1_1, BRP_BACK_2, HALT)
        self.assertEqual((result.status, result.instruction_count, result.pc),
                         (RunStatus.HALTED, 8, 0x3008))
        self.assertEqual(result.registers[1], 0)

    def test_memory_used_is_the_loaded_image_for_a_program_that_only_computes(self):
        self.assertEqual(run(ADD_R0_1, HALT).memory_bytes_written, 4)
        self.assertEqual(run(ADD_R0_1, ADD_R0_1, HALT).memory_bytes_written, 6)

    def test_a_store_to_a_new_address_adds_two_bytes(self):
        # x3000 LEA R1,#126 -> R1 = x3002 + 126 = x3080 ; x3002 STW R0,R1,#0 ; x3004 HALT
        result = run(LEA_R1_126, STW_R0_R1, HALT)
        self.assertEqual(result.registers[1], 0x3080)
        self.assertEqual(result.memory_bytes_written, 6 + 2)

    def test_a_store_over_the_loaded_image_adds_nothing(self):
        # x3000 ADD R2,R2,#7 ; x3002 LEA R1,#4 -> x3008 ; x3004 STW R2,R1,#0 ; x3006 HALT ; x3008 dato
        result = run(ADD_R2_7, LEA_R1_4, STW_R2_R1, HALT, b"\x00\x00")
        self.assertEqual(result.registers[1], 0x3008)
        self.assertEqual(result.registers[2], 7)
        self.assertEqual(result.memory_bytes_written, 10)       # solo la imagen cargada

    def test_reads_and_fetches_do_not_count(self):
        # x3000 LEA R1,#4 -> x3006 ; x3002 LDW R0,R1,#0 ; x3004 HALT ; x3006 dato 0x1234 (34 12)
        result = run(LEA_R1_4, LDW_R0_R1, HALT, b"\x34\x12")
        self.assertEqual(result.registers[0], 0x1234)
        self.assertEqual(result.memory_bytes_written, 8)

    def test_the_memory_size_is_always_the_full_address_space(self):
        for result in (run(HALT), run(BR_SELF, max_steps=3), run(RESERVED_OPCODE), run(max_steps=1)):
            self.assertEqual(result.memory_size, 65536)

    def test_memory_used_never_exceeds_the_memory_size(self):
        result = run(HALT)
        self.assertLessEqual(result.memory_bytes_written, result.memory_size)


# ----------------------------------------------------------------------
# 17. Registros
# ----------------------------------------------------------------------
class TestRegisters(unittest.TestCase):

    def test_the_final_registers_r0_to_r7_are_captured(self):
        result = run(ADD_R0_1, ADD_R1_2, ADD_R2_3, ADD_R7_M1, HALT)
        self.assertEqual(result.registers, (1, 2, 3, 0, 0, 0, 0, 0xFFFF))

    def test_registers_is_an_immutable_tuple_of_eight_sixteen_bit_values(self):
        registers = run(ADD_R7_M1, HALT).registers
        self.assertIs(type(registers), tuple)
        self.assertEqual(len(registers), 8)
        self.assertTrue(all(0 <= value <= 0xFFFF for value in registers))

    def test_a_fresh_cpu_starts_with_every_register_at_zero(self):
        self.assertEqual(run(HALT).registers, (0,) * 8)

    def test_sp_is_not_initialised(self):
        self.assertEqual(run(HALT).registers[6], 0)


# ----------------------------------------------------------------------
# 21. Independencia entre ejecuciones
# ----------------------------------------------------------------------
class TestIndependence(unittest.TestCase):

    # x3000 ADD R2,R2,#7 ; x3002 LEA R1,#6 -> x300A ; x3004 LDW R0,R1,#0 ; x3006 STW R2,R1,#0 ;
    # x3008 HALT ; x300A dato (0). Cada ejecución lee 0 y después escribe 7 en ese dato.
    PROGRAM = (ADD_R2_7, LEA_R1_6, LDW_R0_R1, STW_R2_R1, HALT, b"\x00\x00")

    def test_two_consecutive_runs_give_identical_results(self):
        program = make_program(*self.PROGRAM)
        first, second = run_program(program), run_program(program)
        self.assertEqual(first, second)
        self.assertEqual(first.registers[0], 0)        # leyó 0 antes de escribir
        self.assertEqual(first.registers[2], 7)

    def test_memory_does_not_leak_between_runs(self):
        # Si la memoria persistiera, la segunda lectura devolvería 7 en R0.
        program = make_program(*self.PROGRAM)
        run_program(program)
        self.assertEqual(run_program(program).registers[0], 0)

    def test_registers_do_not_leak_between_runs(self):
        # Si los registros persistieran, R2 valdría 14 en la segunda ejecución.
        program = make_program(*self.PROGRAM)
        run_program(program)
        self.assertEqual(run_program(program).registers[2], 7)

    def test_output_does_not_accumulate_between_runs(self):
        program = make_program(LEA_R0_4, PUTS, HALT, b"Hola\x00")
        self.assertEqual(run_program(program).output, "Hola")
        self.assertEqual(run_program(program).output, "Hola")

    def test_the_instruction_count_does_not_accumulate_between_runs(self):
        program = make_program(ADD_R0_1, HALT)
        self.assertEqual(run_program(program).instruction_count, 2)
        self.assertEqual(run_program(program).instruction_count, 2)

    def test_an_error_run_does_not_affect_the_next_run(self):
        bad, good = make_program(RESERVED_OPCODE), make_program(ADD_R0_1, HALT)
        self.assertEqual(run_program(bad).status, RunStatus.ERROR)
        self.assertEqual(run_program(good).status, RunStatus.HALTED)

    def test_a_new_cpu_is_created_for_every_run(self):
        created = []

        class SpyCPU(CPU):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                created.append(self)

        program = make_program(HALT)
        with mock.patch.object(runner_module, "CPU", SpyCPU):
            run_program(program)
            run_program(program)
        self.assertEqual(len(created), 2)
        self.assertIsNot(created[0], created[1])

    def test_the_program_is_not_modified(self):
        program = make_program(*self.PROGRAM)
        before = (program, program.origin, program.data)
        run_program(program)
        self.assertEqual((program, program.origin, program.data), before)


# ----------------------------------------------------------------------
# 19. Validación de argumentos
# ----------------------------------------------------------------------
class TestArgumentValidation(unittest.TestCase):

    def test_program_must_be_a_loaded_program(self):
        class Lookalike:                                # mismos atributos, otro tipo
            origin = 0x3000
            data = HALT

        for bad in (HALT, bytearray(HALT), None, "program", (0x3000, HALT),
                    {"origin": 0x3000, "data": HALT}, EncodedProgram(0x3000, HALT), Lookalike()):
            with self.subTest(type(bad).__name__), self.assertRaises(TypeError):
                run_program(bad)

    def test_stdin_must_be_text(self):
        for bad in (b"A", bytearray(b"A"), None, 5, ["A"], io.StringIO("A")):
            with self.subTest(type(bad).__name__), self.assertRaises(TypeError):
                run_program(make_program(HALT), stdin=bad)

    def test_invalid_arguments_fail_before_any_cpu_is_created(self):
        with mock.patch.object(runner_module, "CPU") as cpu_class:
            with self.assertRaises(TypeError):
                run_program(None)
            with self.assertRaises(TypeError):
                run_program(make_program(HALT), stdin=b"A")
        cpu_class.assert_not_called()

    def test_arguments_can_be_given_by_position_or_keyword(self):
        program = make_program(GETC, OUT, HALT)
        self.assertEqual(run_program(program, "Z", 10), run_program(program, stdin="Z", max_steps=10))


# ----------------------------------------------------------------------
# 20. RunResult: invariantes
# ----------------------------------------------------------------------
class TestRunResult(unittest.TestCase):

    def test_field_order(self):
        self.assertEqual([f.name for f in dataclasses.fields(RunResult)],
                         ["status", "output", "instruction_count", "memory_bytes_written",
                          "memory_size", "pc", "halt_reason", "error_type", "error_message",
                          "registers"])

    def test_run_status_members(self):
        self.assertEqual([member.name for member in RunStatus],
                         ["HALTED", "INSTRUCTION_LIMIT", "ERROR"])

    def test_valid_results_for_each_status(self):
        self.assertTrue(valid_result().ok)
        self.assertTrue(valid_result(halt_reason="TRAP x25").ok)
        limit = valid_result(status=RunStatus.INSTRUCTION_LIMIT, halt_reason=None)
        self.assertFalse(limit.ok)
        error = valid_result(status=RunStatus.ERROR, halt_reason=None,
                             error_type="UnknownTrapError", error_message="x23")
        self.assertFalse(error.ok)

    def test_ok_is_true_only_for_halted(self):
        for status in RunStatus:
            with self.subTest(status.name):
                if status is RunStatus.HALTED:
                    result = valid_result()
                elif status is RunStatus.INSTRUCTION_LIMIT:
                    result = valid_result(status=status, halt_reason=None)
                else:
                    result = valid_result(status=status, halt_reason=None,
                                          error_type="E", error_message="m")
                self.assertEqual(result.ok, status is RunStatus.HALTED)

    def test_halted_invariants(self):
        for changes in (dict(halt_reason=None),
                        dict(error_type="E"), dict(error_message="m"),
                        dict(error_type="E", error_message="m")):
            with self.subTest(changes), self.assertRaises(ValueError):
                valid_result(**changes)

    def test_instruction_limit_invariants(self):
        base = dict(status=RunStatus.INSTRUCTION_LIMIT, halt_reason=None)
        valid_result(**base)
        for changes in (dict(halt_reason="HALT"), dict(error_type="E"),
                        dict(error_message="m"), dict(error_type="E", error_message="m")):
            with self.subTest(changes), self.assertRaises(ValueError):
                valid_result(**{**base, **changes})

    def test_error_invariants(self):
        base = dict(status=RunStatus.ERROR, halt_reason=None, error_type="E", error_message="m")
        valid_result(**base)
        for changes in (dict(halt_reason="HALT"), dict(error_type=None), dict(error_message=None),
                        dict(error_type=None, error_message=None)):
            with self.subTest(changes), self.assertRaises(ValueError):
                valid_result(**{**base, **changes})

    def test_wrong_types_are_rejected(self):
        for changes in (dict(status="HALTED"), dict(status=None), dict(output=b""),
                        dict(output=None), dict(instruction_count=True),
                        dict(instruction_count=1.5), dict(instruction_count="2"),
                        dict(memory_bytes_written=None), dict(memory_size=65536.0),
                        dict(pc="x3000"), dict(pc=True), dict(halt_reason=5),
                        dict(registers=[0] * 8), dict(registers=None),
                        dict(registers=(0,) * 7), dict(registers=(0,) * 9),
                        dict(registers=(True,) + (0,) * 7), dict(registers=(1.5,) + (0,) * 7)):
            with self.subTest(changes), self.assertRaises(TypeError):
                valid_result(**changes)
        for changes in (dict(error_type=5), dict(error_message=5)):
            with self.subTest(changes), self.assertRaises(TypeError):
                valid_result(status=RunStatus.ERROR, halt_reason=None,
                             **{"error_type": "E", "error_message": "m", **changes})

    def test_out_of_range_values_are_rejected(self):
        for changes in (dict(instruction_count=-1), dict(memory_bytes_written=-1),
                        dict(memory_bytes_written=65537), dict(memory_size=0),
                        dict(pc=-1), dict(pc=0x10000),
                        dict(registers=(-1,) + (0,) * 7), dict(registers=(0,) * 7 + (0x10000,))):
            with self.subTest(changes), self.assertRaises(ValueError):
                valid_result(**changes)

    def test_boundary_values_are_accepted(self):
        valid_result(instruction_count=0, memory_bytes_written=0, pc=0, registers=(0,) * 8)
        valid_result(memory_bytes_written=65536, pc=0xFFFF, registers=(0xFFFF,) * 8)

    def test_the_result_is_immutable(self):
        result = valid_result()
        for name in ("status", "output", "instruction_count", "registers", "pc"):
            with self.subTest(name), self.assertRaises(dataclasses.FrozenInstanceError):
                setattr(result, name, None)
        with self.assertRaises(AttributeError):
            result.ok = False

    def test_equality_and_hash(self):
        self.assertEqual(valid_result(), valid_result())
        self.assertEqual(hash(valid_result()), hash(valid_result()))
        self.assertNotEqual(valid_result(), valid_result(instruction_count=3))
        self.assertNotEqual(valid_result(), valid_result(registers=(1,) + (0,) * 7))


# ----------------------------------------------------------------------
# Integración con el Loader real (y con el ensamblador y el Writer)
# ----------------------------------------------------------------------
class TestIntegrationWithTheLoader(unittest.TestCase):

    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name)

    def test_parse_binary_then_run(self):
        # Archivo formato B escrito a mano: origen x3000 (00 30) + ADD R0,R0,#1 + HALT.
        result = run_program(parse_binary(b"\x00\x30" + ADD_R0_1 + HALT))
        self.assertEqual((result.status, result.registers[0], result.pc),
                         (RunStatus.HALTED, 1, 0x3004))

    def test_read_binary_then_run(self):
        path = self.directory / "program.bin"
        path.write_bytes(b"\x00\x30" + LEA_R0_4 + PUTS + HALT + b"Hola\x00")
        result = run_program(read_binary(path))
        self.assertEqual((result.output, result.instruction_count, result.memory_bytes_written),
                         ("Hola", 3, 11))

    def test_assemble_write_read_run(self):
        text = source(".ORIG x3000", "LEA R0, MSG", "TRAP x22", "HALT",
                      'MSG: .STRINGZ "Hi"', ".END")
        path = self.directory / "hello.bin"
        write_binary(assemble(text), path)
        result = run_program(read_binary(path))
        self.assertEqual(result.output, "Hi")
        self.assertEqual((result.status, result.instruction_count), (RunStatus.HALTED, 3))

    def test_assembled_program_with_input(self):
        text = source(".ORIG x3000", "TRAP x20", "TRAP x21", "HALT", ".END")
        path = self.directory / "echo.bin"
        write_binary(assemble(text), path)
        self.assertEqual(run_program(read_binary(path), stdin="k").output, "k")

    def test_a_loader_valid_empty_file_runs_into_the_limit(self):
        path = self.directory / "empty.bin"
        path.write_bytes(b"\x00\x30")                       # solo el origen
        result = run_program(read_binary(path), max_steps=20)
        self.assertEqual((result.status, result.instruction_count, result.memory_bytes_written),
                         (RunStatus.INSTRUCTION_LIMIT, 20, 0))

    def test_an_odd_origin_cannot_reach_the_runner(self):
        with self.assertRaises(ValueError):
            LoadedProgram(0x3001, HALT)


# ----------------------------------------------------------------------
# Estructura del módulo
# ----------------------------------------------------------------------
class TestModuleStructure(unittest.TestCase):

    @staticmethod
    def tree():
        return ast.parse(Path(runner_module.__file__).read_text(encoding="utf-8"))

    def imported_modules(self):
        imported = set()
        for node in ast.walk(self.tree()):
            if isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)
            elif isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
        return imported

    def test_the_runner_only_depends_on_the_simulator_modules_it_needs(self):
        project = {name for name in self.imported_modules()
                   if name.startswith(("simulator", "assembler"))}
        self.assertEqual(project, {"simulator.cpu", "simulator.loader",
                                   "simulator.registers", "simulator.traps"})

    def test_the_runner_does_not_import_the_assembler(self):
        for name in self.imported_modules():
            self.assertNotEqual(name.split(".")[0], "assembler", name)

    def test_importing_the_runner_does_not_load_the_assembler_at_runtime(self):
        script = ("import sys; import simulator.runner; "
                  "print(sorted(m for m in sys.modules if m.split('.')[0] == 'assembler'))")
        result = subprocess.run([sys.executable, "-B", "-c", script], cwd=PROJECT_ROOT,
                                capture_output=True, text=True, check=True)
        self.assertEqual(result.stdout.strip(), "[]")

    def test_exceptions_are_handled_specifically_and_in_the_right_order(self):
        handlers = [handler for node in ast.walk(self.tree()) if isinstance(node, ast.Try)
                    for handler in node.handlers]
        names = [handler.type.id if isinstance(handler.type, ast.Name) else None
                 for handler in handlers]
        # El límite se captura ANTES que EXECUTION_ERRORS (de la que forma parte).
        self.assertEqual(names, ["ExecutionLimitError", "EXECUTION_ERRORS"])

    def test_there_is_no_blanket_exception_handling(self):
        for node in ast.walk(self.tree()):
            if isinstance(node, ast.ExceptHandler):
                self.assertIsNotNone(node.type, "except desnudo")
                self.assertNotIn(getattr(node.type, "id", None), ("Exception", "BaseException"))

    def test_the_public_api(self):
        self.assertEqual(sorted(runner_module.__all__), ["RunResult", "RunStatus", "run_program"])
        parameters = inspect.signature(run_program).parameters
        self.assertEqual(list(parameters), ["program", "stdin", "max_steps"])
        self.assertEqual(parameters["stdin"].default, "")
        self.assertEqual(parameters["max_steps"].default, DEFAULT_MAX_STEPS)
        self.assertIs(parameters["program"].default, inspect.Parameter.empty)


if __name__ == "__main__":
    unittest.main()