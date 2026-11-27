; EXP para la interfaz del Grupo 27 y el simulador del Grupo 8.
; Entrada: R0 en Q3.12 con signo. Salida: R0 en Q7.8 con signo.
; Conserva R1, R2, R3, R4, R5, R6 y R7.
; EXP_Q3_12 es el simbolo usado por .EXTERNAL g6_EXP-EXP_Q3_12.
; El archivo contiene una subrutina y termina en .END.
; El programa principal aporta .ORIG, carga R0 y llama mediante JSR/JSRR.
;
; EST_EXP y NUM_ITER quedan en memoria, en lugar de devolverse en R1/R2.
; EST_EXP: 0 = normal, 1 = saturado, 2 = redondeado a cero.
; NUM_ITER: 6 en el calculo normal, 0 en saturacion detectada al entrar.
; Ejemplo: R0=x3000 (3) -> R0=x1416 (5142/256 = 20.0859375).
; Otro ejemplo: R0=x1000 (1) -> R0=x02B8 (696/256 = 2.71875).
; CC refleja el resultado al retornar. No hay TRAP ni HALT en la rutina.
;
; Aritmetica multiplicativa de base 16 con escala interna 2^30.
; Usa almacenamiento estatico: las llamadas deben ser secuenciales.
; La rutina no debe invocarse recursivamente ni desde una interrupcion
; mientras otra llamada a EXP esta en curso.
;
; TRABAJO usa R5 como base. Cada valor interno tiene tres palabras
; de 15 bits útiles.

EXP_Q3_12
        ST R1, G6_EXP_R1
        ST R2, G6_EXP_R2
        ST R3, G6_EXP_R3
        ST R4, G6_EXP_R4
        ST R5, G6_EXP_R5
        ST R6, G6_EXP_R6
        ST R7, G6_EXP_R7
        JSR G6_EXP_CALCULA
        ST R1, EST_EXP
        ST R2, NUM_ITER
        LD R1, G6_EXP_R1
        LD R2, G6_EXP_R2
        LD R3, G6_EXP_R3
        LD R4, G6_EXP_R4
        LD R5, G6_EXP_R5
        LD R6, G6_EXP_R6
        LD R7, G6_EXP_R7
        ADD R0, R0, #0
        RET

G6_EXP_R1 .BLKW #1
G6_EXP_R2 .BLKW #1
G6_EXP_R3 .BLKW #1
G6_EXP_R4 .BLKW #1
G6_EXP_R5 .BLKW #1
G6_EXP_R6 .BLKW #1
G6_EXP_R7 .BLKW #1
EST_EXP   .BLKW #1
NUM_ITER  .BLKW #1

G6_EXP_CALCULA
        LD R5, PTR_TRABAJO
        STR R7, R5, #0
        AND R1, R1, #0
        STR R1, R5, #4
        STR R1, R5, #5
        STR R1, R5, #12
        ADD R0, R0, #0
        BRn EXP_NEG
        LD R2, NEG_LIMITE
        ADD R2, R0, R2
        BRp EXP_SAT
        BRnzp ESCALA
EXP_NEG
        ADD R1, R1, #1
        STR R1, R5, #5
        NOT R0, R0
        ADD R0, R0, #1     ; Magnitud sin signo, incluso x8000.

ESCALA
        ; De Q3.12 a escala 2^30: magnitud << 18.
        ; V0=0, V1=(magnitud << 3) mod 2^15, V2=bits 15..12.
        AND R1, R1, #0
        STR R1, R5, #1
        SHL R1, R0, #3
        LD R7, MASK15
        AND R1, R1, R7
        STR R1, R5, #2
        LSR R2, R0, #12
        STR R2, R5, #3

        ; Reducir |x| por restas de ln(2), sin division de hardware.
        ; Si la resta de prueba es negativa se conserva el residuo anterior.
REDUCE
        LDR R0, R5, #1
        LDR R1, R5, #2
        LDR R2, R5, #3
        LD R3, NEG_LN_LO
        ADD R0, R0, R3
        BRzp REDUCE_MED
        ADD R1, R1, #-1
REDUCE_MED
        LD R3, NEG_LN_MI
        ADD R1, R1, R3
        BRzp REDUCE_ALTO
        ADD R2, R2, #-1
REDUCE_ALTO
        ADD R2, R2, #0
        BRn REDUCE_SIGNO
        AND R0, R0, R7
        AND R1, R1, R7
        STR R0, R5, #1
        STR R1, R5, #2
        STR R2, R5, #3
        LDR R3, R5, #4
        ADD R3, R3, #1
        STR R3, R5, #4
        BRnzp REDUCE

REDUCE_SIGNO
        LDR R0, R5, #5
        BRz EXP_INICIA
        LDR R2, R5, #4
        NOT R2, R2         ; Si hay resto, k = -cociente - 1.
        LDR R0, R5, #1
        LDR R1, R5, #2
        ADD R3, R0, R1    ; Suma cero solo si ambas palabras son cero.
        BRnp REDUCE_COMP
        ADD R2, R2, #1     ; Resto cero: k = -cociente.
        BRnzp REDUCE_GUARDA
REDUCE_COMP
        ; Residuo de x negativo: ln(2) - residuo de |x|.
        NOT R0, R0
        ADD R0, R0, #1
        NOT R1, R1
        ADD R1, R1, #1
        LD R3, LN_LO
        ADD R0, R0, R3
        BRzp REDUCE_COMP_MI
        ADD R1, R1, #-1
REDUCE_COMP_MI
        LD R3, LN_MI
        ADD R1, R1, R3
        AND R0, R0, R7
        STR R0, R5, #1
        STR R1, R5, #2
REDUCE_GUARDA
        STR R2, R5, #4

EXP_INICIA
        ; E = 1 -> entero 2^30 -> palabras [0, 0, 1].
        AND R0, R0, #0
        STR R0, R5, #6
        STR R0, R5, #7
        ADD R0, R0, #1
        STR R0, R5, #8
        ADD R0, R0, #3
        STR R0, R5, #11
        LD R0, PTR_D16
        STR R0, R5, #10
        BRnzp EXP_PASO

; Constantes de reduccion. ln(2)*2^30 redondeado = 744261118.
PTR_TRABAJO .FILL TRABAJO
NEG_LIMITE  .FILL #-19873
MASK15      .FILL x7FFF
PTR_D16     .FILL TABLA_D16
LN_LO       .FILL #1534
LN_MI       .FILL #22713
NEG_LN_LO   .FILL #-1534
NEG_LN_MI   .FILL #-22713
FILA_BYTES  .FILL #68
D16          .FILL #16
DELTA_D0     .FILL #-64

EXP_PASO
        ; Cada fila contiene umbrales crecientes. Buscar el mayor
        ; d con tabla[d] <= residuo, preservando los umbrales de LC-3.
        LDR R0, R5, #1
        LDR R1, R5, #2
        LDR R2, R5, #10            ; entrada d=16
        LDR R4, R2, #0
        SUB R4, R0, R4
        LDR R3, R2, #1
        SBC R3, R1, R3
        BRzp EXP_DIGITO16

        LD R3, DELTA_D0
        ADD R2, R2, R3            ; entrada d=0
        AND R7, R7, #0
        ADD R7, R7, #8
EXP_BUSCA
        SHL R6, R7, #2
        ADD R6, R2, R6
        LDR R4, R6, #0
        SUB R4, R0, R4
        LDR R3, R6, #1
        SBC R3, R1, R3
        BRn EXP_BUSCA_SIG
        ADD R2, R6, #0
EXP_BUSCA_SIG
        LSR R7, R7, #1
        BRp EXP_BUSCA

        LDR R3, R5, #10
        SUB R7, R3, R2
        LSR R7, R7, #2
        LD R3, D16
        SUB R7, R3, R7
        BRz EXP_ITERACION          ; d=0 deja E y el residuo intactos.
        LDR R4, R2, #0
        SUB R0, R0, R4
        LDR R4, R2, #1
        SBC R1, R1, R4
        BRnzp EXP_ACEPTA
EXP_DIGITO16
        LD R7, D16
        ADD R0, R4, #0
        ADD R1, R3, #0
EXP_ACEPTA
        LD R3, MASK15
        AND R0, R0, R3
        STR R0, R5, #1
        STR R1, R5, #2

        ; Producto por el dígito d. Se propaga el acarreo en base 2^15.
        LDR R4, R5, #6
        MULUW R0, R4, R7
        AND R2, R0, R3
        STR R2, R5, #13
        LSRW R0, R0, #15

        LDR R4, R5, #7
        MULUW R2, R4, R7
        ADD R2, R2, R0
        ADC R3, R3, R1
        LD R4, MASK15
        AND R0, R2, R4
        STR R0, R5, #14
        LSRW R2, R2, #15

        LDR R4, R5, #8
        MULUW R0, R4, R7
        ADD R2, R2, R0
        STR R2, R5, #15
        LDR R0, R5, #11    ; Dividir E*d por 2^(4*j) con redondeo.
        JSR REDONDEA

        ; Acumular E <- E + redondeo(E*d/2^(4*j)).
        LD R7, MASK15
        LDR R3, R5, #6
        ADD R0, R0, R3
        BRzp EXP_SUMA_MI
        AND R0, R0, R7
        ADD R1, R1, #1
EXP_SUMA_MI
        LDR R3, R5, #7
        ADD R1, R1, R3
        BRzp EXP_SUMA_ALTO
        AND R1, R1, R7
        ADD R2, R2, #1
EXP_SUMA_ALTO
        LDR R3, R5, #8
        ADD R2, R2, R3
        STR R0, R5, #6
        STR R1, R5, #7
        STR R2, R5, #8
EXP_ITERACION
        LDR R3, R5, #12
        ADD R3, R3, #1
        STR R3, R5, #12
        ADD R3, R3, #-6
        BRz EXP_SALIDA
        LDR R0, R5, #10
        LD R1, FILA_BYTES
        ADD R0, R0, R1     ; 17 entradas de dos palabras por fila.
        STR R0, R5, #10
        LDR R0, R5, #11
        ADD R0, R0, #4
        STR R0, R5, #11
        BRnzp EXP_PASO

EXP_SALIDA
        ; Q7.8 = redondeo(E_entero / 2^(30-8-k)).
        ; Si el último dígito fue cero, solo la memoria conserva E.
        LDR R0, R5, #6
        LDR R1, R5, #7
        LDR R2, R5, #8
        STR R0, R5, #13
        STR R1, R5, #14
        STR R2, R5, #15
        LDR R0, R5, #4
        NOT R0, R0
        ADD R0, R0, #1
        ADD R0, R0, #15
        ADD R0, R0, #7
        JSR REDONDEA
        ADD R3, R1, R2    ; Palabras altas distintas de cero: no cabe.
        BRnp EXP_SAT
        ADD R0, R0, #0
        BRnp EXP_FIN      ; R1 ya contiene cero (estado normal).
        ADD R1, R1, #2
        BRnzp EXP_FIN
EXP_SAT
        LD R0, MASK15
        AND R1, R1, #0
        ADD R1, R1, #1
EXP_FIN
        LDR R2, R5, #12
        LDR R7, R5, #0
        RET

; R0 = n (1..44). R2:R1:R0 = (V >> n) + bit(V, n-1),
; donde V se guarda en tres palabras de 15 bits en TRABAJO+13..15.
REDONDEA
        ST R7, RED_GUARDADO_R7
        ADD R7, R0, #-1
        LDR R0, R5, #13
        LDR R1, R5, #14
        LDR R2, R5, #15

        ; Descartar primero las palabras completas de 15 bits.
RED_PALABRA
        ADD R3, R7, #-15
        BRn RED_PARTE
        ADD R7, R3, #0
        ADD R0, R1, #0
        ADD R1, R2, #0
        AND R2, R2, #0
        BRnzp RED_PALABRA

RED_PARTE
        ; Desplazar los bits restantes con propagación entre palabras.
        AND R3, R3, #0
        ADD R3, R3, #15
        SUB R3, R3, R7
        LSR R0, R0, R7
        SHL R4, R1, R3
        OR R0, R0, R4
        LSR R1, R1, R7
        SHL R4, R2, R3
        OR R1, R1, R4
        LSR R2, R2, R7
        LD R4, MASK15
        AND R0, R0, R4
        AND R1, R1, R4

        ; El último bit descartado determina el redondeo hacia arriba.
        AND R7, R0, #1
        LSR R0, R0, #1
        SHL R3, R1, #14
        AND R3, R3, R4
        OR R0, R0, R3
        LSR R1, R1, #1
        SHL R3, R2, #14
        AND R3, R3, R4
        OR R1, R1, R3
        LSR R2, R2, #1
        ADD R0, R0, R7
        BRzp RED_RETORNO
        AND R0, R0, R4
        ADD R1, R1, #1
        BRzp RED_RETORNO
        AND R1, R1, R4
        ADD R2, R2, #1
RED_RETORNO
        LD R7, RED_GUARDADO_R7
        RET

TRABAJO .BLKW #16
RED_GUARDADO_R7 .BLKW #1

; Misma tabla del C. Cada constante se guarda como [bajo15, medio15].
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
