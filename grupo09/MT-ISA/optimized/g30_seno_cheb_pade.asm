; Grupo 30: seno por Chebyshev-Padé. Entrada Q3.12; salida Q1.14.
; Misma reducción de argumento, coeficientes y redondeos que la LC-3.
; R0 es entrada y salida. Se conservan R1–R7.
SEN_CHEB_PADE
        ST    R1, SN_R1
        ST    R2, SN_R2
        ST    R3, SN_R3
        ST    R4, SN_R4
        ST    R5, SN_R5

        AND   R4, R4, #0
        ADD   R0, R0, #0
        BRzp  SN_MOD
        SUB   R0, R4, R0
        ADD   R4, R4, #1
SN_MOD  LD    R1, SN_TWO_PI
        SUB   R2, R0, R1
        BRnz  SN_PI_RANGE
        ADD   R0, R2, #0
SN_PI_RANGE
        LD    R1, SN_PI
        SUB   R2, R0, R1
        BRnz  SN_FOLD
        ADD   R0, R2, #0
        NOT   R4, R4
        AND   R4, R4, #1
SN_FOLD LD    R2, SN_HALF_PI
        SUB   R2, R0, R2
        BRnz  SN_Q14
        SUB   R0, R1, R0
SN_Q14  SHL   R3, R0, #2
        BRz   SN_DONE

        ; La mitad que se descarta queda en C tras LSRW.
        ; La parte alta R1 del resultado desplazado es cero.
        MULUW R0, R3, R3
        LSRW  R0, R0, #15
        ADC   R2, R0, R1            ; u = redondeo(x*x / 2^15)
        LD    R1, SN_A
        MULUW R0, R2, R1
        LSRW  R0, R0, #14
        ADC   R0, R0, R1
        LD    R5, SN_ONE
        SUB   R5, R5, R0            ; numerador
        LD    R1, SN_B
        MULUW R0, R2, R1
        LSRW  R0, R0, #14
        ADC   R0, R0, R1
        LD    R2, SN_ONE
        ADD   R2, R0, R2            ; denominador

        ; R1 sigue en cero. El resto permite redondear el cociente.
        ADD   R0, R5, #0
        SHLW  R0, R0, #14
        DIVUW R0, R0, R2
        ADD   R1, R1, R1
        SUB   R1, R1, R2
        BRn   SN_RATIO
        ADD   R0, R0, #1
SN_RATIO
        MULUW R0, R3, R0
        LSRW  R0, R0, #14
        ADC   R0, R0, R1
        LD    R1, SN_ONE
        SUB   R2, R0, R1
        BRnz  SN_SIGN
        ADD   R0, R1, #0
SN_SIGN ADD   R4, R4, #0
        BRz   SN_DONE
        NOT   R0, R0
        ADD   R0, R0, #1
SN_DONE LD    R1, SN_R1
        LD    R2, SN_R2
        LD    R3, SN_R3
        LD    R4, SN_R4
        LD    R5, SN_R5
        ADD   R7, R7, #0
        RET

SN_R1       .BLKW #1
SN_R2       .BLKW #1
SN_R3       .BLKW #1
SN_R4       .BLKW #1
SN_R5       .BLKW #1
SN_ONE      .FILL #16384
SN_TWO_PI   .FILL #25736
SN_PI       .FILL #12868
SN_HALF_PI  .FILL #6434
SN_A        .FILL #3672
SN_B        .FILL #1814
.END
