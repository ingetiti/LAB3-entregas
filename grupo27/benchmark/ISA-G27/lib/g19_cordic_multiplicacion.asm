;=====================================================================
; SUBRUTINA: CORDIC_MUL (Multiplicación CORDIC lineal en Q7.8)
;
;   Entradas:
;     R0 = a_q8 (primer factor en Q7.8 con signo)
;     R1 = b_q8 (segundo factor en Q7.8 con signo)
;   Salidas:
;     R0 = producto en Q7.8 con signo (0 si desborda)
;     R1 = estado:
;            0 = OK
;            1 = desbordamiento (|a * b| > 127.996)
;            2 = b_q8 inválido (-32768 = x8000)
;   Diagnóstico en memoria:
;     CM_Y_HI : CM_Y_LO = producto bruto de 32 bits (Q16)
;     CM_ITER           = cantidad de iteraciones realizadas
;   Conserva: R2-R5, R6 (intacto) y R7.
;=====================================================================
CORDIC_MUL:
        ST      R2, CM_SAVE_R2
        ST      R3, CM_SAVE_R3
        ST      R4, CM_SAVE_R4
        ST      R5, CM_SAVE_R5
        ST      R7, CM_SAVE_R7

        ; 1. Verificar b_q8 != -32768 (x8000)
        ADD     R2, R1, #0          ; R2 = z = b_q8
        LD      R3, CM_B_MIN        ; x8000
        ADD     R3, R3, R2          ; x8000 + x8000 == 0 solo si b_q8 == x8000
        BRz     CM_B_INVALIDO

        ; 2. Preparar current_x (32 bits) = a_q8 * 2^14:
        ;    x.hi = a_q8 >> 2 (aritmético)
        ;    x.lo = (a_q8 & 3) << 14
        RSH     R3, R0, #2
        SEXT    R3, R3, #14
        ST      R3, CM_X_HI

        AND     R3, R0, #3
        LSH     R3, R3, #14
        ST      R3, CM_X_LO

        ; 3. Inicializar acumulador y (32 bits) = 0, current_z = 2^14 (x4000), i = 0
        AND     R3, R3, #0
        ST      R3, CM_Y_HI
        ST      R3, CM_Y_LO

        LD      R4, CM_Z_INIT       ; R4 = current_z = x4000 (16384)
        AND     R5, R5, #0          ; R5 = i = 0

        ; 4. Lazo CORDIC lineal (hasta 15 iteraciones)
CM_LAZO:
        ADD     R2, R2, #0          ; if (z == 0) break
        BRz     CM_FIN_LAZO
        BRn     CM_Z_NEG

        ; --- Caso z > 0: z -= current_z ; y += current_x ---
        NOT     R3, R4
        ADD     R3, R3, #1
        ADD     R2, R2, R3          ; z -= current_z

        LD      R0, CM_Y_LO
        LD      R1, CM_X_LO
        ADD     R0, R0, R1          ; y.lo += x.lo (actualiza Carry)
        ST      R0, CM_Y_LO

        LD      R0, CM_Y_HI
        LD      R1, CM_X_HI
        ADC     R0, R0, R1          ; y.hi += x.hi + Carry
        ST      R0, CM_Y_HI
        BR      CM_SIGUE

        ; --- Caso z < 0: z += current_z ; y -= current_x ---
CM_Z_NEG:
        ADD     R2, R2, R4          ; z += current_z

        ; Restar 32 bits: y = y - x
        LD      R0, CM_Y_LO
        LD      R1, CM_X_LO
        BRz     CM_Z_NEG_LO_ZERO
        NOT     R1, R1
        ADD     R1, R1, #1
        ADD     R0, R0, R1          ; y.lo - x.lo (C=1 si no hubo borrow)
        ST      R0, CM_Y_LO

        LD      R0, CM_Y_HI
        LD      R1, CM_X_HI
        NOT     R1, R1              ; ~x.hi (sumar C equivale a ~x.hi + 1 - borrow)
        ADC     R0, R0, R1          ; y.hi = y.hi + ~x.hi + C
        ST      R0, CM_Y_HI
        BR      CM_SIGUE

CM_Z_NEG_LO_ZERO:
        ST      R0, CM_Y_LO
        LD      R0, CM_Y_HI
        LD      R1, CM_X_HI
        NOT     R1, R1
        ADD     R0, R0, R1
        ADD     R0, R0, #1          ; Con palabra baja cero, no hay préstamo
        ST      R0, CM_Y_HI

CM_SIGUE:
        ; Desplazar current_x (32 bits) 1 bit a la derecha con signo
        LD      R0, CM_X_HI
        LD      R1, CM_X_LO
        RSHO    R3, R0, #1          ; Bit 0 saliente de x.hi queda en bit 15 de R3
        RSH     R1, R1, #1          ; x.lo >>= 1 (lógico)
        OR      R1, R1, R3          ; Insertar bit saliente de x.hi en x.lo[15]
        ST      R1, CM_X_LO

        RSH     R0, R0, #1
        SEXT    R0, R0, #15         ; x.hi >>= 1 (aritmético)
        ST      R0, CM_X_HI

        ; Siguiente peso: current_z >>= 1 (sin signo)
        RSH     R4, R4, #1

        ADD     R5, R5, #1          ; i++
        ADD     R3, R5, #-8
        ADD     R3, R3, #-7         ; R3 = i - 15
        BRn     CM_LAZO

CM_FIN_LAZO:
        ST      R5, CM_ITER         ; Guardar cantidad de iteraciones realizadas

        ; 5. Reducir y (Q16) a Q7.8 con redondeo: (y + 128) >> 8
        LD      R2, CM_Y_LO
        LD      R3, CM_Y_HI
        LD      R4, CM_128          ; 128 (x0080)
        AND     R5, R5, #0          ; 0 para propagar carry

        ADD     R2, R2, R4          ; y.lo + 128
        ADC     R3, R3, R5          ; y.hi + Carry

        ; Comprobar desbordamiento en Q7.8: ((y.hi + 128) & xFF00) == 0
        ADD     R0, R3, R4          ; y.hi + 128
        LD      R1, CM_FF00
        AND     R0, R0, R1
        BRnp    CM_DESBORDA

        ; Extraer resultado de 16 bits: (y.hi << 8) | (y.lo >> 8)
        LSH     R3, R3, #8
        RSH     R2, R2, #8
        OR      R0, R3, R2          ; R0 = resultado en Q7.8
        AND     R1, R1, #0          ; R1 = estado = 0 (OK)
        BR      CM_FIN

CM_DESBORDA:
        AND     R0, R0, #0          ; R0 = 0
        AND     R1, R1, #0
        ADD     R1, R1, #1          ; R1 = estado = 1 (desbordamiento)
        BR      CM_FIN

CM_B_INVALIDO:
        AND     R0, R0, #0          ; R0 = 0
        ST      R0, CM_ITER         ; 0 iteraciones
        AND     R1, R1, #0
        ADD     R1, R1, #2          ; R1 = estado = 2 (b_q8 inválido)

CM_FIN:
        LD      R2, CM_SAVE_R2
        LD      R3, CM_SAVE_R3
        LD      R4, CM_SAVE_R4
        LD      R5, CM_SAVE_R5
        LD      R7, CM_SAVE_R7
        RET

;=====================================================================
; ZONA DE DATOS Y CONSTANTES
;=====================================================================
CM_B_MIN:       .FILL x8000
CM_Z_INIT:      .FILL x4000         ; 2^14 = 16384
CM_128:         .FILL #128          ; x0080
CM_FF00:        .FILL xFF00

CM_Y_HI:        .FILL #0
CM_Y_LO:        .FILL #0
CM_X_HI:        .FILL #0
CM_X_LO:        .FILL #0
CM_ITER:        .FILL #0

CM_SAVE_R2:     .FILL #0
CM_SAVE_R3:     .FILL #0
CM_SAVE_R4:     .FILL #0
CM_SAVE_R5:     .FILL #0
CM_SAVE_R7:     .FILL #0

.END