;   ============================================================================
;   Subrutina: GETLINE (LC-X)
;       Obtiene una cadena de texto desde el teclado, mostrandola y guardandola
;       en el buffer dado (un caracter por byte) hasta pulsar ENTER ('\n').
;       Los caracteres obtenidos que superan el tamaño maximo del buffer, son
;       simplemente ignorados y no se guardan en el buffer.
;
;   -> INPUT  [R0] Puntero al buffer de la cadena.
;   -> INPUT  [R1] Puntero a 1 pasando del final del buffer de la cadena.
;   <- OUTPUT [R0] Puntero al buffer de la cadena (modificada).
;   Conserva R1-R7.
;   ============================================================================
GETLINE
        PUSH  R0, R1, R2
        ADD   R2, R0, #0        ; [R2] cursor
        SUB   R1, R1, #1        ; [R1] ultimo lugar (para el '\0')
GETLINE_LOOP
        GETC                    ; [R0] char = getc()
        CMP   R0, #10
        BRz   GETLINE_RET       ; if char == '\n': break
        OUT                     ; putc(char)
        CMP   R2, R1
        BRC   GETLINE_LOOP      ; if cursor >= (buffer_end - 1): continue
        STBI  R0, R2            ; cursor.write(char), cursor + 1
        BR    GETLINE_LOOP
GETLINE_RET
        OUT                     ; putc('\n')
        AND   R0, R0, #0
        STB   R0, R2, #0        ; cursor.write('\0')
        POPR  R0, R1, R2

.END
