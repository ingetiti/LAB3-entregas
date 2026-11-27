        .ORIG x3000

; Operandos en Q3.12 y Q7.8. Las tres salidas se guardan en Q7.8.
; EST_SUMA, EST_RESTA y EST_MULT: 0 = valido, 1 = fuera de rango.
; Si un estado vale 1, el resultado asociado se guarda en cero.

; Compatibilizar el primer operando con un corrimiento aritmetico de 4.
; Copiar los 12 bits altos, extendiendo el signo en el acumulador R0.
        LD R1, NUM1_Q3_12
        AND R0, R0, #0
        ADD R1, R1, #0
        BRzp INICIO_Q7
        ADD R0, R0, #-1
INICIO_Q7
        AND R2, R2, #0
        ADD R2, R2, #12
Q7_BIT
        ADD R0, R0, R0
        ADD R1, R1, #0
        BRzp Q7_SIGUIENTE
        ADD R0, R0, #1
Q7_SIGUIENTE
        ADD R1, R1, R1
        ADD R2, R2, #-1
        BRp Q7_BIT

; Suma. Hay desborde si los operandos tienen el mismo signo y el
; resultado cambia de signo.
        LD R1, NUM2_Q7_8
        ADD R2, R0, R1
        AND R3, R3, #0
        ADD R0, R0, #0
        BRn SUMA_A_NEG
        ADD R1, R1, #0
        BRn GUARDA_SUMA
        ADD R2, R2, #0
        BRn SUMA_FUERA
        BRnzp GUARDA_SUMA
SUMA_A_NEG
        ADD R1, R1, #0
        BRzp GUARDA_SUMA
        ADD R2, R2, #0
        BRn GUARDA_SUMA
SUMA_FUERA
        ADD R3, R3, #1
        AND R2, R2, #0
GUARDA_SUMA
        ST R2, RES_SUMA
        ST R3, EST_SUMA

; Resta. Hay desborde si los operandos tienen signos opuestos y el
; resultado cambia respecto del signo del primer operando.
        NOT R2, R1
        ADD R2, R2, #1
        ADD R2, R0, R2
        AND R3, R3, #0
        ADD R0, R0, #0
        BRn RESTA_A_NEG
        ADD R1, R1, #0
        BRzp GUARDA_RESTA
        ADD R2, R2, #0
        BRn RESTA_FUERA
        BRnzp GUARDA_RESTA
RESTA_A_NEG
        ADD R1, R1, #0
        BRn GUARDA_RESTA
        ADD R2, R2, #0
        BRn GUARDA_RESTA
RESTA_FUERA
        ADD R3, R3, #1
        AND R2, R2, #0
GUARDA_RESTA
        ST R2, RES_RESTA
        ST R3, EST_RESTA

; Multiplicar los operandos originales por magnitud. R0 y R1 contienen
; las magnitudes sin signo, incluido x8000 para el extremo negativo.
        AND R7, R7, #0
        LD R0, NUM1_Q3_12
        BRzp MULT_SIGNO_B
        NOT R0, R0
        ADD R0, R0, #1
        ADD R7, R7, #1
MULT_SIGNO_B
        LD R1, NUM2_Q7_8
        BRzp MULT_INICIO
        NOT R1, R1
        ADD R1, R1, #1
        NOT R7, R7
        ADD R7, R7, #2
MULT_INICIO
        ST R7, SIGNO_PRODUCTO
        AND R2, R2, #0
        AND R3, R3, #0
        AND R4, R4, #0
        LD R5, MASCARA15
        AND R6, R6, #0
        ADD R6, R6, #15
        ADD R6, R6, #1

; Producto crudo Q10.20: R2 + R3*2^15 + R4*2^30.
; Recorrer los 16 bits del multiplicador desde el mas significativo.
; En cada vuelta, duplicar el producto parcial y sumar R0 si el bit es 1.
MULT_BIT
        ADD R4, R4, R4
        ADD R3, R3, R3
        BRzp DOBLA_BAJO
        AND R3, R3, R5
        ADD R4, R4, #1
DOBLA_BAJO
        ADD R2, R2, R2
        BRzp MULT_SUMAR
        AND R2, R2, R5
        ADD R3, R3, #1
MULT_SUMAR
        ADD R1, R1, #0
        BRzp MULT_SIGUIENTE
        ADD R2, R2, R0
        BRzp MULT_SIGUIENTE
        AND R2, R2, R5
        ADD R3, R3, #1
        BRzp MULT_SIGUIENTE
        AND R3, R3, R5
        ADD R4, R4, #1
MULT_SIGUIENTE
        ADD R1, R1, R1
        ADD R6, R6, #-1
        BRp MULT_BIT

; El corrimiento de 12 para Q7.8 admite magnitudes crudas menores
; que 2^27. La magnitud 2^27 exacta solo cabe con signo negativo.
        ADD R4, R4, #0
        BRp MULT_FUERA
        LD R5, NEG_4096
        ADD R5, R3, R5
        BRp MULT_FUERA
        BRn MULT_AJUSTE
        LD R5, SIGNO_PRODUCTO
        BRz MULT_FUERA
        ADD R2, R2, #0
        BRnp MULT_FUERA
        LD R0, MINIMO_Q7
        BRnzp MULT_OK

; Cociente por 4096: ocho veces la palabra media mas los tres
; bits superiores de la palabra baja. Los 12 restantes son el resto.
MULT_AJUSTE
        ADD R0, R3, R3
        ADD R0, R0, R0
        ADD R0, R0, R0
        AND R1, R1, #0
        ADD R2, R2, R2
        AND R6, R6, #0
        ADD R6, R6, #3
AJUSTE_BIT
        ADD R1, R1, R1
        ADD R2, R2, #0
        BRzp AJUSTE_SIGUIENTE
        ADD R1, R1, #1
AJUSTE_SIGUIENTE
        ADD R2, R2, R2
        ADD R6, R6, #-1
        BRp AJUSTE_BIT
        ADD R0, R0, R1
        LD R5, SIGNO_PRODUCTO
        BRz MULT_OK
        ADD R2, R2, #0
        BRz MULT_NEGAR
        ADD R0, R0, #1
MULT_NEGAR
        NOT R0, R0
        ADD R0, R0, #1
MULT_OK
        AND R1, R1, #0
        BRnzp GUARDA_MULT
MULT_FUERA
        AND R0, R0, #0
        AND R1, R1, #0
        ADD R1, R1, #1
GUARDA_MULT
        ST R0, RES_MULT
        ST R1, EST_MULT
        HALT

NUM1_Q3_12      .FILL #256      ; 0.0625 en Q3.12
NUM2_Q7_8       .FILL #32       ; 0.125 en Q7.8
MASCARA15       .FILL x7FFF
NEG_4096        .FILL #-4096
MINIMO_Q7       .FILL x8000
SIGNO_PRODUCTO  .BLKW #1
RES_SUMA        .BLKW #1
RES_RESTA       .BLKW #1
RES_MULT        .BLKW #1
EST_SUMA        .BLKW #1
EST_RESTA       .BLKW #1
EST_MULT        .BLKW #1
        .END
