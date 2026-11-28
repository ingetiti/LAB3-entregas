# ISA, Ensamblador y Simulador - Laboratorio 3

## Contenido

- `ISA_SPEC.md`: especificacion de la ISA de 16 bits.
- `assembler.py`: ensamblador y enlazador basico.
- `simulator.py`: nucleo fetch/decode/execute y metricas.
- `lib/`: benchmark original LC-3 conservado como referencia, con ajustes minimos de compatibilidad en `g24_conversor_lc3_max.asm`.
- `benchmark/`: archivos migrados y resultados de pruebas.
- `test_assembler.py` y `test_simulator.py`: pruebas automatizadas.
- `BENCHMARK_RESULTS.md`: resultados y metricas observadas.
- `ISA_OPTIMIZATION.md`: comparativa antes/después de la optimización de ISA.

## Requisitos

- Python 3.10 o superior.
- No requiere paquetes externos.

## Interfaz gráfica

En un entorno Linux con escritorio disponible:

```bash
python3 gui.py
```

Permite abrir, editar y guardar `.asm`, ensamblar en HEX o BIN, ejecutar, inspeccionar registros, PC, instrucciones, memoria observada, pico de memoria, bytes de imagen/código/datos, flags y memoria hexadecimal. Las pestañas **BENCHMARKS** y **REPORTES** ejecutan y muestran los 31 benchmarks reales, los 7 benchmarks migrados, el cierre científico y los reportes Markdown. El interruptor **Comparar optimización** muestra `ISA_OPTIMIZATION.md`.

Atajos: `Ctrl+O` abre un archivo y `F5` ensambla y ejecuta.

## Uso

Ensamblar un programa hexadecimal:

```powershell
python assembler.py benchmark/migrated_easy.asm -o benchmark/migrated_easy.hex --format hex
```

Si un fuente no declara `.ORIG` antes de su primera línea efectiva, el ensamblador usa `x3000` como origen implícito; los `.ORIG` posteriores se respetan.

Activar el peephole opcional (fusiona `MOV+SHL` en `LI16` sin cambiar direcciones):

```bash
python3 assembler.py lib/g24_conversor_lc3_max.asm -o g24.hex --format hex --peephole
```

Ensamblar un programa binario:

```powershell
python assembler.py benchmark/migrated_core_v2.asm -o benchmark/migrated_core_v2.bin --format bin
```

Ejecutar una imagen hexadecimal:

```powershell
python simulator.py benchmark/migrated_easy.hex --format hex --batch --max-instructions 10000
```

Ejecutar una imagen binaria:

```powershell
python simulator.py benchmark/migrated_core_v2.bin --format bin --batch --max-instructions 10000
```

Ejecutar todas las pruebas:

```powershell
python -m unittest -v test_assembler.py test_simulator.py
```

Generar resultados y metricas automaticas:

```powershell
python benchmark_metrics.py -o BENCHMARK_METRICS.md
```

## Ejecución interactiva

Ejecutar sin `--batch` permite que los TRAP GETC/IN usen stdin:

```powershell
python simulator.py program.hex --format hex
```

## Formato hexadecimal

Los archivos `.hex` contienen bytes separados por espacios. Los primeros dos bytes representan la direccion `.ORIG` en little-endian.

## Formato binario

Los archivos `.bin` contienen:

```text
[byte bajo del origen][byte alto del origen][imagen desde el origen]
```

## Formato decimal

Los archivos `.dec` contienen, separados por espacios, los bytes de la imagen: los primeros dos bytes representan el origen `.ORIG` en little-endian y los restantes contienen código y datos.

## Metricas

Al finalizar con HALT, el simulador imprime:

- instrucciones ejecutadas;
- bytes ocupados por el programa y datos escritos;
- pico de memoria ocupada;
- PC final;
- contenido de R0-R7.

## Alcance actual

El repositorio contiene:

- una especificacion formal de ISA;
- ensamblador de dos pasadas;
- enlace basico con `.EXTERNAL` y `.GLOBAL`;
- simulador funcional con memoria byte-addressable;
- benchmarks representativos migrados;
- pruebas automatizadas de ensamblado, ejecucion y alineacion.

Los modulos originales de `lib/` se conservan como referencia para la migracion individual de los algoritmos legacy; `g24_conversor_lc3_max.asm` fue adaptado a la codificacion RI corregida. El alcance exacto pendiente esta documentado en `MIGRATION_STATUS.md`.

## Benchmark real y cierre científico de las 31 interfaces

```bash
python3 real_benchmark.py
python3 scientific_closure.py
python3 -m unittest -v test_assembler.py test_simulator.py
```

`real_benchmark.py` genera un `.asm` ejecutable por interfaz desde `benchmark/real_routines.asm`, ensambla cada fuente, carga el operando en `0x5000`, ejecuta la rutina con `JSR`, compara el resultado escrito en `0x4000` contra una referencia Python y genera `REAL_BENCHMARK.md`. `scientific_closure.py` reutiliza esa ejecución real y genera `SCIENTIFIC_CLOSURE.md`.

Desde la GUI:

1. Abrir `gui.py`.
2. En **BENCHMARKS**, pulsar **Reales 31**, **Migrados 7** o **Cierre**.
3. La tabla muestra estado `PASS`/`FAIL`, entradas, esperado, ejecutado, instrucciones, bytes imagen/datos, pico de memoria y error por caso.
4. En **REPORTES**, usar **Cargar .md** para ver un reporte existente o **Regenerar todo** para recrear los tres archivos Markdown.

También hay una verificación no interactiva:

```bash
python3 gui.py --smoke-benchmarks
```

Debe imprimir `filas=31; migrados=7`.

## Ejemplo con entrada del usuario

Archivo: `benchmark/ejemplo_entrada.asm`

Desde terminal:

```bash
python3 assembler.py benchmark/ejemplo_entrada.asm -o benchmark/ejemplo_entrada.hex --format hex
python3 simulator.py benchmark/ejemplo_entrada.hex --format hex --batch --input 42
```

Desde la GUI:

1. Abrir `benchmark/ejemplo_entrada.asm`.
2. Escribir `42` en el campo **Entrada**.
3. Pulsar **Ejecutar**.
4. Abrir la pestaña **Memoria** y consultar `4000`.

El resultado esperado en `R0` y en `0x4000` es `0x002A`.

## Reporte de resultados

Para mostrar resultados arbitrarios, use `--results BASE COUNT`; por ejemplo, `--results 0x4000 6` muestra seis palabras desde `0x4000`.
