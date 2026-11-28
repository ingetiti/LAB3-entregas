; =====================================================================
;  LAB 3 - LC-3 : sen(x)  entrada Q3.12 -> salida Q1.14 (radianes)
;
;        sen(x) ~= x * (1 - A*u) / (1 + B*u)        u = x^2 / 2
;
;  x reducido a [0, pi/2].  A = 3672/16384 (0.2241), B = 1814/16384 (0.1107),
;  minimax sobre enteros Q1.14.
;
;  ENTRADA  : R0 = angulo en Q3.12 (1 signo, 3 enteros, 12 decimales),
;             entero de 16 bits con signo, 1.0 = 4096, x en [-8, 8).
;  SALIDA   : R0 = sen(x) en Q1.14 (1 signo, 1 entero, 14 decimales),
;             1.0 = 16384.
;  La reduccion se hace en Q3.12 (2pi = 25736, pi = 12868, pi/2 = 6434);
;  al final x (<= pi/2) se pasa a Q1.14 con dos desplazamientos (exacto).
;
;  CONVENCION DE REGISTROS
;   - R6 (pila) y R7 (retorno) NO se usan como registros de trabajo.
;   - SEN_CHEB_PADE guarda R1-R7 en memoria (ST) al entrar y los restaura (LD)
;     antes del RET: el programa que la llama no pierde ningun valor.
;     R0 es la unica excepcion (entrada y salida).
;   - Las rutinas internas MULS15, MULU_Q14 y DIVF destruyen R1-R5 (ya
;     guardados por SEN_CHEB_PADE), no tocan R6 ni R7 y retornan con RET.
; =====================================================================
; =====================================================================
; SEN_CHEB_PADE : R0 = sen(R0)      (Q3.12 -> Q1.14)
; =====================================================================

SEN_CHEB_PADE
        ST   R1, SN_R1           ; guardar los registros del llamador
        ST   R2, SN_R2
        ST   R3, SN_R3
        ST   R4, SN_R4
        ST   R5, SN_R5
        ST   R6, SN_R6
        ST   R7, SN_R7           ; (R7 se pisa en cada JSR interno)

        ; ---- 1) Reduccion de rango (Q3.12) a [0, pi/2] ---------------
        AND  R4, R4, #0          ; R4 = bandera de signo (1 = negativo)
        ADD  R0, R0, #0
        BRzp SN_P1
        NOT  R0, R0
        ADD  R0, R0, #1          ; R0 = |x|  (x = -8.0 da x8000 = 32768)
        ADD  R4, R4, #1
SN_P1   LD   R1, SN_N2PI
        ADD  R2, R0, R1          ; |x| - 2pi  (siempre en [-25736, 7032])
        BRnz SN_P2               ; |x| <= 2pi: sin cambios
        ADD  R0, R2, #0          ; |x| -= 2pi         -> [0, 2pi]
SN_P2   LD   R1, SN_NPI
        ADD  R2, R0, R1          ; |x| - pi
        BRnz SN_P3               ; |x| <= pi: ya esta en [0, pi]
        ADD  R0, R2, #0          ; |x| -= pi          -> [0, pi]
        NOT  R4, R4              ; sen(x) = -sen(x-pi): invertir signo
        AND  R4, R4, #1
SN_P3   LD   R1, SN_NHALFPI
        ADD  R2, R0, R1          ; |x| - pi/2
        BRnz SN_P4
        NOT  R0, R0
        ADD  R0, R0, #1          ; -|x|
        LD   R1, SN_PI
        ADD  R0, R0, R1          ; pi - |x|           -> [0, pi/2]
SN_P4   ADD  R0, R0, R0
        ADD  R0, R0, R0          ; Q3.12 -> Q1.14 (<< 2)
        BRz  SN_EXIT             ; sen(0) = 0
        ST   R4, SN_SIGN
        ST   R0, SN_X

        ; ---- 2) Nucleo racional --------------------------------------
        ADD  R1, R0, #0
        JSR  MULS15              ; u = x*x/2   (redondeado)
        ST   R0, SN_U
        LD   R1, SN_A
        JSR  MULU_Q14            ; A*u
        NOT  R0, R0
        ADD  R0, R0, #1
        LD   R1, SN_ONE
        ADD  R0, R0, R1          ; num = 1 - A*u
        ST   R0, SN_NUM
        LD   R0, SN_U
        LD   R1, SN_B
        JSR  MULU_Q14            ; B*u
        LD   R1, SN_ONE
        ADD  R1, R0, R1          ; den = 1 + B*u
        LD   R0, SN_NUM
        JSR  DIVF                ; ratio = num/den  (<= 1.0)
        ADD  R1, R0, #0
        LD   R0, SN_X
        JSR  MULU_Q14            ; sen = x * ratio
        LD   R1, SN_NEG_ONE      ; saturar a 1.0
        ADD  R1, R0, R1
        BRnz SN_SGN
        LD   R0, SN_ONE

        ; ---- 3) Signo ------------------------------------------------
SN_SGN  LD   R1, SN_SIGN
        BRz  SN_EXIT
        NOT  R0, R0
        ADD  R0, R0, #1

        ; ---- 4) Restaurar los registros del llamador -----------------
SN_EXIT LD   R1, SN_R1
        LD   R2, SN_R2
        LD   R3, SN_R3
        LD   R4, SN_R4
        LD   R5, SN_R5
        LD   R6, SN_R6
        LD   R7, SN_R7           ; direccion de retorno original
        RET

SN_R1      .BLKW #1
SN_R2      .BLKW #1
SN_R3      .BLKW #1
SN_R4      .BLKW #1
SN_R5      .BLKW #1
SN_R6      .BLKW #1
SN_R7      .BLKW #1
SN_SIGN    .BLKW #1
SN_X       .BLKW #1
SN_U       .BLKW #1
SN_NUM     .BLKW #1
SN_ONE     .FILL #16384          ; 1.0 (Q1.14)
SN_NEG_ONE .FILL #-16384
SN_N2PI    .FILL #-25736         ; -2pi  (Q3.12)
SN_PI      .FILL #12868          ; pi    (Q3.12)
SN_NPI     .FILL #-12868
SN_NHALFPI .FILL #-6434          ; -pi/2 (Q3.12)
SN_A       .FILL #3672           ; A = 0.2241
SN_B       .FILL #1814           ; B = 0.1107

; =====================================================================
; MULS15 : R0 = (R0*R1 + 2^14) >> 15   (0 <= R0,R1 <= 32767)
; MULU_Q14: R0 = (R0*R1 + 2^13) >> 14   (producto Q1.14 redondeado)
;
; Shift-and-add "de izquierda a derecha" (Horner): acc = 2*acc + bit*a.
; El multiplicando 'a' (R0) ocupa un solo limb de 15 bits; el acumulador
; de 32 bits son dos limbs de 15 bits: acc = hi*2^15 + lo, lo < 2^15
;   R0 = a (el mayor)     R1 = multiplicador (el menor, bit 14 -> bit 15)
;   R2 = acc_lo           R3 = acc_hi
;   R4 = contador         R5 = temporal
; Una suma de limbs nunca desborda 16 bits y el acarreo es el bit 15
; (la LC-3 no tiene flag de acarreo). El redondeo se suma al final.
; No usa R6 ni R7. Destruye R1-R5.
; =====================================================================
MULS15
        AND  R2, R2, #0
        ADD  R2, R2, #1
        ST   R2, MU_SQ           ; modo: devolver hi
        LD   R2, MU_H15
        ST   R2, MU_RND          ; redondeo = 2^14
        BR   MU_B
MULU_Q14
        AND  R2, R2, #0
        ST   R2, MU_SQ           ; modo: devolver 2*hi + bit14(lo)
        LD   R2, MU_H14
        ST   R2, MU_RND          ; redondeo = 2^13
MU_B    NOT  R2, R1              ; dejar el menor en R1
        ADD  R2, R2, #1
        ADD  R2, R0, R2          ; a - b
        BRzp MU_OK
        ADD  R2, R0, #0
        ADD  R0, R1, #0
        ADD  R1, R2, #0
MU_OK   ADD  R1, R1, #0
        BRz  MU_ZERO             ; multiplicador 0 -> producto 0
        AND  R2, R2, #0          ; acc_lo = 0
        AND  R3, R3, #0          ; acc_hi = 0
        ADD  R1, R1, R1          ; bit 14 del multiplicador -> bit 15
        AND  R4, R4, #0
        ADD  R4, R4, #7          ; 15 bits por revisar (15 = 7+7+1, imm4)
        ADD  R4, R4, #7
        ADD  R4, R4, #1
MU_SK   ADD  R1, R1, #0          ; saltear los ceros iniciales
        BRn  MU_LP
        ADD  R1, R1, R1
        ADD  R4, R4, #-1
        BR   MU_SK
MU_LP   ADD  R2, R2, R2          ; acc *= 2   (lo)
        BRzp MU_D1
        LD   R5, MU_M15
        AND  R2, R2, R5          ; acarreo: limpiar bit 15
        ADD  R3, R3, R3
        ADD  R3, R3, #1          ; hi = 2*hi + 1
        BR   MU_D2
MU_D1   ADD  R3, R3, R3          ; hi = 2*hi
MU_D2   ADD  R1, R1, #0          ; bit 15 del multiplicador
        BRzp MU_NB
        ADD  R2, R2, R0          ; acc_lo += a
        BRzp MU_NB
        LD   R5, MU_M15
        AND  R2, R2, R5          ; acarreo: limpiar bit 15
        ADD  R3, R3, #1          ; y subirlo a acc_hi
MU_NB   ADD  R1, R1, R1          ; multiplicador <<= 1
        ADD  R4, R4, #-1
        BRp  MU_LP
        LD   R5, MU_RND          ; sumar el redondeo
        ADD  R2, R2, R5
        BRzp MU_RS
        LD   R5, MU_M15
        AND  R2, R2, R5
        ADD  R3, R3, #1
MU_RS   LD   R5, MU_SQ
        BRp  MU_HI
        ADD  R0, R3, R3          ; 2*hi
        LD   R5, MU_NEG1
        ADD  R5, R2, R5          ; lo - 16384
        BRn  MU_FIN
        ADD  R0, R0, #1          ; + bit 14 de lo
MU_FIN  RET
MU_HI   ADD  R0, R3, #0
        RET
MU_ZERO AND  R0, R0, #0
        RET
MU_SQ   .BLKW #1
MU_RND  .BLKW #1
MU_H14  .FILL #8192
MU_H15  .FILL #16384
MU_M15  .FILL #32767
MU_NEG1 .FILL #-16384

; =====================================================================
; DIVF : R0 = R0 / R1 en Q1.14 (redondeado), con 0 < R0 <= R1 < 32768.
; Division restauradora de 14 pasos. Destruye R1-R4. No usa R6 ni R7.
; (r<<1 puede pasar de 15 bits, pero 2r-d queda en [-d, d): el signo
;  de esa resta en 16 bits es correcto.)
; =====================================================================
DIVF
        NOT  R3, R1
        ADD  R3, R3, #1          ; R3 = -d
        ADD  R2, R0, #0          ; r = n
        AND  R4, R4, #0          ; q = 0
        AND  R0, R0, #0
        ADD  R0, R0, #7          ; contador = 14 (14 = 7+7, imm4)
        ADD  R0, R0, #7
DV_LP   ADD  R4, R4, R4          ; q <<= 1
        ADD  R2, R2, R2          ; r <<= 1
        ADD  R1, R2, R3          ; r - d
        BRn  DV_NS
        ADD  R2, R1, #0
        ADD  R4, R4, #1
DV_NS   ADD  R0, R0, #-1
        BRp  DV_LP
        ADD  R2, R2, R2          ; redondeo: 2r >= d ?
        ADD  R1, R2, R3
        BRn  DV_NR
        ADD  R4, R4, #1
DV_NR   ADD  R0, R4, #0
        RET

        .END
