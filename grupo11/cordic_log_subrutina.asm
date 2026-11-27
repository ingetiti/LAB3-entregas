; =====================================================================
; SUBRUTINA CORDIC_LOG_BASE : logaritmo natural en Q3.12
;   Entrada : R0 = m  (Q3.12, 0 < m <= 7.9998 = x7FFF)
;   Salida  : R0 = ln(m) (Q3.12, rango representable -8.0 .. 7.99)
;   Conserva R1-R7 (R6 no se usa). Sin .ORIG (se adjunta al programa).
;   m <= 0  -> R0 = x8000 (-8.0, ln no definido)
;   m muy chico (ln(m) < -8) -> R0 = x8000 (saturado)
;
; Metodo: CORDIC hiperbolico, modo vectorial
;   ln(m) = 2*atanh((m-1)/(m+1)) ; se usa x=(m/2)+0.5 , y=(m/2)-0.5
;   (la mitad de m+1 y m-1: la razon y/x es la misma pero x no desborda
;    para m hasta 7.99).
;   Convergencia CORDIC hiperbolico: |y/x| < 0.806  ->  m en [0.107, 9.37]
;   Para m < 0.5 se normaliza: m*2^k en [0.5,1) y ln(m)=ln(m*2^k)-k*ln2
;   y>0 : x=x-(y>>i) ; y=y-(x>>i) ; z=z+atanh(2^-i)
;   y<=0: x=x+(y>>i) ; y=y+(x>>i) ; z=z-atanh(2^-i)
;   Iteraciones i = 1,2,3,4,4,5,...,12
; =====================================================================

CORDIC_LOG_BASE
    ST   R1, guardado_r1
    ST   R2, guardado_r2
    ST   R3, guardado_r3
    ST   R4, guardado_r4
    ST   R5, guardado_r5
    ST   R7, guardado_r7

    ADD  R0, R0, #0
    BRnz LOG_MIN                 ; m <= 0 : no definido

    ; ---- normalizacion: llevar m a >= 0.5 (x0800) contando k
    AND  R5, R5, #0
    LD   R4, NEG_HALF
NORM    ADD  R1, R0, R4
    BRzp NORM_OK
    ADD  R0, R0, R0
    ADD  R5, R5, #1
    BRnzp NORM
NORM_OK ST   R5, var_k

    ; ---- x = m/2 + 0.5 ; y = m/2 - 0.5 ; z = 0
    AND  R5, R5, #0
    ADD  R5, R5, #1
    JSR  ASR                     ; R0 = m >> 1
    LD   R4, HALF_Q12
    ADD  R1, R0, R4              ; x
    NOT  R4, R4
    ADD  R4, R4, #1
    ADD  R2, R0, R4              ; y
    AND  R3, R3, #0              ; z
    AND  R4, R4, #0              ; indice de tabla

ITER    LEA  R5, SEQ_I
    ADD  R5, R5, R4
    LDR  R5, R5, #0              ; R5 = i (0 = fin)
    BRz  FIN

    ADD  R0, R1, #0
    JSR  ASR                     ; R0 = x >> i
    ST   R0, var_xs
    ADD  R0, R2, #0
    JSR  ASR                     ; R0 = y >> i  (ASR conserva R5)

    ADD  R2, R2, #0
    BRp  Y_POS

    ADD  R1, R1, R0              ; y<=0 : x += y>>i
    LD   R0, var_xs
    ADD  R2, R2, R0              ;        y += x>>i
    LEA  R5, LUT_ATANH
    ADD  R5, R5, R4
    LDR  R5, R5, #0
    NOT  R5, R5
    ADD  R5, R5, #1
    ADD  R3, R3, R5              ;        z -= atanh
    BRnzp NEXT

Y_POS   NOT  R0, R0              ; y>0 : x -= y>>i
    ADD  R0, R0, #1
    ADD  R1, R1, R0
    LD   R0, var_xs
    NOT  R0, R0
    ADD  R0, R0, #1
    ADD  R2, R2, R0              ;       y -= x>>i
    LEA  R5, LUT_ATANH
    ADD  R5, R5, R4
    LDR  R5, R5, #0
    ADD  R3, R3, R5              ;       z += atanh

NEXT    ADD  R4, R4, #1
    BRnzp ITER

FIN     ADD  R3, R3, R3          ; 2*z = ln(m*2^k)
    LD   R5, var_k
    BRz  FIN_OK
    ADD  R1, R5, #-11
    BRzp LOG_MIN                 ; k >= 11 : ln < -8, satura
    LD   R1, LN2_Q12
    NOT  R1, R1
    ADD  R1, R1, #1              ; -ln2
RESTA   ADD  R3, R3, R1          ; ln(m) = ln(m*2^k) - k*ln2
    ADD  R5, R5, #-1
    BRp  RESTA
FIN_OK  ST   R3, resultado
    BRnzp LOG_RET

LOG_MIN LD   R3, MIN_Q12
    ST   R3, resultado

LOG_RET LD   R0, resultado
    LD   R1, guardado_r1
    LD   R2, guardado_r2
    LD   R3, guardado_r3
    LD   R4, guardado_r4
    LD   R5, guardado_r5
    LD   R7, guardado_r7
    RET

; ---------------------------------------------------------------------
; ASR: R0 = R0 >> R5 (1..15), redondeo hacia cero. Conserva R1-R5.
; ---------------------------------------------------------------------
ASR     ST   R1, asr_r1
    ST   R2, asr_r2
    ST   R3, asr_r3
    AND  R1, R1, #0              ; bandera de negativo
    ADD  R0, R0, #0
    BRzp A_POS
    NOT  R0, R0
    ADD  R0, R0, #1
    ADD  R1, R1, #1
A_POS   NOT  R3, R5
    ADD  R3, R3, #1
    ADD  R3, R3, #15
    ADD  R3, R3, #1              ; 16 - n iteraciones
    AND  R2, R2, #0
A_LOOP  ADD  R2, R2, R2
    ADD  R0, R0, #0
    BRzp A_Z
    ADD  R2, R2, #1
A_Z     ADD  R0, R0, R0
    ADD  R3, R3, #-1
    BRp  A_LOOP
    ADD  R0, R2, #0
    ADD  R1, R1, #0
    BRz  A_END
    NOT  R0, R0
    ADD  R0, R0, #1
A_END   LD   R1, asr_r1
    LD   R2, asr_r2
    LD   R3, asr_r3
    RET

; ---------------------------------------------------------------------
; ZONA DE DATOS
; ---------------------------------------------------------------------
HALF_Q12  .FILL x0800            ; 0.5
NEG_HALF  .FILL xF800            ; -0.5
LN2_Q12   .FILL #2839            ; ln(2)*4096
MIN_Q12   .FILL x8000            ; -8.0
SEQ_I     .FILL #1
    .FILL #2
    .FILL #3
    .FILL #4
    .FILL #4                     ; repeticion obligatoria
    .FILL #5
    .FILL #6
    .FILL #7
    .FILL #8
    .FILL #9
    .FILL #10
    .FILL #11
    .FILL #12
    .FILL #0
LUT_ATANH                        ; atanh(2^-i)*4096
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
resultado   .FILL #0
var_k       .FILL #0
var_xs      .FILL #0
guardado_r1 .FILL #0
guardado_r2 .FILL #0
guardado_r3 .FILL #0
guardado_r4 .FILL #0
guardado_r5 .FILL #0
guardado_r7 .FILL #0
asr_r1      .FILL #0
asr_r2      .FILL #0
asr_r3      .FILL #0

.END
