
; =============================================================================
; MÓDULO SUBRUTINA: LOG_BORCHARDT_Q8_7 (GRUPO 14)
; Arquitectura: Lab 3c. Conserva las cuatro medias y la tabla de LC-3.
; Formato Punto Fijo: Q8.7 (1.0 = 128 / x0080, 2.0 = 256 / x0100)
; =============================================================================
LOG_BORCHARDT_Q8_7
        ST R7, MAIN_SAVE_R7
        ST R1, MAIN_SAVE_R1
        ST R2, MAIN_SAVE_R2
        ST R3, MAIN_SAVE_R3
        ST R4, MAIN_SAVE_R4

        ADD R2, R0, #0          ; R2 conserva x durante el cálculo de ln(b).
        BRnz MAIN_DIV_ZERO      ; Si x <= 0 -> dominio inválido, devuelve -1
        ADD R1, R1, #0
        BRnz MAIN_DIV_ZERO      ; Si b <= 0 -> base inválida, devuelve -1

        ; 1. Calcular ln(b)
        ADD R0, R1, #0
        JSR LN_GENERAL_Q8_7
        ADD R1, R0, #0                  ; R1 conserva ln(b).
        
        ; 2. Calcular ln(x)
        ADD R0, R2, #0
        JSR LN_GENERAL_Q8_7

        ; 3. Cambio de base: log_b(x) = ln(x) / ln(b)
        ADD R1, R1, #0
        BRz MAIN_DIV_ZERO

        JSR CALC_LOG_BASE_Q8_7
        BR MAIN_FINISH

MAIN_DIV_ZERO
        AND R0, R0, #0
        ADD R0, R0, #-1

MAIN_FINISH
        LD R7, MAIN_SAVE_R7
        LD R1, MAIN_SAVE_R1
        LD R2, MAIN_SAVE_R2
        LD R3, MAIN_SAVE_R3
        LD R4, MAIN_SAVE_R4
        RET

MAIN_SAVE_R7        .BLKW #1
MAIN_SAVE_R1        .BLKW #1
MAIN_SAVE_R2        .BLKW #1
MAIN_SAVE_R3        .BLKW #1
MAIN_SAVE_R4        .BLKW #1

; LN_GENERAL_Q8_7. R0 recibe un argumento positivo y retorna ln(x) en Q8.7.
; El índice x normalizado - 128 identifica una entrada de un byte en la tabla.
LN_GENERAL_Q8_7
        ST R1, LN_R1
        ST R2, LN_R2
        ST R3, LN_R3
        ST R4, LN_R4
        ST R5, LN_R5
        ST R6, LN_R6
        ST R7, LN_R7

        ADD R2, R0, #0
        AND R6, R6, #0
        LD R1, LN_TWO
LN_UP
        SUB R0, R2, R1
        BRn LN_DOWN_INIT
        ADD R6, R6, #1
        LSR R2, R2, #1
        BRnzp LN_UP
LN_DOWN_INIT
        LD R1, LN_ONE
LN_DOWN
        SUB R0, R2, R1
        BRzp LN_MEANS
        ADD R2, R2, R2
        ADD R6, R6, #-1
        BRnzp LN_DOWN

LN_MEANS
        ADD R4, R2, R1
        LSR R4, R4, #1             ; A inicial
        LEA R7, LN_SQRT
        ADD R0, R0, R7
        AND R5, R5, #0
        LDBL R5, R0, #0            ; B inicial
        AND R3, R3, #0
        ADD R3, R3, #4
LN_ITER
        ADD R4, R4, R5
        LSR R4, R4, #1
        MULUW R0, R4, R5           ; R1=0, producto < 2^16
        LSR R0, R0, #7
        ADC R0, R0, R1             ; redondea con el bit descartado
        LD R1, LN_ONE
        SUB R0, R0, R1
        LD R1, LN_MAX_INDEX
        SUB R1, R0, R1
        BRnz LN_AT_INDEX
        LD R0, LN_MAX_INDEX
LN_AT_INDEX
        ADD R0, R0, R7
        LDBL R5, R0, #0
        ADD R3, R3, #-1
        BRp LN_ITER

        ADD R4, R4, R5
        LSR R4, R4, #1
        LSR R5, R4, #1
        LD R1, LN_ONE
        SUB R0, R2, R1
        SHL R0, R0, #7
        ADD R0, R0, R5
        AND R1, R1, #0
        DIVUW R0, R0, R4
        LD R1, LN_LN2
        MULW R2, R6, R1
        ADD R0, R0, R2

        LD R7, LN_R7
        LD R1, LN_R1
        LD R2, LN_R2
        LD R3, LN_R3
        LD R5, LN_R5
        LD R6, LN_R6
        LD R4, LN_R4
        RET

LN_R1 .BLKW #1
LN_R2 .BLKW #1
LN_R3 .BLKW #1
LN_R4 .BLKW #1
LN_R5 .BLKW #1
LN_R6 .BLKW #1
LN_R7 .BLKW #1
LN_TWO .FILL #256
LN_ONE .FILL #128
LN_MAX_INDEX .FILL #127
LN_LN2 .FILL #89

; La división en dos etapas conserva el redondeo y el truncamiento a 16 bits
; aun cuando el cociente Q8.7 completo excede el rango de DIVUW.
CALC_LOG_BASE_Q8_7
        ST R1, LB_R1
        ST R2, LB_R2
        ST R3, LB_R3
        ST R4, LB_R4
        ST R5, LB_R5

        ASR R2, R0, #15
        ASR R3, R1, #15
        XOR R4, R2, R3
        XOR R0, R0, R2
        SUB R0, R0, R2
        XOR R1, R1, R3
        SUB R3, R1, R3
        BRz LB_ZERO

        SHL R0, R0, #6
        AND R1, R1, #0
        DIVUW R0, R0, R3
        SHL R5, R0, #1
        SHL R0, R1, #1
        LSR R2, R3, #1
        ADD R0, R0, R2
        AND R1, R1, #0
        DIVUW R0, R0, R3
        ADD R0, R0, R5
        XOR R0, R0, R4
        SUB R0, R0, R4
        BRnzp LB_DONE
LB_ZERO
        AND R0, R0, #0
        ADD R0, R0, #-1
LB_DONE
        LD R1, LB_R1
        LD R2, LB_R2
        LD R3, LB_R3
        LD R4, LB_R4
        LD R5, LB_R5
        RET

LB_R1 .BLKW #1
LB_R2 .BLKW #1
LB_R3 .BLKW #1
LB_R4 .BLKW #1
LB_R5 .BLKW #1

LN_SQRT
        .BYTE #128
        .BYTE #128
        .BYTE #129
        .BYTE #129
        .BYTE #130
        .BYTE #130
        .BYTE #131
        .BYTE #131
        .BYTE #132
        .BYTE #132
        .BYTE #133
        .BYTE #133
        .BYTE #134
        .BYTE #134
        .BYTE #135
        .BYTE #135
        .BYTE #136
        .BYTE #136
        .BYTE #137
        .BYTE #137
        .BYTE #138
        .BYTE #138
        .BYTE #138
        .BYTE #139
        .BYTE #139
        .BYTE #140
        .BYTE #140
        .BYTE #141
        .BYTE #141
        .BYTE #142
        .BYTE #142
        .BYTE #143
        .BYTE #143
        .BYTE #144
        .BYTE #144
        .BYTE #144
        .BYTE #145
        .BYTE #145
        .BYTE #146
        .BYTE #146
        .BYTE #147
        .BYTE #147
        .BYTE #148
        .BYTE #148
        .BYTE #148
        .BYTE #149
        .BYTE #149
        .BYTE #150
        .BYTE #150
        .BYTE #151
        .BYTE #151
        .BYTE #151
        .BYTE #152
        .BYTE #152
        .BYTE #153
        .BYTE #153
        .BYTE #154
        .BYTE #154
        .BYTE #154
        .BYTE #155
        .BYTE #155
        .BYTE #156
        .BYTE #156
        .BYTE #156
        .BYTE #157
        .BYTE #157
        .BYTE #158
        .BYTE #158
        .BYTE #158
        .BYTE #159
        .BYTE #159
        .BYTE #160
        .BYTE #160
        .BYTE #160
        .BYTE #161
        .BYTE #161
        .BYTE #162
        .BYTE #162
        .BYTE #162
        .BYTE #163
        .BYTE #163
        .BYTE #164
        .BYTE #164
        .BYTE #164
        .BYTE #165
        .BYTE #165
        .BYTE #166
        .BYTE #166
        .BYTE #166
        .BYTE #167
        .BYTE #167
        .BYTE #168
        .BYTE #168
        .BYTE #168
        .BYTE #169
        .BYTE #169
        .BYTE #169
        .BYTE #170
        .BYTE #170
        .BYTE #171
        .BYTE #171
        .BYTE #171
        .BYTE #172
        .BYTE #172
        .BYTE #172
        .BYTE #173
        .BYTE #173
        .BYTE #174
        .BYTE #174
        .BYTE #174
        .BYTE #175
        .BYTE #175
        .BYTE #175
        .BYTE #176
        .BYTE #176
        .BYTE #176
        .BYTE #177
        .BYTE #177
        .BYTE #178
        .BYTE #178
        .BYTE #178
        .BYTE #179
        .BYTE #179
        .BYTE #179
        .BYTE #180
        .BYTE #180
        .BYTE #180
        .BYTE #181
.END
