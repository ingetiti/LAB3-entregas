; Modulo: cordic_division   (archivo cordic_division.asm)   (LC-X)
;=====================================================================
; Division por CORDIC (modo lineal, vectoring) en punto fijo Q15
;
; CORDIC_DIV
;   ENTRADAS (Q15, entero con signo en complemento a 2):
;     R0 = y0  (dividendo)
;     R1 = x0  (divisor)    con x0 > 0  y  |y0| < x0
;   SALIDA:
;     R0 = y0 / x0 en Q15, rango [-1, 1)   (valor real = R0 / 32768)
;          Ejemplo: 0.5 = x4000,  -0.5 = xC000   (error tipico: 1 LSB)
;   Conserva R1-R7 (guarda R2 y R4 en la pila).
;
; El mismo algoritmo que el original: 16 iteraciones que duplican el
; residuo en vez de achicar x:
;     P' = 2P + d*x        Z' = 2Z - d
;     d = +1 si P <= 0 ;  d = -1 si P > 0
; salvo la iteracion 0, que no duplica P (P' = P + d*x, Z' = -d).
; Z no se pone a 0: entra con y0 y sus 16 duplicaciones lo sacan de
; los 16 bits, asi que el resultado es el mismo bit a bit.
;=====================================================================
CORDIC_DIV
        PUSH  R2, R4
        MOVI  R4, #16           ; 16 iteraciones, la 0 incluida
        ADD   R2, R0, #0        ; R2 = P = y0 (CC: signo de y0)
        BRp   CD_POS0           ; la iteracion 0 no duplica P
        BR    CD_NEG0

CD_LAZO BRp   CD_POS
        ADD   R2, R2, R2        ; P <= 0: d = +1, P = 2P + x
CD_NEG0 ADD   R0, R0, R0
        SUB   R0, R0, #1        ;         Z = 2Z - 1
        ADD   R2, R2, R1        ; CC: signo de P
        LOOP  R4, CD_LAZO
        POPR  R2, R4

CD_POS  ADD   R2, R2, R2        ; P > 0:  d = -1, P = 2P - x
CD_POS0 ADD   R0, R0, R0
        ADD   R0, R0, #1        ;         Z = 2Z + 1
        SUB   R2, R2, R1        ; CC: signo de P
        LOOP  R4, CD_LAZO
        POPR  R2, R4

        .END
