# Metricas automaticas de benchmarks migrados

| Benchmark | Instrucciones | Bytes imagen | Memoria observada | Pico memoria | PC HALT | Error absoluto maximo | Estado |
|---|---:|---:|---:|---:|---:|---:|---|
| migrated_easy | 18 | 36 | 48 | 48 | 0x3024 | 0 | PASS |
| migrated_core_v2 | 31 | 62 | 74 | 74 | 0x303E | 0 | PASS |
| migrated_cordic_div | 31 | 56 | 60 | 60 | 0x3026 | 0 | PASS |
| migrated_sqrt | 7 | 14 | 18 | 18 | 0x300E | 0 | PASS |
| migrated_sincos_table | 17 | 34 | 42 | 42 | 0x3022 | 0 | PASS |
| phase4_core | 14 | 28 | 40 | 40 | 0x301C | 0 | PASS |
| phase4_integral | 87 | 174 | 236 | 236 | 0x30AE | 0 | PASS |

## Referencias matematicas

| Referencia | Valor hexadecimal |
|---|---:|
| sin(pi/3) Q1.14 | 0x376D |
| cos(pi/3) Q1.14 | 0x2000 |
| sin(pi/2) Q1.14 | 0x4000 |
| cos(pi/2) Q1.14 | 0x0000 |
