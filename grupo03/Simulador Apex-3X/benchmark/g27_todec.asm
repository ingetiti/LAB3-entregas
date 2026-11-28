; ============================================================================
; Subrutina: TODEC  [LC-3X — optimizada]
;     Convierte un valor Q (entero + fraccion) a cadena decimal ASCII.
;     El buffer recibe 1 caracter por BYTE.
;     Preserva contrato, formato (SHOW_PLUS=1, SHOW_LEADZ=2, SHOW_ENDZ=4)
;     y salida identica caracter por caracter.
; ============================================================================

.EXTERNAL SUMOVER-SUMOVER

TODEC
    PUSHM #xBF                  ; Guarda R0..R5, R7
    ADD R4 R2 #0                ; R4 = cursor de escritura en buffer
    ST R3 todec_fmt
    ST R1 todec_frac

; ==- Signo ==================================================================
    ADD R0 R0 #0
    BRzp todec_sig_pos
    MOVI R5 #45                 ; '-'
    STBL R5 R4 #0
    ADD R4 R4 #1
    NOT R0 R0
    ADD R1 R1 #0
    BRnp todec_neg_ok
    ADD R0 R0 #1
todec_neg_ok
    NEG R1 R1
    ST R1 todec_frac
    BRnzp todec_int

todec_sig_pos
    AND R5 R3 #1                ; SHOW_PLUS?
    BRz todec_int
    MOVI R5 #43                 ; '+'
    STBL R5 R4 #0
    ADD R4 R4 #1

; ==- Parte entera ===========================================================
todec_int
    AND R2 R3 #7                ; R2 = fmt (bits 0..2)
    AND R5 R2 #2                ; SHOW_LEADZ?
    BRnp todec_int_do
    ADD R0 R0 #0
    BRnp todec_int_do
    MOVI R5 #48                 ; '0'
    STBL R5 R4 #0
    ADD R4 R4 #1
    BRnzp todec_early

todec_int_do
    LEA R5 todec_pow10
todec_int_lp
    LDR R1 R5 #0
    BRz todec_int_end
    DIVU R3 R0 R1               ; R3 = digito (0..9)
    REMU R0 R0 R1               ; R0 = resto
    ADD R3 R3 #0
    BRnp todec_int_lead
    AND R1 R2 #2
    BRz todec_int_nxt
    BRnzp todec_int_wr
todec_int_lead
    AND R1 R2 #2
    BRnp todec_int_wr
    ADD R2 R2 #2                ; activar SHOW_LEADZ
todec_int_wr
    MOVI R1 #48
    ADD R3 R3 R1
    STBL R3 R4 #0
    ADD R4 R4 #1
todec_int_nxt
    ADD R5 R5 #2
    BRnzp todec_int_lp

todec_int_end
    AND R1 R2 #2
    BRnp todec_early
    MOVI R1 #48
    STBL R1 R4 #0
    ADD R4 R4 #1
    BRnzp todec_early

todec_fmt       .FILL #0
todec_frac      .FILL #0
todec_pow10     .FILL #10000
                .FILL #1000
                .FILL #100
                .FILL #10
                .FILL #1
                .FILL #0

; ==- Prueba para retorno temprano ===========================================
todec_early
    LD R0 todec_frac
    BRnp todec_dec
    AND R1 R2 #4                ; SHOW_ENDZ?
    BRz todec_nul
    MOVI R1 #46                 ; '.'
    STBL R1 R4 #0
    ADD R4 R4 #1
    MOVI R1 #48                 ; '0'
    MOVI R3 #9
todec_ez_lp
    STBL R1 R4 #0
    ADD R4 R4 #1
    ADD R3 R3 #-1
    BRp todec_ez_lp
todec_nul
    AND R0 R0 #0
    STBL R0 R4 #0
    POPM #xBF
    RET

; ==- Decimal ================================================================
todec_dec
    MOVI R1 #46                 ; '.'
    STBL R1 R4 #0
    ADD R4 R4 #1
    ST R4 todec_cursor
    ST R2 todec_fmt

    ; [R5, R1] = floor(frac * 1_000_000_000 / 65536)
    LD R1 todec_1e9_hi          ; x3B9A
    LD R3 todec_1e9_lo          ; xCA00
    MULHU R5 R0 R1              ; hi1
    MUL R1 R0 R1                ; lo1
    MULHU R3 R0 R3              ; hi2
    ADD R1 R1 R3                ; L = lo1 + hi2 (sets C)
    ADC R5 R5 #0                ; H = hi1 + C

    ; Ajuste exacto por truncado por bit en los bits 0..6 de frac
    MOVI R3 #127
    AND R0 R0 R3
    BRz todec_dec_digits
    AND R3 R3 #0
    LEA R2 todec_rem_tbl
todec_rem_lp
    AND R4 R0 #1
    BRz todec_rem_sk
    LDR R4 R2 #0
    ADD R3 R3 R4
todec_rem_sk
    ADD R2 R2 #2
    SHR R0 R0 #1
    BRp todec_rem_lp
    SHR R3 R3 #7                ; deficit = R3 >> 7
    SUB R1 R1 R3
    SBC R5 R5 #0

todec_dec_digits
    ; R5 = H, R1 = L; extraer 9 digitos dividiendo [H,L] por 10
    LEA R4 todec_dbuf
    ADD R4 R4 #7
    ADD R4 R4 #1                ; apunta al 9no digito (menos significativo)
    ST R4 todec_dptr
    LD R2 todec_fmt
    AND R2 R2 #4                ; SHOW_ENDZ?
    BRz todec_endz_zero
    ST R4 todec_dend            ; con SHOW_ENDZ, imprimir los 9 digitos
    BRnzp todec_dig_init
todec_endz_zero
    AND R2 R2 #0
    ST R2 todec_dend
todec_dig_init
    MOVI R0 #9
    ST R0 todec_cnt
    MOVI R2 #10

todec_dig_lp
    DIVU R0 R5 R2               ; q_h = H / 10
    REMU R5 R5 R2               ; r_h = H % 10
    DIVU R3 R1 R2               ; q_l = L / 10
    REMU R1 R1 R2               ; r_l = L % 10
    ADD R4 R5 R5
    ADD R4 R4 R5
    ADD R4 R4 R4                ; 6 * r_h
    ADD R4 R4 R1                ; rem_sum = 6 * r_h + r_l (0..63)
    REMU R1 R4 R2               ; R1 = digito (0..9)
    DIVU R4 R4 R2               ; R4 = acarreo c1 (0..6)

    ; Guardar digito ASCII en buffer temporal y actualizar fin no-cero
    ST R0 todec_qh
    LD R0 todec_dptr
    ADD R1 R1 #0
    BRz todec_dig_zero
    LD R2 todec_dend
    BRnp todec_dig_zero
    ST R0 todec_dend            ; primer digito no-cero desde la derecha
todec_dig_zero
    MOVI R2 #48
    ADD R1 R1 R2
    STBL R1 R0 #0
    ADD R0 R0 #-1
    ST R0 todec_dptr

    ; L_new = r_h * 6553 + q_l + c1, H_new = q_h
    LD R2 todec_6553
    MUL R5 R5 R2
    ADD R1 R5 R3
    ADD R1 R1 R4
    LD R5 todec_qh

    MOVI R2 #10
    LD R0 todec_cnt
    ADD R0 R0 #-1
    ST R0 todec_cnt
    BRp todec_dig_lp

    ; Copiar digitos al buffer destino hasta todec_dend
    LD R4 todec_cursor
    LEA R0 todec_dbuf
    LD R2 todec_dend
todec_cp_lp
    LDBL R1 R0 #0
    STBL R1 R4 #0
    ADD R4 R4 #1
    SUB R3 R0 R2
    BRz todec_nul
    ADD R0 R0 #1
    BRnzp todec_cp_lp

; ==- Pool de variables y constantes =========================================
todec_cursor    .FILL #0
todec_dptr      .FILL #0
todec_dend      .FILL #0
todec_cnt       .FILL #0
todec_qh        .FILL #0
todec_1e9_hi    .FILL x3B9A
todec_1e9_lo    .FILL xCA00
todec_6553      .FILL #6553
todec_rem_tbl   .FILL #101
                .FILL #74
                .FILL #20
                .FILL #40
                .FILL #80
                .FILL #32
                .FILL #64
todec_dbuf      .BLKW #5

.END
