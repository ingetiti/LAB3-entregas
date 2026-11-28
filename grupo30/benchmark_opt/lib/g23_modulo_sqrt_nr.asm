; =====================================================================
; MODULO: modulo_sqrt_nr (Grupo 23, OPTIMIZADA) - SQRT NON-RESTORING
; Algoritmo digito a digito de Li y Chu (1996), k = 13 iteraciones.
; Entrada: R0 = x en Q7.8 -> Salida: R0 = sqrt(x) en Q6.9 (x8000 si x<0)
; =====================================================================

SQRT_NR
        CMP  R0, #0
        BRn  SQ_NEG

        PUSHM {R1, R2, R3, R4}

        MOVI R1, #13            ; k = 13 iteraciones
        MOVI R2, #0             ; R = 0
        MOVI R3, #0             ; Q = 0

SQ_LAZO
        ; Bajar 2 bits altos de R0 al resto: R = (R << 2) | (R0 >>> 14)
        SHL  R2, R2, #2
        LSR  R4, R0, #14
        OR   R2, R2, R4
        SHL  R0, R0, #2

        ; Paso non-restoring: si R >= 0 -> R -= (4Q + 1), sino R += (4Q + 3)
        SHL  R4, R3, #2         ; 4Q
        CMP  R2, #0
        BRn  SQ_SUMA
        ADD  R4, R4, #1
        SUB  R2, R2, R4
        BRnzp SQ_BIT
SQ_SUMA
        ADD  R4, R4, #3
        ADD  R2, R2, R4

        ; Nuevo bit de la raiz
SQ_BIT
        SHL  R3, R3, #1
        CMP  R2, #0
        BRn  SQ_SIG
        ADD  R3, R3, #1
SQ_SIG
        ADD  R1, R1, #-1
        BRp  SQ_LAZO

        ; Correccion final del resto: si R < 0, R = R + 2Q + 1
        CMP  R2, #0
        BRzp SQ_RED
        SHL  R4, R3, #1
        ADD  R4, R4, #1
        ADD  R2, R2, R4

        ; Redondeo al mas cercano: si R > Q, Q = Q + 1
SQ_RED
        CMP  R2, R3
        BRnz SQ_FIN
        ADD  R3, R3, #1

SQ_FIN
        ADD  R0, R3, #0
        POPM {R1, R2, R3, R4}
        RET

SQ_NEG
        LD   R0, SQ_ERR
        RET

SQ_ERR  .FILL x8000
        .END
