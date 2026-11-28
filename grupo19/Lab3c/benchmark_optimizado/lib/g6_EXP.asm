; EXP para la interfaz del Grupo 27 y el simulador - NUEVA ISA 16-BIT.
; Entrada: R0 en Q3.12 con signo. Salida: R0 en Q7.8 con signo.
; Conserva R1..R7. EST_EXP y NUM_ITER quedan en memoria.
; EST_EXP: 0 = normal, 1 = saturado, 2 = redondeado a cero.
; NUM_ITER: 6 en el calculo normal, 0 en saturacion detectada al entrar.
; CC refleja el resultado al retornar.
;
; Optimizaciones: PUSHM/POPR, SHL/LSR/RLC/RRC/SRLV/SHLV, ADC, NEG, SUB,
; MOVI/LI y empaquetado de 45 bits en REDONDEA sin bucle bit-a-bit.

EXP_Q3_12
        PUSHM {R1, R2, R3, R4, R5, R7}
        JSR G6_EXP_CALCULA
        STPC R1, EST_EXP
        STPC R2, NUM_ITER
        ADDI R0, R0, #0         ; CC refleja el resultado (POPR preserva flags)
        POPR {R1, R2, R3, R4, R5, R7}

EST_EXP   .BLKW #1
NUM_ITER  .BLKW #1

G6_EXP_CALCULA
        LEA R5, TRABAJO
        STW R7, R5, #0
        CLR R1
        STW R1, R5, #4
        STW R1, R5, #5
        STW R1, R5, #12
        ADDI R0, R0, #0
        BRn EXP_NEG
        LI R2, #19873
        CMP R0, R2
        BRgt EXP_SAT
        BR ESCALA
EXP_NEG
        INC R1
        STW R1, R5, #5
        NEG R0, R0              ; Magnitud sin signo, incluso x8000.

ESCALA
        ; De Q3.12 a escala 2^30: magnitud << 18.
        ; V0=0, V1=(magnitud << 3) mod 2^15, V2=bits 15..12.
        CLR R1
        STW R1, R5, #1
        LI R7, x7FFF
        SHL R1, R0, #3
        AND R1, R1, R7
        STW R1, R5, #2
        LSR R2, R0, #12
        STW R2, R5, #3

        ; Reducir |x| por restas de ln(2), sin division de hardware.
        ; ln(2)*2^30 = 744261118 -> LO = 1534, MI = 22713.
REDUCE
        LDW R0, R5, #1
        LDW R1, R5, #2
        LDW R2, R5, #3
        LI R3, #1534
        SUB R0, R0, R3
        BRzp REDUCE_MED
        DEC R1
REDUCE_MED
        LI R3, #22713
        SUB R1, R1, R3
        BRzp REDUCE_ALTO
        DEC R2
REDUCE_ALTO
        ADDI R2, R2, #0
        BRn REDUCE_SIGNO
        AND R0, R0, R7
        AND R1, R1, R7
        STW R0, R5, #1
        STW R1, R5, #2
        STW R2, R5, #3
        LDW R3, R5, #4
        INC R3
        STW R3, R5, #4
        BR REDUCE

REDUCE_SIGNO
        LDW R0, R5, #5
        BRz EXP_INICIA
        LDW R2, R5, #4
        NOT R2, R2              ; Si hay resto, k = -cociente - 1.
        LDW R0, R5, #1
        LDW R1, R5, #2
        ADD R3, R0, R1          ; Suma cero solo si ambas palabras son cero.
        BRnp REDUCE_COMP
        INC R2                  ; Resto cero: k = -cociente.
        BR REDUCE_GUARDA
REDUCE_COMP
        ; Residuo de x negativo: ln(2) - residuo de |x|.
        NEG R0, R0
        NEG R1, R1
        LI R3, #1534
        ADD R0, R0, R3
        BRzp REDUCE_COMP_MI
        DEC R1
REDUCE_COMP_MI
        LI R3, #22713
        ADD R1, R1, R3
        AND R0, R0, R7
        STW R0, R5, #1
        STW R1, R5, #2
REDUCE_GUARDA
        STW R2, R5, #4

EXP_INICIA
        ; E = 1 -> entero 2^30 -> palabras [0, 0, 1].
        CLR R0
        STW R0, R5, #6
        STW R0, R5, #7
        MOVI R0, #1
        STW R0, R5, #8
        MOVI R0, #4
        STW R0, R5, #11
        LEA R0, TABLA_D16
        STW R0, R5, #10
        BR EXP_PASO

EXP_PASO
        LDW R3, R5, #10         ; La tabla apunta a d=16; buscar desde la fila d=0.
        MOVI R4, #16
        SHL R4, R4, #2
        SUB R3, R3, R4
        CLR R7                  ; Mejor digito elegible hasta ahora.
        MOVI R2, #16            ; Probar los bits 16, 8, 4, 2 y 1.
EXP_BUSCA
        ADD R6, R7, R2          ; Probar si mejor + bit sigue siendo <= 16.
        ADDI R4, R6, #-16
        BRp EXP_BUSCA_NEXT
        SHL R4, R6, #2
        ADD R4, R3, R4          ; Dirección de tabla[j][candidato].
        LDW R0, R5, #1
        LDW R1, R5, #2
        LDW R6, R4, #0
        SUB R0, R0, R6
        LDW R6, R4, #1
        SBC R1, R1, R6
        BRn EXP_BUSCA_NEXT      ; La tabla supera el resto: conservar mejor.
        ADD R7, R7, R2
EXP_BUSCA_NEXT
        LSR R2, R2, #1
        BRnp EXP_BUSCA

        ; Restar una sola vez el valor del digito seleccionado.
        SHL R6, R7, #2
        ADD R6, R3, R6
        LDW R0, R5, #1
        LDW R1, R5, #2
        LDW R4, R6, #0
        SUB R0, R0, R4
        LDW R4, R6, #1
        SBC R1, R1, R4
        MOV R3, R7              ; Guardar digito en R3 para el producto.
        LI R7, x7FFF
        AND R0, R0, R7
        STW R0, R5, #1
        STW R1, R5, #2

        ; Producto E*d por sumas. d <= 16. R2:R1:R0 acumula.
        CLR R0
        CLR R1
        CLR R2
        ADDI R3, R3, #0
        BRz EXP_MULT_FIN
EXP_MULT
        LDW R4, R5, #6
        ADD R0, R0, R4
        BRzp EXP_MULT_MI
        AND R0, R0, R7
        INC R1
EXP_MULT_MI
        LDW R4, R5, #7
        ADD R1, R1, R4
        BRzp EXP_MULT_ALTO
        AND R1, R1, R7
        INC R2
EXP_MULT_ALTO
        LDW R4, R5, #8
        ADD R2, R2, R4
        DEC R3
        BRp EXP_MULT
EXP_MULT_FIN
        STW R0, R5, #13
        STW R1, R5, #14
        STW R2, R5, #15
        LDW R0, R5, #11         ; Dividir E*d por 2^(4*j) con redondeo.
        JSR REDONDEA

        ; Acumular E <- E + redondeo(E*d/2^(4*j)).
        LI R7, x7FFF
        LDW R3, R5, #6
        ADD R0, R0, R3
        BRzp EXP_SUMA_MI
        AND R0, R0, R7
        INC R1
EXP_SUMA_MI
        LDW R3, R5, #7
        ADD R1, R1, R3
        BRzp EXP_SUMA_ALTO
        AND R1, R1, R7
        INC R2
EXP_SUMA_ALTO
        LDW R3, R5, #8
        ADD R2, R2, R3
        STW R0, R5, #6
        STW R1, R5, #7
        STW R2, R5, #8
        LDW R3, R5, #12
        INC R3
        STW R3, R5, #12
        ADDI R3, R3, #-6
        BRz EXP_SALIDA
        LDW R0, R5, #10
        MOVI R1, #68            ; 17 constantes de 2 palabras = 34 palabras = 68 bytes.
        ADD R0, R0, R1
        STW R0, R5, #10
        LDW R0, R5, #11
        ADDI R0, R0, #4
        STW R0, R5, #11
        BR EXP_PASO

EXP_SALIDA
        ; Q7.8 = redondeo(E_entero / 2^(30-8-k)).
        STW R0, R5, #13
        STW R1, R5, #14
        STW R2, R5, #15
        LDW R0, R5, #4
        NEG R0, R0
        MOVI R1, #22
        ADD R0, R0, R1
        JSR REDONDEA
        ADD R3, R1, R2          ; Palabras altas distintas de cero: no cabe.
        BRnp EXP_SAT
        ADDI R0, R0, #0
        BRnp EXP_FIN            ; R1 ya contiene cero (estado normal).
        MOVI R1, #2
        BR EXP_FIN
EXP_SAT
        LI R0, x7FFF
        MOVI R1, #1
EXP_FIN
        LDW R2, R5, #12
        LDW R7, R5, #0
        RET

; REDONDEA: entero sin signo de 45 bits en TRABAJO[13..15] (limbos de 15 bits).
; R0 entra con n (1..44). Retorna V/2^n redondeado en R2:R1:R0 (15 bits c/u).
; Empaqueta a 3 palabras de 16 bits, desplaza (n-1) con SRLV/SHLV, suma 1,
; desplaza 1 bit final y re-empaqueta a limbos de 15 bits.
REDONDEA
        PUSHM {R7}
        DEC R0                  ; R0 = m = n - 1 (0..43)
        MOV R7, R0

        ; Empaquetar 3x15 bits (TRABAJO[13..15]) -> 3x16 bits en R2:R1:R0
        LDW R0, R5, #13         ; L0
        LDW R1, R5, #14         ; L1
        LDW R2, R5, #15         ; L2
        SHL R3, R1, #15
        OR R0, R0, R3           ; W0 = L0 | (L1 << 15)
        LSR R1, R1, #1
        SHL R3, R2, #14
        OR R1, R1, R3           ; W1 = (L1 >> 1) | (L2 << 14)
        LSR R2, R2, #2          ; W2 = L2 >> 2

        ; Saltos de 16 bits mientras m >= 16
RED_W16
        ADDI R7, R7, #-16
        BRn RED_W16_FIN
        MOV R0, R1
        MOV R1, R2
        CLR R2
        BR RED_W16
RED_W16_FIN
        ADDI R7, R7, #15
        INC R7                  ; Restaura m mod 16 (0..15)
        BRz RED_ROUND

        ; Desplazamiento variable de R2:R1:R0 por m bits (1..15)
        MOVI R3, #16
        SUB R3, R3, R7          ; rc = 16 - m
        SRLV R0, R0, R7
        SHLV R4, R1, R3
        OR R0, R0, R4
        SRLV R1, R1, R7
        SHLV R4, R2, R3
        OR R1, R1, R4
        SRLV R2, R2, R7

RED_ROUND
        ; Sumar 1 para redondeo y dividir entre 2 -> (V >> n) + bit_{n-1}
        CLR R3                  ; CLR preserva C luego de ADDI
        ADDI R0, R0, #1
        ADC R1, R1, R3
        ADC R2, R2, R3
        LSR R2, R2, #1
        RRC R1, R1
        RRC R0, R0

        ; Desempaquetar 3x16 bits (R2:R1:R0) -> 3x15 bits (R2:R1:R0)
        SHL R2, R2, #2
        LSR R3, R1, #14
        OR R2, R2, R3           ; L2 = (W2 << 2) | (W1 >> 14)

        SHL R1, R1, #1
        LSR R3, R0, #15
        OR R1, R1, R3
        LI R3, x7FFF
        AND R1, R1, R3          ; L1 = ((W1 << 1) | (W0 >> 15)) & x7FFF
        AND R0, R0, R3          ; L0 = W0 & x7FFF

        POPR {R7}

TRABAJO .BLKW #18

; Tabla de constantes. Cada constante se guarda como [bajo15, medio15].
; Las filas se guardan contiguas y el seleccionador empieza en d=16.
; j = 1
          .FILL x0000 ; d=0, bajo
          .FILL x0000 ; medio
          .FILL x4618 ; d=1, bajo
          .FILL x07C2 ; medio
          .FILL x41DC ; d=2, bajo
          .FILL x0F13 ; medio
          .FILL x1838 ; d=3, bajo
          .FILL x15FF ; medio
          .FILL x7BE4 ; d=4, bajo
          .FILL x1C8F ; medio
          .FILL x5CAC ; d=5, bajo
          .FILL x22CE ; medio
          .FILL x0BC2 ; d=6, bajo
          .FILL x28C3 ; medio
          .FILL x57F7 ; d=7, bajo
          .FILL x2E73 ; medio
          .FILL x23ED ; d=8, bajo
          .FILL x33E6 ; medio
          .FILL x77C8 ; d=9, bajo
          .FILL x391F ; medio
          .FILL x0F60 ; d=10, bajo
          .FILL x3E25 ; medio
          .FILL x65C8 ; d=11, bajo
          .FILL x42F9 ; medio
          .FILL x3EBD ; d=12, bajo
          .FILL x47A1 ; medio
          .FILL x2E67 ; d=13, bajo
          .FILL x4C1F ; medio
          .FILL x1FD1 ; d=14, bajo
          .FILL x5076 ; medio
          .FILL x5A4D ; d=15, bajo
          .FILL x54A8 ; medio
TABLA_D16 .FILL x05FE ; d=16, bajo
          .FILL x58B9 ; medio
; j = 2
          .FILL x0000 ; d=0, bajo
          .FILL x0000 ; medio
          .FILL x6015 ; d=1, bajo
          .FILL x007F ; medio
          .FILL x00AA ; d=2, bajo
          .FILL x00FF ; medio
          .FILL x623B ; d=3, bajo
          .FILL x017D ; medio
          .FILL x0546 ; d=4, bajo
          .FILL x01FC ; medio
          .FILL x6A44 ; d=5, bajo
          .FILL x0279 ; medio
          .FILL x11B0 ; d=6, bajo
          .FILL x02F7 ; medio
          .FILL x7C02 ; d=7, bajo
          .FILL x0373 ; medio
          .FILL x29B1 ; d=8, bajo
          .FILL x03F0 ; medio
          .FILL x1B31 ; d=9, bajo
          .FILL x046C ; medio
          .FILL x50F7 ; d=10, bajo
          .FILL x04E7 ; medio
          .FILL x4B76 ; d=11, bajo
          .FILL x0562 ; medio
          .FILL x0B1F ; d=12, bajo
          .FILL x05DD ; medio
          .FILL x1062 ; d=13, bajo
          .FILL x0657 ; medio
          .FILL x5BAE ; d=14, bajo
          .FILL x06D0 ; medio
          .FILL x6D71 ; d=15, bajo
          .FILL x0749 ; medio
          .FILL x4618 ; d=16, bajo
          .FILL x07C2 ; medio
; j = 3
          .FILL x0000 ; d=0, bajo
          .FILL x0000 ; medio
          .FILL x7FE0 ; d=1, bajo
          .FILL x0007 ; medio
          .FILL x7F80 ; d=2, bajo
          .FILL x000F ; medio
          .FILL x7EE0 ; d=3, bajo
          .FILL x0017 ; medio
          .FILL x7E00 ; d=4, bajo
          .FILL x001F ; medio
          .FILL x7CE1 ; d=5, bajo
          .FILL x0027 ; medio
          .FILL x7B81 ; d=6, bajo
          .FILL x002F ; medio
          .FILL x79E2 ; d=7, bajo
          .FILL x0037 ; medio
          .FILL x7803 ; d=8, bajo
          .FILL x003F ; medio
          .FILL x75E4 ; d=9, bajo
          .FILL x0047 ; medio
          .FILL x7385 ; d=10, bajo
          .FILL x004F ; medio
          .FILL x70E7 ; d=11, bajo
          .FILL x0057 ; medio
          .FILL x6E09 ; d=12, bajo
          .FILL x005F ; medio
          .FILL x6AEB ; d=13, bajo
          .FILL x0067 ; medio
          .FILL x678E ; d=14, bajo
          .FILL x006F ; medio
          .FILL x63F2 ; d=15, bajo
          .FILL x0077 ; medio
          .FILL x6015 ; d=16, bajo
          .FILL x007F ; medio
; j = 4
          .FILL x0000 ; d=0, bajo
          .FILL x0000 ; medio
          .FILL x4000 ; d=1, bajo
          .FILL x0000 ; medio
          .FILL x0000 ; d=2, bajo
          .FILL x0001 ; medio
          .FILL x3FFF ; d=3, bajo
          .FILL x0001 ; medio
          .FILL x7FFE ; d=4, bajo
          .FILL x0001 ; medio
          .FILL x3FFD ; d=5, bajo
          .FILL x0002 ; medio
          .FILL x7FFC ; d=6, bajo
          .FILL x0002 ; medio
          .FILL x3FFA ; d=7, bajo
          .FILL x0003 ; medio
          .FILL x7FF8 ; d=8, bajo
          .FILL x0003 ; medio
          .FILL x3FF6 ; d=9, bajo
          .FILL x0004 ; medio
          .FILL x7FF4 ; d=10, bajo
          .FILL x0004 ; medio
          .FILL x3FF1 ; d=11, bajo
          .FILL x0005 ; medio
          .FILL x7FEE ; d=12, bajo
          .FILL x0005 ; medio
          .FILL x3FEB ; d=13, bajo
          .FILL x0006 ; medio
          .FILL x7FE8 ; d=14, bajo
          .FILL x0006 ; medio
          .FILL x3FE4 ; d=15, bajo
          .FILL x0007 ; medio
          .FILL x7FE0 ; d=16, bajo
          .FILL x0007 ; medio
; j = 5
          .FILL x0000 ; d=0, bajo
          .FILL x0000 ; medio
          .FILL x0400 ; d=1, bajo
          .FILL x0000 ; medio
          .FILL x0800 ; d=2, bajo
          .FILL x0000 ; medio
          .FILL x0C00 ; d=3, bajo
          .FILL x0000 ; medio
          .FILL x1000 ; d=4, bajo
          .FILL x0000 ; medio
          .FILL x1400 ; d=5, bajo
          .FILL x0000 ; medio
          .FILL x1800 ; d=6, bajo
          .FILL x0000 ; medio
          .FILL x1C00 ; d=7, bajo
          .FILL x0000 ; medio
          .FILL x2000 ; d=8, bajo
          .FILL x0000 ; medio
          .FILL x2400 ; d=9, bajo
          .FILL x0000 ; medio
          .FILL x2800 ; d=10, bajo
          .FILL x0000 ; medio
          .FILL x2C00 ; d=11, bajo
          .FILL x0000 ; medio
          .FILL x3000 ; d=12, bajo
          .FILL x0000 ; medio
          .FILL x3400 ; d=13, bajo
          .FILL x0000 ; medio
          .FILL x3800 ; d=14, bajo
          .FILL x0000 ; medio
          .FILL x3C00 ; d=15, bajo
          .FILL x0000 ; medio
          .FILL x4000 ; d=16, bajo
          .FILL x0000 ; medio
; j = 6
          .FILL x0000 ; d=0, bajo
          .FILL x0000 ; medio
          .FILL x0040 ; d=1, bajo
          .FILL x0000 ; medio
          .FILL x0080 ; d=2, bajo
          .FILL x0000 ; medio
          .FILL x00C0 ; d=3, bajo
          .FILL x0000 ; medio
          .FILL x0100 ; d=4, bajo
          .FILL x0000 ; medio
          .FILL x0140 ; d=5, bajo
          .FILL x0000 ; medio
          .FILL x0180 ; d=6, bajo
          .FILL x0000 ; medio
          .FILL x01C0 ; d=7, bajo
          .FILL x0000 ; medio
          .FILL x0200 ; d=8, bajo
          .FILL x0000 ; medio
          .FILL x0240 ; d=9, bajo
          .FILL x0000 ; medio
          .FILL x0280 ; d=10, bajo
          .FILL x0000 ; medio
          .FILL x02C0 ; d=11, bajo
          .FILL x0000 ; medio
          .FILL x0300 ; d=12, bajo
          .FILL x0000 ; medio
          .FILL x0340 ; d=13, bajo
          .FILL x0000 ; medio
          .FILL x0380 ; d=14, bajo
          .FILL x0000 ; medio
          .FILL x03C0 ; d=15, bajo
          .FILL x0000 ; medio
          .FILL x0400 ; d=16, bajo
          .FILL x0000 ; medio
        .END
