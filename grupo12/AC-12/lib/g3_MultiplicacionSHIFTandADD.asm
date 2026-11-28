; Multiplicacion de dos operandos Q7.8 -> producto Q15.16.
; Optimizado usando MUL y MULH de la ISA.
; Entrada:
;   R0 = primer operando Q7.8 (con signo)
;   R1 = segundo operando Q7.8 (con signo)
; Salida:
;   R0:R1 = producto Q15.16
;       R0 = parte entera (palabra alta)
;       R1 = parte fraccionaria (palabra baja)
;
; R2-R5 se conservan. R6 y R7 no se utilizan.

MULTIPLICARSHIFTANDADD:
        ST   R2, Q8_GUARDAR_R2
        MULH R2, R0, R1         ; R2 = palabra alta (parte entera)
        MUL  R1, R0, R1         ; R1 = palabra baja (parte fraccionaria)
        ADD  R0, R2, #0         ; R0 = palabra alta
        LD   R2, Q8_GUARDAR_R2
        RET

Q8_GUARDAR_R2: .FILL #0

.END
