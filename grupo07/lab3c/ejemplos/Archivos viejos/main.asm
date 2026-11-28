; main.asm - programa principal de prueba. Llama a la rutina MCD+MCM.
; Cambiar DATO_A y DATO_B (enteros con signo, Q15.0) para probar otros valores.
        .ORIG x3000
        .EXTERNAL mcd_mcm-MCDMCM     ; formato MODULO-ETIQUETA (tambien vale ETIQUETA sola)

        LD R0, DATO_A
        LD R1, DATO_B
        JSR mcd_mcm-MCDMCM
        ST R0, RES_MCD
        ST R1, RES_MCM

        LEA R0, MSG
        PUTS
        HALT

MSG         .STRINGZ "MCD y MCM calculados\n"
DATO_A      .FILL #48
DATO_B      .FILL #180
RES_MCD     .FILL #0
RES_MCM     .FILL #0
.END
