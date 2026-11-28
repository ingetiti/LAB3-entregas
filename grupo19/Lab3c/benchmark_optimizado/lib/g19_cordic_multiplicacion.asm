; =====================================================================
;  MULTIPLICACION POR CORDIC (modo lineal) EN Q7.8 - MODULO DE BIBLIOTECA
;  Exporta: CORDIC_MUL
;
;  FORMATO: Q7.8 en complemento a 2 (16 bits): valor_real = palabra / 256
;
;  CONVENCION DE LLAMADO:
;    Entrada : R0 = a_q8     R1 = b_q8
;    Salida  : R0 = resultado en Q7.8 (0 si R1 != 0)
;              R1 = estado: 0 = ok / 1 = desbordamiento / 2 = b_q8 invalido (-32768)
;    Deja en memoria: CM_Y (32 bits Q16 hi:lo) y CM_ITER (iteraciones)
;    Conserva: R2..R6, R7 y SP
;
;  Optimizaciones nueva ISA:
;    - Modulo limpio sin .ORIG ni MAIN/I/O standalone.
;    - PUSHM/POPR con pila hardware (SP).
;    - PREPARAR_X en 2 instrucciones (ASR #2 y SHL #14).
;    - Suma/resta de 32 bits en registros con ADD+ADC y SUB+SBC.
;    - Desplazamiento aritmetico de 32 bits con ASR #1 + RRC.
;    - current_z generado por LSR #1 desde 16384 (elimina CM_TABLA_Z).
;    - REDUCIR_Q78 directo con ADD+ADC y SHL #8 / LSR #8 / OR.
; =====================================================================

CORDIC_MUL:
        PUSHM   {R2, R3, R4, R5, R6, R7}

        ; Rechazar b_q8 == -32768 (0x8000).
        LI      R3, x8000
        CMP     R1, R3
        BRz     CM_B_INVALIDO

        ; R2 = z = b_q8
        MOV     R2, R1

        ; current_x (R4:R5) = a_q8 * 2^14
        ASR     R4, R0, #2              ; x.hi = a_q8 >>a 2
        SHL     R5, R0, #14             ; x.lo = (a_q8 & 3) << 14

        ; Acumulador y (R0:R1) = 0:0, peso current_z (R3) = 2^14, i (R6) = 0
        CLR     R0
        CLR     R1
        LI      R3, #16384
        CLR     R6

CM_LAZO:
        ADDI    R2, R2, #0              ; if (z == 0) break;
        BRz     CM_FIN_LAZO
        BRn     CM_Z_NEG

        ; z > 0: z -= current_z; y += current_x
        SUB     R2, R2, R3
        ADD     R1, R1, R5
        ADC     R0, R0, R4
        BR      CM_SIGUE

CM_Z_NEG:
        ; z < 0: z += current_z; y -= current_x
        ADD     R2, R2, R3
        SUB     R1, R1, R5
        SBC     R0, R0, R4

CM_SIGUE:
        ASR     R4, R4, #1              ; current_x >>= 1 (aritmetico 32 bits)
        RRC     R5, R5
        INC     R6                      ; i++
        LSR     R3, R3, #1              ; current_z >>= 1 (termina al llegar a 0 tras 15 vueltas)
        BRnp    CM_LAZO

CM_FIN_LAZO:
        ST      R6, CM_ITER
        LEA     R2, CM_Y
        STW     R0, R2, #0              ; CM_Y.hi
        STW     R1, R2, #1              ; CM_Y.lo (offset de palabra 1 = +2 bytes)

        ; Reducir y (Q16) a Q7.8 con redondeo: (y + 128) >> 8
        LI      R2, #128
        CLR     R3
        ADD     R1, R1, R2              ; y.lo + 128
        ADC     R0, R0, R3              ; y.hi + C

        ; Verificar si cabe en Q7.8: ((y.hi + 128) & 0xFF00) == 0
        ADD     R2, R0, R2
        LI      R3, xFF00
        AND     R2, R2, R3
        BRz     CM_SIN_DESB

        CLR     R0
        MOVI    R1, #1                  ; estado = 1 (desbordamiento)
        BR      CM_FIN

CM_SIN_DESB:
        SHL     R0, R0, #8
        LSR     R1, R1, #8
        OR      R0, R0, R1              ; R0 = resultado Q7.8
        CLR     R1                      ; estado = 0 (ok)
        BR      CM_FIN

CM_B_INVALIDO:
        CLR     R0
        ST      R0, CM_ITER
        MOVI    R1, #2                  ; estado = 2 (b_q8 invalido)

CM_FIN:
        POPR    {R2, R3, R4, R5, R6, R7}

CM_Y:    .BLKW  #2                      ; acumulador y (32 bits, Q16)
CM_ITER: .BLKW  #1

        .END
