;=====================================================================
; SUBRUTINA: CORDIC_LOG_BASE (Logaritmo natural ln(m) en Q3.12)
;
;   Método: CORDIC hiperbólico, modo vectorial
;   Entrada:  R0 = m (Q3.12, 0 < m <= 7.9998 = x7FFF)
;   Salida:   R0 = ln(m) (Q3.12, rango representable -8.0 .. +7.9998)
;             m <= 0 o ln(m) < -8.0 -> R0 = x8000 (-8.0, saturado)
;   Conserva: R1-R7, R6 (intacto).
;=====================================================================
CORDIC_LOG_BASE:
        ST      R1, guardado_r1
        ST      R2, guardado_r2
        ST      R3, guardado_r3
        ST      R4, guardado_r4
        ST      R5, guardado_r5
        ST      R7, guardado_r7

        ; 1. Validar m <= 0 (logaritmo no definido)
        ADD     R0, R0, #0
        BRnz    LOG_MIN

        ; 2. Normalización: llevar m a >= 0.5 (x0800) contando desplazamientos k
        AND     R5, R5, #0          ; R5 = k = 0
        LD      R4, NEG_HALF        ; R4 = -0.5 (-x0800)
NORM:
        ADD     R1, R0, R4
        BRzp    NORM_OK
        ADD     R0, R0, R0          ; m <<= 1
        ADD     R5, R5, #1          ; k++
        BR      NORM
NORM_OK:
        ST      R5, var_k

        ; 3. Inicializar variables CORDIC hiperbólico:
        ;    x = (m >> 1) + 0.5
        ;    y = (m >> 1) - 0.5
        ;    z = 0
        RSH     R0, R0, #1          ; m es positivo, RSH con inmediato #1 -> m / 2
        LD      R4, HALF_Q12        ; 0.5 en Q3.12 (x0800)
        ADD     R1, R0, R4          ; R1 = x = m/2 + 0.5
        NOT     R4, R4
        ADD     R4, R4, #1          ; R4 = -0.5
        ADD     R2, R0, R4          ; R2 = y = m/2 - 0.5
        AND     R3, R3, #0          ; R3 = z = 0

        ; Cargar direcciones de tablas mediante punteros locales (PCoffset8 en palabras)
        LD      R4, ptr_seq_neg_i
        LD      R5, ptr_seq_width
        LD      R0, ptr_lut_atanh
        ST      R0, var_ptr_atanh
        BR      ITER

; --- Punteros locales y respaldos cercanos a la entrada ---
ptr_seq_neg_i:  .FILL SEQ_NEG_I
ptr_seq_width:  .FILL SEQ_WIDTH
ptr_lut_atanh:  .FILL LUT_ATANH
guardado_r1:    .FILL #0
guardado_r2:    .FILL #0
guardado_r3:    .FILL #0
guardado_r4:    .FILL #0
guardado_r5:    .FILL #0
guardado_r7:    .FILL #0
NEG_HALF:       .FILL xF800         ; -0.5 en Q3.12
HALF_Q12:       .FILL x0800         ; 0.5 en Q3.12
var_k:          .FILL #0

        ; 4. Lazo principal CORDIC (i = 1, 2, 3, 4, 4, 5 .. 12)
ITER:
        LDR     R7, R4, #0          ; R7 = -i (negativo = desplazar a la derecha)
        BRz     FIN

        ; Guardar ancho de bits (16 - i) para SEXT
        LDR     R0, R5, #0
        ST      R0, var_width

        ; y >> i aritmético: SHR con SR2 = -i, seguido de SEXT con SR2 = (16 - i)
        SHR     R0, R2, R7          ; Desplaza R2 a la derecha i bits (lógico)
        LD      R7, var_width
        SEXT    R0, R0, R7          ; Extiende el signo desde (16 - i) bits a 16 bits
        ST      R0, var_ys          ; Guardar (y >> i) con signo

        ; x >> i aritmético: SHR con SR2 = -i, seguido de SEXT con SR2 = (16 - i)
        LDR     R7, R4, #0          ; R7 = -i
        SHR     R0, R1, R7          ; Desplaza R1 a la derecha i bits (lógico)
        LD      R7, var_width
        SEXT    R0, R0, R7          ; R0 = (x >> i) con signo

        ; Cargar atanh(2^-i) desde LUT_ATANH
        LD      R7, var_ptr_atanh
        LDR     R7, R7, #0          ; R7 = atanh(2^-i)

        ADD     R2, R2, #0
        BRp     Y_POS

        ; Caso y <= 0: x += (y >> i), y += (x >> i), z -= atanh(2^-i)
        ADD     R2, R2, R0          ; y += (x >> i)
        LD      R0, var_ys
        ADD     R1, R1, R0          ; x += (y >> i)
        NOT     R7, R7
        ADD     R7, R7, #1
        ADD     R3, R3, R7          ; z -= atanh(2^-i)
        BR      NEXT

Y_POS:
        ; Caso y > 0: x -= (y >> i), y -= (x >> i), z += atanh(2^-i)
        NOT     R0, R0
        ADD     R0, R0, #1
        ADD     R2, R2, R0          ; y -= (x >> i)
        LD      R0, var_ys
        NOT     R0, R0
        ADD     R0, R0, #1
        ADD     R1, R1, R0          ; x -= (y >> i)
        ADD     R3, R3, R7          ; z += atanh(2^-i)

NEXT:
        LD      R7, var_ptr_atanh
        ADD     R7, R7, #2          ; Avanzar 1 palabra (2 bytes) en LUT_ATANH
        ST      R7, var_ptr_atanh
        ADD     R4, R4, #2          ; Avanzar 1 palabra (2 bytes) en SEQ_NEG_I
        ADD     R5, R5, #2          ; Avanzar 1 palabra (2 bytes) en SEQ_WIDTH
        BR      ITER

; --- Variables locales y constantes cercanas al lazo / salida ---
var_width:      .FILL #0
var_ys:         .FILL #0
var_ptr_atanh:  .FILL #0
LN2_Q12:        .FILL #2839         ; round(ln(2) * 4096)
MIN_Q12:        .FILL x8000         ; -8.0 en Q3.12

        ; 5. Resultado final: ln(m) = 2*z - k*ln(2)
FIN:
        ADD     R3, R3, R3          ; R3 = 2*z = ln(m * 2^k)
        LD      R5, var_k
        BRz     FIN_OK

        ; Si k >= 11, el resultado es menor que -8.0 -> saturar a x8000
        ADD     R1, R5, #-7
        ADD     R1, R1, #-4         ; R1 = k - 11
        BRzp    LOG_MIN

        ; Calcular k * ln(2) con MUL y restarlo de 2*z
        LD      R1, LN2_Q12
        MUL     R1, R5, R1          ; R1 = k * ln(2) en Q3.12
        NOT     R1, R1
        ADD     R1, R1, #1
        ADD     R3, R3, R1          ; R3 = 2*z - k*ln(2)

        ; Verificar desborde negativo (< -8.0)
        ADD     R3, R3, #0
        BRp     LOG_MIN

FIN_OK:
        ADD     R0, R3, #0
        BR      LOG_RET

LOG_MIN:
        LD      R0, MIN_Q12         ; R0 = x8000 (-8.0)

LOG_RET:
        LD      R1, guardado_r1
        LD      R2, guardado_r2
        LD      R3, guardado_r3
        LD      R4, guardado_r4
        LD      R5, guardado_r5
        LD      R7, guardado_r7
        RET

;=====================================================================
; ZONA DE DATOS Y TABLAS CORDIC
;=====================================================================
; Secuencia de desplazamientos negativos (-i) para SHR (negativo = derecha, 0 = fin)
SEQ_NEG_I:      .FILL #-1
                .FILL #-2
                .FILL #-3
                .FILL #-4
                .FILL #-4           ; Repetición obligatoria para convergencia
                .FILL #-5
                .FILL #-6
                .FILL #-7
                .FILL #-8
                .FILL #-9
                .FILL #-10
                .FILL #-11
                .FILL #-12
                .FILL #0

; Cantidad de bits válidos (16 - i) para extensión de signo con SEXT
SEQ_WIDTH:      .FILL #15
                .FILL #14
                .FILL #13
                .FILL #12
                .FILL #12
                .FILL #11
                .FILL #10
                .FILL #9
                .FILL #8
                .FILL #7
                .FILL #6
                .FILL #5
                .FILL #4

; Tabla atanh(2^-i) * 4096 en Q3.12
LUT_ATANH:      .FILL #2250
                .FILL #1046
                .FILL #515
                .FILL #256
                .FILL #256
                .FILL #128
                .FILL #64
                .FILL #32
                .FILL #16
                .FILL #8
                .FILL #4
                .FILL #2
                .FILL #1

.END