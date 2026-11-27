import random
import tempfile
import unittest
from pathlib import Path

from lc10 import isa
from lc10.assembler import AsmError, assemble, format_listing
from lc10.image import Image, ImageError


def asm(text, name="prog.asm"):
    return assemble([(name, text)])


def words(res):
    return res.image.words()


def random_fields(rnd, name):
    """Campos válidos al azar para una instrucción."""
    _, fmt = isa.BY_NAME[name]
    reg = lambda: rnd.randrange(8)
    if fmt == "BR":
        return {"n": rnd.randrange(2), "z": rnd.randrange(2), "p": rnd.randrange(2), "off": rnd.randint(-128, 127)}
    if fmt == "BRX":
        return {"cond": rnd.randrange(8), "off": rnd.randint(-128, 127)}
    if fmt in ("ALU", "CMP"):
        f = {"sr1": reg()}
        if fmt == "ALU":
            f["dr"] = reg()
        if rnd.random() < 0.5:
            f["mode"], f["src"] = "r", reg()
        else:
            f["mode"], f["src"] = "i", rnd.randint(-8, 7)
        return f
    if fmt == "UN":
        return {"dr": reg(), "sr": reg()}
    if fmt == "MD":
        return {"dr": reg(), "sr1": reg(), "sr2": reg()}
    if fmt == "X":
        if name in ("PUSH", "POP"):
            return {"mask": rnd.choice([m for m in range(1, 256) if not m >> isa.SP & 1])}
        dr = reg()
        return {"dr": dr, "sr1": rnd.choice([r for r in range(8) if r != dr]), "sr2": reg()}
    if fmt == "SH":
        f = {"dr": reg(), "sr1": reg()}
        if rnd.random() < 0.5:
            f["mode"], f["src"] = "r", reg()
        else:
            f["mode"], f["src"] = "i", rnd.randint(0, 15)
        return f
    if fmt == "ROTC":
        return {"dr": reg(), "sr": reg(), "right": rnd.randrange(2)}
    if fmt in ("MEMW", "MEMB"):
        return {"reg": reg(), "base": reg(), "off": rnd.randint(-16, 15)}
    if fmt == "PCREL":
        return {"reg": reg(), "off": rnd.randint(-128, 127)}
    if fmt == "MOVI":
        return {"dr": reg(), "imm": rnd.randint(-128, 127)}
    if fmt == "JSR":
        return {"off": rnd.randint(-1024, 1023)}
    if fmt == "JR":
        return {"link": rnd.randrange(2), "base": reg()}
    if fmt == "TRAP":
        return {"vect": rnd.randrange(256)}
    raise AssertionError(fmt)


class TestIsa(unittest.TestCase):
    def test_encode_decode_roundtrip(self):
        rnd = random.Random(1)
        for name, _, _ in isa.INSTRUCTIONS:
            for _ in range(300):
                f = random_fields(rnd, name)
                w = isa.encode(name, **f)
                self.assertEqual(w >> 11, isa.BY_NAME[name][0], "el opcode ocupa los bits 15..11")
                n2, f2 = isa.decode(w)
                self.assertEqual((n2, f2), (name, f))

    def test_opcodes_unique_and_5_bits(self):
        """Un opcode por instrucción, salvo los formatos MD y X, donde varias comparten opcode y se distinguen por fn."""
        plain = [op for _, op, fmt in isa.INSTRUCTIONS if fmt not in ("MD", "X")]
        self.assertEqual(len(plain), len(set(plain)))
        md = [(op, isa.MD_FN[n]) for n, op, fmt in isa.INSTRUCTIONS if fmt == "MD"]
        self.assertEqual(len(md), len(set(md)), "cada (opcode, fn) debe ser único")
        x = [(op, isa.X_FN[n]) for n, op, fmt in isa.INSTRUCTIONS if fmt == "X"]
        self.assertEqual(sorted(x), [(31, 0), (31, 1), (31, 2), (31, 3)])
        self.assertFalse(set(op for op, _ in md + x) & set(plain), "los opcodes MD y X no se comparten con otros formatos")
        codes = plain + [op for op, _ in md + x]
        self.assertTrue(all(0 <= c < 32 for c in codes))
        self.assertEqual(isa.RESERVED_FROM, max(codes) + 1)
        self.assertEqual(len(set(codes)), 32, "los 32 opcodes en uso")

    def test_md_encoding_layout_and_reserved_variant(self):
        # MUL R1, R2, R3: opcode 29, DR=1, SR1=2, fn=0, SR2=3
        self.assertEqual(isa.encode("MUL", dr=1, sr1=2, sr2=3), 29 << 11 | 1 << 8 | 2 << 5 | 0 << 3 | 3)
        self.assertEqual(isa.encode("REMU", dr=7, sr1=6, sr2=5), 30 << 11 | 7 << 8 | 6 << 5 | 3 << 3 | 5)
        with self.assertRaises(isa.IsaError):                # opcode 29, fn = 3: reservado
            isa.decode(29 << 11 | 3 << 3)
        self.assertEqual(isa.disassemble(29 << 11 | 3 << 3), f".FILL x{29 << 11 | 3 << 3:04X}")

    def test_reserved_opcodes_and_nop(self):
        for op in range(isa.RESERVED_FROM, 32):
            with self.assertRaises(isa.IsaError):
                isa.decode(op << 11)
        self.assertEqual(isa.decode(0x0000)[1], {"n": 0, "z": 0, "p": 0, "off": 0})

    def test_field_range_errors(self):
        with self.assertRaises(isa.IsaError):
            isa.encode("ADD", dr=8, sr1=0, mode="r", src=0)
        with self.assertRaises(isa.IsaError):
            isa.encode("ADD", dr=0, sr1=0, mode="i", src=8)
        with self.assertRaises(isa.IsaError):
            isa.encode("SHL", dr=0, sr1=0, mode="i", src=16)
        with self.assertRaises(isa.IsaError):
            isa.encode("MOVI", dr=0, imm=128)
        with self.assertRaises(isa.IsaError):
            isa.encode("BR", n=1, z=1, p=1, off=128)

    def test_disassemble_assemble_roundtrip(self):
        """Desensamblar y volver a ensamblar da la misma palabra."""
        rnd = random.Random(2)
        for name, _, _ in isa.INSTRUCTIONS:
            for _ in range(200):
                f = random_fields(rnd, name)
                # MEMW: el assembly escribe el offset en bytes (par)
                w = isa.encode(name, **f)
                text = isa.disassemble(w, 0x3000)
                res = asm(f".ORIG x3000\n{text}\n.END\n")
                self.assertEqual(words(res), [w], f"{name}: {text}")


class TestOpcode31(unittest.TestCase):
    def test_layout(self):
        # [15:11] = 31, [10:9] = fn, [8] = 0, [7:0] = máscara (bit r = Rr)
        self.assertEqual(isa.encode("PUSH", mask=0b10100110), 31 << 11 | 0 << 9 | 0b10100110)
        self.assertEqual(isa.encode("POP", mask=0b00000001), 31 << 11 | 1 << 9 | 1)
        # DIVREM*: [8:6] = DR, [5:3] = SR1, [2:0] = SR2
        self.assertEqual(isa.encode("DIVREMU", dr=5, sr1=0, sr2=4), 31 << 11 | 2 << 9 | 5 << 6 | 0 << 3 | 4)
        self.assertEqual(isa.encode("DIVREM", dr=1, sr1=2, sr2=3), 31 << 11 | 3 << 9 | 1 << 6 | 2 << 3 | 3)

    def test_reserved_combinations(self):
        for w in (31 << 11,                               # PUSH sin registros
                  31 << 11 | 1 << 9,                      # POP sin registros
                  31 << 11 | 1 << 8 | 1,                  # bit 8 en PUSH
                  31 << 11 | 1 << 6,                      # PUSH R6: es el puntero de pila
                  31 << 11 | 2 << 9 | 3 << 6 | 3 << 3):   # DIVREMU con DR = SR1
            with self.subTest(w=hex(w)):
                with self.assertRaises(isa.IsaError):
                    isa.decode(w)
                self.assertEqual(isa.disassemble(w), f".FILL x{w:04X}")
        for bad in ({"mask": 0}, {"mask": 1 << 6}, {"mask": 256}):
            with self.assertRaises(isa.IsaError):
                isa.encode("PUSH", **bad)
        with self.assertRaises(isa.IsaError):
            isa.encode("DIVREMU", dr=2, sr1=2, sr2=1)

    def test_register_lists(self):
        def w(text):
            return words(asm(f".ORIG x3000\n{text}\n.END\n"))[0]
        self.assertEqual(w("PUSH R1-R5"), isa.encode("PUSH", mask=0b00111110))
        self.assertEqual(w("PUSH R1, R2, R3, R4, R5"), w("PUSH R1-R5"))
        self.assertEqual(w("POP R0, R2-R3, R7"), isa.encode("POP", mask=0b10001101))
        self.assertEqual(w("push r7"), isa.encode("PUSH", mask=0x80))
        self.assertEqual(isa.disassemble(w("PUSH R0-R2, R4, R5, R7")), "PUSH R0-R2, R4, R5, R7")
        self.assertEqual(isa.disassemble(w("POP R3")), "POP R3")
        for bad in ("PUSH", "PUSH R6", "PUSH R1-R7", "PUSH R2, R2", "PUSH R1-R3, R3", "PUSH R5-R1", "POP #3",
                    "DIVREMU R1, R1, R2", "DIVREMU R1, R2", "DIVREM R1, R2, #3"):
            with self.subTest(bad=bad), self.assertRaises(AsmError):
                asm(f".ORIG x3000\n{bad}\n.END\n")


class TestMdAssembly(unittest.TestCase):
    def test_mnemonics_assemble_to_the_encoder_words(self):
        res = asm(".ORIG x3000\nMUL R1, R2, R3\nMULH R4, R5, R6\nMULHU R0, R0, R0\nDIV R1, R2, R3\n"
                  "DIVU R1, R2, R3\nREM R7, R7, R7\nREMU R1, R2, R3\n.END\n")
        self.assertEqual(words(res), [isa.encode("MUL", dr=1, sr1=2, sr2=3), isa.encode("MULH", dr=4, sr1=5, sr2=6),
                                      isa.encode("MULHU", dr=0, sr1=0, sr2=0), isa.encode("DIV", dr=1, sr1=2, sr2=3),
                                      isa.encode("DIVU", dr=1, sr1=2, sr2=3), isa.encode("REM", dr=7, sr1=7, sr2=7),
                                      isa.encode("REMU", dr=1, sr1=2, sr2=3)])

    def test_operand_errors(self):
        for bad in ("MUL R1, R2", "MUL R1, R2, #3", "DIV R1, R2, R3, R4", "REM R1"):
            with self.assertRaises(AsmError, msg=bad):
                asm(f".ORIG x3000\n{bad}\n.END\n")


class TestAssembler(unittest.TestCase):
    def test_basic_program_and_origin(self):
        res = asm(".ORIG x4000\nMOVI R1, #5\nHALT\n.END\n")
        self.assertEqual(res.image.origin, 0x4000)
        self.assertEqual(words(res), [isa.encode("MOVI", dr=1, imm=5), isa.encode("TRAP", vect=0x25)])

    def test_alignment_padding_and_label_binding(self):
        src = """.ORIG x3000
            MOVI R0, #1
        DATO    .BYTE 7
        AQUI    MOVI R1, #2        ; el dato deja el contador impar: debe haber relleno
            BR AQUI
            .END"""
        res = asm(src)
        self.assertEqual(res.pad_bytes, 1)
        self.assertEqual(res.symbols["PROG-DATO"], 0x3002)
        self.assertEqual(res.symbols["PROG-AQUI"], 0x3004, "la etiqueta apunta a la instrucción, no al relleno")
        self.assertEqual(res.image.data[2:4], bytes([7, 0]))
        # BR AQUI desde x3006: destino x3004 => offset -2 (PC+2 = x3008)
        self.assertEqual(words(res)[-1], isa.encode("BR", n=1, z=1, p=1, off=-2))

    def test_label_on_its_own_line_before_instruction_after_odd_bytes(self):
        res = asm(".ORIG x3000\n.BYTE 1\nL1\nMOVI R0, #1\n.END\n")
        self.assertEqual(res.symbols["PROG-L1"], 0x3002)

    def test_stringz_and_fill_after_odd_string(self):
        res = asm('.ORIG x3000\nS .STRINGZ "abc"\nW .FILL x1234\n.END\n')
        self.assertEqual(res.image.data, b"abc\0" + bytes([0x34, 0x12]))   # 4 bytes: ya es par, sin relleno
        res = asm('.ORIG x3000\nS .STRINGZ "ab"\nW .FILL x1234\n.END\n')
        self.assertEqual(res.symbols["PROG-W"], 0x3004)
        self.assertEqual(res.image.data, b"ab\0\0" + bytes([0x34, 0x12]))
        self.assertEqual(res.pad_bytes, 1)

    def test_string_escapes_and_comment_inside_string(self):
        res = asm('.ORIG x3000\nS .STRINGZ "a;b\\n\\"q\\""\n.END\n')
        self.assertEqual(res.image.data, b'a;b\n"q"\0')

    def test_blkw_blkb_byte_align(self):
        res = asm(".ORIG x3000\n.BLKB 3\nA .ALIGN\nB .BLKW 2\nC .BYTE 1, 2, -1\n.END\n")
        self.assertEqual(res.symbols["PROG-A"], 0x3004)
        self.assertEqual(res.symbols["PROG-B"], 0x3004)
        self.assertEqual(res.symbols["PROG-C"], 0x3008)
        self.assertEqual(res.image.data[-4:], bytes([1, 2, 255, 0]))

    def test_number_formats(self):
        res = asm(".ORIG x3000\n.FILL #-1\n.FILL x00FF\n.FILL 0x10\n.FILL 0b101\n.FILL 7\n.END\n")
        self.assertEqual(words(res), [0xFFFF, 0xFF, 0x10, 5, 7])

    def test_branch_variants(self):
        res = asm(""".ORIG x3000
        L   BRn L
            BRz L
            BRp L
            BRnz L
            BRnp L
            BRzp L
            BRnzp L
            BR L
            BRC L
            BRNC L
            BRV L
            BRNV L
            BRLT L
            BRGE L
            BRGT L
            BRLE L
            NOP
        .END""")
        w = words(res)
        flags = [(1, 0, 0), (0, 1, 0), (0, 0, 1), (1, 1, 0), (1, 0, 1), (0, 1, 1), (1, 1, 1), (1, 1, 1)]
        for i, (n, z, p) in enumerate(flags):
            self.assertEqual(w[i], isa.encode("BR", n=n, z=z, p=p, off=-(i + 1)))
        for i, cond in enumerate(range(8)):
            self.assertEqual(w[8 + i], isa.encode("BRX", cond=cond, off=-(8 + i + 1)))
        self.assertEqual(w[16], 0x0000)

    def test_pseudo_ops(self):
        res = asm(".ORIG x3000\nRET\nJMP R3\nJSRR R4\nRCL R1, R2\nRCR R1, R2\nMOV R1, R2\nCLR R5\nTST R2\nGETC\nOUT\nPUTS\nIN\nHALT\n.END\n")
        self.assertEqual(words(res), [
            isa.encode("JR", link=0, base=7), isa.encode("JR", link=0, base=3), isa.encode("JR", link=1, base=4),
            isa.encode("ROTC", dr=1, sr=2, right=0), isa.encode("ROTC", dr=1, sr=2, right=1),
            isa.encode("OR", dr=1, sr1=2, mode="r", src=2), isa.encode("MOVI", dr=5, imm=0),
            isa.encode("OR", dr=2, sr1=2, mode="r", src=2),
            *[isa.encode("TRAP", vect=v) for v in (0x20, 0x21, 0x22, 0x23, 0x25)]])

    def test_memory_offsets_in_bytes(self):
        res = asm(".ORIG x3000\nLDW R1, R2, #4\nSTW R1, R2, #-6\nLDL R1, R2, #-3\nSTH R1, R2\n.END\n")
        self.assertEqual(words(res), [
            isa.encode("LDW", reg=1, base=2, off=2), isa.encode("STW", reg=1, base=2, off=-3),
            isa.encode("LDL", reg=1, base=2, off=-3), isa.encode("STH", reg=1, base=2, off=0)])
        with self.assertRaises(AsmError):
            asm(".ORIG x3000\nLDW R1, R2, #3\n.END\n")       # offset de palabra impar
        with self.assertRaises(AsmError):
            asm(".ORIG x3000\nLDW R1, R2, #32\n.END\n")      # fuera de ±30 bytes

    def test_lea_reaches_odd_byte_addresses(self):
        res = asm(".ORIG x3000\nLEA R0, D\nHALT\n.BYTE 1\nD .BYTE 2\n.END\n")
        self.assertEqual(res.symbols["PROG-D"] % 2, 1)
        self.assertEqual(words(res)[0], isa.encode("LEA", reg=0, off=res.symbols["PROG-D"] - 0x3002))

    def test_listing_contains_addresses_and_words(self):
        res = asm(".ORIG x3000\nMOVI R1, #5\nHALT\n.END\n")
        txt = format_listing(res)
        self.assertIn("x3000  C905  MOVI R1, #5", txt)

    def test_external_linking_between_modules(self):
        main = """.ORIG x3000
        .EXTERNAL SUMA-SUMAR
            MOVI R0, #2
            MOVI R1, #3
            JSR SUMA-SUMAR
            LD R5, PTR
            JSRR R5
            HALT
        PTR .FILL SUMA-SUMAR
        .END"""
        mod = """.EXTERNAL OTRO-X
        SUMAR   ADD R0, R0, R1
                RET
        .END"""
        with self.assertRaises(AsmError):          # falta el módulo OTRO
            assemble([("main.asm", main), ("suma.asm", mod)])
        mod = mod.replace(".EXTERNAL OTRO-X\n", "")
        res = assemble([("main.asm", main), ("suma.asm", mod)])
        sumar = res.symbols["SUMA-SUMAR"]
        self.assertEqual(sumar, 0x3000 + 2 * 6 + 2)
        self.assertEqual(words(res)[6], sumar)     # el .FILL lleva la dirección absoluta
        self.assertEqual([m[0] for m in res.modules], ["MAIN", "SUMA"])

    def test_assembler_errors(self):
        bad = {
            "falta .END": ".ORIG x3000\nHALT\n",
            "falta .ORIG": "HALT\n.END\n",
            "etiqueta no definida": ".ORIG x3000\nBR NADA\n.END\n",
            "etiqueta repetida": ".ORIG x3000\nA HALT\nA HALT\n.END\n",
            "registro inválido": ".ORIG x3000\nADD R8, R0, R0\n.END\n",
            "imm4 fuera de rango": ".ORIG x3000\nADD R1, R1, #8\n.END\n",
            "instrucción desconocida": ".ORIG x3000\nFOO R1\n.END\n",
            "directiva desconocida": ".ORIG x3000\n.FOO 1\n.END\n",
            "texto tras .END": ".ORIG x3000\nHALT\n.END\nHALT\n",
            ".ORIG impar": ".ORIG x3001\nHALT\n.END\n",
            ".FILL fuera de rango": ".ORIG x3000\n.FILL #70000\n.END\n",
            "qualified sin .EXTERNAL": ".ORIG x3000\nJSR A-B\n.END\n",
            "dato impar con LD": ".ORIG x3000\nLD R0, D\nHALT\n.BYTE 1\nD .BYTE 2\n.END\n",
            "branch lejano": ".ORIG x3000\nBR FIN\n.BLKW 200\nFIN HALT\n.END\n",
            "operandos de más": ".ORIG x3000\nNOT R1, R2, R3\n.END\n",
        }
        for why, src in bad.items():
            with self.subTest(why):
                with self.assertRaises(AsmError):
                    asm(src)

    def test_module_with_orig_is_error(self):
        with self.assertRaises(AsmError):
            assemble([("main.asm", ".ORIG x3000\nHALT\n.END\n"), ("m.asm", ".ORIG x4000\nRET\n.END\n")])

    def test_error_message_has_file_and_line(self):
        with self.assertRaises(AsmError) as cm:
            asm(".ORIG x3000\nHALT\nBR NADA\n.END\n", name="x.asm")
        self.assertIn("x.asm:3:", str(cm.exception))

    def test_jsr_out_of_range_suggests_jsrr(self):
        with self.assertRaises(AsmError) as cm:
            asm(".ORIG x3000\nJSR LEJOS\n.BLKW 1100\nLEJOS RET\n.END\n")
        self.assertIn("JSRR", str(cm.exception))


class TestImageFormats(unittest.TestCase):
    def test_roundtrip_all_formats(self):
        res = asm('.ORIG x3000\nMOVI R1, #5\nS .STRINGZ "hi"\nW .FILL xBEEF\nHALT\n.END\n')
        img = res.image
        with tempfile.TemporaryDirectory() as d:
            for fmt in ("bin", "hex", "dec", "bits"):
                p = Path(d) / f"p.{fmt}"
                img.save(p)
                self.assertEqual(Image.load(p), img, fmt)
            # los dos primeros bytes (binario) son el origen
            self.assertEqual(Path(d, "p.bin").read_bytes()[:2], bytes([0x00, 0x30]))
            self.assertTrue(Path(d, "p.hex").read_text().startswith("3000 "))

    def test_text_formats_ignore_comments_and_reject_garbage(self):
        img = Image.from_text("3000 C905 ; MOVI\nE025\n", "hex")
        self.assertEqual((img.origin, img.words()), (0x3000, [0xC905, 0xE025]))
        for bad, fmt in (("3000 ZZ", "hex"), ("3000 70000", "dec"), ("0101", "bits"), ("", "hex")):
            with self.assertRaises(ImageError):
                Image.from_text(bad, fmt)

    def test_odd_origin_rejected(self):
        with self.assertRaises(ImageError):
            Image(0x3001, b"\0\0")


if __name__ == "__main__":
    unittest.main()
