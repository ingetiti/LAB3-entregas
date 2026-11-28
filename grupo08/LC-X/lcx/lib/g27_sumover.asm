;   ============================================================================
;   Subrutina: SUMOVER (LC-X)
;       Sumador de 16 bits que incluye bit carry de entrada y salida.
;
;   -> INPUT  [R0] Valor A.
;   -> INPUT  [R1] Valor B.
;   -> INPUT  [R2] Carry de entrada (tiene que valer 0 o 1).
;   <- OUTPUT [R0] Valor resultado (A + B).
;   <- OUTPUT [R2] Carry de salida (saldra con valor 0 o 1).
;   Conserva R1 y R3-R7.
;   ============================================================================
SUMOVER
        RSHFL R2, R2, #1        ; C = carry de entrada, R2 = 0
        ADC   R0, R0, R1        ; A + B + carry; C = carry de salida
        ADC   R2, R2, #0        ; R2 = carry de salida
        RET
.END
