; ===========================================================================
; Modulo potencia (OPTIMIZADA): A^B por multiplicaciones sucesivas en Q7.8
;   Entrada : R0 = A (Q7.8), R1 = B (entero)
;   Salida  : R0 = A^B (Q7.8), o x8000 en error/overflow
; ===========================================================================

Mul_Sucesiva_POW
        PUSHM {R1, R2, R3, R7}

        ADD  R3, R1, #0         ; R3 = B
        ADD  R1, R0, #0         ; R1 = A
        CMP  R3, #0
        BRn  POT_ERR
        BRp  POT_POS
        CMP  R0, #0             ; B == 0
        BRz  POT_ERR            ; 0^0 error
        LD   R0, POT_UNO        ; A^0 = 1.00
        BRnzp POT_FIN
POT_POS
        CMP  R0, #0
        BRz  POT_FIN            ; 0^B = 0
        ADD  R3, R3, #-1
        BRz  POT_FIN            ; B == 1
        LD   R2, POT_ERRQ
POT_BUC
        JSR  MULT               ; R0 = R0 * A (Q7.8 truncado)
        CMP  R0, R2             ; R0 == x8000?
        BRz  POT_FIN
        ADD  R3, R3, #-1
        BRp  POT_BUC
        BRnzp POT_FIN
POT_ERR
        LD   R0, POT_ERRQ
POT_FIN
        POPM {R1, R2, R3, R7}
        RET

POT_UNO     .FILL x0100
POT_ERRQ    .FILL x8000

; MULT: producto Q7.8 truncado hacia cero con chequeo de desborde (x8000)
MULT
        PUSHM {R1, R2, R3, R4, R5}
        LD   R5, POT_ERRQ       ; x8000
        CMP  R0, R5
        BRz  MULT_DESB
        CMP  R1, R5
        BRz  MULT_DESB

        XOR  R5, R0, R1         ; bit 15 = signo final
        ABS  R2, R0             ; |A| (0..32767)
        ABS  R3, R1             ; |B| (0..32767)

        MULL R0, R2, R3         ; parte baja de |A|*|B|
        MULH R4, R2, R3         ; parte alta de |A|*|B|
        ; Overflow si |A|*|B| >> 8 >= 32768, es decir R4 >= 128
        LSR  R1, R4, #7
        BRnp MULT_DESB

        SHL  R4, R4, #8
        LSR  R0, R0, #8
        OR   R0, R4, R0         ; mag = floor(|A|*|B| / 256)

        CMP  R5, #0
        BRzp MULT_VUELVE
        NEG  R0, R0
        BRnzp MULT_VUELVE

MULT_DESB
        LD   R0, POT_ERRQ

MULT_VUELVE
        POPM {R1, R2, R3, R4, R5}
        RET

        .END
