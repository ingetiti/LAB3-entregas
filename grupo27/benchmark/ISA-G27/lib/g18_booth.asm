;=====================================================================
; SUBRUTINA: MULT_BOOTH (Multiplicador Booth 16x16 en Q7.8 para ISA-G27)
;
;   Entradas:
;     R0 = X, primer operando  (Q7.8, 16 bits con signo)
;     R1 = Y, segundo operando (Q7.8, 16 bits con signo)
;   Salida:
;     R0 = RES = P[23:8]       (producto reducido a Q7.8)
;   Diagnóstico (en memoria):
;     PH   = palabra alta del producto de 32 bits (Q15.16)
;     PL   = palabra baja del producto de 32 bits
;     RES  = copia de P[23:8]
;     OVFV = 0 sin desbordamiento, 1 si PH fuera de [-128, 127]
;   Conserva: R1-R5, R6 (intacto) y R7.
;   CC refleja el signo de RES al retornar.
;=====================================================================
MULT_BOOTH:
        ST      R1, MB_SAVE_R1
        ST      R2, MB_SAVE_R2
        ST      R3, MB_SAVE_R3
        ST      R4, MB_SAVE_R4
        ST      R5, MB_SAVE_R5
        ST      R7, MB_SAVE_R7

        ; Inicialización de variables de Booth:
        ;   R4 = A = 0 (acumulador alto)
        ;   R5 = Q = Y (multiplicador)
        ;   R3 = QM1 = 0 (bit Q[-1])
        ;   R7 = -16 (contador de 16 iteraciones)
        ST      R0, MCAND           ; M <- X
        NOT     R2, R0
        ADD     R2, R2, #1
        ST      R2, MNEG            ; -M <- -X

        ADD     R5, R1, #0          ; Q <- Y
        AND     R4, R4, #0          ; A <- 0
        AND     R3, R3, #0          ; QM1 <- 0
        AND     R7, R7, #0
        ADD     R7, R7, #-8
        ADD     R7, R7, #-8         ; R7 = -16

        ; --- Bucle de Booth (16 iteraciones) ---
BOOTH_LOOP:
        AND     R0, R5, #1          ; R0 = q0 = Q[0]
        NOT     R1, R0
        ADD     R1, R1, #1          ; R1 = -q0
        ADD     R1, R3, R1          ; R1 = QM1 - q0 (d in {-1, 0, +1})
        ADD     R3, R0, #0          ; Actualizar QM1 <- q0 para la próxima vuelta

        ADD     R1, R1, #0
        BRz     BOOTH_SHIFT         ; d == 0 -> solo desplazar
        BRn     BOOTH_SUB           ; d == -1 -> A <- A - M

        ; d == +1 -> A <- A + M
        LD      R1, MCAND
        ADD     R4, R4, R1
        BR      BOOTH_SHIFT

BOOTH_SUB:
        ; d == -1 -> A <- A - M
        LD      R1, MNEG
        ADD     R4, R4, R1

BOOTH_SHIFT:
        ; Desplazamiento aritmético a la derecha de 1 bit del par (A:Q) = (R4:R5):
        ; 1. RSHO obtiene el bit 0 saliente de R4 ya colocado en bit 15 de R2
        RSHO    R2, R4, #1
        ; 2. Desplazar Q (R5) a la derecha 1 bit e insertar el bit saliente de A
        RSH     R5, R5, #1
        OR      R5, R5, R2
        ; 3. Desplazar A (R4) aritméticamente a la derecha 1 bit (RSH + SEXT #15)
        RSH     R4, R4, #1
        SEXT    R4, R4, #15

        ADD     R7, R7, #1
        BRn     BOOTH_LOOP

        ; --- Guardar producto bruto de 32 bits PH:PL = A:Q ---
        ST      R4, PH
        ST      R5, PL

        ; --- Extraer RES = P[23:8] = (PH << 8) | (PL >> 8) ---
        LSH     R1, R4, #8
        RSH     R2, R5, #8
        OR      R0, R1, R2
        ST      R0, RES

        ; --- Calcular desbordamiento OVFV = ((PH + x0080) & xFF00) != 0 ---
        LD      R1, C0080
        ADD     R1, R4, R1          ; PH + 128
        LD      R2, CFF00
        AND     R1, R1, R2          ; Byte alto de (PH + 128)
        BRz     BOOTH_NO_OVF
        AND     R1, R1, #0
        ADD     R1, R1, #1          ; OVFV = 1
BOOTH_NO_OVF:
        ST      R1, OVFV

        ; --- Restaurar registros y retornar con RES en R0 ---
        LD      R1, MB_SAVE_R1
        LD      R2, MB_SAVE_R2
        LD      R3, MB_SAVE_R3
        LD      R4, MB_SAVE_R4
        LD      R5, MB_SAVE_R5
        LD      R7, MB_SAVE_R7
        LD      R0, RES             ; R0 = RES y actualiza CC
        RET

;=====================================================================
; ZONA DE DATOS Y CONSTANTES
;=====================================================================
PH:             .FILL x0000
PL:             .FILL x0000
RES:            .FILL x0000
OVFV:           .FILL x0000

MCAND:          .FILL x0000
MNEG:           .FILL x0000
C0080:          .FILL x0080
CFF00:          .FILL xFF00

MB_SAVE_R1:     .FILL x0000
MB_SAVE_R2:     .FILL x0000
MB_SAVE_R3:     .FILL x0000
MB_SAVE_R4:     .FILL x0000
MB_SAVE_R5:     .FILL x0000
MB_SAVE_R7:     .FILL x0000

.END