.ORIG x3000

;=====================================================================
; PROGRAMA PRINCIPAL DE PRUEBA PARA MAIN_MENU (ISA-G27)
;
; Modos de ejecución en R0:
;   - R0 = 0 (AND R0, R0, #0): modo menú interactivo por teclado.
;   - R0 = ptr (LD R0, ptr_*): modo automático desde bloque de ops.
; Conserva R6 y restaura registros según convención de MAIN_MENU.
;=====================================================================
.EXTERNAL g27_main_menu-MAIN_MENU

        BR      main

sub_main_menu:          .FILL g27_main_menu-MAIN_MENU
ptr_programa_menu:      .FILL programa_del_menu
ptr_programa_completo:  .FILL programa_del_menu_completo

main:
        ; --- Seleccionar modo descomentar/comentar una de las 3 opciones ---
        ; AND     R0, R0, #0                  ; 0 = menú interactivo normal
        ; LD    R0, ptr_programa_menu       ; Bloque reducido de pruebas
         LD    R0, ptr_programa_completo   ; Bloque completo de 23 ops

        LD      R1, sub_main_menu
        JSRR    R1
        HALT


;=====================================================================
; BLOQUE DE OPERACIONES REDUCIDO (MODO VERBOSO = 1)
; Formato por op: [op_idx, arg_a, arg_b, res_0, res_1] (5 words = 10B)
;=====================================================================
programa_del_menu
    .FILL   #1      ;   modo verboso (muestra todos los valores por consola)
    
    .FILL   #15     ;   MULTIPLICACION BOOTH        (Indice de operacion)
    .FILL   x3396   ;   Valor 51,5859375            (Q7.8)
    .FILL   xF8C3   ;   Valor -7,23828125           (Q7.8)
    .FILL   #0      ;   Espacio para el resultado   (Q7.8)
    .FILL   #0      ;   Espacio para el resultado   (Quedara en blanco)
    
    .FILL   #9      ;   SQRT NEWTONRAPHSON          (Indice de operacion)
    .FILL   x0002   ;   Valor 2.0                   (Q15.16) 
    .FILL   x0000   ;   *                           (DQ16 usa 2 WORD)
    .FILL   #0      ;   Espacio para el resultado   (Q15.16)
    .FILL   #0      ;   *                           (DQ16 usa 2 WORD)

    .FILL   #5      ;   COSENO TABLA                (Indice de operacion)
    .FILL   x1921   ;   Valor 1.5708                (Q3.12)
    .FILL   #0      ;   *                           (Usa un solo operando)
    .FILL   #0      ;   Espacio para el resultado   (Q1.14)
    .FILL   #0      ;   Espacio para el resultado   (Quedara en blanco)

    .FILL   #0      ;   SALIR


;=====================================================================
; BLOQUE DE OPERACIONES COMPLETO (TODAS LAS FUNCIONES 1..23)
;=====================================================================
programa_del_menu_completo:
    .FILL   #1      ; modo verboso: muestra cada operacion, sus operandos y su resultado

    .FILL   #1      ; REDUCCION DE ARGUMENTO: entrada 2,3562 (Q3.12), aproximadamente 3pi/4
    .FILL   #9651   ; 2,356201171875 (Q3.12)
    .FILL   #0      ; segundo operando no utilizado
    .FILL   #0      ; resultado (Q3.12)
    .FILL   #0      ; espacio sin uso

    .FILL   #2      ; SENO TAYLOR: entrada de 60 grados (resultado Q3.12)
    .FILL   #600   ; 60 grados, entero
    .FILL   #0      ; segundo operando no utilizado
    .FILL   #0      ; resultado (Q3.12)
    .FILL   #0      ; espacio sin uso

    .FILL   #3      ; SENO TABLA: seno(pi/3) ~= 0,866
    .FILL   #4289   ; pi/3 (Q3.12)
    .FILL   #0      ; segundo operando no utilizado
    .FILL   #0      ; resultado (Q1.14)
    .FILL   #0      ; espacio sin uso

    .FILL   #4      ; SENO CHEBYSHEV-PADE: seno(pi/3) ~= 0,866
    .FILL   #4289   ; pi/3 (Q3.12)
    .FILL   #0      ; segundo operando no utilizado
    .FILL   #0      ; resultado (Q1.14)
    .FILL   #0      ; espacio sin uso

    .FILL   #5      ; COSENO: coseno(pi/3) ~= 0,5
    .FILL   #4289   ; pi/3 (Q3.12)
    .FILL   #0      ; segundo operando no utilizado
    .FILL   #0      ; resultado (Q1.14)
    .FILL   #0      ; espacio sin uso

    .FILL   #6      ; CAMBIO DE BASE A HEX: muestra el entero 1342 en hexadecimal
    .FILL   #1342     ; entero decimal
    .FILL   #0      ; segundo operando no utilizado
    .FILL   #0      ; resultado no aplica (se imprime en consola)
    .FILL   #0      ; espacio sin uso

    .FILL   #7      ; CAMBIO DE BASE A BIN: muestra xFBCA en binario
    .FILL   xFBCA   ; entero representado por xFBCA
    .FILL   #0      ; segundo operando no utilizado
    .FILL   #0      ; resultado no aplica (se imprime en consola)
    .FILL   #0      ; espacio sin uso

    .FILL   #8      ; SQRT NON RESTORING: raiz(4,35546875) ~= 2,087
    .FILL   #1115   ; 4,35546875 (Q7.8)
    .FILL   #0      ; segundo operando no utilizado
    .FILL   #0      ; resultado (Q6.9)
    .FILL   #0      ; espacio sin uso

    .FILL   #9      ; SQRT NEWTON-RAPHSON: raiz(4,35698) ~= 2,0873
    .FILL   #4      ; parte entera de 4,35698 (DQ15.16)
    .FILL   #23395  ; parte fraccionaria de 4,35698 (DQ15.16)
    .FILL   #0      ; parte entera del resultado (DQ15.16)
    .FILL   #0      ; parte fraccionaria del resultado (DQ15.16)

    .FILL   #10     ; EXPONENCIACION: e^1 ~= 2,7183
    .FILL   #4096   ; 1  (Q3.12)
    .FILL   #0      ; segundo operando no utilizado
    .FILL   #0      ; resultado (Q7.8)
    .FILL   #0      ; espacio sin uso

    .FILL   #11     ; POTENCIA POR MULTIPLICACIONES: (-2)^5 = -32
    .FILL   #-512  ; base -2,0 (Q7.8)
    .FILL   #5      ; exponente entero
    .FILL   #0      ; resultado (Q7.8)
    .FILL   #0      ; espacio sin uso

    .FILL   #12     ; POTENCIA EXPONENCIAL BINARIA: (-2)^5 = -32
    .FILL   #-2      ; -2 base entera
    .FILL   #5      ; exponente entero
    .FILL   #0      ; resultado entero
    .FILL   #0      ; espacio sin uso

    .FILL   #13     ; MULTIPLICACION CORDIC: 13,828125 * -7,23828125 ~= -100,0919
    .FILL   x0DD4   ;   Valor 13,828125             (Q7.8)
    .FILL   xF8C3   ;   Valor -7,23828125           (Q7.8)
    .FILL   #0      ; resultado (Q7.8)
    .FILL   #0      ; espacio sin uso

    .FILL   #14     ; MULTIPLICACION SHIFT-SUMA: 13,828125 * -7,23828125 ~= -100,0919
    .FILL   x0DD4   ;   Valor 13,828125             (Q7.8)
    .FILL   xF8C3   ;   Valor -7,23828125           (Q7.8)
    .FILL   #0      ; parte entera del resultado (DQ15.16)
    .FILL   #0      ; parte fraccionaria del resultado (DQ15.16)

    .FILL   #15     ; MULTIPLICACION BOOTH: 13,828125 * -7,23828125 ~= -100,0919
    .FILL   x0DD4   ;   Valor 13,828125             (Q7.8)
    .FILL   xF8C3   ;   Valor -7,23828125           (Q7.8)
    .FILL   #0      ; resultado (Q7.8)
    .FILL   #0      ; espacio sin uso

    .FILL   #16     ; DIVISION LARGA: 6,3671875 / 3,234375 (Q7.8)
    .FILL   #1630   ; 6,3671875 (Q7.8)
    .FILL   #828    ; 3,234375 (Q7.8)
    .FILL   #0      ; resultado (Q7.8)
    .FILL   #0      ; espacio sin uso

    .FILL   #17     ; DIVISION NEWTON-RAPHSON: 6,3671875 / 3,234375 (Q7.8)
    .FILL   #1630   ; 6,3671875 (Q7.8)
    .FILL   #828    ; 3,234375 (Q7.8)
    .FILL   #0      ; resultado (Q7.8)
    .FILL   #0      ; espacio sin uso

    .FILL   #18     ; DIVISION CORDIC: 0,25 / 0,7000122 (Q0.15)
    .FILL   x2000   ; 0.25 (Q0.15)
    .FILL   x599A   ; 0,7000122 (Q0.15)
    .FILL   #0      ; resultado (Q0.15)
    .FILL   #0      ; espacio sin uso

    .FILL   #19     ; LOGARITMO BORCHARDT: ln(1) = 0
    .FILL   x0080   ; 1.0 (Q8.7)
    .FILL   #0      ; segundo operando no utilizado
    .FILL   #0      ; resultado (Q7.8)
    .FILL   #0      ; espacio sin uso

    .FILL   #20     ; LOGARITMO CORDIC: ln(2) ~= 0.6931
    .FILL   x2000   ; 2.0 (Q3.12)
    .FILL   #0      ; segundo operando no utilizado
    .FILL   #0      ; resultado (Q3.12)
    .FILL   #0      ; espacio sin uso

    .FILL   #21     ; MAXIMO COMUN DIVISOR: mcd(48, 18) = 6
    .FILL   #48     ; primer entero
    .FILL   #18     ; segundo entero
    .FILL   #0      ; resultado entero
    .FILL   #0      ; espacio sin uso

    .FILL   #22     ; MINIMO COMUN MULTIPLO: mcm(16, 38) = 304
    .FILL   #16     ; primer entero
    .FILL   #38     ; segundo entero
    .FILL   #0      ; resultado entero
    .FILL   #0      ; espacio sin uso

    .FILL   #23     ; CONVERSION Q3.12 A Q7.8: entrada 5,3662109375
    .FILL   #21980  ; 5,3662109375 (Q3.12)
    .FILL   #0      ; segundo operando no utilizado
    .FILL   #0      ; resultado (Q7.8)
    .FILL   #0      ; espacio sin uso

    .FILL   #0      ; SALIR: termina la ejecucion del bloque


.END