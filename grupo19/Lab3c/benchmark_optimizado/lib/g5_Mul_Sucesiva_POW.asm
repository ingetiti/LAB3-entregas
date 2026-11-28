; ===========================================================================
; Modulo potencia (g5_Mul_Sucesiva_POW.asm): Mul_Sucesiva_POW y MULT juntas.
; Convencion de llamada:
;   R0, R1 = argumentos   R0 = resultado   R1..R7 y SP se conservan
;
; Optimizaciones nueva ISA:
;   - PUSHM/POPR con pila hardware (SP), sin marco manual en R6 ni variables.
;   - LI/MOVI/CLR/DEC/NEG/CMP reemplazan cargas de constantes y complementos.
;   - LSR #8 y SHL #8 + LSR #8 reemplazan los bucles de division por 256.
; ===========================================================================

; ---------------------------------------------------------------------------
; Mul_Sucesiva_POW - A^B por multiplicaciones sucesivas (A en Q7.8, B entero)
;   Salida: R0 = A^B (Q7.8), o x8000 si B < 0, 0^0 u overflow.
; ---------------------------------------------------------------------------
Mul_Sucesiva_POW:
        PUSHM   {R1, R2, R3, R7}

        MOV     R3, R1                  ; R3 = B (contador de multiplicaciones)
        MOV     R1, R0                  ; R1 = A (MULT preserva R1)
        ADDI    R3, R3, #0
        BRn     POT_ERR                 ; exponente negativo
        BRp     POT_POS
        ADDI    R0, R0, #0              ; B = 0
        BRz     POT_ERR                 ; 0^0
        LI      R0, x0100             ; A^0 = 1.00 en Q7.8
        BR      POT_FIN

POT_POS:
        ADDI    R0, R0, #0
        BRz     POT_FIN                 ; 0^B = 0 (R0 ya vale 0)
        DEC     R3                      ; B - 1 multiplicaciones restantes
        BRz     POT_FIN                 ; B = 1 -> R0 = A
        LI      R2, x8000             ; codigo de error para comparar

POT_BUC:
        JSR     MULT                    ; R0 = R0 * R1
        CMP     R0, R2
        BRz     POT_FIN                 ; desborde: R0 ya es x8000
        DEC     R3
        BRp     POT_BUC
        BR      POT_FIN

POT_ERR:
        LI      R0, x8000

POT_FIN:
        POPR    {R1, R2, R3, R7}

; ---------------------------------------------------------------------------
; MULT - Multiplicacion Q7.8 con signo, por sumas sucesivas (truncado hacia 0)
;   Entrada: R0 = A (Q7.8), R1 = B (Q7.8)
;   Salida : R0 = A*B (Q7.8) o x8000 si hay desborde.
; ---------------------------------------------------------------------------
MULT:
        PUSHM   {R1, R2, R3, R4, R5, R6, R7}

        ; Bit 15 de R6 = 1 si los operandos tienen distinto signo.
        XOR     R6, R0, R1
        MOV     R2, R1                  ; R2 = B
        MOV     R1, R0                  ; R1 = A
        BRzp    MULT_A_POS
        NEG     R1, R1                  ; R1 = |A|
        BRn     MULT_DESB               ; x8000 no tiene opuesto en 16 bits
MULT_A_POS:
        ADDI    R2, R2, #0
        BRzp    MULT_B_POS
        NEG     R2, R2                  ; R2 = |B|
        BRn     MULT_DESB
MULT_B_POS:

        ; Separar |B| = BI*256 + BF mediante desplazamientos.
        LSR     R4, R2, #8              ; R4 = BI
        SHL     R2, R2, #8
        LSR     R2, R2, #8              ; R2 = BF (0..255)

        ; Fase 1: sumar |A|, BI veces en R0.
        CLR     R0
        ADDI    R4, R4, #0
        BRz     MULT_DIV_A
MULT_FASE1:
        ADD     R0, R0, R1
        BRn     MULT_DESB
        DEC     R4
        BRp     MULT_FASE1

        ; Separar |A| = AI*256 + AF mediante desplazamientos.
MULT_DIV_A:
        LSR     R4, R1, #8              ; R4 = AI
        SHL     R3, R1, #8
        LSR     R3, R3, #8              ; R3 = AF (0..255)

        ; Fase 2: sumar |A|/256, BF veces.
        CLR     R5                      ; acumulador de fracciones = 0
        MOV     R1, R2                  ; R1 = BF (contador)
        BRz     MULT_FIN_M
        LI      R2, #256
MULT_FASE2:
        ADD     R0, R0, R4              ; resultado += AI
        BRn     MULT_DESB
        ADD     R5, R5, R3              ; acumulador += AF
        CMP     R5, R2                  ; acumulador >= 256?
        BRlt    MULT_SIG
        SUB     R5, R5, R2              ; acumulador -= 256
        INC     R0                      ; acarreo al resultado
        BRn     MULT_DESB
MULT_SIG:
        DEC     R1
        BRp     MULT_FASE2

MULT_FIN_M:
        ADDI    R6, R6, #0
        BRzp    MULT_VUELVE
        NEG     R0, R0
        BR      MULT_VUELVE

MULT_DESB:
        LI      R0, x8000

MULT_VUELVE:
        POPR    {R1, R2, R3, R4, R5, R6, R7}

        .END
