

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

    ST R0 outval_r0                     ;
    ST R1 outval_r1                     ; 
    ST R2 outval_r2                     ;
    ST R3 outval_r3                     ;
    ST R4 outval_r4                     ;
    ST R7 outval_r7                     ;

    ADD R2 R2 #0                        ;
    BRnp outval_sk1                     ;   if n == 0:
    AND R1 R1 #0                        ;       fraccion = 0
    BR outval_out                       ;

outval_sk1                              ;
    ADD R3 R2 #-16                      ;   
    BRz outval_out                      ;   if n != 16:
    ADD R1 R2 #0                        ;
    LD R2 sub_from_qm_n                 ;
    JSRR R2                             ;       (entero, fraccion) = fromQm_n(qm_n, n)

outval_out
    LD R2 ext_buffer                    ;
    AND R3 R3 #0                        ;
    LD R4 sub_todec                     ;
    JSRR R4                             ;
    LD R0 ext_buffer                    ;
    PUTS                                ;   print(todec(value))
    AND R0 R0 #0                        ;
    ADD R0 R0 #10                       ;
    OUT                                 ;   print('\n')

    LD R0 outval_r0                     ;
    LD R1 outval_r1                     ;
    LD R2 outval_r2                     ;
    LD R3 outval_r3                     ;
    LD R4 outval_r4                     ;
    LD R7 outval_r7                     ;
    RET                                 ;

outval_r0           .FILL #0
outval_r1           .FILL #0 
outval_r2           .FILL #0
outval_r3           .FILL #0 
outval_r4           .FILL #0 
outval_r7           .FILL #0 

.END