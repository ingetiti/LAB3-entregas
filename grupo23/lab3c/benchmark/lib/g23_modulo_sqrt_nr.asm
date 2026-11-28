; =====================================================================
; MODULO: modulo_sqrt_nr (Grupo 23) - SQRT por el metodo NON-RESTORING
; Arquitectura de Computadoras (IC221) - FI-UNaM - 2026
;
; Algoritmo digito a digito de Li y Chu (1996): obtiene un bit de la raiz
; por iteracion usando solo sumas, restas (complemento a 2) y corrimientos
; (ADD de un registro consigo mismo). k = 13 iteraciones fijas: es el
; maximo con el que el resto parcial entra en 16 bits con signo.
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
; Registros: R1-R4 se apilan y se restauran; R5 y R7 no se modifican;
;            R6 (pila) vuelve con el mismo valor que tenia al entrar.
; Uso interno: R0 radicando (se corre a la izquierda), R1 contador,
;              R2 resto parcial, R3 raiz parcial, R4 temporal.
; ---------------------------------------------------------------------
; [G23] Version para la ISA G23 (Grupo 23): mismo algoritmo non-restoring,
;       misma interfaz y mismos resultados. Cambios: los bits del radicando
;       bajan al resto con LSL + RLC (rotacion a traves del acarreo), la resta
;       usa SUB, las pruebas de signo usan BRR, el contador DBP y el resguardo
;       PUSH/POP.
SQRT_NR     BRRzp R0, SQ_OK     ; x >= 0: calcular
            LD R0, SQ_ERR       ; x < 0 -> R0 = x8000 (error), sin tocar la pila
            RET
SQ_OK       PUSH R1, R2, R3, R4
            AND R1, R1, #0
            ADD R1, R1, #13     ; k = 13 iteraciones
            AND R2, R2, #0      ; R = 0 (resto parcial)
            AND R3, R3, #0      ; Q = 0 (raiz parcial)

; ---------- lazo: un bit de la raiz por iteracion ---------------------
; 1) Bajar 2 bits del radicando al resto: R = 4R + par
SQ_LAZO     LSL R0, R0, #1      ; C = bit 15 del radicando
            RLC R2, R2, #1      ; R = 2R + C
            LSL R0, R0, #1
            RLC R2, R2, #1      ; R = 4R + par
; 2) Paso non-restoring: si R >= 0, R = R - (4Q + 1); si no, R = R + (4Q + 3)
            LSL R4, R3, #2      ; R4 = 4Q
            BRRn R2, SQ_SUMA
            ADD R4, R4, #1      ; R4 = 4Q + 1
            SUB R2, R2, R4      ; R = R - (4Q + 1)
            BR SQ_BIT
SQ_SUMA     ADD R4, R4, #3      ; R4 = 4Q + 3
            ADD R2, R2, R4      ; R = R + (4Q + 3)
; 3) Nuevo bit de la raiz: Q = 2Q + (R >= 0 ? 1 : 0)
SQ_BIT      ADD R3, R3, R3
            BRRn R2, SQ_SIG
            ADD R3, R3, #1
SQ_SIG      DBP R1, SQ_LAZO     ; k = k - 1; repetir si k > 0

; ---------- correccion final del resto: si R < 0, R = R + 2Q + 1 ------
            BRRzp R2, SQ_RED
            ADD R4, R3, R3
            ADD R4, R4, #1
            ADD R2, R2, R4
; ---------- redondeo al mas cercano: si R > Q, Q = Q + 1 --------------
SQ_RED      SUB R4, R2, R3      ; R4 = R - Q
            BRnz SQ_FIN
            ADD R3, R3, #1
SQ_FIN      ADD R0, R3, #0      ; resultado en Q6.9
            POP R1, R2, R3, R4
            RET


; ---------- constantes ----------
SQ_ERR      .FILL x8000
            .END
