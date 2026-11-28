# Optimización de ISA y benchmarks reales

## Objetivo

Reducir las instrucciones dinámicas de los 31 benchmarks reales sin cambiar resultados ni romper la compatibilidad de las instrucciones anteriores.

## Decisión de compatibilidad

Se mantuvieron todos los opcode y formatos clásicos. El opcode 31, anteriormente `RESERVED`, se extendió como prefijo `EXT` de 4 bytes. Las formas antiguas siguen vigentes como alias; `MOVU`, `CMP` de tres registros y `LI16` son nuevas formas compatibles.

## Cambios de ISA

- `CMP Rd, Rs1, Rs2`: nuevo modo RRR con `bit[1]=1`; el `CMP` de dos operandos conserva `bit[1]=0`.
- `TEST Rd, #n`: el inmediato de 7 bits ahora se extiende con signo antes de aplicarse.
- `MOV Rd, imm8`: se rechaza `128..255`; esos valores se cargan con `MOVU Rd, imm16`.
- Opcode 31 `EXT`: `LI16`, `MOVU`, `LDABS`, `STABS`, `ZEXT8`, `SEXT8`, `SHLV`, `ADDI16`, `SUBI16`, `ANDI16`, `ORI16`, `XORI16`, `CMP16` y `BR16`.
- Ensamblador con tamaño variable: la primera pasada reserva 4 bytes para `EXT`, por lo que las etiquetas posteriores quedan desplazadas correctamente.
- Simulador con fetch de 4 bytes para `EXT` y `PC <- PC + 4`; el resto de la ISA conserva `PC <- PC + 2`.
- Peephole opcional: `Assembler(peephole=True)` o `python3 assembler.py ... --peephole` fusiona `MOV+SHL` en `LI16` y `MOV+SHL+NOT` en `LI16+NOP`, preservando direcciones.

## Resultados agregados

| Métrica | Antes | Después | Delta |
|---|---:|---:|---:|
| Interfaces PASS | 31 | 31 | 0 |
| Instrucciones globales | 718 | 292 | -426 (-59.33%) |
| Instrucciones del harness | 279 | 124 | -155 (-55.56%) |
| Instrucciones de rutinas | 439 | 168 | -271 (-61.73%) |
| Mínimo por interfaz | 11 | 5 | -6 |
| Máximo por interfaz | 129 | 28 | -101 |
| Promedio por interfaz | 23.16 | 9.42 | -13.74 |
| Bytes de imagen acumulados | 25420 | 32798 | +7378 |
| Bytes de código acumulados | 14570 | 17174 | +2604 |
| Bytes de datos acumulados | 186 | 186 | 0 |
| Bytes observados acumulados | 14756 | 17360 | +2604 |
| Pico máximo por interfaz | 476 | 560 | +84 |
| Error absoluto máximo | 0 | 0 | 0 |
| HALT en todas | si | si | 0 |

El costo de memoria aumenta por las instrucciones EXT de 4 bytes y por la tabla de raíces cuadradas en `x3400`; la métrica priorizada por el usuario fue instrucciones dinámicas, no bytes.

## Optimizaciones aplicadas

- Harness: `LDABS R0,0x5000`, `JSR rutina`, `STABS R0,0x4000`, `HALT`; antes usaba dos cargas de base con `MOV+SHL` y dos accesos indirectos.
- Máscaras de byte: `ZEXT8` reemplaza `MOV #-1`, `SHL #8` y `NOT`.
- Máscaras anchas: `ANDI16` reemplaza `MOV`, `SHL` y `OR`.
- Potencias: `SHLV` convierte el bucle de multiplicaciones repetidas en dos instrucciones.
- Tablas: `LI16` carga bases absolutas sin `MOV+SHL`.
- Raíces: tabla acotada para `0..16`, caso especial para `256` y fallback iterativo para el resto.
- Cuerpos idénticos o identidad: `FROM_QM_N`, `TO_QM_N`, `FROMDEC`, `TODEC` y `GETC_GETLINE_OUTVAL` quedan como `RET`.
- Conversión hexadecimal: partición con `ZEXT8` y conversión ASCII con una sola comparación por byte.

## Verificación

- `python3 -B -m unittest -v test_assembler.py test_simulator.py`: 51 pruebas OK.
- `python3 -B real_benchmark.py`: 31/31 PASS, 292 instrucciones, error 0.
- `python3 -B scientific_closure.py`: 31 interfaces, error máximo 0.
- `python3 -B gui.py --smoke`: GUI smoke test OK.
- `python3 -B gui.py --smoke-benchmarks`: filas=31, migrados=7.
- La GUI muestra esta comparativa activando **Comparar optimización** en la pestaña **REPORTES**.
