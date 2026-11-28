;=====================================================================
; SUBRUTINA: LN_Q8_7 (Logaritmo natural ln(x) en formato Q8.7)
;
;   Entrada:  R0 = x en Q8.7 (1.0 = 128 = x0080; x > 0)
;   Salida:   R0 = ln(x) en Q8.7 (xFFFF si x <= 0)
;   Conserva: R1-R5, R6 (intacto) y R7.
;=====================================================================
LN_Q8_7:
        ST      R1, LN_SAVE_R1
        ST      R2, LN_SAVE_R2
        ST      R3, LN_SAVE_R3
        ST      R4, LN_SAVE_R4
        ST      R5, LN_SAVE_R5
        ST      R7, LN_SAVE_R7

        ; 1. Validar dominio: si x <= 0 retornar xFFFF
        ADD     R0, R0, #0
        BRnz    LN_INVALID

        ; 2. Normalizar x en R1 al rango [1.0, 2.0) = [128, 256)
        ;    ln(x) = ln(x_norm) + k * ln(2)
        ADD     R1, R0, #0          ; R1 = x_norm
        AND     R2, R2, #0          ; R2 = k = 0
        LD      R4, VAL_NEG_Q_TWO   ; -256 (-2.0 en Q8.7)

LN_LOOP_UP:
        ADD     R0, R1, R4          ; x_norm - 256
        BRn     LN_CHECK_DOWN
        RSH     R1, R1, #1          ; x_norm >>= 1
        ADD     R2, R2, #1          ; k++
        BR      LN_LOOP_UP

LN_CHECK_DOWN:
        LD      R4, VAL_NEG_Q_ONE   ; -128 (-1.0 en Q8.7)

LN_LOOP_DOWN:
        ADD     R0, R1, R4          ; x_norm - 128
        BRzp    LN_EVAL_KERNEL
        ADD     R1, R1, R1          ; x_norm <<= 1
        ADD     R2, R2, #-1         ; k--
        BR      LN_LOOP_DOWN

LN_EVAL_KERNEL:
        ; Evaluar núcleo de Borchardt sobre x_norm en R1 -> R0 = ln(x_norm)
        ADD     R0, R1, #0
        JSR     BORCHARDT_KERNEL_Q8_7
        ST      R0, LN_TEMP_LNM

        ; Sumar k * ln(2) usando MUL (CONST_LN2 = 89 en Q8.7)
        LD      R1, CONST_LN2
        MUL     R0, R2, R1          ; R0 = k * 89 (en Q8.7)
        LD      R1, LN_TEMP_LNM
        ADD     R0, R0, R1          ; R0 = ln(x_norm) + k * ln(2)
        BR      LN_EXIT

LN_INVALID:
        AND     R0, R0, #0
        ADD     R0, R0, #-1         ; xFFFF

LN_EXIT:
        LD      R1, LN_SAVE_R1
        LD      R2, LN_SAVE_R2
        LD      R3, LN_SAVE_R3
        LD      R4, LN_SAVE_R4
        LD      R5, LN_SAVE_R5
        LD      R7, LN_SAVE_R7
        RET

;=====================================================================
; SUBRUTINA INTERNA: BORCHARDT_KERNEL_Q8_7
;   Entrada:  R0 = x_norm en Q8.7, en [128, 256)
;   Salida:   R0 = ln(x_norm) en Q8.7
;   Conserva: R1-R5, R6 (intacto) y R7.
;=====================================================================
BORCHARDT_KERNEL_Q8_7:
        ST      R1, BK_SAVE_R1
        ST      R2, BK_SAVE_R2
        ST      R3, BK_SAVE_R3
        ST      R4, BK_SAVE_R4
        ST      R5, BK_SAVE_R5
        ST      R7, BK_SAVE_R7

        ST      R0, BK_X_NORM

        ; a_0 = (x_norm + 128) >> 1
        LD      R1, VAL_Q_ONE
        ADD     R0, R0, R1
        RSH     R0, R0, #1
        ST      R0, BK_A

        ; b_0 = sqrt(x_norm) desde TABLA_SQRT
        LD      R0, BK_X_NORM
        JSR     LEER_RAIZ_Q8_7
        ST      R0, BK_B

        ; 4 iteraciones de Borchardt:
        ;   a = (a + b) >> 1
        ;   b = sqrt((a * b + 64) >> 7)
        AND     R5, R5, #0          ; i = 0

BK_FOR_LOOP:
        ADD     R4, R5, #-4
        BRzp    BK_LOOP_END

        LD      R0, BK_A
        LD      R1, BK_B
        ADD     R0, R0, R1
        RSH     R0, R0, #1          ; a_next = (a + b) / 2
        ST      R0, BK_A

        ; Producto sin signo (a_next * b) en 32 bits, escalado >> 7 + 64 redondeo
        MUL     R2, R0, R1          ; Bits bajos [15:0]
        MULH    R3, R0, R1          ; Bits altos [31:16]
        LSH     R3, R3, #9          ; Parte alta alineada para Q8.7
        RSH     R2, R2, #7          ; Parte baja dividida entre 128
        OR      R0, R3, R2
        LD      R1, CONST_64
        ADD     R0, R0, R1          ; +64 redondeo
        RSH     R0, R0, #7

        JSR     LEER_RAIZ_Q8_7
        ST      R0, BK_B

        ADD     R5, R5, #1
        BR      BK_FOR_LOOP

BK_LOOP_END:
        ; m = (a + b) >> 1
        LD      R0, BK_A
        LD      R1, BK_B
        ADD     R0, R0, R1
        RSH     R0, R0, #1
        ST      R0, BK_M

        ; Numerador en Q8.7: (m / 2) + ((x_norm - 128) * 128)
        LD      R0, BK_X_NORM
        LD      R1, VAL_NEG_Q_ONE
        ADD     R0, R0, R1          ; x_norm - 128
        LSH     R0, R0, #7          ; (x_norm - 128) << 7
        ST      R0, BK_TEMP_NUM

        LD      R0, BK_M
        RSH     R0, R0, #1          ; m / 2
        LD      R1, BK_TEMP_NUM
        ADD     R0, R0, R1          ; numerador

        ; ln(x_norm) = numerador / m (en Q8.7, ya que numerador está escalado por 128)
        LD      R1, BK_M
        DIV     R0, R0, R1

        LD      R1, BK_SAVE_R1
        LD      R2, BK_SAVE_R2
        LD      R3, BK_SAVE_R3
        LD      R4, BK_SAVE_R4
        LD      R5, BK_SAVE_R5
        LD      R7, BK_SAVE_R7
        RET

;=====================================================================
; SUBRUTINA INTERNA: LEER_RAIZ_Q8_7
;   Entrada:  R0 = x en Q8.7, en [128, 256)
;   Salida:   R0 = sqrt(x) en Q8.7 vía TABLA_SQRT
;   Conserva: R1-R2, R6 (intacto) y R7.
;=====================================================================
LEER_RAIZ_Q8_7:
        ST      R1, LR_SAVE_R1
        ST      R2, LR_SAVE_R2

        LD      R1, VAL_NEG_Q_ONE
        ADD     R2, R0, R1          ; idx = x - 128
        BRp     LR_CHECK_MAX
        LD      R0, VAL_Q_ONE
        BR      LR_DONE

LR_CHECK_MAX:
        ADD     R1, R2, R1          ; idx - 128
        BRn     LR_LOOKUP
        LD      R2, CONST_127

LR_LOOKUP:
        ADD     R2, R2, R2          ; *2 bytes por palabra en ISA-G27
        LEA     R1, TABLA_SQRT
        ADD     R1, R1, R2
        LDR     R0, R1, #0

LR_DONE:
        LD      R1, LR_SAVE_R1
        LD      R2, LR_SAVE_R2
        RET

;=====================================================================
; ZONA DE DATOS Y TABLA LUT (Q8.7)
;=====================================================================
VAL_Q_ONE:      .FILL #128
VAL_NEG_Q_ONE:  .FILL #-128
VAL_NEG_Q_TWO:  .FILL #-256
CONST_LN2:      .FILL #89
CONST_64:       .FILL #64
CONST_127:      .FILL #127

LN_TEMP_LNM:    .FILL #0
BK_X_NORM:      .FILL #0
BK_A:           .FILL #0
BK_B:           .FILL #0
BK_M:           .FILL #0
BK_TEMP_NUM:    .FILL #0

LN_SAVE_R1:     .FILL #0
LN_SAVE_R2:     .FILL #0
LN_SAVE_R3:     .FILL #0
LN_SAVE_R4:     .FILL #0
LN_SAVE_R5:     .FILL #0
LN_SAVE_R7:     .FILL #0

BK_SAVE_R1:     .FILL #0
BK_SAVE_R2:     .FILL #0
BK_SAVE_R3:     .FILL #0
BK_SAVE_R4:     .FILL #0
BK_SAVE_R5:     .FILL #0
BK_SAVE_R7:     .FILL #0

LR_SAVE_R1:     .FILL #0
LR_SAVE_R2:     .FILL #0

TABLA_SQRT:
        .FILL #128
        .FILL #128
        .FILL #129
        .FILL #129
        .FILL #130
        .FILL #130
        .FILL #131
        .FILL #131
        .FILL #132
        .FILL #132
        .FILL #133
        .FILL #133
        .FILL #134
        .FILL #134
        .FILL #135
        .FILL #135
        .FILL #136
        .FILL #136
        .FILL #137
        .FILL #137
        .FILL #138
        .FILL #138
        .FILL #138
        .FILL #139
        .FILL #139
        .FILL #140
        .FILL #140
        .FILL #141
        .FILL #141
        .FILL #142
        .FILL #142
        .FILL #143
        .FILL #143
        .FILL #144
        .FILL #144
        .FILL #144
        .FILL #145
        .FILL #145
        .FILL #146
        .FILL #146
        .FILL #147
        .FILL #147
        .FILL #148
        .FILL #148
        .FILL #148
        .FILL #149
        .FILL #149
        .FILL #150
        .FILL #150
        .FILL #151
        .FILL #151
        .FILL #151
        .FILL #152
        .FILL #152
        .FILL #153
        .FILL #153
        .FILL #154
        .FILL #154
        .FILL #154
        .FILL #155
        .FILL #155
        .FILL #156
        .FILL #156
        .FILL #156
        .FILL #157
        .FILL #157
        .FILL #158
        .FILL #158
        .FILL #158
        .FILL #159
        .FILL #159
        .FILL #160
        .FILL #160
        .FILL #160
        .FILL #161
        .FILL #161
        .FILL #162
        .FILL #162
        .FILL #162
        .FILL #163
        .FILL #163
        .FILL #164
        .FILL #164
        .FILL #164
        .FILL #165
        .FILL #165
        .FILL #166
        .FILL #166
        .FILL #166
        .FILL #167
        .FILL #167
        .FILL #168
        .FILL #168
        .FILL #168
        .FILL #169
        .FILL #169
        .FILL #169
        .FILL #170
        .FILL #170
        .FILL #171
        .FILL #171
        .FILL #171
        .FILL #172
        .FILL #172
        .FILL #172
        .FILL #173
        .FILL #173
        .FILL #174
        .FILL #174
        .FILL #174
        .FILL #175
        .FILL #175
        .FILL #175
        .FILL #176
        .FILL #176
        .FILL #176
        .FILL #177
        .FILL #177
        .FILL #178
        .FILL #178
        .FILL #178
        .FILL #179
        .FILL #179
        .FILL #179
        .FILL #180
        .FILL #180
        .FILL #180
        .FILL #181

        .END