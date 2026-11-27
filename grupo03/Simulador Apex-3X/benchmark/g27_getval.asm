
; ============================================================================
; Subrutina: GETVAL  [LC-3X — adaptada]
;     Obtiene un valor por teclado en el formato Q especificado.
;
;     Cambios respecto al original LC-3:
;       1. ADD R2, R2, #-16  -> imm4 no admite -16.
;          Reemplazado por MOVI R3, #-16 / ADD R2, R2, R3.
;       No hay otros errores en este modulo (todos los demas imm estan en rango).
;
; -> INPUT  [R0] n (bits fraccionarios; 0=entero, 16=DQ15.16).
; <- OUTPUT [R0] Qm.n u parte entera.
; <- OUTPUT [R1] 0 o parte fraccionaria.
; ============================================================================

.EXTERNAL GETVAL_BUFFER-BUFFER
.EXTERNAL GETVAL_BUFFER-BUFFER_END
ext_buffer      .FILL GETVAL_BUFFER-BUFFER
ext_buffer_end  .FILL GETVAL_BUFFER-BUFFER_END

.EXTERNAL GETLINE-GETLINE
.EXTERNAL FROMDEC-FROMDEC
.EXTERNAL TODEC-TODEC
sub_getline     .FILL GETLINE-GETLINE
sub_fromdec     .FILL FROMDEC-FROMDEC
sub_todec       .FILL TODEC-TODEC

.EXTERNAL to_qm_n-TO_QM_N
.EXTERNAL from_qm_n-FROM_QM_N
sub_to_qm_n     .FILL to_qm_n-TO_QM_N
sub_from_qm_n   .FILL from_qm_n-FROM_QM_N

GETVAL
    ST R2 getval_r2
    ST R3 getval_r3
    ST R4 getval_r4
    ST R5 getval_r5
    ST R7 getval_r7

    ST R0 getval_n

    LD R0 ext_buffer
    LD R1 ext_buffer_end
    LD R2 sub_getline
    JSRR R2                     ; buffer = getline()

    LD R2 sub_fromdec
    JSRR R2                     ; [R0,R1,R5] = [entero, fraccion, errores]

getval_get_int
    LD R2 getval_n
    BRnp getval_get_dq16        ; if n == 0:
    ADD R1 R1 #0
    BRzp getval_get_int_sk1
    ADD R0 R0 #1
getval_get_int_sk1
    AND R1 R1 #0                ;   fraccion = 0
    ST R0 getval_value_0
    ST R1 getval_value_1
    BR getval_out

getval_get_dq16
    MOVI R3 #-16
    ADD R2 R2 R3                ; R2 = n - 16
    BRnp getval_get_qnm         ; elif n == 16:
    ST R0 getval_value_0
    ST R1 getval_value_1
    BR getval_out

getval_get_qnm                  ; else:
    LD R2 getval_n
    LD R3 sub_to_qm_n
    JSRR R3                     ;   qm_n = to_Qm_n(entero, fraccion, n)
    AND R1 R1 #0
    ST R0 getval_value_0
    ST R1 getval_value_1
    LD R1 getval_n
    LD R2 sub_from_qm_n
    JSRR R2                     ;   [R0,R1] = from_Qm_n(qm_n, n)

getval_out
    LD R2 ext_buffer
    AND R3 R3 #0
    LD R4 sub_todec
    JSRR R4

    LEA R0 getval_lbraket
    PUTS
    ADD R0 R2 #0
    PUTS
    LEA R0 getval_rbraket
    PUTS                        ; print("[ " + buffer + " ]\n")

    LD R0 getval_value_0
    LD R1 getval_value_1
    LD R2 getval_r2
    LD R3 getval_r3
    LD R4 getval_r4
    LD R5 getval_r5
    LD R7 getval_r7
    RET

getval_lbraket  .STRINGZ "[ "
getval_rbraket  .STRINGZ " ]\n"
getval_n        .FILL #0
getval_value_0  .FILL #0
getval_value_1  .FILL #0
getval_r2       .FILL #0
getval_r3       .FILL #0
getval_r4       .FILL #0
getval_r5       .FILL #0
getval_r7       .FILL #0

.END
