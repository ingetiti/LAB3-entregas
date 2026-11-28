; Grupo 12: división por Newton–Raphson, entrada y salida Q7.8.
; Conserva la tabla, los dos pasos Q3.12 y el truncamiento original.
; Entrada R0/R1. Devuelve R0 = xFFFF si el divisor es cero.
DIV_NEWTON
        ST    R1, DN_R1
        ST    R2, DN_R2
        ST    R3, DN_R3
        ST    R4, DN_R4
        ST    R5, DN_R5
        ST    R6, DN_R6
        ST    R7, DN_R7

        ; Las máscaras son 0 o -1. (valor XOR máscara) - máscara
        ; obtiene la magnitud sin signo, también para x8000.
        ASR   R2, R0, #15
        ASR   R3, R1, #15
        XOR   R7, R2, R3
        XOR   R0, R0, R2
        SUB   R6, R0, R2
        XOR   R1, R1, R3
        SUB   R2, R1, R3
        BRz   DN_DIV0

        AND   R3, R3, #0            ; s = cantidad de ceros a la izquierda
        ADD   R4, R2, #0
        BRn   DN_NORM
DN_FIND
        ADD   R3, R3, #1
        SHL   R4, R4, #1
        BRzp  DN_FIND
DN_NORM
        ADD   R4, R3, #-4
        BRzp  DN_NORM_LEFT
        NOT   R4, R4
        ADD   R4, R4, #1
        LSR   R2, R2, R4
        BRnzp DN_SEED
DN_NORM_LEFT
        SHL   R2, R2, R4

DN_SEED
        LSR   R4, R2, #8
        AND   R4, R4, #7
        SHL   R4, R4, #1            ; índice de palabra a dirección en bytes
        LEA   R5, DN_LUT
        ADD   R4, R4, R5
        LDR   R5, R4, #0
        LD    R4, DN_TWO

        ; y <- y * (2 - d*y), truncando cada producto por separado.
        MULUW R0, R2, R5
        LSRW  R0, R0, #12
        SUB   R0, R4, R0
        MULUW R0, R5, R0
        LSRW  R0, R0, #12
        ADD   R5, R0, #0

        MULUW R0, R2, R5
        LSRW  R0, R0, #12
        SUB   R0, R4, R0
        MULUW R0, R5, R0
        LSRW  R0, R0, #12

        MULUW R0, R6, R0
        LSRW  R0, R0, #12
        ADD   R3, R3, #-8
        BRzp  DN_DENORM_LEFT
        NOT   R3, R3
        ADD   R3, R3, #1
        LSR   R0, R0, R3
        BRnzp DN_SIGN
DN_DENORM_LEFT
        SHL   R0, R0, R3
DN_SIGN XOR   R0, R0, R7
        SUB   R0, R0, R7
        BRnzp DN_DONE
DN_DIV0 LD    R0, DN_ERROR
DN_DONE LD    R1, DN_R1
        LD    R2, DN_R2
        LD    R3, DN_R3
        LD    R4, DN_R4
        LD    R5, DN_R5
        LD    R6, DN_R6
        LD    R7, DN_R7
        RET

DN_TWO   .FILL x2000
DN_ERROR .FILL xFFFF
DN_LUT   .FILL x1E1E
         .FILL x1AF2
         .FILL x1861
         .FILL x1642
         .FILL x147A
         .FILL x12F6
         .FILL x11A7
         .FILL x1084
DN_R1    .BLKW #1
DN_R2    .BLKW #1
DN_R3    .BLKW #1
DN_R4    .BLKW #1
DN_R5    .BLKW #1
DN_R6    .BLKW #1
DN_R7    .BLKW #1
.END
