; ============================================================
; Archivo: conversor_lc3_max.asm (Grupo 24, OPTIMIZADA)
; ============================================================

SUB_BASE_HEX
        PUSHM {R0, R2, R3, R4, R7}
        ADD  R2, R0, #0

        LEA  R0, BASE_HEX_LBL
        PUTS

        MOVI R4, #4
BASE_HEX_NIBBLE
        LSR  R3, R2, #12        ; extraer nibble superior (0..15)
        SHL  R2, R2, #4
        MOVI R0, #10
        CMP  R3, R0
        BRn  BASE_HEX_DECIMAL
        ADDI R3, #55            ; 'A' - 10
        BRnzp BASE_HEX_EMITE
BASE_HEX_DECIMAL
        ADDI R3, #48            ; '0'
BASE_HEX_EMITE
        ADD  R0, R3, #0
        OUT
        ADD  R4, R4, #-1
        BRp  BASE_HEX_NIBBLE

        MOVI R0, #10
        OUT
        POPM {R0, R2, R3, R4, R7}
        RET

SUB_BASE_BIN
        PUSHM {R0, R2, R3, R7}
        ADD  R2, R0, #0

        LEA  R0, BASE_BIN_LBL
        PUTS

        MOVI R3, #16
BASE_BIN_BUCLE
        LSR  R0, R2, #15        ; bit 15 (0 o 1)
        ADDI R0, #48            ; '0' o '1'
        OUT
        SHL  R2, R2, #1
        ADD  R3, R3, #-1
        BRp  BASE_BIN_BUCLE

        MOVI R0, #10
        OUT
        POPM {R0, R2, R3, R7}
        RET

BASE_BIN_LBL    .STRINGZ "Binario: "
BASE_HEX_LBL    .STRINGZ "Hexadecimal: "

        .END
