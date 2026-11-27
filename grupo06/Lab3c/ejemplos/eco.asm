; Escribir caracteres. Enter termina el programa. Esc pausa al menu.
.ORIG x3000
BUCLE GETC
    OUT
    ADD R1, R0, #-10
    BRnp BUCLE
    HALT
.END
