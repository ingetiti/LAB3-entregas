; ============================================================================
; Subrutina: FROMDEC  [LC-3X — adaptada]
;     Convierte una cadena decimal ASCII al valor Q (entero + fraccion).
;     Lee 1 byte por caracter con LDBL.
; ============================================================================

.EXTERNAL SUMOVER-SUMOVER

FROMDEC
    PUSHM #x9C                  ; Guarda R2, R3, R4, R7 en la pila

    AND R5 R5 #0                ; errores = 0
    ADD R4 R0 #0                ; [R4] cursor del texto

    AND R0 R0 #0
    ST R0 fromdec_entero
    ST R0 fromdec_fraccion
    ST R0 fromdec_negativo
    ST R0 fromdec_has_number

; ==- Signo ==================================================================
    LDBL R0 R4 #0               ; char = buf[cursor]
    MOVI R1 #-45                ; -ord('-')
    ADD R1 R1 R0
    BRnp fromdec_int_plus_chk   ; if char == '-':
    AND R1 R1 #0
    ADD R1 R1 #1
    ST R1 fromdec_negativo      ;   negativo = 1
    ADD R4 R4 #1                ;   cursor++
    BRnzp fromdec_int_loop

fromdec_int_plus_chk
    MOVI R1 #-43                ; -ord('+')
    ADD R1 R1 R0
    BRnp fromdec_int_loop       ; elif char == '+':
    ADD R4 R4 #1                ;   cursor++

; ==- Parte entera ===========================================================
fromdec_int_loop
    LDBL R0 R4 #0               ; char = buf[cursor]

    BRz fromdec_ret             ; if char == '\0': return

    MOVI R1 #-46                ; -ord('.')
    ADD R1 R1 R0
    BRz fromdec_int_period_found
    MOVI R1 #-44                ; -ord(',')
    ADD R1 R1 R0
    BRz fromdec_int_period_found
    BRnzp fromdec_int_range_chk

fromdec_int_period_found        ; if char == '.' or char == ',':
    ADD R4 R4 #1                ;   cursor++
    BRnzp fromdec_dec

fromdec_int_range_chk
    MOVI R1 #-48                ; -ord('0')
    ADD R1 R1 R0
    BRn fromdec_int_invalid
    MOVI R1 #-57                ; -ord('9')
    ADD R1 R1 R0
    BRp fromdec_int_invalid     ; if '0'<=char<='9':

    LD R1 fromdec_entero
    LD R2 fromdec_neg_overchk
    ADD R2 R2 R1
    BRp fromdec_int_overflow
    BRn fromdec_int_append
    MOVI R2 #-56                ; -ord('8')
    LD R3 fromdec_negativo
    NEG R3 R3
    ADD R2 R2 R3
    ADD R2 R2 R0
    BRn fromdec_int_append

fromdec_int_overflow
    NOT R5 R5
    AND R5 R5 #-3
    NOT R5 R5                   ; OVERFLOW

fromdec_int_append
    ADD R2 R1 R1
    ADD R2 R2 R2
    ADD R2 R2 R1
    ADD R1 R2 R2                ; entero = entero * 10

    MOVI R2 #-48
    ADD R1 R1 R2
    ADD R1 R1 R0                ; entero += char - '0'

    AND R2 R2 #0
    ADD R2 R2 #1
    ST R2 fromdec_has_number    ; tiene_numero = 1
    ADD R4 R4 #1                ; cursor++
    ST R1 fromdec_entero
    BRnzp fromdec_int_loop

fromdec_int_invalid
    NOT R5 R5
    AND R5 R5 #-2
    NOT R5 R5                   ; INVALID_INPUT

; ==- Return y Epilogo =======================================================
fromdec_ret
    LD R0 fromdec_has_number
    BRnp fromdec_ret_sk1
    NOT R5 R5
    AND R5 R5 #-2
    NOT R5 R5                   ; INVALID_INPUT (si no hubo ningun digito)

fromdec_ret_sk1
    LD R0 fromdec_negativo
    BRz fromdec_ret_skp_neg
    LD R0 fromdec_entero
    NOT R0 R0
    LD R1 fromdec_fraccion
    BRnp fromdec_ret_sk2
    ADD R0 R0 #1
fromdec_ret_sk2
    NOT R1 R1
    ADD R1 R1 #1
    ST R0 fromdec_entero
    ST R1 fromdec_fraccion      ; negar resultado si negativo

fromdec_ret_skp_neg
    LD R0 fromdec_entero
    LD R1 fromdec_fraccion
    POPM #x9C                   ; Restaura R2, R3, R4, R7
    RET

; ==- Pool de variables central ==============================================
sub_sumover             .FILL SUMOVER-SUMOVER
fromdec_entero          .FILL #0
fromdec_fraccion        .FILL #0
fromdec_negativo        .FILL #0
fromdec_has_number      .FILL #0
fromdec_fraccion_h      .FILL #0
fromdec_fraccion_l      .FILL #0
fromdec_aux_h           .FILL #0
fromdec_aux_l           .FILL #0
fromdec_current         .FILL #0
fromdec_contador        .FILL #0

fromdec_neg_overchk     .FILL #-3276
fromdec_neg_frac_h      .FILL xC465
fromdec_neg_frac_l      .FILL x3600     ; -1_000_000_000

; ==- Parte fraccionaria =====================================================
fromdec_dec
    AND R0 R0 #0
    ST R0 fromdec_fraccion_l
    ST R0 fromdec_fraccion_h
    MOVI R0 #9
    ST R0 fromdec_contador      ; contador = 9

fromdec_dec_loop
    LD R0 fromdec_contador
    BRnz fromdec_dec_break      ; while contador > 0:
    AND R0 R0 #0
    ST R0 fromdec_current
    LDBL R0 R4 #0               ; char = buf[cursor]

    MOVI R1 #-48
    ADD R1 R1 R0
    BRn fromdec_dec_sk1
    MOVI R1 #-57
    ADD R1 R1 R0
    BRp fromdec_dec_sk1         ; if '0'<=char<='9':
    MOVI R1 #-48
    ADD R1 R1 R0
    ST R1 fromdec_current       ;   current = char - '0'
    ADD R4 R4 #1                ;   cursor++
    BRnzp fromdec_dec_increment

fromdec_dec_sk1
    ADD R0 R0 #0
    BRz fromdec_dec_increment   ; elif char != '\0':
    NOT R5 R5
    AND R5 R5 #-2
    NOT R5 R5                   ;   INVALID_INPUT

fromdec_dec_increment
    LD R0 fromdec_fraccion_h
    LD R1 fromdec_fraccion_l
    ADD R0 R0 R0
    ADD R1 R1 #0
    BRzp fromdec_dec_incr_sk1
    ADD R0 R0 #1
fromdec_dec_incr_sk1
    ADD R1 R1 R1                ; [R0,R1] = [h,l] * 2

    ADD R0 R0 R0
    ADD R1 R1 #0
    BRzp fromdec_dec_incr_sk2
    ADD R0 R0 #1
fromdec_dec_incr_sk2
    ADD R1 R1 R1                ; [R0,R1] = [h,l] * 4
    ST R0 fromdec_aux_h
    ST R1 fromdec_aux_l

    LD R0 fromdec_aux_l
    LD R1 fromdec_fraccion_l
    AND R2 R2 #0
    LD R3 sub_sumover
    JSRR R3
    ST R0 fromdec_aux_l
    LD R0 fromdec_aux_h
    LD R1 fromdec_fraccion_h
    ADD R0 R0 R1
    ADD R0 R0 R2
    ST R0 fromdec_aux_h         ; [aux_h,l] = [h,l] * 5

    LD R0 fromdec_aux_h
    LD R1 fromdec_aux_l
    ADD R0 R0 R0
    ADD R1 R1 #0
    BRzp fromdec_dec_incr_sk3
    ADD R0 R0 #1
fromdec_dec_incr_sk3
    ADD R1 R1 R1
    ST R0 fromdec_fraccion_h
    ST R1 fromdec_fraccion_l    ; [h,l] = [h,l] * 10

    LD R0 fromdec_fraccion_l
    LD R1 fromdec_current
    ADD R0 R0 R1
    ST R0 fromdec_fraccion_l    ; fraccion_l += current

    LD R0 fromdec_contador
    ADD R0 R0 #-1
    ST R0 fromdec_contador      ; contador--
    BRnzp fromdec_dec_loop

fromdec_tramp_ret
    BRnzp fromdec_ret

fromdec_dec_break
    AND R0 R0 #0
    ST R0 fromdec_contador      ; contador = 0

fromdec_dec_loop2
    LD R0 fromdec_fraccion_h
    LD R1 fromdec_fraccion_l
    ADD R0 R0 R0
    ADD R1 R1 #0
    BRzp fromdec_dec_loop2_sk1
    ADD R0 R0 #1
fromdec_dec_loop2_sk1
    ADD R1 R1 R1
    ST R0 fromdec_fraccion_h
    ST R1 fromdec_fraccion_l    ; [h,l] <<= 1

    LD R0 fromdec_fraccion_l
    LD R1 fromdec_neg_frac_l
    AND R2 R2 #0
    LD R3 sub_sumover
    JSRR R3
    ST R0 fromdec_aux_l
    LD R0 fromdec_fraccion_h
    LD R1 fromdec_neg_frac_h
    ADD R0 R0 R1
    ADD R0 R0 R2
    ST R0 fromdec_aux_h         ; [aux_h,l] = [h,l] - 1_000_000_000

    LD R0 fromdec_contador
    MOVI R3 #-16
    ADD R0 R0 R3                ; contador - 16
    BRn fromdec_dec_increment2  ; if contador >= 16:

    LD R0 fromdec_aux_h
    BRn fromdec_tramp_ret       ; if [aux_h,l] >= 0:
    LD R0 fromdec_fraccion
    ADD R0 R0 #1
    ST R0 fromdec_fraccion      ;   fraccion++

    BRnp fromdec_tramp_ret      ; if fraccion == 0:
    LD R0 fromdec_entero
    ADD R0 R0 #1
    ST R0 fromdec_entero        ;   entero++

    BR fromdec_tramp_ret

fromdec_dec_increment2
    LD R0 fromdec_fraccion
    ADD R0 R0 R0
    ST R0 fromdec_fraccion      ; fraccion <<= 1

    LD R0 fromdec_aux_h
    BRn fromdec_dec_continue2
    LD R0 fromdec_fraccion
    ADD R0 R0 #1
    ST R0 fromdec_fraccion      ; fraccion |= 1
    LD R0 fromdec_aux_l
    ST R0 fromdec_fraccion_l
    LD R0 fromdec_aux_h
    ST R0 fromdec_fraccion_h    ; [h,l] = [aux_h,l]

fromdec_dec_continue2
    LD R0 fromdec_contador
    ADD R0 R0 #1
    ST R0 fromdec_contador      ; contador++
    BRnzp fromdec_dec_loop2

.END
