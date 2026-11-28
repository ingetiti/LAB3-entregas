; =====================================================================
; MODULO: modulo_sqrt_nr (Grupo 23) - SQRT por NON-RESTORING [LC-3X]
; =====================================================================

SQRT_NR     ADD R0, R0, #0
            BRn SQ_NEG          ; x < 0 -> error

            PUSHM #x1E          ; apila R1-R4

            MOVI R1, #13        ; k = 13 iteraciones
            AND R2, R2, #0      ; R = 0 (resto parcial)
            AND R3, R3, #0      ; Q = 0 (raiz parcial)

SQ_LAZO     ADD R2, R2, R2      ; R = 2R
            ADD R0, R0, #0
            BRzp SQ_B1          ; bit 15 de R0 = 0
            ADD R2, R2, #1      ; bit 15 de R0 = 1
SQ_B1       ADD R0, R0, R0      ; siguiente bit a la posicion 15
            ADD R2, R2, R2      ; R = 2R
            ADD R0, R0, #0
            BRzp SQ_B2
            ADD R2, R2, #1
SQ_B2       ADD R0, R0, R0

            ADD R4, R3, R3
            ADD R4, R4, R4      ; R4 = 4Q
            ADD R2, R2, #0
            BRn SQ_SUMA
            ADD R4, R4, #1      ; R4 = 4Q + 1
            NOT R4, R4
            ADD R4, R4, #1      ; R4 = -(4Q + 1)
            ADD R2, R2, R4
            BRnzp SQ_BIT
SQ_SUMA     ADD R4, R4, #3      ; R4 = 4Q + 3
            ADD R2, R2, R4

SQ_BIT      ADD R3, R3, R3
            ADD R2, R2, #0
            BRn SQ_SIG
            ADD R3, R3, #1
SQ_SIG      ADD R1, R1, #-1
            BRp SQ_LAZO

            ADD R2, R2, #0
            BRzp SQ_RED
            ADD R4, R3, R3
            ADD R4, R4, #1
            ADD R2, R2, R4

SQ_RED      NOT R4, R3
            ADD R4, R4, #1      ; R4 = -Q
            ADD R4, R2, R4      ; R4 = R - Q
            BRnz SQ_FIN
            ADD R3, R3, #1

SQ_FIN      ADD R0, R3, #0      ; resultado en Q6.9
            POPM #x1E           ; desapila R1-R4
            RET

SQ_NEG      LD R0, SQ_ERR       ; R0 = x8000 (codigo de error)
            RET

SQ_ERR      .FILL x8000
            .END
