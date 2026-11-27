; ====================================================================
; booth.asm - Modulo "booth": multiplicador Booth 16x16 en Q7.8       (LC10)
; Funcion publica: MULT_BOOTH      (se importa como G18_BOOTH-MULT_BOOTH)
;
; Es el mismo algoritmo del modulo LC-3 (bucle de Booth de 16 vueltas con A, Q y
; Q-1, extension E del acumulador y producto reducido P[23:8]). Lo que cambia es
; que el desplazamiento a la derecha de 1 bit (SHR1/ASR1, que en la LC-3 era un
; lazo de 16 vueltas por cada llamada) es ahora SAR + RCR, y que P >> 8 es
; SHR + SHL + OR en lugar de ocho desplazamientos de 32 bits.
;
; CONVENCION DE LLAMADA
; Entrada : R0 = X, primer operando  (Q7.8, 16 bits con signo)
;           R1 = Y, segundo operando (Q7.8, 16 bits con signo)
; Salida  : R0 = P[23:8]  (producto reducido a Q7.8)
; Conserva: R1 a R5 y R7 (se apilan y se restauran); R6 vuelve con su valor
; CC      : al retornar reflejan el signo de R0
; (Se quitaron las palabras de diagnostico PH, PL, RES y OVFV del original: nadie
; las lee. El modulo es reentrante.)
;
; Registros: R1 = M (multiplicando)   R2 = Q-1   R4 = A   R5 = Q
;            R7 = contador (-16 a 0)  R0, R3 = temporales
;
; Extension E del original: si A' = A +/- M (16 bits) es negativo y distinto de
; x8000, E = 1; si no, E = 0. El nuevo A es {E, A'[15:1]}: es un SAR, salvo que
; con A' = x8000 el original pone E = 0 (entonces es un SHR).
; ====================================================================

MULT_BOOTH
                        PUSH  R1-R5, R7                 ; marco de 6 palabras (R1 en R6+0 ... R7 en R6+10)

                        MOV   R5, R1                    ; Q <- Y
                        MOV   R1, R0                    ; M <- X
                        CLR   R4                        ; A <- 0
                        CLR   R2                        ; Q-1 <- 0
                        MOVI  R7, #-16                  ; 16 vueltas

BOOTH
                        AND   R0, R5, #1                ; q0
                        CMP   R2, R0                    ; d = Q-1 - q0
                        BRz   SINSUM                    ; d = 0
                        BRNC  RESTA                     ; d = -1
                        ADD   R4, R4, R1                ; d = +1: A <- A + M
                        BR    SINSUM
RESTA                   SUB   R4, R4, R1                ; d = -1: A <- A - M
SINSUM
                        MOV   R2, R0                    ; Q-1 <- q0
                        ADD   R3, R4, R4                ; cero con acarreo <=> A' = x8000
                        BRnp  NORMAL
                        BRNC  NORMAL
                        SHR   R4, R4, #1                ; A' = x8000: E = 0
                        BR    ROTAR
NORMAL                  SAR   R4, R4, #1                ; A <- {E, A'[15:1]}, C = A'[0]
ROTAR                   RCR   R5, R5                    ; Q <- {A'[0], Q[15:1]}
                        ADD   R7, R7, #1
                        BRn   BOOTH

; P = A:Q; RES = P[23:8] = (Q >> 8) | (A << 8)
                        SHR   R0, R5, #8
                        SHL   R3, R4, #8
                        OR    R0, R0, R3

                        POP   R1-R5, R7
                        TST   R0                        ; CC <- signo del resultado
                        RET

.END
