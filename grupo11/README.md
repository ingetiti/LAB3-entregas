# Grupo 11 · Parte de CORDIC para LOG

**Consigna:** Iteración de la serie atanh

## Integrantes

- Morinigo, Santiago Nahuel (@morinigosantiago00-dot)
- Kelm, Nayla Victoria (@naylakelm19-oss)
- Gomez, Pablo Daniel (@danigom429-art)

## Archivos

- `cordic_log_subrutina.asm`: Módulo `CORDIC_LOG_SUBRUTINA` con la subrutina `CORDIC_LOG_BASE` (logaritmo natural, Q3.12) y `ASR` (desplazamiento a la derecha, la usa por dentro). Sin `.ORIG` y terminado con `.END`. No trae programa principal.
- `Lab3_11.asm`: Programa principal mínimo (un solo valor, m = 0.75).
- `main_pruebas.asm`: Programa principal con 17 casos y verificación automática (ver abajo).

## Cómo probarlo

**Con el programa principal mínimo**

- Abrir <https://lc3.lgrum.xyz/> y cargar `cordic_log_subrutina.asm` en la sección de Archivos.
- Crear un archivo `main.asm` y elegir **Usar como entrada** en sus opciones (`...`).
- Crear el `main` con el contenido de debajo.
- **Ensamblar** (la pestaña de problemas tiene que quedar en 0) y pulsar **▶ Continuar**.
- Al llegar al `HALT`, R0 tiene que valer `xFB64` (-1180, que en Q3.12 es -0.2881; ln 0.75 real = -0.2877).

```asm
            .ORIG x3000
            .EXTERNAL CORDIC_LOG_SUBRUTINA-CORDIC_LOG_BASE

            LD   R0, M               ; m en Q3.12
            LD   R5, LOG_PTR         ; (R5 vuelve intacto)
            JSRR R5                  ; R0 = ln(m) en Q3.12
            HALT

M           .FILL x0C00              ; 0.75
LOG_PTR     .FILL CORDIC_LOG_SUBRUTINA-CORDIC_LOG_BASE
            .END
```


**Ejemplo de entrada y salida**

| m (Q3.12) | R0 al entrar | R0 al salir | Valor | ln(m) real |
| --- | --- | --- | --- | --- |
| 0.25 | x0400 | xE9C9 (-5687) | -1.3884 | -1.3863 |
| 0.5 | x0800 | xF4E0 (-2848) | -0.6953 | -0.6931 |
| 0.75 | x0C00 | xFB64 (-1180) | -0.2881 | -0.2877 |
| 1.0 | x1000 | x0000 (0) | 0.0000 | 0 |
| 2.0 | x2000 | x0B18 (2840) | 0.6934 | 0.6931 |
| 3.0 | x3000 | x1190 (4496) | 1.0977 | 1.0986 |
| 7.99976 | x7FFF | x2144 (8516) | 2.0791 | 2.0794 |

## Subrutinas

Siguen la plantilla de subrutinas del repositorio: R0 es la entrada y la salida, no se usa R6 y R1 a R5 y R7 vuelven como se entregaron. Los registros se guardan en palabras de memoria con `ST` y se restauran con `LD`, por eso las rutinas no son reentrantes.

- `CORDIC_LOG_BASE`: logaritmo natural en punto fijo.
    - Entrada: R0 = m en Q3.12 (entero de 16 bits con signo, 1.0 = x1000).
    - Salida: R0 = ln(m) en Q3.12.
    - Casos especiales: si m ≤ 0 (de x0000 y de x8000 a xFFFF) devuelve x8000 (-8.0). Si ln(m) quedaría por debajo de -8.0, satura en x8000; eso solo pasa con m = x0001. No hay palabra de estado: el valor x8000 es la única señal.
    - Cómo funciona: ver Algoritmo. Usa `ASR` 26 veces por llamada.
- `ASR`: R0 = R0 >> R5 (R5 de 1 a 15), con redondeo hacia cero. La LC-3 no tiene desplazamiento a la derecha, así que toma el valor absoluto, reconstruye los 16 − n bits altos con un lazo de duplicación y reaplica el signo. Conserva R1 a R5.

## Algoritmo

CORDIC hiperbólico en modo vectorial (iteración de la serie atanh). Se usa la identidad ln(m) = 2·atanh((m − 1)/(m + 1)):

1. Normalización: si m < 0.5 se lo multiplica por 2 hasta que sea ≥ 0.5, contando k desplazamientos (en Q3.12 el ln(m) final se corrige restando k·ln 2, con ln 2 = 2839).
2. Inicio: x = m/2 + 0.5, y = m/2 − 0.5, z = 0. Se usa la mitad de m + 1 y de m − 1: la razón y/x es la misma pero x no desborda cerca de m = 8.
3. Lazo de 13 iteraciones con i = 1, 2, 3, 4, 4, 5, ..., 12 (la iteración 4 se repite, como exige el CORDIC hiperbólico para converger):
    - Si y > 0: x = x − (y >> i), y = y − (x >> i), z = z + atanh(2⁻ⁱ).
    - Si y ≤ 0: x = x + (y >> i), y = y + (x >> i), z = z − atanh(2⁻ⁱ).
4. Cierre: ln(m) = 2·z − k·ln 2.

Los valores atanh(2⁻ⁱ)·4096 (2250, 1046, 515, 256, 256, 128, ..., 1) están en la tabla `LUT_ATANH`, en el mismo orden que `SEQ_I`.

**Iteraciones:** 13 fijas, sin importar m. Cada llamada ejecuta entre 2497 y 2595 instrucciones (promedio 2539), medido en un emulador de la LC-3 aparte del simulador del curso (con m ≤ 0 sale en 18). Casi todo el costo es `ASR` (26 llamadas). El módulo completo ocupa 156 palabras, con sus datos (113 de código y 43 de datos).

## Formato de punto fijo, rango y precisión

Todo el cálculo se hace con enteros de 16 bits en Q3.12 (1 bit de signo, 3 enteros y 12 fraccionarios; `raw = valor × 4096`, en complemento a 2). No hay emulación de punto flotante.

- Entrada: m de x0001 a x7FFF, es decir de 0.000244 a 7.99976, con resolución 1/4096. El CORDIC hiperbólico solo converge para m entre 0.107 y 9.37; la normalización de m < 0.5 y la mitad de m + 1 / m − 1 cubren el resto del rango.
- Salida: Q3.12, de -8.0 a +2.0794 (ln 7.99976 = x2144 = 8516). La salida no desborda para ninguna entrada válida.
- Precisión: se recorrieron las 32 767 entradas válidas (x0001 a x7FFF) comparando con ln real de la entrada ya cuantizada. El error máximo fue 17.2 LSB (0.0042) en m = 0.81323; el error medio, 2.2 LSB (0.0005); el 15 % de las entradas da exactamente el valor redondeado.

| Rango de m | Error máximo (LSB) | Error medio (LSB) |
| --- | --- | --- |
| 0.0002 a 0.5 | 15.8 | 3.4 |
| 0.5 a 1 | 17.2 | 3.6 |
| 1 a 2 | 15.6 | 3.2 |
| 2 a 4 | 10.5 | 2.1 |
| 4 a 8 | 9.2 | 1.7 |

El error viene del truncamiento en Q3.12 y no baja de unos 10-17 LSB con 12 bits fraccionarios sin bits de guarda. Con m < 0.01 el error es relativo a un m ya muy cuantizado.

## Cómo usarla desde otro programa

El archivo se llama `cordic_log_subrutina.asm`, así que el símbolo se importa como `CORDIC_LOG_SUBRUTINA-CORDIC_LOG_BASE`:

```asm
            .ORIG x3000
            .EXTERNAL CORDIC_LOG_SUBRUTINA-CORDIC_LOG_BASE

            LD   R0, M               ; m en Q3.12
            LD   R5, LOG_PTR         ; (R5 vuelve intacto)
            JSRR R5                  ; R0 = ln(m) en Q3.12
            HALT

M           .FILL x0C00              ; 0.75
LOG_PTR     .FILL CORDIC_LOG_SUBRUTINA-CORDIC_LOG_BASE
            .END
```

Después de la llamada, un R0 igual a x8000 indica m ≤ 0 o resultado saturado.

## Validación

- Se recorrieron las 32 767 entradas válidas en un modelo en C que reproduce paso a paso las operaciones enteras del assembly (los mismos desplazamientos, tablas y redondeos).
- La subrutina se ejecutó en un emulador de la LC-3 aparte del simulador del curso: 809 entradas (los bordes x0001, x0002, x0003, x0100, x07FF, x0800, x1000, x7000, x7FFF y una muestra del resto del rango) dieron el mismo resultado que el modelo en C.
- En esos casos R1 a R5, R6 y R7 volvieron intactos aunque se los cargó antes con valores distintos de cero, y la rutina no escribió fuera de sus propias palabras de datos.

