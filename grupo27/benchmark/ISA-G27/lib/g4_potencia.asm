;=====================================================================
; SUBRUTINA: EXP_RAPIDA (Exponenciación binaria entera para ISA-G27)
;
; ENTRADAS:
;   R0 = Base (entero con signo de 16 bits)
;   R1 = Exponente (entero >= 0)
;
; SALIDA:
;   R0 = Base ^ Exponente (entero con signo de 16 bits)
;
; Conserva R1-R5 y R7. Usa MUL en el esquema de exponenciación binaria.
;=====================================================================
EXP_RAPIDA:
        ST      R1, E_SAVE_R1
        ST      R2, E_SAVE_R2
        ST      R3, E_SAVE_R3
        ST      R4, E_SAVE_R4
        ST      R5, E_SAVE_R5

        ; R2 = Base de trabajo
        ; R3 = Exponente de trabajo
        ; R4 = Acumulador del resultado = 1
        ADD     R2, R0, #0
        ADD     R3, R1, #0
        AND     R4, R4, #0
        ADD     R4, R4, #1

        ; Calcular signo final en R5:
        ; Solo será negativo (bit 15 = 1) si Base < 0 Y Exponente es impar.
        AND     R5, R5, #0
        ADD     R2, R2, #0
        BRzp    E_SIGN_READY
        NOT     R2, R2              ; R2 = |Base|
        ADD     R2, R2, #1
        AND     R0, R3, #1          ; Verificar si el exponente original es impar
        BRz     E_SIGN_READY
        ADD     R5, R5, #-1         ; R5 = 0xFFFF (negativo) para marcar signo final

E_SIGN_READY:
        ST      R5, E_SIGN

        ; ============================================================
        ; BUCLE PRINCIPAL DE EXPONENCIACIÓN BINARIA
        ; ============================================================
E_LOOP:
        ADD     R3, R3, #0
        BRnz    E_FIN               ; Si exponente <= 0, terminar

        ; 1. Si el bit menos significativo del exponente es 1: R4 = R4 * R2
        AND     R0, R3, #1
        BRz     E_DIV2

        MUL     R4, R4, R2          ; R4 = R4 * R2 (se conserva la palabra baja)

        ; 2. Dividir exponente entre 2 en 1 sola instrucción (R3 >>= 1)
E_DIV2:
        RSH     R3, R3, #1
        BRz     E_FIN               ; Si R3 == 0, no hace falta elevar R2 al cuadrado

        ; 3. Elevar la base al cuadrado para la siguiente iteración binaria.
        MUL     R2, R2, R2

        BR      E_LOOP

        ; ============================================================
        ; APLICAR SIGNO FINAL Y RESTAURAR REGISTROS
        ; ============================================================
E_FIN:
        ADD     R0, R4, #0          ; R0 = |Base ^ Exponente|
        LD      R5, E_SIGN
        ADD     R5, R5, #0          ; Recuperar el indicador de signo
        BRzp    E_RESTORE
        NOT     R0, R0              ; Complemento a 2 si resultado debe ser negativo
        ADD     R0, R0, #1

E_RESTORE:
        LD      R1, E_SAVE_R1
        LD      R2, E_SAVE_R2
        LD      R3, E_SAVE_R3
        LD      R4, E_SAVE_R4
        LD      R5, E_SAVE_R5
        RET

;--- Zona de datos ---
E_SAVE_R1:  .FILL #0
E_SAVE_R2:  .FILL #0
E_SAVE_R3:  .FILL #0
E_SAVE_R4:  .FILL #0
E_SAVE_R5:  .FILL #0
E_SIGN:     .FILL #0

.END