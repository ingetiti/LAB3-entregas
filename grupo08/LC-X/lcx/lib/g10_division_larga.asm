; ============================================================================
; Modulo: division   (archivo division.asm)                  Grupo 10 (LC-X)
; Division larga (restoring) con signo en punto fijo de 16 bits.
;
; DIVIDIR
;   Entrada:  R0 = dividendo a (entero de 16 bits con signo, formato Qa)
;             R1 = divisor   b (entero de 16 bits con signo, formato Qb)
;             R2 = s = n_res + n_b - n_a, con 0 <= s <= 16
;                  (cuantos bits se desplaza a la izquierda el dividendo)
;   Salida:   R0 = cociente a/b en el formato de salida Qr, truncado hacia cero
;                  b = 0              -> R0 = 0
;                  cociente no entra  -> R0 saturado: x7FFF (positivo) o x8000
;   Estado:   palabra ESTADO de este archivo: 0 = ok, 1 = divisor 0, 2 = desborde
;   Preserva: R1 a R7 (en la pila).
;   Ejemplo:  Q3.12 / Q7.8 -> Q5.10  =>  s = 10 + 8 - 12 = 6
;
; DIV_LONG  (segunda entrada del modulo, para el menu del Grupo 27)
;   Entrada:  R0 = a (Q7.8), R1 = b (Q7.8)
;   Salida:   R0 = a/b en Q7.8 (DIVIDIR con s = 8 + 8 - 8 = 8)
;   Preserva: R1 a R7.   Estado: igual que DIVIDIR (palabra ESTADO).
;
; El mismo algoritmo que el original: (R1:R0) = |a| << s y 16 pasos de
; division con restauracion, uno por bit del cociente: (resto:cociente) <<= 1
; y, si resto >= |b|, resto -= |b| y el bit es 1. En LC-X el bit sale en C
; (CMP) y entra al cociente con el ADC del paso siguiente.
;
; Registros internos:
;   R0 = cociente (palabra baja del dividendo)   R1 = resto (palabra alta)
;   R2 = contador                                R3 = |b|
;   R4 = bit 15: signo del cociente
; ============================================================================

DIVIDIR PUSH  R1, R2, R3, R4
        BR    DV_COMUN

; ---- DIV_LONG: a/b con a y b en Q7.8, resultado en Q7.8 (s = 8) ----
DIV_LONG
        PUSH  R1, R2, R3, R4
        MOVI  R2, #8            ; s = 8
DV_COMUN
        XOR   R4, R0, R1        ; bit 15 = signo del cociente
        ABS   R3, R1            ; R3 = |b| (x8000 = 32768 sin signo)
        BRz   DV_DIV0
        ABS   R0, R0            ; R0 = |a| (x8000 = 32768 sin signo)

        ; Dividendo de 32 bits = (R1:R0) = |a| desplazado s bits
        CMP   R2, #16
        BRz   DV_S16
        MOVI  R1, #1
        LSHF  R1, R1, R2        ; 2^s
        MULW  R1, R0, R1        ; (R1:R0) = |a| * 2^s
DV_PRE  CMP   R1, R3            ; alta >= |b|: el cociente no entra en 16 bits
        BRC   DV_DESBORDE

        ; Lazo principal: 16 vueltas (C = 0: el primer bit que entra es 0)
        MOVI  R2, #16
DV_LAZO ADC   R0, R0, R0        ; (resto:cociente) <<= 1; entra el bit anterior
        ADC   R1, R1, R1        ; resto < 2|b|: entra en 16 bits
        CMP   R1, R3            ; C = bit del cociente (resto >= |b|)
        BRNC  DV_SIGUE
        SUB   R1, R1, R3        ; resto = resto - |b| (C sigue en 1)
DV_SIGUE
        LOOP  R2, DV_LAZO

        ; Ultimo bit, el signo y el rango (R2 = 0 = estado ok)
        AND   R4, R4, R4        ; no toca C
        BRn   DV_NEG
        ADC   R0, R0, R0        ; positivo: debe ser <= x7FFF
        BRn   DV_DESBORDE
DV_FIN  ST    R2, ESTADO
        POPR  R1, R2, R3, R4

DV_NEG  ADC   R0, R0, R0
        NEG   R0, R0            ; negativo: debe ser <= x8000
        BRnz  DV_FIN
DV_DESBORDE
        LD    R0, K_X7FFF
        RSHFL R2, R4, #15
        ADD   R0, R0, R2        ; x7FFF (positivo) o x8000 (negativo)
        MOVI  R2, #2            ; estado = 2
        BR    DV_FIN

DV_S16  ADD   R1, R0, #0        ; s = 16: alta = |a|, baja = 0
        AND   R0, R0, #0
        BR    DV_PRE

DV_DIV0 AND   R0, R0, #0        ; divisor 0: resultado 0
        MOVI  R2, #1            ; estado = 1
        BR    DV_FIN

; ---- zona de datos ----
ESTADO  .FILL x0000             ; 0 = ok, 1 = divisor 0, 2 = desborde
K_X7FFF .FILL x7FFF
        .END
