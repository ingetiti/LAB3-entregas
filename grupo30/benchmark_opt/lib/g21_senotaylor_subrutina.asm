; =====================================================================
; SUBRUTINA SENO TAYLOR (OPTIMIZADA PARA ISA 16-BIT)
; Entrada : R0 = angulo en decimas de grado [0..3600]
; Salida  : R0 = sin(angulo) en Q3.12 (o -1 si invalido)
; Preserva: R1..R5, R7
; Algoritmo: Reduccion al primer cuadrante + conversion a radianes Q3.12
;   + serie de Taylor S = X - X^3/6 + X^5/120 - X^7/5040
; =====================================================================

CALCULAR_SENO
    PUSHM {R1, R2, R3, R4, R5, R7}

    ; Validar angulo 0 <= R0 <= 3600
    CMP  R0, #0
    BRn  TAY_ERROR
    LD   R1, TAY_LIM360
    CMP  R0, R1
    BRp  TAY_ERROR

    ; Seleccion de cuadrante -> R0 = angulo reducido [0..900], R3 = signo (+1 / -1)
    LD   R1, TAY_LIM90
    CMP  R0, R1
    BRnz TAY_Q1
    LD   R1, TAY_LIM180
    CMP  R0, R1
    BRnz TAY_Q2
    LD   R1, TAY_LIM270
    CMP  R0, R1
    BRnz TAY_Q3

    ; Cuadrante 4: deg = 3600 - R0, sign = -1
    LD   R1, TAY_LIM360
    SUB  R0, R1, R0
    MOVI R3, #-1
    BRnzp TAY_CONV

TAY_Q1
    MOVI R3, #1
    BRnzp TAY_CONV

TAY_Q2
    LD   R1, TAY_LIM180
    SUB  R0, R1, R0
    MOVI R3, #1
    BRnzp TAY_CONV

TAY_Q3
    LD   R1, TAY_LIM180
    SUB  R0, R0, R1
    MOVI R3, #-1

TAY_CONV
    ; Conversion a radianes Q3.12: X = floor(deg * 12868 / 1800) = floor(deg * 3217 / 450)
    ; Descomposicion exacta: deg = 450*q + r -> X = 3217*q + 7*r + floor(67*r / 450)
    LD   R1, TAY_450
    DIV  R2, R0, R1             ; R2 = q (0..2)
    REM  R0, R0, R1             ; R0 = r (0..449)
    LD   R4, TAY_3217
    MULL R2, R2, R4             ; R2 = 3217 * q
    MOVI R4, #7
    MULL R4, R0, R4             ; R4 = 7 * r
    ADD  R2, R2, R4             ; R2 = 3217*q + 7*r
    LD   R4, TAY_67
    MULL R0, R0, R4             ; R0 = 67 * r (<= 30083)
    DIV  R0, R0, R1             ; R0 = floor(67 * r / 450)
    ADD  R0, R2, R0             ; R0 = X (Q3.12, 0..6434)

    ; X2 = floor(X * X / 4096)
    MULL R4, R0, R0
    MULH R5, R0, R0
    LSR  R4, R4, #12
    SHL  R5, R5, #4
    OR   R1, R4, R5             ; R1 = X2_Q12

    ; X3 = floor(X2 * X / 4096)
    MULL R4, R1, R0
    MULH R5, R1, R0
    LSR  R4, R4, #12
    SHL  R5, R5, #4
    OR   R2, R4, R5             ; R2 = X3_Q12

    ; T2 = -floor(X3 / 6) -> acumular S = X + T2 en R0
    MOVI R4, #6
    DIV  R4, R2, R4
    SUB  R0, R0, R4             ; R0 = X - X^3/6

    ; X5 = floor(X3 * X2 / 4096)
    MULL R4, R2, R1
    MULH R5, R2, R1
    LSR  R4, R4, #12
    SHL  R5, R5, #4
    OR   R2, R4, R5             ; R2 = X5_Q12 (unsigned, puede ser >= 32768)

    ; T3 = floor(X5 / 120)
    LD   R4, TAY_120
    ADD  R2, R2, #0
    BRn  TAY_X5_BIG
    DIV  R2, R2, R4             ; R2 = T3_Q12
    BRnzp TAY_T4

TAY_X5_BIG
    LD   R5, TAY_MASK15
    AND  R2, R2, R5             ; X5 - 32768
    ADDI R2, #8                 ; 32768 = 273*120 + 8
    DIV  R2, R2, R4
    LD   R5, TAY_273
    ADD  R2, R2, R5             ; R2 = T3_Q12

TAY_T4
    ; Acumular + T3
    ADD  R0, R0, R2             ; R0 = X - X^3/6 + X^5/120

    ; T4 = floor(floor(T3 * X2 / 4096) / 42)
    MULL R4, R2, R1
    MULH R5, R2, R1
    LSR  R4, R4, #12
    SHL  R5, R5, #4
    OR   R4, R4, R5
    MOVI R5, #42
    DIV  R4, R4, R5             ; R4 = T4_Q12

    ; Acumular - T4
    SUB  R0, R0, R4             ; R0 = S

    ; Aplicar signo del cuadrante
    CMP  R3, #0
    BRzp TAY_DONE
    NEG  R0, R0

TAY_DONE
    POPM {R1, R2, R3, R4, R5, R7}
    RET

TAY_ERROR
    MOVI R0, #-1
    POPM {R1, R2, R3, R4, R5, R7}
    RET

TAY_LIM90   .FILL #900
TAY_LIM180  .FILL #1800
TAY_LIM270  .FILL #2700
TAY_LIM360  .FILL #3600
TAY_450     .FILL #450
TAY_3217    .FILL #3217
TAY_67      .FILL #67
TAY_120     .FILL #120
TAY_273     .FILL #273
TAY_MASK15  .FILL x7FFF

.END
