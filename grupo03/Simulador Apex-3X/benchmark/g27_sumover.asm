
; ============================================================================
; Subrutina: SUMOVER  [LC-3X — optimizada]
;     Sumador de 16 bits con carry de entrada y salida usando ADC.
;
; -> INPUT  [R0] Valor A.
; -> INPUT  [R1] Valor B.
; -> INPUT  [R2] Carry entrada (0 o 1).
; <- OUTPUT [R0] Resultado A + B + carry.
; <- OUTPUT [R2] Carry salida (0 o 1).
; ============================================================================

SUMOVER
    ADD R2 R2 #-1               ; C = 1 si carry_in != 0, 0 si carry_in == 0
    ADC R0 R0 R1                ; R0 = A + B + C_in, C = carry_out
    AND R2 R2 #0                ; R2 = 0 (preserva C)
    ADC R2 R2 #0                ; R2 = carry_out (0 o 1)
    RET

.END
