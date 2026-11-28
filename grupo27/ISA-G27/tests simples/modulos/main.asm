
.ORIG x3000

.EXTERNAL modulo_A-subrutina
.EXTERNAL modulo_B-texto

    JSR modulo_A-subrutina
    LEA R0 modulo_B-texto
    PUTS
    HALT

.END