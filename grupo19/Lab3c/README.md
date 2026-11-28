# Benchmark original y optimizado: uso de los ensambladores y simuladores

## Proposito del proyecto

El benchmark de la calculadora se desarrolló originalmente para la ISA LC-3. En este proyecto se tomó esa implementación como referencia para diseñar una nueva ISA de 16 bits, junto con un ensamblador y un simulador funcional, y adaptar el benchmark para ejecutarlo en esa ISA buscando reducir el trabajo que requieren sus rutinas.

El proyecto permite ejecutar ambas versiones:

1. **Benchmark original:** fuentes escritas para LC-3, ejecutadas con el simulador LC-3 incluido.
2. **Benchmark adaptado/optimizado:** fuentes adaptadas a la nueva ISA, ensambladas a código máquina y ejecutadas con el simulador funcional de esa ISA.

## Estructura relevante

Ejecute los comandos desde la carpeta raíz del proyecto (la que contiene `assembler.py` y `simulator.py`).

```text
proyecto\
|-- assembler.py
|-- simulator.py
|-- lc3_simulator.py
|-- NUEVA_ISA.md
|-- benchmark_original\
|   |-- main_grupo27.asm
|   `-- lib\
|       `-- modulos LC-3 del benchmark y del menu
|-- benchmark_optimizado\
|   |-- main_grupo27.asm
|   `-- lib\
|       `-- modulos adaptados a la nueva ISA
`-- out\
    `-- objetos, mapas y metricas generadas
```

`benchmark_original` conserva la implementación LC-3 que sirve como referencia. `benchmark_optimizado` contiene la adaptación a la nueva ISA. Mantenga cada `main_grupo27.asm` junto a su propia carpeta `lib`: sus módulos externos y convenciones no deben mezclarse entre versiones.

## Requisitos

- Python 3.10 o posterior.
- No se requieren dependencias adicionales.
- PowerShell o una terminal compatible con los comandos de Python.

Compruebe Python desde la raíz del proyecto:

```powershell
python --version
```

## 1. Ejecutar el benchmark original en LC-3

El simulador LC-3 incluido es `lc3_simulator.py`. Recibe la carpeta del benchmark original, ensambla sus módulos LC-3 y ejecuta el bloque completo en modo automático:

```powershell
python lc3_simulator.py .\benchmark_original
```

También se puede indicar directamente el archivo principal:

```powershell
python lc3_simulator.py .\benchmark_original\main_grupo27.asm
```

El simulador busca los módulos `.EXTERNAL` desde la carpeta del fuente principal y sus subcarpetas, incluyendo `lib`. En la configuración predeterminada comprueba que `main` apunte a `programa_del_menu_completo`; si el programa está configurado para el menú manual o para otro bloque, detiene la ejecución con un error explicativo.

La salida contiene:

- texto producido por las operaciones;
- resultados finales de las 23 operaciones automáticas;
- cantidad de instrucciones LC-3 ejecutadas;
- tamaño de la imagen enlazada en **palabras LC-3**.

El límite predeterminado es de diez millones de instrucciones. Puede aumentarse así:

```powershell
python lc3_simulator.py .\benchmark_original --max-steps 50000000
```

Este comando es una herramienta de referencia para el benchmark: internamente ensambla y ejecuta las fuentes LC-3. No genera un objeto LC-3 para pasarlo a `simulator.py`.

## 2. Ensamblar el benchmark adaptado a la nueva ISA

El simulador de la nueva ISA no lee Assembly. Primero convierta el fuente adaptado a un objeto binario:

```powershell
python assembler.py .\benchmark_optimizado\main_grupo27.asm -f bin -o out\benchmark_optimizado.bin -I .\benchmark_optimizado\lib --map out\benchmark_optimizado.map
```

El ensamblador:

- lee el archivo de entrada en la nueva ISA;
- resuelve las directivas `.EXTERNAL` de manera recursiva;
- busca los módulos en la carpeta `lib` indicada con `-I`;
- enlaza código y datos en una imagen;
- produce el objeto para el simulador;
- genera opcionalmente un mapa de símbolos con `--map`.

No es necesario crear `out` manualmente: el ensamblador crea las carpetas padre necesarias para el objeto y el mapa. El simulador también crea las carpetas padre del archivo indicado con `--json`.

También puede generar un objeto hexadecimal:

```powershell
python assembler.py .\benchmark_optimizado\main_grupo27.asm -f hex -o out\benchmark_optimizado.hex -I .\benchmark_optimizado\lib --map out\benchmark_optimizado.map
```

El binario y el hexadecimal representan el objeto completo, incluida la cabecera de origen y el SP inicial.

## 3. Ejecutar el benchmark adaptado con el simulador de la nueva ISA

Después del ensamblado:

```powershell
python simulator.py out\benchmark_optimizado.bin
```

Para guardar métricas detalladas en JSON:

```powershell
python simulator.py out\benchmark_optimizado.bin --json out\metricas_optimizado.json
```

Para ocultar el texto crudo de la calculadora sin ocultar el informe:

```powershell
python simulator.py out\benchmark_optimizado.bin --hide-output --json out\metricas_optimizado.json
```

También puede ejecutar el objeto hexadecimal:

```powershell
python simulator.py out\benchmark_optimizado.hex --json out\metricas_optimizado.json
```

El simulador muestra resultados por operación cuando detecta los banners `==NOMBRE==` del menú automático. Además informa:

- instrucciones totales y mezcla de instrucciones;
- registros finales y PC;
- bytes de imagen, pila máxima y memoria total estimada;
- lecturas y escrituras de datos;
- métricas de cada operación.

El límite predeterminado es de diez millones de instrucciones:

```powershell
python simulator.py out\benchmark_optimizado.bin --max-instructions 50000000
```

## 4. Ejecutar ambas versiones, de principio a fin

Desde la raíz del proyecto, los comandos completos son:

```powershell
# Referencia: fuente original LC-3
python lc3_simulator.py .\benchmark_original

# Adaptación: ensamblar la nueva ISA y ejecutar su objeto
python assembler.py .\benchmark_optimizado\main_grupo27.asm -f bin -o out\benchmark_optimizado.bin -I .\benchmark_optimizado\lib --map out\benchmark_optimizado.map
python simulator.py out\benchmark_optimizado.bin --json out\metricas_optimizado.json
```

Los programas de ambos directorios están configurados para recorrer el bloque automático completo. Si se modifican las entradas, algoritmos o modo de ejecución, repita el flujo correspondiente; para la nueva ISA, siempre vuelva a ensamblar antes de ejecutar.

## 5. Cambiar las entradas automáticas

Los casos de prueba se encuentran en `programa_del_menu_completo`, dentro del `main_grupo27.asm` de cada versión. Cada caso usa cinco palabras:

```asm
.FILL #indice_operacion
.FILL primer_operando
.FILL segundo_operando
.FILL espacio_resultado
.FILL espacio_resultado
```

El número de operación selecciona la rutina; los siguientes campos contienen operandos y espacios de resultado. No todas las operaciones usan ambos operandos o ambas palabras de resultado. Respete el formato numérico indicado en los comentarios de cada caso, por ejemplo `Q3.12`, `Q7.8` o `Q15.16`.

Después de editar:

- Para el benchmark LC-3, vuelva a ejecutar `lc3_simulator.py`; este vuelve a ensamblar los fuentes.
- Para la nueva ISA, ejecute de nuevo `assembler.py` y después `simulator.py`.

## 6. Comparar los resultados

El simulador LC-3 informa instrucciones y memoria enlazada en palabras LC-3. El simulador de la nueva ISA informa instrucciones ejecutadas y memoria en bytes, además de pila, accesos de datos y mezcla de instrucciones. Por lo tanto:

- Compare primero el resultado numérico y el formato fijo de cada operación.
- No compare directamente las cifras de memoria como si tuvieran la misma unidad.
- El conteo de instrucciones sí sirve para observar el trabajo dinámico de cada implementación, pero debe interpretarse considerando que las ISA y sus instrucciones son diferentes.
- La salida de consola y la presentación pueden variar entre versiones.
- La adaptación a la nueva ISA busca optimizar el benchmark original, pero eso no implica que toda rutina use menos instrucciones ni que las aproximaciones numéricas sean idénticas en todos los casos.

Las pruebas diferenciales comparan resultados por operación y aceptan como máximo un LSB del formato Q correspondiente, para no tratar el redondeo de punto fijo como una discrepancia funcional. La multiplicación básica es una excepción al uso de LC-3 como referencia: con entradas `0x0DD4` y `0xF8C3`, el producto Q16.16 correcto es `-100.09185791015625`, y la nueva ISA lo calcula correctamente. LC-3 devuelve `-101.09185791` por un acarreo espurio en `benchmark_original/lib/g3_MultiplicacionSHIFTandADD.asm`: cuando ambos sumandos de la palabra baja son no negativos, la rutina toma el bit de signo del resultado como indicador de acarreo. Así, una suma como `0x4524 + 0x6EA0 = 0xB3C4` incrementa incorrectamente la palabra alta aunque no haya desbordamiento de 16 bits. La prueba valida esa operación contra el producto matemático, no contra el resultado erróneo de LC-3.

La reducción de argumento LC-3 en `benchmark_original/lib/g20_Cordic_reduccion_de_argumento.asm` también tiene un límite con signo: al evaluar `R0 - 6434` para entradas Q3.12 desde `-26335` hasta `-32768`, la resta puede desbordar el rango de 16 bits y seleccionar una rama incorrecta. El fuente LC-3 se conserva sin cambios; las pruebas de esos valores validan la salida de la nueva ISA contra la reducción esperada al intervalo `[-pi/2, pi/2]`, no contra la salida defectuosa de LC-3.

## 7. Archivos de resultados

Los comandos anteriores generan en `out`:

- `benchmark_optimizado.bin`: objeto de la nueva ISA;
- `benchmark_optimizado.map`: mapa de símbolos del enlazado;
- `metricas_optimizado.json`: métricas detalladas de la ejecución nueva.

El simulador LC-3 presenta sus resultados en la terminal y no tiene una opción CLI para exportarlos a JSON.

## 8. Pruebas del proyecto

Desde la raíz del proyecto:

```powershell
python -m unittest -v test_assembler test_isa
```

Estas pruebas verifican el ensamblador y el núcleo de la nueva ISA.

La suite `test_benchmark_translation.py` usa las carpetas `benchmark_original` y `benchmark_optimizado` para comprobar rutinas y comparar ambas implementaciones. Las comparaciones del benchmark se hacen por resultado de operación con tolerancia máxima de un LSB; la multiplicación básica se valida contra el producto matemático porque la rutina de referencia LC-3 tiene el error descrito arriba. Las pruebas de EXP y Taylor no dependen de la salida textual completa, y el marcador de entrada de Taylor admite diferencias de espacios. Los 11 casos pasan con las tolerancias definidas.

```powershell
python -m unittest -v test_benchmark_translation
```

## 9. Documentación técnica

- `NUEVA_ISA.md`: formatos, instrucciones, banderas, memoria, llamadas y convenciones de la nueva ISA.
- `ENSAMBLADOR.md`: formatos de salida, directivas y resolución de módulos externos.
- `assembler.py`: ensamblador y enlazador de la nueva ISA.
- `simulator.py`: simulador funcional de la nueva ISA.
- `lc3_simulator.py`: ensamblador interno y simulador de referencia para el benchmark LC-3.

## Errores frecuentes

### El simulador nuevo rechaza el archivo `.asm`

Es el comportamiento esperado. Ensamble primero para producir `.bin` o `.hex`:

```powershell
python assembler.py .\benchmark_optimizado\main_grupo27.asm -f bin -o out\benchmark_optimizado.bin -I .\benchmark_optimizado\lib
python simulator.py out\benchmark_optimizado.bin
```

### No se encuentra un módulo externo

Compruebe que se usa la carpeta `lib` correspondiente a esa versión:

```powershell
-I .\benchmark_optimizado\lib
```

Para el benchmark original, el comando LC-3 debe recibir la carpeta o el archivo de `benchmark_original`, no el directorio optimizado.

### El simulador LC-3 dice que no está habilitado el modo automático

El CLI de `lc3_simulator.py` ejecuta el bloque completo automático. Revise que `main` cargue en `R0` la dirección de `programa_del_menu_completo` y que la llamada al menú siga a continuación. Vuelva a ejecutar el comando después de guardar los cambios.
