.ORIG x3000
    BR main

;   ============================================================================
;       Programa de ENTRADA para pruebas del menu (LC-3X)
;       Grupo 27
;   ============================================================================

.EXTERNAL G27_MAIN_MENU_PROGRESO-MAIN_MENU
sub_main_menu       .FILL G27_MAIN_MENU_PROGRESO-MAIN_MENU

main
    AND R0 R0 #0                        ; 0 es nullptr (mostrar menu interactivo)
    ;LEA R0 programa_del_menu           ; prueba automatizada reducida
    LEA R0 programa_del_menu_completo   ; prueba automatizada completa

    LD R1 sub_main_menu
    JSRR R1
    HALT

; ============================================================================
; Bloque de Operaciones para correr AUTOMATICAMENTE en el menu
; Cada entrada: [indice_op, op_a, op_b, res_lo, res_hi] (5 words = 10 bytes)
; ============================================================================

programa_del_menu
    .FILL   #1      ; modo verboso
    
    .FILL   #15     ; MULTIPLICACION BOOTH
    .FILL   x3396   ; Valor 13,265625 (Q7.8)
    .FILL   xF8C3   ; Valor -7,23828125 (Q7.8)
    .FILL   #0      ; Espacio para resultado
    .FILL   #0      ; Espacio para resultado
    
    .FILL   #9      ; SQRT NEWTONRAPHSON
    .FILL   x0002   ; Valor 2.0 (Q15.16 entero)
    .FILL   x0000   ; (Q15.16 fraccion)
    .FILL   #0      ; Espacio para resultado entero
    .FILL   #0      ; Espacio para resultado fraccion

    .FILL   #5      ; COSENO TABLA
    .FILL   x1921   ; Valor 1.5708 (Q3.12)
    .FILL   #0
    .FILL   #0      ; Espacio para resultado (Q1.14)
    .FILL   #0

    .FILL   #0      ; SALIR

programa_del_menu_completo
    .FILL   #1      ; modo verboso

    .FILL   #1      ; REDUCCION DE ARGUMENTO: pi/2 (Q3.12)
    .FILL   #9651   ; pi ~= 3.1415/2
    .FILL   #0
    .FILL   #0
    .FILL   #0

    .FILL   #2      ; SENO TAYLOR: 60 grados
    .FILL   #600
    .FILL   #0
    .FILL   #0
    .FILL   #0

    .FILL   #3      ; SENO TABLA: pi/3 (Q3.12)
    .FILL   #4289
    .FILL   #0
    .FILL   #0
    .FILL   #0

    .FILL   #4      ; SENO CHEBYSHEV-PADE: pi/3 (Q3.12)
    .FILL   #4289
    .FILL   #0
    .FILL   #0
    .FILL   #0

    .FILL   #5      ; COSENO: pi/3 (Q3.12)
    .FILL   #4289
    .FILL   #0
    .FILL   #0
    .FILL   #0

    .FILL   #6      ; CAMBIO DE BASE A HEX
    .FILL   #1342
    .FILL   #0
    .FILL   #0
    .FILL   #0

    .FILL   #7      ; CAMBIO DE BASE A BIN
    .FILL   xFBCA
    .FILL   #0
    .FILL   #0
    .FILL   #0

    .FILL   #8      ; SQRT NON RESTORING (Q7.8)
    .FILL   #1115
    .FILL   #0
    .FILL   #0
    .FILL   #0

    .FILL   #9      ; SQRT NEWTON-RAPHSON (DQ15.16)
    .FILL   #4
    .FILL   #23395
    .FILL   #0
    .FILL   #0

    .FILL   #10     ; EXPONENCIACION (Q3.12)
    .FILL   #4096
    .FILL   #0
    .FILL   #0
    .FILL   #0

    .FILL   #11     ; POTENCIA POR MULTIPLICACIONES (Q7.8)
    .FILL   #-512
    .FILL   #5
    .FILL   #0
    .FILL   #0

    .FILL   #12     ; POTENCIA EXPONENCIAL BINARIA (entero)
    .FILL   #-2
    .FILL   #5
    .FILL   #0
    .FILL   #0

    .FILL   #13     ; MULTIPLICACION CORDIC (Q7.8)
    .FILL   x0DD4
    .FILL   xF8C3
    .FILL   #0
    .FILL   #0

    .FILL   #14     ; MULTIPLICACION SHIFT-SUMA (DQ15.16)
    .FILL   x0DD4
    .FILL   xF8C3
    .FILL   #0
    .FILL   #0

    .FILL   #15     ; MULTIPLICACION BOOTH (Q7.8)
    .FILL   x0DD4
    .FILL   xF8C3
    .FILL   #0
    .FILL   #0

    .FILL   #16     ; DIVISION LARGA (Q7.8)
    .FILL   #1630
    .FILL   #828
    .FILL   #0
    .FILL   #0

    .FILL   #17     ; DIVISION NEWTON-RAPHSON (Q7.8)
    .FILL   #1630
    .FILL   #828
    .FILL   #0
    .FILL   #0

    .FILL   #18     ; DIVISION CORDIC (Q0.15)
    .FILL   x2000
    .FILL   x599A
    .FILL   #0
    .FILL   #0

    .FILL   #19     ; LOGARITMO BORCHARDT (Q7.8)
    .FILL   x0100
    .FILL   #0
    .FILL   #0
    .FILL   #0

    .FILL   #20     ; LOGARITMO CORDIC (Q3.12)
    .FILL   x2000
    .FILL   #0
    .FILL   #0
    .FILL   #0

    .FILL   #21     ; MAXIMO COMUN DIVISOR (entero)
    .FILL   #48
    .FILL   #18
    .FILL   #0
    .FILL   #0

    .FILL   #22     ; MINIMO COMUN MULTIPLO (entero)
    .FILL   #16
    .FILL   #38
    .FILL   #0
    .FILL   #0

    .FILL   #23     ; CONVERSION Q3.12 A Q7.8
    .FILL   #21980
    .FILL   #0
    .FILL   #0
    .FILL   #0

    .FILL   #0      ; SALIR

.END
