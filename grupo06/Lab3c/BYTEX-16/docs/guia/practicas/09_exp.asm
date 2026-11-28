; Prueba de EXP optimizada en BYTEX-16.
; Cambiar ENTRADA y volver a ensamblar. No lee por teclado.
; Q3.12: 1=x1000, 2=x2000, 3=x3000, -1=xF000.
; Para 3 se imprime x1416; RES_EXP y R0 conservan ese resultado Q7.8.
; La impresion y HALT agregan instrucciones ajenas a la llamada a EXP.
.ORIG x3000
    .EXTERNAL g6_EXP-EXP_Q3_12
    LD R0,ENTRADA
    LD R3,PTR_EXP
    JSRR R3
    ST R0,RES_EXP
    LEA R0,MENSAJE
    PUTS
    LD R1,RES_EXP
    AND R2,R2,#0
    ADD R2,R2,#12
    LEA R4,DIGITOS
IMPRIME_HEX
    SHR R3,R1,R2
    AND R3,R3,#15
    ADD R3,R3,R3
    ADD R3,R4,R3
    LDR R0,R3,#0
    OUT
    ADD R2,R2,#-4
    BRzp IMPRIME_HEX
    LD R0,RES_EXP
    HALT
ENTRADA .FILL x3000
RES_EXP .BLKW #1
PTR_EXP .FILL g6_EXP-EXP_Q3_12
MENSAJE .STRINGZ "EXP en Q7.8 (hex): x"
DIGITOS .STRINGZ "0123456789ABCDEF"
.END
