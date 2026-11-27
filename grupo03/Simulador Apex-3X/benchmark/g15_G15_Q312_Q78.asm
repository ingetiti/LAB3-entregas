; Conversor del grupo 15: Q3.12 a Q7.8 [LC-3X]

G15_Q312_Q78
        PUSHM #x1E          ; Guarda R1, R2, R3, R4
        AND R1, R1, #0
        AND R2, R2, #0
        MOVI R4, #16
G15_MULT16
        ADD R3, R1, #0       ; palabra baja anterior
        ADD R1, R1, R0
        ADD R0, R0, #0
        BRn G15_SUMANDO_NEG
        ADD R3, R3, #0
        BRzp G15_SIGUIENTE
        ADD R1, R1, #0
        BRzp G15_ACARREO
        BRnzp G15_SIGUIENTE
G15_SUMANDO_NEG
        ADD R2, R2, #-1      ; extension de signo del sumando
        ADD R3, R3, #0
        BRn G15_ACARREO
        ADD R1, R1, #0
        BRn G15_SIGUIENTE
G15_ACARREO
        ADD R2, R2, #1
G15_SIGUIENTE
        ADD R4, R4, #-1
        BRp G15_MULT16

        ADD R0, R2, #0
        ADD R3, R1, #0       ; copia para conservar el intermedio en R2:R1
        MOVI R4, #8
G15_LEER_LO
        ADD R0, R0, R0
        ADD R3, R3, #0
        BRzp G15_BIT_CERO
        ADD R0, R0, #1
G15_BIT_CERO
        ADD R3, R3, R3
        ADD R4, R4, #-1
        BRp G15_LEER_LO

        POPM #x1E           ; Restaura R1, R2, R3, R4
        ADD R0, R0, #0
        RET

.END
