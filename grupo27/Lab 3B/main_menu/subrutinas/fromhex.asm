

;   ============================================================================
;   Subrutina: FROMHEX
;       Convierte una cadena de texto hexadecimal al valor correspondiente.
;
;   -> INPUT  [R0] Puntero a la cadena.
;   <- OUTPUT [R0] Valor obtenido.
;   <- OUTPUT [R5] Banderas de error [15:2 none, 1 OVERFLOW, 0 INVALID_INPUT].
;   ============================================================================

FROMHEX                                 ;
    ST R1 fromhex_r1                    ;
    ST R2 fromhex_r2                    ;
    ST R3 fromhex_r3                    ;
    ST R4 fromhex_r4                    ;

    ST R0 fromhex_str_beg               ;   [str_beg] = texto
    AND R0 R0 #0                        ;   [R0] valor = 0
    LD R1 fromhex_str_beg               ;   [R1] texto = [str_beg]
    AND R5 R5 #0                        ;   [R5] errores = 0

    LDR R2 R1 #0                        ;   [R2] char = texto.peek()
    BRnp fromhex_loop                   ;   if char == '\0':
    NOT R5 R5                           ;
    AND R5 R5 #-2                       ;
    NOT R5 R5                           ;       errores = errores | INVALID_INPUT
    BRnzp fromhex_ret                   ;       return

fromhex_loop                            ;   while True:
    AND R2 R2 #0                        ;       [R2] offset
    LDR R3 R1 #0                        ;       [R3] char = texto.peek()

    BRz fromhex_overflow_chk            ;       if char == '0':
                                        ;           break
    
    LD R4 fromhex_neg_zero              ;
    ADD R4 R4 R3                        ;
    BRn fromhex_lower                   ;
    LD R4 fromhex_neg_nine              ;
    ADD R4 R4 R3                        ;
    BRp fromhex_lower                   ;       if char >= '0' and char <= '9':
    LD R2 fromhex_neg_zero              ;           offset = -ord('0')

fromhex_lower                           ;
    LD R4 fromhex_neg_a                 ;
    ADD R4 R4 R3                        ;
    BRn fromhex_upper                   ;
    LD R4 fromhex_neg_f                 ;
    ADD R4 R4 R3                        ;
    BRp fromhex_upper                   ;       if char >= 'a' and char <= 'f':
    LD R2 fromhex_neg_a                 ;
    ADD R2 R2 #10                       ;           offset = -ord('a') + 10

fromhex_upper                           ;
    LD R4 fromhex_neg_upa               ;
    ADD R4 R4 R3                        ;
    BRn fromhex_invalid_chk             ;
    LD R4 fromhex_neg_upf               ;
    ADD R4 R4 R3                        ;
    BRp fromhex_invalid_chk             ;       if char >= 'A' and char <= 'F':
    LD R2 fromhex_neg_upa               ;
    ADD R2 R2 #10                       ;           offset = -ord('A') + 10

fromhex_invalid_chk                     ;
    ADD R2 R2 #0                        ;
    BRnp fromhex_increment              ;       if offset == 0:
    NOT R5 R5                           ;
    AND R5 R5 #-2                       ;
    NOT R5 R5                           ;           errores = errores | INVALID_INPUT
    BRnzp fromhex_overflow_chk          ;           break

fromhex_increment                       ;
    ADD R0 R0 R0                        ;
    ADD R0 R0 R0                        ;
    ADD R0 R0 R0                        ;
    ADD R0 R0 R0                        ;       valor = valor << 4
    ADD R0 R0 R3                        ;
    ADD R0 R0 R2                        ;       valor = valor + char + offset
    ADD R1 R1 #1                        ;       texto.incr()
    BRnzp fromhex_loop                  ;

fromhex_overflow_chk                    ;
    LD R4 fromhex_str_beg               ;
    ADD R4 R4 #4                        ;
    NOT R4 R4                           ;
    ADD R4 R4 #1                        ;
    ADD R4 R4 R1                        ;
    BRnz fromhex_ret                    ;   if texto >= [text_iter_ini] + 4:
    NOT R5 R5                           ;
    AND R5 R5 #-3                       ;
    NOT R5 R5                           ;       errores = errores | OVERFLOW

fromhex_ret                             ;
    LD R1 fromhex_r1                    ;
    LD R2 fromhex_r2                    ;
    LD R3 fromhex_r3                    ;
    LD R4 fromhex_r4                    ;
    RET                                 ;

fromhex_str_beg         .FILL #0
fromhex_r1              .FILL #0
fromhex_r2              .FILL #0
fromhex_r3              .FILL #0
fromhex_r4              .FILL #0
fromhex_neg_zero        .FILL #-48      ;   - ord('0')
fromhex_neg_nine        .FILL #-57      ;   - ord('9')
fromhex_neg_a           .FILL #-97      ;   - ord('a')
fromhex_neg_f           .FILL #-102     ;   - ord('f')
fromhex_neg_upa         .FILL #-65      ;   - ord('A')
fromhex_neg_upf         .FILL #-70      ;   - ord('F')

.END


