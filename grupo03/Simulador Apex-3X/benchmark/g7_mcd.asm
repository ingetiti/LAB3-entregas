; ============================================================================
; Modulo: mcd  (archivo mcd.asm) [LC-3X]                  Grupo 7
; Maximo comun divisor de dos enteros con signo, en punto fijo Q15.0.
; ============================================================================

MCD
        PUSHM #x0E              ; Guarda R1, R2, R3

        ; Obtener |a| y |b|
        ADD R0, R0, #0
        BRzp mcd_a_positivo
        NOT R0, R0
        ADD R0, R0, #1
mcd_a_positivo
        ADD R1, R1, #0
        BRzp mcd_b_positivo
        NOT R1, R1
        ADD R1, R1, #1
mcd_b_positivo

        ; Casos con cero.
        ADD R0, R0, #0
        BRz mcd_devolver_b
        ADD R1, R1, #0
        BRz mcd_fin

        ; R2 conserva -R1 para no recalcularlo en cada resta.
        NOT R2, R1
        ADD R2, R2, #1
        ADD R3, R0, R2
        BRz mcd_fin
        BRn mcd_r0_menor_r1

mcd_restar_r0
        ADD R0, R3, #0
        ADD R3, R0, R2
        BRp mcd_restar_r0
        BRz mcd_fin

mcd_r0_menor_r1
        NOT R2, R0
        ADD R2, R2, #1
mcd_restar_r1
        ADD R1, R1, R2
        ADD R3, R1, R2
        BRp mcd_restar_r1
        BRz mcd_fin

        NOT R2, R1
        ADD R2, R2, #1
        ADD R3, R0, R2
        BRp mcd_restar_r0
        BRz mcd_fin
        BRnzp mcd_r0_menor_r1

mcd_devolver_b
        ADD R0, R1, #0

mcd_fin
        POPM #x0E               ; Restaura R1, R2, R3
        RET

.END
