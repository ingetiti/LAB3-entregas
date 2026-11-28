

;   ============================================================================
;   Subrutina: GETLINE
;       Obtiene una cadena de texto desde el teclado, mostrandola y guardandola
;       en el buffer dado hasta pulsar ENTER ('\n').
;       Los caracteres obtenidos que superan el tamaño maximo del buffer, son
;       simplemente ignorados y no se guardan en el buffer.
;
;   -> INPUT  [R0] Puntero al buffer de la cadena.
;   -> INPUT  [R1] Puntero a 1 pasando del final del buffer de la cadena.
;   <- OUTPUT [R0] Puntero al buffer de la cadena (modificada).
;   ============================================================================
GETLINE                                 ;
    ST R0 getline_buffer_beg            ;
    ST R1 getline_r1                    ;
    ST R2 getline_r2                    ;
    ST R3 getline_r3                    ;
    ST R7 getline_r7                    ;

    LD R2 getline_buffer_beg            ;   [R2] cursor = [buffer_beg]
    NOT R1 R1                           ;
    ADD R1 R1 #2                        ;   [R1] - (buffer_end - 1)

getline_loop                            ;   while True:
    GETC                                ;       [R0] char = getc()
    ADD R3 R0 #-10                      ;       if char == '\n':
    BRz getline_ret                     ;           break

    OUT                                 ;       putc(char)

    ADD R3 R2 R1                        ;       if cursor >= (buffer_end - 1):
    BRzp getline_loop                   ;           continue

    STR R0 R2 #0                        ;       cursor.write(char)
    ADD R2 R2 #1                        ;       cursor = cursor + 1
    BRnzp getline_loop                  ;       continue

getline_ret                             ;
    AND R0 R0 #0                        ;   
    ADD R0 R0 #10                       ;   
    OUT                                 ;   putc('\n')
    AND R0 R0 #0                        ;
    STR R0 R2 #0                        ;   cursor.write('\0')

    LD R0 getline_buffer_beg            ;
    LD R1 getline_r1                    ;
    LD R2 getline_r2                    ;
    LD R3 getline_r3                    ;
    LD R7 getline_r7                    ;
    RET                                 ;

getline_buffer_beg      .FILL #0
getline_r1              .FILL #0
getline_r2              .FILL #0
getline_r3              .FILL #0
getline_r7              .FILL #0


.END