; =====================================================================
; DIV_NEWTON (GRUPO 12, OPTIMIZADA): Division Q7.8 por Newton-Raphson
;   Entrada : R0 = dividendo (Q7.8), R1 = divisor (Q7.8)
;   Salida  : R0 = cociente (Q7.8) o xFFFF si divisor == 0
;   Algoritmo: Reduccion de rango + LUT inicial + 2 iteraciones NR
;     x_{k+1} = x_k * (2 - d * x_k) en Q3.12 + multiplicacion y desnorm.
; =====================================================================

DIV_NEWTON
    PUSHM {R1, R2, R3, R4, R5, R7}

    ; Signos y magnitudes absolutas
    XOR  R2, R0, R1             ; bit 15 de R2 = signo final
    ST   R2, FLAG_SIGNO

    ABS  R3, R0                 ; |dividendo|
    ABS  R2, R1                 ; |divisor|
    BRz  ERROR_DIV0
    ST   R3, VAR_DIVIDENDO

    ; Reduccion de rango: contar s desplazamientos hasta bit 15 == 1
    MOVI R3, #0
    ADD  R5, R2, #0
FIND_S_LOOP
    CMP  R5, #0
    BRn  FIND_S_DONE
    SHL  R5, R5, #1
    ADD  R3, R3, #1
    BRnzp FIND_S_LOOP
FIND_S_DONE
    ST   R3, SAVED_S

    ; Normalizar R2 a [x1000, x1FFF] (Q3.12 en [1, 2))
    ADD  R4, R3, #-4
    BRz  NORM_DONE
    BRp  NORM_LEFT
    NEG  R4, R4
    LSR  R2, R2, R4
    BRnzp NORM_DONE
NORM_LEFT
    SHL  R2, R2, R4
NORM_DONE

    ; Indice LUT = (R2 >>> 8) & 7
    LSR  R5, R2, #8
    AND  R3, R5, #7
    SHL  R3, R3, #1
    LEA  R4, TABLA_LUT
    ADD  R4, R4, R3
    LDR  R5, R4, #0             ; R5 = x0 (estimacion inicial Q3.12)

    LD   R7, DOS_Q312           ; R7 = 2.0 en Q3.12 (x2000)

    ; Iteracion 1 NR: x1 = x0 * (2 - d * x0)
    MULL R0, R2, R5
    MULH R1, R2, R5
    LSR  R0, R0, #12
    SHL  R1, R1, #4
    OR   R3, R0, R1             ; d * x0 (Q3.12)
    SUB  R3, R7, R3             ; 2 - d * x0
    MULL R0, R5, R3
    MULH R1, R5, R3
    LSR  R0, R0, #12
    SHL  R1, R1, #4
    OR   R5, R0, R1             ; x1

    ; Iteracion 2 NR: x2 = x1 * (2 - d * x1)
    MULL R0, R2, R5
    MULH R1, R2, R5
    LSR  R0, R0, #12
    SHL  R1, R1, #4
    OR   R3, R0, R1             ; d * x1
    SUB  R3, R7, R3             ; 2 - d * x1
    MULL R0, R5, R3
    MULH R1, R5, R3
    LSR  R0, R0, #12
    SHL  R1, R1, #4
    OR   R5, R0, R1             ; x2

    ; Multiplicacion final: |dividendo| * x2 >> 12
    LD   R3, VAR_DIVIDENDO
    MULL R0, R3, R5
    MULH R1, R3, R5
    LSR  R0, R0, #12
    SHL  R1, R1, #4
    OR   R2, R0, R1

    ; Desnormalizacion segun SAVED_S - 8
    LD   R3, SAVED_S
    MOVI R4, #8
    SUB  R4, R3, R4
    BRz  DENORM_DONE
    BRp  DENORM_LEFT
    NEG  R4, R4
    LSR  R2, R2, R4
    BRnzp DENORM_DONE
DENORM_LEFT
    SHL  R2, R2, R4
DENORM_DONE

    ; Restaurar signo
    LD   R0, FLAG_SIGNO
    BRzp FIN_EXITOSO
    NEG  R2, R2

FIN_EXITOSO
    ADD  R0, R2, #0
    BRnzp RESTAURAR_ESTADO

ERROR_DIV0
    MOVI R0, #-1

RESTAURAR_ESTADO
    POPM {R1, R2, R3, R4, R5, R7}
    RET

VAR_DIVIDENDO       .BLKW #1
SAVED_S             .BLKW #1
FLAG_SIGNO          .BLKW #1
DOS_Q312            .FILL x2000

TABLA_LUT           .FILL x1E1E
                    .FILL x1AF2
                    .FILL x1861
                    .FILL x1642
                    .FILL x147A
                    .FILL x12F6
                    .FILL x11A7
                    .FILL x1084

.END
