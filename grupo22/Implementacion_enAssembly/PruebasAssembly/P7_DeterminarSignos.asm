        .ORIG x3000

; PRUEBA 7: DETERMINAR SIGNOS DE SENO Y COSENO

INICIO
        AND R1, R1, #0 ; Inicializar registro de cuadrante en 0

        LEA R4, PI_SOBRE_2 ; Cargar dirección de las constantes
        LEA R5, ANGULO_PRUEBA ; Cargar dirección del ángulo de prueba
        LDR R0, R5, #0 ; Cargar ángulo de entrada Q3.12

; --------------------------------------------------
; COMPROBACIÓN DE CASOS ESPECIALES
; --------------------------------------------------

COMPROBAR_CERO
        BRz CASO_ESPECIAL_CERO ; LDR actualizó NZP: si R0=0, es caso especial

COMPROBAR_90
        LDR R5, R4, #0 ; Cargar PI/2
        NOT R5, R5
        ADD R5, R5, #1
        ADD R5, R0, R5 ; Comparar ángulo con PI/2
        BRz CASO_ESPECIAL_90

COMPROBAR_180
        LDR R5, R4, #1 ; Cargar PI
        NOT R5, R5
        ADD R5, R5, #1
        ADD R5, R0, R5 ; Comparar ángulo con PI
        BRz CASO_ESPECIAL_180

COMPROBAR_270
        LDR R5, R4, #2 ; Cargar 3PI/2
        NOT R5, R5
        ADD R5, R5, #1
        ADD R5, R0, R5 ; Comparar ángulo con 3PI/2
        BRz CASO_ESPECIAL_270

COMPROBAR_360
        LDR R5, R4, #3 ; Cargar 2PI
        NOT R5, R5
        ADD R5, R5, #1
        ADD R5, R0, R5 ; Comparar ángulo con 2PI
        BRz CASO_ESPECIAL_360

; --------------------------------------------------
; DETERMINACIÓN DEL CUADRANTE
; --------------------------------------------------

COMPROBAR_CUADRANTE_1
        LDR R5, R4, #0 ; Cargar PI/2
        NOT R5, R5
        ADD R5, R5, #1
        ADD R2, R0, R5 ; Comparar ángulo con PI/2
        BRn CUADRANTE_1

COMPROBAR_CUADRANTE_2
        LDR R5, R4, #1 ; Cargar PI
        NOT R5, R5
        ADD R5, R5, #1
        ADD R2, R0, R5 ; Comparar ángulo con PI
        BRn CUADRANTE_2

COMPROBAR_CUADRANTE_3
        LDR R5, R4, #2 ; Cargar 3PI/2
        NOT R5, R5
        ADD R5, R5, #1
        ADD R2, R0, R5 ; Comparar ángulo con 3PI/2
        BRn CUADRANTE_3

COMPROBAR_CUADRANTE_4
        AND R1, R1, #0
        ADD R1, R1, #4 ; Identificar cuadrante 4
        BR CALCULAR_REFERENCIA_4

; --------------------------------------------------
; CÁLCULO DEL ÁNGULO DE REFERENCIA
; --------------------------------------------------

CUADRANTE_1
        AND R1, R1, #0
        ADD R1, R1, #1 ; Identificar cuadrante 1
        ADD R2, R0, #0 ; Referencia = ángulo original
        BR CALCULAR_COFUNCION

CUADRANTE_2
        AND R1, R1, #0
        ADD R1, R1, #2 ; Identificar cuadrante 2
        LDR R2, R4, #1 ; Cargar PI
        NOT R2, R2
        ADD R2, R2, #1
        ADD R2, R0, R2 ; Calcular ángulo - PI
        NOT R2, R2
        ADD R2, R2, #1 ; Referencia = PI - ángulo
        BR CALCULAR_COFUNCION

CUADRANTE_3
        AND R1, R1, #0
        ADD R1, R1, #3 ; Identificar cuadrante 3
        LDR R2, R4, #1 ; Cargar PI
        NOT R2, R2
        ADD R2, R2, #1
        ADD R2, R0, R2 ; Referencia = ángulo - PI
        BR CALCULAR_COFUNCION

CALCULAR_REFERENCIA_4
        LDR R2, R4, #3 ; Cargar 2PI
        NOT R2, R2
        ADD R2, R2, #1
        ADD R2, R0, R2 ; Calcular ángulo - 2PI
        NOT R2, R2
        ADD R2, R2, #1 ; Referencia = 2PI - ángulo

; --------------------------------------------------
; CÁLCULO DEL ÁNGULO COMPLEMENTARIO
; --------------------------------------------------

CALCULAR_COFUNCION
        LDR R3, R4, #0 ; Cargar PI/2
        NOT R3, R3
        ADD R3, R3, #1
        ADD R3, R2, R3 ; Calcular referencia - PI/2
        NOT R3, R3
        ADD R3, R3, #1 ; Cofunción = PI/2 - referencia
        BR DETERMINAR_SIGNOS

; --------------------------------------------------
; DETERMINACIÓN DE SIGNOS PARA CASOS NORMALES
; --------------------------------------------------

DETERMINAR_SIGNOS
        ADD R5, R1, #-1
        BRz SIGNOS_CUADRANTE_1

        ADD R5, R1, #-2
        BRz SIGNOS_CUADRANTE_2

        ADD R5, R1, #-3
        BRz SIGNOS_CUADRANTE_3

        BR SIGNOS_CUADRANTE_4

SIGNOS_CUADRANTE_1
        AND R0, R0, #0
        ADD R0, R0, #1 ; Signo del seno = +1
        AND R4, R4, #0
        ADD R4, R4, #1 ; Signo del coseno = +1
        BR GUARDAR_SIGNOS

SIGNOS_CUADRANTE_2
        AND R0, R0, #0
        ADD R0, R0, #1 ; Signo del seno = +1
        AND R4, R4, #0
        ADD R4, R4, #-1 ; Signo del coseno = -1
        BR GUARDAR_SIGNOS

SIGNOS_CUADRANTE_3
        AND R0, R0, #0
        ADD R0, R0, #-1 ; Signo del seno = -1
        AND R4, R4, #0
        ADD R4, R4, #-1 ; Signo del coseno = -1
        BR GUARDAR_SIGNOS

SIGNOS_CUADRANTE_4
        AND R0, R0, #0
        ADD R0, R0, #-1 ; Signo del seno = -1
        AND R4, R4, #0
        ADD R4, R4, #1 ; Signo del coseno = +1
        BR GUARDAR_SIGNOS

; --------------------------------------------------
; DETERMINACIÓN DE SIGNOS PARA CASOS ESPECIALES
; --------------------------------------------------

CASO_ESPECIAL_CERO
        AND R1, R1, #0
        AND R2, R2, #0
        AND R3, R3, #0
        AND R0, R0, #0
        ADD R4, R0, #1 ; Signo del coseno = +1
        BR GUARDAR_SIGNOS

CASO_ESPECIAL_90
        AND R1, R1, #0
        AND R2, R2, #0
        AND R3, R3, #0
        AND R0, R0, #0
        ADD R0, R0, #1 ; Signo del seno = +1
        AND R4, R4, #0 ; Signo del coseno = 0
        BR GUARDAR_SIGNOS

CASO_ESPECIAL_180
        AND R1, R1, #0
        AND R2, R2, #0
        AND R3, R3, #0
        AND R0, R0, #0 ; Signo del seno = 0
        AND R4, R4, #0
        ADD R4, R4, #-1 ; Signo del coseno = -1
        BR GUARDAR_SIGNOS

CASO_ESPECIAL_270
        AND R1, R1, #0
        AND R2, R2, #0
        AND R3, R3, #0
        AND R0, R0, #0
        ADD R0, R0, #-1 ; Signo del seno = -1
        AND R4, R4, #0 ; Signo del coseno = 0
        BR GUARDAR_SIGNOS

CASO_ESPECIAL_360
        AND R1, R1, #0
        AND R2, R2, #0
        AND R3, R3, #0
        AND R0, R0, #0 ; Signo del seno = 0
        AND R4, R4, #0
        ADD R4, R4, #1 ; Signo del coseno = +1

; --------------------------------------------------
; ALMACENAMIENTO DE SIGNOS EN MEMORIA
; --------------------------------------------------

GUARDAR_SIGNOS
        LEA R5, SIGNO_SENO
        STR R0, R5, #0 ; Guardar signo del seno

        LEA R5, SIGNO_COSENO
        STR R4, R5, #0 ; Guardar signo del coseno

FIN
        HALT

; --------------------------------------------------
; CONSTANTES Q3.12
; --------------------------------------------------

ANGULO_PRUEBA       .FILL #22000
PI_SOBRE_2          .FILL #6434 ; 90 grados
PI                  .FILL #12868 ; 180 grados
TRES_PI_SOBRE_2     .FILL #19302 ; 270 grados
DOS_PI              .FILL #25736 ; 360 grados

; --------------------------------------------------
; VARIABLES TEMPORALES
; --------------------------------------------------

SIGNO_SENO          .BLKW #1
SIGNO_COSENO        .BLKW #1

        .END