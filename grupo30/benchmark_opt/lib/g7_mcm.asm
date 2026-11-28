; ============================================================================
; Modulo: mcm (Grupo 7, OPTIMIZADA) - Euclides (REM) + DIV + MULL/MULH
;   Entrada: R0 = a, R1 = b (enteros con signo)
;   Salida : R0 = MCM(|a|, |b|) o x8000 si overflow (> 32767)
; ============================================================================

MCM
        PUSHM {R1, R2, R3, R4}
        ABS  R0, R0
        BRz  mcm_fin
        ABS  R1, R1
        BRz  mcm_cero

        ADD  R3, R0, #0         ; guardar |a|
        ADD  R4, R1, #0         ; guardar |b|

        ; Euclides para MCD en R0
mcm_euclides
        CMP  R1, #0
        BRz  mcm_calc
        REM  R2, R0, R1
        ADD  R0, R1, #0
        ADD  R1, R2, #0
        BRnzp mcm_euclides

mcm_calc
        ; Q = |a| / MCD; MCM = Q * |b| con chequeo de overflow (> 32767)
        DIV  R2, R3, R0
        MULL R0, R2, R4
        MULH R1, R2, R4
        BRnp mcm_overflow
        CMP  R0, #0
        BRzp mcm_fin

mcm_overflow
        LD   R0, mcm_menor_valor
        BRnzp mcm_fin

mcm_cero
        MOVI R0, #0

mcm_fin
        POPM {R1, R2, R3, R4}
        RET

mcm_menor_valor .FILL x8000
        .END
