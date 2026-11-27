
# Especificaciones del cómo realizar el simulador y ensamblador

### General

Se realizará un simulador de una microarquitectura de Computadoras en el lenguaje de programacion Python, basada en la LC-3 del libro "introduction to computing systems" de yale n. patt, sanjay j. patel, tercera edición, pero con cambios especificados en el apartado de más abajo.  

### Simulador

Se deberá poder iniciar un simulador, y pasarle tanto una lista de valores o un archivo de texto con los siguientes formatos:  
- Numéricos (números int del lenguaje python)
- Binario (representado en texto con 8 caracteres '0', '1')
- Hexadecimal (representado en texto con 2 caracteres)
Además se esperara que el primer y segundo valor pasado (tomados combinados como una dirección de 16 bits) sea la ubicación de memoria donde comienza el programa (lo cual se podrá desactivar pasándole una bandera especifica con ese fin).
  
El programa del simulador puede realizarse en módulos pero se intentara mantener lo mas organizado posible sin crear un módulo para cada pequeña parte del proyecto.  
Tiene que estar ligeramente comentado (intentando que el programa se entienda de igual manera).  
Se debe tener en cuenta que es necesario que sea fácil editar, borrar y agregar, instrucciones de la ISA.  
Se deberá realizar enfocado a que se tiene que poder contar y medir factores como:
-  Cantidad de instrucciones ejecutadas
-  Lectura de memoria
-  Escritura en memoria
-  Ciclos ejecutados  

Se deberá poder iniciar un simulador en distintos modos de operación:
- Mono ciclo o Un solo siclo por instrucción.
- Multi ciclo, donde se ejecutan solo las etapas necesarias de cada instrucción.
- Pipeline, que ejecuta en simultaneo etapas distintas de instrucciones consecutivas.

Esto significa que las instrucciones tendrán que tener planteado un sistema para definir que realizan en cada etapa del pipeline (Fetch, Decode, Execute, Memory, entre otras necesarias).  
Además de un sistema para elegir que ocurre cuando se toman saltos condicionales e incondicionales como diferentes predictores de salto entre los cuales pueden estar *Salto siempre tomado*, *salto nunca tomado*, un predictor de 1 bit, o de 2 bits (de momento mantenerlo simple pero expandible, para que se pueda agregar un predictor de salto mas complejo con historial de saltos y demás).  
Todas las opciones del modo del simulador y del predictor de saltos tienen que poderse configurar de alguna manera al iniciar el simulador (ya sea antes o después, o por medio de banderas pasadas al propio simulador). Por defecto si no se selecciona ninguna, se asume que se quiere ejecutar en modo Mono ciclo.  
No es necesario una interfaz grafica (utilizando la consola seria mas que suficiente de momento).


#### ISA a implementar en el Simulador (de momento)

La ISA esta definida en el archivo `ISA-G27.pdf` donde se especifican mnemónico (Nombre de la instrucción), Binario (contando con el opcode y todas las partes de los operandos asi tambien como una pequeña descripción de que realizara a grandes rasgos la instrucción)

La memoria tendrá que ser direccionada por Byte, lo que significa que se contara con $2^{16}$ espacios de 8 bits.  
Las instrucciones ocupan 2 Bytes, osea 1 Word.  
Se dispondrá de un banco de 8 Registros generales de 16 bits cada uno.  
Además se tendrá un registro de condiciones nzp (igual al de la LC-3) y un registro de condiciones oc (overflow, carry) modificables según el resultado de instrucciones.  
La ISA se define Little-Endian lo que significa que una Word compuesta por 2 Bytes tendrá su parte alta a la izquierda y la parte baja a la derecha (un registro de 16 bits [15..0] se carga con dos Bytes consecutivos en memoria como [15..8] y [7..0])


### Ensamblador
Se deberá poder ensamblar una cadena de texto, o un archivo de texto, con el programa en lenguaje ensamblador correspondiente a la ISA que estamos trabajando.


#### ISA a implementar en el Ensamblador (de momento)
La ISA esta definida en el archivo `ISA-G27.pdf` con ejemplos del lenguaje ensamblador correspondiente a las instrucciones y como quedaría en binario las instrucciones correspondientes.  
Se deberá de poder elegir como se quiere el archivo de salida ya ensamblado, y si se quiere el archivo de links (de etiquetas), por medio de banderas, pero por defecto entregara tanto el archivo compilado con caracteres hexadecimales (líneas de 2 caracteres) con en la primer y segunda línea la ubicación de memoria en la que comienza el programa.  
Deberá reconocer las instrucciones, argumentos (tanto separadas con coma ',' como separadas únicamente por espacios en blanco sin coma), e ignorar los comentarios (texto que sigue despues de un punto y coma ';' hasta el final de linea).  


Se dispondrán de las siguientes pseudo operaciones:
- `.ORIG` define el inicio en memoria del programa (solo afecta al programa principal)
- `.END` define el final del programa en el archivo actual.
- `.EXTERNAL` define etiquetas que se encuentran en otros archivos o programas, que serán utilizadas en el programa actual.
- `.FILL` define 1 Word de memoria.
- `.FILLB` define 1 Byte de memoria.
- `.BLKW` define un numero de Words en blanco.
- `.BLKB` define un numero de Bytes en blanco.
- `.STRINGZ` define una cadena de caracteres de 8 bits seguidos por un espacio en blanco (que actúa como carácter '\0').
En caso de haber 1 `.FILLB` (o un dato de 8 bits) y a continuación un dato de 1 Word (instrucción, dato de 16 bits, etc.), se llenara con un padding de un Byte (8 bits en 0).
En caso de haber 2 `.FILLB` (o datos de 8 bits) consecutivos actuaria correctamente llenando únicamente 16 bits de memoria.

Para la pseudo operación `.EXTERNAL`:
- Se espera que la sintaxis sea `.EXTERNAL nombre_de_archivo-etiqueta`
  - *nombre_de_archivo* corresponde al nombre que tendría un archivo dentro del directorio actual o subdirectorios dentro de este (sin el `.asm` que se supone implícito) (digo tendría ya que se puede buscar el código fuente en ensamblador del modulo tanto como archivos, como pedirlo como texto al usuario)
  - *etiqueta* corresponde a la etiqueta vinculada a una dirección de memoria que tendrá una línea del modulo externo una vez todos los módulos estén ensamblados uno tras otro en memoria.
- Se ensamblaran todos los módulos, continuos uno tras otro en memoria después del programa principal.
- Para ensamblar un método que se propone (no es necesario seguirlo tal cual, puede ser optimizado y cambiado parcial o totalmente, si se puede implementar un mejor método de ensamblado), es de realizar dos etapas (lecturas) de cada archivo, donde se generan tablas de datos necesarios y luego se ensambla al formato especifico:
  - La primer etapa, se encarga de buscar todas las direcciones efectivas de las etiquetas necesarias y calcular el tamaño que ocupara en la memoria, el programa actual. Por lo tanto habrá una tabla global con nombre de archivo, dirección de inicio, y tamaño total en memoria, asi tambien como una sub tabla con las etiquetas y direcciones de memoria correspondientes presentes en ese archivo.
  Cada vez que se encuentre `.EXTERNAL` se tendrá que agregar a la tabla el nombre de archivo, para luego, antes de pasar a la segunda etapa, buscar el archivo correspondiente en el directorio actual o subdirectorios, y de no estar presente se puede pedir al usuario que brinde como texto el contenido que tendría este archivo. Cuando se consiga el programa de este archivo, se procede a procesar la primera etapa de este archivo para completar sus datos (teniendo en cuenta que la dirección de inicio será a continuación del archivo anterior, y que este tambien puede tener `.EXTERNAL` a mas archivos).
  - La segunda pasada se encarga de ensamblar las instrucciones y datos del programa actual utilizando los datos obtenidos en las tablas en la primera etapa (que deberían ser suficientes para calcular todos los valores de dirección efectiva que necesiten las instrucciones).



### Sistema Operativo de la ISA

Tambien se deberá programar un sistema operativo que permita las llamadas TRAP, introducir datos por teclado, mostrar datos por monitor (consola), todo con un sistema de interrupciones simulado, registro de estado, pila de modo usuario y modo privilegiado manejada con el Registro 6, similar al que se define en el libro de la LC-3.
Este deberá contar con soporte desde el simulador, o estar integrado en el mismo (con la posibilidad de ser editado), para la implementación de las interrupciones.

