;   ============================================================================
;   Subrutina: PAUSE (LC-X)
;       Muestra un prompt y espera a que se pulse una tecla.
;   Conserva todos los registros.
;   ============================================================================

PAUSE
        PUSH  R0
        LEA   R0, PAUSE_PROMPT
        PUTSP                   ; print("Pulsa una tecla para continuar...")
        GETC                    ; getc()
        MOVI  R0, #10
        OUT                     ; print("\n")
        POPR  R0

PAUSE_PROMPT    .STRINGP "Pulsa una tecla para continuar..."

.END
