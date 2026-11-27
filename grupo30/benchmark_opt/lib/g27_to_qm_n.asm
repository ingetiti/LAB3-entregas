;   ============================================================================
;   Subrutina: TO_QM_N (OPTIMIZADA)
;       Convierte de Q15.16 a Qm.n con redondeo.
;   -> INPUT  [R0] entero, [R1] fraccion, [R2] n
;   <- OUTPUT [R0] Qm.n
;   ============================================================================

TO_QM_N
    PUSHM {R1, R2, R3}
    CMP  R2, #0
    BRz  to_qm_n_round
    MOVI R3, #16
    SUB  R3, R3, R2             ; R3 = 16 - n
    BRz  to_qm_n_16
    SHL  R0, R0, R2
    LSR  R3, R1, R3
    OR   R0, R0, R3
    SHL  R1, R1, R2
to_qm_n_round
    ADD  R1, R1, #0
    BRzp to_qm_n_ret
    ADD  R0, R0, #1
    BRnzp to_qm_n_ret
to_qm_n_16
    ADD  R0, R1, #0
to_qm_n_ret
    POPM {R1, R2, R3}
    RET

.END
