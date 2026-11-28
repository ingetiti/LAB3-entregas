

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
;
;   (i) Version para la ISA del Grupo 7: en vez de correr de a un bit con un
;   bucle, hace todo el corrimiento de una vez con SHL / SHR. Mismo resultado
;   que la version original para cualquier n: si n <= 0 no hace nada, y si n es
;   mayor a 31 gira n mod 32 (rotar 32 bits n veces es lo mismo que n mod 32).
;       n >= 16  ->  primero intercambia A y B (equivale a girar 16 bits).
;       0 < n < 16:
;           A' = (A << n) + (B >> (16 - n))
;           B' = (B << n) + (A >> (16 - n))
;   Conserva R2, R3 y R4 (los guarda en la pila, R6 vuelve al mismo valor).
;   ============================================================================


CIRCLSH                                 ;
    ADD R2 R2 #0                        ;
    BRnz circlsh_nop                    ;   if n <= 0: no hace nada

    ADD R6 R6 #-6                       ;   guarda R2, R3 y R4 en la pila (ahorra 3 palabras de datos)
    STW R2 R6 #0                        ;
    STW R3 R6 #1                        ;
    STW R4 R6 #2                        ;

    LD R3 circlsh_c31                   ;
    AND R2 R2 R3                        ;   [R2] n = n mod 32

    ADD R3 R2 #-16                      ;
    BRn circlsh_sk1                     ;   if n >= 16:
    ADD R2 R3 #0                        ;       n = n - 16
    ADD R3 R0 #0                        ;
    ADD R0 R1 #0                        ;
    ADD R1 R3 #0                        ;       intercambia A y B (giro de 16)

circlsh_sk1                             ;
    ADD R2 R2 #0                        ;
    BRz circlsh_ret                     ;   if n == 0: listo

    LD R3 circlsh_c16                   ;
    SUB R3 R3 R2                        ;   [R3] k = 16 - n

    SHL R4 R0 R2                        ;   [R4] A << n
    SHR R0 R0 R3                        ;   [R0] A >> k
    SHR R3 R1 R3                        ;   [R3] B >> k
    SHL R1 R1 R2                        ;   [R1] B << n
    ADD R1 R1 R0                        ;   B' = (B << n) + (A >> k)
    ADD R0 R4 R3                        ;   A' = (A << n) + (B >> k)

circlsh_ret                             ;
    LDW R2 R6 #0                        ;
    LDW R3 R6 #1                        ;
    LDW R4 R6 #2                        ;
    ADD R6 R6 #6                        ;

circlsh_nop                             ;
    RET                                 ;

circlsh_c16         .FILL #16
circlsh_c31         .FILL #31

.END
