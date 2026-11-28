;=====================================================================
; SUBRUTINA: G15_Q312_Q78 (Conversor de Q3.12 a Q7.8 para ISA-G27)
;
;   Entrada:  R0 = valor con signo en formato Q3.12
;   Salida:   R0 = valor con signo en formato Q7.8 (>> 4 aritmético)
;   Conserva: R1-R7 (todos intactos, no modifica ningún otro registro)
;   CC refleja el valor de R0 al retornar.
;=====================================================================
G15_Q312_Q78:
        RSH     R0, R0, #4          ; Desplazar 4 bits a la derecha (inmediato)
        SEXT    R0, R0, #12         ; Extender signo desde 12 bits a 16 bits (inmediato)
        ADD     R0, R0, #0          ; Asegurar códigos de condición (CC) sobre R0
        RET

.END