; Adaptacion ISA3C; ver ../cambios_punteros.json y ../procedencia.json.
; Grupo 15: conversion de Q3.12 a Q7.8.
; Recibe y devuelve el dato en R0. Conserva R1 a R7.
; Suma la entrada 16 veces y corre el resultado 8 bits a la derecha.
; Los negativos se aproximan hacia abajo.
; Guarda los registros en memoria para llamadas secuenciales.

G15_Q312_Q78
        ST R1, G15_GUARDADO_R1
        ST R2, G15_GUARDADO_R2
        ST R3, G15_GUARDADO_R3
        ST R4, G15_GUARDADO_R4
        AND R1, R1, #0
        AND R2, R2, #0
        AND R4, R4, #0
        ADD R4, R4, #15
        ADD R4, R4, #1
G15_MULT16
        ADD R3, R1, #0       ; palabra baja anterior
        ADD R1, R1, R0
        ADD R0, R0, #0
        BRn G15_SUMANDO_NEG
        ADD R3, R3, #0
        BRzp G15_SIGUIENTE
        ADD R1, R1, #0
        BRzp G15_ACARREO
        BRnzp G15_SIGUIENTE
G15_SUMANDO_NEG
        ADD R2, R2, #-1      ; extension de signo del sumando
        ADD R3, R3, #0
        BRn G15_ACARREO
        ADD R1, R1, #0
        BRn G15_SIGUIENTE
G15_ACARREO
        ADD R2, R2, #1
G15_SIGUIENTE
        ADD R4, R4, #-1
        BRp G15_MULT16

        ADD R0,R2,#0
        ADD R3,R1,#0
        ADD R4,R4,#8
        SHL R0,R0,R4
        SHR R3,R3,R4
        ADD R0,R0,R3
        LD R1, G15_GUARDADO_R1
        LD R2, G15_GUARDADO_R2
        LD R3, G15_GUARDADO_R3
        LD R4, G15_GUARDADO_R4
        ADD R0, R0, #0
        RET

G15_GUARDADO_R1 .BLKW #1
G15_GUARDADO_R2 .BLKW #1
G15_GUARDADO_R3 .BLKW #1
G15_GUARDADO_R4 .BLKW #1
        .END

