;=====================================================================
; SUBRUTINA: CALCULAR_SENO (Seno por serie de Taylor en Q3.12)
;
;   Entrada:  R0 = ángulo en deci-grados con signo (ej. 900 = 90.0°)
;   Salida:   R0 = sin(ángulo) en formato Q3.12 con signo (1.0 = x1000 = 4096)
;   Conserva: R1-R5, R6 (intacto) y R7.
;=====================================================================
CALCULAR_SENO:
        ST      R1, SEN_SAVE_R1
        ST      R2, SEN_SAVE_R2
        ST      R3, SEN_SAVE_R3
        ST      R4, SEN_SAVE_R4
        ST      R5, SEN_SAVE_R5
        ST      R7, SEN_SAVE_R7

        ; 1. Reducir el valor absoluto a [0, 3599] deci-grados.
        LD      R4, C_3600
        AND     R5, R5, #0
        ADD     R5, R5, #1          ; signo inicial = +1
        ADD     R0, R0, #0
        BRzp    SEN_ABS_READY
        NOT     R0, R0
        ADD     R0, R0, #1
        NOT     R5, R5
        ADD     R5, R5, #1          ; signo inicial = -1
SEN_ABS_READY:
        MOD     R0, R0, R4          ; R0 = angulo mod 3600

        ; 2. Reducción al primer cuadrante y ajuste del signo.

        LD      R1, NEG_1800
        ADD     R2, R0, R1          ; R2 = angulo - 1800
        BRn     SEN_HALF_LOW
        ; angulo >= 1800 -> angulo = angulo - 1800, signo = -1
        ADD     R0, R2, #0
        NOT     R5, R5
        ADD     R5, R5, #1          ; Cambiar signo

SEN_HALF_LOW:
        ; Ahora R0 está en [0, 1799]. Si R0 > 900, plegar respecto a 1800: angulo = 1800 - R0
        LD      R1, NEG_900
        ADD     R2, R0, R1          ; R2 = angulo - 900
        BRnz    SEN_TO_Q12
        LD      R1, C_1800
        NOT     R0, R0
        ADD     R0, R0, #1
        ADD     R0, R1, R0          ; R0 = 1800 - angulo (en [1, 899])

SEN_TO_Q12:
        ; 3. Convertir ángulo reducido en deci-grados (R0) a radianes en Q3.12:
        ;    x_q12 = (ang_decigrados * 12868) / 1800
        LD      R1, C_PI_Q12        ; 12868 = round(pi * 4096)
        MUL     R2, R0, R1          ; Bits bajos [15:0]
        MULH    R3, R0, R1          ; Bits altos [31:16]

        ; Como ang_decigrados <= 900 y 12868 < 16384, el producto cabe en 24 bits (R3 <= 176).
        ; Escalamos a 32 bits sin perder los bits bajos usando R3 como parte alta:
        ; Si R3 == 0, basta con DIV R2, R2, R4
        LD      R4, C_1800
        ADD     R3, R3, #0
        BRz     SEN_DIV_1800_LOW

        ; Combinar R3:R2 / 1800 restando múltiplos cuando haya parte alta
        AND     R1, R1, #0          ; Cociente acumulado en R1
SEN_LOOP_1800:
        ADD     R3, R3, #0
        BRz     SEN_ADD_REM_1800
        ; Restar 1800 de 32 bits (R3:R2) sumando cociente en R1
        NOT     R7, R4
        ADD     R7, R7, #1
        ADD     R2, R2, R7
        BRc     SEN_NO_BRW_1800
        ADD     R3, R3, #-1
SEN_NO_BRW_1800:
        ADD     R1, R1, #1
        BR      SEN_LOOP_1800

SEN_ADD_REM_1800:
        NOT     R7, R4
        ADD     R7, R7, #1          ; R7 = -1800
SEN_REM_LOOP:
        ADD     R2, R2, R7
        BRc     SEN_REM_SUBTRACTED
        ADD     R2, R2, R4          ; Restaurar si el resto era menor que 1800
        ADD     R2, R1, #0
        BR      SEN_X_READY
SEN_REM_SUBTRACTED:
        ADD     R1, R1, #1
        BR      SEN_REM_LOOP

SEN_DIV_1800_LOW:
        AND     R1, R1, #0
        BR      SEN_ADD_REM_1800

SEN_X_READY:
        ST      R2, SEN_X_Q12

        ; 4. Calcular x^2 en Q3.12: ((x * x) >> 12)
        MUL     R0, R2, R2
        MULH    R1, R2, R2
        LSH     R1, R1, #4
        RSH     R0, R0, #12
        OR      R3, R1, R0          ; R3 = x^2 en Q3.12
        ST      R3, SEN_X2_Q12

        BR      SEN_TAYLOR_START
SEN_SAVE_R1:    .FILL #0
SEN_SAVE_R2:    .FILL #0
SEN_SAVE_R3:    .FILL #0
SEN_SAVE_R4:    .FILL #0
SEN_SAVE_R5:    .FILL #0
SEN_SAVE_R7:    .FILL #0
SEN_TAYLOR_START:
        ; 5. Calcular T2 = -x^3/6 sin desbordar x^3 en Q3.12:
        ;    T2 = -((x^2 / 6) * x)
        LD      R1, C_6
        DIV     R4, R3, R1
        MUL     R0, R4, R2
        MULH    R1, R4, R2
        LSH     R1, R1, #4
        RSH     R0, R0, #12
        OR      R4, R1, R0          ; Magnitud de T2 en Q3.12
        ADD     R0, R4, #0
        NOT     R0, R0
        ADD     R0, R0, #1
        ST      R0, SEN_T2_Q12

        ; 6. T3 = -T2 * x^2 / 20
        LD      R2, SEN_X2_Q12
        LD      R4, SEN_T2_Q12
        NOT     R4, R4
        ADD     R4, R4, #1          ; Magnitud de T2
        MUL     R0, R4, R2
        MULH    R1, R4, R2
        LSH     R1, R1, #4
        RSH     R0, R0, #12
        OR      R4, R1, R0          ; |T2| * x^2 en Q3.12
        LD      R1, C_20
        DIV     R0, R4, R1
        ST      R0, SEN_T3_Q12

        ; 7. T4 = -T3 * x^2 / 42
        LD      R4, SEN_T3_Q12
        MUL     R0, R4, R2
        MULH    R1, R4, R2
        LSH     R1, R1, #4
        RSH     R0, R0, #12
        OR      R4, R1, R0          ; T3 * x^2 en Q3.12
        LD      R1, C_42
        DIV     R0, R4, R1
        NOT     R0, R0
        ADD     R0, R0, #1
        ST      R0, SEN_T4_Q12

        ; 8. Sumar serie: S = x + T2 + T3 + T4
        LD      R0, SEN_X_Q12
        LD      R1, SEN_T2_Q12
        ADD     R0, R0, R1
        LD      R1, SEN_T3_Q12
        ADD     R0, R0, R1
        LD      R1, SEN_T4_Q12
        ADD     R0, R0, R1

        ; Aplicar signo del cuadrante (R5)
        ADD     R5, R5, #0
        BRzp    SEN_FIN
        NOT     R0, R0
        ADD     R0, R0, #1

SEN_FIN:
        LD      R1, SEN_SAVE_R1
        LD      R2, SEN_SAVE_R2
        LD      R3, SEN_SAVE_R3
        LD      R4, SEN_SAVE_R4
        LD      R5, SEN_SAVE_R5
        LD      R7, SEN_SAVE_R7
        ADD     R0, R0, #0          ; Actualizar CC según resultado en R0
        RET

;=====================================================================
; ZONA DE DATOS Y CONSTANTES
;=====================================================================
C_3600:         .FILL #3600
C_1800:         .FILL #1800
NEG_1800:       .FILL #-1800
NEG_900:        .FILL #-900
C_PI_Q12:       .FILL #12868        ; round(pi * 4096)
C_6:            .FILL #6
C_20:           .FILL #20
C_42:           .FILL #42

SEN_X_Q12:      .FILL #0
SEN_X2_Q12:     .FILL #0
SEN_T2_Q12:     .FILL #0
SEN_T3_Q12:     .FILL #0
SEN_T4_Q12:     .FILL #0

.END