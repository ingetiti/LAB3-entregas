; =====================================================================
; Lab 3a - Actividad en assembly (puntos 3 y 4 del alto nivel)
; Arquitectura de Computadoras (IC221) - FI-UNaM - 2026
;
; Datos en memoria, ya formateados:
; X_Q12    = x en Q3.12 (1 bit de signo, 3 enteros, 12 fraccionarios)
; Y_Q8     = y en Q7.8 (1 bit de signo, 7 enteros, 8 fraccionarios)
; Resultados:
; X_Q8     x pasado a Q7.8 (corrimiento aritmetico a la derecha 4 bits)
; Y_Q12    y pasado a Q3.12 (corrimiento a la izquierda 4 bits)
; OVF_Y    1 si y no entra en Q3.12 (|y| >= 8), 0 si entra
; SUMA_Q8  x + y en Q7.8
; RESTA_Q8 x - y en Q7.8
; PROD_HI / PROD_LO  x*y en 32 bits, formato Q20 (12 + 8)
; PROD_Q8  x*y ajustado a Q7.8
; OVF_P    1 si el producto no entra en Q7.8
; =====================================================================
        .ORIG x3000

; ---------- Punto 3a: Q3.12 -> Q7.8 ----------------------------------
; La LC-3 no tiene corrimiento a la derecha. Truco: armamos un numero
; de 32 bits (R1 = parte alta, R2 = parte baja) con x extendido en signo,
; lo corremos 12 lugares a la IZQUIERDA y la parte alta queda = x >> 4.
        LD R2, X_Q12      ; parte baja = x
        AND R1, R1, #0    ; parte alta = 0 ...
        ADD R2, R2, #0
        BRzp X_POS
        ADD R1, R1, #-1   ; ... o xFFFF si x es negativo
X_POS   AND R3, R3, #0
        ADD R3, R3, #12   ; 12 corrimientos
        JSR SHL32
        ST R1, X_Q8       ; parte alta = x >> 4 (Q7.8)

; ---------- Punto 3b: Q7.8 -> Q3.12 ----------------------------------
; Correr 4 a la izquierda = multiplicar por 16 (sumar el registro consigo
; mismo 4 veces). Solo es valido si y entra en 12 bits con signo.
        LD R0, Y_Q8
        JSR RANGO12       ; R6 = 1 si no entra
        ST R6, OVF_Y
        ADD R6, R6, #0
        BRp SIN_Y12       ; si desborda, no se guarda
        ADD R0, R0, R0    ; x2
        ADD R0, R0, R0    ; x4
        ADD R0, R0, R0    ; x8
        ADD R0, R0, R0    ; x16
        ST R0, Y_Q12
SIN_Y12

; ---------- Punto 3c: suma y resta en el formato de mayor rango (Q7.8) -
        LD R0, X_Q8
        LD R1, Y_Q8
        ADD R2, R0, R1    ; x + y
        ST R2, SUMA_Q8
        NOT R3, R1
        ADD R3, R3, #1    ; -y (complemento a 2)
        ADD R3, R0, R3    ; x - y
        ST R3, RESTA_Q8

; ---------- Punto 4: multiplicacion Q3.12 x Q7.8 ----------------------
; Q12 * Q8 = Q20, y necesita 32 bits. Para volver a Q7.8 hay que correr
; 12 a la derecha: con el mismo truco, 4 a la izquierda y nos quedamos
; con la parte alta.
        LD R1, X_Q12
        LD R2, Y_Q8
        JSR MULS          ; R1:R2 = x*y en Q20 (32 bits)
        ST R1, PROD_HI
        ST R2, PROD_LO
        AND R3, R3, #0
        ADD R3, R3, #4
        ADD R0, R1, #0    ; antes de correr: la parte alta tiene
        JSR RANGO12       ; que entrar en 12 bits para que el
        ST R6, OVF_P      ; resultado entre en Q7.8
        JSR SHL32
        ST R1, PROD_Q8
        HALT

; =====================================================================
; SHL32: corre a la izquierda el par R1:R2 (R1 = alta, R2 = baja)
; R3 veces (R3 > 0). El bit 15 de R2 pasa al bit 0 de R1.
; Entradas: R1, R2, R3. Salidas: R1, R2.
; Resguarda de forma autonoma R3.
; =====================================================================
SHL32   ST R3, SHL_R3     ; RESGUARDO
SH_LAZO ADD R1, R1, R1    ; alta << 1
        ADD R2, R2, #0
        BRzp SH_NC        ; si el bit 15 de la baja es 1 ...
        ADD R1, R1, #1    ; ... entra como bit 0 de la alta
SH_NC   ADD R2, R2, R2    ; baja << 1
        ADD R3, R3, #-1
        BRp SH_LAZO
        LD R3, SHL_R3     ; RESTAURACION
        RET
SHL_R3  .BLKW #1

; =====================================================================
; RANGO12: R6 = 0 si -2048 <= R0 <= 2047 (entra en 12 bits con signo),
; R6 = 1 si no. Entradas: R0. Salidas: R6.
; Resguarda de forma autonoma R5.
; =====================================================================
RANGO12 ST R5, RG_R5      ; RESGUARDO
        AND R6, R6, #0
        LD R5, MENOS2048
        ADD R5, R0, R5    ; R0 - 2048
        BRzp RG_MAL       ; R0 >= 2048 -> no entra
        LD R5, MAS2048
        ADD R5, R0, R5    ; R0 + 2048
        BRzp RG_OK        ; R0 >= -2048 -> entra
RG_MAL  ADD R6, R6, #1
RG_OK   LD R5, RG_R5      ; RESTAURACION
        RET
RG_R5   .BLKW #1

; =====================================================================
; MULS: producto con signo de 16 x 16 bits -> 32 bits
; Entrada: R1 = a, R2 = b | Salida: R1 = parte alta, R2 = parte baja
; Resguarda de forma autonoma R3, R4 y R6.
; =====================================================================
MULS    ST R3, MUL_R3     ; RESGUARDO
        ST R4, MUL_R4
        ST R6, MUL_R6

        AND R6, R6, #0    ; R6 cuenta operandos negativos
        ADD R3, R1, #0    ; R3 = |a|
        BRzp MA_POS
        NOT R3, R3
        ADD R3, R3, #1
        ADD R6, R6, #1
MA_POS  ADD R4, R2, #0    ; R4 = |b|
        BRzp MB_POS
        NOT R4, R4
        ADD R4, R4, #1
        ADD R6, R6, #1
MB_POS  ST R6, MUL_SIGNO  ; 1 = resultado negativo
        AND R1, R1, #0    ; P alta = 0
        AND R2, R2, #0    ; P baja = 0
        AND R6, R6, #0
        ADD R6, R6, #15
        ADD R6, R6, #1    ; 16 vueltas, una por bit de b
M_LAZO  ADD R1, R1, R1    ; P = P << 1 (32 bits)
        ADD R2, R2, #0
        BRzp M_SH
        ADD R1, R1, #1
M_SH    ADD R2, R2, R2
        ADD R4, R4, #0    ; bit mas alto de b
        BRzp M_SIG        ; si es 0, no se suma
; P = P + |a| (suma de 32 bits: hay que detectar el acarreo de la baja)
        ADD R2, R2, #0
        BRn M_BAJA1
        ADD R3, R3, #0    ; bit 15 de P baja = 0
        BRn M_UNO
        ADD R2, R2, R3    ; ninguno tiene bit 15 en 1: sin acarreo
        BRnzp M_SIG
M_BAJA1 ADD R3, R3, #0    ; bit 15 de P baja = 1
        BRn M_DOS
M_UNO   ADD R2, R2, R3    ; solo uno tiene bit 15 en 1:
        BRn M_SIG         ; si la suma queda con bit 15 = 1, no hubo acarreo
        ADD R1, R1, #1    ; si quedo en 0, hubo acarreo
        BRnzp M_SIG
M_DOS   ADD R2, R2, R3    ; los dos tienen bit 15 en 1: siempre acarreo
        ADD R1, R1, #1
M_SIG   ADD R4, R4, R4    ; siguiente bit de b
        ADD R6, R6, #-1
        BRp M_LAZO
        LD R6, MUL_SIGNO  ; signo del resultado
        ADD R6, R6, #-1
        BRnp M_FIN        ; 0 o 2 negativos -> positivo
        NOT R1, R1        ; negar 32 bits: invertir ...
        NOT R2, R2
        ADD R2, R2, #1    ; ... y sumar 1 a la baja
        BRnp M_FIN
        ADD R1, R1, #1    ; si la baja dio 0, el 1 pasa a la alta

M_FIN   LD R3, MUL_R3     ; RESTAURACION
        LD R4, MUL_R4
        LD R6, MUL_R6
        RET

; ---------- constantes y variables ----------
MENOS2048 .FILL xF800     ; -2048
MAS2048   .FILL x0800     ; +2048
MUL_SIGNO .BLKW #1
X_Q12     .FILL x1B33     ; 1.7 en Q3.12 (6963)
Y_Q8      .FILL xFDC0     ; -2.25 en Q7.8 (-576)
X_Q8      .BLKW #1
Y_Q12     .BLKW #1
OVF_Y     .BLKW #1
SUMA_Q8   .BLKW #1
RESTA_Q8  .BLKW #1
PROD_HI   .BLKW #1
PROD_LO   .BLKW #1
PROD_Q8   .BLKW #1
OVF_P     .BLKW #1

; ---------- variables locales de subrutinas ----------
MUL_R3    .BLKW #1
MUL_R4    .BLKW #1
MUL_R6    .BLKW #1

        .END
