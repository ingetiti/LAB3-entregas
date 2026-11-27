# Arquitectura del repositorio

Este documento describe la organización del proyecto, las responsabilidades de sus componentes y el flujo general de trabajo entre el ensamblador y el simulador.

## 1. Componentes principales

El proyecto está organizado en tres componentes:

| Componente | Ubicación | Responsabilidad |
|---|---|---|
| Ensamblador | `assembler/` | Procesar archivos fuente y generar archivos binarios. |
| Simulador | `simulator/` | Cargar archivos binarios y ejecutar los programas. |
| Pruebas automatizadas | `tests/` | Verificar el funcionamiento de los componentes. |

Los componentes comparten definiciones y estructuras internas para mantener la compatibilidad entre el ensamblador y el simulador.

## 2. Flujo general de trabajo

El funcionamiento del proyecto sigue este flujo:

```text
       programa.asm
             |
             v
       ENSAMBLADOR
             |
             v
        programa.bin
             |
             v
        SIMULADOR
             |
             v
    Salida del programa
    Resumen de ejecución
```

El ensamblador recibe un archivo fuente, procesa su contenido y genera un archivo binario.

El simulador recibe ese archivo binario, lo carga en memoria y ejecuta el programa. Al finalizar, informa el resultado y un resumen de la ejecución.

## 3. Organización de directorios

La estructura principal del repositorio es:

```text
Lab3C/
├── assembler/
│   ├── __main__.py
│   ├── parser.py
│   ├── symbols.py
│   ├── encoder.py
│   └── writer.py
│
├── simulator/
│   ├── __main__.py
│   ├── loader.py
│   ├── cpu.py
│   └── isa.py
│
├── tests/
│   ├── test_assembler/
│   └── test_simulator/
│
├── docs/
│
├── 01_aritmetica_logica.asm
├── 02_desplazamientos.asm
├── 03_comparaciones_saltos.asm
├── 04_memoria.asm
├── 05_subrutinas.asm
├── 06_booth.asm
├── insertion_sort.asm
│
└── README.md
```

### 3.1. Ensamblador

El directorio `assembler/` contiene los módulos encargados de transformar los archivos fuente:

- `__main__.py`: proporciona el punto de entrada para ejecutar el ensamblador desde la terminal.
- `parser.py`: procesa las líneas del archivo fuente y valida su estructura.
- `symbols.py`: administra la información de símbolos y etiquetas.
- `encoder.py`: realiza la traducción del contenido procesado.
- `writer.py`: genera el archivo binario de salida.

### 3.2. Simulador

El directorio `simulator/` contiene los módulos encargados de ejecutar los programas:

- `__main__.py`: proporciona el punto de entrada para ejecutar el simulador desde la terminal.
- `loader.py`: carga el archivo binario en memoria.
- `cpu.py`: administra el estado del procesador y la ejecución del programa.
- `isa.py`: contiene definiciones compartidas necesarias para el funcionamiento del simulador y el ensamblador.

### 3.3. Pruebas automatizadas

El directorio `tests/` contiene las pruebas de los distintos componentes.

Las pruebas permiten verificar tanto el procesamiento de los archivos fuente como la ejecución de los programas.

Se ejecutan desde la raíz del proyecto mediante:

```bash
python3 -m unittest discover -v
```

## 4. Relación entre componentes

La relación entre los módulos puede resumirse de la siguiente manera:

1. El usuario proporciona un archivo fuente al ensamblador.
2. El ensamblador procesa el archivo y genera un binario.
3. El usuario proporciona ese binario al simulador.
4. El simulador carga y ejecuta el programa.
5. El resultado se informa mediante la salida del programa y un resumen de ejecución.

Las pruebas automatizadas verifican el comportamiento de los módulos durante las distintas etapas.

## 5. Dependencias

El proyecto utiliza Python 3 y su biblioteca estándar.

No requiere paquetes externos ni servicios adicionales para ensamblar y ejecutar los programas.
