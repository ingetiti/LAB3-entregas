; Logaritmo natural por algoritmo de Borchardt: entrada R0 = x en Q8.7,
; salida R0 = ln(x) en Q8.7 (-1 si x <= 0).
LN_GENERAL_Q8_7
        PUSHM   #xBE
        ADD     R0, R0, #0
        BRp     LOG7_POS
        MOVI    R0, #-1
        BRnzp   LOG7_END
LOG7_POS
        ; Normalizar x = m * 2^k, m en [1.0, 2.0) en Q2.13 (x2000..x3FFF)
        ; En Q8.7, 1.0 = x0080 -> CLZ = 8; k = 8 - lz
        CLZ     R5, R0
        MOVI    R2, #8
        SUB     R4, R2, R5          ; R4 = k = 8 - lz
        ST      R4, BORD_K
        ADD     R2, R5, #-1
        BRnp    LOG7_SHL
        SHR     R1, R0, #1          ; lz == 1 -> m en Q2.13
        BRnzp   LOG7_NORM_OK
LOG7_SHL
        ADD     R2, R5, #-2         ; lz - 2 in [0..13]
        SHL     R1, R0, R2          ; R1 = m en Q2.13
LOG7_NORM_OK
        MOVI    R2, #0
        MOVH    R2, #x20            ; 1.0 en Q2.13 = x2000
        SUB     R3, R1, R2          ; R3 = m - 1.0 en Q2.13
        BRnp    LOG7_BORCHARDT
        AND     R0, R0, #0          ; m == 1.0 -> ln(m) = 0
        BRnzp   LOG7_ADD_K
LOG7_BORCHARDT
        ST      R3, BORD_M1         ; guardar (m - 1.0)
        ADD     R3, R1, R2
        ADD     R3, R3, #1
        SHR     R3, R3, #1          ; R3 = a_0 = (1.0 + m) / 2 en Q2.13
        ADD     R0, R1, #0
        JSR     BORD_SQRT_Q13
        ADD     R4, R0, #0          ; R4 = g_0 = sqrt(m) en Q2.13

        MOVI    R5, #4              ; 4 iteraciones de Borchardt
LOG7_ITER
        ADD     R3, R3, R4
        ADD     R3, R3, #1
        SHR     R3, R3, #1          ; a_{n+1} = (a_n + g_n) / 2
        MULQ14  R0, R3, R4          ; (a * g) >> 14
        SHL     R0, R0, #1          ; -> Q2.13
        JSR     BORD_SQRT_Q13
        ADD     R4, R0, #0          ; g_{n+1} = sqrt(a_{n+1} * g_n)
        ADD     R5, R5, #-1
        BRp     LOG7_ITER

        ; ln(m) = (m - 1) / a_4 en Q2.13
        LD      R1, BORD_M1
        DIVQ14  R0, R1, R3
        ADD     R0, R0, #1
        SHR     R0, R0, #1          ; ln(m) en Q2.13
        ; Convertir Q2.13 -> Q8.7 con redondeo (+32 >> 6)
        MOVI    R1, #32
        ADD     R0, R0, R1
        SHR     R0, R0, #6
LOG7_ADD_K
        LD      R4, BORD_K
        MOVI    R1, #89             ; ln(2) en Q8.7 = 89
        MUL     R1, R4, R1
        ADD     R0, R0, R1
LOG7_END
        POPM    #xBE
        RET

; Entrada: R0 = v en Q2.13 [x2000..x4800]
; Salida:  R0 = sqrt(v) en Q2.13 (preserva R1..R5, R7)
BORD_SQRT_Q13
        PUSHM   #x9E                ; guarda R1..R4, R7
        ADD     R1, R0, #0          ; R1 = v
        MOVI    R2, #0
        MOVH    R2, #x20            ; 1.0 en Q2.13
        ADD     R0, R1, R2
        SHR     R0, R0, #1          ; s_0 = (1.0 + v) / 2
        MOVI    R3, #4              ; 4 iteraciones de Newton
BORD_SQRT_LOOP
        DIVQ14  R2, R1, R0          ; (v / s) en Q0.14
        ADD     R2, R2, #1
        SHR     R2, R2, #1          ; (v / s) en Q2.13
        ADD     R0, R0, R2
        ADD     R0, R0, #1
        SHR     R0, R0, #1          ; s = (s + v/s) / 2
        ADD     R3, R3, #-1
        BRp     BORD_SQRT_LOOP
        POPM    #x9E
        RET

BORD_K  .FILL #0
BORD_M1 .FILL #0
.END
