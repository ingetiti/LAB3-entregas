

.EXTERNAL SUMOVER-SUMOVER
sub_sumover     .FILL SUMOVER-SUMOVER


;   ============================================================================
;   Subrutina: TODEC
;       Convierte un valor a cadena de texto decimal.
;       Utilizara el formato indicado, donde los bits indican:
;       - El bit 0 mostrar signo +.
;       - El bit 1 mantener los 0 a izquierda.
;       - El bit 2 mantener los 0 a derecha.
;       Se espera el valor separado en 2 registros:
;       - En R0 la parte entera (exponentes positivos y cero: [..., 2**1, 2**0])
;       - En R1 la parte fraccionaria (exponentes negativos: [2**-1, 2**-2, ...])
;
;   -> INPUT  [R0] Parte entera.
;   -> INPUT  [R1] Parte fraccionaria.
;   -> INPUT  [R2] Puntero al buffer de la cadena (17 WORDS minimo).
;   -> INPUT  [R3] Formato bits [15:3 none, 2 SHOW_ENDZ, 1 SHOW_LEADZ, 0 SHOW_PLUS]
;   <- OUTPUT [R2] Puntero al buffer de la cadena ya cargada.
;   ============================================================================

TODEC                                   ;
        STI R0, G15_DIR_113
        STI R1, G15_DIR_114
        STI R3, G15_DIR_115
        STI R4, G15_DIR_116
        STI R5, G15_DIR_117
        STI R7, G15_DIR_118

        STI R0, G15_DIR_119
        STI R1, G15_DIR_120
        STI R2, G15_DIR_121
        STI R2, G15_DIR_122
        STI R3, G15_DIR_123

;   ==- Signo -=================================================================
        LDI R0, G15_DIR_119
    BRzp todec_sig_elif                 ;   if [entero] < 0:
        LDI R0, G15_DIR_125
        LDI R1, G15_DIR_122
    STR R0 R1 #0                        ;
        ADD R1, R1, #2
        STI R1, G15_DIR_122
    
        LDI R0, G15_DIR_119
    NOT R0 R0                           ;
        LDI R1, G15_DIR_120
    BRnp todec_sig_sk1                  ;
        ADD R0 R0 #1                    ;
todec_sig_sk1                           ;
    NOT R1 R1                           ;
    ADD R1 R1 #1                        ;
        STI R0, G15_DIR_119
        STI R1, G15_DIR_120
    BRnzp todec_int                     ;
G15_DIR_125 .FILL todec_chr_minus
G15_DIR_123 .FILL todec_format
G15_DIR_122 .FILL todec_cursor_wr
G15_DIR_121 .FILL todec_cursor_beg
G15_DIR_120 .FILL todec_fraccion
G15_DIR_119 .FILL todec_entero
G15_DIR_118 .FILL todec_r7
G15_DIR_117 .FILL todec_r5
G15_DIR_116 .FILL todec_r4
G15_DIR_115 .FILL todec_r3
G15_DIR_114 .FILL todec_r1
G15_DIR_113 .FILL todec_r0

todec_sig_elif                          ;   
        LDI R0, G15_DIR_123
    AND R0 R0 #1                        ;
    BRz todec_int                       ;   elif [format] & SHOW_PLUS:
        LDI R0, G15_DIR_133
        LDI R1, G15_DIR_122
    STR R0 R1 #0                        ;
    ADD R1 R1 #1                        ;
        STI R1, G15_DIR_122

;   ==- Entero -================================================================
todec_int                               ;
        LD R5, G15_DIR_136
        ADD R5, R5, #15
        ADD R5, R5, #1
    LDR R4 R5 #1                        ;   [R4] -expr_actual = -10_000
        LDI R3, G15_DIR_119
    AND R2 R2 #0                        ;   [R2] contador = 0
    
todec_int_loop                          ;   while True:
    ADD R0 R3 R4                        ;       [R0] aux = entero + -expr_actual
    BRn todec_int_format_chk            ;       if aux >= 0:
    ADD R2 R2 #1                        ;           contador = contador + 1
    ADD R3 R0 #0                        ;           entero = aux
    BR todec_int_loop                   ;           continue
G15_DIR_136 .FILL todec_expr_vec
G15_DIR_133 .FILL todec_chr_plus

todec_int_format_chk                    ;
        LDI R0, G15_DIR_123
    AND R0 R0 #2                        ;
    BRnp todec_int_append               ;
    ADD R0 R2 #0                        ;
    BRnp todec_int_append               ;
    BR todec_int_sk1                    ;
G15_DIR_141 .FILL todec_chr_zero
todec_int_append                        ;       if [formato] & SHOW_LEADZ or contador != 0:
        LDI R0, G15_DIR_123
    NOT R0 R0                           ;
    AND R0 R0 #-3                       ;
    NOT R0 R0                           ;
        STI R0, G15_DIR_123
        LDI R0, G15_DIR_141
        LDI R1, G15_DIR_122
    ADD R0 R0 R2                        ;
    STR R0 R1 #0                        ;
        ADD R1, R1, #2
        STI R1, G15_DIR_122

todec_int_sk1                           ;
    AND R2 R2 #0                        ;       contador = 0
        ADD R5, R5, #4
    LDR R4 R5 #1                        ;       -expr_actual = expresiones.peek(1)

    BRz todec_int_break                 ;       if expr_actual == 0:
    BR todec_int_loop                   ;           break
                                        ;       continue

todec_int_break                         ;
        LDI R0, G15_DIR_123
    AND R0 R0 #2                        ;
    BRnp todec_early                    ;   if not [formato] & SHOW_LEADZ:  #(si no se mostro ningun numero)
        LDI R0, G15_DIR_141
        LDI R1, G15_DIR_122
    STR R0 R1 #0                        ;
        ADD R1, R1, #2
        STI R1, G15_DIR_122
    
;   ==- Prueba para retorno temprano -==========================================
todec_early                             ;
    LD R0 todec_fraccion                ;
    BRnp todec_dec                      ;   if decimal == 0:
    LD R1 todec_cursor_wr               ;       [R1] cursor_wr
    LD R0 todec_format                  ;
    AND R0 R0 #4                        ;
    BRz todec_early_chk                 ;       if [formato] & SHOW_ENDZ:
        LDI R0, G15_DIR_147
    STR R0 R1 #0                        ;
    ADD R1 R1 #1                        ;           texto = texto + '.'
        LDI R0, G15_DIR_141
    AND R2 R2 #0                        ;
    ADD R2 R2 #9                        ;           [R2] contador = 9
todec_early_chk_loop                    ;           while contador > 0:
    ADD R2 R2 #0                        ;   
    BRnz todec_early_chk                ;
    STR R0 R1 #0                        ;
    ADD R1 R1 #1                        ;               texto = texto + '0'
    ADD R2 R2 #-1                       ;               contador -= 1
    BRnzp todec_early_chk_loop          ;
G15_DIR_147 .FILL todec_chr_dot

todec_early_chk                         ;
    AND R0 R0 #0                        ;
    STR R0 R1 #0                        ;       texto = texto + '\0'
    ST R1 todec_cursor_wr               ;
    BRnzp todec_ret                     ;       return

;   ==- Decimal -===============================================================
todec_dec                               ;
    LD R0 todec_chr_dot                 ;
    LD R1 todec_cursor_wr               ;
    STR R0 R1 #0                        ;
        ADD R1, R1, #2
    ST R1 todec_cursor_wr               ;   texto = texto + '.'

    AND R0 R0 #0                        ;
    ST R0 todec_fraccion_h              ;   [fraccion_h] = 0
    ST R0 todec_fraccion_l              ;   [fraccion_l] = 0
    
    ST R0 todec_aux_0                   ;
    LD R0 todec_frac_expr_h             ;
    ST R0 todec_aux_1                   ;
    LD R0 todec_frac_expr_l             ;
    ST R0 todec_aux_2                   ;   [aux_0, aux_1, aux_2] = [0, 1_000_000_000]

    AND R5 R5 #0                        ;
    ADD R5 R5 #1                        ;   [R5] mascara = 1

todec_dec_loop1                         ;

    ADD R5 R5 #0                        ;
    BRz todec_dec_break1                ;   while mascara:
    
    LD R0 todec_fraccion                ;
    AND R0 R0 R5                        ;
    BRz todec_dec_continue1             ;       if [fraccion] & mascara:

    LD R0 todec_fraccion_l              ;
    LD R1 todec_aux_1                   ;
    AND R2 R2 #0                        ;
        LDI R3, G15_DIR_148
    JSRR R3                             ;
    ST R0 todec_fraccion_l              ;
    LD R0 todec_fraccion_h              ;
    LD R1 todec_aux_0                   ;
    ADD R0 R0 R1                        ;
    ADD R0 R0 R2                        ;
    ST R0 todec_fraccion_h              ;           [fraccion_h, fraccion_l] = [fraccion_h, fraccion_l] + [aux_0, aux_1]

todec_dec_continue1                     ;
    LD R0 todec_aux_0                   ;
    ADD R0 R0 R0                        ;
    LD R1 todec_aux_1                   ;
    BRzp todec_dec_cont1_sk1            ;
    ADD R0 R0 #1                        ;
todec_dec_cont1_sk1                     ;
    ADD R1 R1 R1                        ;
    LD R2 todec_aux_2                   ;
    BRzp todec_dec_cont1_sk2            ;
    ADD R1 R1 #1                        ;
todec_dec_cont1_sk2                     ;
    ADD R2 R2 R2                        ;
    ST R0 todec_aux_0                   ;
    ST R1 todec_aux_1                   ;
    ST R2 todec_aux_2                   ;       [aux_0, aux_1, aux_2] = [aux_0, aux_1, aux_2] << 1

    ADD R5 R5 R5                        ;       mascara = mascara << 1
    BRnzp todec_dec_loop1               ;       continue
G15_DIR_148 .FILL sub_sumover

todec_dec_break1                        ;
    LEA R5 todec_expr_vec               ;   [R5] expresiones
    AND R4 R4 #0                        ;   [R4] contador = 0

todec_dec_loop2                         ;   while True:
    LD R0 todec_fraccion_l              ;
    LDR R1 R5 #1                        ;
    AND R2 R2 #0                        ;
        LDI R3, G15_DIR_148
    JSRR R3                             ;
    
    LD R1 todec_fraccion_h              ;
    ADD R1 R1 R2                        ;
    LDR R2 R5 #0                        ;
    ADD R1 R1 R2                        ;       [R1, R0] aux = [fraccion_h, fraccion_l] + [expresiones.peek(0), expresiones.peek(1)]

    BRn todec_dec_append                ;       if [fraccion_h, fraccion_l] - [-expresiones.peek(0), expresiones.peek(1)] >= 0:
    ST R1 todec_fraccion_h              ;
    ST R0 todec_fraccion_l              ;           [fraccion_h, fraccion_l] = [R1, R0]
    ADD R4 R4 #1                        ;           contador = contador + 1
    BR todec_dec_loop2                  ;           continue
    
todec_dec_append                        ;
    LD R0 todec_chr_zero                ;
    LD R1 todec_cursor_wr               ;
    ADD R0 R0 R4                        ;
    STR R0 R1 #0                        ;
        ADD R1, R1, #2
    ST R1 todec_cursor_wr               ;       texto = texto + char(contador)

todec_dec_format_chk                    ;
    LD R0 todec_format                  ;
    AND R0 R0 #4                        ;
    BRnp todec_dec_continue2            ;
    LD R0 todec_fraccion_l              ;
    BRnp todec_dec_continue2            ;
    LD R0 todec_fraccion_h              ;
    BRnp todec_dec_continue2            ;       if not [format] & SHOW_ENDZ and [fraccion_h, fraccion_l] == 0:
    BR todec_dec_break2                 ;           break

todec_dec_continue2                     ;
    AND R4 R4 #0                        ;       contador = 0
        ADD R5, R5, #4
    LDR R0 R5 #1                        ;
    BRnp todec_dec_loop2                ;
    LDR R0 R5 #0                        ;
    BRnp todec_dec_loop2                ;       if [expresiones.peek(0), expresiones.peek(1)] == 0:
                                        ;           break

todec_dec_break2                        ;
    LD R1 todec_cursor_wr               ;
    AND R0 R0 #0                        ;   
    STR R0 R1 #0                        ;
        ADD R1, R1, #2
    ST R1 todec_cursor_wr               ;   texto = texto + '\0'

;   ==- Return -================================================================
todec_ret                   
    LD R0 todec_r0                      ;
    LD R1 todec_r1                      ;
    LD R2 todec_cursor_beg              ;
    LD R3 todec_r3                      ;
    LD R4 todec_r4                      ;
    LD R5 todec_r5                      ;
    LD R7 todec_r7                      ;
    RET                                 ;


todec_r0            .FILL #0
todec_r1            .FILL #0
todec_r3            .FILL #0
todec_r4            .FILL #0
todec_r5            .FILL #0
todec_r7            .FILL #0

todec_entero        .FILL #0
todec_fraccion      .FILL #0
todec_cursor_beg    .FILL #0
todec_cursor_wr     .FILL #0
todec_format        .FILL #0
todec_fraccion_h    .FILL #0
todec_fraccion_l    .FILL #0
todec_aux_0         .FILL #0
todec_aux_1         .FILL #0
todec_aux_2         .FILL #0


todec_chr_plus      .FILL #43           ;   ord('+')
todec_chr_minus     .FILL #45           ;   ord('-')
todec_chr_dot       .FILL #46           ;   ord('.')
todec_chr_zero      .FILL #48           ;   ord('0')

todec_frac_expr_h   .FILL x3B9A         ;
todec_frac_expr_l   .FILL xCA00         ;   1_000_000_000

todec_expr_vec      .FILL xfa0a         ;
                    .FILL x1f00         ;  - 10**8          9no digito.
                    .FILL xff67         ;
                    .FILL x6980         ;  - 10**7          8vo digito.
                    .FILL xfff0         ;
                    .FILL xbdc0         ;  - 10**6          7to digito.
                    .FILL xfffe         ;
                    .FILL x7960         ;  - 10**5          6to digito.
                    .FILL xffff         ;
                    .FILL xd8f0         ;  - 10**4          5to digito.
                    .FILL xffff         ;
                    .FILL xfc18         ;  - 10**3          4to digito.
                    .FILL xffff         ;
                    .FILL xff9c         ;  - 10**2          3er digito.
                    .FILL xffff         ;
                    .FILL xfff6         ;  - 10**1          2do digito.
                    .FILL xffff         ;
                    .FILL xffff         ;  - 10**0          1er digito.
                    .FILL x0000         ;
                    .FILL x0000         ;  NULL32           terminacion.

.END
