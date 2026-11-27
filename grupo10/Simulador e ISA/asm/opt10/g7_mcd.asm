; ============================================================================
; Modulo: mcd  (archivo mcd.asm)                      Grupo 7
; Maximo comun divisor de dos enteros con signo, en punto fijo Q15.0.
; Algoritmo: Euclides por restas sucesivas (se resta el menor del mayor hasta
; que ambos sean iguales; ese valor es el MCD).

; MCD
; Entrada:  R0 = a, R1 = b  (enteros con signo, formato Q15.0,
; rango valido [-32767, 32767])
; Salida:   R0 = MCD(|a|, |b|) en Q15.0, exacto, rango [0, 32767]
; MCD(0, b) = |b|, MCD(a, 0) = |a|, MCD(0, 0) = 0
; Preserva: R1 a R3 (los guarda en la pila con PUSH/POP).
; R4 y R5 no se usan. R6 y R7 no se tocan (no usa la pila ni
; llama a nadie). Como guarda en memoria, la rutina no es
; reentrante.
; Nota:     -32768 (x8000) como entrada esta fuera de dominio y no se valida.
; Precision: exacta (resolucion 2^0 = 1, error 0). Nunca desborda.
; Iteraciones: como maximo max(|a|, |b|) (peor caso: 32767 y 1).

; Registros internos:
; R0 = |a| (al salir, el MCD)     R1 = |b|
; R2 = -|b| o -|a| (restas sin recalcular el complemento a 2)
; R3 = temporal (diferencia)
; ============================================================================

MCD
                        PUSH  R1, R2, R3

; Obtener |a| y |b| (actualizando flags antes de cada BRzp).
                        ADD   R0, R0, #0
                        BRzp  mcd_a_positivo
                        NEG   R0, R0                      ; (NOT + ADD #1)
mcd_a_positivo
                        ADD   R1, R1, #0
                        BRzp  mcd_b_positivo
                        NEG   R1, R1                      ; (NOT + ADD #1)
mcd_b_positivo

; Casos con cero.
                        ADD   R0, R0, #0
                        BRz   mcd_devolver_b
                        ADD   R1, R1, #0
                        BRz   mcd_fin

; R2 conserva -R1 para no recalcularlo en cada resta.
                        NEG   R2, R1                      ; (NOT + ADD #1)
                        ADD   R3, R0, R2
                        BRz   mcd_fin
                        BRn   mcd_r0_menor_r1

mcd_restar_r0
                        ADD   R0, R3, #0
                        ADD   R3, R0, R2
                        BRp   mcd_restar_r0
                        BRz   mcd_fin

mcd_r0_menor_r1
; Ahora se conserva -R0 y se resta R0 de R1.
                        NEG   R2, R0                      ; (NOT + ADD #1)
mcd_restar_r1
                        ADD   R1, R1, R2
                        ADD   R3, R1, R2
                        BRp   mcd_restar_r1
                        BRz   mcd_fin

; R1 quedo menor que R0: volver a restar sobre R0.
                        NEG   R2, R1                      ; (NOT + ADD #1)
                        ADD   R3, R0, R2
                        BRp   mcd_restar_r0
                        BRz   mcd_fin
                        BRnzp mcd_r0_menor_r1

mcd_devolver_b
                        ADD   R0, R1, #0

mcd_fin
                        POP   R1, R2, R3
                        RET

; ---- zona de datos ----

.END
