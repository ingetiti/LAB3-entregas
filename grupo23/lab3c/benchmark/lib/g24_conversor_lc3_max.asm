; ============================================================
; Archivo: conversor_lc3_max.asm
; Grupo: 24
; ============================================================

; ============================================================
; SUBRUTINA: SUB_BASE_HEX
; Realiza la conversion de un numero entero a formato hexadecimal
; (4 digitos) y lo imprime directamente en la consola.
; -> INPUT  [R0] valor (int)
; ============================================================
SUB_BASE_HEX
        ST      R7, BASE_SAVE_R7
        ST      R0, BASE_SAVE_R0
        ST      R2, BASE_SAVE_R2
        ST      R3, BASE_SAVE_R3
        ST      R4, BASE_SAVE_R4
        ST      R5, BASE_SAVE_R5
        
        ; Resguardar el entero de R0 en R2 antes de usar R0 para imprimir
        ADD     R2, R0, #0       

        LEA     R0, BASE_HEX_LBL
        PUTS

        LD      R4, BASE_CNT_4
BASE_HEX_NIBBLE
        AND     R3, R3, #0
        LD      R5, BASE_CNT_4
BASE_HEX_BIT
        ADD     R3, R3, R3
        ADD     R2, R2, #0
        BRzp    BASE_HEX_BIT_CERO
        ADD     R3, R3, #1
BASE_HEX_BIT_CERO
        ADD     R2, R2, R2
        ADD     R5, R5, #-1
        BRp     BASE_HEX_BIT
        
        LD      R5, BASE_NEG_10
        ADD     R5, R3, R5
        BRn     BASE_HEX_DECIMAL
        ADD     R3, R3, #15
        ADD     R3, R3, #15
        ADD     R3, R3, #15
        ADD     R3, R3, #10
        BRnzp   BASE_HEX_EMITE
BASE_HEX_DECIMAL
        ADD     R3, R3, #15
        ADD     R3, R3, #15
        ADD     R3, R3, #15
        ADD     R3, R3, #3
BASE_HEX_EMITE
        ADD     R0, R3, #0
        OUT
        ADD     R4, R4, #-1
        BRp     BASE_HEX_NIBBLE
        
        LD      R0, BASE_NL
        OUT
        
        LD      R5, BASE_SAVE_R5
        LD      R4, BASE_SAVE_R4
        LD      R3, BASE_SAVE_R3
        LD      R2, BASE_SAVE_R2
        LD      R0, BASE_SAVE_R0
        LD      R7, BASE_SAVE_R7
        RET


; ============================================================
; SUBRUTINA: SUB_BASE_BIN
; Realiza la conversion de un numero entero a formato binario
; (16 bits) y lo imprime directamente en la consola.
; -> INPUT  [R0] valor (int)
; ============================================================
SUB_BASE_BIN
        ST      R7, BASE_SAVE_R7
        ST      R0, BASE_SAVE_R0
        ST      R2, BASE_SAVE_R2
        ST      R3, BASE_SAVE_R3
        
        ; Resguardar el entero de R0 en R2 antes de usar R0 para imprimir
        ADD     R2, R0, #0       
        
        LEA     R0, BASE_BIN_LBL
        PUTS
        
        LD      R3, BASE_CNT_16
BASE_BIN_BUCLE
        ADD     R2, R2, #0
        BRn     BASE_BIN_UNO
        LD      R0, BASE_CHR_0
        OUT
        BRnzp   BASE_BIN_SIGUE
BASE_BIN_UNO
        LD      R0, BASE_CHR_1
        OUT
BASE_BIN_SIGUE
        ADD     R2, R2, R2
        ADD     R3, R3, #-1
        BRp     BASE_BIN_BUCLE
        
        LD      R0, BASE_NL
        OUT
        
        LD      R3, BASE_SAVE_R3
        LD      R2, BASE_SAVE_R2
        LD      R0, BASE_SAVE_R0
        LD      R7, BASE_SAVE_R7
        RET

; --- Datos locales ---
BASE_BIN_LBL    .STRINGZ "Binario: "
BASE_HEX_LBL    .STRINGZ "Hexadecimal: "
BASE_NL         .FILL #10
BASE_CHR_0      .FILL #48
BASE_CHR_1      .FILL #49
BASE_CNT_16     .FILL #16
BASE_CNT_4      .FILL #4
BASE_NEG_10     .FILL #-10
BASE_SAVE_R0    .FILL #0
BASE_SAVE_R2    .FILL #0
BASE_SAVE_R3    .FILL #0
BASE_SAVE_R4    .FILL #0
BASE_SAVE_R5    .FILL #0
BASE_SAVE_R7    .FILL #0

.END