# LC10: instructivo para correr el ensamblador y el simulador

Laboratorio 3 (parte c) de Arquitectura de Computadoras, UNaM. Grupo 10: Benitez, Denis; Silvero Zapani, Matias; Pintos, Daiana. Tutor: Dr. Ing. Aldo Benitez.

Esta carpeta trae el simulador funcional de la ISA LC10 con su ensamblador, el benchmark del curso ya ensamblado y funcionando, y los `.asm` con que se ensambla. Todo está en Python y usa solo la biblioteca estándar; la ventana gráfica usa tkinter. La documentación de la ISA y el informe del laboratorio se entregan aparte.

## Qué hay en la carpeta

```
benchmark.py            arma y corre el benchmark (ensambla los .asm de asm/opt10 y lo ejecuta en el simulador)
benchmark/              el benchmark ya ensamblado: benchmark_lc10.hex y benchmark_lc10.bin,
                        y salida_simulador.txt (lo que imprime al ejecutarlo)
asm/opt10/              los .asm del benchmark: main_grupo27.asm (programa principal) y los 37 módulos
asm/hola.asm            ejemplo mínimo
asm/main_division.asm   ejemplo con módulo: programa principal que llama a asm/division.asm
lc10/                   el simulador y el ensamblador (isa.py, assembler.py, simulator.py, image.py),
                        el sistema operativo (os_lc10.asm, system.py) y la ventana (gui.py, session.py, syntax.py)
lc10_gui.pyw            abre la ventana (en Windows, doble clic)
```

## Requisitos

Python 3.12 o superior, sin instalar nada más. La ventana necesita tkinter (en Windows viene con el instalador de Python; en Linux, el paquete `python3-tk`). Los comandos de abajo se corren desde esta carpeta (`lab3c`). En Windows se usa `python`; en Linux, `python3`.

## 1. Correr el benchmark

```
python benchmark.py
```

Ensambla `asm/opt10/main_grupo27.asm` con sus 37 módulos, lo ejecuta (modo automático: las entradas son el bloque `.FILL` del programa principal) e imprime todo lo que escribe el menú. Al final muestra:

```
LC10 · 15.822 usuario + 10.901 SO = 26.723 instrucciones · 4963 palabras · x3000–x56C5
```

Son las instrucciones del programa de usuario, las de las rutinas del sistema operativo que resuelven los TRAP (se cuentan aparte) y su suma, más las palabras de la imagen y su rango de direcciones.

El mismo benchmark ya ensamblado se ejecuta directamente con el simulador, que recibe un archivo y no assembly:

```
python -m lc10.simulator benchmark\benchmark_lc10.hex
python -m lc10.simulator benchmark\benchmark_lc10.bin
```

El resultado tiene que coincidir con `benchmark\salida_simulador.txt`.

Otras formas de usar `benchmark.py`:

| Comando | Para qué |
| --- | --- |
| `python benchmark.py RUTA\main_grupo27.asm` | usar otro programa principal (por ejemplo el que entregue la cátedra) con sus entradas |
| `python benchmark.py --interactivo --entrada "7213.25\n-7.5\n d"` | el menú con teclas en lugar del bloque automático (`\n` es Enter) |
| `python benchmark.py --entrada-archivo teclas.txt --interactivo` | lo mismo, con las teclas en un archivo |
| `python benchmark.py -o programa.hex` | guarda además la imagen ensamblada (`.hex`, `.bin`, `.dec` o `.bits`) |
| `python benchmark.py RUTA\main_grupo27.asm --lc3 RUTA\lc3-project` | además lo corre en el simulador de la LC-3 de la cátedra y compara la salida |

## 2. Ensamblar un programa

```
python -m lc10.assembler asm\hola.asm -o hola.hex --listing
```

Con módulos (el primer archivo es el programa principal; los demás son módulos sin `.ORIG`, que se llaman con `.EXTERNAL MODULO-ETIQUETA`, donde `MODULO` es el nombre del archivo en mayúsculas):

```
python -m lc10.assembler asm\main_division.asm asm\division.asm -o div.hex --map
```

| Opción | Qué hace |
| --- | --- |
| `-o ARCHIVO` | archivo de salida (por defecto, `<principal>.hex`) |
| `-f bin\|hex\|dec\|bits` | formato de salida (por defecto, el de la extensión de `-o`) |
| `--listing` | muestra el listado: dirección, palabra y línea fuente |
| `--map` | muestra los módulos y los símbolos con sus direcciones |

La salida lleva la dirección de origen en los dos primeros bytes (o en la primera palabra, en los formatos de texto). Los errores se informan con archivo y número de línea.

## 3. Ejecutar en el simulador

```
python -m lc10.simulator hola.hex
```

Muestra lo que el programa imprime, cómo terminó, el contador `usuario + SO = total`, el uso de memoria, los registros, las banderas y cuántas instrucciones se ejecutaron de cada tipo.

| Opción | Qué hace |
| --- | --- |
| `--input TEXTO` | texto que leen las llamadas de teclado (admite `\n`, `\t` y `\\`) |
| `--input-file ARCHIVO` | lo mismo, desde un archivo de texto |
| `--fin-entrada detener\|menos1` | qué pasa si se acaba la entrada: detener con un aviso (por defecto, como el simulador de la cátedra) o devolver -1 |
| `--max N` | corta después de N instrucciones |
| `--dump 0x3100:16` | muestra 16 bytes de memoria desde esa dirección al terminar (se puede repetir) |
| `--trace` | muestra cada instrucción ejecutada |
| `--no-regs` | no muestra los registros ni las banderas |

El código de salida es 0 si el programa llegó a `HALT`, 2 si hubo una excepción y 3 si llegó al límite de `--max`.

## 4. La ventana

```
python lc10_gui.pyw
python lc10_gui.pyw programa.asm modulo.asm
```

En Windows también sirve el doble clic en `lc10_gui.pyw`. Se abre con un programa de ejemplo: **F5** lo ejecuta y **F10** avanza de a una instrucción. La ventana usa el mismo ensamblador y simulador que los comandos de arriba. Lo más útil:

* **Archivo > Abrir benchmark**: abre `main_grupo27.asm` (como programa principal) y sus 37 módulos; F5 ensambla y ejecuta.
* **Programa > Exportar imagen** guarda el programa ensamblado; **Programa > Abrir imagen y simular** ejecuta una imagen ya ensamblada.
* **F7** ensambla, **F9** pone un punto de parada, **F6** reinicia, **Mayús+F5** detiene. Los demás atajos están en *Ayuda > Atajos de teclado*.
* **Programa > Velocidad de ejecución** limita las instrucciones por segundo para ver correr el programa.
* Paneles de registros, memoria, consola, mensajes, listado, símbolos, métricas y traza.

## Entrega

La documentación que detalla la ISA y el informe del laboratorio se entregan aparte, antes del martes 1/12.
