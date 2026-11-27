; =====================================================================
;  MULTIPLICACION POR CORDIC (modo lineal) EN Q7.8 - PROGRAMA COMPLETO PARA LC-3
;  equivale a CORDIC_multiplicacion_Q78.c
; =====================================================================
;
;  COMO SE USA
;    el programa pide los dos factores por teclado y muestra el producto.
;    los factores se escriben ya como ENTEROS en Q7.8 (valor_real * 256), en decimal, y se termina con Enter:
;         2.0   -> 512         3.0   -> 768         -2.5 -> -640         3.25 -> 832
;    resultado: tambien un entero en Q7.8 (dividir por 256 para el valor real): 512 x 768 -> 1536 (= 6.0)
;    rango de entrada: -32767 a 32767 (se ignoran las letras y los digitos que se pasen de 32767)
;    si |a*b| no entra en Q7.8 (maximo 32767 = 127.996) se muestra DESBORDAMIENTO
;
;  ESTRUCTURA DEL ARCHIVO
;    MAIN             pide los datos con PUTS, los lee con LEER_ENTERO, llama a CORDIC_MUL y muestra el resultado
;    LEER_ENTERO      lee un entero decimal con signo por teclado (GETC + OUT para mostrar lo que se escribe)
;    IMPRIMIR_ENTERO  muestra un entero de 16 bits con signo en decimal
;    NUEVA_LINEA      salto de linea
;    CORDIC_MUL       el algoritmo (lazo de CORDIC)
;
;  FORMATO: Q7.8 en complemento a 2 (16 bits): valor_real = palabra / 256
;
;  CONVENCION DE LLAMADO DE LAS SUBRUTINAS
;  - un valor de 16 bits se pasa por registro.
;  - un valor de 32 bits (int32_par) son 2 palabras seguidas en memoria:
;        [direccion]     = hi  (parte alta)
;        [direccion + 1] = lo  (parte baja)
;    y se pasa por DIRECCION (como un puntero en C).
;  - parametros en R0 y R1. El valor de retorno (si hay) vuelve en R0.
;  - cada subrutina PRESERVA R1..R6 (guarda en memoria los que usa y los restaura antes del RET).
;    R0 solo cambia si la subrutina devuelve un valor. (CORDIC_MUL devuelve el resultado en R0, el estado en R1 y preserva R2..R6)
;  - R7 lo pisa JSR y tambien TRAP (GETC, OUT, PUTS): las subrutinas que los usan guardan R7 y lo restauran.
;  - las zonas de guardado son fijas (ST/LD), por lo tanto NO son recursivas.
;  - al volver, los codigos de condicion (N/Z/P) no tienen un significado definido.
; =====================================================================

        .ORIG x3000

; ---------------------------------------------------------------------
;  MAIN
;    A_Q8, B_Q8 : factores leidos (enteros Q7.8)
;    ESTADO     : 0 = ok / 1 = desbordamiento / 2 = b invalido
; ---------------------------------------------------------------------
MAIN
        LEA  R0, MSG_TITULO
        PUTS
        JSR  NUEVA_LINEA

        LEA  R0, MSG_A          ; "Primer factor..."
        PUTS
        JSR  LEER_ENTERO        ; R0 = valor leido
        ST   R0, A_Q8

        LEA  R0, MSG_B          ; "Segundo factor..."
        PUTS
        JSR  LEER_ENTERO
        ST   R0, B_Q8

        LD   R0, A_Q8
        LD   R1, B_Q8
        JSR  CORDIC_MUL         ; R1 = estado, R0 = resultado Q7.8
        ST   R1, ESTADO
        ST   R0, RESULTADO_Q78

        LD   R0, ESTADO
        BRz  MAIN_OK
        ADD  R0, R0, #-1
        BRz  MAIN_DESBORDA

        LEA  R0, MSG_BINV       ; estado 2
        PUTS
        JSR  NUEVA_LINEA
        BRnzp FIN
MAIN_DESBORDA
        LEA  R0, MSG_DESB       ; estado 1
        PUTS
        JSR  NUEVA_LINEA
        BRnzp FIN
MAIN_OK
        LEA  R0, MSG_RES        ; "Resultado en formato Q7.8: "
        PUTS
        LD   R0, RESULTADO_Q78
        JSR  IMPRIMIR_ENTERO
        JSR  NUEVA_LINEA
FIN     HALT

A_Q8          .BLKW #1
B_Q8          .BLKW #1
ESTADO        .BLKW #1
RESULTADO_Q78 .BLKW #1

MSG_TITULO .STRINGZ "--- MULTIPLICACION POR CORDIC ---"
MSG_A      .STRINGZ "Primer factor (entero Q7.8): "
MSG_B      .STRINGZ "Segundo factor (entero Q7.8): "
MSG_RES    .STRINGZ "Resultado en formato Q7.8: "
MSG_DESB   .STRINGZ "DESBORDAMIENTO: no entra en Q7.8"
MSG_BINV   .STRINGZ "Factor invalido"

; ---------------------------------------------------------------------
;  NUEVA_LINEA : muestra un salto de linea (no modifica ningun registro)
; ---------------------------------------------------------------------
NUEVA_LINEA
        ST   R0, NL_R0
        ST   R7, NL_R7
        LD   R0, NL_LF
        OUT
        LD   R0, NL_R0
        LD   R7, NL_R7
        RET
NL_LF   .FILL x0A
NL_R0   .BLKW #1
NL_R7   .BLKW #1

; ---------------------------------------------------------------------
;  LEER_ENTERO : lee por teclado un entero decimal con signo y lo devuelve en R0
;    - GETC no muestra lo que se escribe, asi que cada caracter valido se muestra con OUT
;    - un '-' solo vale al principio; se ignoran las letras y los digitos que harian pasar el valor de 32767
;    - se termina con Enter (LF o CR)
;    - sin ningun digito el valor es 0
;  el valor se arma en R1 (magnitud) multiplicando por 10 sin multiplicar: 10m = 8m + 2m (duplicaciones)
;    R1 = magnitud   R2 = negativo (0/1)   R3 = cantidad de digitos   R4,R5,R6 = auxiliares
; ---------------------------------------------------------------------
LEER_ENTERO
        ST   R1, LE_R1
        ST   R2, LE_R2
        ST   R3, LE_R3
        ST   R4, LE_R4
        ST   R5, LE_R5
        ST   R6, LE_R6
        ST   R7, LE_R7

        AND  R1, R1, #0         ; magnitud = 0
        AND  R2, R2, #0         ; negativo = 0
        AND  R3, R3, #0         ; digitos = 0
LE_LAZO
        GETC                    ; R0 = caracter
        ADD  R4, R0, #-10       ; Enter (LF)?
        BRz  LE_FIN
        ADD  R4, R0, #-13       ; Enter (CR)?
        BRz  LE_FIN
        LD   R4, LE_NEG_MENOS   ; -45 = -'-'
        ADD  R4, R4, R0
        BRnp LE_DIGITO          ; no es '-'
        ADD  R3, R3, #0         ; el '-' solo vale antes de los digitos
        BRp  LE_LAZO
        ADD  R2, R2, #0         ; y una sola vez
        BRp  LE_LAZO
        OUT                     ; muestra el '-'
        ADD  R2, R2, #1         ; negativo = 1
        BRnzp LE_LAZO
LE_DIGITO
        LD   R4, LE_NEG_CERO    ; -48 = -'0'
        ADD  R4, R4, R0         ; R4 = caracter - '0'
        BRn  LE_LAZO            ; menor que '0': se ignora
        ADD  R5, R4, #-9
        BRp  LE_LAZO            ; mayor que '9': se ignora
        LD   R5, LE_LIM         ; -3277
        ADD  R5, R5, R1
        BRzp LE_LAZO            ; magnitud >= 3277: otro digito pasaria de 32767, se ignora
        ADD  R6, R1, R1         ; 2m
        ADD  R5, R6, R6         ; 4m
        ADD  R5, R5, R5         ; 8m
        ADD  R5, R5, R6         ; 10m
        ADD  R5, R5, R4         ; 10m + digito
        BRn  LE_LAZO            ; paso de 32767: se ignora
        ADD  R1, R5, #0         ; magnitud = nuevo valor
        OUT                     ; muestra el digito
        ADD  R3, R3, #1
        BRnzp LE_LAZO
LE_FIN
        LD   R0, LE_LF
        OUT                     ; salto de linea en pantalla
        ADD  R2, R2, #0
        BRz  LE_POSITIVO
        NOT  R1, R1
        ADD  R1, R1, #1         ; valor = -magnitud
LE_POSITIVO
        ADD  R0, R1, #0         ; devuelve el valor en R0

        LD   R1, LE_R1
        LD   R2, LE_R2
        LD   R3, LE_R3
        LD   R4, LE_R4
        LD   R5, LE_R5
        LD   R6, LE_R6
        LD   R7, LE_R7
        RET
LE_NEG_MENOS .FILL #-45
LE_NEG_CERO  .FILL #-48
LE_LIM       .FILL #-3277
LE_LF        .FILL x0A
LE_R1   .BLKW #1
LE_R2   .BLKW #1
LE_R3   .BLKW #1
LE_R4   .BLKW #1
LE_R5   .BLKW #1
LE_R6   .BLKW #1
LE_R7   .BLKW #1

; ---------------------------------------------------------------------
;  IMPRIMIR_ENTERO : muestra el entero con signo de R0 en decimal (sin ceros a la izquierda)
;  no hay division, asi que cada digito se obtiene restando potencias de 10 (10000, 1000, 100, 10, 1)
;  se trabaja con n = -|valor| (negativo o cero) para que -32768 tambien funcione:
;    mientras n + potencia <= 0 se hace n = n + potencia y el digito sube 1
;    R1 = n   R2 = puntero a la potencia actual   R3 = posiciones que faltan   R4 = ya se imprimio algo
;    R5 = potencia   R6 = digito
;  no modifica ningun registro
; ---------------------------------------------------------------------
IMPRIMIR_ENTERO
        ST   R0, IE_R0
        ST   R1, IE_R1
        ST   R2, IE_R2
        ST   R3, IE_R3
        ST   R4, IE_R4
        ST   R5, IE_R5
        ST   R6, IE_R6
        ST   R7, IE_R7

        ADD  R1, R0, #0
        BRzp IE_POSITIVO
        LD   R0, IE_MENOS       ; negativo: se muestra '-' y n ya es negativo
        OUT
        BRnzp IE_INICIO
IE_POSITIVO
        NOT  R1, R1
        ADD  R1, R1, #1         ; n = -valor
IE_INICIO
        LEA  R2, IE_POTENCIAS
        AND  R3, R3, #0
        ADD  R3, R3, #5         ; 5 posiciones
        AND  R4, R4, #0         ; todavia no se imprimio ningun digito
IE_POSICION
        LDR  R5, R2, #0         ; potencia
        AND  R6, R6, #0         ; digito = 0
IE_RESTAR
        ADD  R0, R1, R5         ; n + potencia
        BRp  IE_SALE            ; si es > 0 ya no cabe otra vez
        ADD  R1, R0, #0         ; n = n + potencia
        ADD  R6, R6, #1         ; digito + 1
        BRnzp IE_RESTAR
IE_SALE
        ADD  R6, R6, #0         ; se imprime si el digito no es 0,
        BRp  IE_IMPRIME
        ADD  R4, R4, #0         ; o si ya se imprimio algo (para no perder ceros del medio),
        BRp  IE_IMPRIME
        ADD  R0, R3, #-1        ; o si es la ultima posicion (para que el 0 se muestre)
        BRz  IE_IMPRIME
        BRnzp IE_SIGUE
IE_IMPRIME
        LD   R0, IE_CERO        ; '0'
        ADD  R0, R0, R6         ; '0' + digito
        OUT
        AND  R4, R4, #0
        ADD  R4, R4, #1         ; ya se imprimio algo
IE_SIGUE
        ADD  R2, R2, #2         ; siguiente potencia
        ADD  R3, R3, #-1
        BRp  IE_POSICION

        LD   R0, IE_R0
        LD   R1, IE_R1
        LD   R2, IE_R2
        LD   R3, IE_R3
        LD   R4, IE_R4
        LD   R5, IE_R5
        LD   R6, IE_R6
        LD   R7, IE_R7
        RET
IE_CERO  .FILL x30
IE_MENOS .FILL x2D
IE_POTENCIAS .FILL #10000
             .FILL #1000
             .FILL #100
             .FILL #10
             .FILL #1
IE_R0   .BLKW #1
IE_R1   .BLKW #1
IE_R2   .BLKW #1
IE_R3   .BLKW #1
IE_R4   .BLKW #1
IE_R5   .BLKW #1
IE_R6   .BLKW #1
IE_R7   .BLKW #1

; CORDIC lineal. R0 y R1 contienen los factores Q7.8. Devuelve el
; producto redondeado en R0 y el estado en R1 (0 válido, 1 desbordamiento,
; 2 segundo factor inválido). Preserva R2..R7.
; R1:R0 = acumulador, R3:R2 = factor desplazado, R4 = residuo,
; R5 = peso de la iteración y R6 = cantidad de iteraciones.
CORDIC_MUL
        ST   R2, CM_R2
        ST   R3, CM_R3
        ST   R4, CM_R4
        ST   R5, CM_R5
        ST   R6, CM_R6

        ADD  R4, R1, #0
        LD   R5, CM_B_MIN
        ADD  R5, R5, R4
        BRz  CM_B_INVALIDO

        SHL  R2, R0, #14
        ASR  R3, R0, #2
        AND  R0, R0, #0
        AND  R1, R1, #0
        AND  R6, R6, #0
        LD   R5, CM_PESO_INICIAL

CM_LAZO
        ADD  R4, R4, #0
        BRz  CM_FIN_LAZO
        BRn  CM_Z_NEG
        SUB  R4, R4, R5
        ADD  R0, R0, R2
        ADC  R1, R1, R3
        BRnzp CM_SIGUE
CM_Z_NEG
        ADD  R4, R4, R5
        SUB  R0, R0, R2
        SBC  R1, R1, R3
CM_SIGUE
        ASRW R2, R2, #1
        ADD  R6, R6, #1
        LSR  R5, R5, #1
        BRp  CM_LAZO

CM_FIN_LAZO
        ST   R6, CM_ITER
        ST   R1, CM_Y
        ST   R0, CM_Y_BAJA

        ; Redondeo original en Q7.8: (acumulador + 128) >> 8.
        LD   R2, CM_MEDIO
        AND  R3, R3, #0
        ADD  R0, R0, R2
        ADC  R1, R1, R3
        ASRW R0, R0, #8
        ASR  R2, R0, #15
        SUB  R2, R1, R2
        BRnp CM_DESBORDA
        ST   R0, CM_RES
        AND  R1, R1, #0
        BRnzp CM_FIN

CM_DESBORDA
        AND  R0, R0, #0
        ADD  R1, R0, #1
        BRnzp CM_FIN
CM_B_INVALIDO
        AND  R0, R0, #0
        ADD  R1, R0, #2
        ST   R0, CM_ITER
CM_FIN
        LD   R2, CM_R2
        LD   R3, CM_R3
        LD   R4, CM_R4
        LD   R5, CM_R5
        LD   R6, CM_R6
        RET

CM_PESO_INICIAL .FILL #16384
CM_B_MIN        .FILL x8000
CM_MEDIO        .FILL #128
CM_Y            .BLKW #1
CM_Y_BAJA       .BLKW #1
CM_RES          .BLKW #1
CM_ITER         .BLKW #1
CM_R2           .BLKW #1
CM_R3           .BLKW #1
CM_R4           .BLKW #1
CM_R5           .BLKW #1
CM_R6           .BLKW #1

        .END
