; ============================================================================
; Sistema operativo mínimo de LC10: las rutinas de los TRAP
;
; El simulador las carga en xFD40 al crear la máquina y arma la tabla de vectores (xFB00 + 2·vv).
; TRAP vv hace R7 = PC y salta a la rutina; la rutina termina con RET. Se ejecutan como cualquier
; otro código y el simulador cuenta sus instrucciones aparte ("SO"), igual que el contador
; actualizado del simulador de la cátedra (usuario + SO = total).
;
; Convenciones (las mismas que en la LC-3)
;   * R7 queda con la dirección de retorno (el usuario lo guarda si lo necesita).
;   * Las rutinas conservan todos los demás registros, salvo R0 donde es el resultado (GETC, IN).
;   * No usan la pila del usuario: guardan los registros en palabras propias (SAVE0..SAVE2).
;   * Los dispositivos son registros de memoria (xFE00..): KBSR/KBDR teclado, DSR/DDR pantalla,
;     MCR máquina. Se leen y escriben con LD y ST relativos al PC (por eso el SO está pegado a ellos).
;   * Las banderas N, Z, P quedan como las dejó la última instrucción de la rutina.
; ============================================================================
        .ORIG xFD40

; ---- GETC (x20): R0 = próximo carácter de la entrada (xFFFF si no quedan)
S_GETC  LD    R0, KBSR
        BRzp  S_GETC             ; bit 15 de KBSR en 0: todavía no hay tecla
        LD    R0, KBDR
        RET

; ---- OUT (x21): escribe el byte bajo de R0 en la pantalla
S_OUT   ST    R1, SAVE1
OUT_W   LD    R1, DSR
        BRzp  OUT_W             ; bit 15 de DSR en 0: la pantalla no está lista
        ST    R0, DDR
        LD    R1, SAVE1
        RET

; ---- PUTS (x22): escribe el texto (un byte por carácter, termina en 0) que empieza en la dirección R0
S_PUTS  ST    R0, SAVE0
        ST    R1, SAVE1
        ST    R2, SAVE2
        LDL   R1, R0, #0        ; primer carácter
        BRz   PUTS_E            ; texto vacío
PUTS_W  LD    R2, DSR
        BRzp  PUTS_W
        ST    R1, DDR
        ADD   R0, R0, #1
        LDL   R1, R0, #0        ; carácter siguiente (la carga actualiza N, Z, P)
        BRnp  PUTS_W            ; distinto de 0: sigue
PUTS_E  LD    R0, SAVE0
        LD    R1, SAVE1
        LD    R2, SAVE2
        RET

; ---- IN (x23): como GETC, y repite el carácter en la pantalla (si no quedan, xFFFF y sin eco)
S_IN    LD    R0, KBSR
        BRzp  S_IN
        LD    R0, KBDR
        BRzp  S_OUT             ; hay carácter: OUT lo escribe y vuelve al usuario con RET
        RET                     ; fin de la entrada

; ---- HALT (x25): MCR bit 15 = 0 detiene la máquina (R7 queda en 0)
S_HALT  MOVI  R7, #0
        ST    R7, MCR

SAVE0   .FILL #0
SAVE1   .FILL #0
SAVE2   .FILL #0

; ---- registros de los dispositivos (el simulador los atiende; no son memoria común)
        .BLKW 61                ; relleno hasta xFE00 (si cambia el código, se ajusta; lo verifica tests/test_os.py)
KBSR    .BLKW 1                 ; xFE00  teclado: estado (bit 15 = hay un carácter)
KBDR    .BLKW 1                 ; xFE02  teclado: dato
DSR     .BLKW 1                 ; xFE04  pantalla: estado (bit 15 = lista)
DDR     .BLKW 1                 ; xFE06  pantalla: dato (se escribe el byte bajo)
MCR     .BLKW 1                 ; xFE08  control de la máquina (bit 15 = 0 la detiene)
        .END
