

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

;   ============================================================================
;   Subrutina: GETVAL
;       Obtiene un valor por teclado en un formato especifico, mostrando el valor
;       que se obtuvo realmente.
;
;       El formato se especifica con un valor numerico que representa la cantidad
;       de bits fraccionarios a tomar (Para Qm.n sera el valor de n).
;       Si el valor es 0, se considera totalmente entero (16 bits enteros), y si
;       el valor es 16, se considera un Q15.16 (Que tendra en R0 el entero, y en
;       R1 el fraccionario).
;
;   -> INPUT  [R0] n .
;   <- OUTPUT [R0] Qn.m obtenido, o parte entera obtenida (depende del formato).
;   <- OUTPUT [R1] cero, o parte fraccionaria obtenida (depende del formato).
;   Optimizaciones:
;     - PUSHM/POPR reemplaza variables de respaldo en memoria.
;     - JSRM llama directamente a subrutinas externas sin usar registro auxiliar.
;     - CLR / INC / MOV reemplazan secuencias AND+ADD.
;   ============================================================================
GETVAL
    PUSHM   {R2, R3, R4, R5, R7}

    ST      R0, getval_n

    LD      R0, ext_buffer
    LD      R1, ext_buffer_end
    JSRM    sub_getline                 ; [R0] buffer = getline()

    JSRM    sub_fromdec                 ; [R0, R1, R5] = [entero, fraccion, errores]

getval_get_int
    LD      R2, getval_n
    BRnp    getval_get_dq16             ; if n == 0:
    MOV     R1, R1
    BRzp    getval_get_int_sk1
    INC     R0
getval_get_int_sk1
    CLR     R1                          ;     fraccion = 0
    ST      R0, getval_value_0          ;     [value_0] = entero
    ST      R1, getval_value_1          ;     [value_1] = 0
    BR      getval_out

getval_get_dq16
    ADDI    R2, R2, #-16
    BRnp    getval_get_qnm              ; elif n == 16:
    ST      R0, getval_value_0          ;     [value_0] = entero
    ST      R1, getval_value_1          ;     [value_1] = fraccion
    BR      getval_out

getval_get_qnm                          ; else:
    LD      R2, getval_n
    JSRM    sub_to_qm_n                 ;     [R0] qm_n = to_Qm_n(entero, fraccion, n)
    CLR     R1                          ;     fraccion = 0
    ST      R0, getval_value_0          ;     [value_0] = qm_n
    ST      R1, getval_value_1          ;     [value_1] = 0
    LD      R1, getval_n
    JSRM    sub_from_qm_n               ;     [R0, R1] = from_Qm_n(qm_n, n)

getval_out
    LD      R2, ext_buffer
    CLR     R3                          ; (R3 = formato)
    JSRM    sub_todec                   ; [R2] = buffer (con valor actualizado)

    LEA     R0, getval_lbraket
    PUTS
    MOV     R0, R2
    PUTS
    LEA     R0, getval_rbraket
    PUTS                                ; print("[ " + buffer + " ]\n")

    LD      R0, getval_value_0
    LD      R1, getval_value_1
    POPR    {R2, R3, R4, R5, R7}


getval_lbraket      .STRINGZ "[ "
getval_rbraket      .STRINGZ " ]\n"
getval_n            .FILL #0
getval_value_0      .FILL #0
getval_value_1      .FILL #0

.END
