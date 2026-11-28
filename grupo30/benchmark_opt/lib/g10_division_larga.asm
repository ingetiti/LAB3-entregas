; ============================================================================
; Modulo: division (Grupo 10, OPTIMIZADA) - Division larga restoring 16 bits
; ============================================================================

DIVIDIR
        PUSHM {R1, R2, R3, R4, R5}

        MOVI R5, #0
        ST   R5, ESTADO

        CMP  R1, #0
        BRz  ERR_DIV0
        XOR  R5, R0, R1         ; bit 15 de R5 = signo del cociente

        ; |b| en R3 (modulo 2^16 para conservar x8000)
        ADD  R3, R1, #0
        BRp  B_POS
        NOT  R3, R3
        ADD  R3, R3, #1
B_POS
        ; |a| en R0 (modulo 2^16 para conservar x8000)
        CMP  R0, #0
        BRzp A_POS
        NOT  R0, R0
        ADD  R0, R0, #1
A_POS
        ; Dividendo 32 bits (R1:R0) = |a| << s (0 <= s <= 16)
        MOVI R1, #0
        CMP  R2, #0
        BRz  PRE_FIN
        MOVI R4, #16
        SUB  R4, R4, R2
        BRz  PRE_16
        LSR  R1, R0, R4
        SHL  R0, R0, R2
        BRnzp PRE_FIN
PRE_16
        ADD  R1, R0, #0
        MOVI R0, #0

PRE_FIN
        ; Si palabra alta >= |b| -> overflow
        SUB  R4, R1, R3
        BRzp OVERFLOW

        ; Lazo principal restoring: 16 iteraciones
        MOVI R2, #16
LAZO
        SHL  R1, R1, #1
        LSR  R4, R0, #15
        OR   R1, R1, R4
        SHL  R0, R0, #1
        CMP  R1, #0
        BRn  L_SIEMPRE          ; resto >= x8000 (>= |b|)
        SUB  R4, R1, R3
        BRn  L_SEGUIR
        ADD  R1, R4, #0
        ADD  R0, R0, #1
        BRnzp L_SEGUIR
L_SIEMPRE
        SUB  R1, R1, R3
        ADD  R0, R0, #1
L_SEGUIR
        ADD  R2, R2, #-1
        BRp  LAZO

        ; Aplicar signo y verificar rango
        CMP  R5, #0
        BRn  POST_NEG
        CMP  R0, #0
        BRn  OVERFLOW
        BRnzp EPILOGO
POST_NEG
        CMP  R0, #0
        BRzp NEG_APLIC
        SHL  R4, R0, #1
        BRnp OVERFLOW
NEG_APLIC
        NOT  R0, R0
        ADD  R0, R0, #1
        BRnzp EPILOGO

OVERFLOW
        MOVI R4, #2
        ST   R4, ESTADO
        LD   R0, K_X8000
        CMP  R5, #0
        BRn  EPILOGO
        NOT  R0, R0
        BRnzp EPILOGO

ERR_DIV0
        MOVI R0, #0
        MOVI R4, #1
        ST   R4, ESTADO

EPILOGO
        POPM {R1, R2, R3, R4, R5}
        RET

DIV_LONG
        PUSHM {R2, R7}
        MOVI R2, #8
        JSR  DIVIDIR
        POPM {R2, R7}
        RET

ESTADO      .FILL x0000
K_X8000     .FILL x8000
            .END
