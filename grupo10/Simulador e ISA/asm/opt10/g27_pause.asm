

; ============================================================================
; Subrutina: PAUSE
; Muestra un prompt y espera a que se pulse una tecla.

; ============================================================================

PAUSE
                        PUSH  R0, R7

                        LEA   R0, pause_prompt
                        PUTS                            ; print("Pulsa una tecla para continuar...")
                        GETC                            ; getc()
                        MOVI  R0, #10                     ; (AND + 2 ADD)
                        OUT                             ; print("\n")

                        POP   R0, R7
                        RET

pause_prompt            .STRINGZ "Pulsa una tecla para continuar..."

.END
