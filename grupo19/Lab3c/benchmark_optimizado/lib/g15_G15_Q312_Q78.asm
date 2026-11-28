; ============================================================================
; Conversor de punto fijo Q3.12 a Q7.8 del grupo 15.
; Equivalente matematico exacto al algoritmo original ((R0 * 16) >> 8 en 32 bits),
; optimizado en la nueva ISA con un desplazamiento aritmetico directo de 4 bits.
;
; -> INPUT  [R0] Valor en formato Q3.12 (con signo)
; <- OUTPUT [R0] Valor convertido a formato Q7.8 (con signo)
; ============================================================================

G15_Q312_Q78
    ASR R0, R0, #4              ; desplazar 4 bits a la derecha con signo (actualiza N/Z/P)
    RET

    .END
