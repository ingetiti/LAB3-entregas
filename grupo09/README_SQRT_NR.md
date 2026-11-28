# Contrato técnico — SQRT Newton-Raphson (Grupo 09)

## Núcleo `SQRT_NR_Q8`

- Entrada: `R0 = x` en Q7.8 no negativo, `4 <= x <= 16`.
- Salida: `R0 = floor(x*y_final*256)` en Q7.8. Para argumentos fuera del rango devuelve 0.
- Conserva `R1` a `R7`, no usa `R6`.
- Iteración de raíz recíproca: `y <- y*(3-x*y^2)/2`, semilla `0.25`, seis iteraciones.
- Multiplicación `MULQ` mediante bits; división `HALF` mediante reconstrucción binaria.

## Adaptador `SQRT_NR_DQ16`

- Entrada: `R0 = palabra alta entera` (16 bits con signo), `R1 = palabra baja fraccionaria` (16 bits).
- Salida: `R0:R1 = sqrt(x)` aproximada en Q15.16 de 32 bits.
- Condición: `0 <= x < 32768`; para `x=0` retorna 0. El programa principal impide negativos.
- Normaliza `x = 4^k * t` con `4 <= t <= 16`, evalúa `sqrt(t)` y reescala por `2^k`.
- Depende solamente de `SQRT_NR_Q8`, `SQ9_ROTL32`, `SQ9_DQ16_TO_Q8`, `SQ9_Q8_TO_DQ16`, todos incluidos en el Grupo 09.

## Programa autónomo `main.asm`

Lee valores enteros o decimales (`0`, `9`, `0.5`, `1000`, `32767.9999`), con **hasta cuatro cifras decimales** y un punto como separador; convierte a Q15.16 mediante división binaria de 16 pasos. Los resultados se imprimen con ocho cifras decimales y se puede continuar calculando sin reiniciar. `q` permite terminar.

Archivos requeridos: `main.asm`, `sq9_read.asm`, `sq9_print.asm`, `sq9_math_helpers.asm`, `sqrt_nr_q8.asm`, `sqrt_nr_dq16.asm`.

No cargar módulos de los Grupos 08, 27 u otros: las dependencias son propias y están en esta carpeta.

## Precisión y rendimiento

El error numérico depende de la cuantización Q7.8 y puede crecer al amplificar el resultado en entradas grandes. La representación decimal con ocho cifras **no representa un aumento de precisión**. El núcleo conserva las optimizaciones y resultados previamente validados, pero el costo de E/S y normalización no está incluido en el benchmark del núcleo.
