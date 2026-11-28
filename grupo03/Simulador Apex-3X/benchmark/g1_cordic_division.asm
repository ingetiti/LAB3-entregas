; Division Q0.15 mediante DIVQ15.
CORDIC_DIV
        PUSHM   #x9E
        DIVQ15  R0, R0, R1
        POPM    #x9E
        RET
.END
