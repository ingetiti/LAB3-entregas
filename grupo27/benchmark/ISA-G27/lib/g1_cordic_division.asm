;=====================================================================
; División por CORDIC (modo lineal, vectoring) en punto fijo Q0.15
;
; CORDIC_DIV_Q15
;   ENTRADAS (Q0.15, entero con signo en complemento a 2):
;     R0 = y0  (dividendo en Q0.15)
;     R1 = x0  (divisor en Q0.15)  con x0 > 0 y |y0| < x0
;   SALIDA:
;     R0 = y0 / x0 en Q0.15, rango [-1, 1) (valor real = R0 / 32768)
;          Ejemplo: 0.5 = x4000, -0.5 = xC000 (error típico: 1 LSB)
;   Conserva R1-R5 y R7 (respalda R2-R4 en memoria local).
;=====================================================================
CORDIC_DIV_Q15
        ST  R2, g_r2_q15
        ST  R3, g_r3_q15
        ST  R4, g_r4_q15

        ADD R2, R0, #0      ; R2 = P = y0 (residuo inicial)[cite: 4]
        AND R0, R0, #0      ; R0 = Z = 0 (acumulador del cociente)[cite: 4]

        ; R3 = -x0 (complemento a 2 de R1)[cite: 4]
        NOT R3, R1
        ADD R3, R3, #1

        ; --- Iteración 0 ---
        ADD R2, R2, #0      ; Actualiza flags según P[cite: 4]
        BRp Q15_INI_NEG
        ADD R2, R2, R1      ; P <= 0 -> d = +1 : P = P + x0[cite: 4]
        ADD R0, R0, #-1     ; Z = -d = -1[cite: 4]
        BR  Q15_INI_LOOP

Q15_INI_NEG
        ADD R2, R2, R3      ; P > 0  -> d = -1 : P = P - x0[cite: 4]
        ADD R0, R0, #1      ; Z = -d = +1[cite: 4]

        ; --- Iteraciones 1 a 15 (15 desplazamientos para escala Q0.15) ---
Q15_INI_LOOP
        AND R4, R4, #0
        ADD R4, R4, #7      ; Contador = 15 (imm4 máximo es 7, se carga en 3 pasos)[cite: 5]
        ADD R4, R4, #7
        ADD R4, R4, #1      ; R4 = 15[cite: 4]

Q15_LOOP
        ADD R2, R2, #0      ; Evalúa el signo actual del residuo P[cite: 4]
        BRp Q15_PPOS

        ; P <= 0 -> d = +1 : P' = 2P + x0, Z' = 2Z - 1[cite: 4]
        ADD R2, R2, R2
        ADD R2, R2, R1
        ADD R0, R0, R0
        ADD R0, R0, #-1
        BR  Q15_NEXT

Q15_PPOS
        ; P > 0  -> d = -1 : P' = 2P - x0, Z' = 2Z + 1[cite: 4]
        ADD R2, R2, R2
        ADD R2, R2, R3
        ADD R0, R0, R0
        ADD R0, R0, #1

Q15_NEXT
        ADD R4, R4, #-1
        BRp Q15_LOOP

        LD  R2, g_r2_q15
        LD  R3, g_r3_q15
        LD  R4, g_r4_q15
        RET

;--- Zona de datos para respaldo de registros ---
g_r2_q15    .FILL #0
g_r3_q15    .FILL #0
g_r4_q15    .FILL #0

.END