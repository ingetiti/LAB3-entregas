;=====================================================================
; SUBRUTINA: TODEC (Convierte [R0: entero, R1: fracción] a texto decimal de 8 bits)
;
;   -> INPUT  [R0] Parte entera (con signo, 16 bits)
;   -> INPUT  [R1] Parte fraccionaria (magnitud/fracción de 16 bits)
;   -> INPUT  [R2] Puntero (dirección de byte) al buffer de salida (mín. 17 bytes)
;   -> INPUT  [R3] Formato: bit 0 = SHOW_PLUS (+), bit 1 = SHOW_LEADZ, bit 2 = SHOW_ENDZ
;   <- OUTPUT [R2] Puntero (dirección de byte) al inicio del buffer con cadena '\0'
;   Conserva: R0-R7 (todos intactos, incluyendo R6).
;=====================================================================
TODEC:
        STI     R0, td_a_r0
        STI     R1, td_a_r1
        STI     R3, td_a_r3
        STI     R4, td_a_r4
        STI     R5, td_a_r5
        STI     R7, td_a_r7

        STI     R0, td_a_entero
        STI     R1, td_a_fraccion
        STI     R2, td_a_cursor_beg
        STI     R2, td_a_cursor_wr
        STI     R3, td_a_format

        ; --- 1. Signo ('-' o '+') ---
        LD      R0, td_a_entero
        LDR     R0, R0, #0
        BRzp    todec_sig_elif

        LD      R0, td_a_chr_minus
        LDR     R0, R0, #0
        LD      R2, td_a_cursor_wr
        LDR     R2, R2, #0
        STRB    R0, R2, #0
        ADD     R2, R2, #1
        STI     R2, td_a_cursor_wr

        ; Negar par [entero, fraccion]
        LD      R0, td_a_entero
        LDR     R0, R0, #0
        LD      R1, td_a_fraccion
        LDR     R1, R1, #0
        NOT     R0, R0
        NOT     R1, R1
        ADD     R1, R1, #1
        BRnp    todec_sig_neg_ok
        ADD     R0, R0, #1
todec_sig_neg_ok:
        STI     R0, td_a_entero
        STI     R1, td_a_fraccion
        BR      todec_int

todec_sig_elif:
        LD      R0, td_a_format
        LDR     R0, R0, #0
        AND     R0, R0, #1
        BRz     todec_int

        LD      R0, td_a_chr_plus
        LDR     R0, R0, #0
        LD      R2, td_a_cursor_wr
        LDR     R2, R2, #0
        STRB    R0, R2, #0
        ADD     R2, R2, #1
        STI     R2, td_a_cursor_wr

todec_dec_divisors:
        .FILL #10000
        .FILL #1000
        .FILL #100
        .FILL #10
        .FILL #1
        .FILL #0

        ; --- 2. Parte entera (dígitos de 10000 a 1 usando DIV / MOD) ---
todec_int:
        LD      R3, td_a_entero        ; R3 = remanente entero
        LDR     R3, R3, #0
        LEA     R5, todec_dec_divisors  ; Tabla de divisores en palabras (2 bytes/elem)

todec_int_loop:
        LDR     R4, R5, #0              ; R4 = divisor actual
        BRz     todec_int_done

        DIV     R2, R3, R4              ; R2 = dígito actual (0..9)
        MOD     R3, R3, R4              ; R3 = nuevo remanente

        ; Mostrar si SHOW_LEADZ está activo, el dígito no es 0, o es el último divisor (1)
        LD      R0, td_a_format
        LDR     R0, R0, #0
        AND     R0, R0, #2
        BRnp    todec_int_emit
        ADD     R2, R2, #0
        BRnp    todec_int_set_leadz
        ADD     R0, R4, #-1
        BRz     todec_int_emit
        BR      todec_int_next

todec_int_set_leadz:
        LD      R0, td_a_format
        LDR     R0, R0, #0
        OR      R0, R0, #2              ; Activar SHOW_LEADZ tras primer dígito no cero
        STI     R0, td_a_format

todec_int_emit:
        LD      R0, td_a_chr_zero
        LDR     R0, R0, #0
        ADD     R0, R0, R2              ; ASCII del dígito
        LD      R2, td_a_cursor_wr
        LDR     R2, R2, #0
        STRB    R0, R2, #0
        ADD     R2, R2, #1
        STI     R2, td_a_cursor_wr

todec_int_next:
        ADD     R5, R5, #2              ; Avanzar 1 palabra (2 bytes)
        BR      todec_int_loop

todec_int_done:
        ; --- 3. Retorno temprano si fraccion == 0 ---
        LD      R0, td_a_fraccion
        LDR     R0, R0, #0
        BRnp    td_jmp_dec_a

        LD      R2, td_a_cursor_wr
        LDR     R2, R2, #0
        LD      R0, td_a_format
        LDR     R0, R0, #0
        AND     R0, R0, #4              ; SHOW_ENDZ
        BRz     todec_write_null

        LD      R0, td_a_chr_dot
        LDR     R0, R0, #0
        STRB    R0, R2, #0
        ADD     R2, R2, #1

        LD      R0, td_a_chr_zero
        LDR     R0, R0, #0
        AND     R4, R4, #0
        ADD     R4, R4, #7
        ADD     R4, R4, #2              ; 9 ceros decimales
todec_early_zeros:
        STRB    R0, R2, #0
        ADD     R2, R2, #1
        ADD     R4, R4, #-1
        BRp     todec_early_zeros

todec_write_null:
        AND     R0, R0, #0
        STRB    R0, R2, #0
        STI     R2, td_a_cursor_wr
        LD      R7, td_a_ret
        JMP     R7

td_jmp_dec_a:
        LD      R7, td_a_dec
        JMP     R7

; --- Bloque de punteros #1 (cubre entrada, signo, parte entera y retorno temprano) ---
td_a_r0:            .FILL todec_r0
td_a_r1:            .FILL todec_r1
td_a_r3:            .FILL todec_r3
td_a_r4:            .FILL todec_r4
td_a_r5:            .FILL todec_r5
td_a_r7:            .FILL todec_r7
td_a_entero:        .FILL todec_entero
td_a_fraccion:      .FILL todec_fraccion
td_a_cursor_beg:    .FILL todec_cursor_beg
td_a_cursor_wr:     .FILL todec_cursor_wr
td_a_format:        .FILL todec_format
td_a_chr_plus:      .FILL todec_chr_plus
td_a_chr_minus:     .FILL todec_chr_minus
td_a_chr_dot:       .FILL todec_chr_dot
td_a_chr_zero:      .FILL todec_chr_zero
td_a_dec:           .FILL todec_dec
td_a_ret:           .FILL todec_ret

        ; --- 4. Parte fraccionaria (acumular fracción * 10^9 en 48 bits) ---
todec_dec:
        LD      R0, td_a_chr_dot
        LDR     R0, R0, #0
        LD      R2, td_a_cursor_wr
        LDR     R2, R2, #0
        STRB    R0, R2, #0
        ADD     R2, R2, #1
        STI     R2, td_a_cursor_wr

        AND     R0, R0, #0
        STI     R0, td_c_frac_h
        STI     R0, td_c_frac_l
        STI     R0, td_c_frac_top
        STI     R0, td_c_aux_0

        LD      R0, td_c_frac_expr_h
        LDR     R0, R0, #0
        STI     R0, td_c_aux_1
        LD      R0, td_c_frac_expr_l
        LDR     R0, R0, #0
        STI     R0, td_c_aux_2

        AND     R5, R5, #0
        ADD     R5, R5, #1              ; mascara = 1

todec_dec_loop1:
        ADD     R5, R5, #0
        BRz     todec_dec_break1

        LD      R0, td_c_fraccion
        LDR     R0, R0, #0
        AND     R0, R0, R5
        BRz     todec_dec_continue1

        LD      R0, td_c_frac_l
        LDR     R0, R0, #0
        LD      R1, td_c_aux_2
        LDR     R1, R1, #0
        ADD     R0, R0, R1
        STI     R0, td_c_frac_l

        LD      R0, td_c_frac_h
        LDR     R0, R0, #0
        LD      R1, td_c_aux_1
        LDR     R1, R1, #0
        ADC     R0, R0, R1
        STI     R0, td_c_frac_h

        LD      R0, td_c_frac_top
        LDR     R0, R0, #0
        LD      R1, td_c_aux_0
        LDR     R1, R1, #0
        ADC     R0, R0, R1
        STI     R0, td_c_frac_top

todec_dec_continue1:
        ; [aux_0:aux_1:aux_2] <<= 1
        LD      R0, td_c_aux_0
        LDR     R0, R0, #0
        LD      R1, td_c_aux_1
        LDR     R1, R1, #0
        LD      R2, td_c_aux_2
        LDR     R2, R2, #0

        LSHO    R3, R2, #1
        LSH     R2, R2, #1

        LSHO    R4, R1, #1
        LSH     R1, R1, #1
        OR      R1, R1, R3

        LSH     R0, R0, #1
        OR      R0, R0, R4

        STI     R0, td_c_aux_0
        STI     R1, td_c_aux_1
        STI     R2, td_c_aux_2

        ADD     R5, R5, R5
        BR      todec_dec_loop1

td_c_fraccion:      .FILL todec_fraccion
td_c_frac_top:      .FILL todec_fraccion_top
td_c_frac_h:        .FILL todec_fraccion_h
td_c_frac_l:        .FILL todec_fraccion_l
td_c_aux_0:         .FILL todec_aux_0
td_c_aux_1:         .FILL todec_aux_1
td_c_aux_2:         .FILL todec_aux_2
td_c_frac_expr_h:   .FILL todec_frac_expr_h
td_c_frac_expr_l:   .FILL todec_frac_expr_l

todec_dec_break1:
        ; Descartar los 16 bits fraccionales del producto frac * 10^9.
        LD      R0, td_c_frac_top
        LDR     R0, R0, #0
        LD      R1, td_c_frac_h
        LDR     R1, R1, #0
        STI     R0, td_c_frac_h
        STI     R1, td_c_frac_l

        ; Extraer 9 dígitos decimales restando 10^8, 10^7, ..., 10^0
        LD      R5, td_b_expr_vec
        AND     R4, R4, #0              ; dígito = 0

todec_dec_loop2:
        LDR     R1, R5, #1              ; -expr_l (palabra baja)
        LDR     R2, R5, #0              ; -expr_h (palabra alta)
        LD      R0, td_b_frac_l
        LDR     R0, R0, #0
        LD      R3, td_b_frac_h
        LDR     R3, R3, #0
        AND     R7, R7, #0
        ADD     R0, R0, R1
        ADC     R7, R7, R7
        ADD     R3, R3, R2
        ADD     R3, R3, R7              ; R3:R0 = val32 + (-expr32)

        BRn     todec_dec_append
        STI     R3, td_b_frac_h
        STI     R0, td_b_frac_l
        ADD     R4, R4, #1
        BR      todec_dec_loop2

todec_dec_append:
        LD      R0, td_b_chr_zero
        LDR     R0, R0, #0
        ADD     R0, R0, R4
        LD      R2, td_b_cursor_wr
        LDR     R2, R2, #0
        STRB    R0, R2, #0
        ADD     R2, R2, #1
        STI     R2, td_b_cursor_wr

        ; Si no se pide SHOW_ENDZ y el resto fraccionario es 0, terminar dígitos
        LD      R0, td_b_format
        LDR     R0, R0, #0
        AND     R0, R0, #4
        BRnp    todec_dec_continue2
        LD      R0, td_b_frac_l
        LDR     R0, R0, #0
        BRnp    todec_dec_continue2
        LD      R0, td_b_frac_h
        LDR     R0, R0, #0
        BRnp    todec_dec_continue2
        BR      todec_dec_break2

todec_dec_continue2:
        AND     R4, R4, #0
        ADD     R5, R5, #4              ; Siguiente par de 32 bits (4 bytes)
        LDR     R0, R5, #1
        BRnp    todec_dec_loop2
        LDR     R0, R5, #0
        BRnp    todec_dec_loop2

todec_dec_break2:
        LD      R2, td_b_cursor_wr
        LDR     R2, R2, #0
        AND     R0, R0, #0
        STRB    R0, R2, #0
        STI     R2, td_b_cursor_wr

        ; --- 5. Restaurar registros y devolver puntero en R2 ---
todec_ret:
        LD      R0, td_b_r0
        LDR     R0, R0, #0
        LD      R1, td_b_r1
        LDR     R1, R1, #0
        LD      R2, td_b_cursor_beg
        LDR     R2, R2, #0
        LD      R3, td_b_r3
        LDR     R3, R3, #0
        LD      R4, td_b_r4
        LDR     R4, R4, #0
        LD      R5, td_b_r5
        LDR     R5, R5, #0
        LD      R7, td_b_r7
        LDR     R7, R7, #0
        RET

; --- Bloque de punteros #2 (cubre parte fraccionaria y retorno) ---
td_b_r0:            .FILL todec_r0
td_b_r1:            .FILL todec_r1
td_b_r3:            .FILL todec_r3
td_b_r4:            .FILL todec_r4
td_b_r5:            .FILL todec_r5
td_b_r7:            .FILL todec_r7
td_b_fraccion:      .FILL todec_fraccion
td_b_cursor_beg:    .FILL todec_cursor_beg
td_b_cursor_wr:     .FILL todec_cursor_wr
td_b_format:        .FILL todec_format
td_b_frac_h:        .FILL todec_fraccion_h
td_b_frac_l:        .FILL todec_fraccion_l
td_b_aux_0:         .FILL todec_aux_0
td_b_aux_1:         .FILL todec_aux_1
td_b_aux_2:         .FILL todec_aux_2
td_b_chr_dot:       .FILL todec_chr_dot
td_b_chr_zero:      .FILL todec_chr_zero
td_b_frac_expr_h:   .FILL todec_frac_expr_h
td_b_frac_expr_l:   .FILL todec_frac_expr_l
td_b_expr_vec:      .FILL todec_expr_vec

;=====================================================================
; ZONA DE DATOS Y CONSTANTES
;=====================================================================
todec_r0:           .FILL #0
todec_r1:           .FILL #0
todec_r3:           .FILL #0
todec_r4:           .FILL #0
todec_r5:           .FILL #0
todec_r7:           .FILL #0

todec_entero:       .FILL #0
todec_fraccion:     .FILL #0
todec_cursor_beg:   .FILL #0
todec_cursor_wr:    .FILL #0
todec_format:       .FILL #0
todec_fraccion_h:   .FILL #0
todec_fraccion_l:   .FILL #0
todec_fraccion_top: .FILL #0
todec_aux_0:        .FILL #0
todec_aux_1:        .FILL #0
todec_aux_2:        .FILL #0

todec_chr_plus:     .FILL #43           ; '+'
todec_chr_minus:    .FILL #45           ; '-'
todec_chr_dot:      .FILL #46           ; '.'
todec_chr_zero:     .FILL #48           ; '0'

todec_frac_expr_h:  .FILL x3B9A
todec_frac_expr_l:  .FILL xCA00         ; 1_000_000_000

todec_expr_vec:
        .FILL xFA0A
        .FILL x1F00         ; -10^8 (9no dígito)
        .FILL xFF67
        .FILL x6980         ; -10^7 (8vo dígito)
        .FILL xFFF0
        .FILL xBDC0         ; -10^6 (7mo dígito)
        .FILL xFFFE
        .FILL x7960         ; -10^5 (6to dígito)
        .FILL xFFFF
        .FILL xD8F0         ; -10^4 (5to dígito)
        .FILL xFFFF
        .FILL xFC18         ; -10^3 (4to dígito)
        .FILL xFFFF
        .FILL xFF9C         ; -10^2 (3er dígito)
        .FILL xFFFF
        .FILL xFFF6         ; -10^1 (2do dígito)
        .FILL xFFFF
        .FILL xFFFF         ; -10^0 (1er dígito)
        .FILL x0000
        .FILL x0000         ; Terminador NULL de 32 bits

.END