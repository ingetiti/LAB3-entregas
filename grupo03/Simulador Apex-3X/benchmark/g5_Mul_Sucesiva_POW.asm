; Potenciacion Q7.8 mediante exponenciacion binaria y MULQ8.
Mul_Sucesiva_POW
        PUSHM   #xBE
        ADD     R2, R0, #0
        ADD     R3, R1, #0
        BRn     POW_ERROR
        BRp     POW_START
        ADD     R0, R0, #0
        BRz     POW_ERROR
        MOVI    R0, #0
        MOVH    R0, #1
        BRnzp   POW_END
POW_START
        MOVI    R4, #0
        MOVH    R4, #1
        AND     R5, R5, #0
        ADD     R2, R2, #0
        BRzp    POW_POS
        ADD     R5, R5, #1
        NEG     R2, R2
POW_POS
        AND     R0, R3, #1
        ST      R0, POW_PARIDAD
POW_LOOP
        AND     R0, R3, #1
        BRz     POW_SKIP
        MULQ8   R4, R4, R2
POW_SKIP
        SHR     R3, R3, #1
        BRz     POW_DONE
        MULQ8   R2, R2, R2
        BRnzp   POW_LOOP
POW_DONE
        ADD     R0, R4, #0
        ADD     R5, R5, #0
        BRz     POW_END
        LD      R1, POW_PARIDAD
        BRz     POW_END
        NEG     R0, R0
        BRnzp   POW_END
POW_ERROR
        MOVI    R0, #0
        MOVH    R0, #x80
POW_END
        POPM    #xBE
        RET
POW_PARIDAD .FILL #0
.END
