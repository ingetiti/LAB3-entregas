;   ============================================================================
;   Subrutina: CIRCLSH
;       Corre de manera circular los bits de 2 registros A y B, hacia la
;       izquierda n veces. (Los bits que salen de A ingresan a B y viceversa).
;       Optimizada para la nueva ISA usando SHLV/SRLV en O(1) para n mod 32.
;
;   -> INPUT  [R0] Registro A.
;   -> INPUT  [R1] Registro B.
;   -> INPUT  [R2] Numero de veces (n).
;   <- OUTPUT [R0] Nuevo registro A despues del corrimiento.
;   <- OUTPUT [R1] Nuevo registro B despues del corrimiento.
;   ============================================================================

CIRCLSH
    PUSHM {R2, R3, R4, R5}
    ADDI R2, R2, #0             ; si n <= 0, no hay corrimiento
    BRle circlsh_ret

circlsh_mod16
    MOVI R3, #16
    CMP R2, R3
    BRlt circlsh_shift          ; si n < 16, desplazamiento directo en O(1)
    MOV R4, R0                  ; cada 16 bits se intercambian R0 y R1
    MOV R0, R1
    MOV R1, R4
    ADDI R2, R2, #-16           ; n -= 16
    BRp circlsh_mod16
    BR circlsh_ret              ; si n quedo en 0, terminado

circlsh_shift
    SUB R3, R3, R2              ; R3 = 16 - n (1..15)
    SRLV R4, R0, R3             ; R4 = R0 >> (16 - n) -> bits bajos de nuevo R1
    SRLV R5, R1, R3             ; R5 = R1 >> (16 - n) -> bits bajos de nuevo R0
    SHLV R0, R0, R2             ; R0 <<= n
    SHLV R1, R1, R2             ; R1 <<= n
    OR R0, R0, R5               ; R0 = (R0 << n) | (R1 >> (16 - n))
    OR R1, R1, R4               ; R1 = (R1 << n) | (R0 >> (16 - n))

circlsh_ret
    POPM {R2, R3, R4, R5}
    RET

    .END
