; LAB 3 - GRUPO 9 - SQRT Newton-Raphson reciproco
; MODULO PARA VINCULAR CON LA INTERFAZ LC-3 (GRUPO 8)
;
; Contrato:
;   Entrada: R0 = x en Q7.8 con 4 <= x <= 16 (x0400..x1000)
;   Salida:  R0 = aproximacion de sqrt(x) en Q7.8
;            R0 = 0 si la entrada esta fuera del rango admitido
;   Conserva: R1, R2, R3, R4, R5, R6, R7
;   Modifica: R0 y codigos de condicion
;   No usa R6; la rutina retorna con RET, no HALT.
;   NO reentrante: utiliza variables estaticas de trabajo.
;
; Si se adjunta al simulador de integracion, SIN .ORIG.
; El programa principal debe establecer .ORIG y efectuar el JSR.
;
SQRT_NR_Q8
        ST  R1, SQ9_SAVE1
        ST  R2, SQ9_SAVE2
        ST  R3, SQ9_SAVE3
        ST  R4, SQ9_SAVE4
        ST  R5, SQ9_SAVE5
        ST  R7, SQ9_SAVE7

        ST  R0, SQ9_X
        LD  R1, SQ9_NEGMIN
        ADD R2, R0, R1
        BRn SQ9_BAD
        LD  R1, SQ9_NEGMAX
        ADD R2, R0, R1
        BRp SQ9_BAD

        ; Reinicia el estado para cada llamada.
        LD  R1, SQ9_SEED
        ST  R1, SQ9_Y
        LD  R1, SQ9_NITER
        ST  R1, SQ9_COUNT

SQ9_ITER
        LD  R0, SQ9_Y
        LD  R1, SQ9_Y
        JSR SQ9_MULQ             ; y2 = floor(y*y/256)
        ST  R0, SQ9_Y2

        LD  R0, SQ9_X
        LD  R1, SQ9_Y2
        JSR SQ9_MULQ             ; xy2 = floor(x*y2/256)
        ST  R0, SQ9_XY2

        LD  R0, SQ9_THREE
        LD  R1, SQ9_XY2
        NOT R1, R1
        ADD R1, R1, #1
        ADD R0, R0, R1
        ST  R0, SQ9_FACTOR       ; 3*256 - xy2

        LD  R1, SQ9_Y
        JSR SQ9_MULQ             ; floor(factor*y/256)

        ; Divide R0 entre 2. La version original lee los bits 8..1 de R0 con un lazo
        ; de 8 pasos (R1 = floor(R0/2) para 0 <= R0 <= 384); [G23] con dos
        ; corrimientos se obtienen exactamente los mismos bits: (R0 >> 1) AND 255.
        LSL R1, R0, #7
        LSR R1, R1, #8
        ST  R1, SQ9_Y

        LD  R1, SQ9_COUNT
        ADD R1, R1, #-1
        ST  R1, SQ9_COUNT
        BRp SQ9_ITER

        ; Recupera raiz cuadrada: sqrt(x) ~= x*y.
        LD  R0, SQ9_X
        LD  R1, SQ9_Y
        JSR SQ9_MULQ
        BRnzp SQ9_DONE

SQ9_BAD
        AND R0, R0, #0          ; entrada fuera del rango

SQ9_DONE
        ST  R0, SQ9_RESULT
        LD  R1, SQ9_SAVE1
        LD  R2, SQ9_SAVE2
        LD  R3, SQ9_SAVE3
        LD  R4, SQ9_SAVE4
        LD  R5, SQ9_SAVE5
        LD  R7, SQ9_SAVE7
        RET

; MULQ optimizada, misma interfaz y truncamiento que la original.
; R0=a>=0, R1=b (0..128) en Q7.8. Retorna floor(a*b/256).
; Uso interno: R0..R5; no toca R6 ni R7. No reentrante.
; Metodo: a=256*alto+bajo.
; Multiplica alto*b y bajo*b por suma binaria (8 bits), luego toma
; los 8 bits mas significativos de bajo*b, sin dividir por restas.
; [G23] Version para la ISA G23 (Grupo 23): mismo metodo (a = 256*alto + bajo,
;       suma binaria de alto*b y bajo*b, 8 bits altos de bajo*b) y mismo
;       resultado. La separacion en bytes y la extraccion de los 8 bits altos
;       usan corrimientos (LSR/LSL) en lugar de restas y lazos, y los bits de b
;       se leen con LSR + bandera C.
SQ9_MULQ
        ; [G23] Version 2: floor(a*b/256) es la parte alta y la parte baja del
        ; producto de 32 bits corridas 8 lugares: (alto << 8) OR (bajo >> 8).
        ; Mismo resultado que la suma binaria (alto*b + floor(bajo*b/256)).
        MUL R2, R0, R1        ; 16 bits bajos de a*b
        MULHU R0, R0, R1      ; 16 bits altos de a*b
        LSL R0, R0, #8
        LSR R2, R2, #8
        OR R0, R0, R2         ; floor(a*b / 256)
        RET

; Constantes (Q7.8) y area privada de trabajo.
SQ9_SEED      .FILL #64
SQ9_NITER     .FILL #6
SQ9_THREE     .FILL #768
SQ9_NEG256    .FILL #-256
SQ9_NEGMIN    .FILL #-1024
SQ9_NEGMAX    .FILL #-4096
SQ9_X         .BLKW #1
SQ9_Y         .BLKW #1
SQ9_Y2        .BLKW #1
SQ9_XY2       .BLKW #1
SQ9_FACTOR    .BLKW #1
SQ9_MUL_B     .BLKW #1
SQ9_COUNT     .BLKW #1
SQ9_RESULT    .BLKW #1
SQ9_SAVE1     .BLKW #1
SQ9_SAVE2     .BLKW #1
SQ9_SAVE3     .BLKW #1
SQ9_SAVE4     .BLKW #1
SQ9_SAVE5     .BLKW #1
SQ9_SAVE7     .BLKW #1
.END
