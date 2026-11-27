; EXP Q3.12 -> Q7.8, aproximacion de Taylor de seis terminos.
EXP_Q3_12
        PUSHM   #xBE
        ADD     R2, R0, #0
        ADD     R3, R0, #0
        LD      R4, EXP_ONE        ; suma = 1.0 en Q3.12
        LD      R5, EXP_ONE        ; termino = 1.0
        MULQ12  R5, R5, R2         ; termino = x
        ADD     R4, R4, R5
        LD      R1, EXP_C2
        MULQ12  R5, R5, R2
        DIVQ12  R5, R5, R1
        ADD     R4, R4, R5
        LD      R1, EXP_C3
        MULQ12  R5, R5, R2
        DIVQ12  R5, R5, R1
        ADD     R4, R4, R5
        LD      R1, EXP_C4
        MULQ12  R5, R5, R2
        DIVQ12  R5, R5, R1
        ADD     R4, R4, R5
        LD      R1, EXP_C5
        MULQ12  R5, R5, R2
        DIVQ12  R5, R5, R1
        ADD     R4, R4, R5
        LD      R1, EXP_C6
        MULQ12  R5, R5, R2
        DIVQ12  R5, R5, R1
        ADD     R4, R4, R5
        MOVI    R1, #8
        ADD     R4, R4, R1
        ASR     R0, R4, #4          ; Q3.12 -> Q7.8 redondeado
        POPM    #xBE
        RET
EXP_C2  .FILL #8192
EXP_C3  .FILL #12288
EXP_C4  .FILL #16384
EXP_C5  .FILL #20480
EXP_C6  .FILL #24576
EXP_ONE .FILL #4096
.END
