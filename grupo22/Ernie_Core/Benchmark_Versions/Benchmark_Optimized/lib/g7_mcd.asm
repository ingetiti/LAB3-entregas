; ============================================================================
; Modulo: mcd  (archivo g7_mcd.asm)                     Grupo 7  [OPT]
; Maximo comun divisor de dos enteros con signo, en punto fijo Q15.0.
; Algoritmo: Euclides con DIV nativo + MUL para el residuo (O(log) iteraciones),
; en lugar de restas sucesivas (hasta 32767 iteraciones).
;
; MCD
;   Entrada:  R0 = a, R1 = b  (enteros con signo, formato Q15.0,
;                              rango valido [-32767, 32767])
;   Salida:   R0 = MCD(|a|, |b|) en Q15.0, exacto, rango [0, 32767]
;                  MCD(0, b) = |b|, MCD(a, 0) = |a|, MCD(0, 0) = 0
;   Preserva: R1 a R3 (los guarda en mcd_guardado_r1..r3).
;             R4 y R5 no se usan. R6 y R7 no se tocan (no usa pila ni llama
;             a nadie). No es reentrante (guarda en memoria).
;   Nota:     -32768 (x8000) como entrada esta fuera de dominio y no se valida.
;   Precision: exacta (resolucion 1, error 0). Nunca desborda.
;
; Registros internos:
;   R0 = a (al salir, el MCD)   R1 = b
;   R2 = cociente a/b           R3 = residuo a - (a/b)*b
;
; Instrucciones nativas usadas: DIV (cociente), MUL (producto q*b), NOT+ADD (resta).
; El divisor nunca es 0 en el bucle (se corta cuando el residuo es 0), por lo que
; DIV no dispara la excepcion fatal de division por cero.
; ============================================================================

MCD
        ST R1, mcd_guardado_r1
        ST R2, mcd_guardado_r2
        ST R3, mcd_guardado_r3

        ; Obtener |a| y |b| (actualizando flags antes de cada BRzp).
        ADD R0, R0, #0
        BRzp mcd_a_positivo
        NOT R0, R0
        ADD R0, R0, #1
mcd_a_positivo
        ADD R1, R1, #0
        BRzp mcd_b_positivo
        NOT R1, R1
        ADD R1, R1, #1
mcd_b_positivo

        ; Casos con cero.
        ADD R0, R0, #0
        BRz mcd_devolver_b
        ADD R1, R1, #0
        BRz mcd_fin

        ; Euclides por division: mientras b != 0, (a,b) <- (b, a mod b).
mcd_loop
        DIV R2, R0, R1          ; R2 = a / b  (b != 0 garantizado)
        MUL R3, R2, R1          ; R3 = (a/b) * b
        NOT R3, R3
        ADD R3, R3, #1          ; R3 = -(a/b)*b
        ADD R3, R0, R3          ; R3 = a - (a/b)*b = a mod b  (0 <= r < b)
        ADD R0, R1, #0          ; a <- b
        ADD R1, R3, #0          ; b <- r
        ADD R1, R1, #0
        BRnz mcd_fin            ; r == 0 -> el MCD esta en R0
        BRnzp mcd_loop

mcd_devolver_b
        ADD R0, R1, #0

mcd_fin
        LD R1, mcd_guardado_r1
        LD R2, mcd_guardado_r2
        LD R3, mcd_guardado_r3
        RET

; ---- zona de datos ----
mcd_guardado_r1    .FILL #0
mcd_guardado_r2    .FILL #0
mcd_guardado_r3    .FILL #0

.END