;====================================================================
; booth.asm (OPTIMIZADA) - Multiplicador Booth 16x16 en Q7.8
; Funcion publica: MULT_BOOTH
;   Entrada : R0 = X (Q7.8), R1 = Y (Q7.8)
;   Salida  : R0 = RES = P[23:8] (Q7.8)
;   Conserva: R1..R5, R6, R7
; Algoritmo: 16 iteraciones de Booth (recodificacion QM1-q0, suma/resta
;   de M, desplazamiento aritmetico con extension E) + reduccion Q7.8.
;====================================================================

MULT_BOOTH
        PUSHM {R1, R2, R3, R4, R5, R7}

        ADD  R7, R0, #0         ; R7 = M (multiplicando X)
        ADD  R5, R1, #0         ; R5 = Q (multiplicador Y)
        MOVI R4, #0             ; R4 = A = 0
        MOVI R2, #0             ; R2 = QM1 = 0
        MOVI R3, #16            ; R3 = contador (16 iteraciones)
        LD   R1, C8000          ; R1 = x8000 (constante para chequeo E)

BOOTH   AND  R0, R5, #1         ; R0 = q0 = Q[0]
        CMP  R2, R0             ; comparar QM1 vs q0
        BRz  SINSUM             ; QM1 == q0: no sumar ni restar
        BRn  RESTA              ; QM1 < q0 (0 - 1 = -1): A = A - M
        ADD  R4, R4, R7         ; QM1 > q0 (1 - 0 = +1): A = A + M
        BRnzp SINSUM
RESTA   SUB  R4, R4, R7         ; A = A - M

SINSUM  ADD  R2, R0, #0         ; nuevo QM1 = q0
        ; Q = {A'[0], Q[15:1]}
        SHL  R0, R4, #15
        LSR  R5, R5, #1
        OR   R5, R5, R0
        ; A = {E, A'[15:1]} (E = 0 si A' == x8000, sino signo de A')
        CMP  R4, R1
        BRz  ECERO
        ASR  R4, R4, #1
        BRnzp NEXT_B
ECERO   LSR  R4, R4, #1
NEXT_B  ADD  R3, R3, #-1
        BRp  BOOTH

        ; Producto bruto PH:PL = R4:R5
        ST   R4, PH
        ST   R5, PL

        ; Q7.8: RES = P[23:8] = (PH << 8) | (PL >>> 8)
        SHL  R0, R4, #8
        LSR  R5, R5, #8
        OR   R0, R0, R5
        ST   R0, RES

        ; OVF = ((PH + x0080) & xFF00) != 0
        LD   R1, C0080
        ADD  R2, R4, R1
        LD   R1, CFF00
        AND  R2, R2, R1
        BRz  GOVF
        MOVI R2, #1
GOVF    ST   R2, OVFV

        POPM {R1, R2, R3, R4, R5, R7}
        ADD  R0, R0, #0         ; CC <- signo de RES
        RET

PH      .FILL x0000
PL      .FILL x0000
RES     .FILL x0000
OVFV    .FILL x0000
C0080   .FILL x0080
CFF00   .FILL xFF00
C8000   .FILL x8000

        .END
