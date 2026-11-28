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
    ADD R3, R0, #-8
    ADD R3, R3, #-2
    BRz FIN_LECTURA

    ; Detectar ENTER (CR)
    ADD R3, R0, #-8
    ADD R3, R3, #-5
    BRz FIN_LECTURA

    OUT

    ; Detectar punto decimal
    ADD R3, R0, #-8
    ADD R3, R3, #-6
    ADD R3, R3, #-8
    ADD R3, R3, #-6
    ADD R3, R3, #-8
    ADD R3, R3, #-6
    ADD R3, R3, #-4
    BRz PUNTO

    ; Convertir ASCII a numero
    LD R3, NEG48
    ADD R0, R0, R3

    ; Validar digito
    BRn LECTURA

    ADD R3, R0, #-8
    ADD R3, R3, #-2
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

; Inicializar producto
AND R4, R4, #0
AND R5, R5, #0

; Multiplicador = 12868
LD R1, MULTIPLICADOR

BUCLE_MULT
    ADD R2, R2, #0
    BRz FIN_MULT

    ADD R4, R4, R1
    BRn ACARREO

    ADD R2, R2, #-1
    BRnzp BUCLE_MULT

ACARREO
    LD R7, BASE32768
    ADD R4, R4, R7
    ADD R5, R5, #1

    ADD R2, R2, #-1
    BRnzp BUCLE_MULT

FIN_MULT

; =================================
; DIVISION POR 1800
; =================================

AND R2, R2, #0
LD R1, NEG1800

BUCLE_DIV1800
    ADD R7, R4, R1
    BRzp RESTA1800

    ADD R5, R5, #0
    BRz FIN_DIV1800

    ADD R5, R5, #-1

    LD R0, BASE32768
    ADD R7, R7, R0
    ADD R4, R7, #0

    ADD R2, R2, #1
    BRnzp BUCLE_DIV1800

RESTA1800
    ADD R4, R7, #0
    ADD R2, R2, #1
    BRnzp BUCLE_DIV1800

FIN_DIV1800


; R2 = angulo en radianes Q3.12
ST R2, ANGULO_Q12


; CALCULANDO X^2

;inicializando los registros 

LD R2, ANGULO_Q12

AND R4, R4, #0
AND R5, R5, #0

ADD R1, R2, #0

BUCLE_CUADRADO
    ADD R2, R2, #0
    BRz FIN_CUADRADO

    ADD R4, R4, R1
    BRn ACARREO_CUADRADO

    ADD R2, R2, #-1
    BRnzp BUCLE_CUADRADO

ACARREO_CUADRADO
    LD R7, BASE32768
    ADD R4, R4, R7
    ADD R5, R5, #1
    ADD R2, R2, #-1
    BRnzp BUCLE_CUADRADO

FIN_CUADRADO


; =================================
; DIVISION POR 4096
; =================================

AND R2, R2, #0
LD R1, NEG4096

BUCLE_DIV4096

    ADD R7, R4, R1
    BRzp RESTA4096

    ; Comprobar si podemos pedir prestado
    ADD R5, R5, #0
    BRz FIN_DIV4096

    ; Pedir prestado una unidad de R5
    ADD R5, R5, #-1

    LD R0, BASE32768
    ADD R7, R7, R0
    ADD R4, R7, #0

    ADD R2, R2, #1
    BRnzp BUCLE_DIV4096

RESTA4096

    ADD R4, R7, #0
    ADD R2, R2, #1
    BRnzp BUCLE_DIV4096

FIN_DIV4096

ST R2, CUADRADO_Q12


; =================================
; CALCULAR X^3 = X * X^2
; =================================

LD R1, CUADRADO_Q12
LD R2, ANGULO_Q12

AND R4, R4, #0
AND R5, R5, #0

    BUCLE_CUBO
    ADD R2, R2, #0
    BRz FIN_CUBO

    ADD R4, R4, R1
    BRn ACARREO_CUBO

    ADD R2, R2, #-1
    BRnzp BUCLE_CUBO

ACARREO_CUBO
    LD R7, BASE32768
    ADD R4, R4, R7
    ADD R5, R5, #1

    ADD R2, R2, #-1
    BRnzp BUCLE_CUBO

FIN_CUBO
    ST R4, CUBO_BAJO
    ST R5, CUBO_ALTO

; =================================
; CONVERTIR X^3 A Q3.12
; DIVISION POR 4096
; =================================

    AND R2, R2, #0
    LD R1, NEG4096

BUCLE_DIV_X3
    ADD R7, R4, R1
    BRzp RESTA_DIV_X3

    ADD R5, R5, #0
    BRz FIN_DIV_X3

    ADD R5, R5, #-1
    LD R0, BASE32768
    ADD R7, R7, R0
    ADD R4, R7, #0

    ADD R2, R2, #1
    BRnzp BUCLE_DIV_X3

RESTA_DIV_X3
    ADD R4, R7, #0
    ADD R2, R2, #1
    BRnzp BUCLE_DIV_X3

FIN_DIV_X3
    ST R2, CUBO_Q12
    BRnzp G21_DATA_SKIP
G21_DATA_BLOCK
T2_Q12   .FILL #0
T3_Q12 .FILL #0
T4_Q12  .FILL #0

ANGULO_Q12       .FILL #0
CUADRADO_Q12 .FILL #0
CUBO_Q12 .FILL #0
QUINTA_Q12 .FILL #0

BASE32768 .FILL x8000

NEG6     .FILL #-6
NEG42    .FILL #-42
NEG120 .FILL #-120
NEG4096  .FILL #-4096
NEG1800  .FILL #-1800

CUBO_BAJO .FILL #0
CUBO_ALTO .FILL #0
QUINTA_BAJO .FILL #0
QUINTA_ALTO .FILL #0

SENO_Q12 .FILL #0
G21_DATA_SKIP

; =================================
; CALCULAR T2 = -X3_Q12 / 6
; =================================

    LD R1, NEG6
    AND R2, R2, #0
    LD R4, CUBO_Q12

BUCLE_DIV_T2
    ADD R4, R4, R1
    BRn FIN_DIV_T2

    ADD R2, R2, #1
    BRnzp BUCLE_DIV_T2

FIN_DIV_T2
    NOT R2, R2
    ADD R2, R2, #1
    ST R2, T2_Q12

    
; =================================
; CALCULAR X^5 = X3_Q12 * X2_Q12
; =================================

    LD R1, CUBO_Q12
    LD R2, CUADRADO_Q12

    AND R4, R4, #0
    AND R5, R5, #0

    LD R0, BASE32768

BUCLE_QUINTO
    ADD R2, R2, #0
    BRz FIN_QUINTO

    ADD R4, R4, R1
    BRn ACARREO_QUINTO

    ADD R2, R2, #-1
    BRnzp BUCLE_QUINTO

ACARREO_QUINTO
    ADD R4, R4, R0
    ADD R5, R5, #1

    ADD R2, R2, #-1
    BRnzp BUCLE_QUINTO

FIN_QUINTO
    ST R4, QUINTA_BAJO
    ST R5, QUINTA_ALTO

; =================================
; CALCULAR T3 = X^5 / 120
; =================================


; =================================
; CONVERTIR X^5 A Q3.12
; DIVISION POR 4096
; =================================

    LD R4, QUINTA_BAJO
    LD R5, QUINTA_ALTO

    AND R2, R2, #0
    LD R1, NEG4096

BUCLE_DIV_X5
    ADD R7, R4, R1
    BRzp RESTA_DIV_X5

    ADD R5, R5, #0
    BRz FIN_DIV_X5

    ADD R5, R5, #-1
    LD R0, BASE32768
    ADD R7, R7, R0
    ADD R4, R7, #0

    ADD R2, R2, #1
    BRnzp BUCLE_DIV_X5

RESTA_DIV_X5
    ADD R4, R7, #0
    ADD R2, R2, #1
    BRnzp BUCLE_DIV_X5

FIN_DIV_X5
    ST R2, QUINTA_Q12


; =================================
; CALCULAR T3 = X5_Q12 / 120
; R2 contiene el resultado sin signo
; =================================

; Separar el valor en base 32768

    AND R5, R5, #0
    ADD R4, R2, #0
    BRzp INICIO_DIV_T3

; Si R2 es negativo, representa un valor
; sin signo mayor o igual a 32768

    AND R5, R5, #0
    ADD R5, R5, #1

    LD R7, BASE32768
    ADD R4, R4, R7

INICIO_DIV_T3

    AND R2, R2, #0
    LD R1, NEG120

BUCLE_DIV_T3

    ADD R4, R4, R1
    BRn PRESTAR_T3

    ADD R2, R2, #1
    BRnzp BUCLE_DIV_T3

PRESTAR_T3

; Si no hay parte alta, terminó la división

    ADD R5, R5, #0
    BRz FIN_DIV_T3

; Pedir prestado una unidad de la parte alta

    ADD R5, R5, #-1

    LD R7, BASE32768
    ADD R4, R4, R7

    ADD R2, R2, #1
    BRnzp BUCLE_DIV_T3

FIN_DIV_T3

    ST R2, T3_Q12

; =================================
; CALCULAR T4 = (T3_Q12 * X2_Q12) / (4096 * 42)
; =================================

    LD R1, T3_Q12
    LD R2, CUADRADO_Q12

    AND R4, R4, #0
    AND R5, R5, #0

    LD R0, BASE32768

BUCLE_T4_MULT
    ADD R2, R2, #0
    BRz FIN_T4_MULT

    ADD R4, R4, R1
    BRn ACARREO_T4

    ADD R2, R2, #-1
    BRnzp BUCLE_T4_MULT

ACARREO_T4
    ADD R4, R4, R0
    ADD R5, R5, #1

    ADD R2, R2, #-1
    BRnzp BUCLE_T4_MULT

FIN_T4_MULT


; =================================
; DIVIDIR EL PRODUCTO POR 4096
; =================================

    AND R2, R2, #0
    LD R1, NEG4096

BUCLE_DIV4096_T4
    ADD R7, R4, R1
    BRzp RESTA4096_T4

    ADD R5, R5, #0
    BRz FIN_DIV4096_T4

    ADD R5, R5, #-1
    LD R0, BASE32768
    ADD R7, R7, R0
    ADD R4, R7, #0

    ADD R2, R2, #1
    BRnzp BUCLE_DIV4096_T4

RESTA4096_T4
    ADD R4, R7, #0
    ADD R2, R2, #1
    BRnzp BUCLE_DIV4096_T4

FIN_DIV4096_T4

; =================================
; DIVIDIR POR 42
; =================================

    AND R1, R1, #0
    LD R4, NEG42

BUCLE_DIV42
    ADD R2, R2, R4
    BRn FIN_DIV42

    ADD R1, R1, #1
    BRnzp BUCLE_DIV42

FIN_DIV42

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

    ; Guardar resultado Q3.12

.END
