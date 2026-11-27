        .ORIG x3000

; ==========================================
; PRUEBA 05 - DETECCION DE CASOS ESPECIALES
;
; Entrada:
; R0 = Angulo en Q3.12
;
; Salida:
; R1 = 0 si es caso especial
; R1 = 1, 2, 3 o 4 si es cuadrante normal
;
; Temporales:
; R2, R3, R4
; ==========================================

INICIO
        AND R1, R1, #0 ; Inicializar registro de salida en 0

; ------------------------------------------
; CARGAR ANGULO DE PRUEBA
; ------------------------------------------

        LEA R4, ANGULO_PRUEBA 
        LDR R0, R4, #0

; ------------------------------------------
; COMPROBAR CASO ESPECIAL: 0 GRADOS
; ------------------------------------------

COMPROBAR_CERO
        BRz CASO_ESPECIAL

; ------------------------------------------
; CARGAR DIRECCION DE CONSTANTES
; ------------------------------------------

        LEA R4, PI_SOBRE_2

; ------------------------------------------
; COMPROBAR CASO ESPECIAL: 90 GRADOS
; ------------------------------------------

COMPROBAR_90
        LDR R3, R4, #0  ; R3 = PI/2
        NOT R3, R3
        ADD R3, R3, #1  ; R3 = -PI/2
        ADD R2, R0, R3  ; R2 = ANGULO - PI/2
        BRz CASO_ESPECIAL ; SI DA 0, CASO ESPECIAL 90 GRADOS

; ------------------------------------------
; COMPROBAR CASO ESPECIAL: 180 GRADOS
; ------------------------------------------

COMPROBAR_180
        LDR R3, R4, #1  ; R3 = PI
        NOT R3, R3
        ADD R3, R3, #1  ; R3 = -PI
        ADD R2, R0, R3  ; R2 = ANGULO - PI
        BRz CASO_ESPECIAL ; SI DA 0, CASO ESPECIAL 180 GRADOS

; ------------------------------------------
; COMPROBAR CASO ESPECIAL: 270 GRADOS
; ------------------------------------------

COMPROBAR_270
        LDR R3, R4, #2  ; R3 = 3PI/2
        NOT R3, R3
        ADD R3, R3, #1  ; R3 = -3PI/2
        ADD R2, R0, R3  ; R2 = ANGULO - 3PI/2
        BRz CASO_ESPECIAL ; SI DA 0, CASO ESPECIAL 270 GRADOS

; ------------------------------------------
; COMPROBAR CASO ESPECIAL: 360 GRADOS
; ------------------------------------------

COMPROBAR_360
        LDR R3, R4, #3  ; R3 = 2PI
        NOT R3, R3
        ADD R3, R3, #1  ; R3 = -2PI
        ADD R2, R0, R3  ; R2 = ANGULO - 2PI
        BRz CASO_ESPECIAL ; SI DA 0, CASO ESPECIAL 360 GRADOS

; ------------------------------------------
; SI NO ES ESPECIAL, DETERMINAR CUADRANTE
; ------------------------------------------

COMPROBAR_CUADRANTE_1
        LDR R3, R4, #0  ; R3 = PI/2
        NOT R3, R3      
        ADD R3, R3, #1  ; R3 = -PI/2
        ADD R2, R0, R3  ; R2 = angulo - PI/2
        BRn CUADRANTE_1 ; Si es negativo, cuadrante 1

COMPROBAR_CUADRANTE_2
        LDR R3, R4, #1  ; R3 = PI
        NOT R3, R3      
        ADD R3, R3, #1  ; R3 = -PI
        ADD R2, R0, R3  ; R2 = angulo - PI
        BRn CUADRANTE_2 ; Si es negativo, cuadrante 2

COMPROBAR_CUADRANTE_3
        LDR R3, R4, #2  ; R3 = 3PI/2
        NOT R3, R3
        ADD R3, R3, #1  ; R3 = -3PI/2
        ADD R2, R0, R3  ; R2 = angulo - 3PI/2
        BRn CUADRANTE_3 ; Si es negativo, cuadrante 3

COMPROBAR_CUADRANTE_4 ; Caso por descarte
        ADD R1, R1, #4 
        BR FIN

; ------------------------------------------
; CASO ESPECIAL
; R1 YA CONTIENE 0
; ------------------------------------------

CASO_ESPECIAL
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

ANGULO_PRUEBA .FILL #22000

; ==========================================
; CONSTANTES Q3.12
; ==========================================

PI_SOBRE_2 .FILL #6434

PI .FILL #12868

TRES_PI_SOBRE_2 .FILL #19302

DOS_PI .FILL #25736

        .END
