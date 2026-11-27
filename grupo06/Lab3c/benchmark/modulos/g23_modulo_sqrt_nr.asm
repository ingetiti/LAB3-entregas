; Adaptacion ISA3C; ver ../cambios_punteros.json y ../procedencia.json.
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
;       .EXTERNAL g23_modulo_sqrt_nr-SQRT_NR
;       LD   R5, PTR_SQRT
;       JSRR R5
;       ...
; PTR_SQRT .FILL g23_modulo_sqrt_nr-SQRT_NR
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
SQRT_NR     ADD R0, R0, #0
            BRn SQ_NEG          ; x < 0 -> error, sin tocar la pila

            ADD R6, R6, #-8     ; apila R1-R4 (la pila crece hacia abajo) ; ISA3C: direccion en bytes
            STR R1, R6, #0
            STR R2, R6, #1
            STR R3, R6, #2
            STR R4, R6, #3

            AND R1, R1, #0
            ADD R1, R1, #13     ; k = 13 iteraciones
            AND R2, R2, #0      ; R = 0 (resto parcial)
            AND R3, R3, #0      ; Q = 0 (raiz parcial)

; ---------- lazo: un bit de la raiz por iteracion ---------------------
; 1) Bajar 2 bits del radicando al resto: R = 4R + par.
;    El bit 15 de R0 se lee con su signo y R0 se corre con ADD R0,R0,R0.
;    Tras 8 iteraciones R0 queda en 0: equivale a D = x << 10.
SQ_LAZO     ADD R2, R2, R2      ; R = 2R
            ADD R0, R0, #0
            BRzp SQ_B1          ; bit 15 de R0 = 0
            ADD R2, R2, #1      ; bit 15 de R0 = 1
SQ_B1       ADD R0, R0, R0      ; siguiente bit a la posicion 15
            ADD R2, R2, R2      ; R = 2R
            ADD R0, R0, #0
            BRzp SQ_B2
            ADD R2, R2, #1
SQ_B2       ADD R0, R0, R0

; 2) Paso non-restoring: si R >= 0, R = R - (4Q + 1); si no, R = R + (4Q + 3)
            ADD R4, R3, R3
            ADD R4, R4, R4      ; R4 = 4Q
            ADD R2, R2, #0
            BRn SQ_SUMA
            ADD R4, R4, #1      ; R4 = 4Q + 1
            NOT R4, R4
            ADD R4, R4, #1      ; R4 = -(4Q + 1)
            ADD R2, R2, R4
            BRnzp SQ_BIT
SQ_SUMA     ADD R4, R4, #3      ; R4 = 4Q + 3
            ADD R2, R2, R4

; 3) Nuevo bit de la raiz: Q = 2Q + (R >= 0 ? 1 : 0)
SQ_BIT      ADD R3, R3, R3
            ADD R2, R2, #0
            BRn SQ_SIG
            ADD R3, R3, #1
SQ_SIG      ADD R1, R1, #-1
            BRp SQ_LAZO

; ---------- correccion final del resto: si R < 0, R = R + 2Q + 1 ------
            ADD R2, R2, #0
            BRzp SQ_RED
            ADD R4, R3, R3
            ADD R4, R4, #1
            ADD R2, R2, R4

; ---------- redondeo al mas cercano: si R > Q, Q = Q + 1 --------------
SQ_RED      NOT R4, R3
            ADD R4, R4, #1      ; R4 = -Q
            ADD R4, R2, R4      ; R4 = R - Q
            BRnz SQ_FIN
            ADD R3, R3, #1

SQ_FIN      ADD R0, R3, #0      ; resultado en Q6.9
            LDR R1, R6, #0      ; desapila R1-R4 en el mismo orden
            LDR R2, R6, #1
            LDR R3, R6, #2
            LDR R4, R6, #3
            ADD R6, R6, #8      ; R6 vuelve a su valor de entrada ; ISA3C: direccion en bytes
            RET

SQ_NEG      LD R0, SQ_ERR       ; R0 = x8000 (codigo de error)
            RET

; ---------- constantes ----------
SQ_ERR      .FILL x8000
            .END

