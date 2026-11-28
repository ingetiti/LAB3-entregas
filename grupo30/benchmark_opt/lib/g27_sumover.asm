;   ============================================================================
;   Subrutina: SUMOVER (OPTIMIZADA)
;       Sumador de 16 bits con carry de entrada y salida sin saltos.
;   -> INPUT  [R0] A, [R1] B, [R2] carry_in (0 o 1)
;   <- OUTPUT [R0] A + B + carry_in, [R2] carry_out (0 o 1)
;   ============================================================================

SUMOVER
    PUSHM {R3, R4}
    ADD  R3, R0, R1
    ADD  R3, R3, R2             ; R3 = sum
    AND  R2, R0, R1             ; a & b
    OR   R4, R0, R1             ; a | b
    NOT  R0, R3                 ; ~sum
    AND  R4, R4, R0             ; (a | b) & ~sum
    OR   R2, R2, R4             ; bit 15 = carry unsigned
    LSR  R2, R2, #15            ; R2 = carry_out (0 o 1)
    ADD  R0, R3, #0             ; R0 = sum
    POPM {R3, R4}
    RET

.END
