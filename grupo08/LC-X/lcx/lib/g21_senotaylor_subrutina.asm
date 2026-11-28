;================================
; SUBRUTINA SENO TAYLOR (LC-X)
;================================
; CALCULAR_SENO
;   Entrada: R0 = angulo en decimas de grado, de 0 a 3600 (600 = 60.0)
;   Salida:  R0 = seno en Q3.12, o -1 si el angulo esta fuera de rango
;   Conserva R1-R7.
;
; Da los mismos bits que la version LC-3, que hacia cada producto y
; cada division con bucles de sumas y restas:
;   r   = angulo llevado al primer cuadrante (0 a 900), con su signo
;   x   = r * 12868 / 1800  = 7r + 67r / 450       (radianes, Q3.12)
;   x2  = x * x / 4096,  x3 = x2 * x / 4096,  x5 = x3 * x2 / 4096
;   T3  = x5 / 120,      T4 = (T3 * x2 / 4096) / 42
;   sen = x - x3 / 6 + T3 - T4
; Todas las divisiones truncan, como los bucles del original.
;================================

CALCULAR_SENO
        PUSH R1, R2, R3, R4
        LD    R1, C1800
        LSHF  R2, R1, #1        ; R2 = 3600
        CMP   R2, R0            ; sin acarreo si R0 > 3600 sin signo
        BRNC  ERROR             ; (tambien rechaza los negativos)

; ---- cuadrante: 1801-3600 se lleva a 1-1800 con signo negativo ----
        AND   R4, R4, #0        ; R4 = 0: el seno es positivo
        CMP   R1, R0
        BRC   MITAD             ; R0 <= 1800
        SUB   R0, R0, R1
        ADD   R4, R4, #1        ; R4 = 1: el seno es negativo
MITAD   RSHFL R2, R1, #1        ; R2 = 900
        CMP   R2, R0
        BRC   CUARTO            ; R0 <= 900
        SUB   R0, R1, R0        ; r = 1800 - angulo

; ---- x = 7r + 67r / 450 (r <= 900, asi que 67r cabe sin signo) ----
CUARTO  RSHFL R3, R1, #2        ; R3 = 450
        MUL   R1, R0, #7
        MOVI  R2, #67
        MUL   R2, R0, R2
        DIVM  R3, R2, R3        ; R2 = 67r / 450
        ADD   R0, R1, R2        ; R0 = x

; ---- serie: x - x3/6 + x5/120 - x7/5040 ----
        ADD   R1, R0, #0
        MULQU R1, R0, #12       ; R1 = x2
        ADD   R2, R1, #0
        MULQU R2, R0, #12       ; R2 = x3
        DIV   R3, R2, #6
        SUB   R0, R0, R3        ; x - x3/6
        MULQU R2, R1, #12       ; R2 = x5
        MOVI  R3, #120
        DIVM  R3, R2, R3        ; R2 = T3
        ADD   R0, R0, R2        ; + T3
        MULQU R2, R1, #12       ; R2 = T3 * x2 / 4096
        MOVI  R3, #42
        DIV   R2, R2, R3        ; R2 = T4
        SUB   R0, R0, R2        ; - T4

        ADD   R4, R4, #0
        BRz   FIN
        NEG   R0, R0
FIN     POP   R1, R2, R3, R4
        RET

ERROR   MOVI  R0, #-1
        POP   R1, R2, R3, R4
        RET

C1800   .FILL #1800

.END
