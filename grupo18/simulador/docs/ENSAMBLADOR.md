# Manual de uso del ensamblador

Este documento explica cómo utilizar el ensamblador del proyecto desde la terminal.

## 1. Requisitos

- Python 3.
- Biblioteca estándar de Python.
- Ejecutar los comandos desde la raíz del proyecto.

No es necesario instalar dependencias externas.

## 2. Ejecución

El ensamblador se ejecuta mediante el módulo `assembler`:

```bash
python3 -m assembler ARCHIVO.asm
```

El argumento obligatorio es la ruta del archivo fuente que se desea procesar.

Por ejemplo:

```bash
python3 -m assembler 01_aritmetica_logica.asm
```

Si el proceso finaliza correctamente, se genera un archivo binario con el mismo nombre base y extensión `.bin`.

En el ejemplo anterior, el resultado es:

```text
01_aritmetica_logica.bin
```

## 3. Elegir el archivo de salida

Es posible especificar un nombre diferente para el archivo binario mediante la opción `-o`:

```bash
python3 -m assembler 04_memoria.asm -o memoria.bin
```

En este caso, el resultado se guarda en `memoria.bin`.

## 4. Resultado del ensamblado

Cuando el proceso finaliza correctamente, el ensamblador muestra un resumen que incluye:

- Archivo fuente procesado.
- Archivo binario generado.
- Dirección de origen.
- Tamaño del archivo generado.
- Dirección final del contenido ensamblado.

Ejemplo:

```text
--- Resumen del ensamblado ---
Fuente:            01_aritmetica_logica.asm
Binario:           01_aritmetica_logica.bin
Origen:            0x3000
Tamaño:            144 bytes
Dirección final:   0x3090 (primera dirección libre)
```

## 5. Errores

Si el archivo fuente no puede procesarse, el ensamblador informa el error correspondiente y finaliza con un código de salida distinto de cero.

Entre las situaciones que pueden producir errores se encuentran:

- Archivo fuente inexistente o inaccesible.
- Errores de sintaxis.
- Referencias o símbolos no válidos.
- Valores u operandos fuera de los límites admitidos.
- Problemas al escribir el archivo de salida.

Se recomienda revisar el mensaje informado por el programa antes de volver a ejecutar el ensamblado.

## 6. Ejemplo de flujo completo

Desde la raíz del proyecto:

```bash
python3 -m assembler 01_aritmetica_logica.asm
python3 -m simulator 01_aritmetica_logica.bin
```

El primer comando genera el archivo binario y el segundo lo ejecuta mediante el simulador.
