; ===========================================================================
; MULT - Multiplicacion Q7.8 con signo, por sumas sucesivas (SUBRUTINA)
;
;   Entrada : R0 = A  (Q7.8 con signo, 16 bits)
;             R1 = B  (Q7.8 con signo, 16 bits)
;   Salida  : R0 = A*B (Q7.8 con signo, truncado hacia cero)
;   Registros: R1..R5 se guardan al entrar y se restauran antes del RET.
;              NO se usa R6 (ni pila). No hay JSR/TRAP en el camino normal,
;              asi que R7 tampoco se modifica.
;   Desborde : si |A*B| no entra en Q7.8 imprime un mensaje y hace HALT.
;
;   Metodo (todo con sumas, sin multiplicar):
;     |B| = BI + BF/256   (BI = parte entera, BF = parte fraccionaria)
;     |A|*|B| = |A| sumado BI veces            -> fase 1
;             + (|A|/256) sumado BF veces      -> fase 2
;     con |A|/256 = AI + AF/256: cada suma de la fase 2 agrega AI al
;     resultado y AF a un acumulador que "acarrea" 1 al llegar a 256.
;     Asi nunca se necesita un valor mayor a 16 bits.
;
;   Todas las etiquetas internas empiezan con MULT_ para no chocar con las
;   de otros archivos al adjuntarlos juntos en el simulador.
; ===========================================================================

MULT            ST R1, MULT_G1          ; guardar el estado inicial
                ST R2, MULT_G2
                ST R3, MULT_G3
                ST R4, MULT_G4
                ST R5, MULT_G5

                ADD R2, R1, #0          ; R2 = B
                ADD R1, R0, #0          ; R1 = A

                ; ---- signos y valores absolutos ----
                AND R5, R5, #0          ; R5 = cantidad de operandos negativos
                ADD R1, R1, #0
                BRzp MULT_A_POS
                NOT R1, R1
                ADD R1, R1, #1          ; R1 = |A|
                BRn MULT_DESB           ; x8000 no tiene opuesto en 16 bits
                ADD R5, R5, #1
MULT_A_POS      ADD R2, R2, #0
                BRzp MULT_B_POS
                NOT R2, R2
                ADD R2, R2, #1          ; R2 = |B|
                BRn MULT_DESB
                ADD R5, R5, #1
MULT_B_POS      AND R0, R0, #0
                ADD R5, R5, #-1         ; con 1 solo negativo R5 queda en 0
                BRnp MULT_SGN_SET
                ADD R0, R0, #1          ; R0 = 1 -> resultado negativo
MULT_SGN_SET    ST R0, MULT_SGN

                ; ---- separar |B| = BI*256 + BF (restas sucesivas de 256) ----
                ADD R3, R2, #0          ; R3 = resto (termina siendo BF)
                AND R4, R4, #0          ; R4 = BI
                LD R5, MULT_NEG256
MULT_DIV_B      ADD R2, R3, R5
                BRn MULT_FIN_B
                ADD R3, R2, #0
                ADD R4, R4, #1
                BRnzp MULT_DIV_B
MULT_FIN_B      ST R3, MULT_BF          ; BF (0..255)

                ; ---- fase 1: sumar |A|, BI veces ----
                AND R0, R0, #0          ; R0 = acumulador del resultado
                ADD R4, R4, #0
                BRz MULT_DIV_A
MULT_FASE1      ADD R0, R0, R1          ; resultado += |A|
                BRn MULT_DESB
                ADD R4, R4, #-1
                BRp MULT_FASE1

                ; ---- separar |A| = AI*256 + AF ----
MULT_DIV_A      ADD R3, R1, #0          ; R3 = resto (termina siendo AF)
                AND R4, R4, #0          ; R4 = AI
                LD R5, MULT_NEG256
MULT_DA_LOOP    ADD R2, R3, R5
                BRn MULT_FIN_A
                ADD R3, R2, #0
                ADD R4, R4, #1
                BRnzp MULT_DA_LOOP

                ; ---- fase 2: sumar |A|/256, BF veces ----
MULT_FIN_A      AND R5, R5, #0          ; R5 = acumulador de fracciones
                LD R1, MULT_BF          ; R1 = contador (|A| ya no hace falta)
                BRz MULT_FIN_M
MULT_FASE2      ADD R0, R0, R4          ; resultado += AI
                BRn MULT_DESB
                ADD R5, R5, R3          ; acumulador += AF
                LD R2, MULT_NEG256
                ADD R2, R5, R2          ; acumulador - 256
                BRn MULT_SIG
                ADD R5, R2, #0          ; acumulador -= 256
                ADD R0, R0, #1          ; acarreo: resultado += 1
                BRn MULT_DESB
MULT_SIG        ADD R1, R1, #-1
                BRp MULT_FASE2

                ; ---- signo ----
MULT_FIN_M      LD R1, MULT_SGN
                BRz MULT_VUELVE
                NOT R0, R0
                ADD R0, R0, #1          ; resultado negativo

                ; R0 ya tiene el resultado. Restauramos R1..R5 como entraron
MULT_VUELVE     LD R1, MULT_G1
                LD R2, MULT_G2
                LD R3, MULT_G3
                LD R4, MULT_G4
                LD R5, MULT_G5
                RET

                ; ---- desborde: el resultado no entra en Q7.8 ----
MULT_DESB       LEA R0, MULT_MSG_DESB
                PUTS
                HALT

                ; ---- ZONA DE DATOS ----
MULT_MSG_DESB   .STRINGZ "Error: fuera de rango Q7.8 (+-127.99)"
MULT_NEG256     .FILL #-256
MULT_SGN        .FILL #0                ; 1 si el resultado es negativo
MULT_BF         .FILL #0                ; parte fraccionaria de |B|
MULT_G1         .FILL #0                ; copias de R1..R5
MULT_G2         .FILL #0
MULT_G3         .FILL #0
MULT_G4         .FILL #0
MULT_G5         .FILL #0

.END                                    ; IMPORTANTE no olvidarse del .END
