; Multiplicacion de dos operandos Q7.8 -> DQ15.16 por Shift-and-Add (OPTIMIZADA)
; Preserva exactamente el algoritmo original del Grupo 3 (incluyendo su deteccion de acarreo).

MULTIPLICARSHIFTANDADD
        PUSHM {R2, R3, R4, R5}

        XOR  R5, R0, R1         ; bit 15 = signo del producto
        ST   R5, Q8_SIGNO
        ABS  R3, R0             ; magnitud multiplicando
        ABS  R2, R1             ; magnitud multiplicador
        ST   R2, Q8_MULTIPLICADOR

        MOVI R0, #0             ; acc_lo
        MOVI R1, #0             ; acc_hi
        MOVI R4, #0             ; mcand_hi
        MOVI R5, #1             ; mascara bit
        MOVI R2, #16
        ST   R2, Q8_CANTIDAD_BITS

Q8_BUCLE
        LD   R2, Q8_MULTIPLICADOR
        AND  R2, R2, R5
        BRz  Q8_DESPLAZAR

        ADD  R2, R0, #0
        ADD  R0, R0, R3
        ADD  R1, R1, R4
        CMP  R2, #0
        BRn  Q8_ANTIGUO_BAJO_NEGATIVO

        CMP  R3, #0
        BRn  Q8_SUMANDO_BAJO_NEGATIVO
        CMP  R0, #0
        BRn  Q8_ACARREO
        BRnzp Q8_DESPLAZAR

Q8_SUMANDO_BAJO_NEGATIVO
        CMP  R0, #0
        BRzp Q8_ACARREO
        BRnzp Q8_DESPLAZAR

Q8_ANTIGUO_BAJO_NEGATIVO
        CMP  R3, #0
        BRn  Q8_ACARREO
        CMP  R0, #0
        BRzp Q8_ACARREO
        BRnzp Q8_DESPLAZAR

Q8_ACARREO
        ADD  R1, R1, #1

Q8_DESPLAZAR
        SHL  R4, R4, #1
        LSR  R2, R3, #15
        OR   R4, R4, R2
        SHL  R3, R3, #1
        SHL  R5, R5, #1
        LD   R2, Q8_CANTIDAD_BITS
        ADD  R2, R2, #-1
        ST   R2, Q8_CANTIDAD_BITS
        BRp  Q8_BUCLE

        ; Aplicar signo 32 bits
        LD   R2, Q8_SIGNO
        BRzp Q8_INTERCAMBIAR
        NOT  R0, R0
        NOT  R1, R1
        ADD  R0, R0, #1
        BRnp Q8_INTERCAMBIAR
        ADD  R1, R1, #1

Q8_INTERCAMBIAR
        ADD  R2, R0, #0
        ADD  R0, R1, #0
        ADD  R1, R2, #0

        POPM {R2, R3, R4, R5}
        RET

Q8_SIGNO           .FILL #0
Q8_MULTIPLICADOR   .FILL #0
Q8_CANTIDAD_BITS   .FILL #0

        .END
