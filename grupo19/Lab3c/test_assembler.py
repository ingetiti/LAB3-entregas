import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from assembler import Assembler, AssemblyImage, _hex_bytes, main


class AssemblerTests(unittest.TestCase):
    def assemble_text(self, text: str, root: Path) -> AssemblyImage:
        source = root / "main.asm"
        source.write_text(text, encoding="utf-8")
        return Assembler().assemble(source)

    def test_binary_header_and_machine_words(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            image = self.assemble_text(
                ".ORIG x3000\n"
                ".STACK xE000\n"
                "MOVI R0, #5\n"
                "NOP\n"
                "HALT\n"
                ".END\n",
                Path(temporary),
            )

        self.assertEqual(image.object_bytes()[:4], b"\x00\x30\x00\xE0")
        self.assertEqual(
            image.image,
            bytes.fromhex("05 30 80 03 25 C0"),
        )

    def test_byte_data_is_padded_before_word_data_and_instruction(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            image = self.assemble_text(
                ".ORIG x3000\n"
                ".BYTE x41\n"
                "DATA: .FILL x1234\n"
                "NEXT: MOVI R1, #1\n"
                ".END\n",
                Path(temporary),
            )

        self.assertEqual(image.symbols["data"], 0x3002)
        self.assertEqual(image.symbols["next"], 0x3004)
        self.assertEqual(image.image, bytes.fromhex("41 00 34 12 01 31"))

    def test_external_module_is_linked_and_its_origin_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "helper.asm").write_text(
                ".ORIG x5000\n"
                "EXPORTED: HALT\n"
                ".END\n",
                encoding="utf-8",
            )
            image = self.assemble_text(
                ".ORIG x3000\n"
                ".EXTERNAL helper-EXPORTED\n"
                "JSR EXPORTED\n"
                ".END\n",
                root,
            )

        self.assertEqual(image.symbols, {})
        self.assertEqual(image.image, bytes.fromhex("00 A8 25 C0"))

    def test_long_conditional_branch_relaxes_to_jmpm_sequence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            image = self.assemble_text(
                ".ORIG x3000\n"
                "BRZ TARGET\n"
                ".BLKB 300\n"
                "TARGET: HALT\n"
                ".END\n",
                Path(temporary),
            )

        self.assertEqual(image.image[:6], bytes.fromhex("82 02 00 D0 32 31"))
        self.assertEqual(image.symbols["target"], 0x3132)

    def test_long_call_returns_past_its_inline_target_word(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            image = self.assemble_text(
                ".ORIG x3000\n"
                "JSR TARGET\n"
                ".BLKB 3000\n"
                "TARGET: RET\n"
                ".END\n",
                Path(temporary),
            )

        self.assertEqual(image.image[:6], bytes.fromhex("01 D8 01 00 BE 3B"))
        self.assertEqual(image.symbols["target"], 0x3BBE)

    def test_distant_pc_load_uses_indirect_pointer_and_skips_literal(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            image = self.assemble_text(
                ".ORIG x3000\n"
                "LDPC R2, DATA\n"
                ".BLKB 300\n"
                "DATA: .FILL x1234\n"
                ".END\n",
                Path(temporary),
            )

        self.assertEqual(image.image[:6], bytes.fromhex("01 E2 01 00 32 31"))
        self.assertEqual(image.symbols["data"], 0x3132)

    def test_unary_function_bits_match_the_isa_format(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            image = self.assemble_text(
                ".ORIG x3000\n"
                "NOT R0, R1\n"
                "NEG R2, R3\n"
                ".END\n",
                Path(temporary),
            )

        self.assertEqual(image.image, bytes.fromhex("20 20 68 22"))

    def test_li_loads_signed_low_byte_then_high_byte(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            image = self.assemble_text(
                ".ORIG x3000\n"
                "LI R0, xABCD\n"
                ".END\n",
                Path(temporary),
            )
        self.assertEqual(image.image, bytes.fromhex("CD 30 AB 38"))

    def test_hex_output_is_the_binary_object_as_byte_pairs(self) -> None:
        raw = bytes.fromhex("00 30 FE FF 01 02")
        self.assertEqual(_hex_bytes(raw), "00 30 FE FF 01 02\n")

    def test_cli_writes_all_requested_formats(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "main.asm"
            source.write_text(".ORIG x3000\nHALT\n.END\n", encoding="utf-8")
            for output_format, suffix in (("bin", ".bin"), ("hex", ".hex"), ("asm", ".asm")):
                output = root / f"result{suffix}"
                with redirect_stdout(StringIO()):
                    result = main([str(source), "--format", output_format, "-o", str(output)])
                self.assertEqual(result, 0)
                self.assertTrue(output.is_file())
            self.assertEqual((root / "result.bin").read_bytes()[:4], b"\x00\x30\xFE\xFF")
            self.assertTrue((root / "result.hex").read_text(encoding="ascii").startswith("00 30 FE FF"))
            self.assertIn("HALT", (root / "result.asm").read_text(encoding="utf-8"))

    def test_odd_byte_address_forces_lea_absolute_load(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            image = self.assemble_text(
                ".ORIG x3000\n"
                "LEA R0, TEXT\n"
                ".BYTE x41\n"
                "TEXT: .BYTE x42\n"
                ".END\n",
                Path(temporary),
            )

        self.assertEqual(image.symbols["text"], 0x3005)
        self.assertEqual(image.image[:4], bytes.fromhex("05 30 30 38"))

    def test_documented_instruction_and_pseudo_op_surface_assembles(self) -> None:
        source = """
.ORIG x3000
.STACK xE000
START: BRNZP START
ADD R0, R1, R2
SUB R0, R1, R2
ADC R0, R1, R2
SBC R0, R1, R2
AND R0, R1, R2
OR R0, R1, R2
XOR R0, R1, R2
CMP R1, R2
ANDI R0, R1, #-1
ADDI R0, R1, #1
NOT R0, R1
NEG R0, R1
MOVI R0, #-1
MOVH R0, xAA
SHL R0, R1, #15
LSR R0, R1, #1
ASR R0, R1, #1
RRC R0, R1
RLC R0, R1
SHLV R0, R1, R2
SRLV R0, R1, R2
SRAV R0, R1, R2
ROLV R0, R1, R2
LDBL R0, R1, #-1
LDBS R0, R1, #1
LDBH R0, R1, #1
STBL R0, R1, #1
STBH R0, R1, #1
LDW R0, R1, #16
STW R0, R1, #31
LDW16 R0, R1, #0
STW16 R0, R1, #31
LDPC R0, DATA
STPC R0, DATA
LDPM R0, POINTER
STPM R0, POINTER
LEA R0, DATA
JSR START
JMP R0
JSRR R0
RET
PUSHM {R0, R7}
POPM {R0, R7}
POPR {R0, R7}
JMPM POINTER
JSRM POINTER
TRAP x25
GETC
OUT
PUTS
IN
HALT
MOV R0, R1
CLR R0
INC R0
DEC R0
LI R0, x1234
PUSH R0
POP R0
NOP
LD R0, DATA
ST R0, DATA
LDR R0, R1, #2
STR R0, R1, #2
DATA: .FILL x1234
POINTER: .FILL START
.END
"""
        with tempfile.TemporaryDirectory() as temporary:
            image = self.assemble_text(source, Path(temporary))

        self.assertGreater(len(image.image), 100)
        self.assertEqual(image.origin, 0x3000)
        self.assertIn("LDW16", image.listing)


if __name__ == "__main__":
    unittest.main()
