# JochISA · Laboratorio 3c

Grupo 15 — Lucca Santino Cruz, Jose Maria Pona y Lautaro Obregon.

## Correr el benchmark

Con Python 3.10 o superior, abrí una terminal en `lab3c` y ejecutá este comando.

```console
python simulador.py benchmark/benchmark_adaptado.obj
```

También podés abrir [JochISA.code-workspace](JochISA.code-workspace) como archivo de área de trabajo en VS Code. Con la extensión de Python instalada, elegí **Ejecutar benchmark** en **Ejecutar y depurar** y presioná **F5**.

El programa corre las 23 operaciones sin pedir datos por teclado y termina en `HALT`. En la última prueba, la conversión de Q3.12 a Q7.8 muestra `5.36328125` para la entrada `5.366210937`.

En la terminal deberían aparecer **288.001 instrucciones** en total (265.933 de usuario y 22.068 del sistema operativo, incluidos los servicios de `TRAP`). El benchmark ocupa **15.806 bytes** y el sistema operativo carga **204 bytes** aparte. Estas medidas excluyen los dos bytes de cabecera de cada `.obj`.

## Volver a ensamblar

El archivo principal está en `benchmark/main_grupo27.asm` y sus subrutinas están en `benchmark/lib/`. Para generar el `.obj` de nuevo, elegí **Ensamblar benchmark** en VS Code y presioná **F5**, o usá este comando desde `lab3c`.

```console
python ensamblador.py benchmark/main_grupo27.asm -o benchmark/benchmark_adaptado.obj
```

El simulador carga `so/servicios.obj` al arrancar. Si querés reconstruir ese archivo, corré también este comando.

```console
python ensamblador.py so/servicios.asm -o so/servicios.obj
```

## Visualizador

Abrí [visualizador.html](visualizador.html) en el navegador y elegí **Correr benchmark**. También hay ejemplos que podés ejecutar paso a paso para ver cómo cambian los registros. Para probar un programa con varios `.asm`, primero ensamblalo con Python y después abrí el `.obj` en el visualizador.
