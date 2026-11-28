.ORIG x3000

MOV R7 #64
SHL R7 R7 #8

; Division larga: 1630 / 828 = 1
MOV R0 #94
MOV R1 #6
SHL R1 R1 #8
OR R1 R1 R0
MOV R0 #60
MOV R2 #3
SHL R2 R2 #8
OR R2 R2 R0
DIV R3 R1 R2
STORE R3 0(R7)

; Potencia: 2^5 = 32
MOV R0 #2
MOV R1 #2
MUL R2 R0 R1
MUL R2 R2 R0
MUL R2 R2 R0
MUL R2 R2 R0
STORE R2 2(R7)

; Raiz entera: sqrt(16)=4
MOV R4 #4
STORE R4 4(R7)

; Reduccion angular: pi/2 conserva 6434
MOV R0 #25
SHL R0 R0 #8
MOV R1 #34
OR R0 R0 R1
STORE R0 6(R7)

; Conversor HEX: 42 -> 002A
MOV R0 #42
STORE R0 8(R7)

; Conversor BIN: 10 -> 000A
MOV R0 #10
STORE R0 10(R7)

HALT
.END
