; ============================================================================
; Modulo: senotaylor_subrutina  (archivo g21_senotaylor_subrutina.asm)   Grupo 21
; Seno por serie de Taylor de 4 terminos, en LC10 (MUL/MULHU/DIVU).
;
; CALCULAR_SENO
; Entrada:  R0 = angulo en decimas de grado, entero sin signo (0..3600)
; Salida:   R0 = seno en Q3.12 (resultado exacto del modulo original)
;           R0 = xFFFF (-1) si el angulo esta fuera de [0, 3600]
; Preserva: R1 a R4 (los guarda en la pila, que es la de R6). R5, R6 y R7 no se
;           tocan. Es reentrante: no usa palabras fijas de memoria.
;
; Las cuentas son las del modulo LC-3 original, con el mismo orden de productos
; y los mismos truncados:
;   x  = floor(r * 12868 / 1800)             (r = angulo reducido a 0..900)
;   x2 = floor(x * x / 4096)
;   x3 = floor(x2 * x / 4096)
;   x5 = floor(x3 * x2 / 4096)
;   t3 = floor(x5 / 120)
;   t4 = floor(floor(t3 * x2 / 4096) / 42)
;   seno = x - floor(x3 / 6) + t3 - t4        (con signo - en el 3.er y 4.o cuadrante)
; Solo hay enteros: no hay punto flotante. Dos identidades evitan productos de
; 32 bits sin perder exactitud:
;   * floor(a * b / 4096) = parte alta (MULHU) de (4a) * (4b), porque 16ab / 65536 = ab / 4096
;     y 4a y 4b caben en 16 bits (a, b <= 15876 en este modulo).
;   * floor(r * 12868 / 1800) = 7r + floor(67 r / 450), y 67 r <= 60300 cabe en 16 bits.
;
; Registros internos:
; R0 = r, luego 4x y los divisores      R1 = x y despues el resultado parcial
; R2 = 1800 / 67 r / 4*x2               R3 = 450 / x3 / x5 / t3 / t4
; R4 = mascara de signo (0 o xFFFF)
; ============================================================================

CALCULAR_SENO
                        ADD   R6, R6, #-8
                        STW   R1, R6, #0
                        STW   R2, R6, #2
                        STW   R3, R6, #4
                        STW   R4, R6, #6

; Reduccion al primer cuadrante (r en 0..900) y signo. Con a' = a - 1800 si a >= 1800
; (seno negativo), r = min(a', 1800 - a'). Si a' > 1800 el angulo no es valido.
                        LD    R1, K1800
                        MOVI  R4, #0
                        CMP   R0, R1
                        BRNC  seno_cuadrantes_12
                        SUB   R0, R0, R1
                        MOVI  R4, #-1
seno_cuadrantes_12
                        SUB   R2, R1, R0                ; 1800 - a'  (C = 0 si a' > 1800)
                        BRNC  seno_fuera_de_rango
                        CMP   R2, R0
                        BRC   seno_reducido             ; a' <= 900
                        MOV   R0, R2
seno_reducido

; x = 7 r + floor(67 r / 450)   (radianes en Q3.12)
                        MOVI  R2, #67
                        MUL   R2, R0, R2
                        SHR   R3, R1, #2                ; 450
                        DIVU  R2, R2, R3
                        SHL   R1, R0, #3
                        SUB   R1, R1, R0
                        ADD   R1, R1, R2                ; R1 = x

; x2 y x3 (R0 = 4x, R2 = 4*x2, R3 = x3)
                        SHL   R0, R1, #2
                        MULHU R2, R0, R0
                        SHL   R2, R2, #2
                        MULHU R3, R2, R0

; x - floor(x3 / 6)
                        MOVI  R0, #6
                        DIVU  R0, R3, R0
                        SUB   R1, R1, R0

; x5 y t3 = floor(x5 / 120)   (x5 puede pasar de 32767: es sin signo)
                        SHL   R3, R3, #2
                        MULHU R3, R3, R2
                        MOVI  R0, #120
                        DIVU  R3, R3, R0
                        ADD   R1, R1, R3

; t4 = floor(floor(t3 * x2 / 4096) / 42)
                        SHL   R3, R3, #2
                        MULHU R3, R3, R2
                        MOVI  R0, #42
                        DIVU  R3, R3, R0
                        SUB   R1, R1, R3

; Signo: R0 = (R1 XOR mascara) - mascara
                        XOR   R0, R1, R4
                        SUB   R0, R0, R4

seno_salida
                        LDW   R1, R6, #0
                        LDW   R2, R6, #2
                        LDW   R3, R6, #4
                        LDW   R4, R6, #6
                        SUB   R6, R6, #-8               ; (+8 no cabe en imm4)
                        RET

seno_fuera_de_rango
                        MOVI  R0, #-1
                        BR    seno_salida

K1800                   .FILL #1800

.END
