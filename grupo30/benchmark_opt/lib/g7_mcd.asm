; ============================================================================
; Modulo: mcd (Grupo 7, OPTIMIZADA) - Algoritmo de Euclides usando REM
;   Entrada: R0 = a, R1 = b (enteros con signo)
;   Salida : R0 = MCD(|a|, |b|)
; ============================================================================

MCD
        PUSHM {R1, R2}
        ABS  R0, R0
        ABS  R1, R1

mcd_loop
        CMP  R1, #0
        BRz  mcd_fin
        REM  R2, R0, R1         ; r = a % b
        ADD  R0, R1, #0         ; a = b
        ADD  R1, R2, #0         ; b = r
        BRnzp mcd_loop

mcd_fin
        POPM {R1, R2}
        RET

        .END
