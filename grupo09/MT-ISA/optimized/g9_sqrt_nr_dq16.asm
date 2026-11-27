; Grupo 9: raíz por Newton–Raphson recíproco, entrada y salida Q15.16.
; La interfaz usa R0 alto y R1 bajo. Se conservan R2–R7.
; Se reduce el argumento a [4, 16] y se repiten los seis pasos Q7.8
; con los mismos truncamientos y redondeos que las rutinas LC-3.
SQRT_NR_DQ16
        ADD   R0, R0, #0
        BRn   SQW_ZERO
        BRp   SQW_INIT
        ADD   R1, R1, #0
        BRz   SQW_RETURN

SQW_INIT
        ST    R2, SQW_R2
        ST    R3, SQW_R3
        ST    R4, SQW_R4
        ST    R5, SQW_R5
        ST    R6, SQW_R6
        ADD   R2, R0, #0
        ADD   R0, R1, #0
        ADD   R1, R2, #0
        AND   R5, R5, #0            ; k, exponente de la reducción
        ADD   R2, R1, #-4
        BRn   SQW_MUL4
        LD    R3, SQW_SIXTEEN
SQW_NORM_HIGH
        SUB   R2, R1, R3
        BRn   SQW_NORM_DONE
        BRp   SQW_DIV4
        ADD   R0, R0, #0
        BRz   SQW_NORM_DONE
SQW_DIV4
        LSRW  R0, R0, #2
        ADD   R5, R5, #1
        BRnzp SQW_NORM_HIGH
SQW_MUL4
        SHLW  R0, R0, #2
        ADD   R5, R5, #-1
        ADD   R2, R1, #-4
        BRn   SQW_MUL4
SQW_NORM_DONE
        LSRW  R0, R0, #8
        ADC   R4, R0, R1            ; x en Q7.8. R1 = 0, C redondea.
        LD    R2, SQW_SEED          ; y = 0,25
        LD    R6, SQW_THREE         ; 3,0 en Q7.8
        AND   R3, R3, #0
        ADD   R3, R3, #6

SQW_ITER
        MULUW R0, R2, R2
        LSRW  R0, R0, #8           ; y^2, truncado
        MULUW R0, R4, R0
        LSRW  R0, R0, #8           ; x*y^2, truncado
        SUB   R0, R6, R0
        MULUW R0, R0, R2
        LSRW  R0, R0, #9           ; dos truncamientos: /256 y /2
        ADD   R2, R0, #0
        ADD   R3, R3, #-1
        BRp   SQW_ITER

        MULUW R0, R4, R2
        LSRW  R0, R0, #8           ; raíz normalizada Q7.8
        SHLW  R0, R0, #8           ; raíz normalizada Q15.16
        ADD   R5, R5, #0
        BRn   SQW_SCALE_DOWN
        SHLW  R0, R0, R5
        BRnzp SQW_OUT
SQW_SCALE_DOWN
        NOT   R5, R5
        ADD   R5, R5, #1
        LSRW  R0, R0, R5
SQW_OUT ADD   R2, R0, #0
        ADD   R0, R1, #0
        ADD   R1, R2, #0
        LD    R2, SQW_R2
        LD    R3, SQW_R3
        LD    R4, SQW_R4
        LD    R5, SQW_R5
        LD    R6, SQW_R6
        BRnzp SQW_RETURN
SQW_ZERO
        AND   R0, R0, #0
        AND   R1, R1, #0
SQW_RETURN
        ADD   R7, R7, #0
        RET

SQW_SIXTEEN .FILL #16
SQW_SEED    .FILL #64
SQW_THREE   .FILL #768
SQW_R2      .BLKW #1
SQW_R3      .BLKW #1
SQW_R4      .BLKW #1
SQW_R5      .BLKW #1
SQW_R6      .BLKW #1
.END
