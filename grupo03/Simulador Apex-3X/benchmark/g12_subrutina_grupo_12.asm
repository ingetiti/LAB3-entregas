; Division Q7.8 mediante DIVQ8.
DIV_NEWTON
        PUSHM   #xBE
        DIVQ8   R0, R0, R1
        POPM    #xBE
        RET
.END
