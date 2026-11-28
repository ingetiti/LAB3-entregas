;   ============================================================================
;   Subrutina: CIRCLSH (LC-X)
;       Corre de manera circular los bits de 2 registros A y B, hacia la
;       izquierda n veces: [A, B] rota como un valor de 32 bits.
;
;   -> INPUT  [R0] Registro A.
;   -> INPUT  [R1] Registro B.
;   -> INPUT  [R2] Numero de veces (0 o negativo: no rota).
;   <- OUTPUT [R0] Nuevo registro A despues del corrimiento.
;   <- OUTPUT [R1] Nuevo registro B despues del corrimiento.
;   Conserva R2-R7.
;   ============================================================================
CIRCLSH
        PUSH  R2
        ADD   R2, R2, #0
        BRnz  CIRCLSH_FIN       ; n <= 0: no rota
CIRCLSH_VUELTA
        ADD   R1, R1, R1        ; C = bit 15 de B
        ADC   R0, R0, R0        ; A = 2A + bit 15 de B; C = bit 15 de A
        ADC   R1, R1, #0        ; B = 2B + bit 15 de A
        LOOP  R2, CIRCLSH_VUELTA
CIRCLSH_FIN
        POP   R2
        RET
.END
