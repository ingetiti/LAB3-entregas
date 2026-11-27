; Potenciacion entera por exponenciacion binaria.
; Entrada R0=base, R1=exponente. Salida R0=base^exponente.

EXP_RAPIDA
        PUSHM   #xBE
        ADD     R2, R0, #0
        ADD     R3, R1, #0
        AND     R4, R4, #0
        ADD     R4, R4, #1
        AND     R5, R5, #0
        ADD     R2, R2, #0
        BRzp    EXP_POS
        ADD     R5, R5, #1
        NEG     R2, R2
EXP_POS
        AND     R0, R3, #1
        ST      R0, EXP_PARIDAD
EXP_LOOP
        ADD     R3, R3, #0
        BRnz    EXP_DONE
        AND     R0, R3, #1
        BRz     EXP_SKIP
        MUL     R4, R4, R2
EXP_SKIP
        SHR     R3, R3, #1
        BRz     EXP_DONE
        MUL     R2, R2, R2
        BRnzp   EXP_LOOP
EXP_DONE
        ADD     R0, R4, #0
        ADD     R5, R5, #0
        BRz     EXP_RESTORE
        LD      R1, EXP_PARIDAD
        BRz     EXP_RESTORE
        NEG     R0, R0
EXP_RESTORE
        POPM    #xBE
        RET
EXP_PARIDAD .FILL #0
.END
