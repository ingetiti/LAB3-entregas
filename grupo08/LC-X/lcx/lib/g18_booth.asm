;====================================================================
; booth.asm - Modulo "booth": multiplicador Booth 16x16 en Q7.8 (LC-X)
; Funcion publica: MULT_BOOTH
;
; El mismo algoritmo que el original: 16 pasos de Booth de base 2 sobre
; A:Q:Q-1. En cada paso, segun q0 y Q-1, se suma o se resta M a A, y
; despues A:Q:Q-1 se corre un bit a la derecha (aritmetico). Las
; instrucciones de LC-X hacen cada corrimiento en un paso, en lugar de
; las subrutinas SHR1/ASR1 bit por bit.
;
; CONVENCION DE LLAMADA (igual que la version LC-3)
;   Entrada : R0 = X, primer operando  (Q7.8, 16 bits con signo)
;             R1 = Y, segundo operando (Q7.8, 16 bits con signo)
;   Salida  : R0 = RES = P[23:8]       (producto reducido a Q7.8)
;   Conserva: R1-R7
;   CC      : al retornar reflejan el signo de RES.
;
; A puede necesitar 17 bits (con M = x8000). Su signo verdadero es N
; salvo que la suma o la resta haya desbordado (V), y entonces es el
; contrario: eso es la extension E del original.
;====================================================================

MULT_BOOTH
        PUSH  R1, R2, R3, R4, R5, R7
        ADD   R2, R0, #0        ; R2 = M (multiplicando)
        AND   R3, R3, #0        ; R3 = A = 0          (R1 = Q = Y)
        AND   R4, R4, #0        ; R4 = Q-1 = 0
        MOVI  R5, #16           ; 16 pasos
        MOVI  R7, #1
        LSHF  R7, R7, #15       ; R7 = x8000

;---------------- bucle de Booth: 16 pasos ----------------
BOOTH   AND   R0, R1, #1        ; R0 = q0
        SUB   R4, R4, R0        ; d = Q-1 - q0
        BRz   CORRE             ; d = 0: ni suma ni resta
        BRn   RESTA             ; d = -1: A = A - M
        ADD   R3, R3, R2        ; d = +1: A = A + M
SIGNO   BRV   DESBORDE          ; el signo de A es el contrario de su bit 15
CORRE   ADD   R4, R0, #0        ; Q-1 = q0
        LSHF  R0, R3, #15       ; bit 0 de A, que pasa al bit 15 de Q
        RSHFA R3, R3, #1        ; A = A >> 1 (aritmetico)
DESPLAZA_Q
        RSHFL R1, R1, #1
        OR    R1, R1, R0        ; Q = {a0, Q[15:1]}
        LOOP  R5, BOOTH

;---------------- Q7.8: RES = P[23:8], con P = A:Q ----------------
        LSHF  R0, R3, #8
        RSHFL R1, R1, #8
        OR    R0, R0, R1        ; CC <- signo de RES
        POPR  R1, R2, R3, R4, R5, R7

RESTA   SUB   R3, R3, R2
        BR    SIGNO
DESBORDE                        ; extension E = NOT bit 15 de A
        ADD   R4, R0, #0        ; Q-1 = q0
        LSHF  R0, R3, #15
        RSHFA R3, R3, #1
        XOR   R3, R3, R7        ; el bit que entra es E, no el bit 15
        BR    DESPLAZA_Q

        .END
