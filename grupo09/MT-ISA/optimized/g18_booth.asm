; Booth 16x16 Q7.8. R0 = X, R1 = Y, devuelve R0 = P[23:8].
; Mantiene las 16 iteraciones y la extensión especial de A'=x8000
; de la versión original, además de los campos de diagnóstico.
; Preserva R1..R7. Al retornar N/Z/P refleja R0.

MULT_BOOTH
        ADD  R6, R6, #-10
        STR  R1, R6, #0
        STR  R2, R6, #1
        STR  R3, R6, #2
        STR  R4, R6, #3
        STR  R5, R6, #4

        ADD  R3, R0, #0         ; M
        ADD  R4, R1, #0         ; Q
        AND  R5, R5, #0         ; A
        AND  R1, R1, #0         ; q[-1]
        AND  R2, R2, #0
        ADD  R2, R2, #-16       ; contador de iteraciones

BOOTH   AND  R0, R4, #1
        SUB  R0, R1, R0         ; q[-1] - q[0]
        BRz  SINSUM
        BRn  RESTA
        ADD  R5, R5, R3
        BRnzp SINSUM
RESTA   SUB  R5, R5, R3

SINSUM  AND  R1, R4, #1         ; conservar q[0] antes de desplazar
        ADD  R0, R5, R5
        BRz  BOOTH_LOGICO      ; A' es cero o x8000: en ambos E=0
        ASRW R4, R4, #1        ; R5:R4 = A:Q
        BRnzp BOOTH_SIG
BOOTH_LOGICO
        LSRW R4, R4, #1
BOOTH_SIG
        ADD  R2, R2, #1
        BRn  BOOTH

        ST   R5, PH
        ST   R4, PL
        ASRW R4, R4, #8
        ST   R4, RES

        LD   R0, PH
        LD   R1, C0080
        ADD  R0, R0, R1
        LD   R1, CFF00
        AND  R0, R0, R1
        BRz  GOVF
        AND  R0, R0, #0
        ADD  R0, R0, #1
GOVF    ST   R0, OVFV

        LDR  R1, R6, #0
        LDR  R2, R6, #1
        LDR  R3, R6, #2
        LDR  R4, R6, #3
        LDR  R5, R6, #4
        ADD  R6, R6, #10
        LD   R0, RES
        RET

PH      .FILL x0000
PL      .FILL x0000
RES     .FILL x0000
OVFV    .FILL x0000
C0080   .FILL x0080
CFF00   .FILL xFF00

.END
