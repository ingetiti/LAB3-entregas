
.ORIG x3000

; ==========================================
; PRUEBA 4: MEMORIA
; ==========================================

; R0 apunta a DATA
; DATA inicialmente contiene x807F

LEA R0, DATA
LEA R4, INITIAL
LDW R1, R4, #0

; ------------------------------------------
; 1) STW y LDW
; Escribir y leer x807F
; ------------------------------------------

STW R1, R0, #0
LDW R2, R0, #0

CMP R2, R1
BRnp ERROR

; ------------------------------------------
; 2) LDBL
; Byte bajo = x7F
; Resultado esperado = x007F
; ------------------------------------------

LDBL R2, R0, #0

LEA R4, EXPECT_LOW
LDW R3, R4, #0

CMP R2, R3
BRnp ERROR

; ------------------------------------------
; 3) LDBH
; Byte alto = x80
; Extensión de signo = xFF80
; ------------------------------------------

LDBH R2, R0, #0

LEA R4, EXPECT_HIGH
LDW R3, R4, #0

CMP R2, R3
BRnp ERROR

; ------------------------------------------
; 4) STBL
; Escribir xAA en byte bajo
; La palabra debe quedar x80AA
; ------------------------------------------

LEA R4, VALUE_AA
LDW R5, R4, #0

STBL R5, R0, #0
LDW R2, R0, #0

LEA R4, EXPECT_80AA
LDW R3, R4, #0

CMP R2, R3
BRnp ERROR

; ------------------------------------------
; 5) STBH
; Escribir xBB en byte alto
; La palabra debe quedar xBBAA
; ------------------------------------------

LEA R4, VALUE_BB
LDW R5, R4, #0

STBH R5, R0, #0
LDW R2, R0, #0

LEA R4, EXPECT_BBAA
LDW R3, R4, #0

CMP R2, R3
BRnp ERROR

; ------------------------------------------
; 6) LDI
; PTR contiene la dirección de TARGET
; TARGET contiene x5678
; ------------------------------------------

LEA R3, PTR
LEA R4, TARGET
STW R4, R3, #0

LDI R5, R3, #0

LEA R4, EXPECT_5678
LDW R6, R4, #0

CMP R5, R6
BRnp ERROR

; ------------------------------------------
; 7) STI
; Almacenar x9ABC en TARGET indirectamente
; ------------------------------------------

LEA R4, VALUE_9ABC
LDW R5, R4, #0

STI R5, R3, #0

; Verificar directamente el destino
LEA R4, TARGET
LDW R6, R4, #0

CMP R5, R6
BRnp ERROR

; ==========================================
; TODAS LAS PRUEBAS PASARON
; ==========================================

LEA R0, MSG_OK
TRAP x22
HALT

ERROR:
LEA R0, MSG_ERROR
TRAP x22
HALT

; ==========================================
; DATOS
; ==========================================

DATA:
.FILL x807F

PTR:
.FILL #0

TARGET:
.FILL x5678

INITIAL:
.FILL x807F

EXPECT_LOW:
.FILL x007F

EXPECT_HIGH:
.FILL xFF80

VALUE_AA:
.FILL x00AA

VALUE_BB:
.FILL x00BB

EXPECT_80AA:
.FILL x80AA

EXPECT_BBAA:
.FILL xBBAA

EXPECT_5678:
.FILL x5678

VALUE_9ABC:
.FILL x9ABC

MSG_OK:
.STRINGZ "OK: MEMORIA"

MSG_ERROR:
.STRINGZ "ERROR: MEMORIA"

.END
