; Multiplicacion de dos operandos Q8.8.
; Entrada:
;   R0 = primer operando Q8.8
;   R1 = segundo operando Q8.8
; Salida:
;   R0:R1 = producto Q16.16
;       R0 = parte entera (palabra alta)
;       R1 = parte fraccionaria (palabra baja)
;
; R2-R5 se conservan. R6 y R7 no se utilizan.

MULTIPLICARSHIFTANDADD:
        ST      R2, Q8_GUARDAR_R2
        ST      R3, Q8_GUARDAR_R3
        ST      R4, Q8_GUARDAR_R4
        ST      R5, Q8_GUARDAR_R5

        ; Multiplicación nativa 16x16->32 FIRMADA (Q8.8 x Q8.8 -> Q16.16).
        ; MUL y MULH son firmados y operan sobre los operandos ORIGINALES R0 y R1.
        ; No se extraen magnitudes ni se aplica bloque de signo: el signo lo maneja
        ; directamente la multiplicación signed de MUL/MULH (incluye el borde 0x8000).
        ADD     R2, R0, #0          ; R2 = primer operando original (R0 se sobreescribe abajo).
        MUL     R0, R0, R1          ; R0 = low 16 bits (parte fraccionaria Q16.16).
        MULH    R1, R2, R1          ; R1 = high 16 bits (parte entera Q16.16).

Q8_INTERCAMBIAR:
        ; Intercambiar R0 y R1 para entregar R0 = entera, R1 = fraccionaria.
        ADD     R2, R0, #0          ; R2 = palabra baja (fraccion)
        ADD     R0, R1, #0          ; R0 = palabra alta (entera)
        ADD     R1, R2, #0          ; R1 = palabra baja (fraccion)

Q8_RESTAURAR:
        LD      R2, Q8_GUARDAR_R2
        LD      R3, Q8_GUARDAR_R3
        LD      R4, Q8_GUARDAR_R4
        LD      R5, Q8_GUARDAR_R5
        RET

; ---- BLOQUE DE VARIABLES LOCALES (reubicado tras RESTAURAR para PCoffset8) ----
Q8_GUARDAR_R2:     .FILL #0
Q8_GUARDAR_R3:     .FILL #0
Q8_GUARDAR_R4:     .FILL #0
Q8_GUARDAR_R5:     .FILL #0

.END