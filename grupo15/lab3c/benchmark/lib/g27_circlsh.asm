; Rotacion circular de R0:R1, de 32 bits, hacia la izquierda R2 veces.
; Si R2 <= 0 no cambia los datos. Conserva R2-R7.
CIRCLSH
        ST R2, circlsh_r2
        ST R3, circlsh_r3
        ST R4, circlsh_r4
        ADD R2, R2, #0
        BRnz circlsh_ret
        LD R4, circlsh_16
        AND R3, R2, R4
        BRz circlsh_bajo
        ADD R3, R0, #0
        ADD R0, R1, #0
        ADD R1, R3, #0
circlsh_bajo
        AND R2, R2, #15
circlsh_loop
        ADD R2, R2, #0
        BRz circlsh_ret
        LSR R3, R0, #15
        LSR R4, R1, #15
        SHL R0, R0, #1
        ADD R0, R0, R4
        SHL R1, R1, #1
        ADD R1, R1, R3
        ADD R2, R2, #-1
        BR circlsh_loop
circlsh_ret
        LD R2, circlsh_r2
        LD R4, circlsh_r4
        LD R3, circlsh_r3
        RET
circlsh_r2 .BLKW #1
circlsh_r3 .BLKW #1
circlsh_r4 .BLKW #1
circlsh_16 .FILL #16
        .END
