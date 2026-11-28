; LAB 3 - GRUPO 9 - SQRT Newton-Raphson con normalizacion de rango (LC-X)
; Input:  R0=palabra entera, R1=palabra fraccionaria (Q15.16, signo 32 bits)
; Output: R0=palabra entera, R1=fraccionaria de sqrt(x), Q15.16
; Rango: 0 <= x < 32768 representable. Negativos retornan cero (validar en menu).
; R2-R7 preservados; R6 solo se usa como pila.
;
; El mismo metodo que el original, con los mismos bits:
;   x = 4^k * t, 4 <= t <= 16 (t truncado al dividir por 4)
;   q = t en Q7.8, redondeado
;   y = 0.25; 6 veces: y = y * (3 - q * y^2) / 2   (Newton, 1/sqrt(q))
;   s = q * y  (Q7.8, cada producto truncado como SQ9_MULQ)
;   sqrt(x) = s * 2^k, truncado
; k sale de CLZ en lugar del bucle de divisiones por 4. Con t = 16 el
; bucle se detiene antes que la cuenta de bits (k - 1 y t = 16 en vez de
; k y t = 4): ESPECIAL repite ese caso.

SQRT_NR_DQ16
        PUSH  R2, R3, R4, R5
        CLZ   R2, R0
        BRz   CERO              ; negativo
; ---- U = palabra alta de x * 4^h, con h = CLZ / 2 ----
        RSHFL R5, R2, #1        ; h (8 si el entero es 0)
        ADD   R2, R5, R5        ; 2h
        MOVI  R3, #1
        LSHF  R3, R3, R2        ; 4^h
        MULW  R4, R1, R3        ; R1 = palabra baja, R4 = bits que suben
        LSHF  R0, R0, R2
        OR    R0, R0, R4        ; U = t * 2^12
        LSHF  R3, R0, #2
        BRnp  SIGUE
        ADD   R0, R0, #0
        BRz   ENTERO0
; ---- ESPECIAL: t = 16 exacto con k >= 1 ----
        SUB   R3, R5, #6
        BRzp  SIGUE             ; k < 1
        RSHFL R3, R0, #15       ; 0 solo si U = x4000
        RSHFL R4, R1, #10
        OR    R3, R3, R4
        BRnp  SIGUE             ; t > 16 antes de dividir
        ADD   R5, R5, #1        ; k - 1
        MOVI  R0, #-1           ; redondea a q = 16
SIGUE   RSHFL R0, R0, #4
        ADC   R0, R0, #0        ; q = t en Q7.8 redondeado

; ---- Newton-Raphson reciproco, 6 iteraciones ----
        MOVI  R1, #64           ; y = 0.25
        MOVI  R2, #6
        LD    R3, TRES          ; 3 en Q7.8
ITER    ADD   R4, R1, #0
        MULQU R4, R1, #8        ; y2 = y * y
        MULQU R4, R0, #8        ; xy2 = q * y2
        SUB   R4, R3, R4        ; 3 - xy2
        MULQU R1, R4, #9        ; y = y * (3 - xy2) / 2
        LOOP  R2, ITER
        MULQU R1, R0, #8        ; s = q * y

; ---- R0:R1 = s * 2^(k+8) = s * (x4000 >> h) ----
        LD    R2, ESCALA
        RSHFL R2, R2, R5
        BRz   MINIMO            ; k = -9: s / 2
        MULW  R0, R1, R2
        POPR  R2, R3, R4, R5

; ---- entero 0: U sale de la fraccion ----
ENTERO0 CLZ   R2, R1
        RSHFL R3, R2, #1
        ADD   R5, R5, R3        ; h = 8 + CLZ / 2
        ADD   R2, R3, R3
        LSHF  R0, R1, R2
        BRnp  SIGUE             ; x = 0 sigue abajo: sqrt(0) = 0
CERO    AND   R1, R1, #0
MINIMO  RSHFL R1, R1, #1
        AND   R0, R0, #0
        POPR  R2, R3, R4, R5

TRES    .FILL #768
ESCALA  .FILL x4000
.END
