.ORIG x3000

; Programa de prueba del Grupo 24.
; TRAP 0x23 lee el entero ingresado por la GUI o por terminal.
TRAP 0x23

MOV R6 #64
SHL R6 R6 #8
STORE R0 0(R6)

; Dec: 
MOV R0 #68
TRAP 0x21
MOV R0 #101
TRAP 0x21
MOV R0 #99
TRAP 0x21
MOV R0 #58
TRAP 0x21
MOV R0 #32
TRAP 0x21
LOAD R0 0(R6)
JSR SUB_BASE_DEC
MOV R0 #10
TRAP 0x21

; Hex: 
MOV R0 #72
TRAP 0x21
MOV R0 #101
TRAP 0x21
MOV R0 #120
TRAP 0x21
MOV R0 #58
TRAP 0x21
MOV R0 #32
TRAP 0x21
LOAD R0 0(R6)
JSR SUB_BASE_HEX
MOV R0 #10
TRAP 0x21

; Bin: 
MOV R0 #66
TRAP 0x21
MOV R0 #105
TRAP 0x21
MOV R0 #110
TRAP 0x21
MOV R0 #58
TRAP 0x21
MOV R0 #32
TRAP 0x21
LOAD R0 0(R6)
JSR SUB_BASE_BIN

MOV R0 #10
TRAP 0x21
HALT


; Convierte R0 como entero decimal con signo y lo imprime.
SUB_BASE_DEC
        STORE R7 2(R6)
        STORE R2 4(R6)
        STORE R3 6(R6)
        STORE R4 8(R6)
        STORE R5 10(R6)

        OR R2 R0 R0
        AND R3 R3 R3
        CMP R2 R3
        BRN DEC_NEGATIVE
        BRNZP DEC_POSITIVE

DEC_NEGATIVE
        MOV R1 #-128
        SHL R1 R1 #8
        CMP R2 R1
        BRZ DEC_MIN_NEGATIVE
        MOV R0 #45
        TRAP 0x21
        NOT R2 R2
        ADD R2 R2 #1
        BRNZP DEC_POSITIVE
DEC_MIN_NEGATIVE
        MOV R0 #45
        TRAP 0x21
        MOV R0 #51
        TRAP 0x21
        MOV R0 #50
        TRAP 0x21
        MOV R0 #55
        TRAP 0x21
        MOV R0 #54
        TRAP 0x21
        MOV R0 #56
        TRAP 0x21
        LOAD R7 2(R6)
        LOAD R2 4(R6)
        LOAD R3 6(R6)
        LOAD R4 8(R6)
        LOAD R5 10(R6)
        RET

DEC_POSITIVE
        AND R5 R5 R5

        ; 10000
        MOV R1 #39
        SHL R1 R1 #8
        MOV R4 #16
        OR R1 R1 R4
        DIV R3 R2 R1
        REM R4 R2 R1
        MOV R0 #0
        MOV R0 #0
        CMP R3 R0
        BRZ DEC_SKIP_10000
        MOV R5 #1
        MOV R0 #48
        ADD R0 R0 R3
        TRAP 0x21
DEC_SKIP_10000
        OR R2 R4 R4

        ; 1000
        MOV R1 #3
        SHL R1 R1 #8
        MOV R4 #-24
        MOV R3 #-1
        SHL R3 R3 #8
        NOT R3 R3
        AND R4 R4 R3
        OR R1 R1 R4
        DIV R3 R2 R1
        REM R4 R2 R1
        MOV R0 #0
        MOV R0 #0
        CMP R3 R0
        BRZ DEC_1000_ZERO
        MOV R5 #1
        MOV R0 #48
        ADD R0 R0 R3
        TRAP 0x21
        BRNZP DEC_1000_DONE
DEC_1000_ZERO
        CMP R5 R0
        BRZ DEC_1000_DONE
        MOV R0 #48
        TRAP 0x21
DEC_1000_DONE
        OR R2 R4 R4

        ; 100
        MOV R1 #100
        DIV R3 R2 R1
        REM R4 R2 R1
        MOV R0 #0
        MOV R0 #0
        CMP R3 R0
        BRZ DEC_100_ZERO
        MOV R5 #1
        MOV R0 #48
        ADD R0 R0 R3
        TRAP 0x21
        BRNZP DEC_100_DONE
DEC_100_ZERO
        CMP R5 R0
        BRZ DEC_100_DONE
        MOV R0 #48
        TRAP 0x21
DEC_100_DONE
        OR R2 R4 R4

        ; 10
        MOV R1 #10
        DIV R3 R2 R1
        REM R4 R2 R1
        MOV R0 #0
        MOV R0 #0
        CMP R3 R0
        BRZ DEC_10_ZERO
        MOV R5 #1
        MOV R0 #48
        ADD R0 R0 R3
        TRAP 0x21
        BRNZP DEC_10_DONE
DEC_10_ZERO
        CMP R5 R0
        BRZ DEC_10_DONE
        MOV R0 #48
        TRAP 0x21
DEC_10_DONE
        OR R2 R4 R4

        ; unidades
        CMP R5 R0
        BRZ DEC_PRINT_UNIT_ONLY
DEC_PRINT_UNIT_ONLY
        MOV R0 #48
        ADD R0 R0 R2
        TRAP 0x21

        LOAD R7 2(R6)
        LOAD R2 4(R6)
        LOAD R3 6(R6)
        LOAD R4 8(R6)
        LOAD R5 10(R6)
        RET


; Convierte R0 como entero hexadecimal sin signo de 16 bits y lo imprime.
SUB_BASE_HEX
        STORE R7 2(R6)
        STORE R2 4(R6)
        STORE R3 6(R6)
        STORE R4 8(R6)
        STORE R5 10(R6)

        OR R2 R0 R0
        MOV R0 #48
        TRAP 0x21
        MOV R0 #120
        TRAP 0x21

        MOV R0 #0
        OR R3 R2 R0
        SHR R3 R3 #12
        MOV R5 #15
        AND R3 R3 R5
        MOV R5 #10
        CMP R3 R5
        BRP HF1
        BRZ HF1
        MOV R0 #48
        ADD R0 R0 R3
        TRAP 0x21
        BRNZP HN2
HF1
        MOV R0 #55
        ADD R0 R0 R3
        TRAP 0x21
HN2
        MOV R0 #0
        OR R3 R2 R0
        SHR R3 R3 #8
        MOV R5 #15
        AND R3 R3 R5
        MOV R5 #10
        CMP R3 R5
        BRP HF2
        BRZ HF2
        MOV R0 #48
        ADD R0 R0 R3
        TRAP 0x21
        BRNZP HN3
HF2
        MOV R0 #55
        ADD R0 R0 R3
        TRAP 0x21
HN3
        MOV R0 #0
        OR R3 R2 R0
        SHR R3 R3 #4
        MOV R5 #15
        AND R3 R3 R5
        MOV R5 #10
        CMP R3 R5
        BRP HF3
        BRZ HF3
        MOV R0 #48
        ADD R0 R0 R3
        TRAP 0x21
        BRNZP HN4
HF3
        MOV R0 #55
        ADD R0 R0 R3
        TRAP 0x21
HN4
        MOV R5 #15
        AND R3 R2 R5
        MOV R5 #10
        CMP R3 R5
        BRP HF4
        BRZ HF4
        MOV R0 #48
        ADD R0 R0 R3
        TRAP 0x21
        BRNZP HDONE
HF4
        MOV R0 #55
        ADD R0 R0 R3
        TRAP 0x21
HDONE
        LOAD R7 2(R6)
        LOAD R2 4(R6)
        LOAD R3 6(R6)
        LOAD R4 8(R6)
        LOAD R5 10(R6)
        RET


; Convierte R0 como entero binario sin signo de 16 bits y lo imprime.
SUB_BASE_BIN
        STORE R7 2(R6)
        STORE R2 4(R6)
        STORE R3 6(R6)
        STORE R4 8(R6)
        STORE R5 10(R6)

        OR R2 R0 R0

        MOV R0 #48
        TRAP 0x21
        MOV R0 #98
        TRAP 0x21

        MOV R4 #16
        MOV R5 #1
BIN_LOOP
        MOV R5 #1
        MOV R0 #0
        OR R3 R2 R0
        SHR R3 R3 #15
        AND R3 R3 R5
        CMP R3 R5
        BRZ BIN_UNO
        MOV R0 #48
        TRAP 0x21
        BRNZP BIN_DESPLAZA
BIN_UNO
        MOV R0 #49
        TRAP 0x21
BIN_DESPLAZA
        SHL R2 R2 #1
        ADD R4 R4 #-1
        MOV R5 #0
        CMP R4 R5
        BRP BIN_LOOP

        LOAD R7 2(R6)
        LOAD R2 4(R6)
        LOAD R3 6(R6)
        LOAD R4 8(R6)
        LOAD R5 10(R6)
        RET

.END