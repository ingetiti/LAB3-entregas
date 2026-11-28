; =====================================================================
; SUBRUTINA CORDIC_LOG_BASE : logaritmo natural en Q3.12 (LC-X)
;   Entrada : R0 = m  (Q3.12, 0 < m <= 7.9998 = x7FFF)
;   Salida  : R0 = ln(m) (Q3.12, rango representable -8.0 .. 7.99)
;   Conserva R1-R7. Sin .ORIG (se adjunta al programa).
;   m <= 0  -> R0 = x8000 (-8.0, ln no definido)
;   m muy chico (ln(m) < -8) -> R0 = x8000 (saturado)
;
; Metodo: CORDIC hiperbolico, modo vectorial (el mismo del original)
;   ln(m) = 2*atanh((m-1)/(m+1)) ; x=(m/2)+0.5 , y=(m/2)-0.5 , z=0
;   Para m < 0.5 se normaliza: m*2^k en [0.5,1) y ln(m)=ln(m*2^k)-k*ln2
;   (k con CLZ; ln(m*2^k) con una llamada recursiva)
;   y>0 : x=x-(y>>i) ; y=y-(x>>i) ; z=z+atanh(2^-i)
;   y<=0: x=x+(y>>i) ; y=y+(x>>i) ; z=z-atanh(2^-i)
;   Iteraciones i = 1,2,3,4,4,5,...,12 ; >> redondea hacia cero
;   Cada entrada de la tabla es atanh(2^-i)*4096*16 + i: los
;   corrimientos por registro usan solo los 4 bits bajos (i).
; =====================================================================

CORDIC_LOG_BASE
        PUSH  R1, R2, R3, R4, R5, R7
        CLZ   R5, R0
        BRz   LOG_MIN           ; m < 0
        SUB   R5, R5, #4        ; k = clz - 4
        BRp   NORMALIZA         ; m < 0.5 (o m = 0)

        RSHFL R0, R0, #1        ; m/2
        MOVI  R7, #1
        LSHF  R7, R7, #11       ; 0.5
        ADD   R1, R0, R7        ; x = m/2 + 0.5
        AND   R3, R3, #0        ; z = 0
        MOVI  R4, #13           ; indice de tabla 13..1
        LEA   R5, LN2_Q12       ; tabla - 2
        SUB   R2, R0, R7        ; y = m/2 - 0.5 (fija N, Z, P)

ITER    BRnz  Y_NEG
        LDRX  R0, R5, R4        ; y>0 : R0 = atanh*16 + i
        RSHFL R7, R0, #4
        ADD   R3, R3, R7        ;       z += atanh
        RSHFA R7, R1, R0        ;       R7 = x>>i (x > 0)
        RSHFA R0, R2, R0        ;       R0 = y>>i
        SUB   R1, R1, R0        ;       x -= y>>i
        SUB   R2, R2, R7        ;       y -= x>>i (fija N, Z, P)
        LOOP  R4, ITER
        BR    FIN
Y_NEG   LDRX  R0, R5, R4        ; y<=0
        RSHFL R7, R0, #4
        SUB   R3, R3, R7        ;       z -= atanh
        RSHFA R7, R1, R0        ;       R7 = x>>i
        NEG   R2, R2            ;       R2 = -y
        RSHFL R0, R2, R0        ;       R0 = -y>>i (hacia cero)
        SUB   R1, R1, R0        ;       x += y>>i
        SUB   R2, R7, R2        ;       y += x>>i (fija N, Z, P)
        LOOP  R4, ITER

FIN     ADD   R0, R3, R3        ; 2*z = ln(m)
        POPR  R1, R2, R3, R4, R5, R7

NORMALIZA
        CMP   R5, #11
        BRzp  LOG_MIN           ; k >= 11 : ln < -8, satura
        LSHF  R0, R0, R5        ; m*2^k
        JSR   CORDIC_LOG_BASE   ; ln(m*2^k), conserva R5 = k
        LD    R7, LN2_Q12
        MUL   R5, R5, R7
        SUB   R0, R0, R5        ; ln(m) = ln(m*2^k) - k*ln2
        POPR  R1, R2, R3, R4, R5, R7

LOG_MIN MOVI  R0, #1
        LSHF  R0, R0, #15       ; x8000 = -8.0
        POPR  R1, R2, R3, R4, R5, R7

; ---------------------------------------------------------------------
; ZONA DE DATOS
; ---------------------------------------------------------------------
LN2_Q12 .FILL #2839             ; ln(2)*4096
; atanh(2^-i)*4096*16 + i, de la ultima iteracion a la primera
        .FILL x001C             ; i=12 : 1
        .FILL x002B             ; i=11 : 2
        .FILL x004A             ; i=10 : 4
        .FILL x0089             ; i=9  : 8
        .FILL x0108             ; i=8  : 16
        .FILL x0207             ; i=7  : 32
        .FILL x0406             ; i=6  : 64
        .FILL x0805             ; i=5  : 128
        .FILL x1004             ; i=4  : 256 (repeticion obligatoria)
        .FILL x1004             ; i=4  : 256
        .FILL x2033             ; i=3  : 515
        .FILL x4162             ; i=2  : 1046
        .FILL x8CA1             ; i=1  : 2250

        .END
