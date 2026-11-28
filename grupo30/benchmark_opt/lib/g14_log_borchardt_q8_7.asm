; =============================================================================
; MODULO SUBRUTINA: LOG_BORCHARDT_Q8_7 (GRUPO 14, OPTIMIZADA)
; Formato Punto Fijo: Q8.7 (1.0 = 128 / x0080, 2.0 = 256 / x0100)
; Algoritmo: Normalizacion a [1, 2) + nucleo iterativo de Borchardt (4 pasos)
;   con LUT de raices cuadradas + suma de k*ln(2).
; =============================================================================

LOG_BORCHARDT_Q8_7
        PUSHM {R1, R2, R3, R4, R7}

        ADD  R2, R0, #0
        BRnz MAIN_DIV_ZERO
        CMP  R1, #0
        BRnz MAIN_DIV_ZERO

        ADD  R0, R1, #0
        JSR  LN_GENERAL_Q8_7
        ADD  R1, R0, #0

        ADD  R0, R2, #0
        JSR  LN_GENERAL_Q8_7

        CMP  R1, #0
        BRz  MAIN_DIV_ZERO

        JSR  CALC_LOG_BASE_Q8_7
        BRnzp MAIN_FINISH

MAIN_DIV_ZERO
        MOVI R0, #-1

MAIN_FINISH
        POPM {R1, R2, R3, R4, R7}
        RET

; =============================================================================
; SUBRUTINA: LN_GENERAL_Q8_7
; =============================================================================
LN_GENERAL_Q8_7
        PUSHM {R1, R2, R4, R7}

        ADD  R1, R0, #0         ; x_norm
        MOVI R2, #0             ; k = 0
        LD   R4, VAL_Q_TWO      ; 256

LNG_LOOP_UP
        CMP  R1, R4
        BRn  LNG_CHECK_DOWN
        LSR  R1, R1, #1
        ADD  R2, R2, #1
        BRnzp LNG_LOOP_UP

LNG_CHECK_DOWN
        LD   R4, VAL_Q_ONE      ; 128

LNG_LOOP_DOWN
        CMP  R1, R4
        BRzp LNG_EVAL_KERNEL
        SHL  R1, R1, #1
        ADD  R2, R2, #-1
        BRnzp LNG_LOOP_DOWN

LNG_EVAL_KERNEL
        ADD  R0, R1, #0
        JSR  BORCHARDT_KERNEL   ; R0 = ln(x_norm)
        LD   R1, CONST_LN2      ; 89
        MULL R1, R2, R1         ; k * ln(2)
        ADD  R0, R0, R1

        POPM {R1, R2, R4, R7}
        RET

VAL_Q_ONE       .FILL #128
VAL_Q_TWO       .FILL #256
CONST_LN2       .FILL #89

; =============================================================================
; SUBRUTINA: BORCHARDT_KERNEL
; =============================================================================
BORCHARDT_KERNEL
        PUSHM {R1, R2, R3, R4, R5, R7}

        ; R2 = x_norm, R3 = a, R4 = b, R5 = contador (4 iteraciones)
        ADD  R2, R0, #0
        LD   R1, VAL_Q_ONE
        ADD  R3, R2, R1
        LSR  R3, R3, #1         ; a = (x_norm + 128) >> 1

        ADD  R0, R2, #0
        JSR  LEER_RAIZ_NORM_Q8_7
        ADD  R4, R0, #0         ; b = sqrt(x_norm)

        MOVI R5, #4

BK_FOR_LOOP
        ADD  R3, R3, R4
        LSR  R3, R3, #1         ; a = (a + b) >> 1

        ; (a * b + 64) >> 7 usando MULQ nativo (redondeo simetrico +2^6)
        ADD  R0, R3, #0
        MULQ R0, R4, #7

        JSR  LEER_RAIZ_NORM_Q8_7
        ADD  R4, R0, #0         ; b = sqrt(a * b)

        ADD  R5, R5, #-1
        BRp  BK_FOR_LOOP

        ; m = (a + b) >> 1
        ADD  R1, R3, R4
        LSR  R1, R1, #1

        ; num = ((x_norm - 128) << 7) + (m >> 1)
        LD   R0, VAL_Q_ONE
        SUB  R0, R2, R0
        SHL  R0, R0, #7
        LSR  R3, R1, #1
        ADD  R0, R0, R3

        ; resultado = num / m (ambos >= 0 y < 32768 -> DIV directo)
        DIV  R0, R0, R1

        POPM {R1, R2, R3, R4, R5, R7}
        RET

; =============================================================================
; SUBRUTINA: LEER_RAIZ_NORM_Q8_7
; =============================================================================
LEER_RAIZ_NORM_Q8_7
        PUSHM {R1, R2}
        LD   R1, VAL_Q_ONE
        SUB  R2, R0, R1
        BRp  LR_CHECK_MAX
        ADD  R0, R1, #0
        BRnzp LR_DONE

LR_CHECK_MAX
        CMP  R2, R1
        BRn  LR_LOOKUP
        LD   R2, CONST_127

LR_LOOKUP
        LD   R1, PTR_TABLA_SQRT
        SHL  R2, R2, #1
        ADD  R1, R1, R2
        LDR  R0, R1, #0

LR_DONE
        POPM {R1, R2}
        RET

CONST_127       .FILL #127
PTR_TABLA_SQRT  .FILL TABLA_SQRT

; =============================================================================
; SUBRUTINA: CALC_LOG_BASE_Q8_7
; =============================================================================
CALC_LOG_BASE_Q8_7
        PUSHM {R1, R2, R3, R4, R5, R7}

        XOR  R2, R0, R1         ; bit 15 = signo final
        ABS  R0, R0
        ABS  R3, R1
        BRz  CLB_ZERO_DIV

        ; R4 = |ln(x)| * 64 (unsigned 16 bits)
        SHL  R4, R0, #6
        ADD  R0, R4, #0
        ADD  R1, R3, #0
        JSR  DIV_UNSIGNED
        ADD  R5, R0, #0         ; q1

        MULL R0, R5, R3
        SUB  R0, R4, R0         ; r1
        SHL  R0, R0, #1         ; 2*r1
        LSR  R1, R3, #1         ; den/2
        ADD  R0, R0, R1
        ADD  R1, R3, #0
        JSR  DIV_UNSIGNED       ; q2

        SHL  R5, R5, #1
        ADD  R0, R5, R0
        CMP  R2, #0
        BRzp CLB_EXIT
        NEG  R0, R0
        BRnzp CLB_EXIT

CLB_ZERO_DIV
        MOVI R0, #-1

CLB_EXIT
        POPM {R1, R2, R3, R4, R5, R7}
        RET

; DIV_UNSIGNED: R0 = unsigned(R0) / unsigned(R1)
DIV_UNSIGNED
        CMP  R1, #0
        BRz  DU_ZERO
        CMP  R0, #0
        BRn  DU_SLOW
        CMP  R1, #0
        BRn  DU_SLOW
        DIV  R0, R0, R1
        RET
DU_ZERO
        MOVI R0, #0
        RET
DU_SLOW
        PUSHM {R2, R3, R4, R5}
        ADD  R2, R0, #0
        MOVI R0, #0
        MOVI R4, #0
        MOVI R5, #16
DU_LOOP
        SHL  R4, R4, #1
        CMP  R2, #0
        BRzp DU_NO_BIT
        ADD  R4, R4, #1
DU_NO_BIT
        SHL  R2, R2, #1
        SHL  R0, R0, #1
        SUB  R3, R4, R1
        BRn  DU_NEXT
        ADD  R4, R3, #0
        ADD  R0, R0, #1
DU_NEXT
        ADD  R5, R5, #-1
        BRp  DU_LOOP
        POPM {R2, R3, R4, R5}
        RET

; =============================================================================
; TABLA DE RAICES CUADRADAS (LUT - 128 PALABRAS EN FORMATO Q8.7)
; =============================================================================
TABLA_SQRT
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
