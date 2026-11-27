; Logaritmo natural CORDIC hiperbolico: entrada R0 = x en Q3.12,
; salida R0 = ln(x) en Q3.12 (x8000 si x <= 0 o desborde negativo).
CORDIC_LOG_BASE
        PUSHM   #xBE
        ADD     R0, R0, #0
        BRp     LOG_POS
        MOVI    R0, #0
        MOVH    R0, #x80
        BRnzp   LOG_END
LOG_POS
        ; Normalizar x = m * 2^k, m en [1.0, 2.0) en Q2.13 (x2000..x3FFF)
        ; lz = CLZ(x) en 1..15; k = 3 - lz (para x=1.0=x1000, lz=3, k=0)
        CLZ     R5, R0              ; R5 = lz
        MOVI    R2, #3
        SUB     R4, R2, R5          ; R4 = k = 3 - lz
        ST      R4, LOG_K
        ADD     R2, R5, #-1
        BRnp    LOG_SHL
        SHR     R1, R0, #1          ; lz == 1 -> desplazar 1 a la derecha
        BRnzp   LOG_NORM_OK
LOG_SHL
        ADD     R2, R5, #-2         ; desplazar (lz - 2) a la izquierda (0..13)
        SHL     R1, R0, R2
LOG_NORM_OK
        ; x_c = m + 1.0, y_c = m - 1.0 en Q2.13; z_c = 0 en Q1.14
        MOVI    R3, #0
        MOVH    R3, #x20            ; 1.0 en Q2.13 = x2000
        AND     R2, R2, #0          ; R2 = z_c = 0 en Q1.14
        ADD     R0, R1, R3          ; R0 = x_c
        SUB     R1, R1, R3          ; R1 = y_c
        BRz     LOG_CORDIC_DONE     ; si m == 1.0 (y_c == 0), ln(m) = 0

        LEA     R5, CORDIC_IDX_TBL
        LEA     R4, CORDIC_ATANH_TBL
        ST      R4, LOG_TBL_PTR
        MOVI    R3, #13             ; 13 pasos (i = 1,2,3,4,4,5..12)
        ST      R3, LOG_CNT
LOG_LOOP
        LDR     R3, R5, #0          ; R3 = i (desplazamiento)
        ASR     R4, R1, R3          ; dy = y_c >> i
        ADD     R1, R1, #0
        BRn     LOG_Y_NEG
        ; y_c >= 0: x' = x - (y>>i), y' = y - (x>>i), z += table[k]
        SUB     R4, R0, R4          ; R4 = x_new
        ASR     R0, R0, R3          ; R0 = x >> i
        SUB     R1, R1, R0          ; R1 = y_new
        ADD     R0, R4, #0          ; R0 = x_new
        LD      R4, LOG_TBL_PTR
        LDR     R4, R4, #0
        ADD     R2, R2, R4
        BRnzp   LOG_NEXT
LOG_Y_NEG
        ; y_c < 0: x' = x + (y>>i), y' = y + (x>>i), z -= table[k]
        ADD     R4, R0, R4          ; R4 = x_new
        ASR     R0, R0, R3          ; R0 = x >> i
        ADD     R1, R1, R0          ; R1 = y_new
        ADD     R0, R4, #0          ; R0 = x_new
        LD      R4, LOG_TBL_PTR
        LDR     R4, R4, #0
        SUB     R2, R2, R4
LOG_NEXT
        ADD     R1, R1, #0
        BRz     LOG_CORDIC_DONE
        ADD     R5, R5, #2
        LD      R4, LOG_TBL_PTR
        ADD     R4, R4, #2
        ST      R4, LOG_TBL_PTR
        LD      R3, LOG_CNT
        ADD     R3, R3, #-1
        ST      R3, LOG_CNT
        BRp     LOG_LOOP

LOG_CORDIC_DONE
        ; Convertir ln(m) de Q1.14 a Q3.12 con redondeo
        ADD     R2, R2, #2
        ASR     R0, R2, #2          ; R0 = ln(m) en Q3.12
        LD      R4, LOG_K
        MOVI    R1, #12
        ADD     R1, R4, R1          ; si k == -12 (x=1), satura debajo de -32768
        BRnp    LOG_ADD_K
        MOVI    R0, #0
        MOVH    R0, #x80
        BRnzp   LOG_END
LOG_ADD_K
        LD      R1, LOG_TWO_VALUE
        MUL     R1, R4, R1          ; k * ln(2) en Q3.12
        ADD     R0, R0, R1
LOG_END
        POPM    #xBE
        RET

LOG_K           .FILL #0
LOG_CNT         .FILL #0
LOG_TBL_PTR     .FILL #0
LOG_TWO_VALUE   .FILL #2840
CORDIC_IDX_TBL
        .FILL #1
        .FILL #2
        .FILL #3
        .FILL #4
        .FILL #4
        .FILL #5
        .FILL #6
        .FILL #7
        .FILL #8
        .FILL #9
        .FILL #10
        .FILL #11
        .FILL #12
CORDIC_ATANH_TBL
        .FILL #18000
        .FILL #8370
        .FILL #4118
        .FILL #2051
        .FILL #2051
        .FILL #1024
        .FILL #512
        .FILL #256
        .FILL #128
        .FILL #64
        .FILL #32
        .FILL #16
        .FILL #8
.END
