;   ============================================================================
;   Subrutina: CIRCLSH (OPTIMIZADA)
;       Corrimiento circular izquierdo de 32 bits (R0:R1) en R2 posiciones.
;   -> INPUT  [R0] Registro A, [R1] Registro B, [R2] n
;   <- OUTPUT [R0] Nuevo A, [R1] Nuevo B
;   ============================================================================

CIRCLSH
    CMP  R2, #0
    BRnz circlsh_done_fast
    PUSHM {R2, R3, R4, R5}
    MOVI R3, #31
    AND  R2, R2, R3
    BRz  circlsh_ret
    MOVI R3, #16
    SUB  R4, R2, R3
    BRn  circlsh_lt16
    ; n >= 16: intercambiar R0 y R1 y reducir n -= 16
    ADD  R5, R0, #0
    ADD  R0, R1, #0
    ADD  R1, R5, #0
    ADD  R2, R4, #0
    BRz  circlsh_ret
circlsh_lt16
    SUB  R4, R3, R2             ; R4 = 16 - n
    SHL  R3, R0, R2             ; A << n
    LSR  R5, R1, R4             ; B >>> (16 - n)
    OR   R3, R3, R5             ; nuevo A
    SHL  R1, R1, R2             ; B << n
    LSR  R5, R0, R4             ; A >>> (16 - n)
    OR   R1, R1, R5             ; nuevo B
    ADD  R0, R3, #0
circlsh_ret
    POPM {R2, R3, R4, R5}
circlsh_done_fast
    RET

.END
