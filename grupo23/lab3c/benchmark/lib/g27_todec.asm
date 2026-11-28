



;   ============================================================================
;   Subrutina: TODEC
;       Convierte un valor a cadena de texto decimal.
;       Utilizara el formato indicado, donde los bits indican:
;       - El bit 0 mostrar signo +.
;       - El bit 1 mantener los 0 a izquierda.
;       - El bit 2 mantener los 0 a derecha.
;       Se espera el valor separado en 2 registros:
;       - En R0 la parte entera (exponentes positivos y cero: [..., 2**1, 2**0])
;       - En R1 la parte fraccionaria (exponentes negativos: [2**-1, 2**-2, ...])
;
;   -> INPUT  [R0] Parte entera.
;   -> INPUT  [R1] Parte fraccionaria.
;   -> INPUT  [R2] Puntero al buffer de la cadena (17 WORDS minimo).
;   -> INPUT  [R3] Formato bits [15:3 none, 2 SHOW_ENDZ, 1 SHOW_LEADZ, 0 SHOW_PLUS]
;   <- OUTPUT [R2] Puntero al buffer de la cadena ya cargada.
;   ============================================================================

;   [G23] Inicio, signo, parte entera y retorno temprano reescritos para la ISA
;   G23 por el Grupo 23. Misma salida que la version del Grupo 27 en todos los
;   formatos: resguardo con PUSH/POP, cursor y formato en registros, y cada
;   digito entero con DIVU + REMU (antes, hasta 9 restas sucesivas por digito).
TODEC
    PUSH R0 R1 R3 R4 R5 R7              ;   resguardo
    ST R2 todec_cursor_beg              ;   [cursor_beg] = cursor ; [R2] cursor de escritura
    ST R1 todec_fraccion                ;   [fraccion] = fraccion ; [R3] formato

;   ==- Signo -=================================================================
    BRRzp R0 todec_sig_elif             ;   if entero < 0:
    LD R4 todec_chr_minus
    STR R4 R2 #0
    ADD R2 R2 #2                        ;       texto = texto + '-'
    NOT R0 R0
    BRRnp R1 todec_sig_sk1
    ADD R0 R0 #1
todec_sig_sk1
    NOT R1 R1
    ADD R1 R1 #1
    ST R1 todec_fraccion                ;       [entero, fraccion] = -[entero, fraccion]
    BR todec_int
todec_sig_elif
    AND R4 R3 #1
    BRz todec_int                       ;   elif formato & SHOW_PLUS:
    LD R4 todec_chr_plus
    STR R4 R2 #0
    ADD R2 R2 #2                        ;       texto = texto + '+'

;   ==- Entero -================================================================
todec_int                               ;   (entero sin signo: -32768 negado = 32768,
                                        ;    igual que en la original, donde la resta da la vuelta)
;   [G23] Version 2: en lugar de probar las 5 potencias de 10, se cuenta la
;   cantidad de digitos (5 con SHOW_LEADZ) y se sacan de derecha a izquierda con
;   DIVU/REMU por 10. Mismo texto: con SHOW_LEADZ los 5 digitos con ceros; sin
;   SHOW_LEADZ los digitos significativos, o "0" si el entero es 0.
    ST R3 todec_format                  ;   la parte decimal usa [formato]
    AND R4 R3 #2
    BRnp todec_int_lz                   ;   if formato & SHOW_LEADZ: 5 digitos
    AND R5 R5 #0
    ADD R5 R5 #1                        ;   [R5] digitos = 1
    AND R4 R4 #0
    ADD R4 R4 #10
    SUB R7 R0 R4
    BRNC todec_int_nd                   ;   entero < 10 (sin signo)
    ADD R5 R5 #1
    LD R4 todec_k100
    SUB R7 R0 R4
    BRNC todec_int_nd                   ;   entero < 100
    ADD R5 R5 #1
    LD R4 todec_k1000
    SUB R7 R0 R4
    BRNC todec_int_nd                   ;   entero < 1000
    ADD R5 R5 #1
    LD R4 todec_k10000
    SUB R7 R0 R4
    BRNC todec_int_nd                   ;   entero < 10000
todec_int_lz
    AND R5 R5 #0
    ADD R5 R5 #5
todec_int_nd
    ADDX R2 R2 R5                       ;   [R2] cursor despues de los digitos
    ADD R1 R2 #0                        ;   [R1] puntero de escritura (de derecha a izquierda)
    AND R4 R4 #0
    ADD R4 R4 #10                       ;   [R4] 10
    LD R3 todec_chr_zero                ;   [R3] '0' (el formato quedo en memoria)
todec_int_dig                           ;   do:
    DIVU R7 R0 R4                       ;       cociente
    REMU R0 R0 R4                       ;       digito
    ADD R0 R0 R3
    STR R0 R1 #-1                       ;       texto[--p] = char(digito)
    ADD R1 R1 #-2
    ADD R0 R7 #0                        ;       entero = cociente
    DBP R5 todec_int_dig                ;   while --digitos > 0
    LD R3 todec_format

;   ==- Prueba para retorno temprano -==========================================
todec_early
    ST R2 todec_cursor_wr               ;   la parte decimal usa [formato] y [cursor_wr]
    LD R1 todec_fraccion
    BRnp todec_dec                      ;   if fraccion == 0:
    AND R4 R3 #4
    BRz todec_early_chk                 ;       if formato & SHOW_ENDZ:
    LD R4 todec_chr_dot
    STR R4 R2 #0
    ADD R2 R2 #2                        ;           texto = texto + '.'
    LD R4 todec_chr_zero
    AND R5 R5 #0
    ADD R5 R5 #9
todec_early_z
    STR R4 R2 #0
    ADD R2 R2 #2                        ;           texto = texto + '0' (9 veces)
    DBP R5 todec_early_z
todec_early_chk
    AND R4 R4 #0
    STR R4 R2 #0                        ;       texto = texto + '\0'
    BR todec_ret                        ;       return

;   ==- Decimal -===============================================================
;   [G23] Seccion reescrita para la ISA G23 por el Grupo 23. Mismo algoritmo y
;   mismos resultados que la version del Grupo 27, pero con los valores en
;   registros y la suma de 32 bits con ADD + ADC (sin llamar a SUMOVER).
todec_dec
    LD R0 todec_chr_dot
    LD R1 todec_cursor_wr
    STR R0 R1 #0
    ADD R1 R1 #2                        ;   [G23] puntero en bytes
    ST R1 todec_cursor_wr               ;   texto = texto + '.'

;   Parte 1: [fraccion_h, fraccion_l] = suma de [aux_0, aux_1] por cada bit en 1
;   de la fraccion, con [aux_0, aux_1, aux_2] = 1_000_000_000 duplicado en cada bit.
;   [G23] Version 2: los bits 7 a 15 de la fraccion (H) suman exactamente
;   H * 10^9 / 2^9 = H * 1953125 (sin redondeo), asi que se calculan con una
;   multiplicacion; el lazo queda solo para los bits 0 a 6, donde cada termino
;   se trunca igual que en la original.
    LD R5 todec_fraccion
    LSR R2 R5 #7                        ;   [R2] H = fraccion >> 7
    LD R4 todec_k52581                  ;   1953125 = 29*65536 + 52581
    MUL R0 R2 R4                        ;   [R0] fraccion_l = parte baja de H*52581
    MULHU R1 R2 R4                      ;   [R1] fraccion_h = parte alta de H*52581
    LD R4 todec_k29
    MUL R4 R2 R4
    ADD R1 R1 R4                        ;   [R1:R0] = H * 1953125
    LSL R5 R5 #9
    LSR R5 R5 #9                        ;   [R5] bits 0 a 6 de la fraccion
    BRz todec_dec_p2                    ;   sin bits bajos: nada mas que sumar
    AND R4 R4 #0                        ;   [R4] aux_0 = 0
    LD R2 todec_frac_expr_h             ;   [R2] aux_1
    LD R3 todec_frac_expr_l             ;   [R3] aux_2   ([aux_0, aux_1, aux_2] = 10^9)
todec_dec_loop1                         ;   do:
    LSR R5 R5 #1                        ;       C = bit actual
    BRNC todec_dec_sk1                  ;       if bit:
    ADD R0 R0 R2                        ;           fraccion_l += aux_1      (C = acarreo)
    ADC R1 R1 R4                        ;           fraccion_h += aux_0 + C
todec_dec_sk1
    ADD R3 R3 R3                        ;       [aux_0, aux_1, aux_2] <<= 1
    ADC R2 R2 R2
    ADC R4 R4 R4
    BRRp R5 todec_dec_loop1             ;   while queden bits en 1

;   Parte 2 [G23]: los 9 digitos de F (F < 10^9) sin restas sucesivas.
;   F = a*10^6 + b*10^3 + c, con a, b, c < 1000; cada grupo da 3 digitos con
;   DIVU/REMU. Se escriben los 9 digitos y, salvo SHOW_ENDZ, se retrocede sobre
;   los ceros finales (la original cortaba cuando lo que quedaba era 0: mismo
;   texto). Metodo verificado con isa_g23/pruebas/modelo_digitos_todec.py.
;   a = F // 10^6: estimado con MULHU(Fh, 4294) y corregido una vez
todec_dec_p2
    LD R4 todec_k4294
    MULHU R2 R1 R4                      ;   [R2] a (estimado, a lo sumo 1 menos)
    LD R4 todec_k16960
    MUL R3 R2 R4                        ;   a*10^6 = a*16960 + a*15*65536
    MULHU R5 R2 R4
    AND R4 R4 #0
    ADD R4 R4 #15
    MUL R4 R2 R4
    ADD R5 R5 R4                        ;   [R5:R3] a*10^6
    NOT R5 R5
    SUB R0 R0 R3                        ;   [R1:R0] R = F - a*10^6  (C = no hubo prestamo)
    ADC R1 R1 R5
    AND R7 R7 #0
    ADD R7 R7 #-16                      ;   (antes de la resta: ADD cambia C)
    LD R4 todec_k16960
    SUB R3 R0 R4                        ;   R - 10^6
    ADC R5 R1 R7                        ;   parte alta: Rh - 16 + C
    BRn todec_dec_rok                   ;   if R >= 10^6:
    ADD R0 R3 #0
    ADD R1 R5 #0                        ;       R = R - 10^6
    ADD R2 R2 #1                        ;       a = a + 1
todec_dec_rok
;   b = R // 1000, c = R % 1000, con R = Rh*65536 + Rl = 1000*(65*Rh) + (536*Rh + Rl)
    LD R4 todec_k536
    MUL R3 R1 R4                        ;   536*Rh
    ADD R3 R3 R0                        ;   t = 536*Rh + Rl  (C = acarreo)
    BRNC todec_dec_t
    ADD R3 R3 R4                        ;   t >= 65536: t = (t - 65536) + 536
    ADD R1 R1 #1                        ;   y 65 mas para b
todec_dec_t
    LD R4 todec_k65
    MUL R1 R1 R4                        ;   65*Rh
    LD R4 todec_k1000
    DIVU R5 R3 R4
    ADD R1 R1 R5                        ;   [R1] b
    REMU R3 R3 R4                       ;   [R3] c
;   escribir los 9 digitos
    LD R0 todec_cursor_wr
    ADD R4 R2 #0
    JSR todec_3dig                      ;   a
    ADD R4 R1 #0
    JSR todec_3dig                      ;   b
    ADD R4 R3 #0
    JSR todec_3dig                      ;   c
;   sin SHOW_ENDZ: quitar los ceros finales (F > 0: siempre queda un digito)
    LD R4 todec_format
    AND R4 R4 #4
    BRnp todec_dec_fin
    LD R5 todec_neg_zero                ;   [R5] -'0'
    AND R2 R2 #0                        ;   [R2] 0
    LDR R4 R0 #-1
    ADD R4 R4 R5
    BRnp todec_dec_fin                  ;   while ultimo caracter == '0':
todec_dec_trim                          ;   (lazo con la prueba al final)
    ADD R0 R0 #-2                       ;       retroceder el cursor
    STR R2 R0 #0                        ;       y borrar el '0' (el buffer queda igual
    LDR R4 R0 #-1                       ;       que con la version original)
    ADD R4 R4 R5
    BRz todec_dec_trim
todec_dec_fin
    AND R4 R4 #0
    STR R4 R0 #0                        ;   texto = texto + '\0'
    BR todec_ret

;   todec_3dig: escribe los 3 digitos de R4 (< 1000) en el cursor R0 y lo avanza.
;   Usa R2 y R5; conserva R1 y R3.
todec_3dig
    LD R5 todec_k100
    DIVU R2 R4 R5
    REMU R4 R4 R5
    LD R5 todec_chr_zero
    ADD R2 R2 R5
    STR R2 R0 #0                        ;   centenas
    AND R5 R5 #0
    ADD R5 R5 #10
    DIVU R2 R4 R5
    REMU R4 R4 R5
    LD R5 todec_chr_zero
    ADD R2 R2 R5
    STR R2 R0 #1                        ;   decenas
    ADD R4 R4 R5
    STR R4 R0 #2                        ;   unidades
    ADD R0 R0 #6
    RET

todec_k4294         .FILL #4294
todec_k52581        .FILL xCD65         ;   52581
todec_k29           .FILL #29
todec_k16960        .FILL #16960
todec_k536          .FILL #536
todec_k65           .FILL #65
todec_k1000         .FILL #1000
todec_k100          .FILL #100

;   ==- Return -================================================================
todec_ret
    LD R2 todec_cursor_beg              ;   [R2] puntero al buffer
    POP R0 R1 R3 R4 R5 R7
    RET

todec_k10000        .FILL #10000

todec_fraccion      .FILL #0
todec_cursor_beg    .FILL #0
todec_cursor_wr     .FILL #0
todec_format        .FILL #0


todec_chr_plus      .FILL #43           ;   ord('+')
todec_chr_minus     .FILL #45           ;   ord('-')
todec_chr_dot       .FILL #46           ;   ord('.')
todec_chr_zero      .FILL #48           ;   ord('0')
todec_neg_zero      .FILL #-48          ;   -ord('0')

todec_frac_expr_h   .FILL x3B9A         ;
todec_frac_expr_l   .FILL xCA00         ;   1_000_000_000


.END
