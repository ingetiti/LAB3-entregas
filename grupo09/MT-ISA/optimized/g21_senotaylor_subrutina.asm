.ORIG x3000
INICIO

  ; LEA R0, MENSAJE
    ;PUTS

    ; Inicializar registros
    AND R1, R1, #0       ; Parte entera
    AND R2, R2, #0       ; Primer decimal
    AND R4, R4, #0       ; Estado del punto decimal

LECTURA

   GETC

    ; Detectar ENTER (LF)
    ADD R3, R0, #-10
    BRz FIN_LECTURA

    ; Detectar ENTER (CR)
    ADD R3, R0, #-13
    BRz FIN_LECTURA

    OUT

    ; Detectar punto decimal
    ADD R3, R0, #-14
    ADD R3, R3, #-14
    ADD R3, R3, #-14
    ADD R3, R3, #-4
    BRz PUNTO

    ; Convertir ASCII a numero
    LD R3, NEG48
    ADD R0, R0, R3

    ; Validar digito
    BRn LECTURA

    ADD R3, R0, #-10
    BRzp LECTURA

    ; Determinar si es parte entera o decimal
    ADD R4, R4, #0
    BRz PARTE_ENTERA

    ADD R3, R4, #-1
    BRp LECTURA

    ; Guardar primer decimal
    ADD R2, R0, #0
    ADD R4, R4, #1

    BRnzp LECTURA

PARTE_ENTERA

    ; R1 = R1 * 10 + digito
    ADD R3, R1, R1
    ADD R5, R3, R3
    ADD R5, R5, R5
    ADD R1, R3, R5
    ADD R1, R1, R0

    BRnzp LECTURA

PUNTO

    ADD R4, R4, #0
    BRp LECTURA

    ADD R4, R4, #1
    BRnzp LECTURA


FIN_LECTURA

    ; Convertir parte entera a decimas
    ADD R3, R1, R1
    ADD R5, R3, R3
    ADD R5, R5, R5
    ADD R1, R3, R5

    ; Sumar primer decimal
    ADD R0, R1, R2

     ; Llamar a la subrutina
    JSR CALCULAR_SENO

    ST R0, RESULTADO
    HALT

NEG48          .FILL #-48
RESULTADO      .FILL #0

; Entrada: R0, angulo en decimas de grado entre 0 y 3600 inclusive.
; Salida: R0, seno en Q3.12, o xFFFF en caso de argumento invalido.
; Se conservan R1 a R7. Las palabras de guardado son de uso interno.
CALCULAR_SENO
    ST R1, SEN_R1
    ST R2, SEN_R2
    ST R3, SEN_R3
    ST R4, SEN_R4
    ST R5, SEN_R5
    ST R7, SEN_R7

    ADD R0, R0, #0
    BRn SEN_ERROR
    LD R1, SEN_NEG3600
    ADD R2, R0, R1
    BRp SEN_ERROR

    ; Reducir a [0, 900]. R7 es positivo si corresponde signo negativo.
    LD R1, SEN_1800
    SUB R7, R0, R1
    BRnz SEN_REFLEJAR
    ADD R0, R7, #0

SEN_REFLEJAR
    LD R2, SEN_NEG900
    ADD R2, R0, R2
    BRnz SEN_RADIANES
    SUB R0, R1, R0

SEN_RADIANES
    ; x = floor(angulo * 12868 / 1800), expresado en Q3.12.
    LD R2, SEN_PI_Q12
    MULUW R2, R0, R2
    DIVUW R0, R2, R1

    ; Conservar los truncamientos intermedios de la serie original.
    ; R4 guarda x^2 en Q3.12. R0 acumula los terminos del polinomio.
    MULUW R2, R0, R0
    LSRW R4, R2, #12

    MULUW R2, R0, R4
    LSRW R2, R2, #12
    ADD R5, R2, #0

    LD R1, SEN_6
    DIVUW R2, R2, R1
    SUB R0, R0, R2

    ; El termino x^5 escalado puede superar x7FFF.
    MULUW R2, R5, R4
    LSRW R2, R2, #12
    LD R1, SEN_120
    DIVUW R2, R2, R1
    ADD R0, R0, R2

    MULUW R2, R2, R4
    LSRW R2, R2, #12
    LD R1, SEN_42
    DIVUW R2, R2, R1
    SUB R0, R0, R2

    ADD R7, R7, #0
    BRnz SEN_GUARDAR
    NOT R0, R0
    ADD R0, R0, #1

SEN_GUARDAR
    ST R0, SENO_Q12

SEN_RETORNAR
    LD R1, SEN_R1
    LD R2, SEN_R2
    LD R4, SEN_R4
    LD R5, SEN_R5
    LD R7, SEN_R7
    LD R3, SEN_R3
    RET

SEN_ERROR
    AND R0, R0, #0
    ADD R0, R0, #-1
    BRnzp SEN_RETORNAR

SEN_NEG3600    .FILL #-3600
SEN_NEG900     .FILL #-900
SEN_1800       .FILL #1800
SEN_PI_Q12     .FILL #12868
SEN_6          .FILL #6
SEN_42         .FILL #42
SEN_120        .FILL #120

SEN_R1         .FILL #0
SEN_R2         .FILL #0
SEN_R3         .FILL #0
SEN_R4         .FILL #0
SEN_R5         .FILL #0
SEN_R7         .FILL #0
SENO_Q12       .FILL #0

.END
