; Conversor Q3.12 -> Q7.8 del Grupo 15 (OPTIMIZADA)
; Desplazamiento aritmetico de 4 bits con signo: R0 = R0 >>a 4

G15_Q312_Q78
        ASR  R0, R0, #4
        RET

        .END
