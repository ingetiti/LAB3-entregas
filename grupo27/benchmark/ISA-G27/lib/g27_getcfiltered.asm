;=====================================================================
; SUBRUTINA: GETCFILTERED (Lectura filtrada de carácter de 8 bits)
;
;   Obtiene un carácter por teclado (GETC) que pertenezca a alguno de
;   los rangos inclusivos [min, max] definidos en la cadena de 8 bits
;   terminada en '\0' apuntada por R0 (ej. "09az" -> '0'-'9' o 'a'-'z').
;
;   -> INPUT  [R0] Puntero (dirección de byte) a la cadena de filtro
;   <- OUTPUT [R0] Carácter capturado válido
;   Conserva: R1-R7 (todos intactos, incluyendo R6).
;=====================================================================
GETCFILTERED:
        ST      R0, getcfiltered_filter_beg
        ST      R1, getcfiltered_r1
        ST      R2, getcfiltered_r2
        ST      R3, getcfiltered_r3
        ST      R7, getcfiltered_r7

getcfiltered_beg:
        GETC                                ; R0 = carácter leído (8 bits)
        LD      R1, getcfiltered_filter_beg ; R1 = puntero actual (en bytes) al filtro

getcfiltered_loop:
        LDRB    R2, R1, #0                  ; R2 = min (byte 0 del par)
        ADD     R2, R2, #0
        BRz     getcfiltered_beg            ; Fin de filtro ('\0') -> leer otro carácter

        LDRB    R3, R1, #1                  ; R3 = max (byte 1 del par)
        ADD     R3, R3, #0
        BRz     getcfiltered_beg            ; Filtro truncado/incompleto -> leer otro carácter

        ; Verificar char >= min  <=>  char - min >= 0
        NOT     R2, R2
        ADD     R2, R2, #1                  ; R2 = -min
        ADD     R2, R0, R2                  ; R2 = char - min
        BRn     getcfiltered_incr           ; char < min -> probar siguiente rango

        ; Verificar char <= max  <=>  max - char >= 0
        NOT     R2, R0
        ADD     R2, R2, #1                  ; R2 = -char
        ADD     R2, R3, R2                  ; R2 = max - char
        BRn     getcfiltered_incr           ; char > max -> probar siguiente rango

        BR      getcfiltered_ret            ; Cumple min <= char <= max -> retornar

getcfiltered_incr:
        ADD     R1, R1, #2                  ; Avanzar 2 bytes al siguiente par [min, max]
        BR      getcfiltered_loop

getcfiltered_ret:
        LD      R1, getcfiltered_r1
        LD      R2, getcfiltered_r2
        LD      R3, getcfiltered_r3
        LD      R7, getcfiltered_r7
        ADD     R0, R0, #0                  ; Actualizar CC con el carácter capturado
        RET

;=====================================================================
; ZONA DE DATOS
;=====================================================================
getcfiltered_filter_beg: .FILL #0
getcfiltered_r1:         .FILL #0
getcfiltered_r2:         .FILL #0
getcfiltered_r3:         .FILL #0
getcfiltered_r7:         .FILL #0

.END