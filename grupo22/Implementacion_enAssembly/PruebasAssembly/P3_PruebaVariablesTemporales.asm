        .ORIG x3000

; PRUEBA 03 - VARIABLES TEMPORALES
; ==========================================

INICIO

; ------------------------------------------
; 1. SIGNO DEL SENO = -1
; ------------------------------------------

        LEA R1, SIGNO_SENO
        AND R0, R0, #0
        ADD R0, R0, #-1
        STR R0, R1, #0
        LDR R2, R1, #0

; ------------------------------------------
; 2. SIGNO DEL COSENO = +1
; ------------------------------------------

        LEA R1, SIGNO_COSENO
        AND R0, R0, #0
        ADD R0, R0, #1
        STR R0, R1, #0
        LDR R2, R1, #0

; ------------------------------------------
; 3. ANGULO DE REFERENCIA = 7 (PRUEBA)
; ------------------------------------------

        LEA R1, ANGULO_REFERENCIA
        AND R0, R0, #0
        ADD R0, R0, #7
        STR R0, R1, #0
        LDR R2, R1, #0

; ------------------------------------------
; 4. RESULTADO DEL SENO = 11 (PRUEBA)
; ------------------------------------------

        LEA R1, RESULTADO_SENO
        AND R0, R0, #0
        ADD R0, R0, #11
        STR R0, R1, #0
        LDR R2, R1, #0

; ------------------------------------------
; 5. RESULTADO DEL COSENO = -13 (PRUEBA)
; ------------------------------------------

        LEA R1, RESULTADO_COSENO
        AND R0, R0, #0
        ADD R0, R0, #-13
        STR R0, R1, #0
        LDR R2, R1, #0

; ------------------------------------------
; 6. REFERENCIA EN GRADOS = 9 (PRUEBA)
; ------------------------------------------

        LEA R1, REFERENCIA_GRADOS
        AND R0, R0, #0
        ADD R0, R0, #9
        STR R0, R1, #0
        LDR R2, R1, #0

        HALT

; ==========================================
; VARIABLES TEMPORALES
; ==========================================

SIGNO_SENO .BLKW #1

SIGNO_COSENO .BLKW #1

ANGULO_REFERENCIA .BLKW #1

RESULTADO_SENO .BLKW #1

RESULTADO_COSENO .BLKW #1

REFERENCIA_GRADOS .BLKW #1

; ==========================================
; TABLA DE SENO EN FORMATO Q1.14
; ==========================================

TABLA_SENO
        .FILL #0 ; Resultado de seno(0)
        .FILL #286 ; Resultado de seno(1)
        .FILL #572 ; Resultado de seno(2)
        .FILL #857 ; Resultado de seno(3)
        .FILL #1143 ; Resultado de seno(4)
        .FILL #1428 ; Resultado de seno(5)
        .FILL #1713 ; Resultado de seno(6)
        .FILL #1997 ; Resultado de seno(7)
        .FILL #2280 ; Resultado de seno(8)
        .FILL #2563 ; Resultado de seno(9)
        .FILL #2845 ; Resultado de seno(10)
        .FILL #3126 ; Resultado de seno(11)
        .FILL #3406 ; Resultado de seno(12)
        .FILL #3686 ; Resultado de seno(13)
        .FILL #3964 ; Resultado de seno(14)
        .FILL #4240 ; Resultado de seno(15)
        .FILL #4516 ; Resultado de seno(16)
        .FILL #4790 ; Resultado de seno(17)
        .FILL #5063 ; Resultado de seno(18)
        .FILL #5334 ; Resultado de seno(19)
        .FILL #5604 ; Resultado de seno(20)
        .FILL #5872 ; Resultado de seno(21)
        .FILL #6138 ; Resultado de seno(22)
        .FILL #6402 ; Resultado de seno(23)
        .FILL #6664 ; Resultado de seno(24)
        .FILL #6924 ; Resultado de seno(25)
        .FILL #7182 ; Resultado de seno(26)
        .FILL #7438 ; Resultado de seno(27)
        .FILL #7692 ; Resultado de seno(28)
        .FILL #7943 ; Resultado de seno(29)
        .FILL #8192 ; Resultado de seno(30)
        .FILL #8438 ; Resultado de seno(31)
        .FILL #8682 ; Resultado de seno(32)
        .FILL #8923 ; Resultado de seno(33)
        .FILL #9162 ; Resultado de seno(34)
        .FILL #9397 ; Resultado de seno(35)
        .FILL #9630 ; Resultado de seno(36)
        .FILL #9860 ; Resultado de seno(37)
        .FILL #10087 ; Resultado de seno(38)
        .FILL #10311 ; Resultado de seno(39)
        .FILL #10531 ; Resultado de seno(40)
        .FILL #10749 ; Resultado de seno(41)
        .FILL #10963 ; Resultado de seno(42)
        .FILL #11174 ; Resultado de seno(43)
        .FILL #11381 ; Resultado de seno(44)
        .FILL #11585 ; Resultado de seno(45)
        .FILL #11786 ; Resultado de seno(46)
        .FILL #11982 ; Resultado de seno(47)
        .FILL #12176 ; Resultado de seno(48)
        .FILL #12365 ; Resultado de seno(49)
        .FILL #12551 ; Resultado de seno(50)
        .FILL #12733 ; Resultado de seno(51)
        .FILL #12911 ; Resultado de seno(52)
        .FILL #13085 ; Resultado de seno(53)
        .FILL #13255 ; Resultado de seno(54)
        .FILL #13421 ; Resultado de seno(55)
        .FILL #13583 ; Resultado de seno(56)
        .FILL #13741 ; Resultado de seno(57)
        .FILL #13894 ; Resultado de seno(58)
        .FILL #14044 ; Resultado de seno(59)
        .FILL #14189 ; Resultado de seno(60)
        .FILL #14330 ; Resultado de seno(61)
        .FILL #14466 ; Resultado de seno(62)
        .FILL #14598 ; Resultado de seno(63)
        .FILL #14726 ; Resultado de seno(64)
        .FILL #14849 ; Resultado de seno(65)
        .FILL #14968 ; Resultado de seno(66)
        .FILL #15082 ; Resultado de seno(67)
        .FILL #15191 ; Resultado de seno(68)
        .FILL #15296 ; Resultado de seno(69)
        .FILL #15396 ; Resultado de seno(70)
        .FILL #15491 ; Resultado de seno(71)
        .FILL #15582 ; Resultado de seno(72)
        .FILL #15668 ; Resultado de seno(73)
        .FILL #15749 ; Resultado de seno(74)
        .FILL #15826 ; Resultado de seno(75)
        .FILL #15897 ; Resultado de seno(76)
        .FILL #15964 ; Resultado de seno(77)
        .FILL #16026 ; Resultado de seno(78)
        .FILL #16083 ; Resultado de seno(79)
        .FILL #16135 ; Resultado de seno(80)
        .FILL #16182 ; Resultado de seno(81)
        .FILL #16225 ; Resultado de seno(82)
        .FILL #16262 ; Resultado de seno(83)
        .FILL #16294 ; Resultado de seno(84)
        .FILL #16322 ; Resultado de seno(85)
        .FILL #16344 ; Resultado de seno(86)
        .FILL #16362 ; Resultado de seno(87)
        .FILL #16374 ; Resultado de seno(88)
        .FILL #16382 ; Resultado de seno(89)
        .FILL #16384 ; Resultado de seno(90)

.END