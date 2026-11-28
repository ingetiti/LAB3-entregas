

.EXTERNAL GETVAL_BUFFER-BUFFER
ext_buffer      .FILL GETVAL_BUFFER-BUFFER

.EXTERNAL TODEC-TODEC
sub_todec       .FILL TODEC-TODEC

.EXTERNAL FROM_QM_N-FROM_QM_N
sub_from_qm_n   .FILL FROM_QM_N-FROM_QM_N


;   ============================================================================
;   Subrutina: OUTVAL
;       Muestra por consola un valor, en un formato especifico.
;
;       El formato se especifica con un valor numerico que representa la cantidad
;       de bits fraccionarios a tomar (Para Qm.n sera el valor de n).
;       Si el valor es 0, se considera totalmente entero (16 bits enteros), y si
;       el valor es 16, se considera un Q15.16 (Que tendra en R0 el entero, y en
;       R1 el fraccionario).
;
;   -> INPUT  [R0] Qn.m , o parte entera (depende del formato).
;   -> INPUT  [R1] cero, o parte fraccionaria (depende del formato).
;   -> INPUT  [R2] n .
;   Optimizaciones:
;     - PUSHM/POPR reemplaza variables de respaldo en memoria.
;     - JSRM llama directamente a subrutinas externas sin clobber de registros.
;     - CLR / MOVI / MOV para ceros, constantes y copias.
;   ============================================================================
OUTVAL
    PUSHM   {R0, R1, R2, R3, R4, R7}

    MOV     R2, R2                      ; Evaluar n
    BRnp    outval_sk1                  ; if n == 0:
    CLR     R1                          ;     fraccion = 0
    BR      outval_out

outval_sk1
    ADDI    R3, R2, #-16                ;
    BRz     outval_out                  ; if n != 16:
    MOV     R1, R2                      ;     [R1] = n
    JSRM    sub_from_qm_n               ;     (entero, fraccion) = from_Qm_n(qm_n, n)

outval_out
    LD      R2, ext_buffer
    CLR     R3
    JSRM    sub_todec                   ; todec(entero, fraccion, buffer, 0)
    LD      R0, ext_buffer
    PUTS                                ; print(todec(value))
    MOVI    R0, #10
    OUT                                 ; print('\n')

    POPR    {R0, R1, R2, R3, R4, R7}

.END
