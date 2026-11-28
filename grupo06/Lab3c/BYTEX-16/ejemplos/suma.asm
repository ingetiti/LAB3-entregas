; Resultado: R2 = 12, RESULTADO = 12.
.ORIG x3000
    AND R0, R0, #0
    ADD R0, R0, #5
    AND R1, R1, #0
    ADD R1, R1, #7
    ADD R2, R0, R1
    ST R2, RESULTADO
    HALT
RESULTADO .BLKW #1
.END
