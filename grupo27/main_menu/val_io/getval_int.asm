

.EXTERNAL GETVAL_BUFFER-BUFFER
.EXTERNAL GETVAL_BUFFER-BUFFER_END

.EXTERNAL GETLINE-GETLINE
.EXTERNAL FROMDEC-FROMDEC
.EXTERNAL TODEC-TODEC


;
;   Subrutina para obtener un valor por teclato en cierto formato, mostrando un prompt y el valor obtenido.
;


GETVAL_INT

    ; [R0] prompt   ("a > ")
    ; [R1] name     ("a:  ")

    ST R1 getval_int_name               ;
    ST R2 getval_int_r2                 ;
    ST R3 getval_int_r3                 ;
    ST R5 getval_int_r5                 ;
    ST R7 getval_int_r7                 ;

    PUTS                                ;   print(prompt)

    LD R0 getval_int_buffer_ptr         ;
    LD R1 getval_int_buffer_end_ptr     ;
    JSR GETLINE-GETLINE                 ;   [R0] buffer = getline()

    JSR FROMDEC-FROMDEC                 ;   [R0, R1, R5] = [entero, decimal, errores]

    ST R0 getval_int_entero             ;
    AND R1 R1 #0                        ;   decimal = 0

    LD R2 getval_int_buffer_ptr         ;
    AND R3 R3 #0                        ;   # (R3 = formato)
    JSR TODEC-TODEC                     ;   [R2] = buffer   # (con valor actualizado)

    LD R0 getval_int_name               ;
    PUTS                                ;
    ADD R0 R2 #0                        ;
    PUTS                                ;
    AND R0 R0 #0                        ;
    ADD R0 R0 #10                       ;
    OUT                                 ;   print(name + buffer + '\n')

    LD R0 getval_int_entero             ;
    LD R1 getval_int_name               ;
    LD R2 getval_int_r2                 ;
    LD R3 getval_int_r3                 ;
    LD R5 getval_int_r5                 ;
    LD R7 getval_int_r7                 ;
    RET                                 ;

getval_int_entero  .FILL #0
getval_int_name    .FILL #0
getval_int_r2      .FILL #0
getval_int_r3      .FILL #0
getval_int_r5      .FILL #0
getval_int_r7      .FILL #0
getval_int_buffer_ptr     .FILL GETVAL_BUFFER-BUFFER
getval_int_buffer_end_ptr .FILL GETVAL_BUFFER-BUFFER_END

.END
