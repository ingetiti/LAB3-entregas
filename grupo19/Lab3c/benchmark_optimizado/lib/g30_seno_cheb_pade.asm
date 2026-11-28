; =====================================================================
;  LAB 3 - NUEVA ISA 16-BIT : sen(x)  entrada Q3.12 -> salida Q1.14 (radianes)
;
;        sen(x) ~= x * (1 - A*u) / (1 + B*u)        u = x^2 / 2
;
;  x reducido a [0, pi/2].  A = 3672/16384 (0.2241), B = 1814/16384 (0.1107).
;  ENTRADA : R0 = angulo en Q3.12 (1.0 = 4096, x en [-8, 8)).
;  SALIDA  : R0 = sen(x) en Q1.14 (1.0 = 16384).
;  Preserva R1..R7.
;  Optimizaciones: PUSHM/POPR, RLC/SHL/LSR de 32 bits con acarreo real,
;  NEG, SUB, CMP, LI/MOVI sin constantes en memoria ni variables temporales.
; =====================================================================

SEN_CHEB_PADE
        PUSHM {R1, R2, R3, R4, R5, R7}

        ; ---- 1) Reduccion de rango (Q3.12) a [0, pi/2] ---------------
        CLR R4                  ; R4 = bandera de signo (1 = negativo)
        ADDI R0, R0, #0
        BRzp SN_P1
        LI R1, #-32768
        CMP R0, R1
        BRz SN_MIN
        NEG R0, R0              ; R0 = |x|
        INC R4
        BR SN_P1
SN_MIN
        LI R0, #5836            ; |x| - 2pi, plegado a pi/2 para x = -8
        INC R4
        BR SN_P4
SN_P1
        LI R1, #25736           ; 2*pi (Q3.12)
        SUB R2, R0, R1          ; |x| - 2pi (en [-25736, 7032])
        BRnz SN_P2
        MOV R0, R2              ; |x| -= 2pi -> [0, 2pi]
SN_P2
        LI R1, #12868           ; pi (Q3.12)
        SUB R2, R0, R1          ; |x| - pi
        BRnz SN_P3
        MOV R0, R2              ; |x| -= pi -> [0, pi]
        MOVI R2, #1
        XOR R4, R4, R2          ; invertir signo
SN_P3
        LSR R1, R1, #1          ; R1 = pi/2 = 6434
        CMP R0, R1              ; |x| - pi/2
        BRle SN_P4
        LI R1, #12868
        SUB R0, R1, R0          ; pi - |x| -> [0, pi/2]
SN_P4
        SHL R0, R0, #2          ; Q3.12 -> Q1.14
        BRz SN_EXIT             ; sen(0) = 0

        ; ---- 2) Nucleo racional --------------------------------------
        PUSHM {R0, R4}          ; guardar x y signo en pila
        MOV R1, R0
        JSR MULS15              ; u = x*x/2 (redondeado)
        PUSHM {R0}              ; guardar u en pila

        LI R1, #3672            ; A = 0.2241
        JSR MULU_Q14            ; A*u
        LI R1, #16384
        SUB R0, R1, R0          ; num = 1 - A*u
        POPM {R1}               ; R1 = u
        PUSHM {R0}              ; guardar num en pila

        MOV R0, R1
        LI R1, #1814            ; B = 0.1107
        JSR MULU_Q14            ; B*u
        LI R1, #16384
        ADD R1, R0, R1          ; den = 1 + B*u
        POPM {R0}               ; R0 = num

        JSR DIVF                ; ratio = num/den (<= 1.0)
        POPM {R1, R4}           ; R1 = x, R4 = signo
        PUSHM {R4}
        JSR MULU_Q14            ; sen = x * ratio
        POPM {R4}

        LI R1, #16384           ; saturar a 1.0
        CMP R0, R1
        BRle SN_SGN
        MOV R0, R1

        ; ---- 3) Signo ------------------------------------------------
SN_SGN
        ADDI R4, R4, #0
        BRz SN_EXIT
        NEG R0, R0

SN_EXIT
        POPR {R1, R2, R3, R4, R5, R7}

; =====================================================================
; MULS15  : R0 = (R0*R1 + 2^14) >> 15   (0 <= R0,R1 <= 32767)
; MULU_Q14: R0 = (R0*R1 + 2^13) >> 14   (producto Q1.14 redondeado)
; Acumulador de 32 bits R3:R2 usando RLC y acarreo de ADD. Destruye R1-R5.
; =====================================================================
MULS15
        LI R5, #16384           ; redondeo = 2^14
        MOVI R4, #1             ; modo = 1 (>> 15)
        BR MU_START
MULU_Q14
        LI R5, #8192            ; redondeo = 2^13
        CLR R4                  ; modo = 0 (>> 14)
MU_START
        ADDI R1, R1, #0
        BRz MU_ZERO
        CLR R2                  ; acc_lo = 0
        CLR R3                  ; acc_hi = 0
        SHL R1, R1, #1          ; bit 14 -> bit 15
        PUSHM {R4}
        MOVI R4, #15
MU_LP
        SHL R2, R2, #1          ; acc <<= 1 (32 bits)
        RLC R3, R3
        SHL R1, R1, #1          ; bit 15 de R1 -> C
        BRnc MU_NB
        ADD R2, R2, R0          ; acc += a
        BRnc MU_NB
        INC R3
MU_NB
        DEC R4
        BRp MU_LP
        ADD R2, R2, R5          ; sumar redondeo
        BRnc MU_RS
        INC R3
MU_RS
        POPM {R4}
        ADDI R4, R4, #0
        BRz MU_Q14
        SHL R2, R2, #1          ; bit 15 de R2 -> C
        RLC R3, R3              ; (R3 << 1) | bit15(R2)
        MOV R0, R3
        RET
MU_Q14
        LSR R2, R2, #14
        SHL R3, R3, #2
        OR R0, R3, R2           ; (R3 << 2) | (R2 >> 14)
        RET
MU_ZERO
        CLR R0
        RET

; =====================================================================
; DIVF : R0 = R0 / R1 en Q1.14 (redondeado), con 0 < R0 <= R1 < 32768.
; Division restauradora de 14 pasos. Destruye R1-R4.
; CMP/BRc comparan sin signo, incluso cuando r<<1 supera 32767.
; =====================================================================
DIVF
        MOV R2, R0              ; r = n
        CLR R4                  ; q = 0
        MOVI R0, #14            ; contador
DV_LP
        SHL R4, R4, #1          ; q <<= 1
        SHL R2, R2, #1          ; r <<= 1
        CMP R2, R1              ; comparacion sin signo de r con d
        BRc DV_NS
        SUB R2, R2, R1
        INC R4
DV_NS
        DEC R0
        BRp DV_LP
        SHL R2, R2, #1          ; redondeo: 2r >= d ?
        CMP R2, R1
        BRc DV_NR
        INC R4
DV_NR
        MOV R0, R4
        RET

        .END
