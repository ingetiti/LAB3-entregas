;====================================================================
; booth.asm - Modulo "booth": multiplicador 16x16 en Q7.8
; Funcion publica: MULT_BOOTH      (se importa como BOOTH-MULT_BOOTH)
; Optimizado usando MUL, MULH, RSHFL y LSHF de la ISA.
;
; CONVENCION DE LLAMADA
;   Entrada : R0 = X, primer operando  (Q7.8, 16 bits con signo)
;             R1 = Y, segundo operando (Q7.8, 16 bits con signo)
;   Salida  : R0 = RES = P[23:8]       (producto reducido a Q7.8)
;   Conserva: R1, R2, R3, R4, R5, R6, R7
;   Destruye: R0 (es el resultado)
;   CC      : al retornar reflejan el signo de RES (ultimo LD es R0).
;====================================================================

MULT_BOOTH
        ST   R2, SAVE_R2
        ST   R3, SAVE_R3

        MUL  R2, R0, R1         ; PL = bits bajos del producto con signo 16x16
        MULH R3, R0, R1         ; PH = bits altos del producto con signo 16x16
        ST   R3, PH
        ST   R2, PL

        RSHFL R2, R2, #8        ; P[15:8] -> bits 7..0
        LSHF  R3, R3, #8        ; P[23:16] -> bits 15..8
        ADD   R0, R2, R3        ; RES = P[23:8] (Q7.8)
        ST    R0, RES

;---------------- OVF = ((PH + x0080) AND xFF00) != 0 ----------------
        LD   R2, PH
        LD   R3, C0080
        ADD  R2, R2, R3         ; PH + 128
        LD   R3, CFF00
        AND  R2, R2, R3         ; byte alto de (PH + 128)
        BRz  GOVF
        AND  R2, R2, #0
        ADD  R2, R2, #1
GOVF    ST   R2, OVFV

        LD   R2, SAVE_R2
        LD   R3, SAVE_R3
        LD   R0, RES            ; R0 = RES (salida) ; CC <- signo de RES
        RET

;---------------- datos del modulo ----------------
PH      .FILL x0000
PL      .FILL x0000
RES     .FILL x0000
OVFV    .FILL x0000
SAVE_R2 .FILL x0000
SAVE_R3 .FILL x0000
C0080   .FILL x0080
CFF00   .FILL xFF00

        .END
