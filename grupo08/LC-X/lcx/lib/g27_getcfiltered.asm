;   ============================================================================
;   Subrutina: GETCFILTERED (LC-X)
;       Obtiene un caracter, solo si cumple con el filtro.
;       El filtro es una cadena de bytes (null terminada) con pares de
;       caracteres, los cuales representaran un rango valido de caracteres.
;       Del par, el primero sera el minimo inclusive, y el segundo sera el
;       maximo inclusive.
;       - Ejemplo: "09az" tomaria caracteres 0-9 y a-z unicamnete.
;
;   -> INPUT  [R0] Puntero al filtro
;   <- OUTPUT [R0] Caracter capturado
;   Conserva R1-R7.
;   ============================================================================

GETCFILTERED
        PUSH  R1, R2, R3
        ADD   R3, R0, #0        ; [R3] filtro
GCF_TECLA
        ADD   R1, R3, #0        ; [R1] cursor del filtro
        GETC                    ; [R0] char
GCF_PAR LDBI  R2, R1            ; [R2] char_a
        BRz   GCF_TECLA         ; fin del filtro: otra tecla
        CMP   R0, R2            ; C = 0 si char < char_a
        LDBI  R2, R1            ; [R2] char_b (no cambia C)
        BRz   GCF_TECLA
        BRNC  GCF_PAR
        CMP   R2, R0            ; C = 0 si char > char_b
        BRNC  GCF_PAR
        POPR  R1, R2, R3        ; return char

.END
