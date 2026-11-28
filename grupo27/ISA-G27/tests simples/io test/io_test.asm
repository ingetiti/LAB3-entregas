
.ORIG x3000

    LEA R0 prompt
    PUTS

loop
    IN
    ADD R0 R0 #-8
    ADD R0 R0 #-2
    BRnp loop

    HALT

prompt  .STRINGZ "Pruebe teclas teclas - pulse INTRO para salir\n"


.END