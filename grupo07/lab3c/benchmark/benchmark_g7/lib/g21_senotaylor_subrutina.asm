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

;================================
;SUBRUTINA SENO TAYLOR
;================================

;MENSAJE .STRINGZ "Ingrese angulo en grados: "
NEG48 .FILL #-48

 JSR CALCULAR_SENO
ST R0, RESULTADO
HALT

ANGULO       .FILL #900
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
; VALIDAR ANGULO
; =================================

ADD R0, R0, #0
BRn ERROR

LD R1, LIMITE
NOT R1, R1
ADD R1, R1, #1
ADD R2, R0, R1
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
    NOT R1, R1
    ADD R1, R1, #1
    ADD R2, R0, R1
    BRnz CUADRANTE1

    LD R1, LIMITE180
    NOT R1, R1
    ADD R1, R1, #1
    ADD R2, R0, R1
    BRnz CUADRANTE2

    LD R1, LIMITE270
    NOT R1, R1
    ADD R1, R1, #1
    ADD R2, R0, R1
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
    NOT R1, R1
    ADD R1, R1, #1
    ADD R2, R0, R1
    NOT R2, R2
    ADD R2, R2, #1

    AND R1, R1, #0
    ADD R1, R1, #1
    STR R1, R3, #6

    BRnzp CONVERSION

CUADRANTE3
    LD R1, LIMITE180
    NOT R1, R1
    ADD R1, R1, #1
    ADD R2, R0, R1

    AND R1, R1, #0
    ADD R1, R1, #-1
    STR R1, R3, #6

    BRnzp CONVERSION

CUADRANTE4
    LD R1, LIMITE360
    NOT R1, R1
    ADD R1, R1, #1
    ADD R2, R0, R1
    NOT R2, R2
    ADD R2, R2, #1

    AND R1, R1, #0
    ADD R1, R1, #-1
    STR R1, R3, #6

; =================================
; CONVERSION A RADIANES Q3.12
; x = angulo_reducido * 12868 / 1800
; =================================

CONVERSION
; ---- Version con MUL / DIV / REM / SHL / SHR (ISA Grupo 7) ----
; Mismos resultados que el calculo original por sumas y restas repetidas.
; x = angulo_reducido * 12868 / 1800 = q*3217 + 7*r + (r*67)/450,
; con angulo_reducido = q*450 + r  (todos los productos entran en 16 bits)
    LD R1, K450
    DIV R4, R2, R1          ; q
    REM R5, R2, R1          ; r
    LD R1, K3217
    MUL R4, R4, R1          ; q*3217
    LD R1, K7
    MUL R7, R5, R1          ; 7*r
    LD R1, K67
    MUL R5, R5, R1          ; r*67
    LD R1, K450
    DIV R5, R5, R1          ; (r*67)/450
    ADD R4, R4, R7
    ADD R2, R4, R5          ; R2 = angulo en radianes Q3.12
    ST R2, ANGULO_Q12

    LD R0, K12              ; R0 = 12 (desplazamiento: dividir por 4096)
    LD R7, K4               ; R7 = 4

; x^2 = (x*x) / 4096
    MUL R4, R2, R2
    MULH R5, R2, R2
    SHR R4, R4, R0
    SHL R5, R5, R7
    ADD R4, R4, R5          ; R4 = x^2 (Q12)
    ST R4, CUADRADO_Q12

; x^3 = (x * x^2) / 4096
    MUL R1, R2, R4
    MULH R5, R2, R4
    SHR R1, R1, R0
    SHL R5, R5, R7
    ADD R1, R1, R5          ; R1 = x^3 (Q12)
    ST R1, CUBO_Q12

; T2 = -(x^3 / 6)
    LD R5, K6
    DIV R5, R1, R5
    NOT R5, R5
    ADD R5, R5, #1
    ST R5, T2_Q12

; x^5 = (x^3 * x^2) / 4096  (sin signo: puede pasar de 32767)
    MUL R2, R1, R4
    MULH R5, R1, R4
    SHR R2, R2, R0
    SHL R5, R5, R7
    ADD R2, R2, R5
    ST R2, QUINTA_Q12

; T3 = x^5 / 120 = (x^5 >> 1) / 60
    LD R5, K1
    SHR R2, R2, R5
    LD R5, K60
    DIV R2, R2, R5
    ST R2, T3_Q12

; T4 = ((T3 * x^2) / 4096) / 42
    MUL R1, R2, R4
    MULH R5, R2, R4
    SHR R1, R1, R0
    SHL R5, R5, R7
    ADD R1, R1, R5
    LD R5, K42
    DIV R1, R1, R5
    ST R1, T4_Q12

; =================================
; SUMAR SERIE DE TAYLOR
; S = X - X^3/6 + X^5/120 - X^7/5040
; =================================

    LD R0, ANGULO_Q12
    LD R1, T2_Q12
    ADD R0, R0, R1

    LD R1, T3_Q12
    ADD R0, R0, R1

    LD R1, T4_Q12
    NOT R1, R1
    ADD R1, R1, #1
    ADD R0, R0, R1

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


T2_Q12   .FILL #0
T3_Q12 .FILL #0
T4_Q12  .FILL #0

ANGULO_Q12       .FILL #0
CUADRADO_Q12 .FILL #0
CUBO_Q12 .FILL #0
QUINTA_Q12 .FILL #0

K450 .FILL #450
K3217 .FILL #3217
K7 .FILL #7
K67 .FILL #67
K12 .FILL #12
K4 .FILL #4
K6 .FILL #6
K1 .FILL #1
K60 .FILL #60
K42 .FILL #42

SENO_Q12 .FILL #0

    ; Guardar resultado Q3.12

.END
