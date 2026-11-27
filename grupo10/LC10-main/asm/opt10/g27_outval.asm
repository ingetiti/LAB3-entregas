

                        .EXTERNAL g27_getval_buffer-BUFFER
ext_buffer              .FILL g27_getval_buffer-BUFFER

                        .EXTERNAL g27_todec-TODEC
sub_todec               .FILL g27_todec-TODEC

                        .EXTERNAL g27_from_qm_n-FROM_QM_N
sub_from_qm_n           .FILL g27_from_qm_n-FROM_QM_N


; ============================================================================
; Subrutina: OUTVAL
; Muestra por consola un valor, en un formato especifico.

; El fomrato se especifica con un valor numerico que representa la cantidad
; de bits fraccionarios a tomar (Para Qm.n sera el valor de n).
; Si el valor es 0, se considera totalmente entero (16 bits enteros), y si
; el valor es 16, se considera un Q15.16 (Que tendra en R0 el entero, y en
; R1 el fraccionario).

; -> INPUT  [R0] Qn.m , o parte entera (depende del formato).
; -> INPUT  [R1] cero, o parte fraccionaria (depende del formato).
; -> INPUT  [R2] n .

; ============================================================================
OUTVAL

                        PUSH  R0-R4, R7

                        ADD   R2, R2, #0
                        BRnp  outval_sk1                ; if n == 0:
                        AND   R1, R1, #0                ; fraccion = 0
                        BR    outval_out

outval_sk1
                        ADD   R3, R2, #-8               ; ADD R3, R2, #-16
                        ADD   R3, R3, #-8               ; (sigue)
                        BRz   outval_out                ; if n != 16:
                        ADD   R1, R2, #0
                        LD    R2, sub_from_qm_n
                        JSRR  R2                        ; (entero, fraccion) = fromQm_n(qm_n, n)

outval_out
                        LD    R2, ext_buffer
                        AND   R3, R3, #0
                        LD    R4, sub_todec
                        JSRR  R4
                        LD    R0, ext_buffer
                        PUTS                            ; print(todec(value))
                        MOVI  R0, #10                     ; (AND + 2 ADD)
                        OUT                             ; print('\n')

                        POP   R0-R4, R7
                        RET


.END
