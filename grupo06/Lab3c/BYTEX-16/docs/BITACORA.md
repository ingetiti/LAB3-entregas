# Bitácora del Laboratorio 3

Registro retrospectivo actualizado el 26 de noviembre de 2026. Las horas no quedaron registradas.

## Octubre y primera semana de noviembre de 2026

Hora no registrada.

**Objetivo.** Comprender punto fijo, desarrollar la función EXP asignada y preparar la primera entrega.

**Actividades realizadas.** El informe anterior agrupa el 7 y 14 de octubre como inicio de Lab3a y trabajo con formatos Q, conversiones y operaciones en C y Assembly. El 21 y 28 registra el desarrollo de EXP por el método multiplicativo de alta radix. El 4 de noviembre registra consultas y cierre; el 5, la preparación de los archivos de GitHub y la publicación de EXP en el simulador del Grupo 8.

**Observaciones y hallazgos.** La entrada elegida para EXP fue Q3.12 y la salida Q7.8 de 16 bits con signo. La escala explica el dato esperado x1416 para EXP(3). El método final usa una tabla y seis pasos generales; no utiliza la serie de Taylor.

**Dificultades y soluciones.** La integración posterior recibió una corrección por la convención de subrutina del Grupo 27. Se reemplazó la prueba autónoma por un módulo que recibe y devuelve R0, preserva los demás registros, evita usar R6 como temporal y retorna con RET. La fecha exacta de esa corrección no se reconstruye aquí. La antigua referencia de resultado fijo en x3007 pertenece al programa autónomo, no a la subrutina actual.

**Próxima sesión.** Usar el módulo corregido como biblioteca y conservar un llamador separado para probarlo. El informe A/B anterior queda como evidencia histórica; el contrato actual está explicado en el informe BYTEX-16.

## 19 de noviembre de 2026

Hora no registrada.

**Objetivo.** Adaptar el simulador existente a la consigna de Lab3c.

**Actividades realizadas.** Se revisó el prototipo C, que pasaba 209 comprobaciones pero todavía utilizaba opcode de cuatro bits, memoria por palabras y carecía de EXTERNAL. En una copia se implementaron instrucciones de 16 bits con opcode fijo de cinco bits, memoria de 65.536 bytes, PC+2, pilas y vectores por bytes, operaciones de byte y métricas. Se separaron ensamblador, lector de objetos y núcleo.

**Observaciones y hallazgos.** Se eligieron ocho registros, orden big-endian y alineación par de palabras. Los offsets de palabra se expresan en palabras; los de byte, en bytes. El enlazador renombra símbolos locales y conserva archivo y línea en los diagnósticos. El editor y depurador de consola se mantuvieron como herramienta opcional.

**Dificultades y soluciones.** La integración reveló que CORDIC_DIV dependía de un R4 inicial incorrecto. Se corrigió en la adaptación. Se añadió un adaptador de seno/coseno y se mantuvieron visibles tres opciones que el menú original no tenía conectadas. La suite creció de 709 a 764 comprobaciones para cubrir opcodes, offsets negativos, retorno a cero, aislamiento de módulos y dependencias repetidas o circulares.

**Próxima sesión.** Conservar la versión estable y estudiar mejoras que reduzcan el trabajo de las rutinas sin cambiar su precisión ni trasladar funciones elementales al hardware.

## 24 de noviembre de 2026

Hora no registrada.

**Objetivo.** Comparar las mejoras experimentales con las operaciones incluidas en el RAR compartido.

**Actividades realizadas.** Se conservaron el RAR y las versiones anteriores. Se compararon formatos, semánticas y estrategias aritméticas. La versión experimental incorporó desplazamientos y rutas rápidas de EXP; también se adaptaron primitivas de Booth, CORDIC y conversión de formatos. La comparación identificó SUB, MUL, MULU, DIVU, CLZ y MOV como operaciones útiles para una ISA general.

**Observaciones y hallazgos.** La secuencia automática del menú pasó de 20.532 instrucciones en la estable a 15.960 en la experimental. El cambio conservó los resultados de esa secuencia. El RAR utiliza diferencias de offsets, TRAP y carga de byte que impiden intercambiar sus objetos con los de nuestra ISA.

**Dificultades y soluciones.** Mezclar directamente ambos decodificadores habría roto los programas ya adaptados. Se decidió portar las ideas aritméticas y mantener el contrato de la ISA propia. Se conservaron todos los nuevos mnemónicos elegidos: algunos reducen bucles y otros, como MOV, expresan una copia sin garantizar ahorro frente a ADD con cero.

**Próxima sesión.** Integrar las operaciones útiles manteniendo el opcode fijo de cinco bits y comprobar de nuevo ensamblador, desensamblador y programas.

## 25 de noviembre de 2026

Hora no registrada.

**Objetivo.** Consolidar la ISA integrada y comprobar compatibilidad funcional y resultados.

**Actividades realizadas.** Se añadieron SUB, MUL, MULU, DIVU, CLZ y MOV como suboperaciones en campos antes libres. Se conservaron SHL, SHR y SAR y se aceptó ASR como alias. Se actualizaron ensamblador, desensamblador y documentación. MUL y MULU reemplazaron el producto emulado de la raíz recíproca de Newton y se conservaron sus seis vueltas.

**Observaciones y hallazgos.** El menú automático pasó a 12.706 instrucciones, con los mismos resultados. La raíz de 2 pasó de 4.283 a 1.029 instrucciones; la de 4, de 3.786 a 588. La equivalencia de raíz se verificó en 5.181 llamadas; se comprobaron 4.542.415 casos de ALU y 3.145.728 combinaciones de desplazamientos.

**Dificultades y soluciones.** Las nuevas palabras reservadas ASR y SUB chocaban con etiquetas internas: se renombraron. MULU devuelve la mitad alta unsigned, por lo que fue necesario conservar ambas mitades y ajustar el punto fijo. La precisión anterior de raíz se mantuvo: para 2 sigue dando 1,421875, y no se presenta esa aproximación como una mejora numérica.

**Próxima sesión.** Optimizar EXP, ampliar el informe de arquitectura y medir cada cambio con el mismo contrato de entrada y salida.

## 26 de noviembre de 2026 con optimización de EXP

Hora no registrada.

**Objetivo.** Reducir las instrucciones de EXP manteniendo el algoritmo y sus resultados.

**Actividades realizadas.** Se sustituyeron diferencias de tabla por SUB, productos repetidos por MUL y MULU y ajustes bit a bit por SHL y SHR. Se mantuvieron los tres limbos de base 2 elevado a 15, el tratamiento del acarreo, las tablas, el redondeo y la convención de registros. Se registró la optimización en el regenerador de módulos y se añadió un ejemplo independiente.

**Observaciones y hallazgos.** Las 65.536 entradas conservaron salida, estado y NUM_ITER. R1 a R7 se preservaron y R6 quedó intacto. El total bajó de 222.466.798 a 68.450.717 instrucciones, un 69,23 %. EXP(3) bajó de 5.016 a 1.755. Mejoraron 45.425 entradas y 20.111 conservaron su conteo, sin casos más lentos.

**Dificultades y soluciones.** Usar solamente la mitad baja del producto habría perdido precisión. Se comprobó el producto en 17.544 casos y REDONDEA en 23.144. Las seis vueltas generales se conservaron. La rutina ocupa dos bytes más: 1.054 frente a 1.052. El error absoluto máximo medido sin saturación se mantiene en aproximadamente 0,001958, menor que un paso Q7.8.

**Próxima sesión.** Facilitar la prueba visual y mantener separados los módulos de BYTEX-16 y el Assembly LC-3 publicado para el simulador del Grupo 8.

## 26 de noviembre de 2026 con interfaz gráfica

Hora no registrada.

**Objetivo.** Ofrecer una ventana clara con controles grandes y mediciones visibles.

**Actividades realizadas.** Se añadió una interfaz Win32 con editor, consola, registros, memoria, ejecución, pausa, pasos y breakpoints. Se reutilizaron núcleo y ensamblador. Se agregaron temas claro y oscuro y contadores Programa, Sistema y Total. Una casilla permite seleccionar el alcance mostrado sin alterar la ejecución. Se comprobó apertura de ASM y OBJ, guardado con nombre Unicode y diagnósticos.

**Observaciones y hallazgos.** El ejemplo 15+27 deja 42 en R0 y en x300E, con 5 instrucciones de programa, 103 del sistema y 108 totales. La demo EXP imprime x1416 y cuenta 1.799 de programa más 405 de sistema. La función aislada conserva 1.755: el resto pertenece al llamador y sus servicios.

**Dificultades y soluciones.** La clasificación de sistema no se puede inferir del nombre del opcode: todas las instrucciones pertenecen a la ISA. Se documentó el mapa de memoria utilizado. La espera de teclado no debe sumar vueltas del temporizador como si fueran instrucciones. Se mantuvo el límite basado siempre en el total para poder detener también un bucle dentro del sistema.

**Próxima sesión.** Probar el ingreso consecutivo de opciones y operandos de la calculadora y verificar que la ventana muestre el resultado sin una pausa manual.

## 26 de noviembre de 2026 con corrección del teclado

Hora no registrada.

**Objetivo.** Resolver la actualización de la calculadora entre pedidos de teclado.

**Actividades realizadas.** Se reprodujo el problema comunicado: pulsar 5 ejecutaba la selección, pero el pedido de exponente aparecía recién al pausar. Se revisó execution_tick y se detectó el retorno temprano cuando ambos extremos del tramo eran Espera teclado. Se añadió gui_session_tick para detectar progreso real aunque el estado final vuelva a esperar.

**Observaciones y hallazgos.** La corrección muestra de inmediato el pedido al pulsar 5, el dígito al escribir 3 y 20.0859375 al confirmar con Enter. Una tecla vuelve al menú sin pausar. Se observaron 3.416 instrucciones tras seleccionar 5 y 9.432 al mostrar el resultado en esa secuencia gráfica controlada. No son la medida aislada del algoritmo.

**Dificultades y soluciones.** La CPU ya avanzaba: el defecto estaba en la decisión de refrescar. Se añadieron regresiones para dos lecturas consecutivas y para la secuencia completa 5, 3, Enter, vuelta al menú y salida. La sesión pasó 121 comprobaciones sin fallos. También se corrigió la construcción de la prueba para disponer del objeto actual de calculadora.

**Próxima sesión.** Cerrar la validación completa, actualizar informe y bitácora y reunir los archivos de entrega con un procedimiento reproducible.

## 26 de noviembre de 2026 con revisión final

Hora no registrada.

**Objetivo.** Completar la documentación y preparar una entrega que permita repetir los resultados.

**Actividades realizadas.** Se ejecutó nuevamente probar.bat y se reunieron instrucciones, imagen, direcciones únicas, tráfico y precisión con tools/medir_entrega.py. Se comprobó el repositorio original: main sigue en d47c5ecb93f7ab4c1d2d521a88e68f20713a10a8, la revisión del benchmark. Se actualizó el informe y se preparó esta bitácora a partir de los registros conservados.

**Observaciones y hallazgos.** Toda la suite terminó sin fallos. Las 37 llamadas suman 25.206 instrucciones y su imagen ocupa 7.468 bytes. El menú automático ejecuta 12.706 instrucciones y ocupa 14.558 bytes sin encabezado. El máximo error absoluto de EXP se midió sobre 52.642 entradas sin saturación; las 12.894 saturadas se informan por separado.

**Dificultades y soluciones.** Se corrigió el tamaño antiguo que figuraba en el informe y se distinguió entre equivalencia con C y exactitud matemática. No se inventaron horas de sesiones pasadas. Se conservaron el título y los integrantes aceptados del README original al preparar la documentación de GitHub. Las tres opciones sin conectar siguen así en la fuente de la cátedra y quedan declaradas.

**Próxima sesión.** Revisar en grupo los ejemplos y preparar la explicación oral. La comparación para promoción depende de la carga y criterios que utilice la cátedra. Una extensión de ciclo preciso corresponde a otra modalidad y no se presenta como implementada. La publicación se realiza desde la carpeta de entrega preparada, revisando antes el diff del PR.

## 26 de noviembre de 2026 con corrección del pegado

Hora no registrada. Objetivo: conservar los renglones al pegar código nuevo. Se identificó que la apertura de archivos convertía LF a CRLF, mientras el portapapeles llegaba directamente al control EDIT. Se unificó esa conversión y se conservó el pegado sobre la selección como una sola operación de Deshacer. Se comprobó en un control real de Windows y en la interfaz visible, incluyendo líneas vacías y acentos. La suite completa y las 44 regresiones del editor terminaron sin fallos. El programa pegado dejó 7 en R0 y RESULTADO. Se actualizó el ejecutable y los paquetes; el núcleo y los algoritmos se conservan.


## 27/11/2026 — Benchmark completo del Grupo 27

**Problema detectado.** La prueba automática entregada solo recorría tres operaciones. El main recibido utiliza un contrato nuevo de 23 operaciones con cinco palabras por registro. Con el menú anterior se reprodujo una excepción de acceso tras 353 instrucciones.

**Corrección.** Se conservó el main recibido y todos sus valores; se actualizó el menú y su direccionamiento por bytes, se añadió el alias G27, se conectaron Taylor y HEX/BIN y se corrigió el acarreo falso en Shift+Add. No cambió la codificación de la ISA ni el núcleo.

**Verificación.** El benchmark recorre las 23 operaciones hasta Q3.12 -> Q7.8 y termina sin excepción: 365.469 instrucciones en modo verboso y 241.990 en silencioso. Las pruebas verifican datos y resultados en memoria, coincidencia fuente/OBJ, funcionamiento interactivo, 4.292 productos y 11 entradas de Taylor. Los conteos anteriores de 12.706 instrucciones corresponden a la prueba histórica corta.
