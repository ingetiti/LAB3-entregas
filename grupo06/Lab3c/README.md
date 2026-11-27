# ISA3C integrada

Esta es la copia preparada para entregar del Grupo 6. Empezar por `LEER_PRIMERO.txt`. Los informes originales, los Word editables y los respaldos se conservan en la carpeta de trabajo.

Versión 1.1, con EXP optimizada el 26/11/2026. Combina nuestra ISA y su calculadora con operaciones aritméticas inspiradas en el RAR compartido. Conserva memoria de 65.536 bytes, instrucciones de 16 bits, opcode fijo de cinco bits, alineación automática, `.EXTERNAL`, ensamblador independiente, núcleo independiente y editor/depurador. La optimización de EXP no modifica la ISA.

También incluye una **interfaz gráfica para Windows con temas claro y oscuro**, agregada el 26/11/2026. Abrir **interfaz.bat**: permite editar ASM, abrir objetos, ensamblar, ejecutar, pausar, avanzar paso a paso, poner breakpoints y ver registros, memoria y consola. El botón de arriba a la derecha alterna el tema durante la sesión y conserva el estado de ejecución. No requiere instalar Python, un navegador ni bibliotecas adicionales.

El panel muestra **instrucciones del programa, del sistema y totales**. La casilla **Incluir instrucciones del sistema** decide qué muestra el contador principal; los tres valores se conservan. Para la suma 15+27: programa=5, sistema=103, total=108. El selector cambia la medición visible y conserva la ejecución. Ver `LEEME_INTERFAZ.txt` y `docs/INTERFAZ_GRAFICA.md`.

**Teclado de la calculadora:** al ejecutar, hacé clic en la consola y pulsá `5`; EXP se selecciona directamente, sin Enter ni Pausar. Después escribí el exponente y Enter. Se corrigió el refresco cuando el programa procesa una entrada y vuelve a esperar la siguiente: los pedidos, resultados y contadores ahora aparecen automáticamente.

## Ejecutar en Windows

Los ejecutables Windows x64 ya están compilados. Extraer el ZIP completo y abrir:

- **interfaz.bat:** interfaz gráfica con editor, consola, depurador y selector del conteo de instrucciones.
- **ejecutar.bat:** calculadora interactiva. Para EXP(3): elegir `5`, ingresar `3`, Enter; debe mostrar `20.0859375`. Una tecla vuelve al menú y `d` sale.
- **editor.bat:** menú de edición, registros, memoria, paso a paso y breakpoints.
- **benchmark.bat:** ejemplo automático del Grupo 27 y métricas por función.
- **probar.bat:** suite de pruebas completa.

Para ensamblar y ejecutar otro programa desde CMD, situado en esta carpeta:

```bat
build\ensamblador.exe ejemplos\alu_integrada.asm -o build\alu_integrada.obj
build\simulador.exe build\alu_integrada.obj
```

El ejemplo muestra `ALU integrada: OK` y conserva diez resultados en la etiqueta RESULTADOS. `ejemplos/prueba_suma.asm` sigue disponible para el ejemplo 5+7.

## Qué se incorporó

| Operación | Sintaxis | Resultado |
|---|---|---|
| Resta | SUB Rd,Rs,Rt | Los 16 bits de Rs−Rt |
| Producto bajo | MUL Rd,Rs,Rt | Los 16 bits bajos del producto |
| Producto alto sin signo | MULU Rd,Rs,Rt | Los 16 bits altos del producto de dos enteros sin signo |
| División sin signo | DIVU Rd,Rs,Rt | Cociente entero; si Rt=0 devuelve cero |
| Ceros iniciales | CLZ Rd,Rs | 0..16; CLZ(0)=16 |
| Copia | MOV Rd,Rs | Copia los 16 bits |
| Desplazamientos | SHL/SHR/SAR Rd,Rs,Rc | Izquierda, derecha lógica y derecha aritmética |
| Alias | ASR Rd,Rs,Rc | La misma codificación que SAR |

Las operaciones nuevas aritméticas se ofrecen con registros. No se copió la variante inmediata de cuatro bits del RAR: ADD/AND conservan nuestros inmediatos −16..15 y los offsets mantienen sus alcances. Para constantes de las operaciones nuevas, cargarlas en un registro. MOV no acepta `MOV R0,#15`.

Todas las operaciones anteriores actualizan NZP. MUL y MULU permiten conservar el producto completo en dos registros cuando se necesita mayor precisión. No existe una instrucción EXP o SQRT: continúan siendo algoritmos Assembly.

## Rendimiento medido

| Medición | Estable original | Experimental anterior | Integrada |
|---|---:|---:|---:|
| Menú automático de tres operaciones | 20.532 | 15.960 | **12.706 instrucciones** |
| Raíz Newton(2), sin interfaz | 4.283 | 4.283 | **1.029 instrucciones** |
| Raíz Newton(4), sin interfaz | 3.786 | 3.786 | **588 instrucciones** |
| Imagen de la calculadora | 14.720 | 14.642 | **14.558 bytes** |

## EXP optimizada para esta ISA

`benchmark/modulos/g6_EXP.asm` utiliza SUB para las diferencias de tabla, MUL/MULU para obtener el producto completo por un dígito y SHL/SHR para ajustar y redondear varias palabras sin recorrer cada bit. Mantiene la entrada Q3.12, la salida Q7.8, R1-R7 y las seis vueltas generales. No se agregó una instrucción EXP al núcleo.

EXP(1) pasa de 4.907 a 1.527 instrucciones; EXP(3), de 5.016 a 1.755. El barrido de las 65.536 entradas pasa de 222.466.798 a 68.450.717 instrucciones, un 69,23 % menos. Las 20.111 entradas de rutas rápidas mantienen su conteo; las otras 45.425 mejoran. Ninguna empeora ni cambia su salida. La rutina ocupa dos bytes adicionales; los conteos excluyen impresión y HALT del llamador.

Prueba independiente de la calculadora, desde esta carpeta:

```bat
build\ensamblador.exe ejemplos\exp_isa3c.asm -I benchmark\modulos -o build\exp_isa3c.obj
build\simulador.exe build\exp_isa3c.obj
```

Muestra `EXP en Q7.8 (hex): x1416`. El dato calculado también queda en R0 y en la etiqueta RES_EXP. Cambiar la constante ENTRADA del ejemplo y reensamblar para probar otro exponente. Para usar la rutina desde otro programa, importar `g6_EXP-EXP_Q3_12` y llamar con R0 cargado. Esta versión es para ISA3C; no se publica como reemplazo LC-3 en el simulador del Grupo 8. Ver `docs/EXP_OPTIMIZADA.md` y `docs/exp_optimizacion.json`.

## Métricas

METRICAS conserva instrucciones, interrupciones, tamaño de programa y direcciones únicas accedidas/escritas. TRAFICO agrega bytes leídos y escritos acumulados, incluyendo búsqueda de instrucciones, servicios, pila y E/S. Acceder repetidamente a una dirección aumenta el tráfico, pero no el número de direcciones únicas. Estas cantidades no son RAM del proceso Windows ni ciclos de hardware.

## Compilar y regenerar

Con GCC y windres en PATH (ambos incluidos en MinGW-w64 de MSYS2), ejecutar `compilar.bat`. Genera el ensamblador, preensambla el sistema de servicios, compila el núcleo, las herramientas y la interfaz gráfica, ensambla el benchmark y ejecuta las pruebas. Para reconstruir solamente la ventana y sus pruebas: `compilar_interfaz.bat`. Las advertencias se tratan como errores. Se incluye CMake como alternativa; la validación de esta entrega se realizó con GCC y los scripts Windows.

Para regenerar desde los originales, con Python 3: `python tools/regenerar_modulos.py`. Ese script aplica ahora automáticamente las seis adaptaciones optimizadas, verificando hashes. `tools/optimizaciones_modulos.json` conserva esas traducciones. Después se debe ejecutar compilar.bat. No se necesita Python para usar los binarios.

## Compatibilidad y alcance

Se mantienen la codificación de las instrucciones válidas de nuestra base y los formatos de datos. Se comprobó el banco estable de 37 casos usando sus objetos anteriores sobre el nuevo núcleo. El opcode antes reservado y algunos subcampos antes no utilizados ahora tienen significado; no se garantiza el comportamiento de codificaciones antiguas inválidas o no canónicas.

Los nombres SUB y ASR pasan a ser palabras reservadas. Se renombraron etiquetas auxiliares que coincidían con esos nombres. Otros fuentes antiguos que usaran esas etiquetas pueden necesitar renombrarlas antes de reensamblar.

Este ensamblador no es el del RAR: sus objetos y fuentes no son intercambiables directamente. Se conservan nuestro TRAP con pila supervisora/RTI, LDBL que preserva la mitad alta y LDBS para extensión de signo. `.STRINGZ` conserva caracteres por palabra para la interfaz. Los módulos para esta ISA local no reemplazan a los módulos LC-3 publicados en el simulador del Grupo 8.

La interfaz de origen conserva avisos para tres opciones sin subrutina conectada: seno Taylor y salida en bases hexadecimal/binaria. Las veinte operaciones disponibles sí están enlazadas. Los módulos matemáticos estáticos mantienen sus límites de reentrancia y precisión.

Ver `docs/ISA.md`, `docs/CAMBIOS.md`, `docs/VALIDACION.md` y los CSV de resultados. Las carpetas anteriores y el RAR original se conservaron.

## Documentación y mediciones finales

La documentación de la ISA y sus instrucciones está en `docs/ISA.md`; el uso de la ventana se explica en `docs/INTERFAZ_GRAFICA.md`. `docs/BITACORA.md` conserva el registro del trabajo en texto.

La suite completa volvió a terminar sin fallos, incluidas las 121 comprobaciones de sesión. Para repetir el resumen de instrucciones, memoria y precisión después de `probar.bat`, ejecutar `python tools/medir_entrega.py`. Requiere Python 3 solo para esa medición. Los resultados están en `docs/mediciones_finales/`: resumen JSON, CSV comparado y salida completa de pruebas.

El máximo error absoluto medido de EXP sin saturación es 0,0019580065052480222, frente a `math.exp` double sobre el exponente Q3.12 ya cuantizado. Se analizaron 52.642 entradas sin saturación y se excluyeron las 12.894 saturadas. La comparación propia no determina el resultado de la evaluación oficial.

El pegado de código por Ctrl+V conserva ahora los saltos de línea, las líneas vacías y las tabulaciones, también desde texto con LF. Ctrl+Z deshace la inserción completa. La corrección pasó 44 pruebas del editor de Windows y una ejecución desde código pegado en la ventana. Ver `docs/INTERFAZ_GRAFICA.md`.
