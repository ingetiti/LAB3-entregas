
.ORIG x3000

; ==========================================
; PRUEBA 2: DESPLAZAMIENTOS
; ==========================================

; ------------------------------------------
; 1) SHL: 5 << 2 = 20
; ------------------------------------------

AND R0, R0, #0
ADD R0, R0, #5

SHL R2, R0, #2

AND R3, R3, #0
ADD R3, R3, #7
ADD R3, R3, #7
ADD R3, R3, #6

CMP R2, R3
BRnp ERROR

; ------------------------------------------
; 2) SHR: 20 >> 2 = 5
; ------------------------------------------

SHR R2, R2, #2

CMP R2, R0
BRnp ERROR

; ------------------------------------------
; 3) SHR LOGICO CON NUMERO NEGATIVO
;
; -16 = 0xFFF0
; SHR(-16, 2) = 0x3FFC
; ------------------------------------------

AND R1, R1, #0
ADD R1, R1, #-8
ADD R1, R1, #-8

SHR R2, R1, #2

LEA R4, EXPECT_SHR
LDW R3, R4, #0

CMP R2, R3
BRnp ERROR

; ------------------------------------------
; 4) SAR: -16 >> 2 = -4
; ------------------------------------------

SAR R2, R1, #2

CMP R2, #-4
BRnp ERROR

; ------------------------------------------
; 5) SAR POSITIVO: 20 >> 2 = 5
; ------------------------------------------

SAR R2, R3, #2

; R3 contiene 0x3FFC, así que no usamos
; este resultado como referencia.
; Reconstruimos 20 en R4.

AND R4, R4, #0
ADD R4, R4, #7
ADD R4, R4, #7
ADD R4, R4, #6

SAR R2, R4, #2

CMP R2, R0
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

MSG_OK:
.STRINGZ "OK: DESPLAZAMIENTOS"

MSG_ERROR:
.STRINGZ "ERROR: DESPLAZAMIENTO INCORRECTO"

EXPECT_SHR:
.FILL x3FFC

.END
