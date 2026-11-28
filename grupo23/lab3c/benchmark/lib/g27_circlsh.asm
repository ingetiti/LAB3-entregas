;   ============================================================================
;   Subrutina: CIRCLSH  (Grupo 27)  -- version adaptada a la ISA G23 (Grupo 23)
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
;   [G23] Misma interfaz y mismos resultados que la version de la LC-3. Es una
;   rotacion de 32 bits de [A:B] n lugares a la izquierda:
;   - n < 8: de a un bit por vuelta con RLC (rotacion a traves del acarreo) y DBP.
;   - n >= 8: de una sola vez. Con s = n mod 32: si s >= 16 se intercambian A y
;     B; con s = s mod 16 y p = 2^s, multiplicar por p deja en la parte baja
;     x << s y en la parte alta x >> (16 - s), asi que
;         A' = MUL(A, p) OR MULHU(B, p)      B' = MUL(B, p) OR MULHU(A, p)
;     (con n chico el lazo es mas barato en ciclos, porque MUL es multiciclo).
;   ============================================================================


.EXTERNAL G12_SUBRUTINA_GRUPO_12-G12_SHR_TAB
circlsh_tabla       .FILL G12_SUBRUTINA_GRUPO_12-G12_SHR_TAB   ;   T[k] = 2^(16-k), k = 1..15

CIRCLSH                                 ;
;   [G23] 2.a etapa: siempre de una sola vez (tambien con n < 8, antes un lazo con
;   RLC) y p = 2^s tomado de la tabla 2^(16-k) de G12 como T[16 - s]: menos memoria.
    PUSH R2 R3 R4                       ;   resguardo
    BRRp R2 circlsh_corre               ;   if n <= 0: no hay nada que correr
circlsh_ret                             ;
    POP R2 R3 R4                        ;
    RET                                 ;
circlsh_corre
    LSR R3 R2 #4
    AND R3 R3 #1
    BRz circlsh_nosw                    ;   if (n mod 32) >= 16:
    ADD R3 R0 #0
    ADD R0 R1 #0
    ADD R1 R3 #0                        ;       A, B = B, A
circlsh_nosw
    AND R2 R2 #15                       ;   s = n mod 16
    BRz circlsh_ret
    NOT R2 R2                           ;   -s - 1
    LD R3 circlsh_tabla
    ADDX R3 R3 R2
    LDR R2 R3 #17                       ;   [R2] p = T[16 - s] = 2^s
    MULHU R3 R0 R2                      ;   A >> (16 - s)
    MULHU R4 R1 R2                      ;   B >> (16 - s)
    MUL R0 R0 R2
    OR R0 R0 R4                         ;   A' = (A << s) | (B >> (16 - s))
    MUL R1 R1 R2
    OR R1 R1 R3                         ;   B' = (B << s) | (A >> (16 - s))
    BR circlsh_ret

.END
