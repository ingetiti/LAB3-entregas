.EXTERNAL BUFFER
ext_buffer      .FILL BUFFER

.EXTERNAL TODEC
sub_todec       .FILL TODEC

.EXTERNAL FROM_QM_N
sub_from_qm_n   .FILL FROM_QM_N

;   ============================================================================
;   Subrutina: OUTVAL (OPTIMIZADA)
;   -> INPUT  [R0] Qm.n o entero, [R1] 0 o fraccion, [R2] n
;   ============================================================================
OUTVAL
    PUSHM {R0, R1, R2, R3, R4, R7}

    CMP  R2, #0
    BRnp outval_sk1
    MOVI R1, #0
    BR   outval_out

outval_sk1
    MOVI R3, #16
    CMP  R2, R3
    BRz  outval_out
    ADD  R1, R2, #0
    LD   R2, sub_from_qm_n
    JSRR R2

outval_out
    LD   R2, ext_buffer
    MOVI R3, #0
    LD   R4, sub_todec
    JSRR R4
    LD   R0, ext_buffer
    PUTS
    MOVI R0, #10
    OUT

    POPM {R0, R1, R2, R3, R4, R7}
    RET

.END
