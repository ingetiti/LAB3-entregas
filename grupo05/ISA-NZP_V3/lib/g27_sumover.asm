

;   ============================================================================
;   Subrutina: SUMOVER
;       Sumador de 16 bits que incluye bit carry de entrada y salida.
;
;   -> INPUT  [R0] Valor A.
;   -> INPUT  [R1] Valor B.
;   -> INPUT  [R2] Carry de entrada (tiene que valer 0 o 1).
;   <- OUTPUT [R0] Valor resultado (A + B).
;   <- OUTPUT [R2] Carry de salida (saldra con valor 0 o 1).
;   ============================================================================

SUMOVER                                 ;
    ST R1 sumover_r1                    ;
    ST R3 sumover_r3                    ;
    ST R4 sumover_r4                    ;

    ADD R3 R0 #0                        ;   [R3] valor_a
    ADD R0 R2 #0                        ;   [R0] resultado = carry
    AND R2 R2 #0                        ;   [R2] carry = 0

    ADD R3 R3 #0                        ;
    BRzp sumover_test_b                 ;   if valor_a & 0x8000:
    ADD R2 R2 #1                        ;       carry += 1

sumover_test_b                          ;
    ADD R1 R1 #0                        ;
    BRzp sumover_sum                    ;   if valor_b & 0x8000:
    ADD R2 R2 #1                        ;       carry += 1

sumover_sum                             ;
    LD R4 sumover_mask                  ;
    AND R3 R3 R4                        ;   valor_a = valor_a & 0x7FFF
    AND R1 R1 R4                        ;   valor_b = valor_b & 0x7FFF
    ADD R0 R0 R3                        ;
    ADD R0 R0 R1                        ;   resultado = resultado + valor_a + valor_b

    BRzp sumover_resultant              ;   if resultado & 0x8000:
    ADD R2 R2 #1                        ;       carry += 1

sumover_resultant                       ;
    AND R0 R0 R4                        ;   resultado = resultado & 0x7FFF

    AND R4 R2 #1                        ;   
    BRz sumover_test_carry              ;   if carry & 0x0001:
    LD R4 sumover_msb                   ;
    ADD R0 R0 R4                        ;       resultado = resultado + 0x8000

sumover_test_carry                      ;
    AND R4 R2 #2                        ;
    BRz sumover_test_carry_else         ;   if carry & 0x0002:
    AND R2 R2 #0                        ;
    ADD R2 R2 #1                        ;       carry = 1
    BRnzp sumover_ret                   ;   else:

sumover_test_carry_else                 ;
    AND R2 R2 #0                        ;       carry = 0

sumover_ret                             ;
    LD R1 sumover_r1                    ;
    LD R3 sumover_r3                    ;
    LD R4 sumover_r4                    ;
    RET                                 ;

sumover_r1          .FILL #0
sumover_r3          .FILL #0
sumover_r4          .FILL #0
sumover_mask        .FILL x7FFF
sumover_msb         .FILL x8000

.END