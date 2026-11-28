; =====================================================================
; MODULO: modulo_sqrt_nr (Grupo 23) - SQRT por el metodo NON-RESTORING
; Arquitectura de Computadoras (IC221) - FI-UNaM - 2026 (Nueva ISA 16 bits)
;
; Algoritmo digito a digito de Li y Chu (1996): obtiene un bit de la raiz
; por iteracion usando solo sumas, restas y desplazamientos.
; k = 13 iteraciones fijas: es el maximo con el que el resto parcial
; entra en 16 bits con signo.
;
; El .ORIG no hace falta: el enlazador ubica el modulo en memoria.
; =====================================================================

; ---------------------------------------------------------------------
; SQRT_NR: R0 = radicando x en Q7.8 (rango valido [0 ; 127,996])
;          devuelve R0 = raiz de x en Q6.9 (rango [0 ; 11,3145]),
;          redondeada al mas cercano (error maximo 1/2 LSB = 0,00098)
;          Si x < 0 devuelve R0 = x8000 (error: no hay raiz real).
; Registros: R1-R4 se preservan con PUSHM/POPM; R5, R6 y R7 no se modifican.
; Uso interno: R0 radicando, R1 contador, R2 resto parcial,
;              R3 raiz parcial, R4 temporal.
; ---------------------------------------------------------------------
SQRT_NR
    ADD R0, R0, #0
    BRn SQ_NEG                  ; x < 0 -> error, sin tocar la pila

    PUSHM {R1, R2, R3, R4}

    MOVI R1, #13                ; k = 13 iteraciones
    CLR R2                      ; R = 0 (resto parcial)
    CLR R3                      ; Q = 0 (raiz parcial)

; ---------- lazo: un bit de la raiz por iteracion ---------------------
; 1) Bajar 2 bits del radicando al resto: R = 4R + par.
SQ_LAZO
    SHL R0, R0, #1              ; C = bit 15 de x
    RLC R2, R2                  ; R = 2R + bit
    SHL R0, R0, #1              ; C = siguiente bit de x
    RLC R2, R2                  ; R = 2R + bit

; 2) Paso non-restoring: si R >= 0, R = R - (4Q + 1); si no, R = R + (4Q + 3)
    SHL R4, R3, #2              ; R4 = 4Q
    ADD R2, R2, #0
    BRn SQ_SUMA
    INC R4                      ; R4 = 4Q + 1
    SUB R2, R2, R4              ; R = R - (4Q + 1)
    BR SQ_BIT
SQ_SUMA
    ADDI R4, R4, #3             ; R4 = 4Q + 3
    ADD R2, R2, R4              ; R = R + (4Q + 3)

; 3) Nuevo bit de la raiz: Q = 2Q + (R >= 0 ? 1 : 0)
SQ_BIT
    SHL R3, R3, #1              ; Q = 2Q
    ADD R2, R2, #0
    BRn SQ_SIG
    INC R3                      ; Q = 2Q + 1
SQ_SIG
    DEC R1
    BRp SQ_LAZO

; ---------- correccion final del resto: si R < 0, R = R + 2Q + 1 ------
    ADD R2, R2, #0
    BRzp SQ_RED
    SHL R4, R3, #1              ; R4 = 2Q
    INC R4                      ; R4 = 2Q + 1
    ADD R2, R2, R4

; ---------- redondeo al mas cercano: si R > Q, Q = Q + 1 --------------
SQ_RED
    CMP R2, R3
    BRle SQ_FIN
    INC R3

SQ_FIN
    MOV R0, R3                  ; resultado en Q6.9
    POPM {R1, R2, R3, R4}
    RET

SQ_NEG
    LI R0, x8000                ; codigo de error
    RET
.END
