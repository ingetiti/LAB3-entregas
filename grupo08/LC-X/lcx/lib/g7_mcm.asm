; ============================================================================
; Modulo: mcm   (archivo mcm.asm)                      Grupo 7 (LC-X)
; Minimo comun multiplo de dos enteros con signo, en punto fijo Q15.0.
; Algoritmo: Euclides por restas sucesivas para el MCD, cociente
; Q = |a| / MCD (DIVM) y MCM = Q * |b| (MUL, con V si no entra en 16 bits).
;
; MCM
;   Entrada:  R0 = a, R1 = b  (enteros con signo, formato Q15.0,
;                              rango valido [-32767, 32767])
;   Salida:   R0 = MCM(|a|, |b|) en Q15.0, exacto, rango [0, 32767]
;                  a = 0 o b = 0        -> R0 = 0
;                  MCM real > 32767     -> R0 = x8000 (-32768), aviso de overflow
;   Preserva: R1 a R7 (R1, R4 y R5 se apilan; R6 vuelve igual).
;   Nota:     -32768 (x8000) como entrada esta fuera de dominio y no se valida.
;   Precision: exacta (resolucion 2^0 = 1, error 0) mientras no haya overflow.
;   Iteraciones: bucle MCD <= max(|a|,|b|).
;
; Registros internos:
;   R0 = |a| / MCD / MCM     R1 = |b|
;   R4 = |a| / cociente Q    R5 = |b|
; ============================================================================

MCM
        PUSH  R1, R4, R5
        ABS   R0, R0
        ADD   R4, R0, #0      ; R4 = |a|
        BRz   mcm_fin         ; a = 0: MCM = 0
        ABS   R1, R1
        ADD   R5, R1, #0      ; R5 = |b|
        BRnp  mcm_restar_r0
        AND   R0, R0, #0      ; b = 0: MCM = 0
        POPR  R1, R4, R5

        ; Euclides: cada resta es SUB + BR; la que da negativo se deshace.
mcm_deshacer_r0
        ADD   R0, R0, R1      ; R0 quedo menor que R1
mcm_restar_r1
        SUB   R1, R1, R0
        BRp   mcm_restar_r1
        BRz   mcm_mcd_en_r0   ; eran iguales: MCD = R0
        ADD   R1, R1, R0      ; R1 quedo menor que R0
mcm_restar_r0
        SUB   R0, R0, R1
        BRp   mcm_restar_r0
        BRn   mcm_deshacer_r0
        DIVM  R0, R4, R1      ; eran iguales: Q = |a| / MCD (MCD = R1)
mcm_multiplicar
        MUL   R0, R4, R5      ; MCM = Q * |b|
        BRNV  mcm_fin
        LD    R0, mcm_menor_valor
mcm_fin
        POPR  R1, R4, R5

mcm_mcd_en_r0
        DIVM  R1, R4, R0      ; Q = |a| / MCD
        BR    mcm_multiplicar

; ---- zona de datos ----
mcm_menor_valor    .FILL x8000

.END
