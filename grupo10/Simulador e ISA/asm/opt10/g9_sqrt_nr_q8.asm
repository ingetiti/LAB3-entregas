; LAB 3 - GRUPO 9 - SQRT Newton-Raphson reciproco
; MODULO PARA VINCULAR CON LA INTERFAZ LC-3 (GRUPO 8)

; Contrato:
; Entrada: R0 = x en Q7.8 con 4 <= x <= 16 (x0400..x1000)
; Salida:  R0 = aproximacion de sqrt(x) en Q7.8
; R0 = 0 si la entrada esta fuera del rango admitido
; Conserva: R1, R2, R3, R4, R5, R6, R7
; Modifica: R0 y codigos de condicion
; No usa R6; la rutina retorna con RET, no HALT.
; NO reentrante: utiliza variables estaticas de trabajo.

; Si se adjunta al simulador de integracion, SIN .ORIG.
; El programa principal debe establecer .ORIG y efectuar el JSR.

SQRT_NR_Q8
                        PUSH  R1, R2, R3, R4, R5, R7

                        ST    R0, SQ9_X
                        LD    R1, SQ9_NEGMIN
                        ADD   R2, R0, R1
                        BRn   SQ9_BAD
                        LD    R1, SQ9_NEGMAX
                        ADD   R2, R0, R1
                        BRp   SQ9_BAD

; Reinicia el estado para cada llamada.
                        LD    R1, SQ9_SEED
                        ST    R1, SQ9_Y
                        LD    R1, SQ9_NITER
                        ST    R1, SQ9_COUNT

SQ9_ITER
                        LD    R0, SQ9_Y
                        LD    R1, SQ9_Y
                        JSR   SQ9_MULQ                  ; y2 = floor(y*y/256)
                        ST    R0, SQ9_Y2

                        LD    R0, SQ9_X
                        LD    R1, SQ9_Y2
                        JSR   SQ9_MULQ                  ; xy2 = floor(x*y2/256)
                        ST    R0, SQ9_XY2

                        LD    R0, SQ9_THREE
                        LD    R1, SQ9_XY2
                        NOT   R1, R1
                        ADD   R1, R1, #1
                        ADD   R0, R0, R1
                        ST    R0, SQ9_FACTOR            ; 3*256 - xy2

                        LD    R1, SQ9_Y
                        JSR   SQ9_MULQ                  ; floor(factor*y/256)

; R1 = floor(R0 / 2). En la LC-3 se leia bit a bit (0 <= R0 <= 384); en LC10 es un SHR.
                        SHR   R1, R0, #1
                        ST    R1, SQ9_Y

                        LD    R1, SQ9_COUNT
                        ADD   R1, R1, #-1
                        ST    R1, SQ9_COUNT
                        BRp   SQ9_ITER

; Recupera raiz cuadrada: sqrt(x) ~= x*y.
                        LD    R0, SQ9_X
                        LD    R1, SQ9_Y
                        JSR   SQ9_MULQ
                        BRnzp SQ9_DONE

SQ9_BAD
                        AND   R0, R0, #0                ; entrada fuera del rango

SQ9_DONE
                        ST    R0, SQ9_RESULT
                        POP   R1, R2, R3, R4, R5, R7
                        RET

; MULQ: R0 = a >= 0, R1 = b (0..128), ambos en Q7.8. Retorna floor(a*b/256).
; La LC-3 partia a = 256*alto + bajo y multiplicaba por sumas de bits;
; floor(a*b/256) = alto*b + floor(bajo*b/256), o sea el producto de 32 bits
; (MUL + MULHU) sin sus 8 bits bajos: (alto del producto << 8) | (bajo >> 8).
; Usa R2 y R3 (la rutina que la llama los tiene guardados en la pila).
SQ9_MULQ
                        MUL   R2, R0, R1
                        MULHU R3, R0, R1
                        SHR   R2, R2, #8
                        SHL   R3, R3, #8
                        OR    R0, R2, R3
                        RET

; Constantes (Q7.8) y area privada de trabajo.
SQ9_SEED                .FILL #64
SQ9_NITER               .FILL #6
SQ9_THREE               .FILL #768
SQ9_NEG256              .FILL #-256
SQ9_NEGMIN              .FILL #-1024
SQ9_NEGMAX              .FILL #-4096
SQ9_X                   .BLKW #1
SQ9_Y                   .BLKW #1
SQ9_Y2                  .BLKW #1
SQ9_XY2                 .BLKW #1
SQ9_FACTOR              .BLKW #1
SQ9_MUL_B               .BLKW #1
SQ9_COUNT               .BLKW #1
SQ9_RESULT              .BLKW #1
.END
