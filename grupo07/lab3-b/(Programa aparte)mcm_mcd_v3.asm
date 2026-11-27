; Programa interactivo OPTIMIZADO de MCD y MCM (mismo algoritmo base).
; Ingresar enteros decimales entre -32767 y 32767, uno por linea.
; Si el MCM supera 32767 (overflow), corta de inmediato y muestra -32768 (x8000)

.ORIG x3000

; LD R6, STACK_BASE ; Descomentar solo si tu simulador local no inicializa R6
        LEA R0, PROMPT_A
        PUTS
        JSR LEER_ENTERO
        ST R0, DATO_A
        
        LEA R0, PROMPT_B
        PUTS
        JSR LEER_ENTERO
        ST R0, DATO_B

; 1. Obtener valores absolutos |A| en R0 y |B| en R1.
        LD R0, DATO_A
        BRzp A_POSITIVO
        NOT R0, R0
        ADD R0, R0, #1
A_POSITIVO
        LD R1, DATO_B
        BRzp B_POSITIVO
        NOT R1, R1
        ADD R1, R1, #1
B_POSITIVO

; 2. Casos con cero: gcd(0,B)=|B|, gcd(A,0)=|A| y el MCM es cero.
        ADD R0, R0, #0
        BRz A_ES_CERO
        ADD R1, R1, #0
        BRz B_ES_CERO

; 3. OPTIMIZACION A: Ordenar copias en R4 (menor) y R5 (mayor)
;    y de paso dejar cargado R2 = -R1 para no recalcularlo en cada vuelta.
        NOT R2, R1
        ADD R2, R2, #1          ; R2 = -|B|
        ADD R3, R0, R2          ; R3 = |A| - |B|
        BRzp A_MAYOR_IGUAL_B
        ADD R4, R0, #0          ; Si |A| < |B|: R4 = |A| (menor)
        ADD R5, R1, #0          ;               R5 = |B| (mayor)
        BRnzp INICIAR_MCD
A_MAYOR_IGUAL_B
        ADD R4, R1, #0          ; Si |A| >= |B|: R4 = |B| (menor)
        ADD R5, R0, #0          ;                R5 = |A| (mayor)

; 4. OPTIMIZACION B: Euclides sin recalcular NOT+ADD en cada iteracion.
;    R2 mantiene siempre -R1, solo se actualiza cuando R1 cambia.
INICIAR_MCD
        ADD R3, R0, R2          ; R3 = R0 - R1
        BRz MCD_LISTO
        BRn R0_MENOR_R1
RESTAR_A_R0
        ADD R0, R3, #0          ; R0 = R0 - R1
        ADD R3, R0, R2          ; R3 = nuevo R0 - R1 (sin recalcular -R1)
        BRp RESTAR_A_R0         ; Sigue restando en bucle rapido (solo 3 instr!)
        BRz MCD_LISTO

R0_MENOR_R1
        NOT R2, R0
        ADD R2, R2, #1          ; R2 = -R0 (calculado una sola vez para esta racha)
RESTAR_A_R1
        ADD R1, R1, R2          ; R1 = R1 - R0
        ADD R3, R1, R2          ; R3 = nuevo R1 - R0
        BRp RESTAR_A_R1         ; Sigue restando en bucle rapido (solo 3 instr!)
        BRz MCD_LISTO
; Si dio negativo, ahora R1 < R0: actualizamos R2 = -R1 y pasamos a restar a R0
        NOT R2, R1
        ADD R2, R2, #1
        ADD R3, R0, R2
        BRp RESTAR_A_R0
        BRz MCD_LISTO
        BRnzp R0_MENOR_R1

MCD_LISTO
        ST R0, RESULTADO_MCD

; 5. Cociente Q = menor / MCD por restas sucesivas (R4 tiene el menor!).
        AND R2, R2, #0          ; R2 = Q = 0
        NOT R3, R0
        ADD R3, R3, #1          ; R3 = -MCD
DIV_LOOP
        ADD R2, R2, #1          ; Q++
        ADD R4, R4, R3          ; R4 = R4 - MCD
        BRp DIV_LOOP            ; Termina en Q vueltas

; 6. OPTIMIZACION C: MCM = Q * mayor con corte temprano por Overflow (Early Exit).
        AND R0, R0, #0          ; R0 = acumulador del MCM
MUL_LOOP
        ADD R0, R0, R5          ; R0 = R0 + mayor
        BRn MCM_OVERFLOW        ; Si R0 < 0 (supero 32767), corta el bucle!
        ADD R2, R2, #-1         ; Q--
        BRp MUL_LOOP
        BRnzp GUARDAR_MCM

MCM_OVERFLOW
        LD R0, NEG_32768        ; Carga x8000 (-32768) como aviso de overflow
GUARDAR_MCM
        ST R0, RESULTADO_MCM
        BRnzp MOSTRAR_RESULTADOS

A_ES_CERO
        ADD R0, R1, #0
B_ES_CERO
        ST R0, RESULTADO_MCD
        AND R0, R0, #0
        ST R0, RESULTADO_MCM

MOSTRAR_RESULTADOS
        LEA R0, TEXTO_MCD
        PUTS
        LD R0, RESULTADO_MCD
        JSR IMPRIMIR_ENTERO
        LEA R0, SALTO_LINEA
        PUTS
        LEA R0, TEXTO_MCM
        PUTS
        LD R0, RESULTADO_MCM
        JSR IMPRIMIR_ENTERO
        LEA R0, SALTO_LINEA
        PUTS
        HALT

; --- Subrutinas de E/S ---
LEER_ENTERO
        ADD R6, R6, #-1
        STR R7, R6, #0
        AND R1, R1, #0
        AND R4, R4, #0
        AND R5, R5, #0
LEER_CARACTER
        GETC
        OUT
        LD R2, NEG_LF
        ADD R2, R0, R2
        BRz FIN_LECTURA
        LD R2, NEG_CR
        ADD R2, R0, R2
        BRz FIN_LECTURA
        LD R2, NEG_MENOS
        ADD R2, R0, R2
        BRnp REVISAR_DIGITO
        ADD R5, R5, #0
        BRz SIGNO_NEGATIVO
        BRnzp LEER_CARACTER
SIGNO_NEGATIVO
        ADD R4, R4, #-1
        ADD R5, R5, #1
        BRnzp LEER_CARACTER
REVISAR_DIGITO
        LD R2, NEG_CERO
        ADD R0, R0, R2
        BRn LEER_CARACTER
        ADD R2, R0, #-10
        BRzp LEER_CARACTER
        ADD R5, R5, #1
        ADD R2, R1, R1
        ADD R3, R2, R2
        ADD R3, R3, R3
        ADD R1, R2, R3
        ADD R1, R1, R0
        BRnzp LEER_CARACTER
FIN_LECTURA
        ADD R0, R1, #0
        ADD R4, R4, #0
        BRzp FIN_LEER_ENTERO
        NOT R0, R0
        ADD R0, R0, #1
FIN_LEER_ENTERO
        LDR R7, R6, #0
        ADD R6, R6, #1
        RET

IMPRIMIR_ENTERO
        ADD R6, R6, #-1
        STR R7, R6, #0
        ADD R1, R0, #0
        BRzp PREPARAR_DIGITOS
        LD R0, ASCII_MENOS
        OUT
        ADD R1, R1, #0
        LD R2, NEG_32768
        ADD R2, R1, R2
        BRnp ABSOLUTO_NORMAL
        LEA R0, TEXTO_MIN_INT
        PUTS
        BRnzp FIN_IMPRESION
ABSOLUTO_NORMAL
        NOT R1, R1
        ADD R1, R1, #1
PREPARAR_DIGITOS
        AND R2, R2, #0
        LEA R3, POTENCIAS
IMPRIMIR_POSICION
        LDR R4, R3, #0
        BRz REVISAR_CERO
        AND R5, R5, #0
RESTAR_POTENCIA
        NOT R0, R4
        ADD R0, R0, #1
        ADD R0, R1, R0
        BRn DIGITO_LISTO
        ADD R1, R0, #0
        ADD R5, R5, #1
        BRnzp RESTAR_POTENCIA
DIGITO_LISTO
        ADD R2, R2, #0
        BRp MOSTRAR_DIGITO
        ADD R5, R5, #0
        BRz SIGUIENTE_POTENCIA
        ADD R2, R2, #1
MOSTRAR_DIGITO
        LD R0, ASCII_CERO
        ADD R0, R0, R5
        OUT
SIGUIENTE_POTENCIA
        ADD R3, R3, #1
        BRnzp IMPRIMIR_POSICION
REVISAR_CERO
        ADD R2, R2, #0
        BRp FIN_IMPRESION
        LD R0, ASCII_CERO
        OUT
FIN_IMPRESION
        LDR R7, R6, #0
        ADD R6, R6, #1
        RET

PROMPT_A       .STRINGZ "Ingresa el primer numero: "
PROMPT_B       .STRINGZ "Ingresa el segundo numero: "
TEXTO_MCD      .STRINGZ "MCD = "
TEXTO_MCM      .STRINGZ "MCM = "
SALTO_LINEA    .FILL x000A
               .FILL x0000
TEXTO_MIN_INT  .STRINGZ "32768"
POTENCIAS      .FILL #10000
               .FILL #1000
               .FILL #100
               .FILL #10
               .FILL #1
               .FILL #0
DATO_A         .FILL #0
DATO_B         .FILL #0
RESULTADO_MCD  .FILL #0
RESULTADO_MCM  .FILL #0
STACK_BASE     .FILL xFDFF
NEG_LF         .FILL #-10
NEG_CR         .FILL #-13
NEG_MENOS      .FILL #-45
NEG_CERO       .FILL #-48
NEG_32768      .FILL x8000
ASCII_MENOS    .FILL #45
ASCII_CERO     .FILL #48
.END