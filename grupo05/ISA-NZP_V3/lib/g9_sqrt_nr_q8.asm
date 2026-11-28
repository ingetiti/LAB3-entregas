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

        ; Divide R0 entre 2 por bits, sin SHIFT ni restas repetidas.
        ; En este nucleo: 0 <= R0 <= 384 (< 512).
        ; Al desplazar R0 7 veces a la izquierda, su bit 8 queda
        ; en el bit de signo. Leemos los bits 8..1 en 8 pasos,
        ; descartando el bit 0: R1 = floor(R0/2).
        ADD R2, R0, #0
        ADD R2, R2, R2
        ADD R2, R2, R2
        ADD R2, R2, R2
        ADD R2, R2, R2
        ADD R2, R2, R2
        ADD R2, R2, R2
        ADD R2, R2, R2
        AND R1, R1, #0
        AND R3, R3, #0
        ADD R3, R3, #8
SQ9_HALF
        ADD R1, R1, R1
        ADD R2, R2, #0
        BRzp SQ9_HALF_ZERO
        ADD R1, R1, #1
SQ9_HALF_ZERO
        ADD R2, R2, R2
        ADD R3, R3, #-1
        BRp SQ9_HALF
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
SQ9_MULQ
        AND R2, R2, #0        ; alto = 0
        ADD R3, R0, #0        ; bajo (provisional) = a
        LD  R4, SQ9_NEG256
SQ9_SPLIT
        ADD R5, R3, R4
        BRn SQ9_SPLIT_END
        ADD R3, R5, #0        ; bajo -= 256
        ADD R2, R2, #1        ; alto++
        BRnzp SQ9_SPLIT
SQ9_SPLIT_END
        ST  R1, SQ9_MUL_B     ; guarda b para reutilizar R1 como auxiliar
        AND R0, R0, #0        ; acumulador alto*b
        AND R5, R5, #0        ; acumulador bajo*b
        AND R4, R4, #0
        ADD R4, R4, #1        ; mascara de bits = 1

SQ9_BITS
        LD  R1, SQ9_MUL_B
        AND R1, R1, R4        ; ¿el bit actual de b esta activo?
        BRz SQ9_NO_ADD
        ADD R0, R0, R2        ; suma alto*2^bit
        ADD R5, R5, R3        ; suma bajo*2^bit
SQ9_NO_ADD
        ADD R2, R2, R2        ; duplica alto
        ADD R3, R3, R3        ; duplica bajo
        ADD R4, R4, R4        ; siguiente mascara
        LD  R1, SQ9_NEG256
        ADD R1, R4, R1
        BRn SQ9_BITS          ; 8 bits: 1,2,4,...,128

        ; R5= bajo*b, entero en 0..32640. Extrae los 8 bits altos
        ; leyendo el signo y desplazando a izquierda 8 veces.
        AND R2, R2, #0        ; cociente = 0
        AND R3, R3, #0
        ADD R3, R3, #8
SQ9_GET_HIGH
        ADD R2, R2, R2
        ADD R5, R5, #0
        BRzp SQ9_HIGH_ZERO
        ADD R2, R2, #1
SQ9_HIGH_ZERO
        ADD R5, R5, R5
        ADD R3, R3, #-1
        BRp SQ9_GET_HIGH
        ADD R0, R0, R2        ; alto*b + floor(bajo*b/256)
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
