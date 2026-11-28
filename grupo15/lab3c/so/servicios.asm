; Servicios de consola de JochISA. Los vectores x20 a x25 aparecen en orden.
.ORIG x0200
    .FILL leer
    .FILL escribir
    .FILL cadena
    .FILL leer_con_eco
    .FILL cadena_packed
    .FILL detener

leer
    ADD R6,R6,#-2
    STR R1,R6,#0
esperar_tecla
    LDI R1,estado_teclado
    BRzp esperar_tecla
    LDI R0,dato_teclado
    LDR R1,R6,#0
    ADD R6,R6,#2
    RTI

escribir
    ADD R6,R6,#-2
    STR R1,R6,#0
esperar_pantalla
    LDI R1,estado_pantalla
    BRzp esperar_pantalla
    STI R0,dato_pantalla
    LDR R1,R6,#0
    ADD R6,R6,#2
    RTI

cadena
    ADD R6,R6,#-4
    STR R0,R6,#0
    STR R1,R6,#1
    ADD R1,R0,#0
otra_letra
    LDR R0,R1,#0
    BRz fin_cadena
    OUT
    ADD R1,R1,#2
    BR otra_letra
fin_cadena
    LDR R0,R6,#0
    LDR R1,R6,#1
    ADD R6,R6,#4
    RTI

leer_con_eco
    LEA R0,aviso
    PUTS
    GETC
    OUT
    RTI

cadena_packed
    ADD R6,R6,#-6
    STR R0,R6,#0
    STR R1,R6,#1
    STR R2,R6,#2
    ADD R1,R0,#0
otra_palabra
    LDR R2,R1,#0
    BRz fin_packed
    ADD R0,R2,#0
    OUT
    LSR R0,R2,#8
    BRz sin_alto
    OUT
sin_alto
    ADD R1,R1,#2
    BR otra_palabra
fin_packed
    LDR R0,R6,#0
    LDR R1,R6,#1
    LDR R2,R6,#2
    ADD R6,R6,#6
    RTI

detener
    ADD R6,R6,#-2
    STR R0,R6,#0
    LEA R0,mensaje_fin
    PUTS
    AND R0,R0,#0
    STI R0,control
    LDR R0,R6,#0
    ADD R6,R6,#2
    RTI

estado_teclado  .FILL xFE00
dato_teclado    .FILL xFE02
estado_pantalla .FILL xFE04
dato_pantalla   .FILL xFE06
control         .FILL xFFFE
aviso           .STRINGZ "Ingresá un carácter: "
mensaje_fin     .STRINGZ "\nHALT\n"
.END
