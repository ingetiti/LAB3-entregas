; =============================================================================
; os_rutinas.asm - Rutinas del Sistema Operativo para la ISA Skynet (16 bits)
; =============================================================================
; Mapa de memoria (64 KB byte-addressable, Little-Endian):
;   x0000 - x00FF : Tabla de Vectores de TRAP (TVT: entrada en vec * 2)
;   x0400 - x0FFF : Rutinas del OS y variables locales (sin colision con
;                   codigo/datos de usuario en x3000+ ni pila en <= xFDFF)
;   xFE00 - xFFFF : Registros de E/S mapeados en memoria (MMIO):
;                     xFE00 = KBSR (bit 15 = tecla lista)
;                     xFE02 = KBDR (byte ASCII en [7:0])
;                     xFE04 = DSR  (bit 15 = pantalla lista)
;                     xFE06 = DDR  (escritura emite caracter ASCII)
;                     xFFFE = MCR  (bit 15 = 0 detiene el procesador)
;
; Vectores implementados:
;   x20 (GETC) : Lee 1 caracter sin eco en R0 (preserva R1..R7)
;   x21 (OUT)  : Imprime R0 & 0xFF via DSR/DDR (preserva R0..R7)
;   x22 (PUTS) : Recorre cadena empaquetada (byte a byte hasta 0x00) con
;                polling directo DSR/DDR en bucle rotado (preserva R0..R7)
;   x23 (IN)   : Imprime prompt, lee con GETC y hace eco con OUT (preserva R1..R7)
;   x25 (HALT) : Imprime "\nHALT\n" via PUTS y apaga reloj en MCR (preserva R0..R7)
;   x26 (PUTI) : Imprime R0 como entero decimal con signo 16b (preserva R0..R7)
; =============================================================================

.ORIG x0000

; Tabla de Vectores de TRAP (TVT: direccion = vec * 2)
.ORIG x0040
    .FILL OS_TRAP_GETC          ; TRAP x20 -> x0040
    .FILL OS_TRAP_OUT           ; TRAP x21 -> x0042
    .FILL OS_TRAP_PUTS          ; TRAP x22 -> x0044
    .FILL OS_TRAP_IN            ; TRAP x23 -> x0046
    .FILL #0                    ; TRAP x24 -> x0048 (no implementado)
    .FILL OS_TRAP_HALT          ; TRAP x25 -> x004A
    .FILL OS_TRAP_PUTI          ; TRAP x26 -> x004C

; Rutinas del Sistema Operativo
.ORIG x0400

; -----------------------------------------------------------------------------
; TRAP x20: GETC - Lee un caracter ASCII sin eco en R0 (zero-extended)
; -----------------------------------------------------------------------------
OS_TRAP_GETC:
    ST   R1, OS_GETC_R1
    LD   R1, OS_KBSR_ADDR       ; R1 = xFE00 (KBSR)
OS_GETC_WAIT:
    LDR  R0, R1, #0             ; R0 = KBSR (bit 15 = 1 cuando hay dato)
    BRzp OS_GETC_WAIT
    LDR  R0, R1, #1             ; R0 = KBDR (xFE00 + 2*1 = xFE02)
    LD   R1, OS_GETC_R1
    RET

; -----------------------------------------------------------------------------
; TRAP x21: OUT - Imprime el caracter ASCII en R0 & 0xFF
; -----------------------------------------------------------------------------
OS_TRAP_OUT:
    ST   R1, OS_OUT_R1
    ST   R2, OS_OUT_R2
    LD   R1, OS_DSR_ADDR        ; R1 = xFE04 (DSR)
OS_OUT_WAIT:
    LDR  R2, R1, #0             ; R2 = DSR (bit 15 = 1 cuando pantalla lista)
    BRzp OS_OUT_WAIT
    STR  R0, R1, #1             ; DDR (xFE04 + 2*1 = xFE06) <- R0 & 0xFF
    LD   R1, OS_OUT_R1
    LD   R2, OS_OUT_R2
    RET

; -----------------------------------------------------------------------------
; TRAP x22: PUTS - Recorre cadena empaquetada (1 byte/char hasta '\0')
; Polling directo de DSR/DDR dentro del bucle (sin TRAP anidado a OUT) y
; rotacion do-while: 6 instrucciones por caracter (preserva R0..R7 y R6)
; -----------------------------------------------------------------------------
OS_TRAP_PUTS:
    ST   R0, OS_PUTS_R0
    ST   R1, OS_PUTS_R1
    ST   R2, OS_PUTS_R2
    ST   R3, OS_PUTS_R3
    LD   R2, OS_DSR_ADDR        ; R2 = xFE04 (DSR) una sola vez
    LDBU R1, R0, #0             ; R1 = primer byte sin signo (actualiza NZP)
    BRz  OS_PUTS_DONE           ; cadena vacia: retorna directo
OS_PUTS_WAIT:
    LDR  R3, R2, #0             ; R3 = DSR (bit 15 = 1 cuando pantalla lista)
    BRzp OS_PUTS_WAIT
    STR  R1, R2, #1             ; DDR (xFE04 + 2*1 = xFE06) <- R1 & 0xFF
    ADD  R0, R0, #1             ; avanza 1 byte (Little-Endian empaquetado)
    LDBU R1, R0, #0             ; siguiente byte (actualiza NZP)
    BRnp OS_PUTS_WAIT           ; si != '\0', repite sin BRnzp extra
OS_PUTS_DONE:
    LD   R0, OS_PUTS_R0
    LD   R1, OS_PUTS_R1
    LD   R2, OS_PUTS_R2
    LD   R3, OS_PUTS_R3
    RET

; -----------------------------------------------------------------------------
; TRAP x23: IN - Solicita un caracter, lo guarda en R0 y lo imprime con eco
; -----------------------------------------------------------------------------
OS_TRAP_IN:
    ST   R7, OS_IN_R7
    LEA  R0, OS_IN_PROMPT       ; "Input a character: "
    PUTS
    GETC
    OUT
    LD   R7, OS_IN_R7
    RET

; -----------------------------------------------------------------------------
; TRAP x25: HALT - Imprime "\nHALT\n" y detiene el procesador via MCR (xFFFE)
; -----------------------------------------------------------------------------
OS_TRAP_HALT:
    ST   R0, OS_HALT_R0
    ST   R1, OS_HALT_R1
    ST   R2, OS_HALT_R2
    ST   R7, OS_HALT_R7
    LEA  R0, OS_HALT_MSG        ; "\nHALT\n"
    PUTS
    LD   R1, OS_MCR_ADDR        ; R1 = xFFFE (MCR)
    LDR  R0, R1, #0             ; lee MCR actual
    LD   R2, OS_MCR_MASK        ; R2 = x7FFF (limpia bit 15: clock enable = 0)
    AND  R0, R0, R2             ; apaga bit 15 de MCR
    STR  R0, R1, #0             ; escribe MCR -> solicita detencion de la CPU
    LD   R0, OS_HALT_R0         ; restaura registros del usuario
    LD   R1, OS_HALT_R1
    LD   R2, OS_HALT_R2
    LD   R7, OS_HALT_R7
    RET

; --- Constantes y slots locales (GETC / OUT / PUTS / IN / HALT) ---
OS_KBSR_ADDR:   .FILL xFE00
OS_DSR_ADDR:    .FILL xFE04
OS_MCR_ADDR:    .FILL xFFFE
OS_MCR_MASK:    .FILL x7FFF
OS_GETC_R1:     .BLKW #1
OS_OUT_R1:      .BLKW #1
OS_OUT_R2:      .BLKW #1
OS_PUTS_R0:     .BLKW #1
OS_PUTS_R1:     .BLKW #1
OS_PUTS_R2:     .BLKW #1
OS_PUTS_R3:     .BLKW #1
OS_IN_R7:       .BLKW #1
OS_HALT_R0:     .BLKW #1
OS_HALT_R1:     .BLKW #1
OS_HALT_R2:     .BLKW #1
OS_HALT_R7:     .BLKW #1
OS_IN_PROMPT:   .STRINGZ "Input a character: "
                .BLKW #0        ; fuerza alineacion par antes de OS_HALT_MSG
OS_HALT_MSG:    .STRINGZ "\nHALT\n"

; -----------------------------------------------------------------------------
; TRAP x26: PUTI - Imprime R0 como entero decimal con signo de 16 bits
; Maneja signo, cero, digitos decimales y el caso limite -32768 (0x8000)
; Usa contador explicito de digitos en R5 (sin comparar direcciones con CMP)
; -----------------------------------------------------------------------------
OS_TRAP_PUTI:
    ST   R0, OS_PUTI_R0
    ST   R1, OS_PUTI_R1
    ST   R2, OS_PUTI_R2
    ST   R3, OS_PUTI_R3
    ST   R4, OS_PUTI_R4
    ST   R5, OS_PUTI_R5
    ST   R7, OS_PUTI_R7

    ADD  R1, R0, #0             ; R1 = valor a imprimir (actualiza NZP)
    BRz  OS_PUTI_ZERO

    MOVI R2, #10                ; R2 = base decimal 10
    LEA  R4, OS_PUTI_BUF        ; R4 = puntero de escritura en buffer
    MOVI R5, #0                 ; R5 = contador de digitos almacenados (0..5)
    ADD  R1, R1, #0             ; reevalua signo de R1 (MOVI modifica NZP)
    BRp  OS_PUTI_POS_LOOP

    ; Caso negativo: extrae el ultimo digito con REM/DIV antes de negar
    ; para evitar saturacion de NEG sobre -32768 (0x8000)
    MOVI R0, #45                ; '-'
    OUT
    REM  R3, R1, R2             ; R3 in [-9..0]
    NEG  R3, R3                 ; R3 in [0..9]
    ADDI R3, #48                ; ASCII '0'..'9'
    STB  R3, R4, #0
    ADD  R4, R4, #1
    ADD  R5, R5, #1             ; digitos almacenados += 1
    DIV  R1, R1, R2             ; R1 in [-3276..0]
    NEG  R1, R1                 ; R1 in [0..3276] (actualiza NZP)
    BRz  OS_PUTI_OUT_LOOP

OS_PUTI_POS_LOOP:
    REM  R3, R1, R2             ; R3 = R1 % 10
    ADDI R3, #48                ; ASCII '0'..'9'
    STB  R3, R4, #0
    ADD  R4, R4, #1
    ADD  R5, R5, #1             ; digitos almacenados += 1
    DIV  R1, R1, R2             ; R1 = R1 / 10 (actualiza NZP)
    BRp  OS_PUTI_POS_LOOP

OS_PUTI_OUT_LOOP:
    ADD  R4, R4, #-1            ; retrocede al siguiente digito (MSB -> LSB)
    LDBU R0, R4, #0
    OUT
    ADD  R5, R5, #-1            ; decrementa contador de digitos (actualiza NZP)
    BRp  OS_PUTI_OUT_LOOP
    BRnzp OS_PUTI_DONE

OS_PUTI_ZERO:
    MOVI R0, #48                ; '0'
    OUT

OS_PUTI_DONE:
    LD   R0, OS_PUTI_R0
    LD   R1, OS_PUTI_R1
    LD   R2, OS_PUTI_R2
    LD   R3, OS_PUTI_R3
    LD   R4, OS_PUTI_R4
    LD   R5, OS_PUTI_R5
    LD   R7, OS_PUTI_R7
    RET

; --- Slots locales y buffer para PUTI ---
OS_PUTI_R0:     .BLKW #1
OS_PUTI_R1:     .BLKW #1
OS_PUTI_R2:     .BLKW #1
OS_PUTI_R3:     .BLKW #1
OS_PUTI_R4:     .BLKW #1
OS_PUTI_R5:     .BLKW #1
OS_PUTI_R7:     .BLKW #1
OS_PUTI_BUF:    .BLKW #4        ; 8 bytes (hasta 5 digitos decimales)

.END
