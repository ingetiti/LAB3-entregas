; V3: nucleo 12E + cuadrantes y cofuncion validados en 12F3.
; ================================================================
; INTERFACES PUBLICAS V3 PARA COMPARACION CON V2
; Entrada R0 = angulo Q3.12.
; Salida R0 = seno o coseno Q1.14.
; Preserva R1-R5 y recupera R6. R7 se restaura para el RET.
; Cada interfaz calcula ambos resultados, igual que las interfaces V2.
; ================================================================

SENO_TABLA
        ADD  R6, R6, #-2
        STR  R7, R6, #0
        JSR  CALCULAR_AMBOS_V3
        LDR  R7, R6, #0
        ADD  R6, R6, #2
        RET

COSENO_TABLA
        ADD  R6, R6, #-2
        STR  R1, R6, #0
        ADD  R6, R6, #-2
        STR  R7, R6, #0
        JSR  CALCULAR_AMBOS_V3
        LEA  R1, RESULTADO_COSENO
        LDR  R0, R1, #0
        LDR  R7, R6, #0
        ADD  R6, R6, #2
        LDR  R1, R6, #0
        ADD  R6, R6, #2
        RET
; Buffers internos compartidos por las interfaces publicas y el nucleo.
RESULTADO_SENO   .BLKW #1
RESULTADO_COSENO .BLKW #1
TEMP_SENO        .BLKW #1

; ------------------------------------------------
; SUBRUTINA DE INTEGRACION: CUADRANTE + SENO + COSENO
; Entrada R0 = angulo Q3.12, salida R0 = seno Q1.14.
; RESULTADO_COSENO contiene el coseno Q1.14.
; Preserva R1-R5 y R6; restaura R7 para el llamador.
; ------------------------------------------------
CALCULAR_AMBOS_V3
        ADD  R6, R6, #-2
        STR  R1, R6, #0
        ADD  R6, R6, #-2
        STR  R2, R6, #0
        ADD  R6, R6, #-2
        STR  R3, R6, #0
        ADD  R6, R6, #-2
        STR  R4, R6, #0
        ADD  R6, R6, #-2
        STR  R5, R6, #0
        ADD  R6, R6, #-2
        STR  R7, R6, #0

; R1 conserva el angulo original durante la clasificacion.
        ADD  R1, R0, #0
        LEA  R5, CONSTANTES_ANGULARES

; Si angulo < PI/2, cuadrante 1.
        LDR  R2, R5, #0
        NOT  R2, R2
        ADD  R2, R2, #1
        ADD  R2, R1, R2
        BRn  CUADRANTE_1_V3

; Si angulo < PI, cuadrante 2.
        LDR  R2, R5, #1
        NOT  R2, R2
        ADD  R2, R2, #1
        ADD  R2, R1, R2
        BRn  CUADRANTE_2_V3

; Si angulo < 3PI/2, cuadrante 3.
        LDR  R2, R5, #2
        NOT  R2, R2
        ADD  R2, R2, #1
        ADD  R2, R1, R2
        BRn  CUADRANTE_3_V3

; Resto del dominio: cuadrante 4, incluyendo 2PI.
CUADRANTE_4_V3
        LDR  R2, R5, #3
        NOT  R2, R2
        ADD  R2, R2, #1
        ADD  R2, R1, R2
        NOT  R2, R2
        ADD  R2, R2, #1
        AND  R4, R4, #0
        ADD  R4, R4, #-1
        AND  R5, R5, #0
        ADD  R5, R5, #1   ; @ok
        BRnzp REFERENCIAS_LISTAS_V3

CUADRANTE_1_V3
        ADD  R2, R1, #0
        AND  R4, R4, #0
        ADD  R4, R4, #1
        AND  R5, R5, #0
        ADD  R5, R5, #1
        BRnzp REFERENCIAS_LISTAS_V3

CUADRANTE_2_V3
        LEA  R5, CONSTANTES_ANGULARES
        LDR  R2, R5, #1
        NOT  R2, R2
        ADD  R2, R2, #1
        ADD  R2, R1, R2
        NOT  R2, R2
        ADD  R2, R2, #1
        AND  R4, R4, #0
        ADD  R4, R4, #1
        AND  R5, R5, #0
        ADD  R5, R5, #-1   ; @ok
        BRnzp REFERENCIAS_LISTAS_V3

CUADRANTE_3_V3
        LEA  R5, CONSTANTES_ANGULARES
        LDR  R2, R5, #1
        NOT  R2, R2
        ADD  R2, R2, #1
        ADD  R2, R1, R2
        AND  R4, R4, #0
        ADD  R4, R4, #-1
        AND  R5, R5, #0
        ADD  R5, R5, #-1   ; @ok

REFERENCIAS_LISTAS_V3
; R2 = referencia del seno; R3 = PI/2 - referencia.
        LEA  R1, CONSTANTES_ANGULARES
        LDR  R3, R1, #0
        NOT  R3, R3
        ADD  R3, R3, #1
        ADD  R3, R2, R3
        NOT  R3, R3
        ADD  R3, R3, #1

; Primera llamada: interpolar seno.
        ADD  R0, R2, #0
        JSR  INTERPOLAR_PRIMER_CUADRANTE
        LEA  R1, TEMP_SENO
        STR  R0, R1, #0

; Segunda llamada: interpolar coseno mediante cofuncion.
        ADD  R0, R3, #0
        JSR  INTERPOLAR_PRIMER_CUADRANTE
        LEA  R1, RESULTADO_COSENO
        STR  R0, R1, #0

; Aplicar signo al seno y guardar resultado.
        LEA  R1, TEMP_SENO
        LDR  R2, R1, #0
        ADD  R4, R4, #0
        BRzp SENO_POSITIVO_V3
        NOT  R2, R2
        ADD  R2, R2, #1
SENO_POSITIVO_V3
        LEA  R1, RESULTADO_SENO
        STR  R2, R1, #0

; Aplicar signo al coseno y guardar resultado.
        LEA  R1, RESULTADO_COSENO
        LDR  R2, R1, #0
        ADD  R5, R5, #0
        BRzp COSENO_POSITIVO_V3
        NOT  R2, R2
        ADD  R2, R2, #1
COSENO_POSITIVO_V3
        LEA  R1, RESULTADO_COSENO
        STR  R2, R1, #0

; Retornar el seno en R0 y restaurar contexto.
        LEA  R1, RESULTADO_SENO
        LDR  R0, R1, #0
        LDR  R7, R6, #0
        ADD  R6, R6, #2
        LDR  R5, R6, #0
        ADD  R6, R6, #2
        LDR  R4, R6, #0
        ADD  R6, R6, #2
        LDR  R3, R6, #0
        ADD  R6, R6, #2
        LDR  R2, R6, #0
        ADD  R6, R6, #2
        LDR  R1, R6, #0
        ADD  R6, R6, #2
        RET

CONSTANTES_ANGULARES
        .FILL #6434
        .FILL #12868
        .FILL #19302
        .FILL #25736

INTERPOLAR_PRIMER_CUADRANTE
; Guardar registros de trabajo. R6 funciona como puntero de pila.
        ADD  R6, R6, #-2
        STR  R1, R6, #0
        ADD  R6, R6, #-2
        STR  R2, R6, #0
        ADD  R6, R6, #-2
        STR  R3, R6, #0
        ADD  R6, R6, #-2
        STR  R4, R6, #0
        ADD  R6, R6, #-2
        STR  R5, R6, #0
        ADD  R6, R6, #-2
        STR  R7, R6, #0

; 1. Separar resto angular: resto = angulo AND 31.
        ADD  R1, R0, #0
        LEA  R2, MASCARA_RESTO
        LDR  R2, R2, #0
        AND  R3, R0, R2

; 2. Calcular indice = floor(angulo / 32), extrayendo bits 12..5.
        AND  R4, R4, #0
        ADD  R1, R1, R1
        ADD  R1, R1, R1
        ADD  R1, R1, R1
        BRn  IDX12_UNO
        ADD  R4, R4, R4
        BRnzp IDX11
IDX12_UNO
        ADD  R4, R4, R4
        ADD  R4, R4, #1
IDX11
        ADD  R1, R1, R1
        BRn  IDX11_UNO
        ADD  R4, R4, R4
        BRnzp IDX10
IDX11_UNO
        ADD  R4, R4, R4
        ADD  R4, R4, #1
IDX10
        ADD  R1, R1, R1
        BRn  IDX10_UNO
        ADD  R4, R4, R4
        BRnzp IDX9
IDX10_UNO
        ADD  R4, R4, R4
        ADD  R4, R4, #1
IDX9
        ADD  R1, R1, R1
        BRn  IDX9_UNO
        ADD  R4, R4, R4
        BRnzp IDX8
IDX9_UNO
        ADD  R4, R4, R4
        ADD  R4, R4, #1
IDX8
        ADD  R1, R1, R1
        BRn  IDX8_UNO
        ADD  R4, R4, R4
        BRnzp IDX7
IDX8_UNO
        ADD  R4, R4, R4
        ADD  R4, R4, #1
IDX7
        ADD  R1, R1, R1
        BRn  IDX7_UNO
        ADD  R4, R4, R4
        BRnzp IDX6
IDX7_UNO
        ADD  R4, R4, R4
        ADD  R4, R4, #1
IDX6
        ADD  R1, R1, R1
        BRn  IDX6_UNO
        ADD  R4, R4, R4
        BRnzp IDX5
IDX6_UNO
        ADD  R4, R4, R4
        ADD  R4, R4, #1
IDX5
        ADD  R1, R1, R1
        BRn  IDX5_UNO
        ADD  R4, R4, R4
        BRnzp FIN_INDICE
IDX5_UNO
        ADD  R4, R4, R4
        ADD  R4, R4, #1
FIN_INDICE

; 3. Leer dos muestras consecutivas mediante direccionamiento dinamico.
        LEA  R5, TABLA_SENO_203
        ADD  R5, R5, R4
        ADD  R5, R5, R4         ; @ok indice*2 (palabras de 2 bytes)
        LDR  R1, R5, #0
        LDR  R2, R5, #1

; 4. Calcular delta = muestra siguiente - muestra actual.
        NOT  R7, R1
        ADD  R7, R7, #1
        ADD  R7, R2, R7

; 5. Producto = delta * resto, con cinco etapas binarias.
        AND  R4, R4, #0
        LEA  R2, MASCARAS_MULT
; Bit 16.
        ADD  R4, R4, R4
        LDR  R0, R2, #0
        AND  R0, R3, R0
        BRz  MUL_16_CERO
        ADD  R4, R4, R7
MUL_16_CERO
; Bit 8.
        ADD  R4, R4, R4
        LDR  R0, R2, #1
        AND  R0, R3, R0
        BRz  MUL_8_CERO
        ADD  R4, R4, R7
MUL_8_CERO
; Bit 4.
        ADD  R4, R4, R4
        LDR  R0, R2, #2
        AND  R0, R3, R0
        BRz  MUL_4_CERO
        ADD  R4, R4, R7
MUL_4_CERO
; Bit 2.
        ADD  R4, R4, R4
        LDR  R0, R2, #3
        AND  R0, R3, R0
        BRz  MUL_2_CERO
        ADD  R4, R4, R7
MUL_2_CERO
; Bit 1.
        ADD  R4, R4, R4
        LDR  R0, R2, #4
        AND  R0, R3, R0
        BRz  MUL_1_CERO
        ADD  R4, R4, R7
MUL_1_CERO

; 6. Redondear y dividir por 32 con las ramas optimizadas de 12E.
; R1 conserva la muestra actual y se copia a R5.
        ADD  R5, R1, #0
        LEA  R2, CONSTANTE_16
        LDR  R0, R2, #0
        ADD  R4, R4, R0
        ADD  R2, R4, #0
        ADD  R0, R2, #0
        AND  R1, R1, #0
; Alinear el bit 11 con el bit de signo.
        ADD  R0, R0, R0
        ADD  R0, R0, R0
        ADD  R0, R0, R0
        ADD  R0, R0, R0
; Extraer bits 11..5: se mantiene el orden de ramas medido en 12E.
        BRzp DIV11_CERO
        ADD  R1, R1, R1
        ADD  R1, R1, #1
        BRnzp DIV10
DIV11_CERO
        ADD  R1, R1, R1
DIV10
        ADD  R0, R0, R0
        BRzp DIV10_CERO
        ADD  R1, R1, R1
        ADD  R1, R1, #1
        BRnzp DIV9
DIV10_CERO
        ADD  R1, R1, R1
DIV9
        ADD  R0, R0, R0
        BRzp DIV9_CERO
        ADD  R1, R1, R1
        ADD  R1, R1, #1
        BRnzp DIV8
DIV9_CERO
        ADD  R1, R1, R1
DIV8
        ADD  R0, R0, R0
        BRzp DIV8_CERO
        ADD  R1, R1, R1
        ADD  R1, R1, #1
        BRnzp DIV7
DIV8_CERO
        ADD  R1, R1, R1
DIV7
        ADD  R0, R0, R0
        BRzp DIV7_CERO
        ADD  R1, R1, R1
        ADD  R1, R1, #1
        BRnzp DIV6
DIV7_CERO
        ADD  R1, R1, R1
DIV6
        ADD  R0, R0, R0
        BRzp DIV6_CERO
        ADD  R1, R1, R1
        ADD  R1, R1, #1
        BRnzp DIV5
DIV6_CERO
        ADD  R1, R1, R1
DIV5
        ADD  R0, R0, R0
        BRzp DIV5_CERO
        ADD  R1, R1, R1
        ADD  R1, R1, #1
        BRnzp FIN_DIVISION
DIV5_CERO
        ADD  R1, R1, R1
FIN_DIVISION

; 7. Resultado final = muestra actual + incremento.
        ADD  R0, R5, R1

; Restaurar registros. R0 conserva el resultado de retorno.
        LDR  R7, R6, #0
        ADD  R6, R6, #2
        LDR  R5, R6, #0
        ADD  R6, R6, #2
        LDR  R4, R6, #0
        ADD  R6, R6, #2
        LDR  R3, R6, #0
        ADD  R6, R6, #2
        LDR  R2, R6, #0
        ADD  R6, R6, #2
        LDR  R1, R6, #0
        ADD  R6, R6, #2
        RET

; Constantes de la subrutina. Se leen mediante puntero + LDR.
MASCARA_RESTO       .FILL x001F
CONSTANTE_16        .FILL #16
MASCARAS_MULT
        .FILL x0010
        .FILL x0008
        .FILL x0004
        .FILL x0002
        .FILL x0001

TABLA_SENO_203
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
