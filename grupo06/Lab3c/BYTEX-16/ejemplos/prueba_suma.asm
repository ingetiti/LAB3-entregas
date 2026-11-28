; Ejemplo para nuestro simulador BYTEX-16.
; Suma dos enteros y muestra el resultado decimal por pantalla.
; Se pueden cambiar NUMERO_A y NUMERO_B: ambos deben ser >= 0
; y su suma debe estar entre 0 y 99.
; La suma tambien queda en R2 y en la etiqueta RESULTADO.

.ORIG x3000
    LD R0, NUMERO_A
    LD R1, NUMERO_B
    ADD R2, R0, R1
    ST R2, RESULTADO

    LEA R0, MENSAJE
    PUTS

    ; Separar el resultado en decenas (R1) y unidades (R3).
    AND R1, R1, #0
    ADD R3, R2, #0
CONTAR_DECENAS
    ADD R4, R3, #-10
    BRn MOSTRAR
    ADD R3, R4, #0
    ADD R1, R1, #1
    BR CONTAR_DECENAS

MOSTRAR
    ; No imprimir un cero a la izquierda si hay una sola cifra.
    ADD R1, R1, #0
    BRz UNIDADES
    LD R0, ASCII_CERO
    ADD R0, R0, R1
    OUT
UNIDADES
    LD R0, ASCII_CERO
    ADD R0, R0, R3
    OUT
    LD R0, SALTO_LINEA
    OUT
    HALT

NUMERO_A    .FILL #5
NUMERO_B    .FILL #7
RESULTADO   .BLKW #1
ASCII_CERO  .FILL #48
SALTO_LINEA .FILL #10
MENSAJE     .STRINGZ "Resultado de la suma: "
.END
