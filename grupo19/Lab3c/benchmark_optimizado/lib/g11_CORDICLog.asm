; =====================================================================
; SUBRUTINA CORDIC_LOG_BASE : logaritmo natural en Q3.12 (Nueva ISA 16 bits)
;   Entrada : R0 = m  (Q3.12, 0 < m <= 7.9998 = x7FFF)
;   Salida  : R0 = ln(m) (Q3.12, rango representable -8.0 .. 7.99)
;   Conserva R1-R7 (R6 no se usa). Sin .ORIG (se adjunta al programa).
;   m <= 0  -> R0 = x8000 (-8.0, ln no definido)
;   m muy chico (ln(m) < -8) -> R0 = x8000 (saturado)
;
; Metodo: CORDIC hiperbolico, modo vectorial
;   ln(m) = 2*atanh((m-1)/(m+1)) ; se usa x=(m/2)+0.5 , y=(m/2)-0.5
;   Iteraciones i = 1,2,3,4,4,5,...,12.
;   Los desplazamientos por i usan SRLV (sin subrutina ASR), manteniendo
;   el truncamiento hacia cero exacto para valores negativos de y.
; =====================================================================

CORDIC_LOG_BASE
    ADD  R0, R0, #0
    BRnz LOG_MIN_EARLY          ; m <= 0 : no definido

    PUSHM {R1, R2, R3, R4, R5}

    ; ---- normalizacion: llevar m a >= 0.5 (x0800) contando k
    CLR  R5                     ; k = 0
    LD   R4, HALF_Q12           ; 0.5
NORM
    CMP  R0, R4
    BRge NORM_OK
    SHL  R0, R0, #1
    INC  R5
    BR   NORM
NORM_OK
    ST   R5, var_k

    ; ---- x = m/2 + 0.5 ; y = m/2 - 0.5 ; z = 0
    LSR  R0, R0, #1             ; R0 = m >> 1 (m > 0)
    ADD  R1, R0, R4             ; x = m/2 + 0.5
    SUB  R2, R0, R4             ; y = m/2 - 0.5
    CLR  R3                     ; z = 0
    CLR  R4                     ; indice en bytes para tablas de palabras (0, 2, 4...)

ITER
    LEA  R5, SEQ_I
    ADD  R5, R5, R4
    LDW  R5, R5, #0             ; R5 = i (0 = fin)
    BRz  FIN

    SRLV R0, R1, R5             ; x > 0: x >> i (truncado hacia cero)
    ST   R0, var_xs

    MOV  R0, R2                 ; y >> i con truncamiento hacia cero
    ADD  R0, R0, #0
    BRzp Y_SHIFT_POS
    NEG  R0, R0
    SRLV R0, R0, R5
    NEG  R0, R0
    BR   Y_SHIFT_DONE
Y_SHIFT_POS
    SRLV R0, R0, R5
Y_SHIFT_DONE

    ADD  R2, R2, #0
    BRp  Y_POS

    ADD  R1, R1, R0             ; y<=0 : x += y>>i
    LD   R0, var_xs
    ADD  R2, R2, R0             ;        y += x>>i
    LEA  R5, LUT_ATANH
    ADD  R5, R5, R4
    LDW  R5, R5, #0
    SUB  R3, R3, R5             ;        z -= atanh
    BR   NEXT

Y_POS
    SUB  R1, R1, R0             ; y>0 : x -= y>>i
    LD   R0, var_xs
    SUB  R2, R2, R0             ;       y -= x>>i
    LEA  R5, LUT_ATANH
    ADD  R5, R5, R4
    LDW  R5, R5, #0
    ADD  R3, R3, R5             ;       z += atanh

NEXT
    ADDI R4, R4, #2             ; siguiente palabra (2 bytes)
    BR   ITER

FIN
    SHL  R3, R3, #1             ; 2*z = ln(m*2^k)
    LD   R5, var_k
    BRz  FIN_OK
    ADDI R1, R5, #-11
    BRzp LOG_MIN                ; k >= 11 : ln < -8, satura
    LD   R1, LN2_Q12
RESTA
    SUB  R3, R3, R1             ; ln(m) = ln(m*2^k) - k*ln2
    DEC  R5
    BRp  RESTA
FIN_OK
    MOV  R0, R3
    POPM {R1, R2, R3, R4, R5}
    RET

LOG_MIN
    LI   R0, x8000
    POPM {R1, R2, R3, R4, R5}
    RET

LOG_MIN_EARLY
    LI   R0, x8000
    RET

; ---------------------------------------------------------------------
; ZONA DE DATOS
; ---------------------------------------------------------------------
HALF_Q12  .FILL x0800           ; 0.5
LN2_Q12   .FILL #2839           ; ln(2)*4096
SEQ_I     .FILL #1
    .FILL #2
    .FILL #3
    .FILL #4
    .FILL #4                    ; repeticion obligatoria
    .FILL #5
    .FILL #6
    .FILL #7
    .FILL #8
    .FILL #9
    .FILL #10
    .FILL #11
    .FILL #12
    .FILL #0
LUT_ATANH                       ; atanh(2^-i)*4096
    .FILL #2250
    .FILL #1046
    .FILL #515
    .FILL #256
    .FILL #256
    .FILL #128
    .FILL #64
    .FILL #32
    .FILL #16
    .FILL #8
    .FILL #4
    .FILL #2
    .FILL #1
var_k       .BLKW #1
var_xs      .BLKW #1
.END
