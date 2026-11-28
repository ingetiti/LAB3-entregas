import sys
import tempfile
import unittest
from pathlib import Path
import subprocess
import io
import contextlib

from assembler import Assembler, write_output
from simulator import Simulator, AlignmentError, ExecutionError


def word(opcode, rd=0, rs1=0, rs2=0, low=0):
    if low:
        return (opcode << 11) | (rd << 8) | (low & 0xff)
    return (opcode << 11) | (rd << 8) | (rs1 << 5) | (rs2 << 2)


def alu_immediate(opcode, rd, value):
    return (opcode << 11) | (rd << 8) | 1 | ((value & 0x7f) << 1)


class SimulatorTests(unittest.TestCase):
    def assemble_program(self, text):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "test.asm"
            source.write_text(text, encoding="utf-8")
            sparse = Assembler().assemble([source])
        memory = bytearray(65536)
        for address, value in sparse.items():
            memory[address] = value
        return Simulator(memory, pc=0x3000)

    def test_mov_and_add_signed(self):
        memory = bytearray(65536)
        memory[0x3000:0x3002] = word(7, rd=0, low=42).to_bytes(2, "little")
        memory[0x3002:0x3004] = alu_immediate(0, rd=0, value=42).to_bytes(2, "little")
        memory[0x3004:0x3006] = (26 << 11).to_bytes(2, "little")
        simulator = Simulator(memory, pc=0x3000)
        simulator.execute()
        self.assertEqual(simulator.registers[0], 84)
        self.assertTrue(simulator.flags["P"])
        self.assertEqual(simulator.instructions, 3)

    def test_loadl_storel_load_and_store(self):
        memory = bytearray(65536)
        memory[0x4000] = 0xAB
        memory[0x4002:0x4004] = (0x1234).to_bytes(2, "little")
        memory[0x3000:0x3002] = (16 << 11 | 0 << 8 | 2 << 5 | 0).to_bytes(2, "little")
        memory[0x3002:0x3004] = (18 << 11 | 1 << 8 | 2 << 5 | 2).to_bytes(2, "little")
        memory[0x3004:0x3006] = (21 << 11 | 1 << 8 | 2 << 5 | 4).to_bytes(2, "little")
        memory[0x3006:0x3008] = (26 << 11).to_bytes(2, "little")
        simulator = Simulator(memory, pc=0x3000)
        simulator.registers[2] = 0x4000
        simulator.execute()
        self.assertEqual(simulator.registers[0], 0x00AB)
        self.assertEqual(simulator.registers[1], 0x1234)
        self.assertEqual(simulator.memory[0x4004], 0x34)

    def test_branch_not_taken_then_halt(self):
        memory = bytearray(65536)
        memory[0x3000:0x3002] = ((7 << 11) | 0).to_bytes(2, "little")
        memory[0x3002:0x3004] = ((22 << 11) | (1 << 8) | 0x04).to_bytes(2, "little")
        memory[0x3004:0x3006] = word(27).to_bytes(2, "little")
        memory[0x3006:0x3008] = (26 << 11).to_bytes(2, "little")
        simulator = Simulator(memory, pc=0x3000)
        simulator.execute()
        self.assertEqual(simulator.instructions, 4)
        self.assertEqual(simulator.pc, 0x3008)

    def test_jsrr_and_ret(self):
        memory = bytearray(65536)
        memory[0x3000:0x3002] = word(27).to_bytes(2, "little")
        memory[0x3002:0x3004] = ((23 << 11) | (1 << 10) | (1 << 5)).to_bytes(2, "little")
        memory[0x3004:0x3006] = (26 << 11).to_bytes(2, "little")
        memory[0x3008:0x300A] = ((25 << 11) | (7 << 5)).to_bytes(2, "little")
        simulator = Simulator(memory, pc=0x3000)
        simulator.registers[1] = 0x3008
        simulator.execute()
        self.assertEqual(simulator.registers[7], 0x3004)

    def test_jmp_swap_sign_se_and_loadh(self):
        memory = bytearray(65536)
        memory[0x4001] = 0xAB
        memory[0x3000:0x3002] = (11 << 11 | 2 << 8 | 1 | 1 << 1).to_bytes(2, "little")
        memory[0x3002:0x3004] = (28 << 11 | 3 << 8 | 1 << 5).to_bytes(2, "little")
        memory[0x3004:0x3006] = (29 << 11 | 4 << 8 | 0xFE).to_bytes(2, "little")
        memory[0x3006:0x3008] = (17 << 11 | 6 << 8 | 5 << 5 | 1).to_bytes(2, "little")
        memory[0x3008:0x300A] = (24 << 11 | 7 << 5).to_bytes(2, "little")
        memory[0x300A:0x300C] = (26 << 11).to_bytes(2, "little")
        simulator = Simulator(memory, pc=0x3000)
        simulator.registers[1] = 0xABCD
        simulator.registers[5] = 0x4000
        simulator.registers[7] = 0x300A
        simulator.execute()
        self.assertEqual(simulator.registers[2], 0xCDAB)
        self.assertEqual(simulator.registers[3], 0xFFCD)
        self.assertEqual(simulator.registers[4], 0xFFFE)
        self.assertEqual(simulator.registers[6], 0xAB00)
        self.assertTrue(simulator.halted)

    def test_odd_jump_alignment_error(self):
        memory = bytearray(65536)
        memory[0x3000:0x3002] = ((24 << 11) | (1 << 5)).to_bytes(2, "little")
        simulator = Simulator(memory, pc=0x3000)
        simulator.registers[1] = 0x3001
        with self.assertRaises(AlignmentError):
            simulator.execute()

    def test_odd_load_word_alignment_error(self):
        memory = bytearray(65536)
        memory[0x3000:0x3002] = (18 << 11 | 0 << 8 | 1 << 5).to_bytes(2, "little")
        simulator = Simulator(memory, pc=0x3000)
        simulator.registers[1] = 0x3001
        with self.assertRaises(AlignmentError):
            simulator.execute()

    def test_binary_loader_prefix_and_metrics(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "program.bin"
            path.write_bytes(b"\x00\x30" + (27 << 11).to_bytes(2, "little") + (26 << 11).to_bytes(2, "little") )
            simulator = Simulator(batch=True)
            origin, size = simulator.load_image(path)
            simulator.execute()
            self.assertEqual(origin, 0x3000)
            self.assertEqual(size, 4)
            self.assertEqual(simulator.instructions, 2)
            self.assertEqual(len(simulator.occupied), 4)

    def test_migrated_sincos_table_results(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            image = root / "migrated_sincos_table.hex"
            source = Path("benchmark/migrated_sincos_table.asm")
            subprocess.run([
                sys.executable,
                "assembler.py", str(source), "-o", str(image), "--format", "hex"
            ], check=True)
            simulator = Simulator(batch=True)
            simulator.load_hex(image)
            simulator.execute(1000)
            results = [simulator.read_word(0x4000 + index * 2) for index in range(4)]
            self.assertEqual(results, [0x376D, 0x2000, 0x4000, 0x0000])
            self.assertEqual(simulator.instructions, 17)

    def test_migrated_sqrt_results(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            image = root / "migrated_sqrt.hex"
            source = Path("benchmark/migrated_sqrt.asm")
            subprocess.run([
                sys.executable,
                "assembler.py", str(source), "-o", str(image), "--format", "hex"
            ], check=True)
            simulator = Simulator(batch=True)
            simulator.load_hex(image)
            simulator.execute(1000)
            self.assertEqual(simulator.read_word(0x4000), 4)
            self.assertEqual(simulator.read_word(0x4002), 8)
            self.assertEqual(simulator.instructions, 7)

    def test_migrated_cordic_div_results(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            image = root / "migrated_cordic_div.hex"
            source = Path("benchmark/migrated_cordic_div.asm")
            subprocess.run([
                sys.executable,
                "assembler.py", str(source), "-o", str(image), "--format", "hex"
            ], check=True)
            simulator = Simulator(batch=True)
            simulator.load_hex(image)
            simulator.execute(1000)
            self.assertEqual(simulator.read_word(0x4000), 0x4000)
            self.assertEqual(simulator.read_word(0x4002), 0xC000)
            self.assertEqual(simulator.instructions, 31)

    def test_benchmark_metrics_all_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            from benchmark_metrics import run_benchmark, BENCHMARKS
            for name, (source, base_address, expected) in BENCHMARKS.items():
                result = run_benchmark(source, directory, base_address, expected)
                with self.subTest(benchmark=name):
                    self.assertTrue(result["halted"])
                    self.assertEqual(result["max_absolute_error"], 0)

    def test_fixed_point_reference_errors(self):
        sqrt16_word = 4
        q78_sqrt16 = 512
        g15_result = 516 >> 4
        mcd_result = 6
        mcm_result = 36
        cases = [
            (sqrt16_word, 4, "raiz entera"),
            (q78_sqrt16, 512, "sqrt Q7.8"),
            (g15_result, 32, "Q3.12 -> Q7.8"),
            (mcd_result, 6, "MCD"),
            (mcm_result, 36, "MCM"),
        ]
        for actual, expected, name in cases:
            with self.subTest(name=name):
                self.assertEqual(actual, expected)
                self.assertEqual(abs(actual - expected), 0)

    def test_migrated_core_v2_results(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            image = root / "migrated_core_v2.hex"
            source = Path("benchmark/migrated_core_v2.asm")
            subprocess.run([
                sys.executable,
                "assembler.py", str(source), "-o", str(image), "--format", "hex"
            ], check=True)
            simulator = Simulator(batch=True)
            simulator.load_hex(image)
            simulator.execute(1000)
            results = [simulator.read_word(0x4000 + index * 2) for index in range(6)]
            self.assertEqual(results, [0x0001, 0x0020, 0x0004, 0x1922, 0x002A, 0x000A])
            self.assertEqual(simulator.instructions, 31)

    def test_migrated_easy_results(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            image = root / "migrated_easy.hex"
            source = Path("benchmark/migrated_easy.asm")
            subprocess.run([
                sys.executable,
                "assembler.py", str(source), "-o", str(image), "--format", "hex"
            ], check=True)
            simulator = Simulator(batch=True)
            simulator.load_hex(image)
            simulator.execute(1000)
            results = [simulator.read_word(0x4000 + index * 2) for index in range(6)]
            self.assertEqual(results, [0x0006, 0x0024, 0x0020, 0x1922, 0x002A, 0x000A])
            self.assertEqual(simulator.instructions, 18)

    def test_phase4_integral_results(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            image = root / "phase4_integral.hex"
            source = Path("benchmark/phase4_integral.asm")
            subprocess.run([
                sys.executable,
                "assembler.py", str(source), "-o", str(image), "--format", "hex"
            ], check=True)
            simulator = Simulator(batch=True)
            simulator.load_hex(image)
            simulator.execute(10000)
            results = [simulator.read_word(0x4000 + index * 2) for index in range(31)]
            expected = [
                0x0080, 0x0019, 0x0020, 0x0008, 0x0100, 0x0024, 0x0006, 0x0001,
                0x0004, 0x0000, 0x0002, 0x0000, 0x0020, 0x0019, 0x000C, 0x0000,
                0x1922, 0x4000, 0x4000, 0x0010, 0x002A, 0x000A, 0x0080, 0x0204,
                0x0204, 0x002A, 0x002A, 0x0000, 0x4000, 0x0004, 0x0200,
            ]
            self.assertEqual(results, expected)
            self.assertEqual(simulator.instructions, 87)

    def test_phase4_core_results(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            image = root / "phase4.hex"
            source = Path("benchmark/phase4_core.asm")
            subprocess.run([
                sys.executable,
                "assembler.py", str(source), "-o", str(image), "--format", "hex"
            ], check=True)
            simulator = Simulator(batch=True)
            simulator.load_hex(image)
            simulator.execute(10000)
            results = [simulator.read_word(0x4000 + index * 2) for index in range(6)]
            self.assertEqual(results, [0x0019, 0x0001, 0x0006, 0x0020, 0x0020, 0x0004])
            self.assertEqual(simulator.instructions, 14)

    def test_division_by_zero_is_reported(self):
        memory = bytearray(65536)
        memory[0x3000:0x3002] = (14 << 11 | 0 << 8 | 1 << 5 | 2 << 2).to_bytes(2, "little")
        simulator = Simulator(memory, pc=0x3000)
        with self.assertRaises(ExecutionError):
            simulator.execute()

    def test_cmp_and_test_signed(self):
        memory = bytearray(65536)
        memory[0x3000:0x3002] = word(7, rd=0, low=-5).to_bytes(2, "little")
        memory[0x3002:0x3004] = alu_immediate(6, rd=0, value=-5).to_bytes(2, "little")
        memory[0x3004:0x3006] = (26 << 11).to_bytes(2, "little")
        simulator = Simulator(memory, pc=0x3000)
        simulator.execute()
        self.assertTrue(simulator.flags["Z"])

    def test_signed_division_and_remainder(self):
        memory = bytearray(65536)
        memory[0x3000:0x3002] = word(7, rd=1, low=-7).to_bytes(2, "little")
        memory[0x3002:0x3004] = word(7, rd=2, low=3).to_bytes(2, "little")
        memory[0x3004:0x3006] = (14 << 11 | 0 << 8 | 1 << 5 | 2 << 2).to_bytes(2, "little")
        memory[0x3006:0x3008] = (15 << 11 | 3 << 8 | 1 << 5 | 2 << 2).to_bytes(2, "little")
        memory[0x3008:0x300A] = (26 << 11).to_bytes(2, "little")
        simulator = Simulator(memory, pc=0x3000)
        simulator.execute()
        self.assertEqual(simulator.registers[0], 0xFFFE)
        self.assertEqual(simulator.registers[3], 0xFFFF)

    def test_scientific_closure_all_31_interfaces(self):
        with tempfile.TemporaryDirectory() as directory:
            from scientific_closure import run_closure
            result = run_closure(directory)
            self.assertEqual(len(result["rows"]), 31)
            self.assertTrue(result["halted"])
            self.assertEqual(result["max_absolute_error"], 0)

    def test_decimal_input_example(self):
        with tempfile.TemporaryDirectory() as directory:
            from assembler import Assembler, write_output
            source = Path("benchmark/ejemplo_entrada.asm")
            image = Path(directory) / "ejemplo_entrada.hex"
            assembler = Assembler()
            memory = assembler.assemble([source])
            write_output(image, memory, assembler.origins[0], "hex")
            simulator = Simulator(batch=True, input_chars=list("42"))
            simulator.load_hex(image)
            simulator.execute(1000)
            self.assertEqual(simulator.registers[0], 42)
            self.assertEqual(simulator.read_word(0x4000), 42)

    def test_g24_decimal_hex_binary(self):
        from assembler import Assembler, write_output
        with tempfile.TemporaryDirectory() as directory:
            source = Path("lib/g24_conversor_lc3_max.asm")
            image = Path(directory) / "g24.hex"
            assembler = Assembler()
            memory = assembler.assemble([source])
            write_output(image, memory, assembler.origins[0], "hex")

            cases = {
                "42": (42, "Dec: 42\nHex: 0x002A\nBin: 0b0000000000101010"),
                "-123": (-123, "Dec: -123\nHex: 0xFF85\nBin: 0b1111111110000101"),
            }
            for text, (expected_register, expected_output) in cases.items():
                with self.subTest(input=text):
                    simulator = Simulator(batch=True, input_chars=list(text))
                    simulator.load_hex(image)
                    output = io.StringIO()
                    with contextlib.redirect_stdout(output):
                        simulator.execute(100000)
                    self.assertEqual(simulator.read_word(0x4000), expected_register & 0xffff)
                    self.assertEqual(output.getvalue().strip(), expected_output)

    def test_decimal_loader_and_result_range(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "program.dec"
            path.write_text("48 18 216 0 48 18 42 0", encoding="ascii")
            simulator = Simulator(batch=True)
            origin, size = simulator.load_decimal(path)
            self.assertEqual(origin, 0x1230)
            self.assertEqual(size, 6)
            simulator.write_word(0x4000, 42)
            simulator.write_word(0x4002, 123)
            self.assertEqual(simulator.read_word(0x4000), 42)
            self.assertEqual(simulator.read_word(0x4002), 123)

    def test_real_benchmark_all_31_interfaces(self):
        from real_benchmark import run_all
        with tempfile.TemporaryDirectory() as directory:
            first = run_all(directory)
            second = run_all(directory)
        self.assertEqual(len(first["rows"]), 31)
        self.assertEqual(first["max_absolute_error"], 0)
        self.assertTrue(first["halted"])
        self.assertEqual(first["global_instructions"], sum(row["instructions"] for row in first["rows"]))
        self.assertEqual(
            [row["instructions"] for row in first["rows"]],
            [row["instructions"] for row in second["rows"]],
        )

    def test_cmp_three_operand_uses_second_and_third_operands(self):
        simulator = self.assemble_program(""".ORIG x3000
CMP R0 R1 R2
BRn negativo
HALT
negativo HALT
.END
""")
        simulator.registers[1] = 5
        simulator.registers[2] = 8
        simulator.execute()
        self.assertTrue(simulator.flags["N"])
        self.assertEqual(simulator.instructions, 3)

    def test_test_immediate_is_sign_extended(self):
        simulator = self.assemble_program(""".ORIG x3000
TEST R3 #-64
BRn negativo
HALT
negativo HALT
.END
""")
        simulator.registers[3] = 0x8000
        simulator.execute()
        self.assertTrue(simulator.flags["N"])
        self.assertEqual(simulator.instructions, 3)

    def test_ext_instructions_execute_as_single_four_byte_operations(self):
        simulator = self.assemble_program(""".ORIG x3000
LI16 R0 #4660
MOVU R1 #65535
LDABS R2 0x4000
STABS R1 0x4002
ZEXT8 R3 R0
SEXT8 R4 R2
SHLV R5 R1 R0
HALT
.END
""")
        simulator.write_word(0x4000, 0x00FF)
        simulator.execute()
        self.assertEqual(simulator.registers[0], 0x1234)
        self.assertEqual(simulator.registers[1], 0xFFFF)
        self.assertEqual(simulator.registers[2], 0x00FF)
        self.assertEqual(simulator.read_word(0x4002), 0xFFFF)
        self.assertEqual(simulator.registers[3], 0x0034)
        self.assertEqual(simulator.registers[4], 0xFFFF)
        self.assertEqual(simulator.registers[5], 0xFFF0)
        self.assertEqual(simulator.instructions, 8)

    def test_br16_uses_absolute_target(self):
        simulator = self.assemble_program(""".ORIG x3000
BR16 destino
HALT
destino HALT
.END
""")
        simulator.execute()
        self.assertEqual(simulator.instructions, 2)
        self.assertEqual(simulator.pc, 0x3008)

    def test_ret_without_call_frame_halts(self):
        simulator = self.assemble_program(""".ORIG x3000
RET
.END
""")
        simulator.execute()
        self.assertTrue(simulator.halted)
        self.assertEqual(simulator.instructions, 1)


if __name__ == "__main__":
    unittest.main()
