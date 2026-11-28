; =====================================================================
;  MULTIPLICACION POR CORDIC (modo lineal) EN Q7.8 - PROGRAMA COMPLETO PARA LC-3
;  VARIANTE HORNER (sin corrimientos a la derecha): mismo resultado que CORDIC_multiplicacion_Q78.c
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
;    CORDIC_MUL       el algoritmo (lazo de CORDIC en forma de Horner: duplica y suma, nunca desplaza a la derecha)
;    subrutinas       DUP32, SUMA32, REDUCIR_Q78
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
;  CORDIC_MUL : a_q8 * b_q8 con CORDIC lineal, FORMA DE HORNER (sin corrimientos a la derecha)
;     entrada : R0 = a_q8     R1 = b_q8
;     salida  : R0 = resultado en Q7.8 (solo valido si R1 = 0; en otro caso vale 0)
;               R1 = estado:  0 = ok / 1 = desbordamiento (|a*b| > 127.996) / 2 = b_q8 invalido (-32768)
;     deja ademas en memoria: CM_Y    = acumulador de 32 bits (Q16), que vale a_q8 * b_q8
;                             CM_ITER = cantidad de iteraciones realizadas
;     preserva R2..R6
;
;  IDEA. El CORDIC clasico acumula  y = y +- a * 2^(14-i)  y por eso tiene que ir corriendo a hacia la derecha
;  (current_x /= 2), que en el LC-3 se hace bit por bit. La suma total es la misma si se evalua asi (Horner):
;        y = 2 * y +- a          (duplicar y sumar o restar a; duplicar es sumar un numero consigo mismo)
;  Para z se sigue t = z * 2^i, que en cada vuelta queda  t = 2t + 0x8000  (en 16 bits):
;        el signo de t es el de z, y t == 0 equivale a z == 0.
;  Si el lazo corta antes de las 15 vueltas (t == 0) faltan (15 - vueltas) duplicaciones de y.
;  -a se calcula una sola vez (CM_NA), asi cada vuelta es siempre una SUMA32 (no hace falta RESTA32).
;
;    R2 = t   R5 = vueltas   R0 = &y (se mantiene durante todo el lazo)   R1 = &a o &(-a)   R3,R4,R6 = auxiliares
; ---------------------------------------------------------------------
CORDIC_MUL
        ST   R2, CM_R2
        ST   R3, CM_R3
        ST   R4, CM_R4
        ST   R5, CM_R5
        ST   R6, CM_R6
        ST   R7, CM_R7

        ADD  R2, R1, #0         ; t = b_q8 (el multiplicador)
        LD   R3, CM_B_MIN       ; 0x8000
        ADD  R3, R3, R2         ; 0x8000 + 0x8000 = 0 solo si b_q8 == -32768
        BRz  CM_B_INVALIDO

        ; a extendido a 32 bits en CM_A: lo = a_q8, hi = 0 o -1 segun el signo de a_q8
        LEA  R4, CM_A
        STR  R0, R4, #1         ; lo = a_q8
        AND  R3, R3, #0
        ADD  R0, R0, #0
        BRzp CM_A_POSITIVO
        ADD  R3, R3, #-1        ; hi = -1 (todos los bits en 1)
CM_A_POSITIVO
        STR  R3, R4, #0         ; hi

        ; CM_NA = -CM_A (32 bits): se invierte todo y se suma 1
        NOT  R3, R3             ; ~hi
        LDR  R6, R4, #1
        NOT  R6, R6             ; ~lo
        ADD  R6, R6, #1         ; ~lo + 1
        BRnp CM_NA_ARMAR        ; si lo no dio 0 no hubo acarreo hacia hi
        ADD  R3, R3, #1
CM_NA_ARMAR
        LEA  R4, CM_NA
        STR  R3, R4, #0
        STR  R6, R4, #1

        ; se inicializa el acumulador en 0
        LEA  R0, CM_Y           ; R0 = &y durante todo el lazo
        AND  R3, R3, #0
        STR  R3, R0, #0
        STR  R3, R0, #1
        AND  R5, R5, #0         ; vueltas = 0
CM_LAZO
        ADD  R2, R2, #0         ; if (t == 0) break;
        BRz  CM_FIN_LAZO
        JSR  DUP32              ; y = 2 * y
        LEA  R1, CM_A           ; t > 0: se suma +a
        ADD  R2, R2, #0
        BRp  CM_SUMAR
        LEA  R1, CM_NA          ; t < 0: se suma -a
CM_SUMAR
        JSR  SUMA32             ; y = y +- a
        ADD  R2, R2, R2         ; t = 2t + 0x8000 (en 16 bits)
        LD   R3, CM_BIT15
        ADD  R2, R2, R3
        ADD  R5, R5, #1         ; vueltas = vueltas + 1
        ADD  R3, R5, #-15
        BRn  CM_LAZO            ; mientras vueltas < 15
CM_FIN_LAZO
        ST   R5, CM_ITER        ; iteraciones realizadas

        ; si se corto antes de las 15 vueltas faltan (15 - vueltas) duplicaciones de y
        ADD  R4, R5, #-15       ; R4 = -(15 - vueltas)
        BRzp CM_REDUCIR
CM_FALTAN
        JSR  DUP32
        ADD  R4, R4, #1
        BRn  CM_FALTAN

        ; y (Q16) -> Q7.8 con redondeo
CM_REDUCIR
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

CM_BIT15 .FILL x8000
CM_B_MIN .FILL x8000
CM_A     .BLKW #2               ; a_q8 extendido a 32 bits
CM_NA    .BLKW #2               ; -a_q8 en 32 bits
CM_Y     .BLKW #2               ; acumulador y (32 bits, Q16)
CM_RES   .BLKW #1               ; resultado Q7.8 que escribe REDUCIR_Q78
CM_ITER  .BLKW #1
CM_R2    .BLKW #1
CM_R3    .BLKW #1
CM_R4    .BLKW #1
CM_R5    .BLKW #1
CM_R6    .BLKW #1
CM_R7    .BLKW #1

; ---------------------------------------------------------------------
;  DUP32 : [R0] = [R0] * 2   (duplica un par hi/lo: v = v + v)
;  es la operacion que reemplaza al corrimiento a la derecha: duplicar es solo una suma
;  hay acarreo de lo hacia hi cuando lo tiene el bit 15 en 1 (lo < 0)
;  no modifica ningun registro
; ---------------------------------------------------------------------
DUP32
        ST   R1, DUP_R1
        ST   R2, DUP_R2
        LDR  R1, R0, #1         ; lo
        LDR  R2, R0, #0         ; hi
        ADD  R2, R2, R2         ; hi = hi * 2
        ADD  R1, R1, #0
        BRzp DUP_SIN_ACARREO
        ADD  R2, R2, #1         ; el bit 15 de lo pasa al bit 0 de hi
DUP_SIN_ACARREO
        ADD  R1, R1, R1         ; lo = lo * 2
        STR  R2, R0, #0
        STR  R1, R0, #1
        LD   R1, DUP_R1
        LD   R2, DUP_R2
        RET
DUP_R1  .BLKW #1
DUP_R2  .BLKW #1

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