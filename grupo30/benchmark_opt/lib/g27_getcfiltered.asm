;   ============================================================================
;   Subrutina: GETCFILTERED (OPTIMIZADA)
;   -> INPUT  [R0] Puntero al filtro
;   <- OUTPUT [R0] Caracter capturado
;   ============================================================================

GETCFILTERED
    PUSHM {R1, R2, R3, R4, R7}
    ADD  R4, R0, #0

getcfiltered_beg
    ADD  R1, R4, #0
    GETC

getcfiltered_loop
    LDBU R2, R1, #0
    BRz  getcfiltered_beg
    LDBU R3, R1, #1
    BRz  getcfiltered_beg

    CMP  R0, R2
    BRn  getcfiltered_incr
    CMP  R0, R3
    BRp  getcfiltered_incr
    POPM {R1, R2, R3, R4, R7}
    RET

getcfiltered_incr
    ADD  R1, R1, #2
    BRnzp getcfiltered_loop

.END
