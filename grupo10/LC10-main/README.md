# LC10: ISA, ensamblador y simulador del Grupo 10

Laboratorio 3 (parte c) de Arquitectura de Computadoras, UNaM. Grupo 10: Benitez, Denis; Silvero Zapani, Matias; Pintos, Daiana. Tema del grupo: división por método de división larga. Tutor: Dr. Ing. Aldo Benitez.

Esta carpeta contiene una ISA nueva (LC10), su ensamblador, su simulador funcional, una ventana gráfica para escribir y ejecutar código sin usar comandos, y la rutina de división larga del grupo portada a esa ISA. Todo está en Python y usa solo la biblioteca estándar (la ventana usa tkinter, que viene con Python).

Estado: **versión 2**. Cumple la funcionalidad obligatoria del enunciado (ver la tabla de la sección 8 de `docs/ISA.md`) y usa los 32 opcodes. Incluye multiplicación y división enteras de 16 bits (`MUL`, `MULH`, `MULHU`, `DIV`, `DIVU`, `REM`, `REMU`), cociente y resto en una instrucción (`DIVREMU`, `DIVREM`) y guardado de varios registros en la pila con una instrucción (`PUSH`, `POP`). El benchmark completo del curso (programa del grupo 27 y los módulos de todos los grupos) está portado a LC10 y reproduce la salida de la LC-3 con 93,0 % menos instrucciones, contando también las de las rutinas de los TRAP como pidió la cátedra (26.723 = 15.822 de usuario + 10.901 del SO, contra 379.579 = 357.505 + 22.074; 95,6 % menos si se cuenta solo el usuario), y 37,1 % menos palabras (sección "El benchmark del curso"). Las cifras de LC10 se midieron con el simulador de este repositorio (el del curso no ejecuta LC10); las de LC-3 de la división se verificaron además con el simulador del curso.

## Correr el benchmark de la cátedra (con sus entradas)

El programa principal del benchmark (`main_grupo27.asm` de la cátedra, en LC-3) ensambla tal cual en LC10 y se enlaza con los módulos portados de `asm/opt10`. Las entradas son el bloque `.FILL` de ese archivo (modo automático) o, con `--interactivo`, las teclas que se le pasen:

```
python benchmark.py                                         # el benchmark tal como lo entregó la cátedra
python benchmark.py RUTA\main_grupo27.asm                   # el main que entregue la cátedra, con sus entradas
python benchmark.py RUTA\main_grupo27.asm -o programa.hex    # y guarda la imagen que corre el simulador
python -m lc10.simulator programa.hex                       # el simulador, con un archivo, como pide el enunciado
python benchmark.py --interactivo --entrada "7213.25\n-7.5\n d"     # el menú con teclas (7 = x, 2 = Booth, d = salir)
python benchmark.py RUTA\main_grupo27.asm --lc3 RUTA\lc3-project     # además lo corre en LC-3 y compara
```

Al final muestra lo mismo que la barra del simulador de la cátedra, para LC10 (y para LC-3 con `--lc3`):

```
LC10 · 15.822 usuario + 10.901 SO = 26.723 instrucciones · 4963 palabras · x3000–x56C5
LC-3 · 357.505 instrucciones · 7896 palabras · x3000–x4ED7
salida idéntica a la de LC-3: sí
diferencia: instrucciones de usuario -95.6 %, palabras -37.1 %
con el SO (LC-3: 357.505 usuario + 22.074 SO = 379.579, informado por la cátedra; LC10: 26.723): instrucciones -93.0 %
```

El simulador de la cátedra que está en `lc3-project` cuenta cada TRAP como una instrucción; el grupo 8 lo actualizó para sumar las del SO (357.505 + 22.074 = 379.579) y la cátedra pidió que los demás simuladores también las cuenten. En LC10 los TRAP los resuelve un SO escrito en LC10 (`lc10/os_lc10.asm`) cuyas instrucciones se ejecutan y se cuentan aparte, por eso la barra dice "usuario + SO = total".

Las teclas también se pueden pasar en un archivo (`--entrada-archivo teclas.txt`). Si el programa pide una tecla y no quedan, se detiene con el aviso "no hay más caracteres disponibles en la entrada", igual que el simulador de la cátedra.

Única diferencia conocida con otras entradas: seno y coseno por tabla (grupo 22) con un ángulo fuera de 0..2π. El módulo original lee fuera de su tabla y el resultado depende de la memoria que haya ahí, que en LC10 es otra (detalle en `docs/ISA.md`, sección 12, "Dominio de las tablas").

## Contenido

```
docs/ISA.md            especificación: registros, formatos, instrucciones, ensamblador, simulador,
                       cumplimiento del enunciado, resultados y decisiones abiertas
lc10/isa.py            tabla de instrucciones, codificación, decodificación, desensamblado
lc10/image.py          formatos de archivo del programa ensamblado (.bin, .hex, .dec, .bits)
lc10/assembler.py      ensamblador con enlace de módulos (.EXTERNAL)
lc10/simulator.py      simulador funcional con métricas (cuenta usuario + SO)
lc10/os_lc10.asm       el sistema operativo: rutinas de GETC, OUT, PUTS, IN y HALT, en LC10
lc10/system.py         ensambla el SO, arma la tabla de vectores TRAP y lo instala en la máquina
lc10/session.py        lógica de la ventana (ensamblar, paso a paso, puntos de parada, cambios), sin tkinter
lc10/syntax.py         colores del editor y escapes de la entrada, sin tkinter
lc10/gui.py            la ventana (tkinter)
lc10_gui.pyw           lanzador: doble clic en Windows
benchmark.py           corre el benchmark con el main que se le pase (y lo compara con LC-3 con --lc3)
bench/evidencia.py     corre todas las comparaciones con la cátedra y guarda las salidas en bench/resultados/
asm/division.asm       DIV_LONG (Q7.8 / Q7.8 -> Q7.8) en LC10, módulo sin main
asm/main_division.asm  programa principal mínimo para probarla
asm/hola.asm           ejemplo mínimo (PUTS)
asm/bench10/           el benchmark del curso (38 módulos) portado línea a línea a LC10 por el traductor
asm/opt10/             el mismo benchmark con 12 módulos reescritos a mano con las instrucciones de LC10
tools/                 lc3_to_lc10.py (traductor), port_hints.py (ajustes del traductor), peephole_lc10.py
tests/                 pruebas (unittest)
bench/                 comparación de la división en LC-3 y en LC10; línea base del benchmark del curso
                       (lc3_baseline.py + lc3_baseline_salida.txt); lc10_bench.py (el benchmark en LC10);
                       pruebas de equivalencia contra los módulos reales de la cátedra (equivalencia_*.py)
```

## Cómo empezar: la ventana

```
python lc10_gui.pyw                       (en Windows también sirve el doble clic)
python lc10_gui.pyw programa.asm modulo.asm
```

Se abre con un programa de ejemplo ya cargado: **F5** lo ejecuta, **F10** avanza de a una instrucción.

* **Editor** con pestañas, colores, números de línea y puntos de parada (clic en el margen izquierdo o F9). La primera pestaña es el programa principal (★) y las demás son módulos que se enlazan con `.EXTERNAL`, igual que en la línea de comandos.
* **Muchos archivos abiertos** (por ejemplo los 38 del benchmark): sobre el editor hay una franja con el nombre completo del archivo a la vista (con ★ si es el principal y ● si tiene cambios), su posición («módulo · 22 de 38») y dos botones con el nombre del archivo anterior y del siguiente. **Ctrl+Tab** y **Ctrl+Mayús+Tab** (o Ctrl+Av Pág y Ctrl+Re Pág) hacen lo mismo con el teclado y dan la vuelta al llegar al final. El botón **☰ Archivos** (o **Ctrl+B**, o *Ver > Lista de archivos*) abre un panel con la lista de todos los archivos: un clic cambia de archivo, y el cuadro **Buscar** filtra por nombre mientras se escribe (Enter abre el primero que coincide, Esc borra el filtro). El panel aparece solo al abrir más de 4 archivos; si se lo oculta a mano, no vuelve a aparecer solo. El nombre del archivo a la vista también está en el título de la ventana.
* **Registros** en hexadecimal, decimal con signo y binario, las banderas N Z P C V y la instrucción que sigue. Lo que cambió en el último paso queda resaltado, y la línea que se va a ejecutar se marca en el editor.
* **Memoria** de 256 bytes (o palabras de 16 bits) con scroll; "Ir" acepta una dirección (`x3000`, `12288`) o una etiqueta (`MSG`, `DIVISION-DIV_LONG`), y "Seguir PC" la mantiene en la instrucción actual. Los bytes que cambió el último paso se resaltan.
* **Consola** para `OUT`, `PUTS`, `GETC` e `IN` (la entrada se escribe arriba a la derecha y se toma al ensamblar o reiniciar; admite `\n`). Pestañas de **Mensajes** (errores con un enlace que lleva a la línea), **Listado**, **Símbolos**, **Métricas** (instrucciones ejecutadas por tipo y uso de memoria) y **Traza**.
* **Abrir benchmark:** *Archivo > Abrir benchmark* reemplaza lo que haya abierto (si hay cambios sin guardar, avisa y no hace nada) por `main_grupo27.asm` de `asm/opt10`, marcado como programa principal (★), seguido de sus 37 módulos. Queda todo listo: F5 ensambla y ejecuta (o F7 solo ensambla) y termina en 26.723 instrucciones (15.822 de usuario + 10.901 del SO), 4963 palabras, x3000–x56C5. No hace falta abrir los archivos a mano ni pasar por `benchmark.py`.
* **Velocidad de ejecución:** *Programa > Velocidad de ejecución* limita F5 a como máximo 100, 1.000, 2.000, 5.000 o 10.000 instrucciones por segundo (por defecto, sin límite). A esas velocidades se ve correr el programa: la línea actual se mueve por el editor (y cambia de archivo cuando la ejecución pasa a otro módulo), los registros y los bytes de memoria que cambian se resaltan y la consola va mostrando la salida. Se puede cambiar mientras el programa corre. Los puntos de parada y el tope de instrucciones siguen funcionando. Como referencia, el benchmark completo (26.723 instrucciones) tarda unos 4 minutos y medio a 100 por segundo y menos de 3 segundos a 10.000. La velocidad es un máximo: si la computadora no llega, va más lento.
* **Tope de instrucciones:** F5 se detiene solo a las 20 millones de instrucciones sin llegar a `HALT` (un bucle infinito), avisa en la barra de estado y en la consola, y F5 de nuevo sigue otro tanto. *Programa > Límite de instrucciones por ejecución...* cambia el tope (0 = sin tope). Mayús+F5 detiene en cualquier momento.
* **Imágenes:** *Programa > Exportar imagen* guarda el `.hex`, `.bin`, `.dec` o `.bits`, y *Programa > Abrir imagen y simular* ejecuta una imagen ya ensamblada sin pasar por el fuente (así se conserva el esquema del enunciado: el simulador trabaja con un archivo).
* **Ejemplos** en *Archivo > Ejemplos*, incluida la división con su programa principal y su módulo. Los atajos están en *Ayuda > Atajos de teclado* y una referencia de instrucciones en *Ayuda > Referencia*.

La ventana no tiene lógica propia de la ISA: usa el mismo ensamblador y el mismo simulador que los comandos de abajo. Sus pruebas pasan en Linux (pantalla virtual, Python 3.12, Tk 8.6) y en Windows 11 (Python 3.15, Tk 9.0); en macOS no se probó.

## Cómo empezar: línea de comandos

Ensamblar y ejecutar un programa:

```
python -m lc10.assembler asm/hola.asm -o hola.hex --listing
python -m lc10.simulator hola.hex
```

Con módulos (el primer archivo es el principal, los demás son módulos sin `.ORIG`):

```
python -m lc10.assembler asm/main_division.asm asm/division.asm -o div.hex --map
python -m lc10.simulator div.hex
```

El resultado de ese ejemplo es R0 = x02C0 (5,5 / 2 = 2,75 en Q7.8) y el simulador informa instrucciones ejecutadas, instrucciones por tipo y uso de memoria.

Opciones útiles:

| Herramienta | Opción | Para qué |
| --- | --- | --- |
| ensamblador | `-f bin\|hex\|dec\|bits` | formato de salida (por defecto, el de la extensión de `-o`) |
| ensamblador | `--listing`, `--map` | listado con direcciones y palabras; módulos y símbolos |
| simulador | `--input TEXTO` | texto que leen `GETC` e `IN` (admite `\n`, `\t`, `\\`) |
| simulador | `--input-file ARCHIVO` | lo mismo, desde un archivo de texto |
| simulador | `--fin-entrada menos1` | si se acaba la entrada, `GETC` devuelve -1 en lugar de detener la ejecución |
| simulador | `--dump 0x3100:16` | volcado de memoria al terminar (se puede repetir) |
| simulador | `--trace` | muestra cada instrucción ejecutada |
| simulador | `--max N` | corta después de N instrucciones |

El simulador informa el uso de memoria así (benchmark del curso):

```
Memoria: imagen 9926 bytes (4963 palabras, x3000–x56C5); usados 5608 bytes distintos: 5566 dentro de la imagen y 42 fuera (xFFD6–xFFFF)
  detalle: instrucciones leídas de 3520 bytes; datos leídos 1986 bytes y escritos 328 bytes distintos
```

"Usados" son los bytes distintos que el programa leyó como instrucción, leyó como dato o escribió. Los de afuera de la imagen se listan como rangos (en el benchmark son los 28 bytes de la pila, al final de la memoria). Antes se informaba solo el rango x3000..xFFFF, que hacía parecer que se usaba casi toda la memoria.

El simulador recibe siempre un archivo ya ensamblado. Informa `LC10 · N instrucciones · M palabras · xORIGEN–xFIN` como la barra del simulador de la cátedra, y termina con código 0 si llegó a `HALT`, 2 si hubo una excepción (PC o salto a dirección impar, palabra en dirección impar, combinación reservada del opcode 29 o 31, fin de la entrada) y 3 si llegó al límite de `--max`.

## Pruebas

```
python -m unittest discover -s tests -t .
```

244 pruebas (157 sin pantalla y 87 de la ventana): codificación y desensamblado (incluidas las combinaciones reservadas del opcode 31), ensamblador (alineación, cadenas, saltos, enlace de módulos, mensajes de error), formatos de archivo, banderas de la ALU contra una referencia con signo, multiplicación y división contra referencias en enteros (incluida la división por cero), `DIVREMU`/`DIVREM` contra la división seguida del resto, `PUSH`/`POP` con máscaras al azar, desplazamientos y rotaciones, aritmética de 32 bits con acarreo, memoria por byte y palabra, excepciones, llamadas a subrutinas, TRAP y métricas, el sistema operativo (`tests/test_os.py`: mapa de memoria, tabla de vectores, el costo exacto de cada rutina de TRAP, registros que conservan, fin de la entrada y dispositivos), la línea de comandos y `benchmark.py`, y el benchmark completo (`tests/test_benchmark.py`: los dos puertos tienen que imprimir exactamente la salida de referencia de LC-3, y el optimizado con 15.822 instrucciones de usuario (más 10.901 del SO) y 4.963 palabras, con la pila de `PUSH`/`POP` equilibrada). La división se verifica contra el modelo exacto en unos 20.000 casos (bordes y aleatorios), incluida la preservación de R1 a R7. La parte de la ventana se prueba abriéndola de verdad: ensamblar, ejecutar, paso a paso, puntos de parada, errores, memoria, imágenes, pestañas, guardar y abrir, y la navegación entre archivos (franja, botones, atajos, lista y buscador, incluida la apertura de los 38 archivos del benchmark desde la ventana con 15.822 instrucciones de usuario), *Abrir benchmark* (principal, módulos, avisos, ejecución) y el tope de velocidad (que ninguna velocidad se pase del máximo, que se pueda cambiar corriendo, que los puntos de parada no se salteen y que la ejecución termine con el mismo resultado).

Las 87 pruebas de la ventana necesitan tkinter y una pantalla; si no hay, se saltean solas. En un equipo sin pantalla: `xvfb-run -a python -m unittest discover -s tests -t .`

## Resultados: división larga

Mismos 20.361 casos para las dos versiones, con resultado y `ESTADO` verificados en cada uno:

| | LC-3 | LC10 |
| --- | --- | --- |
| Instrucciones por llamada (mínimo / promedio / máximo) | 27 / 227,9 / 327 | 19 / 122,7 / 175 |
| Tamaño del módulo | 212 bytes (incluye `DIVIDIR` general) | 120 bytes (solo `DIV_LONG`) |

Reducción promedio de instrucciones: 46,2 %. Para reproducirlo: `python bench/bench_division.py`. Detalle y alcance de la comparación en `docs/ISA.md`, sección 9.

## El benchmark del curso: LC-3 contra LC10

```
python bench/lc3_baseline.py RUTA\lc3-project          # la línea base en LC-3 (simulador de la cátedra)
python bench/lc10_bench.py asm/opt10 --por-modulo      # el mismo programa en LC10, y compara la salida
```

La línea base ensambla `main_grupo27.asm` con sus módulos y lo ejecuta con el ensamblador y el simulador de la cátedra, sin modificarlos: imagen idéntica a `programa.obj`, **357.505 instrucciones** de usuario y **7896 palabras** (las cifras del tutor), más la salida impresa, que se guarda en `bench/lc3_baseline_salida.txt`. El grupo 8 actualizó el contador para sumar las del SO: **357.505 usuario + 22.074 SO = 379.579**. El puerto a LC10 imprime exactamente ese texto:

| Versión | Usuario | SO | Total | Palabras |
| --- | ---: | ---: | ---: | ---: |
| LC-3 (cátedra; SO según el grupo 8) | 357.505 | 22.074 | **379.579** | 7.896 |
| LC10, puerto directo (`asm/bench10`) | 358.481 | 10.901 | **369.382** (−2,7 %) | 6.896 |
| LC10 versión 0, optimizado, sin el opcode 31 | 17.791 | 10.901 | **28.692** (−92,4 %) | 5.352 (−32,2 %) |
| LC10 versión 2, optimizado (`asm/opt10`) | 15.822 | 10.901 | **26.723** (−93,0 %) | **4.963** (−37,1 %) |

Solo con las instrucciones del usuario, la versión 2 ahorra 95,6 %. Las del SO de LC10 son las de sus rutinas de TRAP (133 `PUTS` con 1.541 caracteres a 9 + 6 por carácter, 76 `OUT` a 6 y el `HALT`, 2); como no tenemos el SO del grupo 8, si el de LC10 costara lo mismo que el de la LC-3 (22.074) el total sería 37.896 (−90,0 %). Detalle en `docs/ISA.md`, secciones 5 y 12.

Criterios confirmados por el tutor: se pueden sacar los códigos de prueba propios de `g19` y `g21` (innecesarios; son unas 400 de las palabras ahorradas, y sin ese recorte la reducción sería de aproximadamente 32 %) y `MUL`/`DIV` cuentan como una instrucción. El desglose del ahorro y las demás salvedades están en `docs/ISA.md`, sección 12. Qué contiene el benchmark y dónde se gastan las instrucciones en LC-3: sección 11.

Criterio del tutor: se puede usar MUL/DIV solo si el resultado es idéntico al de la subrutina original (hay que modelar sus cuentas). Cada módulo reescrito se contrasta con el módulo real de la cátedra ejecutado en su simulador:

| Prueba | Alcance | Resultado |
| --- | --- | --- |
| `bench/equivalencia_modulos.py RUTA\lc3-project asm/opt10 --casos 150` | las 39 subrutinas del benchmark (5.801 casos, registros R1 a R5 con valores centinela) y 17 sesiones completas del menú | 0 diferencias |
| `bench/equivalencia_seno_lc10.py` | los 65.536 valores de entrada del seno de Taylor | 0 diferencias |
| `bench/equivalencia_todec_lc10.py` | 328.160 llamadas de `TODEC` (todas las fracciones, todos los enteros, los 8 formatos) | 0 diferencias |
| `bench/equivalencia_chicos_lc10.py` | `SUMOVER` y `CIRCLSH`, unas 400.000 llamadas | 0 diferencias |
| `bench/equivalencia_div_lc10.py RUTA\lc3-project` | `DIV_NEWTON`, 12.210 casos por longitud de bit del divisor | 0 diferencias |
| `bench/equivalencia_exp_lc10.py` | `EXP_Q3_12`, las 65.536 entradas, contra el puerto directo | 0 diferencias |
| `bench/equivalencia_entradas.py RUTA\lc3-project` | el main de la cátedra con otras entradas: 52 casos al azar por cada una de las 23 operaciones, en LC-3 y en LC10 | 0 diferencias, salvo seno y coseno por tabla con ángulo fuera de 0..2π (ver arriba) |

**Evidencia guardada.** `python bench/evidencia.py RUTA\lc3-project` corre todas estas comparaciones (y las pruebas automáticas, la línea base y el benchmark) y guarda la salida completa de cada una en `bench/resultados/`, con un índice `LEEME.md` que tiene la fecha, la versión de Python y una huella (SHA-256) de `asm/opt10` y `lc10/`: si se cambia un módulo o el simulador, la huella cambia y hay que regenerarla. `--lista` muestra las pruebas y `--solo NOMBRE` corre algunas.

Las pruebas largas tardan minutos y se pueden partir en tandas: `EXP` con `--desde` y `--hasta`, `TODEC` con `--parte K/N` (cada tanda recorre cada N-ésimo caso), las rutinas chicas con `--solo SUMOVER|CIRCLSH` y `--parte K/N`, y `equivalencia_modulos.py` con `--solo ETIQUETA…` y `--sin-sesiones` (las 17 sesiones del menú se corren aparte con `--sesiones`).

## Cómo agregar o cambiar una instrucción

1. Editar la tabla `INSTRUCTIONS` de `lc10/isa.py` (nombre, opcode, formato). Si el formato es nuevo, agregarlo en `encode`, `decode` y `disassemble`. No quedan opcodes libres: una instrucción nueva tiene que ir como variante (campo fn) de un opcode existente, como `MUL`/`MULH`/`MULHU` en el 29 o las cuatro del 31.
2. Ensamblador: si la instrucción tiene una sintaxis particular, agregarla en `lc10/assembler.py`.
3. Simulador: agregar su efecto en `Machine.step` de `lc10/simulator.py`.
4. Agregar pruebas en `tests/` y actualizar `docs/ISA.md`.

La ventana toma el ensamblador y el simulador tal cual: una instrucción nueva aparece sola en el editor (los colores salen de `assembler.is_mnemonic`), en el desensamblado de "sigue" y en las métricas. Lo único que hay que actualizar a mano es el texto de `REFERENCIA` en `lc10/gui.py`.

## Notas de entrega

* Esta carpeta (`grupo10/lab3c`) es la entrega del Grupo 10 para el Laboratorio 3c: la ISA, su ensamblador y su simulador funcional, más la ventana y el benchmark del curso portado.
* Los comandos de este documento se ejecutan desde esta carpeta. Hace falta Python 3 y solo la biblioteca estándar (la ventana usa tkinter). Se probó con Python 3.12 en Linux (Tk 9.0) y con Python 3.15 en Windows 11 (Tk 9.0); las pruebas sin pantalla y `benchmark.py`, también con Python 3.10.
* La línea base del benchmark y las pruebas de equivalencia necesitan la carpeta `lc3-project` de la cátedra (se pasa como `RUTA`); las demás pruebas no.
* La rutina `../division.asm` del banco de algoritmos (LC-3 original) es independiente de este proyecto y se entregó antes; el README de `grupo10/` la describe.
