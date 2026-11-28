; ============================================================================
; Modulo: mcm   (archivo mcm.asm)                      Grupo 7
; Minimo comun multiplo de dos enteros con signo, en punto fijo Q15.0.
; Algoritmo: Euclides por restas sucesivas para el MCD, cociente
; Q = menor / MCD por restas sucesivas y MCM = Q * mayor por sumas sucesivas
; (se divide antes de multiplicar para evitar overflow prematuro).
;
; MCM
;   Entrada:  R0 = a, R1 = b  (enteros con signo, formato Q15.0,
;                              rango valido [-32767, 32767])
;   Salida:   R0 = MCM(|a|, |b|) en Q15.0, exacto, rango [0, 32767]
;                  a = 0 o b = 0        -> R0 = 0
;                  MCM real > 32767     -> R0 = x8000 (-32768), aviso de overflow
;   Preserva: R1 a R5 (los guarda en las palabras mcm_guardado_r1 a
;             mcm_guardado_r5, como pide la plantilla de subrutinas).
;             R6 y R7 no se tocan (no usa la pila ni llama a nadie).
;             Como guarda en memoria, la rutina no es reentrante.
;   Nota:     -32768 (x8000) como entrada esta fuera de dominio y no se valida.
;   Precision: exacta (resolucion 2^0 = 1, error 0) mientras no haya overflow.
;   Iteraciones: bucle MCD <= max(|a|,|b|); division = Q; multiplicacion = Q.
;
; Registros internos:
;   R0 = |a| / MCD / acumulador del MCM     R1 = |b|
;   R2 = -|b| (Euclides) / cociente Q       R3 = temporal
;   R4 = menor de |a|,|b|                   R5 = mayor de |a|,|b|
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

        ; R4 = menor, R5 = mayor.
        NOT R2, R1
        ADD R2, R2, #1
        ADD R3, R0, R2
        BRn mcm_a_es_menor

        ADD R4, R1, #0
        ADD R5, R0, #0
        BRnzp mcm_iniciar_mcd

mcm_a_es_menor
        ADD R4, R0, #0
        ADD R5, R1, #0

mcm_iniciar_mcd
        ; Euclides optimizado: R2 ya conserva -R1.
        ADD R3, R0, R2
        BRz mcm_mcd_listo
        BRn mcm_r0_menor_r1

mcm_restar_r0
        ADD R0, R3, #0
        ADD R3, R0, R2
        BRp mcm_restar_r0
        BRz mcm_mcd_listo

mcm_r0_menor_r1
        NOT R2, R0
        ADD R2, R2, #1
mcm_restar_r1
        ADD R1, R1, R2
        ADD R3, R1, R2
        BRp mcm_restar_r1
        BRz mcm_mcd_listo

        NOT R2, R1
        ADD R2, R2, #1
        ADD R3, R0, R2
        BRp mcm_restar_r0
        BRz mcm_mcd_listo
        BRnzp mcm_r0_menor_r1

mcm_mcd_listo
        ; Cociente = menor / MCD por restas sucesivas.
        AND R2, R2, #0
        NOT R3, R0
        ADD R3, R3, #1

mcm_dividir
        ADD R2, R2, #1
        ADD R4, R4, R3
        BRp mcm_dividir

        ; MCM = cociente * mayor, con corte temprano por overflow.
        AND R0, R0, #0

mcm_multiplicar
        ADD R0, R0, R5
        BRn mcm_overflow
        ADD R2, R2, #-1
        BRp mcm_multiplicar
        BRnzp mcm_fin

mcm_overflow
        LD R0, mcm_menor_valor
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