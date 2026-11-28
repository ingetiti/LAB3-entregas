; ============================================================================
; Modulo: mcm   (archivo g7_mcm.asm)                  Grupo 7
; Minimo comun multiplo de dos enteros con signo, en punto fijo Q15.0.
; Algoritmo: Euclides por restas sucesivas para el MCD, cociente
; Q = menor / MCD por restas sucesivas y MCM = Q * mayor por sumas sucesivas
; (se divide antes de multiplicar para evitar overflow prematuro).
; Optimizado para la nueva ISA con PUSHM/POPM, NEG, CMP, SUB, CLR, INC, DEC, MOVH.
;
; MCM
;   Entrada:  R0 = a, R1 = b  (enteros con signo, Q15.0, [-32767, 32767])
;   Salida:   R0 = MCM(|a|, |b|) en Q15.0, exacto, rango [0, 32767]
;                  a = 0 o b = 0        -> R0 = 0
;                  MCM real > 32767     -> R0 = x8000 (-32768), aviso de overflow
;   Preserva: R1..R7 y SP (reentrante).
; ============================================================================

MCM
    PUSHM {R1, R2, R4, R5}

    ; Obtener |a| y |b|.
    ADDI R0, R0, #0
    BRzp mcm_a_pos
    NEG R0, R0
mcm_a_pos
    ADDI R1, R1, #0
    BRzp mcm_b_pos
    NEG R1, R1
mcm_b_pos

    ; Si alguno es cero, el MCM es cero.
    ADDI R0, R0, #0
    BRz mcm_resultado_cero
    ADDI R1, R1, #0
    BRz mcm_resultado_cero

    ; R4 = menor, R5 = mayor.
    CMP R0, R1
    BRlt mcm_a_es_menor
    MOV R4, R1
    MOV R5, R0
    BR mcm_mcd_loop

mcm_a_es_menor
    MOV R4, R0
    MOV R5, R1

    ; Euclides por restas sucesivas: resultado en R0.
mcm_mcd_loop
    CMP R0, R1
    BRz mcm_mcd_listo
    BRlt mcm_r0_menor
    SUB R0, R0, R1
    BR mcm_mcd_loop

mcm_r0_menor
    SUB R1, R1, R0
    BR mcm_mcd_loop

mcm_mcd_listo
    ; Cociente R2 = menor / MCD por restas sucesivas.
    CLR R2
mcm_dividir
    INC R2
    SUB R4, R4, R0
    BRp mcm_dividir

    ; MCM = cociente * mayor por sumas sucesivas, con corte por overflow.
    CLR R0
mcm_multiplicar
    ADD R0, R0, R5
    BRn mcm_overflow
    DEC R2
    BRp mcm_multiplicar
    BR mcm_fin

mcm_overflow
    CLR R0
    MOVH R0, #128               ; R0 = x8000 (-32768)

mcm_fin
    POPM {R1, R2, R4, R5}
    RET

mcm_resultado_cero
    CLR R0
    BR mcm_fin

    .END
