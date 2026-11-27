
.ORIG x3000

; ==========================================
; PRUEBA 1: JSR
; ==========================================

AND R2, R2, #0

JSR SUB_JSR

; Si JSR regreso correctamente, R2 debe valer 5
AND R4, R4, #0
ADD R4, R4, #5
CMP R2, R4
BRnp ERROR_JSR

; ==========================================
; PRUEBA 2: JSRR
; ==========================================

LEA R3, SUB_JSRR
JSRR R3

; Si JSRR regreso correctamente, R2 debe valer 9
AND R4, R4, #0
ADD R4, R4, #7
ADD R4, R4, #2
CMP R2, R4
BRnp ERROR_JSRR

; ==========================================
; PRUEBA 3: JMP mediante registro
; ==========================================

LEA R5, DESTINO_JMP
JMP R5

; Esta instruccion no debe ejecutarse
FALLO_JMP:
    BRnzp ERROR_JMP

DESTINO_JMP:
    AND R6, R6, #0
    ADD R6, R6, #7

; Comprobar que llegamos al destino
AND R4, R4, #0
ADD R4, R4, #7
CMP R6, R4
BRnp ERROR_JMP

; ==========================================
; RESULTADO CORRECTO
; ==========================================

LEA R0, MSG_OK
TRAP x22
HALT

; ==========================================
; SUBRUTINA JSR
; ==========================================

SUB_JSR:
    ADD R2, R2, #5
    JMP R7

; ==========================================
; SUBRUTINA JSRR
; ==========================================

SUB_JSRR:
    AND R2, R2, #0
    ADD R2, R2, #7
    ADD R2, R2, #2
    JMP R7

; ==========================================
; MENSAJES DE ERROR
; ==========================================

ERROR_JSR:
    LEA R0, MSG_JSR
    TRAP x22
    HALT

ERROR_JSRR:
    LEA R0, MSG_JSRR
    TRAP x22
    HALT

ERROR_JMP:
    LEA R0, MSG_JMP
    TRAP x22
    HALT

MSG_OK:
    .STRINGZ "OK: SUBRUTINAS Y SALTOS"

MSG_JSR:
    .STRINGZ "ERROR: JSR O RETORNO"

MSG_JSRR:
    .STRINGZ "ERROR: JSRR O RETORNO"

MSG_JMP:
    .STRINGZ "ERROR: JMP"

.END

