;=====================================================================
; SUBRUTINA: FROMHEX (Convierte cadena hexadecimal de 8 bits a 16 bits)
;
;   -> INPUT  [R0] Puntero (dirección de byte) a cadena ASCII hex ('\0')
;   <- OUTPUT [R0] Valor entero de 16 bits acumulado
;   <- OUTPUT [R5] Banderas de error:
;                    bit 0 (1): INVALID_INPUT (cadena vacía o carácter no hex)
;                    bit 1 (2): OVERFLOW (más de 4 dígitos hexadecimales)
;   Conserva: R1-R4, R6 (intacto) y R7.
;=====================================================================
FROMHEX:
        ST      R1, fromhex_r1
        ST      R2, fromhex_r2
        ST      R3, fromhex_r3
        ST      R4, fromhex_r4

        ST      R0, fromhex_str_beg
        AND     R0, R0, #0              ; R0 = valor acumulado = 0
        LD      R1, fromhex_str_beg     ; R1 = puntero actual (en bytes)
        AND     R5, R5, #0              ; R5 = errores = 0

        LDRB    R2, R1, #0              ; Leer primer byte
        ADD     R2, R2, #0
        BRnp    fromhex_loop

        ; Cadena vacía -> marcar INVALID_INPUT (bit 0 = #1)
        AND     R4, R4, #0
        ADD     R4, R4, #1
        OR      R5, R5, R4
        BR      fromhex_ret

fromhex_loop:
        LDRB    R3, R1, #0              ; R3 = carácter actual (8 bits)
        ADD     R3, R3, #0
        BRz     fromhex_overflow_chk    ; Fin de cadena ('\0')

        AND     R2, R2, #0              ; R2 = 0 (indica no válido hasta reconocer dígito)

        ; Rango '0'..'9' (48..57) -> valor = char - 48
        LD      R4, fromhex_neg_zero
        ADD     R4, R4, R3
        BRn     fromhex_lower
        LD      R4, fromhex_neg_nine
        ADD     R4, R4, R3
        BRp     fromhex_lower
        LD      R2, fromhex_neg_zero    ; offset = -48

fromhex_lower:
        ; Rango 'a'..'f' (97..102) -> valor = char - 97 + 10 = char - 87
        LD      R4, fromhex_neg_a
        ADD     R4, R4, R3
        BRn     fromhex_upper
        LD      R4, fromhex_neg_f
        ADD     R4, R4, R3
        BRp     fromhex_upper
        LD      R2, fromhex_neg_a
        ADD     R2, R2, #7
        ADD     R2, R2, #3              ; offset = -97 + 10 = -87

fromhex_upper:
        ; Rango 'A'..'F' (65..70) -> valor = char - 65 + 10 = char - 55
        LD      R4, fromhex_neg_upa
        ADD     R4, R4, R3
        BRn     fromhex_invalid_chk
        LD      R4, fromhex_neg_upf
        ADD     R4, R4, R3
        BRp     fromhex_invalid_chk
        LD      R2, fromhex_neg_upa
        ADD     R2, R2, #7
        ADD     R2, R2, #3              ; offset = -65 + 10 = -55

fromhex_invalid_chk:
        ADD     R2, R2, #0
        BRnp    fromhex_increment       ; Carácter hex válido

        ; Carácter inválido -> marcar INVALID_INPUT (bit 0 = #1) y verificar longitud
        AND     R4, R4, #0
        ADD     R4, R4, #1
        OR      R5, R5, R4
        BR      fromhex_overflow_chk

fromhex_increment:
        LSH     R0, R0, #4              ; valor <<= 4 (inmediato #4)
        ADD     R0, R0, R3
        ADD     R0, R0, R2              ; valor += char + offset (0..15)
        ADD     R1, R1, #1              ; Avanzar 1 byte en la cadena
        BR      fromhex_loop

fromhex_overflow_chk:
        ; Si se leyeron más de 4 caracteres (R1 - str_beg > 4), activar OVERFLOW (bit 1 = #2)
        LD      R4, fromhex_str_beg
        ADD     R4, R4, #4
        NOT     R4, R4
        ADD     R4, R4, #1              ; R4 = -(str_beg + 4)
        ADD     R4, R1, R4              ; R4 = R1 - (str_beg + 4)
        BRnz    fromhex_ret

        AND     R4, R4, #0
        ADD     R4, R4, #2
        OR      R5, R5, R4              ; errores |= OVERFLOW (2)

fromhex_ret:
        LD      R1, fromhex_r1
        LD      R2, fromhex_r2
        LD      R3, fromhex_r3
        LD      R4, fromhex_r4
        ADD     R0, R0, #0              ; Actualizar CC con el valor obtenido
        RET

;=====================================================================
; ZONA DE DATOS Y CONSTANTES
;=====================================================================
fromhex_str_beg: .FILL #0
fromhex_r1:      .FILL #0
fromhex_r2:      .FILL #0
fromhex_r3:      .FILL #0
fromhex_r4:      .FILL #0

fromhex_neg_zero: .FILL #-48
fromhex_neg_nine: .FILL #-57
fromhex_neg_a:    .FILL #-97
fromhex_neg_f:    .FILL #-102
fromhex_neg_upa:  .FILL #-65
fromhex_neg_upf:  .FILL #-70

.END