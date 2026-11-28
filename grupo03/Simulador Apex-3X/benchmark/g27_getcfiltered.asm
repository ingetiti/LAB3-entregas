
; ============================================================================
; Subrutina: GETCFILTERED  [LC-3X — adaptada]
;     Obtiene un caracter que cumple con el filtro dado (pares min/max).
;     El filtro es una cadena null-terminada con pares de bytes.
;     Ejemplo: "09az" acepta 0-9 y a-z.
;
;     Cambios respecto al original LC-3:
;       1. LDR R2, R1, #0  -> desplazamiento 0 bytes (par) -> OK.
;          LDR R3, R1, #1  -> desplazamiento 1 byte  -> IMPAR -> ERROR.
;          En LC-3X los accesos de 16 bits con LDR deben ser par.
;          El filtro se lee byte a byte con LDBL (Load Byte Low).
;          LDBL R2, R1, #0  y  LDBL R3, R1, #1  son validos (despl. en bytes).
;       2. ADD R1, R1, #2 (avanzar de a 2 bytes en el filtro) -> OK (imm4).
;
; -> INPUT  [R0] Puntero al filtro (string byte a byte).
; <- OUTPUT [R0] Caracter capturado.
; ============================================================================

GETCFILTERED
    ST R0 getcfiltered_filter_beg
    ST R1 getcfiltered_r1
    ST R2 getcfiltered_r2
    ST R3 getcfiltered_r3
    ST R7 getcfiltered_r7

getcfiltered_beg                ; while True:
    LD R1 getcfiltered_filter_beg
    GETC                        ;   [R0] char

getcfiltered_loop               ;   for cada par del filtro:
    LDBL R2 R1 #0               ;     [R2] char_a = filtro[0]  (byte)
    BRz getcfiltered_beg        ;     if char_a == 0: reintentar

    LDBL R3 R1 #1               ;     [R3] char_b = filtro[1]  (byte)
    BRz getcfiltered_beg        ;     if char_b == 0: reintentar

    NEG R2 R2                   ;     R2 = -char_a
    ADD R2 R2 R0
    BRn getcfiltered_incr       ;     if char < char_a: siguiente par

    NEG R3 R3                   ;     R3 = -char_b
    ADD R3 R3 R0
    BRp getcfiltered_incr       ;     if char > char_b: siguiente par

    BRnzp getcfiltered_ret      ;     char esta en [char_a, char_b] -> OK

getcfiltered_incr
    ADD R1 R1 #2                ;   avanzar 2 bytes al siguiente par
    BRnzp getcfiltered_loop

getcfiltered_ret
    LD R1 getcfiltered_r1
    LD R2 getcfiltered_r2
    LD R3 getcfiltered_r3
    LD R7 getcfiltered_r7
    RET

getcfiltered_filter_beg .FILL #0
getcfiltered_r1         .FILL #0
getcfiltered_r2         .FILL #0
getcfiltered_r3         .FILL #0
getcfiltered_r7         .FILL #0

.END
