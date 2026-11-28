; LAB 3 - GRUPO 9 - SQRT Newton-Raphson reciproco (Nueva ISA 16 bits)
; MODULO PARA VINCULAR CON LA INTERFAZ (GRUPO 8)
;
; Contrato:
;   Entrada: R0 = x en Q7.8 con 4 <= x <= 16 (x0400..x1000)
;   Salida:  R0 = aproximacion de sqrt(x) en Q7.8
;            R0 = 0 si la entrada esta fuera del rango admitido
;   Conserva: R1, R2, R3, R4, R5, R6, R7
;   Modifica: R0 y codigos de condicion
;   No usa R6; retorna con POPR/RET.
;   Sin .ORIG: el enlazador ubica el modulo en memoria.
;
SQRT_NR_Q8
        PUSHM {R1, R2, R3, R4, R5, R7}

        LI  R1, #1024
        CMP R0, R1
        BRlt SQ9_BAD
        LI  R1, #4096
        CMP R0, R1
        BRgt SQ9_BAD

        ST  R0, SQ9_X
        MOVI R1, #64            ; y inicial = 0.25 en Q7.8
        ST  R1, SQ9_Y
        MOVI R4, #6             ; 6 iteraciones fijas

SQ9_ITER
        LD  R0, SQ9_Y
        MOV R1, R0
        JSR SQ9_MULQ            ; y2 = floor(y*y/256)

        MOV R1, R0
        LD  R0, SQ9_X
        JSR SQ9_MULQ            ; xy2 = floor(x*y2/256)

        LI  R1, #768            ; 3*256
        SUB R0, R1, R0          ; factor = 3*256 - xy2
        LD  R1, SQ9_Y
        JSR SQ9_MULQ            ; floor(factor*y/256)

        LSR R0, R0, #1          ; y = floor(R0 / 2)
        ST  R0, SQ9_Y

        DEC R4
        BRp SQ9_ITER

        ; Recupera raiz cuadrada: sqrt(x) ~= floor(x*y/256).
        LD  R0, SQ9_X
        LD  R1, SQ9_Y
        JSR SQ9_MULQ
        POPR {R1, R2, R3, R4, R5, R7}

SQ9_BAD
        CLR R0                  ; entrada fuera del rango
        POPR {R1, R2, R3, R4, R5, R7}

; MULQ optimizada: R0=a>=0, R1=b (0..128) en Q7.8. Retorna floor(a*b/256).
; Uso interno: R0..R3, R5; conserva R4, R6, R7.
; Metodo: a = 256*alto + bajo usando LSR #8 y AND #255.
; Multiplica alto*b y bajo*b por desplazamiento de b (corte temprano si b=0),
; luego toma los 8 bits altos de bajo*b con LSR #8.
SQ9_MULQ
        LSR R2, R0, #8          ; alto = a >> 8
        LI  R3, #255
        AND R3, R0, R3          ; bajo = a & 0xFF
        CLR R0                  ; acumulador alto*b
        CLR R5                  ; acumulador bajo*b
SQ9_BITS
        LSR R1, R1, #1          ; C = bit 0 de b
        BRnc SQ9_BIT1_NO_ADD
        ADD R0, R0, R2          ; suma alto * 2^bit
        ADD R5, R5, R3          ; suma bajo * 2^bit
SQ9_BIT1_NO_ADD
        SHL R2, R2, #1
        SHL R3, R3, #1
        LSR R1, R1, #1
        BRnc SQ9_BIT2_NO_ADD
        ADD R0, R0, R2
        ADD R5, R5, R3
SQ9_BIT2_NO_ADD
        ADD R1, R1, #0          ; quedan bits activos en b?
        BRz SQ9_MUL_DONE
        SHL R2, R2, #1          ; alto <<= 1
        SHL R3, R3, #1          ; bajo <<= 1
        BR SQ9_BITS
SQ9_MUL_DONE
        LSR R5, R5, #8          ; floor(bajo*b / 256)
        ADD R0, R0, R5          ; alto*b + floor(bajo*b / 256)
        RET

; Area privada de trabajo.
SQ9_X         .BLKW #1
SQ9_Y         .BLKW #1
.END
