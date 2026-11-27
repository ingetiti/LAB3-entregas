# Grupo 09 · SQRT Newton-Raphson (LC-3 independiente)

**Consigna:** calcular la raíz cuadrada mediante Newton-Raphson aplicado a la raíz recíproca.

## Integrantes

- Mantulak, Gustavo (@Gustavo-Mantu)
- Casales, Mia (@miacasales)
- Münz, Yessica (@yessi2004)

## Implementación

Se utiliza la iteración

\[
y_{n+1} = y_n\,\frac{3 - x y_n^2}{2}, \qquad \sqrt{x} \approx x\,y_n.
\]

- **Núcleo:** punto fijo Q7.8, semilla `y0 = 0.25`, seis iteraciones, multiplicación `MULQ` y división `HALF` optimizadas.
- **Rango ampliado:** reducción por potencias de 4 hasta el intervalo [4,16] y recuperación de escala en Q15.16 de dos palabras.
- **Entrada matemática:** 0 ≤ x < 32768. El lector interactivo acepta punto decimal y **hasta cuatro cifras decimales**; no acepta negativos.
- **Salida:** parte entera y fraccionaria Q15.16, mostrada en decimal con ocho posiciones después del punto. La impresión decimal es truncada a ocho cifras, y **la precisión interna sigue siendo Q7.8**.
- **Independencia:** no se utiliza ni se modifica ningún archivo de `grupo27/` ni de otros grupos. Todas las dependencias están incluidas en `grupo09/`.

### Archivos (todos del Grupo 09)

| Archivo | Función |
| --- | --- |
| `main.asm` | Programa principal con consola interactiva; **archivo de entrada**. |
| `sqrt_nr_q8.asm` | Núcleo Newton-Raphson Q7.8 con `MULQ` y `HALF` optimizadas. |
| `sqrt_nr_dq16.asm` | Normalización y recuperación de escala Q15.16. |
| `sq9_math_helpers.asm` | Rotación de 32 bits y conversiones Q15.16↔Q7.8 propias. |
| `sq9_read.asm` | Lectura decimal, validación de rango y conversión a Q15.16. |
| `sq9_print.asm` | Impresión decimal autónoma, sin usar `OUTVAL` ni `TODEC`. |
| `README_SQRT_NR.md` | Contratos técnicos y pruebas de la implementación. |

### Cómo probar en LC-3 Simulator

1. Abrir **https://lc3.lgrum.xyz/**.
2. Descargar los archivos del repositorio.
3. En **Subir archivos**, cargar los archivos del repositorio.
4. Seleccionar `main.asm` → **Usar como entrada**.
5. Presionar **Ensamblar → Reiniciar → Continuar**.
6. En la consola, escribir un número y presionar **Enter**. Repetir tantas veces como sea necesario; escribir `q` y Enter para salir.

### Pruebas de referencia

| Entrada | Salida esperada en pantalla |
| ---: | ---: |
| `0` | `0.00000000` |
| `0.5` | `0.71093750` |
| `2` | `1.42187500` |
| `4` | `1.98437500` |
| `9` | `2.98828125` |
| `16` | `4.00000000` |
| `36` | `5.97656250` |
| `100` | `10.04687500` |
| `1000` | `31.25000000` |

`-9` informa argumento negativo, `40000` informa fuera de rango y `abc` informa entrada inválida. Usar **punto**, no coma, como separador decimal.

### Alcance de la validación

Se ejecutaron pruebas de instrucciones LC-3 mediante un intérprete de validación local: casos anteriores, errores de entrada, múltiples cálculos consecutivos y 160 entradas decimales aleatorias. Se comprobaron también los desplazamientos PC-relativos de los seis módulos y no se detectaron referencias fuera de rango. **La nueva versión independiente todavía debe verificarse en el simulador web**, aunque el núcleo integrado ya se había probado allí.

Las optimizaciones MULQ+HALF redujeron aproximadamente un **56 %** las instrucciones del núcleo para √9 frente al núcleo original. Esa medición no incluye lectura, impresión ni normalización.

### Bitácora

[Bitácora del Grupo 09](https://docs.google.com/document/d/1y0KH7npD7WXnLNtVTXCE_g3k6S87dZBEdLG64QTJp9Q/edit?usp=sharing).
