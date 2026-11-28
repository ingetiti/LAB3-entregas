.ORIG x3000
INICIO

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

    ; Detectar punto decimal ('.' = 46)
    LD R3, CONST46
    SUB R3, R0, R3
    BRz PUNTO

    ; Convertir ASCII a numero ('0' = 48)
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
    LD R5, CONST10
    MUL R1, R1, R5
    ADD R1, R1, R0

    BRnzp LECTURA

PUNTO

    ADD R4, R4, #0
    BRp LECTURA

    ADD R4, R4, #1
    BRnzp LECTURA


FIN_LECTURA

    ; Convertir parte entera a decimas y sumar primer decimal
    LD R5, CONST10
    MUL R1, R1, R5
    ADD R0, R1, R2

    ; Llamar a la subrutina
    JSR CALCULAR_SENO

    ST R0, RESULTADO
    HALT

;================================
;SUBRUTINA SENO TAYLOR
;================================

NEG48        .FILL #-48
CONST10      .FILL #10
CONST46      .FILL #46

ANGULO        .FILL #900
MULTIPLICADOR .FILL #12868

LIMITE       .FILL #3600
LIMITE90     .FILL #900
LIMITE180    .FILL #1800
LIMITE270    .FILL #2700
LIMITE360    .FILL #3600

RESULTADO .FILL #0

ENTRADA_ANGULO .FILL #0

GUARDADO_R1 .FILL #0
GUARDADO_R2 .FILL #0
GUARDADO_R3 .FILL #0
GUARDADO_R4 .FILL #0
GUARDADO_R5 .FILL #0
GUARDADO_R7 .FILL #0

SIGNO_CUADRANTE .FILL #0

CALCULAR_SENO

    ST R0, ENTRADA_ANGULO

    ; Guardar el R3 original antes de utilizarlo como puntero
    LEA R0, GUARDADO_R1
    STR R3, R0, #2

    ; R3 queda como puntero al bloque de registros
    LEA R3, GUARDADO_R1

    STR R1, R3, #0
    STR R2, R3, #1
    STR R4, R3, #3
    STR R5, R3, #4
    STR R7, R3, #5

    LD R0, ENTRADA_ANGULO


; =================================
; VALIDAR ANGULO (0 <= R0 <= 3600)
; =================================

    ADD R0, R0, #0
    BRn ERROR

    LD R1, LIMITE
    SUB R2, R0, R1
    BRp ERROR

    BRnzp CONTINUAR

ERROR
    AND R0, R0, #0
    ADD R0, R0, #-1
    BRnzp RESTAURAR_ERROR

RESTAURAR_ERROR

    LDR R1, R3, #0
    LDR R2, R3, #1
    LDR R4, R3, #3
    LDR R5, R3, #4
    LDR R7, R3, #5
    LDR R3, R3, #2

    RET

; =================================
; SELECCION DE CUADRANTE
; =================================

CONTINUAR

    LD R1, LIMITE90
    SUB R2, R0, R1
    BRnz CUADRANTE1

    LD R1, LIMITE180
    SUB R2, R0, R1
    BRnz CUADRANTE2

    LD R1, LIMITE270
    SUB R2, R0, R1
    BRnz CUADRANTE3

    BRnzp CUADRANTE4

CUADRANTE1
    ADD R2, R0, #0

    AND R1, R1, #0
    ADD R1, R1, #1
    STR R1, R3, #6

    BRnzp CONVERSION

CUADRANTE2
    LD R1, LIMITE180
    SUB R2, R1, R0

    AND R1, R1, #0
    ADD R1, R1, #1
    STR R1, R3, #6

    BRnzp CONVERSION

CUADRANTE3
    LD R1, LIMITE180
    SUB R2, R0, R1

    AND R1, R1, #0
    ADD R1, R1, #-1
    STR R1, R3, #6

    BRnzp CONVERSION

CUADRANTE4
    LD R1, LIMITE360
    SUB R2, R1, R0

    AND R1, R1, #0
    ADD R1, R1, #-1
    STR R1, R3, #6

; =================================
; CONVERSION A RADIANES Q3.12
; x = (angulo_reducido * 12868) / 1800
; =================================

CONVERSION

    LD R1, MULTIPLICADOR
    MUL R4, R2, R1          ; parte baja 16 bits
    MULH R5, R2, R1         ; parte alta 16 bits
    LD R1, DIV1800
    JSR DIV_32_16           ; R2 = angulo en radianes Q3.12
    ST R2, ANGULO_Q12

; =================================
; CALCULAR X^2 = (X * X) / 4096
; =================================

    MUL R4, R2, R2
    MULH R5, R2, R2
    RSHFL R4, R4, #12
    LSHF R5, R5, #4
    ADD R2, R4, R5
    ST R2, CUADRADO_Q12

; =================================
; CALCULAR X^3 = (X^2 * X) / 4096
; =================================

    LD R1, ANGULO_Q12
    MUL R4, R2, R1
    MULH R5, R2, R1
    RSHFL R4, R4, #12
    LSHF R5, R5, #4
    ADD R4, R4, R5
    ST R4, CUBO_Q12

; =================================
; CALCULAR T2 = -(X^3 / 6)
; =================================

    AND R5, R5, #0
    LD R1, DIV6
    JSR DIV_32_16
    NOT R2, R2
    ADD R2, R2, #1
    ST R2, T2_Q12

; =================================
; CALCULAR X^5 = (X^3 * X^2) / 4096
; =================================

    LD R1, CUBO_Q12
    LD R2, CUADRADO_Q12
    MUL R4, R1, R2
    MULH R5, R1, R2
    RSHFL R4, R4, #12
    LSHF R5, R5, #4
    ADD R4, R4, R5
    ST R4, QUINTA_Q12

; =================================
; CALCULAR T3 = X^5 / 120
; =================================

    AND R5, R5, #0
    LD R1, DIV120
    JSR DIV_32_16
    ST R2, T3_Q12

; =================================
; CALCULAR T4 = ((T3 * X^2) / 4096) / 42
; =================================

    LD R1, CUADRADO_Q12
    MUL R4, R2, R1
    MULH R5, R2, R1
    RSHFL R4, R4, #12
    LSHF R5, R5, #4
    ADD R4, R4, R5
    AND R5, R5, #0
    LD R1, DIV42
    JSR DIV_32_16
    ST R2, T4_Q12

; =================================
; SUMAR SERIE DE TAYLOR
; S = X + T2 + T3 - T4
; =================================

    LD R0, ANGULO_Q12
    LD R1, T2_Q12
    ADD R0, R0, R1

    LD R1, T3_Q12
    ADD R0, R0, R1

    LD R1, T4_Q12
    SUB R0, R0, R1

    ; Aplicar signo del cuadrante
    LDR R1, R3, #6
    ADD R1, R1, #0
    BRzp SIGNO_OK

    NOT R0, R0
    ADD R0, R0, #1

SIGNO_OK
    ST R0, SENO_Q12

FIN_CALCULAR_SENO

    LDR R1, R3, #0
    LDR R2, R3, #1
    LDR R4, R3, #3
    LDR R5, R3, #4
    LDR R7, R3, #5
    LDR R3, R3, #2

    RET

; =================================
; DIV_32_16: cociente sin signo (R5:R4) / R1 -> R2
; Conserva R1, R3, R6. Destruye R0, R4, R5, R7.
; =================================
DIV_32_16
    ST R7, DIV_RET
    AND R0, R0, #0
    ADD R0, R0, #15
    ADD R0, R0, #1
DIV_32_16_LOOP
    ADD R5, R5, R5
    ADD R4, R4, #0
    BRzp DIV_32_16_NOMSB
    ADD R5, R5, #1
DIV_32_16_NOMSB
    ADD R4, R4, R4
    SUB R7, R5, R1
    BRn DIV_32_16_NEXT
    ADD R5, R7, #0
    ADD R4, R4, #1
DIV_32_16_NEXT
    ADD R0, R0, #-1
    BRp DIV_32_16_LOOP
    ADD R2, R4, #0
    LD R7, DIV_RET
    RET

DIV_RET      .FILL #0
T2_Q12       .FILL #0
T3_Q12       .FILL #0
T4_Q12       .FILL #0

ANGULO_Q12   .FILL #0
CUADRADO_Q12 .FILL #0
CUBO_Q12     .FILL #0
QUINTA_Q12   .FILL #0

DIV6         .FILL #6
DIV42        .FILL #42
DIV120       .FILL #120
DIV1800      .FILL #1800

SENO_Q12     .FILL #0

.END
