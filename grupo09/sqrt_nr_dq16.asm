; LAB 3 - GRUPO 9 - SQRT Newton-Raphson con normalizacion de rango
; Subrutina para la calculadora del grupo de interfaz.
; Input:  R0=palabra entera, R1=palabra fraccionaria (Q15.16, signo 32 bits)
; Output: R0=palabra entera, R1=fraccionaria de sqrt(x), Q15.16
; Rango: 0 <= x < 32768 representable. Negativos retornan cero (validar en menu).
; R2-R7 preservados; R6 nunca utilizado. Variables internas no reentrantes.
; No lleva .ORIG porque lo establece el programa principal.
;
; Reduccion de rango: x=4^k*t, 4 <= t <= 16.
; Entonces sqrt(x)=2^k*sqrt(t); t se evalua con SQRT_NR_Q8 original.
; Las transformaciones utilizan la rotacion de 32 bits CIRCLSH (grupo 8).
.EXTERNAL SQRT_NR_Q8-SQRT_NR_Q8
.EXTERNAL CIRCLSH-CIRCLSH
.EXTERNAL DQ16_TO_Q8-DQ16_TO_Q8
.EXTERNAL Q8_TO_DQ16-Q8_TO_DQ16

SQRT_NR_DQ16
    ST R2 SQW_SAVE2
    ST R3 SQW_SAVE3
    ST R4 SQW_SAVE4
    ST R5 SQW_SAVE5
    ST R7 SQW_SAVE7

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
    ADD R2 R0 #-16
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
    ; Una rotacion de 31 equivale a SHR32(1) tras limpiar bit 31.
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
    LD R2 SQW_SAVE2
    LD R3 SQW_SAVE3
    LD R4 SQW_SAVE4
    LD R5 SQW_SAVE5
    LD R7 SQW_SAVE7
    RET

SQW_ROT2          .FILL #2
SQW_ROT30         .FILL #30
SQW_ROT31         .FILL #31
SQW_MASK14        .FILL x3FFF
SQW_MASK15        .FILL x7FFF
SQW_EXP           .BLKW #1
SQW_CIRCLSH_PTR   .FILL CIRCLSH-CIRCLSH
SQW_DQ16_Q8_PTR   .FILL DQ16_TO_Q8-DQ16_TO_Q8
SQW_Q8_DQ16_PTR   .FILL Q8_TO_DQ16-Q8_TO_DQ16
SQW_SQRT_PTR      .FILL SQRT_NR_Q8-SQRT_NR_Q8
SQW_SAVE2         .BLKW #1
SQW_SAVE3         .BLKW #1
SQW_SAVE4         .BLKW #1
SQW_SAVE5         .BLKW #1
SQW_SAVE7         .BLKW #1
.END
