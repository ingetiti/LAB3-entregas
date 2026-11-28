; ============================================================================
; Modulo: mcd  (archivo mcd.asm)                      Grupo 7 (LC-X)
; Maximo comun divisor de dos enteros con signo, en punto fijo Q15.0.
; Algoritmo: Euclides por restas sucesivas (se resta el menor del mayor hasta
; que ambos sean iguales; ese valor es el MCD).
;
; MCD
;   Entrada:  R0 = a, R1 = b  (enteros con signo, formato Q15.0,
;                              rango valido [-32767, 32767])
;   Salida:   R0 = MCD(|a|, |b|) en Q15.0, exacto, rango [0, 32767]
;                  MCD(0, b) = |b|, MCD(a, 0) = |a|, MCD(0, 0) = 0
;   Preserva: R1 a R7 (R1 se apila; R6 vuelve igual).
;   Nota:     -32768 (x8000) como entrada esta fuera de dominio y no se valida.
;   Precision: exacta (resolucion 2^0 = 1, error 0). Nunca desborda.
;   Iteraciones: como maximo max(|a|, |b|) (peor caso: 32767 y 1).
;
; Registros internos: R0 = |a| (al salir, el MCD)     R1 = |b|
; Cada resta es SUB + BR: se resta mientras quede positivo; la ultima
; resta (que da negativo) se deshace y se cambia de lado.
; ============================================================================

MCD
        PUSH  R1
        ABS   R0, R0          ; R0 = |a|
        BRz   mcd_devolver_b
        ABS   R1, R1          ; R1 = |b|
        BRnp  mcd_restar_r0
        POPR  R1              ; b = 0: MCD = |a|

mcd_deshacer_r1
        ADD   R1, R1, R0      ; R1 quedo menor que R0
mcd_restar_r0
        SUB   R0, R0, R1
        BRp   mcd_restar_r0
        BRz   mcd_devolver_b  ; eran iguales: MCD = R1
        ADD   R0, R0, R1      ; R0 quedo menor que R1
mcd_restar_r1
        SUB   R1, R1, R0
        BRp   mcd_restar_r1
        BRn   mcd_deshacer_r1
        POPR  R1              ; eran iguales: MCD = R0

mcd_devolver_b
        ABS   R0, R1
        POPR  R1

.END
