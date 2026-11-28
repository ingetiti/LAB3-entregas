; Prueba del conversor del grupo 15.
; Cambiar ENTRADA para probar otro valor.
; Con ENTRADA = 516, SALIDA debe quedar en 32.
; Revisar el resultado y los registros antes de HALT.

G15_Q312_Q78:
                                ST R1,G15_GUARDADO_R1
                                ST R2,G15_GUARDADO_R2
                                ST R3,G15_GUARDADO_R3
                                ST R4,G15_GUARDADO_R4
                                MOVI R1,#0
                                MOVI R2,#0
                                MOVI R4,#15
                                ADD R4,R4,#1
G15_MULT16:
                                MOV R3,R1                    ; palabra baja anterior
                                ADD R1,R1,R0
                                ADD R0,R0,#0
                                BRN G15_SUMANDO_NEG
                                ADD R3,R3,#0
                                BRZP G15_SIGUIENTE
                                ADD R1,R1,#0
                                BRZP G15_ACARREO
                                BRNZP G15_SIGUIENTE
G15_SUMANDO_NEG:
                                ADD R2,R2,#-1                ; extension de signo del sumando
                                ADD R3,R3,#0
                                BRN G15_ACARREO
                                ADD R1,R1,#0
                                BRN G15_SIGUIENTE
G15_ACARREO:
                                ADD R2,R2,#1
G15_SIGUIENTE:
                                ADD R4,R4,#-1
                                BRP G15_MULT16

                                MOV R0,R2
                                MOV R3,R1                    ; copia para conservar el intermedio en R2:R1
                                ADD R4,R4,#8
G15_LEER_LO:
                                ADD R0,R0,R0
                                ADD R3,R3,#0
                                BRZP G15_BIT_CERO
                                ADD R0,R0,#1
G15_BIT_CERO:
                                ADD R3,R3,R3
                                ADD R4,R4,#-1
                                BRP G15_LEER_LO
                                LD R1,G15_GUARDADO_R1
                                LD R2,G15_GUARDADO_R2
                                LD R3,G15_GUARDADO_R3
                                LD R4,G15_GUARDADO_R4
                                ADD R0,R0,#0
                                RET

G15_GUARDADO_R1:                .BLKW #1
G15_GUARDADO_R2:                .BLKW #1
G15_GUARDADO_R3:                .BLKW #1
G15_GUARDADO_R4:                .BLKW #1
.END
