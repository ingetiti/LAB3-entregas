; =====================================================================
; SUBRUTINA CORDIC_LOG_BASE (OPTIMIZADA): logaritmo natural en Q3.12
;   Entrada : R0 = m  (Q3.12, 0 < m <= 7.9998)
;   Salida  : R0 = ln(m) (Q3.12)
;   Algoritmo: CORDIC hiperbolico modo vectorial, iteraciones i=1..12 (4 rep.)
; =====================================================================

CORDIC_LOG_BASE
    PUSHM {R1, R2, R3, R4, R5, R7}

    CMP  R0, #0
    BRnz LOG_MIN

    ; Normalizacion: llevar m a >= 0.5 (x0800) contando k
    MOVI R5, #0
    LD   R4, HALF_Q12
NORM
    CMP  R0, R4
    BRzp NORM_OK
    SHL  R0, R0, #1
    ADD  R5, R5, #1
    BRnzp NORM
NORM_OK
    ST   R5, var_k

    ; x = m/2 + 0.5 ; y = m/2 - 0.5 ; z = 0
    LSR  R0, R0, #1             ; m > 0 -> truncamiento hacia 0 = LSR #1
    ADD  R1, R0, R4             ; x
    SUB  R2, R0, R4             ; y
    MOVI R3, #0                 ; z
    MOVI R4, #0                 ; indice de tabla (bytes)

ITER
    LEA  R5, SEQ_I
    ADD  R5, R5, R4
    LDR  R5, R5, #0             ; R5 = i (0 = fin)
    BRz  FIN

    ; R0 = x >> i (truncado hacia 0)
    ADD  R0, R1, #0
    JSR  SUB_ASR
    ST   R0, var_xs
    ; R0 = y >> i (truncado hacia 0)
    ADD  R0, R2, #0
    JSR  SUB_ASR

    CMP  R2, #0
    BRp  Y_POS

    ; y <= 0: x += y>>i; y += x>>i; z -= atanh
    ADD  R1, R1, R0
    LD   R0, var_xs
    ADD  R2, R2, R0
    LEA  R5, LUT_ATANH
    ADD  R5, R5, R4
    LDR  R5, R5, #0
    SUB  R3, R3, R5
    BRnzp NEXT

Y_POS
    ; y > 0: x -= y>>i; y -= x>>i; z += atanh
    SUB  R1, R1, R0
    LD   R0, var_xs
    SUB  R2, R2, R0
    LEA  R5, LUT_ATANH
    ADD  R5, R5, R4
    LDR  R5, R5, #0
    ADD  R3, R3, R5

NEXT
    ADD  R4, R4, #2
    BRnzp ITER

FIN
    SHL  R3, R3, #1             ; 2*z = ln(m*2^k)
    LD   R5, var_k
    BRz  FIN_OK
    MOVI R1, #11
    CMP  R5, R1
    BRzp LOG_MIN
    LD   R1, LN2_Q12
    MULL R1, R1, R5             ; k * ln(2)
    SUB  R3, R3, R1             ; ln(m) = 2*z - k*ln(2)
FIN_OK
    ADD  R0, R3, #0
    BRnzp LOG_RET

LOG_MIN
    LD   R0, MIN_Q12

LOG_RET
    POPM {R1, R2, R3, R4, R5, R7}
    RET

; SUB_ASR: R0 = trunc_toward_zero(R0 / 2^R5). Conserva R1..R5.
SUB_ASR
    CMP  R0, #0
    BRn  A_NEG
    LSR  R0, R0, R5
    RET
A_NEG
    NEG  R0, R0
    LSR  R0, R0, R5
    NEG  R0, R0
    RET

HALF_Q12    .FILL x0800
LN2_Q12     .FILL #2839
MIN_Q12     .FILL x8000
var_k       .FILL #0
var_xs      .FILL #0

SEQ_I
    .FILL #1
    .FILL #2
    .FILL #3
    .FILL #4
    .FILL #4
    .FILL #5
    .FILL #6
    .FILL #7
    .FILL #8
    .FILL #9
    .FILL #10
    .FILL #11
    .FILL #12
    .FILL #0
LUT_ATANH
    .FILL #2250
    .FILL #1046
    .FILL #515
    .FILL #256
    .FILL #256
    .FILL #128
    .FILL #64
    .FILL #32
    .FILL #16
    .FILL #8
    .FILL #4
    .FILL #2
    .FILL #1

.END
