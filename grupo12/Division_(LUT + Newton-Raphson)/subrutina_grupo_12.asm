DIV_NEWTON
    ; --- 1. GUARDADO DE ESTADO  ---
    ST R1, G_R1
    ST R2, G_R2
    ST R3, G_R3
    ST R4, G_R4
    ST R5, G_R5
    ST R7, G_R7

    ; --- 2. LOGICA DE SIGNOS (Entradas: R0=Dividendo, R1=Divisor) ---
    AND R2, R2, #0       ; R2 sera el contador temporal de signos
    
    ADD R3, R0, #0       ; Evaluamos el Dividendo (R0)
    BRzp CHK_DIVISOR
    NOT R3, R3
    ADD R3, R3, #1       ; Lo volvemos absoluto
    ADD R2, R2, #1       ; Contamos un negativo
    
CHK_DIVISOR
    ADD R4, R1, #0       ; Evaluamos el Divisor (R1)
    BRzp SIGN_DONE
    NOT R4, R4
    ADD R4, R4, #1       ; Lo volvemos absoluto
    ADD R2, R2, #1       ; Contamos un negativo
    
SIGN_DONE
    AND R2, R2, #1       ; Mascara para saber si el resultado final sera negativo
    ST R2, FLAG_SIGNO
    
    ST R3, VAR_DIVIDENDO ; Guardamos el Dividendo absoluto
    ADD R2, R4, #0       ; Movemos el Divisor absoluto a R2 para iniciar el algoritmo
    
    ; --- 3. REDUCCION DE RANGO ---
    ADD R2, R2, #0
    BRz ERROR_DIV0
    
    AND R3, R3, #0
    ADD R5, R2, #0
FIND_S_LOOP
    ADD R5, R5, #0
    BRn FIND_S_DONE
    ADD R5, R5, R5
    ADD R3, R3, #1
    BRnzp FIND_S_LOOP
FIND_S_DONE
    ST R3, SAVED_S
    
    ADD R4, R3, #-4
    BRz NORM_DONE
    BRp NORM_LEFT
    NOT R4, R4
    ADD R4, R4, #1
NORM_RIGHT_OUTER
    AND R0, R0, #0
    LD R1, CONST_15
    ADD R5, R2, #0
NORM_SR_LOOP
    ADD R0, R0, R0
    ADD R5, R5, #0
    BRzp NORM_SR_SKIP
    ADD R0, R0, #1
NORM_SR_SKIP
    ADD R5, R5, R5
    ADD R1, R1, #-1
    BRp NORM_SR_LOOP
    ADD R2, R0, #0
    ADD R4, R4, #-1
    BRp NORM_RIGHT_OUTER
    BRnzp NORM_DONE
NORM_LEFT
    ADD R2, R2, R2
    ADD R4, R4, #-1
    BRp NORM_LEFT
NORM_DONE
    
    ADD R5, R2, #0
    LD R4, CONST_8
IDX_RIGHT_OUTER
    AND R0, R0, #0
    LD R1, CONST_15
    ADD R7, R5, #0
IDX_SR_LOOP
    ADD R0, R0, R0
    ADD R7, R7, #0
    BRzp IDX_SR_SKIP
    ADD R0, R0, #1
IDX_SR_SKIP
    ADD R7, R7, R7
    ADD R1, R1, #-1
    BRp IDX_SR_LOOP
    ADD R5, R0, #0
    ADD R4, R4, #-1
    BRp IDX_RIGHT_OUTER
    
    LD R0, MASK_0007
    AND R3, R5, R0
    
    LEA R4, TABLA_LUT
    ADD R4, R4, R3
    LDR R5, R4, #0
    
    ; --- 4. NEWTON-RAPHSON ---
    ADD R0, R2, #0
    ADD R1, R5, #0
    JSR MULT_MODULO
    LD R3, RES_MULT
    LD R7, DOS_Q312
    NOT R3, R3
    ADD R3, R3, #1
    ADD R7, R7, R3
    ADD R0, R5, #0
    ADD R1, R7, #0
    JSR MULT_MODULO
    LD R5, RES_MULT
    
    ADD R0, R2, #0
    ADD R1, R5, #0
    JSR MULT_MODULO
    LD R3, RES_MULT
    LD R7, DOS_Q312
    NOT R3, R3
    ADD R3, R3, #1
    ADD R7, R7, R3
    ADD R0, R5, #0
    ADD R1, R7, #0
    JSR MULT_MODULO
    LD R5, RES_MULT
    
    ; Multiplicacion Final
    LD R0, VAR_DIVIDENDO
    ADD R1, R5, #0
    JSR MULT_MODULO
    LD R2, RES_MULT      ; R2 alojara temporalmente el resultado
    
    ; --- 5. DESNORMALIZACION ---
    LD R3, SAVED_S
    ADD R4, R3, #-8
    BRz DENORM_DONE
    BRp DENORM_LEFT
    NOT R4, R4
    ADD R4, R4, #1
DENORM_RIGHT_OUTER
    AND R0, R0, #0
    LD R1, CONST_15
    ADD R5, R2, #0
DENORM_SR_LOOP
    ADD R0, R0, R0
    ADD R5, R5, #0
    BRzp DENORM_SR_SKIP
    ADD R0, R0, #1
DENORM_SR_SKIP
    ADD R5, R5, R5
    ADD R1, R1, #-1
    BRp DENORM_SR_LOOP
    ADD R2, R0, #0
    ADD R4, R4, #-1
    BRp DENORM_RIGHT_OUTER
    BRnzp DENORM_DONE
DENORM_LEFT
    ADD R2, R2, R2
    ADD R4, R4, #-1
    BRp DENORM_LEFT
DENORM_DONE

    ; --- 6. RESTAURACION DE SIGNO ---
    LD R0, FLAG_SIGNO
    BRz FIN_EXITOSO
    NOT R2, R2
    ADD R2, R2, #1       ; Volvemos el resultado negativo si correspondia

FIN_EXITOSO
    ADD R0, R2, #0       ; Carga el resultado final en R0 (Salida)
    BRnzp RESTAURAR_ESTADO
    
ERROR_DIV0
    LD R0, FLAG_ERR      ; Carga bandera de error en R0
    
RESTAURAR_ESTADO
    LD R1, G_R1
    LD R2, G_R2
    LD R3, G_R3
    LD R4, G_R4
    LD R5, G_R5
    LD R7, G_R7
    RET

; --- SUBRUTINA: MULTIPLICACION MODULAR 32 BITS ---
MULT_MODULO
    ST R0, M_R0
    ST R1, M_R1
    ST R2, M_R2
    ST R3, M_R3
    ST R4, M_R4
    ST R5, M_R5
    ST R7, M_R7
    AND R4, R4, #0
    AND R5, R5, #0
    ADD R2, R1, #0
    LD R3, CONT_16
LOOP_MULT
    ADD R5, R5, #0
    BRzp SHIFT_ACC_NORM
    ADD R5, R5, R5
    ADD R4, R4, R4
    ADD R4, R4, #1
    BRnzp SHIFT_ACC_FIN
SHIFT_ACC_NORM
    ADD R5, R5, R5
    ADD R4, R4, R4
SHIFT_ACC_FIN
    ADD R2, R2, #0
    BRzp OMITIR_SUMA
    ADD R5, R5, #0
    BRzp SUMAR_NORM
    ADD R5, R5, R0
    BRn OMITIR_SUMA
    ADD R4, R4, #1
    BRnzp OMITIR_SUMA
SUMAR_NORM
    ADD R5, R5, R0
OMITIR_SUMA
    ADD R2, R2, R2
    ADD R3, R3, #-1
    BRp LOOP_MULT
    LD R3, CONT_4
AJUSTE_Q312
    ADD R5, R5, #0
    BRzp SHIFT_AJ_NORM
    ADD R5, R5, R5
    ADD R4, R4, R4
    ADD R4, R4, #1
    BRnzp SHIFT_AJ_FIN
SHIFT_AJ_NORM
    ADD R5, R5, R5
    ADD R4, R4, R4
SHIFT_AJ_FIN
    ADD R3, R3, #-1
    BRp AJUSTE_Q312
    
    ST R4, RES_MULT      
    
    LD R0, M_R0
    LD R1, M_R1
    LD R2, M_R2
    LD R3, M_R3
    LD R4, M_R4
    LD R5, M_R5
    LD R7, M_R7
    RET

; --- ZONA DE DATOS ---
FLAG_SIGNO          .BLKW #1
VAR_DIVIDENDO       .BLKW #1
SAVED_S             .BLKW #1
RES_MULT            .BLKW #1
CONST_15            .FILL #15
CONST_8             .FILL #8
MASK_0007           .FILL x0007
DOS_Q312            .FILL x2000
FLAG_ERR            .FILL xFFFF
CONT_16             .FILL #16
CONT_4              .FILL #4

TABLA_LUT           .FILL x1E1E
                    .FILL x1AF2
                    .FILL x1861
                    .FILL x1642
                    .FILL x147A
                    .FILL x12F6
                    .FILL x11A7
                    .FILL x1084

; Espacio para Guardado Principal
G_R1                .BLKW #1
G_R2                .BLKW #1
G_R3                .BLKW #1
G_R4                .BLKW #1
G_R5                .BLKW #1
G_R7                .BLKW #1

; Espacio para Guardado de MULT_MODULO
M_R0                .BLKW #1
M_R1                .BLKW #1
M_R2                .BLKW #1
M_R3                .BLKW #1
M_R4                .BLKW #1
M_R5                .BLKW #1
M_R7                .BLKW #1

.END