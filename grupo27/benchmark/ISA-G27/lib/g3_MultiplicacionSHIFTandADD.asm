;=====================================================================
; Multiplicación con signo por Shift & Add en punto fijo (ISA-G27)
;   Entradas:
;     R0 = multiplicando en Q7.8 (16 bits con signo)
;     R1 = multiplicador en Q7.8 (16 bits con signo)
;   Salida:
;     R0:R1 = producto en Q15.16 (32 bits con signo)
;       R0 = parte entera (palabra alta)
;       R1 = parte fraccionaria (palabra baja)
;   Conserva R2-R5 y R7. No utiliza MUL ni MULH.
;=====================================================================
MUL_Q7_8_SHIFT_ADD:
        ST      R2, M_SAVE_R2
        ST      R3, M_SAVE_R3
        ST      R4, M_SAVE_R4
        ST      R5, M_SAVE_R5

        ; 1. Calcular signo resultante en R5 (bit 15 de R0 XOR R1)
        XOR     R5, R0, R1

        ; 2. Obtener magnitud de R0 (|R0|)
        ADD     R0, R0, #0
        BRzp    M_R0_POS
        NOT     R0, R0
        ADD     R0, R0, #1
M_R0_POS:

        ; 3. Obtener magnitud de R1 (|R1|)
        ADD     R1, R1, #0
        BRzp    M_R1_POS
        NOT     R1, R1
        ADD     R1, R1, #1
M_R1_POS:

        ; 4. Preparar registros para el bucle de 16 iteraciones
        ;    R0:R1 = acumulador de 32 bits (R0 = alta, R1 = baja / multiplicador)
        ;    R2    = multiplicando (|R0| original)
        ;    R3    = contador de 16 bits
        ADD     R2, R0, #0          ; R2 = |multiplicando|
        AND     R0, R0, #0          ; R0 (palabra alta del producto) = 0
        AND     R3, R3, #0
        ADD     R3, R3, #7          ; Cargar 16 en R3 (imm4 máximo es 7)
        ADD     R3, R3, #7
        ADD     R3, R3, #2          ; R3 = 16

        ; 5. Bucle Shift-and-Add (16 pasos)
        ;    Se inspecciona el LSB de R1 (multiplicador). Si es 1, R0 += R2.
        ;    Luego se desplaza el par de 32 bits R0:R1 una posición a la derecha.
M_LOOP:
        AND     R4, R1, #1          ; Probar bit 0 del multiplicador
        BRz     M_SHIFT
        ADD     R0, R0, R2          ; Sumar multiplicando a la palabra alta

M_SHIFT:
        AND     R4, R0, #1          ; Guardar bit 0 de R0 (acarreo hacia bit 15 de R1)
        RSH     R0, R0, #1          ; Desplazar R0 lógico a la derecha (bit 15 <- 0)
        RSH     R1, R1, #1          ; Desplazar R1 lógico a la derecha
        ADD     R4, R4, #0
        BRz     M_NEXT
        ; Si el LSB de R0 era 1, encender el MSB (bit 15 = 0x8000) de R1
        AND     R4, R4, #0
        ADD     R4, R4, #1
        LSH     R4, R4, #15         ; R4 = 0x8000
        OR      R1, R1, R4          ; Insertar bit en R1[15]

M_NEXT:
        ADD     R3, R3, #-1
        BRp     M_LOOP

        ; 6. Aplicar signo al producto de 32 bits (R0:R1) si R5 < 0
        ADD     R5, R5, #0
        BRzp    M_RESTORE
        NOT     R1, R1              ; Complemento a 2 en 32 bits (R0:R1)
        NOT     R0, R0
        ADD     R1, R1, #1          ; Suma 1 a la palabra baja (modifica flag 'c')
        ADC     R0, R0, #0          ; Propaga el carry directo a la palabra alta

M_RESTORE:
        LD      R2, M_SAVE_R2
        LD      R3, M_SAVE_R3
        LD      R4, M_SAVE_R4
        LD      R5, M_SAVE_R5
        RET

;--- Zona de datos ---
M_SAVE_R2:  .FILL #0
M_SAVE_R3:  .FILL #0
M_SAVE_R4:  .FILL #0
M_SAVE_R5:  .FILL #0

.END