;=====================================================================
; SUBRUTINA: FROMDEC (Cadena decimal de 8 bits -> Parte entera + Q0.16)
;
;   -> INPUT  [R0] Puntero (dirección de byte) a cadena ASCII decimal ('\0')
;   <- OUTPUT [R0] Parte entera (entero con signo de 16 bits)
;   <- OUTPUT [R1] Parte fraccionaria en Q0.16 (0..65535; 0.5 = 32768)
;   <- OUTPUT [R5] Banderas de error:
;                    bit 0 (1): INVALID_INPUT
;                    bit 1 (2): OVERFLOW
;   Conserva: R2-R4, R6 (intacto) y R7.
;=====================================================================
FROMDEC:
        STI     R2, p_a_r2
        STI     R3, p_a_r3
        STI     R4, p_a_r4
        STI     R7, p_a_r7

        AND     R5, R5, #0              ; errores = 0
        ADD     R4, R0, #0              ; R4 = puntero de lectura (bytes)

        AND     R0, R0, #0
        STI     R0, p_a_entero
        STI     R0, p_a_fraccion
        STI     R0, p_a_negativo
        STI     R0, p_a_has_number

        ; --- 1. Signo opcional ('-' o '+') ---
        LDRB    R0, R4, #0              ; LDRB actualiza NZP
        BRz     fd_jmp_ret_a

        LD      R1, p_a_neg_minus
        LDR     R1, R1, #0
        ADD     R1, R1, R0
        BRnp    fromdec_chk_plus
        AND     R1, R1, #0
        ADD     R1, R1, #1
        STI     R1, p_a_negativo
        ADD     R4, R4, #1
        BR      fromdec_int_loop

fromdec_chk_plus:
        LD      R1, p_a_neg_plus
        LDR     R1, R1, #0
        ADD     R1, R1, R0
        BRnp    fromdec_int_loop
        ADD     R4, R4, #1
        BR      fromdec_int_loop

fd_jmp_ret_a:
        LD      R7, p_a_ret
        JMP     R7

        ; --- 2. Parte entera ---
fromdec_int_loop:
        LDRB    R0, R4, #0              ; LDRB actualiza NZP
        BRz     fd_jmp_ret_a

        LD      R1, p_a_neg_dot
        LDR     R1, R1, #0
        ADD     R1, R1, R0
        BRz     fromdec_int_period_found

        LD      R1, p_a_neg_period
        LDR     R1, R1, #0
        ADD     R1, R1, R0
        BRz     fromdec_int_period_found
        BR      fromdec_int_range_chk

fromdec_int_period_found:
        ADD     R4, R4, #1              ; Avanzar tras '.' o ','
        LD      R7, p_a_dec
        JMP     R7

fromdec_int_range_chk:
        LD      R1, p_a_neg_zero
        LDR     R1, R1, #0
        ADD     R1, R1, R0
        BRn     fromdec_int_invalid

        LD      R1, p_a_neg_nine
        LDR     R1, R1, #0
        ADD     R1, R1, R0
        BRp     fromdec_int_invalid

        ; Comprobar desbordamiento (> 3276, o == 3276 con dígito >= 8 + negativo)
        LD      R1, p_a_entero
        LDR     R1, R1, #0
        LD      R2, p_a_neg_overchk
        LDR     R2, R2, #0
        ADD     R2, R2, R1
        BRp     fromdec_int_overflow
        BRn     fromdec_int_append

        LD      R2, p_a_neg_eight
        LDR     R2, R2, #0
        LD      R3, p_a_negativo
        LDR     R3, R3, #0
        NOT     R3, R3
        ADD     R3, R3, #1
        ADD     R2, R2, R3
        ADD     R2, R2, R0
        BRn     fromdec_int_append

fromdec_int_overflow:
        OR      R5, R5, #2              ; OVERFLOW (bit 1)

fromdec_int_append:
        LD      R2, p_a_c10
        LDR     R2, R2, #0
        MUL     R1, R1, R2              ; entero * 10
        LD      R2, p_a_neg_zero
        LDR     R2, R2, #0
        ADD     R1, R1, R2
        ADD     R1, R1, R0              ; entero = entero * 10 + (char - '0')

        AND     R2, R2, #0
        ADD     R2, R2, #1
        STI     R2, p_a_has_number
        STI     R1, p_a_entero
        ADD     R4, R4, #1
        BR      fromdec_int_loop

fromdec_int_invalid:
        OR      R5, R5, #1              ; INVALID_INPUT (bit 0)
        BR      fd_jmp_ret_a

; --- Bloque de punteros #1 (cubre entrada y parte entera) ---
p_a_r2:             .FILL fromdec_r2
p_a_r3:             .FILL fromdec_r3
p_a_r4:             .FILL fromdec_r4
p_a_r7:             .FILL fromdec_r7
p_a_entero:         .FILL fromdec_entero
p_a_fraccion:       .FILL fromdec_fraccion
p_a_negativo:       .FILL fromdec_negativo
p_a_has_number:     .FILL fromdec_has_number
p_a_neg_minus:      .FILL fromdec_neg_minus
p_a_neg_plus:       .FILL fromdec_neg_plus
p_a_neg_dot:        .FILL fromdec_neg_dot
p_a_neg_period:     .FILL fromdec_neg_period
p_a_neg_zero:       .FILL fromdec_neg_zero
p_a_neg_nine:       .FILL fromdec_neg_nine
p_a_neg_eight:      .FILL fromdec_neg_eight
p_a_neg_overchk:    .FILL fromdec_neg_overchk
p_a_c10:            .FILL fromdec_c10
p_a_dec:            .FILL fromdec_dec
p_a_ret:            .FILL fromdec_ret

        ; --- 3. Parte fraccionaria escalada a 32 bits (base 10^9) ---
fromdec_dec:
        AND     R0, R0, #0
        STI     R0, p_b_frac_l
        STI     R0, p_b_frac_h
        LD      R0, p_b_c9
        LDR     R0, R0, #0
        STI     R0, p_b_contador

fromdec_dec_loop:
        LD      R0, p_b_contador
        LDR     R0, R0, #0
        BRnz    fd_jmp_dec_break_b

        AND     R0, R0, #0
        STI     R0, p_b_current
        LDRB    R0, R4, #0              ; LDRB actualiza NZP

        LD      R1, p_b_neg_zero
        LDR     R1, R1, #0
        ADD     R1, R1, R0
        BRn     fromdec_dec_sk1
        LD      R1, p_b_neg_nine
        LDR     R1, R1, #0
        ADD     R1, R1, R0
        BRp     fromdec_dec_sk1

        LD      R1, p_b_neg_zero
        LDR     R1, R1, #0
        ADD     R1, R1, R0
        STI     R1, p_b_current
        ADD     R4, R4, #1
        BR      fromdec_dec_increment

fromdec_dec_sk1:
        BRz     fromdec_dec_increment
        OR      R5, R5, #1              ; INVALID_INPUT (bit 0)

fromdec_dec_increment:
        ; [aux_h:aux_l] = 4 * [fraccion_h:fraccion_l]
        LD      R0, p_b_frac_h
        LDR     R0, R0, #0
        LD      R1, p_b_frac_l
        LDR     R1, R1, #0
        LSHO    R2, R0, #2
        LSH     R0, R0, #2
        LSHO    R3, R1, #2
        LSH     R1, R1, #2
        OR      R0, R0, R3
        STI     R0, p_b_aux_h
        STI     R1, p_b_aux_l

        ; [aux_h:aux_l] = 5 * [fraccion_h:fraccion_l]
        LD      R2, p_b_aux_l
        LDR     R2, R2, #0
        LD      R1, p_b_frac_l
        LDR     R1, R1, #0
        AND     R3, R3, #0
        ADD     R2, R2, R1
        ADC     R3, R3, R3
        STI     R2, p_b_aux_l

        LD      R2, p_b_aux_h
        LDR     R2, R2, #0
        LD      R1, p_b_frac_h
        LDR     R1, R1, #0
        ADD     R2, R2, R1
        ADD     R2, R2, R3
        STI     R2, p_b_aux_h

        ; [fraccion_h:fraccion_l] = 2 * [aux_h:aux_l] = 10 * frac
        LD      R0, p_b_aux_h
        LDR     R0, R0, #0
        LD      R1, p_b_aux_l
        LDR     R1, R1, #0
        LSHO    R2, R1, #1
        LSH     R1, R1, #1
        LSH     R0, R0, #1
        OR      R0, R0, R2
        STI     R0, p_b_frac_h
        STI     R1, p_b_frac_l

        ; Sumar dígito actual en parte baja de 32 bits
        LD      R2, p_b_current
        LDR     R2, R2, #0
        AND     R3, R3, #0
        ADD     R1, R1, R2
        ADC     R0, R0, R3
        STI     R1, p_b_frac_l
        STI     R0, p_b_frac_h

        LD      R0, p_b_contador
        LDR     R0, R0, #0
        ADD     R0, R0, #-1
        STI     R0, p_b_contador
        BR      fromdec_dec_loop

fd_jmp_dec_break_b:
        LD      R7, p_b_dec_break
        JMP     R7

; --- Bloque de punteros #2 (cubre parte decimal y enlace a Q0.16) ---
p_b_frac_h:         .FILL fromdec_fraccion_h
p_b_frac_l:         .FILL fromdec_fraccion_l
p_b_aux_h:          .FILL fromdec_aux_h
p_b_aux_l:          .FILL fromdec_aux_l
p_b_current:        .FILL fromdec_current
p_b_contador:       .FILL fromdec_contador
p_b_c9:             .FILL fromdec_c9
p_b_neg_zero:       .FILL fromdec_neg_zero
p_b_neg_nine:       .FILL fromdec_neg_nine
p_b_dec_break:      .FILL fromdec_dec_break

        ; --- 4. Convertir fracción decimal (10^9) a 16 bits Q0.16 ---
fromdec_dec_break:
        AND     R0, R0, #0
        STI     R0, p_c_contador
        STI     R0, p_c_fraccion

fromdec_dec_loop2:
        ; Duplicar valor decimal de 32 bits: val32 = val32 * 2
        LD      R0, p_c_frac_h
        LDR     R0, R0, #0
        LD      R1, p_c_frac_l
        LDR     R1, R1, #0
        LSHO    R2, R1, #1
        LSH     R1, R1, #1
        LSH     R0, R0, #1
        OR      R0, R0, R2
        STI     R0, p_c_frac_h
        STI     R1, p_c_frac_l

        ; Comparar val32 contra 1_000_000_000: aux32 = val32 - 1_000_000_000
        LD      R2, p_c_neg_frac_l
        LDR     R2, R2, #0
        LD      R3, p_c_neg_frac_h
        LDR     R3, R3, #0
        AND     R4, R4, #0
        ADD     R1, R1, R2
        ADC     R0, R0, R3
        STI     R1, p_c_aux_l
        STI     R0, p_c_aux_h

        ; Si ya se generaron los 16 bits Q0.16 (contador >= 16), redondear y salir
        LD      R0, p_c_contador
        LDR     R0, R0, #0
        LD      R1, p_c_neg_16
        LDR     R1, R1, #0
        ADD     R0, R0, R1
        BRzp    fromdec_dec_round

        ; Desplazar acumulador Q0.16 a la izquierda 1 bit
        LD      R0, p_c_fraccion
        LDR     R0, R0, #0
        LSH     R0, R0, #1

        ; Si val32 >= 1_000_000_000 (aux_h >= 0), el bit es 1 y actualizamos val32 = aux32
        LD      R1, p_c_aux_h
        LDR     R1, R1, #0
        BRn     fromdec_dec_continue2
        OR      R0, R0, #1
        LD      R1, p_c_aux_l
        LDR     R1, R1, #0
        STI     R1, p_c_frac_l
        LD      R1, p_c_aux_h
        LDR     R1, R1, #0
        STI     R1, p_c_frac_h

fromdec_dec_continue2:
        STI     R0, p_c_fraccion
        LD      R0, p_c_contador
        LDR     R0, R0, #0
        ADD     R0, R0, #1
        STI     R0, p_c_contador
        BR      fromdec_dec_loop2

fromdec_dec_round:
        ; Redondeo al más cercano usando el bit 17 (aux_h >= 0)
        LD      R0, p_c_aux_h
        LDR     R0, R0, #0
        BRn     fd_jmp_ret_c
        LD      R0, p_c_fraccion
        LDR     R0, R0, #0
        ADD     R0, R0, #1
        STI     R0, p_c_fraccion
        BRnp    fd_jmp_ret_c

        ; Si fraccion Q0.16 desborda a 0 (65536 -> 0), incrementar parte entera
        LD      R0, p_c_entero
        LDR     R0, R0, #0
        ADD     R0, R0, #1
        STI     R0, p_c_entero

fd_jmp_ret_c:
        LD      R7, p_c_ret
        JMP     R7

; --- Bloque de punteros #3 (cubre conversión Q0.16 y retorno) ---
p_c_contador:       .FILL fromdec_contador
p_c_fraccion:       .FILL fromdec_fraccion
p_c_frac_h:         .FILL fromdec_fraccion_h
p_c_frac_l:         .FILL fromdec_fraccion_l
p_c_aux_h:          .FILL fromdec_aux_h
p_c_aux_l:          .FILL fromdec_aux_l
p_c_neg_frac_h:     .FILL fromdec_neg_frac_h
p_c_neg_frac_l:     .FILL fromdec_neg_frac_l
p_c_neg_16:         .FILL fromdec_neg_16
p_c_entero:         .FILL fromdec_entero
p_c_negativo:       .FILL fromdec_negativo
p_c_has_number:     .FILL fromdec_has_number
p_c_r2:             .FILL fromdec_r2
p_c_r3:             .FILL fromdec_r3
p_c_r4:             .FILL fromdec_r4
p_c_r7:             .FILL fromdec_r7
p_c_ret:            .FILL fromdec_ret

        ; --- 5. Retorno y aplicación de signo ---
fromdec_ret:
        LD      R0, p_c_has_number
        LDR     R0, R0, #0
        BRnp    fromdec_ret_sk1
        OR      R5, R5, #1              ; INVALID_INPUT si no hubo dígitos

fromdec_ret_sk1:
        LD      R0, p_c_negativo
        LDR     R0, R0, #0
        BRz     fromdec_ret_skp_neg

        LD      R0, p_c_entero
        LDR     R0, R0, #0
        LD      R1, p_c_fraccion
        LDR     R1, R1, #0
        NOT     R0, R0
        NOT     R1, R1
        ADD     R1, R1, #1
        BRnp    fromdec_neg_store
        ADD     R0, R0, #1

fromdec_neg_store:
        STI     R0, p_c_entero
        STI     R1, p_c_fraccion

fromdec_ret_skp_neg:
        LD      R0, p_c_entero
        LDR     R0, R0, #0
        LD      R1, p_c_fraccion
        LDR     R1, R1, #0
        LD      R2, p_c_r2
        LDR     R2, R2, #0
        LD      R3, p_c_r3
        LDR     R3, R3, #0
        LD      R4, p_c_r4
        LDR     R4, R4, #0
        LD      R7, p_c_r7
        LDR     R7, R7, #0
        RET

;=====================================================================
; ZONA DE DATOS Y CONSTANTES
;=====================================================================
fromdec_entero:       .FILL #0
fromdec_fraccion:     .FILL #0
fromdec_negativo:     .FILL #0
fromdec_has_number:   .FILL #0
fromdec_fraccion_h:   .FILL #0
fromdec_fraccion_l:   .FILL #0
fromdec_aux_h:        .FILL #0
fromdec_aux_l:        .FILL #0
fromdec_current:      .FILL #0
fromdec_contador:     .FILL #0

fromdec_r2:           .FILL #0
fromdec_r3:           .FILL #0
fromdec_r4:           .FILL #0
fromdec_r7:           .FILL #0

fromdec_c9:           .FILL #9
fromdec_c10:          .FILL #10
fromdec_neg_16:       .FILL #-16
fromdec_neg_plus:     .FILL #-43
fromdec_neg_period:   .FILL #-44
fromdec_neg_minus:    .FILL #-45
fromdec_neg_dot:      .FILL #-46
fromdec_neg_zero:     .FILL #-48
fromdec_neg_eight:    .FILL #-56
fromdec_neg_nine:     .FILL #-57
fromdec_neg_overchk:  .FILL #-3276
fromdec_neg_frac_h:   .FILL xC465
fromdec_neg_frac_l:   .FILL x3600

.END