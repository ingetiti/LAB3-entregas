# Lab 3c · Grupo 9

Simulador funcional y ensamblador para MT-ISA: Modern Teaching Instruction Set Architecture . El benchmark de la calculadora fue integrado por el Grupo 27 con aportes de otros grupos y adaptado a MT-ISA por el Grupo 9.

## Preparación

Extraé el ZIP y abrí una terminal en la carpeta `Lab3c_Grupo9_Entrega`. Se requiere Python 3.10 o superior. En Windows podés usar `py -3` en lugar de `python`. Para la interfaz gráfica se requiere Tkinter.

## Ejecutar el benchmark incluido

```sh
python simulator.py build/complete/v2.bin --target lab3c-v2
```

La consola muestra los resultados del benchmark completo. La ejecución termina con 11.567 instrucciones. El simulador muestra las métricas al finalizar.

## Usar la interfaz gráfica

```sh
python demo_gui.py
```

Al abrirse, el simulador carga el benchmark de Lab 3c v2. Presioná **Ejecutar** para correrlo o **Paso** para avanzar una instrucción. Para cargar el binario manualmente, elegí **lab3c-v2** y usá **Abrir binario** con `build/complete/v2.bin`.

## Volver a ensamblar el benchmark

```sh
python assembler.py ported/main_grupo27.asm --target lab3c-v2 -I optimized_v2 -I optimized -I ported -o benchmark_reensamblado.bin
python simulator.py benchmark_reensamblado.bin --target lab3c-v2
```

El orden de las opciones `-I` selecciona los módulos que se usaron para generar el binario incluido. El archivo `benchmark_reensamblado.bin` queda en la carpeta de la entrega y se puede abrir también desde la interfaz gráfica.
