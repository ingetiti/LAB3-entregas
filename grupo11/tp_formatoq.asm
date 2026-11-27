; =====================================================================
; TP punto fijo - LC-3 (actividades en assembly)
;   Punto 3: pasar un numero de un formato Q a otro y sumar / restar
;   Punto 4: multiplicar dos numeros en Q distintos y ajustar el resultado
;
;   NUM_A esta en Q3.12 (1.0 = 4096)   NUM_B esta en Q7.8 (1.0 = 256)
;   Ambos ya formateados en memoria (cambiarlos para otras pruebas).
;
;   PUNTO 3 - conversion: Q3.12 -> Q7.8 = corrimiento ARITMETICO a la
;     derecha de 4 bits (12-8), o sea dividir entre 2^4 redondeando hacia
;     -infinito. Q7.8 -> Q3.12 = corrimiento a la izquierda de 4 bits (x16).
;     La LC-3 no tiene desplazamientos: a la izquierda se hace con ADD R,R,R
;     (duplicar); a la derecha se reconstruyen los bits con un lazo de
;     duplicacion sobre el valor (si es negativo se usa NOT antes y despues,
;     porque floor(v/16) = ~((~v)/16)).
;   PUNTO 4 - producto: 16x16 bits da 32 bits con 12+8 = 20 fraccionarios.
;     Para dejarlo en Q7.8 se descartan 12 bits (corrimiento a la derecha
;     de 12, con redondeo al mas cercano). La multiplicacion es suma y
;     desplazamiento "de izquierda a derecha", con el acumulador en dos
;     palabras de 15 bits (acum = HI*2^15 + LO).
;
;   Restriccion: los operandos de MUL no pueden valer x8000 (-8 / -128).
;   Resultados en memoria:  A_Q78, B_Q312, SUMA, RESTA, PROD  (+ banderas)
;   Banderas: OVF_B = 1 si B no entra en Q3.12 ; OVF_S / OVF_R = 1 si la
;   suma / resta no entra en Q7.8 ; OVF_P = 1 si el producto no entra.
; =====================================================================
        .ORIG x3000

        ; ---- Punto 3: A (Q3.12) -> Q7.8, luego A+B y A-B en Q7.8 --------
        LD   R0, NUM_A
        JSR  Q312_A_Q78          ; R0 = A en Q7.8
        ST   R0, A_Q78
        LD   R1, NUM_B           ; R1 = B (Q7.8)
        ADD  R2, R0, R1          ; suma A+B
        ST   R2, SUMA
        NOT  R3, R1
        ADD  R3, R3, #1          ; R3 = -B
        ADD  R3, R0, R3          ; resta A-B
        ST   R3, RESTA

        ; deteccion de desborde de suma/resta: el resultado desborda si
        ; los dos operandos de la suma tienen igual signo y el resultado no
        AND  R4, R4, #0
        ST   R4, OVF_S
        ST   R4, OVF_R
        ADD  R0, R0, #0
        BRn  S_AN
        ADD  R1, R1, #0          ; A >= 0
        BRn  S_FIN               ; B < 0 : no desborda
        ADD  R2, R2, #0
        BRzp S_FIN
        BRnzp S_OV
S_AN    ADD  R1, R1, #0          ; A < 0
        BRzp S_FIN
        ADD  R2, R2, #0
        BRn  S_FIN
S_OV    AND  R4, R4, #0
        ADD  R4, R4, #1
        ST   R4, OVF_S
S_FIN
        ; resta A-B: desborda si A y -B tienen igual signo y el resultado no
        ; (-B = R3 antes de sumar no se conserva: se usa B directamente)
        LD   R0, A_Q78
        LD   R1, NUM_B
        ADD  R0, R0, #0
        BRn  R_AN
        ADD  R1, R1, #0          ; A >= 0 : desborda si B < 0 y resultado < 0
        BRzp R_FIN
        LD   R3, RESTA
        ADD  R3, R3, #0
        BRzp R_FIN
        BRnzp R_OV
R_AN    ADD  R1, R1, #0          ; A < 0 : desborda si B > 0 y resultado >= 0
        BRnz R_FIN
        LD   R3, RESTA
        ADD  R3, R3, #0
        BRn  R_FIN
R_OV    AND  R4, R4, #0
        ADD  R4, R4, #1
        ST   R4, OVF_R
R_FIN
        ; ---- Punto 3 (otro sentido): B (Q7.8) -> Q3.12 -------------------
        LD   R0, NUM_B
        JSR  Q78_A_Q312
        ST   R0, B_Q312

        ; ---- Punto 4: A*B, resultado en Q7.8 ------------------------------
        LD   R0, NUM_A
        LD   R1, NUM_B
        JSR  MUL_Q312_Q78
        ST   R0, PROD
        HALT

; ---------------------------------------------------------------------
; Q312_A_Q78 : R0 = R0 >> 4 (aritmetico). Destruye R1-R3.
; ---------------------------------------------------------------------
Q312_A_Q78
        AND  R1, R1, #0          ; R1 = bandera de negativo
        ADD  R0, R0, #0
        BRzp C_POS
        NOT  R0, R0              ; ~v >= 0
        ADD  R1, R1, #1
C_POS   AND  R2, R2, #0          ; R2 = resultado
        AND  R3, R3, #0
        ADD  R3, R3, #12         ; 16 - 4 iteraciones
C_LP    ADD  R2, R2, R2          ; resultado *= 2
        ADD  R0, R0, #0
        BRzp C_Z
        ADD  R2, R2, #1          ; entra el bit alto de R0
C_Z     ADD  R0, R0, R0
        ADD  R3, R3, #-1
        BRp  C_LP
        ADD  R0, R2, #0
        ADD  R1, R1, #0
        BRz  C_END
        NOT  R0, R0
C_END   RET

; ---------------------------------------------------------------------
; Q78_A_Q312 : R0 = R0 << 4 (x16). Si no entra en 16 bits: OVF_B = 1 y
; R0 queda saturado (x7FFF / x8000). Destruye R1-R3.
; ---------------------------------------------------------------------
Q78_A_Q312
        AND  R1, R1, #0
        ST   R1, OVF_B
        ADD  R1, R0, #0          ; R1 = valor original
        AND  R3, R3, #0
        ADD  R3, R3, #4          ; 4 duplicaciones
L_LP    ADD  R0, R0, R0
        ADD  R1, R1, #0          ; signo del original
        BRn  L_NEG
        ADD  R0, R0, #0          ; original >= 0: no debe volverse negativo
        BRn  L_OV_P
        BRnzp L_NX
L_NEG   ADD  R0, R0, #0          ; original < 0: no debe volverse >= 0
        BRzp L_OV_N
L_NX    ADD  R3, R3, #-1
        BRp  L_LP
        RET
L_OV_P  LD   R0, K_MAX
        BRnzp L_OV
L_OV_N  LD   R0, K_MIN
L_OV    AND  R1, R1, #0
        ADD  R1, R1, #1
        ST   R1, OVF_B
        RET

; ---------------------------------------------------------------------
; MUL_Q312_Q78 : R0 = A (Q3.12), R1 = B (Q7.8)  ->  R0 = A*B en Q7.8
; Producto de modulos con acumulador HI:LO (15 bits cada uno); luego
; R0 = HI*8 + redondeo(LO/4096) = producto >> 12. Destruye R1-R5.
; ---------------------------------------------------------------------
MUL_Q312_Q78
        AND  R5, R5, #0          ; R5 = cantidad de operandos negativos
        ADD  R0, R0, #0
        BRzp M_A
        NOT  R0, R0
        ADD  R0, R0, #1
        ADD  R5, R5, #1
M_A     ADD  R1, R1, #0
        BRzp M_B
        NOT  R1, R1
        ADD  R1, R1, #1
        ADD  R5, R5, #1
M_B     ADD  R5, R5, #-1         ; exactamente un negativo -> R5 = 0
        BRz  M_NEG
        AND  R5, R5, #0          ; signo positivo
        BRnzp M_SG
M_NEG   AND  R5, R5, #0
        ADD  R5, R5, #1          ; signo negativo
M_SG    ST   R5, M_SIGNO
        AND  R2, R2, #0          ; R2 = LO
        AND  R3, R3, #0          ; R3 = HI
        ADD  R1, R1, R1          ; bit 14 del multiplicador -> bit 15
        AND  R4, R4, #0
        ADD  R4, R4, #15         ; 15 bits
M_LP    ADD  R2, R2, R2          ; acum *= 2
        BRzp M_D1
        LD   R5, K_M15
        AND  R2, R2, R5          ; acarreo: limpiar bit 15 ...
        ADD  R3, R3, R3
        ADD  R3, R3, #1          ; ... y pasarlo a HI
        BRnzp M_D2
M_D1    ADD  R3, R3, R3
M_D2    ADD  R1, R1, #0          ; bit actual del multiplicador
        BRzp M_NB
        ADD  R2, R2, R0          ; acum += A
        BRzp M_NB
        LD   R5, K_M15
        AND  R2, R2, R5
        ADD  R3, R3, #1
M_NB    ADD  R1, R1, R1
        ADD  R4, R4, #-1
        BRp  M_LP
        ; ---- ajuste: producto >> 12 con redondeo --------------------
        AND  R4, R4, #0          ; R4 = floor(LO / 4096)
        LD   R5, K_N4096
M_DV    ADD  R2, R2, R5
        BRn  M_DVE
        ADD  R4, R4, #1
        BRnzp M_DV
M_DVE   LD   R5, K_4096
        ADD  R2, R2, R5          ; R2 = resto (0..4095)
        LD   R5, K_N2048
        ADD  R2, R2, R5
        BRn  M_NR
        ADD  R4, R4, #1          ; resto >= 2048: redondea hacia arriba
M_NR    LD   R5, K_N4096         ; HI >= 4096 -> HI*8 no entra
        ADD  R5, R3, R5
        BRzp M_OVF
        ADD  R3, R3, R3
        ADD  R3, R3, R3
        ADD  R3, R3, R3          ; HI*8
        ADD  R0, R3, R4          ; modulo del resultado
        BRn  M_OVF               ; >= 32768: no entra
        BRnzp M_SIGNO_AP
M_OVF   AND  R5, R5, #0
        ADD  R5, R5, #1
        ST   R5, OVF_P
        LD   R0, K_MAX           ; satura (el negativo queda en x8001..x8000)
        LD   R5, M_SIGNO
        BRz  M_RET
        LD   R0, K_MIN
        BRnzp M_RET
M_SIGNO_AP
        AND  R5, R5, #0
        ST   R5, OVF_P
        LD   R5, M_SIGNO
        BRz  M_RET
        NOT  R0, R0
        ADD  R0, R0, #1
M_RET   RET

; ---------------------------------------------------------------------
; Datos de entrada (ya formateados en memoria)
; ---------------------------------------------------------------------
NUM_A   .FILL #12868             ; 3.14159 en Q3.12 = 3.14159*4096 = x3244
NUM_B   .FILL #3200              ; 12.5    en Q7.8  = 12.5*256     = x0C80

; Resultados y banderas
A_Q78   .FILL #0                 ; A pasado a Q7.8
B_Q312  .FILL #0                 ; B pasado a Q3.12 (solo valido si OVF_B=0)
SUMA    .FILL #0                 ; A+B en Q7.8
RESTA   .FILL #0                 ; A-B en Q7.8
PROD    .FILL #0                 ; A*B en Q7.8
OVF_B   .FILL #0
OVF_S   .FILL #0
OVF_R   .FILL #0
OVF_P   .FILL #0
M_SIGNO .FILL #0

; Constantes
K_MAX   .FILL x7FFF
K_MIN   .FILL x8000
K_M15   .FILL x7FFF
K_4096  .FILL #4096
K_N4096 .FILL #-4096
K_N2048 .FILL #-2048
        .END
