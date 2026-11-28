; Reduccion_Argumento (LC-X)
; Entrada: R0 = tita en Q3.12 (pi = 12867)
; Salida:  R0 = tita reducido a [-pi/2, pi/2] restando o sumando pi
; Conserva R1-R7.
; (La bandera de signo del original vivia en R3, que se restauraba antes
;  del RET: nunca llegaba al llamador, asi que no se calcula.)
; Arreglo: en el original, tita - pi/2 desbordaba con tita < -26334 y el
; resultado salia mal; aqui BRV lo manda al lazo de sumar pi.

Reduccion_Argumento
        PUSH R1, R2
        LD   R1, PI_DOS          ; R1 = pi/2
        LD   R2, PI              ; R2 = pi

        CMP  R0, R1              ; tita - pi/2
        BRV  REDUCCION_NEG       ; desborda: tita < -26334
        BRnz REDUCCION_NEG
REDUCCION_POS
        SUB  R0, R0, R2          ; tita = tita - pi
        CMP  R0, R1
        BRp  REDUCCION_POS

REDUCCION_NEG
        NEG  R1, R1              ; R1 = -pi/2
NEG_LAZO
        CMP  R0, R1              ; tita + pi/2
        BRp  FIN
        ADD  R0, R0, R2          ; tita = tita + pi
        BR   NEG_LAZO

FIN     POPR R1, R2              ; restaurar y volver

PI      .FILL #12867
PI_DOS  .FILL #6434

.END
