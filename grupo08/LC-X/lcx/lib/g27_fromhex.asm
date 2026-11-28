;   ============================================================================
;   Subrutina: FROMHEX (LC-X)
;       Convierte una cadena de texto hexadecimal (un caracter por byte) al
;       valor correspondiente.
;
;   -> INPUT  [R0] Puntero a la cadena.
;   <- OUTPUT [R0] Valor obtenido.
;   <- OUTPUT [R5] Banderas de error [15:2 none, 1 OVERFLOW, 0 INVALID_INPUT].
;   Conserva R1-R4, R6 y R7.
;   ============================================================================

FROMHEX
        PUSH  R0, R1, R2, R3    ; [R6] = inicio de la cadena
        ADD   R1, R0, #0        ; [R1] texto
        AND   R0, R0, #0        ; [R0] valor = 0
        AND   R5, R5, #0        ; [R5] errores = 0
        LDB   R2, R1, #0
        BRnp  FROMHEX_LOOP      ; if char == '\0':
        OR    R5, R5, #1        ;     errores = errores | INVALID_INPUT
        BR    FROMHEX_RET       ;     return

FROMHEX_LOOP
        LDB   R2, R1, #0        ; [R2] char = texto.peek()
        BRz   FROMHEX_OVERFLOW_CHK
        MOVI  R3, #-48
        ADD   R3, R2, R3        ; '0'-'9' -> 0-9
        CMP   R3, #10
        BRNC  FROMHEX_INCREMENT
        MOVI  R3, #32
        OR    R2, R2, R3        ; 'A'-'F' -> 'a'-'f'
        MOVI  R3, #-87
        ADD   R3, R2, R3        ; 'a'-'f' -> 10-15
        SUB   R2, R3, #10
        CMP   R2, #6
        BRNC  FROMHEX_INCREMENT
        OR    R5, R5, #1        ; errores = errores | INVALID_INPUT
        BR    FROMHEX_OVERFLOW_CHK

FROMHEX_INCREMENT
        LSHF  R0, R0, #4
        ADD   R0, R0, R3        ; valor = valor << 4 + cifra
        ADD   R1, R1, #1        ; texto.incr()
        BR    FROMHEX_LOOP

FROMHEX_OVERFLOW_CHK
        LDR   R2, R6, #0
        SUB   R2, R1, R2        ; cifras leidas
        CMP   R2, #5
        BRNC  FROMHEX_RET       ; if mas de 4 cifras:
        OR    R5, R5, #2        ;     errores = errores | OVERFLOW
FROMHEX_RET
        ADD   R6, R6, #2        ; descarta el inicio
        POPR  R1, R2, R3

.END
