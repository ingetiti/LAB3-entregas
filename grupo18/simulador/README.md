# Lab3C — Ensamblador y simulador funcional

Laboratorio N.º 3C de **Arquitectura de Computadoras**  
Universidad Nacional de Misiones.

El proyecto incluye un ensamblador, un simulador funcional y programas de demostración para probar su funcionamiento.

El flujo general de trabajo es:

```text
programa.asm → ensamblador → programa.bin → simulador → resultado
```

## 1. Requisitos

- Python 3.
- Biblioteca estándar de Python.
- No requiere bibliotecas externas ni instalación adicional.

Todos los comandos deben ejecutarse desde la raíz del proyecto.

Para comprobar la versión instalada:

```bash
python3 --version
```

## 2. Ensamblar un programa

Para ensamblar un archivo fuente:

```bash
python3 -m assembler 01_aritmetica_logica.asm
```

El comando genera el archivo `01_aritmetica_logica.bin` en el directorio actual.

Para especificar otro nombre de salida:

```bash
python3 -m assembler 04_memoria.asm -o memoria.bin
```

## 3. Ejecutar un programa

El simulador recibe un archivo binario generado previamente por el ensamblador:

```bash
python3 -m simulator 01_aritmetica_logica.bin
```

La ejecución muestra la salida del programa y un resumen de la simulación, que incluye:

- Estado final de ejecución.
- Cantidad de instrucciones ejecutadas.
- Cantidad de bytes de memoria escritos.
- Valor final del contador de programa (PC).

## 4. Opciones del simulador

El simulador admite las siguientes opciones:

- `--max-steps N`: establece el límite máximo de instrucciones ejecutadas.
- `--input-file ARCHIVO`: proporciona un archivo de entrada al programa.
- `--input-file -`: utiliza la entrada estándar.

Ejemplo:

```bash
python3 -m simulator programa.bin --max-steps 100000
```

## 5. Ejecutar las pruebas automatizadas

Para ejecutar la suite de pruebas:

```bash
python3 -m unittest discover -v
```

Las pruebas utilizan el módulo `unittest` de la biblioteca estándar de Python.

## 6. Programas incluidos

El proyecto contiene siete programas de demostración:

| Archivo fuente | Archivo binario |
|---|---|
| `01_aritmetica_logica.asm` | `01_aritmetica_logica.bin` |
| `02_desplazamientos.asm` | `02_desplazamientos.bin` |
| `03_comparaciones_saltos.asm` | `03_comparaciones_saltos.bin` |
| `04_memoria.asm` | `04_memoria.bin` |
| `05_subrutinas.asm` | `05_subrutinas.bin` |
| `06_booth.asm` | `06_booth.bin` |
| `insertion_sort.asm` | `insertion_sort.bin` |

Cada programa cuenta con su correspondiente archivo binario ensamblado y puede ejecutarse mediante el simulador.

## 7. Documentación

La documentación operativa se encuentra en el directorio `docs/`:

| Documento | Contenido |
|---|---|
| [ARQUITECTURA.md](docs/ARQUITECTURA.md) | Organización general del repositorio y sus componentes. |
| [ENSAMBLADOR.md](docs/ENSAMBLADOR.md) | Instrucciones de uso del ensamblador. |
| [SIMULADOR.md](docs/SIMULADOR.md) | Instrucciones de uso del simulador. |
