; Multiplicacion de dos operandos Q8.8 (LC-X).
; Entrada:
;   R0 = primer operando Q8.8
;   R1 = segundo operando Q8.8
; Salida:
;   R0:R1 = producto Q16.16
;       R0 = parte entera (palabra alta)
;       R1 = parte fraccionaria (palabra baja)
;
; R2-R7 se conservan.
;
; El mismo algoritmo que el original: con las magnitudes, se recorren los
; 16 bits del multiplicador; por cada bit en 1 se suma el multiplicando
; (32 bits) al acumulador, y el multiplicando se corre a la izquierda.
; Al final se aplica el signo. Con LC-X, la suma de 32 bits es ADD + ADC
; y el corrimiento es ADD + ADC sobre las dos palabras.
; (La version LC-3 deducia el acarreo de la suma baja mirando signos y
; sumaba uno de mas cuando la suma prendia el bit 15 sin que ningun
; sumando lo tuviera: el resultado podia salir una unidad mas grande.)
MULTIPLICARSHIFTANDADD:
        PUSH  R2, R3, R4, R5, R7
        XOR   R7, R0, R1        ; bit 15 = signo del producto
        ABS   R3, R0            ; R4:R3 = multiplicando (magnitud, 32 bits)
        AND   R4, R4, #0
        ABS   R2, R1            ; R2 = multiplicador (magnitud)
        AND   R0, R0, #0        ; R0:R1 = acumulador
        AND   R1, R1, #0
        MOVI  R5, #16           ; 16 bits
Q8_BUCLE:
        RSHFL R2, R2, #1        ; C = bit del multiplicador
        BRNC  Q8_DESPLAZAR
        ADD   R1, R1, R3        ; acumulador = acumulador + multiplicando
        ADC   R0, R0, R4
Q8_DESPLAZAR:
        ADD   R3, R3, R3        ; multiplicando = multiplicando << 1
        ADC   R4, R4, R4
        LOOP  R5, Q8_BUCLE
        ADD   R7, R7, #0        ; aplicar el signo al resultado de 32 bits
        BRzp  Q8_FIN
        NOT   R0, R0
        NEG   R1, R1            ; C = 1 solo si la palabra baja es 0
        ADC   R0, R0, #0
Q8_FIN: POP   R2, R3, R4, R5, R7
        RET
.END
