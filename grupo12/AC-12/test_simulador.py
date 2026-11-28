import ast
import py_compile
import queue
import subprocess
import sys
import tempfile
import threading
import types
import unittest
from pathlib import Path

ISA_DIR = Path(__file__).resolve().parent
PROJECT_DIR = ISA_DIR.parent
BENCHMARK_MAIN = (
    ISA_DIR / "main_grupo27.asm"
    if (ISA_DIR / "main_grupo27.asm").is_file()
    else PROJECT_DIR / "benchmark_actual" / "main_grupo27.asm"
)

if str(ISA_DIR) not in sys.path:
    sys.path.insert(0, str(ISA_DIR))

from CPU import (
    CPU,
    OPCODE_ADDI5,
    OPCODE_ADDX,
    OPCODE_LDRX,
    OPCODE_MUL,
    OPCODE_MULH,
    OPCODE_STRX,
    OPCODE_SUB,
    parse_machine_code,
)
from ensamblador import AssemblyError, LC3Assembler


def _import_interfaz_headless():
    try:
        import interfaz_isa  # noqa: F401
        return sys.modules["interfaz_isa"]
    except ModuleNotFoundError as exc:
        if exc.name != "tkinter":
            raise
        tk_stub = types.ModuleType("tkinter")
        tk_stub.filedialog = types.ModuleType("tkinter.filedialog")
        tk_stub.simpledialog = types.ModuleType("tkinter.simpledialog")
        tk_stub.ttk = types.ModuleType("tkinter.ttk")
        sys.modules["tkinter"] = tk_stub
        sys.modules["tkinter.filedialog"] = tk_stub.filedialog
        sys.modules["tkinter.simpledialog"] = tk_stub.simpledialog
        sys.modules["tkinter.ttk"] = tk_stub.ttk
        import interfaz_isa  # noqa: F401
        return sys.modules["interfaz_isa"]


def _assemble_and_run(source, fractional_bits=0, trap_input="", source_path=None, max_instructions=1_000_000):
    assembler = LC3Assembler()
    origin, words = assembler.assemble(
        source,
        fractional_bits=fractional_bits,
        source_path=source_path,
    )
    cpu = CPU()
    cpu.trap_input = trap_input
    cpu.load_program(origin, words)
    result = cpu.run(max_instructions=max_instructions)
    return assembler, cpu, result


class TestInstruccionesISA14(unittest.TestCase):
    def test_aritmeticas_logicas_desplazamientos_y_addi5(self):
        source = """.ORIG x3000
            ADD R0, R0, #5
            ADD R1, R0, #-12
            ADD R2, R0, #15
            AND R3, R2, #6
            AND R4, R0, R2
            NOT R5, R0
            LSHF R6, R0, #2
            RSHFL R3, R5, #1
            RSHFA R4, R5, #1
            HALT
        .END
        """
        _asm, cpu, res = _assemble_and_run(source)
        self.assertIsNone(res["error_message"])
        # ADD R1, R0, #-12 y ADD R2, R0, #15 deben usar OPCODE_ADDI5
        self.assertEqual((cpu._read_word(0x3002) >> 11) & 0b11111, OPCODE_ADDI5)
        self.assertEqual((cpu._read_word(0x3004) >> 11) & 0b11111, OPCODE_ADDI5)
        self.assertEqual(cpu.R[0], 5)
        self.assertEqual(cpu.R[1], (-7) & 0xFFFF)
        self.assertEqual(cpu.R[2], 20)
        self.assertEqual(cpu.R[5], (~5) & 0xFFFF)          # 0xFFFA (-6)
        self.assertEqual(cpu.R[6], 20)
        self.assertEqual(cpu.R[3], 0xFFFA >> 1)            # 0x7FFD (lógico)
        self.assertEqual(cpu.R[4], (-6 >> 1) & 0xFFFF)     # 0xFFFD (-3 aritmético)

    def test_sub_mul_y_mulh(self):
        source = """.ORIG x3000
            ADD R1, R1, #5
            ADD R2, R2, #3
            ADD R3, R3, #-4
            SUB R4, R1, R3      ; 5 - (-4) = 9
            SUB R5, R1, #7      ; 5 - 7 = -2 (C=1, V=0, N=1)
            BRC OK_SUB_C
            BR FAIL
        OK_SUB_C
            BRV FAIL
            BRN OK_SUB_N
            BR FAIL
        OK_SUB_N
            LD R0, MIN_NEG
            SUB R0, R0, #1      ; -32768 - 1 -> x7FFF (V=1, C=0, P=1)
            BRV OK_SUB_V
            BR FAIL
        OK_SUB_V
            BRC FAIL
            MUL R0, R2, R3      ; 3 * (-4) = -12 (xFFF4, V=0, C=0)
            BRV FAIL
            MULH R1, R2, R3     ; parte alta de -12 = xFFFF
            LD R2, BIG
            MUL R6, R2, R2      ; 256 * 256 = 65536 -> lo=0 (Z=1), V=1
            BRV OK_MUL_V
            BR FAIL
        OK_MUL_V
            BRZ OK_MUL_Z
            BR FAIL
        OK_MUL_Z
            MULH R6, R2, R2     ; parte alta de 65536 = x0001 (V=0, C=0)
            BRV FAIL
            HALT
        FAIL
            ADD R6, R6, #-1
            HALT
        MIN_NEG .FILL x8000
        BIG     .FILL #256
        .END
        """
        asm, cpu, res = _assemble_and_run(source)
        self.assertIsNone(res["error_message"])
        self.assertEqual(res["outcome"], "Programa detenido por HALT.")
        self.assertEqual((cpu._read_word(0x3006) >> 11) & 0b11111, OPCODE_SUB)
        self.assertEqual((cpu._read_word(asm.labels["OK_SUB_V"] + 2) >> 11) & 0b11111, OPCODE_MUL)
        self.assertEqual((cpu._read_word(asm.labels["OK_SUB_V"] + 6) >> 11) & 0b11111, OPCODE_MULH)
        self.assertEqual(cpu.R[4], 9)
        self.assertEqual(cpu.R[5], (-2) & 0xFFFF)
        self.assertEqual(cpu.R[0], (-12) & 0xFFFF)
        self.assertEqual(cpu.R[1], 0xFFFF)
        self.assertEqual(cpu.R[6], 1)
        self.assertEqual(cpu.V, 0)
        self.assertEqual(cpu.C, 0)

        for bad in (
            ".ORIG x3000\n SUB R0, R1, #8\n HALT\n.END\n",
            ".ORIG x3000\n SUB R0, R1, #-9\n HALT\n.END\n",
            ".ORIG x3000\n MUL R0, R1, #3\n HALT\n.END\n",
            ".ORIG x3000\n MULH R0, R1, #3\n HALT\n.END\n",
        ):
            with self.assertRaises(AssemblyError):
                asm.assemble(bad)

        # Casos extremos de MUL/MULH (cero, -32768*-32768, -32768*-1, sin alterar R7)
        extreme_src = """.ORIG x3000
            LD R1, MIN_N
            AND R2, R2, #0
            MUL R0, R1, R2      ; -32768 * 0 = 0 (Z, V=0)
            BRV FAIL
            BRZ OK_ZERO
            BR FAIL
        OK_ZERO
            MUL R3, R1, R1      ; -32768 * -32768 = +x4000_0000 -> lo=x0000 (V=1)
            BRV OK_OVF
            BR FAIL
        OK_OVF
            MULH R4, R1, R1     ; hi = x4000 (V=0)
            ADD R2, R2, #-1
            MUL R5, R1, R2      ; -32768 * -1 = +32768 (x8000 en 16 bits, V=1)
            BRV OK_MIN_NEG1
            BR FAIL
        OK_MIN_NEG1
            MULH R6, R1, R2     ; hi = x0000
            HALT
        FAIL
            ADD R0, R0, #-1
            HALT
        MIN_N .FILL x8000
        .END
        """
        _asm2, cpu2, res2 = _assemble_and_run(extreme_src)
        self.assertIsNone(res2["error_message"])
        self.assertEqual(cpu2.R[0], 0)
        self.assertEqual(cpu2.R[3], 0x0000)
        self.assertEqual(cpu2.R[4], 0x4000)
        self.assertEqual(cpu2.R[5], 0x8000)
        self.assertEqual(cpu2.R[6], 0x0000)

        # Uso de SUB y MUL/MULH con punto fijo formato Q (Q11.4 y Q7.8)
        q_sub_src = """.ORIG x3000
            ADD R0, R0, #1.5     ; Q11.4: 24
            SUB R1, R0, #0.25    ; Q11.4: 24 - 4 = 20 (1.25)
            HALT
        .END
        """
        _asm_qs, cpu_qs, res_qs = _assemble_and_run(q_sub_src, fractional_bits=4)
        self.assertIsNone(res_qs["error_message"])
        self.assertEqual(cpu_qs.R[0], 24)
        self.assertEqual(cpu_qs.R[1], 20)

        # Producto Q7.8: 1.5 (x0180) * -2.25 (xFDC0) = -3.375 (xFCA0) usando MUL/MULH + shifts
        q_mul_src = """.ORIG x3000
            LD R1, A_Q8
            LD R2, B_Q8
            MUL R3, R1, R2       ; bits 15..0 de producto Q15.16
            MULH R4, R1, R2      ; bits 31..16 de producto Q15.16
            RSHFL R3, R3, #8     ; bits 15..8 -> bits 7..0
            LSHF R4, R4, #8      ; bits 23..16 -> bits 15..8
            ADD R5, R3, R4       ; resultado Q7.8 = -3.375 = -864 = xFCA0
            HALT
        A_Q8 .FILL x0180
        B_Q8 .FILL xFDC0
        .END
        """
        _asm_qm, cpu_qm, res_qm = _assemble_and_run(q_mul_src)
        self.assertIsNone(res_qm["error_message"])
        self.assertEqual(cpu_qm.R[5], (-864) & 0xFFFF)

    def test_memoria_palabra_bytes_ldh_sth_y_ldrx_strx(self):
        source = """.ORIG x3000
            LEA R0, TABLA
            LDR R1, R0, #0
            STR R1, R0, #1
            LDR R2, R0, #1
            ; Offsets fuera de -16..15 -> LDRX / STRX (4 bytes)
            STR R1, R0, #20
            LDR R3, R0, #20
            ; Bytes bajo/alto con LDB/STB y LDH/STH
            LEA R4, BYTES_TEST
            LDB R5, R4, #0
            LDH R6, R4, #0
            LEA R4, DEST_WORD
            ADD R1, R1, #0
            STB R1, R4, #0
            STH R1, R4, #0
            LDR R4, R4, #0
            HALT
        TABLA      .FILL x1234
        COPIA      .FILL x0000
        BYTES_TEST .FILL xFB05
        DEST_WORD  .FILL x0000
        RELLENO    .BLKW #16
        LEJOS      .FILL x0000
        .END
        """
        asm, cpu, res = _assemble_and_run(source)
        self.assertIsNone(res["error_message"])
        # Confirmar codificación de STRX y LDRX
        self.assertEqual((cpu._read_word(0x3008) >> 11) & 0b11111, OPCODE_STRX)
        self.assertEqual((cpu._read_word(0x300C) >> 11) & 0b11111, OPCODE_LDRX)
        self.assertEqual(cpu.R[1], 0x1234)
        self.assertEqual(cpu.R[2], 0x1234)
        self.assertEqual(cpu.R[3], 0x1234)
        self.assertEqual(cpu._read_word(asm.labels["LEJOS"]), 0x1234)
        # BYTES_TEST = xFB05 -> low byte = 0x05 (+5), high byte = 0xFB (-5 -> 0xFFFB)
        self.assertEqual(cpu.R[5], 0x0005)
        self.assertEqual(cpu.R[6], 0xFFFB)
        # STB + STH de x1234 reconstruyen x1234 completo
        self.assertEqual(cpu.R[4], 0x1234)

    def test_decode_ldrx_strx_sin_efectos_secundarios(self):
        source = """.ORIG x3000
            LEA R0, BASE
            LDR R1, R0, #20
            HALT
        BASE .BLKW #20
        VAL  .FILL xABCD
        .END
        """
        asm = LC3Assembler()
        origin, words = asm.assemble(source)
        cpu = CPU()
        cpu.load_program(origin, words)
        cpu.fetch()
        cpu.execute()  # LEA
        cpu.fetch()    # fetch LDRX en x3002 -> PC queda en x3004
        pc_before = cpu.PC
        cpu.decode()
        cpu.decode()   # llamar decode() repetidamente no debe mutar PC
        self.assertEqual(cpu.PC, pc_before)
        cpu.execute()
        self.assertEqual(cpu.PC, pc_before + 2)
        self.assertEqual(cpu.R[1], 0xABCD)

    def test_ldrx_strx_explicitos(self):
        source = """.ORIG x3000
            LEA R0, MID
            LDRX R1, R0, #20
            BRN OK_NEG
            BR FAIL
        OK_NEG
            ; STRX no debe modificar CC (sigue en N por VAL_POS_OFF = xCAFE)
            STRX R1, R0, #-20
            BRN OK_STRX_CC
            BR FAIL
        OK_STRX_CC
            LDRX R2, R0, #-20
            LDRX R3, R0, #0
            HALT
        FAIL
            ADD R6, R6, #-1
            HALT
        SLOT_NEG   .FILL x0000
                   .BLKW #19
        MID        .FILL x1234
                   .BLKW #19
        VAL_POS_OFF .FILL xCAFE
        .END
        """
        asm, cpu, res = _assemble_and_run(source)
        self.assertIsNone(res["error_message"])
        self.assertEqual(res["outcome"], "Programa detenido por HALT.")
        self.assertEqual((cpu._read_word(0x3002) >> 11) & 0b11111, OPCODE_LDRX)
        self.assertEqual((cpu._read_word(asm.labels["OK_NEG"]) >> 11) & 0b11111, OPCODE_STRX)
        self.assertEqual(cpu.R[1], 0xCAFE)
        self.assertEqual(cpu.R[2], 0xCAFE)
        self.assertEqual(cpu.R[3], 0x1234)
        self.assertEqual(cpu.R[6], 0)
        self.assertEqual(cpu._read_word(asm.labels["SLOT_NEG"]), 0xCAFE)
        self.assertEqual(cpu.CC, 0b001)

        for bad in (
            ".ORIG x3000\n LDRX R0, R1, #32768\n HALT\n.END\n",
            ".ORIG x3000\n STRX R0, R1, #-32769\n HALT\n.END\n",
        ):
            with self.assertRaises(AssemblyError):
                asm.assemble(bad)

    def test_ld_y_st_adelante_atras_y_cc(self):
        source = """.ORIG x3000
            BRNZP INICIO
        DATO_ATRAS .FILL xBEEF
        BUF_ATRAS  .FILL x0000
        INICIO
            LD R0, DATO_ATRAS
            BRN OK_NEG_ATRAS
            BR FAIL
        OK_NEG_ATRAS
            LD R1, VAL_POS
            BRP OK_POS
            BR FAIL
        OK_POS
            LD R2, VAL_CERO
            BRZ OK_CERO
            BR FAIL
        OK_CERO
            LD R3, VAL_NEG
            ST R1, BUF_ATRAS
            ST R0, BUF_ADELANTE
            BRN OK_ST_SIN_CC
            BR FAIL
        OK_ST_SIN_CC
            LD R4, BUF_ATRAS
            LD R5, BUF_ADELANTE
            LD R6, VAL_CERO
            ST R4, COPIA_FINAL
            HALT
        FAIL
            ADD R6, R6, #-1
            HALT
        VAL_POS      .FILL x1234
        VAL_CERO     .FILL x0000
        VAL_NEG      .FILL xFFFE
        BUF_ADELANTE .FILL x0000
        COPIA_FINAL  .FILL x0000
        .END
        """
        asm, cpu, res = _assemble_and_run(source)
        self.assertIsNone(res["error_message"])
        self.assertEqual(res["outcome"], "Programa detenido por HALT.")
        self.assertEqual(cpu.R[0], 0xBEEF)
        self.assertEqual(cpu.R[1], 0x1234)
        self.assertEqual(cpu.R[2], 0x0000)
        self.assertEqual(cpu.R[3], 0xFFFE)
        self.assertEqual(cpu.R[4], 0x1234)
        self.assertEqual(cpu.R[5], 0xBEEF)
        self.assertEqual(cpu.R[6], 0x0000)
        self.assertEqual(cpu._read_word(asm.labels["BUF_ATRAS"]), 0x1234)
        self.assertEqual(cpu._read_word(asm.labels["BUF_ADELANTE"]), 0xBEEF)
        self.assertEqual(cpu._read_word(asm.labels["COPIA_FINAL"]), 0x1234)
        self.assertEqual(cpu.CC, 0b010)
        self.assertEqual(cpu.PSR & 0b111, 0b010)

    def test_saltos_condicionales_br_brv_brc_y_subrutinas(self):
        source = """.ORIG x3000
            ADD R0, R0, #0
            BRN FAIL
            BRP FAIL
            BRV FAIL
            BRC FAIL
            BRZ OK_Z
        FAIL
            ADD R6, R6, #-1
            HALT
        OK_Z
            ADD R0, R0, #-1
            BRZP FAIL
            BRN OK_N
            BR FAIL
        OK_N
            ADD R0, R0, #3
            BRNZ FAIL
            BRP OK_P
            BR FAIL
        OK_P
            BRNP OK_NP
            BR FAIL
        OK_NP
            BRZP OK_ZP
            BR FAIL
        OK_ZP
            BRNZP OK_NZP
            BR FAIL
        OK_NZP
            LD R1, VAL_MAX_POS
            ADD R1, R1, #1
            BRV OK_V
            BR FAIL
        OK_V
            JSR SUB_A
            LEA R3, SUB_B
            JSRR R3
            LD R2, VAL_MAX_UNS
            ADD R2, R2, #1
            BRC OK_C
            BR FAIL
        OK_C
            LEA R4, FIN
            JMP R4
            BR FAIL
        SUB_A
            ADD R5, R5, #4
            RET
        SUB_B
            ADD R5, R5, #6
            RET
        FIN
            HALT
        VAL_MAX_POS .FILL x7FFF
        VAL_MAX_UNS .FILL xFFFF
        .END
        """
        _asm, cpu, res = _assemble_and_run(source)
        self.assertIsNone(res["error_message"])
        self.assertEqual(res["outcome"], "Programa detenido por HALT.")
        self.assertEqual(cpu.R[5], 10)
        self.assertEqual(cpu.R[6], 0)
        self.assertEqual(cpu.V, 0)
        self.assertEqual(cpu.C, 1)

    def test_traps_y_putsp_se_detiene_en_nulo_alto(self):
        source = r""".ORIG x3000
            GETC
            OUT
            IN
            LEA R0, MSG
            PUTS
            LEA R0, PACKED
            PUTSP
            HALT
        MSG    .STRINGZ "|Hola; \"1.4\"\t\\ok\n"
        PACKED .FILL x4241
               .FILL x0043
               .FILL x4544
               .FILL x0000
        .END
        """
        _asm, cpu, res = _assemble_and_run(source, trap_input="XY")
        self.assertIsNone(res["error_message"])
        # PUTSP debe parar tras 'C' (high_character == 0) y NO imprimir 'DE'
        self.assertEqual(res["trap_output"], 'XY|Hola; "1.4"\t\\ok\nABC')

    def test_rti_supervisor_y_modo_usuario(self):
        source = """.ORIG x3000
            LEA R6, MARCO
            RTI
            ADD R0, R0, #7
            HALT
        DESTINO
            ADD R0, R0, #3
            HALT
        MARCO
            .FILL DESTINO
            .FILL x0004
        .END
        """
        asm, cpu, res = _assemble_and_run(source)
        self.assertIsNone(res["error_message"])
        self.assertEqual(res["outcome"], "Programa detenido por HALT.")
        self.assertEqual(cpu.R[0], 3)
        self.assertEqual(cpu.R[6], (asm.labels["MARCO"] // 2 + 2) & 0xFFFF)
        self.assertEqual(cpu.PSR & 0x8000, 0)
        self.assertEqual(cpu.CC, 0b001)

        # RTI en modo usuario (bit 15 de PSR = 1) debe fallar
        origin, words = asm.assemble(source)
        cpu_user = CPU()
        cpu_user.load_program(origin, words)
        cpu_user.PSR = 0x8002
        res_user = cpu_user.run()
        self.assertIsNotNone(res_user["error_message"])
        self.assertIn("modo supervisor", res_user["error_message"])

    def test_formato_q_instruccion_extendida_y_fill(self):
        source = """.ORIG x3000
            ADD R0, R0, #1.5
            ADD R1, R0, #-1.25
            LD R3, CONST_Q
            ADD R4, R1, R3
            HALT
        CONST_Q .FILL #2.25
        .END
        """
        _asm, cpu, res = _assemble_and_run(source, fractional_bits=4)
        self.assertIsNone(res["error_message"])
        # 1.5 * 16 = 24 (> 15) -> debe emitir OPCODE_ADDX (0b10010) de 4 bytes
        self.assertEqual((cpu._read_word(0x3000) >> 11) & 0b11111, OPCODE_ADDX)
        self.assertEqual(cpu._read_word(0x3002), 24)
        # -1.25 * 16 = -20 (< -16) -> también debe emitir OPCODE_ADDX
        self.assertEqual((cpu._read_word(0x3004) >> 11) & 0b11111, OPCODE_ADDX)
        self.assertEqual(cpu.R[0], 24)      # 1.5
        self.assertEqual(cpu.R[1], 4)       # 0.25
        self.assertEqual(cpu.R[3], 36)      # 2.25
        self.assertEqual(cpu.R[4], 40)      # 2.5


class TestAlineacionCargadorYCLI(unittest.TestCase):
    def test_byte_impar_alineacion_y_validacion_stringz(self):
        source = r""".ORIG x3000
            BRNZP INICIO
        DATO_B .BYTE #99
        INICIO
            LEA R0, TEXTO
            PUTS
            HALT
        OTRO_B .BYTE #1, #2, #3
        TEXTO  .STRINGZ "A, B; \"C\"\t\\fin\n"
        .END
        """
        asm, cpu, res = _assemble_and_run(source)
        self.assertIsNone(res["error_message"])
        self.assertEqual(asm.labels["DATO_B"], 0x3002)
        self.assertEqual(asm.labels["INICIO"], 0x3004)
        self.assertEqual(cpu.memory[0x3003], 0)
        self.assertEqual(asm.labels["TEXTO"] & 1, 0)
        self.assertEqual(res["trap_output"], 'A, B; "C"\t\\fin\n')

        for bad in (
            '.ORIG x3000\nMSG .STRINGZ "sin cerrar\n.END\n',
            '.ORIG x3000\nMSG .STRINGZ "escape \\q"\n.END\n',
            '.ORIG x3000\nMSG .STRINGZ "a" "b"\n.END\n',
        ):
            with self.assertRaises(AssemblyError):
                asm.assemble(bad)

    def test_parse_machine_code_hex_bin_decimal_y_comentario_origen(self):
        # Hex con @x, @0x, @XXXX y sin @
        for text in (
            "@x3000\nx0815\nx7825\n",
            "@0x3000\n0x0815\n0x7825\n",
            "@3000\n0815\n7825\n",
            "x3000\nx0815\nx7825\n",
            "3000\n0815\n7825\n",
            "; Origen: x3000\nx0815\nx7825\n",
        ):
            with self.subTest(hex_text=text):
                origin, words, fmt = parse_machine_code(text)
                self.assertEqual((origin, words, fmt), (0x3000, [0x0815, 0x7825], "HEXADECIMAL"))

        # Binario con @ y sin @
        for text in (
            "@0011000000000000\n0000100000010101\n0111100000100101\n",
            "0011000000000000\n0000100000010101\n0111100000100101\n",
        ):
            with self.subTest(bin_text=text):
                origin, words, fmt = parse_machine_code(text)
                self.assertEqual((origin, words, fmt), (0x3000, [0x0815, 0x7825], "BINARIO"))

        # Decimal con @12288 y con '; Origen: 12288'
        for text in (
            "@12288\n2069\n30757\n",
            "; Origen: 12288\n2069\n30757\n",
        ):
            with self.subTest(dec_text=text):
                origin, words, fmt = parse_machine_code(text)
                self.assertEqual((origin, words, fmt), (0x3000, [0x0815, 0x7825], "DECIMAL"))

        # Consistencia hex en ensamblador.py
        asm = LC3Assembler()
        for text in ("@x3000\nx0815\nx7825\n", "@0x3000\n0x0815\n0x7825\n", "@3000\n0815\n7825\n"):
            self.assertEqual(asm.assemble(text), (0x3000, [0x0815, 0x7825]))

    def test_cpu_no_importa_ensamblador_y_cli_completo(self):
        tree = ast.parse((ISA_DIR / "CPU.py").read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)
        self.assertNotIn("ensamblador", imported)

        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            asm_src = tmp_dir / "demo.asm"
            asm_src.write_text(
                '.ORIG x3000\n  LEA R0, MSG\n  PUTS\n  GETC\n  OUT\n  HALT\nMSG .STRINGZ "OK:"\n.END\n',
                encoding="utf-8",
            )
            hex_out = tmp_dir / "demo.hex"
            bin_out = tmp_dir / "demo.bin"
            subprocess.run(
                [sys.executable, "-B", str(ISA_DIR / "ensamblador.py"), str(asm_src), "-o", str(hex_out)],
                check=True, capture_output=True, text=True,
            )
            subprocess.run(
                [sys.executable, "-B", str(ISA_DIR / "ensamblador.py"), str(asm_src), "-f", "bin", "-o", str(bin_out)],
                check=True, capture_output=True, text=True,
            )
            for path, fmt in ((hex_out, "HEXADECIMAL"), (bin_out, "BINARIO")):
                run_res = subprocess.run(
                    [sys.executable, "-B", str(ISA_DIR / "CPU.py"), str(path), "-i", "Z"],
                    check=True, capture_output=True, text=True,
                )
                self.assertIn(f"formato {fmt}", run_res.stdout)
                self.assertIn("Motivo de detención: Programa detenido por HALT.", run_res.stdout)
                self.assertIn("Total de memoria utilizada:", run_res.stdout)
                self.assertIn("Salida de TRAP:\nOK:Z", run_res.stdout)

            # Formato Q desde CLI
            q_src = tmp_dir / "q.asm"
            q_hex = tmp_dir / "q.hex"
            q_src.write_text(".ORIG x3000\n  ADD R0, R0, #1.5\n  HALT\n.END\n", encoding="utf-8")
            subprocess.run(
                [sys.executable, "-B", str(ISA_DIR / "ensamblador.py"), str(q_src), "-q", "4", "-o", str(q_hex)],
                check=True, capture_output=True, text=True,
            )
            q_res = subprocess.run(
                [sys.executable, "-B", str(ISA_DIR / "CPU.py"), str(q_hex)],
                check=True, capture_output=True, text=True,
            )
            self.assertIn("R0 = x0018  (sin signo: 24, con signo: 24)", q_res.stdout)

    def test_interfaz_sintaxis_y_execute_program(self):
        with tempfile.TemporaryDirectory() as tmp:
            for fname in ("CPU.py", "ensamblador.py", "interfaz_isa.py"):
                py_compile.compile(
                    str(ISA_DIR / fname),
                    cfile=str(Path(tmp) / f"{fname}c"),
                    doraise=True,
                )

        interfaz_isa = _import_interfaz_headless()
        self.assertIs(interfaz_isa.CPU, CPU)
        self.assertIs(interfaz_isa.LC3Assembler, LC3Assembler)
        self.assertIs(interfaz_isa.AssemblyError, AssemblyError)

        class DummyWorkbench:
            pass

        asm = LC3Assembler()
        origin, words = asm.assemble(".ORIG x3000\n  ADD R0, R0, #5\n  HALT\n.END\n")
        dummy = DummyWorkbench()
        dummy.run_results = queue.Queue()
        interfaz_isa.ISAWorkbench._execute_program(dummy, origin, words, threading.Event(), "", 0)
        details, status = dummy.run_results.get_nowait()
        self.assertEqual(status, "Ejecución finalizada.")
        self.assertIn("Programa cargado (código + datos):", details)
        self.assertIn("Total de memoria utilizada:", details)


class TestBenchmarkCalculadora(unittest.TestCase):
    def test_ensamblado_y_ejecucion_completa_main_grupo27(self):
        self.assertTrue(BENCHMARK_MAIN.is_file(), f"No se encontró {BENCHMARK_MAIN}")
        with tempfile.TemporaryDirectory() as tmp:
            hex_path = Path(tmp) / "main_grupo27.hex"
            asm_run = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(ISA_DIR / "ensamblador.py"),
                    str(BENCHMARK_MAIN),
                    "-o",
                    str(hex_path),
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(
                asm_run.returncode,
                0,
                f"Falló ensamblado de main_grupo27.asm:\nSTDOUT:\n{asm_run.stdout}\nSTDERR:\n{asm_run.stderr}",
            )

            cpu_run = subprocess.run(
                [sys.executable, "-B", str(ISA_DIR / "CPU.py"), str(hex_path)],
                capture_output=True,
                text=True,
            )
            self.assertEqual(
                cpu_run.returncode,
                0,
                f"Falló ejecución de main_grupo27.hex:\nSTDOUT:\n{cpu_run.stdout}\nSTDERR:\n{cpu_run.stderr}",
            )
            out = cpu_run.stdout
            self.assertIn("Motivo de detención: Programa detenido por HALT.", out)
            self.assertIn("Total de memoria utilizada:", out)
            # Verificación de resultados clave de la calculadora (23 operaciones)
            for expected_fragment in (
                "==REDUCCION DE ARGUMENTO (CORDIC)==",
                "==SENO TRIGONOMETRICO (TAYLOR)==",
                "==SENO TRIGONOMETRICO (TABLE)==",
                "==SENO TRIGONOMETRICO (CHEVYSHEV-PADE)==",
                "==COSENO TRIGONOMETRICO (TABLE)==",
                "Hexadecimal: 053E",
                "Binario: 1111101111001010",
                "==RAIZ CUADRADA (NON RESTORING)==",
                "==RAIZ CUADRADA (NEWTON-RAPHSON)==",
                "==EXPONENCIACION==",
                "(Q7.8) -32",
                "(int) -32",
                "==MAXIMO COMUN DIVISOR==",
                "(int) 6",
                "==MINIMO COMUN MULTIPLO==",
                "(int) 304",
            ):
                self.assertIn(expected_fragment, out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
