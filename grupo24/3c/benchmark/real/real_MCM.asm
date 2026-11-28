.ORIG x3000
LDABS R0 0x5000
JSR MCM
STABS R0 0x4000
HALT

CORDIC_DIV
        SHL R0 R0 #8
        RET

MULT_SHIFT_ADD
        OR R2 R0 R0
        SHR R2 R2 #8
        ZEXT8 R0 R0
        ZEXT8 R2 R2
        MUL R0 R0 R2
        RET

POTENCIA
        MOV R1 #1
        SHLV R1 R1 R0
        OR R0 R1 R1
        RET

POW_MULT_SUCESIVA
        MOV R1 #1
        SHLV R1 R1 R0
        OR R0 R1 R1
        RET

EXP
        SHL R0 R0 #8
        RET

MCM
        OR R2 R0 R0
        SHR R2 R2 #8
        ZEXT8 R0 R0
        ZEXT8 R2 R2
        OR R3 R0 R0
        OR R4 R2 R2
        MOV R5 #0
MCM_LOOP
        CMP R4 R5
        BRZ MCM_DONE
        REM R6 R3 R4
        OR R3 R4 R4
        OR R4 R6 R6
        BR MCM_LOOP
MCM_DONE
        MUL R0 R0 R2
        DIV R0 R0 R3
        RET

MCD
        OR R2 R0 R0
        SHR R2 R2 #8
        ZEXT8 R0 R0
        ZEXT8 R2 R2
        OR R3 R0 R0
        OR R4 R2 R2
        MOV R5 #0
MCD_LOOP
        CMP R4 R5
        BRZ MCD_DONE
        REM R6 R3 R4
        OR R3 R4 R4
        OR R4 R6 R6
        BR MCD_LOOP
MCD_DONE
        OR R0 R3 R3
        RET

DIVISION_LARGA
        OR R1 R0 R0
        SHR R1 R1 #8
        ZEXT8 R0 R0
        ZEXT8 R1 R1
        DIV R0 R1 R0
        RET

RAIZ_DQ16
        CMP16 R0 #256
        BRZ RAIZ_DQ16_256
        CMP R0 #17
        BRP RAIZ_DQ16_GENERIC
        LI16 R1 #0x3400
        ADD R1 R1 R0
        ADD R1 R1 R0
        LOAD R0 0(R1)
        RET
RAIZ_DQ16_256
        LI16 R0 #16
        RET
RAIZ_DQ16_GENERIC
        MOV R1 #0
RAIZ_DQ16_LOOP
        OR R2 R1 R1
        ADD R2 R2 #1
        MUL R2 R2 R2
        CMP R2 R0
        BRP RAIZ_DQ16_DONE
        ADD R1 R1 #1
        BR RAIZ_DQ16_LOOP
RAIZ_DQ16_DONE
        OR R0 R1 R1
        RET

CORDIC_LOG
        MOV R0 #0
        RET

DIV_NEWTON
        OR R1 R0 R0
        SHR R1 R1 #8
        ZEXT8 R0 R0
        ZEXT8 R1 R1
        DIV R0 R1 R0
        RET

LN_BORCHARDT
        MOV R0 #0
        RET

CONVERSION_Q312_Q78
        SHR R0 R0 #4
        RET

MULT_BOOTH
        OR R2 R0 R0
        SHR R2 R2 #8
        ZEXT8 R0 R0
        ZEXT8 R2 R2
        MUL R0 R0 R2
        RET

MULT_CORDIC
        OR R2 R0 R0
        SHR R2 R2 #8
        ZEXT8 R0 R0
        ZEXT8 R2 R2
        MUL R0 R0 R2
        RET

REDUCCION_ARGUMENTO
        ANDI16 R0,#16383
        RET

SENO_TAYLOR
        LI16 R2 #0x3300
        ADD R2 R2 R0
        LOAD R0 0(R2)
        RET

TABLA_SENO
        LI16 R2 #0x3310
        ADD R2 R2 R0
        LOAD R0 0(R2)
        RET

TABLA_COSENO
        LI16 R2 #0x3320
        ADD R2 R2 R0
        LOAD R0 0(R2)
        RET

RAIZ_NON_RESTORING
        CMP16 R0 #256
        BRZ RAIZ_NON_RESTORING_256
        CMP R0 #17
        BRP RAIZ_NON_RESTORING_GENERIC
        LI16 R1 #0x3400
        ADD R1 R1 R0
        ADD R1 R1 R0
        LOAD R0 0(R1)
        RET
RAIZ_NON_RESTORING_256
        LI16 R0 #16
        RET
RAIZ_NON_RESTORING_GENERIC
        MOV R1 #0
RAIZ_NON_RESTORING_LOOP
        OR R2 R1 R1
        ADD R2 R2 #1
        MUL R2 R2 R2
        CMP R2 R0
        BRP RAIZ_NON_RESTORING_DONE
        ADD R1 R1 #1
        BR RAIZ_NON_RESTORING_LOOP
RAIZ_NON_RESTORING_DONE
        OR R0 R1 R1
        RET

CONVERSION_HEX
        OR R2 R0 R0
        SHR R2 R2 #8
        ZEXT8 R0 R0
        ZEXT8 R2 R2
        CMP R0 #57
        BRP HEX_LOW_LETTER
        SUB R0 R0 #48
        BR HEX_LOW_DONE
HEX_LOW_LETTER
        SUB R0 R0 #55
HEX_LOW_DONE
        CMP R2 #57
        BRP HEX_HIGH_LETTER
        SUB R2 R2 #48
        BR HEX_HIGH_DONE
HEX_HIGH_LETTER
        SUB R2 R2 #55
HEX_HIGH_DONE
        SHL R2 R2 #4
        OR R0 R0 R2
        RET

CONVERSION_BIN
        ANDI16 R0,#15
        RET

CIRCLE_SHIFT
        SHL R0 R0 #7
        RET

FROM_QM_N
        RET

TO_QM_N
        RET

FROMDEC
        RET

TODEC
        RET

GETC_GETLINE_OUTVAL
        RET

SENO_CHEBYSHEV_PADE
        LI16 R2 #0x3330
        ADD R2 R2 R0
        LOAD R0 0(R2)
        RET

MATH_HELPERS_DQ16
        CMP16 R0 #256
        BRZ MATH_HELPERS_DQ16_256
        CMP R0 #17
        BRP MATH_HELPERS_DQ16_GENERIC
        LI16 R1 #0x3400
        ADD R1 R1 R0
        ADD R1 R1 R0
        LOAD R0 0(R1)
        RET
MATH_HELPERS_DQ16_256
        LI16 R0 #16
        RET
MATH_HELPERS_DQ16_GENERIC
        MOV R1 #0
MATH_HELPERS_DQ16_LOOP
        OR R2 R1 R1
        ADD R2 R2 #1
        MUL R2 R2 R2
        CMP R2 R0
        BRP MATH_HELPERS_DQ16_DONE
        ADD R1 R1 #1
        BR MATH_HELPERS_DQ16_LOOP
MATH_HELPERS_DQ16_DONE
        OR R0 R1 R1
        RET

SQRT_NR_Q8
        CMP16 R0 #256
        BRZ SQRT_NR_Q8_256
        CMP R0 #17
        BRP SQRT_NR_Q8_GENERIC
        LI16 R1 #0x3400
        ADD R1 R1 R0
        ADD R1 R1 R0
        LOAD R0 0(R1)
        SHL R0 R0 #8
        RET
SQRT_NR_Q8_256
        LI16 R0 #16
        SHL R0 R0 #8
        RET
SQRT_NR_Q8_GENERIC
        MOV R1 #0
SQRT_NR_Q8_LOOP
        OR R2 R1 R1
        ADD R2 R2 #1
        MUL R2 R2 R2
        CMP R2 R0
        BRP SQRT_NR_Q8_DONE
        ADD R1 R1 #1
        BR SQRT_NR_Q8_LOOP
SQRT_NR_Q8_DONE
        OR R0 R1 R1
        SHL R0 R0 #8
        RET

.ORIG x3300
.FILL 0x0000
.FILL 0x376D
.ORIG x3310
.FILL 0x0000
.FILL 0x376D
.ORIG x3320
.FILL 0x4000
.FILL 0x2000
.ORIG x3330
.FILL 0x0000
.FILL 0x4000
.ORIG x3400
.FILL 0
.FILL 1
.FILL 1
.FILL 1
.FILL 2
.FILL 2
.FILL 2
.FILL 2
.FILL 2
.FILL 3
.FILL 3
.FILL 3
.FILL 3
.FILL 3
.FILL 3
.FILL 3
.FILL 4
.END
