; Multiplicacion Q7.8 x Q7.8 -> DQ15.16.
; Entrada R0,R1. Salida R0:palabra alta, R1:palabra baja.

MULTIPLICARSHIFTANDADD
        PUSHM   #xBC
        ADD     R2, R0, #0
        ADD     R3, R1, #0
        MUL     R1, R2, R3
        MULH    R0, R2, R3
        POPM    #xBC
        RET

.END
