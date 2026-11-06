

.EXTERNAL GETVAL_BUFFER-BUFFER
.EXTERNAL GETVAL_BUFFER-BUFFER_END

.EXTERNAL GETLINE-GETLINE
.EXTERNAL FROMDEC-FROMDEC
.EXTERNAL TODEC-TODEC

.EXTERNAL DQ16_TO_Q8-DQ16_TO_Q8
.EXTERNAL Q8_TO_DQ16-Q8_TO_DQ16

;
;   Subrutina para obtener un valor por teclato en cierto formato, mostrando un prompt y el valor obtenido.
;

GETVAL_Q8

    ; [R0] prompt   ("a > ")
    ; [R1] name     ("a:  ")

    ST R1 getval_q8_name                ;
    ST R2 getval_q8_r2                  ;
    ST R3 getval_q8_r3                  ;
    ST R5 getval_q8_r5                  ;
    ST R7 getval_q8_r7                  ;

    PUTS                                ;   print(prompt)

    LD R0 getval_q8_buffer_ptr         ;
    LD R1 getval_q8_buffer_end_ptr     ;
    JSR GETLINE-GETLINE                 ;   [R0] buffer = getline()

    JSR FROMDEC-FROMDEC                 ;   [R0, R1, R5] = [entero, decimal, errores]

    JSR DQ16_TO_Q8-DQ16_TO_Q8           ;
    ST R0 getval_q8_value               ;   
    JSR Q8_TO_DQ16-Q8_TO_DQ16           ;

    LD R2 getval_q8_buffer_ptr         ;
    AND R3 R3 #0                        ;   # (R3 = formato)
    JSR TODEC-TODEC                     ;   [R2] = buffer   # (con valor actualizado)

    LD R0 getval_q8_name                ;
    PUTS                                ;
    ADD R0 R2 #0                        ;
    PUTS                                ;
    AND R0 R0 #0                        ;
    ADD R0 R0 #10                       ;
    OUT                                 ;   print(name + buffer + '\n')

    LD R0 getval_q8_value               ;
    LD R1 getval_q8_name                ;
    LD R2 getval_q8_r2                  ;
    LD R3 getval_q8_r3                  ;
    LD R5 getval_q8_r5                  ;
    LD R7 getval_q8_r7                  ;
    RET                                 ;

getval_q8_value   .FILL #0
getval_q8_name    .FILL #0
getval_q8_r2      .FILL #0
getval_q8_r3      .FILL #0
getval_q8_r5      .FILL #0
getval_q8_r7      .FILL #0
getval_q8_buffer_ptr     .FILL GETVAL_BUFFER-BUFFER
getval_q8_buffer_end_ptr .FILL GETVAL_BUFFER-BUFFER_END

.END
