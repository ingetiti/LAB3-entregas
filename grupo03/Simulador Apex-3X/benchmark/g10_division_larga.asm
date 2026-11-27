; Division Q7.8 mediante DIVQ8.
DIV_LONG
        PUSHM   #xBE
        ADD     R1, R1, #0
        BRz     DIV_ZERO
        DIVQ8   R0, R0, R1
        AND     R2, R2, #0
        ST      R2, ESTADO
        BRnzp   DIV_END
DIV_ZERO
        AND     R0, R0, #0
        AND     R2, R2, #0
        ADD     R2, R2, #1
        ST      R2, ESTADO
DIV_END
        POPM    #xBE
        RET
ESTADO  .FILL #0
.END
