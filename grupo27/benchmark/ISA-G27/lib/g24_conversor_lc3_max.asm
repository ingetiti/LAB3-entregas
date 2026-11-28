;=====================================================================
; SUBRUTINA: SUB_BASE_BIN
;   Convierte un entero de 16 bits a binario (16 bits) y lo imprime.
;   Entrada:  R0 = valor entero (16 bits)
;   Salida:   Impresión en consola ("Binario: <16 bits>\n")
;   Conserva: R0-R7 (todos intactos, incluyendo R6).
;=====================================================================
SUB_BASE_BIN:
        ST      R0, BASE_SAVE_R0
        ST      R2, BASE_SAVE_R2
        ST      R3, BASE_SAVE_R3
        ST      R7, BASE_SAVE_R7

        ADD     R2, R0, #0          ; R2 = copia del valor a imprimir
        ST      R2, BASE_WORK

        LEA     R0, BASE_BIN_LBL
        PUTS

        LD      R2, BASE_WORK
        LD      R3, BASE_VAL_16     ; R3 = contador de 16 bits

BASE_BIN_BUCLE:
        LSHO    R0, R2, #1          ; Bit [15] de R2 pasa a bit [0] de R0
        LSH     R2, R2, #1          ; R2 <<= 1 para el siguiente bit
        LD      R7, BASE_CHR_0
        ADD     R0, R0, R7          ; '0' (48) si bit=0, '1' (49) si bit=1
        OUT

        ADD     R3, R3, #-1
        BRp     BASE_BIN_BUCLE

        LD      R0, BASE_NL
        OUT

        LD      R0, BASE_SAVE_R0
        LD      R2, BASE_SAVE_R2
        LD      R3, BASE_SAVE_R3
        LD      R7, BASE_SAVE_R7
        RET

;=====================================================================
; SUBRUTINA: SUB_BASE_HEX
;   Convierte un entero de 16 bits a hexadecimal (4 dígitos) y lo imprime.
;   Entrada:  R0 = valor entero (16 bits)
;   Salida:   Impresión en consola ("Hexadecimal: <4 dígitos>\n")
;   Conserva: R0-R7 (todos intactos, incluyendo R6).
;=====================================================================
SUB_BASE_HEX:
        ST      R0, BASE_SAVE_R0
        ST      R2, BASE_SAVE_R2
        ST      R3, BASE_SAVE_R3
        ST      R4, BASE_SAVE_R4
        ST      R5, BASE_SAVE_R5
        ST      R7, BASE_SAVE_R7

        ADD     R2, R0, #0          ; R2 = copia del valor a imprimir
        ST      R2, BASE_WORK

        LEA     R0, BASE_HEX_LBL
        PUTS

        LD      R2, BASE_WORK
        AND     R4, R4, #0
        ADD     R4, R4, #4          ; R4 = 4 dígitos hexadecimales

BASE_HEX_NIBBLE:
        LSHO    R3, R2, #4          ; R3 = nibble superior [15:12] en bits [3:0]
        LSH     R2, R2, #4          ; R2 <<= 4 para el siguiente nibble

        LD      R5, BASE_NEG_10
        ADD     R5, R3, R5          ; R3 - 10
        BRn     BASE_HEX_DIGITO

        LD      R5, BASE_HEX_A_OFF  ; 55 ('A' - 10)
        ADD     R0, R3, R5
        BR      BASE_HEX_EMITE

BASE_HEX_DIGITO:
        LD      R5, BASE_CHR_0      ; 48 ('0')
        ADD     R0, R3, R5

BASE_HEX_EMITE:
        OUT
        ADD     R4, R4, #-1
        BRp     BASE_HEX_NIBBLE

        LD      R0, BASE_NL
        OUT

        LD      R0, BASE_SAVE_R0
        LD      R2, BASE_SAVE_R2
        LD      R3, BASE_SAVE_R3
        LD      R4, BASE_SAVE_R4
        LD      R5, BASE_SAVE_R5
        LD      R7, BASE_SAVE_R7
        RET

;=====================================================================
; ZONA DE DATOS Y CONSTANTES
;=====================================================================
BASE_BIN_LBL:   .STRINGZ "Binario: "
BASE_HEX_LBL:   .STRINGZ "Hexadecimal: "
BASE_NL:        .FILL #10
BASE_CHR_0:     .FILL #48
BASE_HEX_A_OFF: .FILL #55
BASE_NEG_10:    .FILL #-10
BASE_VAL_16:    .FILL #16

BASE_SAVE_R0:   .FILL #0
BASE_SAVE_R2:   .FILL #0
BASE_SAVE_R3:   .FILL #0
BASE_SAVE_R4:   .FILL #0
BASE_SAVE_R5:   .FILL #0
BASE_SAVE_R7:   .FILL #0
BASE_WORK:      .FILL #0

.END