; ============================================================
; Conversor del grupo 15: Q3.12 a Q7.8 (LC-X).
; -> INPUT  [R0] valor en Q3.12
; <- OUTPUT [R0] valor en Q7.8 (truncado hacia -infinito, sin saturar)
; Conserva R1-R7. CC segun R0.
;
; El original multiplicaba por 16 con 16 sumas en 32 bits (R2:R1) y
; tomaba los bits [23:8]: eso es correr 4 bits a la derecha con signo.
; ============================================================

G15_Q312_Q78
        RSHFA R0, R0, #4        ; Q3.12 -> Q7.8, piso, CC <- R0
        RET

        .END
