; ============================================================================
; Modulo: Reduccion de Argumento CORDIC (g20_Cordic_reduccion_de_argumento.asm)
; Reduce R0 (Q3.12) al intervalo [-Pi/2, Pi/2] sumando o restando Pi.
; Adaptado y optimizado para la nueva ISA de 16 bits byte-addressable:
;   - PUSHM/POPM en pila hardware SP.
;   - LI/CMP/BRle/BRge/SUB para evitar accesos a memoria dentro del lazo.
; ============================================================================

Reduccion_Argumento
        PUSHM {R1, R2}        ; Guardamos registros auxiliares en pila hardware

        LI    R1, #6434       ; Pi/2 (+1 LSB de tolerancia: tita <= 6434)
        LI    R2, #12867      ; Pi en Q3.12

REDUCCION_POS
        CMP   R0, R1          ; tita - 6434
        BRle  REDUCCION_NEG_INIT
        SUB   R0, R0, R2      ; tita = tita - Pi
        BR    REDUCCION_POS

REDUCCION_NEG_INIT
        LI    R1, #-6433      ; -Pi/2 en Q3.12

REDUCCION_NEG
        CMP   R0, R1          ; tita - (-6433)
        BRge  FIN
        ADD   R0, R0, R2      ; tita = tita + Pi
        BR    REDUCCION_NEG

FIN
        POPM  {R1, R2}        ; Restauramos registros auxiliares
        RET

        .END
