; =============================================================================
; MÓDULO SUBRUTINA: SENO TAYLOR (GRUPO 21) - NUEVA ISA 16-BIT
; Entrada: R0 = ángulo en décimas de grado (0..3600).
; Salida : R0 = sen(ángulo) en Q3.12 (-4096..4096), o -1 si R0 fuera de rango.
; Preserva R1..R7.
; Optimizaciones: PUSHM/POPR, multiplicación 16x16->32 por shift-and-add,
; división >> 12 en 3 instrucciones (LSR/SHL/OR), división binaria 32/16, CMP, NEG.
; =============================================================================

CALCULAR_SENO
        PUSHM {R1, R2, R3, R4, R5, R7}

        ; Validar 0 <= R0 <= 3600
        ADDI R0, R0, #0
        BRn SENO_ERROR
        LI R1, #3600
        CMP R0, R1
        BRgt SENO_ERROR

        ; Selección de cuadrante -> R2 = ángulo reducido [0..900], R5 = signo (+1 / -1)
        LI R1, #900
        CMP R0, R1
        BRgt CHK_Q2
        MOV R2, R0
        MOVI R5, #1
        BR CONVERSION

CHK_Q2
        LI R1, #1800
        CMP R0, R1
        BRgt CHK_Q3
        SUB R2, R1, R0          ; 1800 - R0
        MOVI R5, #1
        BR CONVERSION

CHK_Q3
        LI R4, #2700
        CMP R0, R4
        BRgt Q4
        SUB R2, R0, R1          ; R0 - 1800
        MOVI R5, #-1
        BR CONVERSION

Q4
        LI R1, #3600
        SUB R2, R1, R0          ; 3600 - R0
        MOVI R5, #-1

CONVERSION
        ; x = (ángulo_reducido * 12868) / 1800  (en Q3.12)
        MOV R0, R2
        LI R1, #12868
        JSR MULT_U32            ; R0:R1 = R2 * 12868
        LI R2, #1800
        JSR DIV_U32_16          ; R0 = x en Q3.12
        MOV R3, R0              ; R3 = x (T1)

        ; Calcular x^2 en Q3.12 = (x * x) >> 12
        MOV R1, R0
        JSR MULT_U32
        LSR R1, R1, #12
        SHL R0, R0, #4
        OR R4, R0, R1           ; R4 = x^2 en Q3.12

        ; Calcular x^3 en Q3.12 = (x * x^2) >> 12
        MOV R0, R3
        MOV R1, R4
        JSR MULT_U32
        LSR R1, R1, #12
        SHL R0, R0, #4
        OR R0, R0, R1           ; R0 = x^3 en Q3.12
        PUSHM {R0}              ; Guardar x^3 en pila para x^5

        ; T2 = -x^3 / 6
        MOV R1, R0
        CLR R0
        MOVI R2, #6
        JSR DIV_U32_16
        NEG R0, R0
        PUSHM {R0}              ; Guardar T2 en pila

        ; Calcular x^5 en Q3.12 = (x^3 * x^2) >> 12
        ; En pila: [T2, x^3]. Extraer x^3 sin perder T2:
        POPM {R2}               ; R2 = T2
        POPM {R0}               ; R0 = x^3
        PUSHM {R2}              ; Dejar T2 en pila
        MOV R1, R4
        JSR MULT_U32
        LSR R1, R1, #12
        SHL R0, R0, #4
        OR R1, R0, R1           ; R1 = x^5 en Q3.12

        ; T3 = x^5 / 120
        CLR R0
        MOVI R2, #120
        JSR DIV_U32_16          ; R0 = T3
        MOV R2, R0              ; R2 = T3

        ; T4 = ((T3 * x^2) >> 12) / 42
        MOV R1, R4
        JSR MULT_U32
        LSR R1, R1, #12
        SHL R0, R0, #4
        OR R1, R0, R1
        CLR R0
        PUSHM {R2}              ; Guardar T3
        MOVI R2, #42
        JSR DIV_U32_16          ; R0 = T4
        POPM {R2}               ; R2 = T3
        POPM {R1}               ; R1 = T2

        ; S = x + T2 + T3 - T4
        ADD R3, R3, R1
        ADD R3, R3, R2
        SUB R0, R3, R0

        ; Aplicar signo del cuadrante
        ADDI R5, R5, #0
        BRzp SENO_DONE
        NEG R0, R0

SENO_DONE
        POPR {R1, R2, R3, R4, R5, R7}

SENO_ERROR
        MOVI R0, #-1
        POPR {R1, R2, R3, R4, R5, R7}

; =============================================================================
; MULT_U32: R0:R1 (alta:baja) = R0 * R1 (16x16 sin signo -> 32 bits)
; Preserva R2..R7.
; =============================================================================
MULT_U32
        PUSHM {R2, R3, R4}
        MOV R2, R0              ; R4:R2 = multiplicando desplazado
        MOV R3, R1              ; R3 = multiplicador
        CLR R4
        CLR R0                  ; R0:R1 = acumulador
        CLR R1
MU32_LP
        LSR R3, R3, #1          ; Procesar primero los bits bajos del multiplicador.
        BRnc MU32_SK
        ADD R1, R1, R2
        ADC R0, R0, R4
MU32_SK
        ADDI R3, R3, #0
        BRz MU32_DONE
        SHL R2, R2, #1
        RLC R4, R4
        BR MU32_LP
MU32_DONE
        POPM {R2, R3, R4}
        RET

; =============================================================================
; DIV_U32_16: R0 = (R0:R1) / R2 (dividendo 32 bits sin signo, divisor 16 bits)
; Preserva R2..R7.
; =============================================================================
DIV_U32_16
        PUSHM {R3, R4, R5}
        CLR R3                  ; R3 = resto = 0
        CLR R4                  ; R4 = cociente = 0
        ADDI R0, R0, #0
        BRnp DU32_WIDE
        MOV R0, R1              ; Alinear el dividendo de 16 bits en la palabra alta.
        CLR R1
        MOVI R5, #16
        BR DU32_LP
DU32_WIDE
        MOVI R5, #32
DU32_LP
        SHL R1, R1, #1
        RLC R0, R0
        RLC R3, R3              ; C = bit 16 del resto
        BRc DU32_SHF_SUB
        SHL R4, R4, #1
        CMP R3, R2              ; C=1 si R3 < R2
        BRc DU32_NX
        BR DU32_SUB
DU32_SHF_SUB
        SHL R4, R4, #1
DU32_SUB
        SUB R3, R3, R2
        INC R4
DU32_NX
        DEC R5
        BRp DU32_LP
        MOV R0, R4
        POPM {R3, R4, R5}
        RET

        .END
