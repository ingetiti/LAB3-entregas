;   ============================================================================
;   Subrutina: PAUSE (OPTIMIZADA)
;   ============================================================================

PAUSE
    PUSHM {R0, R7}
    LEA  R0, pause_prompt
    PUTS
    GETC
    MOVI R0, #10
    OUT
    POPM {R0, R7}
    RET

pause_prompt .STRINGZ "Pulsa una tecla para continuar..."

.END
