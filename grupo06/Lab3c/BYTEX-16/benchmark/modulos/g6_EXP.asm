; Biblioteca EXP para BYTEX-16. Optimizacion del 26/11/2026.
; EXP optimizada para BYTEX-16: NO es codigo LC-3 original.
; Interfaz compatible con el menu del Grupo 27 adaptado a nuestra ISA.
; Usa SUB, MUL, MULU, SHL y SHR para reducir instrucciones ejecutadas.
; Entrada: R0 en Q3.12 con signo. Salida: R0 en Q7.8 con signo.
; Conserva R1, R2, R3, R4, R5 y R7. R6 no se utiliza ni se modifica.
; EXP_Q3_12 es el simbolo usado por .EXTERNAL g6_EXP-EXP_Q3_12.
; El archivo contiene una subrutina y termina en .END.
; El programa principal aporta .ORIG, carga R0 y llama mediante JSR/JSRR.
;
; EST_EXP y NUM_ITER quedan en memoria, en lugar de devolverse en R1/R2.
; EST_EXP: 0 = normal, 1 = saturado, 2 = redondeado a cero.
; NUM_ITER: 6 en la ruta general; 0 en x=0, saturacion inicial o cero temprano.
; Mantiene las mismas tablas, redondeo y resultados enteros de la version C.
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
; de 15 bits utiles. El desplazamiento 9 guarda el bit de redondeo.

EXP_Q3_12
        ST R1, G6_EXP_R1
        ST R2, G6_EXP_R2
        ST R3, G6_EXP_R3
        ST R4, G6_EXP_R4
        ST R5, G6_EXP_R5
        ST R7, G6_EXP_R7
        JSR G6_EXP_CALCULA
        ST R1, EST_EXP
        ST R2, NUM_ITER
        LD R1, G6_EXP_R1
        LD R2, G6_EXP_R2
        LD R3, G6_EXP_R3
        LD R4, G6_EXP_R4
        LD R5, G6_EXP_R5
        LD R7, G6_EXP_R7
        ADD R0, R0, #0
        RET

G6_EXP_R1 .BLKW #1
G6_EXP_R2 .BLKW #1
G6_EXP_R3 .BLKW #1
G6_EXP_R4 .BLKW #1
G6_EXP_R5 .BLKW #1
G6_EXP_R7 .BLKW #1
EST_EXP   .BLKW #1
NUM_ITER  .BLKW #1

G6_EXP_CALCULA
        ADD R0,R0,#0
        BRp G6_NORMAL
        BRn G6_PROBAR_CERO
        LD R0,G6_UNO
        AND R1,R1,#0
        AND R2,R2,#0
        RET
G6_PROBAR_CERO
        LD R1,G6_UMBRAL_CERO
        ADD R1,R0,R1
        BRp G6_NORMAL
        AND R0,R0,#0
        AND R1,R1,#0
        ADD R1,R1,#2
        AND R2,R2,#0
        RET
G6_UNO .FILL #256
G6_UMBRAL_CERO .FILL #25553
G6_NORMAL
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
        AND R3, R3, #0
        ADD R3, R3, #3
        SHL R1, R0, R3
        LD R7, MASK15
        AND R1, R1, R7
        STR R1, R5, #2
        ADD R3, R3, #9     ; 12 bits: extraer magnitud >> 12.
        SHR R2, R0, R3
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
SALTO_FILA  .FILL #68
BITS_SALIDA .FILL #22
LN_LO       .FILL #1534
LN_MI       .FILL #22713
NEG_LN_LO   .FILL #-1534
NEG_LN_MI   .FILL #-22713

EXP_PASO
        LDR R3, R5, #10    ; Comenzar por el digito 16 de la fila.
        AND R7, R7, #0
        ADD R7, R7, #15
        ADD R7, R7, #1
EXP_BUSCA
        LDR R0, R5, #1
        LDR R1, R5, #2
        LDR R4, R3, #0     ; Probar r - tabla[j][d] en dos palabras.
        SUB R0, R0, R4    ; Diferencia de dos limbos de 15 bits.
        BRzp EXP_BUSCA_MI
        ADD R1, R1, #-1
EXP_BUSCA_MI
        LDR R4, R3, #1
        SUB R1, R1, R4
        BRzp EXP_ACEPTA
        ADD R3, R3, #-4    ; Digito anterior en la misma fila. ; BYTEX-16: direccion en bytes
        ADD R7, R7, #-1
        BRnzp EXP_BUSCA
EXP_ACEPTA
        ADD R3, R7, #0     ; Guardar digito en R3 para el producto.
        LD R7, MASK15
        AND R0, R0, R7
        STR R0, R5, #1
        STR R1, R5, #2

        ; Producto completo de E (tres limbos base 2^15) por d <= 16.
        ; MUL entrega bits 15..0 y MULU bits 31..16 del producto unsigned.
        ; carry = 2*alto16 + (bajo16 >> 15); limbo = bajo16 AND x7FFF.
EXP_PRODUCTO
        ADD R3, R3, #0
        BRz EXP_MULT_CERO
        LDR R4, R5, #6
        MUL R0, R4, R3
        MULU R1, R4, R3
        AND R2, R2, #0
        ADD R2, R2, #15
        SHR R4, R0, R2
        ADD R1, R1, R1
        ADD R1, R1, R4     ; Acarreo del primer limbo.
        AND R0, R0, R7
        STR R0, R5, #13
        STR R1, R5, #14

        LDR R4, R5, #7
        MUL R0, R4, R3
        MULU R1, R4, R3
        SHR R4, R0, R2
        ADD R1, R1, R1
        ADD R2, R1, R4     ; Acarreo del producto del limbo medio.
        AND R1, R0, R7
        LDR R4, R5, #14
        ADD R1, R1, R4     ; Sumar el acarreo del limbo bajo.
        BRzp EXP_MULT_MEDIO
        ADD R2, R2, #1
        AND R1, R1, R7
EXP_MULT_MEDIO
        LDR R4, R5, #8
        MUL R0, R4, R3
        ADD R2, R2, R0     ; Parte alta: E < 2*2^30, sin truncamiento.
        LDR R0, R5, #13
        BRnzp EXP_MULT_FIN
EXP_MULT_CERO
        AND R0, R0, #0
        AND R1, R1, #0
        AND R2, R2, #0
EXP_MULT_FIN
        STR R0, R5, #13
        STR R1, R5, #14
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
        LDR R3, R5, #12
        ADD R3, R3, #1
        STR R3, R5, #12
        ADD R3, R3, #-6
        BRz EXP_SALIDA
        LDR R0, R5, #10
        LD R3, SALTO_FILA
        ADD R0, R0, R3     ; 17 entradas * 2 palabras * 2 bytes = 68.
        STR R0, R5, #10
        LDR R0, R5, #11
        ADD R0, R0, #4
        STR R0, R5, #11
        BRnzp EXP_PASO

EXP_SALIDA
        ; Q7.8 = redondeo(E_entero / 2^(30-8-k)).
        STR R0, R5, #13
        STR R1, R5, #14
        STR R2, R5, #15
        LDR R0, R5, #4
        LD R3, BITS_SALIDA
        SUB R0, R3, R0     ; n = 22 - k: Q30 a Q7.8 y factor 2^k.
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

; REDONDEA: redondear un entero unsigned de 45 bits dividido por 2^n.
; Entrada: R0=n (1..44), TRABAJO+13..15=[a,b,c], 15 bits por limbo.
; Salida: R2:R1:R0, en la misma base 2^15. Mitades se redondean hacia arriba.
; Ya no recorre bits: separa n en 0, 1 o 2 limbos mas un resto de 0..14.
; Para resto r>0: bajo=(a>>r)+((b<<(15-r)) AND x7FFF), y analogo.
; El bit n-1 decide el redondeo, como sumar 2^(n-1) antes de dividir.
; Usa R3/R4/R7 como temporales. R5 es la base; R6 nunca se toca.
REDONDEA
        STR R7, R5, #16
        ADD R3, R0, #-15
        BRn RED_MENOR15
        ADD R4, R3, #-15
        BRn RED_MEDIO
        ADD R3, R4, #0     ; n>=30: conservar el limbo alto; r=n-30.
        LDR R0, R5, #15
        AND R1, R1, #0
        AND R2, R2, #0
        ADD R3, R3, #0
        BRp RED_DESPLAZA
        LDR R4, R5, #14    ; n=30: bit 14 del limbo medio decide.
        BRnzp RED_MULT15
RED_MEDIO
        LDR R0, R5, #14    ; 15<=n<30: quitar un limbo entero.
        LDR R1, R5, #15
        AND R2, R2, #0
        ADD R3, R3, #0
        BRp RED_DESPLAZA
        LDR R4, R5, #13    ; n=15: bit 14 del limbo bajo decide.
RED_MULT15
        AND R7, R7, #0
        ADD R7, R7, #14
        SHR R4, R4, R7
        BRnzp RED_REDONDEA
RED_MENOR15
        ADD R3, R0, #0     ; 1<=n<15: conservar los tres limbos.
        LDR R0, R5, #13
        LDR R1, R5, #14
        LDR R2, R5, #15
RED_DESPLAZA
        ADD R4, R3, #-1
        SHR R4, R0, R4
        AND R4, R4, #1
        STR R4, R5, #9     ; Bit de redondeo antes de perder la fuente.
        SHR R0, R0, R3
        AND R4, R4, #0
        ADD R4, R4, #15
        SUB R4, R4, R3     ; 15-r esta entre 1 y 14, nunca 16.
        SHL R7, R1, R4
        LD R4, RED_MASK15
        AND R7, R7, R4
        ADD R0, R0, R7     ; Campos disjuntos: ADD equivale a OR.
        SHR R1, R1, R3
        AND R4, R4, #0
        ADD R4, R4, #15
        SUB R4, R4, R3
        SHL R7, R2, R4
        LD R4, RED_MASK15
        AND R7, R7, R4
        ADD R1, R1, R7
        SHR R2, R2, R3
        LDR R4, R5, #9
RED_REDONDEA
        ADD R4, R4, #0
        BRz RED_RETORNO
        ADD R0, R0, #1
        BRzp RED_RETORNO
        LD R7, RED_MASK15
        AND R0, R0, R7
        ADD R1, R1, #1
        BRzp RED_RETORNO
        AND R1, R1, R7
        ADD R2, R2, #1
RED_RETORNO
        LDR R7, R5, #16
        RET
RED_MASK15 .FILL x7FFF

TRABAJO .BLKW #18

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

