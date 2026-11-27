        .ORIG x3000

; ==========================================
; PRUEBA 04 - DETERMINAR CUADRANTE (Casos normales)
;
; Entrada:
; R0 = Angulo en Q3.12
;
; Salida:
; R1 = Numero de cuadrante (1, 2, 3 o 4)
;
; Temporales:
; R2, R3, R4
; ==========================================

INICIO
        AND R1, R1, #0 ; Inicializar registro de salida en 0

; ------------------------------------------
; CARGAR ANGULO DE PRUEBA
; En el programa integrado, R0 ya vendra
; cargado desde el modulo de la interfaz.
; ------------------------------------------

        LEA R4, ANGULO_PRUEBA
        LDR R0, R4, #0

; ------------------------------------------
; COMPARAR CON PI/2
; ------------------------------------------
COMPROBAR_CUADRANTE_1
        LEA R4, PI_SOBRE_2
        LDR R3, R4, #0        ; R3 = PI/2

        NOT R3, R3
        ADD R3, R3, #1        ; R3 = -PI/2

        ADD R2, R0, R3        ; R2 = angulo - PI/2

        BRn CUADRANTE_1       ; Si es negativo, cuadrante 1

; ------------------------------------------
; COMPARAR CON PI
; ------------------------------------------
COMPROBAR_CUADRANTE_2
        LDR R3, R4, #1        ; R3 = PI

        NOT R3, R3
        ADD R3, R3, #1        ; R3 = -PI

        ADD R2, R0, R3        ; R2 = angulo - PI

        BRn CUADRANTE_2       ; Si es negativo, cuadrante 2

; ------------------------------------------
; COMPARAR CON 3PI/2
; ------------------------------------------
COMPROBAR_CUADRANTE_3
        LDR R3, R4, #2        ; R3 = 3PI/2

        NOT R3, R3
        ADD R3, R3, #1        ; R3 = -3PI/2

        ADD R2, R0, R3        ; R2 = angulo - 3PI/2

        BRn CUADRANTE_3       ; Si es negativo, cuadrante 3

; ------------------------------------------
; SI SUPERA LOS LIMITES ANTERIORES:
; CUADRANTE 4 - Caso por descarte
; ------------------------------------------
COMPROBAR_CUADRANTE_4
        ADD R1, R1, #4
        BR FIN

; ------------------------------------------
; ASIGNAR CUADRANTES
; ------------------------------------------

CUADRANTE_1
        ADD R1, R1, #1
        BR FIN

CUADRANTE_2
        ADD R1, R1, #2
        BR FIN

CUADRANTE_3
        ADD R1, R1, #3

FIN
        HALT

; ==========================================
; DATOS DE PRUEBA
; ==========================================

ANGULO_PRUEBA .FILL #20000

; ==========================================
; CONSTANTES Q3.12
; ==========================================

PI_SOBRE_2 .FILL #6434 ; 90 grados

PI .FILL #12868 ; 180 grados

TRES_PI_SOBRE_2 .FILL #19302 ; 270 grados

DOS_PI .FILL #25736 ; 360 grados

        .END