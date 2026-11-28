;   ============================================================================
;   Subrutina: FROM_QM_N (LC-X)
;       Convierte entre distintos formatos Q (De Qm.n a Q15.16).
;
;   -> INPUT  [R0] Qm.n .
;   -> INPUT  [R1] n, de 0 a 16.
;   <- OUTPUT [R0] Parte entera del Q15.16 .
;   <- OUTPUT [R1] Parte fraccionaria del Q15.16 .
;   Conserva R2-R7.
;   ============================================================================

FROM_QM_N
        PUSH  R2
        ADD   R2, R1, #0
        BRz   FROM_QM_N_N0
        SUB   R2, R2, #15
        BRp   FROM_QM_N_N16
        MOVI  R2, #16
        SUB   R2, R2, R1        ; 16 - n
        LSHF  R2, R0, R2        ; fraccion = Qm.n << (16 - n)
        RSHFA R0, R0, R1        ; entero = Qm.n >> n, con signo
        ADD   R1, R2, #0
        POP   R2
        RET
FROM_QM_N_N0                    ; n = 0: todo es entero
        AND   R1, R1, #0
        POP   R2
        RET
FROM_QM_N_N16                   ; n = 16: todo es fraccion
        ADD   R1, R0, #0
        RSHFA R0, R0, #15       ; entero = extension del signo
        POP   R2
        RET

.END
