;=====================================================================
; SUBRUTINA: EXP_Q3_12 (Exponencial e^A optimizada para ISA-G27)
;
;   Entrada:
;     R0 = A en Q3.12 con signo (rango [-8.0, +7.99975])
;   Salida:
;     R0 = e^A en Q7.8 con signo (saturado a x7FFF si e^A >= 128)
;     EST_EXP  = 0 (normal), 1 (saturado), 2 (redondeado a cero)
;     NUM_ITER = 6 (cálculo normal), 0 (saturación detectada al entrar)
;   Conserva: R1-R5 y R7; no utiliza R6.
;   CC refleja el valor de R0 al retornar.
;=====================================================================
EXP_Q3_12:
        ST      R1, G6_EXP_R1
        ST      R2, G6_EXP_R2
        ST      R3, G6_EXP_R3
        ST      R4, G6_EXP_R4
        ST      R5, G6_EXP_R5
        ST      R7, G6_EXP_R7

        ; 1. Comprobar saturación inmediata si A > ln(127.998) (~4.8520 -> x4DA1)
        ADD     R0, R0, #0
        BRn     EXP_NEG
        LD      R2, NEG_LIMITE      ; -19873 (-x4DA1)
        ADD     R2, R0, R2
        BRn     EXP_NORMAL          ; A < límite

        LD      R0, MAX_Q7_8
        AND     R1, R1, #0
        ADD     R1, R1, #1          ; EST_EXP = 1 (saturado)
        AND     R2, R2, #0          ; NUM_ITER = 0 (saturación al entrar)
        BR      EXP_EXIT

EXP_NORMAL:
        AND     R5, R5, #0          ; R5 = 0 (signo positivo)
        BR      EXP_REDUCE

EXP_NEG:
        AND     R5, R5, #0
        ADD     R5, R5, #1          ; R5 = 1 (signo negativo)
        NOT     R0, R0
        ADD     R0, R0, #1          ; R0 = |A| (magnitud sin signo, soporta x8000)

        ; ------------------------------------------------------------
        ; 2. Reducción de rango: |A| = k * ln(2) + r, con 0 <= r < ln(2)
        ;    Multiplicamos |A| (Q3.12) por 2^12 -> escala Q4.24:
        ;      Parte alta (R1) = |A| >> 4  (bits [15:4])
        ;      Parte baja (R2) = (|A| & x000F) << 12
        ; ------------------------------------------------------------
EXP_REDUCE:
        RSH     R1, R0, #4
        LD      R3, MASK_NIBBLE
        AND     R2, R0, R3
        LSH     R2, R2, #12

        ; ln(2) en Q4.24 = round(0.69314718 * 2^24) = 11629080 = x00B17218
        ; k = floor(|A|_Q24 / ln(2)_Q24), con k en [0, 11]
        LD      R3, LN2_HI          ; x00B1 (177)
        LD      R4, LN2_LO          ; x7218 (29208)
        AND     R0, R0, #0          ; R0 = k (cociente entero)

EXP_RED_LOOP:
        ; Comparar R1:R2 con LN2_HI:LN2_LO
        NOT     R7, R3
        ADD     R7, R7, #1
        ADD     R7, R1, R7          ; R1 - LN2_HI
        BRn     EXP_RED_DONE        ; Si R1 < LN2_HI, terminamos
        BRp     EXP_RED_SUB         ; Si R1 > LN2_HI, restar
        ; Si R1 == LN2_HI, comparar palabra baja R2 con LN2_LO (sin signo)
        NOT     R7, R4
        ADD     R7, R7, #1
        ADD     R7, R2, R7          ; R2 - LN2_LO (si R2 >= LN2_LO hay carry)
        BRc     EXP_RED_SUB
        BR      EXP_RED_DONE

EXP_RED_SUB:
        ; Restar LN2_HI:LN2_LO de R1:R2 (en 32 bits)
        NOT     R7, R4
        ADD     R7, R7, #1
        ADD     R2, R2, R7          ; R2 = R2 - LN2_LO (carry=1 si no hubo préstamo)
        BRc     EXP_NO_BORROW
        ADD     R1, R1, #-1
EXP_NO_BORROW:
        NOT     R7, R3
        ADD     R7, R7, #1
        ADD     R1, R1, R7          ; R1 = R1 - LN2_HI
        ADD     R0, R0, #1          ; k++
        BR      EXP_RED_LOOP

EXP_RED_DONE:
        ; Convertir resto r (Q4.24) a Q1.15 en R2:
        ; r_Q15 = (R1 << 7) | (R2 >> 9)
        LSH     R1, R1, #7
        RSH     R2, R2, #9
        OR      R2, R1, R2          ; R2 = r en Q1.15 (0 <= r < 22713)
        BR      EXP_REMAINDER_SIGN

NEG_LIMITE:   .FILL #-19873         ; -x4DA1 (límite de saturación en Q3.12)
MAX_Q7_8:     .FILL x7FFF           ; Valor máximo positivo en Q7.8
MASK_NIBBLE:  .FILL x000F           ; Máscara de 4 bits bajos
LN2_HI:       .FILL x00B1           ; Parte alta de ln(2) * 2^24
LN2_LO:       .FILL x7218           ; Parte baja de ln(2) * 2^24
LN2_Q15:      .FILL #22713          ; round(ln(2) * 32768)
ONE_Q15:      .FILL x8000           ; 1.0 en Q1.15 sin signo
MASK_BYTE:    .FILL x00FF

TEMP_K:       .FILL #0
EST_EXP:      .FILL #0
NUM_ITER:     .FILL #0
TEMP_R:       .FILL #0
TEMP_J:       .FILL #0

EXP_EXIT:
        ST      R1, EST_EXP
        ST      R2, NUM_ITER
        LD      R1, G6_EXP_R1
        LD      R2, G6_EXP_R2
        LD      R3, G6_EXP_R3
        LD      R4, G6_EXP_R4
        LD      R5, G6_EXP_R5
        LD      R7, G6_EXP_R7
        ADD     R0, R0, #0          ; Actualizar CC con el resultado en R0
        RET

G6_EXP_R1:    .FILL #0
G6_EXP_R2:    .FILL #0
G6_EXP_R3:    .FILL #0
G6_EXP_R4:    .FILL #0
G6_EXP_R5:    .FILL #0
G6_EXP_R7:    .FILL #0

EXP_REMAINDER_SIGN:
        ; Si A era negativo (R5 == 1):
        ;   Si r == 0 -> k = -k, r = 0
        ;   Si r > 0  -> k = -k - 1, r = ln(2)_Q15 - r
        ADD     R5, R5, #0
        BRz     EXP_TAYLOR
        NOT     R0, R0              ; R0 = -k - 1
        ADD     R2, R2, #0
        BRnp    EXP_COMP_R
        ADD     R0, R0, #1          ; Si r == 0, k = -k
        BR      EXP_TAYLOR
EXP_COMP_R:
        LD      R1, LN2_Q15         ; 22713 (round(ln(2) * 32768))
        NOT     R2, R2
        ADD     R2, R2, #1
        ADD     R2, R1, R2          ; R2 = ln(2)_Q15 - r

        ; ------------------------------------------------------------
        ; 3. Evaluar e^r para r en [0, ln(2)) con esquema de Horner (6 términos)
        ;    e^r ≈ 1 + r*(1 + r/2*(1 + r/3*(1 + r/4*(1 + r/5*(1 + r/6)))))
        ;    R0 = k, R2 = r en Q1.15
        ; ------------------------------------------------------------
EXP_TAYLOR:
        ST      R0, TEMP_K          ; Guardar k en memoria temporal
        ST      R2, TEMP_R          ; El resto no debe alterarse durante el esquema de Horner
        LD      R3, ONE_Q15         ; Acumulador E = 1.0 (x8000 en Q1.15)
        AND     R4, R4, #0
        ADD     R4, R4, #6          ; j = 6 iteraciones (6, 5, 4, 3, 2, 1)

EXP_HORNER_LOOP:
        ; Paso 1: dividir E entre j como entero sin signo.
        ; E puede tener el bit alto activo, así que se dividen sus bytes por separado.
        ST      R4, TEMP_J
        RSH     R0, R3, #8          ; byte alto de E
        LD      R1, MASK_BYTE
        AND     R1, R3, R1          ; byte bajo de E
        DIV     R2, R0, R4          ; byte alto del cociente
        MOD     R0, R0, R4          ; resto del byte alto
        LSH     R0, R0, #8
        OR      R0, R0, R1          ; resto * 256 + byte bajo
        DIV     R0, R0, R4
        LSH     R2, R2, #8
        OR      R3, R2, R0          ; E / j, sin signo

        ; Paso 2: (E * r) >> 15, con E y r tratados como Q1.15 sin signo.
        ; Si E/j tiene bit alto activo, compensar el producto firmado de MULH.
        ADD     R0, R3, #0
        BRn     EXP_MUL_Q_NEG
        AND     R4, R4, #0
        BR      EXP_MUL_Q_READY
EXP_MUL_Q_NEG:
        AND     R4, R4, #0
        ADD     R4, R4, #1
EXP_MUL_Q_READY:
        LD      R1, TEMP_R
        MUL     R2, R0, R1          ; palabra baja del producto firmado
        MULH    R3, R0, R1          ; palabra alta del producto firmado
        ADD     R4, R4, #0
        BRz     EXP_MUL_Q_CORRECT
        ADD     R3, R3, R1          ; sumar r * 2^16 para recuperar E sin signo
EXP_MUL_Q_CORRECT:
        LSH     R3, R3, #1
        RSH     R2, R2, #15
        OR      R3, R3, R2          ; R3 = (E / j) * r en Q1.15
        ; Paso 3: E = 1.0 + R3
        LD      R0, ONE_Q15
        ADD     R3, R3, R0          ; E en Q1.15 [x8000 .. xFFFE]
        LD      R4, TEMP_J
        ADD     R4, R4, #-1
        BRp     EXP_HORNER_LOOP

        ; ------------------------------------------------------------
        ; 4. Escalar por 2^k y convertir de Q1.15 a Q7.8 con redondeo:
        ;    Resultado = round(E_Q15 * 2^(k - 7))
        ;    Si k >= 7: desplazar a la izquierda (k - 7) bits
        ;    Si k <  7: desplazar a la derecha (7 - k) bits con redondeo
        ; ------------------------------------------------------------
        LD      R1, TEMP_K          ; R1 = k
        ADD     R1, R1, #-7         ; R1 = desplazamiento neto (k - 7)
        BRn     EXP_SHIFT_RIGHT

        ; k >= 7: si k == 7 no desplaza; si k > 7 satura
        BRz     EXP_CHECK_OVERFLOW
        BR      EXP_SAT_NORM

EXP_CHECK_OVERFLOW:
        ; Con k = 7, R3 (sin signo en Q1.15) pasa directo a Q7.8.
        ; Si bit 15 de R3 está en 1 (R3 >= x8000), no cabe en Q7.8 con signo -> saturar
        ADD     R0, R3, #0
        BRn     EXP_SAT_NORM
        AND     R1, R1, #0          ; EST_EXP = 0 (normal)
        BR      EXP_DONE_6

EXP_SHIFT_RIGHT:
        ; Aquí R1 = k - 7 está en [-19, -1].
        ; Sea n = -(k - 7) = 7 - k (en [1, 19]).
        ; Si R1 < -16 (es decir, n > 16), el resultado redondeado es 0.
        ADD     R2, R1, #7
        ADD     R2, R2, #7
        ADD     R2, R2, #2          ; R2 = (k - 7) + 16 = 16 - n
        BRn     EXP_UNDERFLOW       ; Si n > 16 -> underflow a 0

        ; Extraer bit de redondeo (bit n - 1 de R3) usando SHR con desplazamiento -(n - 1) = R1 + 1:
        ADD     R2, R1, #1          ; R2 = -(n - 1) (en [-15, 0], negativo = derecha)
        SHR     R0, R3, R2          ; Bit (n - 1) queda en bit 0 de R0
        AND     R0, R0, #1          ; R0 = bit de redondeo (0 o 1)

        ; Desplazar R3 a la derecha n bits usando SHR con desplazamiento -n = R1 (en [-16, -1]):
        SHR     R3, R3, R1          ; R3 = E_Q15 >> n (lógico)
        ADD     R0, R3, R0          ; R0 = resultado Q7.8 redondeado
        BRz     EXP_UNDERFLOW       ; Si redondeó a 0 -> EST_EXP = 2
        AND     R1, R1, #0          ; EST_EXP = 0 (normal)
        BR      EXP_DONE_6

EXP_UNDERFLOW:
        AND     R0, R0, #0          ; R0 = 0
        AND     R1, R1, #0
        ADD     R1, R1, #2          ; EST_EXP = 2 (redondeado a cero)
        BR      EXP_DONE_6

EXP_SAT_NORM:
        LD      R0, MAX_Q7_8        ; R0 = x7FFF
        AND     R1, R1, #0
        ADD     R1, R1, #1          ; EST_EXP = 1 (saturado)

EXP_DONE_6:
        AND     R2, R2, #0
        ADD     R2, R2, #6          ; NUM_ITER = 6
        BR      EXP_EXIT

.END