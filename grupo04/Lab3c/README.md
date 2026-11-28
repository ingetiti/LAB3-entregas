# Manual de uso – ISA Grupo 4

Arquitectura de Computadoras – UNaM, Facultad de Ingeniería – Laboratorio 3c

Este manual explica cómo ensamblar y ejecutar el benchmark con el ensamblador y el simulador del Grupo 4.

## 1. Contenido de la entrega

| Archivo o carpeta | Para qué sirve |
| --- | --- |
| `assembly.py` | Ensamblador y enlazador. Convierte archivos `.asm` en código máquina (`.obj`) |
| `simulador.py` | Simulador funcional. Ejecuta un `.obj` e informa resultados, instrucciones ejecutadas y uso de memoria |
| `so.asm` | Imagen del sistema que el simulador carga antes del programa de usuario (ver 6.2) |
| `main_grupo27.asm` | Programa principal del benchmark (calculadora) |
| `lib_port/` | Módulos `.asm` del benchmark, portados a esta ISA |
| `lib_opt/` | Los mismos módulos con rutinas auxiliares optimizadas. Producen exactamente la misma salida |

Se usa **una** de las dos carpetas de módulos por vez (`--link-dir lib_port` o `--link-dir lib_opt`).

Requisito: Python 3.10 o superior, sin librerías externas. En Windows se usa `py`; en Linux o macOS, `python3`. Los comandos de este manual usan `py`.

## 2. Inicio rápido

Desde la carpeta que contiene los archivos:

```
py assembly.py main_grupo27.asm --format obj --link-dir lib_port
py simulador.py main_grupo27.obj --stats
```

El primer comando genera `main_grupo27.obj`. El segundo lo ejecuta y, al final, imprime las estadísticas.

Tal como se entrega, `main_grupo27.asm` arranca en **modo menú** (ver la sección 3): el programa muestra la calculadora y espera teclas. Para ver el benchmark completo sin teclado hay que activar el modo automático.

## 3. Importante: modo del programa principal (`main_grupo27.asm`)

**El archivo se entrega con las líneas `LEA R0 ...` comentadas, es decir en modo menú interactivo.** El modo se elige en la etiqueta `main`:

```
main
     AND R0 R0 #0
     ;LEA R0 programa_del_menu
     ;LEA R0 programa_del_menu_completo
```

| Líneas activas | Modo |
| --- | --- |
| Ninguna `LEA` (como se entrega) | **Menú interactivo**: se muestra la calculadora y se opera con el teclado |
| `LEA R0 programa_del_menu_completo` | **Automático completo**: ejecuta las 23 operaciones del benchmark sin teclado y termina |
| `LEA R0 programa_del_menu` | **Automático corto**: ejecuta solo 3 operaciones de ejemplo (Booth, raíz por Newton-Raphson y coseno) |

Para ejecutar el benchmark completo:

1. Abrir `main_grupo27.asm` y quitar el `;` del inicio de la línea `LEA R0 programa_del_menu_completo`.
2. Dejar comentada la otra línea `LEA`. La línea `AND R0 R0 #0` puede quedar como está.
3. **Volver a ensamblar** (`py assembly.py main_grupo27.asm --format obj --link-dir lib_port`). El `.obj` no cambia solo: cada vez que se edita el `.asm` hay que regenerarlo.
4. Ejecutar `py simulador.py main_grupo27.obj --stats`.

Para volver al menú, se vuelve a comentar la línea `LEA` y se reensambla.

## 4. El ensamblador (`assembly.py`)

### 4.1 Uso

```
py assembly.py ARCHIVO.asm [--format obj|hex|bin|dec] [--link-dir CARPETA]
```

| Opción | Efecto |
| --- | --- |
| `--format obj` | Genera `ARCHIVO.obj` (binario). Los dos primeros bytes son la dirección de origen del programa (big-endian) y a continuación el código máquina |
| `--format hex` / `bin` / `dec` | Imprime en pantalla los mismos bytes como texto, en hexadecimal, binario o decimal |
| `--link-dir CARPETA` | Carpeta donde buscar los módulos `.EXTERNAL`. **Por defecto es `./lib`, que no se entrega**: para el benchmark hay que indicar siempre `lib_port` o `lib_opt` |

### 4.2 Sintaxis del código fuente

- Los comentarios empiezan con `;`.
- Números: `#10` o `10` (decimal), `x1F` o `0x1F` (hexadecimal), `b1010` o `0b1010` (binario).
- Los operandos se separan con coma o con espacio.
- Una etiqueta es un nombre al comienzo de la línea, solo o junto a una instrucción o directiva.
- Un programa empieza con `.ORIG` y termina con `.END`.
- Las direcciones y las etiquetas son **direcciones de byte**: con `.ORIG x3000` la primera instrucción queda en `x3000` y la segunda en `x3002`.

### 4.3 Directivas

| Directiva | Descripción |
| --- | --- |
| `.ORIG xNNNN` | Dirección de inicio. Debe ser par |
| `.FILL valor` | Una palabra de 16 bits |
| `.BLKW n` | Reserva n palabras inicializadas en cero |
| `.STRINGZ "texto"` | Cadena de caracteres, un byte por carácter, terminada en 0 |
| `.EXTERNAL MODULO-ETIQUETA` | Enlaza con otro archivo (ver 4.5) |
| `.END` | Fin del archivo |

### 4.4 Alineación

Todas las instrucciones quedan en direcciones pares. Si un dato intermedio (por ejemplo una cadena de longitud impar) deja el contador de direcciones en un valor impar, el ensamblador inserta automáticamente un byte de relleno que nunca se ejecuta. Un `.ORIG` impar se rechaza con un mensaje de error.

### 4.5 Enlazado de módulos (`.EXTERNAL`)

El ensamblador incluye un enlazador simple. En el programa que llama a una subrutina de otro archivo se escribe:

```
.EXTERNAL G27_MAIN_MENU_PROGRESO-MAIN_MENU
sub_main_menu   .FILL G27_MAIN_MENU_PROGRESO-MAIN_MENU
```

- El formato es `MODULO-ETIQUETA`: busca el archivo `modulo.asm` (sin distinguir mayúsculas de minúsculas) en la carpeta indicada con `--link-dir` y toma de allí la etiqueta.
- Cada módulo tiene su propio `.ORIG`; el enlazador los reubica y los coloca uno a continuación del otro.
- El `.FILL MODULO-ETIQUETA` guarda la dirección final de la etiqueta, y el programa la usa para llamar a la subrutina.
- Los módulos que a su vez tienen `.EXTERNAL` se enlazan en cadena. Un módulo usado por varios se incluye una sola vez.

## 5. El simulador (`simulador.py`)

### 5.1 Uso

```
py simulador.py ARCHIVO.obj [--stats] [--registers] [--input "texto"] [--max-steps N] [--os so.obj] [--no-os]
```

| Opción | Efecto |
| --- | --- |
| `--stats` | Al finalizar muestra instrucciones ejecutadas y uso de memoria (ver 5.3) |
| `--registers` | Al finalizar muestra el estado de los registros. También se muestra si el programa terminó con error |
| `--input "texto"` | Entrega ese texto como si se escribiera en el teclado (modo no interactivo) |
| `--max-steps N` | Detiene la ejecución tras N instrucciones. Evita bucles infinitos. Si el benchmark completo se corta, subir este valor |
| `--os RUTA` | Usa otra imagen del sistema en lugar de `so.obj` |
| `--no-os` | Ejecuta sin cargar la imagen del sistema (modo heredado: las llamadas del sistema cuentan como una sola instrucción) |

### 5.2 Entrada de teclado

- **En una consola interactiva** (PowerShell, cmd, terminal de Linux o macOS), el programa lee **una tecla sin esperar Enter y sin eco**. Enter llega como salto de línea. Es el comportamiento que usa el menú de la calculadora.
- **Con `--input` o con redirección** (`< archivo` o `|`), el simulador lee de ese flujo carácter por carácter. Si el programa pide más caracteres de los disponibles, termina con `No hay más caracteres disponibles`.
- Algunos editores o consolas integradas no se comportan como una terminal real. Si el menú no responde como se espera, ejecutar el simulador desde PowerShell, cmd o una terminal del sistema.

### 5.3 Estadísticas (`--stats`)

```
===== ESTADÍSTICAS =====
Instrucciones ejecutadas : <total>
  del usuario            : <programa y módulos>
  del SO                 : <imagen del sistema>
Bytes del programa       : <tamaño del programa y módulos>
Bytes del SO             : <tamaño de la imagen del sistema>
Bytes de memoria usados  : <direcciones distintas accedidas>
```

- **Instrucciones del usuario:** las del programa cargado desde el `.obj` (incluidos los módulos enlazados). Es la cifra que se usa para comparar versiones del benchmark.
- **Instrucciones del SO:** las que ejecuta la imagen del sistema para atender las llamadas de entrada y salida y la detención del programa.
- **Bytes de memoria usados:** cantidad de direcciones distintas de memoria que fueron leídas o escritas, incluyendo la carga del programa.

### 5.4 Imagen del sistema (`so.asm`)

El simulador necesita una imagen del sistema (`so.obj`) junto a `simulador.py`. Si no existe, la **genera sola** a partir de `so.asm` (para eso `assembly.py` debe estar en la misma carpeta). También se puede generar a mano:

```
py assembly.py so.asm --format obj
```

No hace falta editar `so.asm` para usar el benchmark.

## 6. La calculadora del benchmark

### 6.1 Menú interactivo

En modo menú se muestra la pantalla `CALCULADORA ARQUITECTURA 2026`. Se elige la operación con **una tecla** (sin Enter):

| Tecla | Operación | Tecla | Operación |
| --- | --- | --- | --- |
| `0` | Reducción de argumento | `7` | Multiplicación |
| `1` | Seno | `8` | División |
| `2` | Coseno | `9` | Logaritmo |
| `3` | Expresión con base (hex y binario) | `a` | Máximo común divisor |
| `4` | Raíz cuadrada | `b` | Mínimo común múltiplo |
| `5` | Exponenciación | `c` | Conversión Q3.12 a Q7.8 |
| `6` | Potenciación | `d` | Salir |

Algunas operaciones ofrecen un submenú para elegir el algoritmo (por ejemplo, potenciación por multiplicaciones sucesivas o por exponenciación binaria). Después se escribe cada operando y se confirma con Enter. Los operandos se aceptan como enteros o en formato Q según lo que indique la pantalla. Al terminar muestra `Pulsa una tecla para continuar...` y vuelve al menú.

Ejemplo (potenciación por exponenciación binaria, 3 elevado a 2): pulsar `6`, `1`, escribir `3` y Enter, escribir `2` y Enter. El resultado es `(int) 9`. Luego pulsar cualquier tecla y `d` para salir.

### 6.2 El mismo ejemplo sin teclado (`--input`)

Con `main_grupo27.asm` en modo menú (como se entrega) y ya ensamblado:

```
py simulador.py main_grupo27.obj --input "613`n2`n d" --stats
```

Ese comando es para **PowerShell**, donde `` `n `` es el salto de línea (Enter). El simulador **no interpreta** la secuencia de texto `\n`: el salto de línea tiene que llegar como un carácter real. En Linux o macOS se escribe `--input $'613\n2\n d'`. En cmd no hay una forma cómoda de escribir un salto de línea dentro de un argumento; conviene usar PowerShell o redirigir un archivo de texto con `< archivo`.

Con `--input` hay que tener en cuenta que las teclas del menú **no llevan Enter**: `6` y `1` van pegadas al primer operando (`3`), cada operando termina con un salto de línea, la tecla de "continuar" es el espacio y `d` sale. Si se agrega un salto de línea después de las teclas del menú, el programa lo toma como un operando vacío (valor 0).

### 6.3 Modo automático

En modo automático el programa recorre un bloque de operaciones definido en `main_grupo27.asm` (`programa_del_menu_completo` o `programa_del_menu`) y no usa el teclado. Cada operación del bloque son cinco palabras `.FILL` consecutivas y el bloque termina con un `.FILL #0`:

```
.FILL #1      ; solo en la primera: 1 = modo verboso, 0 = silencioso
.FILL #15     ; índice de la operación
.FILL x3396   ; operando a
.FILL xF8C3   ; operando b
.FILL #0      ; espacio para el resultado
.FILL #0      ; espacio para el resultado (segunda parte, si aplica)
...
.FILL #0      ; fin del bloque
```

| Índice | Operación | Índice | Operación |
| --- | --- | --- | --- |
| 1 | Reducción de argumento (CORDIC) | 13 | Multiplicación CORDIC |
| 2 | Seno Taylor | 14 | Multiplicación básica |
| 3 | Seno por tabla | 15 | Multiplicación Booth |
| 4 | Seno Chebyshev-Padé | 16 | División larga |
| 5 | Coseno por tabla | 17 | División Newton-Raphson |
| 6 | Base: hexadecimal | 18 | División CORDIC |
| 7 | Base: binario | 19 | Logaritmo Borchardt |
| 8 | Raíz non-restoring | 20 | Logaritmo CORDIC |
| 9 | Raíz Newton-Raphson | 21 | Máximo común divisor |
| 10 | Exponenciación | 22 | Mínimo común múltiplo |
| 11 | Potencia por multiplicaciones sucesivas | 23 | Conversión Q3.12 a Q7.8 |
| 12 | Potencia por exponenciación binaria | 0 | Salir |

## 7. Resultados esperados

Con `programa_del_menu_completo` activo, el simulador imprime los resultados de las 23 operaciones, cada una bajo un título `==NOMBRE==` (por ejemplo `==REDUCCION DE ARGUMENTO (CORDIC)==`, `==SENO TRIGONOMETRICO (TAYLOR)==`, `==MAXIMO COMUN DIVISOR==`) y termina con `HALT`. **La salida de texto es idéntica con `lib_port` y con `lib_opt`.** Solo cambian las estadísticas:

| Métrica (`--stats`) | `lib_port` | `lib_opt` |
| --- | --- | --- |
| Instrucciones del usuario | 357.601 | 124.295 |
| Instrucciones del SO | 13.126 | 13.126 |
| Instrucciones ejecutadas (total) | 370.727 | 137.421 |
| Bytes del programa | 13.640 | 13.436 |
| Bytes del SO | 375 | 375 |
| Bytes de memoria usados | 14.043 | 13.839 |

Estos valores corresponden a `main_grupo27.asm` en modo automático completo y a los archivos de esta entrega.

## 8. Verificación rápida

Para comprobar que las dos bibliotecas producen la misma salida (PowerShell, con `main_grupo27.asm` en modo automático completo):

```
py assembly.py main_grupo27.asm --format obj --link-dir lib_port
py simulador.py main_grupo27.obj > salida_port.txt
py assembly.py main_grupo27.asm --format obj --link-dir lib_opt
py simulador.py main_grupo27.obj > salida_opt.txt
fc salida_port.txt salida_opt.txt
```

`fc` debe informar `No se han encontrado diferencias`. En Linux o macOS se usa `diff` en lugar de `fc`.

## 9. Mensajes de error y solución de problemas

| Síntoma o mensaje | Causa y solución |
| --- | --- |
| El programa muestra el menú y espera teclas | `main_grupo27.asm` está en modo menú. Para el benchmark automático ver la sección 3 |
| Cambié el `.asm` y nada cambió | Falta volver a ensamblar. El simulador ejecuta el `.obj`, no el `.asm` |
| `ERROR: No se encontró el módulo X ni una definición de Y` al ensamblar | No se indicó `--link-dir` (el valor por defecto `./lib` no se entrega) o la carpeta indicada no existe. Usar `--link-dir lib_port` o `--link-dir lib_opt` |
| `literal o símbolo inválido 'X'` al ensamblar | El `.asm` usa una etiqueta que no está definida (por ejemplo, un error de tipeo en el nombre). Revisar la línea indicada |
| `No hay más caracteres disponibles` | El programa pidió más teclas que las dadas con `--input` (o se ejecutó el menú sin teclado). Ver 6.2 |
| `Salto a dirección impar xNNNN` | Un salto o llamada apuntó a una dirección impar. Las instrucciones deben estar en direcciones pares |
| `PC desalineado` | El contador de programa quedó en una dirección impar |
| `Se alcanzó el límite de N instrucciones` | Bucle infinito o programa largo. Subir `--max-steps` |
| `División por cero` | El programa dividió por cero |
| `offset ... fuera de rango` al ensamblar | Un dato o etiqueta quedó demasiado lejos de la instrucción que lo usa. Acercarlo en el código fuente |
| El menú no responde a las teclas como se espera | Ejecutar desde una terminal real (ver 5.2) |
