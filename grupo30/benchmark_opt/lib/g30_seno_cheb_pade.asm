; =====================================================================
;  LAB 3 - GRUPO 30 (OPTIMIZADA): sen(x) entrada Q3.12 -> salida Q1.14
;        sen(x) ~= x * (1 - A*u) / (1 + B*u)        u = x^2 / 2
;  Usa MULQ (#15, #14) y DIVQ (#14) nativos de la ISA de 16 bits.
; =====================================================================

SEN_CHEB_PADE
        PUSHM {R1, R2, R3, R4, R7}

        ; 1) Reduccion de rango (Q3.12) a [0, pi/2]
        MOVI R4, #0             ; bandera de signo (1 = negativo)
        CMP  R0, #0
        BRzp SN_P1
        NOT  R0, R0
        ADD  R0, R0, #1         ; |x| (x8000 = 32768)
        MOVI R4, #1
SN_P1   LD   R1, SN_N2PI
        ADD  R2, R0, R1         ; |x| - 2pi
        BRnz SN_P2
        ADD  R0, R2, #0
SN_P2   LD   R1, SN_PI
        CMP  R0, R1
        BRnz SN_P3
        SUB  R0, R0, R1         ; |x| -= pi
        XOR  R4, R4, #1         ; invertir signo
SN_P3   LD   R1, SN_HALFPI
        CMP  R0, R1
        BRnz SN_P4
        LD   R1, SN_PI
        SUB  R0, R1, R0         ; pi - |x|
SN_P4   SHL  R0, R0, #2         ; Q3.12 -> Q1.14
        BRz  SN_EXIT

        ; 2) Nucleo racional con MULQ y DIVQ nativos
        ADD  R3, R0, #0         ; R3 = x (Q1.14)
        MULQ R0, R0, #15        ; R0 = u = round(x * x / 2^15)
        ADD  R2, R0, #0         ; R2 = u
        LD   R1, SN_A
        MULQ R0, R1, #14        ; R0 = A * u (Q1.14)
        LD   R1, SN_ONE
        SUB  R0, R1, R0         ; R0 = num = 1 - A * u
        LD   R1, SN_B
        MULQ R2, R1, #14        ; R2 = B * u (Q1.14)
        LD   R1, SN_ONE
        ADD  R1, R2, R1         ; R1 = den = 1 + B * u
        DIVQ R0, R1, #14        ; R0 = ratio = round((num << 14) / den)
        MULQ R0, R3, #14        ; R0 = sen = round(ratio * x / 2^14)

        LD   R1, SN_ONE
        CMP  R0, R1
        BRnz SN_SGN
        ADD  R0, R1, #0         ; saturar a 1.0

        ; 3) Signo
SN_SGN  CMP  R4, #0
        BRz  SN_EXIT
        NEG  R0, R0

SN_EXIT POPM {R1, R2, R3, R4, R7}
        RET

SN_ONE     .FILL #16384
SN_N2PI    .FILL #-25736
SN_PI      .FILL #12868
SN_HALFPI  .FILL #6434
SN_A       .FILL #3672
SN_B       .FILL #1814

        .END
