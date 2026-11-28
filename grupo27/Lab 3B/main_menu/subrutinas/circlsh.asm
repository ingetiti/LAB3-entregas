

;   ============================================================================
;   Subrutina: CIRCLSH
;       Corre de manera circular los bits de 2 registros A y B, hacia la
;       izquierda n veces. (Circular hace referencia a que los bits que salen de
;       A son agregados a B y viceversa).
;   
;   -> INPUT  [R0] Registro A.
;   -> INPUT  [R1] Registro B.
;   -> INPUT  [R2] Numero de veces.
;   <- OUTPUT [R0] Nuevo registro A despues del corrimiento. 
;   <- OUTPUT [R1] Nuevo registro B despues del corrimiento.
;   ============================================================================


CIRCLSH                                 ;
    ST R2 circlsh_r2                    ;   [R2] n
    ST R3 circlsh_r3                    ;

circlsh_loop                            ;
    AND R3 R3 #0                        ;   [R3] carry = 0
    ADD R2 R2 #0                        ;
    BRnz circlsh_ret                    ;   while n > 0:
    ADD R0 R0 #0                        ;
    BRzp circlsh_sk1                    ;       if right & 0x8000:
    ADD R3 R3 #1                        ;           carry = carry + 1
circlsh_sk1                             ;
    ADD R0 R0 R0                        ;       right = right << 1
    ADD R1 R1 #0                        ;
    BRzp circlsh_sk2                    ;       if left & 0x8000:
    ADD R0 R0 #1                        ;           right = right + 1
circlsh_sk2                             ;
    ADD R1 R1 R1                        ;       left = left << 1
    ADD R1 R1 R3                        ;       left = left + carry
    ADD R2 R2 #-1                       ;       n -= 1       
    BRnzp circlsh_loop                  ;

circlsh_ret                             ;
    LD R2 circlsh_r2                    ;
    LD R3 circlsh_r3                    ;
    RET                                 ;

circlsh_r2          .FILL #0
circlsh_r3          .FILL #0

.END