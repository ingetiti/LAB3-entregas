

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
    ST R2 fromdec_r2                    ;
    ST R3 fromdec_r3                    ;
    ST R4 fromdec_r4                    ;
    ST R7 fromdec_r7                    ;

    AND R5 R5 #0                        ;   [R5] errores
    ADD R4 R0 #0                        ;   [R4] texto

    AND R0 R0 #0
    ST R0 fromdec_entero                ;   [entero]   = 0          # parte entera obtenida
    ST R0 fromdec_fraccion              ;   [fraccion] = 0          # parte fraccion obtenida
    ST R0 fromdec_negativo              ;   [negativo] = 0          # signo obtenido
    ST R0 fromdec_has_number            ;   [tiene_numero] = 0      # verifica que haya almenos 1 numero

;   ==- Signo -=================================================================
    LDR R0 R4 #0                        ;   [R0] char = texto.peek()
    LD  R1 fromdec_neg_minus            ;
    ADD R1 R1 R0                        ;
    BRnp fromdec_int_loop               ;   if char == '-':
    AND R1 R1 #0                        ;
    ADD R1 R1 #1                        ;
    ST R1 fromdec_negativo              ;       [negativo] = 1
    ADD R4 R4 #1                        ;       texto.incr()
    BRnzp fromdec_int_loop              ;
    LD R1 fromdec_neg_plus              ;
    ADD R1 R1 R0                        ;
    BRnp fromdec_int_loop               ;   elif char == '+':
    ADD R4 R4 #1                        ;       texto.incr()

;   ==- Parte entera -==========================================================
fromdec_int_loop                        ;   while True:
    LDR R0 R4 #0                        ;       [R0] char = texto.peek()

    BRz fromdec_ret                     ;       if char == '\0':
                                        ;           return

    LD R1 fromdec_neg_dot               ;
    ADD R1 R1 R0                        ;
    BRz fromdec_int_period_found        ;
    LD R1 fromdec_neg_period            ;
    ADD R1 R1 R0                        ;
    BRz fromdec_int_period_found        ;
    BRnzp fromdec_int_range_chk         ;
fromdec_int_period_found                ;       if char == '.' or char == ',':
    ADD R4 R4 #1                        ;           texto.incr()
    BRnzp fromdec_dec                   ;           break

fromdec_int_range_chk                   ;
    LD R1 fromdec_neg_zero              ;
    ADD R1 R1 R0                        ;
    BRn fromdec_int_invalid             ;
    LD R1 fromdec_neg_nine              ;
    ADD R1 R1 R0                        ;
    BRp fromdec_int_invalid             ;       if char >= '0' and char <= '9':

    LD R1 fromdec_entero                ;           [R1] entero = [entero]
    LD R2 fromdec_neg_overchk           ;
    ADD R2 R2 R1                        ;
    BRp fromdec_int_overflow            ;
    BRn fromdec_int_append              ;
    LD R2 fromdec_neg_eight             ;
    LD R3 fromdec_negativo              ;
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

    LD  R2 fromdec_neg_zero             ;
    ADD R1 R1 R2                        ;
    ADD R1 R1 R0                        ;           entero = entero + ord(char) - ord('0')

    AND R2 R2 #0                        ;
    ADD R2 R2 #1                        ;
    ST R2 fromdec_has_number            ;           [tiene_numero] = 1
    ADD R4 R4 #1                        ;           texto.incr()
    ST R1 fromdec_entero                ;           [entero] = entero
    BRnzp fromdec_int_loop              ;           continue

fromdec_int_invalid                     ;
    NOT R5 R5                           ;
    AND R5 R5 #-2                       ;
    NOT R5 R5                           ;       errores = errores | INVALID_INPUT
    BRnzp fromdec_ret                   ;       return

;   ==- Parte fraccionaria -====================================================
fromdec_dec                             ;
    AND R0 R0 #0                        ;
    ST R0 fromdec_fraccion_l            ;   [fraccion_l] = 0
    ST R0 fromdec_fraccion_h            ;   [fraccion_h] = 0
    AND R0 R0 #0                        ;
    ADD R0 R0 #9                        ;   
    ST R0 fromdec_contador              ;   [contador] = 9

fromdec_dec_loop                        ;   
    LD R0 fromdec_contador              ;   
    BRnz fromdec_dec_break              ;   while contador > 0:
    AND R0 R0 #0                        ;
    ST R0 fromdec_current               ;       [current] = 0
    LDR R0 R4 #0                        ;       [R0] char = texto.peek()

    LD R1 fromdec_neg_zero              ;
    ADD R1 R1 R0                        ;
    BRn fromdec_dec_sk1                 ;
    LD R1 fromdec_neg_nine              ;
    ADD R1 R1 R0                        ;
    BRp fromdec_dec_sk1                 ;       if char >= '0' or char <= '9':
    LD R1 fromdec_neg_zero              ;
    ADD R1 R1 R0                        ;
    ST R1 fromdec_current               ;           [current] = char - ord('0')
    ADD R4 R4 #1                        ;           texto.incr()
    BRnzp fromdec_dec_increment         ;

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
    LD R1 fromdec_fraccion_l            ;
    AND R2 R2 #0                        ;
    LD R3 sub_sumover                   ;
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
    LD R3 sub_sumover                   ;
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