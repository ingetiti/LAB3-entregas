; ============================================================================
; Modulo: sumover  (archivo g27_sumover.asm)                            Grupo 27
; Sumador de 16 bits con acarreo de entrada y de salida. En LC10 es una sola
; instruccion, ADC; el modulo original la emulaba con mascaras de 15 bits.
;
; SUMOVER
; Entrada:  R0 = valor A, R1 = valor B, R2 = acarreo de entrada (0 o 1)
; Salida:   R0 = (A + B + acarreo) mod 2^16
;           R2 = acarreo de salida (0 o 1)
; Preserva: R1 y todos los demas registros (no usa memoria ni la pila).
; ============================================================================

SUMOVER
                        SHR   R2, R2, #1                ; C = acarreo de entrada
                        ADC   R0, R0, R1                ; R0 = A + B + C, C = acarreo de salida
                        MOVI  R2, #0                    ; (MOVI no toca C)
                        ADC   R2, R2, #0                ; R2 = C
                        RET

.END
