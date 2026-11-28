;=====================================================================
; SUBRUTINA: Reduccion_Argumento (Reducción de argumento en Q3.12)
;
;   Entrada:  R0 = ángulo theta en radianes (formato Q3.12 con signo)
;   Salida:   R0 = ángulo reducido en rango aproximado [-Pi/2, +Pi/2] (Q3.12)
;   Conserva: R1-R7 (todos intactos, incluyendo R6).
;=====================================================================
Reduccion_Argumento:
        ST      R1, GUARDADO_R1
        ST      R2, GUARDADO_R2
        ST      R3, GUARDADO_R3
        ST      R4, GUARDADO_R4
        ST      R5, GUARDADO_R5
        ST      R7, GUARDADO_R7

        LD      R4, PI_Q12          ; R4 = +Pi en Q3.12 (12868)
        LD      R5, NPI_Q12         ; R5 = -Pi en Q3.12 (-12868)

        ; --- Caso positivo: si theta > Pi/2, reducir usando DIV y MUL ---
        LD      R1, NPI_DOS         ; -Pi/2
        ADD     R2, R0, R1          ; R2 = theta - Pi/2
        BRnz    REDUCCION_NEG

        ; k = (theta + Pi/2) / Pi
        LD      R1, PI_DOS
        ADD     R2, R0, R1          ; R2 = theta + Pi/2
        DIV     R2, R2, R4          ; R2 = k múltiplos de Pi a restar

        ; theta = theta - k * Pi
        MUL     R1, R2, R4          ; R1 = k * Pi
        NOT     R1, R1
        ADD     R1, R1, #1
        ADD     R0, R0, R1          ; R0 = theta - k * Pi

        ; Ajuste fino por si theta > Pi/2 tras el cálculo entero
REDUCCION_POS:
        LD      R1, NPI_DOS
        ADD     R2, R0, R1          ; R2 = theta - Pi/2
        BRnz    REDUCCION_NEG
        ADD     R0, R0, R5          ; theta -= Pi
        BR      REDUCCION_POS

        ; --- Caso negativo: si theta < -Pi/2, llevar al rango ---
REDUCCION_NEG:
        LD      R1, PI_DOS          ; +Pi/2
        ADD     R2, R0, R1          ; R2 = theta + Pi/2
        BRzp    FIN

        ; k = (-theta + Pi/2) / Pi
        NOT     R2, R0
        ADD     R2, R2, #1          ; R2 = -theta
        ADD     R2, R2, R1          ; R2 = -theta + Pi/2
        DIV     R2, R2, R4          ; R2 = k múltiplos de Pi a sumar

        ; theta = theta + k * Pi
        MUL     R1, R2, R4          ; R1 = k * Pi
        ADD     R0, R0, R1

AJUSTE_NEG_LOOP:
        LD      R1, PI_DOS
        ADD     R2, R0, R1          ; R2 = theta + Pi/2
        BRzp    FIN
        ADD     R0, R0, R4          ; theta += Pi
        BR      AJUSTE_NEG_LOOP

FIN:
        LD      R1, GUARDADO_R1
        LD      R2, GUARDADO_R2
        LD      R3, GUARDADO_R3
        LD      R4, GUARDADO_R4
        LD      R5, GUARDADO_R5
        LD      R7, GUARDADO_R7
        ADD     R0, R0, #0          ; Actualizar CC según resultado en R0
        RET

;=====================================================================
; ZONA DE DATOS Y CONSTANTES (Q3.12)
;=====================================================================
PI_Q12:         .FILL #12868        ; round(pi * 4096)
NPI_Q12:        .FILL #-12868       ; -round(pi * 4096)
PI_DOS:         .FILL #6434         ; round((pi/2) * 4096)
NPI_DOS:        .FILL #-6434        ; -round((pi/2) * 4096)

GUARDADO_R1:    .FILL #0
GUARDADO_R2:    .FILL #0
GUARDADO_R3:    .FILL #0
GUARDADO_R4:    .FILL #0
GUARDADO_R5:    .FILL #0
GUARDADO_R7:    .FILL #0

.END