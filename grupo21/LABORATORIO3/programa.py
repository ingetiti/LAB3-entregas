.ORIG x3000

BRnzp INICIO

ANGULO       .FILL #258
MULTIPLICADOR .FILL #12868

LIMITE       .FILL #3600
LIMITE90     .FILL #900
LIMITE180    .FILL #1800
LIMITE270    .FILL #2700
LIMITE360    .FILL #3600

PROMPT .STRINGZ "Ingrese angulo (en un rango de 0° a 360°): "

NEG_ASCII_CERO .FILL #-48
NEG10_ENTRADA  .FILL #-10
NEG13_ENTRADA  .FILL #-13
PUNTO_ENTRADA  .FILL #46

INICIO

; =================================
; INGRESO DEL ANGULO POR TECLADO
; =================================

    LEA R0, PROMPT
    PUTS

    AND R1, R1, #0    ; Parte entera
    AND R3, R3, #0    ; Decima
    AND R4, R4, #0    ; Cantidad de digitos enteros
    AND R5, R5, #0    ; Estado: 0 entero, 1 decimal
    AND R6, R6, #0    ; Cantidad de decimales

LEER_CARACTER

    GETC
    OUT

; Comprobar ENTER (LF)
    LD R7, NEG10_ENTRADA
    ADD R2, R0, R7
    BRz FIN_LECTURA

; Comprobar ENTER (CR)
    LD R7, NEG13_ENTRADA
    ADD R2, R0, R7
    BRz FIN_LECTURA

; Comprobar punto decimal
    LD R7, PUNTO_ENTRADA
    NOT R7, R7
    ADD R7, R7, #1
    ADD R2, R0, R7
    BRz PUNTO_DECIMAL

; Convertir caracter ASCII a numero
    LD R7, NEG_ASCII_CERO
    ADD R2, R0, R7

    BRn ERROR

    LD R7, NEG10_ENTRADA
    ADD R7, R2, R7
    BRzp ERROR

; Comprobar si estamos en la parte entera
    ADD R5, R5, #0
    BRp GUARDAR_DECIMAL

; =================================
; ACUMULAR PARTE ENTERA
; =================================

    ADD R7, R4, #-3
    BRzp ERROR

; Multiplicar parte entera por 10
    ADD R7, R1, R1
    ADD R0, R7, R7
    ADD R0, R0, R0
    ADD R0, R0, R7
    ADD R1, R0, R2

    ADD R4, R4, #1
    BRnzp LEER_CARACTER

; =================================
; GUARDAR DECIMA
; =================================

GUARDAR_DECIMAL

    ADD R6, R6, #0
    BRp ERROR

    ADD R3, R2, #0
    ADD R6, R6, #1

    BRnzp LEER_CARACTER

; =================================
; DETECTAR PUNTO DECIMAL
; =================================

PUNTO_DECIMAL

    ADD R5, R5, #0
    BRp ERROR

    ADD R4, R4, #0
    BRz ERROR

    ADD R5, R5, #1
    BRnzp LEER_CARACTER

; =================================
; FINALIZAR INGRESO
; =================================

FIN_LECTURA

    ADD R5, R5, #-1
    BRnp ERROR

    ADD R6, R6, #-1
    BRnp ERROR

; Convertir grados a decimas
    ADD R7, R1, R1
    ADD R0, R7, R7
    ADD R0, R0, R0
    ADD R0, R0, R7
    ADD R0, R0, R3

    ST R0, ANGULO

    AND R0, R0, #0
ADD R0, R0, #10
OUT

; =================================
; VALIDAR ANGULO
; =================================


LEA R7, ANGULO
LDR R0, R7, #0
ADD R0, R0, #0
BRn ERROR

LD R1, LIMITE
NOT R1, R1
ADD R1, R1, #1
ADD R2, R0, R1
BRp ERROR

BRnzp CONTINUAR

ERROR
    LEA R0, MENSAJE1
    PUTS
    HALT

MENSAJE1
    .STRINGZ "ANGULO NO VALIDO"

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

; =================================
; CONVERTIR Q3.12 A DECIMAL
; MOSTRAR 4 CIFRAS DECIMALES
; =================================

    LD R2, SENO_Q12

; Comprobar si el resultado es negativo
    ADD R2, R2, #0
    BRzp DEC_POSITIVO

    NOT R2, R2
    ADD R2, R2, #1

    AND R0, R0, #0
ADD R0, R0, #12
ADD R0, R0, R0
ADD R0, R0, R0
ADD R0, R0, #-3
OUT

DEC_POSITIVO

; =================================
; OBTENER PARTE ENTERA
; =================================

    AND R1, R1, #0

    LD R3, NEG4096
    ADD R4, R2, R3
    BRn DEC_ENTERO_CERO

    ADD R2, R4, #0
    ADD R1, R1, #1

DEC_ENTERO_CERO

; Mostrar parte entera
    AND R0, R0, #0
ADD R0, R0, #12
ADD R0, R0, R0
ADD R0, R0, R0
ADD R0, R0, R1
OUT

; Mostrar punto decimal
    AND R0, R0, #0
ADD R0, R0, #12
ADD R0, R0, R0
ADD R0, R0, R0
ADD R0, R0, #-2
OUT

; =================================
; OBTENER 4 CIFRAS DECIMALES
; =================================

    AND R6, R6, #0
    ADD R6, R6, #4

DEC_DIGITO

    AND R1, R1, #0
    AND R5, R5, #0

; Multiplicar el resto por 10
    ADD R4, R4, #0
    AND R4, R4, #0
    ADD R4, R4, #10

DEC_MULT10

    ADD R5, R5, R2

    LD R3, NEG4096
    ADD R3, R5, R3
    BRn DEC_NO_RESTA

    ADD R5, R3, #0
    ADD R1, R1, #1

DEC_NO_RESTA

    ADD R4, R4, #-1
    BRp DEC_MULT10

; Mostrar el dígito obtenido
    AND R0, R0, #0
ADD R0, R0, #12
ADD R0, R0, R0
ADD R0, R0, R0
ADD R0, R0, R1
OUT

; Guardar el resto para el siguiente dígito
    ADD R2, R5, #0

    ADD R6, R6, #-1
    BRp DEC_DIGITO

; Salto de línea
    AND R0, R0, #0
ADD R0, R0, #10
OUT

    HALT



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