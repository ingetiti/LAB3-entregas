; Adaptacion ISA3C; ver ../cambios_punteros.json y ../procedencia.json.


;   Tabla de opciones:

;   DIV CORDIC .................................... [8]     [2]     (Q15,  Q15 -> Q15)
;   MULT SHIFT ADD ................................ [7]     [1]     (Q8,   Q8  -> DQ16)
;   POW EXPBIN .................................... [6]     [1]     (int,  int -> int)
;   POW MULTS ..................................... [6]     [0]     (Q8,   int -> Q8)
;   EXP ........................................... [5]     .       (Q12       -> Q8)
;   MCD ........................................... [10]    .       (int,  int -> int)
;   MCM ........................................... [11]    .       (int,  int -> int)
;   SQRT NEWTONRAPHSON ............................ [4]     [1]     (DQ16      -> DQ16)
;   DIV LONG ...................................... [8]     [0]     (Q8,   Q8  -> Q8)
;   LOG CORDIC .................................... [9]     [1]     (Q12       -> Q12)
;   DIV NEWTONRAPHSON ............................. [8]     [1]     (Q8,   Q8  -> Q8)
;   LOG BORCHARDT ................................. [9]     [0]     (Q7        -> Q7)
;   Q3.12 to Q7.8 ................................. [12]    .       (Q12       -> Q8)
;   MULT BOOTH .................................... [7]     [2]     (Q8,   Q8  -> Q8)
;   MULT CORDIC ................................... [7]     [0]     (Q8,   Q8  -> Q8)
;   REDUCCION DE ARGUMENTO (CORDIC) ............... [0]     .       (Q12       -> Q12)
;   SIN TAYLOR .................................... [1]     [0]     (Q12       -> ? )
;   SIN TABLE ..................................... [1]     [1]     (Q12       -> Q14)
;   COS TABLE ..................................... [2]     .       (Q12       -> Q14)
;   SQRT NONRES ................................... [4]     [0]     (Q8        -> Q9)
;   BASE HEX ...................................... [3]     [0]     (int       -> noresult)
;   BASE BIN ...................................... [3]     [1]     (int       -> noresult)
;   SIN CHEBYSHEV-PADE ............................ [1]     [2]     (Q12       -> Q14)
;   [SALIR] ....................................... [13]    .       .

;   MODALIDAD:
;   silencioso     0    (ejecutar todas las funciones sin mostrar por consola)
;   verboso        1    (ejecutar todas las funciones mostrando que se ejecuta por consola)


;
;   **Como se organizan los datos en el bloque de operaciones:**
;
;   -   Primero se dispone de la MODALIDAD de operacion. (silencioso o verboso)
;   -   Luego se procede con datos de cada operacion que incluyen:
;       +   Opcion seleccionada (1 o 2 valores que indican la operacion a realizar).
;       +   Operandos (valores de entrada en el formato correspondiente).
;       +   Espacio para el resultado (suficiente para el formato correspondiente).
;

; EJEMPLO:
;
programa_del_menu
    .FILL   #1      ;   modo verboso (muestra todos los valores por consola)
    
    .FILL   #7      ;   MULTIPLICACION
    .FILL   #2      ;   MULTIPLICACION BOOTH
    .FILL   x0500   ;   (Q7.8) valor a (5)
    .FILL   xF400   ;   (Q7.8) valor b (-12)
    .FILL   #0      ;   (Q7.8) espacio para el resultado.
    
    .FILL   #4      ;   SQRT
    .FILL   #1      ;   SQRT NEWTONRAPHSON
    .FILL   x0002   ;   
    .FILL   x0000   ;   (Q15.16 usa 2 WORD) valor a (2.0)
    .FILL   #0      ;   
    .FILL   #0      ;   (Q15.16 usa 2 WORD) espacio para resultado.

    .FILL   #2      ;   COS TABLE
    .FILL   x1921   ;   (Q3.12) valor a (1.5708)
    .FILL   #0      ;   (Q1.14) espacio para el resultado.

    .FILL   #13     ;   SALIR
