; =============================================================================
; MÓDULO SUBRUTINA: LOG_BORCHARDT_Q8_7 (GRUPO 14) - NUEVA ISA 16-BIT
; Formato Punto Fijo: Q8.7 (1.0 = 128 / x0080, 2.0 = 256 / x0100)
; Optimizaciones: PUSHM/POPR, LSR/SHL, CMP, NEG, SUB, MOVI/LI, BRc/BRlt.
; =============================================================================
LOG_BORCHARDT_Q8_7
        PUSHM {R1, R2, R7}

        ADDI R2, R0, #0         ; Guarda x en R2
        BRnz MAIN_DIV_ZERO      ; Si x <= 0 -> dominio inválido, devuelve -1
        ADDI R1, R1, #0
        BRnz MAIN_DIV_ZERO      ; Si b <= 0 -> base inválida, devuelve -1

        ; 1. Calcular ln(b)
        MOV R0, R1
        JSR LN_GENERAL_Q8_7
        MOV R1, R0              ; R1 = ln(b)

        ; 2. Calcular ln(x)
        MOV R0, R2
        JSR LN_GENERAL_Q8_7     ; R0 = ln(x)

        ; 3. Cambio de base: log_b(x) = ln(x) / ln(b)
        ADDI R1, R1, #0
        BRz MAIN_DIV_ZERO

        JSR CALC_LOG_BASE_Q8_7
        BR MAIN_FINISH

MAIN_DIV_ZERO
        MOVI R0, #-1

MAIN_FINISH
        POPR {R1, R2, R7}

; =============================================================================
; SUBRUTINA: LN_GENERAL_Q8_7
; =============================================================================
LN_GENERAL_Q8_7
        PUSHM {R1, R2, R4, R7}

        MOV R1, R0              ; R1 = x_norm
        CLR R2                  ; R2 = k = 0
        LI R4, #256             ; R4 = 2.0 en Q8.7

LNG_LOOP_UP
        CMP R1, R4              ; x_norm - 256
        BRlt LNG_CHECK_DOWN     ; Si < 256, pasar a límite inferior
        LSR R1, R1, #1          ; x_norm >>= 1 (reemplaza SHIFT_RIGHT_1)
        INC R2                  ; k++
        BR LNG_LOOP_UP

LNG_CHECK_DOWN
        LSR R4, R4, #1          ; R4 = 128 (1.0 en Q8.7)

LNG_LOOP_DOWN
        CMP R1, R4              ; x_norm - 128
        BRge LNG_EVAL_KERNEL    ; Si >= 128, evaluar kernel
        SHL R1, R1, #1          ; x_norm <<= 1
        DEC R2                  ; k--
        BR LNG_LOOP_DOWN

LNG_EVAL_KERNEL
        MOV R0, R1
        JSR BORCHARDT_KERNEL
        MOV R4, R0              ; R4 = ln(x_norm) (preservado por MULT_SIGNED)

        MOV R0, R2
        MOVI R1, #89            ; CONST_LN2 = 89 en Q8.7 (~ln(2))
        JSR MULT_SIGNED
        ADD R0, R0, R4          ; ln(x) = k*ln(2) + ln(x_norm)

        POPR {R1, R2, R4, R7}

; =============================================================================
; SUBRUTINA: BORCHARDT_KERNEL
; =============================================================================
BORCHARDT_KERNEL
        PUSHM {R1, R2, R3, R4, R5, R7}

        MOV R2, R0              ; R2 = x_norm
        LI R1, #128
        ADD R3, R0, R1
        LSR R3, R3, #1          ; R3 = a = (x_norm + 128) >> 1

        JSR LEER_RAIZ_NORM_Q8_7
        MOV R4, R0              ; R4 = b = sqrt(x_norm)

        MOVI R5, #4             ; 4 iteraciones

BK_FOR_LOOP
        ADD R3, R3, R4
        LSR R3, R3, #1          ; a = (a + b) >> 1

        MOV R0, R3
        MOV R1, R4
        JSR MULT_UNSIGNED       ; R0 = a * b
        MOVI R1, #64
        ADD R0, R0, R1
        LSR R0, R0, #7          ; (a*b + 64) >> 7 (reemplaza SHIFT_RIGHT_7)

        JSR LEER_RAIZ_NORM_Q8_7
        MOV R4, R0              ; b = sqrt(...)

        DEC R5
        BRp BK_FOR_LOOP

        ADD R1, R3, R4
        LSR R1, R1, #1          ; R1 = m = (a + b) >> 1

        LI R0, #128
        SUB R0, R2, R0
        SHL R0, R0, #7          ; (x_norm - 128) << 7 (reemplaza SHIFT_LEFT_7)
        LSR R3, R1, #1          ; m >> 1 para redondeo
        ADD R0, R0, R3

        JSR DIV_UNSIGNED        ; R0 = ((x_norm - 128)<<7 + m>>1) / m

        POPR {R1, R2, R3, R4, R5, R7}

; =============================================================================
; SUBRUTINA: LEER_RAIZ_NORM_Q8_7
; =============================================================================
LEER_RAIZ_NORM_Q8_7
        PUSHM {R1, R2}

        LI R1, #128
        SUB R2, R0, R1          ; idx = x_norm - 128
        BRp LR_CHECK_MAX
        MOV R0, R1              ; Si <= 128, devuelve 128
        BR LR_DONE

LR_CHECK_MAX
        CMP R2, R1              ; idx < 128 ?
        BRlt LR_LOOKUP
        MOVI R2, #127

LR_LOOKUP
        LEA R1, TABLA_SQRT
        SHL R2, R2, #1          ; Índice de palabra -> desplazamiento en bytes
        ADD R1, R1, R2
        LDW R0, R1, #0

LR_DONE
        POPM {R1, R2}
        RET

; =============================================================================
; SUBRUTINA: CALC_LOG_BASE_Q8_7
; =============================================================================
CALC_LOG_BASE_Q8_7
        PUSHM {R1, R2, R3, R4, R5, R7}

        CLR R2                  ; R2 = signo
        ADDI R0, R0, #0
        BRzp CLB_NUM_POS
        NEG R0, R0              ; R0 = |ln(x)|
        INC R2

CLB_NUM_POS
        ADDI R3, R1, #0         ; R3 = ln(b)
        BRz CLB_ZERO_DIV
        BRp CLB_DEN_POS
        NEG R3, R3              ; R3 = |ln(b)|
        DEC R2

CLB_DEN_POS
        ; Escala |ln(x)| por 64
        SHL R0, R0, #6
        MOV R4, R0              ; R4 = |ln(x)| * 64

        ; Primera división: q1 = (|ln(x)| * 64) / |ln(b)|
        MOV R1, R3
        JSR DIV_UNSIGNED
        MOV R5, R0              ; R5 = q1

        ; Resto: r1 = R4 - (q1 * |ln(b)|)
        MOV R1, R3
        JSR MULT_UNSIGNED
        SUB R0, R4, R0          ; R0 = r1

        ; Ajuste con redondeo: q2 = (2*r1 + |ln(b)|/2) / |ln(b)|
        SHL R0, R0, #1          ; 2 * r1
        MOV R4, R0
        LSR R0, R3, #1          ; |ln(b)| / 2
        ADD R0, R4, R0
        MOV R1, R3
        JSR DIV_UNSIGNED        ; R0 = q2

        ; Resultado final: 2 * q1 + q2
        SHL R5, R5, #1
        ADD R0, R5, R0
        ADDI R2, R2, #0
        BRz CLB_EXIT
        NEG R0, R0
        BR CLB_EXIT

CLB_ZERO_DIV
        MOVI R0, #-1

CLB_EXIT
        POPR {R1, R2, R3, R4, R5, R7}

; =============================================================================
; SUBRUTINAS MATEMÁTICAS AUXILIARES
; =============================================================================
MULT_UNSIGNED
        PUSHM {R2, R3, R4}
        MOV R2, R0              ; R2 = multiplicando
        MOV R3, R1              ; R3 = multiplicador
        CLR R0                  ; R0 = acumulador
        MOVI R4, #16

MU_LOOP
        SHL R0, R0, #1
        SHL R3, R3, #1          ; bit 15 de R3 -> C
        BRnc MU_SKIP
        ADD R0, R0, R2
MU_SKIP
        DEC R4
        BRp MU_LOOP

        POPM {R2, R3, R4}
        RET

MULT_SIGNED
        PUSHM {R4, R7}
        CLR R4

        ADDI R0, R0, #0
        BRzp MS_CHECK_R1
        NEG R0, R0
        INC R4

MS_CHECK_R1
        ADDI R1, R1, #0
        BRzp MS_DO_MULT
        NEG R1, R1
        INC R4

MS_DO_MULT
        JSR MULT_UNSIGNED
        ANDI R4, R4, #1
        BRz MS_DONE
        NEG R0, R0

MS_DONE
        POPR {R4, R7}

DIV_UNSIGNED
        PUSHM {R2, R3, R4}
        MOV R2, R0              ; R2 = dividendo
        CLR R0                  ; R0 = cociente
        ADDI R1, R1, #0         ; Verifica divisor == 0
        BRz DU_DONE

        CLR R3                  ; R3 = resto = 0
        MOVI R4, #16

DU_LOOP
        SHL R2, R2, #1          ; bit 15 de R2 -> C
        RLC R3, R3              ; resto = (resto << 1) | C
        SHL R0, R0, #1          ; cociente <<= 1
        CMP R3, R1              ; C=1 si resto < divisor
        BRc DU_NEXT
        SUB R3, R3, R1
        INC R0
DU_NEXT
        DEC R4
        BRp DU_LOOP

DU_DONE
        POPM {R2, R3, R4}
        RET

; =============================================================================
; TABLA DE RAÍCES CUADRADAS (LUT - 128 PALABRAS EN FORMATO Q8.7)
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
