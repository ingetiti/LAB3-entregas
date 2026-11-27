; ============================================================================
; Modulo: todec  (archivo g27_todec.asm)                                Grupo 27
; Convierte un valor a texto decimal, en LC10 (con MUL/DIVU/REMU).
;
; TODEC
; Entrada:  R0 = parte entera, R1 = parte fraccionaria (Q.16, exponentes negativos)
;           R2 = puntero al buffer de la cadena (bytes, 17 como minimo)
;           R3 = formato: bit 0 mostrar +, bit 1 conservar ceros a la izquierda,
;                         bit 2 conservar ceros a la derecha
; Salida:   la cadena queda escrita en el buffer (terminada en 0)
; Preserva: R0 a R5 y R7 (los guarda en la pila con PUSH/POP; R6 vuelve igual)
;
; Mismo resultado que el modulo LC-3 original, sin sus lazos de restas:
;
; * Parte entera: el original resta 10^4, 10^3, ... sucesivamente. Aca se divide.
;   La parte entera, ya sin signo, es a lo sumo 32768.
;
; * Parte fraccionaria: el original suma, por cada bit k encendido de la fraccion,
;   (10^9 << k) >> 16 truncado, con aritmetica de 32 bits emulada, y despues saca
;   9 digitos. Eso no es floor(f * 10^9 / 65536) (da otro 9.o decimal casi siempre),
;   asi que hay que reproducirlo. Con m = f >> 7 y u = f & 127:
;       suma = 5^9 * m + 15258 * u + (u >> 1) + (u >> 2) + (u >> 5)
;   (los bits k >= 7 dan multiplos exactos de 5^9; los 7 bajos truncan, y
;   floor(5^9 / 2^j) = 15258 * 2^(7-j) + floor(101 / 2^j)). Se calcula en 4 "limbos"
;   de base 100 (cada producto entra en 16 bits) y de ahi salen los digitos:
;       a0 = 25 m + 58 u + F(u)     a1 = 31 m + 52 u     a2 = 95 m + u     a3 = m
;   (5^9 = 1|95|31|25 y 15258 = 1|52|58 en base 100). Se prueba contra las 65.536
;   fracciones en bench/equivalencia_todec.py y bench/equivalencia_modulos.py.
; ============================================================================

TODEC
                        PUSH  R0-R5, R7               ; guarda R0..R5 y R7 en la pila (R6)

; ---- Signo: si la parte entera es negativa se niega todo el valor [entero, fraccion]
                        TST   R0
                        BRzp  todec_positivo
                        MOVI  R4, #45                   ; '-'
                        STL   R4, R2, #0
                        ADD   R2, R2, #1
                        NOT   R0, R0
                        TST   R1
                        BRnp  todec_neg_sk
                        ADD   R0, R0, #1                ; fraccion 0: entero = -entero
todec_neg_sk
                        NEG   R1, R1
                        BR    todec_entero
todec_positivo
                        AND   R4, R3, #1
                        BRz   todec_entero
                        MOVI  R4, #43                   ; '+'
                        STL   R4, R2, #0
                        ADD   R2, R2, #1

; ---- Parte entera: digitos de R0 (0..32768), de mayor a menor (R4 = 10^k)
todec_entero
                        MOVI  R3, #48                   ; '0'
                        LD    R4, todec_k10000
                        LDW   R5, R6, #6                ; R3 de entrada (formato), guardado por PUSH en R6+6
                        AND   R5, R5, #2
                        BRnp  todec_emitir              ; SHOW_LEADZ: los 5 digitos
                        TST   R0
                        BRnp  todec_saltear
                        MOVI  R4, #1                    ; entero 0: un solo digito
                        BR    todec_emitir
todec_saltear
                        MOVI  R5, #10
todec_sk_lazo
                        CMP   R0, R4
                        BRC   todec_emitir              ; entero >= 10^k: desde este digito
                        DIVU  R4, R4, R5
                        BR    todec_sk_lazo

; ---- datos (en medio del codigo, para que LD y ST los alcancen desde los dos extremos)
todec_k10000            .FILL #10000
todec_k3030             .FILL x3030

todec_emitir
                        DIVREMU R5, R0, R4             ; R5 = R0 / R4 y R0 = R0 % R4
                        ADD   R5, R5, R3
                        STL   R5, R2, #0
                        ADD   R2, R2, #1
                        MOVI  R5, #10
                        DIVU  R4, R4, R5
                        BRp   todec_emitir

; ---- Parte fraccionaria
                        TST   R1
                        BRnp  todec_fraccion
                        LDW   R5, R6, #6                ; R3 de entrada (formato), guardado por PUSH en R6+6
                        AND   R5, R5, #4
                        BRz   todec_fin                 ; fraccion 0 sin SHOW_ENDZ: no hay punto
todec_fraccion
                        MOVI  R5, #46                   ; '.'
                        STL   R5, R2, #0
                        ADD   R2, R2, #7
                        ADD   R2, R2, #3                ; R2 = fin de los 9 digitos (+1 del punto)
                        SHR   R3, R1, #7                ; m
                        MOVI  R4, #127
                        AND   R4, R1, R4                ; u

; limbo 0: a0 = 25 m + 58 u + (u>>1) + (u>>2) + (u>>5); sus digitos van en R2-2 y R2-1
                        MOVI  R1, #25
                        MUL   R1, R3, R1
                        MOVI  R5, #58
                        MUL   R5, R4, R5
                        ADD   R1, R1, R5
                        SHR   R5, R4, #1
                        ADD   R1, R1, R5
                        SHR   R5, R4, #2
                        ADD   R1, R1, R5
                        SHR   R5, R4, #5
                        ADD   R1, R1, R5
                        MOVI  R5, #100
                        DIVREMU R0, R1, R5             ; acarreo = a / 100 y r = a % 100 (queda en R1)
                        MOVI  R5, #10
                        DIVREMU R7, R1, R5             ; decenas (R7) y unidades (R1)
                        SHL   R7, R7, #8
                        OR    R7, R7, R1
                        LD    R5, todec_k3030
                        ADD   R7, R7, R5                ; (decenas + '0') en el byte alto, (unidades + '0') en el bajo
                        STH   R7, R2, #-2
                        STL   R7, R2, #-1

; limbo 1: a1 = 31 m + 52 u + acarreo; digitos en R2-4 y R2-3
                        MOVI  R1, #31
                        MUL   R1, R3, R1
                        MOVI  R5, #52
                        MUL   R5, R4, R5
                        ADD   R1, R1, R5
                        ADD   R1, R1, R0
                        MOVI  R5, #100
                        DIVREMU R0, R1, R5             ; acarreo = a / 100 y r = a % 100 (queda en R1)
                        MOVI  R5, #10
                        DIVREMU R7, R1, R5             ; decenas (R7) y unidades (R1)
                        SHL   R7, R7, #8
                        OR    R7, R7, R1
                        LD    R5, todec_k3030
                        ADD   R7, R7, R5                ; (decenas + '0') en el byte alto, (unidades + '0') en el bajo
                        STH   R7, R2, #-4
                        STL   R7, R2, #-3

; limbo 2: a2 = 95 m + u + acarreo; digitos en R2-6 y R2-5
                        MOVI  R1, #95
                        MUL   R1, R3, R1
                        ADD   R1, R1, R4
                        ADD   R1, R1, R0
                        MOVI  R5, #100
                        DIVREMU R0, R1, R5             ; acarreo = a / 100 y r = a % 100 (queda en R1)
                        MOVI  R5, #10
                        DIVREMU R7, R1, R5             ; decenas (R7) y unidades (R1)
                        SHL   R7, R7, #8
                        OR    R7, R7, R1
                        LD    R5, todec_k3030
                        ADD   R7, R7, R5                ; (decenas + '0') en el byte alto, (unidades + '0') en el bajo
                        STH   R7, R2, #-6
                        STL   R7, R2, #-5

; limbo 3: a3 = m + acarreo; digitos en R2-8 y R2-7, y el acarreo (0..9) es el primer digito
                        ADD   R1, R3, R0
                        MOVI  R5, #100
                        DIVREMU R0, R1, R5             ; acarreo = a / 100 y r = a % 100 (queda en R1)
                        MOVI  R5, #10
                        DIVREMU R7, R1, R5             ; decenas (R7) y unidades (R1)
                        SHL   R7, R7, #8
                        OR    R7, R7, R1
                        LD    R5, todec_k3030
                        ADD   R7, R7, R5                ; (decenas + '0') en el byte alto, (unidades + '0') en el bajo
                        STH   R7, R2, #-8
                        STL   R7, R2, #-7

                        LD    R5, todec_k3030
                        ADD   R0, R0, R5                ; (3030 = '0' en cada byte: sirve el bajo)
                        STL   R0, R2, #-9

; Sin SHOW_ENDZ se sacan los ceros del final (siempre queda un digito distinto de cero)
                        LDW   R5, R6, #6                ; R3 de entrada (formato), guardado por PUSH en R6+6
                        AND   R5, R5, #4
                        BRnp  todec_fin
                        MOVI  R3, #48
todec_ceros
                        ADD   R2, R2, #-1
                        LDL   R5, R2, #0
                        CMP   R5, R3
                        BRz   todec_ceros
                        ADD   R2, R2, #1

todec_fin
                        MOVI  R5, #0
                        STL   R5, R2, #0                ; fin de cadena
                        POP   R0-R5, R7
                        RET

.END
