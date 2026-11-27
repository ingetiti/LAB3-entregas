# Interfaz gráfica de ISA3C

La ventana nativa de Windows utiliza el núcleo y el ensamblador C del proyecto. El diseño es claro, con controles grandes, editor a la izquierda, registros y memoria a la derecha y consola debajo del editor. La calculadora es uno de los ejemplos; también se pueden ejecutar programas propios compatibles con ISA3C.

## Abrir y ejecutar

Extraer el proyecto completo y abrir `interfaz.bat`, o `build/isa3c_gui.exe`. Los ejecutables Windows x64 ya están compilados. La interfaz usa controles de Windows y no necesita Python ni un servidor. El manifiesto activa controles comunes, escala de pantalla y rutas UTF-8 en Windows 10 1903 o posterior y Windows 11.

La primera ventana muestra `ejemplos/suma_grafica.asm`, ya ensamblado. F5 lo ejecuta. R0 y la variable RESULTADO contienen 42 (`x002A`). En el campo de memoria se puede escribir RESULTADO y pulsar Enter: en esta versión del ejemplo está en `x300E`.

## Tema claro y oscuro

El botón **Modo oscuro** de la parte superior derecha cambia los paneles, editor, consola, memoria, registros y controles. En ese tema se llama **Modo claro** para volver. También se puede usar Ayuda > Cambiar tema claro / oscuro. El cambio es inmediato y conserva el programa, sus resultados, los breakpoints y los contadores, incluso si hay una ejecución activa. Se inicia en claro cada vez que se abre la aplicación; la selección dura esa sesión.

La apariencia de los menús, barras de desplazamiento y cuadros Abrir/Guardar pertenece a los controles nativos de Windows. La barra de título usa `DWMWA_USE_IMMERSIVE_DARK_MODE` cuando Windows lo admite. Esto no cambia el tema global del sistema.

Archivo permite abrir `.asm` y `.obj`, guardar el fuente, guardar una copia y exportar el objeto ensamblado. Un objeto se ejecuta y depura, pero no conserva el fuente ni sus etiquetas. Para modificarlo hay que abrir su `.asm`. El editor conserva los cambios en memoria hasta Guardar; pregunta antes de reemplazar o cerrar un fuente modificado.

| Acción | Atajo | Efecto |
|---|---|---|
| Abrir | Ctrl+O | Abre un fuente u objeto. |
| Guardar | Ctrl+S | Guarda el fuente como UTF-8. |
| Guardar como | Ctrl+Shift+S | Guarda el fuente en otra ruta. |
| Ensamblar | F7 | Ensambla el texto actual y reinicia la máquina y los contadores. |
| Ejecutar | F5 | Ensambla si falta y continúa; después de HALT reinicia y ejecuta de nuevo. |
| Pausar | F6 o Esc | Detiene temporalmente la ejecución y conserva el estado. |
| Paso | F10 | Ejecuta un paso del núcleo, incluso dentro de servicios del sistema. |
| Reiniciar | F2 | Restaura la imagen inicial y pone a cero los contadores. |
| Breakpoint | F9 o doble clic | Alterna un punto en la fila seleccionada de memoria. |
| Ayuda | F1 | Muestra ayuda dentro de la aplicación. |

## Contar con o sin instrucciones del sistema

Se almacenan siempre tres cantidades acumuladas desde el último ensamblado o reinicio:

- **Programa:** instrucciones del programa cargado, sus subrutinas y código ejecutado en la memoria normal de usuario.
- **Sistema:** instrucciones ejecutadas en la región reservada, fuera de la imagen cargada y de la memoria normal de usuario. En los programas habituales son los servicios del sistema, incluidos impresión, teclado y detención.
- **Total:** suma de ambas cantidades. Es el contador original `Lc3.instructions` del procesador.

La casilla **Incluir instrucciones del sistema** decide qué se muestra en el contador grande. Marcada muestra Total; desmarcada muestra Programa. Cambiarla conserva memoria, registros y conteos; no filtra ni evita ejecutar instrucciones. Se puede alternar antes, durante o después de una ejecución.

Las instrucciones del sistema también pertenecen a la ISA. La distinción es entre el programa y sus servicios, no entre instrucciones válidas e inválidas de la arquitectura.

| Ejemplo terminado | Programa | Sistema | Total |
|---|---:|---:|---:|
| Suma 15+27 (`suma_grafica.asm`) | 5 | 103 | 108 |
| Demo de EXP(3) (`exp_isa3c.asm`) | 1.799 | 405 | 2.204 |

HALT o PUTS escritos en el fuente cuentan como instrucciones del programa. Las instrucciones ejecutadas dentro de sus servicios se suman al sistema. EXP, la interfaz Assembly del Grupo 27 y las bibliotecas matemáticas externas se consideran programa: están enlazadas con el ejecutable del usuario. Comentarios, etiquetas, `.FILL`, `.STRINGZ` y líneas vacías no suman por existir en el archivo; los datos contarían como instrucciones solo si el flujo los ejecutara.

El contador avanza por cada instrucción realmente buscada y decodificada por `lc3_step`, no por cada iteración del temporizador de la ventana ni por cada fila dibujada. Entrar a una interrupción sin buscar un opcode incrementa el contador de interrupciones del núcleo, pero no inventa una instrucción. Una instrucción inválida que fue buscada sí forma parte del total antes de provocar su excepción.

### Criterio de clasificación

`gui_session.c` toma el PC **antes** del paso y la variación del contador original **después**. La imagen cargada tiene prioridad: sus bytes se consideran programa incluso si alguien carga deliberadamente un programa supervisor por debajo de `x3000`. Fuera de esa imagen, `x3000..xFDFF` se considera memoria de programa, lo que permite contar código generado dinámicamente. Las demás direcciones se consideran sistema.

Este criterio corresponde al mapa de memoria de este núcleo. No depende del nombre de una etiqueta ni únicamente del modo Usuario/Supervisor. El código de un sistema operativo personalizado colocado en otra región necesitaría ajustar esa política si se quisiera clasificarlo de otra manera.

### Acumulación y límites

Pausar, continuar y dar pasos conservan el acumulado. Reiniciar o ensamblar de nuevo pone Programa, Sistema y Total en cero. Ejecutar después de HALT empieza una nueva ejecución desde la imagen inicial. Limpiar la consola solo limpia el texto.

El campo **Límite total por ejecución** siempre usa el total, aunque la casilla esté desmarcada. De esta manera un bucle dentro del sistema también se puede detener. Al alcanzar el límite, la máquina queda pausada; F5 concede otro tramo y continúa sin borrar los contadores. El límite no es una estimación de tiempo real ni de ciclos de hardware.

## Medir la función EXP aislada

El valor 1.799 de la tabla incluye el programa llamador y la conversión a hexadecimal. La función EXP(3) aislada sigue ejecutando 1.755 instrucciones. Para comprobarlo con el ejemplo entregado, sin modificar el fuente:

1. Elegí Ejemplos > EXP optimizada y ensamblá con F7.
2. Buscá `x3004` en memoria y colocá un breakpoint con F9. Allí está `JSRR R3`.
3. Buscá `x3006` y colocá otro. Allí está `ST R0,RES_EXP`, que se ejecuta al regresar.
4. Ejecutá F5. Se detiene antes de JSRR: Programa=2.
5. Ejecutá F5 otra vez. Se detiene al regresar, antes de ST: Programa=1.758; R0=`x1416`.
6. La diferencia es `1758 - 2 = 1756`. Una de ellas es la llamada JSRR; al descontarla quedan **1.755** dentro de EXP.

Las direcciones valen para el archivo entregado; cambian si se agregan instrucciones antes de la llamada. Para comparar otra función, ubicá su llamada y el retorno correspondiente. Ambas mediciones deben usar la misma entrada, precisión y alcance.

## Teclado y consola

Al ejecutar, el foco pasa a la consola. Hacé clic allí y escribí: cada tecla ASCII se envía al teclado simulado. Enter se convierte en LF para GETLINE. Ctrl+C conserva su función normal de copiar una selección de la consola.

El campo inferior permite preparar texto. **Enviar línea**, o Enter dentro del campo, agrega LF al final. **Solo texto** manda el contenido exacto, sin agregar Enter; sirve para opciones del menú que esperan una sola tecla. Se admite hasta 256 bytes pendientes. Si no hay lugar para todo el envío, se rechaza completo y se informa el problema.

Cuando una consulta a KBSR no encuentra entrada, la ejecución gráfica espera hasta recibir una tecla. La ventana continúa respondiendo y no acumula vueltas de espera mientras la persona decide qué escribir. Los pasos que sí se ejecutaron se cuentan. Por esa diferencia de programación de la entrada, una comparación de rendimiento con consola interactiva debe controlar también cuándo se entrega el teclado. Para medir algoritmos conviene aislar la llamada con breakpoints o usar el banco reproducible del proyecto.

La calculadora se prueba desde Ejemplos > Calculadora del laboratorio. Ejecutá, hacé clic en la consola y pulsá `5`; cuando pida el exponente escribí `3` y Enter. Muestra `20.0859375`. Una tecla vuelve al menú y `d` termina. Las opciones que ya tenían un aviso por falta de módulo conservan ese comportamiento.

La opción del menú se elige con una tecla, sin Enter. El dato decimal se confirma con Enter. No hace falta pausar entre esos pasos. Si se utiliza el campo inferior para elegir una opción, Solo texto envía la tecla sin agregar el Enter de una línea.

Se corrigió una actualización omitida cuando el estado era Espera teclado tanto antes como después de procesar un dato. El procesador ya había avanzado y producido el siguiente pedido o resultado, pero la ventana conservaba el contenido anterior hasta una pausa. Ahora `gui_session_tick` informa el progreso aunque el estado final vuelva a ser Espera teclado; la ventana actualiza inmediatamente consola, registros y contadores al salir de cada espera. Si no hay entrada ni progreso, mantiene la espera sin repintar ni sumar instrucciones.

## Memoria, registros y breakpoints

R0..R7 se muestran en hexadecimal y decimal con signo. Debajo aparecen PC, IR, condición NZP, PSR y modo. Una palabra de 16 bits puede tener distintas interpretaciones según el programa: `xFFFF` equivale a −1 con signo y a 65535 sin signo.

La vista de memoria muestra hasta 128 palabras desde la dirección indicada. Se puede escribir `x3000`, `#12288` o una etiqueta exacta del programa ensamblado. Una dirección impar se alinea al byte par anterior porque la tabla muestra palabras. El botón PC lleva a la próxima instrucción. La dirección del PC se pinta en azul y los breakpoints en rojo.

La tabla desensambla también datos: una variable puede aparecer como NOP u otra operación sin que haya sido ejecutada. Mirá Hex, Decimal y Etiqueta para identificar un resultado. La barra inferior interpreta la palabra seleccionada también como Q3.12 y Q7.8; es una ayuda de escala, no una declaración de tipo guardada en memoria.

Un breakpoint detiene **antes** de ejecutar la instrucción. F5 desde ese punto permite ejecutar esa instrucción y seguir; si el flujo vuelve a ella, vuelve a detenerse. F10 siempre permite un paso. Reiniciar conserva los puntos; reensamblar los borra, porque las direcciones pueden haber cambiado.

La consulta visual usa `lc3_peek`, por lo que no consume KBDR ni aumenta las métricas de memoria del programa. La interfaz no escribe registros ni memoria manualmente; los cambia la ejecución o el reinicio.

## Módulos externos

La interfaz llama `lc3_assemble_project` con el texto del editor y la ruta del fuente. Conserva la búsqueda junto al archivo principal y agrega `benchmark/modulos` del proyecto. Por eso el ejemplo EXP y la calculadora se ensamblan directamente desde el menú gráfico.

Herramientas > Elegir carpeta adicional de subrutinas agrega otra carpeta de búsqueda durante la sesión. Después hay que volver a ensamblar. Guardar un fuente nuevo en su carpeta antes de ensamblar facilita encontrar bibliotecas colocadas junto a él. Una vez exportado un `.obj`, ya incluye el código enlazado y no necesita leer esos módulos para ejecutarse.

## Código y compilación

| Archivo | Responsabilidad |
|---|---|
| `src/gui_win32.c` | Ventana, editor, menús, archivos, consola, registros, memoria y temporizador. |
| `src/gui_session.c` | Sesión de ejecución, breakpoints, contadores, entrada, salida y reinicio. |
| `include/gui_session.h` | Interfaz de la sesión, independiente de los controles Win32. |
| `tests/test_gui_session.c` | Casos funcionales de ejecución, conteo, teclado, objetos, fallos y EXP. |
| `resources/isa3c.manifest` | Controles de Windows, escala de pantalla, UTF-8 y permisos de usuario normal. |
| `compilar_interfaz.bat` | Compila ventana, recursos y prueba de sesión con GCC/windres. |
| `interfaz.bat` | Abre el ejecutable gráfico. |

`compilar.bat` incluye la interfaz y `probar.bat` incorpora sus pruebas. La compilación utiliza las advertencias estrictas del resto del proyecto. CMake también declara los nuevos destinos; la ventana se compila solo en Windows. La validación de esta entrega se realiza con GCC y los scripts Windows.

El temporizador ejecuta tramos acotados de instrucciones y devuelve el control a Windows para atender pausas, teclado y repintado. La salida se conserva hasta 1 MiB; si un programa imprime indefinidamente, se descarta la mitad más antigua al llenar ese buffer. Esta política de visualización no afecta los contadores ni la ejecución de la CPU.

El núcleo `lc3.c`, las codificaciones de `isa.h`, las subrutinas y los objetos previos conservan su comportamiento. Los contadores adicionales pertenecen a la sesión gráfica. La consola anterior sigue disponible con `editor.bat`, y el ejecutor independiente con `build/simulador.exe`.

Referencias de las API utilizadas: [manifiestos y UTF-8 de Windows](https://learn.microsoft.com/en-us/windows/apps/design/globalizing/use-utf8-code-page), [manifiestos de aplicaciones Win32](https://learn.microsoft.com/en-us/windows/desktop/sbscs/application-manifests) y [temas claro y oscuro en Win32](https://learn.microsoft.com/windows/apps/desktop/modernize/apply-windows-themes).

## Pegar código desde el portapapeles

Con el foco en el editor, Ctrl+V pega el código conservando sus renglones. Se normalizan LF, CRLF y CR al formato CRLF del control de Windows. Se conservan líneas vacías, tabulaciones, acentos y el salto final. Ctrl+Z deshace el pegado completo y recupera el texto reemplazado por la selección.

La misma conversión se usa al abrir archivos. Guardar y ensamblar siguen trabajando con UTF-8 y saltos LF. El editor de objetos y el código durante una ejecución conservan su protección de solo lectura. Si el texto excede el límite del editor, se rechaza el pegado completo sin cortar el programa.

La regresión `tests/test_gui_editor.c` utiliza un control EDIT real de Windows, sin cambiar el portapapeles del usuario. Pasó 44 comprobaciones, incluidas selección, Deshacer, formatos de línea, solo lectura, límite de tamaño y 5.001 renglones. También se comprobó el pegado real de un programa con comentarios y líneas vacías: ensambló y dejó R0=7 y RESULTADO=7, con 107 instrucciones totales.
