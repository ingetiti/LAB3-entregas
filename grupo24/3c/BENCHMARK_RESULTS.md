# Resultados del benchmark - Corte Fase 4 integral

## Alcance

Este corte valida una suite indexada de 31 funciones equivalentes a las operaciones publicas del benchmark original. Los algoritmos legacy siguen siendo preservados en `lib/` como codigo fuente de referencia.

- multiplicacion fija: 25
- division: cociente entero 1
- MCD: 6
- potencia: 32
- conversion Q3.12 -> Q7.8: 32
- raiz entera: 4

Los archivos originales de `lib/` se conservan como referencia; `lib/g24_conversor_lc3_max.asm` recibio ajustes minimos de compatibilidad con la codificacion RI corregida.

## Ensamblado y ejecucion

Comandos:

```powershell
python assembler.py benchmark/phase4_integral.asm -o benchmark/phase4_integral.hex --format hex
python simulator.py benchmark/phase4_integral.hex --format hex --batch --max-instructions 10000
python -m unittest -v test_assembler.py test_simulator.py
```

## Matriz de 31 casos

| Indice | Operacion | Resultado hexadecimal |
|---:|---|---:|
| 0 | CORDIC_DIV | 0x0080 |
| 1 | MULT_SHIFT_ADD | 0x0019 |
| 2 | POTENCIA | 0x0020 |
| 3 | POW_MULT_SUCESIVA | 0x0008 |
| 4 | EXP | 0x0100 |
| 5 | MCM | 0x0024 |
| 6 | MCD | 0x0006 |
| 7 | DIVISION_LARGA | 0x0001 |
| 8 | RAIZ_DQ16 | 0x0004 |
| 9 | CORDIC_LOG | 0x0000 |
| 10 | DIV_NEWTON | 0x0002 |
| 11 | LN_BORCHARDT | 0x0000 |
| 12 | CONVERSION_Q312_Q78 | 0x0020 |
| 13 | MULT_BOOTH | 0x0019 |
| 14 | MULT_CORDIC | 0x000C |
| 15 | REDUCCION_ARGUMENTO | 0x0000 |
| 16 | SENO_TAYLOR | 0x1922 |
| 17 | TABLA_SENO_COSENO | 0x4000 |
| 18 | TABLA_SENO_COSENO | 0x4000 |
| 19 | RAIZ_NON_RESTORING | 0x0010 |
| 20 | CONVERSION_HEX | 0x002A |
| 21 | CONVERSION_BIN | 0x000A |
| 22 | CIRCLE_SHIFT | 0x0080 |
| 23 | FROM_QM_N | 0x0204 |
| 24 | TO_QM_N | 0x0204 |
| 25 | FROMDEC | 0x002A |
| 26 | TODEC | 0x002A |
| 27 | GETC/GETLINE/OUTVAL | 0x0000 |
| 28 | SENO_CHEBYSHEV_PADE | 0x4000 |
| 29 | MATH_HELPERS_DQ16 | 0x0004 |
| 30 | SQRT_NR_Q8 | 0x0200 |

## Migracion real validada

Los primeros modulos migrados cuerpo a cuerpo son:

- MCD por Euclides por restas: `MCD(48,18)=6`.
- MCM mediante MCD y division/multiplicacion: `MCM(12,18)=36`.
- Conversion G15 Q3.12 -> Q7.8: `516 -> 32`.
- Reduccion angular: `6434 -> 6434` en el caso representativo.
- Conversion hexadecimal: `42 -> 0x002A`.
- Conversion binaria: `10 -> 0x000A`.

Ejecucion de [benchmark/migrated_easy.asm](benchmark/migrated_easy.asm): 72 instrucciones dinamicas, 98 bytes de imagen y 110 bytes observados, con HALT en `0x3034`.

Ejecucion de [benchmark/migrated_core_v2.asm](benchmark/migrated_core_v2.asm): division=1, potencia=32, raiz=4, reduccion angular=6434, hexadecimal=42 y binario=10. El programa ejecuta 58 instrucciones, usa 80 bytes de imagen y 92 bytes observados, con HALT en `0x3050`.

Ejecucion de [benchmark/migrated_cordic_div.asm](benchmark/migrated_cordic_div.asm): salida positiva 0x4000 y negativa 0xC000 en Q15. Ejecuta 314 instrucciones y usa 94 bytes observados.

Ejecucion de [benchmark/migrated_sqrt.asm](benchmark/migrated_sqrt.asm): sqrt(16)=4 y sqrt(64)=8. Ejecuta 59 instrucciones y usa 48 bytes observados.

Ejecucion de [benchmark/migrated_sincos_table.asm](benchmark/migrated_sincos_table.asm): para pi/3 retorna seno 0x376D y coseno 0x2000; para pi/2 retorna seno 0x4000 y coseno 0x0000.

## Metricas

- Direccion de origen: `0x3000`
- Instrucciones dinamicas: 87
- Imagen ensamblada: 174 bytes
- Memoria observada por el simulador: 236 bytes
- Terminacion: `HALT`
- R7 final: `0x4030`
- Errores de alineacion observados: ninguno

## Limitaciones

- Los 31 casos muestran equivalencia funcional y resultados almacenados, no reproduccion cuerpo a cuerpo de cada algoritmo legacy.
- Se conserva el codigo original en `lib/` para migracion manual posterior.
- El estado exacto modulo por modulo esta en `MIGRATION_STATUS.md`.
- La precision punto fijo completa exige casos adicionales por modulo y comparacion con Python.

## Cierre real posterior

Se reemplazo el cierre basado en `.FILL` por rutinas ISA ejecutables en `benchmark/real_routines.asm`. El controlador `real_benchmark.py` genera un programa por interfaz, carga el operando en `0x5000`, ejecuta `JSR` a la rutina correspondiente y compara el resultado escrito en `0x4000` contra una referencia Python independiente.

Comandos:

```powershell
python real_benchmark.py
python scientific_closure.py
python benchmark_metrics.py
python -m unittest -v test_assembler.py test_simulator.py
```

Resultados finales después de la optimización de ISA:

- 31 de 31 interfaces con HALT y error absoluto maximo 0.
- Instrucciones globales: 292; baseline corregido: 718 (-59.33%).
- Minimo por interfaz: 5; maximo: 28; promedio: 9.42.
- Bytes de imagen acumulados: 32798; bytes de codigo acumulados: 17174.
- Bytes de datos por interfaz: 6; pico maximo de memoria por interfaz: 560.
- Dos ejecuciones consecutivas del benchmark producen las mismas 292 instrucciones sin arrastre de contadores.
- Los 51 tests unitarios pasan con `python -m unittest -v test_assembler.py test_simulator.py`.
- Detalle completo en `REAL_BENCHMARK.md`, `SCIENTIFIC_CLOSURE.md`, `BENCHMARK_METRICS.md` e `ISA_OPTIMIZATION.md`.

La correccion central de codificacion usa `bit[0]=1` como modo RI con `imm7` en `bits[7:1]`; RRR conserva `bits[1:0]=00` salvo el modo compatible de `CMP` de tres operandos, que usa `bit[1]=1`. El opcode 31 se extendió con instrucciones `EXT` de 4 bytes. Esto elimina la ambiguedad por la que un inmediato multiplo de 4 se decodificaba como una instruccion de registro.
