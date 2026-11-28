

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
    ST R0 todec_r0                      ;
    ST R1 todec_r1                      ;
    ST R3 todec_r3                      ;
    ST R4 todec_r4                      ;
    ST R5 todec_r5                      ;
    ST R7 todec_r7                      ;

    ST R0 todec_entero                  ;   [entero] = entero
    ST R1 todec_fraccion                ;   [fraccion] = fraccion
    ST R2 todec_cursor_beg              ;   [cursor_beg] = cursor
    ST R2 todec_cursor_wr               ;   [cursor_wr] = cursor
    ST R3 todec_format                  ;   [formato] = formato

;   ==- Signo -=================================================================
    LD R0 todec_entero                  ;   
    BRzp todec_sig_elif                 ;   if [entero] < 0:
    LD R0 todec_chr_minus               ;
    LD R1 todec_cursor_wr               ;
    STR R0 R1 #0                        ;
    ADD R1 R1 #1                        ;       
    ST R1 todec_cursor_wr               ;       texto = texto + '-'
    
    LD R0 todec_entero                  ;
    NOT R0 R0                           ;
    LD R1 todec_fraccion                ;
    BRnp todec_sig_sk1                  ;
        ADD R0 R0 #1                    ;
todec_sig_sk1                           ;
    NOT R1 R1                           ;
    ADD R1 R1 #1                        ;
    ST R0 todec_entero                  ;
    ST R1 todec_fraccion                ;       [entero, decimal] = -[entero, decimal]
    BRnzp todec_int                     ;

todec_sig_elif                          ;   
    LD R0 todec_format                  ;
    AND R0 R0 #1                        ;
    BRz todec_int                       ;   elif [format] & SHOW_PLUS:
    LD R0 todec_chr_plus                ;
    LD R1 todec_cursor_wr               ;
    STR R0 R1 #0                        ;
    ADD R1 R1 #1                        ;
    ST R1 todec_cursor_wr               ;       texto = texto + '+'

;   ==- Entero -================================================================
todec_int                               ;
    LEA R5 todec_expr_vec               ;   
    ADD R5 R5 #8                        ;   [R5] expresiones    #(+8 por que comenzamos en 5to digito)
    LDR R4 R5 #1                        ;   [R4] -expr_actual = -10_000
    LD R3 todec_entero                  ;   [R3] entero = [entero]
    AND R2 R2 #0                        ;   [R2] contador = 0
    
todec_int_loop                          ;   while True:
    ADD R0 R3 R4                        ;       [R0] aux = entero + -expr_actual
    BRn todec_int_format_chk            ;       if aux >= 0:
    ADD R2 R2 #1                        ;           contador = contador + 1
    ADD R3 R0 #0                        ;           entero = aux
    BR todec_int_loop                   ;           continue

todec_int_format_chk                    ;
    LD R0 todec_format                  ;
    AND R0 R0 #2                        ;
    BRnp todec_int_append               ;
    ADD R0 R2 #0                        ;
    BRnp todec_int_append               ;
    BR todec_int_sk1                    ;
todec_int_append                        ;       if [formato] & SHOW_LEADZ or contador != 0:
    LD R0 todec_format                  ;
    NOT R0 R0                           ;
    AND R0 R0 #-3                       ;
    NOT R0 R0                           ;
    ST R0 todec_format                  ;           [formato] = [formato] | SHOW_LEADZ
    LD R0 todec_chr_zero                ;
    LD R1 todec_cursor_wr               ;
    ADD R0 R0 R2                        ;
    STR R0 R1 #0                        ;
    ADD R1 R1 #1                        ;
    ST R1 todec_cursor_wr               ;           texto = texto + char(contador)

todec_int_sk1                           ;
    AND R2 R2 #0                        ;       contador = 0
    ADD R5 R5 #2                        ;       expresiones.incr(2)
    LDR R4 R5 #1                        ;       -expr_actual = expresiones.peek(1)

    BRz todec_int_break                 ;       if expr_actual == 0:
    BR todec_int_loop                   ;           break
                                        ;       continue

todec_int_break                         ;
    LD R0 todec_format                  ;
    AND R0 R0 #2                        ;
    BRnp todec_early                    ;   if not [formato] & SHOW_LEADZ:  #(si no se mostro ningun numero)
    LD R0 todec_chr_zero                ;
    LD R1 todec_cursor_wr               ;
    STR R0 R1 #0                        ;
    ADD R1 R1 #1                        ;       
    ST R1 todec_cursor_wr               ;       texto = texto + '0'
    
;   ==- Prueba para retorno temprano -==========================================
todec_early                             ;
    LD R0 todec_fraccion                ;
    BRnp todec_dec                      ;   if decimal == 0:
    LD R1 todec_cursor_wr               ;       [R1] cursor_wr
    LD R0 todec_format                  ;
    AND R0 R0 #4                        ;
    BRz todec_early_chk                 ;       if [formato] & SHOW_ENDZ:
    LD R0 todec_chr_dot                 ;
    STR R0 R1 #0                        ;
    ADD R1 R1 #1                        ;           texto = texto + '.'
    LD R0 todec_chr_zero                ;           [R0] char '0'
    AND R2 R2 #0                        ;
    ADD R2 R2 #9                        ;           [R2] contador = 9
todec_early_chk_loop                    ;           while contador > 0:
    ADD R2 R2 #0                        ;   
    BRnz todec_early_chk                ;
    STR R0 R1 #0                        ;
    ADD R1 R1 #1                        ;               texto = texto + '0'
    ADD R2 R2 #-1                       ;               contador -= 1
    BRnzp todec_early_chk_loop          ;

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
    ADD R1 R1 #1                        ;   
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
    LD R3 sub_sumover                   ;
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

todec_dec_break1                        ;
    LEA R5 todec_expr_vec               ;   [R5] expresiones
    AND R4 R4 #0                        ;   [R4] contador = 0

todec_dec_loop2                         ;   while True:
    LD R0 todec_fraccion_l              ;
    LDR R1 R5 #1                        ;
    AND R2 R2 #0                        ;
    LD R3 sub_sumover                   ;
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
    ADD R1 R1 #1                        ;
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
    ADD R5 R5 #2                        ;       expresiones.incr(2)
    LDR R0 R5 #1                        ;
    BRnp todec_dec_loop2                ;
    LDR R0 R5 #0                        ;
    BRnp todec_dec_loop2                ;       if [expresiones.peek(0), expresiones.peek(1)] == 0:
                                        ;           break

todec_dec_break2                        ;
    LD R1 todec_cursor_wr               ;
    AND R0 R0 #0                        ;   
    STR R0 R1 #0                        ;
    ADD R1 R1 #1                        ;
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