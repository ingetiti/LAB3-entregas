;   ============================================================================
;   Subrutina: TODEC   (version optimizada con MUL/MULH/DIV/REM/SHR de la ISA Grupo 7)
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
;   -> INPUT  [R2] Puntero al buffer de la cadena (17 BYTES minimo).
;   -> INPUT  [R3] Formato bits [15:3 none, 2 SHOW_ENDZ, 1 SHOW_LEADZ, 0 SHOW_PLUS]
;   <- OUTPUT [R2] Puntero al buffer de la cadena ya cargada.
;
;   Idea: la parte fraccionaria A (16 bits) equivale a F = 15258*A + 101*(A>>7) + U(A&127)
;   (donde U suma pesos fijos por cada bit bajo), un entero de 9 digitos decimales.
;   F se guarda en base 2^15 (H,L) para dividirlo por 10 con DIV de 16 bits.
;   Resultado identico a la version original (suma de potencias de 2 truncadas).
;   ============================================================================

TODEC                                   ;
    ADD R6 R6 #-16                      ;   marco de pila de 18 bytes (9 palabras)
    ADD R6 R6 #-2                       ;
    STR R0 R6 #0                        ;
    STR R1 R6 #1                        ;
    STR R3 R6 #2                        ;   [2] = formato
    STR R4 R6 #3                        ;
    STR R5 R6 #4                        ;
    STR R7 R6 #5                        ;
    STR R2 R6 #6                        ;   [6] = inicio del buffer

;   ==- Signo -=================================================================
    ADD R0 R0 #0                        ;
    BRzp todec_pos                      ;   if entero < 0:
    LD R4 todec_chr_minus               ;
    STB R4 R2 #0                        ;
    ADD R2 R2 #1                        ;       texto = '-'
    NOT R0 R0                           ;
    ADD R1 R1 #0                        ;
    BRnp todec_neg1                     ;
    ADD R0 R0 #1                        ;
todec_neg1                              ;
    NOT R1 R1                           ;
    ADD R1 R1 #1                        ;       [entero, fraccion] = -[entero, fraccion]
    BRnzp todec_int                     ;
todec_pos                               ;
    AND R4 R3 #1                        ;
    BRz todec_int                       ;   elif formato & SHOW_PLUS:
    LD R4 todec_chr_plus                ;
    STB R4 R2 #0                        ;
    ADD R2 R2 #1                        ;       texto = '+'

;   ==- Entero -================================================================
todec_int                               ;
    STR R1 R6 #7                        ;   [7] = fraccion
    LD R3 todec_chr_zero                ;   [R3] = '0'
    LD R5 todec_k10                     ;   [R5] = 10
    ADD R0 R0 #0                        ;
    BRn todec_big                       ;   caso especial entero = x8000 (-32768)
    AND R4 R4 #0                        ;
    ADD R4 R4 #5                        ;   [R4] largo = 5
    LDR R7 R6 #2                        ;
    AND R7 R7 #2                        ;
    BRnp todec_wr                       ;   if formato & SHOW_LEADZ: largo = 5
    ADD R4 R4 #-4                       ;   largo = 1
    ADD R7 R0 #0                        ;
todec_len                               ;
    DIV R7 R7 R5                        ;
    BRz todec_wr                        ;   mientras entero/10^k != 0:
    ADD R4 R4 #1                        ;       largo = largo + 1
    BR todec_len                        ;
todec_wr                                ;
    ADD R2 R2 R4                        ;   cursor despues de los digitos
    ADD R1 R2 #0                        ;
todec_wl                                ;   escribe los digitos de derecha a izquierda
    ADD R1 R1 #-1                       ;
    REM R7 R0 R5                        ;
    DIV R0 R0 R5                        ;
    ADD R7 R7 R3                        ;
    STB R7 R1 #0                        ;
    ADD R4 R4 #-1                       ;
    BRp todec_wl                        ;
    BR todec_fr                         ;

todec_big                               ;   entero = 32768: "3" + digitos de 2768
    LD R0 todec_k2768                   ;
    ADD R7 R3 #3                        ;
    STB R7 R2 #0                        ;
    ADD R2 R2 #1                        ;
    AND R4 R4 #0                        ;
    ADD R4 R4 #4                        ;
    BR todec_wr                         ;

;   ==- Fraccion -===============================================================
todec_fr                                ;
    LDR R1 R6 #7                        ;
    BRnp todec_dec                      ;   if fraccion == 0:
    LDR R7 R6 #2                        ;
    AND R7 R7 #4                        ;
    BRz todec_nul                       ;       if formato & SHOW_ENDZ:
    LD R4 todec_chr_dot                 ;
    STB R4 R2 #0                        ;
    ADD R2 R2 #1                        ;           '.'
    AND R4 R4 #0                        ;
    ADD R4 R4 #9                        ;
todec_ez                                ;
    STB R3 R2 #0                        ;           9 veces '0'
    ADD R2 R2 #1                        ;
    ADD R4 R4 #-1                       ;
    BRp todec_ez                        ;
todec_nul                               ;
    AND R3 R3 #0                        ;
    STB R3 R2 #0                        ;       '\0'
    BR todec_ret                        ;

todec_dec                               ;   [R1] = A (fraccion, 16 bits sin signo)
    LD R4 todec_chr_dot                 ;
    STB R4 R2 #0                        ;
    ADD R2 R2 #1                        ;   '.'
    STR R2 R6 #8                        ;   [8] = inicio de los 9 digitos
    LD R3 todec_k7FFF                   ;
    AND R4 R1 R3                        ;   a15 = A & 0x7FFF
    LD R5 todec_k15258                  ;
    MUL R7 R4 R5                        ;   P = 15258 * a15 (32 bits)
    MULH R4 R4 R5                       ;
    LD R0 todec_k15                     ;
    SHR R5 R7 R0                        ;
    AND R7 R7 R3                        ;   [R7] L = P & 0x7FFF
    ADD R4 R4 R4                        ;
    ADD R4 R4 R5                        ;   [R4] H = P >> 15
    SHR R5 R1 R0                        ;   s = bit 15 de A
    BRz todec_s0                        ;
    LD R5 todec_k15258                  ;
    ADD R4 R4 R5                        ;   H = H + 15258
todec_s0                                ;
    LD R0 todec_k7                      ;
    SHR R5 R1 R0                        ;   B = A >> 7
    LD R0 todec_k101                    ;
    MUL R5 R5 R0                        ;   S = 101 * B
    LD R0 todec_k127                    ;
    AND R1 R1 R0                        ;   c = A & 127
    LEA R0 todec_w                      ;
    LD R3 todec_k1                      ;
todec_u                                 ;   S = S + sum(pesos de los bits de c)
    ADD R1 R1 #0                        ;
    BRz todec_uend                      ;
    AND R2 R1 #1                        ;
    BRz todec_usk                       ;
    LDR R2 R0 #0                        ;
    ADD R5 R5 R2                        ;
todec_usk                               ;
    SHR R1 R1 R3                        ;
    ADD R0 R0 #2                        ;
    BR todec_u                          ;
todec_uend                              ;
    LD R3 todec_k7FFF                   ;
    LD R0 todec_k15                     ;
    AND R1 R5 R3                        ;   S bajo (15 bits)
    SHR R5 R5 R0                        ;   S alto (0 o 1)
    ADD R7 R7 R1                        ;
    SHR R1 R7 R0                        ;   acarreo
    AND R7 R7 R3                        ;   L = (L + S_bajo) & 0x7FFF
    ADD R4 R4 R5                        ;
    ADD R4 R4 R1                        ;   H = H + S_alto + acarreo   ->  F = H*32768 + L

    LDR R2 R6 #8                        ;
    ADD R2 R2 #8                        ;   [R2] ultimo digito
    LD R5 todec_k10                     ;
todec_dl                                ;   F / 10 en base 2^15 (L se divide aparte para no desbordar)
    REM R0 R4 R5                        ;   r1 = H % 10
    DIV R4 R4 R5                        ;   H = H / 10
    REM R1 R7 R5                        ;   l0 = L % 10
    DIV R7 R7 R5                        ;   l1 = L / 10
    LD R3 todec_k8                      ;
    MUL R3 R0 R3                        ;
    ADD R1 R1 R3                        ;   z = l0 + r1*8   (z <= 81)
    LD R3 todec_k3276                   ;
    MUL R0 R0 R3                        ;   r1 * 3276
    ADD R7 R7 R0                        ;
    DIV R0 R1 R5                        ;   z / 10
    REM R1 R1 R5                        ;   digito = z % 10
    ADD R7 R7 R0                        ;   L = l1 + r1*3276 + z/10
    LD R3 todec_chr_zero                ;
    ADD R1 R1 R3                        ;
    STB R1 R2 #0                        ;
    ADD R2 R2 #-1                       ;
    LDR R3 R6 #8                        ;
    SUB R3 R2 R3                        ;
    BRzp todec_dl                       ;   mientras cursor >= inicio

    LDR R2 R6 #8                        ;
    ADD R2 R2 #9                        ;
    AND R3 R3 #0                        ;
    STB R3 R2 #0                        ;   '\0'
    LDR R0 R6 #2                        ;
    AND R0 R0 #4                        ;
    BRnp todec_ret                      ;   if formato & SHOW_ENDZ: listo
    LD R1 todec_chr_zero                ;
todec_trim                              ;   quita los ceros finales
    ADD R2 R2 #-1                       ;
    LDBS R0 R2 #0                       ;
    SUB R0 R0 R1                        ;
    BRnp todec_ret                      ;
    STB R3 R2 #0                        ;
    BR todec_trim                       ;

;   ==- Return -================================================================
todec_ret                               ;
    LDR R0 R6 #0                        ;
    LDR R1 R6 #1                        ;
    LDR R2 R6 #6                        ;
    LDR R3 R6 #2                        ;
    LDR R4 R6 #3                        ;
    LDR R5 R6 #4                        ;
    LDR R7 R6 #5                        ;
    ADD R6 R6 #14                       ;
    ADD R6 R6 #4                        ;
    RET                                 ;

todec_chr_plus      .FILL #43           ;   ord('+')
todec_chr_minus     .FILL #45           ;   ord('-')
todec_chr_dot       .FILL #46           ;   ord('.')
todec_chr_zero      .FILL #48           ;   ord('0')
todec_k10           .FILL #10
todec_k8            .FILL #8
todec_k3276         .FILL #3276
todec_k15258        .FILL #15258
todec_k7FFF         .FILL x7FFF
todec_k15           .FILL #15
todec_k7            .FILL #7
todec_k101          .FILL #101
todec_k127          .FILL #127
todec_k1            .FILL #1
todec_k2768         .FILL #2768
todec_w             .FILL #0            ;   pesos floor(101*2^i/128), i = 0..6
                    .FILL #1
                    .FILL #3
                    .FILL #6
                    .FILL #12
                    .FILL #25
                    .FILL #50

.END
