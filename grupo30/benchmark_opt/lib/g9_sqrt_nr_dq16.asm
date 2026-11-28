; LAB 3 - GRUPO 9 - SQRT Newton-Raphson con normalizacion de rango (OPTIMIZADA)
.EXTERNAL SQRT_NR_Q8
.EXTERNAL SQ9_ROTL32
.EXTERNAL SQ9_DQ16_TO_Q8
.EXTERNAL SQ9_Q8_TO_DQ16

SQRT_NR_DQ16
    PUSHM {R2, R3, R4, R5, R7}

    CMP  R0, #0
    BRn  SQW_ZERO
    BRp  SQW_PREPARE
    CMP  R1, #0
    BRz  SQW_ZERO

SQW_PREPARE
    MOVI R4, #0                 ; k = 0

SQW_NORM
    MOVI R2, #16
    CMP  R0, R2
    BRp  SQW_DIV4
    BRn  SQW_CHECK_LOW
    CMP  R1, #0
    BRnp SQW_DIV4
    BRnzp SQW_NORMALIZED
SQW_CHECK_LOW
    CMP  R0, #4
    BRn  SQW_MUL4
    BRnzp SQW_NORMALIZED

SQW_DIV4
    ; (R0:R1) >>>= 2
    SHL  R2, R0, #14
    LSR  R1, R1, #2
    OR   R1, R1, R2
    LSR  R0, R0, #2
    ADD  R4, R4, #1
    BRnzp SQW_NORM

SQW_MUL4
    ; (R0:R1) <<= 2
    LSR  R2, R1, #14
    SHL  R0, R0, #2
    OR   R0, R0, R2
    SHL  R1, R1, #2
    ADD  R4, R4, #-1
    BRnzp SQW_NORM

SQW_NORMALIZED
    LD   R3, SQW_DQ16_Q8_PTR
    JSRR R3
    LD   R3, SQW_SQRT_PTR
    JSRR R3
    LD   R3, SQW_Q8_DQ16_PTR
    JSRR R3

    CMP  R4, #0
    BRz  SQW_DONE
    BRn  SQW_SCALE_DOWN

    ; Multiplicar por 2^k (1 <= k <= 7)
    MOVI R2, #16
    SUB  R2, R2, R4
    LSR  R3, R1, R2
    SHL  R0, R0, R4
    OR   R0, R0, R3
    SHL  R1, R1, R4
    BRnzp SQW_DONE

SQW_SCALE_DOWN
    NEG  R4, R4                 ; -k
    MOVI R2, #16
    SUB  R2, R2, R4
    SHL  R3, R0, R2
    LSR  R1, R1, R4
    OR   R1, R1, R3
    LSR  R0, R0, R4
    BRnzp SQW_DONE

SQW_ZERO
    MOVI R0, #0
    MOVI R1, #0

SQW_DONE
    POPM {R2, R3, R4, R5, R7}
    RET

SQW_DQ16_Q8_PTR   .FILL SQ9_DQ16_TO_Q8
SQW_Q8_DQ16_PTR   .FILL SQ9_Q8_TO_DQ16
SQW_SQRT_PTR      .FILL SQRT_NR_Q8

.END
