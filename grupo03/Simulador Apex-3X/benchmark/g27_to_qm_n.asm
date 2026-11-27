
; ============================================================================
; Subrutina: TO_QM_N  [LC-3X — sin cambios necesarios]
;     Convierte de Q15.16 a Qm.n.
;     Todos los immediatos estan en rango -> OK sin cambios.
;
; -> INPUT  [R0] Parte entera Q15.16
; -> INPUT  [R1] Parte fraccionaria Q15.16
; -> INPUT  [R2] n
; <- OUTPUT [R0] Qm.n
; ============================================================================

.EXTERNAL CIRCLSH-CIRCLSH
sub_circlsh     .FILL CIRCLSH-CIRCLSH

TO_QM_N
    ST R1 to_qm_n_r1
    ST R2 to_qm_n_r2
    ST R3 to_qm_n_r3
    ST R7 to_qm_n_r7

    LD R3 sub_circlsh
    JSRR R3

    ADD R1 R1 #0
    BRzp to_qm_n_ret
    ADD R0 R0 #1                ; redondeo

to_qm_n_ret
    LD R1 to_qm_n_r1
    LD R2 to_qm_n_r2
    LD R3 to_qm_n_r3
    LD R7 to_qm_n_r7
    RET

to_qm_n_r1  .FILL #0
to_qm_n_r2  .FILL #0
to_qm_n_r3  .FILL #0
to_qm_n_r7  .FILL #0

.END
