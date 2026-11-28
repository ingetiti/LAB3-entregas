; EXP para la interfaz del Grupo 27 (LC-X).
; Entrada: R0 en Q3.12 con signo. Salida: R0 = e^x en Q7.8 con signo.
; Conserva R1, R2, R3, R4, R5 y R7. R6 solo se usa como pila.
; EXP_Q3_12 es el simbolo usado por .EXTERNAL g6_EXP-EXP_Q3_12.
; Ejemplo: R0=x3000 (3) -> R0=x1416 (5142/256 = 20.0859375).
; Otro ejemplo: R0=x1000 (1) -> R0=x02B8 (696/256 = 2.71875).
; CC refleja el resultado al retornar.
;
; El mismo algoritmo que el original, con escala interna 2^30:
;  1. x = k*ln(2) + r, restando (o sumando, si x < 0) ln(2) hasta pasar
;     de signo. Se trabaja con x*2^17 y ln(2)/2 para caber en 32 bits.
;  2. Seis pasos de base 16: en el paso j se elige el mayor d con
;     T[j][d] <= r, r -= T[j][d] y E += redondeo(E*d / 16^j), E = 2^30.
;  3. Q7.8 = redondeo(E / 2^(22-k)); 0 si k <= -10. x > 19873 satura.
; La tabla es la del original multiplicada por 16^(j-1): asi r se
; multiplica por 16 en cada paso y el digito siempre esta en los bits
; 29..26 de r (estimacion d0 = r >> 26, luego se compara con T[d0+1]).
; Las filas 5 y 6 quedan iguales con esa escala: T[d] = d * 2^26. Tras
; el paso 4, r < 2^26, asi que los digitos 5 y 6 son los bits 25..18 de
; r (bits 9..2 de la palabra alta) y no hace falta buscarlos en la tabla.
; Los digitos se juntan en R0 de a cuatro bits y despues se hacen las
; seis actualizaciones de E, en el mismo orden.

EXP_Q3_12
        PUSH  R1, R2, R3, R4, R5, R7
        LD    R3, LN_BAJO       ; R4:R3 = ln(2)/2 * 2^30
        LD    R4, LN_ALTO
        AND   R2, R2, #0        ; R1:R2 = x * 2^17
        LSHF  R1, R0, #1        ; C = signo de x
        BRNC  POSITIVO

        MOVI  R5, #-7
NEG_LAZO
        ADD   R2, R2, R3        ; sumar ln(2) hasta que haya acarreo
        ADC   R1, R1, R4
        BRC   NEG_FIN
        LOOP  R5, NEG_LAZO
NEG_FIN NEG   R5, R5            ; s = 22 - k - 16 = 6 + sumas
        BR    REDUCIDO

POSITIVO
        MOVI  R5, #7
POS_LAZO
        SUB   R2, R2, R3        ; restar ln(2) hasta que haya prestamo
        SBC   R1, R1, R4
        BRNC  POS_FIN
        LOOP  R5, POS_LAZO
        LD    R0, MAXIMO        ; 7 restas: x > 19873, satura
        POPR  R1, R2, R3, R4, R5, R7
POS_FIN ADD   R2, R2, R3        ; deshacer la ultima resta
        ADC   R1, R1, R4
        SUB   R5, R5, #1        ; s = 6 - restas

REDUCIDO
        ADD   R2, R2, R2        ; r = 2 * resto (escala 2^30)
        ADC   R1, R1, R1
        PUSH  R5
        LEA   R5, FILA1         ; R5 = fila, R7 = pasos, R0 = digitos
        MOVI  R7, #4
        BR    PASO

; ---- pasos: R1:R2 = r, R4 = puntero a T[j][d], R3 temporal ----
ARRIBA  RSHFL R3, R2, #12       ; r = r * 16
        LSHF  R2, R2, #4
        LSHF  R1, R1, #4
        OR    R1, R1, R3
        LDR   R3, R5, #-1       ; distancia a la fila siguiente
        ADD   R5, R5, R3
PASO    RSHFL R3, R1, #10       ; d0 = r >> 26
        LSHF  R0, R0, #4
        OR    R0, R0, R3
        LSHF  R4, R3, #2
        ADD   R4, R4, R5        ; R4 = &T[j][d0]
BUSCA   LDR   R3, R4, #3        ; r >= T[j][d+1]?
        CMP   R1, R3
        BRn   RESTA
        BRp   MAS
        LDR   R3, R4, #2
        CMP   R2, R3
        BRNC  RESTA
MAS     ADD   R4, R4, #4        ; d = d + 1
        ADD   R0, R0, #1
        BR    BUSCA
RESTA   LDR   R3, R4, #0        ; r = r - T[j][d]
        SUB   R2, R2, R3
        LDR   R3, R4, #1
        SBC   R1, R1, R3
        LOOP  R7, ARRIBA

; ---- E += redondeo(E*d/16^j); R2:R1 = E, R0 = M = d << (16-4j) ----
        RSHFL R4, R1, #2        ; pasos 5 y 6: d5 d6 = bits 25..18 de r
        PUSH  R4
        ADD   R3, R0, #0        ; R3 = d1 d2 d3 d4
        AND   R1, R1, #0        ; E = 2^30
        MOVI  R2, #1
        LSHF  R2, R2, #14
        MOVI  R7, #15
        LSHF  R7, R7, #12       ; mascara xF000
CUENTA1 AND   R0, R3, R7
        AND   R4, R3, R7
        MULQU R4, R1, #16       ; R4 = alta(Elo*M), C = bit de redondeo
        MULW  R5, R0, R2        ; R5:R0 = Ehi*M
        ADC   R0, R0, R4
        ADC   R5, R5, #0        ; R5:R0 = redondeo(E*M / 2^16)
        ADD   R1, R1, R0
        ADC   R2, R2, R5
        RSHFL R7, R7, #4
        BRnp  CUENTA1
        POP   R3
        LSHF  R3, R3, #8        ; R3 = d5 d6 0 0, M = d << 12 y d << 8
        LD    R7, MASCARA2      ; xF080: el bit 3 corta tras dos vueltas
CUENTA2 AND   R0, R3, R7
        AND   R4, R3, R7
        MULQU R4, R1, #16
        MULW  R5, R0, R2
        ADD   R0, R0, R4        ; R5:R0 = E*M / 2^16
        ADC   R5, R5, #0
        LSHF  R0, R0, #1        ; redondeo(E*M / 2^32)
        ADC   R5, R5, #0
        ADD   R1, R1, R5
        ADC   R2, R2, #0
        RSHFL R7, R7, #4
        BRNC  CUENTA2

; ---- Q7.8 = redondeo(E / 2^(16+s)); E < 2^31, nunca pasa de x7FFF ----
        POP   R5
        CMP   R5, #15
        BRp   CERO              ; k <= -10: redondea a 0
        LSHF  R4, R1, #1        ; C = bit 15 de Elo (para s = 0)
        RSHFL R0, R2, R5
        ADC   R0, R0, #0
        POPR  R1, R2, R3, R4, R5, R7
CERO    AND   R0, R0, #0
        POPR  R1, R2, R3, R4, R5, R7

LN_BAJO   .FILL x42FF           ; ln(2)/2 * 2^30 = 372130559
LN_ALTO   .FILL x162E
MAXIMO    .FILL x7FFF
MASCARA2  .FILL xF080

; Tabla: T[j][d] * 16^(j-1) en [bajo, alto], d = 0..16, j = 1..4.
; j = 1
          .FILL #70      ; distancia a la fila siguiente
FILA1     .FILL x0000 ; d=0
          .FILL x0000
          .FILL x4618 ; d=1
          .FILL x03E1
          .FILL xC1DC ; d=2
          .FILL x0789
          .FILL x9838 ; d=3
          .FILL x0AFF
          .FILL xFBE4 ; d=4
          .FILL x0E47
          .FILL x5CAC ; d=5
          .FILL x1167
          .FILL x8BC2 ; d=6
          .FILL x1461
          .FILL xD7F7 ; d=7
          .FILL x1739
          .FILL x23ED ; d=8
          .FILL x19F3
          .FILL xF7C8 ; d=9
          .FILL x1C8F
          .FILL x8F60 ; d=10
          .FILL x1F12
          .FILL xE5C8 ; d=11
          .FILL x217C
          .FILL xBEBD ; d=12
          .FILL x23D0
          .FILL xAE67 ; d=13
          .FILL x260F
          .FILL x1FD1 ; d=14
          .FILL x283B
          .FILL x5A4D ; d=15
          .FILL x2A54
          .FILL x85FE ; d=16
          .FILL x2C5C
; j = 2
          .FILL #70      ; distancia a la fila siguiente
FILA2     .FILL x0000 ; d=0
          .FILL x0000
          .FILL x0150 ; d=1
          .FILL x03FE
          .FILL x0AA0 ; d=2
          .FILL x07F8
          .FILL x23B0 ; d=3
          .FILL x0BEE
          .FILL x5460 ; d=4
          .FILL x0FE0
          .FILL xA440 ; d=5
          .FILL x13CE
          .FILL x1B00 ; d=6
          .FILL x17B9
          .FILL xC020 ; d=7
          .FILL x1B9F
          .FILL x9B10 ; d=8
          .FILL x1F82
          .FILL xB310 ; d=9
          .FILL x2361
          .FILL x0F70 ; d=10
          .FILL x273D
          .FILL xB760 ; d=11
          .FILL x2B14
          .FILL xB1F0 ; d=12
          .FILL x2EE8
          .FILL x0620 ; d=13
          .FILL x32B9
          .FILL xBAE0 ; d=14
          .FILL x3685
          .FILL xD710 ; d=15
          .FILL x3A4E
          .FILL x6180 ; d=16
          .FILL x3E14
; j = 3
          .FILL #68      ; distancia a la fila siguiente (FILA4 no lleva distancia)
FILA3     .FILL x0000 ; d=0
          .FILL x0000
          .FILL xE000 ; d=1
          .FILL x03FF
          .FILL x8000 ; d=2
          .FILL x07FF
          .FILL xE000 ; d=3
          .FILL x0BFE
          .FILL x0000 ; d=4
          .FILL x0FFE
          .FILL xE100 ; d=5
          .FILL x13FC
          .FILL x8100 ; d=6
          .FILL x17FB
          .FILL xE200 ; d=7
          .FILL x1BF9
          .FILL x0300 ; d=8
          .FILL x1FF8
          .FILL xE400 ; d=9
          .FILL x23F5
          .FILL x8500 ; d=10
          .FILL x27F3
          .FILL xE700 ; d=11
          .FILL x2BF0
          .FILL x0900 ; d=12
          .FILL x2FEE
          .FILL xEB00 ; d=13
          .FILL x33EA
          .FILL x8E00 ; d=14
          .FILL x37E7
          .FILL xF200 ; d=15
          .FILL x3BE3
          .FILL x1500 ; d=16
          .FILL x3FE0
; j = 4 (la ultima: no lleva distancia)
FILA4     .FILL x0000 ; d=0
          .FILL x0000
          .FILL x0000 ; d=1
          .FILL x0400
          .FILL x0000 ; d=2
          .FILL x0800
          .FILL xF000 ; d=3
          .FILL x0BFF
          .FILL xE000 ; d=4
          .FILL x0FFF
          .FILL xD000 ; d=5
          .FILL x13FF
          .FILL xC000 ; d=6
          .FILL x17FF
          .FILL xA000 ; d=7
          .FILL x1BFF
          .FILL x8000 ; d=8
          .FILL x1FFF
          .FILL x6000 ; d=9
          .FILL x23FF
          .FILL x4000 ; d=10
          .FILL x27FF
          .FILL x1000 ; d=11
          .FILL x2BFF
          .FILL xE000 ; d=12
          .FILL x2FFE
          .FILL xB000 ; d=13
          .FILL x33FE
          .FILL x8000 ; d=14
          .FILL x37FE
          .FILL x4000 ; d=15
          .FILL x3BFE
          .FILL x0000 ; d=16
          .FILL x3FFE
        .END
