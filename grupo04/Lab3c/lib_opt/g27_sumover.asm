

;   ============================================================================
;   Subrutina: SUMOVER   (version optimizada con ADDC)
;       Sumador de 16 bits que incluye bit carry de entrada y salida.
;
;   -> INPUT  [R0] Valor A.
;   -> INPUT  [R1] Valor B.
;   -> INPUT  [R2] Carry de entrada (tiene que valer 0 o 1).
;   <- OUTPUT [R0] Valor resultado (A + B + carry).
;   <- OUTPUT [R2] Carry de salida (saldra con valor 0 o 1).
;
;   Usa el bit C de la ISA:
;     ADD  R3 R2 #-1  : R2 = 1 -> 1 + 0xFFFF genera carry (C = 1)
;                       R2 = 0 -> 0 + 0xFFFF no genera carry (C = 0)
;     ADDC R0 R0 R1   : R0 = R0 + R1 + C, y deja en C el carry de salida
;     AND  R2 R2 #0   : no modifica C
;     ADDC R2 R2 R2   : R2 = 0 + 0 + C
;   ============================================================================

SUMOVER                                 ;
    ST R3 sumover_r3                    ;
    ADD R3 R2 #-1                       ;   C = carry de entrada
    ADDC R0 R0 R1                       ;   R0 = A + B + C ; C = carry de salida
    AND R2 R2 #0                        ;
    ADDC R2 R2 R2                       ;   R2 = carry de salida (0 o 1)
    LD R3 sumover_r3                    ;
    RET                                 ;

sumover_r3          .FILL #0

.END
