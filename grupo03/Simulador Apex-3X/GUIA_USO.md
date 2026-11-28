# Guía sencilla de uso — Simulador Apex-3X

Esta guía explica paso a paso cómo usar el simulador **Apex-3X** y cómo ejecutar y revisar el **benchmark** oficial de 38 módulos.

---

## 1. Cómo abrir el simulador

- **En local (con Node.js):**
  ```bash
  npm install
  npm run dev
  ```
  Luego abrí `http://localhost:3000` en tu navegador.
- **En la web / GitHub Pages:** abrí directamente la URL publicada del proyecto (no requiere instalar nada).

---

## 2. Cómo usar el simulador paso a paso

La pantalla principal está organizada en 6 paneles que podés ocultar, mover o redimensionar desde la barra superior:

### Paso 1: Escribir o cargar un programa
- En el panel **Código fuente** podés escribir código assembly Apex-3X directamente.
- Si querés probar rápido, elegí uno de los programas del menú desplegable (arriba del editor) y hacé clic en **Cargar**.
- Al posicionar el cursor sobre una línea, debajo del editor aparece una ayuda rápida con la sintaxis de esa instrucción.

### Paso 2: Ensamblar
- Hacé clic en **Ensamblar** (o presioná **`Ctrl + Enter`**).
- Si el código es correcto, verás el mensaje en verde con el tamaño en bytes y la dirección de inicio (por ejemplo `x3000`), y el programa aparecerá en **Listado ensamblado**.
- Si hay algún error de sintaxis, hacé clic sobre el mensaje en rojo para ir directo a la línea con problema.

### Paso 3: Ejecutar y depurar
- **Ejecutar / Pausar (`F9`)**: corre el programa completo hasta `HALT` (o hasta encontrar un breakpoint).
- **Paso (`F10`)**: ejecuta una sola instrucción por vez. Es ideal para ver cómo cambian:
  - **Registros** (`R0` a `R7`, con `R6` como puntero de pila y `R7` como dirección de retorno) y **Flags** (`N`, `Z`, `P`, `C`).
  - **Memoria por byte**: resalta en amarillo el `PC` actual y en verde los bytes modificados.
- **Reiniciar (`F8`)**: devuelve registros, flags, memoria y consola al estado inicial del programa ensamblado.
- **Breakpoints**: hacé clic en cualquier fila del **Listado ensamblado** para activar o quitar un punto de detención (círculo rojo).
- **Vistas del listado**: podés alternar entre **ASM**, **HEX** y **BIN**, o pulsar **Ver PC** para centrar la vista en la instrucción actual.

### Paso 4: Entrada y salida en Consola
- Las salidas de `OUT` y `PUTS` se muestran en el panel **Consola**.
- Si el programa se detiene en **"Esperando entrada"** (`GETC` o `IN`), escribí el texto en el cuadro inferior de la consola y presioná **`Enter`**.

### Paso 5: Ver métricas y exportar
- En **Métricas de ejecución** ves en tiempo real: instrucciones de usuario, instrucciones de sistema operativo (SO), total, ciclos de reloj, tamaño, datos accedidos, lecturas/escrituras en memoria, pico de pila y desglose por tipo de instrucción.
- Desde la barra superior podés descargar **`.bin`**, **`.hex`** o un **Informe JSON** con todo el resumen de la ejecución.

---

## 3. Cómo probar el Benchmark (38 módulos)

El benchmark enlaza automáticamente `benchmark/main_grupo27.asm` con los 37 módulos de prueba y mide rendimiento, uso de memoria/pila y exactitud de resultados.

### Pasos para correrlo
1. En la barra de herramientas superior, hacé clic en **Modo Prueba y Benchmark**.
2. En el selector **Suite**, elegí qué querés ejecutar:
   - **Completo (`main_grupo27`) + desglose 23 operaciones** *(recomendado)*: corre el programa completo del menú y además evalúa por separado cada una de las 23 subrutinas.
   - **Solo programa completo**: corre todo `main_grupo27.asm` con su salida por consola.
   - **Solo prueba reducida**: corre la versión corta de 3 operaciones.
   - **Solo 23 subrutinas aisladas**: mide únicamente el cómputo puro de las 23 operaciones.
3. Hacé clic en **Correr Benchmark**.
   - El simulador enlaza los 38 archivos automáticamente y ejecuta la suite elegida.

### Cómo leer los resultados del benchmark
- **Tarjetas KPI superiores**:
  - **Instrucciones (Total)**: muestra la suma total desglosada en **Usuario** y **SO**, junto con los **Ciclos** de reloj.
  - **Tamaño del programa**: bytes totales ocupados por los 38 módulos enlazados.
  - **Datos accedidos** y **Pico de pila (`R6`)**.
- **Histograma de instrucciones** y **Salida de consola**: muestran qué instrucciones se ejecutaron más veces (marcando con `*` las extensiones propias de Apex-3X) y todo el texto impreso por el programa.
- **Desglose por operación (23 operaciones)**:
  - Cada fila muestra tamaño del módulo, instrucciones (Usuario / SO / Total), datos, pila, valor **Esperado**, valor **Obtenido** y estado:
    - **`PASS`**: la subrutina retornó sin errores y dentro de la tolerancia esperada.
    - **`FAIL`**: retornó, pero el resultado está fuera de la tolerancia.
    - **`ERR`**: ocurrió un error en tiempo de ejecución o superó el límite de pasos.
  - Podés filtrar por texto o por estado (`Solo PASS` / `Solo FAIL / ERR`), o pulsar **Probar** en una fila para cargarla directo en la prueba unitaria.
- **Perfil por módulo**: ordena los módulos de mayor a menor cantidad de instrucciones ejecutadas y cantidad de llamadas.
- **Exportar JSON**: descarga `benchmark_apex3x_metricas.json` con todas las métricas y resultados.

---

## 4. Cómo probar una subrutina puntual (Prueba unitaria)

Dentro del mismo panel **Modo Prueba y Benchmark**:
1. En **1. Subrutina destino**, elegí la etiqueta de entrada en el menú (o escribila manualmente / ingresá una dirección como `x3000`).
2. En **2. Registros iniciales**, cargá los valores de entrada en `R0..R6` (decimal `#10` o hex `x000A`). Si la subrutina lee memoria, podés precargar direcciones (ejemplo: `x4000=x000A, x4002=#25`).
3. En **3. Ejecución unitaria**, opcionalmente indicá qué registro y valor esperás comprobar (ej. `R0` = `3547`) y hacé clic en **Probar Subrutina**.

---

## 5. Atajos de teclado

| Atajo | Acción |
| :--- | :--- |
| `Ctrl + Enter` | Ensamblar el código del editor |
| `F9` | Ejecutar o pausar |
| `F10` | Ejecutar una instrucción (Paso) |
| `F8` | Reiniciar CPU |
| `F1` | Abrir o cerrar la guía rápida en pantalla |
