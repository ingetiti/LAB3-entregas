; Grupo 09 - Rutinas auxiliares propias para el SQRT independiente. [LC-3X]
; Entrada de SQ9_ROTL32: R0=palabra alta, R1=palabra baja, R2=n (0..31).
; Salida: (R0:R1) rotado 32 bits n posiciones hacia la izquierda.
; Conserva R2,R3,R7.
SQ9_ROTL32
    PUSHM #x0C                  ; Guarda R2, R3
SQH_LOOP
    ADD R2 R2 #0
    BRnz SQH_DONE
    AND R3 R3 #0
    ADD R0 R0 #0
    BRzp SQH_HI_ZERO
    ADD R3 R3 #1
SQH_HI_ZERO
    ADD R0 R0 R0
    ADD R1 R1 #0
    BRzp SQH_LO_ZERO
    ADD R0 R0 #1
SQH_LO_ZERO
    ADD R1 R1 R1
    ADD R1 R1 R3
    ADD R2 R2 #-1
    BRnzp SQH_LOOP
SQH_DONE
    POPM #x0C                   ; Restaura R2, R3
    RET

; Conversor Q15.16 (R0:R1) -> Q7.8 (R0), redondeo a 8 bits.
SQ9_DQ16_TO_Q8
    PUSHM #x86                  ; Guarda R1, R2, R7
    MOVI R2 #8
    JSR SQ9_ROTL32
    ADD R1 R1 #0
    BRzp SQH_CIN_OK
    ADD R0 R0 #1
SQH_CIN_OK
    POPM #x86                   ; Restaura R1, R2, R7
    RET

; Conversor Q7.8 (R0) -> Q15.16 (R0:R1).
SQ9_Q8_TO_DQ16
    PUSHM #x84                  ; Guarda R2, R7
    ADD R1 R0 #0
    AND R0 R0 #0
    ADD R1 R1 #0
    BRzp SQH_COUT_POS
    NOT R0 R0
SQH_COUT_POS
    MOVI R2 #8
    JSR SQ9_ROTL32
    LD R2 SQH_FF00
    AND R1 R1 R2
    POPM #x84                   ; Restaura R2, R7
    RET

SQH_FF00 .FILL xFF00

.END
