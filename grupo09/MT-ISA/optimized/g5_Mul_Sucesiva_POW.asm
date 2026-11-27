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
;   Metodo  : R0 = A; luego (B-1) veces R0 = R0 * A con MULT.
;             Si MULT devuelve x8000, se corta.
;   Casos   : B = 0 y A = 0 -> error     B = 0 y A <> 0 -> 1.00
;             A = 0 y B > 0 -> 0         B < 0 -> error
; ---------------------------------------------------------------------------
Mul_Sucesiva_POW ADD R6, R6, #-8         ; apilar R1, R2, R3 y R7
                 STR R1, R6, #0
                 STR R2, R6, #1
                 STR R3, R6, #2
                 STR R7, R6, #3          ; R7 se pisa con el JSR MULT

                 ADD R3, R1, #0          ; R3 = B (cuenta las multiplicaciones)
                 ADD R1, R0, #0          ; R1 = A (MULT preserva R1)
                 ADD R3, R3, #0
                 BRn POT_ERR             ; exponente negativo
                 BRp POT_POS
                 ADD R0, R0, #0          ; B = 0
                 BRz POT_ERR             ; 0^0
                 LD R0, POT_UNO          ; A^0 = 1.00
                 BRnzp POT_FIN
POT_POS          ADD R0, R0, #0
                 BRz POT_FIN             ; 0^B = 0 (R0 ya vale 0)
                 ADD R3, R3, #-1         ; B-1 multiplicaciones restantes
                 BRz POT_FIN             ; B = 1 -> R0 = A
POT_BUC          JSR MULT                ; R0 = R0 * R1  (acumulado * A)
                 LD R2, POT_ERRQ
                 ADD R2, R0, R2          ; 0 solo si R0 = x8000
                 BRz POT_FIN             ; desborde: R0 ya es el codigo de error
                 ADD R3, R3, #-1
                 BRp POT_BUC
                 BRnzp POT_FIN
POT_ERR          LD R0, POT_ERRQ

                ; R0 tiene la salida. Desapilamos en el mismo orden
POT_FIN          LDR R1, R6, #0
                 LDR R2, R6, #1
                 LDR R3, R6, #2
                 LDR R7, R6, #3
                 ADD R6, R6, #8          ; R6 vuelve a su valor de entrada
                 RET

POT_UNO          .FILL x0100             ; 1.00 en Q7.8
POT_ERRQ         .FILL x8000             ; codigo de error


; ---------------------------------------------------------------------------
; MULT - Multiplicación Q7.8 con signo
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
;   El producto completo ocupa R3:R2. Sumar 255 a un producto negativo
;   hace que el desplazamiento de ocho bits trunque hacia cero. Se verifica
;   que la mitad alta sea la extensión de signo de la mitad baja.
; ---------------------------------------------------------------------------
MULT
                ADD R6, R6, #-4
                STR R2, R6, #0
                STR R3, R6, #1
                LD R2, MULT_ERRQ
                ADD R3, R0, R2
                BRz MULT_DESB
                ADD R3, R1, R2
                BRz MULT_DESB
                MULW R2, R0, R1
                BRzp MULT_ESCALA
                LD R0, MULT_BIAS
                ADD R2, R2, R0
                AND R0, R0, #0
                ADC R3, R3, R0
MULT_ESCALA     ASRW R2, R2, #8
                ASR R0, R2, #15
                SUB R0, R3, R0
                BRnp MULT_DESB
                LD R0, MULT_ERRQ
                ADD R0, R2, R0
                BRz MULT_DESB
                ADD R0, R2, #0
                BR MULT_VUELVE
MULT_DESB       LD R0, MULT_ERRQ
MULT_VUELVE     LDR R2, R6, #0
                LDR R3, R6, #1
                ADD R6, R6, #4
                RET
MULT_BIAS       .FILL #255
MULT_ERRQ       .FILL x8000
                .END
