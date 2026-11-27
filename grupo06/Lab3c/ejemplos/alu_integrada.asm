; Demostracion autocontenida de las operaciones integradas.
; Escribir RESULTADOS en el depurador permite ver diez palabras.
.ORIG x3000
    LEA R5,RESULTADOS
    LD R1,A
    LD R2,B
    SUB R0,R1,R2
    STR R0,R5,#0
    MUL R0,R1,R2
    STR R0,R5,#1
    DIVU R0,R1,R2
    STR R0,R5,#2
    CLZ R0,R1
    STR R0,R5,#3
    MOV R0,R1
    STR R0,R5,#4
    LD R1,GRANDE
    LD R2,TRECE
    MULU R0,R1,R2
    STR R0,R5,#5
    LD R1,A
    LD R2,B
    SHL R0,R1,R2
    STR R0,R5,#6
    SHR R0,R1,R2
    STR R0,R5,#7
    LD R1,NEGATIVO
    SAR R0,R1,R2
    STR R0,R5,#8
    ASR R0,R1,R2
    STR R0,R5,#9

    ; Comprobar usando las operaciones antiguas, no SUB.
    LEA R4,ESPERADOS
    AND R3,R3,#0
    ADD R3,R3,#10
COMPROBAR
    LDR R0,R5,#0
    LDR R1,R4,#0
    NOT R1,R1
    ADD R1,R1,#1
    ADD R2,R0,R1
    BRnp ERROR
    ADD R5,R5,#2
    ADD R4,R4,#2
    ADD R3,R3,#-1
    BRp COMPROBAR
    LEA R0,TEXTO_OK
    PUTS
    HALT
ERROR LEA R0,TEXTO_ERROR
    PUTS
    HALT
A .FILL #16
B .FILL #4
GRANDE .FILL xFFFE
TRECE .FILL #13
NEGATIVO .FILL #-16
RESULTADOS .BLKW #10
ESPERADOS .FILL #12
    .FILL #64
    .FILL #4
    .FILL #11
    .FILL #16
    .FILL #12
    .FILL #256
    .FILL #1
    .FILL xFFFF
    .FILL xFFFF
TEXTO_OK .STRINGZ "ALU integrada: OK\n"
TEXTO_ERROR .STRINGZ "ALU integrada: ERROR\n"
.END
