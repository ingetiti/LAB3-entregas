# Benchmark real de la calculadora

Cada interfaz se ejecuta en un programa ensamblado propio que lee su operando desde 0x5000, llama a una rutina ISA real y escribe el resultado en 0x4000.

| # | Interfaz | Formato | Entrada | Esperado | Ejecutado | Instrucciones | Bytes imagen | Bytes datos | Pico memoria | Error | Estado |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | CORDIC_DIV | Q15 | 0x0040 | 0x4000 | 0x4000 | 6 | 1058 | 6 | 560 | 0 | PASS |
| 2 | MULT_SHIFT_ADD | Q16.16 | 0x0505 | 0x0019 | 0x0019 | 10 | 1058 | 6 | 560 | 0 | PASS |
| 3 | POTENCIA | entero | 0x0005 | 0x0020 | 0x0020 | 8 | 1058 | 6 | 560 | 0 | PASS |
| 4 | POW_MULT_SUCESIVA | Q7.8 | 0x0003 | 0x0008 | 0x0008 | 8 | 1058 | 6 | 560 | 0 | PASS |
| 5 | EXP | Q7.8 | 0x0001 | 0x0100 | 0x0100 | 6 | 1058 | 6 | 560 | 0 | PASS |
| 6 | MCM | Q15.0 | 0x0C12 | 0x0024 | 0x0024 | 28 | 1058 | 6 | 560 | 0 | PASS |
| 7 | MCD | Q15.0 | 0x0C12 | 0x0006 | 0x0006 | 27 | 1058 | 6 | 560 | 0 | PASS |
| 8 | DIVISION_LARGA | Q7.8 | 0x0101 | 0x0001 | 0x0001 | 10 | 1058 | 6 | 560 | 0 | PASS |
| 9 | RAIZ_DQ16 | Q15.16 | 0x0010 | 0x0004 | 0x0004 | 13 | 1058 | 6 | 560 | 0 | PASS |
| 10 | CORDIC_LOG | Q3.12 | 0x0001 | 0x0000 | 0x0000 | 6 | 1058 | 6 | 560 | 0 | PASS |
| 11 | DIV_NEWTON | Q7.8 | 0x0804 | 0x0002 | 0x0002 | 10 | 1058 | 6 | 560 | 0 | PASS |
| 12 | LN_BORCHARDT | Q8.7 | 0x0001 | 0x0000 | 0x0000 | 6 | 1058 | 6 | 560 | 0 | PASS |
| 13 | CONVERSION_Q312_Q78 | Q3.12->Q7.8 | 0x0200 | 0x0020 | 0x0020 | 6 | 1058 | 6 | 560 | 0 | PASS |
| 14 | MULT_BOOTH | Q7.8 | 0x0505 | 0x0019 | 0x0019 | 10 | 1058 | 6 | 560 | 0 | PASS |
| 15 | MULT_CORDIC | Q7.8 | 0x0304 | 0x000C | 0x000C | 10 | 1058 | 6 | 560 | 0 | PASS |
| 16 | REDUCCION_ARGUMENTO | Q3.12 | 0x1922 | 0x1922 | 0x1922 | 6 | 1058 | 6 | 560 | 0 | PASS |
| 17 | SENO_TAYLOR | Q1.14 | 0x0002 | 0x376D | 0x376D | 8 | 1058 | 6 | 560 | 0 | PASS |
| 18 | TABLA_SENO | Q1.14 | 0x0002 | 0x376D | 0x376D | 8 | 1058 | 6 | 560 | 0 | PASS |
| 19 | TABLA_COSENO | Q1.14 | 0x0002 | 0x2000 | 0x2000 | 8 | 1058 | 6 | 560 | 0 | PASS |
| 20 | RAIZ_NON_RESTORING | Q6.9 | 0x0100 | 0x0010 | 0x0010 | 8 | 1058 | 6 | 560 | 0 | PASS |
| 21 | CONVERSION_HEX | texto | 0x3241 | 0x002A | 0x002A | 18 | 1058 | 6 | 560 | 0 | PASS |
| 22 | CONVERSION_BIN | texto | 0x000A | 0x000A | 0x000A | 6 | 1058 | 6 | 560 | 0 | PASS |
| 23 | CIRCLE_SHIFT | 16 bits | 0x0001 | 0x0080 | 0x0080 | 6 | 1058 | 6 | 560 | 0 | PASS |
| 24 | FROM_QM_N | Q15.16 | 0x0204 | 0x0204 | 0x0204 | 5 | 1058 | 6 | 560 | 0 | PASS |
| 25 | TO_QM_N | Qm.n | 0x0204 | 0x0204 | 0x0204 | 5 | 1058 | 6 | 560 | 0 | PASS |
| 26 | FROMDEC | texto | 0x002A | 0x002A | 0x002A | 5 | 1058 | 6 | 560 | 0 | PASS |
| 27 | TODEC | texto | 0x002A | 0x002A | 0x002A | 5 | 1058 | 6 | 560 | 0 | PASS |
| 28 | GETC_GETLINE_OUTVAL | I/O | 0x0000 | 0x0000 | 0x0000 | 5 | 1058 | 6 | 560 | 0 | PASS |
| 29 | SENO_CHEBYSHEV_PADE | Q1.14 | 0x0002 | 0x4000 | 0x4000 | 8 | 1058 | 6 | 560 | 0 | PASS |
| 30 | MATH_HELPERS_DQ16 | Q15.16 | 0x0010 | 0x0004 | 0x0004 | 13 | 1058 | 6 | 560 | 0 | PASS |
| 31 | SQRT_NR_Q8 | Q7.8 | 0x0004 | 0x0200 | 0x0200 | 14 | 1058 | 6 | 560 | 0 | PASS |

## Totales

- Instrucciones globales: 292
- Minimo por interfaz: 5
- Maximo por interfaz: 28
- Promedio por interfaz: 9.42
- Bytes de imagen acumulados: 32798
- Bytes de codigo acumulados: 17174
- Bytes de datos acumulados: 186
- Bytes observados acumulados: 17360
- Pico de memoria acumulado: 17360
- Pico maximo por interfaz: 560
- Error absoluto maximo: 0
- HALT en todas las interfaces: si
