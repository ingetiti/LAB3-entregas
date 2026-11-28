; ===========================================================================
; Modulo potencia (archivo potencia.asm): trae POTENCIA y MULT juntas.
; Convencion de llamada del simulador:
;   R0, R1 = argumentos   R0 = resultado   R1..R5 y R6 se conservan
;   Los registros se guardan en la pila (R6) y se desapilan antes del RET.
;   R6 no se inicializa nunca: el simulador ya lo apunta a la pila de usuario.
; ===========================================================================

; ---------------------------------------------------------------------------
; POTENCIA - A^B por multiplicaciones sucesivas
;
;   Formatos: A en Q7.8 con signo / B entero con signo (NO Q7.8) / R0 en Q7.8
;   Entrada : R0 = A
;             R1 = B
;   Salida  : R0 = A^B (Q7.8)
;             R0 = x8000 si hubo error (-128.00 nunca es un resultado valido).
;             La causa se deduce del signo de B:
;                B < 0  -> exponente negativo (no soportado)
;                B = 0  -> indeterminacion 0^0
;                B > 0  -> overflow (el resultado no entra en Q7.8)
;   Conserva: R1..R5 y R6 (R7 se apila porque se llama a MULT)
;   Metodo  : R0 = A; luego (B-1) veces R0 = R0 * A con MULT, que a su vez
;             multiplica por suma sucesiva. Si MULT devuelve x8000, se corta.
;   Casos   : B = 0 y A = 0 -> error     B = 0 y A <> 0 -> 1.00
;             A = 0 y B > 0 -> 0         B < 0 -> error
; ---------------------------------------------------------------------------
Mul_Sucesiva_POW:               ADD R6,R6,#-8                ; apilar R1, R2, R3 y R7
                                STW R1,R6,#0
                                STW R2,R6,#2
                                STW R3,R6,#4
                                STW R7,R6,#6                 ; R7 se pisa con el JSR MULT

                                MOV R3,R1                    ; R3 = B (cuenta las multiplicaciones)
                                MOV R1,R0                    ; R1 = A (MULT preserva R1)
                                ADD R3,R3,#0
                                BRN POT_ERR                  ; exponente negativo
                                BRP POT_POS
                                ADD R0,R0,#0                 ; B = 0
                                BRZ POT_ERR                  ; 0^0
                                LD R0,POT_UNO                ; A^0 = 1.00
                                BRNZP POT_FIN
POT_POS:                        ADD R0,R0,#0
                                BRZ POT_FIN                  ; 0^B = 0 (R0 ya vale 0)
                                ADD R3,R3,#-1                ; B-1 multiplicaciones restantes
                                BRZ POT_FIN                  ; B = 1 -> R0 = A
POT_BUC:                        JSR MULT                     ; R0 = R0 * R1  (acumulado * A)
                                LD R2,POT_ERRQ
                                ADD R2,R0,R2                 ; 0 solo si R0 = x8000
                                BRZ POT_FIN                  ; desborde: R0 ya es el codigo de error
                                ADD R3,R3,#-1
                                BRP POT_BUC
                                BRNZP POT_FIN
POT_ERR:                        LD R0,POT_ERRQ

                ; R0 tiene la salida. Desapilamos en el mismo orden
POT_FIN:                        LDW R1,R6,#0
                                LDW R2,R6,#2
                                LDW R3,R6,#4
                                LDW R7,R6,#6
                                ADD R6,R6,#8                 ; R6 vuelve a su valor de entrada
                                RET

POT_UNO:                        .FILL x0100                  ; 1.00 en Q7.8
POT_ERRQ:                       .FILL x8000                  ; codigo de error


; ---------------------------------------------------------------------------
; MULT - Multiplicacion Q7.8 con signo, por sumas sucesivas
;
;   Formatos: A, B y R0 en Q7.8 con signo
;   Entrada : R0 = A
;             R1 = B
;   Salida  : R0 = A*B (truncado hacia cero)
;             R0 = x8000 si el resultado no entra en Q7.8 (desborde); no se
;             hace HALT. Ningun resultado valido vale x8000 (el maximo en
;             modulo es x7FFF), asi que sirve de codigo de error.
;   Conserva: R1..R5 y R6 (tambien en caso de desborde). No hay JSR/TRAP,
;             asi que R7 tampoco se modifica.
;
;   Metodo (todo con sumas, sin multiplicar):
;     |B| = BI + BF/256   (BI = parte entera, BF = parte fraccionaria)
;     |A|*|B| = |A| sumado BI veces            -> fase 1
;             + (|A|/256) sumado BF veces      -> fase 2
;     con |A|/256 = AI + AF/256: cada suma de la fase 2 agrega AI al
;     resultado y AF a un acumulador que "acarrea" 1 al llegar a 256.
;     Asi nunca se necesita un valor mayor a 16 bits.
; ---------------------------------------------------------------------------
MULT:                           ADD R6,R6,#-10               ; apilar R1..R5
                                STW R1,R6,#0
                                STW R2,R6,#2
                                STW R3,R6,#4
                                STW R4,R6,#6
                                STW R5,R6,#8

                                MOV R2,R1                    ; R2 = B
                                MOV R1,R0                    ; R1 = A

                ; ---- signos y valores absolutos ----
                                MOVI R5,#0                   ; R5 = cantidad de operandos negativos
                                ADD R1,R1,#0
                                BRZP MULT_A_POS
                                NEG R1,R1                    ; R1 = |A|
                                BRN MULT_DESB                ; x8000 no tiene opuesto en 16 bits
                                ADD R5,R5,#1
MULT_A_POS:                     ADD R2,R2,#0
                                BRZP MULT_B_POS
                                NEG R2,R2                    ; R2 = |B|
                                BRN MULT_DESB
                                ADD R5,R5,#1
MULT_B_POS:                     MOVI R0,#0
                                ADD R5,R5,#-1                ; con 1 solo negativo R5 queda en 0
                                BRNP MULT_SGN_SET
                                ADD R0,R0,#1                 ; R0 = 1 -> resultado negativo
MULT_SGN_SET:                   ST R0,MULT_SGN

                ; ---- separar |B| = BI*256 + BF (restas sucesivas de 256) ----
                                MOV R3,R2                    ; R3 = resto (termina siendo BF)
                                MOVI R4,#0                   ; R4 = BI
                                LD R5,MULT_NEG256
MULT_DIV_B:                     ADD R2,R3,R5
                                BRN MULT_FIN_B
                                MOV R3,R2
                                ADD R4,R4,#1
                                BRNZP MULT_DIV_B
MULT_FIN_B:                     ST R3,MULT_BF                ; BF (0..255)

                ; ---- fase 1: sumar |A|, BI veces ----
                                MOVI R0,#0                   ; R0 = acumulador del resultado
                                ADD R4,R4,#0
                                BRZ MULT_DIV_A
MULT_FASE1:                     ADD R0,R0,R1                 ; resultado += |A|
                                BRN MULT_DESB
                                ADD R4,R4,#-1
                                BRP MULT_FASE1

                ; ---- separar |A| = AI*256 + AF ----
MULT_DIV_A:                     MOV R3,R1                    ; R3 = resto (termina siendo AF)
                                MOVI R4,#0                   ; R4 = AI
                                LD R5,MULT_NEG256
MULT_DA_LOOP:                   ADD R2,R3,R5
                                BRN MULT_FIN_A
                                MOV R3,R2
                                ADD R4,R4,#1
                                BRNZP MULT_DA_LOOP

                ; ---- fase 2: sumar |A|/256, BF veces ----
MULT_FIN_A:                     MOVI R5,#0                   ; R5 = acumulador de fracciones
                                LD R1,MULT_BF                ; R1 = contador (|A| ya no hace falta)
                                BRZ MULT_FIN_M
MULT_FASE2:                     ADD R0,R0,R4                 ; resultado += AI
                                BRN MULT_DESB
                                ADD R5,R5,R3                 ; acumulador += AF
                                LD R2,MULT_NEG256
                                ADD R2,R5,R2                 ; acumulador - 256
                                BRN MULT_SIG
                                MOV R5,R2                    ; acumulador -= 256
                                ADD R0,R0,#1                 ; acarreo: resultado += 1
                                BRN MULT_DESB
MULT_SIG:                       ADD R1,R1,#-1
                                BRP MULT_FASE2

                ; ---- signo ----
MULT_FIN_M:                     LD R1,MULT_SGN
                                BRZ MULT_VUELVE
                                NEG R0,R0                    ; resultado negativo
                                BRNZP MULT_VUELVE

                ; ---- desborde: R0 = x8000 y se vuelve desapilando todo ----
MULT_DESB:                      LD R0,MULT_ERRQ

                ; R0 tiene la salida. Desapilamos en el mismo orden
MULT_VUELVE:                    LDW R1,R6,#0
                                LDW R2,R6,#2
                                LDW R3,R6,#4
                                LDW R4,R6,#6
                                LDW R5,R6,#8
                                ADD R6,R6,#10                ; R6 vuelve a su valor de entrada
                                RET

MULT_NEG256:                    .FILL #-256
MULT_ERRQ:                      .FILL x8000                  ; codigo de error (desborde)
MULT_SGN:                       .FILL #0                     ; 1 si el resultado es negativo
MULT_BF:                        .FILL #0                     ; parte fraccionaria de |B|

.END
