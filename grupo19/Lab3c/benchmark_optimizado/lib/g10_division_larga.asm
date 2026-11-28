; ============================================================================
; Modulo: division   (archivo g10_division_larga.asm)                Grupo 10
; Division larga (restoring) con signo en punto fijo de 16 bits.
; Adaptado y optimizado para la nueva ISA de 16 bits byte-addressable.
;
; DIVIDIR
;   Entrada:  R0 = dividendo a (entero de 16 bits con signo, formato Qa)
;             R1 = divisor   b (entero de 16 bits con signo, formato Qb)
;             R2 = s = n_res + n_b - n_a, con 0 <= s <= 16
;   Salida:   R0 = cociente a/b en el formato de salida Qr, truncado hacia cero
;                  b = 0              -> R0 = 0
;                  cociente no entra  -> R0 saturado: x7FFF (positivo) o x8000
;   Estado:   palabra ESTADO: 0 = ok, 1 = divisor 0, 2 = desborde
;   Preserva: R1 a R7 (usa la pila hardware SP con PUSHM/POPM).
;
; DIV_LONG  (segunda entrada del modulo, para el menu del Grupo 27)
;   Entrada:  R0 = a (Q7.8), R1 = b (Q7.8)
;   Salida:   R0 = a/b en Q7.8 (llama a DIVIDIR con s = 8)
;   Preserva: R1 a R7 (usa PUSHM/POPR).
; ============================================================================

DIVIDIR     PUSHM {R1, R2, R3, R4, R5} ; guardar R1..R5 en pila hardware

            CLR   R5                   ; R5 = cuenta de operandos negativos
            ST    R5, ESTADO           ; estado = 0 (ok)

            ADDI  R1, R1, #0           ; divisor = 0 ?
            BRz   ERR_DIV0
            BRp   B_POS
            INC   R5                   ; divisor negativo
            NEG   R1, R1               ; R1 = |b| (x8000 queda x8000 = 32768 sin signo)
B_POS       MOV   R3, R1               ; R3 = |b| (comparacion sin signo con CMP)

            ADDI  R0, R0, #0           ; dividendo negativo ?
            BRzp  A_POS
            INC   R5
            NEG   R0, R0               ; R0 = |a| (x8000 queda x8000 = 32768 sin signo)
A_POS       ANDI  R5, R5, #1           ; R5 = 1 si exactamente un operando es negativo

            ; Dividendo de 32 bits = (R1:R0) = |a| << s (en O(1) con SRLV/SHLV)
            ADDI  R2, R2, #0
            BRz   PRE_S0
            MOVI  R4, #16
            SUB   R4, R4, R2           ; R4 = 16 - s
            BRz   PRE_S16
            SRLV  R1, R0, R4           ; R1 = |a| >> (16 - s)
            SHLV  R0, R0, R2           ; R0 = |a| << s
            BR    PRE_FIN
PRE_S0      CLR   R1
            BR    PRE_FIN
PRE_S16     MOV   R1, R0
            CLR   R0

PRE_FIN     CMP   R1, R3               ; comparar sin signo: R1 >= |b| -> C = 0
            BRnc  OVERFLOW             ; alta >= |b|: el cociente no entra en 16 bits

            ; Lazo principal: 16 vueltas; (resto:cociente) <<= 1 y comparar con |b|
            MOVI  R2, #16
LAZO        SHL   R0, R0, #1           ; sale bit 15 de R0 hacia C
            RLC   R1, R1               ; entra C en bit 0 de R1: (R1:R0) <<= 1
            CMP   R1, R3               ; sin signo: R1 < |b| -> C = 1
            BRc   L_SEGUIR             ; resto < |b|: bit del cociente = 0
            SUB   R1, R1, R3           ; resto -= |b|
            INC   R0                   ; bit del cociente = 1
L_SEGUIR    DEC   R2
            BRp   LAZO

            ; R0 = cociente sin signo; aplicar el signo y verificar el rango
            ADDI  R5, R5, #0
            BRp   POST_NEG
            ADDI  R0, R0, #0           ; positivo: debe ser <= x7FFF
            BRn   OVERFLOW
            BR    EPILOGO
POST_NEG    ADDI  R0, R0, #0           ; negativo: debe ser <= x8000
            BRzp  NEG_APLIC
            SHL   R4, R0, #1           ; si R0 >= x8000 solo vale x8000 (R0 << 1 == 0)
            BRnp  OVERFLOW
NEG_APLIC   NEG   R0, R0
            BR    EPILOGO

OVERFLOW    MOVI  R4, #2
            ST    R4, ESTADO           ; estado = 2
            LI    R0, x8000
            ADDI  R5, R5, #0
            BRp   EPILOGO              ; negativo: x8000 (-32768)
            NOT   R0, R0               ; positivo: x7FFF (32767)
            BR    EPILOGO

ERR_DIV0    CLR   R0                   ; divisor 0: resultado 0
            MOVI  R4, #1
            ST    R4, ESTADO           ; estado = 1

EPILOGO     POPM  {R1, R2, R3, R4, R5} ; restaurar R1..R5
            RET

; ---- DIV_LONG: a/b con a y b en Q7.8, resultado en Q7.8 (s = 8) ----
DIV_LONG    PUSHM {R2, R7}             ; guardar R2 y R7 en pila hardware
            MOVI  R2, #8               ; s = 8
            JSR   DIVIDIR              ; R0 = a/b en Q7.8
            POPR  {R2, R7}             ; restaurar R2, R7 y retornar

; ---- zona de datos ----
ESTADO      .FILL x0000                ; 0 = ok, 1 = divisor 0, 2 = desborde
            .END
