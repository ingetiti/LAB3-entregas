;=====================================================================
; SUBRUTINA: SQRT_NR (Raíz cuadrada Non-Restoring de Q7.8 a Q6.9)
;
;   Entrada:  R0 = radicando x en Q7.8 con signo (rango válido [0 ; 127.996])
;   Salida:   R0 = sqrt(x) en Q6.9, redondeada al más cercano
;                  R0 = x8000 si x < 0 (error: sin raíz real)
;   Conserva: R1-R7 (todos intactos, incluyendo R6).
;=====================================================================
SQRT_NR:
        ; Validar dominio: x < 0 -> devolver x8000 inmediatamente
        ADD     R0, R0, #0
        BRn     SQ_NEG

        ST      R1, SQ_SAVE_R1
        ST      R2, SQ_SAVE_R2
        ST      R3, SQ_SAVE_R3
        ST      R4, SQ_SAVE_R4

        ; Inicializar algoritmo Non-Restoring:
        ;   R1 = 13 (k = 13 iteraciones para obtener los 13 bits significativos en Q6.9)
        ;   R2 = 0  (R: resto parcial)
        ;   R3 = 0  (Q: raíz parcial)
        AND     R1, R1, #0
        ADD     R1, R1, #7
        ADD     R1, R1, #6          ; R1 = 13
        AND     R2, R2, #0          ; R = 0
        AND     R3, R3, #0          ; Q = 0

        ; --- Lazo Non-Restoring: 1 bit de raíz por iteración ---
SQ_LAZO:
        ; 1. Bajar 2 bits altos de R0 al resto R: R = (R << 2) | (R0 >> 14)
        LSHO    R4, R0, #2          ; Bits [15:14] salientes de R0 quedan en [1:0] de R4
        LSH     R0, R0, #2          ; Desplazar radicando 2 bits a la izquierda
        LSH     R2, R2, #2          ; R = 4R
        OR      R2, R2, R4          ; R = 4R + par de bits bajados

        ; 2. Paso Non-Restoring:
        ;    Si R >= 0 -> R = R - (4Q + 1)
        ;    Si R <  0 -> R = R + (4Q + 3)
        LSH     R4, R3, #2          ; R4 = 4Q
        ADD     R2, R2, #0
        BRn     SQ_SUMA

        ADD     R4, R4, #1          ; R4 = 4Q + 1
        NOT     R4, R4
        ADD     R4, R4, #1          ; R4 = -(4Q + 1)
        ADD     R2, R2, R4          ; R = R - (4Q + 1)
        BR      SQ_BIT

SQ_SUMA:
        ADD     R4, R4, #3          ; R4 = 4Q + 3
        ADD     R2, R2, R4          ; R = R + (4Q + 3)

        ; 3. Actualizar raíz parcial: Q = (Q << 1) + (R >= 0 ? 1 : 0)
SQ_BIT:
        ADD     R3, R3, R3          ; Q = 2Q
        ADD     R2, R2, #0
        BRn     SQ_SIG
        ADD     R3, R3, #1          ; Bit de raíz = 1 si R >= 0

SQ_SIG:
        ADD     R1, R1, #-1
        BRp     SQ_LAZO

        ; --- Corrección final del resto: si R < 0, R = R + 2Q + 1 ---
        ADD     R2, R2, #0
        BRzp    SQ_RED
        ADD     R4, R3, R3          ; 2Q
        ADD     R4, R4, #1          ; 2Q + 1
        ADD     R2, R2, R4          ; R = R + 2Q + 1

        ; --- Redondeo al más cercano: si R > Q, Q = Q + 1 ---
SQ_RED:
        NOT     R4, R3
        ADD     R4, R4, #1          ; -Q
        ADD     R4, R2, R4          ; R - Q
        BRnz    SQ_FIN
        ADD     R3, R3, #1          ; Redondear hacia arriba

SQ_FIN:
        ADD     R0, R3, #0          ; Resultado final en R0 (formato Q6.9)
        LD      R1, SQ_SAVE_R1
        LD      R2, SQ_SAVE_R2
        LD      R3, SQ_SAVE_R3
        LD      R4, SQ_SAVE_R4
        ADD     R0, R0, #0          ; Actualizar CC con resultado en R0
        RET

SQ_NEG:
        LD      R0, SQ_ERR          ; R0 = x8000 (código de error)
        RET

;=====================================================================
; ZONA DE DATOS Y CONSTANTES
;=====================================================================
SQ_ERR:         .FILL x8000
SQ_SAVE_R1:     .FILL #0
SQ_SAVE_R2:     .FILL #0
SQ_SAVE_R3:     .FILL #0
SQ_SAVE_R4:     .FILL #0

.END