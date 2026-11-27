; Adaptacion de grupo21/LABORATORIO3/programa.py (publicado como Assembly).
; Entrada R0: decimas de grado, 0..3600. Salida R0: seno Q3.12.
; Conserva la reduccion por cuadrantes y los cuatro terminos de Taylor originales.
; R1-R7 se guardan y restauran; no realiza E/S ni detiene al llamador.
CALCULAR_SENO
    ST R1, SENO_SAVE_R1
    ST R2, SENO_SAVE_R2
    ST R3, SENO_SAVE_R3
    ST R4, SENO_SAVE_R4
    ST R5, SENO_SAVE_R5
    ST R6, SENO_SAVE_R6
    ST R7, SENO_SAVE_R7
    ADD R0, R0, #0
    BRn SENO_FUERA_DE_RANGO
    LD R1, SENO_NEG_3600
    ADD R2, R0, R1
    BRp SENO_FUERA_DE_RANGO
    BR CONTINUAR
SENO_FUERA_DE_RANGO
    AND R0, R0, #0
    BR SENO_RETORNO
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
    AND R3, R3, #0
    ADD R3, R3, #1
    BRnzp CONVERSION

CUADRANTE2
    LD R1, LIMITE180
    NOT R1, R1
    ADD R1, R1, #1
    ADD R2, R0, R1
    NOT R2, R2
    ADD R2, R2, #1

    AND R3, R3, #0
    ADD R3, R3, #1
    BRnzp CONVERSION

CUADRANTE3
    LD R1, LIMITE180
    NOT R1, R1
    ADD R1, R1, #1
    ADD R2, R0, R1

    AND R3, R3, #0
    ADD R3, R3, #-1
    BRnzp CONVERSION

CUADRANTE4
    LD R1, LIMITE360
    NOT R1, R1
    ADD R1, R1, #1
    ADD R2, R0, R1
    NOT R2, R2
    ADD R2, R2, #1

    AND R3, R3, #0
    ADD R3, R3, #-1

; =================================
; CONVERSION A RADIANES Q3.12
; x = angulo_reducido * 12868 / 1800
; =================================

CONVERSION

; Inicializar producto
AND R4, R4, #0
AND R5, R5, #0

; Contador = angulo reducido
ADD R6, R2, #0

; Multiplicador = 12868
LD R1, MULTIPLICADOR

BUCLE_MULT
    ADD R6, R6, #0
    BRz FIN_MULT

    ADD R4, R4, R1
    BRn ACARREO

    ADD R6, R6, #-1
    BRnzp BUCLE_MULT

ACARREO
    LD R7, BASE32768
    ADD R4, R4, R7
    ADD R5, R5, #1

    ADD R6, R6, #-1
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

    LD R6, BASE32768
    ADD R7, R7, R6
    ADD R4, R7, #0

    ADD R2, R2, #1
    BRnzp BUCLE_DIV1800

RESTA1800
    ADD R4, R7, #0
    ADD R2, R2, #1
    BRnzp BUCLE_DIV1800

FIN_DIV1800


; R2 = angulo en radianes Q3.12
ST R2, X_Q12


; CALCULANDO X^2

;inicializando los registros 

LD R2, X_Q12

AND R4, R4, #0
AND R5, R5, #0

ADD R1, R2, #0
ADD R6, R2, #0

BUCLE_CUADRADO
    ADD R6, R6, #0
    BRz FIN_CUADRADO

    ADD R4, R4, R1
    BRn ACARREO_CUADRADO

    ADD R6, R6, #-1
    BRnzp BUCLE_CUADRADO

ACARREO_CUADRADO
    LD R7, BASE32768
    ADD R4, R4, R7
    ADD R5, R5, #1
    ADD R6, R6, #-1
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

    LD R6, BASE32768
    ADD R7, R7, R6
    ADD R4, R7, #0

    ADD R2, R2, #1
    BRnzp BUCLE_DIV4096

RESTA4096

    ADD R4, R7, #0
    ADD R2, R2, #1
    BRnzp BUCLE_DIV4096

FIN_DIV4096

ST R2, X2_Q12

; =================================
; CALCULAR X^3 = X * X^2
; =================================

LD R1, X2_Q12
LD R6, X_Q12

AND R4, R4, #0
AND R5, R5, #0

BUCLE_CUBO
    ADD R6, R6, #0
    BRz FIN_CUBO

    ADD R4, R4, R1
    BRn ACARREO_CUBO

    ADD R6, R6, #-1
    BRnzp BUCLE_CUBO

ACARREO_CUBO
    LD R7, BASE32768
    ADD R4, R4, R7
    ADD R5, R5, #1
    ADD R6, R6, #-1
    BRnzp BUCLE_CUBO



FIN_CUBO
    ST R4, X3_BAJO
    ST R5, X3_ALTO

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
    LD R6, BASE32768
    ADD R7, R7, R6
    ADD R4, R7, #0

    ADD R2, R2, #1
    BRnzp BUCLE_DIV_X3

RESTA_DIV_X3
    ADD R4, R7, #0
    ADD R2, R2, #1
    BRnzp BUCLE_DIV_X3

FIN_DIV_X3
    ST R2, X3_Q12

; =================================
; CALCULAR T2 = -X3_Q12 / 6
; =================================

    LD R1, NEG6
    AND R2, R2, #0
    LD R4, X3_Q12

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

    LD R1, X3_Q12
    LD R6, X2_Q12

    AND R4, R4, #0
    AND R5, R5, #0

    LD R0, BASE32768

BUCLE_QUINTO
    ADD R6, R6, #0
    BRz FIN_QUINTO

    ADD R4, R4, R1
    BRn ACARREO_QUINTO

    ADD R6, R6, #-1
    BRnzp BUCLE_QUINTO

ACARREO_QUINTO
    ADD R4, R4, R0
    ADD R5, R5, #1

    ADD R6, R6, #-1
    BRnzp BUCLE_QUINTO

FIN_QUINTO
    ST R4, X5_BAJO
    ST R5, X5_ALTO

; =================================
; DIVIDIR X^5 POR 491520
; =================================

    AND R2, R2, #0
    ADD R1, R5, #0
    LD R7, NEG15

BUCLE_DIV_T3
    ADD R1, R1, R7
    BRn FIN_DIV_T3

    ADD R2, R2, #1
    BRnzp BUCLE_DIV_T3

FIN_DIV_T3
    ST R2, T3_Q12

; =================================
; CONVERTIR X^5 A Q3.12
; DIVISION POR 4096
; =================================

    LD R4, X5_BAJO
    LD R5, X5_ALTO

    AND R2, R2, #0
    LD R1, NEG4096

BUCLE_DIV_X5
    ADD R7, R4, R1
    BRzp RESTA_DIV_X5

    ADD R5, R5, #0
    BRz FIN_DIV_X5

    ADD R5, R5, #-1
    LD R6, BASE32768
    ADD R7, R7, R6
    ADD R4, R7, #0

    ADD R2, R2, #1
    BRnzp BUCLE_DIV_X5

RESTA_DIV_X5
    ADD R4, R7, #0
    ADD R2, R2, #1
    BRnzp BUCLE_DIV_X5

FIN_DIV_X5
    ST R2, X5_Q12


; =================================
; CALCULAR T4 = (T3_Q12 * X2_Q12) / (4096 * 42)
; =================================

    LD R1, T3_Q12
    LD R6, X2_Q12

    AND R4, R4, #0
    AND R5, R5, #0

    LD R0, BASE32768

BUCLE_T4_MULT
    ADD R6, R6, #0
    BRz FIN_T4_MULT

    ADD R4, R4, R1
    BRn ACARREO_T4

    ADD R6, R6, #-1
    BRnzp BUCLE_T4_MULT

ACARREO_T4
    ADD R4, R4, R0
    ADD R5, R5, #1

    ADD R6, R6, #-1
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
    LD R6, BASE32768
    ADD R7, R7, R6
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

    LD R0, X_Q12
    LD R1, T2_Q12
    ADD R0, R0, R1

    LD R1, T3_Q12
    ADD R0, R0, R1

    LD R1, T4_Q12
    NOT R1, R1
    ADD R1, R1, #1
    ADD R0, R0, R1

    ; Aplicar signo del cuadrante

ADD R3, R3, #0
BRzp SIGNO_OK

NOT R0, R0
ADD R0, R0, #1

SIGNO_OK
    ST R0, SENO_Q12
SENO_RETORNO
    LD R1, SENO_SAVE_R1
    LD R2, SENO_SAVE_R2
    LD R3, SENO_SAVE_R3
    LD R4, SENO_SAVE_R4
    LD R5, SENO_SAVE_R5
    LD R6, SENO_SAVE_R6
    LD R7, SENO_SAVE_R7
    RET
MULTIPLICADOR .FILL #12868
LIMITE90 .FILL #900
LIMITE180 .FILL #1800
LIMITE270 .FILL #2700
LIMITE360 .FILL #3600
SENO_NEG_3600 .FILL #-3600
SENO_SAVE_R1 .FILL #0
SENO_SAVE_R2 .FILL #0
SENO_SAVE_R3 .FILL #0
SENO_SAVE_R4 .FILL #0
SENO_SAVE_R5 .FILL #0
SENO_SAVE_R6 .FILL #0
SENO_SAVE_R7 .FILL #0
T2_Q12   .FILL #0
T3_Q12 .FILL #0
T4_Q12  .FILL #0

X_Q12       .FILL #1844
X2_Q12  .FILL #0
X3_Q12 .FILL #0
X5_Q12 .FILL #0

BASE32768   .FILL x8000

NEG6     .FILL #-6
NEG42    .FILL #-42
NEG15    .FILL #-15
NEG4096  .FILL #-4096
NEG1800  .FILL #-1800

X3_BAJO .FILL #0
X3_ALTO .FILL #0

X5_BAJO .FILL #0
X5_ALTO .FILL #0

SENO_Q12 .FILL #0


.END
