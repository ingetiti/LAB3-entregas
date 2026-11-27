
; ============================================================================
; Subrutina: FROMHEX  [LC-3X — adaptada]
;     Convierte una cadena hex ASCII al valor numerico correspondiente.
;     Lee bytes del buffer con LDBL (1 byte por caracter).
;
;     Cambios respecto al original LC-3:
;       1. LDR R2, R1, #0  y  LDR R3, R1, #0  ->  el buffer almacena chars
;          de 1 byte c/u en LC-3X.  Se usa LDBL (Load Byte Low, despl byte).
;       2. ADD R2, R2, #10  (en 2 lugares) ->  imm4 no admite 10.
;          Reemplazado por  MOVI R2, #10  /  ADD R2, R2, R_neg_offset.
;       3. ADD R1, R1, #1  (avanzar cursor) -> imm4 permite +1 -> OK.
;       4. ADD R4, R4, #4  (limite overflow) -> OK.
;
; -> INPUT  [R0] Puntero al buffer (string byte a byte, terminado en '\0').
; <- OUTPUT [R0] Valor obtenido.
; <- OUTPUT [R5] Flags error [1=OVERFLOW, 0=INVALID_INPUT].
; ============================================================================

FROMHEX
    ST R1 fromhex_r1
    ST R2 fromhex_r2
    ST R3 fromhex_r3
    ST R4 fromhex_r4

    ST R0 fromhex_str_beg
    AND R0 R0 #0                ; valor = 0
    LD R1 fromhex_str_beg
    AND R5 R5 #0                ; errores = 0

    LDBL R2 R1 #0               ; char = buf[0]
    BRnp fromhex_loop
    NOT R5 R5
    AND R5 R5 #-2
    NOT R5 R5                   ; INVALID_INPUT
    BRnzp fromhex_ret

fromhex_loop
    AND R2 R2 #0                ; offset = 0
    LDBL R3 R1 #0               ; char = buf[cursor]

    BRz fromhex_overflow_chk    ; if char == '\0': break

    LD R4 fromhex_neg_zero
    ADD R4 R4 R3
    BRn fromhex_lower
    LD R4 fromhex_neg_nine
    ADD R4 R4 R3
    BRp fromhex_lower           ; if '0'<=char<='9':
    LD R2 fromhex_neg_zero      ;   offset = -ord('0')

fromhex_lower
    LD R4 fromhex_neg_a
    ADD R4 R4 R3
    BRn fromhex_upper
    LD R4 fromhex_neg_f
    ADD R4 R4 R3
    BRp fromhex_upper           ; if 'a'<=char<='f':
    LD R2 fromhex_neg_a
    MOVI R3 #10
    ADD R2 R2 R3                ;   offset = -ord('a') + 10

fromhex_upper
    LD R4 fromhex_neg_upa
    ADD R4 R4 R3
    BRn fromhex_invalid_chk
    LD R4 fromhex_neg_upf
    ADD R4 R4 R3
    BRp fromhex_invalid_chk     ; if 'A'<=char<='F':
    LD R2 fromhex_neg_upa
    MOVI R3 #10
    ADD R2 R2 R3                ;   offset = -ord('A') + 10

fromhex_invalid_chk
    ADD R2 R2 #0
    BRnp fromhex_increment      ; if offset == 0:
    NOT R5 R5
    AND R5 R5 #-2
    NOT R5 R5                   ;   INVALID_INPUT
    BRnzp fromhex_overflow_chk

fromhex_increment
    ; Reload char (R3 may have been clobbered by MOVI above)
    LDBL R3 R1 #0
    ADD R0 R0 R0
    ADD R0 R0 R0
    ADD R0 R0 R0
    ADD R0 R0 R0                ; valor <<= 4
    ADD R0 R0 R3
    ADD R0 R0 R2                ; valor += char + offset
    ADD R1 R1 #1                ; cursor++
    BRnzp fromhex_loop

fromhex_overflow_chk
    LD R4 fromhex_str_beg
    ADD R4 R4 #4
    NEG R4 R4
    ADD R4 R4 R1
    BRnz fromhex_ret
    NOT R5 R5
    AND R5 R5 #-3
    NOT R5 R5                   ; OVERFLOW

fromhex_ret
    LD R1 fromhex_r1
    LD R2 fromhex_r2
    LD R3 fromhex_r3
    LD R4 fromhex_r4
    RET

fromhex_str_beg     .FILL #0
fromhex_r1          .FILL #0
fromhex_r2          .FILL #0
fromhex_r3          .FILL #0
fromhex_r4          .FILL #0
fromhex_neg_zero    .FILL #-48      ; -ord('0')
fromhex_neg_nine    .FILL #-57      ; -ord('9')
fromhex_neg_a       .FILL #-97      ; -ord('a')
fromhex_neg_f       .FILL #-102     ; -ord('f')
fromhex_neg_upa     .FILL #-65      ; -ord('A')
fromhex_neg_upf     .FILL #-70      ; -ord('F')

.END
