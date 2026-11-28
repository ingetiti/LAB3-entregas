;   ============================================================================
;   Subrutina: FROMDEC
;       Convierte una cadena de texto decimal (1 byte por caracter) al valor
;       en punto fijo 16.16 correspondiente.
;       - En R0 la parte entera (signed 16-bit)
;       - En R1 la parte fraccionaria (2**-1, 2**-2, ...)
;       Optimizada para la nueva ISA con LDBL, SHL/RLC, ADC/SBC, NEG y PUSHM/POPM.
;       No requiere subrutina externa SUMOVER.
;
;   -> INPUT  [R0] Puntero de la cadena.
;   <- OUTPUT [R0] Parte entera obtenida.
;   <- OUTPUT [R1] Parte fraccionaria obtenida.
;   <- OUTPUT [R5] Error flag bits [15:2 none, 1 OVERFLOW, 0 INVALID_INPUT].
;   ============================================================================

FROMDEC
    PUSHM {R2, R3, R4, R6}              ;   preserva registros del caller

    MOV R4, R0                          ;   [R4] puntero texto (bytes)
    CLR R5                              ;   [R5] errores = 0
    CLR R3                              ;   [R3] entero = 0
    CLR R6                              ;   [R6] flags: bit0=has_number, bit1=negativo
    STPC R3, fromdec_fraccion           ;   [fraccion] = 0

;   ==- Signo -=================================================================
    LDBL R0, R4, #0                     ;   [R0] char = *texto
    MOVI R1, #-45                       ;   -ord('-')
    ADD R1, R1, R0                      ;
    BRnp fromdec_int_loop               ;   si char != '-', pasar a parte entera
    MOVI R6, #2                         ;   negativo = 1 (bit 1)
    ADDI R4, R4, #1                     ;   texto++

;   ==- Parte entera -==========================================================
fromdec_int_loop
    LDBL R0, R4, #0                     ;   [R0] char = *texto
    BRz fromdec_ret_prep                ;   if char == '\0': return

    MOVI R1, #-46                       ;   -ord('.')
    ADD R1, R1, R0                      ;
    BRz fromdec_int_period_found        ;
    MOVI R1, #-44                       ;   -ord(',')
    ADD R1, R1, R0                      ;
    BRnp fromdec_int_range_chk          ;

fromdec_int_period_found
    ADDI R4, R4, #1                     ;   texto++
    BR fromdec_dec                      ;   pasar a parte fraccionaria

fromdec_int_range_chk
    MOVI R1, #-48                       ;   -ord('0')
    ADD R0, R0, R1                      ;   R0 = char - '0'
    BRn fromdec_int_invalid             ;   char < '0'
    ADDI R1, R0, #-9                    ;
    BRp fromdec_int_invalid             ;   char > '9'

    LI R2, #3276                        ;   umbral de overflow entero
    CMP R3, R2                          ;
    BRgt fromdec_int_overflow           ;   entero > 3276 -> overflow
    BRlt fromdec_int_append             ;   entero < 3276 -> seguro

    ANDI R2, R6, #2                     ;   negativo (0 o 2)
    LSR R2, R2, #1                      ;   0 o 1
    ADDI R2, R2, #8                     ;   limite digito: 8 (pos) o 9 (neg)
    CMP R0, R2                          ;
    BRlt fromdec_int_append             ;   if digito >= 8 + negativo: overflow

fromdec_int_overflow
    MOVI R2, #2                         ;
    OR R5, R5, R2                       ;   errores |= OVERFLOW

fromdec_int_append
    SHL R2, R3, #2                      ;   entero * 4
    ADD R2, R2, R3                      ;   entero * 5
    SHL R3, R2, #1                      ;   entero * 10
    ADD R3, R3, R0                      ;   entero = entero * 10 + digito

    MOVI R2, #1                         ;
    OR R6, R6, R2                       ;   has_number = 1
    ADDI R4, R4, #1                     ;   texto++
    BR fromdec_int_loop

fromdec_int_invalid
    MOVI R2, #1                         ;
    OR R5, R5, R2                       ;   errores |= INVALID_INPUT
    BR fromdec_ret_prep

;   ==- Parte fraccionaria -====================================================
fromdec_dec
    STPC R3, fromdec_entero             ;   guarda parte entera
    STPC R6, fromdec_flags              ;   guarda flags (has_number, negativo)

    CLR R0                              ;   [R0:R1] fraccion_32 = 0 (alta:baja)
    CLR R1                              ;
    MOVI R6, #9                         ;   [R6] contador = 9 digitos

fromdec_dec_loop
    CLR R2                              ;   [R2] current = 0
    LDBL R3, R4, #0                     ;   [R3] char = *texto
    BRz fromdec_dec_mul10               ;   fin de cadena: rellenar con 0

    MOVI R2, #-48                       ;   -ord('0')
    ADD R2, R3, R2                      ;   R2 = char - '0'
    BRn fromdec_dec_badchr              ;
    ADDI R3, R2, #-9                    ;
    BRp fromdec_dec_badchr              ;
    ADDI R4, R4, #1                     ;   digito valido: texto++
    BR fromdec_dec_mul10                ;

fromdec_dec_badchr
    CLR R2                              ;   current = 0
    MOVI R3, #1                         ;
    OR R5, R5, R3                       ;   errores |= INVALID_INPUT

fromdec_dec_mul10
    PUSHM {R2}                          ;   guarda digito actual (0..9)
    MOV R2, R0                          ;   copia [R0:R1] en [R2:R3]
    MOV R3, R1                          ;
    SHL R1, R1, #1                      ;
    RLC R0, R0                          ;   * 2
    SHL R1, R1, #1                      ;
    RLC R0, R0                          ;   * 4
    ADD R1, R1, R3                      ;
    ADC R0, R0, R2                      ;   * 5
    SHL R1, R1, #1                      ;
    RLC R0, R0                          ;   * 10

    POPM {R2}                           ;   recupera digito actual
    CLR R3                              ;
    ADD R1, R1, R2                      ;
    ADC R0, R0, R3                      ;   [R0:R1] += current

    ADDI R6, R6, #-1                    ;   contador--
    BRp fromdec_dec_loop                ;

;   -- Conversion de decimal (base 10^9) a fraccion binaria (2^16) --
    CLR R2                              ;   [R2] fraccion = 0
    MOVI R6, #16                        ;   [R6] 16 bits + 1 paso de redondeo

fromdec_dec_loop2
    SHL R1, R1, #1                      ;
    RLC R0, R0                          ;   [R0:R1] *= 2

    LDPC R4, fromdec_c_lo               ;   1_000_000_000 parte baja
    LDPC R3, fromdec_c_hi               ;   1_000_000_000 parte alta
    SUB R4, R1, R4                      ;   [R3:R4] = [R0:R1] - 1_000_000_000
    SBC R3, R0, R3                      ;   C = 1 si [R0:R1] < 1_000_000_000
    BRc fromdec_dec_lt                  ;

    ;   [R0:R1] >= 1_000_000_000
    ADD R6, R6, #0                      ;   paso de redondeo (R6 == 0)?
    BRz fromdec_dec_round               ;
    ADDI R6, R6, #-1                    ;
    SHL R2, R2, #1                      ;   fraccion <<= 1
    INC R2                              ;   fraccion |= 1
    MOV R0, R3                          ;   [R0:R1] = [R3:R4]
    MOV R1, R4                          ;
    BR fromdec_dec_loop2                ;

fromdec_dec_lt
    ADD R6, R6, #0                      ;   paso de redondeo (R6 == 0)?
    BRz fromdec_dec_done                ;
    ADDI R6, R6, #-1                    ;
    SHL R2, R2, #1                      ;   fraccion <<= 1
    BR fromdec_dec_loop2                ;

fromdec_dec_round
    INC R2                              ;   fraccion += 1
    BRnp fromdec_dec_done               ;   si fraccion == 0 (wrap), entero += 1
    LDPC R0, fromdec_entero             ;
    INC R0                              ;
    STPC R0, fromdec_entero             ;

fromdec_dec_done
    STPC R2, fromdec_fraccion           ;
    LDPC R3, fromdec_entero             ;
    LDPC R6, fromdec_flags              ;

;   ==- Return -================================================================
fromdec_ret_prep
    ANDI R0, R6, #1                     ;   has_number == 0?
    BRnp fromdec_ret_chk_neg            ;
    MOVI R0, #1                         ;
    OR R5, R5, R0                       ;   errores |= INVALID_INPUT

fromdec_ret_chk_neg
    MOV R0, R3                          ;   [R0] entero
    LDPC R1, fromdec_fraccion           ;   [R1] fraccion
    ANDI R2, R6, #2                     ;   negativo?
    BRz fromdec_ret                     ;
    NOT R0, R0                          ;   [R0:R1] = -[R0:R1] (32 bits)
    NEG R1, R1                          ;
    BRnp fromdec_ret                    ;
    INC R0                              ;

fromdec_ret
    POPM {R2, R3, R4, R6}               ;
    RET                                 ;


fromdec_entero          .FILL #0
fromdec_fraccion        .FILL #0
fromdec_flags           .FILL #0
fromdec_c_hi            .FILL x3B9A
fromdec_c_lo            .FILL xCA00     ;   1_000_000_000

.END
