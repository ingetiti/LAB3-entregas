; LAB 3 - GRUPO 9 - SQRT Newton-Raphson con normalizacion de rango (Nueva ISA 16 bits)
; Subrutina del Grupo 09; sin dependencias de otros grupos.
; Input:  R0=palabra entera, R1=palabra fraccionaria (Q15.16, signo 32 bits)
; Output: R0=palabra entera, R1=fraccionaria de sqrt(x), Q15.16
; Rango: 0 <= x < 32768 representable. Negativos retornan cero (validar en menu).
; R2-R7 preservados; R6 nunca utilizado.
; No lleva .ORIG porque lo establece el programa principal.
;
; Reduccion de rango: x=4^k*t, 4 <= t <= 16.
; Entonces sqrt(x)=2^k*sqrt(t); t se evalua con SQRT_NR_Q8.
; Los desplazamientos 32 bits usan SHL/RLC y LSR/RRC en lugar de rotaciones por lazo.
.EXTERNAL SQRT_NR_Q8-SQRT_NR_Q8
.EXTERNAL SQ9_MATH_HELPERS-SQ9_DQ16_TO_Q8
.EXTERNAL SQ9_MATH_HELPERS-SQ9_Q8_TO_DQ16

SQRT_NR_DQ16
    ; Evitar negativos y cero antes de apilar.
    ADD R0, R0, #0
    BRn SQW_ZERO
    BRp SQW_PREPARE
    ADD R1, R1, #0
    BRz SQW_ZERO            ; sqrt(0)=0

SQW_PREPARE
    PUSHM {R2, R3, R4, R5, R7}
    CLR R4                  ; R4 = k = 0

; Si el entero es >16, o es 16 con fraccion no nula, dividir por 4.
; Si el entero es <4, multiplicar por 4.
; De otro modo, el numero ya esta normalizado.
SQW_NORM
    ADDI R2, R0, #-16
    BRp SQW_DIV4
    BRn SQW_CHECK_LOW
    ADD R1, R1, #0
    BRnp SQW_DIV4
    BR SQW_NORMALIZED
SQW_CHECK_LOW
    ADDI R2, R0, #-4
    BRn SQW_MUL4
    BR SQW_NORMALIZED

SQW_DIV4
    LSR R0, R0, #1          ; (R0:R1) >>= 2 (logico, x > 0)
    RRC R1, R1
    LSR R0, R0, #1
    RRC R1, R1
    INC R4                  ; k++
    BR SQW_NORM

SQW_MUL4
    SHL R1, R1, #1          ; (R0:R1) <<= 2 (seguro al ser x < 4)
    RLC R0, R0
    SHL R1, R1, #1
    RLC R0, R0
    DEC R4                  ; k--
    BR SQW_NORM

SQW_NORMALIZED
    JSR SQ9_MATH_HELPERS-SQ9_DQ16_TO_Q8 ; x Q15.16 -> Q7.8 redondeado en R0
    JSR SQRT_NR_Q8-SQRT_NR_Q8           ; SQRT_NR_Q8(x) en R0
    JSR SQ9_MATH_HELPERS-SQ9_Q8_TO_DQ16 ; R0:R1 = raiz normalizada Q15.16

    ADD R4, R4, #0
    BRz SQW_DONE
    BRn SQW_SCALE_DOWN

SQW_SCALE_UP
    SHL R1, R1, #1          ; multiplicar por 2^k (salida < 182, no desborda)
    RLC R0, R0
    DEC R4
    BRp SQW_SCALE_UP
    BR SQW_DONE

SQW_SCALE_DOWN
    LSR R0, R0, #1          ; dividir por 2^(-k) con truncamiento
    RRC R1, R1
    INC R4
    BRn SQW_SCALE_DOWN

SQW_DONE
    POPR {R2, R3, R4, R5, R7}

SQW_ZERO
    CLR R0
    CLR R1
    RET
.END
