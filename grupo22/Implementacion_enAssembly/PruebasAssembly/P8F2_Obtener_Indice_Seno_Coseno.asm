        .ORIG x3000

; ==========================================================
; PRUEBA 8 - FASE 2 - OBTENCION DE LOS INDICES DE SENO Y COSENO
;
; OBJETIVO:
; Obtener los indices correspondientes a las referencias
; del seno y del coseno, expresadas en formato Q3.12.
;
; ENTRADAS:
; REFERENCIA_SENO_PRUEBA   = Referencia del seno Q3.12.
; REFERENCIA_COSENO_PRUEBA = Referencia del coseno Q3.12.
;
; SALIDAS:
; INDICE_SENO   = Indice de la tabla correspondiente al seno.
; INDICE_COSENO = Indice de la tabla correspondiente al coseno.
;
; REGISTROS AL FINAL:
; R1 = Indice del seno.
; R2 = Indice del coseno.
; R4 = Indice del coseno.
;
; PROCEDIMIENTO:
; 1. Calcular el indice del seno.
; 2. Guardar el indice del seno.
; 3. Calcular el indice del coseno.
; 4. Guardar el indice del coseno.
;
; IMPORTANTE:
; Se reutiliza la misma logica de conversion validada
; en la Prueba 8A. No se modifica el procedimiento
; matematico de multiplicacion, conversion ni redondeo.
;
; FORMULA:
; G_Q8.8 = (REFERENCIA * 58671) / 16384
;
; INDICE = (G_Q8.8 + 128) / 256
; ==========================================================


INICIO

; ==========================================================
; PRIMER CALCULO: INDICE DEL SENO
; ==========================================================

; ----------------------------------------------------------
; CARGA DE LA REFERENCIA DEL SENO
; ----------------------------------------------------------

        LEA R5, REFERENCIA_SENO_PRUEBA
        LDR R0, R5, #0

; ----------------------------------------------------------
; INICIALIZACION DEL ACUMULADOR DE 32 BITS
;
; R2:R1 representa el acumulador:
; R2 = palabra alta
; R1 = palabra baja
; ----------------------------------------------------------

        AND R1, R1, #0
        AND R2, R2, #0

; ----------------------------------------------------------
; MULTIPLICACION POR 58671
;
; Se procesan los bits del multiplicador desde el bit 15
; hasta el bit 0.
;
; Por cada bit:
; 1. Se duplica el acumulador de 32 bits.
; 2. Si el bit vale 1, se suma la referencia.
; ----------------------------------------------------------

; BIT 15 = 1

        JSR DOBLAR_ACUMULADOR
        JSR SUMAR_REFERENCIA

; BIT 14 = 1

        JSR DOBLAR_ACUMULADOR
        JSR SUMAR_REFERENCIA

; BIT 13 = 1

        JSR DOBLAR_ACUMULADOR
        JSR SUMAR_REFERENCIA

; BIT 12 = 0

        JSR DOBLAR_ACUMULADOR

; BIT 11 = 0

        JSR DOBLAR_ACUMULADOR

; BIT 10 = 1

        JSR DOBLAR_ACUMULADOR
        JSR SUMAR_REFERENCIA

; BIT 9 = 0

        JSR DOBLAR_ACUMULADOR

; BIT 8 = 1

        JSR DOBLAR_ACUMULADOR
        JSR SUMAR_REFERENCIA

; BIT 7 = 0

        JSR DOBLAR_ACUMULADOR

; BIT 6 = 0

        JSR DOBLAR_ACUMULADOR

; BIT 5 = 1

        JSR DOBLAR_ACUMULADOR
        JSR SUMAR_REFERENCIA

; BIT 4 = 0

        JSR DOBLAR_ACUMULADOR

; BIT 3 = 1

        JSR DOBLAR_ACUMULADOR
        JSR SUMAR_REFERENCIA

; BIT 2 = 1

        JSR DOBLAR_ACUMULADOR
        JSR SUMAR_REFERENCIA

; BIT 1 = 1

        JSR DOBLAR_ACUMULADOR
        JSR SUMAR_REFERENCIA

; BIT 0 = 1

        JSR DOBLAR_ACUMULADOR
        JSR SUMAR_REFERENCIA

; ----------------------------------------------------------
; ALMACENAMIENTO DEL PRODUCTO DEL SENO
; ----------------------------------------------------------

        LEA R5, PRODUCTO_SENO_BAJO
        STR R1, R5, #0

        LEA R5, PRODUCTO_SENO_ALTO
        STR R2, R5, #0

; ----------------------------------------------------------
; CONVERSION DEL PRODUCTO A GRADOS Q8.8
;
; Para obtener Q8.8 dividimos el producto por 2^14.
;
; G_Q8.8 = (PALABRA_ALTA * 4) + BITS_15_14
;
; R4 almacena temporalmente los dos bits extraidos
; de la palabra baja.
; ----------------------------------------------------------

        AND R4, R4, #0

; Comprobar el bit 15 de la palabra baja.

        ADD R3, R1, R1
        BRzp SENO_BIT_15_CERO
        ADD R4, R4, #2

SENO_BIT_15_CERO

; Comprobar el bit 14 de la palabra baja.

        ADD R3, R3, R3
        BRzp SENO_BIT_14_CERO
        ADD R4, R4, #1

SENO_BIT_14_CERO

; Multiplicar la palabra alta por cuatro.

        ADD R2, R2, R2
        ADD R2, R2, R2

; Incorporar los dos bits extraidos.

        ADD R2, R2, R4

; ----------------------------------------------------------
; ALMACENAMIENTO DE LOS GRADOS Q8.8 DEL SENO
; ----------------------------------------------------------

        LEA R5, GRADOS_SENO_Q8_8
        STR R2, R5, #0

; ----------------------------------------------------------
; REDONDEO AL ENTERO MAS CERCANO (+128)
; ----------------------------------------------------------

        LEA R5, CONSTANTE_128
        LDR R3, R5, #0
        ADD R2, R2, R3

; ----------------------------------------------------------
; OBTENCION DEL INDICE DEL SENO MEDIANTE RESTAS
; SUCESIVAS (/256)
;
; R5 contiene -256.
; R4 acumula la cantidad de restas exitosas.
; ----------------------------------------------------------

        LEA R5, CONSTANTE_MENOS_256
        LDR R5, R5, #0

        AND R4, R4, #0

OBTENER_INDICE_SENO

        ADD R3, R2, R5
        BRn FIN_INDICE_SENO

        ADD R2, R3, #0
        ADD R4, R4, #1

        BR OBTENER_INDICE_SENO

FIN_INDICE_SENO

; ----------------------------------------------------------
; ALMACENAMIENTO DEL INDICE DEL SENO
;
; R4 contiene el indice entero de la tabla.
; Guardamos el resultado para conservarlo durante
; el calculo posterior del coseno.
; ----------------------------------------------------------

        LEA R5, INDICE_SENO
        STR R4, R5, #0


; ==========================================================
; SEGUNDO CALCULO: INDICE DEL COSENO
; ==========================================================

; ----------------------------------------------------------
; CARGA DE LA REFERENCIA DEL COSENO
;
; En el programa principal esta referencia se encuentra
; en R3. Para esta prueba independiente la cargamos
; desde REFERENCIA_COSENO_PRUEBA.
; ----------------------------------------------------------

        LEA R5, REFERENCIA_COSENO_PRUEBA
        LDR R0, R5, #0

; ----------------------------------------------------------
; REINICIALIZACION DEL ACUMULADOR DE 32 BITS
;
; Es necesario comenzar desde cero porque ahora se
; procesa una referencia diferente: la del coseno.
; ----------------------------------------------------------

        AND R1, R1, #0
        AND R2, R2, #0

; ----------------------------------------------------------
; MULTIPLICACION POR 58671
; Se conserva exactamente el mismo procedimiento
; utilizado anteriormente para el indice del seno.
; ----------------------------------------------------------

; BIT 15 = 1

        JSR DOBLAR_ACUMULADOR
        JSR SUMAR_REFERENCIA

; BIT 14 = 1

        JSR DOBLAR_ACUMULADOR
        JSR SUMAR_REFERENCIA

; BIT 13 = 1

        JSR DOBLAR_ACUMULADOR
        JSR SUMAR_REFERENCIA

; BIT 12 = 0

        JSR DOBLAR_ACUMULADOR

; BIT 11 = 0

        JSR DOBLAR_ACUMULADOR

; BIT 10 = 1

        JSR DOBLAR_ACUMULADOR
        JSR SUMAR_REFERENCIA

; BIT 9 = 0

        JSR DOBLAR_ACUMULADOR

; BIT 8 = 1

        JSR DOBLAR_ACUMULADOR
        JSR SUMAR_REFERENCIA

; BIT 7 = 0

        JSR DOBLAR_ACUMULADOR

; BIT 6 = 0

        JSR DOBLAR_ACUMULADOR

; BIT 5 = 1

        JSR DOBLAR_ACUMULADOR
        JSR SUMAR_REFERENCIA

; BIT 4 = 0

        JSR DOBLAR_ACUMULADOR

; BIT 3 = 1

        JSR DOBLAR_ACUMULADOR
        JSR SUMAR_REFERENCIA

; BIT 2 = 1

        JSR DOBLAR_ACUMULADOR
        JSR SUMAR_REFERENCIA

; BIT 1 = 1

        JSR DOBLAR_ACUMULADOR
        JSR SUMAR_REFERENCIA

; BIT 0 = 1

        JSR DOBLAR_ACUMULADOR
        JSR SUMAR_REFERENCIA

; ----------------------------------------------------------
; ALMACENAMIENTO DEL PRODUCTO DEL COSENO
; ----------------------------------------------------------

        LEA R5, PRODUCTO_COSENO_BAJO
        STR R1, R5, #0

        LEA R5, PRODUCTO_COSENO_ALTO
        STR R2, R5, #0

; ----------------------------------------------------------
; CONVERSION DEL PRODUCTO A GRADOS Q8.8
; ----------------------------------------------------------

        AND R4, R4, #0

; Comprobar el bit 15 de la palabra baja.

        ADD R3, R1, R1
        BRzp COSENO_BIT_15_CERO
        ADD R4, R4, #2

COSENO_BIT_15_CERO

; Comprobar el bit 14 de la palabra baja.

        ADD R3, R3, R3
        BRzp COSENO_BIT_14_CERO
        ADD R4, R4, #1

COSENO_BIT_14_CERO

; Multiplicar la palabra alta por cuatro.

        ADD R2, R2, R2
        ADD R2, R2, R2

; Incorporar los dos bits extraidos.

        ADD R2, R2, R4

; ----------------------------------------------------------
; ALMACENAMIENTO DE LOS GRADOS Q8.8 DEL COSENO
; ----------------------------------------------------------

        LEA R5, GRADOS_COSENO_Q8_8
        STR R2, R5, #0

; ----------------------------------------------------------
; REDONDEO AL ENTERO MAS CERCANO (+128)
; ----------------------------------------------------------

        LEA R5, CONSTANTE_128
        LDR R3, R5, #0
        ADD R2, R2, R3

; ----------------------------------------------------------
; OBTENCION DEL INDICE DEL COSENO MEDIANTE RESTAS
; SUCESIVAS (/256)
; ----------------------------------------------------------

        LEA R5, CONSTANTE_MENOS_256
        LDR R5, R5, #0

        AND R4, R4, #0

OBTENER_INDICE_COSENO

        ADD R3, R2, R5
        BRn FIN_INDICE_COSENO

        ADD R2, R3, #0
        ADD R4, R4, #1

        BR OBTENER_INDICE_COSENO

FIN_INDICE_COSENO

; ----------------------------------------------------------
; ALMACENAMIENTO DEL INDICE DEL COSENO
; ----------------------------------------------------------

        LEA R5, INDICE_COSENO
        STR R4, R5, #0


; ==========================================================
; PREPARACION DE LOS REGISTROS DE SALIDA
;
; R1 = Indice del seno.
; R2 = Indice del coseno.
; R4 = Indice del coseno.
;
; Los dos resultados tambien permanecen almacenados
; en sus respectivas variables de memoria.
; ==========================================================

        LEA R5, INDICE_SENO
        LDR R1, R5, #0

        LEA R5, INDICE_COSENO
        LDR R2, R5, #0

; ----------------------------------------------------------
; FIN DE LA PRUEBA
; ----------------------------------------------------------

        HALT


; ==========================================================
; SUBRUTINA: DOBLAR_ACUMULADOR
;
; OBJETIVO:
; Multiplicar por dos el acumulador de 32 bits R2:R1.
;
; Se comprueba el bit 15 de R1 para detectar si debe
; transferirse un acarreo hacia la palabra alta R2.
; ==========================================================

DOBLAR_ACUMULADOR

        ADD R3, R1, #0
        BRn DOBLAR_CON_ACARREO

; Caso sin acarreo desde la palabra baja.

        ADD R1, R1, R1
        ADD R2, R2, R2

        RET

; Caso en el que el bit 15 original de R1 era 1.

DOBLAR_CON_ACARREO

        ADD R1, R1, R1
        ADD R2, R2, R2
        ADD R2, R2, #1

        RET


; ==========================================================
; SUBRUTINA: SUMAR_REFERENCIA
;
; OBJETIVO:
; Sumar R0 a la palabra baja del acumulador.
;
; Si la suma produce un acarreo unsigned, se incrementa
; la palabra alta R2.
; ==========================================================

SUMAR_REFERENCIA

        ADD R3, R1, #0
        BRn SUMAR_DESDE_NEGATIVO

; La palabra baja era menor que 32768.

        ADD R1, R1, R0

        RET

; La palabra baja era mayor o igual a 32768.
; Comprobar si la suma produce un acarreo.

SUMAR_DESDE_NEGATIVO

        ADD R1, R1, R0
        BRn FIN_SUMAR_REFERENCIA

        ADD R2, R2, #1

FIN_SUMAR_REFERENCIA

        RET


; ==========================================================
; DATOS DE PRUEBA
; ==========================================================

; Referencia del seno expresada en Q3.12.
REFERENCIA_SENO_PRUEBA       .FILL #6434

; Referencia del coseno expresada en Q3.12.
REFERENCIA_COSENO_PRUEBA     .FILL #0


; ==========================================================
; CONSTANTES DE CONVERSION Y REDONDEO
; ==========================================================

CONSTANTE_128                .FILL #128
CONSTANTE_MENOS_256          .FILL #-256


; ==========================================================
; RESULTADOS INTERMEDIOS DEL SENO
; ==========================================================

PRODUCTO_SENO_BAJO           .BLKW #1
PRODUCTO_SENO_ALTO           .BLKW #1

GRADOS_SENO_Q8_8             .BLKW #1
INDICE_SENO                  .BLKW #1


; ==========================================================
; RESULTADOS INTERMEDIOS DEL COSENO
; ==========================================================

PRODUCTO_COSENO_BAJO         .BLKW #1
PRODUCTO_COSENO_ALTO         .BLKW #1

GRADOS_COSENO_Q8_8           .BLKW #1
INDICE_COSENO                .BLKW #1


        .END