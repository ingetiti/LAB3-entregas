;   ============================================================================
;   Subrutina: SUMOVER
;       Sumador de 16 bits que incluye bit carry de entrada y salida.
;       Optimizada para la nueva ISA usando flags de carry nativos (C) y RET.
;
;   -> INPUT  [R0] Valor A.
;   -> INPUT  [R1] Valor B.
;   -> INPUT  [R2] Carry de entrada (tiene que valer 0 o 1).
;   <- OUTPUT [R0] Valor resultado (A + B + cin).
;   <- OUTPUT [R2] Carry de salida (saldra con valor 0 o 1).
;   ============================================================================

SUMOVER
    ADD R0, R0, R1                      ;   R0 = A + B, C = carry1
    BRc sumover_c1                      ;   si carry1 == 1, carry_out sera 1
    ADD R0, R0, R2                      ;   R0 = A + B + cin, C = carry2
    BRc sumover_ret_c1                  ;   si carry2 == 1, carry_out = 1
    CLR R2                              ;   carry_out = 0
    RET

sumover_c1
    ADD R0, R0, R2                      ;   suma cin sin alterar el carry total (1)
sumover_ret_c1
    MOVI R2, #1                         ;   carry_out = 1
    RET

.END
