;   ============================================================================
;   Subrutina: FROMHEX (OPTIMIZADA)
;   -> INPUT  [R0] Puntero a la cadena
;   <- OUTPUT [R0] Valor obtenido, [R5] Error flags
;   ============================================================================

FROMHEX
    PUSHM {R1, R2, R3, R4}

    ADD  R1, R0, #0             ; cursor
    ST   R0, fromhex_str_beg
    MOVI R0, #0                 ; valor = 0
    MOVI R5, #0                 ; errores = 0

    LDBU R2, R1, #0
    BRnp fromhex_loop
    OR   R5, R5, #1             ; INVALID_INPUT
    BRnzp fromhex_ret

fromhex_loop
    LDBU R3, R1, #0
    BRz  fromhex_overflow_chk

    MOVI R4, #48                ; '0'
    CMP  R3, R4
    BRn  fromhex_invalid
    MOVI R4, #57                ; '9'
    CMP  R3, R4
    BRp  fromhex_upper
    ADDI R3, #-48
    BRnzp fromhex_accum

fromhex_upper
    LD   R4, fromhex_up_a
    CMP  R3, R4
    BRn  fromhex_invalid
    LD   R4, fromhex_up_f
    CMP  R3, R4
    BRp  fromhex_lower
    ADDI R3, #-55
    BRnzp fromhex_accum

fromhex_lower
    LD   R4, fromhex_a
    CMP  R3, R4
    BRn  fromhex_invalid
    LD   R4, fromhex_f
    CMP  R3, R4
    BRp  fromhex_invalid
    LD   R4, fromhex_off_a
    ADD  R3, R3, R4

fromhex_accum
    SHL  R0, R0, #4
    ADD  R0, R0, R3
    ADD  R1, R1, #1
    BRnzp fromhex_loop

fromhex_invalid
    OR   R5, R5, #1

fromhex_overflow_chk
    LD   R4, fromhex_str_beg
    ADD  R4, R4, #4
    CMP  R1, R4
    BRnz fromhex_ret
    OR   R5, R5, #2             ; OVERFLOW

fromhex_ret
    POPM {R1, R2, R3, R4}
    RET

fromhex_str_beg .FILL #0
fromhex_up_a    .FILL #65
fromhex_up_f    .FILL #70
fromhex_a       .FILL #97
fromhex_f       .FILL #102
fromhex_off_a   .FILL #-87

.END
