; Multiplicacion de dos operandos Q8.8.
; Entrada:
;   R0 = primer operando Q8.8
;   R1 = segundo operando Q8.8
; Salida:
;   R0:R1 = producto Q16.16
;       R0 = parte entera (palabra alta)
;       R1 = parte fraccionaria (palabra baja)
;
; R2-R5 se conservan. R6 y R7 no se utilizan.

MULTIPLICARSHIFTANDADD:
        ST      R2, Q8_GUARDAR_R2
        ST      R3, Q8_GUARDAR_R3
        ST      R4, Q8_GUARDAR_R4
        ST      R5, Q8_GUARDAR_R5

        ; Obtener la magnitud del primer operando y contar su signo.
        AND     R5, R5, #0
        ADD     R0, R0, #0
        BRzp    Q8_PRIMER_POSITIVO
        NOT     R0, R0
        ADD     R0, R0, #1
        ADD     R5, R5, #1
Q8_PRIMER_POSITIVO:
        ADD     R3, R0, #0

        ; Obtener la magnitud del segundo operando y contar su signo.
        ADD     R1, R1, #0
        BRzp    Q8_SEGUNDO_POSITIVO
        NOT     R1, R1
        ADD     R1, R1, #1
        ADD     R5, R5, #1
Q8_SEGUNDO_POSITIVO:
        ADD     R2, R1, #0

        ; El signo final es negativo si exactamente un operando era negativo.
        AND     R5, R5, #1
        ST      R5, Q8_SIGNO
        ST      R2, Q8_MULTIPLICADOR

        ; Acumulador de 32 bits (interno): R1:R0 = alta:baja.
        AND     R0, R0, #0
        AND     R1, R1, #0

        ; Multiplicando de 32 bits: R4:R3.
        AND     R4, R4, #0
        AND     R5, R5, #0
        ADD     R5, R5, #1
        AND     R2, R2, #0
        ADD     R2, R2, #15
        ADD     R2, R2, #1
        ST      R2, Q8_CANTIDAD_BITS

Q8_BUCLE:
        ; Probar el bit seleccionado del multiplicador.
        LD      R2, Q8_MULTIPLICADOR
        AND     R2, R2, R5
        BRz     Q8_DESPLAZAR

        ; Sumar el multiplicando al acumulador y detectar acarreo.
        ADD     R2, R0, #0
        ADD     R0, R0, R3
        ADD     R1, R1, R4
        ADD     R2, R2, #0
        BRn     Q8_ANTIGUO_BAJO_NEGATIVO

        ADD     R3, R3, #0
        BRn     Q8_SUMANDO_BAJO_NEGATIVO
        ADD     R0, R0, #0
        BRn     Q8_ACARREO
        BR      Q8_DESPLAZAR

Q8_SUMANDO_BAJO_NEGATIVO:
        ADD     R0, R0, #0
        BRzp    Q8_ACARREO
        BR      Q8_DESPLAZAR

Q8_ANTIGUO_BAJO_NEGATIVO:
        ADD     R3, R3, #0
        BRn     Q8_ACARREO
        ADD     R0, R0, #0
        BRzp    Q8_ACARREO
        BR      Q8_DESPLAZAR

Q8_ACARREO:
        ADD     R1, R1, #1

Q8_DESPLAZAR:
        ; Desplazar a la izquierda el multiplicando R4:R3.
        ADD     R2, R3, #0
        ADD     R3, R3, R3
        ADD     R4, R4, R4
        ADD     R2, R2, #0
        BRzp    Q8_SIN_ACARREO
        ADD     R4, R4, #1
Q8_SIN_ACARREO:
        ADD     R5, R5, R5
        LD      R2, Q8_CANTIDAD_BITS
        ADD     R2, R2, #-1
        ST      R2, Q8_CANTIDAD_BITS
        BRp     Q8_BUCLE

        ; Aplicar el signo al resultado de 32 bits.
        LD      R2, Q8_SIGNO
        BRz     Q8_INTERCAMBIAR
        NOT     R0, R0
        NOT     R1, R1
        ADD     R0, R0, #1
        BRnp    Q8_INTERCAMBIAR
        ADD     R1, R1, #1

Q8_INTERCAMBIAR:
        ; Intercambiar R0 y R1 para entregar R0 = entera, R1 = fraccionaria.
        ADD     R2, R0, #0          ; R2 = palabra baja (fraccion)
        ADD     R0, R1, #0          ; R0 = palabra alta (entera)
        ADD     R1, R2, #0          ; R1 = palabra baja (fraccion)

Q8_RESTAURAR:
        LD      R2, Q8_GUARDAR_R2
        LD      R3, Q8_GUARDAR_R3
        LD      R4, Q8_GUARDAR_R4
        LD      R5, Q8_GUARDAR_R5
        RET

Q8_GUARDAR_R2:     .FILL #0
Q8_GUARDAR_R3:     .FILL #0
Q8_GUARDAR_R4:     .FILL #0
Q8_GUARDAR_R5:     .FILL #0
Q8_SIGNO:          .FILL #0
Q8_MULTIPLICADOR:  .FILL #0
Q8_CANTIDAD_BITS:  .FILL #0

.END