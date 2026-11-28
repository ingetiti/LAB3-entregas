# EXP optimizada para BYTEX-16

Actualización del 26 de noviembre de 2026. La función mantiene el algoritmo multiplicativo de alta radix, las tablas y los seis pasos generales. El objetivo es ejecutar menos instrucciones, conservando exactamente los enteros de salida de la referencia anterior y de C.

## Cambios de implementación

- Las diferencias de la selección del dígito se resuelven con SUB.
- El producto de tres palabras base 2^15 por d, de 0 a 16, usa MUL y MULU. Se convierten ambas mitades al acarreo de base 2^15 para no perder bits altos.
- REDONDEA separa el desplazamiento en cero, uno o dos limbos y un resto de 0 a 14. Usa SHL/SHR para componer el cociente y el bit descartado para el mismo redondeo anterior. Ya no copia los bits uno por uno.
- La escala inicial usa desplazamientos directos. El ajuste final calcula 22-k con SUB.

## Convención

R0 recibe Q3.12 y devuelve Q7.8 signed de 16 bits. R1-R7 se conservan; R6 no se modifica. El resultado también determina NZP al retornar. EST_EXP y NUM_ITER permanecen en memoria. La rutina es estática y no reentrante. No utiliza TRAP ni HALT.

## Mediciones

| Entrada x | Antes | Optimizada | Salida Q7.8 |
|---|---:|---:|---:|
| 0 | 24 | 24 | 256 |
| 1 | 4.907 | 1.527 | 696 |
| 2 | 4.898 | 1.416 | 1.892 |
| 3 | 5.016 | 1.755 | 5.142 |
| 4 | 5.021 | 1.576 | 13.977 |

El barrido uniforme de las 65.536 entradas baja de 222.466.798 a 68.450.717 instrucciones, un 69,23 %. Mejoran 45.425 entradas y 20.111 quedan iguales por las rutas rápidas; ninguna empeora. No se cuentan la impresión ni HALT del llamador. La rutina ocupa 1.054 bytes, frente a 1.052. Los dos programas mínimos de comparación ocupan 1.058 y 1.056 bytes, respectivamente.

El número de vueltas del algoritmo sigue siendo seis en la ruta general: una vuelta requiere menos trabajo. Las rutas rápidas de x=0, saturación inicial y redondeo temprano a cero mantienen NUM_ITER=0. La equivalencia se comprueba frente al algoritmo C, no frente a una exponencial real exacta.

## Verificación y uso

Se comprobaron las 65.536 entradas completas con igualdad de salida, estado y contador, preservación de R1-R7 y NZP de salida. Además, REDONDEA pasó 23.144 casos sobre sus 44 desplazamientos admitidos y el producto pasó 17.544 casos. Se volvió a compilar con advertencias tratadas como errores y pasó toda la suite. La regeneración produce los mismos bytes de los 38 módulos.

La referencia previa está en tests/exp_previa. test_exp_optimized compara ambos módulos con un llamador mínimo idéntico y genera build/exp_comparacion.csv y build/exp_optimizacion.json. docs/exp_casos.csv contiene una selección pequeña; docs/exp_optimizacion.json resume todo el dominio.

ejemplos/exp_bytex16.asm es una prueba independiente, con entrada fija 3. Imprime x1416 y conserva el resultado en R0 y RES_EXP. Cambiar ENTRADA y reensamblar para otros valores. El archivo benchmark/modulos/g6_EXP.asm ya está enlazado en los objetos actualizados de la calculadora y registrado en el regenerador. El ejemplo y la biblioteca se entregan dentro de este proyecto.

La ISA conserva su codificación 1.1. Esta biblioteca se ensambla para nuestra ISA local; el fuente LC-3 del simulador del Grupo 8 se conserva por separado. CMake sigue siendo una alternativa no ejecutada en esta validación; la compilación comprobada es GCC con los scripts Windows.
