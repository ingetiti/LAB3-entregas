;=====================================================================
; SUBRUTINA: MCD (Máximo Común Divisor de dos enteros con signo)
;
;   Entradas:
;     R0 = a (entero con signo, 16 bits)
;     R1 = b (entero con signo, 16 bits)
;   Salida:
;     R0 = MCD(|a|, |b|) (entero >= 0; MCD(0,0) = 0)
;   Conserva: R1, R2, R6 y R7.
;=====================================================================
MCD:
        ST      R1, mcd_guardado_r1
        ST      R2, mcd_guardado_r2

        ; 1. Obtener |a| en R0
        ADD     R0, R0, #0
        BRzp    mcd_a_pos
        NOT     R0, R0
        ADD     R0, R0, #1
mcd_a_pos:

        ; 2. Obtener |b| en R1
        ADD     R1, R1, #0
        BRzp    mcd_b_pos
        NOT     R1, R1
        ADD     R1, R1, #1
mcd_b_pos:

        ; 3. Bucle de Euclides con MOD:
        ;    Mientras R1 != 0:
        ;      R2 = R0 MOD R1
        ;      R0 = R1
        ;      R1 = R2
mcd_bucle:
        ADD     R1, R1, #0
        BRz     mcd_fin
        MOD     R2, R0, R1
        ADD     R0, R1, #0
        ADD     R1, R2, #0
        BR      mcd_bucle

mcd_fin:
        LD      R1, mcd_guardado_r1
        LD      R2, mcd_guardado_r2
        RET

;--- Zona de datos ---
mcd_guardado_r1:    .FILL #0
mcd_guardado_r2:    .FILL #0

.END