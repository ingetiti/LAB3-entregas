.ORIG x3000

; ==========================================
; PRUEBA 1: ARITMETICA Y LOGICA
; ==========================================

; Inicializar operandos:
; R0 = 12
; R1 = 10

AND R0, R0, #0
ADD R0, R0, #7
ADD R0, R0, #5

AND R1, R1, #0
ADD R1, R1, #7
ADD R1, R1, #3

; 1) ADD: 12 + 10 = 22

ADD R2, R0, R1

AND R3, R3, #0
ADD R3, R3, #7
ADD R3, R3, #7
ADD R3, R3, #7
ADD R3, R3, #1

CMP R2, R3
BRnp ERROR

; 2) SUB: 12 - 10 = 2

SUB R2, R0, R1

AND R3, R3, #0
ADD R3, R3, #2

CMP R2, R3
BRnp ERROR

; 3) AND: 1100 AND 1010 = 1000 (8)

AND R2, R0, R1

AND R3, R3, #0
ADD R3, R3, #7
ADD R3, R3, #1

CMP R2, R3
BRnp ERROR

; 4) OR: 1100 OR 1010 = 1110 (14)

OR R2, R0, R1

AND R3, R3, #0
ADD R3, R3, #7
ADD R3, R3, #7

CMP R2, R3
BRnp ERROR

; 5) XOR: 1100 XOR 1010 = 0110 (6)

XOR R2, R0, R1

AND R3, R3, #0
ADD R3, R3, #6

CMP R2, R3
BRnp ERROR

; 6) NOT: NOT(10) + 10 = -1

NOT R2, R1
ADD R2, R2, R1

CMP R2, #-1
BRnp ERROR

; Todas las pruebas pasaron

LEA R0, MSG_OK
TRAP x22
HALT

ERROR:
LEA R0, MSG_ERROR
TRAP x22
HALT

MSG_OK:
.STRINGZ "OK: ARITMETICA Y LOGICA"

MSG_ERROR:
.STRINGZ "ERROR: RESULTADO INCORRECTO"

.END
