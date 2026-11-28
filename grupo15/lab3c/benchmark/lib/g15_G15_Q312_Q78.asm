; Q3.12 a Q7.8: dividir el entero con signo por 16, hacia abajo.
; Conserva R1-R7. NZP corresponde al resultado de R0.
G15_Q312_Q78
        ASR R0, R0, #4
        RET
        .END
