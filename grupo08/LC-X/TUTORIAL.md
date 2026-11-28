# Benchmark de la calculadora en LC-X: cómo ejecutarlo

Esta carpeta contiene el benchmark de la clase portado a LC-X, ya ensamblado, y los reportes que lo comparan con la LC-3. Se ejecuta en el simulador web del repositorio, sin instalar nada.

## Contenido

| Archivo | Qué es |
| --- | --- |
| `benchmark-lcx.zip` | Proyecto LC-X en assembly: `main.asm` y la carpeta `lib/` con los 37 módulos. Al abrirlo, el simulador cambia solo a LC-X. |
| `benchmark-lcx-verboso.obj` | Programa LC-X ya ensamblado, corrida verbosa: muestra cada operación, sus operandos y su resultado. |
| `benchmark-lcx-silencioso.obj` | Programa LC-X ya ensamblado, corrida silenciosa: solo calcula. |
| `benchmark-lc3.zip` | El benchmark original de la clase en LC-3, para comparar. |
| `reportes/full-verbose.txt` | Corrida verbosa: totales de LC-3 y LC-X, detalle por archivo y comparación de la salida. |
| `reportes/full-silent.txt` | Lo mismo para la corrida silenciosa. |
| `reportes/routines.txt` | Cada una de las 1.761 llamadas de prueba a las rutinas, en LC-3 y en LC-X. |

## Antes de empezar

1. Abrir el simulador: <https://lc3.lgrum.xyz>.
2. Para ver la interfaz en castellano, elegir **Español** en la barra de estado, abajo a la derecha.

El selector del conjunto de instrucciones está en la barra de estado, abajo a la izquierda: muestra **LC-3** o **LC-X**.

## Opción A: abrir el proyecto en assembly (`.zip`)

1. En el panel **Archivos**, hacer clic en el botón **Abrir un proyecto desde .zip** y elegir `benchmark-lcx.zip`.
2. Confirmar con **Reemplazar**. El selector de la barra de estado pasa a **LC-X**.
3. Hacer clic en **Ensamblar**. La barra de estado muestra **2427 palabras · x3000–x42F5**: es la memoria que ocupa el programa.
4. Hacer clic en **Continuar**. La consola muestra cada operación de la calculadora.
5. Entre una operación y la siguiente, el programa espera una tecla. Hacer clic en la **Consola** y presionar **Enter** cada vez que se detenga, hasta que aparezca **HALT**.
6. Leer en la barra de estado las instrucciones ejecutadas: **6482 instrucciones (6475 usuario + 7 SO)**.

Para la corrida silenciosa desde el `.zip`: en `main.asm`, buscar la etiqueta `programa_del_menu_completo` y cambiar el `.FILL #1` que la sigue por `.FILL #0`. Después, **Ensamblar** y **Continuar**.

## Opción B: cargar el programa ensamblado (`.obj`)

Un `.obj` no indica su conjunto de instrucciones, así que primero hay que elegirlo.

1. En la barra de estado, elegir **LC-X** en el selector del conjunto de instrucciones.
2. Abrir el menú **Archivo** › **Cargar programa (.obj)…** y elegir `benchmark-lcx-verboso.obj` o `benchmark-lcx-silencioso.obj`. Un aviso arriba del editor confirma que se está ejecutando el archivo objeto.
3. Hacer clic en **Continuar** y, como en la opción A, presionar **Enter** en la **Consola** cada vez que el programa espere una tecla, hasta **HALT**. La corrida silenciosa se detiene una sola vez, después de mostrar el cambio de base.

Para volver al proyecto en assembly, hacer clic en **Volver al código** en el aviso, o en **Ensamblar**.

## Resultados esperados

| Corrida | Instrucciones de usuario | Instrucciones del SO | Total que muestra el simulador | Memoria |
| --- | --- | --- | --- | --- |
| Verbosa | 6.475 | 7 | 6.482 | 2.427 palabras |
| Silenciosa | 2.244 | 7 | 2.251 | 2.427 palabras |

Los reportes cuentan 6 instrucciones del SO en lugar de 7, y por eso dan 6.481 y 2.250 en total: dejan de contar en la instrucción que detiene el reloj, y el simulador también la cuenta. Las de usuario coinciden.

Como comparación, la LC-3 ejecuta 379.578 instrucciones en la corrida verbosa y 254.079 en la silenciosa, y ocupa 7.896 palabras. Para verlo en el simulador, abrir `benchmark-lc3.zip`: el selector pasa a **LC-3**. Es mucho más lento, y en la corrida verbosa también espera una tecla entre operaciones.

## Formato del `.obj`

Es el formato de archivo objeto de la LC-3: los dos primeros bytes son la dirección de origen (x3000) y después vienen las palabras del programa, cada una con el byte alto primero. En memoria, LC-X guarda el byte bajo primero; el simulador las ubica así al cargar el archivo. Por eso, en un editor hexadecimal, los textos del `.obj` se ven con los caracteres invertidos de a pares (`==ERUDCCOI` en lugar de `==REDUCCION`), y en la consola se ven bien.
