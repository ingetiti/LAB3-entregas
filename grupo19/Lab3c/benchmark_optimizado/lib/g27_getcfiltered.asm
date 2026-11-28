;   ============================================================================
;   Subrutina: GETCFILTERED
;       Obtiene un caracter, solo si cumple con el filtro.
;       El filtro es una cadena (null terminada) con pares de caracteres, los
;       cuales representaran un rango valido de caracteres. Del par, el primero
;       sera el minimo inclusive, y el segundo sera el maximo inclusive.
;       - Ejemplo: "09az" tomaria caracteres 0-9 y a-z unicamente.
;
;   -> INPUT  [R0] Puntero al filtro
;   <- OUTPUT [R0] Caracter capturado
;
;   Optimizaciones nueva ISA:
;       - PUSHM/POPM en lugar de variables estaticas; TRAP GETC preserva R7.
;       - LDBL para leer bytes de .STRINGZ (1 byte por caracter).
;       - CMP + BRlt/BRgt en lugar de complemento a 2 manual.
;   ============================================================================

GETCFILTERED
    PUSHM {R1, R2, R3, R4}              ; Guarda registros preservados
    MOV R4, R0                          ; R4 = puntero al inicio del filtro

getcfiltered_beg                        ; while True:
    MOV R1, R4                          ;     R1 = filtro
    GETC                                ;     R0 = char

getcfiltered_loop                       ;     while True:
    LDBL R2, R1, #0                     ;         R2 = char_a = filtro[0] (byte)
    BRz getcfiltered_beg                ;         if char_a == 0: break

    LDBL R3, R1, #1                     ;         R3 = char_b = filtro[1] (byte)
    BRz getcfiltered_beg                ;         if char_b == 0: break

    CMP R0, R2                          ;         if char < char_a:
    BRlt getcfiltered_incr              ;             siguiente par
    CMP R0, R3                          ;         if char > char_b:
    BRgt getcfiltered_incr              ;             siguiente par

    POPM {R1, R2, R3, R4}               ;         return char (en R0)
    RET

getcfiltered_incr
    ADDI R1, R1, #2                     ;         avanzar al siguiente par (2 bytes)
    BR getcfiltered_loop

.END
