;=====================================================================
; SUBRUTINA: DIV_LONG (División larga Q7.8 sin usar DIV ni MOD)
;
;   Entradas:
;     R0 = dividendo a en Q7.8 (16 bits con signo)
;     R1 = divisor   b en Q7.8 (16 bits con signo)
;   Salida:
;     R0 = cociente a/b en Q7.8, truncado hacia cero
;          b = 0              -> R0 = 0
;          cociente no entra  -> R0 saturado: x7FFF (+) o x8000 (-)
;     ESTADO = 0 (ok), 1 (divisor 0), 2 (desborde)
;   Conserva: R1-R5, R6 (intacto) y R7.
;=====================================================================
DIV_LONG:
        ST      R1, GUARDADO_R1
        ST      R2, GUARDADO_R2
        ST      R3, GUARDADO_R3
        ST      R4, GUARDADO_R4
        ST      R5, GUARDADO_R5

        AND     R5, R5, #0
        ST      R5, ESTADO          ; ESTADO = 0 (ok)

        ; 1. Validar divisor == 0
        ADD     R1, R1, #0
        BRz     ERR_DIV0

        ; 2. Calcular signo resultante en bit 15 de R5 (R5 < 0 si signos distintos)
        XOR     R5, R0, R1

        ; 3. Obtener magnitudes sin signo |b| y |a| (x8000 queda como 32768)
        ADD     R1, R1, #0
        BRzp    B_POS
        NOT     R1, R1
        ADD     R1, R1, #1          ; R1 = |b|
B_POS:
        NOT     R3, R1
        ADD     R3, R3, #1          ; R3 = -|b|

        ADD     R0, R0, #0
        BRzp    A_POS
        NOT     R0, R0
        ADD     R0, R0, #1          ; R0 = |a|
A_POS:

        ; 4. Escalar dividendo |a| por 2^8 (s = 8 para Q7.8) en par (R1:R0):
        ;    R1 (palabra alta) = |a| >> 8
        ;    R0 (palabra baja) = |a| << 8
        RSH     R1, R0, #8
        LSH     R0, R0, #8

        ; 5. Comprobar desborde previo: si palabra alta >= |b|, no cabe en 16 bits
        ADD     R4, R1, R3          ; R1 - |b| (ambos <= 32768; seguro sin overflow)
        BRzp    OVERFLOW

        ; 6. Lazo principal de división larga (16 iteraciones, 1 por bit)
        AND     R2, R2, #0
        ADD     R2, R2, #7
        ADD     R2, R2, #7
        ADD     R2, R2, #2          ; R2 = 16

LAZO:
        LSHO    R4, R0, #1          ; Extraer el bit alto de la palabra baja
        LSH     R0, R0, #1          ; Desplazar la palabra baja para el siguiente bit
        LSH     R1, R1, #1
        ADD     R1, R1, R4          ; Incorporar el bit saliente

        ADD     R1, R1, #0
        BRn     L_SIEMPRE           ; Si resto >= x8000, seguro es >= |b|
        ADD     R4, R1, R3          ; resto - |b| (resto <= x7FFF, no desborda)
        BRn     L_SEGUIR            ; Si resto < |b|, el bit del cociente queda en 0
        ADD     R1, R4, #0          ; resto = resto - |b|
        ADD     R0, R0, #1          ; bit del cociente = 1
        BR      L_SEGUIR

L_SIEMPRE:
        ADD     R1, R1, R3          ; resto -= |b| (aritmética modular 16 bits)
        ADD     R0, R0, #1          ; bit del cociente = 1

L_SEGUIR:
        ADD     R2, R2, #-1
        BRp     LAZO

        ; 7. Aplicar signo y verificar saturación de 16 bits con signo
        ADD     R5, R5, #0
        BRn     POST_NEG

        ; Resultado positivo: debe ser <= x7FFF (bit 15 == 0)
        ADD     R0, R0, #0
        BRn     OVERFLOW
        BR      EPILOGO

POST_NEG:
        ; Resultado negativo: magnitud debe ser <= x8000
        ADD     R0, R0, #0
        BRzp    NEG_APLIC
        ADD     R4, R0, R0          ; Si bit 15 == 1, solo es válido x8000 (x8000*2 == 0)
        BRnp    OVERFLOW
NEG_APLIC:
        NOT     R0, R0
        ADD     R0, R0, #1
        BR      EPILOGO

OVERFLOW:
        AND     R4, R4, #0
        ADD     R4, R4, #2
        ST      R4, ESTADO          ; ESTADO = 2 (desborde)
        LD      R0, K_X8000
        ADD     R5, R5, #0
        BRn     EPILOGO             ; Negativo saturado -> x8000 (-32768)
        NOT     R0, R0              ; Positivo saturado -> x7FFF (+32767)
        BR      EPILOGO

ERR_DIV0:
        AND     R0, R0, #0          ; Divisor 0 -> resultado = 0
        AND     R4, R4, #0
        ADD     R4, R4, #1
        ST      R4, ESTADO          ; ESTADO = 1 (divisor 0)

EPILOGO:
        LD      R1, GUARDADO_R1
        LD      R2, GUARDADO_R2
        LD      R3, GUARDADO_R3
        LD      R4, GUARDADO_R4
        LD      R5, GUARDADO_R5
        RET

;--- Zona de datos ---
ESTADO:         .FILL x0000         ; 0 = ok, 1 = divisor 0, 2 = desborde
K_X8000:        .FILL x8000
GUARDADO_R1:    .FILL #0
GUARDADO_R2:    .FILL #0
GUARDADO_R3:    .FILL #0
GUARDADO_R4:    .FILL #0
GUARDADO_R5:    .FILL #0

.END