

# MANUAL DE USO DEL SIMULADOR:


## Ensamblador

Consiste en un modulo de Python que ensambla un programa desde archivo, texto o diccionario de textos a un archivo de texto hexadecimal, texto binario, o una lista de valores de Python.

Implementa las instrucciones del archivo `instrucciones.py` y las pseudo operaciones del archivo `pseudoops.py`.

*(Para mas información vea detalles de la ISA-G27)*

### Uso como modulo ejecutable por consola

Al ejecutar el modulo `ensamblador.py` con Python, este intentará ensamblar un archivo que se le debe pasar como argumento en la llamada.

Además del archivo, opcionalmente se tiene disponible argumentos para:
- Definir formato de salida *(por defecto es `hex`)*.
- Generar tabla de símbolos.
- Definir directorio de inclusiones *(por defecto es directorio del archivo de entrada)*.
- Dar Nombre de archivo de salida *(por defecto es el archivo de entrada cambiada de extensión)*.
- *(entre otros)*.

**Ensamblado del archivo `hola_mundo.asm`:**
```sh
python -m grupo27.simulador.ensamblador ".\grupo27\ISA-G27\tests simples\hola mundo\hola_mundo.asm"
```

**Ensamblado del archivo `io_test.asm`:**
```sh
python -m grupo27.simulador.ensamblador ".\grupo27\ISA-G27\tests simples\io test\io_test.asm"
```

**Ensamblado del archivo `main.asm` de test de modulos:**
```sh
python -m grupo27.simulador.ensamblador ".\grupo27\ISA-G27\tests simples\modulos\main.asm"
```

**Ensamblado del benchmark:**
```sh
python -m grupo27.simulador.ensamblador ".\grupo27\benchmark\ISA-G27\main.asm"
```

**Ejecutar ensamblado del benchmark con nombre de archivo de salida:**
```sh
python -m grupo27.simulador.ensamblador ".\grupo27\benchmark\ISA-G27\main.asm" -o ".\grupo27\benchmark\ISA-G27\main.hex"
```

**Mostrar lista completa de argumentos:**
```sh
python -m grupo27.simulador.ensamblador --help
```

### Uso como objeto importable en Python

Como es un modulo de Python, es posible utilizar el mismo en otros proyectos e instanciar la `class Assembler`, y utilizar esta instancia para ensamblar programas.


## Simulador

Consiste en un modulo de Python que permite ejecutar un programa desde archivo, o lista de valores de Python, utilizando la consola, manteniendo registrado las estadísticas de uso.

Implementa las instrucciones del archivo `instrucciones.py`.

*(Implementa distintos modos de operación [single, multi, pipeline], además de predictores de salto en el modulo `predictores.py`)*

*(Para mas información vea detalles en el informe principal)*

### Uso como modulo ejecutable por consola

Al ejecutar el modulo `simulador.py` con Python, este intentará ejecutar un archivo que se le debe pasar como argumento en la llamada.

Además del archivo opcionalmente se tiene disponible argumentos para:
- Definir modos de operación.
- Definir predictor de saltos.
- Definir sistema operativo.
- *(entre otros)*.

**Simulación del archivo `hola_mundo.hex`:**
```sh
python -m grupo27.simulador.simulador ".\grupo27\ISA-G27\tests simples\hola mundo\hola_mundo.hex"
```

**Simulación del archivo `io_test.hex`:**
```sh
python -m grupo27.simulador.simulador ".\grupo27\ISA-G27\tests simples\io test\io_test.hex"
```

**Simulación del archivo `main.hex` de test de modulos:**
```sh
python -m grupo27.simulador.simulador ".\grupo27\ISA-G27\tests simples\modulos\main.hex"
```

**Simulación del benchmark:**
```sh
python -m grupo27.simulador.simulador ".\grupo27\benchmark\ISA-G27\main.hex"
```

**Mostrar lista completa de argumentos:**
```sh
python -m grupo27.simulador.simulador --help
```

### Uso como objeto importable en Python

Como es un modulo de Python, es posible utilizar el mismo en otros proyectos e instanciar la `class Simulador`, y utilizar esta instancia para correr programas.
