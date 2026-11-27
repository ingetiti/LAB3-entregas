; Grupo 09 - Rutinas auxiliares para SQRT (OPTIMIZADAS)

; SQ9_ROTL32: rota (R0:R1) 32 bits R2 posiciones a la izquierda.
SQ9_ROTL32
    CMP  R2, #0
    BRnz SQH_FAST
    PUSHM {R2, R3, R4, R5}
    MOVI R3, #31
    AND  R2, R2, R3
    BRz  SQH_DONE
    MOVI R3, #16
    SUB  R4, R2, R3
    BRn  SQH_LT16
    ADD  R5, R0, #0
    ADD  R0, R1, #0
    ADD  R1, R5, #0
    ADD  R2, R4, #0
    BRz  SQH_DONE
SQH_LT16
    SUB  R4, R3, R2
    SHL  R3, R0, R2
    LSR  R5, R1, R4
    OR   R3, R3, R5
    SHL  R1, R1, R2
    LSR  R5, R0, R4
    OR   R1, R1, R5
    ADD  R0, R3, #0
SQH_DONE
    POPM {R2, R3, R4, R5}
SQH_FAST
    RET

; Conversor Q15.16 (R0:R1) -> Q7.8 (R0), con redondeo a 8 bits.
SQ9_DQ16_TO_Q8
    PUSHM {R2}
    SHL  R0, R0, #8
    LSR  R2, R1, #8
    OR   R0, R0, R2
    LSR  R2, R1, #7
    AND  R2, R2, #1
    ADD  R0, R0, R2
    POPM {R2}
    RET

; Conversor Q7.8 (R0) -> Q15.16 (R0:R1).
SQ9_Q8_TO_DQ16
    SHL  R1, R0, #8
    ASR  R0, R0, #8
    RET

.END
