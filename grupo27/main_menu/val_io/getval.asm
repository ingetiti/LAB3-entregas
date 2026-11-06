

.EXTERNAL GETVAL_BUFFER-BUFFER
.EXTERNAL GETVAL_BUFFER-BUFFER_END

.EXTERNAL GETLINE-GETLINE
.EXTERNAL FROMDEC-FROMDEC
.EXTERNAL TODEC-TODEC

;
;   Subrutina para obtener un valor por teclato en cierto formato, mostrando un prompt y el valor obtenido.
;


GETVAL

    ; [R0] prompt   ("a > ")
    ; [R1] name     ("a:  ")

    ST R1 getval_name                   ;
    ST R2 getval_r2                     ;
    ST R3 getval_r3                     ;
    ST R5 getval_r5                     ;
    ST R7 getval_r7                     ;

    PUTS                                ;   print(prompt)

    LD R0 getval_buffer_ptr         ;
    LD R1 getval_buffer_end_ptr     ;
    JSR GETLINE-GETLINE                 ;   [R0] buffer = getline()

    JSR FROMDEC-FROMDEC                 ;   [R0, R1, R5] = [entero, decimal, errores]

    ST R0 getval_entero                 ;
    ST R1 getval_decimal                ;

    LD R2 getval_buffer_ptr         ;
    AND R3 R3 #0                        ;   # (R3 = formato)
    JSR TODEC-TODEC                     ;   [R2] = buffer   # (con valor actualizado)

    LD R0 getval_name                   ;
    PUTS                                ;
    ADD R0 R2 #0                        ;
    PUTS                                ;
    AND R0 R0 #0                        ;
    ADD R0 R0 #10                       ;
    OUT                                 ;   print(name + buffer + '\n')

    LD R0 getval_entero                 ;
    LD R1 getval_decimal                ;
    LD R2 getval_r2                     ;
    LD R3 getval_r3                     ;
    LD R5 getval_r5                     ;
    LD R7 getval_r7                     ;
    RET                                 ;

getval_entero   .FILL #0
getval_decimal  .FILL #0
getval_name     .FILL #0
getval_r2       .FILL #0
getval_r3       .FILL #0
getval_r5       .FILL #0
getval_r7       .FILL #0


getval_buffer_ptr .FILL GETVAL_BUFFER-BUFFER
getval_buffer_end_ptr .FILL GETVAL_BUFFER-BUFFER_END
.END
