.ORIG x3000
                                BR main

;   ============================================================================
;       Programa de ENTRADA para pruebas del menu
;       *****************************************
;   ============================================================================
;
;   Metodologia:
;       Se puede probar el menu, de ditintas maneras:
;       -   Prueba de unicamente la interfaz (SIN SUBRUTINAS EXTERNAS).
;       -   Prueba de unicamente la interfaz en modo automatico (SIN SUBRUTINAS EXTERNAS).
;       -   Prueba con subrutinas externas.
;       -   Prueba con subrutinas externas en modo automatico.
;
;
;   (!) Para que se carguen correctamente las SUBRUTINAS EXTERNAS, tiene que estar *logeado*
;   con alguna cuenta (ya sea de grupo o administrador) y darle a *Ensamblar*.
;
;   (!) Para cambiar entre prueba SIN y CON SUBRUTINAS EXTERNAS, comente y descomente las
;   siguientes lineas:

; .EXTERNAL MAIN_MENU-MAIN_MENU                               ; <- Pruebas unicamente la interfaz.
; sub_main_menu       .FILL MAIN_MENU-MAIN_MENU               ; <- *

.EXTERNAL G27_MAIN_MENU_PROGRESO-MAIN_MENU
sub_main_menu:                  .FILL G27_MAIN_MENU_PROGRESO-MAIN_MENU ; <- *


;   (!) Para cambiar entre modo Mostrar interfaz, y modo Automatico, comente y descomente las
;   siguientes lineas:

main:
                                MOVI R0,#0                   ; <- 0 es nullptr (osea mostrar el menu normalmente)
     ;LEA R0 programa_del_menu            ; <- ptr (es para que automaticamente corra el programa de abajo)
                                LEA R0,programa_del_menu_completo ; <- ptr (es para que automaticamente corra el programa de abajo)

                                LD R1,sub_main_menu
                                JSRR R1
                                HALT


;   (i) Bloque de Operaciones para correr AUTOMATICAMENTE en el menu:
;   (vea archivo 'como_programar_bloque_automatizacion.asm' el grupo 27 para mas info).

programa_del_menu:
                                .FILL #1                     ;   modo verboso (muestra todos los valores por consola)

                                .FILL #15                    ;   MULTIPLICACION BOOTH        (Indice de operacion)
                                .FILL x3396                  ;   Valor 13,265625             (Q7.8)
                                .FILL xF8C3                  ;   Valor -7,23828125                   (Q7.8)
                                .FILL #0                     ;   Espacio para el resultado   (Q7.8)
                                .FILL #0                     ;   Espacio para el resultado   (Quedara en blanco)

                                .FILL #9                     ;   SQRT NEWTONRAPHSON          (Indice de operacion)
                                .FILL x0002                  ;   Valor 2.0                   (Q15.16)
                                .FILL x0000                  ;   *                           (DQ16 usa 2 WORD)
                                .FILL #0                     ;   Espacio para el resultado   (Q15.16)
                                .FILL #0                     ;   *                           (DQ16 usa 2 WORD)

                                .FILL #5                     ;   COSENO TABLA                (Indice de operacion)
                                .FILL x1921                  ;   Valor 1.5708                (Q3.12)
                                .FILL #0                     ;   *                           (Usa un solo operando)
                                .FILL #0                     ;   Espacio para el resultado   (Q1.14)
                                .FILL #0                     ;   Espacio para el resultado   (Quedara en blanco)

                                .FILL #0                     ;   SALIR


programa_del_menu_completo:
                                .FILL #1                     ; modo verboso: muestra cada operacion, sus operandos y su resultado

                                .FILL #1                     ; REDUCCION DE ARGUMENTO: pi/2 (Q3.12) debe permanecer aproximadamente igual
                                .FILL #9651                  ; pi ~= 3.1415/2
                                .FILL #0                     ; segundo operando no utilizado
                                .FILL #0                     ; resultado (Q3.12)
                                .FILL #0                     ; espacio sin uso

                                .FILL #2                     ; SENO TAYLOR: seno de 205 grados ~= -0.4226 (resultado Q3.12)
                                .FILL #600                   ; 60 grados, entero
                                .FILL #0                     ; segundo operando no utilizado
                                .FILL #0                     ; resultado (Q3.12)
                                .FILL #0                     ; espacio sin uso

                                .FILL #3                     ; SENO TABLA: seno(pi/2) ~= 1
                                .FILL #4289                  ; pi/3 (Q3.12)
                                .FILL #0                     ; segundo operando no utilizado
                                .FILL #0                     ; resultado (Q1.14)
                                .FILL #0                     ; espacio sin uso

                                .FILL #4                     ; SENO CHEBYSHEV-PADE: seno(pi/2) ~= 1
                                .FILL #4289                  ; pi/3 (Q3.12)
                                .FILL #0                     ; segundo operando no utilizado
                                .FILL #0                     ; resultado (Q1.14)
                                .FILL #0                     ; espacio sin uso

                                .FILL #5                     ; COSENO: coseno(pi/2) ~= 0
                                .FILL #4289                  ; pi/3 (Q3.12)
                                .FILL #0                     ; segundo operando no utilizado
                                .FILL #0                     ; resultado (Q1.14)
                                .FILL #0                     ; espacio sin uso

                                .FILL #6                     ; CAMBIO DE BASE A HEX: muestra el entero 42 en hexadecimal
                                .FILL #1342                  ; entero decimal
                                .FILL #0                     ; segundo operando no utilizado
                                .FILL #0                     ; resultado no aplica (se imprime en consola)
                                .FILL #0                     ; espacio sin uso

                                .FILL #7                     ; CAMBIO DE BASE A BIN: muestra el entero 10 en binario
                                .FILL xFBCA                  ; entero decimal
                                .FILL #0                     ; segundo operando no utilizado
                                .FILL #0                     ; resultado no aplica (se imprime en consola)
                                .FILL #0                     ; espacio sin uso

                                .FILL #8                     ; SQRT NON RESTORING: raiz(4) = 2
                                .FILL #1115                  ; 4,35698 (Q7.8)
                                .FILL #0                     ; segundo operando no utilizado
                                .FILL #0                     ; resultado (Q6.9)
                                .FILL #0                     ; espacio sin uso

                                .FILL #9                     ; SQRT NEWTON-RAPHSON: raiz(4) = 2
                                .FILL #4                     ; parte entera de 4.2339504128 (DQ15.16)
                                .FILL #23395                 ; parte fraccionaria de 4.2339504128 (DQ15.16)
                                .FILL #0                     ; parte entera del resultado (DQ15.16)
                                .FILL #0                     ; parte fraccionaria del resultado (DQ15.16)

                                .FILL #10                    ; EXPONENCIACION: e^(ln(2)) ~= 2
                                .FILL #4096                  ; 1  (Q3.12)
                                .FILL #0                     ; segundo operando no utilizado
                                .FILL #0                     ; resultado (Q7.8)
                                .FILL #0                     ; espacio sin uso

                                .FILL #11                    ; POTENCIA POR MULTIPLICACIONES: 2^3 = 8
                                .FILL #-512                  ; base -2.0 (Q7.8)
                                .FILL #5                     ; exponente entero
                                .FILL #0                     ; resultado (Q7.8)
                                .FILL #0                     ; espacio sin uso

                                .FILL #12                    ; POTENCIA EXPONENCIAL BINARIA: 2^5 = 32
                                .FILL #-2                    ; -2 base entera
                                .FILL #5                     ; exponente entero
                                .FILL #0                     ; resultado entero
                                .FILL #0                     ; espacio sin uso

                                .FILL #13                    ; MULTIPLICACION CORDIC: 3 * 4 = 12
                                .FILL x0DD4                  ;   Valor 13,265625             (Q7.8)
                                .FILL xF8C3                  ;   Valor -7,23828125           (Q7.8)
                                .FILL #0                     ; resultado (Q7.8)
                                .FILL #0                     ; espacio sin uso

                                .FILL #14                    ; MULTIPLICACION SHIFT-SUMA: 3 * 4 = 12
                                .FILL x0DD4                  ;   Valor 13,265625             (Q7.8)
                                .FILL xF8C3                  ;   Valor -7,23828125           (Q7.8)
                                .FILL #0                     ; parte entera del resultado (DQ15.16)
                                .FILL #0                     ; parte fraccionaria del resultado (DQ15.16)

                                .FILL #15                    ; MULTIPLICACION BOOTH: (-3) * 4 = -12
                                .FILL x0DD4                  ;   Valor 13,265625             (Q7.8)
                                .FILL xF8C3                  ;   Valor -7,23828125           (Q7.8)
                                .FILL #0                     ; resultado (Q7.8)
                                .FILL #0                     ; espacio sin uso

                                .FILL #16                    ; DIVISION LARGA: 6 / 3 = 2
                                .FILL #1630                  ; 6,3689652 (Q7.8)
                                .FILL #828                   ; 3,2348937 (Q7.8)
                                .FILL #0                     ; resultado (Q7.8)
                                .FILL #0                     ; espacio sin uso

                                .FILL #17                    ; DIVISION NEWTON-RAPHSON: 9 / 3 = 3
                                .FILL #1630                  ; 6,3689652 (Q7.8)
                                .FILL #828                   ; 3,2348937 (Q7.8)
                                .FILL #0                     ; resultado (Q7.8)
                                .FILL #0                     ; espacio sin uso

                                .FILL #18                    ; DIVISION CORDIC: 0.25 / 0.5 = 0.5
                                .FILL x2000                  ; 0.25 (Q0.15)
                                .FILL x599A                  ; 0.7 (Q0.15)
                                .FILL #0                     ; resultado (Q0.15)
                                .FILL #0                     ; espacio sin uso

                                .FILL #19                    ; LOGARITMO BORCHARDT: ln(1) = 0
                                .FILL x0100                  ; 1.0 (Q7.8)
                                .FILL #0                     ; segundo operando no utilizado
                                .FILL #0                     ; resultado (Q7.8)
                                .FILL #0                     ; espacio sin uso

                                .FILL #20                    ; LOGARITMO CORDIC: ln(2) ~= 0.6931
                                .FILL x2000                  ; 2.0 (Q3.12)
                                .FILL #0                     ; segundo operando no utilizado
                                .FILL #0                     ; resultado (Q3.12)
                                .FILL #0                     ; espacio sin uso

                                .FILL #21                    ; MAXIMO COMUN DIVISOR: mcd(48, 18) = 6
                                .FILL #48                    ; primer entero
                                .FILL #18                    ; segundo entero
                                .FILL #0                     ; resultado entero
                                .FILL #0                     ; espacio sin uso

                                .FILL #22                    ; MINIMO COMUN MULTIPLO: mcm(6, 8) = 24
                                .FILL #16                    ; primer entero
                                .FILL #38                    ; segundo entero
                                .FILL #0                     ; resultado entero
                                .FILL #0                     ; espacio sin uso

                                .FILL #23                    ; CONVERSION Q3.12 A Q7.8: 1.5 permanece 1.5
                                .FILL #21980                 ; 5,3663844453 (Q3.12)
                                .FILL #0                     ; segundo operando no utilizado
                                .FILL #0                     ; resultado (Q7.8)
                                .FILL #0                     ; espacio sin uso

                                .FILL #0                     ; SALIR: termina la ejecucion del bloque


.END
