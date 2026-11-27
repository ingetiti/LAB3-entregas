

;   ============================================================================
;   ==- TABLA DEL VECTOR DE OPERACIONES -=======================================
    0:  SALIR           
    1:  argrd           REDUCCION DE ARGUMENTO      (Q12       -> Q12)
    2:  sin_taylor      SENO TAYLOR                 (int       -> Q12)
    3:  sin_table       SENO TABLA                  (Q12       -> Q14)
    4:  sin_cheb        SENO CHEBYSHEV-PADE         (Q12       -> Q14)
    5:  cos             COSENO TABLA                (Q12       -> Q14)
    6:  base_hex        CAMBIO DE BASE A HEX        (int       -> consola)
    7:  base_bin        CAMBIO DE BASE A BIN        (int       -> consola)
    8:  sqrt_nonres     SQRT NON RESTORING          (Q8        -> Q9)
    9:  sqrt_nr         SQRT NEWTONRAPHSON          (DQ16      -> DQ16)
   10:  exp             EXPONENCIACION              (Q12       -> Q8)
   11:  pow_mults       POTENCIA MULTIPLICACIONES   (Q8,   int -> Q8)
   12:  pow_expbin      POTENCIA EXPON. BINARIA     (int,  int -> int)
   13:  mult_cordic     MULTIPLICACION CORDIC       (Q8,   Q8  -> Q8)
   14:  mult_basic      MULTIPLICACION SHIFT SUMA   (Q8,   Q8  -> DQ16)
   15:  mult_booth      MULTIPLICACION BOOTH        (Q8,   Q8  -> Q8)
   16:  div_long        DIVISION LARGA              (Q8,   Q8  -> Q8)
   17:  div_nr          DIVISION NEWTONRAPHSON      (Q8,   Q8  -> Q8)
   18:  div_cordic      DIVISION CORDIC             (Q15,  Q15 -> Q15)
   19:  log_borch       LOGARITMO BORCHARDT         (Q7        -> Q7)
   20:  log_cordic      LOGARITMO CORDIC            (Q12       -> Q12)
   21:  mcd             MINIMO COMUN DIVISOR        (int,  int -> int)
   22:  mcm             MAXIMO COMUN MULTIPLO       (int,  int -> int)
   23:  qtoq            Q3.12 A Q7.8                (Q12       -> Q8)

;   MODALIDAD:
;   silencioso     0    (ejecutar todas las funciones sin mostrar por consola)
;   verboso        1    (ejecutar todas las funciones mostrando que se ejecuta por consola)


;
;   **Como se organizan los datos en el bloque de operaciones:**
;
;   -   Primero se dispone de la MODALIDAD de operacion. (silencioso o verboso)
;   -   Luego se procede con indice de la operacion.
;   -   Los datos necesarios para la opearacion se pasan con el siguiente formato (ocupan 4 WORD):
;       +   Operando de entrada a.
;       +   Operando de entrada b. (En el caso que el operando de entrada sea DQ16 ocuparia los
;           dos espacios, parte entera y parte fraccionaria).
;       +   Espacio para el resultado.
;       +   Espacio para el resultado. (En el caso que el resultado sea DQ16 ocuparia los dos
;           espacios, parte entera y parte fraccionaria).
;   (Puede verse que cada operacion ocuparia exactamente 5 WORD, 1 para la operacion y 4 para los datos necesarios,
;   con la excepcion de la operacion SALIR (0), ya que no requiere de datos).

; EJEMPLO:
;
programa_del_menu
    .FILL   #1      ;   modo verboso (muestra todos los valores por consola)
    
    .FILL   #15     ;   MULTIPLICACION BOOTH        (Indice de operacion)
    .FILL   x0500   ;   Valor 5                     (Q7.8)
    .FILL   xF400   ;   Valor -12                   (Q7.8)
    .FILL   #0      ;   Espacio para el resultado   (Q7.8)
    .FILL   #0      ;   Espacio para el resultado   (Quedara en blanco)
    
    .FILL   #9      ;   SQRT NEWTONRAPHSON          (Indice de operacion)
    .FILL   x0002   ;   Valor 2.0                   (Q15.16) 
    .FILL   x0000   ;   *                           (DQ16 usa 2 WORD)
    .FILL   #0      ;   Espacio para el resultado   (Q15.16)
    .FILL   #0      ;   *                           (DQ16 usa 2 WORD)

    .FILL   #5      ;   COSENO TABLA                (Indice de operacion)
    .FILL   x1921   ;   Valor 1.5708                (Q3.12)
    .FILL   #0      ;   *                           (Usa un solo operando)
    .FILL   #0      ;   Espacio para el resultado   (Q1.14)
    .FILL   #0      ;   Espacio para el resultado   (Quedara en blanco)

    .FILL   #0      ;   SALIR