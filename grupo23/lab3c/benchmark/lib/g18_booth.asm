;====================================================================
; [G23] g18_booth.asm - version para la ISA G23 (capa de optimizaciones)
; Funcion publica: MULT_BOOTH
;
; La cátedra autorizó (25/11/2026) reemplazar completas las subrutinas que solo
; multiplican o dividen por MUL/DIV cuando dan los mismos resultados. El algoritmo
; de Booth del original calcula el producto exacto de 32 bits (se verificó con un
; modelo y contra la LC-3), así que acá se obtiene con MUL (16 bits bajos) y MULH
; (16 bits altos, con signo), y se arma igual que el original:
;
; CONVENCION DE LLAMADA (la misma del original)
;   Entrada : R0 = X (Q7.8)   R1 = Y (Q7.8)
;   Salida  : R0 = RES = P[23:8] (producto reducido a Q7.8)
;   Conserva: R1..R7
;   CC      : al retornar reflejan el signo de RES
;   Datos   : PH, PL (producto de 32 bits), RES y OVFV (1 si PH esta fuera de
;             [-128, 127]), igual que el original
;====================================================================

MULT_BOOTH
        PUSH R1, R2
        MUL  R2, R0, R1         ; PL = 16 bits bajos de X*Y
        MULH R1, R0, R1         ; PH = 16 bits altos (con signo)
        ST   R2, PL
        ST   R1, PH
        LSR  R2, R2, #8         ; P[15:8]
        LSL  R0, R1, #8         ; P[23:16] en la parte alta
        OR   R0, R0, R2         ; RES = P[23:8] = P >> 8
        ST   R0, RES
;---------------- OVF = ((PH + x0080) AND xFF00) != 0 ----------------
        LD   R2, C0080
        ADD  R1, R1, R2         ; PH + 128
        LD   R2, CFF00
        AND  R1, R1, R2
        BRz  GOVF
        AND  R1, R1, #0
        ADD  R1, R1, #1         ; OVF = 1
GOVF    ST   R1, OVFV
        POP  R1, R2
        ADD  R0, R0, #0         ; CC <- signo de RES (como el original)
        RET
;---------------- datos del modulo ----------------
PH      .FILL x0000
PL      .FILL x0000
RES     .FILL x0000
OVFV    .FILL x0000
C0080   .FILL x0080
CFF00   .FILL xFF00
        .END
