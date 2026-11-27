; ============================================================================
; Modulo: division   (archivo division.asm)                         Grupo 10
; Division larga (restoring) con signo en punto fijo de 16 bits.
;
; DIVIDIR
;   Entrada:  R0 = dividendo a (entero de 16 bits con signo, formato Qa)
;             R1 = divisor   b (entero de 16 bits con signo, formato Qb)
;             R2 = s = n_res + n_b - n_a, con 0 <= s <= 16
;                  (n_x = bits fraccionarios del formato x; es cuantos bits se
;                   desplaza a la izquierda el dividendo antes de dividir)
;   Salida:   R0 = cociente a/b en el formato de salida Qr, truncado hacia cero
;                  (error < 1 LSB de Qr).
;                  b = 0              -> R0 = 0
;                  cociente no entra  -> R0 saturado: x7FFF (positivo) o x8000
;   Estado:   palabra ESTADO de este archivo: 0 = ok, 1 = divisor 0, 2 = desborde
;   Preserva: R1 a R5 (los guarda en las palabras GUARDADO_R1 a GUARDADO_R5, como pide
;             la plantilla de subrutinas). R6 y R7 no se tocan (no usa la pila ni llama
;             a nadie). Como guarda en memoria, la rutina no es reentrante.
;   Ejemplo:  Q3.12 / Q7.8 -> Q5.10  =>  s = 10 + 8 - 12 = 6
;   Formato de salida: bits enteros = ceil(log2(max|a| / divisor_minimo));
;   Iteraciones del lazo principal: 16 (una por bit del cociente).
;
; Registros internos:
;   R0 = cociente (palabra baja del dividendo)   R1 = resto (palabra alta)
;   R2 = contador                                R3 = -|b|
;   R4 = temporal                                R5 = 1 si el cociente es negativo
;
; DIV_LONG
;   Entrada:  R0 = a (Q7.8), R1 = b (Q7.8)
;   Salida:   R0 = a/b en Q7.8 (llama a DIVIDIR con s = 8 + 8 - 8 = 8)
;   Preserva: R1 a R7 (R2 y R7 en GUARDADO_DL_R2 y GUARDADO_DL_R7; R1, R3, R4 y R5
;             los preserva DIVIDIR). No es reentrante.
;   Estado:   igual que DIVIDIR (palabra ESTADO).
; ============================================================================

DIVIDIR     ST  R1, GUARDADO_R1      ; guardar R1..R5 (R0 es la salida)
            ST  R2, GUARDADO_R2
            ST  R3, GUARDADO_R3
            ST  R4, GUARDADO_R4
            ST  R5, GUARDADO_R5

            AND R5, R5, #0           ; R5 = cuenta de operandos negativos
            ST  R5, ESTADO           ; estado = 0 (ok)

            ADD R1, R1, #0           ; divisor = 0 ?
            BRz ERR_DIV0
            BRp B_POS
            ADD R5, R5, #1           ; divisor negativo
            NOT R1, R1
            ADD R1, R1, #1           ; R1 = |b|  (x8000 queda x8000 = 32768 sin signo)
B_POS       NOT R3, R1
            ADD R3, R3, #1           ; R3 = -|b|

            ADD R0, R0, #0           ; dividendo negativo ?
            BRzp A_POS
            ADD R5, R5, #1
            NOT R0, R0
            ADD R0, R0, #1           ; R0 = |a|  (x8000 queda x8000 = 32768 sin signo)
A_POS       ADD R5, R5, #-1          ; cuenta 0 -> -1, 1 -> 0, 2 -> 1
            BRz SIGNO_NEG            ; exactamente un operando negativo
            AND R5, R5, #0           ; cociente positivo: R5 = 0
            BRnzp SIGNO_FIN
SIGNO_NEG   ADD R5, R5, #1           ; cociente negativo: R5 = 1

            ; Dividendo de 32 bits = (R1:R0) = |a| desplazado s bits a la izquierda
SIGNO_FIN   AND R1, R1, #0           ; palabra alta = 0 (|b| ya esta en R3)
            ADD R2, R2, #0
            BRz PRE_FIN
PRE         ADD R1, R1, R1           ; (R1:R0) <<= 1
            ADD R0, R0, #0
            BRzp PRE_SIN
            ADD R1, R1, #1           ; el bit 15 de R0 pasa a R1
PRE_SIN     ADD R0, R0, R0
            ADD R2, R2, #-1
            BRp PRE

PRE_FIN     ADD R4, R1, R3           ; palabra alta - |b|
            BRzp OVERFLOW            ; alta >= |b|: el cociente no entra en 16 bits

            ; Lazo principal: 16 vueltas; (resto:cociente) <<= 1 y comparar con |b|
            AND R2, R2, #0
            ADD R2, R2, #8
            ADD R2, R2, #8           ; R2 = 16
LAZO        ADD R0, R0, #0
            BRzp L_BIT0
            ADD R0, R0, R0           ; sale un 1 de R0 ...
            ADD R1, R1, R1
            ADD R1, R1, #1           ; ... y entra al resto
            BRnzp L_CMP
L_BIT0      ADD R0, R0, R0
            ADD R1, R1, R1
L_CMP       ADD R1, R1, #0
            BRn L_SIEMPRE            ; resto >= x8000 (>= |b| seguro)
            ADD R4, R1, R3           ; resto - |b|  (no desborda: resto <= x7FFF)
            BRn L_SEGUIR             ; resto < |b|: bit 0
            ADD R1, R4, #0           ; resto = resto - |b|
            ADD R0, R0, #1           ; bit del cociente = 1
            BRnzp L_SEGUIR
L_SIEMPRE   ADD R1, R1, R3           ; resto - |b| (aritmetica modular de 16 bits)
            ADD R0, R0, #1
L_SEGUIR    ADD R2, R2, #-1
            BRp LAZO

            ; R0 = cociente sin signo; aplicar el signo y verificar el rango
            ADD R5, R5, #0
            BRp POST_NEG
            ADD R0, R0, #0           ; positivo: debe ser <= x7FFF
            BRn OVERFLOW
            BRnzp EPILOGO
POST_NEG    ADD R0, R0, #0           ; negativo: debe ser <= x8000
            BRzp NEG_APLIC
            ADD R4, R0, R0           ; si R0 >= x8000 solo vale x8000 (R0+R0 = 0)
            BRnp OVERFLOW
NEG_APLIC   NOT R0, R0
            ADD R0, R0, #1
            BRnzp EPILOGO

OVERFLOW    AND R4, R4, #0
            ADD R4, R4, #2
            ST  R4, ESTADO           ; estado = 2
            LD  R0, K_X8000
            ADD R5, R5, #0
            BRp EPILOGO              ; negativo: x8000 (-32768)
            NOT R0, R0               ; positivo: x7FFF (32767)
            BRnzp EPILOGO

ERR_DIV0    AND R0, R0, #0           ; divisor 0: resultado 0
            AND R4, R4, #0
            ADD R4, R4, #1
            ST  R4, ESTADO           ; estado = 1

EPILOGO     LD  R1, GUARDADO_R1      ; restaurar R1..R5
            LD  R2, GUARDADO_R2
            LD  R3, GUARDADO_R3
            LD  R4, GUARDADO_R4
            LD  R5, GUARDADO_R5
            RET

; ---- DIV_LONG: a/b con a y b en Q7.8, resultado en Q7.8 (s = 8) ----
DIV_LONG    ST  R2, GUARDADO_DL_R2   ; guardar R2 y R7 (aca se llama a DIVIDIR)
            ST  R7, GUARDADO_DL_R7
            AND R2, R2, #0
            ADD R2, R2, #8           ; s = 8
            JSR DIVIDIR              ; R0 = a/b en Q7.8; R1..R5 vuelven intactos
            LD  R2, GUARDADO_DL_R2
            LD  R7, GUARDADO_DL_R7
            RET

; ---- zona de datos ----
ESTADO      .FILL x0000              ; 0 = ok, 1 = divisor 0, 2 = desborde
K_X8000     .FILL x8000
GUARDADO_R1 .FILL #0
GUARDADO_R2 .FILL #0
GUARDADO_R3 .FILL #0
GUARDADO_R4 .FILL #0
GUARDADO_R5 .FILL #0
GUARDADO_DL_R2 .FILL #0
GUARDADO_DL_R7 .FILL #0
            .END

