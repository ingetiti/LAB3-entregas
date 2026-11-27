; Seno por serie de Taylor: entrada R0 = angulo entero en decimas de grado,
; salida R0 = sin(angulo) en formato Q3.12.
CALCULAR_SENO
        PUSHM   #xBE
        AND     R5, R5, #0          ; R5 = bandera de signo (0=+, 1=-)
        ADD     R0, R0, #0
        BRzp    TAY_NONNEG
        NEG     R0, R0
        ADD     R5, R5, #1
TAY_NONNEG
        LD      R1, TAY_3600
        REM     R0, R0, R1          ; R0 in [0, 3599]
        LD      R1, TAY_1800
        SUB     R2, R0, R1
        BRn     TAY_LT1800
        ADD     R0, R2, #0          ; R0 -= 1800
        MOVI    R2, #1
        SUB     R5, R2, R5          ; invertir signo
TAY_LT1800
        LD      R2, TAY_900
        SUB     R3, R0, R2
        BRnz    TAY_QUAD1
        SUB     R0, R1, R0          ; R0 = 1800 - R0
TAY_QUAD1
        ; Convertir decimas de grado [0..900] a radianes x en Q1.14:
        ; x_q14 = MULQ14(R0 << 5, round((pi/1800)*16384/32 * 16384))
        SHL     R1, R0, #5
        LD      R2, TAY_DEG2RAD
        MULQ14  R1, R1, R2          ; R1 = x en Q1.14 (max 25736)

        ; x2_half = (x^2 / 2) en Q1.14 (max 20213 < 32768)
        ADD     R2, R1, #1
        SHR     R2, R2, #1          ; x / 2 redondeado
        MULQ14  R2, R1, R2          ; R2 = x^2 / 2 en Q1.14

        ; Serie de Taylor: t1 - t2 + t3 - t4 + t5 (en Q1.14)
        ; R3 = acumulador, R1 = termino actual
        ADD     R3, R1, #0          ; + t1 = x

        MULQ14  R1, R1, R2
        MOVI    R4, #3
        DIV     R1, R1, R4          ; t2 = x^3 / 6
        SUB     R3, R3, R1

        MULQ14  R1, R1, R2
        MOVI    R4, #10
        DIV     R1, R1, R4          ; t3 = x^5 / 120
        ADD     R3, R3, R1

        MULQ14  R1, R1, R2
        MOVI    R4, #21
        DIV     R1, R1, R4          ; t4 = x^7 / 5040
        SUB     R3, R3, R1

        MULQ14  R1, R1, R2
        MOVI    R4, #36
        DIV     R1, R1, R4          ; t5 = x^9 / 362880
        ADD     R3, R3, R1

        ; Convertir Q1.14 -> Q3.12 redondeado y aplicar signo
        ADD     R3, R3, #2
        ASR     R0, R3, #2
        ADD     R5, R5, #0
        BRz     TAY_DONE
        NEG     R0, R0
TAY_DONE
        POPM    #xBE
        RET

TAY_3600    .FILL #3600
TAY_1800    .FILL #1800
TAY_900     .FILL #900
TAY_DEG2RAD .FILL #14641
.END
