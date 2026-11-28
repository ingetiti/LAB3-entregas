;   ============================================================================
;   Subrutina: FROM_QM_N
;       Convierte entre distintos formatos Q (De Qm.n a Q15.16).
;       Optimizada para la nueva ISA con SRAV y SHLV directos (sin llamadas
;       a CIRCLSH ni mascaras en bucle).
;
;   -> INPUT  [R0] Qm.n .
;   -> INPUT  [R1] n .
;   <- OUTPUT [R0] Parte entera del Q15.16 .
;   <- OUTPUT [R1] Parte fraccionaria del Q15.16 .
;   ============================================================================

FROM_QM_N
    PUSHM {R2, R3}
    ADDI R1, R1, #0             ; caso especial n == 0 (Q15.0)
    BRz from_qm_n_n0
    MOVI R2, #16
    SUB R2, R2, R1              ; R2 = 16 - n
    BRz from_qm_n_n16           ; caso especial n == 16 (Q0.16)

    MOV R3, R0                  ; R3 = Qm.n
    SRAV R0, R3, R1             ; R0 = Qm.n >>_arith n (parte entera con signo)
    SHLV R1, R3, R2             ; R1 = Qm.n << (16 - n) (parte fraccionaria)
    POPM {R2, R3}
    RET

from_qm_n_n0
    CLR R1                      ; sin parte fraccionaria
    POPM {R2, R3}
    RET

from_qm_n_n16
    MOV R1, R0                  ; toda la palabra es fraccionaria
    ASR R0, R0, #15             ; extension de signo (0 o -1)
    POPM {R2, R3}
    RET

    .END
