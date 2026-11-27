; Multiplicacion Q7.8 mediante MULQ8.
CORDIC_MUL
        PUSHM   #xBE
        MULQ8   R0, R0, R1
        POPM    #xBE
        RET
.END
