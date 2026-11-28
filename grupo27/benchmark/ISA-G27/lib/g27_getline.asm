;=====================================================================
; SUBRUTINA: GETLINE (Lectura de cadena de 8 bits por teclado en ISA-G27)
;
;   -> INPUT  [R0] Puntero (dirección de byte) al inicio del buffer.
;   -> INPUT  [R1] Puntero (dirección de byte) 1 más allá del final del buffer.
;   <- OUTPUT [R0] Puntero al inicio del buffer (cadena terminada en '\0').
;   Conserva: R1-R7 (todos intactos, incluyendo R6).
;=====================================================================
GETLINE:
        ST      R0, getline_buffer_beg
        ST      R1, getline_r1
        ST      R2, getline_r2
        ST      R3, getline_r3
        ST      R7, getline_r7

        LD      R2, getline_buffer_beg  ; R2 = cursor (dirección base en bytes)
        NOT     R1, R1
        ADD     R1, R1, #2              ; R1 = -(buffer_end - 1) para reservar '\0'

getline_loop:
        GETC                            ; R0 = carácter leído (8 bits)
        ADD     R3, R0, #-8
        ADD     R3, R3, #-2             ; ¿Carácter == '\n' (10)?
        BRz     getline_ret

        OUT                             ; Mostrar carácter en consola

        ADD     R3, R2, R1              ; ¿cursor >= (buffer_end - 1)?
        BRzp    getline_loop            ; Si está lleno, ignorar escritura

        STRB    R0, R2, #0              ; Guardar byte en [R2 + 0] (BaseR + Buoffset5)
        ADD     R2, R2, #1              ; Avanzar puntero 1 byte
        BR      getline_loop

getline_ret:
        AND     R0, R0, #0
        ADD     R0, R0, #7
        ADD     R0, R0, #3              ; R0 = #10 ('\n')
        OUT

        AND     R0, R0, #0
        STRB    R0, R2, #0              ; Escribir terminador nulo '\0' en [R2 + 0]

        LD      R0, getline_buffer_beg
        LD      R1, getline_r1
        LD      R2, getline_r2
        LD      R3, getline_r3
        LD      R7, getline_r7
        RET

;=====================================================================
; ZONA DE DATOS
;=====================================================================
getline_buffer_beg: .FILL #0
getline_r1:         .FILL #0
getline_r2:         .FILL #0
getline_r3:         .FILL #0
getline_r7:         .FILL #0

.END