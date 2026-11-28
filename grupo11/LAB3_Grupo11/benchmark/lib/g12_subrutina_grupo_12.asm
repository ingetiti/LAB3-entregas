DIV_NEWTON:
    ; --- 1. GUARDADO DE ESTADO  ---
                                ST R1,G_R1
                                ST R2,G_R2
                                ST R3,G_R3
                                ST R4,G_R4
                                ST R5,G_R5
                                ST R7,G_R7

    ; --- 2. LOGICA DE SIGNOS (Entradas: R0=Dividendo, R1=Divisor) ---
                                MOVI R2,#0                   ; R2 sera el contador temporal de signos

                                MOV R3,R0                    ; Evaluamos el Dividendo (R0)
                                BRZP CHK_DIVISOR
                                NEG R3,R3                    ; Lo volvemos absoluto
                                ADD R2,R2,#1                 ; Contamos un negativo

CHK_DIVISOR:
                                MOV R4,R1                    ; Evaluamos el Divisor (R1)
                                BRZP SIGN_DONE
                                NEG R4,R4                    ; Lo volvemos absoluto
                                ADD R2,R2,#1                 ; Contamos un negativo

SIGN_DONE:
                                AND R2,R2,#1                 ; Mascara para saber si el resultado final sera negativo
                                ST R2,FLAG_SIGNO

                                ST R3,VAR_DIVIDENDO          ; Guardamos el Dividendo absoluto
                                MOV R2,R4                    ; Movemos el Divisor absoluto a R2 para iniciar el algoritmo

    ; --- 3. REDUCCION DE RANGO ---
                                ADD R2,R2,#0
                                BRZ ERROR_DIV0

                                MOVI R3,#0
                                MOV R5,R2
FIND_S_LOOP:
                                ADD R5,R5,#0
                                BRN FIND_S_DONE
                                ADD R5,R5,R5
                                ADD R3,R3,#1
                                BRNZP FIND_S_LOOP
FIND_S_DONE:
                                ST R3,SAVED_S

                                ADD R4,R3,#-4
                                BRZ NORM_DONE
                                BRP NORM_LEFT
                                NEG R4,R4
NORM_RIGHT_OUTER:
                                MOVI R0,#0
                                LD R1,CONST_15
                                MOV R5,R2
NORM_SR_LOOP:
                                ADD R0,R0,R0
                                ADD R5,R5,#0
                                BRZP NORM_SR_SKIP
                                ADD R0,R0,#1
NORM_SR_SKIP:
                                ADD R5,R5,R5
                                ADD R1,R1,#-1
                                BRP NORM_SR_LOOP
                                MOV R2,R0
                                ADD R4,R4,#-1
                                BRP NORM_RIGHT_OUTER
                                BRNZP NORM_DONE
NORM_LEFT:
                                ADD R2,R2,R2
                                ADD R4,R4,#-1
                                BRP NORM_LEFT
NORM_DONE:

                                MOV R5,R2
                                LD R4,CONST_8
IDX_RIGHT_OUTER:
                                MOVI R0,#0
                                LD R1,CONST_15
                                MOV R7,R5
IDX_SR_LOOP:
                                ADD R0,R0,R0
                                ADD R7,R7,#0
                                BRZP IDX_SR_SKIP
                                ADD R0,R0,#1
IDX_SR_SKIP:
                                ADD R7,R7,R7
                                ADD R1,R1,#-1
                                BRP IDX_SR_LOOP
                                MOV R5,R0
                                ADD R4,R4,#-1
                                BRP IDX_RIGHT_OUTER

                                LD R0,MASK_0007
                                AND R3,R5,R0

                                LEA R4,TABLA_LUT
                                ADD R4,R4,R3
                                ADD R4,R4,R3
                                LDW R5,R4,#0

    ; --- 4. NEWTON-RAPHSON ---
                                MOV R0,R2
                                MOV R1,R5
                                JSR MULT_MODULO
                                LD R3,RES_MULT
                                LD R7,DOS_Q312
                                NEG R3,R3
                                ADD R7,R7,R3
                                MOV R0,R5
                                MOV R1,R7
                                JSR MULT_MODULO
                                LD R5,RES_MULT

                                MOV R0,R2
                                MOV R1,R5
                                JSR MULT_MODULO
                                LD R3,RES_MULT
                                LD R7,DOS_Q312
                                NEG R3,R3
                                ADD R7,R7,R3
                                MOV R0,R5
                                MOV R1,R7
                                JSR MULT_MODULO
                                LD R5,RES_MULT

    ; Multiplicacion Final
                                LD R0,VAR_DIVIDENDO
                                MOV R1,R5
                                JSR MULT_MODULO
                                LD R2,RES_MULT               ; R2 alojara temporalmente el resultado

    ; --- 5. DESNORMALIZACION ---
                                LD R3,SAVED_S
                                ADD R4,R3,#-8
                                BRZ DENORM_DONE
                                BRP DENORM_LEFT
                                NEG R4,R4
DENORM_RIGHT_OUTER:
                                MOVI R0,#0
                                LD R1,CONST_15
                                MOV R5,R2
DENORM_SR_LOOP:
                                ADD R0,R0,R0
                                ADD R5,R5,#0
                                BRZP DENORM_SR_SKIP
                                ADD R0,R0,#1
DENORM_SR_SKIP:
                                ADD R5,R5,R5
                                ADD R1,R1,#-1
                                BRP DENORM_SR_LOOP
                                MOV R2,R0
                                ADD R4,R4,#-1
                                BRP DENORM_RIGHT_OUTER
                                BRNZP DENORM_DONE
DENORM_LEFT:
                                ADD R2,R2,R2
                                ADD R4,R4,#-1
                                BRP DENORM_LEFT
DENORM_DONE:

    ; --- 6. RESTAURACION DE SIGNO ---
                                LD R0,FLAG_SIGNO
                                BRZ FIN_EXITOSO
                                NEG R2,R2                    ; Volvemos el resultado negativo si correspondia

FIN_EXITOSO:
                                MOV R0,R2                    ; Carga el resultado final en R0 (Salida)
                                BRNZP RESTAURAR_ESTADO

ERROR_DIV0:
                                LD R0,FLAG_ERR               ; Carga bandera de error en R0

RESTAURAR_ESTADO:
                                LD R1,G_R1
                                LD R2,G_R2
                                LD R3,G_R3
                                LD R4,G_R4
                                LD R5,G_R5
                                LD R7,G_R7
                                RET

; --- SUBRUTINA: MULTIPLICACION MODULAR 32 BITS ---
MULT_MODULO:
                                ST R0,M_R0
                                ST R1,M_R1
                                ST R2,M_R2
                                ST R3,M_R3
                                ST R4,M_R4
                                ST R5,M_R5
                                ST R7,M_R7
                                MOVI R4,#0
                                MOVI R5,#0
                                MOV R2,R1
                                LD R3,CONT_16
LOOP_MULT:
                                ADD R5,R5,#0
                                BRZP SHIFT_ACC_NORM
                                ADD R5,R5,R5
                                ADD R4,R4,R4
                                ADD R4,R4,#1
                                BRNZP SHIFT_ACC_FIN
SHIFT_ACC_NORM:
                                ADD R5,R5,R5
                                ADD R4,R4,R4
SHIFT_ACC_FIN:
                                ADD R2,R2,#0
                                BRZP OMITIR_SUMA
                                ADD R5,R5,#0
                                BRZP SUMAR_NORM
                                ADD R5,R5,R0
                                BRN OMITIR_SUMA
                                ADD R4,R4,#1
                                BRNZP OMITIR_SUMA
SUMAR_NORM:
                                ADD R5,R5,R0
OMITIR_SUMA:
                                ADD R2,R2,R2
                                ADD R3,R3,#-1
                                BRP LOOP_MULT
                                LD R3,CONT_4
AJUSTE_Q312:
                                ADD R5,R5,#0
                                BRZP SHIFT_AJ_NORM
                                ADD R5,R5,R5
                                ADD R4,R4,R4
                                ADD R4,R4,#1
                                BRNZP SHIFT_AJ_FIN
SHIFT_AJ_NORM:
                                ADD R5,R5,R5
                                ADD R4,R4,R4
SHIFT_AJ_FIN:
                                ADD R3,R3,#-1
                                BRP AJUSTE_Q312

                                ST R4,RES_MULT

                                LD R0,M_R0
                                LD R1,M_R1
                                LD R2,M_R2
                                LD R3,M_R3
                                LD R4,M_R4
                                LD R5,M_R5
                                LD R7,M_R7
                                RET

; --- ZONA DE DATOS ---
FLAG_SIGNO:                     .BLKW #1
VAR_DIVIDENDO:                  .BLKW #1
SAVED_S:                        .BLKW #1
RES_MULT:                       .BLKW #1
CONST_15:                       .FILL #15
CONST_8:                        .FILL #8
MASK_0007:                      .FILL x0007
DOS_Q312:                       .FILL x2000
FLAG_ERR:                       .FILL xFFFF
CONT_16:                        .FILL #16
CONT_4:                         .FILL #4

TABLA_LUT:                      .FILL x1E1E
                                .FILL x1AF2
                                .FILL x1861
                                .FILL x1642
                                .FILL x147A
                                .FILL x12F6
                                .FILL x11A7
                                .FILL x1084

; Espacio para Guardado Principal
G_R1:                           .BLKW #1
G_R2:                           .BLKW #1
G_R3:                           .BLKW #1
G_R4:                           .BLKW #1
G_R5:                           .BLKW #1
G_R7:                           .BLKW #1

; Espacio para Guardado de MULT_MODULO
M_R0:                           .BLKW #1
M_R1:                           .BLKW #1
M_R2:                           .BLKW #1
M_R3:                           .BLKW #1
M_R4:                           .BLKW #1
M_R5:                           .BLKW #1
M_R7:                           .BLKW #1

.END
