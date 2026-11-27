
;====================================================================
; proyecto_completo.asm - VERSION INTEGRADA DE PRUEBA (un solo archivo)
; Programa principal + modulo Booth (MULT_BOOTH) + datos. Un solo .ORIG
; y un solo .END. NO es la entrega definitiva (esa es booth.asm).
;
; El principal recorre una tabla de casos, llama a MULT_BOOTH con
; LD/JSRR (igual que main.asm) y comprueba por caso:
;   R0 = RES esperado, PH, PL y OVFV esperados (datos auxiliares del
;   modulo), R1 = Y, R4 y R5 conservados, R6 igual que antes de llamar.
; Al terminar (HALT):  FALLAS = 0  -> todos los casos pasaron.
;   Cada fila de TABLA guarda a la derecha lo OBTENIDO (G_RES, G_PH,
;   G_PL, G_OVF) para inspeccionarlo en memoria.
; No inicializa R6. Si el simulador no lo apunta a una pila valida,
;   hay que apuntarlo a una zona libre antes de ejecutar.
;====================================================================
        .ORIG x3000

        LEA  R2, TABLA          ; R2 = fila actual (el modulo conserva R2)
        LD   R3, NCASOS_N       ; R3 = -NCASOS (el modulo conserva R3)
        AND  R0, R0, #0
        ST   R0, FALLAS
BUCLE   LDR  R0, R2, #0         ; R0 = X
        LDR  R1, R2, #1         ; R1 = Y
        LD   R4, CENT4          ; centinela en R4
        ST   R6, R6PRE          ; R6 antes de la llamada
        LD   R5, BOOTH_PTR      ; dir. del modulo (aqui es etiqueta local)
        JSRR R5
        STR  R0, R2, #6        ; G_RES  <- R0
        ST   R1, GR1            ; registros tal como volvieron
        ST   R4, GR4
        ST   R5, GR5
        ST   R6, GR6
        LD   R0, PH             ; datos auxiliares del modulo
        STR  R0, R2, #7        ; G_PH
        LD   R0, PL
        STR  R0, R2, #8        ; G_PL
        LD   R0, OVFV
        STR  R0, R2, #9        ; G_OVF
        LDR  R0, R2, #6        ; --- comparaciones (JSR CHK: R0=obtenido, R1=esperado)
        LDR  R1, R2, #4         ; RES
        JSR  CHK
        LDR  R0, R2, #7
        LDR  R1, R2, #2         ; PH
        JSR  CHK
        LDR  R0, R2, #8
        LDR  R1, R2, #3         ; PL
        JSR  CHK
        LDR  R0, R2, #9
        LDR  R1, R2, #5         ; OVF
        JSR  CHK
        LD   R0, GR1
        LDR  R1, R2, #1         ; R1 debe seguir valiendo Y
        JSR  CHK
        LD   R0, GR4
        LD   R1, CENT4          ; R4 conservado
        JSR  CHK
        LD   R0, GR5
        LD   R1, BOOTH_PTR      ; R5 conservado
        JSR  CHK
        LD   R0, GR6
        LD   R1, R6PRE          ; R6 igual que a la entrada
        JSR  CHK
        ADD  R2, R2, #10        ; siguiente fila (10 palabras)
        ADD  R3, R3, #1
        BRn  BUCLE
        HALT                    ; fin del PROGRAMA PRINCIPAL

; CHK: R0 = obtenido, R1 = esperado. Si difieren, FALLAS <- FALLAS + 1.
CHK     NOT  R1, R1
        ADD  R1, R1, #1
        ADD  R0, R0, R1
        BRz  CHKOK
        LD   R0, FALLAS
        ADD  R0, R0, #1
        ST   R0, FALLAS
CHKOK   RET

FALLAS    .FILL x0000           ; cantidad de comprobaciones fallidas
NCASOS_N  .FILL #-13            ; -(cantidad de casos)
CENT4     .FILL xA4A4
R6PRE     .FILL x0000
GR1       .FILL x0000
GR4       .FILL x0000
GR5       .FILL x0000
GR6       .FILL x0000
BOOTH_PTR .FILL MULT_BOOTH      ; en el archivo unico basta la etiqueta local

; ===================== MODULO BOOTH (identico a booth.asm) =====================
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


; ===================== TABLA DE CASOS =====================
; fila (10 palabras) = X, Y, PH, PL, RES, OVF | obtenidos: G_RES, G_PH, G_PL, G_OVF
; (las 4 ultimas palabras se llenan al ejecutar)
TABLA
        .FILL x0C80                ; 12.5 x 3.75
        .FILL x03C0
        .FILL x002E
        .FILL xE000
        .FILL x2EE0
        .FILL x0000
        .FILL x0000
        .FILL x0000
        .FILL x0000
        .FILL x0000
        .FILL x0100                ; 1 x 2
        .FILL x0200
        .FILL x0002
        .FILL x0000
        .FILL x0200
        .FILL x0000
        .FILL x0000
        .FILL x0000
        .FILL x0000
        .FILL x0000
        .FILL xFC40                ; -3.75 x 2
        .FILL x0200
        .FILL xFFF8
        .FILL x8000
        .FILL xF880
        .FILL x0000
        .FILL x0000
        .FILL x0000
        .FILL x0000
        .FILL x0000
        .FILL x0000                ; 0 x 5
        .FILL x0500
        .FILL x0000
        .FILL x0000
        .FILL x0000
        .FILL x0000
        .FILL x0000
        .FILL x0000
        .FILL x0000
        .FILL x0000
        .FILL x6400                ; 100 x 2 (OVF)
        .FILL x0200
        .FILL x00C8
        .FILL x0000
        .FILL xC800
        .FILL x0001
        .FILL x0000
        .FILL x0000
        .FILL x0000
        .FILL x0000
        .FILL x9C00                ; -100 x 2 (OVF)
        .FILL x0200
        .FILL xFF38
        .FILL x0000
        .FILL x3800
        .FILL x0001
        .FILL x0000
        .FILL x0000
        .FILL x0000
        .FILL x0000
        .FILL xFC40                ; -3.75 x -2
        .FILL xFE00
        .FILL x0007
        .FILL x8000
        .FILL x0780
        .FILL x0000
        .FILL x0000
        .FILL x0000
        .FILL x0000
        .FILL x0000
        .FILL x4000                ; 64 x 2 (OVF, limite)
        .FILL x0200
        .FILL x0080
        .FILL x0000
        .FILL x8000
        .FILL x0001
        .FILL x0000
        .FILL x0000
        .FILL x0000
        .FILL x0000
        .FILL x8000                ; -128 x 1 (limite)
        .FILL x0100
        .FILL xFF80
        .FILL x0000
        .FILL x8000
        .FILL x0000
        .FILL x0000
        .FILL x0000
        .FILL x0000
        .FILL x0000
        .FILL x8000                ; -128 x -128 (OVF)
        .FILL x8000
        .FILL x4000
        .FILL x0000
        .FILL x0000
        .FILL x0001
        .FILL x0000
        .FILL x0000
        .FILL x0000
        .FILL x0000
        .FILL x7FFF                ; 127.996 x 1
        .FILL x0100
        .FILL x007F
        .FILL xFF00
        .FILL x7FFF
        .FILL x0000
        .FILL x0000
        .FILL x0000
        .FILL x0000
        .FILL x0000
        .FILL x0080                ; 0.5 x 0.5
        .FILL x0080
        .FILL x0000
        .FILL x4000
        .FILL x0040
        .FILL x0000
        .FILL x0000
        .FILL x0000
        .FILL x0000
        .FILL x0000
        .FILL xFFFF                ; -1/256 x 1/256 (trunca)
        .FILL x0001
        .FILL xFFFF
        .FILL xFFFF
        .FILL xFFFF
        .FILL x0000
        .FILL x0000
        .FILL x0000
        .FILL x0000
        .FILL x0000

        .END
