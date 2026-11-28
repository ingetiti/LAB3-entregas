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
;    subrutinas       DESP_DER_LOG, DESP_DER_ARIT, SUMA32, RESTA32, DESP_DER_32, PREPARAR_X, REDUCIR_Q78
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
        ADD  R2, R2, #1         ; siguiente potencia
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

; ---------------------------------------------------------------------
;  CORDIC_MUL : a_q8 * b_q8 con CORDIC lineal
;     entrada : R0 = a_q8     R1 = b_q8
;     salida  : R0 = resultado en Q7.8 (solo valido si R1 = 0; en otro caso vale 0)
;               R1 = estado:  0 = ok / 1 = desbordamiento (|a*b| > 127.996) / 2 = b_q8 invalido (-32768)
;     deja ademas en memoria: CM_Y    = acumulador de 32 bits (Q16), que vale a_q8 * b_q8
;                             CM_ITER = cantidad de iteraciones realizadas
;     preserva R2..R6
;
;  equivale al C:   z = b_q8;  y = 0;  current_x = a_q8 * 2^14;
;                   for (i = 0; i < 15; i++) { if (z == 0) break;
;                        if (z > 0) { z -= current_z; y += current_x; } else { z += current_z; y -= current_x; }
;                        current_x /= 2; }
;    R2 = z (multiplicador que se va vaciando)   R3 = current_z (peso de la iteracion) / auxiliar
;    R5 = i (iteracion)                          R6 = puntero a CM_TABLA_Z (peso actual)
; ---------------------------------------------------------------------
CORDIC_MUL
        ST   R2, CM_R2
        ST   R3, CM_R3
        ST   R4, CM_R4
        ST   R5, CM_R5
        ST   R6, CM_R6
        ST   R7, CM_R7

        ADD  R2, R1, #0         ; z = b_q8 (el multiplicador que voy a vaciar)
        LD   R3, CM_B_MIN       ; 0x8000
        ADD  R3, R3, R2         ; 0x8000 + 0x8000 = 0 solo si b_q8 == -32768
        BRz  CM_B_INVALIDO

        ; se inicializa el acumulador en 0
        LEA  R4, CM_Y
        AND  R3, R3, #0
        STR  R3, R4, #0         ; y.hi = 0
        STR  R3, R4, #1         ; y.lo = 0

        ; current_x arranca en a_q8 * 2^14 para no perder decimales al dividir por 2 (R0 = a_q8)
        LEA  R1, CM_X
        JSR  PREPARAR_X

        AND  R5, R5, #0         ; i = 0
        LEA  R6, CM_TABLA_Z     ; R6 apunta a tabla_z[i]
CM_LAZO
        ADD  R2, R2, #0         ; if (z == 0) break;
        BRz  CM_FIN_LAZO
        LDR  R3, R6, #0         ; current_z = tabla_z[i]
        ADD  R2, R2, #0         ; z > 0 o z < 0 (ya se sabe que no es 0)
        BRn  CM_Z_NEG

        NOT  R3, R3             ; z > 0:  z = z - current_z
        ADD  R3, R3, #1
        ADD  R2, R2, R3
        LEA  R0, CM_Y
        LEA  R1, CM_X
        JSR  SUMA32             ;         y = y + current_x
        BRnzp CM_SIGUE
CM_Z_NEG
        ADD  R2, R2, R3         ; z < 0:  z = z + current_z
        LEA  R0, CM_Y
        LEA  R1, CM_X
        JSR  RESTA32            ;         y = y - current_x
CM_SIGUE
        LEA  R0, CM_X
        JSR  DESP_DER_32        ; current_x = current_x / 2
        ADD  R6, R6, #1         ; siguiente peso de la tabla
        ADD  R5, R5, #1         ; i = i + 1
        ADD  R3, R5, #-15
        BRn  CM_LAZO            ; mientras i < 15
CM_FIN_LAZO
        ST   R5, CM_ITER        ; iteraciones realizadas

        ; y (Q16) -> Q7.8 con redondeo
        LEA  R0, CM_Y
        LEA  R1, CM_RES
        JSR  REDUCIR_Q78        ; R0 = 1 si hay desbordamiento
        ADD  R1, R0, #0
        BRp  CM_DESBORDA
        LD   R0, CM_RES         ; resultado Q7.8
        BRnzp CM_FIN
CM_DESBORDA
        AND  R0, R0, #0         ; sin resultado valido (R1 ya vale 1)
        BRnzp CM_FIN
CM_B_INVALIDO
        AND  R1, R1, #0
        ADD  R1, R1, #2         ; estado = 2
        AND  R0, R0, #0
        ST   R0, CM_ITER        ; 0 iteraciones
CM_FIN
        LD   R2, CM_R2
        LD   R3, CM_R3
        LD   R4, CM_R4
        LD   R5, CM_R5
        LD   R6, CM_R6
        LD   R7, CM_R7
        RET

; pesos de cada iteracion: 2^14, 2^13, ..., 2^0 (reemplaza a "current_z /= 2": el LC-3 no puede dividir)
CM_TABLA_Z .FILL #16384
           .FILL #8192
           .FILL #4096
           .FILL #2048
           .FILL #1024
           .FILL #512
           .FILL #256
           .FILL #128
           .FILL #64
           .FILL #32
           .FILL #16
           .FILL #8
           .FILL #4
           .FILL #2
           .FILL #1
CM_B_MIN .FILL x8000
CM_Y     .BLKW #2                ; acumulador y (32 bits, Q16)
CM_X     .BLKW #2                ; current_x (32 bits)
CM_RES   .BLKW #1                ; resultado Q7.8 que escribe REDUCIR_Q78
CM_ITER  .BLKW #1
CM_R2    .BLKW #1
CM_R3    .BLKW #1
CM_R4    .BLKW #1
CM_R5    .BLKW #1
CM_R6    .BLKW #1
CM_R7    .BLKW #1

; ---------------------------------------------------------------------
;  DESP_DER_LOG : R0 = R0 >> 1, rellenando con 0 a la izquierda
;  no hay instruccion de desplazamiento, asi que se copia bit por bit:
;    R1 = m  mascara que apunta al bit que se lee   (2, 4, 8, ..., 0x8000)
;    R2 = r  bit de destino donde se escribe        (1, 2, 4, ..., 0x4000)
;    R3 = res
;  m y r se corren hacia la izquierda sumandose a si mismas
; ---------------------------------------------------------------------
DESP_DER_LOG
        ST   R1, DDL_R1
        ST   R2, DDL_R2
        ST   R3, DDL_R3
        ST   R4, DDL_R4
        ST   R5, DDL_R5

        AND  R3, R3, #0         ; res = 0
        AND  R1, R1, #0
        ADD  R1, R1, #2         ; m = 2
        AND  R2, R2, #0
        ADD  R2, R2, #1         ; r = 1
        AND  R4, R4, #0
        ADD  R4, R4, #15        ; k = 15 vueltas
DDL_LAZO
        AND  R5, R0, R1         ; x & m
        BRz  DDL_SIGUE          ; ese bit era 0
        ADD  R3, R3, R2         ; res = res + r
DDL_SIGUE
        ADD  R1, R1, R1         ; m = m + m
        ADD  R2, R2, R2         ; r = r + r
        ADD  R4, R4, #-1
        BRp  DDL_LAZO

        ADD  R0, R3, #0         ; devuelve res

        LD   R1, DDL_R1
        LD   R2, DDL_R2
        LD   R3, DDL_R3
        LD   R4, DDL_R4
        LD   R5, DDL_R5
        RET
DDL_R1  .BLKW #1
DDL_R2  .BLKW #1
DDL_R3  .BLKW #1
DDL_R4  .BLKW #1
DDL_R5  .BLKW #1

; ---------------------------------------------------------------------
;  DESP_DER_ARIT : R0 = R0 >> 1, copiando el signo (los negativos siguen negativos)
; ---------------------------------------------------------------------
DESP_DER_ARIT
        ST   R1, DDA_R1
        ST   R2, DDA_R2
        ST   R7, DDA_R7

        ADD  R2, R0, #0         ; se guarda x para ver su signo despues
        JSR  DESP_DER_LOG       ; R0 = x >> 1 (logico)
        ADD  R2, R2, #0         ; codigos de condicion segun el signo de x
        BRzp DDA_FIN            ; x >= 0: listo
        LD   R1, DDA_BIT15
        ADD  R0, R0, R1         ; res = res - 32768 (prende el bit 15)
DDA_FIN
        LD   R1, DDA_R1
        LD   R2, DDA_R2
        LD   R7, DDA_R7
        RET
DDA_BIT15 .FILL x8000
DDA_R1  .BLKW #1
DDA_R2  .BLKW #1
DDA_R7  .BLKW #1

; ---------------------------------------------------------------------
;  SUMA32 : [R0] = [R0] + [R1]   (cada uno es un par hi/lo de 32 bits)
;  el LC-3 no avisa cuando la suma de los lo se pasa de 16 bits (acarreo),
;  asi que se deduce mirando los signos:
;    - los dos lo "grandes" (bit 15 en 1)                     -> hay acarreo
;    - uno grande, el otro no, y el resultado quedo "chico"   -> hay acarreo
;    - cualquier otro caso                                    -> no hay acarreo
;    R2,R3 = a.lo, b.lo   R4 = lo (suma)   R5 = acarreo
; ---------------------------------------------------------------------
SUMA32
        ST   R2, S32_R2
        ST   R3, S32_R3
        ST   R4, S32_R4
        ST   R5, S32_R5

        LDR  R2, R0, #1         ; a.lo
        LDR  R3, R1, #1         ; b.lo
        ADD  R4, R2, R3         ; lo = a.lo + b.lo
        AND  R5, R5, #0         ; acarreo = 0

        ADD  R2, R2, #0         ; es a.lo "grande"?
        BRn  S32_A_GRANDE
        ; a.lo chico
        ADD  R3, R3, #0
        BRzp S32_SUMA_HI        ; b.lo tambien chico: no hay acarreo
        ADD  R4, R4, #0         ; b.lo grande: hay acarreo si lo quedo chico (>= 0)
        BRn  S32_SUMA_HI
        ADD  R5, R5, #1
        BRnzp S32_SUMA_HI
S32_A_GRANDE
        ADD  R3, R3, #0
        BRn  S32_ACARREO        ; los dos grandes: hay acarreo
        ADD  R4, R4, #0         ; a grande y b chico: hay acarreo si lo quedo chico (>= 0)
        BRn  S32_SUMA_HI
S32_ACARREO
        ADD  R5, R5, #1         ; acarreo = 1
S32_SUMA_HI
        LDR  R2, R0, #0         ; a.hi
        LDR  R3, R1, #0         ; b.hi
        ADD  R2, R2, R3
        ADD  R2, R2, R5         ; a.hi = a.hi + b.hi + acarreo
        STR  R2, R0, #0
        STR  R4, R0, #1         ; a.lo = lo

        LD   R2, S32_R2
        LD   R3, S32_R3
        LD   R4, S32_R4
        LD   R5, S32_R5
        RET
S32_R2  .BLKW #1
S32_R3  .BLKW #1
S32_R4  .BLKW #1
S32_R5  .BLKW #1

; ---------------------------------------------------------------------
;  RESTA32 : [R0] = [R0] - [R1]
;  restar es sumar el opuesto; el opuesto en complemento a 2 es invertir los bits (NOT) y sumar 1.
;  se arma el opuesto de b en la zona REST_OPUESTO y se llama a SUMA32
; ---------------------------------------------------------------------
RESTA32
        ST   R1, REST_R1
        ST   R2, REST_R2
        ST   R3, REST_R3
        ST   R7, REST_R7

        LDR  R2, R1, #0         ; b.hi
        NOT  R2, R2             ; ~b.hi
        LDR  R3, R1, #1         ; b.lo
        NOT  R3, R3             ; ~b.lo
        ADD  R3, R3, #1         ; ~b.lo + 1
        BRnp REST_ARMAR          ; si lo no dio 0 no hubo acarreo hacia hi
        ADD  R2, R2, #1         ; el +1 desbordo lo: se lleva 1 a hi
REST_ARMAR
        LEA  R1, REST_OPUESTO
        STR  R2, R1, #0
        STR  R3, R1, #1
        JSR  SUMA32             ; a = a + (-b)

        LD   R1, REST_R1
        LD   R2, REST_R2
        LD   R3, REST_R3
        LD   R7, REST_R7
        RET
REST_OPUESTO .BLKW #2
REST_R1  .BLKW #1
REST_R2  .BLKW #1
REST_R3  .BLKW #1
REST_R7  .BLKW #1

; ---------------------------------------------------------------------
;  DESP_DER_32 : v = v / 2 sobre un par hi/lo (corre 1 bit a la derecha manteniendo el signo)
;  el bit mas bajo de hi pasa a ser el bit mas alto de lo
;    R3 = &v   R2 = bit mas bajo de hi
; ---------------------------------------------------------------------
DESP_DER_32
        ST   R1, D32_R1
        ST   R2, D32_R2
        ST   R3, D32_R3
        ST   R7, D32_R7

        ADD  R3, R0, #0         ; R3 = &v (R0 se va a usar para pasar valores)
        LDR  R1, R3, #0         ; v.hi
        AND  R2, R1, #1         ; bit_bajo_hi (antes de modificar hi)
        LDR  R0, R3, #1         ; v.lo
        JSR  DESP_DER_LOG       ; R0 = v.lo >> 1 (logico)
        ADD  R2, R2, #0
        BRz  D32_SIN_BIT
        LD   R1, D32_BIT15
        ADD  R0, R0, R1         ; lo recibe el bit en la posicion 15
D32_SIN_BIT
        STR  R0, R3, #1         ; v.lo
        LDR  R0, R3, #0         ; v.hi
        JSR  DESP_DER_ARIT      ; R0 = v.hi >> 1 (aritmetico)
        STR  R0, R3, #0         ; v.hi
        ADD  R0, R3, #0         ; R0 vuelve a ser &v

        LD   R1, D32_R1
        LD   R2, D32_R2
        LD   R3, D32_R3
        LD   R7, D32_R7
        RET
D32_BIT15 .FILL x8000
D32_R1  .BLKW #1
D32_R2  .BLKW #1
D32_R3  .BLKW #1
D32_R7  .BLKW #1

; ---------------------------------------------------------------------
;  PREPARAR_X : [R1] = R0 * 2^14   (R0 = a_q8, R1 = &x)  sin multiplicar
;  como 2^14 = 2^16 / 4, el numero de 32 bits queda:
;     hi = a_q8 / 4 (con signo)      lo = (a_q8 & 3) * 2^14
;    R2 = resto = a_q8 & 3 (se duplica 14 veces)   R3 = contador
; ---------------------------------------------------------------------
PREPARAR_X
        ST   R0, PX_R0
        ST   R2, PX_R2
        ST   R3, PX_R3
        ST   R7, PX_R7

        AND  R2, R0, #3         ; resto = a_q8 & 3
        JSR  DESP_DER_ARIT      ; R0 = a_q8 >> 1
        JSR  DESP_DER_ARIT      ; R0 = a_q8 >> 2
        STR  R0, R1, #0         ; x.hi
        AND  R3, R3, #0
        ADD  R3, R3, #14        ; 14 duplicaciones
PX_LAZO
        ADD  R2, R2, R2         ; resto = resto + resto
        ADD  R3, R3, #-1
        BRp  PX_LAZO
        STR  R2, R1, #1         ; x.lo

        LD   R0, PX_R0
        LD   R2, PX_R2
        LD   R3, PX_R3
        LD   R7, PX_R7
        RET
PX_R0   .BLKW #1
PX_R2   .BLKW #1
PX_R3   .BLKW #1
PX_R7   .BLKW #1

; ---------------------------------------------------------------------
;  REDUCIR_Q78 : pasa y (Q16, 32 bits) a Q7.8 de 16 bits con redondeo: (y + 128) >> 8
;     entrada : R0 = &y    R1 = &resultado_q78
;     salida  : R0 = 0 si esta bien (el resultado queda en [R1])
;               R0 = 1 si no entra en 16 bits (desbordamiento; no se escribe [R1])
;  y no se modifica: se trabaja sobre una copia
;    R3 = chequeo / contador   R4 = parte_baja   R5 = lo y despues hi   R6 = &resultado
; ---------------------------------------------------------------------
REDUCIR_Q78
        ST   R1, RQ_R1
        ST   R2, RQ_R2
        ST   R3, RQ_R3
        ST   R4, RQ_R4
        ST   R5, RQ_R5
        ST   R6, RQ_R6
        ST   R7, RQ_R7

        ; copia = y
        LEA  R2, RQ_COPIA
        LDR  R3, R0, #0
        STR  R3, R2, #0
        LDR  R3, R0, #1
        STR  R3, R2, #1

        ; copia = copia + 128 (medio escalon de los 256 que se descartan, para que redondee y no corte)
        ADD  R0, R2, #0         ; R0 = &copia
        LEA  R1, RQ_MEDIO       ; par (0 : 128)
        JSR  SUMA32

        ; entra en 16 bits solo si hi esta entre -128 y 127; sumando 128 queda entre 0 y 255
        ; (se comprueba con un AND contra 0xFF00: tiene que dar 0)
        LDR  R3, R0, #0         ; copia.hi
        LD   R4, RQ_128
        ADD  R3, R3, R4         ; chequeo = copia.hi + 128
        LD   R4, RQ_FF00
        AND  R3, R3, R4
        BRz  RQ_SIN_DESB
        AND  R0, R0, #0
        ADD  R0, R0, #1         ; desbordamiento = 1
        BRnzp RQ_FIN

RQ_SIN_DESB
        ; parte_baja = byte alto de copia.lo: se lee el signo de lo y se duplica lo, 8 veces
        AND  R4, R4, #0         ; parte_baja = 0
        LDR  R5, R0, #1         ; copia.lo
        AND  R3, R3, #0
        ADD  R3, R3, #8
RQ_LAZO_LO
        ADD  R4, R4, R4         ; parte_baja = parte_baja + parte_baja
        ADD  R5, R5, #0
        BRzp RQ_LO_SIGUE        ; bit 15 en 0
        ADD  R4, R4, #1
RQ_LO_SIGUE
        ADD  R5, R5, R5         ; lo = lo + lo
        ADD  R3, R3, #-1
        BRp  RQ_LAZO_LO

        ; hi * 256: se duplica hi 8 veces
        LDR  R5, R0, #0         ; copia.hi
        AND  R3, R3, #0
        ADD  R3, R3, #8
RQ_LAZO_HI
        ADD  R5, R5, R5
        ADD  R3, R3, #-1
        BRp  RQ_LAZO_HI

        ADD  R5, R5, R4         ; resultado = hi * 256 + parte_baja
        LD   R6, RQ_R1          ; &resultado_q78
        STR  R5, R6, #0
        AND  R0, R0, #0         ; desbordamiento = 0
RQ_FIN
        LD   R1, RQ_R1
        LD   R2, RQ_R2
        LD   R3, RQ_R3
        LD   R4, RQ_R4
        LD   R5, RQ_R5
        LD   R6, RQ_R6
        LD   R7, RQ_R7
        RET
RQ_COPIA .BLKW #2
RQ_MEDIO .FILL #0
         .FILL #128
RQ_128  .FILL #128
RQ_FF00 .FILL xFF00
RQ_R1   .BLKW #1
RQ_R2   .BLKW #1
RQ_R3   .BLKW #1
RQ_R4   .BLKW #1
RQ_R5   .BLKW #1
RQ_R6   .BLKW #1
RQ_R7   .BLKW #1

        .END