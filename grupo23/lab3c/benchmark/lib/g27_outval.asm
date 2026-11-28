

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
;       El fomrato se especifica con un valor numerico que representa la cantidad
;       de bits fraccionarios a tomar (Para Qm.n sera el valor de n).
;       Si el valor es 0, se considera totalmente entero (16 bits enteros), y si 
;       el valor es 16, se considera un Q15.16 (Que tendra en R0 el entero, y en
;       R1 el fraccionario).
;
;   -> INPUT  [R0] Qn.m , o parte entera (depende del formato).
;   -> INPUT  [R1] cero, o parte fraccionaria (depende del formato).
;   -> INPUT  [R2] n .
;
;   ============================================================================
OUTVAL                                  ;
;   [G23] Misma salida que la version de la LC-3. El resguardo de los seis
;   registros pasa de 6 ST + 6 LD a un PUSH y un POP (la pila R6 ya la usan TODEC
;   y FROM_QM_N), y el salto de linea se carga de memoria con un LD en lugar de
;   AND + ADD.
    PUSH R0 R1 R2 R3 R4 R7              ;   resguardo
    ADD R2 R2 #0                        ;
    BRnp outval_sk1                     ;   if n == 0:
    AND R1 R1 #0                        ;       fraccion = 0
    BR outval_out                       ;

outval_sk1                              ;
    ADD R3 R2 #-16                      ;
    BRz outval_out                      ;   if n != 16:
    BRp outval_lento                    ;       (n > 16: FROM_QM_N)
    ADD R4 R2 #-1
    BRnz outval_lento                   ;       (n <= 1: FROM_QM_N)
;   [G23] 2.a etapa: con n de 2 a 15, FROM_QM_N en linea: con p = 2^(16-n), la
;   parte alta del producto con signo v*p es el entero (v >> n) y la baja la
;   fraccion (v << (16-n)); los demas n siguen llamando a FROM_QM_N.
    LD R4 outval_tabla
    ADDX R4 R4 R2
    LDR R4 R4 #0                        ;       [R4] p = 2^(16-n)
    MUL R1 R0 R4                        ;       fraccion
    MULH R0 R0 R4                       ;       entero

outval_out
    LD R2 ext_buffer                    ;
    AND R3 R3 #0                        ;
    LD R4 sub_todec                     ;
    JSRR R4                             ;
    LD R0 ext_buffer                    ;
    PUTS                                ;   print(todec(value))
    LD R0 outval_nl                     ;
    OUT                                 ;   print(salto de linea)
    POP R0 R1 R2 R3 R4 R7               ;
    RET                                 ;

outval_lento
    ADD R1 R2 #0                        ;
    LD R2 sub_from_qm_n                 ;
    JSRR R2                             ;   (entero, fraccion) = fromQm_n(qm_n, n)
    BR outval_out

.EXTERNAL G12_SUBRUTINA_GRUPO_12-G12_SHR_TAB
outval_tabla        .FILL G12_SUBRUTINA_GRUPO_12-G12_SHR_TAB

outval_nl           .FILL #10

.END
