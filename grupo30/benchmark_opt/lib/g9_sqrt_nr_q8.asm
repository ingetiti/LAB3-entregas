; LAB 3 - GRUPO 9 - SQRT Newton-Raphson reciproco (OPTIMIZADA)
; Entrada: R0 = x en Q7.8 con 4 <= x <= 16 (x0400..x1000)
; Salida : R0 = aproximacion de sqrt(x) en Q7.8 (0 si fuera de rango)
; Algoritmo: 6 iteraciones de Newton-Raphson reciproco y <- y*(3 - x*y^2)/2

SQRT_NR_Q8
        PUSHM {R1, R2, R3, R4, R5, R7}

        LD   R1, SQ9_MIN
        CMP  R0, R1
        BRn  SQ9_BAD
        LD   R1, SQ9_MAX
        CMP  R0, R1
        BRp  SQ9_BAD

        ; R3 = x, R2 = y = 64 (0.25 en Q7.8), R4 = 6 iteraciones, R5 = 768 (3.0)
        ADD  R3, R0, #0
        MOVI R2, #32
        SHL  R2, R2, #1         ; R2 = 64
        MOVI R4, #6
        LD   R5, SQ9_THREE

SQ9_ITER
        ; y2 = floor(y * y / 256)
        MULL R0, R2, R2
        LSR  R0, R0, #8         ; y <= 192 -> y*y <= 36864, pero y <= 128 -> <= 16384 (cabe en 16b!)
        ; xy2 = floor(x * y2 / 256) usando 32 bits (MULH:MULL)
        MULL R1, R3, R0
        MULH R7, R3, R0
        LSR  R1, R1, #8
        SHL  R7, R7, #8
        OR   R0, R1, R7         ; R0 = xy2
        ; factor = 768 - xy2
        SUB  R0, R5, R0
        ; floor(factor * y / 256)
        MULL R1, R0, R2
        MULH R7, R0, R2
        LSR  R1, R1, #8
        SHL  R7, R7, #8
        OR   R0, R1, R7
        ; y = floor(R0 / 2)
        LSR  R2, R0, #1

        ADD  R4, R4, #-1
        BRp  SQ9_ITER

        ; sqrt(x) ~= floor(x * y / 256)
        MULL R1, R3, R2
        MULH R7, R3, R2
        LSR  R1, R1, #8
        SHL  R7, R7, #8
        OR   R0, R1, R7
        BRnzp SQ9_DONE

SQ9_BAD
        MOVI R0, #0

SQ9_DONE
        POPM {R1, R2, R3, R4, R5, R7}
        RET

SQ9_THREE   .FILL #768
SQ9_MIN     .FILL #1024
SQ9_MAX     .FILL #4096

        .END
