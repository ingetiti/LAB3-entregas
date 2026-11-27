; Modulo: cordic_division (Grupo 1, OPTIMIZADA)
; Division por CORDIC (modo lineal, vectoring) en punto fijo Q0.15
;   Entrada: R0 = y0, R1 = x0 (x0 > 0, |y0| < x0)
;   Salida : R0 = y0 / x0 en Q0.15

CORDIC_DIV
        PUSHM {R2, R4}

        ADD  R2, R0, #0         ; R2 = P = y0
        MOVI R0, #0             ; R0 = Z = 0

        ; Iteracion 0
        CMP  R2, #0
        BRp  INI_NEG
        ADD  R2, R2, R1         ; y <= 0: P += x, Z = -1
        MOVI R0, #-1
        BRnzp INI_LOOP
INI_NEG
        SUB  R2, R2, R1         ; y > 0: P -= x, Z = +1
        MOVI R0, #1

        ; Iteraciones 1 a 15
INI_LOOP
        MOVI R4, #15
LOOP
        CMP  R2, #0
        BRp  PPOS
        SHL  R2, R2, #1
        ADD  R2, R2, R1         ; P = 2P + x
        SHL  R0, R0, #1
        ADD  R0, R0, #-1        ; Z = 2Z - 1
        BRnzp GOON
PPOS
        SHL  R2, R2, #1
        SUB  R2, R2, R1         ; P = 2P - x
        SHL  R0, R0, #1
        ADD  R0, R0, #1         ; Z = 2Z + 1
GOON
        ADD  R4, R4, #-1
        BRp  LOOP

        POPM {R2, R4}
        RET

        .END
