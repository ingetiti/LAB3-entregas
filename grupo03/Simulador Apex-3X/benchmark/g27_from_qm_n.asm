
; ============================================================================
; Subrutina: FROM_QM_N  [LC-3X — adaptada]
;     Convierte de Qm.n a Q15.16 (entero + fraccion separados).
;
;     Cambios respecto al original LC-3:
;       1. ADD R2, R2, #-16  ->  imm4 no admite -16 (rango -8..7).
;          Reemplazado por:  MOVI R3, #-16  /  ADD R2, R2, R3
;
; -> INPUT  [R0] Qm.n
; -> INPUT  [R1] n
; <- OUTPUT [R0] Parte entera (Q15.16)
; <- OUTPUT [R1] Parte fraccionaria (Q15.16)
; ============================================================================

.EXTERNAL CIRCLSH-CIRCLSH
sub_circlsh     .FILL CIRCLSH-CIRCLSH

FROM_QM_N
    ST R2 from_qm_n_r2
    ST R3 from_qm_n_r3
    ST R7 from_qm_n_r7

    ADD R2 R1 #0                ; [R2] n
    MOVI R3 #-16
    ADD R2 R2 R3                ; [R2] n - 16
    NEG R2 R2                   ; [R2] 16 - n
    ADD R1 R0 #0                ; [R1] qm.n

    AND R0 R0 #0
    ADD R1 R1 #0
    BRzp from_qm_n_sk1
    NOT R0 R0                   ; extension de signo (0xFFFF)

from_qm_n_sk1
    LD R3 sub_circlsh
    JSRR R3

    ST R0 from_qm_n_entero
    ST R1 from_qm_n_fraccion

    AND R0 R0 #0
    NOT R1 R0                   ; R1 = 0xFFFF
    LD R3 sub_circlsh
    JSRR R3                     ; [R1] mascara de fraccion

    LD R0 from_qm_n_entero
    LD R2 from_qm_n_fraccion
    AND R1 R1 R2                ; fraccion = fraccion & mascara

    LD R2 from_qm_n_r2
    LD R3 from_qm_n_r3
    LD R7 from_qm_n_r7
    RET

from_qm_n_r2        .FILL #0
from_qm_n_r3        .FILL #0
from_qm_n_r7        .FILL #0
from_qm_n_entero    .FILL #0
from_qm_n_fraccion  .FILL #0

.END
