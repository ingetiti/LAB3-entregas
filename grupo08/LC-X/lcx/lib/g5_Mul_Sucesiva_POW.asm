; ===========================================================================
; Modulo potencia (archivo potencia.asm), version LC-X.
; Convencion de llamada del simulador:
;   R0, R1 = argumentos   R0 = resultado   R1..R5 y R6 se conservan
;   Los registros se guardan en la pila (R6) y se desapilan antes del RET.
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
;   Conserva: R1..R5, R6 y R7
;   Metodo  : acumulado = |A|; luego (B-1) veces acumulado = acumulado * |A|
;             (MULQ: producto Q7.8 truncado; V si no entra en Q7.8, y se
;             corta). El signo se pone al final: negativo si A < 0 y B impar.
;   Casos   : B = 0 y A = 0 -> error     B = 0 y A <> 0 -> 1.00
;             A = 0 y B > 0 -> 0         B < 0 -> error
; ---------------------------------------------------------------------------
Mul_Sucesiva_POW PUSH  R1, R2, R3
                 LSHF  R3, R1, #15       ; bit 15 = B impar
                 SUB   R1, R1, #1        ; R1 = B-1 multiplicaciones
                 BRnz  POT_CORTO         ; B <= 1
                 BRV   POT_ERR           ; B = x8000 (negativo)
                 ABS   R2, R0            ; R2 = |A|, V si A = x8000
                 BRV   POT_ERR           ; x8000 no tiene opuesto: desborde
                 BRz   POT_FIN           ; 0^B = 0
                 AND   R3, R3, R0        ; R3 < 0: A < 0 y B impar
                 ADD   R0, R2, #0        ; acumulado = |A|
POT_BUC          MULQ  R0, R2, #8        ; acumulado * |A|
                 BRV   POT_ERR           ; no entra en Q7.8
                 LOOP  R1, POT_BUC
                 ADD   R3, R3, #0
                 BRzp  POT_FIN
                 NEG   R0, R0            ; resultado negativo
POT_FIN          POPR  R1, R2, R3

POT_CORTO        BRz   POT_FIN           ; B = 1 -> R0 = A
                 ADD   R1, R1, #1        ; R1 = B
                 BRn   POT_ERR           ; exponente negativo
                 ADD   R0, R0, #0        ; B = 0
                 BRz   POT_ERR           ; 0^0
                 LD    R0, POT_UNO       ; A^0 = 1.00
                 POPR  R1, R2, R3
POT_ERR          LD    R0, POT_ERRQ      ; codigo de error
                 POPR  R1, R2, R3

POT_UNO          .FILL x0100             ; 1.00 en Q7.8
POT_ERRQ         .FILL x8000             ; codigo de error

                 .END
