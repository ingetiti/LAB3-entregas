;   ============================================================================
;   Subrutina: FROMDEC (LC-X)
;       Convierte una cadena de texto decimal (un caracter por byte) al valor
;       correspondiente. El resultado obtenido es separado en 2 registros:
;       - En R0 la parte entera (exponentes positivos y cero: [..., 2**1, 2**0])
;       - En R1 la parte fraccionaria (exponentes negativos: [2**-1, 2**-2, ...])
;
;   -> INPUT  [R0] Puntero de la cadena.
;   <- OUTPUT [R0] Parte entera obtenida.
;   <- OUTPUT [R1] Parte fraccionaria obtenida.
;   <- OUTPUT [R5] Error flag bits [15:2 none, 1 OVERFLOW, 0 INVALID_INPUT].
;   Conserva R2-R4, R6 y R7.
;
;   Mientras trabaja, R5 tambien lleva tiene_numero (bit 2) y negativo (bit 3).
;   Las 9 cifras decimales se juntan en un entero de 32 bits D, y la fraccion
;   sale de D / 10^9 bit a bit (16 bits, y un bit mas para redondear).
;   (Arreglo: la version LC-3 no llevaba el acarreo de sumar la cifra a la
;   palabra alta de D.)
;   ============================================================================

FROMDEC
        PUSH  R2, R3, R4, R7
        ADD   R4, R0, #0        ; [R4] texto
        AND   R0, R0, #0        ; [R0] entero = 0
        AND   R1, R1, #0        ; [R1] fraccion = 0
        AND   R5, R5, #0        ; [R5] errores = 0

;   ==- Signo -=================================================================
        LDB   R2, R4, #0
        CMP   R2, #45
        BRnp  FROMDEC_INT_LOOP  ; if char == '-':
        OR    R5, R5, #8        ;     negativo = 1
        ADD   R4, R4, #1        ;     texto.incr()

;   ==- Parte entera -==========================================================
FROMDEC_INT_LOOP
        LDB   R2, R4, #0        ; [R2] char = texto.peek()
        BRz   FROMDEC_RET       ; if char == '\0': return
        CMP   R2, #46
        BRz   FROMDEC_DEC       ; if char == '.' or char == ',': break
        CMP   R2, #44
        BRz   FROMDEC_DEC
        MOVI  R3, #-48
        ADD   R3, R2, R3        ; [R3] cifra = char - '0'
        CMP   R3, #10
        BRC   FROMDEC_INVALID   ; no es '0'-'9'
        LD    R2, FROMDEC_3276
        SUB   R2, R0, R2
        BRn   FROMDEC_APPEND
        BRp   FROMDEC_OVERFLOW
        RSHFL R2, R5, #3        ; negativo
        ADD   R2, R2, #8
        CMP   R3, R2
        BRNC  FROMDEC_APPEND    ; if entero > 3276 or (entero == 3276 and cifra >= 8 + negativo):
FROMDEC_OVERFLOW
        OR    R5, R5, #2        ;     errores = errores | OVERFLOW
FROMDEC_APPEND
        MUL   R0, R0, #10
        ADD   R0, R0, R3        ; entero = entero * 10 + cifra
        OR    R5, R5, #4        ; tiene_numero = 1
        ADD   R4, R4, #1        ; texto.incr()
        BR    FROMDEC_INT_LOOP

FROMDEC_INVALID
        OR    R5, R5, #1        ; errores = errores | INVALID_INPUT
        BR    FROMDEC_RET

;   ==- Parte fraccionaria -====================================================
FROMDEC_DEC
        ADD   R4, R4, #1        ; texto.incr()
        PUSH  R0                ; entero
        AND   R2, R2, #0        ; [R2, R1] D = 0
        MOVI  R0, #9            ; 9 cifras
FROMDEC_DEC_LOOP
        LDB   R3, R4, #0
        MOVI  R7, #-48
        ADD   R3, R3, R7        ; [R3] current = char - '0'
        CMP   R3, #10
        BRNC  FROMDEC_DEC_DIGIT
        LDB   R3, R4, #0
        BRz   FROMDEC_DEC_ZERO  ; elif char != '\0':
        OR    R5, R5, #1        ;     errores = errores | INVALID_INPUT
FROMDEC_DEC_ZERO
        AND   R3, R3, #0        ; current = 0
        BR    FROMDEC_DEC_ADD
FROMDEC_DEC_DIGIT
        ADD   R4, R4, #1        ; texto.incr()
FROMDEC_DEC_ADD
        MOVI  R7, #10
        MUL   R2, R2, #10
        MULW  R7, R1, R7        ; [R7, R1] = palabra baja * 10
        ADD   R2, R2, R7        ; D = D * 10
        ADD   R1, R1, R3
        ADC   R2, R2, #0        ; D = D + current
        LOOP  R0, FROMDEC_DEC_LOOP

        MOVI  R4, #16           ; [R0] fraccion = 0 (el LOOP la deja en 0)
FROMDEC_BIN
        ADD   R0, R0, R0        ; fraccion = fraccion << 1
        ADD   R1, R1, R1
        ADC   R2, R2, R2        ; D = D * 2
        LD    R3, FROMDEC_MIL_L
        LD    R7, FROMDEC_MIL_H
        SUB   R3, R1, R3
        SBC   R7, R2, R7        ; [R7, R3] = D - 10^9; C = 1 si D >= 10^9
        BRNC  FROMDEC_BIN_NEXT  ; if D >= 10^9:
        ADD   R0, R0, #1        ;     fraccion = fraccion + 1
        ADD   R1, R3, #0
        ADD   R2, R7, #0        ;     D = D - 10^9
FROMDEC_BIN_NEXT
        LOOP  R4, FROMDEC_BIN
        ADD   R1, R1, R1
        ADC   R2, R2, R2        ; D = D * 2 (bit 17: redondeo)
        LD    R3, FROMDEC_MIL_L
        LD    R7, FROMDEC_MIL_H
        SUB   R3, R1, R3
        SBC   R7, R2, R7        ; [R7, R3] = D - 10^9; C = 1 si D >= 10^9
        ADC   R1, R0, #0        ; fraccion = fraccion + bit
        POP   R0
        ADC   R0, R0, #0        ; if fraccion == 0: entero = entero + 1

;   ==- Return -================================================================
FROMDEC_RET
        AND   R2, R5, #4
        BRnp  FROMDEC_RET_SK1   ; if not tiene_numero:
        OR    R5, R5, #1        ;     errores = errores | INVALID_INPUT
FROMDEC_RET_SK1
        AND   R2, R5, #8
        BRz   FROMDEC_RET_POS   ; if negativo:
        NOT   R0, R0
        NEG   R1, R1            ;     C = 1 solo si la fraccion es 0
        ADC   R0, R0, #0        ;     [entero, fraccion] = -[entero, fraccion]
FROMDEC_RET_POS
        AND   R5, R5, #3
        POPR  R2, R3, R4, R7

FROMDEC_3276    .FILL #3276
FROMDEC_MIL_L   .FILL xCA00     ;   10^9 = x3B9ACA00
FROMDEC_MIL_H   .FILL x3B9A

.END
