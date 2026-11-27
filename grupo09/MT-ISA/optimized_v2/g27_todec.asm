; Convertir a decimal según el mismo redondeo del módulo LC-3.
; R0:R1 = entero:fracción Q15.16. R2 apunta al búfer de 17 palabras.
; R3 selecciona signo positivo explícito y ceros a la izquierda o derecha.
TODEC
    ST R0, TO_R0
    ST R1, TO_R1
    ST R2, TO_R2
    ST R3, TO_R3
    ST R4, TO_R4
    ST R5, TO_R5
    ST R7, TO_R7
    JSR TODEC_FAST
    LD R0, TO_R0
    LD R1, TO_R1
    LD R2, TO_R2
    LD R3, TO_R3
    LD R4, TO_R4
    LD R5, TO_R5
    LD R7, TO_R7
    RET

; Entrada rápida para OUTVAL. Modifica R0–R5 y conserva R6 y R7.
TODEC_FAST
    ST R7, FAST_LINK
    ADD R0, R0, #0
    BRzp POSITIVE
    LD R4, CH_MINUS
    STR.POST R4, R2
    AND R4, R4, #0
    SUB R1, R4, R1
    SBC R0, R4, R0
    BR INTEGER
POSITIVE
    AND R4, R3, #1
    BRz INTEGER
    LD R4, CH_PLUS
    STR.POST R4, R2
INTEGER
    ; Encontrar el primer dígito visible y dividir por las potencias de diez.
    ST R1, FRAC
    LD R5, CH_ZERO
    AND R7, R3, #2
    BRnp FIVE
    ADD R4, R0, #-10
    BRn ONE
    LD R4, NEG100
    ADD R4, R0, R4
    BRn TWO
    LD R4, NEG1000
    ADD R4, R0, R4
    BRn THREE
    LD R4, NEG10000
    ADD R4, R0, R4
    BRn FOUR
FIVE
    LEA R4, DIV10000
    BR DIGITS
FOUR
    LEA R4, DIV1000
    BR DIGITS
THREE
    LEA R4, DIV100
    BR DIGITS
TWO
    LEA R4, DIV10
DIGITS
    LDR R7, R4, #0
DIGIT_LOOP
    AND R1, R1, #0
    DIVUW R0, R0, R7
    ADD R0, R0, R5
    STR.POST R0, R2
    ADD R0, R1, #0
    ADD R4, R4, #2
    LDR R7, R4, #0
    BRp DIGIT_LOOP
ONE
    ADD R0, R0, R5
    STR.POST R0, R2
    LD R0, FRAC
    BRnp FRACTION
    AND R4, R3, #4
    BRz TERMINATE
    LD R4, CH_DOT
    STR.POST R4, R2
    AND R4, R4, #0
    ADD R4, R4, #9
ZERO_LOOP
    STR.POST R5, R2
    ADD R4, R4, #-1
    BRp ZERO_LOOP
    BR TERMINATE
FRACTION
    LD R4, CH_DOT
    STR.POST R4, R2
    ; Compensar el truncamiento por bit del módulo LC-3 antes de recortar ceros.
    LD R4, CORRECTION_MASK
    AND R4, R4, R0
    LEA R7, todec_corrections
    ADD R4, R4, R7
    AND R7, R7, #0
    LDBL R7, R4, #0
    AND R4, R4, #0
    ADD R4, R4, #10
    MULUW R0, R0, R4
    ADD R1, R1, R5
    STR R1, R2, #0
    MULUW R0, R0, R4
    ADD R1, R1, R5
    STR R1, R2, #1
    MULUW R0, R0, R4
    ADD R1, R1, R5
    STR R1, R2, #2
    MULUW R0, R0, R4
    ADD R1, R1, R5
    STR R1, R2, #3
    MULUW R0, R0, R4
    ADD R1, R1, R5
    STR R1, R2, #4
    MULUW R0, R0, R4
    ADD R1, R1, R5
    STR R1, R2, #5
    MULUW R0, R0, R4
    ADD R1, R1, R5
    STR R1, R2, #6
    MULUW R0, R0, R4
    ADD R1, R1, R5
    STR R1, R2, #7
    MULUW R0, R0, R4
    ADD R1, R1, R5
    STR R1, R2, #8

    ADD R4, R2, #14
    ADD R4, R4, #2
    ADD R7, R7, #0
    BRz TRIM
    ADD R0, R4, #0
CORRECT
    LDR R1, R0, #0
    SUB R1, R1, R5
    SUB R1, R1, R7
    BRzp CORRECT_DONE
    ADD R1, R1, #10
    ADD R1, R1, R5
    STR R1, R0, #0
    AND R7, R7, #0
    ADD R7, R7, #1
    ADD R0, R0, #-2
    BR CORRECT
CORRECT_DONE
    ADD R1, R1, R5
    STR R1, R0, #0
TRIM
    AND R3, R3, #4
    BRnp TERMINATE_FRAC
TRIM_LOOP
    LDR R0, R4, #0
    SUB R0, R0, R5
    BRnp TERMINATE_FRAC
    SUB R0, R4, R2
    BRz TERMINATE_FRAC
    ADD R4, R4, #-2
    BR TRIM_LOOP
TERMINATE_FRAC
    ADD R2, R4, #2
TERMINATE
    AND R0, R0, #0
    STR R0, R2, #0
    LD R7, FAST_LINK
    RET

TO_R0 .BLKW #1
TO_R1 .BLKW #1
TO_R2 .BLKW #1
TO_R3 .BLKW #1
TO_R4 .BLKW #1
TO_R5 .BLKW #1
TO_R7 .BLKW #1
FAST_LINK .BLKW #1
FRAC .BLKW #1
CH_MINUS .FILL #45
CH_PLUS .FILL #43
CH_DOT .FILL #46
CH_ZERO .FILL #48
NEG100 .FILL #-100
NEG1000 .FILL #-1000
NEG10000 .FILL #-10000
DIV10000 .FILL #10000
DIV1000 .FILL #1000
DIV100 .FILL #100
DIV10 .FILL #10
    .FILL #0
CORRECTION_MASK .FILL x007F
todec_corrections
    .BYTE #0, #0, #0, #1, #0, #0, #0, #1, #0, #1, #0, #1, #0, #1, #1, #1
    .BYTE #0, #1, #1, #1, #0, #1, #1, #2, #0, #1, #1, #2, #1, #1, #1, #2
    .BYTE #0, #1, #0, #1, #0, #1, #0, #1, #0, #1, #1, #1, #0, #1, #1, #2
    .BYTE #0, #1, #1, #2, #1, #1, #1, #2, #1, #1, #1, #2, #1, #2, #1, #2
    .BYTE #0, #1, #1, #1, #0, #1, #1, #2, #0, #1, #1, #2, #0, #1, #1, #2
    .BYTE #1, #1, #1, #2, #1, #2, #1, #2, #1, #2, #2, #2, #1, #2, #2, #2
    .BYTE #0, #1, #1, #2, #0, #1, #1, #2, #1, #1, #1, #2, #1, #2, #1, #2
    .BYTE #1, #2, #1, #2, #1, #2, #2, #2, #1, #2, #2, #3, #1, #2, #2, #3

.END
