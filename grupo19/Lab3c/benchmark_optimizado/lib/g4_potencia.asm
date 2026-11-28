; ============================================================
; SUBRUTINA: EXP_RAPIDA (exponenciacion binaria entera)
;
; ENTRADAS:
;   R0 = Base
;   R1 = Exponente
;
; SALIDA:
;   R0 = Base ^ Exponente
;
; CONSERVA:
;   R1..R7 y SP
;
; Optimizaciones nueva ISA:
;   - PUSHM/POPR con pila hardware (SP), sin variables en memoria.
;   - LSR #1 reemplaza el bucle de division por 2 mediante restas.
;   - NEG, CLR, DEC, MOV reducen instrucciones de control y signo.
;   - R6 guarda directamente si el resultado final debe negarse.
; ============================================================

EXP_RAPIDA:
        PUSHM   {R1, R2, R3, R4, R5, R6, R7}

        MOV     R2, R0                  ; R2 = base de trabajo
        MOV     R3, R1                  ; R3 = exponente de trabajo
        MOVI    R4, #1                  ; R4 = acumulador = 1

        ; R6 = 1 solo si base < 0 y exponente original impar
        CLR     R6
        ADDI    R2, R2, #0
        BRzp    EXP_LISTO_SIGNO
        NEG     R2, R2                  ; R2 = |base|
        ANDI    R6, R3, #1              ; R6 = paridad del exponente

EXP_LISTO_SIGNO:
        ; Si exponente <= 0, finaliza (devuelve 1 o -1 segun signo)
        ADDI    R3, R3, #0
        BRnz    POST_PROC

LOOP_W:
        ; Dividir exponente entre 2; bit 0 queda en C.
        LSR     R3, R3, #1
        BRnc    L_CHECK_ZERO

        ; R4 = R4 * R2 mediante sumas sucesivas
        CLR     R0
        MOV     R1, R2
        BRnz    M_END1
M_LOOP1:
        ADD     R0, R0, R4
        DEC     R1
        BRp     M_LOOP1
M_END1:
        MOV     R4, R0

L_CHECK_ZERO:
        ; Si el nuevo exponente es 0, termina sin elevar R2 al cuadrado.
        ADDI    R3, R3, #0
        BRz     POST_PROC

        ; R2 = R2 * R2 mediante sumas sucesivas
        CLR     R0
        MOV     R1, R2
        BRnz    M_END2
M_LOOP2:
        ADD     R0, R0, R2
        DEC     R1
        BRp     M_LOOP2
M_END2:
        MOV     R2, R0
        BR      LOOP_W

POST_PROC:
        MOV     R0, R4
        ADDI    R6, R6, #0
        BRz     RESTAURAR
        NEG     R0, R0

RESTAURAR:
        POPR    {R1, R2, R3, R4, R5, R6, R7}

        .END
