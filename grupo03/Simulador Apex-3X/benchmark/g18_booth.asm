; Multiplicacion Booth Q7.8 mediante MULQ8.
MULT_BOOTH
        PUSHM   #xBE
        MULQ8   R0, R0, R1
        POPM    #xBE
        RET
.END
