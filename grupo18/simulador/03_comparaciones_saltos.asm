
.ORIG x3000

; ==========================================
; PRUEBA 3: CMP Y SALTOS CONDICIONALES
; ==========================================

; R0 = -2
; R1 =  1

AND R0, R0, #0
ADD R0, R0, #-2

AND R1, R1, #0
ADD R1, R1, #1

; ------------------------------------------
; 1) BRn: debe saltar si el resultado es N
; ------------------------------------------

CMP R0, R1
BRn N_OK
BRnzp ERROR

N_OK:

; ------------------------------------------
; 2) BRz: debe saltar si el resultado es Z
; ------------------------------------------

CMP R0, R0
BRz Z_OK
BRnzp ERROR

Z_OK:

; ------------------------------------------
; 3) BRp: debe saltar si el resultado es P
; ------------------------------------------

CMP R1, R0
BRp P_OK
BRnzp ERROR

P_OK:

; ------------------------------------------
; 4) BRnz: debe saltar con N
; ------------------------------------------

CMP R0, R1
BRnz NZ_OK
BRnzp ERROR

NZ_OK:

; BRnz NO debe saltar con P

CMP R1, R0
BRnz ERROR

; ------------------------------------------
; 5) BRnp: debe saltar con N
; ------------------------------------------

CMP R0, R1
BRnp NP_OK
BRnzp ERROR

NP_OK:

; BRnp NO debe saltar con Z

CMP R0, R0
BRnp ERROR

; ------------------------------------------
; 6) BRzp: debe saltar con P
; ------------------------------------------

CMP R1, R0
BRzp ZP_OK
BRnzp ERROR

ZP_OK:

; BRzp NO debe saltar con N

CMP R0, R1
BRzp ERROR

; ------------------------------------------
; 7) BRnzp: siempre debe saltar
; ------------------------------------------

BRnzp ALWAYS_OK
BRnzp ERROR

ALWAYS_OK:

; ------------------------------------------
; 8) CMP con inmediato
; R1 = 1
; CMP R1, #-1 => positivo
; ------------------------------------------

CMP R1, #-1
BRp IMM_OK
BRnzp ERROR

IMM_OK:

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
.STRINGZ "OK: CMP Y SALTOS"

MSG_ERROR:
.STRINGZ "ERROR: CMP O BR INCORRECTO"

.END
