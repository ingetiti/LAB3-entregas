


.EXTERNAL CIRCLSH-CIRCLSH
sub_circlsh     .FILL CIRCLSH-CIRCLSH


;   ============================================================================
;   Subrutina: FROM_QM_N
;       Convierte entre distintos formatos Q (De Qm.n a Q15.16).
;   
;   -> INPUT  [R0] Qm.n .
;   -> INPUT  [R1] n .
;   <- OUTPUT [R0] Parte entera del Q15.16 . 
;   <- OUTPUT [R1] Parte fraccionaria del Q15.16 .
;   ============================================================================

;   [....Qm_n......][..............]
;   [.....ext......][....Qm_n......]    (ext de signo)
;   ..ext..][....Qm_n......][.......    (<< (16 - n))

;   [00000000000000][11111111111111]    (mascara fraccion)
;   0000000][11111111111111][0000000    (<< (16 - n))

;   [.....int......][.frac..0000000]    (mascarar exedente)
;   [.....int......][.....frac.....]


FROM_QM_N

    ST R2 from_qm_n_r2
    ST R3 from_qm_n_r3
    ST R7 from_qm_n_r7
    
    ; [R0] qm.n
    ; [R1] n

    ADD R2 R1 #0                        ;   [R2] n
    ADD R2 R2 #-16
    NOT R2 R2
    ADD R2 R2 #1                        ;   [R2] 16 - n
    ADD R1 R0 #0                        ;   [R1] qm.n

    AND R0 R0 #0                        
    ADD R1 R1 #0
    BRzp from_qm_n_sk1
    NOT R0 R0                           ;   ext

from_qm_n_sk1
    LD R3 sub_circlsh
    JSRR R3
    
    ST R0 from_qm_n_entero
    ST R1 from_qm_n_fraccion

    AND R0 R0 #0
    NOT R1 R0
    LD R3 sub_circlsh
    JSRR R3                             ; [R1] mascara

    LD R0 from_qm_n_entero
    LD R2 from_qm_n_fraccion
    AND R1 R1 R2

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