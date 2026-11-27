; LAB 3 - GRUPO 9 - SQRT Newton-Raphson con normalizacion de rango [LC-3X]
; Input:  R0=palabra entera, R1=palabra fraccionaria (Q15.16, signo 32 bits)
; Output: R0=palabra entera, R1=fraccionaria de sqrt(x), Q15.16

.EXTERNAL SQRT_NR_Q8-SQRT_NR_Q8
.EXTERNAL SQ9_MATH_HELPERS-SQ9_ROTL32
.EXTERNAL SQ9_MATH_HELPERS-SQ9_DQ16_TO_Q8
.EXTERNAL SQ9_MATH_HELPERS-SQ9_Q8_TO_DQ16

SQRT_NR_DQ16
    PUSHM #xBC              ; Guarda R2, R3, R4, R5, R7

    ; Evitar negativos: el menu muestra Invalid Argument.
    ADD R0 R0 #0
    BRn SQW_ZERO
    BRp SQW_PREPARE
    ADD R1 R1 #0
    BRz SQW_ZERO            ; sqrt(0)=0

SQW_PREPARE
    AND R4 R4 #0
    ST R4 SQW_EXP           ; k=0

; Si el entero es >16, o es 16 con fraccion no nula, dividir por 4.
; Si el entero es <4, multiplicar por 4.
; De otro modo, el numero ya esta normalizado.
SQW_NORM
    MOVI R2 #-16
    ADD R2 R0 R2
    BRp SQW_DIV4
    BRn SQW_CHECK_LOW
    ADD R1 R1 #0
    BRnp SQW_DIV4
    BRnzp SQW_NORMALIZED
SQW_CHECK_LOW
    ADD R2 R0 #-4
    BRn SQW_MUL4
    BRnzp SQW_NORMALIZED

SQW_DIV4
    LD R2 SQW_ROT30
    LD R3 SQW_CIRCLSH_PTR
    JSRR R3                 ; ROTL32(30) = SHR32(2), antes de mascarar
    LD R2 SQW_MASK14
    AND R0 R0 R2            ; descartar los 2 bits circulares de cabecera
    LD R4 SQW_EXP
    ADD R4 R4 #1
    ST R4 SQW_EXP
    BRnzp SQW_NORM

SQW_MUL4
    LD R2 SQW_ROT2
    LD R3 SQW_CIRCLSH_PTR
    JSRR R3                 ; SHL32(2), seguro al ser x < 4
    LD R4 SQW_EXP
    ADD R4 R4 #-1
    ST R4 SQW_EXP
    BRnzp SQW_NORM

SQW_NORMALIZED
    LD R3 SQW_DQ16_Q8_PTR
    JSRR R3                 ; x Q15.16 -> Q7.8 redondeado en R0
    LD R3 SQW_SQRT_PTR
    JSRR R3                 ; SQRT_NR_Q8(x) en R0
    LD R3 SQW_Q8_DQ16_PTR
    JSRR R3                 ; R0:R1 = raiz normalizada Q15.16

    LD R4 SQW_EXP
    BRz SQW_DONE
    BRn SQW_SCALE_DOWN

SQW_SCALE_UP
    ADD R2 R4 #0           ; multiplicar por 2^k
    LD R3 SQW_CIRCLSH_PTR
    JSRR R3                 ; la salida maxima es <182, no desborda
    BRnzp SQW_DONE

SQW_SCALE_DOWN
    ; Dividir el resultado 32 bits por 2^(-k) con truncamiento.
    LD R2 SQW_ROT31
    LD R3 SQW_CIRCLSH_PTR
    JSRR R3
    LD R2 SQW_MASK15
    AND R0 R0 R2
    ADD R4 R4 #1
    BRn SQW_SCALE_DOWN
    BRnzp SQW_DONE

SQW_ZERO
    AND R0 R0 #0
    AND R1 R1 #0

SQW_DONE
    POPM #xBC               ; Restaura R2, R3, R4, R5, R7
    RET

SQW_ROT2          .FILL #2
SQW_ROT30         .FILL #30
SQW_ROT31         .FILL #31
SQW_MASK14        .FILL x3FFF
SQW_MASK15        .FILL x7FFF
SQW_EXP           .BLKW #1
SQW_CIRCLSH_PTR   .FILL SQ9_MATH_HELPERS-SQ9_ROTL32
SQW_DQ16_Q8_PTR   .FILL SQ9_MATH_HELPERS-SQ9_DQ16_TO_Q8
SQW_Q8_DQ16_PTR   .FILL SQ9_MATH_HELPERS-SQ9_Q8_TO_DQ16
SQW_SQRT_PTR      .FILL SQRT_NR_Q8-SQRT_NR_Q8

.END
