;=====================================================================
; SUBRUTINA: OUTVAL (Imprime por consola un valor en formato n / Qm.n)
;
;   -> INPUT  [R0] Valor Qm.n (1..15), parte entera (n=0 o n=16)
;   -> INPUT  [R1] 0 (n=0 o Qm.n), o parte fraccionaria Q0.16 (n=16)
;   -> INPUT  [R2] n = bits fraccionarios (0 -> entero, 16 -> Q15.16, 1..15 -> Qm.n)
;   Salida:   Imprime el valor formateado seguido de '\n' en consola.
;   Conserva: R0-R7 (todos intactos, incluyendo R6).
;=====================================================================
.EXTERNAL g27_todec-TODEC

sub_todec:      .FILL g27_todec-TODEC

OUTVAL:
        ST      R0, outval_r0
        ST      R1, outval_r1
        ST      R2, outval_r2
        ST      R3, outval_r3
        ST      R4, outval_r4
        ST      R5, outval_r5
        ST      R7, outval_r7

        ; Caso n == 0 -> forzar parte fraccionaria a 0
        ADD     R2, R2, #0
        BRnp    outval_chk_16
        AND     R1, R1, #0
        BR      outval_print

outval_chk_16:
        ; Caso n == 16 -> R0 ya es entero y R1 ya es fracción Q0.16
        LD      R3, outval_neg16
        ADD     R3, R2, R3
        BRz     outval_print

        ; --- Conversión interna from_qm_n para 1 <= n <= 15 ---
        ; R0 = Qm.n con signo, R1 = trabajo, R2 = n
        AND     R4, R4, #0              ; R4 = flag de signo negativo (0 = +, 1 = -)
        ADD     R0, R0, #0
        BRzp    outval_mag_ready

        ADD     R4, R4, #1
        NOT     R0, R0
        ADD     R0, R0, #1              ; Magnitud positiva de R0

outval_mag_ready:
        ; 1) Parte fraccionaria en Q0.16: R1 = (magnitud << (16 - n))
        LD      R5, outval_c16
        NOT     R3, R2
        ADD     R3, R3, #1
        ADD     R5, R5, R3              ; R5 = 16 - n (1..15)
        ADD     R1, R0, #0

outval_shl_frac:
        LSH     R1, R1, #1
        ADD     R5, R5, #-1
        BRp     outval_shl_frac

        ; 2) Parte entera: R0 = (magnitud >> n)
        ADD     R5, R2, #0              ; R5 = n (1..15)

outval_shr_int:
        RSH     R0, R0, #1
        ADD     R5, R5, #-1
        BRp     outval_shr_int

        ; 3) Reaplicar signo a [R0: entero, R1: fracción Q0.16] si era negativo
        ADD     R4, R4, #0
        BRz     outval_print

        NOT     R0, R0
        NOT     R1, R1
        ADD     R1, R1, #1
        BRnp    outval_print
        ADD     R0, R0, #1

        ; --- Formatear con TODEC e imprimir cadena + '\n' ---
outval_print:
        LEA     R2, outval_buf          ; Puntero (dirección de byte) al buffer interno
        AND     R3, R3, #0              ; Formato = 0
        LD      R4, sub_todec
        JSRR    R4                      ; R2 = puntero al buffer formateado

        ADD     R0, R2, #0
        PUTS

        AND     R0, R0, #0
        ADD     R0, R0, #7
        ADD     R0, R0, #3              ; R0 = #10 ('\n')
        OUT

        LD      R0, outval_r0
        LD      R1, outval_r1
        LD      R2, outval_r2
        LD      R3, outval_r3
        LD      R4, outval_r4
        LD      R5, outval_r5
        LD      R7, outval_r7
        RET

;=====================================================================
; ZONA DE DATOS Y BUFFER INTERNO (CARACTERES DE 8 BITS)
;=====================================================================
outval_c16:     .FILL #16
outval_neg16:   .FILL #-16

outval_r0:      .FILL #0
outval_r1:      .FILL #0
outval_r2:      .FILL #0
outval_r3:      .FILL #0
outval_r4:      .FILL #0
outval_r5:      .FILL #0
outval_r7:      .FILL #0

outval_buf:     .BLKW #16

.END