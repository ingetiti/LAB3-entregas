# Validación vigente de BYTEX-16

El 27/11/2026 se recompilaron las herramientas y la interfaz con el nombre **BYTEX-16 - Grupo 6**. La entrega está en `Lab3c/BYTEX-16/`. La suite completa terminó sin fallos; el benchmark de 23 operaciones mantiene 365.469 instrucciones totales y excepción 0. Los objetos de calculadora, calculadora automática, funciones, sistema y EXP coinciden byte por byte con la implementación anterior al cambio de nombre.

Se verificaron los temas claro y oscuro, el título sin recortes y la suma 15+27: R0=42, 5 instrucciones de programa, 103 de sistema y 108 totales. Las doce prácticas de la guía se ensamblaron y ejecutaron; la práctica de bucle infinito se detuvo en su límite previsto. La guía PDF tiene 29 páginas. `VALIDACION_COPIA_ENTREGA.json` y `mediciones_finales/resumen.json` reúnen las medidas actuales.

El generador de entradas reconstruye ahora el benchmark completo del main recibido y reproduce los tres objetos de entrada entregados. Este ajuste de la herramienta no cambia el código máquina del benchmark.

## Historial anterior

Las secciones siguientes conservan el registro de las versiones previas, incluidos sus conteos y opciones pendientes de aquel momento.

> Actualización del 27/11/2026: el benchmark vigente recorre las 23 operaciones del main recibido, con 365.469 instrucciones y excepción 0. Los conteos de tres operaciones y las opciones pendientes mencionados abajo describen la versión anterior.

# Validación de BYTEX-16 1.1

## Interfaz gráfica — 26/11/2026

La sesión gráfica pasó 121 comprobaciones: ejecución y registros, clasificación de instrucciones de programa/sistema, pasos, breakpoints, reinicio, límites, espera de teclado, cola de entrada, objetos, errores y EXP. `compilar.bat` terminó correctamente con la ventana incluida y pasó la suite completa existente. La recompilación de la corrección de teclado pasó las 121 comprobaciones, incluidas dos lecturas consecutivas y la secuencia completa de calculadora sin pausas. Las pruebas gráficas comprobaron suma 42, selector 108/5, EXP hexadecimal `x1416`, calculadora con resultado 20.0859375, entrada directa y por línea, guardado con nombre Unicode, diagnóstico de ensamblado y ejecución de objetos. También se alternaron claro/oscuro conservando resultado y contadores. Ver `interfaz_validacion.json` e `interfaz_compilacion_pruebas.txt`.

Se reprodujo el fallo anterior: pulsar 5 mantenía visible el menú con 2.831 instrucciones; Pausar revelaba el pedido de exponente que ya había producido la CPU con 3.416 instrucciones. Con la corrección, al pulsar únicamente 5 se ve inmediatamente ese pedido y el conteo 3.416; al escribir 3 aparece el dígito, al pulsar Enter aparece 20.0859375 con 9.432 instrucciones y una tecla vuelve al menú. La prueba gráfica corregida no utilizó Pausar.

El núcleo, los opcodes y los fuentes Assembly anteriores se conservaron. Los contadores adicionales pertenecen a `gui_session.c`. Los criterios de medición y la distinción entre instrucciones de la demo e instrucciones de la función aislada se documentan en `INTERFAZ_GRAFICA.md`.

Se compiló con GCC C11, O2, enlace estático y `-Wall -Wextra -Wpedantic -Wconversion -Wshadow -Werror` en Windows x64. `compilar.bat` terminó con código cero. La salida completa está en `compilacion_pruebas.txt`.

| Prueba | Resultado |
|---|---|
| Suite de ISA, ensamblador y enlace | 764 comprobaciones, cero fallos |
| Banco de funciones | 37 casos, cero fallos con las tolerancias declaradas |
| EXP frente a C | 65.536 entradas, cero diferencias de salida; registros preservados |
| Desplazamientos | 3.145.728 combinaciones, cero fallos |
| ALU integrada | 4.542.415 comprobaciones, cero fallos |
| Raíz contra la implementación anterior | 5.181 llamadas con salidas binarias iguales y preservación de registros |
| Menú automático | Termina sin excepción y conserva los resultados −60, 1.421875 y 0 |
| Teclado de la interfaz | EXP(3) muestra 20.0859375 y permite salir |
| Objetos de la versión estable anterior | Sus 37 casos siguen funcionando sobre el núcleo integrado |
| Regeneración de módulos | Reconstruye byte a byte los 38 módulos finales, incluidas seis traducciones optimizadas |

La prueba de ALU cubre codificaciones hexadecimales independientes, desensamblado, los 65.536 valores de CLZ y MOV, valores límite y 100.000 pares deterministas para SUB/MUL/MULU/DIVU. Se incluyen destinos que coinciden con fuentes, división por cero, condiciones NZP, preservación de las fuentes y acceso de dos bytes por instrucción ALU. Las formas de operandos inválidas y el campo reservado de las instrucciones unarias se rechazan.

La prueba de raíz recorre los 3.073 valores del núcleo Q7.8 en [4,16], 60 combinaciones límite de dos palabras y 2.048 entradas deterministas del envoltorio Q15.16. La referencia binaria se obtuvo ejecutando la versión experimental anterior y se conserva en `tests/sqrt_reference.bin`. No se modificaron las seis vueltas de Newton ni se pretendió mejorar su precisión matemática.

## Mediciones

| Programa | Estable original | Experimental previa | Integrada |
|---|---:|---:|---:|
| Menú automático | 20.532 | 15.960 | 12.706 instrucciones |
| Suma de 37 casos, una llamada por caso | 60.225 | 38.299 | 25.206 instrucciones |
| Imagen del banco | 7.630 | 7.552 | 7.468 bytes |
| Imagen de calculadora | 14.720 | 14.642 | 14.558 bytes |

La mejora del menú es 38,12 % respecto de la estable y 20,39 % respecto de la experimental. La suma de pruebas propia mejora 58,15 % respecto de la estable; no es la puntuación oficial de promoción. Los conteos por llamada excluyen impresión del llamador y HALT; el menú incluye esos servicios. Los objetos agregan dos bytes de encabezado al tamaño de la imagen indicado.

El menú integrado registra 32.308 bytes leídos y 3.668 escritos como tráfico acumulado. Sus direcciones únicas son 2.866 accedidas y 282 escritas. Se informa cada medida con su unidad; las cifras no son intercambiables.

## Alcance

Las rutinas de otras funciones mantienen sus aproximaciones. La interfaz de origen tiene tres opciones sin subrutina conectada que siguen mostrando un aviso explícito. No se modelan ciclos precisos ni pipeline; una operación ALU nativa cuenta como instrucción, sin afirmar una latencia física de un ciclo.

La configuración CMake se entrega como alternativa; se comprobó GCC con los scripts Windows. Se conservaron los hashes de los 160 archivos registrados de la estable y los 157 archivos registrados de la experimental al iniciar esta integración. El RAR original no se sobrescribió. `validacion.json` contiene los conteos, la referencia y el SHA-256 del archivo RAR.

## Actualizacion de EXP del 26 de noviembre de 2026

La ISA y los servicios no cambian. La nueva EXP conserva los resultados de las 65.536 entradas, estados, rutas rapidas y registros. La comparacion antes/despues usa el mismo llamador minimo y mide solo la subrutina. El total pasa de 222.466.798 a 68.450.717 instrucciones (69,23 % menos); 45.425 entradas mejoran, 20.111 quedan iguales y ninguna empeora. EXP(3) pasa de 5.016 a 1.755 instrucciones.

REDONDEA se verifico por separado con 23.144 combinaciones de enteros de 45 bits y desplazamientos de 1 a 44. El producto de varias palabras por digitos de 0 a 16 se verifico en 17.544 casos. Todas las comprobaciones terminan sin fallos. La rutina utiliza dos bytes mas de imagen. El menu automatico conserva su conteo porque sus tres operaciones no incluyen EXP; la prueba de teclado de EXP(3) pasa a 12.487 instrucciones incluyendo interfaz y servicios.

El fuente anterior esta en tests/exp_previa, la prueba comparativa es tests/test_exp_optimized.c y el resumen esta en exp_optimizacion.json. La regeneracion reconstruye los 38 modulos con bytes identicos. El log completo de GCC y de la suite esta en compilacion_pruebas.txt. El informe Word/PDF actualizado incorpora esta optimización, la interfaz y sus contadores. La bitácora documenta el proceso y la corrección de teclado.

## Cierre documental y mediciones del 26 de noviembre

Se volvió a ejecutar la suite completa con cero fallos, incluidas las 121 comprobaciones de sesión. `mediciones_finales/pruebas_completas.txt` conserva la salida. `python tools/medir_entrega.py` vuelve a reunir las métricas del banco y los programas y calcula la precisión de EXP sobre la entrada ya cuantizada. El resumen y el CSV están en `mediciones_finales/`.

El error absoluto mínimo medido sin saturación es cero para x=0; el máximo es 0,0019580065052480222 para x=4,79150390625, frente a math.exp double. Se incluyen 52.642 entradas sin saturación y se excluyen 12.894 saturadas. El máximo es menor que un paso Q7.8 y ligeramente mayor que medio paso. El error relativo alcanza 100 % cuando una salida muy pequeña se redondea a cero.

Se comprobó que el repositorio original mantiene la revisión `d47c5ecb93f7ab4c1d2d521a88e68f20713a10a8`. `revision_repositorio_20261126.json` identifica los archivos consultados. Las tres opciones sin conectar siguen así en ese origen; no se presentan como funciones verificadas ni se utiliza el banco propio como puntuación oficial de promoción.

## Regresión de pegado del editor

La versión corregida pasó la suite completa y 44 comprobaciones adicionales sobre el control EDIT nativo: saltos LF/CRLF/CR, selección, Deshacer, texto Unicode, líneas vacías, solo lectura, límite atómico y 5.001 renglones. El pegado por Ctrl+V en la ventana se comprobó con un programa de diez renglones que ensambló y terminó con R0=7 y RESULTADO=7: Programa=4, Sistema=103 y Total=107. Ctrl+Z restauró el programa anterior. Los registros están en `pegado_compilacion_pruebas.txt` y `pegado_validacion.json`.
