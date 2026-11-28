;=====================================================================
; SUBRUTINA: SEN_CHEB_PADE (Seno por aproximación racional Chebyshev-Padé)
;
;   Fórmula:  sen(x) ~= x * (1 - A*u) / (1 + B*u),  con u = x^2 / 2
;             A = 3672 / 16384 (0.2241), B = 1814 / 16384 (0.1107)
;   Entrada:  R0 = ángulo x en radianes (formato Q3.12 con signo)
;   Salida:   R0 = sen(x) en formato Q1.14 con signo (1.0 = 16384 = x4000)
;   Conserva: R1-R5 y R7; no utiliza R6.
;=====================================================================
SEN_CHEB_PADE:
        ST      R1, SN_R1
        ST      R2, SN_R2
        ST      R3, SN_R3
        ST      R4, SN_R4
        ST      R5, SN_R5
        ST      R7, SN_R7

        ; ---- 1. Reducción de rango (Q3.12) a [0, pi/2] y signo ----
        AND     R4, R4, #0          ; R4 = bandera de signo (0 = +, 1 = -)
        ADD     R0, R0, #0
        BRzp    SN_ABS_OK
        NOT     R0, R0
        ADD     R0, R0, #1          ; R0 = |x| (si x = -8.0 -> x8000 = 32768 sin signo)
        ADD     R4, R4, #1          ; signo = negativo

SN_ABS_OK:
        ; Reducir |x| si supera 2*pi (25736)
        LD      R1, SN_N2PI         ; -25736
        ADD     R2, R0, R1          ; |x| - 2*pi
        BRnz    SN_CHK_PI
        ADD     R0, R2, #0          ; |x| -= 2*pi -> [0, 2*pi]

SN_CHK_PI:
        ; Si |x| > pi (12868), restar pi e invertir signo
        LD      R1, SN_NPI          ; -12868
        ADD     R2, R0, R1          ; |x| - pi
        BRnz    SN_CHK_HALFPI
        ADD     R0, R2, #0          ; |x| -= pi -> [0, pi]
        XOR     R4, R4, #1          ; Invertir bandera de signo

SN_CHK_HALFPI:
        ; Si |x| > pi/2 (6434), reflejar respecto a pi: x_ref = pi - |x|
        LD      R1, SN_NHALFPI      ; -6434
        ADD     R2, R0, R1          ; |x| - pi/2
        BRnz    SN_TO_Q14
        LD      R1, SN_PI           ; +12868
        NOT     R0, R0
        ADD     R0, R0, #1
        ADD     R0, R1, R0          ; R0 = pi - |x| -> [0, pi/2]

SN_TO_Q14:
        ; Convertir x en [0, pi/2] de Q3.12 a Q1.14 (<< 2)
        LSH     R0, R0, #2          ; R0 = x en Q1.14 (0..25736)
        BRz     SN_EXIT             ; Si x == 0 -> sen(0) = 0
        ST      R4, SN_SIGN
        ST      R0, SN_X
        BR      SN_KERNEL

SN_ONE:         .FILL #16384        ; 1.0 en Q1.14 (2^14)
SN_NEG_ONE:     .FILL #-16384       ; -1.0 en Q1.14
SN_HALF:        .FILL #8192         ; 0.5 en Q1.14 (2^13, redondeo)
SN_N2PI:        .FILL #-25736       ; -2*pi en Q3.12
SN_PI:          .FILL #12868        ; +pi en Q3.12
SN_NPI:         .FILL #-12868       ; -pi en Q3.12
SN_NHALFPI:     .FILL #-6434        ; -pi/2 en Q3.12
SN_A:           .FILL #3672         ; A = 0.2241 en Q1.14
SN_B:           .FILL #1814         ; B = 0.1107 en Q1.14
SN_SIGN:        .FILL #0
SN_X:           .FILL #0
SN_NUM:         .FILL #0
SN_U:           .FILL #0
SN_DEN:         .FILL #0
SN_R1:          .FILL #0
SN_R2:          .FILL #0
SN_R3:          .FILL #0
SN_R4:          .FILL #0
SN_R5:          .FILL #0
SN_R7:          .FILL #0

SN_KERNEL:
        ; ---- 2. Núcleo racional Chebyshev-Padé (Q1.14) ----
        ; 2a) u = (x * x + 2^14) >> 15  (x^2 / 2 redondeado en Q1.14)
        ADD     R1, R0, #0
        MUL     R2, R0, R1
        MULH    R3, R0, R1
        LD      R1, SN_ONE          ; 16384 = 2^14 (redondeo para >> 15)
        AND     R5, R5, #0
        ADD     R2, R2, R1
        ADC     R3, R3, R5          ; Propagar acarreo a la palabra alta
        LSH     R3, R3, #1          ; Bits altos desplazados para >> 15
        RSH     R2, R2, #15         ; Bit 15 de la palabra baja pasa a bit 0
        OR      R4, R3, R2          ; R4 = u en Q1.14
        ST      R4, SN_U

        ; 2b) num = 1.0 - ((A * u + 2^13) >> 14)
        ADD     R0, R4, #0
        LD      R1, SN_A            ; A = 3672
        MUL     R2, R0, R1
        MULH    R3, R0, R1
        LD      R1, SN_HALF         ; 8192 = 2^13 (redondeo para >> 14)
        AND     R5, R5, #0
        ADD     R2, R2, R1
        ADC     R3, R3, R5
        LSH     R3, R3, #2          ; Bits altos para >> 14
        RSH     R2, R2, #14         ; Bits bajos [15:14] -> [1:0]
        OR      R2, R3, R2          ; R2 = A * u en Q1.14

        LD      R1, SN_ONE          ; 16384 (1.0 en Q1.14)
        NOT     R2, R2
        ADD     R2, R2, #1
        ADD     R2, R1, R2          ; R2 = num = 1 - A*u
        ST      R2, SN_NUM

        ; 2c) den = 1.0 + ((B * u + 2^13) >> 14)
        LD      R0, SN_U
        LD      R1, SN_B            ; B = 1814
        MUL     R2, R0, R1
        MULH    R3, R0, R1
        LD      R1, SN_HALF         ; 8192 = 2^13
        AND     R5, R5, #0
        ADD     R2, R2, R1
        ADC     R3, R3, R5
        LSH     R3, R3, #2
        RSH     R2, R2, #14
        OR      R2, R3, R2          ; R2 = B * u en Q1.14

        LD      R1, SN_ONE          ; 16384
        ADD     R4, R1, R2          ; R4 = den = 1 + B*u
        ST      R4, SN_DEN

        ; 2d) ratio = round((num / den) * 2^14), generando los 14 bits fraccionarios.
        LD      R0, SN_NUM
        LD      R1, SN_DEN
        ADD     R3, R0, #0          ; R3 = resto inicial
        AND     R2, R2, #0          ; R2 = cociente Q1.14
        AND     R5, R5, #0
        ADD     R5, R5, #7
        ADD     R5, R5, #7          ; 14 iteraciones
        NOT     R4, R1
        ADD     R4, R4, #1          ; R4 = -den
SN_DIV_FRAC_LOOP:
        LSH     R3, R3, #1          ; candidato = resto * 2
        ADD     R0, R3, #0
        BRn     SN_DIV_FRAC_GE      ; candidato >= 32768 > den
        DIV     R0, R0, R1          ; cociente del paso (0 o 1)
        MOD     R3, R3, R1          ; resto del paso
        BR      SN_DIV_FRAC_NEXT
SN_DIV_FRAC_GE:
        ADD     R3, R3, R4          ; candidato - den, sin desbordar
        AND     R0, R0, #0
        ADD     R0, R0, #1
SN_DIV_FRAC_NEXT:
        LSH     R2, R2, #1
        ADD     R2, R2, R0
        ADD     R5, R5, #-1
        BRp     SN_DIV_FRAC_LOOP

        ; Redondear según el resto que quedó luego de obtener los 14 bits.
        LSH     R3, R3, #1
        ADD     R0, R3, #0
        BRn     SN_DIV_FRAC_ROUND
        ADD     R0, R3, R4
        BRc     SN_DIV_FRAC_ROUND
        BR      SN_DIV_FRAC_DONE
SN_DIV_FRAC_ROUND:
        ADD     R2, R2, #1
SN_DIV_FRAC_DONE:

        ; 2e) sen = (x * ratio + 2^13) >> 14
        LD      R0, SN_X
        ADD     R1, R2, #0          ; ratio devuelto por la división
        MUL     R2, R0, R1
        MULH    R3, R0, R1
        LD      R1, SN_HALF         ; 8192 = 2^13
        AND     R5, R5, #0
        ADD     R2, R2, R1
        ADC     R3, R3, R5
        LSH     R3, R3, #2
        RSH     R2, R2, #14
        OR      R0, R3, R2          ; R0 = |sen(x)| en Q1.14

        ; Saturar a 1.0 (16384) si supera 16384
        LD      R1, SN_NEG_ONE      ; -16384
        ADD     R1, R0, R1
        BRnz    SN_APLICAR_SIGNO
        LD      R0, SN_ONE          ; 16384

        ; ---- 3. Aplicar signo del cuadrante ----
SN_APLICAR_SIGNO:
        LD      R1, SN_SIGN
        BRz     SN_EXIT
        NOT     R0, R0
        ADD     R0, R0, #1

        ; ---- 4. Restaurar registros del llamador ----
SN_EXIT:
        LD      R1, SN_R1
        LD      R2, SN_R2
        LD      R3, SN_R3
        LD      R4, SN_R4
        LD      R5, SN_R5
        LD      R7, SN_R7
        ADD     R0, R0, #0          ; Actualizar CC según resultado en R0
        RET

.END