;   ============================================================================
;   Subrutina: TODEC
;       Convierte un valor en punto fijo 16.16 a cadena de texto decimal
;       (1 byte por caracter).
;       Utilizara el formato indicado, donde los bits indican:
;       - Bit 0: mostrar signo '+' (SHOW_PLUS).
;       - Bit 1: mantener ceros a izquierda (SHOW_LEADZ).
;       - Bit 2: mantener ceros a derecha (SHOW_ENDZ).
;       Optimizada para la nueva ISA con STBL, LSR/SHL/RLC, ADC, NEG y PUSHM/POPM.
;       No requiere subrutina externa SUMOVER.
;
;   -> INPUT  [R0] Parte entera.
;   -> INPUT  [R1] Parte fraccionaria.
;   -> INPUT  [R2] Puntero al buffer de la cadena (17 bytes minimo).
;   -> INPUT  [R3] Formato bits [15:3 none, 2 SHOW_ENDZ, 1 SHOW_LEADZ, 0 SHOW_PLUS]
;   <- OUTPUT [R2] Puntero al buffer de la cadena ya cargada.
;   ============================================================================

TODEC
    PUSHM {R0, R1, R2, R3, R4, R5, R6}  ;   preserva registros del caller (incluye R2)

;   ==- Signo -=================================================================
    ADD R0, R0, #0                      ;   entero < 0?
    BRzp todec_sig_elif                 ;
    MOVI R4, #45                        ;   '-'
    STBL R4, R2, #0                     ;
    ADDI R2, R2, #1                     ;   cursor++

    NOT R0, R0                          ;   [R0:R1] = -[R0:R1] (32 bits)
    NEG R1, R1                          ;
    BRnp todec_int                      ;
    INC R0                              ;   carry si fraccion == 0
    BR todec_int                        ;

todec_sig_elif
    ANDI R4, R3, #1                     ;   format & SHOW_PLUS?
    BRz todec_int                       ;
    MOVI R4, #43                        ;   '+'
    STBL R4, R2, #0                     ;
    ADDI R2, R2, #1                     ;   cursor++

;   ==- Entero -================================================================
todec_int
    PUSHM {R1}                          ;   guarda fraccion en pila, libera R1
    ANDI R1, R3, #2                     ;   sin ceros a izquierda?
    BRnp todec_int_full                 ;
    ADDI R1, R0, #-10                   ;
    BRzp todec_int_full                 ;   entero >= 10?
    MOVI R1, #48                        ;   emitir directamente el unico digito
    ADD R1, R1, R0                      ;
    STBL R1, R2, #0                     ;
    ADDI R2, R2, #1                     ;
    BR todec_early                      ;

todec_int_full
    LEA R5, todec_expr_vec              ;
    ADDI R5, R5, #15                    ;   +16 bytes (8 words: comienza en -10000)
    ADDI R5, R5, #1                     ;
    LDW R4, R5, #1                      ;   [R4] -expr_actual = -10_000
    CLR R6                              ;   [R6] contador = 0

todec_int_loop
    ADD R1, R0, R4                      ;   aux = entero + (-expr_actual)
    BRn todec_int_format_chk            ;   if aux >= 0:
    INC R6                              ;       contador++
    MOV R0, R1                          ;       entero = aux
    BR todec_int_loop                   ;

todec_int_format_chk
    ANDI R1, R3, #2                     ;   format & SHOW_LEADZ?
    BRnp todec_int_append               ;
    ADD R6, R6, #0                      ;   contador != 0?
    BRz todec_int_sk1                   ;

todec_int_append
    MOVI R1, #2                         ;
    OR R3, R3, R1                       ;   format |= SHOW_LEADZ
    MOVI R1, #48                        ;   '0'
    ADD R1, R1, R6                      ;
    STBL R1, R2, #0                     ;   *cursor = '0' + contador
    ADDI R2, R2, #1                     ;   cursor++

todec_int_sk1
    CLR R6                              ;   contador = 0
    ADDI R5, R5, #4                     ;   siguiente entrada de 32 bits (4 bytes)
    LDW R4, R5, #1                      ;   -expr_actual
    BRnp todec_int_loop                 ;   si != 0, continuar

    ANDI R1, R3, #2                     ;   se mostro algun digito?
    BRnp todec_early                    ;
    MOVI R1, #48                        ;   '0'
    STBL R1, R2, #0                     ;   *cursor = '0'
    ADDI R2, R2, #1                     ;   cursor++

;   ==- Prueba para retorno temprano -==========================================
todec_early
    POPM {R1}                           ;   recupera fraccion (preserva flags)
    ADD R1, R1, #0                      ;   fraccion == 0?
    BRnp todec_dec                      ;

    ANDI R4, R3, #4                     ;   format & SHOW_ENDZ?
    BRz todec_early_end                 ;
    MOVI R4, #46                        ;   '.'
    STBL R4, R2, #0                     ;
    ADDI R2, R2, #1                     ;   cursor++
    MOVI R4, #48                        ;   '0'
    MOVI R6, #9                         ;   9 ceros finales

todec_early_zero_loop
    STBL R4, R2, #0                     ;
    ADDI R2, R2, #1                     ;   cursor++
    ADDI R6, R6, #-1                    ;
    BRp todec_early_zero_loop           ;

todec_early_end
    CLR R4                              ;
    STBL R4, R2, #0                     ;   *cursor = '\0'
    POPM {R0, R1, R2, R3, R4, R5, R6}   ;   restaura registros (R2 = cursor_beg)
    RET                                 ;

;   ==- Decimal -===============================================================
todec_dec
    MOVI R4, #46                        ;   '.'
    STBL R4, R2, #0                     ;
    ADDI R2, R2, #1                     ;   cursor++

    STPC R3, todec_format               ;   guarda formato
    PUSHM {R2}                          ;   guarda cursor_wr en pila

    ;   [R0:R1] = suma exacta de las contribuciones de cada bit fraccionario
    MOV R5, R1                          ;   [R5] fraccion
    CLR R0                              ;   [R0:R1] acumulador = 0
    CLR R1                              ;
    ANDI R6, R5, #15                    ;   nibble menos significativo
    SHL R6, R6, #2                      ;   cada entrada ocupa dos palabras
    LEA R4, todec_frac_lut0
    ADD R4, R4, R6
    LDW R2, R4, #0
    LDW R3, R4, #1
    ADD R1, R1, R3
    ADC R0, R0, R2

    LSR R6, R5, #4
    ANDI R6, R6, #15
    SHL R6, R6, #2
    LEA R4, todec_frac_lut1
    ADD R4, R4, R6
    LDW R2, R4, #0
    LDW R3, R4, #1
    ADD R1, R1, R3
    ADC R0, R0, R2

    LSR R6, R5, #8
    ANDI R6, R6, #15
    SHL R6, R6, #2
    LEA R4, todec_frac_lut2
    ADD R4, R4, R6
    LDW R2, R4, #0
    LDW R3, R4, #1
    ADD R1, R1, R3
    ADC R0, R0, R2

    LSR R6, R5, #12
    ANDI R6, R6, #15
    SHL R6, R6, #2
    LEA R4, todec_frac_lut3
    ADD R4, R4, R6
    LDW R2, R4, #0
    LDW R3, R4, #1
    ADD R1, R1, R3
    ADC R0, R0, R2

    POPM {R2}                           ;   recupera cursor_wr
    LEA R5, todec_expr_vec              ;   [R5] tabla de -10^8 .. -10^0
    CLR R6                              ;   [R6] contador = 0

todec_dec_loop2
    LDW R4, R5, #1                      ;   -expr baja
    LDW R3, R5, #0                      ;   -expr alta
todec_dec_sub
    ADD R1, R1, R4                      ;   probar restar -expr_actual
    ADC R0, R0, R3                      ;
    BRn todec_dec_restore               ;   si < 0, restaurar el acumulador
    INC R6                              ;   contador++
    BR todec_dec_sub                    ;

todec_dec_restore
    NOT R4, R4                          ;   R3:R4 = expr_actual
    NOT R3, R3                          ;
    INC R4                              ;
    BRnp todec_dec_restore_add          ;
    INC R3                              ;
todec_dec_restore_add
    ADD R1, R1, R4                      ;   restaurar el valor anterior
    ADC R0, R0, R3                      ;
    BR todec_dec_append                 ;

todec_dec_append
    MOVI R4, #48                        ;   '0'
    ADD R4, R4, R6                      ;
    STBL R4, R2, #0                     ;   *cursor = '0' + contador
    ADDI R2, R2, #1                     ;   cursor++

    LDPC R4, todec_format               ;
    ANDI R4, R4, #4                     ;   SHOW_ENDZ?
    BRnp todec_dec_continue2            ;
    OR R4, R0, R1                       ;   [R0:R1] == 0?
    BRz todec_dec_break2                ;   terminar si no SHOW_ENDZ y resto == 0

todec_dec_continue2
    CLR R6                              ;   contador = 0
    ADDI R5, R5, #4                     ;   siguiente entrada (4 bytes)
    LDW R4, R5, #1                      ;
    BRnp todec_dec_loop2                ;
    LDW R4, R5, #0                      ;
    BRnp todec_dec_loop2                ;   si entrada != 0, continuar

todec_dec_break2
    CLR R4                              ;
    STBL R4, R2, #0                     ;   *cursor = '\0'
    POPM {R0, R1, R2, R3, R4, R5, R6}   ;   restaura registros (R2 = cursor_beg)
    RET                                 ;


todec_format        .FILL #0
; Cada entrada LUT guarda alto/bajo de la suma legacy para un nibble.
todec_frac_lut0
                    .FILL x0000
                    .FILL x0000
                    .FILL x0000
                    .FILL x3B9A
                    .FILL x0000
                    .FILL x7735
                    .FILL x0000
                    .FILL xB2CF
                    .FILL x0000
                    .FILL xEE6B
                    .FILL x0001
                    .FILL x2A05
                    .FILL x0001
                    .FILL x65A0
                    .FILL x0001
                    .FILL xA13A
                    .FILL x0001
                    .FILL xDCD6
                    .FILL x0002
                    .FILL x1870
                    .FILL x0002
                    .FILL x540B
                    .FILL x0002
                    .FILL x8FA5
                    .FILL x0002
                    .FILL xCB41
                    .FILL x0003
                    .FILL x06DB
                    .FILL x0003
                    .FILL x4276
                    .FILL x0003
                    .FILL x7E10
todec_frac_lut1
                    .FILL x0000
                    .FILL x0000
                    .FILL x0003
                    .FILL xB9AC
                    .FILL x0007
                    .FILL x7359
                    .FILL x000B
                    .FILL x2D05
                    .FILL x000E
                    .FILL xE6B2
                    .FILL x0012
                    .FILL xA05E
                    .FILL x0016
                    .FILL x5A0B
                    .FILL x001A
                    .FILL x13B7
                    .FILL x001D
                    .FILL xCD65
                    .FILL x0021
                    .FILL x8711
                    .FILL x0025
                    .FILL x40BE
                    .FILL x0028
                    .FILL xFA6A
                    .FILL x002C
                    .FILL xB417
                    .FILL x0030
                    .FILL x6DC3
                    .FILL x0034
                    .FILL x2770
                    .FILL x0037
                    .FILL xE11C
todec_frac_lut2
                    .FILL x0000
                    .FILL x0000
                    .FILL x003B
                    .FILL x9ACA
                    .FILL x0077
                    .FILL x3594
                    .FILL x00B2
                    .FILL xD05E
                    .FILL x00EE
                    .FILL x6B28
                    .FILL x012A
                    .FILL x05F2
                    .FILL x0165
                    .FILL xA0BC
                    .FILL x01A1
                    .FILL x3B86
                    .FILL x01DC
                    .FILL xD650
                    .FILL x0218
                    .FILL x711A
                    .FILL x0254
                    .FILL x0BE4
                    .FILL x028F
                    .FILL xA6AE
                    .FILL x02CB
                    .FILL x4178
                    .FILL x0306
                    .FILL xDC42
                    .FILL x0342
                    .FILL x770C
                    .FILL x037E
                    .FILL x11D6
todec_frac_lut3
                    .FILL x0000
                    .FILL x0000
                    .FILL x03B9
                    .FILL xACA0
                    .FILL x0773
                    .FILL x5940
                    .FILL x0B2D
                    .FILL x05E0
                    .FILL x0EE6
                    .FILL xB280
                    .FILL x12A0
                    .FILL x5F20
                    .FILL x165A
                    .FILL x0BC0
                    .FILL x1A13
                    .FILL xB860
                    .FILL x1DCD
                    .FILL x6500
                    .FILL x2187
                    .FILL x11A0
                    .FILL x2540
                    .FILL xBE40
                    .FILL x28FA
                    .FILL x6AE0
                    .FILL x2CB4
                    .FILL x1780
                    .FILL x306D
                    .FILL xC420
                    .FILL x3427
                    .FILL x70C0
                    .FILL x37E1
                    .FILL x1D60

todec_expr_vec      .FILL xfa0a
                    .FILL x1f00         ;  - 10**8          9no digito.
                    .FILL xff67
                    .FILL x6980         ;  - 10**7          8vo digito.
                    .FILL xfff0
                    .FILL xbdc0         ;  - 10**6          7to digito.
                    .FILL xfffe
                    .FILL x7960         ;  - 10**5          6to digito.
                    .FILL xffff
                    .FILL xd8f0         ;  - 10**4          5to digito.
                    .FILL xffff
                    .FILL xfc18         ;  - 10**3          4to digito.
                    .FILL xffff
                    .FILL xff9c         ;  - 10**2          3er digito.
                    .FILL xffff
                    .FILL xfff6         ;  - 10**1          2do digito.
                    .FILL xffff
                    .FILL xffff         ;  - 10**0          1er digito.
                    .FILL x0000
                    .FILL x0000         ;  NULL32           terminacion.

.END
