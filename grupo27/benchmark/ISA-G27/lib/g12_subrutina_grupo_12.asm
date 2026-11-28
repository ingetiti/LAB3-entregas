;=====================================================================
; SUBRUTINA: DIV_NEWTON (División Q7.8 por Newton-Raphson para ISA-G27)
;
;   Entradas:
;     R0 = Dividendo (Q7.8 con signo)
;     R1 = Divisor   (Q7.8 con signo)
;   Salida:
;     R0 = Cociente (Q7.8 con signo)
;          R0 = xFFFF si el divisor es 0
;   Conserva: R1-R5, R6 (intacto) y R7.
;=====================================================================
DIV_NEWTON:
        ; --- 1. GUARDADO DE ESTADO (sin tocar R6) ---
        ST      R1, G_R1
        ST      R2, G_R2
        ST      R3, G_R3
        ST      R4, G_R4
        ST      R5, G_R5
        ST      R7, G_R7

        ; --- 2. LOGICA DE SIGNOS Y MAGNITUDES ---
        ; Validar divisor == 0
        ADD     R1, R1, #0
        BRz     ERROR_DIV0

        ; Signo resultante en bit 15 de R2 (R2 < 0 si signos distintos)
        XOR     R2, R0, R1
        ST      R2, FLAG_SIGNO

        ; Magnitud del dividendo |R0| -> VAR_DIVIDENDO
        ADD     R0, R0, #0
        BRzp    DIV_A_POS
        NOT     R0, R0
        ADD     R0, R0, #1
DIV_A_POS:
        ST      R0, VAR_DIVIDENDO

        ; Magnitud del divisor |R1| -> R2
        ADD     R2, R1, #0
        BRzp    DIV_B_POS
        NOT     R2, R2
        ADD     R2, R2, #1
DIV_B_POS:

        ; --- 3. REDUCCION DE RANGO ---
        ; Contar desplazamientos a la izquierda hasta que bit 15 de R5 sea 1
        AND     R3, R3, #0          ; R3 = s
        ADD     R5, R2, #0
FIND_S_LOOP:
        ADD     R5, R5, #0
        BRn     FIND_S_DONE
        ADD     R5, R5, R5
        ADD     R3, R3, #1
        BR      FIND_S_LOOP
FIND_S_DONE:
        ST      R3, SAVED_S

        ; Normalizar divisor R2 a Q3.12 en [1.0, 2.0) desplazando (4 - s) bits:
        ; Si (4 - s) > 0 -> izquierda; si (4 - s) < 0 -> derecha
        AND     R4, R4, #0
        ADD     R4, R3, #-4         ; R4 = s - 4 (en [-4, +11])
        SHR     R2, R2, R4          ; R2 = divisor normalizado en Q3.12 (x1000..x1FFF)

        ; Obtener índice [0..7] de TABLA_LUT: (R2 >> 8) & x0007
        RSH     R5, R2, #8
        AND     R3, R5, #7          ; R3 = índice 0..7 (imm4 #7 es válido)
        ADD     R3, R3, R3          ; Multiplicar por 2 (2 bytes por palabra en ISA-G27)
        LEA     R4, TABLA_LUT
        ADD     R4, R4, R3
        LDR     R5, R4, #0          ; R5 = estimación inicial x_0 en Q3.12

        ; --- 4. NEWTON-RAPHSON (2 iteraciones: x_{n+1} = x_n * (2 - d * x_n)) ---
        ; Iteración 1:
        ;   R3 = (d * x_0) >> 12
        MUL     R0, R2, R5          ; Bits bajos [15:0]
        MULH    R1, R2, R5          ; Bits altos [31:16]
        LSH     R1, R1, #4
        RSH     R0, R0, #12
        OR      R3, R1, R0          ; R3 = d * x_0 en Q3.12

        ;   R7 = 2.0 (x2000) - d * x_0
        LD      R7, DOS_Q312
        NOT     R3, R3
        ADD     R3, R3, #1
        ADD     R7, R7, R3

        ;   x_1 = (x_0 * R7) >> 12 -> R5
        MUL     R0, R5, R7
        MULH    R1, R5, R7
        LSH     R1, R1, #4
        RSH     R0, R0, #12
        OR      R5, R1, R0          ; R5 = x_1 en Q3.12

        ; Iteración 2:
        ;   R3 = (d * x_1) >> 12
        MUL     R0, R2, R5
        MULH    R1, R2, R5
        LSH     R1, R1, #4
        RSH     R0, R0, #12
        OR      R3, R1, R0          ; R3 = d * x_1 en Q3.12

        ;   R7 = 2.0 (x2000) - d * x_1
        LD      R7, DOS_Q312
        NOT     R3, R3
        ADD     R3, R3, #1
        ADD     R7, R7, R3

        ;   x_2 = (x_1 * R7) >> 12 -> R5
        MUL     R0, R5, R7
        MULH    R1, R5, R7
        LSH     R1, R1, #4
        RSH     R0, R0, #12
        OR      R5, R1, R0          ; R5 = x_2 (1 / d_norm) en Q3.12

        ; Multiplicación final: cociente_norm = (|dividendo| * x_2) >> 12
        LD      R0, VAR_DIVIDENDO
        MUL     R3, R0, R5
        MULH    R1, R0, R5
        LSH     R1, R1, #4
        RSH     R3, R3, #12
        OR      R2, R1, R3          ; R2 = cociente antes de desnormalizar

        ; --- 5. DESNORMALIZACION ---
        ; Desplazar R2 por (s - 8) bits:
        ; Si (s - 8) > 0 -> izquierda; si (s - 8) < 0 -> derecha
        LD      R3, SAVED_S
        ADD     R4, R3, #-8         ; R4 = s - 8 (en [-8, +7])
        SHR     R2, R2, R4          ; Desplazamiento directo en 1 instrucción

        ; --- 6. RESTAURACION DE SIGNO ---
        LD      R0, FLAG_SIGNO
        BRzp    FIN_EXITOSO
        NOT     R2, R2
        ADD     R2, R2, #1          ; Negar resultado si signos eran distintos

FIN_EXITOSO:
        ADD     R0, R2, #0          ; Devolver resultado en R0
        BR      RESTAURAR_ESTADO

ERROR_DIV0:
        LD      R0, FLAG_ERR        ; Devolver xFFFF por división entre cero

RESTAURAR_ESTADO:
        LD      R1, G_R1
        LD      R2, G_R2
        LD      R3, G_R3
        LD      R4, G_R4
        LD      R5, G_R5
        LD      R7, G_R7
        RET

; --- ZONA DE DATOS ---
FLAG_SIGNO:         .BLKW #1
VAR_DIVIDENDO:      .BLKW #1
SAVED_S:            .BLKW #1
DOS_Q312:           .FILL x2000
FLAG_ERR:           .FILL xFFFF

TABLA_LUT:          .FILL x1E1E
                    .FILL x1AF2
                    .FILL x1861
                    .FILL x1642
                    .FILL x147A
                    .FILL x12F6
                    .FILL x11A7
                    .FILL x1084

; Espacio para Guardado Principal
G_R1:               .BLKW #1
G_R2:               .BLKW #1
G_R3:               .BLKW #1
G_R4:               .BLKW #1
G_R5:               .BLKW #1
G_R7:               .BLKW #1

.END