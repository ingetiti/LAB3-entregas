
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
Tiene que estar ligeramente comentado (intentando que el programa se entienda de igual manera)  .
Se debe tener en cuenta que es necesario que sea fácil editar, borrar y agregar, instrucciones de la ISA.
Se deberá realizar enfocado a que se tiene que poder contar y medir factores como:
-  Cantidad de instrucciones ejecutadas
-  Lectura de memoria
-  Escritura en memoria
-  Ciclos ejecutados  

Se deberá poder iniciar un simulador en distintos modos de operación que serán monociclo, multiciclo y pipeline, donde por defecto se utilizara el modo monociclo.
Esto significa que las instrucciones tendrán que tener planteado un sistema para definir que realizan en cada parte del pipeline (Fetch, Decode, Execute, Memory, entre otras necesarias).
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

Para la pseudo operación `.EXTERNAL nombre_de_archivo-etiqueta`, que permite utilizar etiquetas de fuera del archivo actual se plantea lo siguiente como guía básica (que se puede cambiar, optimizar o replantear):  
Se hará posible implementando tablas de etiquetas tanto locales para el archivo que se esta ensamblando, como globales para utilizarse en todos los archivos del proceso de ensamblaje actual.  
Para cada archivo, en la primer etapa del ensamblador, se calculará el tamaño que va a utilizar el programa del archivo actual, ya que será necesario para poder calcular direcciones efectivas de archivos externos, debido a que estos se añaden consecutivos al programa actual y su dirección de inicio depende del tamaño del programa actual (en los archivos externos se ignora el .ORIG y se utiliza esta nueva dirección de inicio). Por lo tanto es necesario una tabla con las direcciones de inicio de los distintos programas y sus tamaños, para poderse agregar consecutivamente los programas externos.  
En la segunda etapa, se procederá a buscar todas las etiquetas y direcciones necesarias para el calculo de direcciones efectivas de las instrucciones. Estas se guardaran en una tabla correspondiente al archivo actual. Se tendrá en cuenta que las etiquetas que son declaradas con `.EXTERNAL nombre_de_archivo-etiqueta` se guardaran en una segunda tabla global al proceso de ensamblaje actual (para que puedan ser incluidas en otros de ser necesario), y se procederá a buscar en el directorio actual y subdirectorios el archivo especificado en el `.EXTERNAL` (con su extensión `.asm`). En caso de no encontrarse este archivo, se preguntara al usuario si tiene el programa necesario de ese archivo en formato texto, para poder utilizarlo. En caso de que se disponga del programa necesario, se realizara el ensamblaje del mismo agregando el binario de este abajo consecutivo al programa anterior agregando a la tabla de direcciones de inicio su tamaño.  
Ya en la tercer etapa de ensamblado, se deberá de tener en la tabla de etiquetas del archivo actual las necesarias para calcular todas las direcciones efectivas de las instrucciones.  
Las etapas son individuales de cada archivo, por lo que se realizan las etapas posibles en cada archivo antes de continuar con los siguientes archivos necesarios.  


### Sistema Operativo de la ISA

Tambien se deberá programar un sistema operativo que permita las llamadas TRAP, introducir datos por teclado, mostrar datos por monitor (consola), todo con un sistema de interrupciones simulado, registro de estado, pila de modo usuario y modo privilegiado manejada con el Registro 6, similar al que se define en el libro de la LC-3.
Este deberá contar con soporte desde el simulador, o estar integrado en el mismo (con la posibilidad de ser editado), para la implementación de las interrupciones.

