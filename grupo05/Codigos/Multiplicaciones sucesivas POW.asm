.ORIG x3000
        LD R6, PILA
        LEA R0, MSGA
        PUTS
        JSR LEER
        ST R1, AQ
        LEA R0, MSGB
        PUTS
        JSR LEER
        ADD R2, R1, #0          ; R2 = B
        LD R1, AQ               ; R1 = A
        JSR MULT                ; R0 = A*B
        ST R0, RQ
        LEA R0, MSGR
        PUTS
        LD R3, RQ
        BRzp MOSTRAR
        LD R0, ASC_MENOS
        OUT
        LD R3, RQ
        NOT R3, R3
        ADD R3, R3, #1
MOSTRAR AND R4, R4, #0
        LD R5, NEG256
SEP     ADD R2, R3, R5
        BRn FIN_SEP
        ADD R3, R2, #0
        ADD R4, R4, #1
        BRnzp SEP
FIN_SEP ST R3, FRAC8
        ADD R0, R4, #0
        AND R5, R5, #0
        ADD R5, R5, #1
        JSR IMPRIMIR
        LD R0, ASC_PUNTO
        OUT
        JSR DECIMALES
        LD R0, ASC_LF
        OUT
        HALT

MSGA    .STRINGZ "Ingrese A: "
MSGB    .STRINGZ "Ingrese B: "
MSGR    .STRINGZ "Resultado: "

LEER    ST R7, GUARDA7
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
LISTO   LD R7, GUARDA7
        RET

PILA    .FILL x4000
NEG_MENOS .FILL xFFD3
NEG_PUNTO .FILL xFFD2
NEG_ENTER .FILL xFFF6
NEG_CERO .FILL xFFD0
NEG127  .FILL #-127
NEG256  .FILL #-256
NEG500  .FILL #-500
NEG1000 .FILL #-1000
ASC_MENOS .FILL x2D
ASC_PUNTO .FILL x2E
ASC_CERO .FILL x30
ASC_LF  .FILL x0A
GUARDA7 .BLKW #1
SIGNO   .BLKW #1
NDIG    .BLKW #1
FCNT    .BLKW #1
FRAC8   .BLKW #1
AQ      .BLKW #1
RQ      .BLKW #1

ERR_ENT LD R0, ASC_LF
        OUT
        LEA R0, MSGE1
        PUTS
        HALT
ERR_DESB LD R0, ASC_LF
        OUT
        LEA R0, MSGE2
        PUTS
        HALT
MSGE1   .STRINGZ "Error: entrada invalida"
MSGE2   .STRINGZ "Error: fuera de rango Q7.8 (+-127.99)"

; ===========================================================================
; MULT - Multiplicacion Q7.8 por suma sucesiva (SUBRUTINA)
;   Entrada : R1 = A    (Q7.8 con signo, 16 bits)
;             R2 = B    (Q7.8 con signo, 16 bits)
;   Salida  : R0 = A*B  (Q7.8 con signo, 16 bits)
;   Preserva: R1..R5 (los guarda en la pila) y R6. No toca R7 (no hay JSR).
;   Desborde: salta a ERR_DESB (el resultado no entra en Q7.8)
;
;   Metodo (todo con sumas, sin multiplicar):
;     |B| = BI + BF/256   (BI = parte entera, BF = parte fraccionaria)
;     |A|*|B| = |A| sumado BI veces            -> fase 1
;             + (|A|/256) sumado BF veces      -> fase 2
;     con |A|/256 = AI + AF/256: cada suma de la fase 2 agrega AI al
;     resultado y AF a un acumulador que "acarrea" 1 al llegar a 256.
;     Asi nunca se necesita un valor mayor a 16 bits.
; ===========================================================================
MULT    ADD R6, R6, #-5         ; reservar 5 palabras en la pila
        STR R1, R6, #0
        STR R2, R6, #1
        STR R3, R6, #2
        STR R4, R6, #3
        STR R5, R6, #4
        ; ---- signos y valores absolutos ----
        AND R5, R5, #0          ; R5 = cantidad de operandos negativos
        ADD R1, R1, #0
        BRzp A_POS
        NOT R1, R1
        ADD R1, R1, #1          ; R1 = |A|
        BRn ERR_DESB            ; x8000 no tiene opuesto en 16 bits
        ADD R5, R5, #1
A_POS   ADD R2, R2, #0
        BRzp B_POS
        NOT R2, R2
        ADD R2, R2, #1          ; R2 = |B|
        BRn ERR_DESB
        ADD R5, R5, #1
B_POS   AND R0, R0, #0
        ADD R5, R5, #-1         ; con 1 solo negativo R5 queda en 0
        BRnp SGN_SET
        ADD R0, R0, #1          ; R0 = 1 -> resultado negativo
SGN_SET ST R0, SGN
        ; ---- separar |B| = BI*256 + BF (restas sucesivas de 256) ----
        ADD R3, R2, #0          ; R3 = resto (termina siendo BF)
        AND R4, R4, #0          ; R4 = BI
        LD R5, NEG256
DIV_B   ADD R2, R3, R5
        BRn FIN_B
        ADD R3, R2, #0
        ADD R4, R4, #1
        BRnzp DIV_B
FIN_B   ST R3, BF               ; BF (0..255)
        ; ---- fase 1: sumar |A|, BI veces ----
        AND R0, R0, #0          ; resultado = 0
        ADD R4, R4, #0
        BRz DIV_A
FASE1   ADD R0, R0, R1          ; resultado += |A|
        BRn ERR_DESB
        ADD R4, R4, #-1
        BRp FASE1
        ; ---- separar |A| = AI*256 + AF ----
DIV_A   ADD R3, R1, #0          ; R3 = resto (termina siendo AF)
        AND R4, R4, #0          ; R4 = AI
        LD R5, NEG256
DA_LOOP ADD R2, R3, R5
        BRn FIN_A
        ADD R3, R2, #0
        ADD R4, R4, #1
        BRnzp DA_LOOP
        ; ---- fase 2: sumar |A|/256, BF veces ----
FIN_A   AND R5, R5, #0          ; R5 = acumulador de fracciones
        LD R1, BF               ; R1 = contador (|A| ya no hace falta)
        BRz FIN_M
FASE2   ADD R0, R0, R4          ; resultado += AI
        BRn ERR_DESB
        ADD R5, R5, R3          ; acumulador += AF
        LD R2, NEG256
        ADD R2, R5, R2          ; acumulador - 256
        BRn SIG
        ADD R5, R2, #0          ; acumulador -= 256
        ADD R0, R0, #1          ; acarreo: resultado += 1
        BRn ERR_DESB
SIG     ADD R1, R1, #-1
        BRp FASE2
        ; ---- signo y retorno ----
FIN_M   LD R1, SGN
        BRz VUELVE
        NOT R0, R0
        ADD R0, R0, #1          ; resultado negativo
VUELVE  LDR R1, R6, #0          ; restaurar R1..R5
        LDR R2, R6, #1
        LDR R3, R6, #2
        LDR R4, R6, #3
        LDR R5, R6, #4
        ADD R6, R6, #5
        RET
SGN     .BLKW #1                ; variables locales de MULT
BF      .BLKW #1

DECIMALES ST R7, GUARDA7
        LD R3, FRAC8
        AND R4, R4, #0
        ADD R4, R4, #4
FLOOP   ADD R1, R3, R3
        ADD R2, R1, R1
        ADD R2, R2, R2
        ADD R3, R2, R1
        AND R0, R0, #0
        LD R5, NEG256
FD      ADD R2, R3, R5
        BRn FIN_FD
        ADD R3, R2, #0
        ADD R0, R0, #1
        BRnzp FD
FIN_FD  LD R1, ASC_CERO
        ADD R0, R0, R1
        OUT
        ADD R4, R4, #-1
        BRp FLOOP
        LD R7, GUARDA7
        RET

IMPRIMIR ST R7, GUARDA7
        ADD R1, R0, #0
        AND R4, R4, #0
DIV     AND R2, R2, #0
RESTA   ADD R3, R1, #-10
        BRn FIN_DIV
        ADD R1, R3, #0
        ADD R2, R2, #1
        BRnzp RESTA
FIN_DIV LD R0, ASC_CERO
        ADD R0, R0, R1
        ADD R6, R6, #-1
        STR R0, R6, #0
        ADD R4, R4, #1
        ADD R5, R5, #-1
        ADD R1, R2, #0
        BRp DIV
        ADD R5, R5, #0
        BRp DIV
SACAR   LDR R0, R6, #0
        ADD R6, R6, #1
        OUT
        ADD R4, R4, #-1
        BRp SACAR
        LD R7, GUARDA7
        RET
        .END
