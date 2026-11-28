; ============================================================================
; Modulo: g7_mcd_mcm (archivo g7_mcd_mcm.asm)             Grupo 7
; MCD y MCM de dos enteros con signo en UNA sola rutina (Q15.0).
; Algoritmo: Euclides con REM para el MCD; MCM = (|a| / MCD) * |b|
; (se divide antes de multiplicar) con deteccion de overflow por MULH.
;
; Puntos de entrada (los que usa el menu):
;   MCD: R0 = a, R1 = b  ->  R0 = MCD(|a|, |b|)
;   MCM: R0 = a, R1 = b  ->  R0 = MCM(|a|, |b|)  (0 si a o b es 0;
;        x8000 si el MCM real no entra en 15 bits)
; Preservan R1 a R5, R6 y R7. No es reentrante.
; Nucleo (MCDMCM): R0 = MCD, R1 = MCM.
; ============================================================================

MCD
        ST R1, mm_guardado_r1
        ST R7, mm_guardado_r7
        JSR MCDMCM              ; R0 = MCD
        BRnzp mm_restaura

MCM
        ST R1, mm_guardado_r1
        ST R7, mm_guardado_r7
        JSR MCDMCM
        ADD R0, R1, #0          ; R0 = MCM
mm_restaura
        LD R1, mm_guardado_r1
        LD R7, mm_guardado_r7
        RET

MCDMCM
        ST R2, mm_guardado_r2
        ST R3, mm_guardado_r3
        ST R4, mm_guardado_r4

        ABS R0, R0              ; R0 = |a|
        BRz mm_a_cero
        ABS R1, R1              ; R1 = |b|
        BRz mm_b_cero

        ADD R2, R0, #0          ; R2 = |a|
        ADD R3, R1, #0          ; R3 = |b|
mm_euclides
        REM R4, R2, R3          ; R4 = R2 mod R3
        ADD R2, R3, #0
        ADD R3, R4, #0          ; NZP segun el resto
        BRnp mm_euclides        ; repetir mientras el resto no sea 0
                                ; R2 = MCD
        DIV R4, R0, R2          ; R4 = |a| / MCD
        MULH R3, R4, R1         ; parte alta de R4 * |b|
        BRnp mm_overflow        ; parte alta distinta de 0: no entra
        MUL R1, R4, R1          ; parte baja = MCM
        BRn mm_overflow         ; bit 15 en 1: no entra en 15 bits
        ADD R0, R2, #0          ; R0 = MCD
        BRnzp mm_fin

mm_overflow
        ADD R0, R2, #0          ; R0 = MCD
        LD R1, mm_centinela     ; R1 = x8000 (aviso de overflow)
        BRnzp mm_fin

mm_a_cero
        ABS R0, R1              ; MCD(0, b) = |b|
mm_b_cero
        AND R1, R1, #0          ; MCM = 0

mm_fin
        LD R2, mm_guardado_r2
        LD R3, mm_guardado_r3
        LD R4, mm_guardado_r4
        RET

; ---- zona de datos ----
mm_guardado_r1     .FILL #0
mm_guardado_r2     .FILL #0
mm_guardado_r3     .FILL #0
mm_guardado_r4     .FILL #0
mm_guardado_r7     .FILL #0
mm_centinela       .FILL x8000

.END
