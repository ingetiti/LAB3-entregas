# Evidencia: LC10 contra la cátedra

Generado con `python bench/evidencia.py RUTA` el 25/11/2026 17:27, Python 3.13.18 en Linux 6.18.44-fc-v880.

Huella del código usado: `asm/opt10` = `d4e554bb1d112dd1`, `lc10/` = `819527526cfd465e`. Si cambia un módulo o el simulador, la huella cambia y esta evidencia hay que regenerarla.

Código de salida 0 = sin diferencias (en `entradas`, 1 indica las diferencias conocidas de seno y coseno por tabla fuera de 0..2π; ver `docs/ISA.md`, sección 12).

| # | Qué compara | Resultado (líneas de la salida) | Archivo |
| --- | --- | --- | --- |
| 1 | pruebas automáticas (ISA, ensamblador, simulador, ventana si hay pantalla, benchmark) | `Ran 244 tests in 8.756s · OK (skipped=87)` | [01_pruebas.txt](01_pruebas.txt) (código 0) |
| 2 | el benchmark en LC-3 con el ensamblador y el simulador de la cátedra | `salida idéntica a lc3_baseline_salida.txt: sí · LÍNEA BASE REPRODUCIDA` | [02_linea_base_lc3.txt](02_linea_base_lc3.txt) (código 0) |
| 3 | el main de la cátedra en LC10 y en LC-3: misma salida, instrucciones y palabras | `LC10 · 15.822 usuario + 10.901 SO = 26.723 instrucciones · 4963 palabras · x3000–x56C5 · LC-3 · 357.505 instrucciones · 7896 palabras · x3000–x4ED7 · salida idéntica a la de LC-3: sí · diferencia: instrucciones de usuario -95.6 %, palabras -37.1 %` | [03_benchmark_lc10.txt](03_benchmark_lc10.txt) (código 0) |
| 4 | reparto de instrucciones y palabras por módulo (puerto optimizado) | `salida idéntica a la de la línea base LC-3: sí` | [04_benchmark_por_modulo.txt](04_benchmark_por_modulo.txt) (código 0) |
| 5 | puerto directo (traducción sin optimizar): misma salida | `salida idéntica a la de la línea base LC-3: sí` | [05_benchmark_puerto_directo.txt](05_benchmark_puerto_directo.txt) (código 0) |
| 6 | las 39 subrutinas contra los módulos reales de la cátedra y 17 sesiones del menú | `RESULTADO: todo coincide` | [06_modulos.txt](06_modulos.txt) (código 0) |
| 7 | el main de la cátedra con operandos al azar, operación por operación | `RESULTADO: 13 casos distintos` | [07_entradas.txt](07_entradas.txt) (código 1) |
| 8 | seno y coseno por tabla con el ángulo dentro de 0..2π | `RESULTADO: todo coincide` | [08_entradas_dominio.txt](08_entradas_dominio.txt) (código 0) |
| 9 | seno de Taylor de la cátedra contra el modelo de sus cuentas | `casos: 3704 / distintos del modelo exacto: 0 / R1 a R5 preservados: True` | [09_seno_modelo.txt](09_seno_modelo.txt) (código 0) |
| 10 | seno de Taylor en LC10, las 65.536 entradas, contra ese modelo | `valores de R0 probados: 65536 / distintos del modelo exacto: 0 / sin preservar R1-R5/R6/R7: 0` | [10_seno_lc10.txt](10_seno_lc10.txt) (código 0) |
| 11 | TODEC de la cátedra contra el modelo de sus cuentas | `casos: 5011 / distintos del modelo: 0 / instrucciones LC-3 por llamada: prom 2225, máx 4621 · fórmula cerrada 1953125*(f>>7) + tabla de 7 constantes: 0 diferencias de 65536` | [11_todec_modelo.txt](11_todec_modelo.txt) (código 0) |
| 12 | TODEC en LC10: 328.160 llamadas contra ese modelo | `parte 0/1 / llamadas probadas: 328160 / distintas del modelo exacto: 0 / registros sin preservar: 0 / escrituras fuera del buffer de 17 bytes: 0` | [12_todec_lc10.txt](12_todec_lc10.txt) (código 0) |
| 13 | SUMOVER y CIRCLSH en LC10, unas 400.000 llamadas | `SUMOVER: 200242 casos, distintos: 0, instrucciones por llamada: 5 · CIRCLSH: 200904 casos, distintos: 0, instrucciones por llamada: mín 5, máx 20` | [13_sumover_circlsh.txt](13_sumover_circlsh.txt) (código 0) |
| 14 | DIV_NEWTON en LC10 contra el módulo real | `12210 casos, 0 diferencias` | [14_div_newton.txt](14_div_newton.txt) (código 0) |
| 15 | EXP_Q3_12 en LC10, las 65.536 entradas, contra el puerto directo | `65536 entradas [0, 65536), 0 diferencias; instrucciones medias ref 4020 / opt 893` | [15_exp.txt](15_exp.txt) (código 0) |
| 16 | división larga del grupo: LC-3 contra LC10 | `reduccion de instrucciones (promedio): 46.2 %` | [16_division_larga.txt](16_division_larga.txt) (código 0) |
