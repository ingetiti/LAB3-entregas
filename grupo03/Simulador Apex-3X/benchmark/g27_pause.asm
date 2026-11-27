
; ============================================================================
; Subrutina: PAUSE  [LC-3X — adaptada]
;     Muestra un prompt y espera a que se pulse una tecla.
;     Cambios respecto al original LC-3:
;       - ADD R0, R0, #10  reemplazado por  MOVI R0, #10
;         (imm4 solo va hasta +7; 10 > 7 requiere MOVI imm8).
; ============================================================================

PAUSE
    ST R0 pause_r0
    ST R7 pause_r7

    LEA R0 pause_prompt
    PUTS                        ; print("Pulsa una tecla para continuar...")
    GETC                        ; getc()
    MOVI R0 #10                 ; '\n'  (imm8 permite #10 directamente)
    OUT                         ; print('\n')

    LD R0 pause_r0
    LD R7 pause_r7
    RET

pause_r0      .FILL #0
pause_r7      .FILL #0
pause_prompt  .STRINGZ "Pulsa una tecla para continuar..."

.END
