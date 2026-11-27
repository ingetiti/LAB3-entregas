
; ============================================================================
; Subrutina: CIRCLSH  [LC-3X — optimizada]
;     Rotacion circular de 32 bits (R0||R1) hacia la izquierda n veces en O(1).
;
; -> INPUT  [R0] Registro A (palabra alta).
; -> INPUT  [R1] Registro B (palabra baja).
; -> INPUT  [R2] n: numero de rotaciones.
; <- OUTPUT [R0] A rotado.
; <- OUTPUT [R1] B rotado.
; ============================================================================

CIRCLSH
    PUSHM #x3C                  ; Guarda R2, R3, R4, R5
    ADD R2 R2 #0
    BRnz circlsh_done
    MOVI R3 #16
    AND R4 R2 R3                ; bit 4 de n (swap de palabras si n mod 32 >= 16)
    BRz circlsh_no_swap
    ADD R4 R0 #0
    ADD R0 R1 #0
    ADD R1 R4 #0

circlsh_no_swap
    ADD R3 R3 #-1               ; R3 = 15
    AND R2 R2 R3                ; R2 = k = n mod 16 (0..15)
    BRz circlsh_done
    ADD R3 R3 #1                ; R3 = 16
    SUB R3 R3 R2                ; R3 = 16 - k (1..15)
    SHR R4 R1 R3                ; B >>> (16 - k)
    SHR R5 R0 R3                ; A >>> (16 - k)
    SHL R0 R0 R2                ; A << k
    SHL R1 R1 R2                ; B << k
    ADD R0 R0 R4                ; (A << k) | (B >>> (16 - k))
    ADD R1 R1 R5                ; (B << k) | (A >>> (16 - k))

circlsh_done
    POPM #x3C                   ; Restaura R2, R3, R4, R5
    RET

.END
