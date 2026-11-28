


                        .EXTERNAL g27_circlsh-CIRCLSH
sub_circlsh             .FILL g27_circlsh-CIRCLSH


; ============================================================================
; Subrutina: TO_QM_N
; Convierte entre distintos formatos Q (De Q15.16 a Qm.n).

; -> INPUT  [R0] Parte entera del Q15.16 .
; -> INPUT  [R1] Parte fraccionaria del Q15.16 .
; -> INPUT  [R2] n.
; <- OUTPUT [R0] Qm.n .
; ============================================================================

; [.....int......][.....frac.....]
; ..int..][.....frac.....][.......    (<< n)
; [....Qm_n......][..............]


TO_QM_N

                        PUSH  R1, R2, R3, R7

; [R0] entero
; [R1] decimal
; [R2] n

                        LD    R3, sub_circlsh
                        JSRR  R3

                        ADD   R1, R1, #0
                        BRzp  to_qm_n_ret
                        ADD   R0, R0, #1                ; redondeo

to_qm_n_ret
                        POP   R1, R2, R3, R7
                        RET



.END
