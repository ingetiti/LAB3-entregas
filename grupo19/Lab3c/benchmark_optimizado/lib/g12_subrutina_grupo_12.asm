; ============================================================================
; Modulo: division Newton-Raphson (archivo g12_subrutina_grupo_12.asm)
; Division por aproximacion inicial LUT + 2 iteraciones de Newton-Raphson (Q3.12).
; Adaptado y optimizado para la nueva ISA de 16 bits byte-addressable:
;   - Pila hardware (PUSHM/POPM/POPR) en lugar de variables estaticas.
;   - Desplazamientos directos (SRLV, SHLV, LSR, SHL, RLC) sin bucles.
;   - Tabla TABLA_LUT indexada por bytes (indice * 2 con SHL).
;   - NEG/SUB/OR/MOVI/LI para reducir instrucciones.
; ============================================================================

DIV_NEWTON
    ; --- 1. GUARDADO DE ESTADO ---
    PUSHM {R1, R2, R3, R4, R5, R7}

    ; --- 2. LOGICA DE SIGNOS (Entradas: R0=Dividendo, R1=Divisor) ---
    CLR   R2                  ; R2 = contador temporal de signos
    MOV   R3, R0              ; Evaluamos el Dividendo (R0)
    BRzp  CHK_DIVISOR
    NEG   R3, R3              ; |Dividendo|
    INC   R2

CHK_DIVISOR
    MOV   R4, R1              ; Evaluamos el Divisor (R1)
    BRzp  SIGN_DONE
    NEG   R4, R4              ; |Divisor|
    INC   R2

SIGN_DONE
    ANDI  R2, R2, #1          ; 1 si el resultado final sera negativo
    ST    R2, FLAG_SIGNO
    ST    R3, VAR_DIVIDENDO   ; Guardamos |Dividendo|
    MOV   R2, R4              ; R2 = |Divisor|

    ; --- 3. REDUCCION DE RANGO ---
    ADDI  R2, R2, #0
    BRz   ERROR_DIV0

    CLR   R3
    MOV   R5, R2
FIND_S_LOOP
    ADDI  R5, R5, #0
    BRn   FIND_S_DONE
    SHL   R5, R5, #1
    INC   R3
    BR    FIND_S_LOOP
FIND_S_DONE
    ST    R3, SAVED_S

    ADDI  R4, R3, #-4
    BRz   NORM_DONE
    BRp   NORM_LEFT
    NEG   R4, R4              ; R4 = 4 - s (en 1..4)
    SRLV  R2, R2, R4          ; Normalizacion logica a la derecha en 1 instruccion
    BR    NORM_DONE
NORM_LEFT
    SHLV  R2, R2, R4          ; Normalizacion a la izquierda en 1 instruccion
NORM_DONE

    ; Indice LUT = (R2 >> 8) & 7, escalado * 2 por direccionamiento de palabras
    LSR   R3, R2, #8
    ANDI  R3, R3, #7
    SHL   R3, R3, #1          ; offset en bytes (2 bytes por palabra)
    LEA   R4, TABLA_LUT
    ADD   R4, R4, R3
    LDW   R5, R4, #0          ; R5 = X0 (estimacion inicial en Q3.12)

    ; --- 4. NEWTON-RAPHSON (2 iteraciones: X = X * (2 - D * X)) ---
    LI    R3, x2000           ; 2.0 en Q3.12 (MULT_MODULO preserva R3)

    ; Iteracion 1
    MOV   R0, R2
    MOV   R1, R5
    JSR   MULT_MODULO         ; R0 = D * X0
    SUB   R1, R3, R0          ; R1 = 2 - D * X0
    MOV   R0, R5
    JSR   MULT_MODULO         ; R0 = X0 * (2 - D * X0)
    MOV   R5, R0              ; R5 = X1

    ; Iteracion 2
    MOV   R0, R2
    MOV   R1, R5
    JSR   MULT_MODULO         ; R0 = D * X1
    SUB   R1, R3, R0          ; R1 = 2 - D * X1
    MOV   R0, R5
    JSR   MULT_MODULO         ; R0 = X1 * (2 - D * X1)
    MOV   R5, R0              ; R5 = X2

    ; Multiplicacion Final: |Dividendo| * X2
    LD    R0, VAR_DIVIDENDO
    MOV   R1, R5
    JSR   MULT_MODULO         ; R0 = resultado antes de desnormalizar
    MOV   R2, R0

    ; --- 5. DESNORMALIZACION ---
    LD    R3, SAVED_S
    ADDI  R4, R3, #-8
    BRz   DENORM_DONE
    BRp   DENORM_LEFT
    NEG   R4, R4              ; R4 = 8 - s (en 1..8)
    SRLV  R2, R2, R4
    BR    DENORM_DONE
DENORM_LEFT
    SHLV  R2, R2, R4
DENORM_DONE

    ; --- 6. RESTAURACION DE SIGNO ---
    LD    R0, FLAG_SIGNO
    BRz   FIN_EXITOSO
    NEG   R2, R2              ; Volvemos el resultado negativo si correspondia

FIN_EXITOSO
    MOV   R0, R2              ; Resultado final en R0
    BR    RESTAURAR_ESTADO

ERROR_DIV0
    MOVI  R0, #-1             ; xFFFF: bandera de error en R0

RESTAURAR_ESTADO
    POPR  {R1, R2, R3, R4, R5, R7}

; --- SUBRUTINA: MULTIPLICACION MODULAR 32 BITS (Q3.12 x Q3.12 -> Q3.12) ---
; Entradas: R0, R1. Salida: R0 = ((R0 * R1) >> 12) & xFFFF. Preserva R2..R5.
MULT_MODULO
    PUSHM {R2, R3, R4, R5}
    CLR   R4                  ; Acumulador alto
    CLR   R5                  ; Acumulador bajo
    MOV   R2, R1              ; Multiplicador
    MOVI  R3, #16
LOOP_MULT
    SHL   R5, R5, #1          ; (R4:R5) <<= 1
    RLC   R4, R4
    SHL   R2, R2, #1          ; Bit 15 del multiplicador pasa a C
    BRnc  OMITIR_SUMA
    ADD   R5, R5, R0          ; (R4:R5) += R0
    BRnc  OMITIR_SUMA
    INC   R4
OMITIR_SUMA
    DEC   R3
    BRp   LOOP_MULT

    ; Ajuste Q3.12: ((R4:R5) << 4) >> 16 = (R4 << 4) | (R5 >> 12)
    SHL   R4, R4, #4
    LSR   R5, R5, #12
    OR    R0, R4, R5

    POPM  {R2, R3, R4, R5}
    RET

; --- ZONA DE DATOS ---
FLAG_SIGNO          .BLKW #1
VAR_DIVIDENDO       .BLKW #1
SAVED_S             .BLKW #1

TABLA_LUT           .FILL x1E1E
                    .FILL x1AF2
                    .FILL x1861
                    .FILL x1642
                    .FILL x147A
                    .FILL x12F6
                    .FILL x11A7
                    .FILL x1084

                    .END
