# Entrega de ISA3C del 26 de noviembre de 2026

La entrega incluye el simulador funcional, ensamblador independiente, editor de consola, interfaz Win32, bibliotecas, ejemplos y pruebas. La interfaz abre con `interfaz.bat`. La biblioteca EXP para esta ISA es distinta del módulo LC-3 que se publica en el simulador del Grupo 8.

## Documentación

- `informes/Informe_ISA3C_integrada.pdf`: arquitectura, catálogo completo de instrucciones, EXP optimizada, precisión, interfaz, contadores y correspondencia con las consignas.
- `informes/Bitacora_Laboratorio_3.pdf`: proceso y problemas documentados. Las horas antiguas no se inventan; el registro se identifica como retrospectivo.
- `BITACORA.md`: el mismo registro de sesiones en texto.
- `INTERFAZ_GRAFICA.md`: uso detallado de la ventana y medición con breakpoints.
- `mediciones_finales/`: resultados, comparación por caso y registro de la suite completa.

## Verificación

`probar.bat` volvió a terminar sin fallos: 764 comprobaciones de ISA/ensamblador, 37 casos del banco, 65.536 entradas de EXP, 23.144 casos de redondeo, 17.544 de producto, 3.145.728 combinaciones de desplazamientos, 4.542.415 de ALU, 5.181 llamadas de raíz y 121 comprobaciones de la sesión gráfica. Las pruebas del banco aplican las tolerancias declaradas por caso; no demuestran exactitud global de todas las funciones matemáticas.

`python tools/medir_entrega.py` reproduce el resumen después de ejecutar las pruebas. El menú automático conserva 12.706 instrucciones y una imagen de 14.558 bytes. Las 37 llamadas suman 25.206 instrucciones. EXP(3) aislada usa 1.755; la demo con impresión y sistema usa 2.204.

La referencia de precisión es `math.exp` double sobre la entrada cuantizada. El error absoluto máximo sin saturación es 0,0019580065052480222 y el mínimo es cero. Se analizaron 52.642 entradas y se separaron las 12.894 saturadas. El error de cuantización de un exponente real anterior no está incluido.

## Alcance de la revisión

Se comprobó la revisión original `d47c5ecb93f7ab4c1d2d521a88e68f20713a10a8`, que coincide con la registrada en `benchmark/procedencia.json`. El menú mantiene tres opciones sin conectar en su origen. La evaluación oficial de rendimiento y la exposición corresponden a la cátedra y al grupo. Pipeline y simulación de ciclo preciso son extensiones opcionales que no están implementadas.

Esta copia contiene los archivos del simulador y benchmark para la entrega. No incluye los respaldos ni los Word editables. LEER_PRIMERO.txt explica cómo ejecutar y ensamblar.
