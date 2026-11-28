; ============================================================
; SUBRUTINA: EXP_RAPIDA (Grupo 4, OPTIMIZADA)
; Exponenciacion binaria: R0 = R0 ^ R1 (enteros con signo)
; ============================================================

EXP_RAPIDA
        PUSHM {R1, R2, R3, R4, R5}

        ADD  R2, R0, #0         ; base
        ADD  R3, R1, #0         ; exponente
        MOVI R4, #1             ; acumulador = 1
        AND  R1, R3, #1         ; R1 = paridad del exponente

        ; R5 = 1 si base negativa, R2 = |base|
        MOVI R5, #0
        CMP  R2, #0
        BRzp LOOP_W
        MOVI R5, #1
        NEG  R2, R2

LOOP_W
        CMP  R3, #0
        BRnz POST_PROC
        AND  R0, R3, #1
        BRz  L_SHIFT
        MULL R4, R4, R2         ; acc *= base
L_SHIFT
        LSR  R3, R3, #1         ; exp >>= 1
        BRz  POST_PROC
        MULL R2, R2, R2         ; base *= base
        BRnzp LOOP_W

POST_PROC
        ADD  R0, R4, #0
        CMP  R5, #0
        BRz  RESTAURAR
        CMP  R1, #0
        BRz  RESTAURAR
        NEG  R0, R0

RESTAURAR
        POPM {R1, R2, R3, R4, R5}
        RET

        .END
