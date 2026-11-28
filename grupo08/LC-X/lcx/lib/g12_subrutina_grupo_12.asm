;====================================================================
; DIVISION POR NEWTON-RAPHSON EN Q7.8 (LC-X)
;====================================================================
; DIV_NEWTON
;   Entrada : R0 = dividendo, R1 = divisor (Q7.8 con signo)
;   Salida  : R0 = cociente en Q7.8, saturado a x7FFF / x8000 si no
;             entra, o xFFFF si el divisor es 0
;   Conserva: R1-R7
;
; El mismo algoritmo que el original, sobre los valores absolutos:
;   s = ceros a la izquierda del divisor
;   d = divisor llevado a [0.5, 1) en Q3.12 (bit mas alto en el 11)
;   y = TABLA[bits 10-8 de d]              (1/d aproximado, Q3.12)
;   dos veces: y = y * (2 - d * y)
;   q = dividendo * y, desplazado s - 8 bits, y el signo al final
; Cada producto es (a * b) >> 12 sin signo, como MULT_MODULO; aqui es
; un MULQU. Las normalizaciones multiplican por 2^s.
; Arreglos: el original perdia el bit 16 de dividendo * y (-128 / 1 y
; -128 / -128 daban 0), y un cociente fuera de Q7.8 daba la vuelta sin
; aviso. Aqui ese bit se suma aparte y el cociente se satura.
;====================================================================

DIV_NEWTON
        PUSH  R1, R2, R3, R4, R5, R7
        XOR   R2, R0, R1        ; bit 15 = signo del resultado
        ABS   R0, R0            ; |dividendo| (x8000 se queda)
        ABS   R1, R1            ; |divisor|
        BRz   ERROR_DIV0

; ---- reduccion de rango ----
        CLZ   R3, R1            ; s = ceros a la izquierda
        MOVI  R4, #1
        LSHF  R3, R4, R3        ; R3 = 2^s
        MULQU R1, R3, #4        ; R1 = d = (|divisor| << s) >> 4
        RSHFL R4, R1, #8        ; R4 = 8 + indice de la tabla
        LEA   R5, TABLA_8       ; TABLA_LUT - 8 palabras (ver abajo)
        LDRX  R5, R5, R4        ; R5 = y inicial
        LD    R7, DOS_Q312      ; R7 = 2.0

; ---- Newton-Raphson: dos iteraciones ----
        ADD   R4, R1, #0
        MULQU R4, R5, #12       ; d * y
        SUB   R4, R7, R4        ; 2 - d * y
        MULQU R5, R4, #12       ; y = y * (2 - d * y)
        MULQU R1, R5, #12       ; d * y
        SUB   R1, R7, R1        ; 2 - d * y
        MULQU R5, R1, #12       ; y = y * (2 - d * y)

; ---- multiplicacion final y desnormalizacion ----
        MULQU R0, R5, #12       ; q = dividendo * y, V = bit 16
        BRV   Q17
        MULQU R0, R3, #8        ; M = q * 2^(s - 8), V: M >= 2^16
        BRV   SATURA

; ---- signo y saturacion: M (sin signo) en R0, con sus CC ----
SIGNO   BRn   GRANDE            ; M >= x8000
        ADD   R2, R2, #0
        BRzp  FIN
        NEG   R0, R0
FIN     POPR  R1, R2, R3, R4, R5, R7

GRANDE  ADD   R4, R0, R0
        BRnp  SATURA            ; M > x8000
        ADD   R2, R2, #0
        BRn   FIN               ; -128 justo: R0 = x8000
SATURA  LD    R0, MAX_Q78       ; x7FFF, o x8000 si es negativo
        ADD   R2, R2, #0
        BRzp  FIN
        ADD   R0, R0, #1
        POPR  R1, R2, R3, R4, R5, R7

; TABLA_8 esta 8 palabras antes de TABLA_LUT: no meter nada entre medio.
Q17     LSHF  R4, R3, #8        ; el bit 16 vale 2^(s + 8) en M
TABLA_8 BRz   SATURA            ; s >= 8: M >= 2^16
        MULQU R0, R3, #8
        ADD   R0, R0, R4        ; M, sin desborde: s < 8
        BR    SIGNO

ERROR_DIV0
        MOVI  R0, #-1           ; bandera de error
        POPR  R1, R2, R3, R4, R5, R7
MAX_Q78 .FILL x7FFF
DOS_Q312
        .FILL x2000

TABLA_LUT
        .FILL x1E1E
        .FILL x1AF2
        .FILL x1861
        .FILL x1642
        .FILL x147A
        .FILL x12F6
        .FILL x11A7
        .FILL x1084

        .END
