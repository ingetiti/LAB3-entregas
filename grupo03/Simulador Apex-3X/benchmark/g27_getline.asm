
; ============================================================================
; Subrutina: GETLINE  [LC-3X — adaptada]
;     Obtiene una cadena desde el teclado (hasta '\n') y la guarda en el
;     buffer dado.  El cursor del buffer se opera en BYTES (1 byte por char).
;
;     Cambios respecto al original LC-3:
;       1. STR / LDR tienen desplazamiento en BYTES en LC-3X.
;          "STR R0, R2, #0" -> despl=0 (par) OK.
;          "STR R0, R2, #1" seria IMPAR -> ERROR.
;          Aqui el desplazamiento es 0 en ambas stores, correcto.
;       2. Avance de cursor: ADD R2, R2, #1  (1 byte por char)  -> OK.
;          En LC-3 original habia que avanzar 1 "word"; en LC-3X el buffer
;          se trata como byte-array, 1 caracter = 1 byte, misma instruccion.
;       3. ADD R0, R0, #-10 -> rango imm4 permitido (-8..7) -> FUERA DE RANGO.
;          Reemplazado por MOVI R3, #10 + NOT R3, R3 + ADD R3, R3, #1 (NEG).
;          Luego ADD R3, R0, R3 para comparar con '\n'.
;       4. ADD R0, R0, #10 (para imprimir '\n') -> FUERA DE RANGO.
;          Reemplazado por MOVI R0, #10.
;
; -> INPUT  [R0] Puntero al inicio del buffer.
; -> INPUT  [R1] Puntero a 1 pasando del final del buffer.
; <- OUTPUT [R0] Puntero al buffer (con la cadena guardada).
; ============================================================================
GETLINE
    ST R0 getline_buffer_beg
    ST R1 getline_r1
    ST R2 getline_r2
    ST R3 getline_r3
    ST R7 getline_r7

    LD R2 getline_buffer_beg    ; [R2] cursor = buffer_beg
    NOT R1 R1
    ADD R1 R1 #2                ; [R1] -(buffer_end - 1)  para comparacion

getline_loop                    ; while True:
    GETC                        ;   [R0] char = getc()

    ; Comparar char con '\n' (ASCII 10)
    MOVI R3 #10
    NEG R3 R3                   ; R3 = -10
    ADD R3 R3 R0                ; R3 = char - 10
    BRz getline_ret             ;   if char == '\n': break

    OUT                         ;   putc(char)

    ADD R3 R2 R1
    BRzp getline_loop           ;   if cursor >= buffer_end-1: continue

    STBL R0 R2 #0               ;   cursor[0] = char  (byte store)
    ADD R2 R2 #1                ;   cursor++
    BRnzp getline_loop

getline_ret
    MOVI R0 #10
    OUT                         ; putc('\n')
    AND R0 R0 #0
    STBL R0 R2 #0               ; cursor[0] = '\0'  (byte store)

    LD R0 getline_buffer_beg
    LD R1 getline_r1
    LD R2 getline_r2
    LD R3 getline_r3
    LD R7 getline_r7
    RET

getline_buffer_beg  .FILL #0
getline_r1          .FILL #0
getline_r2          .FILL #0
getline_r3          .FILL #0
getline_r7          .FILL #0

.END
