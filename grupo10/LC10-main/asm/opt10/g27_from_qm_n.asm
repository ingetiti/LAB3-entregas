                        .EXTERNAL g27_circlsh-CIRCLSH
sub_circlsh             .FILL g27_circlsh-CIRCLSH


; ============================================================================
; Subrutina: FROM_QM_N
; Convierte entre distintos formatos Q (De Qm.n a Q15.16).

; -> INPUT  [R0] Qm.n .
; -> INPUT  [R1] n .
; <- OUTPUT [R0] Parte entera del Q15.16 .
; <- OUTPUT [R1] Parte fraccionaria del Q15.16 .
; Preserva: R2 a R5 y R7.
; ============================================================================

; [....Qm_n......][..............]
; [.....ext......][....Qm_n......]    (ext de signo)
; ..ext..][....Qm_n......][.......    (<< (16 - n))

; [00000000000000][11111111111111]    (mascara fraccion)
; 0000000][11111111111111][0000000    (<< (16 - n))

; [.....int......][.frac..0000000]    (mascarar exedente)
; [.....int......][.....frac.....]

; Version LC10. Para 1 <= n <= 15 los dos giros de 32 bits con CIRCLSH del original se reducen a
;     entero = qm >> n  (aritmetico)        fraccion = qm << (16 - n)
; porque el entero es la palabra alta de [ext:qm] girada (16 - n) lugares, o sea el corrimiento
; aritmetico de qm, y la fraccion es la palabra baja (los bits de qm subidos 16 - n lugares) ya
; enmascarada: la mascara solo borra los bits que entran por el giro. Para cualquier otro n (que
; nadie usa en el benchmark) se sigue con el camino general del original.

FROM_QM_N
                        PUSH  R2, R3
                        ADD   R3, R1, #-1               ; n - 1
                        MOVI  R2, #15
                        CMP   R3, R2
                        BRC   from_qm_n_general         ; n - 1 >= 15 sin signo: n <= 0 o n >= 16
                        MOV   R3, R0                    ; qm
                        SAR   R0, R3, R1                ; entero
                        MOVI  R2, #16
                        SUB   R2, R2, R1
                        SHL   R1, R3, R2                ; fraccion
                        POP   R2, R3
                        RET

from_qm_n_general
                        PUSH  R7

; [R0] qm.n
; [R1] n

                        ADD   R2, R1, #0                ; [R2] n
                        ADD   R2, R2, #-8               ; ADD R2, R2, #-16
                        ADD   R2, R2, #-8               ; (sigue)
                        NEG   R2, R2                    ; [R2] 16 - n
                        ADD   R1, R0, #0                ; [R1] qm.n

                        AND   R0, R0, #0
                        ADD   R1, R1, #0
                        BRzp  from_qm_n_sk1
                        NOT   R0, R0                    ; ext

from_qm_n_sk1
                        LD    R3, sub_circlsh
                        JSRR  R3

                        ST    R0, from_qm_n_entero
                        ST    R1, from_qm_n_fraccion

                        AND   R0, R0, #0
                        NOT   R1, R0
                        LD    R3, sub_circlsh
                        JSRR  R3                        ; [R1] mascara

                        LD    R0, from_qm_n_entero
                        LD    R2, from_qm_n_fraccion
                        AND   R1, R1, R2

                        POP   R7                      ; en orden inverso a los PUSH
                        POP   R2, R3
                        RET

from_qm_n_entero        .FILL #0
from_qm_n_fraccion      .FILL #0

.END
