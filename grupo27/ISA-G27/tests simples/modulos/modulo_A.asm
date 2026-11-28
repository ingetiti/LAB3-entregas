


subrutina
    ST R7 subrutina_r7
    LEA R0 texto
    PUTS
    LD R7 subrutina_r7
    RET

texto .STRINGZ "se ejecuto modulo_A\n"
subrutina_r7 .FILL #0

.END