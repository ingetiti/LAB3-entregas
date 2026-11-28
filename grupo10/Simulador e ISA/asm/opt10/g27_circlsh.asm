; ============================================================================
; Modulo: circlsh  (archivo g27_circlsh.asm)                            Grupo 27
; Rota a la izquierda, n veces, el par de registros A y B como un solo valor de
; 32 bits [B:A]: el bit alto de A pasa a ser el bajo de B y el alto de B el bajo
; de A. En LC10 se resuelve sin lazo con desplazamientos: girar n veces es girar
; n mod 32 (el original hacia n pasadas de 14 instrucciones).
;
; CIRCLSH
; Entrada:  R0 = A, R1 = B, R2 = n (con signo; si n <= 0 no se gira)
; Salida:   R0 = nuevo A, R1 = nuevo B
; Preserva: R2 a R5 (R3 a R5 se guardan en la pila con PUSH/POP)
;
;   s = n mod 16; si el bit 4 de n esta encendido primero se intercambian A y B
;   (giro de 16); luego, con q = 16 - s:
;       A' = (A << s) | (B >> q)       B' = (B << s) | (A >> q)
;   (un desplazamiento de 16 da 0, asi que s = 0 deja los registros iguales)
; ============================================================================

CIRCLSH
                        PUSH  R3, R4, R5
                        TST   R2
                        BRnz  circlsh_ret               ; n <= 0: nada que girar
                        SHL   R3, R2, #12
                        SHR   R3, R3, #12               ; s = n mod 16
                        SHL   R4, R2, #11               ; bit 4 de n a la bandera N
                        BRzp  circlsh_sk
                        XOR   R0, R0, R1                ; giro de 16: intercambiar A y B
                        XOR   R1, R1, R0
                        XOR   R0, R0, R1
circlsh_sk
                        MOVI  R4, #16
                        SUB   R4, R4, R3                ; q = 16 - s
                        SHR   R5, R0, R4                ; A >> q
                        SHL   R0, R0, R3
                        SHR   R4, R1, R4                ; B >> q
                        OR    R0, R0, R4
                        SHL   R1, R1, R3
                        OR    R1, R1, R5
circlsh_ret
                        POP   R3, R4, R5
                        RET


.END
