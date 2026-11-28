;se debe ingresar el angulo multiplicado por 10, dado que no acepta
;numeros decimales (90 ----> 900)
;                  (180 ----> 1800)
;                  (20,1 ---> 201)
.ORIG x3000

    LD R0, ANGULO
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

INICIO

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

; =================================
; [G23] CALCULO DE LOS TERMINOS CON MUL / MULHU / DIVU (ISA G23, Grupo 23)
; Mismo metodo (serie de Taylor de 4 terminos, valores Q3.12, divisiones
; truncadas) y mismos resultados que la version original del Grupo 21: cada
; multiplicacion por sumas sucesivas pasa a MUL + MULHU (producto de 32 bits),
; cada division por 4096 a un corrimiento, y las divisiones por 1800, 6, 120 y
; 42 por restas sucesivas pasan a DIVU.
; =================================
CONVERSION
; x = floor(r * 12868 / 1800) = 7r + floor(67r / 450)  (12868 = 7*1800 + 268 y
; 268/1800 = 67/450: identico y sin pasar de 16 bits, r <= 900)
    LD R1, G23_K67
    MUL R4, R2, R1          ; 67r (<= 60300)
    LD R1, G23_K450
    DIVU R4, R4, R1         ; floor(67r / 450)
    AND R1, R1, #0
    ADD R1, R1, #7
    MUL R5, R2, R1          ; 7r
    ADD R2, R5, R4          ; x en Q3.12
    ST R2, ANGULO_Q12
; x2 = floor(x * x / 4096)
    MUL R4, R2, R2          ; parte baja del producto de 32 bits
    MULHU R5, R2, R2        ; parte alta
    LSL R5, R5, #4
    LSR R4, R4, #12
    OR R1, R5, R4           ; (alta:baja) >> 12
    ST R1, CUADRADO_Q12
; x3 = floor(x * x2 / 4096)
    MUL R4, R2, R1
    MULHU R5, R2, R1
    LSL R5, R5, #4
    LSR R4, R4, #12
    OR R0, R5, R4
    ST R0, CUBO_Q12
; T2 = -floor(x3 / 6)
    AND R4, R4, #0
    ADD R4, R4, #6
    DIVU R4, R0, R4
    NOT R4, R4
    ADD R4, R4, #1
    ST R4, T2_Q12
; x5 = floor(x3 * x2 / 4096) (16 bits sin signo, como la original)
    MUL R4, R0, R1
    MULHU R5, R0, R1
    LSL R5, R5, #4
    LSR R4, R4, #12
    OR R2, R5, R4
    ST R2, QUINTA_Q12
; T3 = floor(x5 / 120)  (division sin signo)
    LD R4, G23_K120
    DIVU R2, R2, R4
    ST R2, T3_Q12
; T4 = floor(floor(T3 * x2 / 4096) / 42)
    MUL R4, R2, R1
    MULHU R5, R2, R1
    LSL R5, R5, #4
    LSR R4, R4, #12
    OR R4, R5, R4
    LD R5, G23_K42
    DIVU R4, R4, R5
    ST R4, T4_Q12
    BRnzp G23_SUMAR

G23_K67   .FILL #67
G23_K450  .FILL #450
G23_K120  .FILL #120
G23_K42   .FILL #42

G23_SUMAR
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

FIN_SUBRUTINA

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


    
.END