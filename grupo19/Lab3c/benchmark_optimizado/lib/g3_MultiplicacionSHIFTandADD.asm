; Multiplicacion de dos operandos Q8.8 (Shift-and-Add).
; Entrada:
;   R0 = primer operando Q8.8 (con signo)
;   R1 = segundo operando Q8.8 (con signo)
; Salida:
;   R0:R1 = producto Q16.16
;       R0 = parte entera (palabra alta)
;       R1 = parte fraccionaria (palabra baja)
;
; Conserva R2-R5, R6 y R7 mediante pila hardware (SP).
; Optimizaciones nueva ISA:
;   - PUSHM/POPR en lugar de guardado en memoria estatica (reentrante).
;   - NEG y XOR para signos y magnitudes sin complementos manuales.
;   - ADD + ADC para suma de 32 bits sin deteccion manual de acarreo.
;   - SHL + RLC para desplazamiento de 32 bits y LSR para el multiplicador
;     (permite salida temprana cuando el multiplicador llega a 0).

MULTIPLICARSHIFTANDADD:
        PUSHM   {R2, R3, R4, R5, R7}

        ; Bit 15 de R5 = 1 si los operandos tienen distinto signo.
        XOR     R5, R0, R1

        ; R3 = |op1|
        MOV     R3, R0
        BRzp    Q8_PRIMER_POSITIVO
        NEG     R3, R3
Q8_PRIMER_POSITIVO:

        ; R4 = |op2|
        MOV     R4, R1
        BRzp    Q8_SEGUNDO_POSITIVO
        NEG     R4, R4
Q8_SEGUNDO_POSITIVO:

        ; Acumulador de 32 bits en R0:R1 (alta:baja) = 0:0.
        ; Multiplicando de 32 bits en R2:R3 (alta:baja) = 0:|op1|.
        CLR     R0
        CLR     R1
        CLR     R2

Q8_BUCLE:
        ; Extraer bit 0 del multiplicador en C; si es 1, sumar R2:R3 a R0:R1.
        LSR     R4, R4, #1
        BRnc    Q8_DESPLAZAR
        ADD     R1, R1, R3
        ADC     R0, R0, R2

Q8_DESPLAZAR:
        ; Salir apenas no queden bits en 1 en el multiplicador.
        ADDI    R4, R4, #0
        BRz     Q8_FIN_BUCLE

        ; Desplazar a la izquierda el multiplicando de 32 bits R2:R3.
        SHL     R3, R3, #1
        RLC     R2, R2
        BR      Q8_BUCLE

Q8_FIN_BUCLE:
        ; Aplicar el signo al resultado de 32 bits R0:R1 si bit 15 de R5 = 1.
        ADDI    R5, R5, #0
        BRzp    Q8_RESTAURAR
        NOT     R1, R1
        NOT     R0, R0
        ADDI    R1, R1, #1
        BRnp    Q8_RESTAURAR
        INC     R0

Q8_RESTAURAR:
        POPR    {R2, R3, R4, R5, R7}

        .END
