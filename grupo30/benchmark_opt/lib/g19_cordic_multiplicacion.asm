; =====================================================================
;  MULTIPLICACION POR CORDIC (modo lineal) EN Q7.8 (OPTIMIZADA)
;  Funcion publica: CORDIC_MUL
;    Entrada : R0 = a_q8, R1 = b_q8
;    Salida  : R0 = resultado Q7.8, R1 = estado (0=ok, 1=ovf, 2=b invalido)
;    Conserva: R2..R6, R7
;  Algoritmo: 15 iteraciones de CORDIC lineal (z, y, current_x) +
;    redondeo y reduccion de 32 bits (Q16) a Q7.8.
; =====================================================================

CORDIC_MUL
        PUSHM {R2, R3, R4, R5, R7}

        ADD  R2, R1, #0         ; z = b_q8
        LD   R3, CM_B_MIN       ; 0x8000
        CMP  R2, R3
        BRz  CM_B_INVALIDO

        ; Acumulador y = 0 (en memoria CM_Y: hi, lo)
        MOVI R3, #0
        ST   R3, CM_Y
        ST   R3, CM_Y_LO

        ; current_x = a_q8 * 2^14 -> hi = a >>a 2, lo = a << 14
        ASR  R3, R0, #2
        SHL  R4, R0, #14
        ST   R3, CM_X
        ST   R4, CM_X_LO

        ; Lazo CORDIC lineal (hasta 15 iteraciones)
        ; R2 = z, R4 = puntero a CM_TABLA_Z, R5 = i (0..14)
        MOVI R5, #0
        LEA  R4, CM_TABLA_Z
CM_LAZO
        CMP  R2, #0
        BRz  CM_FIN_LAZO
        LDR  R3, R4, #0         ; current_z = tabla_z[i]
        CMP  R2, #0
        BRn  CM_Z_NEG

        ; z > 0: z -= current_z; y += current_x
        SUB  R2, R2, R3
        LEA  R0, CM_Y
        LEA  R1, CM_X
        JSR  SUMA32
        BRnzp CM_SIGUE

CM_Z_NEG
        ; z < 0: z += current_z; y -= current_x
        ADD  R2, R2, R3
        LEA  R0, CM_Y
        LEA  R1, CM_X
        JSR  RESTA32

CM_SIGUE
        ; current_x >>= 1 (aritmetico 32 bits en CM_X)
        LD   R0, CM_X           ; x.hi
        LD   R1, CM_X_LO        ; x.lo
        SHL  R3, R0, #15
        LSR  R1, R1, #1
        OR   R1, R1, R3
        ASR  R0, R0, #1
        ST   R0, CM_X
        ST   R1, CM_X_LO

        ADD  R4, R4, #2         ; siguiente peso (2 bytes)
        ADD  R5, R5, #1
        MOVI R3, #15
        CMP  R5, R3
        BRn  CM_LAZO

CM_FIN_LAZO
        ST   R5, CM_ITER

        ; Reducir y (Q16) -> Q7.8 con redondeo: (y + 128) >> 8
        LEA  R0, CM_Y
        LEA  R1, CM_RES
        JSR  REDUCIR_Q78
        ADD  R1, R0, #0
        BRp  CM_DESBORDA
        LD   R0, CM_RES
        BRnzp CM_FIN

CM_DESBORDA
        MOVI R0, #0
        BRnzp CM_FIN

CM_B_INVALIDO
        MOVI R1, #2
        MOVI R0, #0
        ST   R0, CM_ITER

CM_FIN
        POPM {R2, R3, R4, R5, R7}
        RET

CM_TABLA_Z .FILL #16384
           .FILL #8192
           .FILL #4096
           .FILL #2048
           .FILL #1024
           .FILL #512
           .FILL #256
           .FILL #128
           .FILL #64
           .FILL #32
           .FILL #16
           .FILL #8
           .FILL #4
           .FILL #2
           .FILL #1
CM_B_MIN .FILL x8000
CM_Y     .BLKW #1
CM_Y_LO  .BLKW #1
CM_X     .BLKW #1
CM_X_LO  .BLKW #1
CM_RES   .BLKW #1
CM_ITER  .BLKW #1

; ---------------------------------------------------------------------
;  SUMA32 : [R0] = [R0] + [R1] (pares hi/lo de 32 bits)
; ---------------------------------------------------------------------
SUMA32
        PUSHM {R2, R3, R4, R5}
        LDR  R2, R0, #1         ; a.lo
        LDR  R3, R1, #1         ; b.lo
        ADD  R4, R2, R3         ; lo = a.lo + b.lo
        ; carry unsigned sin saltos: ((a & b) | ((a | b) & ~lo)) >>> 15
        AND  R5, R2, R3
        OR   R2, R2, R3
        NOT  R3, R4
        AND  R2, R2, R3
        OR   R5, R5, R2
        LSR  R5, R5, #15
        LDR  R2, R0, #0         ; a.hi
        LDR  R3, R1, #0         ; b.hi
        ADD  R2, R2, R3
        ADD  R2, R2, R5
        STR  R2, R0, #0
        STR  R4, R0, #1
        POPM {R2, R3, R4, R5}
        RET

; ---------------------------------------------------------------------
;  RESTA32 : [R0] = [R0] - [R1]
; ---------------------------------------------------------------------
RESTA32
        PUSHM {R1, R2, R3, R7}
        LDR  R2, R1, #0
        NOT  R2, R2
        LDR  R3, R1, #1
        NOT  R3, R3
        ADD  R3, R3, #1
        BRnp REST_ARMAR
        ADD  R2, R2, #1
REST_ARMAR
        LEA  R1, REST_OPUESTO
        STR  R2, R1, #0
        STR  R3, R1, #1
        JSR  SUMA32
        POPM {R1, R2, R3, R7}
        RET
REST_OPUESTO .BLKW #2

; ---------------------------------------------------------------------
;  REDUCIR_Q78 : pasa y (Q16, 32 bits) a Q7.8 con redondeo: (y + 128) >> 8
; ---------------------------------------------------------------------
REDUCIR_Q78
        PUSHM {R1, R2, R3, R4, R5, R7}
        ADD  R5, R1, #0         ; R5 = &resultado_q78
        LEA  R2, RQ_COPIA
        LDR  R3, R0, #0
        STR  R3, R2, #0
        LDR  R3, R0, #1
        STR  R3, R2, #1

        ADD  R0, R2, #0
        LEA  R1, RQ_MEDIO
        JSR  SUMA32

        LDR  R3, R0, #0         ; copia.hi
        LD   R4, RQ_128
        ADD  R4, R3, R4
        LD   R2, RQ_FF00
        AND  R4, R4, R2
        BRz  RQ_SIN_DESB
        MOVI R0, #1
        BRnzp RQ_FIN

RQ_SIN_DESB
        LDR  R4, R0, #1         ; copia.lo
        SHL  R3, R3, #8         ; hi << 8
        LSR  R4, R4, #8         ; lo >>> 8
        OR   R3, R3, R4
        STR  R3, R5, #0
        MOVI R0, #0

RQ_FIN
        POPM {R1, R2, R3, R4, R5, R7}
        RET

RQ_COPIA .BLKW #2
RQ_MEDIO .FILL #0
         .FILL #128
RQ_128   .FILL #128
RQ_FF00  .FILL xFF00

        .END
