; ============================================================================
; Modulo: division (division.asm)                          Grupo 10 - ISA LC10
;
; DIV_LONG: division larga (restoring) con signo, a / b con a y b en Q7.8.
;   Entrada:  R0 = a (Q7.8), R1 = b (Q7.8)
;   Salida:   R0 = a / b en Q7.8, truncado hacia cero
;               b = 0              -> R0 = 0
;               el cociente no entra -> R0 saturado: x7FFF (positivo) o x8000
;   Estado:   palabra ESTADO: 0 = ok, 1 = divisor 0, 2 = desborde
;   Preserva: R1 a R5 (los guarda en memoria, como pide la plantilla de subrutinas);
;             R6 y R7 no se tocan (no usa la pila ni llama a nadie).
;   Nota:     (a << 8) / b : el dividendo se alinea con SHR/SHL por 8 en lugar de un
;             lazo, y el desplazamiento de 32 bits usa SHL + RCL (acarreo).
;   Iteraciones del lazo principal: 16 (una por bit del cociente).
;
; Registros internos:
;   R0 = cociente (palabra baja del dividendo)   R1 = |b|
;   R2 = resto (palabra alta del dividendo)      R3 = contador
;   R4 = temporal                                R5 = bit 15 en 1 si el cociente es negativo
; ============================================================================

DIV_LONG    ST   R1, GUARDADO_R1     ; guardar R1..R5 (R0 es la salida)
            ST   R2, GUARDADO_R2
            ST   R3, GUARDADO_R3
            ST   R4, GUARDADO_R4
            ST   R5, GUARDADO_R5

            CLR  R2
            ST   R2, ESTADO          ; estado = 0 (ok)

            XOR  R5, R0, R1          ; bit 15 = 1 si a y b tienen distinto signo
            TST  R1                  ; divisor = 0 ?
            BRz  ERR_DIV0
            BRp  B_POS
            NEG  R1, R1              ; R1 = |b|  (x8000 queda x8000 = 32768 sin signo)
B_POS       TST  R0
            BRzp A_POS
            NEG  R0, R0              ; R0 = |a|  (x8000 queda x8000 = 32768 sin signo)

            ; Dividendo de 32 bits (R2:R0) = |a| << 8
A_POS       SHR  R2, R0, #8          ; palabra alta
            SHL  R0, R0, #8          ; palabra baja
            CMP  R2, R1              ; alta >= |b| (sin signo)?
            BRC  OVERFLOW            ; el cociente no entra en 16 bits
            MOVI R3, #16

            ; Lazo principal: 16 vueltas; (resto:cociente) <<= 1 y comparar con |b|
LAZO        SHL  R0, R0, #1          ; C = bit que sale de R0
            RCL  R2, R2              ; entra a R2; C = bit que sale de R2 (resto >= x10000)
            BRC  RESTAR              ; resto >= |b| seguro
            CMP  R2, R1              ; C = 1 si resto >= |b|
            BRNC SEGUIR              ; resto < |b|: bit 0
RESTAR      SUB  R2, R2, R1          ; resto = resto - |b|
            ADD  R0, R0, #1          ; bit del cociente = 1
SEGUIR      ADD  R3, R3, #-1
            BRp  LAZO

            ; R0 = cociente sin signo; aplicar el signo y verificar el rango
            TST  R5
            BRn  POST_NEG
            TST  R0                  ; positivo: debe ser <= x7FFF
            BRn  OVERFLOW
            BR   EPILOGO
POST_NEG    NEG  R0, R0              ; negativo: |q| <= x8000 <=> el resultado es negativo o cero
            BRp  OVERFLOW
            BR   EPILOGO

OVERFLOW    MOVI R4, #2
            ST   R4, ESTADO          ; estado = 2
            LD   R0, K_X8000
            TST  R5
            BRn  EPILOGO             ; negativo: x8000 (-32768)
            NOT  R0, R0              ; positivo: x7FFF (32767)
            BR   EPILOGO

ERR_DIV0    CLR  R0                  ; divisor 0: resultado 0
            MOVI R4, #1
            ST   R4, ESTADO          ; estado = 1

EPILOGO     LD   R1, GUARDADO_R1     ; restaurar R1..R5
            LD   R2, GUARDADO_R2
            LD   R3, GUARDADO_R3
            LD   R4, GUARDADO_R4
            LD   R5, GUARDADO_R5
            RET

; ---- zona de datos ----
ESTADO      .FILL x0000              ; 0 = ok, 1 = divisor 0, 2 = desborde
K_X8000     .FILL x8000
GUARDADO_R1 .FILL #0
GUARDADO_R2 .FILL #0
GUARDADO_R3 .FILL #0
GUARDADO_R4 .FILL #0
GUARDADO_R5 .FILL #0
            .END
