; ===========================================================================
; POTENCIA con exponente entero 0..127 - Q7.8 - 16 bits
; Programa principal: lee A (real) y B (entero), llama a POTENCIA y muestra.
;   - POTENCIA y MULT estan juntas en el modulo potencia.asm. Este archivo va
;     como entrada ("Usar como entrada") y llama a POTENCIA con .FILL + JSRR.
;   - No inicializa R6: el simulador ya lo apunta a la pila de usuario.
;   - POTENCIA: entrada R0 = A (Q7.8), R1 = B (entero) / salida R0 = A^B,
;     o R0 = x8000 si hubo error (la causa se deduce del signo de B).
;   - LEER, IMPRIMIR y DECIMALES guardan y restauran los registros que usan
;     (y R7), y cada una trae sus propias constantes.
; ===========================================================================
        .ORIG x3000
        .EXTERNAL Mul_Sucesiva_POW-Mul_Sucesiva_POW   ; etiqueta POTENCIA del modulo potencia.asm
        LEA R0, MSGA
        PUTS
        JSR LEER                ; R0 = A en Q7.8
        ST R0, AQ
        LEA R0, MSGB
        PUTS
        JSR LEER                ; R0 = B en Q7.8
        ADD R1, R0, #0          ; R1 = B
        LD R2, MASK8
        AND R2, R1, R2          ; bits fraccionarios de B
        BRz EXP_ENT
        LEA R0, MSGE5           ; B tiene parte decimal
        PUTS
        HALT
EXP_ENT AND R2, R2, #0          ; R2 = B entero
        AND R3, R3, #0          ; R3 = 1 si B es negativo
        ADD R1, R1, #0
        BRzp EXP_POS
        NOT R1, R1
        ADD R1, R1, #1
        ADD R3, R3, #1
EXP_POS LD R4, NEG256
EXP_DIV ADD R5, R1, R4          ; B = B - 256 (restas sucesivas)
        BRn EXP_FIN
        ADD R1, R5, #0
        ADD R2, R2, #1
        BRnzp EXP_DIV
EXP_FIN ADD R3, R3, #0
        BRz EXP_LLAMA
        NOT R2, R2
        ADD R2, R2, #1          ; B negativo
EXP_LLAMA ADD R1, R2, #0        ; R1 = B (entero con signo)
        ST R1, BQ
        LD R0, AQ               ; R0 = A (Q7.8)
        LD R5, POT_PTR          ; direccion completa (16 bits) de POTENCIA
        JSRR R5                 ; R0 = A^B   (x8000 = error)
        ST R0, RQ
        LD R1, COD_ERR
        ADD R1, R0, R1          ; R1 = 0 solo si R0 = x8000
        BRnp MOSTRAR_OK
        LD R1, BQ               ; hubo error: la causa depende del signo de B
        BRn M_NEG
        BRp M_OVF
        LEA R0, MSGE6           ; B = 0: indeterminacion 0^0
        PUTS
        HALT
M_NEG   LEA R0, MSGE4           ; exponente negativo
        PUTS
        HALT
M_OVF   LEA R0, MSGE3           ; overflow
        PUTS
        HALT
MOSTRAR_OK LEA R0, MSGR
        PUTS
        LD R3, RQ
        BRzp MOSTRAR
        LD R0, ASC_MENOS
        OUT
        LD R3, RQ
        NOT R3, R3
        ADD R3, R3, #1          ; R3 = |resultado|
MOSTRAR AND R4, R4, #0          ; R4 = parte entera
        LD R5, NEG256
SEP     ADD R2, R3, R5
        BRn FIN_SEP
        ADD R3, R2, #0
        ADD R4, R4, #1
        BRnzp SEP
FIN_SEP ST R3, FRAC8            ; R3 = parte fraccionaria (0..255)
        ADD R0, R4, #0
        JSR IMPRIMIR            ; imprime la parte entera
        LD R0, ASC_PUNTO
        OUT
        LD R0, FRAC8
        JSR DECIMALES           ; imprime 2 decimales
        LD R0, ASC_LF
        OUT
        HALT

; ---- datos del programa principal ----
MASK8   .FILL x00FF             ; para detectar parte decimal del exponente
NEG256  .FILL #-256
COD_ERR .FILL x8000             ; codigo de error que devuelve POTENCIA
POT_PTR .FILL Mul_Sucesiva_POW-Mul_Sucesiva_POW ; direccion de POTENCIA (la resuelve el enlazador)
ASC_MENOS .FILL x2D
ASC_PUNTO .FILL x2E
ASC_LF  .FILL x0A
AQ      .FILL #0
BQ      .FILL #0
RQ      .FILL #0
FRAC8   .FILL #0

MSGE3   .STRINGZ "ERROR: overflow"
MSGE4   .STRINGZ "ERROR: exp. negativo no soportado"
MSGE5   .STRINGZ "ERROR: exp. no entero"
MSGE6   .STRINGZ "ERROR: indeterminacion 0^0"
MSGA    .STRINGZ "Ingrese A: "
MSGB    .STRINGZ "Ingrese B (entero): "
MSGR    .STRINGZ "Resultado: "

; ===========================================================================
; LEER - lee un numero decimal con signo y hasta 3 decimales
;   Entrada : (teclado)
;   Salida  : R0 = valor en Q7.8
;   Preserva: R1..R5 y R7
; ===========================================================================
LEER    ST R1, LEER_G1
        ST R2, LEER_G2
        ST R3, LEER_G3
        ST R4, LEER_G4
        ST R5, LEER_G5
        ST R7, LEER_G7
        AND R0, R0, #0
        ST R0, SIGNO
        ST R0, NDIG
        ADD R0, R0, #-1
        ST R0, FCNT
        AND R1, R1, #0
        AND R2, R2, #0
        GETC
        OUT
        LD R3, NEG_MENOS
        ADD R3, R0, R3
        BRnp CICLO
        ADD R3, R3, #1
        ST R3, SIGNO
        GETC
        OUT
CICLO   LD R3, NEG_ENTER
        ADD R3, R0, R3
        BRz FIN_LEER
        LD R3, NEG_PUNTO
        ADD R3, R0, R3
        BRnp DIGITO
        LD R3, FCNT
        BRzp ERR_ENT
        AND R3, R3, #0
        ST R3, FCNT
        BRnzp SIGUE
DIGITO  LD R3, NEG_CERO
        ADD R0, R0, R3
        BRn ERR_ENT
        ADD R3, R0, #-9
        BRp ERR_ENT
        LD R3, NDIG
        ADD R3, R3, #1
        ST R3, NDIG
        LD R3, FCNT
        BRzp FRAC
        ADD R3, R1, #-12
        BRp ERR_DESB
        ADD R3, R1, R1
        ADD R4, R3, R3
        ADD R4, R4, R4
        ADD R1, R4, R3
        ADD R1, R1, R0
        LD R3, NEG127
        ADD R3, R1, R3
        BRp ERR_DESB
        BRnzp SIGUE
FRAC    ADD R3, R3, #1
        ST R3, FCNT
        ADD R3, R3, #-3
        BRp ERR_ENT
        ADD R3, R2, R2
        ADD R4, R3, R3
        ADD R4, R4, R4
        ADD R2, R4, R3
        ADD R2, R2, R0
SIGUE   GETC
        OUT
        BRnzp CICLO
FIN_LEER LD R3, NDIG
        BRz ERR_ENT
        LD R3, FCNT
        BRzp PAD_N
        AND R3, R3, #0
PAD_N   NOT R3, R3
        ADD R3, R3, #1
        ADD R3, R3, #3
PAD     ADD R3, R3, #0
        BRz FIN_PAD
        ADD R4, R2, R2
        ADD R5, R4, R4
        ADD R5, R5, R5
        ADD R2, R5, R4
        ADD R3, R3, #-1
        BRnzp PAD
FIN_PAD AND R3, R3, #0
        AND R4, R4, #0
        ADD R4, R4, #8
        LD R5, NEG1000
BITS    ADD R3, R3, R3
        ADD R2, R2, R2
        ADD R0, R2, R5
        BRn NOBIT
        ADD R2, R0, #0
        ADD R3, R3, #1
NOBIT   ADD R4, R4, #-1
        BRp BITS
        LD R5, NEG500
        ADD R0, R2, R5
        BRn SIN_RED
        ADD R3, R3, #1
SIN_RED AND R4, R4, #0
        ADD R4, R4, #8
D256    ADD R1, R1, R1
        ADD R4, R4, #-1
        BRp D256
        ADD R1, R1, R3
        BRn ERR_DESB
        LD R0, SIGNO
        BRz LISTO
        NOT R1, R1
        ADD R1, R1, #1
LISTO   ADD R0, R1, #0          ; R0 = valor leido (salida)
        LD R1, LEER_G1
        LD R2, LEER_G2
        LD R3, LEER_G3
        LD R4, LEER_G4
        LD R5, LEER_G5
        LD R7, LEER_G7
        RET

; ---- errores de entrada (terminan el programa) ----
ERR_ENT LD R0, ERR_LF
        OUT
        LEA R0, MSGE1
        PUTS
        HALT
ERR_DESB LD R0, ERR_LF
        OUT
        LEA R0, MSGE2
        PUTS
        HALT

; ---- ZONA DE DATOS de LEER ----
MSGE1   .STRINGZ "Error: entrada invalida"
MSGE2   .STRINGZ "Error: fuera de rango Q7.8 (+-127.99)"
ERR_LF  .FILL x0A
NEG_MENOS .FILL xFFD3
NEG_PUNTO .FILL xFFD2
NEG_ENTER .FILL xFFF6
NEG_CERO .FILL xFFD0
NEG127  .FILL #-127
NEG500  .FILL #-500
NEG1000 .FILL #-1000
SIGNO   .FILL #0
NDIG    .FILL #0
FCNT    .FILL #0
LEER_G1 .FILL #0
LEER_G2 .FILL #0
LEER_G3 .FILL #0
LEER_G4 .FILL #0
LEER_G5 .FILL #0
LEER_G7 .FILL #0

; ===========================================================================
; IMPRIMIR - imprime R0 (entero >= 0) en decimal, sin ceros a la izquierda
;   Entrada : R0 = numero
;   Salida  : (pantalla)
;   Preserva: R0..R5 y R7     (no usa R6: las cifras salen con una tabla)
; ===========================================================================
IMPRIMIR ST R0, IMP_G0
        ST R1, IMP_G1
        ST R2, IMP_G2
        ST R3, IMP_G3
        ST R4, IMP_G4
        ST R5, IMP_G5
        ST R7, IMP_G7
        ADD R1, R0, #0          ; R1 = valor que falta imprimir
        LEA R2, IMP_TABLA       ; R2 -> tabla de potencias de 10 (negativas)
        AND R5, R5, #0          ; R5 = 0: todavia no salio ninguna cifra
IMP_PROX LDR R3, R2, #0         ; R3 = -potencia de 10
        BRz IMP_FIN             ; 0 marca el fin de la tabla
        AND R4, R4, #0          ; R4 = cifra
IMP_REST ADD R0, R1, R3
        BRn IMP_CIFRA
        ADD R1, R0, #0
        ADD R4, R4, #1
        BRnzp IMP_REST
IMP_CIFRA ADD R4, R4, #0
        BRp IMP_SHOW            ; cifra distinta de 0: se imprime
        ADD R5, R5, #0
        BRp IMP_SHOW            ; ya salieron cifras: se imprime el 0
        LDR R0, R2, #1          ; hay una potencia mas? (si no, son las unidades)
        BRnp IMP_SIG            ; si: cero a la izquierda, se saltea
IMP_SHOW LD R0, IMP_ASC0
        ADD R0, R0, R4
        OUT
        AND R5, R5, #0
        ADD R5, R5, #1
IMP_SIG ADD R2, R2, #1
        BRnzp IMP_PROX
IMP_FIN LD R0, IMP_G0
        LD R1, IMP_G1
        LD R2, IMP_G2
        LD R3, IMP_G3
        LD R4, IMP_G4
        LD R5, IMP_G5
        LD R7, IMP_G7
        RET
IMP_ASC0 .FILL x30
IMP_TABLA .FILL #-10000
        .FILL #-1000
        .FILL #-100
        .FILL #-10
        .FILL #-1
        .FILL #0
IMP_G0  .FILL #0
IMP_G1  .FILL #0
IMP_G2  .FILL #0
IMP_G3  .FILL #0
IMP_G4  .FILL #0
IMP_G5  .FILL #0
IMP_G7  .FILL #0

; ===========================================================================
; DECIMALES - imprime 2 decimales (truncados) de una fraccion Q0.8
;   Entrada : R0 = fraccion (0..255, es decir F/256)
;   Salida  : (pantalla)
;   Preserva: R0..R5 y R7
; ===========================================================================
DECIMALES ST R0, DEC_G0
        ST R1, DEC_G1
        ST R2, DEC_G2
        ST R3, DEC_G3
        ST R4, DEC_G4
        ST R5, DEC_G5
        ST R7, DEC_G7
        ADD R3, R0, #0          ; R3 = fraccion
        AND R4, R4, #0
        ADD R4, R4, #2          ; solo 2 decimales (truncados)
FLOOP   ADD R1, R3, R3
        ADD R2, R1, R1
        ADD R2, R2, R2
        ADD R3, R2, R1          ; R3 = 10 * R3
        AND R0, R0, #0
        LD R5, DEC_N256
FD      ADD R2, R3, R5
        BRn FIN_FD
        ADD R3, R2, #0
        ADD R0, R0, #1
        BRnzp FD
FIN_FD  LD R1, DEC_ASC0
        ADD R0, R0, R1
        OUT
        ADD R4, R4, #-1
        BRp FLOOP
        LD R0, DEC_G0
        LD R1, DEC_G1
        LD R2, DEC_G2
        LD R3, DEC_G3
        LD R4, DEC_G4
        LD R5, DEC_G5
        LD R7, DEC_G7
        RET
DEC_N256 .FILL #-256
DEC_ASC0 .FILL x30
DEC_G0  .FILL #0
DEC_G1  .FILL #0
DEC_G2  .FILL #0
DEC_G3  .FILL #0
DEC_G4  .FILL #0
DEC_G5  .FILL #0
DEC_G7  .FILL #0

        .END
