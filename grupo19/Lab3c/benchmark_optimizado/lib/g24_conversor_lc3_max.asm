; ============================================================
; Archivo: conversor_lc3_max.asm
; Grupo: 24
; Adaptado y optimizado para la ISA de 16 bits byte-addressable
; ============================================================

; ============================================================
; SUBRUTINA: SUB_BASE_HEX
; Realiza la conversion de un numero entero a formato hexadecimal
; (4 digitos) y lo imprime directamente en la consola.
; -> INPUT  [R0] valor (int)
; Optimizaciones:
;   - PUSHM/POPR reemplaza guardado/restaurado manual en memoria.
;   - LSR #12 y SHL #4 extraen cada nibble directamente sin bucle de 4 bits.
;   - MOVI reemplaza constantes en memoria.
; ============================================================
SUB_BASE_HEX
        PUSHM   {R0, R2, R3, R4, R7}

        MOV     R2, R0                  ; Resguardar el entero antes de usar R0

        LEA     R0, BASE_HEX_LBL
        PUTS

        MOVI    R4, #4                  ; 4 nibbles a emitir
BASE_HEX_NIBBLE
        LSR     R3, R2, #12             ; Extraer nibble superior (bits 15..12)
        SHL     R2, R2, #4              ; Desplazar siguiente nibble al frente

        ADDI    R0, R3, #-10
        BRn     BASE_HEX_DECIMAL
        MOVI    R0, #55                 ; 'A' - 10 = 55
        ADD     R0, R0, R3
        BR      BASE_HEX_EMITE
BASE_HEX_DECIMAL
        MOVI    R0, #48                 ; '0' = 48
        ADD     R0, R0, R3
BASE_HEX_EMITE
        OUT
        DEC     R4
        BRp     BASE_HEX_NIBBLE

        MOVI    R0, #10                 ; '\n'
        OUT

        POPR    {R0, R2, R3, R4, R7}


; ============================================================
; SUBRUTINA: SUB_BASE_BIN
; Realiza la conversion de un numero entero a formato binario
; (16 bits) y lo imprime directamente en la consola.
; -> INPUT  [R0] valor (int)
; Optimizaciones:
;   - PUSHM/POPR para pila de registros.
;   - SHL #1 actualiza C con el MSB saliente y BRnc evita saltos extra.
; ============================================================
SUB_BASE_BIN
        PUSHM   {R0, R2, R3, R7}

        MOV     R2, R0                  ; Resguardar el entero antes de usar R0

        LEA     R0, BASE_BIN_LBL
        PUTS

        MOVI    R3, #16                 ; 16 bits a emitir
BASE_BIN_BUCLE
        MOVI    R0, #48                 ; '0'
        SHL     R2, R2, #1              ; Bit mas significativo pasa a C
        BRnc    BASE_BIN_EMITE
        INC     R0                      ; '1'
BASE_BIN_EMITE
        OUT
        DEC     R3
        BRp     BASE_BIN_BUCLE

        MOVI    R0, #10                 ; '\n'
        OUT

        POPR    {R0, R2, R3, R7}

; --- Datos locales ---
BASE_BIN_LBL    .STRINGZ "Binario: "
BASE_HEX_LBL    .STRINGZ "Hexadecimal: "

.END
