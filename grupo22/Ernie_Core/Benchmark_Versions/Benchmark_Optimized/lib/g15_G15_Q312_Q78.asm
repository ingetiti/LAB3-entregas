; Prueba del conversor del grupo 15.
; Cambiar ENTRADA para probar otro valor.
; Con ENTRADA = 516, SALIDA debe quedar en 32.
; Revisar el resultado y los registros antes de HALT.

G15_Q312_Q78
        ST R1, G15_GUARDADO_R1
        ST R2, G15_GUARDADO_R2
        ST R3, G15_GUARDADO_R3
        ST R4, G15_GUARDADO_R4
        ASR R0, R0, #4       ; R0 = floor(N/16) (shift aritmetico, imm4=4 [-8,+7])
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
