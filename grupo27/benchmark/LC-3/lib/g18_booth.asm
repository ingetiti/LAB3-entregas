;====================================================================
; booth.asm - Modulo "booth": multiplicador Booth 16x16 en Q7.8
; Funcion publica: MULT_BOOTH      (se importa como BOOTH-MULT_BOOTH)
;
; Derivado de BOOTH16v3.ASM. El algoritmo (bucle de Booth, extension E,
; SHR1/ASR1, conversion P>>8 y calculo de OVF) es el mismo del original.
; Solo se cambio la interfaz: sin teclado ni pantalla, sin TRAP, sin
; HALT, sin .ORIG, y con la convencion de llamada de la calculadora.
;
; CONVENCION DE LLAMADA
;   Entrada : R0 = X, primer operando  (Q7.8, 16 bits con signo)
;             R1 = Y, segundo operando (Q7.8, 16 bits con signo)
;   Salida  : R0 = RES = P[23:8]       (producto reducido a Q7.8)
;   Conserva: R1, R2, R3, R4, R5 (se apilan y se restauran)
;             R6 vuelve con el mismo valor que tenia al entrar
;             R7 se apila al entrar y se restaura antes de RET
;   Destruye: R0 (es el resultado)
;   CC      : al retornar reflejan el signo de RES (ultimo LD es R0).
;
; PILA (R6 crece hacia direcciones menores). Marco de 7 palabras:
;     R6+0 = R1   R6+1 = R2   R6+2 = R3   R6+3 = R4
;     R6+4 = R5   R6+5 = R7   R6+6 = CNT (contador del bucle)
;   CNT reemplaza al uso de R6 como contador del original, porque R6 es
;   ahora el puntero de pila. R6 solo se usa como base de STR/LDR y para
;   reservar/liberar el marco; nunca se inicializa ni se usa como
;   registro de trabajo. Al retornar no queda nada apilado.
;
; R7: se apila al entrar porque las JSR internas (SHR1/ASR1) lo
;   sobrescriben; el RET final usa el R7 original restaurado.
;
; DATOS AUXILIARES (solo diagnostico; NO forman parte de la interfaz):
;   PH   = palabra alta del producto de 32 bits (Q15.16)
;   PL   = palabra baja del producto de 32 bits
;   RES  = copia de P[23:8]
;   OVFV = 0 sin desbordamiento, 1 si PH esta fuera de [-128,127]
;          (con OVFV = 1 el valor de R0 no representa el producto)
;   El programa principal de la calculadora no necesita leerlos.
;   Son datos del modulo, por lo tanto NO es reentrante.
;
; ENLAZADOR: sin .ORIG, sin direcciones absolutas, todo es relativo al
;   PC dentro de este archivo. Las JSR a SHR1/ASR1 son internas y
;   cortas. Ninguna etiqueta contiene '-'.
;====================================================================

MULT_BOOTH
        ADD  R6, R6, #-7        ; reservar marco en la pila
        STR  R1, R6, #0         ; apilar R1..R5 y R7
        STR  R2, R6, #1
        STR  R3, R6, #2
        STR  R4, R6, #3
        STR  R5, R6, #4
        STR  R7, R6, #5

        ST   R0, MCAND          ; M <- X
        ADD  R5, R1, #0         ; Q <- Y
        NOT  R1, R0
        ADD  R1, R1, #1         ; MNEG = NOT(M) + 1  (mod 2^16)
        ST   R1, MNEG
        AND  R4, R4, #0         ; A <- 0
        AND  R0, R0, #0
        ST   R0, QM1            ; QM1 <- 0
        ADD  R0, R0, #-16
        STR  R0, R6, #6         ; CNT <- -16 (en la pila)

;---------------- bucle de Booth: 16 iteraciones (sin cambios) ----------------
BOOTH   AND  R0, R5, #1         ; R0 = q0 = Q[0]
        ST   R0, Q0SAVE
        NOT  R0, R0
        ADD  R0, R0, #1         ; R0 = -q0
        LD   R1, QM1
        ADD  R0, R0, R1         ; R0 = QM1 - q0 ; CC <- signo de d
        BRz  SINSUM             ; d = 0
        BRn  RESTA              ; d = -1  (BR no altera CC: el 2.o BR ve el mismo CC)
        LD   R1, MCAND          ; d = +1 : A <- A + M
        ADD  R4, R4, R1
        BRnzp SINSUM
RESTA   LD   R1, MNEG           ; d = -1 : A <- A - M = A + MNEG
        ADD  R4, R4, R1
;   aqui R4 = patron de A' (acumulador antes de desplazar)
SINSUM  AND  R3, R4, #1         ; a0 = A'[0]
        NOT  R3, R3
        ADD  R3, R3, #1         ; R3 = -a0 : negativo <=> a0 = 1
        ADD  R0, R5, #0         ; X = Q
        JSR  SHR1               ; R0 = {a0, Q[15:1]}
        ADD  R5, R0, #0         ; Q <- R0
;   extension E de A'
        ADD  R0, R4, #0         ; X = A'
        ADD  R3, R4, #0         ; R3 = A' ; CC <- signo de A'
        BRzp ECERO              ; A' >= 0 -> E = 0
        ADD  R1, R4, R4         ; con A' < 0: A'+A' = 0  <=>  A' = x8000
        BRnp ECUNO              ; distinto de x8000 -> E = 1 (R3 = A' es negativo)
ECERO   AND  R3, R3, #0         ; E = 0 (A' >= 0, o A' = x8000)
ECUNO   JSR  SHR1               ; R0 = {E, A'[15:1]}
        ADD  R4, R0, #0         ; A <- R0
        LD   R0, Q0SAVE
        ST   R0, QM1            ; QM1 <- q0 anterior
        LDR  R0, R6, #6
        ADD  R0, R0, #1         ; CNT <- CNT + 1 ; CC <- CNT
        STR  R0, R6, #6         ; (STR no altera CC)
        BRn  BOOTH              ; repite mientras CNT < 0 (16 vueltas)

;---------------- producto bruto: PH:PL = A:Q ----------------
        ST   R4, PH
        ST   R5, PL

;---------------- Q7.8: RES = P[23:8] = P >>a 8 ----------------
;   8 veces: {R4:R5} <- {R4:R5} >>a 1   (R4 = hi, R5 = lo)
;   R4:R5 se destruye; el producto sigue en PH/PL
        AND  R0, R0, #0
        ADD  R0, R0, #-8
        STR  R0, R6, #6         ; CNT <- -8
CONV    AND  R3, R4, #1         ; hi[0]
        NOT  R3, R3
        ADD  R3, R3, #1         ; R3 = -hi[0] : negativo <=> hi[0] = 1
        ADD  R0, R5, #0         ; X = lo
        JSR  SHR1               ; R0 = {hi[0], lo[15:1]}
        ADD  R5, R0, #0         ; lo <- R0
        ADD  R0, R4, #0         ; X = hi
        JSR  ASR1               ; R0 = hi >>a 1  (relleno = signo de hi)
        ADD  R4, R0, #0         ; hi <- R0
        LDR  R0, R6, #6
        ADD  R0, R0, #1         ; CNT <- CNT + 1 ; CC <- CNT
        STR  R0, R6, #6
        BRn  CONV               ; 8 vueltas
        ST   R5, RES            ; RES = lo = P[23:8]

;---------------- OVF = ((PH + x0080) AND xFF00) != 0 ----------------
        LD   R0, PH
        LD   R1, C0080
        ADD  R0, R0, R1         ; PH + 128
        LD   R1, CFF00
        AND  R0, R0, R1         ; byte alto de (PH + 128) ; CC
        BRz  GOVF               ; 0 -> OVF = 0 (R0 ya vale 0)
        AND  R0, R0, #0
        ADD  R0, R0, #1         ; OVF = 1
GOVF    ST   R0, OVFV

;---------------- epilogo: restaurar registros y volver ----------------
        LDR  R1, R6, #0         ; desapilar en el mismo orden
        LDR  R2, R6, #1
        LDR  R3, R6, #2
        LDR  R4, R6, #3
        LDR  R5, R6, #4
        LDR  R7, R6, #5         ; direccion de retorno original
        ADD  R6, R6, #7         ; R6 vuelve a su valor de entrada
        LD   R0, RES            ; R0 = RES (salida) ; CC <- signo de RES
        RET

;---------------- datos del modulo ----------------
;   diagnostico (no forman parte de la interfaz)
PH      .FILL x0000
PL      .FILL x0000
RES     .FILL x0000
OVFV    .FILL x0000
;   internos del algoritmo
MCAND   .FILL x0000
MNEG    .FILL x0000
QM1     .FILL x0000
Q0SAVE  .FILL x0000
C0080   .FILL x0080
CFF00   .FILL xFF00
C8000   .FILL x8000

;---------------- SHR1 / ASR1 (de SHR1 del original; sin cambios) ----------------
;   Entrada: R0 = X ; R3 = relleno (negativo -> 1, cero -> 0).
;            ASR1 toma el relleno de X (R3 <- X), o sea desplazamiento aritmetico.
;   Salida : R0 = {relleno, X[15:1]}. Destruye R1, R2, R3 (R7 lo fija la JSR).
;   (LSR1 del original no se usa en Booth y se omitio.)
ASR1    ADD  R3, R0, #0
SHR1    ADD  R1, R0, #0         ; W <- X
        AND  R2, R2, #0
        ADD  R2, R2, #1         ; R <- 1 (centinela en bit 0)
SLAZO   ADD  R2, R2, R2         ; R <- 2R
        ADD  R1, R1, #0         ; CC <- signo de W (= bit 15)
        BRzp SNOBIT
        ADD  R2, R2, #1         ; bit 15 de W era 1
SNOBIT  ADD  R1, R1, R1         ; W <- 2W
        ADD  R2, R2, #0         ; CC <- signo de R (= centinela en bit 15?)
        BRzp SLAZO
        ADD  R3, R3, #0         ; CC <- relleno
        BRn  SFIN               ; relleno=1: el centinela ya es el bit 15
        LD   R3, C8000
        ADD  R2, R2, R3         ; relleno=0: borra el centinela
SFIN    ADD  R0, R2, #0
        RET                     ; vuelve por R7 (fijado por la JSR interna)

        .END
