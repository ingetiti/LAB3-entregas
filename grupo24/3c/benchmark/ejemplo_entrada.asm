.ORIG x3000

; TRAP 0x23 lee una línea decimal y devuelve el valor en R0.
TRAP 0x23

; Conserva el número ingresado en la memoria de datos.
MOV R6 #64
SHL R6 R6 #8
STORE R0 0(R6)

HALT
.END
