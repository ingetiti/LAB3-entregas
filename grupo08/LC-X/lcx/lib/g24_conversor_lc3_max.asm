; ============================================================
; Archivo: conversor_lc3_max.asm (LC-X)
; Grupo: 24
; ============================================================

; ============================================================
; SUBRUTINA: SUB_BASE_HEX
; Realiza la conversion de un numero entero a formato hexadecimal
; (4 digitos) y lo imprime directamente en la consola, con un
; salto de linea al final.
; -> INPUT  [R0] valor (int)
; Conserva todos los registros.
; ============================================================
SUB_BASE_HEX
        PUSH    R0, R1, R2, R3, R4
        ADD     R1, R0, #0      ; R1 = valor
        LEA     R0, BASE_HEX_LBL
        PUTSP
        MOVI    R2, #4          ; 4 nibbles
        MOVI    R3, #48         ; '0'
        MOVI    R4, #16
BASE_HEX_NIBBLE
        MULW    R0, R1, R4      ; R0 = nibble mas alto, R1 = R1 << 4
        CMP     R0, #10
        BRn     BASE_HEX_EMITE
        ADD     R0, R0, #7      ; 'A' - '0' - 10
BASE_HEX_EMITE
        ADD     R0, R0, R3
        OUT
        LOOP    R2, BASE_HEX_NIBBLE
        MOVI    R0, #10
        OUT
        POPR    R0, R1, R2, R3, R4

; ============================================================
; SUBRUTINA: SUB_BASE_BIN
; Realiza la conversion de un numero entero a formato binario
; (16 bits) y lo imprime directamente en la consola, con un
; salto de linea al final.
; -> INPUT  [R0] valor (int)
; Conserva todos los registros.
; ============================================================
SUB_BASE_BIN
        PUSH    R0, R1, R2, R3
        ADD     R1, R0, #0      ; R1 = valor
        LEA     R0, BASE_BIN_LBL
        PUTSP
        MOVI    R2, #16         ; 16 bits
        MOVI    R3, #48         ; '0'
BASE_BIN_BUCLE
        LSHF    R1, R1, #1      ; C = bit mas alto
        ADC     R0, R3, #0      ; '0' o '1'
        OUT
        LOOP    R2, BASE_BIN_BUCLE
        MOVI    R0, #10
        OUT
        POPR    R0, R1, R2, R3

; --- Datos locales ---
BASE_BIN_LBL    .STRINGP "Binario: "
BASE_HEX_LBL    .STRINGP "Hexadecimal: "

.END
