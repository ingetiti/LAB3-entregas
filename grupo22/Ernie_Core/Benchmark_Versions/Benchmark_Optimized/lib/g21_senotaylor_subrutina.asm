.ORIG x3000

;==================================================================
; G21 - SENOTAYLOR_SUBRUTINA  (CALCULAR_SENO)
; Optimizacion Fase 1 (Sub-lote 1A): instrucciones nativas ISA.
;
; ABI (sin cambios):
;   Entrada : R0 = angulo en decimas de grado (0..3600)
;   Salida  : R0 = sen(theta) en Q3.12
;   Preserva: R1-R5, R7 ; R6 intacto (0xFFFE) ; salida por RET.
;
; Algoritmo (equivalente bit-a-bit al original, pero con MUL/MULH/DIV):
;   1. Reduccion de cuadrante -> r en [0,900] decimas + signo.
;   2. x = (r * 29282) >> 12            (Q3.12; 29282/4096 ~= 12868/1800)
;   3. x2=(x*x)>>12 ; x3=(x2*x)>>12 ; x5=(x3*x2)>>12            (Q3.12)
;   4. T2 = -(x3/6) ; T3 = x5/120 ; T4 = ((T3*x2)>>12)/42
;   5. S = x + T2 + T3 - T4 ; aplicar signo del cuadrante.
;
; El bloque de datos se ubica al INICIO para que todas las cargas
; PC-relativas (LD/ST) queden dentro del rango PCoffset8 [-128,+127].
;==================================================================

;================= BLOQUE DE DATOS =================
GUARDADO_R1     .FILL #0
GUARDADO_R2     .FILL #0
GUARDADO_R3     .FILL #0
GUARDADO_R4     .FILL #0
GUARDADO_R5     .FILL #0
GUARDADO_R7     .FILL #0
SIGNO_CUADRANTE .FILL #0

ENTRADA         .FILL #0

LIM900          .FILL #900
LIM1800         .FILL #1800
LIM2700         .FILL #2700
LIM3600         .FILL #3600

C_Q12           .FILL #29282
C120            .FILL #120
C42             .FILL #42

;================= CODIGO =================
CALCULAR_SENO

    ; ---- Guardar contexto (R3 se usa como puntero al bloque) ----
    ST R0, ENTRADA
    LEA R0, GUARDADO_R1
    STR R3, R0, #2          ; GUARDADO_R3 = R3 original
    LEA R3, GUARDADO_R1     ; R3 = puntero base
    STR R1, R3, #0
    STR R2, R3, #1
    STR R4, R3, #3
    STR R5, R3, #4
    STR R7, R3, #5

    LD R0, ENTRADA

    ; ---- Validar angulo en [0, 3600] ----
    ADD R0, R0, #0
    BRn ERROR
    LD R1, LIM3600
    NOT R1, R1
    ADD R1, R1, #1          ; R1 = -3600
    ADD R2, R0, R1
    BRp ERROR

    ; ---- Seleccion de cuadrante (R0 = r en [0,900], signo en memoria) ----
    LD R1, LIM900
    NOT R1, R1
    ADD R1, R1, #1          ; -900
    ADD R2, R0, R1
    BRnz CUADRANTE1         ; angulo <= 900

    LD R1, LIM1800
    NOT R1, R1
    ADD R1, R1, #1          ; -1800
    ADD R2, R0, R1
    BRnz CUADRANTE2         ; angulo <= 1800

    LD R1, LIM2700
    NOT R1, R1
    ADD R1, R1, #1          ; -2700
    ADD R2, R0, R1
    BRnz CUADRANTE3         ; angulo <= 2700

    BRnzp CUADRANTE4        ; angulo <= 3600

CUADRANTE1                  ; r = angulo, signo = +1
    AND R1, R1, #0
    ADD R1, R1, #1
    STR R1, R3, #6
    BRnzp CONVERSION

CUADRANTE2                  ; r = 1800 - angulo, signo = +1
    LD R1, LIM1800
    NOT R1, R1
    ADD R1, R1, #1
    ADD R0, R0, R1          ; angulo - 1800
    NOT R0, R0
    ADD R0, R0, #1          ; 1800 - angulo
    AND R1, R1, #0
    ADD R1, R1, #1
    STR R1, R3, #6
    BRnzp CONVERSION

CUADRANTE3                  ; r = angulo - 1800, signo = -1
    LD R1, LIM1800
    NOT R1, R1
    ADD R1, R1, #1
    ADD R0, R0, R1          ; angulo - 1800
    AND R1, R1, #0
    ADD R1, R1, #-1
    STR R1, R3, #6
    BRnzp CONVERSION

CUADRANTE4                  ; r = 3600 - angulo, signo = -1
    LD R1, LIM3600
    NOT R1, R1
    ADD R1, R1, #1
    ADD R0, R0, R1          ; angulo - 3600
    NOT R0, R0
    ADD R0, R0, #1          ; 3600 - angulo
    AND R1, R1, #0
    ADD R1, R1, #-1
    STR R1, R3, #6

    ; ---- Conversion a radianes Q3.12: x = (r * 29282) >> 12 ----
CONVERSION
    LD R1, C_Q12            ; 29282
    MUL R2, R0, R1          ; bajo  del producto r*C
    MULH R4, R0, R1         ; alto   del producto r*C
    LSL R4, R4, #4          ; alto << 4
    LSR R2, R2, #6
    LSR R2, R2, #6          ; bajo >> 12
    ADD R0, R4, R2          ; R0 = x (Q3.12)

    ; ---- x2 = (x*x) >> 12 ----
    MUL R2, R0, R0
    MULH R4, R0, R0
    LSL R4, R4, #4
    LSR R2, R2, #6
    LSR R2, R2, #6
    ADD R1, R4, R2          ; R1 = x2 (Q3.12)

    ; ---- x3 = (x2 * x) >> 12 ----
    MUL R2, R1, R0
    MULH R4, R1, R0
    LSL R4, R4, #4
    LSR R2, R2, #6
    LSR R2, R2, #6
    ADD R5, R4, R2          ; R5 = x3 (Q3.12)

    ; ---- x5 = (x3 * x2) >> 12 ----
    MUL R2, R5, R1
    MULH R4, R5, R1
    LSL R4, R4, #4
    LSR R2, R2, #6
    LSR R2, R2, #6
    ADD R7, R4, R2          ; R7 = x5 (Q3.12)

    ; ---- T2 = -(x3 / 6) ----
    DIV R5, R5, #6
    NOT R5, R5
    ADD R5, R5, #1          ; R5 = T2 (Q3.12)

    ; ---- T3 = x5 / 120 (x5 es unsigned 0..39165; div. exacta por partes) ----
    ; x5 = 256*hi + lo ; x5/120 = 2*hi + (16*hi + lo)/120  (todo < 32768)
    LSR R2, R7, #4
    LSR R2, R2, #4          ; R2 = hi = x5 >> 8
    LSL R4, R2, #4
    LSL R4, R4, #4          ; R4 = hi << 8
    NOT R4, R4
    ADD R4, R4, #1          ; R4 = -(hi << 8)
    ADD R7, R7, R4          ; R7 = lo = x5 - (hi << 8)
    LSL R4, R2, #4          ; R4 = 16*hi
    ADD R7, R7, R4          ; R7 = 16*hi + lo
    LD R4, C120
    DIV R7, R7, R4          ; R7 = (16*hi + lo)/120
    ADD R2, R2, R2          ; R2 = 2*hi
    ADD R7, R7, R2          ; R7 = T3 (Q3.12)

    ; ---- T4 = ((T3 * x2) >> 12) / 42 ----
    MUL R2, R7, R1
    MULH R4, R7, R1
    LSL R4, R4, #4
    LSR R2, R2, #6
    LSR R2, R2, #6
    ADD R2, R4, R2          ; (T3*x2) en Q3.12
    LD R4, C42
    DIV R2, R2, R4          ; R2 = T4 (Q3.12)

    ; ---- Serie de Taylor: S = x + T2 + T3 - T4 ----
    ADD R0, R0, R5          ; x + T2
    ADD R0, R0, R7          ; + T3
    NOT R2, R2
    ADD R2, R2, #1          ; -T4
    ADD R0, R0, R2          ; R0 = S (Q3.12)

    ; ---- Aplicar signo del cuadrante ----
    LDR R1, R3, #6
    ADD R1, R1, #0
    BRzp SIGNO_OK
    NOT R0, R0
    ADD R0, R0, #1

SIGNO_OK
    ; ---- Restaurar contexto y retornar ----
    LDR R1, R3, #0
    LDR R2, R3, #1
    LDR R4, R3, #3
    LDR R5, R3, #4
    LDR R7, R3, #5
    LDR R3, R3, #2
    RET

ERROR
    AND R0, R0, #0
    ADD R0, R0, #-1         ; R0 = -1 (angulo fuera de rango)
    LDR R1, R3, #0
    LDR R2, R3, #1
    LDR R4, R3, #3
    LDR R5, R3, #4
    LDR R7, R3, #5
    LDR R3, R3, #2
    RET

.END