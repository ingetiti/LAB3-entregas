;   ============================================================================
;   Subrutina: FROMHEX
;       Convierte una cadena de texto hexadecimal (1 byte por caracter) al valor
;       correspondiente de 16 bits.
;       Optimizada para la nueva ISA con LDBL, SHL #4, PUSHM/POPM y MOVI.
;
;   -> INPUT  [R0] Puntero a la cadena.
;   <- OUTPUT [R0] Valor obtenido.
;   <- OUTPUT [R5] Banderas de error [15:2 none, 1 OVERFLOW, 0 INVALID_INPUT].
;   ============================================================================

FROMHEX
    PUSHM {R1, R2, R3, R4}              ;   preserva registros del caller

    MOV R1, R0                          ;   [R1] puntero texto
    CLR R0                              ;   [R0] valor = 0
    CLR R4                              ;   [R4] contador de digitos = 0
    CLR R5                              ;   [R5] errores = 0

fromhex_loop
    LDBL R2, R1, #0                     ;   [R2] char = *texto (byte sin signo)
    BRz fromhex_end                     ;   fin de cadena '\0'

    MOVI R3, #-48                       ;   -ord('0')
    ADD R2, R2, R3                      ;   R2 = char - '0'
    BRn fromhex_invalid                 ;   char < '0' -> invalido
    ADDI R3, R2, #-9                    ;
    BRnz fromhex_got_digit              ;   '0' <= char <= '9' -> R2 ya es 0..9

    MOVI R3, #-17                       ;   -(ord('A') - ord('0'))
    ADD R2, R2, R3                      ;   R2 = char - 'A'
    BRn fromhex_invalid                 ;   '9' < char < 'A' -> invalido
    ADDI R3, R2, #-5                    ;
    BRnz fromhex_alpha                  ;   'A' <= char <= 'F'

    MOVI R3, #-32                       ;   -(ord('a') - ord('A'))
    ADD R2, R2, R3                      ;   R2 = char - 'a'
    BRn fromhex_invalid                 ;   'F' < char < 'a' -> invalido
    ADDI R3, R2, #-5                    ;
    BRp fromhex_invalid                 ;   char > 'f' -> invalido

fromhex_alpha
    ADDI R2, R2, #10                    ;   digito hex 10..15

fromhex_got_digit
    SHL R0, R0, #4                      ;   valor <<= 4
    ADD R0, R0, R2                      ;   valor += digito
    ADDI R1, R1, #1                     ;   texto++ (1 byte)
    ADDI R4, R4, #1                     ;   digitos++
    BR fromhex_loop

fromhex_end
    ADD R4, R4, #0                      ;   cadena vacia si digitos == 0
    BRnp fromhex_overflow_chk

fromhex_invalid
    MOVI R3, #1                         ;
    OR R5, R5, R3                       ;   errores |= INVALID_INPUT

fromhex_overflow_chk
    ADDI R4, R4, #-4                    ;   mas de 4 digitos?
    BRnz fromhex_ret                    ;
    MOVI R3, #2                         ;
    OR R5, R5, R3                       ;   errores |= OVERFLOW

fromhex_ret
    POPM {R1, R2, R3, R4}               ;
    RET

.END
