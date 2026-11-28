;   ============================================================================
;   Subrutina: TO_QM_N
;       Convierte entre distintos formatos Q (De Q15.16 a Qm.n).
;       Optimizada para la nueva ISA con SHLV/SRLV directos y redondeo
;       mediante el bit mas significativo descartado.
;
;   -> INPUT  [R0] Parte entera del Q15.16 .
;   -> INPUT  [R1] Parte fraccionaria del Q15.16 .
;   -> INPUT  [R2] n.
;   <- OUTPUT [R0] Qm.n .
;   ============================================================================

TO_QM_N
    PUSHM {R1, R2, R3}
    ADDI R2, R2, #0             ; caso especial n == 0
    BRz to_qm_n_n0
    MOVI R3, #16
    SUB R3, R3, R2              ; R3 = 16 - n
    BRz to_qm_n_n16             ; caso especial n == 16

    SRLV R3, R1, R3             ; R3 = frac >> (16 - n)
    SHLV R0, R0, R2             ; R0 = entero << n
    OR R0, R0, R3               ; R0 = (entero << n) | (frac >> (16 - n))
    SHLV R3, R1, R2             ; bit 15 de R3 = primer bit fraccionario descartado
    BRzp to_qm_n_ret
    INC R0                      ; redondeo

to_qm_n_ret
    POPM {R1, R2, R3}
    RET

to_qm_n_n0
    ADDI R1, R1, #0             ; redondeo segun bit 15 de frac
    BRzp to_qm_n_ret
    INC R0
    BR to_qm_n_ret

to_qm_n_n16
    MOV R3, R0                  ; conservar entero para bit de redondeo original
    MOV R0, R1                  ; resultado = frac
    ADDI R3, R3, #0
    BRzp to_qm_n_ret
    INC R0
    BR to_qm_n_ret

    .END
