;   ============================================================================
;   Subrutina: TODEC (OPTIMIZADA PARA ISA 16-BIT)
;       Convierte [R0=entero, R1=fraccion] a cadena decimal en [R2].
;   -> INPUT  [R0] Parte entera, [R1] Parte fraccionaria, [R2] Buffer, [R3] Formato
;   <- OUTPUT [R2] Puntero al buffer cargado.
;   ============================================================================

TODEC
    PUSHM {R0, R1, R2, R3, R4, R5, R7}

    ST   R1, todec_fraccion
    ST   R3, todec_format

;   ==- Signo -=================================================================
    CMP  R0, #0
    BRzp todec_sig_elif
    MOVI R4, #45                ; '-'
    STB  R4, R2, #0
    ADD  R2, R2, #1
    NOT  R0, R0
    CMP  R1, #0
    BRnp todec_sig_sk1
    ADD  R0, R0, #1
todec_sig_sk1
    NOT  R1, R1
    ADD  R1, R1, #1
    ST   R1, todec_fraccion
    BRnzp todec_int

todec_sig_elif
    AND  R4, R3, #1
    BRz  todec_int
    MOVI R4, #43                ; '+'
    STB  R4, R2, #0
    ADD  R2, R2, #1

;   ==- Entero (atajos 0..9 / 10..99 y bucle DIV/REM para >= 100) -=============
todec_int
    CMP  R0, #0
    BRn  todec_int_x8000        ; caso especial x8000 (32768 sin signo)
    MOVI R4, #10
    CMP  R0, R4                 ; R0 in [0..9]?
    BRn  todec_int_1d
    LD   R5, todec_100
    CMP  R0, R5                 ; R0 in [10..99]?
    BRzp todec_int_multi
    DIV  R7, R0, R4             ; decena (1..9), R4 ya es 10
    REM  R0, R0, R4             ; unidad (0..9)
    ADDI R7, #48
    STB  R7, R2, #0
    ADD  R2, R2, #1
todec_int_1d
    ADDI R0, #48                ; '0'..'9'
    STB  R0, R2, #0
    ADD  R2, R2, #1
    BRnzp todec_early

todec_int_multi
    LEA  R5, todec_int_divs     ; {10000, 1000, 100, 10, 1, 0}
    BRnzp todec_int_loop

todec_int_x8000
    LEA  R5, todec_int_divs
    MOVI R4, #51                ; '3'
    STB  R4, R2, #0
    ADD  R2, R2, #1
    OR   R3, R3, #2
    LD   R4, todec_neg_30000
    ADD  R0, R0, R4
    ADD  R5, R5, #2

todec_int_loop
    LDR  R4, R5, #0
    BRz  todec_early
    DIV  R7, R0, R4
    REM  R0, R0, R4
    AND  R1, R3, #2
    BRnp todec_int_emit
    CMP  R7, #0
    BRz  todec_int_next
todec_int_emit
    OR   R3, R3, #2
    ADDI R7, #48
    STB  R7, R2, #0
    ADD  R2, R2, #1
todec_int_next
    ADD  R5, R5, #2
    BRnzp todec_int_loop

;   ==- Retorno temprano si fraccion == 0 -=====================================
todec_early
    LD   R0, todec_fraccion
    BRnp todec_dec
    AND  R4, R3, #4
    BRz  todec_early_null
    MOVI R4, #46                ; '.'
    STB  R4, R2, #0
    ADD  R2, R2, #1
    MOVI R4, #48
    MOVI R5, #9
todec_early_zloop
    STB  R4, R2, #0
    ADD  R2, R2, #1
    ADD  R5, R5, #-1
    BRp  todec_early_zloop
todec_early_null
    MOVI R4, #0
    STB  R4, R2, #0
    POPM {R0, R1, R2, R3, R4, R5, R7}
    RET

;   ==- Datos locales (zona central) -==========================================
todec_fraccion      .FILL #0
todec_format        .FILL #0
todec_neg_30000     .FILL #-30000
todec_100           .FILL #100
todec_m12955        .FILL #-12955
todec_15258         .FILL x3B9A

todec_int_divs      .FILL #10000
                    .FILL #1000
                    .FILL #100
                    .FILL #10
                    .FILL #1
                    .FILL #0

;   ==- Decimal: calculo cerrado exacto [R1:R2] via MULL/MULH (sin bucle) -====
;   10^9 / 2^16 = 15258 + 202/256; bits [15:7] son multiplos exactos de
;   1953125 = 30*65536 - 12955, y los 7 bits bajos [6:0] suman f_lo*15258 + corr
todec_dec
    MOVI R4, #46                ; '.'
    STB  R4, R2, #0
    ADD  R2, R2, #1
    PUSHM {R2, R3}              ; guarda cursor_wr (R2) y format (R3) en pila

    ; Parte alta exacta: f_hi = f >> 7 (0..511), [R1:R2] = f_hi * 1953125
    LSR  R1, R0, #7
    LD   R4, todec_m12955       ; -12955
    MULL R2, R1, R4             ; lo16
    MULH R3, R1, R4             ; hi16 signed de f_hi * (-12955)
    MOVI R4, #30
    MULL R1, R1, R4             ; 30 * f_hi (0..15330)
    ADD  R1, R1, R3             ; hi16 exacto

    ; Parte baja: f_lo = f & 0x7F (0..127); si es 0 (Q7.8/Q8.7/Q6.9) termina ya
    SHL  R0, R0, #9
    LSR  R0, R0, #9
    BRz  todec_split_9

    ; lo_part = f_lo * 15258 + corr(f_lo)  [exacto para los 65536 valores uint16]
    LD   R4, todec_15258        ; 15258 (x3B9A)
    MULL R5, R0, R4             ; lo16 de f_lo * 15258
    MULH R4, R0, R4             ; hi16 de f_lo * 15258 (0..29)

    ; corr = 12*(f_lo>>4) + (f_lo>>5) + ((f_lo>>1)&1) + 3*((f_lo>>2)&3)  (0..97)
    LSR  R3, R0, #4
    SHL  R7, R3, #1
    ADD  R3, R3, R7             ; 3*(f_lo>>4)
    SHL  R3, R3, #2             ; 12*(f_lo>>4)
    LSR  R7, R0, #5
    ADD  R3, R3, R7
    LSR  R7, R0, #1
    AND  R7, R7, #1
    ADD  R3, R3, R7
    LSR  R7, R0, #2
    AND  R7, R7, #3
    ADD  R3, R3, R7
    SHL  R7, R7, #1
    ADD  R3, R3, R7             ; R3 = corr (0..97)

    ; [R4:R7] = [R4:R5] + corr (carry sin signo: bit15(R5) & ~bit15(R5+corr))
    ADD  R7, R5, R3
    NOT  R0, R7
    AND  R0, R5, R0
    LSR  R0, R0, #15
    ADD  R4, R4, R0

    ; [R1:R2] += [R4:R7] (suma 32-bit sin signo sin saltos)
    ADD  R5, R2, R7             ; sum_lo
    AND  R0, R2, R7             ; a & b
    OR   R2, R2, R7             ; a | b
    NOT  R3, R5                 ; ~sum
    AND  R2, R2, R3             ; (a | b) & ~sum
    OR   R0, R0, R2             ; carry en bit 15
    LSR  R0, R0, #15
    ADD  R1, R1, R4
    ADD  R1, R1, R0
    ADD  R2, R5, #0

;   ==- Division exacta de 30-bit [R1:R2] por 100000 via MULH/MULL -===========
todec_split_9
    ; q_est = (R1 * 21474) >> 15  (error 0..2 respecto a N / 100000)
    LD   R5, todec_21474
    MULL R3, R1, R5
    MULH R4, R1, R5
    LSR  R3, R3, #15
    SHL  R4, R4, #1
    OR   R3, R3, R4             ; R3 = q_est (0..9999)

    ; P = q_est * 100000 = [2*q_est + MULH(q_est, -31072) : MULL(q_est, -31072)]
    LD   R5, todec_m31072
    MULL R4, R3, R5             ; P_lo
    MULH R5, R3, R5
    SHL  R7, R3, #1
    ADD  R5, R5, R7             ; P_hi

    ; rem = [R1:R2] - [R5:R4]
    SUB  R7, R2, R4             ; rem_lo
    ; borrow unsigned de R2 - R4: ((~R2 & R4) | ((~R2 | R4) & R7)) >>> 15
    NOT  R0, R2
    AND  R2, R0, R4             ; ~a & b
    OR   R0, R0, R4             ; ~a | b
    AND  R0, R0, R7             ; (~a | b) & diff
    OR   R0, R0, R2
    LSR  R0, R0, #15            ; borrow (0 o 1)
    SUB  R1, R1, R5
    SUB  R1, R1, R0             ; rem_hi (0..4)
    ADD  R2, R7, #0             ; rem_lo

    ; Ajustar q_est mientras [R1:R2] >= 100000 = [1 : x86A0] (max 2 veces)
    LD   R5, todec_m31072       ; x86A0 = 34464 unsigned
td_adj_loop
    CMP  R1, #0
    BRz  td_adj_done
    CMP  R1, #1
    BRp  td_adj_sub
    ; R1 == 1: comparar unsigned R2 >= 34464 (bit 15 == 1 y R2 >= -31072)
    CMP  R2, #0
    BRzp td_adj_done
    CMP  R2, R5
    BRn  td_adj_done
td_adj_sub
    ; [R1:R2] -= [1 : x86A0]
    SUB  R7, R2, R5
    NOT  R0, R2
    AND  R4, R0, R5
    OR   R0, R0, R5
    AND  R0, R0, R7
    OR   R0, R0, R4
    LSR  R0, R0, #15
    ADD  R1, R1, #-1
    SUB  R1, R1, R0
    ADD  R2, R7, #0
    ADD  R3, R3, #1
    BRnzp td_adj_loop

td_adj_done
    ; Ahora R3 = hi4 (0..9999) y [R1:R2] = rem5 (0..99999)
    ; Separar rem5 en d5 (0..9) y rem4 (0..9999)
    MOVI R4, #0                 ; d5 = 0
    CMP  R1, #0
    BRz  td_rem5_hi0
    ; R1 == 1: 65536 = 6*10000 + 5536
    LD   R5, todec_5536
    ADD  R2, R2, R5
    MOVI R4, #6
td_rem5_hi0
    LD   R5, todec_neg_30000_b
td_rem5_u16
    CMP  R2, #0
    BRzp td_rem5_pos
    ADD  R2, R2, R5             ; -= 30000
    ADD  R4, R4, #3
    BRnzp td_rem5_u16
td_rem5_pos
    LD   R5, todec_10000
    DIV  R7, R2, R5
    REM  R2, R2, R5             ; R2 = rem4 (0..9999)
    ADD  R4, R4, R7             ; R4 = d5 (0..9)
    ST   R4, todec_d5
    ST   R2, todec_rem4

    ; Emitir los 4 digitos altos (R3 = hi4)
    POPM {R0, R1}               ; R0 = cursor_wr, R1 = format
    AND  R1, R1, #4             ; R1 = SHOW_ENDZ
    OR   R2, R4, R2             ; R2 != 0 si hay digitos bajos no nulos
    LEA  R5, todec_lo_divs      ; {1000, 100, 10, 1, 0}

td_emit_hi4
    LDR  R4, R5, #0
    BRz  td_emit_d5
    DIV  R7, R3, R4
    REM  R3, R3, R4
    ADDI R7, #48
    STB  R7, R0, #0
    ADD  R0, R0, #1
    CMP  R1, #0
    BRnp td_hi4_next
    OR   R7, R3, R2
    BRz  todec_dec_done
td_hi4_next
    ADD  R5, R5, #2
    BRnzp td_emit_hi4

td_emit_d5
    LD   R7, todec_d5
    ADDI R7, #48
    STB  R7, R0, #0
    ADD  R0, R0, #1
    LD   R2, todec_rem4
    CMP  R1, #0
    BRnp td_emit_lo4_start
    CMP  R2, #0
    BRz  todec_dec_done

td_emit_lo4_start
    LEA  R5, todec_lo_divs
td_emit_lo4
    LDR  R4, R5, #0
    BRz  todec_dec_done
    DIV  R7, R2, R4
    REM  R2, R2, R4
    ADDI R7, #48
    STB  R7, R0, #0
    ADD  R0, R0, #1
    CMP  R1, #0
    BRnp td_lo4_next
    CMP  R2, #0
    BRz  todec_dec_done
td_lo4_next
    ADD  R5, R5, #2
    BRnzp td_emit_lo4

todec_dec_done
    MOVI R4, #0
    STB  R4, R0, #0

todec_ret
    POPM {R0, R1, R2, R3, R4, R5, R7}
    RET

todec_d5            .FILL #0
todec_rem4          .FILL #0
todec_neg_30000_b   .FILL #-30000
todec_5536          .FILL #5536
todec_10000         .FILL #10000
todec_21474         .FILL #21474
todec_m31072        .FILL #-31072       ; x86A0 = 34464 unsigned
todec_lo_divs       .FILL #1000
                    .FILL #100
                    .FILL #10
                    .FILL #1
                    .FILL #0

.END
