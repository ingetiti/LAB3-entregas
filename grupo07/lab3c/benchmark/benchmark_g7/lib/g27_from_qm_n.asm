


;   ============================================================================
;   Subrutina: FROM_QM_N
;       Convierte entre distintos formatos Q (De Qm.n a Q15.16).
;
;   -> INPUT  [R0] Qm.n .
;   -> INPUT  [R1] n .
;   <- OUTPUT [R0] Parte entera del Q15.16 .
;   <- OUTPUT [R1] Parte fraccionaria del Q15.16 .
;   ============================================================================

;   (i) Version para la ISA del Grupo 7: en vez de girar bits con CIRCLSH y
;   enmascarar, usa los desplazamientos SAR / SHL (mismo resultado que la
;   version original para 0 <= n):
;       entero    = Qm.n >> n          (aritmetico: conserva el signo)
;       fraccion  = Qm.n << (16 - n)   (en 16 bits)
;       n = 0     -> entero = Qm.n, fraccion = 0
;       n >= 16   -> entero = extension de signo (0 o xFFFF), fraccion = Qm.n
;   Ya no usa CIRCLSH ni toca R7. Conserva R2 y R3.


FROM_QM_N

    ST R2 from_qm_n_r2
    ST R3 from_qm_n_r3

    ; [R0] qm.n
    ; [R1] n

    ADD R2 R1 #-16                      ;
    BRzp from_qm_n_big                  ;   if n >= 16: caso especial
    ADD R1 R1 #0                        ;
    BRz from_qm_n_ret                   ;   if n == 0: entero = qm.n, fraccion = 0 (R1 ya es 0)

    LD R2 from_qm_n_c16                 ;
    SUB R2 R2 R1                        ;   [R2] 16 - n
    SHL R3 R0 R2                        ;   [R3] fraccion = qm.n << (16 - n)
    SAR R0 R0 R1                        ;   [R0] entero = qm.n >> n (con signo)
    ADD R1 R3 #0                        ;   [R1] fraccion

from_qm_n_ret
    LD R2 from_qm_n_r2
    LD R3 from_qm_n_r3
    RET

from_qm_n_big                           ;   n >= 16
    ADD R1 R0 #0                        ;   fraccion = qm.n
    AND R0 R0 #0                        ;   entero = 0
    ADD R1 R1 #0                        ;
    BRzp from_qm_n_ret                  ;
    NOT R0 R0                           ;   si qm.n < 0: entero = xFFFF
    BRnzp from_qm_n_ret                 ;

from_qm_n_r2        .FILL #0
from_qm_n_r3        .FILL #0
from_qm_n_c16       .FILL #16

.END
