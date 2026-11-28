; Primer programa: imprimir un mensaje.
.ORIG x3000
    LEA R0, SALUDO
    PUTS
    HALT
SALUDO .STRINGZ "Hola desde LC-3 en C!\n"
.END
