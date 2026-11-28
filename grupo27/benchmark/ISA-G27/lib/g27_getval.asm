;=====================================================================
; SUBRUTINA: GETVAL (Lectura formateada por teclado y eco del valor real)
;
;   -> INPUT  [R0] n = cantidad de bits fraccionarios (0 -> entero,
;                      16 -> Q15.16, 1..15 -> Qm.n)
;   <- OUTPUT [R0] Valor Qm.n obtenido, o parte entera (si n=0 o n=16)
;   <- OUTPUT [R1] 0 (si n=0 o Qm.n), o parte fraccionaria Q0.16 (si n=16)
;   Conserva: R2-R7 (todos intactos, incluyendo R6).
;=====================================================================
.EXTERNAL g27_getline-GETLINE
.EXTERNAL g27_fromdec-FROMDEC
.EXTERNAL g27_todec-TODEC

sub_getline:    .FILL g27_getline-GETLINE
sub_fromdec:    .FILL g27_fromdec-FROMDEC
sub_todec:      .FILL g27_todec-TODEC

GETVAL:
        ST      R2, getval_r2
        ST      R3, getval_r3
        ST      R4, getval_r4
        ST      R5, getval_r5
        ST      R7, getval_r7

        ST      R0, getval_n

        ; 1. Leer línea en el buffer interno (caracteres de 8 bits)
        LD      R0, getval_buf_ads
        LD      R1, getval_buf_end_ads
        LD      R2, sub_getline
        JSRR    R2                      ; R0 = puntero al buffer

        ; 2. Parsear texto decimal -> [R0 = entero, R1 = fraccion Q0.16, R5 = err]
        LD      R2, sub_fromdec
        JSRR    R2

        ; 3. Seleccionar formato según n (en getval_n)
        LD      R2, getval_n            ; LD actualiza NZP
        BRnp    getval_chk_16

        ; --- Caso n == 0 (entero de 16 bits truncado hacia cero) ---
        ADD     R0, R0, #0
        BRzp    getval_int_ok           ; Si entero >= 0, ya está truncado
        ADD     R1, R1, #0
        BRz     getval_int_ok           ; Si entero < 0 y fracción == 0, exacto
        ADD     R0, R0, #1              ; Si entero < 0 y fracción != 0, truncar hacia 0
getval_int_ok:
        AND     R1, R1, #0
        ST      R0, getval_value_0
        ST      R1, getval_value_1
        BR      getval_out

getval_chk_16:
        ADD     R2, R2, #-8
        ADD     R2, R2, #-8             ; R2 = n - 16
        BRnp    getval_qnm

        ; --- Caso n == 16 (separado en R0 = entero, R1 = fraccion Q0.16) ---
        ST      R0, getval_value_0
        ST      R1, getval_value_1
        BR      getval_out

        ; --- Caso 1 <= n <= 15 (formato Qm.n empaquetado en 16 bits) ---
getval_qnm:
        ; 3a) to_qm_n: empaquetar [R0: entero, R1: fraccion Q0.16] en Qm.n
        ST      R0, getval_tmp_int
        ST      R1, getval_tmp_frac

        AND     R4, R4, #0              ; R4 = flag negativo (0 = +, 1 = -)
        ADD     R0, R0, #0
        BRzp    getval_qm_mag_ready

        ADD     R4, R4, #1
        NOT     R0, R0
        NOT     R1, R1
        ADD     R1, R1, #1
        BRnp    getval_qm_neg_ok
        ADD     R0, R0, #1
getval_qm_neg_ok:
        ST      R0, getval_tmp_int
        ST      R1, getval_tmp_frac

getval_qm_mag_ready:
        ; Parte entera << n
        LD      R0, getval_tmp_int
        LD      R3, getval_n            ; contador = n (1..15)
getval_shl_int:
        LSH     R0, R0, #1
        ADD     R3, R3, #-1
        BRp     getval_shl_int

        ; Bits fraccionarios superiores: fraccion >> (16 - n)
        LD      R1, getval_tmp_frac
        LD      R5, getval_16           ; 16
        LD      R3, getval_n
        NOT     R3, R3
        ADD     R3, R3, #1
        ADD     R5, R5, R3              ; R5 = 16 - n (1..15)
getval_shr_frac:
        RSH     R1, R1, #1
        ADD     R5, R5, #-1
        BRp     getval_shr_frac

        OR      R0, R0, R1              ; Magnitud Qm.n en R0

        ; Aplicar signo si correspondía
        ADD     R4, R4, #0
        BRz     getval_qm_stored
        NOT     R0, R0
        ADD     R0, R0, #1

getval_qm_stored:
        ST      R0, getval_value_0      ; Guardar Qm.n
        AND     R1, R1, #0
        ST      R1, getval_value_1      ; R1 de salida = 0 para Qm.n

        ; 3b) from_qm_n: desempaquetar R0 (Qm.n) a [R0 = entero, R1 = fraccion Q0.16]
        AND     R4, R4, #0
        ADD     R0, R0, #0
        BRzp    getval_from_mag_ok
        ADD     R4, R4, #1
        NOT     R0, R0
        ADD     R0, R0, #1

getval_from_mag_ok:
        ; Parte fraccionaria en Q0.16: magnitud << (16 - n)
        LD      R5, getval_16
        LD      R3, getval_n
        NOT     R3, R3
        ADD     R3, R3, #1
        ADD     R5, R5, R3              ; R5 = 16 - n (1..15)
        ADD     R1, R0, #0
getval_shl_frac:
        LSH     R1, R1, #1
        ADD     R5, R5, #-1
        BRp     getval_shl_frac

        ; Parte entera: magnitud >> n
        LD      R5, getval_n            ; R5 = n (1..15)
getval_shr_int:
        RSH     R0, R0, #1
        ADD     R5, R5, #-1
        BRp     getval_shr_int

        ; Reaplicar signo a [R0: entero, R1: fraccion]
        ADD     R4, R4, #0
        BRz     getval_out
        NOT     R0, R0
        NOT     R1, R1
        ADD     R1, R1, #1
        BRnp    getval_out
        ADD     R0, R0, #1

        ; 4. Formatear con TODEC e imprimir "[ <valor> ]\n"
getval_out:
        LD      R2, getval_buf_ads
        AND     R3, R3, #0              ; Formato = 0
        LD      R4, sub_todec
        JSRR    R4                      ; R2 = puntero al buffer formateado

        LEA     R0, getval_lbraket
        PUTS
        LD      R0, getval_buf_ads
        PUTS
        LEA     R0, getval_rbraket
        PUTS

        ; 5. Restaurar registros y devolver resultados en R0 y R1
        LD      R0, getval_value_0
        LD      R1, getval_value_1
        LD      R2, getval_r2
        LD      R3, getval_r3
        LD      R4, getval_r4
        LD      R5, getval_r5
        LD      R7, getval_r7
        RET

;=====================================================================
; ZONA DE DATOS Y BUFFER INTERNO (CARACTERES DE 8 BITS)
;=====================================================================
getval_lbraket:     .STRINGZ "[ "
getval_rbraket:     .STRINGZ " ]\n"

getval_n:           .FILL #0
getval_value_0:     .FILL #0
getval_value_1:     .FILL #0
getval_tmp_int:     .FILL #0
getval_tmp_frac:    .FILL #0

getval_r2:          .FILL #0
getval_r3:          .FILL #0
getval_r4:          .FILL #0
getval_r5:          .FILL #0
getval_r7:          .FILL #0

getval_16:          .FILL #16

getval_buf_ads:     .FILL getval_buf
getval_buf_end_ads: .FILL getval_buf_end
getval_buf:         .BLKW #16
getval_buf_end:

.END