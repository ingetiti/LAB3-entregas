; Ejemplo mínimo para LC10: escribe un texto (bytes, terminado en 0) y termina.
        .ORIG x3000
        LEA   R0, MSG           ; R0 = dirección del primer byte (LEA llega a direcciones impares)
        PUTS
        HALT
MSG     .STRINGZ "Hola LC10\n"
        .END
