; ============================================================================
; Modulo: mcd  (archivo g7_mcd.asm)                   Grupo 7
; Maximo comun divisor de dos enteros con signo, en punto fijo Q15.0.
; Algoritmo: Euclides por restas sucesivas (se resta el menor del mayor hasta
; que ambos sean iguales; ese valor es el MCD).
; Optimizado para la nueva ISA con PUSHM/POPM, NEG, CMP y SUB.
;
; MCD
;   Entrada:  R0 = a, R1 = b  (enteros con signo, Q15.0, [-32767, 32767])
;   Salida:   R0 = MCD(|a|, |b|) en Q15.0, exacto, rango [0, 32767]
;                  MCD(0, b) = |b|, MCD(a, 0) = |a|, MCD(0, 0) = 0
;   Preserva: R1..R7 y SP (reentrante).
; ============================================================================

MCD
    PUSHM {R1}

    ; Obtener |a| y |b|.
    ADDI R0, R0, #0
    BRzp mcd_a_pos
    NEG R0, R0
mcd_a_pos
    ADDI R1, R1, #0
    BRzp mcd_b_pos
    NEG R1, R1
mcd_b_pos

    ; Casos con cero.
    ADDI R0, R0, #0
    BRz mcd_devolver_b
    ADDI R1, R1, #0
    BRz mcd_fin

    ; Euclides por restas sucesivas.
mcd_loop
    CMP R0, R1
    BRz mcd_fin
    BRlt mcd_r0_menor
    SUB R0, R0, R1
    BR mcd_loop

mcd_r0_menor
    SUB R1, R1, R0
    BR mcd_loop

mcd_devolver_b
    MOV R0, R1

mcd_fin
    POPM {R1}
    RET

    .END
