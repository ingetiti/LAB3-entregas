        .ORIG x3000

; ==========================================
; PRUEBA 06 - ANGULO DE REFERENCIA Y COFUNCION
;
; Entrada:
; R0 = Angulo en Q3.12
;
; Salida:
; R1 = Numero de cuadrante (1, 2, 3 o 4)
; R2 = Angulo de referencia en Q3.12 (indice Seno)
; R3 = Angulo de cofuncion en Q3.12 (indice Coseno)
;
; Temporales:
; R4
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
        LDR R1, R4, #0  ; R1 = PI/2
        NOT R1, R1
        ADD R1, R1, #1  ; R1 = -PI/2
        ADD R2, R0, R1  ; R2 = ANGULO - PI/2
        BRz CASO_ESPECIAL

; ------------------------------------------
; COMPROBAR CASO ESPECIAL: 180 GRADOS
; ------------------------------------------

COMPROBAR_180
        LDR R1, R4, #1  ; R1 = PI
        NOT R1, R1
        ADD R1, R1, #1  ; R1 = -PI
        ADD R2, R0, R1  ; R2 = ANGULO - PI
        BRz CASO_ESPECIAL

; ------------------------------------------
; COMPROBAR CASO ESPECIAL: 270 GRADOS
; ------------------------------------------

COMPROBAR_270
        LDR R1, R4, #2  ; R1 = 3PI/2
        NOT R1, R1
        ADD R1, R1, #1  ; R1 = -3PI/2
        ADD R2, R0, R1  ; R2 = ANGULO - 3PI/2
        BRz CASO_ESPECIAL

; ------------------------------------------
; COMPROBAR CASO ESPECIAL: 360 GRADOS
; ------------------------------------------

COMPROBAR_360
        LDR R1, R4, #3  ; R1 = 2PI
        NOT R1, R1
        ADD R1, R1, #1  ; R1 = -2PI
        ADD R2, R0, R1  ; R2 = ANGULO - 2PI
        BRz CASO_ESPECIAL

; ------------------------------------------
; SI NO ES ESPECIAL, DETERMINAR CUADRANTE
; ------------------------------------------

COMPROBAR_CUADRANTE_1
        LDR R1, R4, #0  ; R1 = PI/2
        NOT R1, R1
        ADD R1, R1, #1  ; R1 = -PI/2
        ADD R2, R0, R1  ; R2 = ANGULO - PI/2
        BRn CUADRANTE_1

COMPROBAR_CUADRANTE_2
        LDR R1, R4, #1  ; R1 = PI
        NOT R1, R1
        ADD R1, R1, #1  ; R1 = -PI
        ADD R2, R0, R1  ; R2 = ANGULO - PI
        BRn CUADRANTE_2

COMPROBAR_CUADRANTE_3
        LDR R1, R4, #2  ; R1 = 3PI/2
        NOT R1, R1
        ADD R1, R1, #1  ; R1 = -3PI/2
        ADD R2, R0, R1  ; R2 = ANGULO - 3PI/2
        BRn CUADRANTE_3

COMPROBAR_CUADRANTE_4 ; Caso por descarte
        AND R1, R1, #0
        ADD R1, R1, #4
        BR CALCULAR_REFERENCIA_4

; ------------------------------------------
; CALCULAR ANGULO DE REFERENCIA
; ------------------------------------------

CUADRANTE_1
        AND R1, R1, #0
        ADD R1, R1, #1
        ADD R2, R0, #0  ; REFERENCIA = ANGULO
        BR CALCULAR_COFUNCION

CUADRANTE_2
        AND R1, R1, #0
        ADD R1, R1, #2
        LDR R2, R4, #1  ; R2 = PI
        NOT R2, R2
        ADD R2, R2, #1  ; R2 = -PI
        ADD R2, R0, R2  ; REFERENCIA = ANGULO - PI
        NOT R2, R2
        ADD R2, R2, #1  ; REFERENCIA = PI - ANGULO
        BR CALCULAR_COFUNCION

CUADRANTE_3
        AND R1, R1, #0
        ADD R1, R1, #3
        LDR R2, R4, #1  ; R2 = PI
        NOT R2, R2
        ADD R2, R2, #1  ; R2 = -PI
        ADD R2, R0, R2  ; REFERENCIA = ANGULO - PI
        BR CALCULAR_COFUNCION

CALCULAR_REFERENCIA_4
        LDR R2, R4, #3  ; R2 = 2PI
        NOT R2, R2
        ADD R2, R2, #1  ; R2 = -2PI
        ADD R2, R0, R2  ; R2 = ANGULO - 2PI
        NOT R2, R2
        ADD R2, R2, #1  ; REFERENCIA = 2PI - ANGULO

; ------------------------------------------
; CALCULAR ANGULO DE COFUNCION
; COFUNCION = PI/2 - REFERENCIA
; ------------------------------------------

CALCULAR_COFUNCION
        LDR R3, R4, #0  ; R3 = PI/2
        NOT R3, R3
        ADD R3, R3, #1  ; R3 = -PI/2
        ADD R3, R2, R3  ; R3 = REFERENCIA - PI/2
        NOT R3, R3
        ADD R3, R3, #1  ; R3 = PI/2 - REFERENCIA
        BR FIN

; ------------------------------------------
; CASO ESPECIAL
; R1 = 0
; NO SE CALCULAN REFERENCIA NI COFUNCION
; ------------------------------------------

CASO_ESPECIAL
        AND R1, R1, #0
        AND R2, R2, #0
        AND R3, R3, #0
        BR FIN

FIN
        HALT

; ==========================================
; DATOS DE PRUEBA
; ==========================================

ANGULO_PRUEBA .FILL #22000

; ==========================================
; CONSTANTES Q3.12
; ==========================================

PI_SOBRE_2 .FILL #6434 ; 90 grados

PI .FILL #12868 ; 180 grados

TRES_PI_SOBRE_2 .FILL #19302 ; 270 grados

DOS_PI .FILL #25736 ; 360 grados

        .END