; Adaptacion BYTEX-16; ver ../cambios_punteros.json y ../procedencia.json.
SENO_TABLA
    ST R1, ADAPT_R1
    AND R1, R1, #0
    BR ADAPT_IN
COSENO_TABLA
    ST R1, ADAPT_R1
    AND R1, R1, #0
    ADD R1, R1, #1
ADAPT_IN
    ST R1, ADAPT_MODE
    ST R2, ADAPT_R2
    ST R3, ADAPT_R3
    ST R4, ADAPT_R4
    ST R5, ADAPT_R5
    ST R6, ADAPT_R6
    ST R7, ADAPT_R7
ADAPT_NORM
    ADD R0, R0, #0
    BRn ADAPT_NEG
    LD R1, ADAPT_NEG_2PI
    ADD R2, R0, R1
    BRn ADAPT_READY
    ADD R0, R2, #0
    BR ADAPT_NORM
ADAPT_NEG
    LD R1, ADAPT_2PI
    ADD R0, R0, R1
    BR ADAPT_NORM
ADAPT_READY
    STI R0, ADAPT_ANGLE_PTR
    BR INICIO
ADAPT_FIN
    LD R0, ADAPT_MODE
    BRp ADAPT_COS
    ADD R0, R1, #0
    BR ADAPT_RESTORE
ADAPT_COS
    ADD R0, R2, #0
ADAPT_RESTORE
    LD R1, ADAPT_R1
    LD R2, ADAPT_R2
    LD R3, ADAPT_R3
    LD R4, ADAPT_R4
    LD R5, ADAPT_R5
    LD R6, ADAPT_R6
    LD R7, ADAPT_R7
    RET
ADAPT_MODE .FILL #0
ADAPT_2PI .FILL #25736
ADAPT_NEG_2PI .FILL #-25736
ADAPT_ANGLE_PTR .FILL ANGULO_PRUEBA
ADAPT_R1 .FILL #0
ADAPT_R2 .FILL #0
ADAPT_R3 .FILL #0
ADAPT_R4 .FILL #0
ADAPT_R5 .FILL #0
ADAPT_R6 .FILL #0
ADAPT_R7 .FILL #0
; BYTEX-16: origen asignado por el programa principal.

        BR INICIO

; PUNTEROS A DATOS ALEJADOS

PUNTERO_PI       .FILL PI_SOBRE_2
PUNTERO_ANGULO   .FILL ANGULO_PRUEBA

; ==========================================================
; ENTRADAS:
; R1 = Valor absoluto del seno en Q1.14
; R2 = Valor absoluto del coseno en Q1.14
;
; SIGNOS EN MEMORIA:
; SIGNO_SENO   = +1, -1 o 0
; SIGNO_COSENO = +1, -1 o 0
;
; SALIDAS:
; R1 = Seno final en Q1.14
; R2 = Coseno final en Q1.14
;
; REGISTROS UTILIZADOS:
; R1 = Resultado del seno
; R2 = Resultado del coseno
; R3 = Signo temporal
; R5 = Puntero a memoria
;
; IMPORTANTE:
; Para obtener un numero negativo utilizamos complemento
; a dos: NOT del valor seguido de ADD #1.
;
; Si el signo es cero, el resultado se fuerza a cero.
; ==========================================================


INICIO

        AND R1, R1, #0

        ; Recuperar la dirección de PI/2.
    LD R4, ADAPT_PTR1
    BR ADAPT_SKIP1
ADAPT_PTR1 .FILL PUNTERO_PI
ADAPT_SKIP1
        LDR R4, R4, #0

        ; Recuperar la dirección del ángulo de entrada.
    LD R5, ADAPT_PTR2
    BR ADAPT_SKIP2
ADAPT_PTR2 .FILL PUNTERO_ANGULO
ADAPT_SKIP2
        LDR R5, R5, #0

        ; Cargar el ángulo Q3.12.
        LDR R0, R5, #0

; --------------------------------------------------
; COMPROBACIÓN DE CASOS ESPECIALES
; --------------------------------------------------

COMPROBAR_CERO
        BRz CASO_ESPECIAL_CERO ; LDR actualizó NZP: si R0=0, es caso especial

COMPROBAR_90
        LDR R5, R4, #0 ; Cargar PI/2
        NOT R5, R5
        ADD R5, R5, #1
        ADD R5, R0, R5 ; Comparar ángulo con PI/2
        BRz CASO_ESPECIAL_90

COMPROBAR_180
        LDR R5, R4, #1 ; Cargar PI
        NOT R5, R5
        ADD R5, R5, #1
        ADD R5, R0, R5 ; Comparar ángulo con PI
        BRz CASO_ESPECIAL_180

COMPROBAR_270
        LDR R5, R4, #2 ; Cargar 3PI/2
        NOT R5, R5
        ADD R5, R5, #1
        ADD R5, R0, R5 ; Comparar ángulo con 3PI/2
        BRz CASO_ESPECIAL_270

COMPROBAR_360
        LDR R5, R4, #3 ; Cargar 2PI
        NOT R5, R5
        ADD R5, R5, #1
        ADD R5, R0, R5 ; Comparar ángulo con 2PI
        BRz CASO_ESPECIAL_360

; --------------------------------------------------
; DETERMINACIÓN DEL CUADRANTE
; --------------------------------------------------

COMPROBAR_CUADRANTE_1
        LDR R5, R4, #0 ; Cargar PI/2
        NOT R5, R5
        ADD R5, R5, #1
        ADD R2, R0, R5 ; Comparar ángulo con PI/2
        BRn CUADRANTE_1

COMPROBAR_CUADRANTE_2
        LDR R5, R4, #1 ; Cargar PI
        NOT R5, R5
        ADD R5, R5, #1
        ADD R2, R0, R5 ; Comparar ángulo con PI
        BRn CUADRANTE_2

COMPROBAR_CUADRANTE_3
        LDR R5, R4, #2 ; Cargar 3PI/2
        NOT R5, R5
        ADD R5, R5, #1
        ADD R2, R0, R5 ; Comparar ángulo con 3PI/2
        BRn CUADRANTE_3

COMPROBAR_CUADRANTE_4
        AND R1, R1, #0
        ADD R1, R1, #4 ; Identificar cuadrante 4
        BR CALCULAR_REFERENCIA_4

; --------------------------------------------------
; CÁLCULO DEL ÁNGULO DE REFERENCIA
; --------------------------------------------------

CUADRANTE_1
        AND R1, R1, #0
        ADD R1, R1, #1 ; Identificar cuadrante 1
        ADD R2, R0, #0 ; Referencia = ángulo original
        BR CALCULAR_COFUNCION

CUADRANTE_2
        AND R1, R1, #0
        ADD R1, R1, #2 ; Identificar cuadrante 2
        LDR R2, R4, #1 ; Cargar PI
        NOT R2, R2
        ADD R2, R2, #1
        ADD R2, R0, R2 ; Calcular ángulo - PI
        NOT R2, R2
        ADD R2, R2, #1 ; Referencia = PI - ángulo
        BR CALCULAR_COFUNCION

CUADRANTE_3
        AND R1, R1, #0
        ADD R1, R1, #3 ; Identificar cuadrante 3
        LDR R2, R4, #1 ; Cargar PI
        NOT R2, R2
        ADD R2, R2, #1
        ADD R2, R0, R2 ; Referencia = ángulo - PI
        BR CALCULAR_COFUNCION

CALCULAR_REFERENCIA_4
        LDR R2, R4, #3 ; Cargar 2PI
        NOT R2, R2
        ADD R2, R2, #1
        ADD R2, R0, R2 ; Calcular ángulo - 2PI
        NOT R2, R2
        ADD R2, R2, #1 ; Referencia = 2PI - ángulo

; --------------------------------------------------
; CÁLCULO DEL ÁNGULO COMPLEMENTARIO
; --------------------------------------------------

CALCULAR_COFUNCION
        LDR R3, R4, #0 ; Cargar PI/2
        NOT R3, R3
        ADD R3, R3, #1
        ADD R3, R2, R3 ; Calcular referencia - PI/2
        NOT R3, R3
        ADD R3, R3, #1 ; Cofunción = PI/2 - referencia
        BR DETERMINAR_SIGNOS

; --------------------------------------------------
; DETERMINACIÓN DE SIGNOS PARA CASOS NORMALES
; --------------------------------------------------

DETERMINAR_SIGNOS
        ADD R5, R1, #-1
        BRz SIGNOS_CUADRANTE_1

        ADD R5, R1, #-2
        BRz SIGNOS_CUADRANTE_2

        ADD R5, R1, #-3
        BRz SIGNOS_CUADRANTE_3

        BR SIGNOS_CUADRANTE_4

SIGNOS_CUADRANTE_1
        AND R0, R0, #0
        ADD R0, R0, #1 ; Signo del seno = +1
        AND R4, R4, #0
        ADD R4, R4, #1 ; Signo del coseno = +1
        BR GUARDAR_SIGNOS

SIGNOS_CUADRANTE_2
        AND R0, R0, #0
        ADD R0, R0, #1 ; Signo del seno = +1
        AND R4, R4, #0
        ADD R4, R4, #-1 ; Signo del coseno = -1
        BR GUARDAR_SIGNOS

SIGNOS_CUADRANTE_3
        AND R0, R0, #0
        ADD R0, R0, #-1 ; Signo del seno = -1
        AND R4, R4, #0
        ADD R4, R4, #-1 ; Signo del coseno = -1
        BR GUARDAR_SIGNOS

SIGNOS_CUADRANTE_4
        AND R0, R0, #0
        ADD R0, R0, #-1 ; Signo del seno = -1
        AND R4, R4, #0
        ADD R4, R4, #1 ; Signo del coseno = +1
        BR GUARDAR_SIGNOS

; --------------------------------------------------
; DETERMINACIÓN DE SIGNOS PARA CASOS ESPECIALES
; --------------------------------------------------

CASO_ESPECIAL_CERO
        AND R1, R1, #0
        AND R2, R2, #0
        AND R0, R0, #0
        ADD R4, R0, #1

; Referencia del seno = 0.
        AND R2, R2, #0

; Referencia del coseno = 90 grados.
    LD R5, ADAPT_PTR3
    BR ADAPT_SKIP3
ADAPT_PTR3 .FILL PI_SOBRE_2
ADAPT_SKIP3
        LDR R3, R5, #0

        BR GUARDAR_SIGNOS

CASO_ESPECIAL_90
        AND R1, R1, #0
        AND R3, R3, #0
        AND R0, R0, #0
        ADD R0, R0, #1
        AND R4, R4, #0

; Referencia del seno = 90 grados.
    LD R5, ADAPT_PTR4
    BR ADAPT_SKIP4
ADAPT_PTR4 .FILL PI_SOBRE_2
ADAPT_SKIP4
        LDR R2, R5, #0

; Referencia del coseno = 0.
        AND R3, R3, #0

        BR GUARDAR_SIGNOS

CASO_ESPECIAL_180
        AND R1, R1, #0
        AND R0, R0, #0
        AND R4, R4, #0
        ADD R4, R4, #-1

; Referencia del seno = 0.
        AND R2, R2, #0

; Referencia del coseno = 90 grados.
    LD R5, ADAPT_PTR5
    BR ADAPT_SKIP5
ADAPT_PTR5 .FILL PI_SOBRE_2
ADAPT_SKIP5
        LDR R3, R5, #0

        BR GUARDAR_SIGNOS

CASO_ESPECIAL_270
        AND R1, R1, #0
        AND R3, R3, #0
        AND R0, R0, #0
        ADD R0, R0, #-1
        AND R4, R4, #0

; Referencia del seno = 90 grados.
    LD R5, ADAPT_PTR6
    BR ADAPT_SKIP6
ADAPT_PTR6 .FILL PI_SOBRE_2
ADAPT_SKIP6
        LDR R2, R5, #0

; Referencia del coseno = 0.
        AND R3, R3, #0

        BR GUARDAR_SIGNOS

CASO_ESPECIAL_360
        AND R1, R1, #0
        AND R0, R0, #0
        AND R4, R4, #0
        ADD R4, R4, #1

; Referencia del seno = 0.
        AND R2, R2, #0

; Referencia del coseno = 90 grados.
    LD R5, ADAPT_PTR7
    BR ADAPT_SKIP7
ADAPT_PTR7 .FILL PI_SOBRE_2
ADAPT_SKIP7
        LDR R3, R5, #0

; ==========================================================
; GUARDAR REFERENCIAS Y SIGNOS
; ==========================================================

GUARDAR_SIGNOS

; Guardar referencia del seno.
    LD R5, ADAPT_PTR8
    BR ADAPT_SKIP8
ADAPT_PTR8 .FILL REFERENCIA_SENO_PRUEBA
ADAPT_SKIP8
        STR R2, R5, #0

; Guardar referencia del coseno.
    LD R5, ADAPT_PTR9
    BR ADAPT_SKIP9
ADAPT_PTR9 .FILL REFERENCIA_COSENO_PRUEBA
ADAPT_SKIP9
        STR R3, R5, #0

; Guardar signo del seno.
    LD R5, ADAPT_PTR10
    BR ADAPT_SKIP10
ADAPT_PTR10 .FILL SIGNO_SENO
ADAPT_SKIP10
        STR R0, R5, #0

; Guardar signo del coseno.
    LD R5, ADAPT_PTR11
    BR ADAPT_SKIP11
ADAPT_PTR11 .FILL SIGNO_COSENO
ADAPT_SKIP11
        STR R4, R5, #0

; Continuar con el cálculo de índices de la Prueba 8.

        BR CALCULO_SENO
        
; ==========================================================
; PRIMER CALCULO: INDICE DEL SENO
; ==========================================================

; ----------------------------------------------------------
; CARGA DE LA REFERENCIA DEL SENO
; ----------------------------------------------------------

CALCULO_SENO
    LD R5, ADAPT_PTR12
    BR ADAPT_SKIP12
ADAPT_PTR12 .FILL REFERENCIA_SENO_PRUEBA
ADAPT_SKIP12
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
    LD R5, ADAPT_PTR13
    BR ADAPT_SKIP13
ADAPT_PTR13 .FILL PRODUCTO_SENO_BAJO
ADAPT_SKIP13
        STR R1, R5, #0
    LD R5, ADAPT_PTR14
    BR ADAPT_SKIP14
ADAPT_PTR14 .FILL PRODUCTO_SENO_ALTO
ADAPT_SKIP14
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
    LD R5, ADAPT_PTR15
    BR ADAPT_SKIP15
ADAPT_PTR15 .FILL GRADOS_SENO_Q8_8
ADAPT_SKIP15
        STR R2, R5, #0

; ----------------------------------------------------------
; REDONDEO AL ENTERO MAS CERCANO (+128)
; ----------------------------------------------------------
    LD R5, ADAPT_PTR16
    BR ADAPT_SKIP16
ADAPT_PTR16 .FILL CONSTANTE_128
ADAPT_SKIP16
        LDR R3, R5, #0
        ADD R2, R2, R3

; ----------------------------------------------------------
; OBTENCION DEL INDICE DEL SENO MEDIANTE RESTAS
; SUCESIVAS (/256)
;
; R5 contiene -256.
; R4 acumula la cantidad de restas exitosas.
; ----------------------------------------------------------
    LD R5, ADAPT_PTR17
    BR ADAPT_SKIP17
ADAPT_PTR17 .FILL CONSTANTE_MENOS_256
ADAPT_SKIP17
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
    LD R5, ADAPT_PTR18
    BR ADAPT_SKIP18
ADAPT_PTR18 .FILL INDICE_SENO
ADAPT_SKIP18
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
    LD R5, ADAPT_PTR19
    BR ADAPT_SKIP19
ADAPT_PTR19 .FILL REFERENCIA_COSENO_PRUEBA
ADAPT_SKIP19
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
    LD R5, ADAPT_PTR20
    BR ADAPT_SKIP20
ADAPT_PTR20 .FILL PRODUCTO_COSENO_BAJO
ADAPT_SKIP20
        STR R1, R5, #0
    LD R5, ADAPT_PTR21
    BR ADAPT_SKIP21
ADAPT_PTR21 .FILL PRODUCTO_COSENO_ALTO
ADAPT_SKIP21
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
    LD R5, ADAPT_PTR22
    BR ADAPT_SKIP22
ADAPT_PTR22 .FILL GRADOS_COSENO_Q8_8
ADAPT_SKIP22
        STR R2, R5, #0

; ----------------------------------------------------------
; REDONDEO AL ENTERO MAS CERCANO (+128)
; ----------------------------------------------------------
    LD R5, ADAPT_PTR23
    BR ADAPT_SKIP23
ADAPT_PTR23 .FILL CONSTANTE_128
ADAPT_SKIP23
        LDR R3, R5, #0
        ADD R2, R2, R3

; ----------------------------------------------------------
; OBTENCION DEL INDICE DEL COSENO MEDIANTE RESTAS
; SUCESIVAS (/256)
; ----------------------------------------------------------
    LD R5, ADAPT_PTR24
    BR ADAPT_SKIP24
ADAPT_PTR24 .FILL CONSTANTE_MENOS_256
ADAPT_SKIP24
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
    LD R5, ADAPT_PTR25
    BR ADAPT_SKIP25
ADAPT_PTR25 .FILL INDICE_COSENO
ADAPT_SKIP25
        STR R4, R5, #0


; ----------------------------------------------------------
; CARGA DE LA DIRECCION BASE DE LA TABLA
; ----------------------------------------------------------
    LD R3, ADAPT_PTR26
    BR ADAPT_SKIP26
ADAPT_PTR26 .FILL TABLA_SENO
ADAPT_SKIP26


; ==========================================================
; BUSQUEDA DEL VALOR DEL SENO
; ==========================================================

; Recuperar el indice del seno desde memoria.
    LD R5, ADAPT_PTR27
    BR ADAPT_SKIP27
ADAPT_PTR27 .FILL INDICE_SENO
ADAPT_SKIP27
        LDR R4, R5, #0

; Calcular la direccion dinamica del elemento.

        ADD R5, R3, R4
    ADD R5, R5, R4 ; BYTEX-16: indice de palabras a bytes

; Recuperar el valor correspondiente de la tabla.

        LDR R1, R5, #0

; Guardar el resultado del seno en memoria.
    LD R5, ADAPT_PTR28
    BR ADAPT_SKIP28
ADAPT_PTR28 .FILL RESULTADO_SENO
ADAPT_SKIP28
        STR R1, R5, #0


; ==========================================================
; BUSQUEDA DEL VALOR DEL COSENO
; ==========================================================

; Recuperar el indice del coseno desde memoria.
    LD R5, ADAPT_PTR29
    BR ADAPT_SKIP29
ADAPT_PTR29 .FILL INDICE_COSENO
ADAPT_SKIP29
        LDR R4, R5, #0

; Calcular la direccion dinamica del elemento.

        ADD R5, R3, R4
    ADD R5, R5, R4 ; BYTEX-16: indice de palabras a bytes

; Recuperar el valor correspondiente de la tabla.

        LDR R2, R5, #0

; Guardar el resultado del coseno en memoria.
    LD R5, ADAPT_PTR30
    BR ADAPT_SKIP30
ADAPT_PTR30 .FILL RESULTADO_COSENO
ADAPT_SKIP30
        STR R2, R5, #0

; ----------------------------------------------------------
; 1. APLICAR SIGNO AL SENO
; ----------------------------------------------------------
    LD R5, ADAPT_PTR31
    BR ADAPT_SKIP31
ADAPT_PTR31 .FILL SIGNO_SENO
ADAPT_SKIP31
        LDR R3, R5, #0

; Comprobar si el signo del seno es cero.

        ADD R3, R3, #0
        BRz SENO_CERO

; Comprobar si el signo del seno es negativo.

        BRn SENO_NEGATIVO

; Si llegamos aqui, el signo es positivo.
; Por lo tanto, R1 conserva su valor original.

        BRnzp SENO_FINALIZADO


; ----------------------------------------------------------
; SENO NEGATIVO
; ----------------------------------------------------------

SENO_NEGATIVO

; Aplicar complemento a dos para cambiar el signo.

        NOT R1, R1
        ADD R1, R1, #1

        BRnzp SENO_FINALIZADO


; ----------------------------------------------------------
; SENO IGUAL A CERO
; ----------------------------------------------------------

SENO_CERO

; Forzar el resultado del seno a cero.

        AND R1, R1, #0


SENO_FINALIZADO


; ----------------------------------------------------------
; 2. APLICAR SIGNO AL COSENO
; ----------------------------------------------------------
    LD R5, ADAPT_PTR32
    BR ADAPT_SKIP32
ADAPT_PTR32 .FILL SIGNO_COSENO
ADAPT_SKIP32
        LDR R3, R5, #0

; Comprobar si el signo del coseno es cero.

        ADD R3, R3, #0
        BRz COSENO_CERO

; Comprobar si el signo del coseno es negativo.

        BRn COSENO_NEGATIVO

; Si llegamos aqui, el signo es positivo.
; Por lo tanto, R2 conserva su valor original.

        BRnzp COSENO_FINALIZADO


; ----------------------------------------------------------
; COSENO NEGATIVO
; ----------------------------------------------------------

COSENO_NEGATIVO

; Aplicar complemento a dos para cambiar el signo.

        NOT R2, R2
        ADD R2, R2, #1

        BRnzp COSENO_FINALIZADO


; ----------------------------------------------------------
; COSENO IGUAL A CERO
; ----------------------------------------------------------

COSENO_CERO

; Forzar el resultado del coseno a cero.

        AND R2, R2, #0


COSENO_FINALIZADO


; ----------------------------------------------------------
; 3. ACTUALIZAR LOS RESULTADOS EN MEMORIA
; ----------------------------------------------------------

; Guardar el seno definitivo en memoria.
    LD R5, ADAPT_PTR33
    BR ADAPT_SKIP33
ADAPT_PTR33 .FILL RESULTADO_SENO
ADAPT_SKIP33
        STR R1, R5, #0

; Guardar el coseno definitivo en memoria.
    LD R5, ADAPT_PTR34
    BR ADAPT_SKIP34
ADAPT_PTR34 .FILL RESULTADO_COSENO
ADAPT_SKIP34
        STR R2, R5, #0


; ----------------------------------------------------------
; FINALIZACION DE LA PRUEBA 8D
; ----------------------------------------------------------

        LD R0, ADAPT_EXIT_PTR
        JMP R0
ADAPT_EXIT_PTR .FILL ADAPT_FIN


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

; Ángulo original de entrada en Q3.12.
ANGULO_PRUEBA               .FILL #25736

; Constantes para determinar cuadrantes.
PI_SOBRE_2                  .FILL #6434
PI                          .FILL #12868
TRES_PI_SOBRE_2             .FILL #19302
DOS_PI                      .FILL #25736

; Referencias calculadas por la Prueba 7.
REFERENCIA_SENO_PRUEBA      .BLKW #1
REFERENCIA_COSENO_PRUEBA    .BLKW #1

; Signos calculados por la Prueba 7.
SIGNO_SENO                  .BLKW #1
SIGNO_COSENO                .BLKW #1


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

; ==========================================================
; RESULTADOS DE LA CONSULTA A LA TABLA
; ==========================================================

RESULTADO_SENO       .BLKW #1
RESULTADO_COSENO     .BLKW #1

; ==========================================================
; TABLA DE SENO EN FORMATO Q1.14
; 91 VALORES: DESDE 0 GRADOS HASTA 90 GRADOS
; ==========================================================

TABLA_SENO
        .FILL #0
        .FILL #286
        .FILL #572
        .FILL #857
        .FILL #1143
        .FILL #1428
        .FILL #1713
        .FILL #1997
        .FILL #2280
        .FILL #2563
        .FILL #2845
        .FILL #3126
        .FILL #3406
        .FILL #3686
        .FILL #3964
        .FILL #4240
        .FILL #4516
        .FILL #4790
        .FILL #5063
        .FILL #5334
        .FILL #5604
        .FILL #5872
        .FILL #6138
        .FILL #6402
        .FILL #6664
        .FILL #6924
        .FILL #7182
        .FILL #7438
        .FILL #7692
        .FILL #7943
        .FILL #8192
        .FILL #8438
        .FILL #8682
        .FILL #8923
        .FILL #9162
        .FILL #9397
        .FILL #9630
        .FILL #9860
        .FILL #10087
        .FILL #10311
        .FILL #10531
        .FILL #10749
        .FILL #10963
        .FILL #11174
        .FILL #11381
        .FILL #11585
        .FILL #11786
        .FILL #11982
        .FILL #12176
        .FILL #12365
        .FILL #12551
        .FILL #12733
        .FILL #12911
        .FILL #13085
        .FILL #13255
        .FILL #13421
        .FILL #13583
        .FILL #13741
        .FILL #13894
        .FILL #14044
        .FILL #14189
        .FILL #14330
        .FILL #14466
        .FILL #14598
        .FILL #14726
        .FILL #14849
        .FILL #14968
        .FILL #15082
        .FILL #15191
        .FILL #15296
        .FILL #15396
        .FILL #15491
        .FILL #15582
        .FILL #15668
        .FILL #15749
        .FILL #15826
        .FILL #15897
        .FILL #15964
        .FILL #16026
        .FILL #16083
        .FILL #16135
        .FILL #16182
        .FILL #16225
        .FILL #16262
        .FILL #16294
        .FILL #16322
        .FILL #16344
        .FILL #16362
        .FILL #16374
        .FILL #16382
        .FILL #16384


        .END
