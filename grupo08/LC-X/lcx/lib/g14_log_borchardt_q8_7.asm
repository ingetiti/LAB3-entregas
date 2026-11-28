;=============================================================================
; MODULO: LOG_BORCHARDT_Q8_7 (GRUPO 14) - LC-X
; Funcion publica: LN_GENERAL_Q8_7
;
; CONVENCION DE LLAMADA (igual que la version LC-3)
;   Entrada : R0 = x en Q8.7 (1.0 = 128 / x0080, 2.0 = 256 / x0100)
;   Salida  : R0 = ln(x) en Q8.7, o x8000 (-256.0, "menos infinito") si
;             x <= 0
;   Conserva: R1-R7
;   Arreglos: el original no terminaba con x = 0, daba valores sin sentido
;   con x < 0, y 6 raices de la tabla (i = 22, 56, 91, 99, 107 y 118)
;   estaban a una unidad del redondeo.
;
; El mismo metodo que el original:
;   1. x = xn * 2^k, con xn en 128..255 (1 <= m < 2)
;   2. Borchardt: a = (xn + 128) / 2, b = raiz(xn), y 4 veces
;      a = (a + b) / 2, b = raiz((a * b + 64) / 128); al final M = (a + b) / 2
;   3. ln(m) = ((xn - 128) * 128 + M / 2) / M;  ln(x) = ln(m) + k * 89
; Las raices salen de la misma tabla de 128 entradas, ahora de un byte.
;=============================================================================

LN_GENERAL_Q8_7
        PUSH  R1, R2, R3, R4, R5, R7
        ADD   R0, R0, #0
        BRnz  NO_DEF            ; x <= 0
        CLZ   R1, R0
        LSHF  R0, R0, R1
        RSHFL R0, R0, #8        ; R0 = xn
        SUB   R1, R1, #8        ; R1 = -k
        MOVI  R2, #-89          ; ln(2) = 89 en Q8.7
        MUL   R2, R1, R2
        PUSH  R2                ; k * ln(2), para el final
        MOVI  R7, #-128
        ADD   R0, R0, R7        ; R0 = xn - 128
        RSHFL R1, R0, #1
        SUB   R1, R1, R7        ; R1 = a = (xn + 128) / 2
        LSHF  R7, R0, #7        ; R7 = (xn - 128) * 128
        LEA   R3, TABLA
        LD    R5, CTE
        MOVI  R4, #5            ; 5 raices
        BR    RAIZ

;---- 4 vueltas de Borchardt (la primera raiz es la de xn) ----
CICLO   MUL   R0, R1, R2        ; a * b
        ADD   R0, R0, R5        ; + 64 - 128 * 128
        RSHFA R0, R0, #7        ; R0 = v - 128, v = (a * b + 64) / 128
RAIZ    CMP   R0, #127
        BRNC  LEE               ; 0..126: en la tabla
        RSHFA R0, R0, #7
        ADD   R0, R0, #1
        BRz   LEE               ; v < 128: raiz = 128 (entrada 0)
        MOVI  R0, #127          ; v > 254: raiz = 181 (entrada 127)
LEE     ADD   R0, R0, R3
        LDBI  R2, R0            ; R2 = b = raiz(v) (128..181, sin signo)
        ADD   R1, R1, R2
        RSHFL R1, R1, #1        ; a = (a + b) / 2
        LOOP  R4, CICLO         ; tras la quinta raiz, R1 = M

;---- ln(x) = ((xn - 128) * 128 + M / 2) / M + k * ln(2) ----
        RSHFL R0, R1, #1
        ADD   R0, R0, R7
        DIVM  R2, R0, R1
        POP   R2
        ADD   R0, R0, R2
        POPR  R1, R2, R3, R4, R5, R7

;---- x <= 0: ln no esta definido ----
NO_DEF  MOVI  R0, #-128
        LSHF  R0, R0, #8        ; x8000
        POPR  R1, R2, R3, R4, R5, R7

CTE     .FILL xC040             ; 64 - 128 * 128

; ---- raiz(1 + i/128) en Q8.7, i = 0..127: un byte por entrada ----
TABLA
        .FILL x8080         ; 128, 128
        .FILL x8181         ; 129, 129
        .FILL x8282         ; 130, 130
        .FILL x8383         ; 131, 131
        .FILL x8484         ; 132, 132
        .FILL x8585         ; 133, 133
        .FILL x8686         ; 134, 134
        .FILL x8787         ; 135, 135
        .FILL x8888         ; 136, 136
        .FILL x8989         ; 137, 137
        .FILL x8A8A         ; 138, 138
        .FILL x8B8B         ; 139, 139
        .FILL x8C8B         ; 139, 140
        .FILL x8D8C         ; 140, 141
        .FILL x8E8D         ; 141, 142
        .FILL x8F8E         ; 142, 143
        .FILL x908F         ; 143, 144
        .FILL x9090         ; 144, 144
        .FILL x9191         ; 145, 145
        .FILL x9292         ; 146, 146
        .FILL x9393         ; 147, 147
        .FILL x9494         ; 148, 148
        .FILL x9594         ; 148, 149
        .FILL x9695         ; 149, 150
        .FILL x9796         ; 150, 151
        .FILL x9797         ; 151, 151
        .FILL x9898         ; 152, 152
        .FILL x9999         ; 153, 153
        .FILL x9A99         ; 153, 154
        .FILL x9B9A         ; 154, 155
        .FILL x9C9B         ; 155, 156
        .FILL x9C9C         ; 156, 156
        .FILL x9D9D         ; 157, 157
        .FILL x9E9E         ; 158, 158
        .FILL x9F9E         ; 158, 159
        .FILL xA09F         ; 159, 160
        .FILL xA0A0         ; 160, 160
        .FILL xA1A1         ; 161, 161
        .FILL xA2A2         ; 162, 162
        .FILL xA3A2         ; 162, 163
        .FILL xA4A3         ; 163, 164
        .FILL xA4A4         ; 164, 164
        .FILL xA5A5         ; 165, 165
        .FILL xA6A6         ; 166, 166
        .FILL xA7A6         ; 166, 167
        .FILL xA7A7         ; 167, 167
        .FILL xA8A8         ; 168, 168
        .FILL xA9A9         ; 169, 169
        .FILL xAAA9         ; 169, 170
        .FILL xAAAA         ; 170, 170
        .FILL xABAB         ; 171, 171
        .FILL xACAC         ; 172, 172
        .FILL xADAC         ; 172, 173
        .FILL xADAD         ; 173, 173
        .FILL xAEAE         ; 174, 174
        .FILL xAFAF         ; 175, 175
        .FILL xB0AF         ; 175, 176
        .FILL xB0B0         ; 176, 176
        .FILL xB1B1         ; 177, 177
        .FILL xB2B1         ; 177, 178
        .FILL xB3B2         ; 178, 179
        .FILL xB3B3         ; 179, 179
        .FILL xB4B4         ; 180, 180
        .FILL xB5B4         ; 180, 181

        .END
