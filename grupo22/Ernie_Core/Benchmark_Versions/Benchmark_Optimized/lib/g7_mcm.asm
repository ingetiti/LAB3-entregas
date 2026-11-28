; ============================================================================
; Modulo: mcm   (archivo g7_mcm.asm)                    Grupo 7  [OPT]
; Minimo comun multiplo de dos enteros con signo, en punto fijo Q15.0.
; Algoritmo: MCD por Euclides con DIV+MUL (O(log)); cociente = menor/MCD con
; DIV nativo; MCM = cociente*mayor con MUL+MULH y deteccion de overflow.
;
; MCM
;   Entrada:  R0 = a, R1 = b  (enteros con signo, formato Q15.0,
;                              rango valido [-32767, 32767])
;   Salida:   R0 = MCM(|a|, |b|) en Q15.0, exacto, rango [0, 32767]
;                  a = 0 o b = 0        -> R0 = 0
;                  MCM real > 32767     -> R0 = x8000 (-32768), aviso de overflow
;   Preserva: R1 a R5 (los guarda en mcm_guardado_r1..r5).
;             R6 y R7 no se tocan (no usa la pila ni llama a nadie).
;             No es reentrante (guarda en memoria).
;   Precision: exacta (resolucion 1, error 0) mientras no haya overflow.
;
; Registros internos:
;   R0 = |a| / MCD / resultado     R1 = |b| / temporal
;   R2 = cociente / scratch        R3 = scratch / mayor
;   R4 = |a| (original)            R5 = |b| (original) / parte alta del producto
;
; Instrucciones nativas: DIV (cociente MCD y menor/MCD), MUL (producto),
; MULH (parte alta para detectar overflow > 32767), LSL/LSR no requeridos.
; DIV nunca recibe divisor 0 (se corta el Euclides con residuo 0; el MCD es >= 1).
; ============================================================================

MCM
        ST R1, mcm_guardado_r1
        ST R2, mcm_guardado_r2
        ST R3, mcm_guardado_r3
        ST R4, mcm_guardado_r4
        ST R5, mcm_guardado_r5

        ; Obtener |a| y |b| (actualizando flags antes de cada BRzp).
        ADD R0, R0, #0
        BRzp mcm_a_positivo
        NOT R0, R0
        ADD R0, R0, #1
mcm_a_positivo
        ADD R1, R1, #0
        BRzp mcm_b_positivo
        NOT R1, R1
        ADD R1, R1, #1
mcm_b_positivo

        ; Si alguno es cero, el MCM es cero.
        ADD R0, R0, #0
        BRz mcm_resultado_cero
        ADD R1, R1, #0
        BRz mcm_resultado_cero

        ; Conservar |a| y |b| originales para menor/mayor y producto final.
        ADD R4, R0, #0          ; R4 = |a|
        ADD R5, R1, #0          ; R5 = |b|

        ; ---- MCD(|a|,|b|) por Euclides con DIV+MUL -> queda en R0 ----
mcm_loop
        DIV R2, R0, R1          ; R2 = a / b  (b != 0 garantizado)
        MUL R3, R2, R1          ; R3 = (a/b) * b
        NOT R3, R3
        ADD R3, R3, #1
        ADD R3, R0, R3          ; R3 = a mod b
        ADD R0, R1, #0          ; a <- b
        ADD R1, R3, #0          ; b <- r
        ADD R1, R1, #0
        BRnz mcm_mcd_listo      ; r == 0 -> MCD en R0
        BRnzp mcm_loop
mcm_mcd_listo               ; R0 = MCD (>= 1)

        ; ---- menor = min(|a|,|b|) -> R2 ; mayor = max(|a|,|b|) -> R3 ----
        NOT R1, R5
        ADD R1, R1, #1          ; -|b|
        ADD R1, R4, R1          ; |a| - |b|
        BRn mcm_a_menor
        ADD R2, R5, #0          ; menor = |b|
        ADD R3, R4, #0          ; mayor = |a|
        BRnzp mcm_dividir
mcm_a_menor
        ADD R2, R4, #0          ; menor = |a|
        ADD R3, R5, #0          ; mayor = |b|

mcm_dividir
        ; cociente = menor / MCD (exacto) -> R2
        DIV R2, R2, R0

        ; ---- MCM = cociente * mayor (32 bits) con deteccion de overflow ----
        MUL  R4, R2, R3         ; R4 = producto bajo  (lo)
        MULH R5, R2, R3         ; R5 = producto alto  (hi)
        ADD R5, R5, #0
        BRnp mcm_overflow       ; hi != 0 -> producto > 65535 -> overflow
        ADD R4, R4, #0
        BRn mcm_overflow        ; lo con bit 15 -> producto > 32767 -> overflow
        ADD R0, R4, #0          ; resultado = lo (<= 32767)
        BRnzp mcm_fin

mcm_overflow
        LD R0, mcm_menor_valor  ; x8000 (centinela de overflow)
        BRnzp mcm_fin

mcm_resultado_cero
        AND R0, R0, #0

mcm_fin
        LD R1, mcm_guardado_r1
        LD R2, mcm_guardado_r2
        LD R3, mcm_guardado_r3
        LD R4, mcm_guardado_r4
        LD R5, mcm_guardado_r5
        RET

; ---- zona de datos ----
mcm_guardado_r1    .FILL #0
mcm_guardado_r2    .FILL #0
mcm_guardado_r3    .FILL #0
mcm_guardado_r4    .FILL #0
mcm_guardado_r5    .FILL #0
mcm_menor_valor    .FILL x8000

.END