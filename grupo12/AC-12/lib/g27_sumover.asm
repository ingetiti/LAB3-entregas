;   ============================================================================
;   Subrutina: SUMOVER
;       Sumador de 16 bits que incluye bit carry de entrada y salida.
;       Optimizado usando la bandera de acarreo hardware (C / BRC).
;
;   -> INPUT  [R0] Valor A.
;   -> INPUT  [R1] Valor B.
;   -> INPUT  [R2] Carry de entrada (tiene que valer 0 o 1).
;   <- OUTPUT [R0] Valor resultado (A + B + carry_in).
;   <- OUTPUT [R2] Carry de salida (saldra con valor 0 o 1).
;   Conserva: R1, R3, R4, R5, R6, R7.
;   ============================================================================

SUMOVER
    ADD R0 R0 R2                    ;   R0 = A + carry_in ; C = carry1
    BRC sumover_c1
    ADD R0 R0 R1                    ;   R0 = (A + carry_in) + B ; C = carry2
    BRC sumover_c2
    AND R2 R2 #0                    ;   carry_out = 0
    RET

sumover_c1
    ADD R0 R0 R1                    ;   carry1 = 1 -> R0 era 0, sumar B no genera 2do carry
sumover_c2
    AND R2 R2 #0
    ADD R2 R2 #1                    ;   carry_out = 1
    RET

.END
