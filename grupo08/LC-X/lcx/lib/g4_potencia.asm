; ============================================================
; SUBRUTINA: EXP_RAPIDA (LC-X)
;
; ENTRADAS:
;   R0 = Base
;   R1 = Exponente
;
; SALIDA:
;   R0 = Base ^ Exponente (16 bits)
;
; REGISTROS CALLEE-SAVED:
;   R1 a R7 (R1 y R2 se apilan; R6 vuelve igual)
;
; METODO: exponenciacion rapida, un bit del exponente por vuelta
;   (del menos significativo al mas): si el bit es 1, acum = acum * base;
;   luego base = base^2 (salvo en el ultimo bit). Con MUL en vez de sumas
;   sucesivas. Como en LC-3, una base que queda negativa vale 0 (sus
;   sumas sucesivas no se ejecutan). El signo se arrastra en el producto:
;   la base va con signo, que es lo mismo que negar al final si la base
;   es negativa y el exponente impar.
;   Exponente <= 0: 1, o -1 si la base es negativa y el exponente impar.
; ============================================================

EXP_RAPIDA
        PUSH  R1, R2
        ADD   R2, R0, #0      ; R2 = base
        RSHFA R1, R1, #1      ; R1 = exponente / 2, C = bit 0
        BRnz  EXP_CORTO       ; exponente <= 1
        BRC   EXP_CUAD        ; impar: acum = base (ya en R0)
        MOVI  R0, #1          ; par: acum = 1
        BR    EXP_CUAD

        ; ---- bucle: un bit del exponente por vuelta ----
EXP_LAZO
        RSHFL R1, R1, #1      ; C = bit, Z = era el ultimo
        BRz   EXP_ULT
        BRNC  EXP_CUAD
        MUL   R0, R0, R2      ; acum = acum * base
EXP_CUAD
        MUL   R2, R2, R2      ; base = base^2
        BRzp  EXP_LAZO
        AND   R2, R2, #0      ; base negativa: vale 0
        BR    EXP_LAZO

EXP_ULT
        MUL   R0, R0, R2      ; ultimo bit (siempre 1)
EXP_FIN
        POPR  R1, R2

        ; ---- exponente <= 1 ----
EXP_CORTO
        BRNC  EXP_UNO         ; par (0 o negativo): 1
        BRz   EXP_E1          ; exponente 1
        RSHFA R0, R0, #15     ; impar negativo: -1 si base < 0
        OR    R0, R0, #1      ; 1 si no
        POPR  R1, R2
EXP_E1
        ABS   R2, R0          ; V si base = x8000
        BRNV  EXP_FIN         ; R0 = base
        AND   R0, R0, #0      ; x8000 es negativa: 0
        POPR  R1, R2
EXP_UNO
        MOVI  R0, #1
        POPR  R1, R2

.END
