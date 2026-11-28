;=====================================================================
; SUBRUTINA: SQRT_NR_DQ16 (Raíz cuadrada Newton-Raphson en Q15.16)
;
;   Entradas:
;     R0 = parte entera (Q15.16, palabra alta)
;     R1 = parte fraccionaria (Q15.16, palabra baja)
;   Salida:
;     R0 = parte entera de sqrt(x) (Q15.16, palabra alta)
;     R1 = parte fraccionaria de sqrt(x) (Q15.16, palabra baja)
;   Rango: 0 <= x < 32768. Entradas negativas retornan 0:0.
;   Conserva: R2-R7, R6 (intacto).
;=====================================================================
SQRT_NR_DQ16:
        ST      R2, SQ_SAVE2
        ST      R3, SQ_SAVE3
        ST      R4, SQ_SAVE4
        ST      R5, SQ_SAVE5
        ST      R7, SQ_SAVE7

        ; 1. Validar signo y cero: si x <= 0 retornar 0:0
        ADD     R0, R0, #0
        BRn     SQ_ZERO
        BRp     SQ_PREPARE
        ADD     R1, R1, #0
        BRz     SQ_ZERO

SQ_PREPARE:
        AND     R4, R4, #0          ; R4 = k (contador de escala 4^k)

        ; 2. Normalizar x en R0:R1 al rango [4, 16) mediante multiplicación/división por 4
SQ_NORM:
        ; Si R0 > 16, o (R0 == 16 y R1 != 0) -> dividir por 4 (k++)
        LD      R2, SQ_NEG16
        ADD     R2, R0, R2
        BRp     SQ_DIV4
        BRn     SQ_CHECK_LOW
        ADD     R1, R1, #0
        BRnp    SQ_DIV4
        BR      SQ_NORMALIZED

SQ_CHECK_LOW:
        ; Si R0 < 4 -> multiplicar por 4 (k--)
        ADD     R2, R0, #-4
        BRn     SQ_MUL4
        BR      SQ_NORMALIZED

SQ_DIV4:
        ; (R0:R1) >>= 2 en 32 bits sin signo usando LSH y RSH
        AND     R2, R0, #3          ; Guardar los 2 bits bajos de R0
        LSH     R2, R2, #14         ; Colocarlos en bits [15:14] para R1
        RSH     R0, R0, #2          ; R0 >>= 2
        RSH     R1, R1, #2          ; R1 >>= 2
        OR      R1, R1, R2          ; R1 |= (R0_old[1:0] << 14)
        ADD     R4, R4, #1          ; k++
        BR      SQ_NORM

SQ_MUL4:
        ; (R0:R1) <<= 2 en 32 bits (seguro para x < 4)
        RSH     R2, R1, #14         ; Guardar los 2 bits altos de R1
        AND     R2, R2, #3
        LSH     R0, R0, #2          ; R0 <<= 2
        OR      R0, R0, R2          ; R0 |= (R1_old[15:14])
        LSH     R1, R1, #2          ; R1 <<= 2
        ADD     R4, R4, #-1         ; k--
        BR      SQ_NORM

SQ_NORMALIZED:
        ; Convertir t (normalizado en [4, 16), R0:R1 en Q15.16) a Q7.8 en R2:
        ; t_Q7_8 = ((R0 & x00FF) << 8) | (R1 >> 8)
        LD      R3, SQ_MASK_FF
        AND     R0, R0, R3
        LSH     R0, R0, #8
        RSH     R1, R1, #8
        OR      R2, R0, R1          ; R2 = t en Q7.8 (rango x0400..x0FFF)
        ST      R2, SQ_T_Q8

        ; 3. Newton-Raphson para raíz cuadrada inversa en Q7.8:
        ;    y_{n+1} = y_n * (3*256 - t * y_n^2) / (2 * 256)
        LD      R3, SQ_SEED_Q8      ; R3 = y (semilla inicial en Q7.8)
        AND     R5, R5, #0
        ADD     R5, R5, #6          ; Contador de 6 iteraciones

SQ_NR_LOOP:
        ; y2 = (y * y) >> 8 en Q7.8
        MUL     R0, R3, R3
        MULH    R1, R3, R3
        LSH     R1, R1, #8
        RSH     R0, R0, #8
        OR      R0, R1, R0          ; R0 = y^2 en Q7.8

        ; xy2 = (t * y2) >> 8 en Q7.8
        LD      R1, SQ_T_Q8
        MUL     R2, R0, R1
        MULH    R1, R0, R1
        LSH     R1, R1, #8
        RSH     R2, R2, #8
        OR      R1, R1, R2          ; R1 = t * y^2 en Q7.8

        ; factor = 768 (3.0 en Q7.8) - xy2
        LD      R0, SQ_THREE_Q8
        NOT     R1, R1
        ADD     R1, R1, #1
        ADD     R0, R0, R1          ; R0 = 3*256 - t*y^2

        ; prod = (factor * y) >> 8 en Q7.8
        MUL     R1, R0, R3
        MULH    R2, R0, R3
        LSH     R2, R2, #8
        RSH     R1, R1, #8
        OR      R1, R2, R1          ; R1 = factor * y en Q7.8

        ; y_next = R1 / 2 mediante RSH en 1 instrucción
        RSH     R3, R1, #1          ; R3 = y_next en Q7.8

        ADD     R5, R5, #-1
        BRp     SQ_NR_LOOP

        ; 4. Recuperar sqrt(t) = t * y en Q7.8:
        LD      R0, SQ_T_Q8
        MUL     R1, R0, R3
        MULH    R2, R0, R3
        LSH     R2, R2, #8
        RSH     R1, R1, #8
        OR      R1, R2, R1          ; R1 = sqrt(t) en Q7.8

        ; Expandir sqrt(t) de Q7.8 a Q15.16 (R0:R1):
        ; Parte entera (R0) = R1 >> 8, parte fraccionaria (R1) = (R1 & x00FF) << 8
        RSH     R0, R1, #8
        LD      R2, SQ_MASK_FF
        AND     R1, R1, R2
        LSH     R1, R1, #8

        ; 5. Reescalar por 2^k según el signo de R4 (k):
        ADD     R4, R4, #0
        BRz     SQ_DONE
        BRp     SQ_SCALE_UP

SQ_SCALE_DOWN:
        ; Dividir (R0:R1) entre 2 por cada unidad de (-k)
        AND     R2, R0, #1
        LSH     R2, R2, #15
        RSH     R0, R0, #1
        RSH     R1, R1, #1
        OR      R1, R1, R2
        ADD     R4, R4, #1
        BRn     SQ_SCALE_DOWN
        BR      SQ_DONE

SQ_SCALE_UP:
        ; Multiplicar (R0:R1) por 2 por cada unidad de k
        RSH     R2, R1, #15
        AND     R2, R2, #1
        LSH     R0, R0, #1
        OR      R0, R0, R2
        LSH     R1, R1, #1
        ADD     R4, R4, #-1
        BRp     SQ_SCALE_UP
        BR      SQ_DONE

SQ_ZERO:
        AND     R0, R0, #0
        AND     R1, R1, #0

SQ_DONE:
        LD      R2, SQ_SAVE2
        LD      R3, SQ_SAVE3
        LD      R4, SQ_SAVE4
        LD      R5, SQ_SAVE5
        LD      R7, SQ_SAVE7
        RET

;--- Constantes y respaldo de registros ---
SQ_NEG16:     .FILL #-16
SQ_MASK_FF:   .FILL x00FF
SQ_SEED_Q8:   .FILL #64           ; Semilla inicial y0 en Q7.8
SQ_THREE_Q8:  .FILL #768          ; 3.0 en Q7.8 (3 * 256)
SQ_T_Q8:      .FILL #0

SQ_SAVE2:     .FILL #0
SQ_SAVE3:     .FILL #0
SQ_SAVE4:     .FILL #0
SQ_SAVE5:     .FILL #0
SQ_SAVE7:     .FILL #0

.END