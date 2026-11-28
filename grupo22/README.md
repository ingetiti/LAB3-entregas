# Grupo 22 · SIN y COS por tabla

**Consigna:** Se debe tener una sola tabla; para la otra función, aplicar un desplazamiento de pi/2

## Objetivo
- El objetivo del presente proyecto consiste en elaborar una tabla de consulta capaz de almacenar los resultados de seno y coseno en un rango de 0 grados hasta 90 grados. Estos valores consultados se encuentran precargados en la tabla para facilitar el uso al usuario y la incorporacion de una mejor optimizacion en la nueva ISA planteada.

## Integrantes
<!-- Completar en el primer Pull Request -->
- Arce, Andres Agustin (@agxsh)
- Becker, Ramón Angel David (@Dav-2005)
- Cuadra, Josias (@jcaseli)

## Archivos Assembly
<!-- Qué archivo hace qué -->
- `P1_armado_tabla_enAssembly.asm`: A modo de prueba, verifica la creación de la tabla con los valores de Seno en formato Q1.14 (ya escalados) para su futura implementación en el programa final.
- `P2_Seleccion_dinamica_deIndice.asm`: A modo de prueba, verifica el funcionamiento de LDR para la obtención de un ángulo elegido por el usuario (almacenado en un registro) el cual puede variar en tiempo de ejecución.
- `P3_PruebaVariablesTemporales.asm`: A modo de prueba, verifica la reserva de espacio de memoria con .BLKW para uso de datos temporales.
- `P4_DetCuadrante_CasoNormal.asm`: A modo de prueba, recibe el ángulo en radianes ingresado por el usuario y determina en que cuadrante esta, sin considerar los valores que se encuentran sobre los ejes (denominados "casos especiales").
- `P5_DetCuadrante_CasoNormalyEspecial.asm`: A modo de prueba, determina el cuadrante por el ángulo ingresado en radianes considerando inclusive casos especiales: 0°, 90°, 180°, 270°, y 360°. Dichos casos se identifican con 0 para representar que se encuentran sobre los ejes, y que se tratan de angulos no pertenecientes a un cuadrante en particular.
- `P6_DetIndice_Seno_Coseno_casosNormales.asm`: A modo de prueba, habiendo verificado el cuadrante del ángulo ingresado por el usuario, determina el índice correspondiente para el seno aprovechando la propiedad de la simetría (obteniendo el ángulo de referencia), y también para el coseno mediante la propiedad de la cofusión (90° - ángulo de referencia).
- `P7_DeterminarSignos.asm`: A modo de prueba, teniendo determinado el cuadrante en donde se sitúa el ángulo ingresado por el usuario, aplica los signos correspondientes tanto para el seno como para el coseno. En caso de que se trate de un caso especial (0°, 90°, 180°, 270°, o 360°) los signos establecidos en 0 representaran el mismo resultado, ya sea para seno o coseno.
- `P8F1_Obtener_Indice_Seno.asm`: A modo de prueba, realiza la conversión necesaria para obtener el índice correspondiente del seno a partir del ángulo en radianes ingresado por el usuario.
- `P8F2_Obtener_Indice_Seno_Coseno.asm`: A modo de prueba, realiza la conversión para obtener el índice tanto del seno como del coseno a partir del ángulo en radianes ingresado por el usuario.
- `P8F3_ObtenerIndices_GuardarValores.asm`: A modo de prueba, una vez obtenido los índices correspondientes, obtiene los resultados directamente de la tabla.
- `P8F4_Integracion_De_Pruebas1a8.asm`: A modo de prueba, aplica los signos correspondientes y los resultados correctos al ángulo ingresado por el usuario.
- `Tabla_SIN_y_COS.asm`: Integra las funciones y verificaciones realizadas en los archivos de prueba anteriores, validando y comprobando el funcionamiento unificado de cada una en un mismo archivo.

## Archivos C++
- `P1_armado_tabla_enC++.cpp`: A modo de prueba, realiza la conversión a Q1.14 e imprime la tabla a importar en Assembly.
- `P2_Determinar_Cuadrante.cpp`: A modo de prueba, determina el cuadrante, el ángulo de referencia, y casos especiales, para la equivalencia en Assembly.
- `P3_Prueba_indices_A_vs_B.cpp`: A modo de prueba, verifica el margen de error entre una solución de reducción y la conversión en variable temporal de radianes a grados.
- `P4_Conversion_Grados.cpp`: A modo de prueba, determina el resultado de la conversión de radian a grados, para la obtención del indice de la tabla.
- `P5_Interpolacion.cpp`: A modo de prueba, determina la interpolación para ángulos con decimal, y su margen de error.
- `P6_Prueba_Integral.cpp`: A modo de prueba, unifica las pruebas anteriores para comprobación de resultados generales.
- `P7_Prueba_Demostrativa.cpp`: A modo de prueba, integra las validaciones con una interfaz simulando el funcionamiento de la tabla incorporada en la nueva ISA.
- `Tabla.h`: Integra todas las funciones desarrolladas en C++ para su próximo pasaje a Assembly. 

## Cómo probarlo
<!-- Pasos para ensamblar y ejecutar, y un ejemplo de entrada y salida -->
- A través del archivo Tabla_SIN_y_COS.asm se podrá establecer el ángulo a probar (en radian) en formato Q3.12, en la linea 968 se encuentra el espacio reservado "ANGULO_PRUEBA", desde este espacio puede modificar el valor que recibirá el programa. Al integrarlo en la nueva ISA este valor será recibido a través del Registro 0, mientras que, para facilitar su prueba de testeo de forma aislada puede asignar un valor en Q3.12 al espacio "ANGULO_PRUEBA" y comprobar el funcionamiento de la tabla. En el registro 1 se encontrara el valor resultante para Seno, mientras que para el registro 2 se encontrara el valor resultante para Coseno, ambos con sus signos correspondientes. En caso de que sea un ángulo sobre un eje alguno de los dos valores (ya sea Seno o Coseno) tendrá como valor 0, mientras que el otro un 1 con su signo correspondiente. Desafortunadamente, no se ha implementado la interpolación debido a falta de tiempo.

REPORTE DE ERROR DE BENITEZ ALDO.

VERIFICAR EL SENO PARA EL MÉTODO POR TAYLOR, VERIFIQUÉ POR EJEMPLO SEN(6.28) Y ARROJA UN VALOR ERRÓNEO.
