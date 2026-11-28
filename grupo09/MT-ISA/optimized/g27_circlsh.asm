; Rotación a la izquierda de R1:R0. R2 contiene el número de bits con signo.
CIRCLSH
    ADD R2, R2, #0
    BRnz circlsh_ret
    ST R3, circlsh_r3
    ST R4, circlsh_r4
    ST R5, circlsh_r5
    LD R4, circlsh_mask
    AND R4, R4, R2
    BRz circlsh_restore
    LD R3, circlsh_width
    SUB R3, R3, R4
    LSRW R4, R0, R3
    LD R3, circlsh_mask
    AND R3, R3, R2
    SHLW R0, R0, R3
    OR R0, R0, R4
    OR R1, R1, R5
circlsh_restore
    LD R3, circlsh_r3
    LD R4, circlsh_r4
    LD R5, circlsh_r5
circlsh_ret
    ADD R3, R3, #0
    RET
circlsh_mask .FILL #31
circlsh_width .FILL #32
circlsh_r3 .BLKW #1
circlsh_r4 .BLKW #1
circlsh_r5 .BLKW #1
.END
