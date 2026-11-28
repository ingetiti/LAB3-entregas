;=====================================================================
; SUBRUTINAS: SENO_TABLA y COSENO_TABLA (Por LUT + interpolación lineal)
;
;   Entradas:
;     R0 = ángulo en radianes (formato Q3.12 con signo)
;   Salidas:
;     R0 = sin(ángulo) o cos(ángulo) en formato Q1.14 con signo
;          (1.0 = 16384 = x4000, -1.0 = -16384 = xC000)
;   Conserva: R1-R5, R6 (intacto) y R7.
;=====================================================================

; --------------------------------------------------------------------
; COSENO_TABLA: cos(theta) = sin(theta + pi/2)
; --------------------------------------------------------------------
COSENO_TABLA:
        ST      R1, COS_SAVE_R1
        ST      R7, COS_SAVE_R7

        LD      R1, C_PI_2          ; +pi/2 en Q3.12 (6434)
        ADD     R0, R0, R1          ; theta + pi/2
        JSR     SENO_TABLA          ; Calcula sin(theta + pi/2)

        LD      R1, COS_SAVE_R1
        LD      R7, COS_SAVE_R7
        ADD     R0, R0, #0          ; Actualizar CC con resultado en R0
        RET

; --------------------------------------------------------------------
; SENO_TABLA: sin(theta) mediante tabla de 203 muestras + interpolación
; --------------------------------------------------------------------
SENO_TABLA:
        ST      R1, SEN_SAVE_R1
        ST      R2, SEN_SAVE_R2
        ST      R3, SEN_SAVE_R3
        ST      R4, SEN_SAVE_R4
        ST      R5, SEN_SAVE_R5
        ST      R7, SEN_SAVE_R7

        ; 1. Normalizar ángulo a [0, 2*pi) en Q3.12 usando MOD
        LD      R1, C_2PI           ; 25736 (2*pi en Q3.12)
        MOD     R0, R0, R1          ; R0 en (-25736, +25736)
        ADD     R0, R0, #0
        BRzp    ST_RANGO_OK
        ADD     R0, R0, R1          ; Si era negativo, llevar a [0, 2*pi)
ST_RANGO_OK:

        ; 2. Clasificar cuadrante, obtener ángulo de referencia en [0, pi/2]
        ;    y signo del seno en R5 (+1 en Q1/Q2, -1 en Q3/Q4)
        AND     R5, R5, #0
        ADD     R5, R5, #1          ; R5 = +1 (signo positivo por defecto)

        LD      R1, NEG_PI          ; -12868 (-pi)
        ADD     R2, R0, R1          ; R2 = theta - pi
        BRn     ST_MITAD_SUP        ; theta < pi -> cuadrante 1 o 2

        ; Mitad inferior [pi, 2*pi): theta = theta - pi, signo = -1
        ADD     R0, R2, #0
        AND     R5, R5, #0
        ADD     R5, R5, #-1         ; R5 = -1

ST_MITAD_SUP:
        ; Ahora R0 está en [0, pi). Si R0 > pi/2, reflejar: theta_ref = pi - R0
        LD      R1, NEG_PI_2        ; -6434 (-pi/2)
        ADD     R2, R0, R1          ; R2 = theta - pi/2
        BRnz    ST_INTERPOLAR       ; theta <= pi/2 -> R0 ya es theta_ref

        LD      R1, C_PI            ; 12868 (pi)
        NOT     R0, R0
        ADD     R0, R0, #1
        ADD     R0, R1, R0          ; R0 = pi - theta (en [0, pi/2])

        ; 3. Interpolación lineal sobre TABLA_SENO_203 (paso = 32 unidades Q3.12)
ST_INTERPOLAR:
        ; resto = R0 & x001F (5 bits bajos)
        LD      R1, MASCARA_RESTO
        AND     R3, R0, R1          ; R3 = resto (0..31)

        ; índice k = R0 >> 5 (0..201)
        RSH     R4, R0, #5          ; R4 = k
        ADD     R4, R4, R4          ; k * 2 (2 bytes por palabra en ISA-G27)

        ; Leer muestra[k] y muestra[k + 1]
        LEA     R1, TABLA_SENO_203
        ADD     R1, R1, R4
        LDR     R2, R1, #0          ; R2 = muestra[k]
        LDR     R4, R1, #1          ; R4 = muestra[k + 1]

        ; delta = muestra[k + 1] - muestra[k]
        NOT     R1, R2
        ADD     R1, R1, #1
        ADD     R4, R4, R1          ; R4 = delta

        ; incremento = (delta * resto + 16) >> 5
        MUL     R4, R4, R3          ; delta * resto (cabe en 16 bits sin signo)
        LD      R1, CONST_16
        ADD     R4, R4, R1          ; +16 para redondeo al entero más cercano
        RSH     R4, R4, #5          ; / 32

        ; magnitud = muestra[k] + incremento
        ADD     R0, R2, R4

        ; 4. Aplicar signo del cuadrante (R5)
        ADD     R5, R5, #0
        BRzp    ST_FIN
        NOT     R0, R0
        ADD     R0, R0, #1

ST_FIN:
        LD      R1, SEN_SAVE_R1
        LD      R2, SEN_SAVE_R2
        LD      R3, SEN_SAVE_R3
        LD      R4, SEN_SAVE_R4
        LD      R5, SEN_SAVE_R5
        LD      R7, SEN_SAVE_R7
        ADD     R0, R0, #0          ; Actualizar CC con resultado en R0
        RET

;=====================================================================
; ZONA DE DATOS Y TABLA LUT (203 muestras Q1.14)
;=====================================================================
C_PI_2:         .FILL #6434         ; pi/2 en Q3.12
NEG_PI_2:       .FILL #-6434        ; -pi/2 en Q3.12
C_PI:           .FILL #12868        ; pi en Q3.12
NEG_PI:         .FILL #-12868       ; -pi en Q3.12
C_2PI:          .FILL #25736        ; 2*pi en Q3.12
MASCARA_RESTO:  .FILL x001F         ; Máscara de 5 bits bajos (0..31)
CONST_16:       .FILL #16           ; Redondeo 0.5 * 32

COS_SAVE_R1:    .FILL #0
COS_SAVE_R7:    .FILL #0

SEN_SAVE_R1:    .FILL #0
SEN_SAVE_R2:    .FILL #0
SEN_SAVE_R3:    .FILL #0
SEN_SAVE_R4:    .FILL #0
SEN_SAVE_R5:    .FILL #0
SEN_SAVE_R7:    .FILL #0

TABLA_SENO_203:
        .FILL #0 ; k=  0, X=   0
        .FILL #128 ; k=  1, X=  32
        .FILL #256 ; k=  2, X=  64
        .FILL #384 ; k=  3, X=  96
        .FILL #512 ; k=  4, X= 128
        .FILL #640 ; k=  5, X= 160
        .FILL #768 ; k=  6, X= 192
        .FILL #896 ; k=  7, X= 224
        .FILL #1023 ; k=  8, X= 256
        .FILL #1151 ; k=  9, X= 288
        .FILL #1279 ; k= 10, X= 320
        .FILL #1406 ; k= 11, X= 352
        .FILL #1534 ; k= 12, X= 384
        .FILL #1661 ; k= 13, X= 416
        .FILL #1788 ; k= 14, X= 448
        .FILL #1916 ; k= 15, X= 480
        .FILL #2043 ; k= 16, X= 512
        .FILL #2170 ; k= 17, X= 544
        .FILL #2296 ; k= 18, X= 576
        .FILL #2423 ; k= 19, X= 608
        .FILL #2550 ; k= 20, X= 640
        .FILL #2676 ; k= 21, X= 672
        .FILL #2802 ; k= 22, X= 704
        .FILL #2928 ; k= 23, X= 736
        .FILL #3054 ; k= 24, X= 768
        .FILL #3180 ; k= 25, X= 800
        .FILL #3305 ; k= 26, X= 832
        .FILL #3430 ; k= 27, X= 864
        .FILL #3555 ; k= 28, X= 896
        .FILL #3680 ; k= 29, X= 928
        .FILL #3805 ; k= 30, X= 960
        .FILL #3929 ; k= 31, X= 992
        .FILL #4053 ; k= 32, X=1024
        .FILL #4177 ; k= 33, X=1056
        .FILL #4301 ; k= 34, X=1088
        .FILL #4424 ; k= 35, X=1120
        .FILL #4547 ; k= 36, X=1152
        .FILL #4670 ; k= 37, X=1184
        .FILL #4793 ; k= 38, X=1216
        .FILL #4915 ; k= 39, X=1248
        .FILL #5037 ; k= 40, X=1280
        .FILL #5159 ; k= 41, X=1312
        .FILL #5280 ; k= 42, X=1344
        .FILL #5401 ; k= 43, X=1376
        .FILL #5522 ; k= 44, X=1408
        .FILL #5642 ; k= 45, X=1440
        .FILL #5762 ; k= 46, X=1472
        .FILL #5882 ; k= 47, X=1504
        .FILL #6001 ; k= 48, X=1536
        .FILL #6120 ; k= 49, X=1568
        .FILL #6238 ; k= 50, X=1600
        .FILL #6357 ; k= 51, X=1632
        .FILL #6474 ; k= 52, X=1664
        .FILL #6592 ; k= 53, X=1696
        .FILL #6709 ; k= 54, X=1728
        .FILL #6825 ; k= 55, X=1760
        .FILL #6942 ; k= 56, X=1792
        .FILL #7057 ; k= 57, X=1824
        .FILL #7173 ; k= 58, X=1856
        .FILL #7287 ; k= 59, X=1888
        .FILL #7402 ; k= 60, X=1920
        .FILL #7516 ; k= 61, X=1952
        .FILL #7629 ; k= 62, X=1984
        .FILL #7742 ; k= 63, X=2016
        .FILL #7855 ; k= 64, X=2048
        .FILL #7967 ; k= 65, X=2080
        .FILL #8079 ; k= 66, X=2112
        .FILL #8190 ; k= 67, X=2144
        .FILL #8300 ; k= 68, X=2176
        .FILL #8410 ; k= 69, X=2208
        .FILL #8520 ; k= 70, X=2240
        .FILL #8629 ; k= 71, X=2272
        .FILL #8738 ; k= 72, X=2304
        .FILL #8846 ; k= 73, X=2336
        .FILL #8953 ; k= 74, X=2368
        .FILL #9060 ; k= 75, X=2400
        .FILL #9166 ; k= 76, X=2432
        .FILL #9272 ; k= 77, X=2464
        .FILL #9377 ; k= 78, X=2496
        .FILL #9482 ; k= 79, X=2528
        .FILL #9586 ; k= 80, X=2560
        .FILL #9690 ; k= 81, X=2592
        .FILL #9793 ; k= 82, X=2624
        .FILL #9895 ; k= 83, X=2656
        .FILL #9997 ; k= 84, X=2688
        .FILL #10098 ; k= 85, X=2720
        .FILL #10198 ; k= 86, X=2752
        .FILL #10298 ; k= 87, X=2784
        .FILL #10397 ; k= 88, X=2816
        .FILL #10496 ; k= 89, X=2848
        .FILL #10594 ; k= 90, X=2880
        .FILL #10691 ; k= 91, X=2912
        .FILL #10788 ; k= 92, X=2944
        .FILL #10884 ; k= 93, X=2976
        .FILL #10979 ; k= 94, X=3008
        .FILL #11074 ; k= 95, X=3040
        .FILL #11168 ; k= 96, X=3072
        .FILL #11261 ; k= 97, X=3104
        .FILL #11354 ; k= 98, X=3136
        .FILL #11446 ; k= 99, X=3168
        .FILL #11537 ; k=100, X=3200
        .FILL #11628 ; k=101, X=3232
        .FILL #11717 ; k=102, X=3264
        .FILL #11807 ; k=103, X=3296
        .FILL #11895 ; k=104, X=3328
        .FILL #11983 ; k=105, X=3360
        .FILL #12070 ; k=106, X=3392
        .FILL #12156 ; k=107, X=3424
        .FILL #12241 ; k=108, X=3456
        .FILL #12326 ; k=109, X=3488
        .FILL #12410 ; k=110, X=3520
        .FILL #12493 ; k=111, X=3552
        .FILL #12575 ; k=112, X=3584
        .FILL #12657 ; k=113, X=3616
        .FILL #12738 ; k=114, X=3648
        .FILL #12818 ; k=115, X=3680
        .FILL #12897 ; k=116, X=3712
        .FILL #12976 ; k=117, X=3744
        .FILL #13054 ; k=118, X=3776
        .FILL #13131 ; k=119, X=3808
        .FILL #13207 ; k=120, X=3840
        .FILL #13282 ; k=121, X=3872
        .FILL #13357 ; k=122, X=3904
        .FILL #13430 ; k=123, X=3936
        .FILL #13503 ; k=124, X=3968
        .FILL #13575 ; k=125, X=4000
        .FILL #13647 ; k=126, X=4032
        .FILL #13717 ; k=127, X=4064
        .FILL #13787 ; k=128, X=4096
        .FILL #13855 ; k=129, X=4128
        .FILL #13923 ; k=130, X=4160
        .FILL #13990 ; k=131, X=4192
        .FILL #14057 ; k=132, X=4224
        .FILL #14122 ; k=133, X=4256
        .FILL #14186 ; k=134, X=4288
        .FILL #14250 ; k=135, X=4320
        .FILL #14313 ; k=136, X=4352
        .FILL #14375 ; k=137, X=4384
        .FILL #14435 ; k=138, X=4416
        .FILL #14496 ; k=139, X=4448
        .FILL #14555 ; k=140, X=4480
        .FILL #14613 ; k=141, X=4512
        .FILL #14671 ; k=142, X=4544
        .FILL #14727 ; k=143, X=4576
        .FILL #14783 ; k=144, X=4608
        .FILL #14837 ; k=145, X=4640
        .FILL #14891 ; k=146, X=4672
        .FILL #14944 ; k=147, X=4704
        .FILL #14996 ; k=148, X=4736
        .FILL #15047 ; k=149, X=4768
        .FILL #15098 ; k=150, X=4800
        .FILL #15147 ; k=151, X=4832
        .FILL #15195 ; k=152, X=4864
        .FILL #15243 ; k=153, X=4896
        .FILL #15289 ; k=154, X=4928
        .FILL #15335 ; k=155, X=4960
        .FILL #15379 ; k=156, X=4992
        .FILL #15423 ; k=157, X=5024
        .FILL #15466 ; k=158, X=5056
        .FILL #15507 ; k=159, X=5088
        .FILL #15548 ; k=160, X=5120
        .FILL #15588 ; k=161, X=5152
        .FILL #15627 ; k=162, X=5184
        .FILL #15665 ; k=163, X=5216
        .FILL #15702 ; k=164, X=5248
        .FILL #15738 ; k=165, X=5280
        .FILL #15773 ; k=166, X=5312
        .FILL #15807 ; k=167, X=5344
        .FILL #15840 ; k=168, X=5376
        .FILL #15873 ; k=169, X=5408
        .FILL #15904 ; k=170, X=5440
        .FILL #15934 ; k=171, X=5472
        .FILL #15964 ; k=172, X=5504
        .FILL #15992 ; k=173, X=5536
        .FILL #16019 ; k=174, X=5568
        .FILL #16046 ; k=175, X=5600
        .FILL #16071 ; k=176, X=5632
        .FILL #16095 ; k=177, X=5664
        .FILL #16119 ; k=178, X=5696
        .FILL #16141 ; k=179, X=5728
        .FILL #16163 ; k=180, X=5760
        .FILL #16183 ; k=181, X=5792
        .FILL #16203 ; k=182, X=5824
        .FILL #16221 ; k=183, X=5856
        .FILL #16239 ; k=184, X=5888
        .FILL #16255 ; k=185, X=5920
        .FILL #16271 ; k=186, X=5952
        .FILL #16285 ; k=187, X=5984
        .FILL #16299 ; k=188, X=6016
        .FILL #16311 ; k=189, X=6048
        .FILL #16323 ; k=190, X=6080
        .FILL #16333 ; k=191, X=6112
        .FILL #16343 ; k=192, X=6144
        .FILL #16352 ; k=193, X=6176
        .FILL #16359 ; k=194, X=6208
        .FILL #16366 ; k=195, X=6240
        .FILL #16371 ; k=196, X=6272
        .FILL #16376 ; k=197, X=6304
        .FILL #16379 ; k=198, X=6336
        .FILL #16382 ; k=199, X=6368
        .FILL #16383 ; k=200, X=6400
        .FILL #16384 ; k=201, X=6432
        .FILL #16384 ; k=202, X=6464

.END