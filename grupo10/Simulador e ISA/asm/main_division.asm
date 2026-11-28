; Programa principal minimo para probar division.asm (una llamada a DIV_LONG)
            .ORIG x3000
            .EXTERNAL DIVISION-DIV_LONG

            LD   R0, A               ; a = 5,5 en Q7.8
            LD   R1, B               ; b = 2,0 en Q7.8
            JSR  DIVISION-DIV_LONG   ; R0 = a / b en Q7.8
            HALT                     ; R0 = x02C0 = 704 = 2,75

A           .FILL #1408
B           .FILL #512
            .END
