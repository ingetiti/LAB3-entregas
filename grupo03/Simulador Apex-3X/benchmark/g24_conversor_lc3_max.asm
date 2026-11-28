; ============================================================
; Archivo: conversor_lc3_max.asm [LC-3X]
; Grupo: 24
; ============================================================

SUB_BASE_HEX
        PUSHM   #xBD            ; Guarda R0, R2, R3, R4, R5, R7
        
        ADD     R2, R0, #0       
        LEA     R0, BASE_HEX_LBL
        PUTS

        MOVI    R4, #4
BASE_HEX_NIBBLE
        AND     R3, R3, #0
        MOVI    R5, #4
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
        MOVI    R5, #55         ; 'A' - 10
        ADD     R3, R3, R5
        BRnzp   BASE_HEX_EMITE
BASE_HEX_DECIMAL
        MOVI    R5, #48         ; '0'
        ADD     R3, R3, R5
BASE_HEX_EMITE
        ADD     R0, R3, #0
        OUT
        ADD     R4, R4, #-1
        BRp     BASE_HEX_NIBBLE
        
        MOVI    R0, #10
        OUT
        
        POPM    #xBD            ; Restaura R0, R2, R3, R4, R5, R7
        RET

SUB_BASE_BIN
        PUSHM   #x8D            ; Guarda R0, R2, R3, R7
        
        ADD     R2, R0, #0       
        LEA     R0, BASE_BIN_LBL
        PUTS
        
        MOVI    R3, #16
BASE_BIN_BUCLE
        ADD     R2, R2, #0
        BRn     BASE_BIN_UNO
        MOVI    R0, #48
        OUT
        BRnzp   BASE_BIN_SIGUE
BASE_BIN_UNO
        MOVI    R0, #49
        OUT
BASE_BIN_SIGUE
        ADD     R2, R2, R2
        ADD     R3, R3, #-1
        BRp     BASE_BIN_BUCLE
        
        MOVI    R0, #10
        OUT
        
        POPM    #x8D            ; Restaura R0, R2, R3, R7
        RET

; --- Datos locales ---
BASE_BIN_LBL    .STRINGZ "Binario: "
BASE_HEX_LBL    .STRINGZ "Hexadecimal: "
BASE_NEG_10     .FILL #-10

.END
