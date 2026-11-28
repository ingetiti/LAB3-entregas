.ORIG x3000

; Base aritmetica
AND R0, R0, #0
ADD R0, R0, #5
AND R1, R1, #0
ADD R1, R1, #2
ADD R2, R0, R1
SUB R3, R0, R1
AND R4, R0, R1
OR R5, R0, R1
XOR R6, R0, R1
NOT R7, R0

; Hardware matematico
MUL R2, R0, R1
DIV R3, R0, R1
CMP R3, R1
BRz CMP_OK
BRnzp FIN
CMP_OK
AND R7, R7, #0

; Memoria word por PC
LEA R6, WORD
STW R0, WORD
LDW R1, WORD

; Memoria base/offset word y byte
STRW R0, R6, #0
LDRW R2, R6, #0
STRB R0, R6, #1
LDRB R3, R6, #1

; Memoria byte por PC
STB R0, BYTE
LDB R4, BYTE

; Memoria indirecta word
STIW R0, PTR
LDIW R5, PTR

; Memoria indirecta byte
STIB R0, BPTR
LDIB R7, BPTR

; Desplazamientos
SHF R2, R0, LSHF, #2
SHF R3, R0, RSHF, #1

; Jumps y subrutina
JSR FUNC
LEA R6, FUNC2
JSRR R6
LEA R7, RTI_TEST
JMP R7

FUNC
ADD R7, R7, #0
RET

FUNC2
ADD R7, R7, #0
RET

RTI_TEST
LEA R7, FIN
RTI

FIN
TRAP x25

PTR .FILL WORD
BPTR .FILL BYTE
WORD .FILL x0000
BYTE .FILL x0000
.END