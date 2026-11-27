;====================================================================
; main.asm - Programa principal de PRUEBA LOCAL para el modulo booth
; En la plataforma: crear booth.asm y main.asm, clic derecho sobre
; main.asm -> "Usar como entrada", Ensamblar, Ejecutar.
; Calcula 12.5 x 3.75 (cambiar OP_X / OP_Y para otros casos).
; No toca R6: lo deja como lo inicializa el simulador.
;====================================================================
        .ORIG x3000
        .EXTERNAL BOOTH-MULT_BOOTH      ; etiqueta MULT_BOOTH de booth.asm

        LD   R0, OP_X                   ; R0 = X en Q7.8
        LD   R1, OP_Y                   ; R1 = Y en Q7.8
        LD   R5, BOOTH_PTR              ; direccion completa de 16 bits
        JSRR R5                         ; llamada entre archivos
        ST   R0, RESULTADO              ; R0 = RES en Q7.8
        HALT                            ; fin del programa principal

OP_X      .FILL x0C80                   ; 12.5   en Q7.8
OP_Y      .FILL x03C0                   ; 3.75   en Q7.8
RESULTADO .FILL x0000                   ; esperado x2EE0 (= 46.875)
BOOTH_PTR .FILL BOOTH-MULT_BOOTH        ; .FILL + JSRR en toda llamada externa
        .END
