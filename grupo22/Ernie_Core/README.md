# Ernie-Core — Instructivo de Uso del Ensamblador y Simulador

Guía práctica de línea de comandos para ensamblar, enlazar, simular y verificar programas en la toolchain **Ernie-Core**.

## 1. Requisitos y estructura del directorio

* **Requisitos:** Python 3.8 o superior (no requiere librerías externas; utiliza únicamente la biblioteca estándar de Python).

* **Directorio de trabajo:** Todos los comandos de este instructivo están preparados para ejecutarse desde la carpeta raíz de la entrega (`Ernie_Core`).

```
Ernie_Core/
├── ernie_assembler.py                     # Ensamblador y enlazador
├── ernie_simulator.py                     # Simulador de ejecución y telemetría
├── ernie_runner.py                        # Lanzador unificado de pruebas y diagnóstico
├── suite_oraculo_benchmark_Standard.py    # Suite de verificación (variante Standard)
├── suite_oraculo_benchmark_Optimized.py   # Suite de verificación (variante Optimized)
├── Benchmark_Versions/                    # Código fuente (.asm) del benchmark y librerías
│   ├── Benchmark_Standard/
│   └── Benchmark_Optimized/
└── Resultados/                            # Reportes JSON de verificación y salidas auxiliares




```

## 2. Tabla general de herramientas y modos CLI

| Herramienta | Modo / Flag | Sintaxis de invocación | Función | 
| ----- | ----- | ----- | ----- | 
| `ernie_assembler.py` | *(Estándar)* | `python ernie_assembler.py <main.asm> <salida.bin> [modulos.asm ...]` | Ensambla y enlaza uno o más archivos `.asm` generando un ejecutable `.bin`. | 
| `ernie_assembler.py` | `--strict` | `python ernie_assembler.py --strict <main.asm> <salida.bin> [modulos.asm ...]` | Ensambla aplicando validación estricta de sintaxis, registros e inmediatos. | 
| `ernie_assembler.py` | `--syntax` | `python ernie_assembler.py --syntax [--strict] <main.asm> [modulos.asm ...]` | Comprueba sintaxis y enlaces en seco (*dry-run*) sin escribir archivos `.bin`. | 
| `ernie_assembler.py` | `--map` | `python ernie_assembler.py --map [--strict] <main.asm> [salida.bin] [modulos.asm ...]` | Imprime en consola el mapa de módulos enlazados y la tabla de símbolos resueltos. | 
| `ernie_simulator.py` | *(Estándar)* | `python ernie_simulator.py <programa.bin>` | Ejecuta un archivo `.bin` hasta `HALT` y muestra su salida y telemetría. | 
| `ernie_runner.py` | `--profile` | `python ernie_runner.py --profile <programa.bin>` | Ejecuta un `.bin` reportando instrucciones, ciclos por subrutina y uso de pila (`R6`). | 
| `ernie_simulator.py` | `--check-abi` | `python ernie_simulator.py --check-abi <programa.bin>` | Ejecuta un `.bin` auditando la preservación de registros y el balance de pila en subrutinas. | 
| `ernie_runner.py` | `--selftest` | \`python ernie_runner.py --selftest \[—opt || — standard\] | Ejecuta una prueba con valores precargados en los módulos del benchmark desde main | 
| `ernie_runner.py` | `--verify` | \`python ernie_runner.py --verify \[—standard || —opt\] | Ejecuta una prueba exhaustiva sobre los módulos del benchmark, verificando si el resultado obtenido es correcto y coincide con la suite. | 
| `ernie_runner.py` | `--profile` | \`python ernie_runner.py --profile \[--opt || —standard\] | Reporta instrucciones, ciclos por subrutina y uso de pila (`R6`) para todo el benchmark en general. | 
| `ernie_runner.py` | `--check-abi` | \`python ernie_runner.py --check-abi \[--opt || —standard\] | Verifica que módulos utilizan inadecuadamente la pila sin restaurarla al finalizar. | 

> **Nota sobre variantes:** En `ernie_runner.py`, si no se especifica variante, se ejecuta `Standard` por defecto. Para utilizar la versión optimizada del benchmark se agrega `--opt` (o `--standard` para explicitar la estándar sin optimización). Ambos flags son mutuamente excluyentes.

## 3. Guía de uso del Ensamblador (`ernie_assembler.py`)

Aclaración: al estar una especificación entre < > quiere decir que es una especificación obligatoria. Al estar entre \[ \] es opcional.

### 3.1. Ensamblado y enlazado básico

Para compilar un único archivo fuente a binario:

```
python ernie_assembler.py <programa.asm> <salida.bin>




```

Para enlazar un programa principal junto con módulos externos que resuelvan directivas `.EXTERNAL`:

```
python ernie_assembler.py <main.asm> <salida.bin> [modulo1.asm modulo2.asm]




```

### 3.2. Ensamblado estricto (`--strict`)

Verifica que el código cumpla de forma estricta con todas las reglas de formato (sufijos explícitos en saltos `BRnzp`, inmediatos dentro de rango con signo, no sobrescritura manual del puntero de pila `R6` y avance de punteros alineado a palabra):

```
python ernie_assembler.py --strict <programa.asm> [salida.bin]




```

*Nota: Algunos módulos heredados de las librerías del benchmark requieren ensamblarse sin `--strict` por compatibilidad.*

### 3.3. Verificación de sintaxis sin generar binario (`--syntax`)

Permite validar rápidamente si un programa o conjunto de módulos ensambla sin errores, sin crear ni sobrescribir ningún `.bin` en disco. Puede combinarse con `--strict`:

```
python ernie_assembler.py --syntax <programa.asm>
python ernie_assembler.py --syntax --strict <programa.asm> [modulo_extra.asm]




```

### 3.4. Mapa de memoria y tabla de símbolos (`--map`)

Muestra directamente por consola (sin crear archivos `.map` en disco) dos tablas:

1. **Mapa de Módulos Enlazados:** dirección de inicio, fin y tamaño en bytes de cada módulo.

2. **Tabla de Símbolos:** dirección hexadecimal (`0xXXXX`), etiqueta, módulo de origen y alcance (`GLOBAL` o `LOCAL`).

* **Generar el binario y ver el mapa en consola:**

  ```
  python ernie_assembler.py --map <main.asm> <salida.bin> [modulo_extra.asm]
  
  
  
  
  ```

* **Ver solo el mapa del benchmark completo sin generar binario:**

  * En **PowerShell**:

    ```
    python ernie_assembler.py --map Benchmark_Versions\Benchmark_Standard\main_grupo27.asm (Get-ChildItem Benchmark_Versions\Benchmark_Standard\lib\*.asm).FullName
    
    
    
    
    ```

  * En **Símbolo del sistema (CMD)**:

    ```
    set "LIBS=" & for %f in (Benchmark_Versions\Benchmark_Standard\lib\*.asm) do @call set "LIBS=%LIBS% %f"
    python ernie_assembler.py --map Benchmark_Versions\Benchmark_Standard\main_grupo27.asm %LIBS%
    
    
    
    
    ```

## 4. Guía de uso del Simulador (`ernie_simulator.py`)

### 4.1. Ejecución estándar

Carga un archivo binario `.bin`, ejecuta las instrucciones hasta encontrar `HALT` (`TRAP x25`) y presenta la salida por consola del programa junto con el estado de registros y métricas de ejecución:

```
python ernie_simulator.py <salida.bin>




```

### 4.2. Perfilado de un binario (`--profile`)

Mide la cantidad de llamadas, instrucciones ejecutadas, ciclos estimados y porcentaje de tiempo por subrutina, además de registrar la profundidad máxima alcanzada por la pila (`R6` respecto a su base `0xFFFE`):

```
python ernie_simulator.py --profile [--opt || --standard] [salida.bin]




```

### 4.3. Auditoría de convención de llamada (`--check-abi`)

Inspecciona cada par de instrucciones `JSR`/`JSRR` y `RET`, verificando automáticamente que las subrutinas preserven los registros *callee-saved* (`R2` a `R5`), mantengan balanceado el puntero de pila (`R6`) y no corrompan la dirección de retorno (`R7`):

```
python ernie_simulator.py --check-abi [--opt || --standard] [salida.bin]




```

## 5. Guía de uso del Lanzador Unificado (`ernie_runner.py`)

`ernie_runner.py` automatiza el ensamblado, enlazado y ejecución del benchmark completo para ambas variantes (`Benchmark_Standard` y `Benchmark_Optimized`).

### 5.1. Autoevaluación automática (`--selftest`)

Ensambla el programa principal del Grupo 27 (`main_grupo27.asm`) junto con sus 37 librerías y ejecuta de forma automática (sin intervención por teclado) las 23 operaciones precargadas, verificando detención limpia por `HALT`, ausencia de excepciones fatales y balance de pila:

```
python ernie_runner.py --selftest
python ernie_runner.py --selftest [--opt || --standard]




```

### 5.2. Verificación completa contra oráculos (`--verify`)

Ejecuta la suite de 723 vectores de prueba sobre los 38 módulos del proyecto, guarda el detalle en `Resultados/` y muestra en consola el resumen de casos aprobados (`PASS`), fallidos (`FAIL`) y excepciones fatales:

```
python ernie_runner.py --verify
python ernie_runner.py --verify [--opt || --standard]




```

*(También admite el argumento posicional `standard` u `optimized`: `python ernie_runner.py --verify optimized`).*

### 5.3. Perfilado del benchmark completo (`--profile`)

Ensambla el benchmark, resuelve los nombres de las subrutinas y su grupo de pertenencia (`Gxx`) y genera el reporte ordenado por consumo de instrucciones junto con el pico de uso de pila:

```
python ernie_runner.py --profile
python ernie_runner.py --profile [--opt || --standard]




```

### 5.4. Auditoría ABI del benchmark completo (`--check-abi`)

Ejecuta el flujo completo del benchmark supervisando todas las llamadas a subrutinas y listando cualquier rutina que modifique `R2..R5`, desbalancee `R6` o altere `R7`:

```
python ernie_runner.py --check-abi
python ernie_runner.py --check-abi [--opt || --standard]




```

## 6. Códigos de salida (Exit Codes)

Todas las herramientas devuelven códigos de estado estándar para facilitar su integración en scripts o pruebas automatizadas:

| Código | Significado | 
| ----- | ----- | 
| **`0`** | Ejecución exitosa (ensamblado sin errores, simulación limpia, `selftest`/`verify` aprobados o cero violaciones ABI). | 
| **`1`** | Error en tiempo de ensamblado o ejecución (error de sintaxis, símbolo `.EXTERNAL` no resuelto, violación de `--strict`, excepción fatal en simulación, fallo en casos de `--verify` o detección de violaciones en `--check-abi`). | 
| **`2`** | Uso incorrecto de argumentos en línea de comandos (flags faltantes, opciones mutuamente excluyentes o rutas no especificadas). | 
