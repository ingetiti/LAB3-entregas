; ============================================================================
; Modulo: subrutina_grupo_12  (archivo g12_subrutina_grupo_12.asm)    Grupo 12
; Division por Newton-Raphson en Q3.12, en LC10.                     DIV_NEWTON
;
; Entrada:  R0 = dividendo, R1 = divisor (enteros con signo de 16 bits)
; Salida:   R0 = cociente; si el divisor es 0, R0 = xFFFF
; Preserva: R1 a R5 y R7 (los guarda en la pila con PUSH/POP)
;
; Es el mismo algoritmo del modulo LC-3: signos aparte, normalizar el divisor para
; que su bit alto quede en la posicion 11 (s = desplazamientos que hacen falta para
; llevarlo al bit 15, normalizado a s = 4), valor inicial x0 de una tabla de 8
; entradas indexada por (d >> 8) & 7, dos iteraciones x <- x * (2 - d * x), producto
; final dividendo * x, y desnormalizar (s - 8). Todas las multiplicaciones son
; modulo 2^16 en Q3.12: MULM(a, b) = (a * b) >> 12, que es
; (MULHU << 4) | (MUL >> 12) en LC10. La rutina LC-3 la hacia con un lazo de 16
; sumas con acarreo deducido por signos (MULT_MODULO) y los corrimientos con lazos
; bit a bit; con operandos de este modulo (a <= x8000) el resultado es el mismo.
;
; Registros: R0 = |dividendo|    R1 = d (divisor normalizado)    R2, R3 = temporales
;            R4 = s    R5 = x (la aproximacion de 1/d)    R7 = enlace de DN_ITERACION
; El signo del cociente (bit 15) se guarda en la palabra G_SIGNO.
; ============================================================================

DIV_NEWTON
                        PUSH  R1, R2, R3, R4, R5, R7

                        XOR   R2, R0, R1                ; el bit 15 es el signo del cociente
                        ST    R2, G_SIGNO
                        TST   R0
                        BRzp  DN_A_POS
                        NEG   R0, R0                    ; |dividendo|
DN_A_POS
                        TST   R1
                        BRz   ERROR_DIV0
                        BRzp  DN_D_POS
                        NEG   R1, R1                    ; |divisor|
DN_D_POS

; s = cantidad de desplazamientos a la izquierda hasta que el bit 15 quede en 1
                        CLR   R4
                        MOV   R3, R1
DN_CLZ
                        BRn   DN_CLZ_FIN
                        ADD   R4, R4, #1
                        SHL   R3, R3, #1
                        BR    DN_CLZ
DN_CLZ_FIN

; normalizar a s = 4: a la izquierda (s - 4) o a la derecha (4 - s)
                        ADD   R5, R4, #-4
                        BRz   DN_NORM_FIN
                        BRn   DN_NORM_DER
                        SHL   R1, R1, R5
                        BR    DN_NORM_FIN
DN_NORM_DER
                        NEG   R5, R5
                        SHR   R1, R1, R5
DN_NORM_FIN

; x0 = TABLA_LUT[(d >> 8) & 7]
                        SHR   R3, R1, #8
                        AND   R3, R3, #7
                        SHL   R3, R3, #1
                        LEA   R5, TABLA_LUT
                        ADD   R5, R5, R3
                        LDW   R5, R5, #0

; dos iteraciones: x <- MULM(x, 2 - MULM(d, x))   (2.0 en Q3.12 = x2000)
                        JSR   DN_ITERACION
                        JSR   DN_ITERACION

; cociente = MULM(|dividendo|, x)
                        MUL   R3, R0, R5
                        MULHU R2, R0, R5
                        SHR   R3, R3, #12
                        SHL   R2, R2, #4
                        OR    R3, R3, R2

; desnormalizar: a la izquierda (s - 8) o a la derecha (8 - s)
                        ADD   R5, R4, #-8
                        BRz   DN_DENORM_FIN
                        BRn   DN_DENORM_DER
                        SHL   R3, R3, R5
                        BR    DN_DENORM_FIN
DN_DENORM_DER
                        NEG   R5, R5
                        SHR   R3, R3, R5
DN_DENORM_FIN
                        LD    R2, G_SIGNO
                        TST   R2
                        BRzp  DN_SIGNO_OK
                        NEG   R3, R3                    ; signos distintos: cociente negativo
DN_SIGNO_OK
                        MOV   R0, R3
                        BR    RESTAURAR_ESTADO

ERROR_DIV0
                        LD    R0, FLAG_ERR

RESTAURAR_ESTADO
                        POP   R1, R2, R3, R4, R5, R7
                        RET

; x <- MULM(x, 2 - MULM(d, x))    (R1 = d, R5 = x; usa R2, R3; R7 es el enlace)
DN_ITERACION
                        MUL   R3, R1, R5
                        MULHU R2, R1, R5
                        SHR   R3, R3, #12
                        SHL   R2, R2, #4
                        OR    R3, R3, R2                ; MULM(d, x)
                        MOVI  R2, #1
                        SHL   R2, R2, #13               ; 2.0 = x2000
                        SUB   R2, R2, R3
                        MUL   R3, R5, R2
                        MULHU R5, R5, R2
                        SHR   R3, R3, #12
                        SHL   R5, R5, #4
                        OR    R5, R5, R3                ; MULM(x, 2 - d*x)
                        RET

FLAG_ERR                .FILL xFFFF

TABLA_LUT               .FILL x1E1E
                        .FILL x1AF2
                        .FILL x1861
                        .FILL x1642
                        .FILL x147A
                        .FILL x12F6
                        .FILL x11A7
                        .FILL x1084

G_SIGNO                 .FILL #0

.END
