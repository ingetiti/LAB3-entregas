.EXTERNAL g27_circlsh-CIRCLSH

;   ============================================================================
;   Subrutina: TO_QM_N (LC-X)
;       Convierte entre distintos formatos Q (De Q15.16 a Qm.n).
;
;   -> INPUT  [R0] Parte entera del Q15.16 .
;   -> INPUT  [R1] Parte fraccionaria del Q15.16 .
;   -> INPUT  [R2] n.
;   <- OUTPUT [R0] Qm.n .
;   Conserva R1-R7.
;   ============================================================================

;   [.....int......][.....frac.....]
;   ..int..][.....frac.....][.......    (<< n)
;   [....Qm_n......][..............]

TO_QM_N
        PUSH  R1, R7
        JSR   g27_circlsh-CIRCLSH   ; [R0, R1] rotado n bits a la izquierda
        ADD   R1, R1, #0
        BRzp  TO_QM_N_RET
        ADD   R0, R0, #1        ; redondeo
TO_QM_N_RET
        POPR  R1, R7

.END
