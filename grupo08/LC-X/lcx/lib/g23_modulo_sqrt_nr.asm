; =====================================================================
; MODULO: modulo_sqrt_nr (Grupo 23) - SQRT por el metodo NON-RESTORING (LC-X)
; Arquitectura de Computadoras (IC221) - FI-UNaM - 2026
;
; Algoritmo digito a digito de Li y Chu (1996): obtiene un bit de la raiz
; por iteracion usando solo sumas, restas y corrimientos. k = 13
; iteraciones fijas, como el original. Con LC-X, MULW baja los 2 bits del
; radicando en un paso, y en vez de Q se guarda W = 4Q, el valor de
; prueba: el bit anterior es el signo de R, que ya decide el camino.
;
; Uso desde otro archivo (convencion de la plataforma):
;       .EXTERNAL G23_MODULO_SQRT_NR-SQRT_NR
;       LD   R5, PTR_SQRT
;       JSRR R5
;       ...
; PTR_SQRT .FILL G23_MODULO_SQRT_NR-SQRT_NR
;
; El .ORIG no hace falta: el enlazador ubica el modulo en memoria.
; =====================================================================

; ---------------------------------------------------------------------
; SQRT_NR: R0 = radicando x en Q7.8 (rango valido [0 ; 127,996])
;          devuelve R0 = raiz de x en Q6.9 (rango [0 ; 11,3145]),
;          redondeada al mas cercano (error maximo 1/2 LSB = 0,00098)
;          Si x < 0 devuelve R0 = x8000 (error: no hay raiz real).
; Registros: R1-R7 no se modifican (R6 vuelve con el mismo valor).
; Uso interno: R0 radicando (se corre a la izquierda), R1 contador,
;              R2 resto parcial R, R3 W = 4Q, R5 = 4, R7 par de bits.
; ---------------------------------------------------------------------
SQRT_NR     ADD   R0, R0, #0    ; C = 0
            BRn   SQ_NEG        ; x < 0 -> error, sin tocar la pila
            PUSH  R1, R2, R3, R5, R7
            MOVI  R1, #13       ; k = 13 iteraciones
            AND   R2, R2, #0    ; R = 0
            MOVI  R3, #-2       ; W: la primera vuelta deja 4Q = 0
            MOVI  R5, #4

; ---------- lazo: un bit de la raiz por iteracion ---------------------
; 1) R = 4R + par: MULW deja en R7 los 2 bits altos de R0 y corre R0.
SQ_LAZO     MULW  R7, R0, R5
            LSHF  R2, R2, #2
            ADD   R2, R2, R7    ; C = 0, N = signo de R
; 2) Paso non-restoring: si R >= 0, R = R - (4Q + 1); si no, R = R + (4Q + 3)
;    El bit anterior de Q es 1 si R >= 0: W = 2W + 4; si no, W = 2W.
            BRn   SQ_SUMA
            ADD   R3, R3, #2
            ADD   R3, R3, R3    ; W = 4Q, C = 0
            SBC   R2, R2, R3    ; R = R - W - 1
            LOOP  R1, SQ_LAZO
            BRn   SQ_FNEG
; ---------- R >= 0: Q = W/2 + 1; redondeo: si R > Q, Q = Q + 1 ---------
SQ_FPOS     ADD   R3, R3, #2
            RSHFL R3, R3, #1    ; R3 = Q, C = 0
            SBC   R7, R2, R3    ; C = (R - Q - 1 >= 0)
            ADC   R0, R3, #0
            POPR  R1, R2, R3, R5, R7

SQ_SUMA     ADD   R3, R3, R3    ; W = 4Q
            ADD   R2, R2, R3
            ADD   R2, R2, #3    ; R = R + W + 3
            LOOP  R1, SQ_LAZO
            BRzp  SQ_FPOS
; ---------- R < 0: Q = W/2; resto R + 2Q + 1 > Q si R + Q >= 0 ---------
SQ_FNEG     RSHFL R3, R3, #1    ; R3 = Q, C = 0
            ADD   R7, R2, R3    ; C = (R + Q >= 0)
            ADC   R0, R3, #0
            POPR  R1, R2, R3, R5, R7

SQ_NEG      LD    R0, SQ_ERR    ; R0 = x8000 (codigo de error)
            RET

; ---------- constantes ----------
SQ_ERR      .FILL x8000
            .END
