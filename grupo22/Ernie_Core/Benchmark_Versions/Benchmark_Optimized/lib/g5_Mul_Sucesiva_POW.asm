; ===========================================================================
; Modulo potencia (archivo g5_Mul_Sucesiva_POW.asm)           Grupo 5  [OPT]
; Convencion de llamada del simulador:
;   R0, R1 = argumentos   R0 = resultado   R1..R5 y R6 se conservan
;   Los registros se guardan en la pila (R6) y se desapilan antes del RET.
;   R6 no se inicializa nunca: el simulador ya lo apunta a la pila de usuario.
;
; OPTIMIZACION: la subrutina MULT (antes por sumas sucesivas) ahora usa MUL
; (parte baja) + MULH (parte alta) y reajuste de escala Q7.8 con LSL #4 / LSR #4
; (desplazar 8 bits; imm4 = 4 dentro de [-8,+7]). Se conserva el truncado hacia
; cero y la deteccion de overflow (|resultado| > 32767 o |operando| == 32768).
; POTENCIA (el bucle A^B) se mantiene identico: llama a MULT y corta si x8000.
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
;   Metodo  : R0 = A; luego (B-1) veces R0 = R0 * A con MULT (MUL+MULH). Si MULT
;             devuelve x8000, se corta.
; ---------------------------------------------------------------------------
Mul_Sucesiva_POW ADD R6, R6, #-8         ; apilar R1, R2, R3 y R7 (8 bytes)
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
                 ADD R6, R6, #7          ; R6 vuelve a su valor de entrada (8 bytes)
                 ADD R6, R6, #1          ; #8 no es codificable (sign-extend a -8)
                 RET

POT_UNO          .FILL x0100             ; 1.00 en Q7.8
POT_ERRQ         .FILL x8000             ; codigo de error


; ---------------------------------------------------------------------------
; MULT - Multiplicacion Q7.8 con signo (MUL + MULH)           [OPT]
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
;   Metodo (nativo):
;     |A|, |B| (si alguno es x8000 -> desborde, no tiene opuesto en 16 bits)
;     P = |A| * |B|  (32 bits): hi = MULH, lo = MUL
;     q = trunc(P / 256) = (hi << 8) | (lo >> 8)   [LSL#4 x2, LSR#4 x2]
;     overflow si hi >= 128 (q > 32767)  -> x8000
;     signo: neg si exactamente un operando es negativo.
; ---------------------------------------------------------------------------
MULT            ADD R6, R6, #-8         ; apilar R1..R5 (10 bytes)
                ADD R6, R6, #-2
                STR R1, R6, #0
                STR R2, R6, #1
                STR R3, R6, #2
                STR R4, R6, #3
                STR R5, R6, #4

                ; ---- signo y valores absolutos ----
                ADD  R2, R1, #0         ; R2 = B (segundo operando = R1 de entrada)
                ADD  R1, R0, #0         ; R1 = A (primer operando = R0 de entrada)
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
MULT_B_POS      ; R1 = |A|, R2 = |B| (0..32767)
                MULH R3, R1, R2         ; R3 = hi = P >> 16
                MUL  R4, R1, R2         ; R4 = lo = P & 0xFFFF
                LD   R0, MULT_MASK      ; 0xFF80
                AND  R0, R3, R0
                BRnp MULT_DESB          ; hi >= 128 -> q > 32767 -> overflow
                LSL  R3, R3, #4
                LSL  R3, R3, #4         ; R3 = hi << 8
                LSR  R4, R4, #4
                LSR  R4, R4, #4         ; R4 = lo >> 8
                ADD  R4, R4, R3         ; R4 = q = trunc(|A|*|B| / 256)
                ; ---- aplicar signo (negativo si R5 == 1) ----
                ADD  R0, R5, #-1
                BRz  MULT_NEG
                ADD  R0, R4, #0         ; resultado positivo
                BRnzp MULT_VUELVE
MULT_NEG        NOT  R4, R4
                ADD  R4, R4, #1
                ADD  R0, R4, #0         ; resultado negativo
                BRnzp MULT_VUELVE

MULT_DESB       LD   R0, MULT_ERRQ      ; x8000 (desborde)

MULT_VUELVE     LDR R1, R6, #0
                LDR R2, R6, #1
                LDR R3, R6, #2
                LDR R4, R6, #3
                LDR R5, R6, #4
                ADD R6, R6, #7          ; R6 vuelve a su valor de entrada (10 bytes)
                ADD R6, R6, #3
                RET

MULT_MASK       .FILL xFF80             ; mascara de overflow (hi >= 128)
MULT_ERRQ       .FILL x8000             ; codigo de error (desborde)

                .END