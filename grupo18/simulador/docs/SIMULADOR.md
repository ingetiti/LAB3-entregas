# Manual de uso del simulador

Este documento explica cómo ejecutar programas binarios mediante el simulador del proyecto.

## 1. Requisitos

- Python 3.
- Biblioteca estándar de Python.
- Ejecutar los comandos desde la raíz del proyecto.

No es necesario instalar dependencias externas.

## 2. Ejecución básica

El simulador recibe como argumento un archivo binario generado previamente por el ensamblador.

La forma general de ejecución es:

```bash
python3 -m simulator ARCHIVO.bin
```

Por ejemplo:

```bash
python3 -m simulator 01_aritmetica_logica.bin
```

Al finalizar, el simulador informa el resultado de la ejecución y muestra un resumen.

## 3. Opciones disponibles

### 3.1. Limitar la cantidad de instrucciones

La opción `--max-steps` permite establecer un límite máximo de instrucciones ejecutadas:

```bash
python3 -m simulator programa.bin --max-steps 5000
```

Esto permite evitar ejecuciones excesivamente largas.

### 3.2. Proporcionar un archivo de entrada

La opción `--input-file` permite indicar un archivo desde el cual se obtendrán los datos de entrada del programa:

```bash
python3 -m simulator programa.bin --input-file entrada.txt
```

También es posible utilizar `-` para recibir los datos desde la entrada estándar:

```bash
python3 -m simulator programa.bin --input-file -
```

## 4. Información de salida

Al finalizar la ejecución, el simulador presenta información sobre el resultado y el estado de la ejecución.

El resumen incluye datos como:

- Estado de finalización.
- Cantidad de instrucciones ejecutadas.
- Cantidad de escrituras en memoria.
- Valor del contador de programa al finalizar.

La salida generada por el propio programa también se muestra durante la ejecución.

## 5. Errores y finalización

Una ejecución puede finalizar correctamente o informar un error.

Entre las situaciones que pueden impedir la ejecución se encuentran:

- Archivo binario inexistente o inaccesible.
- Archivo binario inválido.
- Entrada insuficiente o incorrecta.
- Superación del límite máximo de instrucciones.
- Errores detectados durante la ejecución.

Ante un error, se recomienda revisar el mensaje informado por el simulador y verificar el archivo de entrada.

## 6. Ejemplo de flujo completo

Desde la raíz del proyecto, se puede ensamblar y ejecutar un programa con los siguientes comandos:

```bash
python3 -m assembler 01_aritmetica_logica.asm
python3 -m simulator 01_aritmetica_logica.bin
```

El primer comando genera el archivo binario y el segundo lo carga y ejecuta.
