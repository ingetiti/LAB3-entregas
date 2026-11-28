; ================================================================
; SENO Y COSENO POR TABLA CON INTERPOLACION LINEAL (LC-X)
; ================================================================
; SENO_TABLA / COSENO_TABLA
;   Entrada: R0 = angulo Q3.12, cualquiera (se reduce a 0..2PI = 25736).
;   Salida:  R0 = seno o coseno Q1.14.
;   Conserva R1-R7.
;
; El mismo metodo que el original:
;   1. Cuadrante: se compara con PI/2, PI y 3PI/2 (signo del 16 bits
;      de la resta, como el original) y se lleva el angulo al primer
;      cuadrante. El coseno usa la cofuncion PI/2 - referencia.
;   2. INTERPOLAR: indice = bits 12..5, resto = bits 4..0,
;      dos muestras de la tabla, delta = siguiente - actual,
;      resultado = actual + (delta * resto + 16) / 32.
; La tabla guarda las muestras de indice par en palabras y, en bytes,
; la diferencia de cada una con la impar que le sigue (0..128): la
; muestra impar es la par mas su delta. Las muestras son las mismas.
; Son las 203 muestras del original (k = 0..202; el indice llega a 201
; porque la referencia es <= PI/2, y la muestra siguiente a 202).
;   3. Signo segun el cuadrante.
; Cada interfaz calcula solo el resultado que devuelve.
; Arreglo: fuera de 0..2PI el original leia pasada la tabla. Aqui
; REDUCIR suma o resta 2PI primero, asi que cualquier angulo Q3.12 vale.
; ================================================================

SENO_TABLA
        PUSH  R1, R2, R3, R7
        JSR   REDUCIR
        LD    R1, PI_2
        CMP   R0, R1
        BRn   NUCLEO            ; c1: x
        LSHF  R2, R1, #1        ; R2 = PI
        CMP   R0, R2
        BRn   REFLEJO           ; c2: PI - x
        SUB   R0, R0, R2        ; c3 y c4: x - PI, negativo
        CMP   R0, R1
        BRn   NEGATIVO          ; c3: x - PI
REFLEJO_N
        SUB   R0, R2, R0        ; c4: 2PI - x
NEGATIVO
        JSR   MARCO
        NEG   R0, R0
        POPR  R1, R2, R3, R7

COSENO_TABLA
        PUSH  R1, R2, R3, R7
        JSR   REDUCIR
        LD    R2, PI_2
        CMP   R0, R2
        BRn   REFLEJO           ; c1: PI/2 - x
        SUB   R0, R0, R2        ; x - PI/2
        CMP   R0, R2
        BRn   NEGATIVO          ; c2: x - PI/2, negativo
        SUB   R0, R0, R2        ; y = x - PI
        CMP   R0, R2
        BRn   REFLEJO_N         ; c3: PI/2 - y, negativo
        SUB   R0, R0, R2        ; c4: y - PI/2
        BRnzp NUCLEO

; Marco interno: el nucleo vuelve al NEG con su POPR.
MARCO   PUSH  R1, R2, R3, R7
        BRnzp NUCLEO

REFLEJO SUB   R0, R2, R0

; ------------------------------------------------
; INTERPOLAR_PRIMER_CUADRANTE: R0 = referencia, devuelve R0.
; ------------------------------------------------
NUCLEO  LSHF  R0, R0, #3        ; descarta los bits 15..13
        RSHFL R2, R0, #9        ; R2 = indice / 2 (bits 12..6)
        LEA   R1, TABLA_DELTA
        ADD   R1, R1, R2
        LDBI  R1, R1            ; R1 = delta de la muestra par (0..128, sin signo)
        LEA   R7, TABLA_SENO_PAR
        LSHF  R3, R0, #8        ; R3 = resto (bits 4..0) << 11, C = indice impar
        LDRX  R0, R7, R2        ; R0 = muestra par
        BRNC  INTERPOLA         ; indice par: actual y su delta
        ADD   R0, R0, R1        ; indice impar: actual = par + delta
        ADD   R7, R7, #2
        LDRX  R1, R7, R2        ; muestra par siguiente
        SUB   R1, R1, R0        ; delta = siguiente - actual
INTERPOLA
        MULQU R1, R3, #16       ; delta * resto / 32, C = bit 4
        ADC   R0, R0, R1        ; actual + incremento redondeado
        POPR  R1, R2, R3, R7

; REDUCIR: R0 = angulo llevado a 0..2PI; usa R1.
REDUCIR LD    R1, DOS_PI
        CMP   R0, R1
        BRNC  RED_FIN           ; 0 <= x < 2PI (sin signo)
        ADD   R0, R0, #0
        BRn   RED_SUMA
        SUB   R0, R0, R1        ; 2PI <= x < 8: una vez
        RET
RED_SUMA
        ADD   R0, R0, R1        ; x < 0: una o dos veces
        BRn   RED_SUMA
RED_FIN RET

PI_2    .FILL #6434
DOS_PI  .FILL #25736

; delta[k] = muestra[k+1] - muestra[k], k = 0, 2, ..., 200
TABLA_DELTA
        .BYTE #128 ; k=  0
        .BYTE #128 ; k=  2
        .BYTE #128 ; k=  4
        .BYTE #128 ; k=  6
        .BYTE #128 ; k=  8
        .BYTE #127 ; k= 10
        .BYTE #127 ; k= 12
        .BYTE #128 ; k= 14
        .BYTE #127 ; k= 16
        .BYTE #127 ; k= 18
        .BYTE #126 ; k= 20
        .BYTE #126 ; k= 22
        .BYTE #126 ; k= 24
        .BYTE #125 ; k= 26
        .BYTE #125 ; k= 28
        .BYTE #124 ; k= 30
        .BYTE #124 ; k= 32
        .BYTE #123 ; k= 34
        .BYTE #123 ; k= 36
        .BYTE #122 ; k= 38
        .BYTE #122 ; k= 40
        .BYTE #121 ; k= 42
        .BYTE #120 ; k= 44
        .BYTE #120 ; k= 46
        .BYTE #119 ; k= 48
        .BYTE #119 ; k= 50
        .BYTE #118 ; k= 52
        .BYTE #116 ; k= 54
        .BYTE #115 ; k= 56
        .BYTE #114 ; k= 58
        .BYTE #114 ; k= 60
        .BYTE #113 ; k= 62
        .BYTE #112 ; k= 64
        .BYTE #111 ; k= 66
        .BYTE #110 ; k= 68
        .BYTE #109 ; k= 70
        .BYTE #108 ; k= 72
        .BYTE #107 ; k= 74
        .BYTE #106 ; k= 76
        .BYTE #105 ; k= 78
        .BYTE #104 ; k= 80
        .BYTE #102 ; k= 82
        .BYTE #101 ; k= 84
        .BYTE #100 ; k= 86
        .BYTE #99 ; k= 88
        .BYTE #97 ; k= 90
        .BYTE #96 ; k= 92
        .BYTE #95 ; k= 94
        .BYTE #93 ; k= 96
        .BYTE #92 ; k= 98
        .BYTE #91 ; k=100
        .BYTE #90 ; k=102
        .BYTE #88 ; k=104
        .BYTE #86 ; k=106
        .BYTE #85 ; k=108
        .BYTE #83 ; k=110
        .BYTE #82 ; k=112
        .BYTE #80 ; k=114
        .BYTE #79 ; k=116
        .BYTE #77 ; k=118
        .BYTE #75 ; k=120
        .BYTE #73 ; k=122
        .BYTE #72 ; k=124
        .BYTE #70 ; k=126
        .BYTE #68 ; k=128
        .BYTE #67 ; k=130
        .BYTE #65 ; k=132
        .BYTE #64 ; k=134
        .BYTE #62 ; k=136
        .BYTE #61 ; k=138
        .BYTE #58 ; k=140
        .BYTE #56 ; k=142
        .BYTE #54 ; k=144
        .BYTE #53 ; k=146
        .BYTE #51 ; k=148
        .BYTE #49 ; k=150
        .BYTE #48 ; k=152
        .BYTE #46 ; k=154
        .BYTE #44 ; k=156
        .BYTE #41 ; k=158
        .BYTE #40 ; k=160
        .BYTE #38 ; k=162
        .BYTE #36 ; k=164
        .BYTE #34 ; k=166
        .BYTE #33 ; k=168
        .BYTE #30 ; k=170
        .BYTE #28 ; k=172
        .BYTE #27 ; k=174
        .BYTE #24 ; k=176
        .BYTE #22 ; k=178
        .BYTE #20 ; k=180
        .BYTE #18 ; k=182
        .BYTE #16 ; k=184
        .BYTE #14 ; k=186
        .BYTE #12 ; k=188
        .BYTE #10 ; k=190
        .BYTE #9 ; k=192
        .BYTE #7 ; k=194
        .BYTE #5 ; k=196
        .BYTE #3 ; k=198
        .BYTE #1 ; k=200

; muestra[k], k = 0, 2, ..., 202
TABLA_SENO_PAR
        .FILL #0 ; k=  0, X=   0
        .FILL #256 ; k=  2, X=  64
        .FILL #512 ; k=  4, X= 128
        .FILL #768 ; k=  6, X= 192
        .FILL #1023 ; k=  8, X= 256
        .FILL #1279 ; k= 10, X= 320
        .FILL #1534 ; k= 12, X= 384
        .FILL #1788 ; k= 14, X= 448
        .FILL #2043 ; k= 16, X= 512
        .FILL #2296 ; k= 18, X= 576
        .FILL #2550 ; k= 20, X= 640
        .FILL #2802 ; k= 22, X= 704
        .FILL #3054 ; k= 24, X= 768
        .FILL #3305 ; k= 26, X= 832
        .FILL #3555 ; k= 28, X= 896
        .FILL #3805 ; k= 30, X= 960
        .FILL #4053 ; k= 32, X=1024
        .FILL #4301 ; k= 34, X=1088
        .FILL #4547 ; k= 36, X=1152
        .FILL #4793 ; k= 38, X=1216
        .FILL #5037 ; k= 40, X=1280
        .FILL #5280 ; k= 42, X=1344
        .FILL #5522 ; k= 44, X=1408
        .FILL #5762 ; k= 46, X=1472
        .FILL #6001 ; k= 48, X=1536
        .FILL #6238 ; k= 50, X=1600
        .FILL #6474 ; k= 52, X=1664
        .FILL #6709 ; k= 54, X=1728
        .FILL #6942 ; k= 56, X=1792
        .FILL #7173 ; k= 58, X=1856
        .FILL #7402 ; k= 60, X=1920
        .FILL #7629 ; k= 62, X=1984
        .FILL #7855 ; k= 64, X=2048
        .FILL #8079 ; k= 66, X=2112
        .FILL #8300 ; k= 68, X=2176
        .FILL #8520 ; k= 70, X=2240
        .FILL #8738 ; k= 72, X=2304
        .FILL #8953 ; k= 74, X=2368
        .FILL #9166 ; k= 76, X=2432
        .FILL #9377 ; k= 78, X=2496
        .FILL #9586 ; k= 80, X=2560
        .FILL #9793 ; k= 82, X=2624
        .FILL #9997 ; k= 84, X=2688
        .FILL #10198 ; k= 86, X=2752
        .FILL #10397 ; k= 88, X=2816
        .FILL #10594 ; k= 90, X=2880
        .FILL #10788 ; k= 92, X=2944
        .FILL #10979 ; k= 94, X=3008
        .FILL #11168 ; k= 96, X=3072
        .FILL #11354 ; k= 98, X=3136
        .FILL #11537 ; k=100, X=3200
        .FILL #11717 ; k=102, X=3264
        .FILL #11895 ; k=104, X=3328
        .FILL #12070 ; k=106, X=3392
        .FILL #12241 ; k=108, X=3456
        .FILL #12410 ; k=110, X=3520
        .FILL #12575 ; k=112, X=3584
        .FILL #12738 ; k=114, X=3648
        .FILL #12897 ; k=116, X=3712
        .FILL #13054 ; k=118, X=3776
        .FILL #13207 ; k=120, X=3840
        .FILL #13357 ; k=122, X=3904
        .FILL #13503 ; k=124, X=3968
        .FILL #13647 ; k=126, X=4032
        .FILL #13787 ; k=128, X=4096
        .FILL #13923 ; k=130, X=4160
        .FILL #14057 ; k=132, X=4224
        .FILL #14186 ; k=134, X=4288
        .FILL #14313 ; k=136, X=4352
        .FILL #14435 ; k=138, X=4416
        .FILL #14555 ; k=140, X=4480
        .FILL #14671 ; k=142, X=4544
        .FILL #14783 ; k=144, X=4608
        .FILL #14891 ; k=146, X=4672
        .FILL #14996 ; k=148, X=4736
        .FILL #15098 ; k=150, X=4800
        .FILL #15195 ; k=152, X=4864
        .FILL #15289 ; k=154, X=4928
        .FILL #15379 ; k=156, X=4992
        .FILL #15466 ; k=158, X=5056
        .FILL #15548 ; k=160, X=5120
        .FILL #15627 ; k=162, X=5184
        .FILL #15702 ; k=164, X=5248
        .FILL #15773 ; k=166, X=5312
        .FILL #15840 ; k=168, X=5376
        .FILL #15904 ; k=170, X=5440
        .FILL #15964 ; k=172, X=5504
        .FILL #16019 ; k=174, X=5568
        .FILL #16071 ; k=176, X=5632
        .FILL #16119 ; k=178, X=5696
        .FILL #16163 ; k=180, X=5760
        .FILL #16203 ; k=182, X=5824
        .FILL #16239 ; k=184, X=5888
        .FILL #16271 ; k=186, X=5952
        .FILL #16299 ; k=188, X=6016
        .FILL #16323 ; k=190, X=6080
        .FILL #16343 ; k=192, X=6144
        .FILL #16359 ; k=194, X=6208
        .FILL #16371 ; k=196, X=6272
        .FILL #16379 ; k=198, X=6336
        .FILL #16383 ; k=200, X=6400
        .FILL #16384 ; k=202, X=6464

        .END
