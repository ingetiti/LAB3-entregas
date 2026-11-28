; ============================================================================
; Modulo: mcm   (archivo mcm.asm) [LC-3X]                      Grupo 7
; Minimo comun multiplo de dos enteros con signo, en punto fijo Q15.0.
; ============================================================================

MCM
        PUSHM #x3E              ; Guarda R1..R5

        ; Obtener |a| y |b|
        ADD R0, R0, #0
        BRzp mcm_a_positivo
        NOT R0, R0
        ADD R0, R0, #1
mcm_a_positivo
        ADD R1, R1, #0
        BRzp mcm_b_positivo
        NOT R1, R1
        ADD R1, R1, #1
mcm_b_positivo

        ; Si alguno es cero, el MCM es cero.
        ADD R0, R0, #0
        BRz mcm_resultado_cero
        ADD R1, R1, #0
        BRz mcm_resultado_cero

        ; R4 = menor, R5 = mayor.
        NOT R2, R1
        ADD R2, R2, #1
        ADD R3, R0, R2
        BRn mcm_a_es_menor

        ADD R4, R1, #0
        ADD R5, R0, #0
        BRnzp mcm_iniciar_mcd

mcm_a_es_menor
        ADD R4, R0, #0
        ADD R5, R1, #0

mcm_iniciar_mcd
        ADD R3, R0, R2
        BRz mcm_mcd_listo
        BRn mcm_r0_menor_r1

mcm_restar_r0
        ADD R0, R3, #0
        ADD R3, R0, R2
        BRp mcm_restar_r0
        BRz mcm_mcd_listo

mcm_r0_menor_r1
        NOT R2, R0
        ADD R2, R2, #1
mcm_restar_r1
        ADD R1, R1, R2
        ADD R3, R1, R2
        BRp mcm_restar_r1
        BRz mcm_mcd_listo

        NOT R2, R1
        ADD R2, R2, #1
        ADD R3, R0, R2
        BRp mcm_restar_r0
        BRz mcm_mcd_listo
        BRnzp mcm_r0_menor_r1

mcm_mcd_listo
        ; Cociente = menor / MCD por restas sucesivas.
        AND R2, R2, #0
        NOT R3, R0
        ADD R3, R3, #1

mcm_dividir
        ADD R2, R2, #1
        ADD R4, R4, R3
        BRp mcm_dividir

        ; MCM = cociente * mayor
        AND R0, R0, #0

mcm_multiplicar
        ADD R0, R0, R5
        BRn mcm_overflow
        ADD R2, R2, #-1
        BRp mcm_multiplicar
        BRnzp mcm_fin

mcm_overflow
        LD R0, mcm_menor_valor
        BRnzp mcm_fin

mcm_resultado_cero
        AND R0, R0, #0

mcm_fin
        POPM #x3E               ; Restaura R1..R5
        RET

mcm_menor_valor    .FILL x8000

.END
