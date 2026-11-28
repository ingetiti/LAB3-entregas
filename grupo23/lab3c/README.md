# Grupo 23 · Lab 3c · LOVELACE

**LOVELACE** es la ISA de 16 bits del Grupo 23. Su nombre es un homenaje a Ada Lovelace, que en 1843 escribió
el primer algoritmo pensado para ejecutarse en una máquina.

Integrantes: De Los Santos, Dahiara Claribel · Kamchem, Melina · Wereszczuk, Danna Maira

## Resumen

| | LC-3 | LOVELACE | |
|---|---:|---:|---|
| Instrucciones del programa | 357 505 | **17 905** | **19,97× menos** |
| Instrucciones con el sistema operativo | 379 579 | **28 855** | 13,15× menos (SO simulado en assembly) |
| Ciclos de reloj del programa (modelo multiciclo) | 1 333 071 | **93 454** | **14,26× menos** (CPI 5,22) |
| Memoria del programa | 15 792 B | **11 980 B** | 24,1 % menos |

- **Salida idéntica a la LC-3, carácter por carácter, en las 23 operaciones** de la calculadora. La interfaz
  gráfica lo comprueba al terminar y lo muestra operación por operación.
- **Interfaz gráfica** (`python simulador/interfaz.py`): ejecución continua o paso a paso, puntos de parada,
  ciclos y etapas de cada instrucción, memoria escrita resaltada y verificación contra la LC-3.
- **Reproducible:** el `.asm` entregado, ensamblado con el comando de la sección 3, genera exactamente la imagen de
  `benchmark/`.

Instructivo para ejecutar el simulador y el ensamblador de LOVELACE con el benchmark de la cátedra
(benchmark definitivo del 17/11/2026: programa principal del Grupo 27 con los módulos de todos los grupos).

## Contenido

| Carpeta / archivo | Qué es |
|---|---|
| `simulador/simulador.py` | Simulador funcional: ejecuta la imagen `.hex` o `.bin` (no acepta assembly) |
| `simulador/interfaz.py` | **Interfaz gráfica** del simulador (mismo núcleo y mismas cifras que `simulador.py`) |
| `simulador/ensamblador.py` | Ensamblador: traduce el assembly a `.hex`, `.bin`, `.sym` (símbolos) y `.map` (mapa de memoria) |
| `simulador/isa.py`, `optimizador.py`, `eliminar_muerto.py` | Módulos que usan el ensamblador y el simulador |
| `simulador/so_g23.hex` (`.bin`, `.asm`) | Sistema operativo (servicios `TRAP`); el simulador lo carga solo |
| `benchmark/benchmark_g23.hex` y `.bin` | **Benchmark ya ensamblado**, listo para el simulador |
| `benchmark/benchmark_g23.sym` y `.map` | Símbolos y mapa de memoria del benchmark ensamblado |
| `benchmark/main_benchmark.asm` y `benchmark/lib/` | **Los `.asm` que se usaron para ensamblar** el benchmark |
| `ejemplos/eco_teclado.asm` (y `.hex`) | Programa corto que lee el teclado: sirve para probar la consola de la interfaz |
| `ejemplos/calculadora.asm` (y `.hex`) | El mismo benchmark con el menú de la calculadora **por teclado** (sin el bloque automático) |
| `benchmark/salida_referencia_lc3.txt` | Salida del mismo benchmark en la LC-3 (simulador web): la interfaz compara contra ella |
| `benchmark/cadenas_empaquetadas.json` | Lista de cadenas que usa la opción `-S` del ensamblador |

## Requisitos

Python 3.10 o superior. No hace falta instalar ninguna biblioteca.

Todos los comandos se ejecutan **desde esta carpeta** (la del grupo).

## 1. Ejecutar el benchmark ya ensamblado

```
python simulador/simulador.py benchmark/benchmark_g23.hex
```

El simulador muestra la salida de la calculadora (las 23 operaciones del benchmark) y al final:

```
Instrucciones ejecutadas: 28855  (programa 17905, SO 10950)
Memoria: 11980 bytes = 5990 palabras  x3000-x5ECB
```

- **Instrucciones ejecutadas:** el total y, entre paréntesis, las del programa (un `TRAP` cuenta como una
  instrucción, igual que el simulador web del Grupo 8) y las del sistema operativo que atiende los `TRAP`.
  En la LC-3 el mismo benchmark ejecuta 379 579 (357 505 del programa y 22 074 del sistema operativo).
- **Memoria:** bytes que ocupa la imagen del programa (en la LC-3, 15 792 bytes = 7896 palabras).
- Después se lista cuántas veces se ejecutó cada instrucción.

Con la imagen binaria el resultado es el mismo:

```
python simulador/simulador.py benchmark/benchmark_g23.bin
```

## 2. Interfaz gráfica

```
python simulador/interfaz.py
```

Abre el benchmark ya ensamblado (`benchmark/benchmark_g23.hex`); con **Abrir…** se puede elegir otra imagen
`.hex`/`.bin` o un `.asm`, que se ensambla automáticamente. Usa Tkinter, que viene con Python en Windows.

- **Ejecutar / Pausar**, **Paso** (una instrucción; un `TRAP` cuenta como una), **Paso ×10**, **Reiniciar** y
  velocidad (lenta, media, rápida o máxima).
- **Programa:** listado desensamblado con las etiquetas del `.sym`; la instrucción actual se resalta.
  **Doble clic** en una línea pone o quita un punto de parada; al seleccionarla se ve su codificación en bits.
- **Ejecutar hasta:** corre hasta una etiqueta (por ejemplo `TODEC`) o una dirección (`x3100`).
- **Registros** R0–R7, PC, banderas N Z P C V y modo (usuario o sistema operativo); se resaltan los que
  cambiaron en el último paso.
- **Memoria:** ocho palabras por línea desde una dirección o etiqueta, con su texto; el botón **Pila (R6)**
  muestra la pila. Las palabras que escribió la última instrucción se **resaltan**, y con **Seguir escrituras**
  la vista va sola a la última dirección escrita (por ejemplo, se ve cómo `PUSH` llena la pila).
- **Ciclos de reloj:** las métricas muestran los ciclos del programa y del SO y el CPI con el modelo multiciclo
  del informe (cada instrucción usa solo las etapas IF, ID, EX, MEM y WB que necesita; MUL y DIV secuenciales).
  **Paso** informa los ciclos y las etapas de la instrucción ejecutada, y la pestaña **Ciclos** los reparte por
  clase de instrucción. Con el benchmark completo: 93 454 ciclos del programa (CPI 5,22), 44 397 del SO y
  14,26× menos ciclos que la LC-3 (1 333 071).
- **Consola:** salida del programa; si el programa lee del teclado, se hace clic en la consola y se escribe.
  Para probarlo: **Abrir…** → `ejemplos/eco_teclado.hex` → **Ejecutar**, escribir un nombre y apretar Enter.
  La calculadora completa por teclado está en `ejemplos/calculadora.hex`: por ejemplo `7` (multiplicación),
  `1` (BASIC), `3` Enter, `4` Enter muestra `12`; cualquier tecla vuelve al menú y `d` sale.
- **Métricas:** instrucciones y ciclos del programa y del SO, memoria y comparación con la LC-3.
- **Verificación:** al terminar el benchmark, la interfaz compara la salida con la de la LC-3, operación por
  operación, y muestra el resultado de cada una en las dos máquinas. Con el benchmark entregado:
  **✔ salida idéntica a la LC-3, carácter por carácter: 23 de 23 operaciones**. La pestaña
  **Estadísticas** muestra, al terminar, las instrucciones por tipo y por módulo.

Al ejecutar el benchmark completo muestra las mismas cifras que la línea de comandos: 28 855 instrucciones
(programa 17 905, SO 10 950) y 11 980 bytes.

## 3. Ensamblar el benchmark

```
python simulador/ensamblador.py benchmark/main_benchmark.asm -L benchmark/lib -o benchmark/benchmark_g23 -O -D -S benchmark/cadenas_empaquetadas.json
```

- `-L benchmark/lib`: carpeta de los módulos que se enlazan con `.EXTERNAL`.
- `-o benchmark/benchmark_g23`: nombre de salida (sin extensión); genera `.hex`, `.bin`, `.sym` y `.map`.
  Los dos primeros bytes de la imagen son la dirección de origen (`30 00` para x3000).
- `-O`, `-D` y `-S` son optimizaciones del ensamblador (mirilla, eliminación de código sin uso y cadenas
  empaquetadas). Con las tres se obtiene exactamente la imagen entregada en `benchmark/`; `-D` deja además el
  detalle de lo eliminado en `benchmark/benchmark_g23_muerto.txt`.

También se puede ensamblar sin optimizaciones; la salida de la calculadora es la misma:

```
python simulador/ensamblador.py benchmark/main_benchmark.asm -L benchmark/lib -o benchmark/sin_opciones
python simulador/simulador.py benchmark/sin_opciones.hex
```

(da 32 419 instrucciones en total, 18 699 del programa, y 14 780 bytes).

## 4. Otras opciones del simulador

| Opción | Qué hace |
|---|---|
| `--map benchmark/benchmark_g23.map` | Agrega las instrucciones ejecutadas por módulo |
| `--teclado "texto"` | Entrada de teclado para los programas que leen (`\n` = Enter) |
| `--desensamblar` | Lista la imagen en assembly, con las etiquetas del `.sym` |
| `--traza N` | Muestra las primeras N instrucciones ejecutadas y los registros que cambian |
| `--depurar` | Depurador paso a paso: puntos de parada, registros y memoria (`h` muestra la ayuda) |
| `--perfil archivo.json` | Guarda las métricas en un archivo JSON |
| `--max N` | Límite de instrucciones (para detectar lazos infinitos) |

Ejemplo:

```
python simulador/simulador.py benchmark/benchmark_g23.hex --map benchmark/benchmark_g23.map
```

Si el programa lee o escribe una palabra en una dirección impar, o salta a una dirección impar, el simulador
se detiene y muestra una excepción con la dirección.

## Repositorio completo

El repositorio completo del grupo, con el porte desde la LC-3, las 81 pruebas de la ISA, la prueba diferencial de
las subrutinas contra la LC-3, el modelo de ciclos y la verificación automática (`python construir.py`), está en
GitHub (`dahizz/lab3c-isa-g23`, con acceso de la cátedra). La documentación detallada de la ISA y el informe se
entregan hasta el martes 1/12/2026, como indicó la cátedra.
