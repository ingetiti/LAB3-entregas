;====================================================================
; g18_booth.asm - Modulo "booth": multiplicador Booth 16x16 en Q7.8
; Funcion publica: MULT_BOOTH
;
; CONVENCION DE LLAMADA
;   Entrada : R0 = X, primer operando  (Q7.8, 16 bits con signo)
;             R1 = Y, segundo operando (Q7.8, 16 bits con signo)
;   Salida  : R0 = RES = P[23:8]       (producto reducido a Q7.8)
;   Conserva: R1..R7 y SP
;   CC      : al retornar reflejan el signo de RES (R0).
;
; Optimizaciones nueva ISA:
;   - PUSHM/POPR con pila hardware (SP), sin marco manual en R6.
;   - Todo el bucle de Booth en registros (sin MCAND/MNEG/QM1/Q0SAVE).
;   - ASR/LSR + RRC reemplazan las subrutinas SHR1/ASR1 de 15 vueltas.
;   - Conversion P[23:8] directa con SHL #8, LSR #8 y OR (sin bucle de 8).
;====================================================================

MULT_BOOTH:
        PUSHM   {R1, R2, R3, R4, R5, R6, R7}

        ; R0 = M (X), R5 = Q (Y), R4 = A = 0, R1 = QM1 = 0, R2 = CNT = 16
        MOV     R5, R1
        CLR     R4
        CLR     R1
        MOVI    R2, #16
        LI      R6, x8000             ; constante para caso borde A' == x8000

;---------------- bucle de Booth: 16 iteraciones ----------------
BOOTH_LOOP:
        ANDI    R3, R5, #1              ; R3 = q0 = Q[0]
        CMP     R1, R3                  ; comparar QM1 con q0
        BRz     BOOTH_SHIFT             ; QM1 == q0 -> sin suma ni resta
        BRlt    BOOTH_RESTA             ; QM1 < q0 (0 < 1) -> A <- A - M
        ADD     R4, R4, R0              ; QM1 > q0 (1 > 0) -> A <- A + M
        BR      BOOTH_SHIFT
BOOTH_RESTA:
        SUB     R4, R4, R0

BOOTH_SHIFT:
        ; Desplazar {A', Q} 1 bit a la derecha.
        ; Preserva el caso borde del original: si A' == x8000, E = 0 (LSR).
        CMP     R4, R6
        BRz     BOOTH_LSR_A
        ASR     R4, R4, #1              ; A <- A' >>a 1, bit 0 -> C
        BR      BOOTH_ROT_Q
BOOTH_LSR_A:
        LSR     R4, R4, #1              ; E = 0, bit 0 -> C
BOOTH_ROT_Q:
        RRC     R5, R5                  ; Q <- {A'[0], Q[15:1]}
        MOV     R1, R3                  ; QM1 <- q0
        DEC     R2
        BRp     BOOTH_LOOP

;---------------- producto bruto: PH:PL = A:Q ----------------
        ST      R4, PH
        ST      R5, PL

;---------------- Q7.8: RES = P[23:8] = (PH << 8) | (PL >> 8) ----------------
        SHL     R1, R4, #8
        LSR     R5, R5, #8
        OR      R0, R1, R5
        ST      R0, RES

;---------------- OVF = ((PH + x0080) AND xFF00) != 0 ----------------
        LI      R1, x0080
        ADD     R4, R4, R1              ; PH + 128
        LI      R1, xFF00
        AND     R4, R4, R1
        BRz     BOOTH_GOVF
        MOVI    R4, #1
BOOTH_GOVF:
        ST      R4, OVFV

        ; Asegurar CC segun el signo de RES (R0); POPR preserva todos los flags.
        ADDI    R0, R0, #0
        POPR    {R1, R2, R3, R4, R5, R6, R7}

;---------------- datos de diagnostico del modulo ----------------
PH:     .FILL   x0000
PL:     .FILL   x0000
RES:    .FILL   x0000
OVFV:   .FILL   x0000

        .END
