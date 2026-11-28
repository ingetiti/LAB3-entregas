;   ============================================================================
;   Subrutina: GETLINE
;       Obtiene una cadena de texto desde el teclado, mostrandola y guardandola
;       en el buffer dado hasta pulsar ENTER ('\n').
;       Los caracteres obtenidos que superan el tamano maximo del buffer, son
;       simplemente ignorados y no se guardan en el buffer.
;
;   -> INPUT  [R0] Puntero al buffer de la cadena.
;   -> INPUT  [R1] Puntero a 1 byte pasando del final del buffer de la cadena.
;   <- OUTPUT [R0] Puntero al buffer de la cadena (modificada).
;
;   Optimizaciones nueva ISA:
;       - PUSHM/POPM en lugar de variables estaticas; TRAP preserva R7.
;       - STBL para escribir 1 byte por caracter en buffer .STRINGZ/.BLKB.
;       - CMP + BRnc para comparar cursor >= (buffer_end - 1) sin signo.
;   ============================================================================

GETLINE
    PUSHM {R0, R1, R2, R3}              ; Guarda registros (R0 se restaura al retornar)
    MOV R2, R0                          ; R2 = cursor = buffer_beg
    ADDI R1, R1, #-1                    ; R1 = buffer_end - 1 (posicion para '\0')
    MOVI R3, #10                        ; R3 = '\n' para comparacion rapida

getline_loop                            ; while True:
    GETC                                ;     R0 = char = getc()
    CMP R0, R3                          ;     if char == '\n':
    BRz getline_ret                     ;         break

    OUT                                 ;     putc(char)

    CMP R2, R1                          ;     if cursor >= (buffer_end - 1):
    BRnc getline_loop                   ;         continue (C=0 indica sin prestamo)

    STBL R0, R2, #0                     ;     *cursor = char (1 byte)
    ADDI R2, R2, #1                     ;     cursor++
    BR getline_loop

getline_ret
    MOV R0, R3                          ; R0 = '\n'
    OUT                                 ; putc('\n')
    CLR R0
    STBL R0, R2, #0                     ; *cursor = '\0'

    POPM {R0, R1, R2, R3}               ; Restaura R0 (buffer_beg) y registros
    RET

.END
