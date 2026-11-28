;   ============================================================================
;   SISTEMA OPERATIVO MINIMO - ISA del Grupo 4
;   ============================================================================
;
;   Se ensambla con:   python assembly.py so.asm --format obj     (genera so.obj)
;   El simulador lo carga en memoria ANTES del programa de usuario (que
;   arranca en x3000). Todas sus instrucciones se ejecutan en el simulador y
;   se contabilizan igual que las del usuario (el simulador las informa
;   aparte como "instrucciones del SO": las que se buscan con PC < x3000).
;
;   MAPA DE MEMORIA (direcciones de byte)
;       x0000 - x00FF   Tabla de vectores de TRAP (128 palabras; vector 7 bits)
;                       TRAP v:  R7 <- PC (siguiente instruccion); PC <- mem[2*v]
;       x0100 - x01FF   Tabla de vectores de interrupcion / excepcion
;                       (128 palabras). Entrada = x0100 + 2*vector.
;                           vector x00  excepcion: RTI en modo usuario
;                           vector x01  excepcion: opcode ilegal
;                           vector x10  interrupcion de teclado (prioridad 4)
;       x0200 - x0211   KB_COUNT (x0200) y KB_BUF (x0202..x0211): los llena la
;                       rutina de interrupcion de teclado
;       x0212 - ...     Rutinas del SO
;       x3000           Programa de usuario
;       xFE00 - xFFFF   Registros de dispositivos (ver simulador.py):
;                           xFE00 KBSR  bit15 = dato listo, bit14 = IE
;                           xFE02 KBDR  dato (leerlo limpia "listo")
;                           xFE04 DSR   bit15 = pantalla lista
;                           xFE06 DDR   escribir = imprimir el byte bajo
;                           xFFFC PSR   estado del procesador
;                           xFFFE MCR   bit15 = reloj; escribir 0 = detener
;
;   CONVENCION DE LAS RUTINAS TRAP (igual que la LC-3 original):
;       - Preservan todos los registros que no son su resultado (R7 se pierde:
;         TRAP lo sobreescribe con la direccion de retorno).
;       - No preservan los codigos de condicion.
;   ============================================================================

.ORIG x0000

;   ---------------------------------------------------------------------------
;   x0000: tabla de vectores de TRAP  (128 palabras)
;   ---------------------------------------------------------------------------
                .BLKW   #32                 ;   vectores x00..x1F: sin uso
                .FILL   TRAP_GETC           ;   x20
                .FILL   TRAP_OUT            ;   x21
                .FILL   TRAP_PUTS           ;   x22
                .FILL   TRAP_IN             ;   x23
                .FILL   TRAP_PUTSP          ;   x24
                .FILL   TRAP_HALT           ;   x25
                .BLKW   #90                 ;   vectores x26..x7F: sin uso

;   ---------------------------------------------------------------------------
;   x0100: tabla de vectores de interrupcion y excepcion (128 palabras)
;   ---------------------------------------------------------------------------
                .FILL   EXC_PRIV            ;   x00  RTI en modo usuario
                .FILL   EXC_ILL             ;   x01  opcode ilegal
                .BLKW   #14                 ;   x02..x0F: sin uso
                .FILL   ISR_KB              ;   x10  teclado
                .BLKW   #111                ;   x11..x7F: sin uso

;   ---------------------------------------------------------------------------
;   x0200: datos de la rutina de teclado
;   ---------------------------------------------------------------------------
KB_COUNT        .FILL   #0                  ;   cantidad de caracteres en KB_BUF
KB_BUF          .BLKW   #8                  ;   16 bytes

;   ---------------------------------------------------------------------------
;   ISR_KB: interrupcion de teclado.
;       Corre en modo supervisor con la pila de supervisor (el hardware ya
;       apilo PSR y PC). Guarda el caracter en KB_BUF[KB_COUNT++] (si hay lugar;
;       si no, lo descarta) y vuelve con RTI. No modifica ningun registro
;       (ni los codigos de condicion, que restaura RTI desde el PSR apilado).
;   ---------------------------------------------------------------------------
ISR_KB
    ADD R6 R6 #-2
    STR R0 R6 #0
    ADD R6 R6 #-2
    STR R1 R6 #0
    ADD R6 R6 #-2
    STR R2 R6 #0

    LD R1 kbsr_p
    LDR R0 R1 #1                            ;   R0 = KBDR (lo lee y baja "listo")
    LD R1 KB_COUNT
    ADD R2 R1 #-16
    BRzp isr_kb_full                        ;   buffer lleno: descarta
    LEA R2 KB_BUF
    ADD R2 R2 R1
    STRB R0 R2 #0                           ;   KB_BUF[n] = caracter
    ADD R1 R1 #1
    ST R1 KB_COUNT
isr_kb_full
    LDR R2 R6 #0
    ADD R6 R6 #2
    LDR R1 R6 #0
    ADD R6 R6 #2
    LDR R0 R6 #0
    ADD R6 R6 #2
    RTI

;   ---------------------------------------------------------------------------
;   Excepciones: imprimen un mensaje y detienen la maquina.
;   ---------------------------------------------------------------------------
EXC_PRIV
    LEA R0 msg_priv
    PUTS
    HALT

EXC_ILL
    LEA R0 msg_ill
    PUTS
    HALT

;   ---------------------------------------------------------------------------
;   TRAP x20  GETC: R0 = caracter leido del teclado (sin eco).
;   ---------------------------------------------------------------------------
TRAP_GETC
    ST R1 gc_r1
    LD R1 kbsr_p
gc_wait
    LDR R0 R1 #0                            ;   R0 = KBSR
    BRzp gc_wait                            ;   bit 15 = 0: no hay dato
    LDR R0 R1 #1                            ;   R0 = KBDR
    LD R1 gc_r1
    RET

;   ---------------------------------------------------------------------------
;   TRAP x21  OUT: imprime el byte bajo de R0.
;   ---------------------------------------------------------------------------
TRAP_OUT
    ST R1 out_r1
    ST R2 out_r2
    LD R1 dsr_p
out_wait
    LDR R2 R1 #0                            ;   R2 = DSR
    BRzp out_wait                           ;   bit 15 = 0: pantalla ocupada
    STR R0 R1 #1                            ;   DDR = R0
    LD R2 out_r2
    LD R1 out_r1
    RET

;   ---------------------------------------------------------------------------
;   TRAP x22  PUTS: imprime la cadena de bytes (terminada en 0) en [R0].
;   ---------------------------------------------------------------------------
TRAP_PUTS
    ST R0 puts_r0
    ST R1 puts_r1
    ST R2 puts_r2
    ST R3 puts_r3
    LD R2 dsr_p
puts_loop
    LDBR R1 R0 #0                           ;   R1 = siguiente byte
    BRz puts_done
puts_wait
    LDR R3 R2 #0                            ;   R3 = DSR
    BRzp puts_wait
    STR R1 R2 #1                            ;   DDR = byte
    ADD R0 R0 #1
    BR puts_loop
puts_done
    LD R3 puts_r3
    LD R2 puts_r2
    LD R1 puts_r1
    LD R0 puts_r0
    RET

;   ---------------------------------------------------------------------------
;   TRAP x23  IN: pide un caracter con prompt, lo imprime (eco) y lo deja en R0.
;   ---------------------------------------------------------------------------
TRAP_IN
    ST R7 in_r7
    LEA R0 in_prompt
    PUTS
    GETC
    OUT
    LD R7 in_r7
    RET

;   ---------------------------------------------------------------------------
;   TRAP x24  PUTSP: imprime una cadena con dos caracteres por palabra
;   (byte alto primero; si el byte bajo es 0 no se imprime). Termina en 0x0000.
;   ---------------------------------------------------------------------------
TRAP_PUTSP
    ST R0 psp_r0
    ST R1 psp_r1
    ST R2 psp_r2
    ST R3 psp_r3
    ST R4 psp_r4
    LD R4 dsr_p
psp_loop
    LDR R1 R0 #0                            ;   R1 = palabra
    BRz psp_done
    SHR R2 R1 #8                            ;   byte alto
psp_wait1
    LDR R3 R4 #0
    BRzp psp_wait1
    STR R2 R4 #1
    SHL R2 R1 #8                            ;   byte bajo (en bits 15..8)
    BRz psp_next                            ;   0: no se imprime
    SHR R2 R2 #8
psp_wait2
    LDR R3 R4 #0
    BRzp psp_wait2
    STR R2 R4 #1
psp_next
    ADD R0 R0 #2
    BR psp_loop
psp_done
    LD R4 psp_r4
    LD R3 psp_r3
    LD R2 psp_r2
    LD R1 psp_r1
    LD R0 psp_r0
    RET

;   ---------------------------------------------------------------------------
;   TRAP x25  HALT: imprime "HALT" y detiene el reloj (MCR bit 15 = 0).
;   ---------------------------------------------------------------------------
TRAP_HALT
    LEA R0 halt_msg
    PUTS
    LD R1 mcr_p
    AND R0 R0 #0
    STR R0 R1 #0                            ;   MCR = 0: el procesador se detiene
halt_spin
    BR halt_spin

;   ---------------------------------------------------------------------------
;   Datos del SO
;   ---------------------------------------------------------------------------
kbsr_p      .FILL xFE00
dsr_p       .FILL xFE04
mcr_p       .FILL xFFFE

gc_r1       .FILL #0
out_r1      .FILL #0
out_r2      .FILL #0
puts_r0     .FILL #0
puts_r1     .FILL #0
puts_r2     .FILL #0
puts_r3     .FILL #0
in_r7       .FILL #0
psp_r0      .FILL #0
psp_r1      .FILL #0
psp_r2      .FILL #0
psp_r3      .FILL #0
psp_r4      .FILL #0

halt_msg    .STRINGZ "\nHALT\n"
in_prompt   .STRINGZ "Enter a character: "
msg_priv    .STRINGZ "\n*** EXCEPCION: RTI en modo usuario ***\n"
msg_ill     .STRINGZ "\n*** EXCEPCION: opcode ilegal ***\n"

.END
