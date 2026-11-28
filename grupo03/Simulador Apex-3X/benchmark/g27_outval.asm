
; ============================================================================
; Subrutina: OUTVAL  [LC-3X — adaptada]
;     Muestra por consola un valor en el formato Q especificado.
;
;     Cambios respecto al original LC-3:
;       1. ADD R3, R2, #-16  -> imm4 no admite -16.
;          Reemplazado por MOVI R3, #-16 / ADD R3, R3, R2 (en orden).
;       2. ADD R0, R0, #10  (imprimir '\n') -> imm4 no admite 10.
;          Reemplazado por MOVI R0, #10.
;
; -> INPUT  [R0] Qm.n o parte entera.
; -> INPUT  [R1] 0 o parte fraccionaria.
; -> INPUT  [R2] n (bits fraccionarios).
; ============================================================================

.EXTERNAL GETVAL_BUFFER-BUFFER
ext_buffer      .FILL GETVAL_BUFFER-BUFFER

.EXTERNAL TODEC-TODEC
sub_todec       .FILL TODEC-TODEC

.EXTERNAL FROM_QM_N-FROM_QM_N
sub_from_qm_n   .FILL FROM_QM_N-FROM_QM_N

OUTVAL
    ST R0 outval_r0
    ST R1 outval_r1
    ST R2 outval_r2
    ST R3 outval_r3
    ST R4 outval_r4
    ST R7 outval_r7

    ADD R2 R2 #0
    BRnp outval_sk1             ; if n == 0:
    AND R1 R1 #0                ;   fraccion = 0
    BR outval_out

outval_sk1
    MOVI R3 #-16
    ADD R3 R3 R2                ; R3 = n - 16
    BRz outval_out              ; if n != 16:
    ADD R1 R2 #0
    LD R2 sub_from_qm_n
    JSRR R2                     ;   (entero, fraccion) = from_Qm_n(qm_n, n)

outval_out
    LD R2 ext_buffer
    AND R3 R3 #0
    LD R4 sub_todec
    JSRR R4
    LD R0 ext_buffer
    PUTS                        ; print(todec(value))
    MOVI R0 #10
    OUT                         ; print('\n')

    LD R0 outval_r0
    LD R1 outval_r1
    LD R2 outval_r2
    LD R3 outval_r3
    LD R4 outval_r4
    LD R7 outval_r7
    RET

outval_r0   .FILL #0
outval_r1   .FILL #0
outval_r2   .FILL #0
outval_r3   .FILL #0
outval_r4   .FILL #0
outval_r7   .FILL #0

.END
