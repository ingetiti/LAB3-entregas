;   ============================================================================
;   Subrutina: PAUSE
;       Muestra un prompt y espera a que se pulse una tecla.
;       Optimizada: usa pila hardware (PUSHM/POPM), MOVI y aprovecha que TRAP
;       no modifica R7.
;   ============================================================================

PAUSE
    PUSHM {R0}                          ; Guarda R0 en pila hardware
    LEA R0, pause_prompt
    PUTS                                ; print("Pulsa una tecla para continuar...")
    GETC                                ; getc() (TRAP preserva R7)
    MOVI R0, #10
    OUT                                 ; print("\n")
    POPM {R0}                           ; Restaura R0
    RET

pause_prompt  .STRINGZ "Pulsa una tecla para continuar..."

.END
