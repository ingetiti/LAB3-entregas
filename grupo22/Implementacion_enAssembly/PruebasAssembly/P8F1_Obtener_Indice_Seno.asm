
        .ORIG x3000

; ==========================================================
; PRUEBA 8 - FASE 1 - CONVERSION DE REFERENCIA A GRADOS Q8.8
;
; OBJETIVO:
; Convertir un angulo de referencia Q3.12 a grados Q8.8
; y obtener el indice entero de la tabla mediante redondeo.
;
; ENTRADA:
; R0 = Angulo de referencia Q3.12 (0 a 6434)
;
; SALIDAS:
; R2 = Resultado temporal de calculo
; R4 = Indice entero de la tabla (0 a 90)
;
; REGISTROS UTILIZADOS:
; R0 = Referencia Q3.12
; R1 = Palabra baja del producto de 32 bits
; R2 = Palabra alta del producto / grados Q8.8
; R3 = Registro auxiliar
; R4 = Indice / bits fraccionarios
; R5 = Puntero a memoria
;
; FORMULA:
; G_Q8.8 = (REFERENCIA * 58671) / 16384
;
; REDONDEO:
; INDICE = (G_Q8.8 + 128) / 256
;
; MULTIPLICADOR:
; 58671 = 1110010100101111 (binario)
;
; IMPORTANTE:
; El producto se calcula usando dos palabras de 16 bits.
; La palabra alta y la baja se mantienen separadas.
; ==========================================================

INICIO

; ----------------------------------------------------------
; CARGA DE LA REFERENCIA DE PRUEBA
; ----------------------------------------------------------

        LEA R5, REFERENCIA_PRUEBA
        LDR R0, R5, #0

; ----------------------------------------------------------
; INICIALIZACION DEL ACUMULADOR DE 32 BITS
;
; R2:R1 representa el acumulador:
; R2 = palabra alta
; R1 = palabra baja
;
; Inicialmente el acumulador vale cero.
; ----------------------------------------------------------

        AND R1, R1, #0
        AND R2, R2, #0

; ----------------------------------------------------------
; MULTIPLICACION POR 58671
;
; Se utiliza el algoritmo de multiplicacion binaria:
;
; Por cada bit del multiplicador:
; 1. Se duplica el acumulador de 32 bits.
; 2. Si el bit correspondiente vale 1, se suma R0.
;
; La rutina DOBLAR_ACUMULADOR conserva el acarreo
; entre las dos palabras.
;
; La rutina SUMAR_REFERENCIA detecta el acarreo
; producido al sumar R0 a la palabra baja.
;
; Los bits de 58671 se procesan desde el bit 15
; hasta el bit 0.
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
; ALMACENAMIENTO DEL PRODUCTO DE 32 BITS
;
; Guardamos ambas palabras para poder inspeccionar
; el resultado de la multiplicacion en memoria.
; ----------------------------------------------------------

        LEA R5, PRODUCTO_BAJO
        STR R1, R5, #0

        LEA R5, PRODUCTO_ALTO
        STR R2, R5, #0

; ----------------------------------------------------------
; CONVERSION DEL PRODUCTO A GRADOS Q8.8
;
; El producto representa:
;
; PRODUCTO = REFERENCIA * 58671
;
; Para obtener Q8.8 debemos dividir por 2^14.
;
; En el producto de 32 bits:
;
; G_Q8.8 = (PALABRA_ALTA * 4) + BITS_15_14
;
; Los dos bits mas significativos de la palabra baja
; se extraen mediante duplicaciones sucesivas.
;
; R4 almacena temporalmente esos dos bits.
; ----------------------------------------------------------

        AND R4, R4, #0

; Comprobar el bit 15 de la palabra baja.

        ADD R3, R1, R1
        BRzp BIT_15_CERO
        ADD R4, R4, #2

BIT_15_CERO

; Comprobar el bit 14 de la palabra baja.
; La segunda duplicacion coloca ese bit en la posicion 15.

        ADD R3, R3, R3
        BRzp BIT_14_CERO
        ADD R4, R4, #1

BIT_14_CERO

; Multiplicar la palabra alta por cuatro.

        ADD R2, R2, R2
        ADD R2, R2, R2

; Incorporar los dos bits extraidos de la palabra baja.

        ADD R2, R2, R4

; ----------------------------------------------------------
; ALMACENAMIENTO DE LOS GRADOS Q8.8
;
; R2 contiene ahora el angulo expresado en grados Q8.8.
; ----------------------------------------------------------

        LEA R5, GRADOS_Q8_8
        STR R2, R5, #0

; ----------------------------------------------------------
; REDONDEO AL ENTERO MAS CERCANO
;
; Para redondear al entero mas cercano:
;
; INDICE = (GRADOS_Q8.8 + 128) / 256
;
; Primero sumamos 128, que representa media unidad
; en formato Q8.8.
; ----------------------------------------------------------

        LEA R5, CONSTANTE_128
        LDR R3, R5, #0
        ADD R2, R2, R3

; ----------------------------------------------------------
; OBTENCION DEL INDICE MEDIANTE RESTAS SUCESIVAS
;
; Dividimos por 256 mediante restas sucesivas.
;
; Cada resta exitosa incrementa el indice en uno.
;
; R5 contiene -256.
; R4 acumula la cantidad de restas exitosas.
; ----------------------------------------------------------

        LEA R5, CONSTANTE_MENOS_256
        LDR R5, R5, #0

        AND R4, R4, #0

OBTENER_INDICE

        ADD R3, R2, R5

; Si el resultado es negativo, R2 era menor que 256.
; Por lo tanto, finalizamos la division.

        BRn FIN_DIVISION

; La resta fue valida: actualizar el resto e incrementar
; el indice obtenido.

        ADD R2, R3, #0
        ADD R4, R4, #1

        BR OBTENER_INDICE

FIN_DIVISION

; ----------------------------------------------------------
; ALMACENAMIENTO DEL INDICE FINAL
;
; R4 contiene el indice entero de la tabla de seno.
; El resultado debe encontrarse entre 0 y 90.
; ----------------------------------------------------------

        LEA R5, INDICE_TABLA
        STR R4, R5, #0

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
; PROCEDIMIENTO:
; 1. Se comprueba el bit 15 de R1.
; 2. Se duplica R1.
; 3. Se duplica R2.
; 4. Si el bit 15 original de R1 era 1, se suma 1 a R2.
;
; De esta manera se transfiere correctamente el acarreo
; desde la palabra baja hacia la palabra alta.
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
;
; DETECCION DEL ACARREO:
; Si R1 era negativo antes de sumar, representa un valor
; unsigned mayor o igual a 32768.
;
; Al sumar R0 (que siempre es positivo en esta prueba):
; - Si el resultado sigue siendo negativo, no hubo acarreo.
; - Si el resultado es cero o positivo, hubo acarreo.
; ==========================================================

SUMAR_REFERENCIA

        ADD R3, R1, #0
        BRn SUMAR_DESDE_NEGATIVO

; La palabra baja era menor que 32768.
; Como R0 es positivo y menor que 32768, no puede
; producirse un acarreo unsigned en esta suma.

        ADD R1, R1, R0

        RET

; La palabra baja era mayor o igual a 32768.
; Debemos comprobar si la suma desbordo los 16 bits.

SUMAR_DESDE_NEGATIVO

        ADD R1, R1, R0
        BRn FIN_SUMAR_REFERENCIA

; Si el resultado ya no es negativo, se produjo
; un acarreo hacia la palabra alta.

        ADD R2, R2, #1

FIN_SUMAR_REFERENCIA

        RET


; ==========================================================
; DATOS DE PRUEBA
; ==========================================================

; Modificar este valor para realizar diferentes pruebas.
; El valor debe representar un angulo de referencia Q3.12.

REFERENCIA_PRUEBA      .FILL #6434

; ==========================================================
; CONSTANTES DE CONVERSION Y REDONDEO
; ==========================================================

CONSTANTE_128          .FILL #128
CONSTANTE_MENOS_256    .FILL #-256

; ==========================================================
; RESULTADOS INTERMEDIOS Y FINALES
; ==========================================================

PRODUCTO_BAJO         .BLKW #1
PRODUCTO_ALTO         .BLKW #1

GRADOS_Q8_8           .BLKW #1
INDICE_TABLA          .BLKW #1

        .END
