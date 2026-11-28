; ============================================================
; SUBRUTINA: EXP_RAPIDA
;
; ENTRADAS:
;   R0 = Base
;   R1 = Exponente
;
; SALIDA:
;   R0 = Base ^ Exponente
;
; REGISTROS CALLEE-SAVED:
;   R1, R2, R3, R4, R5
;
; R6:
;   NO SE UTILIZA
;
; R7:
;   No se modifica porque esta subrutina no llama a otra
;   subrutina.
; ============================================================

EXP_RAPIDA

        ; ----------------------------------------------------
        ; 1. GUARDAR ESTADO ORIGINAL DE LOS REGISTROS
        ; ----------------------------------------------------
        ; R0 es la salida, por lo tanto no se guarda.
        ; R1-R5 deben regresar con su valor original.

        ST R1, GUARDADO_R1
        ST R2, GUARDADO_R2
        ST R3, GUARDADO_R3
        ST R4, GUARDADO_R4
        ST R5, GUARDADO_R5


        ; ----------------------------------------------------
        ; 2. COPIAR LOS ARGUMENTOS A REGISTROS DE TRABAJO
        ; ----------------------------------------------------
        ; R0 = base
        ; R1 = exponente
        ;
        ; R2 = base de trabajo
        ; R3 = exponente de trabajo
        ; R4 = acumulador
        ; R5 = indicador de signo

        ADD R2, R0, #0          ; R2 = base
        ADD R3, R1, #0          ; R3 = exponente

        ; R4 = 1
        AND R4, R4, #0
        ADD R4, R4, #1


        ; ----------------------------------------------------
        ; 3. GUARDAR PARIDAD DEL EXPONENTE ORIGINAL
        ; ----------------------------------------------------
        ; R0 = R3 AND 1
        ;
        ; 0 -> exponente par
        ; 1 -> exponente impar
        ;
        ; Se almacena en memoria porque R6 no puede utilizarse.

        AND R0, R3, #1
        ST R0, PARIDAD


        ; ----------------------------------------------------
        ; 4. DETERMINAR SIGNO DE LA BASE
        ; ----------------------------------------------------
        ; R5 = 0 -> base positiva
        ; R5 = 1 -> base negativa

        AND R5, R5, #0

        ADD R2, R2, #0
        BRzp LOOP_W

        ; Base negativa
        ADD R5, R5, #1

        ; R2 = |base|
        NOT R2, R2
        ADD R2, R2, #1


        ; ====================================================
        ; 5. BUCLE PRINCIPAL DE EXPONENTIACIÓN RÁPIDA
        ; ====================================================

LOOP_W

        ; Si exponente <= 0, finaliza
        ADD R3, R3, #0
        BRnz POST_PROC


        ; ----------------------------------------------------
        ; 5.1 Comprobar si el exponente es impar
        ; ----------------------------------------------------

        AND R0, R3, #1
        BRz L_SHIFT

        ; ----------------------------------------------------
        ; 5.2 R4 = R4 * R2
        ;
        ; Multiplicación mediante sumas sucesivas
        ; ----------------------------------------------------

        AND R0, R0, #0          ; resultado temporal = 0
        ADD R1, R2, #0          ; contador = base

M_LOOP1

        ADD R1, R1, #0
        BRnz M_END1

        ADD R0, R0, R4          ; resultado += acumulador
        ADD R1, R1, #-1         ; contador--

        BR M_LOOP1

M_END1

        ADD R4, R0, #0          ; R4 = R4 * R2


        ; ----------------------------------------------------
        ; 5.3 Dividir exponente entre 2
        ;     mediante restas sucesivas
        ; ----------------------------------------------------

L_SHIFT

        AND R0, R0, #0          ; cociente = 0
        ADD R1, R3, #0          ; R1 = dividendo

D_LOOP

        ADD R1, R1, #-2
        BRn D_END

        ADD R0, R0, #1          ; cociente++
        BR D_LOOP

D_END

        ADD R3, R0, #0          ; R3 = R3 / 2


        ; Si el nuevo exponente es 0, termina.
        ADD R3, R3, #0
        BRnz POST_PROC


        ; ----------------------------------------------------
        ; 5.4 R2 = R2 * R2
        ;
        ; Cuadrado de la base mediante sumas sucesivas
        ; ----------------------------------------------------

        AND R0, R0, #0          ; resultado temporal = 0
        ADD R1, R2, #0          ; contador = base

M_LOOP2

        ADD R1, R1, #0
        BRnz M_END2

        ADD R0, R0, R2          ; resultado += base
        ADD R1, R1, #-1         ; contador--

        BR M_LOOP2

M_END2

        ADD R2, R0, #0          ; R2 = R2 * R2

        BR LOOP_W


        ; ====================================================
        ; 6. PROCESAMIENTO FINAL
        ; ====================================================

POST_PROC

        ; El acumulador contiene el resultado absoluto.
        ADD R0, R4, #0


        ; ----------------------------------------------------
        ; Si la base era positiva, el resultado queda positivo
        ; ----------------------------------------------------

        ADD R5, R5, #0
        BRz RESTAURAR


        ; ----------------------------------------------------
        ; Base negativa.
        ; El resultado solamente es negativo si el exponente
        ; original era impar.
        ; ----------------------------------------------------

        LD R1, PARIDAD

        ADD R1, R1, #0
        BRz RESTAURAR


        ; ----------------------------------------------------
        ; Resultado negativo:
        ; complemento a dos
        ; ----------------------------------------------------

        NOT R0, R0
        ADD R0, R0, #1


        ; ====================================================
        ; 7. RESTAURAR REGISTROS
        ; ====================================================

RESTAURAR

        LD R1, GUARDADO_R1
        LD R2, GUARDADO_R2
        LD R3, GUARDADO_R3
        LD R4, GUARDADO_R4
        LD R5, GUARDADO_R5

        RET


; ============================================================
; ZONA DE DATOS
; ============================================================

PARIDAD        .FILL #0

GUARDADO_R1    .FILL #0
GUARDADO_R2    .FILL #0
GUARDADO_R3    .FILL #0
GUARDADO_R4    .FILL #0
GUARDADO_R5    .FILL #0

.END