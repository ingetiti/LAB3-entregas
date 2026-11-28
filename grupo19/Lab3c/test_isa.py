import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

from assembler import Assembler
from simulator import (
    AlignmentError,
    ExecutionError,
    InputFormatError,
    Machine,
    StackError,
    load_object_file,
    main,
    parse_object,
)


def assemble_object(source_text: str) -> bytes:
    with tempfile.TemporaryDirectory() as temporary:
        source = Path(temporary) / "program.asm"
        source.write_text(source_text, encoding="utf-8")
        return Assembler().assemble(source).object_bytes()


class SimulatorTests(unittest.TestCase):
    def run_source(self, source_text: str, input_text: str = ""):
        image = parse_object(assemble_object(source_text))
        return Machine(image, input_text.encode("latin-1")).run()

    def test_binary_and_hex_objects_load_but_asm_is_rejected(self) -> None:
        object_bytes = assemble_object(".ORIG x3000\nHALT\n.END\n")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            binary = root / "program.bin"
            hexadecimal = root / "program.hex"
            assembly = root / "program.asm"
            binary.write_bytes(object_bytes)
            hexadecimal.write_text(
                " ".join(f"{byte:02X}" for byte in object_bytes),
                encoding="ascii",
            )
            assembly.write_text(".ORIG x3000\nHALT\n.END\n", encoding="ascii")

            self.assertEqual(load_object_file(binary), load_object_file(hexadecimal))
            with self.assertRaises(InputFormatError):
                load_object_file(assembly)

    def test_cli_executes_binary_object_and_rejects_asm_input(self) -> None:
        object_bytes = assemble_object(".ORIG x3000\nHALT\n.END\n")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            binary = root / "program.bin"
            assembly = root / "program.asm"
            binary.write_bytes(object_bytes)
            assembly.write_text(".ORIG x3000\nHALT\n.END\n", encoding="ascii")

            output = StringIO()
            with redirect_stdout(output):
                self.assertEqual(main([str(binary)]), 0)
            self.assertIn("Instructions executed: 1", output.getvalue())

            errors = StringIO()
            with redirect_stderr(errors):
                self.assertEqual(main([str(assembly)]), 1)
            self.assertIn("ASM is not accepted", errors.getvalue())

    def test_add_carry_overflow_and_compare_borrow_flags(self) -> None:
        result = self.run_source(
            ".ORIG x3000\n"
            "LI R0, x7FFF\n"
            "MOVI R1, #1\n"
            "ADD R2, R0, R1\n"
            "HALT\n"
            ".END\n"
        )
        self.assertEqual(result.registers[2], 0x8000)
        machine = Machine(parse_object(assemble_object(
            ".ORIG x3000\n"
            "LI R0, xFFFF\n"
            "MOVI R1, #1\n"
            "ADD R2, R0, R1\n"
            "HALT\n"
            ".END\n"
        )))
        result = machine.run()
        self.assertEqual(result.registers[2], 0)
        self.assertTrue(machine.c)
        self.assertTrue(machine.z)
        self.assertFalse(machine.v)

        borrow_machine = Machine(parse_object(assemble_object(
            ".ORIG x3000\n"
            "MOVI R0, #0\n"
            "MOVI R1, #1\n"
            "CMP R0, R1\n"
            "SBC R2, R0, R0\n"
            "HALT\n"
            ".END\n"
        )))
        borrow_result = borrow_machine.run()
        self.assertEqual(borrow_result.registers[2], 0xFFFF)
        self.assertTrue(borrow_machine.c)

    def test_unary_logic_and_arithmetic_match_encoded_function_fields(self) -> None:
        result = self.run_source(
            ".ORIG x3000\n"
            "MOVI R0, #1\n"
            "NOT R1, R0\n"
            "NEG R2, R0\n"
            "HALT\n"
            ".END\n"
        )
        self.assertEqual(result.registers[1], 0xFFFE)
        self.assertEqual(result.registers[2], 0xFFFF)

    def test_byte_word_memory_and_extended_word_offsets(self) -> None:
        result = self.run_source(
            ".ORIG x3000\n"
            "LEA R1, BASE\n"
            "LI R2, xABCD\n"
            "STW R2, R1, #0\n"
            "LDBL R3, R1, #0\n"
            "LDBS R4, R1, #1\n"
            "LI R5, x1234\n"
            "LDBH R5, R1, #1\n"
            "STBH R2, R1, #2\n"
            "LDW R6, R1, #0\n"
            "STW R2, R1, #16\n"
            "LDW R0, R1, #16\n"
            "HALT\n"
            "BASE: .BLKW #16\n"
            "EXTENDED: .FILL x5678\n"
            ".END\n"
        )
        self.assertEqual(result.registers[3], 0xCD)
        self.assertEqual(result.registers[4], 0xFFAB)
        self.assertEqual(result.registers[5], 0xAB34)
        self.assertEqual(result.registers[6], 0xABCD)
        self.assertEqual(result.registers[0], 0xABCD)

    def test_word_alignment_fault_is_reported(self) -> None:
        machine = Machine(parse_object(assemble_object(
            ".ORIG x3000\n"
            "LI R1, x3001\n"
            "LDW R0, R1, #0\n"
            "HALT\n"
            ".END\n"
        )))
        with self.assertRaisesRegex(AlignmentError, "unaligned word read"):
            machine.run()

    def test_pc_relative_indirect_long_load_reads_its_inline_pointer(self) -> None:
        result = self.run_source(
            ".ORIG x3000\n"
            "LDPC R0, DATA\n"
            "HALT\n"
            ".BLKB 300\n"
            "DATA: .FILL x1234\n"
            ".END\n"
        )
        self.assertEqual(result.registers[0], 0x1234)

    def test_jsr_jsrr_jmpm_and_jsrm_control_flow(self) -> None:
        result = self.run_source(
            ".ORIG x3000\n"
            "JSR SUB\n"
            "JSRM SUB_POINTER\n"
            "HALT\n"
            "SUB: ADDI R0, R0, #1\n"
            "RET\n"
            "SUB_POINTER: .FILL SUB\n"
            ".END\n"
        )
        self.assertEqual(result.registers[0], 2)

        jump_machine = Machine(parse_object(assemble_object(
            ".ORIG x3000\n"
            "LEA R0, TARGET\n"
            "JMP R0\n"
            "MOVI R1, #1\n"
            "TARGET: MOVI R1, #2\n"
            "HALT\n"
            ".END\n"
        )))
        self.assertEqual(jump_machine.run().registers[1], 2)

    def test_stack_order_flags_popr_and_underflow_checks(self) -> None:
        machine = Machine(parse_object(assemble_object(
            ".ORIG x3000\n"
            ".STACK xF000\n"
            "LI R0, x1234\n"
            "LEA R7, RETURN_POINT\n"
            "PUSHM {R0, R7}\n"
            "CLR R0\n"
            "CLR R7\n"
            "POPM {R0, R7}\n"
            "PUSHM {R7}\n"
            "CLR R7\n"
            "POPR {R7}\n"
            "RETURN_POINT: HALT\n"
            ".END\n"
        )))
        result = machine.run()
        self.assertEqual(result.registers[0], 0x1234)
        self.assertEqual(result.max_stack_bytes, 4)
        self.assertEqual(result.instructions_executed, 11)

        underflow = Machine(parse_object(assemble_object(
            ".ORIG x3000\n"
            "POPM {R0}\n"
            ".END\n"
        )))
        with self.assertRaises(StackError):
            underflow.run()

    def test_traps_input_output_and_halt(self) -> None:
        result = self.run_source(
            ".ORIG x3000\n"
            "LEA R0, MESSAGE\n"
            "PUTS\n"
            "GETC\n"
            "OUT\n"
            "HALT\n"
            "MESSAGE: .STRINGZ \"Hi\"\n"
            ".END\n",
            "!",
        )
        self.assertEqual(result.output, "Hi!")
        self.assertEqual(result.registers[0], ord("!"))
        self.assertEqual(result.instructions_executed, 5)

    def test_odd_register_jump_target_and_instruction_limit_fail(self) -> None:
        odd_jump = Machine(parse_object(assemble_object(
            ".ORIG x3000\n"
            "LI R0, x3001\n"
            "JMP R0\n"
            ".END\n"
        )))
        with self.assertRaisesRegex(AlignmentError, "unaligned jump target"):
            odd_jump.run()

        infinite_loop = Machine(parse_object(assemble_object(
            ".ORIG x3000\n"
            "LOOP: BR LOOP\n"
            ".END\n"
        )))
        with self.assertRaisesRegex(ExecutionError, "instruction limit exceeded"):
            infinite_loop.run(max_instructions=3)


if __name__ == "__main__":
    unittest.main()
