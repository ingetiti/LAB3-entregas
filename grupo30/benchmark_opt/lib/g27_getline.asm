;   ============================================================================
;   Subrutina: GETLINE (OPTIMIZADA)
;   -> INPUT  [R0] buffer, [R1] buffer_end
;   <- OUTPUT [R0] buffer
;   ============================================================================

GETLINE
    PUSHM {R0, R1, R2, R3, R7}
    ADD  R2, R0, #0
    ADD  R1, R1, #-1            ; buffer_end - 1

getline_loop
    GETC
    MOVI R3, #10
    CMP  R0, R3
    BRz  getline_ret
    OUT
    CMP  R2, R1
    BRzp getline_loop
    STB  R0, R2, #0
    ADD  R2, R2, #1
    BRnzp getline_loop

getline_ret
    MOVI R0, #10
    OUT
    MOVI R0, #0
    STB  R0, R2, #0
    POPM {R0, R1, R2, R3, R7}
    RET

.END
