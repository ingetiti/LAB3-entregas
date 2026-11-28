; =====================================================================
;  LAB 3 - LC-X : sen(x)  entrada Q3.12 -> salida Q1.14 (radianes)
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
;   - SEN_CHEB_PADE guarda R1-R4 en la pila y los restaura: el programa
;     que la llama no pierde ningun valor (R5-R7 no se tocan).
;     R0 es la unica excepcion (entrada y salida).
;   - Los productos redondeados (MULS15, MULU_Q14) son MULQU + ADC y la
;     division redondeada (DIVF) es DIVQ + RSHFL + ADC: mismos bits.
; =====================================================================
; =====================================================================
; SEN_CHEB_PADE : R0 = sen(R0)      (Q3.12 -> Q1.14)
; =====================================================================

SEN_CHEB_PADE
        PUSH R1, R2, R3, R4
        ADD  R3, R0, #0          ; R3 = signo de x (bit 15)

        ; ---- 1) Reduccion de rango (Q3.12) a [0, pi/2] ---------------
        ABS  R0, R0              ; R0 = |x|  (x = -8.0 da x8000 = 32768)
        LD   R1, SN_2PI
        CMP  R1, R0
        BRC  SN_P2               ; |x| <= 2pi (sin signo): sin cambios
        SUB  R0, R0, R1          ; |x| -= 2pi         -> [0, 2pi]
SN_P2   RSHFL R1, R1, #1         ; R1 = pi
        CMP  R1, R0
        BRC  SN_P3               ; |x| <= pi: ya esta en [0, pi]
        SUB  R0, R0, R1          ; |x| -= pi          -> [0, pi]
        NOT  R3, R3              ; sen(x) = -sen(x-pi): invertir signo
SN_P3   RSHFL R2, R1, #1         ; R2 = pi/2
        CMP  R2, R0
        BRC  SN_P4
        SUB  R0, R1, R0          ; pi - |x|           -> [0, pi/2]
SN_P4   LSHF R0, R0, #2          ; Q3.12 -> Q1.14 (<< 2)
        BRz  SN_EXIT             ; sen(0) = 0

        ; ---- 2) Nucleo racional --------------------------------------
        ADD  R1, R0, #0
        MULQU R1, R0, #15
        ADC  R1, R1, #0          ; u = x*x/2   (redondeado)
        LD   R2, SN_A
        MULQU R2, R1, #14
        ADC  R2, R2, #0          ; A*u
        LD   R4, SN_B
        MULQU R4, R1, #14
        ADC  R4, R4, #0          ; B*u
        LD   R1, SN_ONE
        SUB  R2, R1, R2          ; num = 1 - A*u
        ADD  R4, R4, R1          ; den = 1 + B*u
        DIVQ R2, R4, #15         ; 2*num/den  (num = den da x8000)
        RSHFL R2, R2, #1
        ADC  R2, R2, #0          ; ratio = num/den  (redondeado, <= 1.0)
        MULQU R0, R2, #14
        ADC  R0, R0, #0          ; sen = x * ratio  (nunca pasa de 1.0)

        ; ---- 3) Signo ------------------------------------------------
        ADD  R3, R3, #0
        BRzp SN_EXIT
        NEG  R0, R0

        ; ---- 4) Restaurar los registros del llamador -----------------
SN_EXIT POPR R1, R2, R3, R4      ; restaurar y volver

SN_ONE     .FILL #16384          ; 1.0 (Q1.14)
SN_2PI     .FILL #25736          ; 2pi   (Q3.12)
SN_A       .FILL #3672           ; A = 0.2241
SN_B       .FILL #1814           ; B = 0.1107

        .END
