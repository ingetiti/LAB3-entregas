;=====================================================================
; SUBRUTINA: Mul_Sucesiva_POW (Potencia A^B en Q7.8 para ISA-G27)
;
;   Formatos: A en Q7.8 con signo / B entero con signo / R0 en Q7.8
;   Entradas:
;     R0 = A (base en Q7.8)
;     R1 = B (exponente entero con signo)
;   Salida:
;     R0 = A^B (Q7.8, truncado hacia cero)
;     R0 = x8000 si hubo error:
;          - B < 0 : exponente negativo no soportado
;          - B = 0 y A = 0 : indeterminación 0^0
;          - B > 0 : overflow (el resultado excede el rango Q7.8 [-127.996, +127.996])
;   Conserva: R1-R5, R6 (intacto) y R7.
;=====================================================================
Mul_Sucesiva_POW:
        ST      R1, P_SAVE_R1
        ST      R2, P_SAVE_R2
        ST      R3, P_SAVE_R3
        ST      R4, P_SAVE_R4
        ST      R7, P_SAVE_R7

        ADD     R3, R1, #0          ; R3 = B (contador de multiplicaciones)
        ADD     R1, R0, #0          ; R1 = A (constante a multiplicar)

        ; --- Casos especiales de B ---
        ADD     R3, R3, #0
        BRn     POT_ERR             ; B < 0 -> error
        BRp     POT_POS

        ; B == 0:
        ADD     R0, R0, #0
        BRz     POT_ERR             ; 0^0 -> error
        LD      R0, POT_UNO         ; A^0 = 1.00 (x0100)
        BR      POT_FIN

POT_POS:
        ADD     R0, R0, #0
        BRz     POT_FIN             ; 0^B = 0 (con B > 0)
        LD      R2, POT_ERRQ        ; Verificar que A != x8000 (desborde en signo)
        ADD     R4, R0, R2
        BRz     POT_ERR
        ADD     R3, R3, #-1         ; B - 1 multiplicaciones restantes
        BRz     POT_FIN             ; Si B == 1 -> resultado es A

POT_BUC:
        JSR     MULT_Q7_8           ; R0 = R0 * R1 (en Q7.8)
        LD      R2, POT_ERRQ
        ADD     R4, R0, R2          ; Comprobar si MULT_Q7_8 devolvió x8000
        BRz     POT_FIN             ; Si hubo overflow, cortar y devolver x8000
        ADD     R3, R3, #-1
        BRp     POT_BUC
        BR      POT_FIN

POT_ERR:
        LD      R0, POT_ERRQ        ; Cargar código de error x8000

POT_FIN:
        LD      R1, P_SAVE_R1
        LD      R2, P_SAVE_R2
        LD      R3, P_SAVE_R3
        LD      R4, P_SAVE_R4
        LD      R7, P_SAVE_R7
        RET

;=====================================================================
; SUBRUTINA AUXILIAR: MULT_Q7_8 (Multiplicación Q7.8 por hardware)
;
;   Entradas: R0 = A (Q7.8), R1 = B (Q7.8)
;   Salida:   R0 = (A * B) >> 8 en Q7.8 (truncado hacia cero)
;             R0 = x8000 si hay desborde fuera de [-x7FFF, +x7FFF]
;   Conserva: R1-R5, R6 (intacto) y R7.
;=====================================================================
MULT_Q7_8:
        ST      R1, M_SAVE_R1
        ST      R2, M_SAVE_R2
        ST      R3, M_SAVE_R3
        ST      R4, M_SAVE_R4

        ; 1. Determinar signo resultante en R4 (bit 15 = 1 si signos distintos)
        XOR     R4, R0, R1

        ; 2. Convertir A (R0) y B (R1) a magnitud (16 bits sin signo)
        ADD     R0, R0, #0
        BRzp    M_A_POS
        NOT     R0, R0
        ADD     R0, R0, #1
        BRn     M_DESB              ; x8000 no es representable en magnitud Q7.8
M_A_POS:
        ADD     R1, R1, #0
        BRzp    M_B_POS
        NOT     R1, R1
        ADD     R1, R1, #1
        BRn     M_DESB              ; x8000 no es representable en magnitud Q7.8
M_B_POS:

        ; 3. Producto de 32 bits sin signo en hardware: R3:R2 = |A| * |B|
        ;    En Q7.8 * Q7.8 = Q14.16; debemos extraer los bits [23:8]
        MUL     R2, R0, R1          ; R2 = 16 bits bajos del producto [15:0]
        MULH    R3, R0, R1          ; R3 = 16 bits altos del producto [31:16]

        ; 4. Verificar desborde en Q7.8:
        ;    La magnitud máxima válida es x7FFF (R3 debe ser <= x007F)
        RSH     R0, R3, #7          ; R0 = R3 >> 7 (debe ser 0 si R3 <= x007F)
        BRnp    M_DESB              ; Si R3 >= x0080, la magnitud >= x8000 -> overflow

        ; 5. Reensamblar el resultado Q7.8 = (R3 << 8) | (R2 >> 8)
        LSH     R3, R3, #8          ; Coloca bits [23:16] en [15:8]
        RSH     R2, R2, #8          ; Coloca bits [15:8] en [7:0]
        OR      R0, R3, R2          ; R0 = magnitud final en Q7.8

        ; 6. Aplicar signo al resultado si R4 < 0
        ADD     R4, R4, #0
        BRzp    M_FIN
        NOT     R0, R0
        ADD     R0, R0, #1

M_FIN:
        LD      R1, M_SAVE_R1
        LD      R2, M_SAVE_R2
        LD      R3, M_SAVE_R3
        LD      R4, M_SAVE_R4
        RET

M_DESB:
        LD      R0, POT_ERRQ        ; Devolver x8000 en caso de desborde
        BR      M_FIN

;--- Constantes y respaldo de registros ---
POT_UNO:    .FILL x0100             ; 1.00 en Q7.8
POT_ERRQ:   .FILL x8000             ; Código de error / overflow

P_SAVE_R1:  .FILL #0
P_SAVE_R2:  .FILL #0
P_SAVE_R3:  .FILL #0
P_SAVE_R4:  .FILL #0
P_SAVE_R7:  .FILL #0

M_SAVE_R1:  .FILL #0
M_SAVE_R2:  .FILL #0
M_SAVE_R3:  .FILL #0
M_SAVE_R4:  .FILL #0

.END