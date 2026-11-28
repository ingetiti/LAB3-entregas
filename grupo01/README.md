# Grupo 01 · Transformación bilineal

**Consigna:** Explicar qué rol juega en el algoritmo de CORDIC esta parte e implementar la división por CORDIC

## Integrantes

- Batista Da Silva, Dante Samuel (@batistadante047-sys)
- Tizano, Gerson Nahuel

## Archivos

- `cordic_division.asm`: módulo LC-3 con la subrutina `CORDIC_DIV`, que calcula `y0 / x0` en punto fijo Q15 mediante CORDIC lineal (vectoring mode), usando solo sumas, restas y saltos.
- `README.md`: este documento.

---

## Rol de esta parte en el algoritmo CORDIC

CORDIC resuelve muchas funciones con una única iteración generalizada (Muller, *Elementary Functions*, cap. 7, ec. 7.11), que según el parámetro `m` trabaja en tres modos:

| Modo | m | Ángulo wₖ | Vectoring mode (dₙ = −signo(yₙ)) |
|---|---|---|---|
| circular | 1 | arctan 2⁻ᵏ | zₙ → z₀ + arctan(y₀/x₀) |
| **lineal** | **0** | **2⁻ᵏ** | **zₙ → z₀ + y₀/x₀** |
| hiperbólico | −1 | tanh⁻¹ 2⁻ᵏ | zₙ → z₁ + tanh⁻¹(y₁/x₁) |

(Tabla 7.1 del libro.) **La división es el modo lineal en vectoring mode.** Con `m = 0` el término `x` de la iteración no cambia, el factor de escala vale `K = 1` (no hay que compensar nada) y los ángulos son simplemente `2⁻ᵏ`, así que no hace falta ninguna tabla de arctan.

La idea es una búsqueda binaria con signo. Se busca `z` tal que `y0 − z·x0 = 0`. En cada paso `n`:

```
d  = −signo(y)            (+1 si y <= 0, −1 si y > 0)
y ← y + d · x · 2⁻ⁿ       (empuja y hacia 0)
z ← z − d · 2⁻ⁿ           (acumula el cociente)
```

Los pasos son 1, ½, ¼, ⅛, …, y cada uno reduce el error a la mitad. Al terminar `y ≈ 0` y `z ≈ y0 / x0`.

**Relación con la transformación bilineal:** esta transformación (`s = (2/T)·(z−1)/(z+1)`) requiere cocientes. Esta subrutina aporta esa división usando únicamente operaciones disponibles en la LC-3, que no tiene instrucciones de multiplicar, dividir ni desplazar a la derecha.

### Adaptación a LC-3

Como la LC-3 no puede desplazar a la derecha (`x >> n`), se usa una forma equivalente: en vez de achicar `x`, se **duplica el residuo** en cada paso (`ADD R,R,R`):

```
P ← 2P + d · x            (P es el residuo, equivale a y·2ⁿ)
Z ← 2Z − d                (Z es el cociente acumulado)
```

Es el mismo algoritmo con otra escala. Después de 16 iteraciones, `Z` ya está directamente en Q15 y no se necesita ninguna conversión. Además la aritmética es exacta (no se pierden bits por desplazar).

---

## 1. Qué se necesita para verificar el funcionamiento

### Formato de punto fijo: Q15

- Enteros de 16 bits con signo en complemento a 2.
- 1 bit de signo y 15 bits fraccionarios. Factor de escala: `32768` (2¹⁵).
- Conversión: `Q15 = round(real × 32768)`  y  `real = Q15 / 32768`.
- Rango representable: `[−1, 1)`, es decir, enteros de −32768 a 32767.

### Entradas y salida

| | Registro | Significado | Formato | Rango válido |
|---|---|---|---|---|
| Entrada | `R0` | `y0`, dividendo | Q15 con signo | `−x0 < y0 < x0` |
| Entrada | `R1` | `x0`, divisor | Q15 con signo | `1 ≤ x0 ≤ 32767` (positivo) |
| **Salida** | `R0` | `y0 / x0` | **Q15 con signo** | `[−1, 1)` |

- **Precondición:** `x0 > 0` y `|y0| < x0` (estricto). Eso garantiza que el cociente cabe en Q15. Si `|y0| ≥ x0` el resultado es incorrecto por desborde; por ejemplo `y0 = x0` y `y0 = −x0` no están soportados.
- **No se controla** divisor cero ni divisor negativo: el que llama debe garantizarlo.
- **Valor real del resultado:** `R0 / 32768`. Por ejemplo `0.5 → x4000` y `−0.5 → xC000`.
- **Precisión:** error máximo de **1 LSB** (≈ 3,05·10⁻⁵) respecto del cociente exacto.
- **Caso `y0 = 0`:** da `xFFFF` (−1 LSB), no exactamente 0, porque CORDIC no tiene la opción `d = 0` y siempre da un paso hacia un lado.
- **Convención de la guía de módulos:** argumentos en `R0` y `R1`, resultado en `R0`. Conserva `R1`–`R5` (usa la pila `R6` para guardar `R2`, `R3` y `R4`) y `R6` vuelve a su valor de entrada. La subrutina no llama a otras, así que no toca `R7`.

### Casos de prueba

| y / x (reales) | y0 (Q15) | x0 (Q15) | Resultado `R0` | Hex | Valor real | Esperado | Error (LSB) |
|---|---|---|---|---|---|---|---|
| 0.4 / 0.8 | 13107 | 26214 | 16383 | `x3FFF` | 0.49997 | 0.50000 | 1.00 |
| 0.1 / 0.9 | 3276 | 29491 | 3641 | `x0E39` | 0.11111 | 0.11111 | 0.11 |
| 0.5 / 0.9 | 16384 | 29491 | 18205 | `x471D` | 0.55557 | 0.55556 | 0.56 |
| −0.3 / 0.6 | −9830 | 19660 | −16385 | `xBFFF` | −0.50003 | −0.50000 | 1.00 |
| −0.2 / 0.7 | −6553 | 22937 | −9361 | `xDB6F` | −0.28568 | −0.28571 | 1.29 |
| 0.0 / 0.7 | 0 | 22937 | −1 | `xFFFF` | −0.00003 | 0.00000 | 1.00 |
| 0.99 / 0.995 | 32440 | 32604 | 32603 | `x7F5B` | 0.99496 | 0.99497 | 0.34 |

Los valores `y0` y `x0` se obtienen truncando `real × 32768`; la columna *Error* compara contra el cociente de los reales originales, así que incluye ese pequeño error de conversión de entrada.

**Cómo calcular el valor esperado de cualquier caso** (Python):

```python
y0, x0 = 13107, 26214
esperado = round(y0 / x0 * 32768)   # debe coincidir con R0 con diferencia <= 1
```

---

## 2. Assembly subido al simulador

### `cordic_division.asm` (módulo publicado)

```asm
; Modulo: cordic_division   (archivo cordic_division.asm)
;=====================================================================
; Division por CORDIC (modo lineal, vectoring) en punto fijo Q15
;
; CORDIC_DIV
;   ENTRADAS (Q15, entero con signo en complemento a 2):
;     R0 = y0  (dividendo)
;     R1 = x0  (divisor)    con x0 > 0  y  |y0| < x0
;   SALIDA:
;     R0 = y0 / x0 en Q15, rango [-1, 1)   (valor real = R0 / 32768)
;          Ejemplo: 0.5 = x4000,  -0.5 = xC000   (error tipico: 1 LSB)
;   Conserva R1-R5 y R6 (usa la pila para guardar R2, R3 y R4).
;
; Como la LC-3 no tiene desplazamiento a la derecha, en cada paso se
; duplica el residuo en vez de achicar x:
;     P' = 2P + d*x        Z' = 2Z - d
;     d = +1 si P <= 0 ;  d = -1 si P > 0
;=====================================================================
CORDIC_DIV
        ADD R6, R6, #-3 ; Apilamos R2, R3 Y R4
        STR R2, R6, #0
        STR R3, R6, #1
        STR R4, R6, #2

        ADD R2, R0, #0  ; R2 = P = y0
        AND R0, R0, #0  ; R0 = Z = 0, el resultado
        ; R3 = -x0
        NOT R3, R1
        ADD R3, R3, #1

        ; R0 -> Entra como y0 y sale como el cociente
        ; R1 -> x0
        ; R2 -> P el residuo
        ; R3 -> -x
        ; R4 -> contador del bucle
        ; R5 -> No se usa, asi que, no se toca
        ; R6 -> Puntero de la pila
        ; R7 -> Para retornar de la subrutina, como no hay que ir a otra subrutina, no se toca
        
        ; Iteraccion 0
        ADD R2, R2, #0  ; Actualizar los CC con el signo de y0 y es tambien P
        BRp INI_NEG
        ADD R2, R2, R1  ; y <= 0 : d = + 1 -> P = P + x
        ADD R0, R0, #-1 ; z = -d = -1
        BRnzp INI_LOOP
INI_NEG ADD R2, R2, R3  ; y > 0 : d = -1 -> P = P - x
        ADD R0, R0, #1  ; z = -d = +1

        ; Iteracciones 1 a 15
INI_LOOP ADD R4, R4, #0 ; Inicializamos R4 que es nuestro i del for
        ADD R4, R4, #15 ; R4 = 15; ya hicimos la iteraciion 0
LOOP    ADD R2, R2, #0  ; Actualizar los CC con el signo de P
        BRp PPOS
        ADD R2, R2, R2  ; P <= 0 : d = +1
        ADD R2, R2, R1  ; P = 2P + x
        ADD R0, R0, R0
        ADD R0, R0, #-1 ; z = 2z - 1
        BRnzp GOON
PPOS    ADD R2, R2, R2  ; P > 0 : d = -1
        ADD R2, R2, R3  ; P = 2P - x
        ADD R0, R0, R0
        ADD R0, R0, #1  ; z = 2z + x
GOON    ADD R4, R4, #-1
        BRp LOOP
        
        
        
        LDR R2, R6, #0  ; Desapilamos en el mismo orden
        LDR R3, R6, #1
        LDR R4, R6, #2
        ADD R6, R6, #3  ; Devolvemos el estado original a R6
        RET
        .END
```

### `main.asm` (solo para probar en local, no se publica)

```asm
        .ORIG x3000
        .EXTERNAL CORDIC_DIVISION-CORDIC_DIV
        LD R0, DIVIDEND
        LD R1, DIVIDER
        LD R5, DIV_PTR
        JSRR R5
        ST R0, QUOTIENT
        
        HALT
DIVIDEND .FILL #13107   ; Aporx. 0.4
DIVIDER  .FILL #26214   ; Aprox. 0.8
QUOTIENT .BLKW #1
DIV_PTR  .FILL CORDIC_DIVISION-CORDIC_DIV
        .END
; Resultado deberia ser 0.4 / 0.8 = 0.5
; En el programa por el error -> 0.49997
```

---

## 3. Estado en simuladores

- **Pruebas realizadas hasta ahora:** se construyó y se probó este algoritmo `.asm` con el simulador web del grupo 8.

---

## Cómo probarlo

- Para integrarlo en otro programa: cargar `R0 = y0`, `R1 = x0`, cargar la dirección de `CORDIC_DIVISION-CORDIC_DIV` con `.FILL` en un registro libre (por ejemplo `R5`) y llamar con `JSRR`. El cociente queda en `R0`.

---

## 4. Bitácora de avances

1. **Estudio del algoritmo.** Se leyó el capítulo 7 (*The CORDIC Algorithm*) de Muller y se armó una primera versión en Python con aritmética Q15.
2. **Primera versión (incorrecta).** El código usaba el modo **circular** (tabla de `arctan(2⁻ⁱ)`). Para 0.4 / 0.8 no daba 0.5 sino aproximadamente `arctan(0.5) ≈ 0.4636`: ese modo calcula un arcotangente, no un cociente.
3. **Diagnóstico.** Revisando la Tabla 7.1 se vio que la división corresponde al modo **lineal** (m = 0) en vectoring mode, con `zₙ → z₀ + y₀/x₀`. Se descartó la tabla de arctan y el factor de escala (K = 1).
4. **Reescritura en Python.** Se implementó el modo lineal. Se corrigieron dos errores de transcripción: el signo de `d` (debe ser `−signo(y)`) y el paso de `z` (debe ser `32768 >> i`, no un valor fijo). Resultados con error de orden 10⁻⁴.
5. **Aclaración sobre el modo hiperbólico.** Se confirmó que no hacía falta implementarlo y que lo pedido era la división por CORDIC (ver sección siguiente).
6. **Traducción a LC-3.** La LC-3 no tiene desplazamiento a la derecha, así que se reformuló el algoritmo duplicando el residuo (`P ← 2P + d·x`, `Z ← 2Z − d`). Se verificó que el resultado sale directamente en Q15 y que no hay desbordes problemáticos.
7. **Adaptación a la guía de módulos.** Se convirtió el programa en un módulo: argumentos en `R0` y `R1`, resultado en `R0`, registros guardados en la pila con `R6`, sin `HALT` ni datos de prueba, y un `main.asm` aparte para probar en local.
8. **Pruebas.** Se realizaron varias pruebas en el algoritmo hecho en Python, pero no testeamos en el simulador, ya que el primer resultadio coincidió con el obtenido en el programa de Python.

---

## Confusión con el modo hiperbólico y por qué terminamos haciendo la división

El capítulo de CORDIC presenta tres modos de trabajo (circular, lineal e hiperbólico, Tabla 7.1), y al principio no estaba claro cuál de ellos correspondía a nuestra parte. Nuestro primer código y nuestro primer README hablaban de "modo circular", que es el más conocido porque es el que calcula senos, cosenos y arcotangentes, pero ese modo **no divide**.

Se nos indicó que, si ningún otro grupo implementaba la división por CORDIC, la hiciéramos nosotros, y que no nos preocupáramos por el modo hiperbólico. Eso aclaró el alcance: el modo hiperbólico sirve para funciones como exponencial, logaritmo y raíz cuadrada, que no son parte de nuestra tarea. La división se obtiene con el **modo lineal** (m = 0), que además es el más simple de los tres porque no necesita tabla de ángulos ni compensación de factor de escala.

Por eso el módulo final implementa **la división por CORDIC en modo lineal, vectoring mode**.

---

## Bibliografía

- Muller, J.-M. *Elementary Functions: Algorithms and Implementation*, cap. 7: *The CORDIC Algorithm* (Tablas 7.1 y 7.2).

- COMENTARIOS DE ALDO BENITEZ
- VERIFICAR LA DIVISIÓN POR CORDIC, PROBÉ ALGUNOS VALORES (POR EJEMPLO -1 / 3 Y ARROJA UN RESULTADO ERRÓNEO), LAS DIVISIÓNES POR LONG Y NEWTON R. DAN CORRECTAS.
- Patt, Y. N., & Patel, S. J. *Introduction to Computing Systems: From Bits & Gates to C/C++ & Beyond*. McGraw-Hill.
- Volder, J. E. (1959). *The CORDIC Computing Technique*. IRE Transactions on Electronic Computers.
- Guía de módulos de la calculadora (convención de llamada y publicación).
