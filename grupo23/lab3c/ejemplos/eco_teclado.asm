; Prueba de teclado para la interfaz grafica de LOVELACE.
; Pide un nombre, lo lee tecla por tecla con GETC (cada tecla se muestra con
; OUT) hasta Enter y despues saluda. Se detiene con HALT.
        .ORIG x3000
        LEA   R0, PREGUNTA
        PUTS                    ; "Escribi tu nombre y apreta Enter: "
        LEA   R1, NOMBRE        ; [R1] puntero al buffer
        LD    R3, MENOS_ENTER   ; [R3] -10 (codigo de Enter)
LEER    GETC                    ; [R0] tecla
        OUT                     ; eco en la consola
        ADD   R2, R0, R3
        BRz   FIN               ; Enter: termina la lectura
        STR   R0, R1, #0        ; guarda el caracter
        ADD   R1, R1, #2        ; siguiente palabra (direcciones de byte)
        BR    LEER
FIN     AND   R2, R2, #0
        STR   R2, R1, #0        ; fin de cadena
        LEA   R0, HOLA
        PUTS
        LEA   R0, NOMBRE
        PUTS
        LEA   R0, CIERRE
        PUTS
        HALT
MENOS_ENTER .FILL #-10
PREGUNTA .STRINGZ "Escribi tu nombre y apreta Enter: "
HOLA     .STRINGZ "Hola, "
CIERRE   .STRINGZ "! Saludos de LOVELACE.\n"
NOMBRE   .BLKW 40
        .END
