import unittest
import tempfile
from pathlib import Path

from assembler import Assembler, AssemblyError, OPCODES, write_output


class AssemblerTests(unittest.TestCase):
    def assemble_text(self, text):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "test.asm"
            source.write_text(text, encoding="utf-8")
            assembler = Assembler()
            memory = assembler.assemble([source])
            return assembler, memory

    def test_rrr_and_relative_branch_encoding(self):
        assembler, memory = self.assemble_text(""".ORIG x3000
start ADD R1 R2 R3
      BRz start
      HALT
.END
""")
        word_add = memory[0x3000] | (memory[0x3001] << 8)
        word_br = memory[0x3002] | (memory[0x3003] << 8)
        self.assertEqual(word_add, (0 << 11) | (1 << 8) | (2 << 5) | (3 << 2))
        self.assertEqual(word_br, (22 << 11) | (2 << 8) | 0xFC)

    def test_immediate_and_memory_encoding(self):
        assembler, memory = self.assemble_text(""".ORIG x3000
MOV R0 #-5
LOAD R1 4(R6)
STOREL R2 -2(R3)
.END
""")
        mov = memory[0x3000] | (memory[0x3001] << 8)
        load = memory[0x3002] | (memory[0x3003] << 8)
        store = memory[0x3004] | (memory[0x3005] << 8)
        self.assertEqual(mov, (7 << 11) | (0 << 8) | 0xFB)
        self.assertEqual(load, (18 << 11) | (1 << 8) | (6 << 5) | 4)
        self.assertEqual(store, (19 << 11) | (2 << 8) | (3 << 5) | 0x1E)

    def test_odd_byte_inserts_padding_before_instruction(self):
        assembler, memory = self.assemble_text(""".ORIG x3000
.BYTE 0x41
NOP
.END
""")
        self.assertEqual(memory[0x3000], 0x41)
        self.assertEqual(memory[0x3001], 0)
        nop = memory[0x3002] | (memory[0x3003] << 8)
        self.assertEqual(nop, 27 << 11)
        self.assertEqual(len(assembler.paddings), 1)

    def test_external_and_fill_reference(self):
        assembler, memory = self.assemble_text(""".ORIG x3000
.EXTERNAL util-EXTERNAL_FUNC
.FILL 0
.END
""")
        self.assertIn("EXTERNAL_FUNC", assembler.externals)

    def test_external_symbol_resolves_across_modules(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            main = root / "main.asm"
            lib = root / "lib.asm"
            main.write_text(""".ORIG x3000
.EXTERNAL lib-FUNC
JSR FUNC
HALT
.END
""", encoding="utf-8")
            lib.write_text(""".ORIG x3080
FUNC NOP
RET
.END
""", encoding="utf-8")
            assembler = Assembler()
            memory = assembler.assemble([main, lib])
            jsr = memory[0x3000] | (memory[0x3001] << 8)
            self.assertEqual(jsr, (23 << 11) | ((0x3080 - 0x3002) & 0xff))

    def test_binary_output_has_origin_prefix(self):
        assembler, memory = self.assemble_text(""".ORIG x3000
NOP
.END
""")
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "program.bin"
            write_output(output, memory, assembler.origins[0], "bin")
            data = output.read_bytes()
            self.assertEqual(data[:2], b'\x00\x30')
            self.assertEqual(data[2:4], b'\x00\xD8')

    def test_jsr_direct_and_jsrr_register_encoding(self):
        assembler, memory = self.assemble_text(""".ORIG x3000
JSR target
JSRR R2
HALT
target NOP
.END
""")
        jsr = memory[0x3000] | (memory[0x3001] << 8)
        jsrr = memory[0x3002] | (memory[0x3003] << 8)
        self.assertEqual(((jsr >> 8) & 7), 0)
        self.assertEqual((jsrr >> 10) & 1, 1)
        self.assertEqual((jsrr >> 5) & 7, 2)

    def test_bare_ret_and_jsr_label_starting_with_r(self):
        assembler, memory = self.assemble_text(""".ORIG x3000
JSR REDUCE_NATIVE
HALT
REDUCE_NATIVE RET
.END
""")
        jsr = memory[0x3000] | (memory[0x3001] << 8)
        ret = memory[0x3004] | (memory[0x3005] << 8)
        self.assertEqual((jsr >> 11) & 31, 23)
        self.assertEqual((ret >> 11) & 31, 25)
        self.assertEqual((ret >> 5) & 7, 7)

    def test_multiple_globals_are_exported(self):
        assembler, memory = self.assemble_text(""".ORIG x3000
.GLOBAL FUNC_ONE, FUNC_TWO
FUNC_ONE NOP
FUNC_TWO RET
.END
""")
        self.assertIn("FUNC_ONE", assembler.globals)
        self.assertIn("FUNC_TWO", assembler.globals)
        self.assertIn("FUNC_ONE", assembler.symbols)
        self.assertIn("FUNC_TWO", assembler.symbols)

    def test_global_and_external_fill_resolve(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            main = root / "main.asm"
            lib = root / "lib.asm"
            main.write_text(""".ORIG x3000
.EXTERNAL lib-FUNC
.FILL FUNC
HALT
.END
""", encoding="utf-8")
            lib.write_text(""".ORIG x3100
.GLOBAL FUNC
FUNC RET
.END
""", encoding="utf-8")
            assembler = Assembler()
            memory = assembler.assemble([main, lib])
            self.assertIn("FUNC", assembler.globals)
            self.assertIn("FUNC", assembler.symbols)
            self.assertEqual(memory[0x3000] | (memory[0x3001] << 8), 0x3100)

    def test_unresolved_external_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "bad.asm"
            source.write_text(""".ORIG x3000
.EXTERNAL lib-MISSING
JSR MISSING
.END
""", encoding="utf-8")
            with self.assertRaises(AssemblyError):
                Assembler().assemble([source])

    def test_stringz_odd_padding_before_next_instruction(self):
        assembler, memory = self.assemble_text(""".ORIG x3000
.STRINGZ \"AB\"
NOP
.END
""")
        self.assertEqual(memory[0x3000], ord("A"))
        self.assertEqual(memory[0x3001], ord("B"))
        self.assertEqual(memory[0x3002], 0)
        self.assertEqual(memory[0x3003], 0)
        nop = memory[0x3004] | (memory[0x3005] << 8)
        self.assertEqual(nop, 27 << 11)
        self.assertEqual(len(assembler.paddings), 1)

    def test_decimal_output_format(self):
        assembler, memory = self.assemble_text(""".ORIG x3000
NOP
HALT
.END
""")
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "program.dec"
            write_output(output, memory, assembler.origins[0], "dec")
            values = [int(token) for token in output.read_text(encoding="ascii").split()]
            self.assertEqual(values[:2], [0x00, 0x30])
            self.assertEqual(values[2], 0x00)
            self.assertEqual(values[3], 0xD8)

    def test_cmp_three_operand_uses_extended_rrr_mode(self):
        assembler, memory = self.assemble_text(""".ORIG x3000
CMP R0 R1 R2
.END
""")
        word = memory[0x3000] | (memory[0x3001] << 8)
        self.assertEqual(word, (6 << 11) | (0 << 8) | (1 << 5) | (2 << 2) | 2)

    def test_ext_instructions_occupy_two_words_and_advance_labels(self):
        assembler, memory = self.assemble_text(""".ORIG x3000
LI16 R0 #4660
MOVU R1 #65535
ADD R0 R0 #1
HALT
.END
""")
        li16 = memory[0x3000] | (memory[0x3001] << 8)
        movu = memory[0x3004] | (memory[0x3005] << 8)
        add = memory[0x3008] | (memory[0x3009] << 8)
        self.assertEqual(li16, (31 << 11) | (0 << 8) | 0x00)
        self.assertEqual(memory[0x3002] | (memory[0x3003] << 8), 4660)
        self.assertEqual(movu, (31 << 11) | (1 << 8) | 0x00)
        self.assertEqual(memory[0x3006] | (memory[0x3007] << 8), 65535)
        self.assertEqual(add, (0 << 11) | (0 << 8) | 1 | (1 << 1))

    def test_br16_target_accounts_for_four_byte_instruction(self):
        assembler, memory = self.assemble_text(""".ORIG x3000
BR16 done
HALT
done HALT
.END
""")
        br16 = memory[0x3000] | (memory[0x3001] << 8)
        self.assertEqual(br16, (31 << 11) | 0x0C)
        self.assertEqual(memory[0x3002] | (memory[0x3003] << 8), 0x3006)

    def test_peephole_fuses_mov_and_shift_into_li16(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "test.asm"
            source.write_text(""".ORIG x3000
MOV R0 #4
SHL R0 R0 #8
HALT
.END
""", encoding="utf-8")
            assembler = Assembler(peephole=True)
            memory = assembler.assemble([source])
        first = memory[0x3000] | (memory[0x3001] << 8)
        self.assertEqual(first, (31 << 11) | (0 << 8) | 0x00)
        self.assertEqual(memory[0x3002] | (memory[0x3003] << 8), 0x0400)
        self.assertEqual(memory[0x3004] | (memory[0x3005] << 8), 26 << 11)

    def test_mov_rejects_unsigned_eight_bit_immediate(self):
        with self.assertRaises(AssemblyError):
            self.assemble_text(""".ORIG x3000
MOV R0 #255
.END
""")

    def test_missing_orig_defaults_to_x3000(self):
        assembler, memory = self.assemble_text("""start ADD R0 R0 #1
      HALT
.END
""")
        self.assertEqual(assembler.origins, [0x3000])
        self.assertEqual(assembler.symbols["start"], 0x3000)
        self.assertIn(0x3000, memory)
        self.assertIn(0x3002, memory)

    def test_late_orig_keeps_implicit_code_origin(self):
        assembler, memory = self.assemble_text("""start ADD R0 R0 #1
      HALT
.ORIG x3300
value .FILL x1234
.END
""")
        self.assertEqual(assembler.origins, [0x3000, 0x3300])
        self.assertEqual(assembler.symbols["start"], 0x3000)
        self.assertEqual(assembler.symbols["value"], 0x3300)
        self.assertEqual(memory[0x3300], 0x34)
        self.assertEqual(memory[0x3301], 0x12)

    def test_real_routines_assemble_without_explicit_initial_origin(self):
        source = Path(__file__).parent / "benchmark" / "real_routines.asm"
        assembler = Assembler()
        memory = assembler.assemble([source])
        self.assertEqual(assembler.origins[0], 0x3000)
        self.assertIn(0x3300, memory)
        self.assertIn(0x3400, memory)


if __name__ == "__main__":
    unittest.main()
