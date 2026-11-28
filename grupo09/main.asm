; LAB 3 - GRUPO 09 - PROGRAMA INDEPENDIENTE SQRT
; No importa archivos, menu ni utilidades de los otros grupos.
; Cargar todos los .asm de esta carpeta. Seleccionar este como entrada.
.EXTERNAL SQ9_READ-SQ9_READ_DQ16
.EXTERNAL SQ9_PRINT-SQ9_PRINT_DQ16
.EXTERNAL SQRT_NR_DQ16-SQRT_NR_DQ16

.ORIG x3000
SQ9_MAIN
    LEA R0 SQM_TITLE
    PUTS
SQM_LOOP
    LEA R0 SQM_PROMPT
    PUTS
    LD R3 SQM_READ_PTR
    JSRR R3                     ; R0:R1 entrada Q15.16, R2 estado
    ADD R3 R2 #0
    BRz SQM_CALCULATE
    ADD R3 R2 #-4
    BRz SQM_EXIT
    ADD R3 R2 #-1
    BRz SQM_INVALID
    ADD R3 R2 #-2
    BRz SQM_NEGATIVE
    LEA R0 SQM_RANGE_TEXT
    PUTS
    BRnzp SQM_LOOP
SQM_INVALID
    LEA R0 SQM_INVALID_TEXT
    PUTS
    BRnzp SQM_LOOP
SQM_NEGATIVE
    LEA R0 SQM_NEGATIVE_TEXT
    PUTS
    BRnzp SQM_LOOP
SQM_CALCULATE
    LD R3 SQM_SQRT_PTR
    JSRR R3                     ; R0:R1 raiz Q15.16
    ST R0 SQM_OUT_HI
    ST R1 SQM_OUT_LO
    LEA R0 SQM_RESULT
    PUTS
    LD R0 SQM_OUT_HI
    LD R1 SQM_OUT_LO
    LD R3 SQM_PRINT_PTR
    JSRR R3
    BRnzp SQM_LOOP
SQM_EXIT
    LD R0 SQM_BYE_PTR
    PUTS
    HALT
SQM_OUT_HI       .BLKW #1
SQM_OUT_LO       .BLKW #1
SQM_BYE_PTR      .FILL SQM_BYE
SQM_READ_PTR     .FILL SQ9_READ-SQ9_READ_DQ16
SQM_PRINT_PTR    .FILL SQ9_PRINT-SQ9_PRINT_DQ16
SQM_SQRT_PTR     .FILL SQRT_NR_DQ16-SQRT_NR_DQ16
SQM_TITLE        .STRINGZ "\n== GRUPO 09 - SQRT NEWTON-RAPHSON ==\nRango: 0 <= x < 32768, hasta 4 decimales.\nIngrese q para salir.\n"
SQM_PROMPT       .STRINGZ "x > "
SQM_RESULT       .STRINGZ "sqrt(x) ~= "
SQM_INVALID_TEXT .STRINGZ "ERROR: entrada invalida (use un decimal con hasta 4 cifras fraccionarias).\n"
SQM_NEGATIVE_TEXT .STRINGZ "ERROR: argumento negativo.\n"
SQM_RANGE_TEXT   .STRINGZ "ERROR: fuera de rango Q15.16 (0 <= x < 32768).\n"
SQM_BYE          .STRINGZ "Programa finalizado.\n"
.END
