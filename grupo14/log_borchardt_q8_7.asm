
; =============================================================================
; MÓDULO SUBRUTINA: LOG_BORCHARDT_Q8_7 (GRUPO 14)
; Arquitectura: LC-3 Assembly
; Formato Punto Fijo: Q8.7 (1.0 = 128 / x0080, 2.0 = 256 / x0100)
; =============================================================================
LOG_BORCHARDT_Q8_7
        ST R7, MAIN_SAVE_R7
        ST R1, MAIN_SAVE_R1
        ST R2, MAIN_SAVE_R2
        ST R3, MAIN_SAVE_R3
        ST R4, MAIN_SAVE_R4

        ADD R2, R0, #0          ; Guarda temporalmente el valor x en el registro R2
        BRnz MAIN_DIV_ZERO      ; Si x <= 0 -> dominio inválido, devuelve -1
        ADD R1, R1, #0
        BRnz MAIN_DIV_ZERO      ; Si b <= 0 -> base inválida, devuelve -1

        ; 1. Calcular ln(b)
        ADD R0, R1, #0                  ; Carga el balor de la base a R0
        JSR LN_GENERAL_Q8_7
        ADD R1, R0, #0                  ; Está para que la división tenga los valores correctos
        
        ; 2. Calcular ln(x)
        ADD R0, R2, #0                  ; Se carga el valor x que estaba en R2
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

; =============================================================================
; SUBRUTINA: LN_GENERAL_Q8_7
; =============================================================================
LN_GENERAL_Q8_7
        ST R7, LNG_SAVE_R7
        ST R1, LNG_SAVE_R1
        ST R2, LNG_SAVE_R2              ; Mantener para que LOG_BORCHARDT_Q8_7 funcione
        ST R4, LNG_SAVE_R4

        ADD R1, R0, #0              ; R1 = x_norm
        AND R2, R2, #0              ; R2 = k = 0

        LD R4, VAL_NEG_Q_TWO        ; R4 = -256

LNG_LOOP_UP                         
        ADD R0, R1, R4              ; x_norm - 256
        BRn LNG_CHECK_DOWN          ;Si la resta da negativo significa que es menor a 2

        ADD R0, R1, #0
        JSR SHIFT_RIGHT_1
        ADD R1, R0, #0
        ADD R2, R2, #1              ; k++
        BR LNG_LOOP_UP

LNG_CHECK_DOWN
        LD R4, VAL_NEG_Q_ONE              ; R4 = -128
        
LNG_LOOP_DOWN
        ADD R0, R1, R4
        BRzp LNG_EVAL_KERNEL

        ADD R1, R1, R1              ; x_norm <<= 1
        ADD R2, R2, #-1             ; k--
        BR LNG_LOOP_DOWN

LNG_EVAL_KERNEL
        ADD R0, R1, #0
        JSR BORCHARDT_KERNEL

        ST R0, LNG_TEMP_LNM
        ADD R0, R2, #0
        LD R1, CONST_LN2            ; 89 en Q8.7 (~ln(2))
        JSR MULT_SIGNED

        LD R1, LNG_TEMP_LNM
        ADD R0, R0, R1

        LD R7, LNG_SAVE_R7
        LD R1, LNG_SAVE_R1
        LD R2, LNG_SAVE_R2
        LD R4, LNG_SAVE_R4
        RET

LNG_SAVE_R7     .BLKW #1
LNG_SAVE_R1     .BLKW #1
LNG_SAVE_R2     .BLKW #1
LNG_SAVE_R4     .BLKW #1
LNG_TEMP_LNM    .BLKW #1
VAL_Q_ONE       .FILL #128
VAL_NEG_Q_ONE   .FILL #-128
VAL_NEG_Q_TWO    .FILL #-256
CONST_LN2       .FILL #89

; =============================================================================
; SUBRUTINA: BORCHARDT_KERNEL
; =============================================================================
BORCHARDT_KERNEL
        ST R7, BK_SAVE_R7
        ST R1, BK_SAVE_R1
        ST R4, BK_SAVE_R4
        ST R5, BK_SAVE_R5

        ST R0, BK_X_NORM

        LD R1, VAL_Q_ONE
        ADD R0, R0, R1
        JSR SHIFT_RIGHT_1
        ST R0, BK_A

        LD R0, BK_X_NORM
        JSR LEER_RAIZ_NORM_Q8_7
        ST R0, BK_B

        AND R5, R5, #0

BK_FOR_LOOP
        ADD R4, R5, #-4
        BRzp BK_LOOP_END

        LD R0, BK_A
        LD R1, BK_B
        ADD R0, R0, R1
        JSR SHIFT_RIGHT_1
        ST R0, BK_A

        JSR MULT_UNSIGNED
        LD R1, CONST_64
        ADD R0, R0, R1
        JSR SHIFT_RIGHT_7

        JSR LEER_RAIZ_NORM_Q8_7
        ST R0, BK_B

        ADD R5, R5, #1
        BR BK_FOR_LOOP

BK_LOOP_END
        LD R0, BK_A
        LD R1, BK_B
        ADD R0, R0, R1
        JSR SHIFT_RIGHT_1
        ST R0, BK_M

        LD R0, BK_X_NORM
        LD R1, VAL_NEG_Q_ONE
        ADD R0, R0, R1
        JSR SHIFT_LEFT_7
        
        LD R1, BK_M
        ST R0, BK_TEMP_NUM
        ADD R0, R1, #0
        JSR SHIFT_RIGHT_1
        LD R1, BK_TEMP_NUM
        ADD R0, R0, R1

        LD R1, BK_M
        JSR DIV_UNSIGNED

        LD R7, BK_SAVE_R7
        LD R1, BK_SAVE_R1
        LD R4, BK_SAVE_R4
        LD R5, BK_SAVE_R5
        RET

BK_SAVE_R7      .BLKW #1
BK_SAVE_R1      .BLKW #1
BK_SAVE_R4      .BLKW #1
BK_SAVE_R5      .BLKW #1
BK_X_NORM       .BLKW #1
BK_A            .BLKW #1
BK_B            .BLKW #1
BK_M            .BLKW #1
BK_TEMP_NUM     .BLKW #1
CONST_64        .FILL #64

; =============================================================================
; SUBRUTINA: LEER_RAIZ_NORM_Q8_7
; =============================================================================
LEER_RAIZ_NORM_Q8_7
        ST R1, LR_SAVE_R1
        ST R2, LR_SAVE_R2

        LD R1, VAL_NEG_Q_ONE
        ADD R2, R0, R1
        
        BRp LR_CHECK_MAX
        LD R0, VAL_Q_ONE
        BR LR_DONE

LR_CHECK_MAX
        ADD R1, R2, R1
        BRn LR_LOOKUP
        LD R2, CONST_127

LR_LOOKUP
        LEA R1, TABLA_SQRT
        ADD R1, R1, R2
        LDR R0, R1, #0

LR_DONE
        LD R1, LR_SAVE_R1
        LD R2, LR_SAVE_R2
        RET

LR_SAVE_R1      .BLKW #1
LR_SAVE_R2      .BLKW #1
CONST_127       .FILL #127

; =============================================================================
; SUBRUTINA: CALC_LOG_BASE_Q8_7 (SIN PÉRDIDA DE REGISTROS)
; =============================================================================
CALC_LOG_BASE_Q8_7
        ST R7, CLB_SAVE_R7
        ST R1, CLB_SAVE_R1
        ST R2, CLB_SAVE_R2
        ST R3, CLB_SAVE_R3
        ST R4, CLB_SAVE_R4
        ST R5, CLB_SAVE_R5

        AND R2, R2, #0

        ADD R0, R0, #0
        BRzp CLB_NUM_POS
        NOT R0, R0
        ADD R0, R0, #1          ; R0 = |ln(x)|
        ADD R2, R2, #1          ; marcamos signo negativo
        
 CLB_NUM_POS
         ADD R3, R1, #0              ; R3 = den = ln(b)

        
        BRz CLB_ZERO_DIV

        BRp CLB_DEN_POS
        NOT R3, R3
        ADD R3, R3, #1          ; R3 = |ln(b)|
        ADD R2, R2, #-1         ; invierte la bandera de signo
        
CLB_DEN_POS

; Escala |ln(x)| por 64 (6 desplazamientos, nunca supera 65535)
    ADD R0, R0, R0
    ADD R0, R0, R0
    ADD R0, R0, R0
    ADD R0, R0, R0
    ADD R0, R0, R0
    ADD R0, R0, R0
    ADD R4, R0, #0          ; R4 = |ln(x)| * 64

    ; Primera división: q1 = (|ln(x)| * 64) / |ln(b)|
    ADD R1, R3, #0
    JSR DIV_UNSIGNED
    ADD R5, R0, #0          ; R5 = q1

    ; Calcula el resto: r1 = R4 - (q1 * |ln(b)|)
    ADD R1, R3, #0
    JSR MULT_UNSIGNED
    NOT R0, R0
    ADD R0, R0, #1
    ADD R0, R4, R0          ; R0 = r1

    ; Ajuste de la mitad faltante con redondeo: q2 = (2*r1 + |ln(b)|/2) / |ln(b)|
    ADD R0, R0, R0          ; 2 * r1
    ADD R4, R0, #0
    ADD R0, R3, #0
    JSR SHIFT_RIGHT_1       ; |ln(b)| / 2
    ADD R0, R4, R0
    ADD R1, R3, #0
    JSR DIV_UNSIGNED        ; R0 = q2

    ; Resultado final: 2 * q1 + q2
    ADD R5, R5, R5
    ADD R0, R5, R0
        ADD R2, R2, #0
        BRz CLB_EXIT
        NOT R0, R0
        ADD R0, R0, #1
        BR CLB_EXIT

CLB_ZERO_DIV
        AND R0, R0, #0
        ADD R0, R0, #-1

CLB_EXIT
        LD R7, CLB_SAVE_R7
        LD R1, CLB_SAVE_R1
        LD R2, CLB_SAVE_R2
        LD R3, CLB_SAVE_R3
        LD R4, CLB_SAVE_R4
        LD R5, CLB_SAVE_R5
        RET

CLB_SAVE_R7     .BLKW #1
CLB_SAVE_R1     .BLKW #1
CLB_SAVE_R2     .BLKW #1
CLB_SAVE_R3     .BLKW #1
CLB_SAVE_R4     .BLKW #1
CLB_SAVE_R5     .BLKW #1

; =============================================================================
; SUBRUTINAS MATEMÁTICAS AUXILIARES
; =============================================================================
SHIFT_RIGHT_1               ;Divide en dos al numero dado
        ST R1, SR1_R1
        ST R2, SR1_R2           ; Contador    

        AND R2, R2, #0
        ADD R2, R2, #15
        AND R1, R1, #0

BUCLE_FOR
        ADD R1, R1, R1
        ADD R0, R0, #0
        BRzp CONTINUA
        ADD R1, R1, #1

CONTINUA
        ADD R0, R0, R0
        ADD R2, R2, #-1
        BRp BUCLE_FOR
        
        ADD R0, R1, #0
        
        LD R1, SR1_R1
        LD R2, SR1_R2
        RET

SR1_R1          .BLKW #1
SR1_R2          .BLKW #1

SHIFT_RIGHT_7
        ST R1, SR7_R1
        ST R7, SR7_R7
        
        LD R1, VAL_Q_ONE
        JSR DIV_UNSIGNED
        
        LD R1, SR7_R1
        LD R7, SR7_R7
        RET

SR7_R1          .BLKW #1
SR7_R7          .BLKW #1

SHIFT_LEFT_7
        ADD R0, R0, R0
        ADD R0, R0, R0
        ADD R0, R0, R0
        ADD R0, R0, R0
        ADD R0, R0, R0
        ADD R0, R0, R0
        ADD R0, R0, R0
        RET

MULT_UNSIGNED
    ST R2, MU_R2
    ST R3, MU_R3
    ST R4, MU_R4
    ADD R2, R0, #0          ; R2 = multiplicando
    ADD R3, R1, #0          ; R3 = multiplicador (se lee bit a bit)
    AND R0, R0, #0          ; R0 = acumulador en 0
    AND R4, R4, #0
    ADD R4, R4, #-16        ; Contador de 16 bits (-16 hasta 0)

MU_LOOP
    ADD R0, R0, R0          ; Desplaza el acumulador 1 bit a la izquierda
    ADD R3, R3, #0          ; Evalúa el bit más significativo (bit 15) de R3
    BRzp MU_SKIP            ; Si el bit 15 es 0 (positivo/cero), no suma
    ADD R0, R0, R2          ; Si el bit 15 es 1 (negativo), suma el multiplicando
MU_SKIP
    ADD R3, R3, R3          ; Desplaza R3 a la izquierda para traer el siguiente bit
    ADD R4, R4, #1          ; Avanza el contador
    BRn MU_LOOP             ; Repite mientras R4 < 0 (16 vueltas exactas)

    LD R2, MU_R2
    LD R3, MU_R3
    LD R4, MU_R4
    RET

MU_R2   .BLKW #1
MU_R3   .BLKW #1
MU_R4   .BLKW #1

MULT_SIGNED
    ST R7, MS_R7
    ST R4, MS_R4
    AND R4, R4, #0          ; Contador de signos negativos

    ADD R0, R0, #0
    BRzp MS_CHECK_R1
    NOT R0, R0
    ADD R0, R0, #1
    ADD R4, R4, #1

MS_CHECK_R1
    ADD R1, R1, #0
    BRzp MS_DO_MULT
    NOT R1, R1
    ADD R1, R1, #1
    ADD R4, R4, #1

MS_DO_MULT
    JSR MULT_UNSIGNED

    AND R4, R4, #1
    BRz MS_DONE
    NOT R0, R0
    ADD R0, R0, #1

MS_DONE
    LD R7, MS_R7
    LD R4, MS_R4
    RET

MS_R7   .BLKW #1
MS_R4   .BLKW #1

DIV_UNSIGNED
    ST R2, DU_R2
    ST R3, DU_R3            ; Antes era R6
    ST R4, DU_R4
    ST R5, DU_R5
    ADD R2, R0, #0          ; R2 = dividendo
    AND R0, R0, #0          ; R0 = cociente = 0
    ADD R1, R1, #0          ; Verifica divisor == 0
    BRz DU_DONE

    NOT R1, R1
    ADD R1, R1, #1          ; R1 = -divisor
    AND R4, R4, #0          ; R4 = resto = 0
    AND R5, R5, #0
    ADD R5, R5, #-16        ; Contador de 16 bits (-16 hasta 0)

DU_LOOP
    ADD R4, R4, R4
    ADD R2, R2, #0
    BRzp DU_NO_BIT
    ADD R4, R4, #1
DU_NO_BIT
    ADD R2, R2, R2
    ADD R0, R0, R0
    ADD R3, R4, R1          ; Antes era R6 (R3 = resto - divisor)
    BRn DU_NEXT
    ADD R4, R3, #0          ; Antes era R6
    ADD R0, R0, #1
DU_NEXT
    ADD R5, R5, #1
    BRn DU_LOOP

DU_DONE
    LD R2, DU_R2
    LD R3, DU_R3            ; Antes era R6
    LD R4, DU_R4
    LD R5, DU_R5
    RET

DU_R2   .BLKW #1
DU_R3   .BLKW #1            ; Antes era DU_R6
DU_R4   .BLKW #1
DU_R5   .BLKW #1
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
