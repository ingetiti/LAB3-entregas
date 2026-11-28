

.EXTERNAL SUMOVER-SUMOVER
sub_sumover     .FILL SUMOVER-SUMOVER


;   ============================================================================
;   Subrutina: FROMDEC
;       Convierte una cadena de texto decimal al valor correspondiente.
;       El resultado obtenido es separado en 2 registros:
;       - En R0 la parte entera (exponentes positivos y cero: [..., 2**1, 2**0])
;       - En R1 la parte fraccionaria (exponentes negativos: [2**-1, 2**-2, ...])
;
;   -> INPUT  [R0] Puntero de la cadena.
;   <- OUTPUT [R0] Parte entera obtenida.
;   <- OUTPUT [R1] Parte fraccionaria obtenida.
;   <- OUTPUT [R5] Error flag bits [15:2 none, 1 OVERFLOW, 0 INVALID_INPUT].
;   ============================================================================

FROMDEC                                 ;
        STI R2, G15_DIR_79
        STI R3, G15_DIR_80
        STI R4, G15_DIR_81
        STI R7, G15_DIR_82

    AND R5 R5 #0                        ;   [R5] errores
    ADD R4 R0 #0                        ;   [R4] texto

    AND R0 R0 #0
        STI R0, G15_DIR_83
        STI R0, G15_DIR_84
        STI R0, G15_DIR_85
        STI R0, G15_DIR_86

;   ==- Signo -=================================================================
    LDR R0 R4 #0                        ;   [R0] char = texto.peek()
        LDI R1, G15_DIR_87
    ADD R1 R1 R0                        ;
    BRnp fromdec_int_loop               ;   if char == '-':
    AND R1 R1 #0                        ;
    ADD R1 R1 #1                        ;
        STI R1, G15_DIR_85
    ADD R4 R4 #1                        ;       texto.incr()
    BRnzp fromdec_int_loop              ;
G15_DIR_89 .FILL fromdec_neg_plus
G15_DIR_87 .FILL fromdec_neg_minus
G15_DIR_86 .FILL fromdec_has_number
G15_DIR_85 .FILL fromdec_negativo
G15_DIR_84 .FILL fromdec_fraccion
G15_DIR_83 .FILL fromdec_entero
G15_DIR_82 .FILL fromdec_r7
G15_DIR_81 .FILL fromdec_r4
G15_DIR_80 .FILL fromdec_r3
G15_DIR_79 .FILL fromdec_r2
        LDI R1, G15_DIR_89
    ADD R1 R1 R0                        ;
    BRnp fromdec_int_loop               ;   elif char == '+':
    ADD R4 R4 #1                        ;       texto.incr()

;   ==- Parte entera -==========================================================
fromdec_int_loop                        ;   while True:
    LDR R0 R4 #0                        ;       [R0] char = texto.peek()

        BRZ G15_RELE_90
                                        ;           return

        LDI R1, G15_DIR_91
    ADD R1 R1 R0                        ;
    BRz fromdec_int_period_found        ;
        LDI R1, G15_DIR_92
    ADD R1 R1 R0                        ;
    BRz fromdec_int_period_found        ;
    BRnzp fromdec_int_range_chk         ;
G15_DIR_92 .FILL fromdec_neg_period
G15_DIR_91 .FILL fromdec_neg_dot
fromdec_int_period_found                ;       if char == '.' or char == ',':
    ADD R4 R4 #1                        ;           texto.incr()
    BRnzp fromdec_dec                   ;           break
G15_DIR_97 .FILL fromdec_neg_eight
G15_DIR_96 .FILL fromdec_neg_overchk
G15_DIR_94 .FILL fromdec_neg_nine
G15_DIR_93 .FILL fromdec_neg_zero

fromdec_int_range_chk                   ;
        LDI R1, G15_DIR_93
    ADD R1 R1 R0                        ;
    BRn fromdec_int_invalid             ;
        LDI R1, G15_DIR_94
    ADD R1 R1 R0                        ;
    BRp fromdec_int_invalid             ;       if char >= '0' and char <= '9':

        LDI R1, G15_DIR_83
        LDI R2, G15_DIR_96
    ADD R2 R2 R1                        ;
    BRp fromdec_int_overflow            ;
    BRn fromdec_int_append              ;
        LDI R2, G15_DIR_97
        LDI R3, G15_DIR_85
    NOT R3 R3                           ;
    ADD R3 R3 #1                        ;
    ADD R2 R2 R3                        ;
    ADD R2 R2 R0                        ;
    BRn fromdec_int_append              ;           if entero > 3276 or (entero == 3276 and char >= '8' + negativo):

fromdec_int_overflow                    ;
    NOT R5 R5                           ;
    AND R5 R5 #-3                       ;
    NOT R5 R5                           ;               errores = errores | OVERFLOW

fromdec_int_append                      ;
    ADD R2 R1 R1                        ;
    ADD R2 R2 R2                        ;
    ADD R2 R2 R1                        ;
    ADD R1 R2 R2                        ;           entero = entero * 10

        LDI R2, G15_DIR_93
    ADD R1 R1 R2                        ;
    ADD R1 R1 R0                        ;           entero = entero + ord(char) - ord('0')

    AND R2 R2 #0                        ;
    ADD R2 R2 #1                        ;
        STI R2, G15_DIR_86
    ADD R4 R4 #1                        ;           texto.incr()
        STI R1, G15_DIR_83
    BRnzp fromdec_int_loop              ;           continue

fromdec_int_invalid                     ;
    NOT R5 R5                           ;
    AND R5 R5 #-2                       ;
    NOT R5 R5                           ;       errores = errores | INVALID_INPUT
    BRnzp fromdec_ret                   ;       return
G15_DIR_104 .FILL fromdec_contador
G15_DIR_103 .FILL fromdec_fraccion_h
G15_DIR_102 .FILL fromdec_fraccion_l

;   ==- Parte fraccionaria -====================================================
fromdec_dec                             ;
    AND R0 R0 #0                        ;
        STI R0, G15_DIR_102
        STI R0, G15_DIR_103
    AND R0 R0 #0                        ;
    ADD R0 R0 #9                        ;   
        STI R0, G15_DIR_104

fromdec_dec_loop                        ;   
        LDI R0, G15_DIR_104
    BRnz fromdec_dec_break              ;   while contador > 0:
    AND R0 R0 #0                        ;
        STI R0, G15_DIR_106
    LDR R0 R4 #0                        ;       [R0] char = texto.peek()

        LDI R1, G15_DIR_93
    ADD R1 R1 R0                        ;
    BRn fromdec_dec_sk1                 ;
        LDI R1, G15_DIR_94
    ADD R1 R1 R0                        ;
    BRp fromdec_dec_sk1                 ;       if char >= '0' or char <= '9':
        LDI R1, G15_DIR_93
    ADD R1 R1 R0                        ;
        STI R1, G15_DIR_106
    ADD R4 R4 #1                        ;           texto.incr()
    BRnzp fromdec_dec_increment         ;
G15_DIR_106 .FILL fromdec_current

fromdec_dec_sk1                         ;
    ADD R0 R0 #0                        ;
    BRz fromdec_dec_increment           ;       elif char != '\0':
    NOT R5 R5                           ;
    AND R5 R5 #-2                       ;
    NOT R5 R5                           ;           errores = errores | INVALID_INPUT

fromdec_dec_increment                   ;
    LD R0 fromdec_fraccion_h            ;
    LD R1 fromdec_fraccion_l            ;
    ADD R0 R0 R0                        ;
    ADD R1 R1 #0                        ;
    BRzp fromdec_dec_incr_sk1           ;
    ADD R0 R0 #1                        ;
fromdec_dec_incr_sk1                    ;
    ADD R1 R1 R1                        ;       [R0, R1] = [fraccion_h, fromdec_aux_l] * 2

    ADD R0 R0 R0                        ;
    ADD R1 R1 #0                        ;
    BRzp fromdec_dec_incr_sk2           ;
    ADD R0 R0 #1                        ;
fromdec_dec_incr_sk2                    ;
    ADD R1 R1 R1                        ;       [R0, R1] = [fraccion_h, fromdec_aux_l] * 4
    ST R0 fromdec_aux_h                 ;
    ST R1 fromdec_aux_l                 ;       [aux_h, aux_l] = [R0, R1]

    LD R0 fromdec_aux_l                 ;
        BR G15_SIG_90
G15_RELE_90 BR fromdec_ret
G15_DIR_111 .FILL sub_sumover
G15_SIG_90
    LD R1 fromdec_fraccion_l            ;
    AND R2 R2 #0                        ;
        LDI R3, G15_DIR_111
    JSRR R3                             ;
    ST R0 fromdec_aux_l                 ;
    LD R0 fromdec_aux_h                 ;
    LD R1 fromdec_fraccion_h            ;
    ADD R0 R0 R1                        ;
    ADD R0 R0 R2                        ;
    ST R0 fromdec_aux_h                 ;       [aux_h, aux_l] = [fraccion_h, fraccion_l] * 5

    LD R0 fromdec_aux_h                 ;
    LD R1 fromdec_aux_l                 ;
    ADD R0 R0 R0                        ;
    ADD R1 R1 #0                        ;
    BRzp fromdec_dec_incr_sk3           ;
    ADD R0 R0 #1                        ;
fromdec_dec_incr_sk3                    ;
    ADD R1 R1 R1                        ;
    ST R0 fromdec_fraccion_h            ;
    ST R1 fromdec_fraccion_l            ;       [fraccion_h, fraccion_l] = [fraccion_h, fraccion_l] * 10

    LD R0 fromdec_fraccion_l            ;
    LD R1 fromdec_current               ;
    ADD R0 R0 R1                        ;
    ST R0 fromdec_fraccion_l            ;       [fraccion_l] = [fraccion_l] + [current]

    LD R0 fromdec_contador              ;
    ADD R0 R0 #-1                       ;       
    ST R0 fromdec_contador              ;       [contador] -= 1
    BRnzp fromdec_dec_loop              ;

fromdec_dec_break                       ;
    AND R0 R0 #0                        ;   
    ST R0 fromdec_contador              ;   [contador] = 0

fromdec_dec_loop2                       ;   while True:
    LD R0 fromdec_fraccion_h            ;
    LD R1 fromdec_fraccion_l            ;
    ADD R0 R0 R0                        ;
    ADD R1 R1 #0                        ;
    BRzp fromdec_dec_loop2_sk1          ;
    ADD R0 R0 #1                        ;
fromdec_dec_loop2_sk1                   ;
    ADD R1 R1 R1                        ;
    ST R0 fromdec_fraccion_h            ;
    ST R1 fromdec_fraccion_l            ;       [fraccion_h, fraccion_l] = [fraccion_h, fraccion_l] * 2

    LD R0 fromdec_fraccion_l            ;
    LD R1 fromdec_neg_frac_l            ;
    AND R2 R2 #0                        ;
        LDI R3, G15_DIR_111
    JSRR R3                             ;
    ST R0 fromdec_aux_l                 ;
    LD R0 fromdec_fraccion_h            ;
    LD R1 fromdec_neg_frac_h            ;
    ADD R0 R0 R1                        ;
    ADD R0 R0 R2                        ;
    ST R0 fromdec_aux_h                 ;       [aux_h, aux_l] = [fraccion_h, fraccion_l] - 1_000_000_000
    
    LD R0 fromdec_contador              ;
    ADD R0 R0 #-16                      ;
    BRn fromdec_dec_increment2          ;       if [contador] >= 16:

    LD R0 fromdec_aux_h                 ;
    BRn fromdec_ret                     ;           if [aux_h, aux_l] >= 0:
    LD R0 fromdec_fraccion              ;
    ADD R0 R0 #1                        ;
    ST R0 fromdec_fraccion              ;               [fraccion] = [fraccion] + 1

    BRnp fromdec_ret                    ;           if [fraccion] == 0:
    LD R0 fromdec_entero                ;
    ADD R0 R0 #1                        ;   
    ST R0 fromdec_entero                ;               [entero] = [entero] + 1

    BR fromdec_ret                      ;           return


fromdec_dec_increment2                  ;       
    LD R0 fromdec_fraccion              ;       
    ADD R0 R0 R0                        ;       
    ST R0 fromdec_fraccion              ;       [fraccion] = [fraccion] << 1
    
    LD R0 fromdec_aux_h                 ;       
    BRn fromdec_dec_continue2           ;       if [aux_h, aux_l] >= 0:
    LD R0 fromdec_fraccion              ;       
    ADD R0 R0 #1                        ;       
    ST R0 fromdec_fraccion              ;           [fraccion] = [fraccion] + 1
    LD R0 fromdec_aux_l                 ;       
    ST R0 fromdec_fraccion_l            ;
    LD R0 fromdec_aux_h                 ;       
    ST R0 fromdec_fraccion_h            ;           [fraccion_h, fraccion_l] = [aux_h, aux_l]
    
fromdec_dec_continue2                   ;
    LD R0 fromdec_contador              ;
    ADD R0 R0 #1                        ;
    ST R0 fromdec_contador              ;       [contador] += 1
    BRnzp fromdec_dec_loop2             ;

;   ==- Return -================================================================
fromdec_ret                             ;
    LD R0 fromdec_has_number            ;
    BRnp fromdec_ret_sk1                ;   if not [tiene_numero]:
    NOT R5 R5                           ;   
    AND R5 R5 #-2                       ;
    NOT R5 R5                           ;       errores = errores | INVALID_INPUT

fromdec_ret_sk1
    LD R0 fromdec_negativo              ;
    BRz fromdec_ret_skp_neg             ;   if [negativo]:
    LD R0 fromdec_entero                ;       [R0] entero
    NOT R0 R0                           ;
    LD R1 fromdec_fraccion              ;       [R1] fraccion
    BRnp fromdec_ret_sk2                ;
    ADD R0 R0 #1                        ;
fromdec_ret_sk2                         ;
    NOT R1 R1                           ;
    ADD R1 R1 #1                        ;       [entero, fraccion] = -[entero, fraccion]
    ST R0 fromdec_entero                ;       [entero]  = entero
    ST R1 fromdec_fraccion              ;       [fraccion] = fraccion

fromdec_ret_skp_neg                     ;
    LD R0 fromdec_entero                ;
    LD R1 fromdec_fraccion              ;
    LD R2 fromdec_r2                    ;
    LD R3 fromdec_r3                    ;
    LD R4 fromdec_r4                    ;
    LD R7 fromdec_r7                    ;
    RET                                 ;


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
fromdec_r2              .FILL #0
fromdec_r3              .FILL #0
fromdec_r4              .FILL #0
fromdec_r7              .FILL #0
fromdec_neg_plus        .FILL #-43      ;   - ord('+')
fromdec_neg_period      .FILL #-44      ;   - ord(',')
fromdec_neg_minus       .FILL #-45      ;   - ord('-')
fromdec_neg_dot         .FILL #-46      ;   - ord('.')
fromdec_neg_zero        .FILL #-48      ;   - ord('0')
fromdec_neg_eight       .FILL #-56      ;   - ord('8')
fromdec_neg_nine        .FILL #-57      ;   - ord('9')
fromdec_neg_overchk     .FILL #-3276

fromdec_neg_frac_h      .FILL xC465     ;
fromdec_neg_frac_l      .FILL x3600     ;   -1_000_000_000

.END
