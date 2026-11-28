;=====================================================================
; SUBRUTINA: MCM (Mínimo Común Múltiplo de dos enteros con signo)
;
;   Entradas:
;     R0 = a (entero con signo, rango válido [-32767, 32767])
;     R1 = b (entero con signo, rango válido [-32767, 32767])
;   Salida:
;     R0 = MCM(|a|, |b|) en Q15.0, rango [0, 32767]
;          a = 0 o b = 0    -> R0 = 0
;          MCM real > 32767 -> R0 = x8000 (aviso de overflow)
;   Conserva: R1-R5, R6 (intacto) y R7.
;=====================================================================
MCM:
        ST      R1, mcm_guardado_r1
        ST      R2, mcm_guardado_r2
        ST      R3, mcm_guardado_r3
        ST      R4, mcm_guardado_r4
        ST      R5, mcm_guardado_r5

        ; 1. Obtener |a| en R0 y |b| en R1
        ADD     R0, R0, #0
        BRzp    mcm_a_pos
        NOT     R0, R0
        ADD     R0, R0, #1
mcm_a_pos:
        ADD     R1, R1, #0
        BRzp    mcm_b_pos
        NOT     R1, R1
        ADD     R1, R1, #1
mcm_b_pos:

        ; 2. Si alguno es cero, el MCM es cero
        ADD     R0, R0, #0
        BRz     mcm_resultado_cero
        ADD     R1, R1, #0
        BRz     mcm_resultado_cero

        ; Conservar |a| en R4 y |b| en R5 para el cálculo final
        ADD     R4, R0, #0
        ADD     R5, R1, #0

        ; 3. Calcular MCD(|a|, |b|) en R0 usando Euclides con MOD
mcm_bucle_mcd:
        ADD     R1, R1, #0
        BRz     mcm_mcd_listo
        MOD     R2, R0, R1
        ADD     R0, R1, #0
        ADD     R1, R2, #0
        BR      mcm_bucle_mcd

mcm_mcd_listo:
        ; 4. Dividir antes de multiplicar: Q = |a| / MCD (en R2)
        DIV     R2, R4, R0

        ; 5. Multiplicar en hardware: MCM = Q * |b|
        MUL     R0, R2, R5          ; 16 bits bajos del producto
        MULH    R3, R2, R5          ; 16 bits altos del producto

        ; 6. Verificar overflow (> 32767 = x7FFF):
        ;    Si R3 != 0 o bit 15 de R0 es 1 (R0 < 0), hay desborde
        ADD     R3, R3, #0
        BRnp    mcm_overflow
        ADD     R0, R0, #0
        BRn     mcm_overflow
        BR      mcm_fin

mcm_overflow:
        LD      R0, mcm_menor_valor ; Cargar x8000
        BR      mcm_fin

mcm_resultado_cero:
        AND     R0, R0, #0

mcm_fin:
        LD      R1, mcm_guardado_r1
        LD      R2, mcm_guardado_r2
        LD      R3, mcm_guardado_r3
        LD      R4, mcm_guardado_r4
        LD      R5, mcm_guardado_r5
        RET

;--- Zona de datos ---
mcm_guardado_r1:    .FILL #0
mcm_guardado_r2:    .FILL #0
mcm_guardado_r3:    .FILL #0
mcm_guardado_r4:    .FILL #0
mcm_guardado_r5:    .FILL #0
mcm_menor_valor:    .FILL x8000

.END