;   ============================================================================
;   Subrutina: FROM_QM_N (OPTIMIZADA)
;       Convierte de Qm.n a Q15.16 (R0 = entero, R1 = fraccion).
;   -> INPUT  [R0] Qm.n, [R1] n
;   <- OUTPUT [R0] Parte entera, [R1] Parte fraccionaria
;   ============================================================================

FROM_QM_N
    PUSHM {R2, R3}
    CMP  R1, #0
    BRz  from_qm_n_zero
    MOVI R2, #16
    SUB  R3, R2, R1             ; R3 = 16 - n
    BRz  from_qm_n_16
    SHL  R2, R0, R3             ; fraccion = qm_n << (16 - n)
    ASR  R0, R0, R1             ; entero = qm_n >>a n
    ADD  R1, R2, #0
    POPM {R2, R3}
    RET

from_qm_n_zero
    MOVI R1, #0
    POPM {R2, R3}
    RET

from_qm_n_16
    ADD  R1, R0, #0
    ASR  R0, R0, #15
    POPM {R2, R3}
    RET

.END
