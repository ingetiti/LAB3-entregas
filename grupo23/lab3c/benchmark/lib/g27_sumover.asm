;   ============================================================================
;   Subrutina: SUMOVER  (Grupo 27)  -- version adaptada a la ISA G23 (Grupo 23)
;       Sumador de 16 bits que incluye bit carry de entrada y salida.
;
;   -> INPUT  [R0] Valor A.
;   -> INPUT  [R1] Valor B.
;   -> INPUT  [R2] Carry de entrada (tiene que valer 0 o 1).
;   <- OUTPUT [R0] Valor resultado (A + B).
;   <- OUTPUT [R2] Carry de salida (saldra con valor 0 o 1).
;
;   [G23] Misma interfaz y mismos resultados que la version de la LC-3. La
;   suma con acarreo la hace la instruccion ADC (bandera C de la ISA G23), en
;   lugar de separar los bits 15 y sumar las partes por software
;   (39 instrucciones en la LC-3 -> 5 en la ISA G23, contando el RET).
;   ============================================================================

SUMOVER                                 ;
    ADD R2 R2 #-1                       ;   C = carry de entrada (1 + xFFFF -> C = 1; 0 + xFFFF -> C = 0)
    ADC R0 R0 R1                        ;   resultado = A + B + C ; C = carry de salida
    AND R2 R2 #0                        ;   (AND no modifica C)
    ADC R2 R2 R2                        ;   carry = 0 + 0 + C
    RET                                 ;

.END
