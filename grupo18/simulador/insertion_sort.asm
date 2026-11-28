.ORIG x3000

; ============================================================
; INSERTION_SORT.ASM
; Ordenamiento por insercion de enteros de 16 bits CON SIGNO,
; con autoverificacion de 10 casos.
;
; El archivo tiene dos partes separadas:
;   1. HARNESS (desde INICIO): para cada caso de la tabla CASES
;      llama a INSERTION_SORT y verifica el resultado. El mensaje
;      OK se imprime SOLO si los 10 casos pasan los 4 controles:
;        a) ORDEN:     a[k] <= a[k+1] para todo k (CMP con signo).
;        b) CONTENIDO: a[k] == esperado[k] para todo k. El esperado
;                      es la entrada ordenada con sorted() de Python,
;                      calculado fuera del algoritmo. Como es una
;                      permutacion ordenada de la entrada, este
;                      control prueba que se conservaron todos los
;                      elementos, con sus repeticiones.
;        c) LIMITES:   las palabras guarda (x5A5A) inmediatamente
;                      antes y despues del arreglo siguen intactas:
;                      la rutina no escribio fuera del arreglo.
;        d) CONTRATO:  la rutina conserva R0 (base) y R6.
;      Cada falla imprime un mensaje especifico y detiene el programa.
;   2. RUTINA INSERTION_SORT: la implementacion reutilizable.
; ============================================================

; Saltear los datos iniciales.
BRnzp INICIO

; La tabla de casos esta al final del programa (fuera del alcance
; de LEA, -128..+127 bytes): se accede mediante este puntero.
CASES_ADDR:
    .FILL CASES

GUARD_VALUE:
    .FILL x5A5A       ; valor de las palabras guarda

REMAIN:
    .FILL #10          ; contador persistente de casos (= casos en CASES)

INICIO:
    LEA R6, CASES_ADDR
    LDW R6, R6, #0      ; R6 = direccion del primer descriptor

CASE_LOOP:
    ; Descriptor del caso (offsets en BYTES, cada .FILL = 2 bytes):
    ;   #0 = direccion del arreglo, #2 = direccion del esperado, #4 = n
    LDW R0, R6, #0      ; R0 = base del arreglo
    LDW R1, R6, #4      ; R1 = n
    JSR INSERTION_SORT

    ; d) La rutina debe conservar R0 (base) y R6 (descriptor).
    LDW R5, R6, #0
    CMP R0, R5
    BRnp ERROR_REGS

    ; a) ORDEN: n-1 comparaciones a[k] <= a[k+1] (con signo).
    LDW R1, R6, #4      ; R1 = n (la rutina lo destruye)
    ADD R3, R0, #0      ; R3 = &a[0]
    ADD R4, R1, #-1     ; R4 = pares por comparar (n-1; -1 si n=0)
ORDER_LOOP:
    CMP R4, #0
    BRnz ORDER_DONE
    LDW R2, R3, #0      ; a[k]
    LDW R5, R3, #2      ; a[k+1]
    CMP R2, R5
    BRp ERROR_ORDER     ; a[k] > a[k+1]: no esta ordenado
    ADD R3, R3, #2
    ADD R4, R4, #-1
    BRnzp ORDER_LOOP
ORDER_DONE:

    ; b) CONTENIDO: a[k] == esperado[k] para k = 0..n-1.
    ADD R2, R0, #0      ; R2 = &a[0]
    LDW R3, R6, #2      ; R3 = &esperado[0]
    ADD R4, R1, #0      ; R4 = n
CONTENT_LOOP:
    CMP R4, #0
    BRnz CONTENT_DONE
    LDW R5, R2, #0      ; a[k]
    LDW R1, R3, #0      ; esperado[k] (R1 ya no se necesita)
    CMP R5, R1
    BRnp ERROR_CONTENT
    ADD R2, R2, #2
    ADD R3, R3, #2
    ADD R4, R4, #-1
    BRnzp CONTENT_LOOP
CONTENT_DONE:

    ; c) LIMITES: R2 = &a[n] = guarda superior; R0 - 2 = guarda inferior.
    LEA R4, GUARD_VALUE
    LDW R4, R4, #0
    LDW R5, R2, #0
    CMP R5, R4
    BRnp ERROR_BOUNDS
    LDW R5, R0, #-2
    CMP R5, R4
    BRnp ERROR_BOUNDS

    ; Siguiente descriptor: 3 palabras = 6 bytes.
    ADD R6, R6, #6

    ; Contador de casos en memoria: la rutina destruye R1..R5.
    LEA R4, REMAIN
    LDW R5, R4, #0
    ADD R5, R5, #-1
    STW R5, R4, #0
    CMP R5, #0
    BRp CASE_LOOP

    LEA R0, MSG_OK
    TRAP x22
    HALT

; ------------------------------------------------------------
; Mensajes de error: cada uno identifica el control que fallo.
; ------------------------------------------------------------
ERROR_ORDER:
    LEA R0, MSG_ORDER
    TRAP x22
    HALT

ERROR_CONTENT:
    LEA R0, MSG_CONTENT
    TRAP x22
    HALT

ERROR_BOUNDS:
    LEA R0, MSG_BOUNDS
    TRAP x22
    HALT

ERROR_REGS:
    LEA R0, MSG_REGS
    TRAP x22
    HALT

MSG_OK:
    .STRINGZ "OK: INSERTION SORT - 10 CASOS"

MSG_ORDER:
    .STRINGZ "ERROR SORT: ORDEN"

MSG_CONTENT:
    .STRINGZ "ERROR SORT: CONTENIDO"

MSG_BOUNDS:
    .STRINGZ "ERROR SORT: LIMITES"

MSG_REGS:
    .STRINGZ "ERROR SORT: REGISTROS"

; ============================================================
; RUTINA INSERTION_SORT - ordena ascendente un arreglo de
; palabras de 16 bits con signo, en el lugar.
; ============================================================
; Entrada:
;   R0 = direccion del primer elemento (par: cada elemento es
;        una palabra; la rutina no lo exige, LDW acepta impares)
;   R1 = n, cantidad de elementos (0 <= n <= 32767)
; Salida:
;   El arreglo a[0..n-1] queda ordenado de menor a mayor.
;   Es estable: los iguales conservan su orden relativo (se
;   detiene en a[j-1] <= key, no en <).
; Registros:
;   R0       se conserva.
;   R1..R5   se destruyen.
;   R6       se conserva (la rutina no lo usa).
;   R7       no se modifica (no llama a otras subrutinas);
;            retorna con JMP R7.
; Flags NZP al retornar: indefinidos.
; Memoria: solo lee y escribe a[0..n-1]. El arreglo debe caber
;   en memoria (base + 2n <= x10000).
;
; Algoritmo (para i = 1 .. n-1):
;   key = a[i]; j = i
;   mientras j > 0 y a[j-1] > key:  a[j] = a[j-1]; j = j - 1
;   a[j] = key
;
; Por que "j > 0" se prueba como R3 == R0 (igualdad de
; direcciones) y no con CMP R3, R0 / BRn: CMP compara CON SIGNO.
; Si el arreglo empieza en x8000, &a[-1] = x7FFE es positivo y
; x8000 es negativo: "R3 < R0" daria falso y el bucle seguiria
; por debajo del arreglo (es el defecto de la version anterior).
; La igualdad (Z) no depende del signo. Los contadores i y n son
; cantidades (0..32767), por eso para ellos CMP es correcto.
;
; Registros internos:
;   R0 = base, R1 = n, R2 = key, R3 = &a[j], R4 = i, R5 = a[j-1]
; ------------------------------------------------------------
INSERTION_SORT:
    CMP R1, #1
    BRnz IS_END         ; n <= 1: ya esta ordenado

    AND R4, R4, #0
    ADD R4, R4, #1      ; i = 1

IS_OUTER:
    ADD R3, R4, R4      ; R3 = 2*i (offset en bytes)
    ADD R3, R3, R0      ; R3 = &a[i]
    LDW R2, R3, #0      ; key = a[i]

IS_INNER:
    CMP R3, R0
    BRz IS_PLACE        ; j == 0
    LDW R5, R3, #-2     ; R5 = a[j-1]
    CMP R5, R2
    BRnz IS_PLACE       ; a[j-1] <= key (con signo): posicion hallada
    STW R5, R3, #0      ; a[j] = a[j-1]
    ADD R3, R3, #-2     ; j = j - 1
    BRnzp IS_INNER

IS_PLACE:
    STW R2, R3, #0      ; a[j] = key

    ADD R4, R4, #1      ; i = i + 1
    CMP R4, R1
    BRn IS_OUTER        ; mientras i < n

IS_END:
    JMP R7

; ------------------------------------------------------------
; Casos de prueba. Cada arreglo esta rodeado por dos palabras
; guarda; el esperado es sorted(entrada), calculado en Python.
; ------------------------------------------------------------
; Descriptores: direccion del arreglo, direccion del esperado, n.
CASES:
    .FILL ARR1
    .FILL EXP1
    .FILL #8
    .FILL ARR2
    .FILL EXP2
    .FILL #8
    .FILL ARR3
    .FILL EXP3
    .FILL #7
    .FILL ARR4
    .FILL EXP4
    .FILL #9
    .FILL ARR5
    .FILL EXP5
    .FILL #7
    .FILL ARR6
    .FILL EXP6
    .FILL #5
    .FILL ARR7
    .FILL EXP7
    .FILL #1
    .FILL ARR8
    .FILL EXP8
    .FILL #2
    .FILL ARR9
    .FILL EXP9
    .FILL #0
    .FILL ARR10
    .FILL EXP10
    .FILL #16

; Caso 1: original: negativos, positivos y cero
;   entrada:  [-5, 3, -1, 0, -8, 2, -3, 1]
;   esperado: [-8, -5, -3, -1, 0, 1, 2, 3]
    .FILL x5A5A      ; guarda inferior
ARR1:
    .FILL #-5
    .FILL #3
    .FILL #-1
    .FILL #0
    .FILL #-8
    .FILL #2
    .FILL #-3
    .FILL #1
    .FILL x5A5A      ; guarda superior
EXP1:
    .FILL #-8
    .FILL #-5
    .FILL #-3
    .FILL #-1
    .FILL #0
    .FILL #1
    .FILL #2
    .FILL #3

; Caso 2: repetidos (incluye 0 y negativos)
;   entrada:  [4, -2, 4, 0, -2, 0, 4, -2]
;   esperado: [-2, -2, -2, 0, 0, 4, 4, 4]
    .FILL x5A5A      ; guarda inferior
ARR2:
    .FILL #4
    .FILL #-2
    .FILL #4
    .FILL #0
    .FILL #-2
    .FILL #0
    .FILL #4
    .FILL #-2
    .FILL x5A5A      ; guarda superior
EXP2:
    .FILL #-2
    .FILL #-2
    .FILL #-2
    .FILL #0
    .FILL #0
    .FILL #4
    .FILL #4
    .FILL #4

; Caso 3: ya ordenado
;   entrada:  [-3, -1, 0, 0, 2, 5, 9]
;   esperado: [-3, -1, 0, 0, 2, 5, 9]
    .FILL x5A5A      ; guarda inferior
ARR3:
    .FILL #-3
    .FILL #-1
    .FILL #0
    .FILL #0
    .FILL #2
    .FILL #5
    .FILL #9
    .FILL x5A5A      ; guarda superior
EXP3:
    .FILL #-3
    .FILL #-1
    .FILL #0
    .FILL #0
    .FILL #2
    .FILL #5
    .FILL #9

; Caso 4: orden inverso
;   entrada:  [9, 7, 5, 2, 0, -1, -4, -6, -9]
;   esperado: [-9, -6, -4, -1, 0, 2, 5, 7, 9]
    .FILL x5A5A      ; guarda inferior
ARR4:
    .FILL #9
    .FILL #7
    .FILL #5
    .FILL #2
    .FILL #0
    .FILL #-1
    .FILL #-4
    .FILL #-6
    .FILL #-9
    .FILL x5A5A      ; guarda superior
EXP4:
    .FILL #-9
    .FILL #-6
    .FILL #-4
    .FILL #-1
    .FILL #0
    .FILL #2
    .FILL #5
    .FILL #7
    .FILL #9

; Caso 5: extremos de 16 bits (x - y desbordaria)
;   entrada:  [32767, -32768, 0, -1, 1, -32768, 32767]
;   esperado: [-32768, -32768, -1, 0, 1, 32767, 32767]
    .FILL x5A5A      ; guarda inferior
ARR5:
    .FILL #32767
    .FILL #-32768
    .FILL #0
    .FILL #-1
    .FILL #1
    .FILL #-32768
    .FILL #32767
    .FILL x5A5A      ; guarda superior
EXP5:
    .FILL #-32768
    .FILL #-32768
    .FILL #-1
    .FILL #0
    .FILL #1
    .FILL #32767
    .FILL #32767

; Caso 6: todos iguales
;   entrada:  [7, 7, 7, 7, 7]
;   esperado: [7, 7, 7, 7, 7]
    .FILL x5A5A      ; guarda inferior
ARR6:
    .FILL #7
    .FILL #7
    .FILL #7
    .FILL #7
    .FILL #7
    .FILL x5A5A      ; guarda superior
EXP6:
    .FILL #7
    .FILL #7
    .FILL #7
    .FILL #7
    .FILL #7

; Caso 7: un elemento
;   entrada:  [-42]
;   esperado: [-42]
    .FILL x5A5A      ; guarda inferior
ARR7:
    .FILL #-42
    .FILL x5A5A      ; guarda superior
EXP7:
    .FILL #-42

; Caso 8: dos elementos invertidos
;   entrada:  [1, -1]
;   esperado: [-1, 1]
    .FILL x5A5A      ; guarda inferior
ARR8:
    .FILL #1
    .FILL #-1
    .FILL x5A5A      ; guarda superior
EXP8:
    .FILL #-1
    .FILL #1

; Caso 9: vacio (n = 0)
;   entrada:  []
;   esperado: []
    .FILL x5A5A      ; guarda inferior
ARR9:
    .FILL x5A5A      ; guarda superior
EXP9:

; Caso 10: 16 elementos mezclados con repetidos
;   entrada:  [12, -7, 0, 300, -300, 12, 5, -7, 1000, -1, 0, 99, -32000, 31000, 5, 12]
;   esperado: [-32000, -300, -7, -7, -1, 0, 0, 5, 5, 12, 12, 12, 99, 300, 1000, 31000]
    .FILL x5A5A      ; guarda inferior
ARR10:
    .FILL #12
    .FILL #-7
    .FILL #0
    .FILL #300
    .FILL #-300
    .FILL #12
    .FILL #5
    .FILL #-7
    .FILL #1000
    .FILL #-1
    .FILL #0
    .FILL #99
    .FILL #-32000
    .FILL #31000
    .FILL #5
    .FILL #12
    .FILL x5A5A      ; guarda superior
EXP10:
    .FILL #-32000
    .FILL #-300
    .FILL #-7
    .FILL #-7
    .FILL #-1
    .FILL #0
    .FILL #0
    .FILL #5
    .FILL #5
    .FILL #12
    .FILL #12
    .FILL #12
    .FILL #99
    .FILL #300
    .FILL #1000
    .FILL #31000

.END