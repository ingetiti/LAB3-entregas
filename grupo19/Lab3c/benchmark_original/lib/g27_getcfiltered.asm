

;   ============================================================================
;   Subrutina: GETCFILTERED
;       Obtiene un caracter, solo si cumple con el filtro.
;       El filtro es una cadena (null terminada) con pares de caracteres, los
;       cuales representaran un rango valido de caracteres. Del par, el primero
;       sera el minimo inclusive, y el segundo sera el maximo inclusive.
;       - Ejemplo: "09az" tomaria caracteres 0-9 y a-z unicamnete.
;
;   -> INPUT  [R0] Puntero al filtro
;   <- OUTPUT [R0] Caracter capturado
;   ============================================================================

GETCFILTERED                            ;
    ST R0 getcfiltered_filter_beg       ;   [filtro_beg] = filtro
    ST R1 getcfiltered_r1               ;
    ST R2 getcfiltered_r2               ;
    ST R3 getcfiltered_r3               ;
    ST R7 getcfiltered_r7               ;   (necesario por que usamos GETC)

getcfiltered_beg                        ;   while True:
    LD R1 getcfiltered_filter_beg       ;       [R1] filtro
    GETC                                ;       [R0] char

getcfiltered_loop                       ;       while True:
    LDR R2 R1 #0                        ;           [R2] char_a = filtro.peek(0)
    BRz getcfiltered_beg                ;           if char_a == 0: break

    LDR R3 R1 #1                        ;           [R3] char_b = filtro.peek(1)
    BRz getcfiltered_beg                ;           if char_b == 0: break

    NOT R2 R2                           ;
    ADD R2 R2 #1                        ;
    ADD R2 R2 R0                        ;
    BRn getcfiltered_incr               ;
    NOT R3 R3                           ;
    ADD R3 R3 #1                        ;
    ADD R3 R3 R0                        ;
    BRp getcfiltered_incr               ;           if char >= char_a and char <= char_b:
    BRnzp getcfiltered_ret              ;               return char

getcfiltered_incr                       ;
    ADD R1 R1 #2                        ;           filtro.incr(2)
    BRnzp getcfiltered_loop             ;       

getcfiltered_ret                        ;
    LD R1 getcfiltered_r1               ;
    LD R2 getcfiltered_r2               ;
    LD R3 getcfiltered_r3               ;
    LD R7 getcfiltered_r7               ;
    RET

getcfiltered_filter_beg     .FILL #0
getcfiltered_r1             .FILL #0
getcfiltered_r2             .FILL #0
getcfiltered_r3             .FILL #0
getcfiltered_r7             .FILL #0



.END