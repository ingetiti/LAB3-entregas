# Integración de las operaciones del RAR en ISA3C

## Interfaz gráfica de Windows — 26/11/2026

Se agregó `interfaz.bat` y una ventana nativa con editor, consola, registros, memoria, pasos y breakpoints. Reutiliza el ensamblador y el núcleo existentes. Incluye temas claro/oscuro y contadores separados de programa, sistema y total, con una casilla para elegir el alcance visible. Los temas y el selector conservan el estado de ejecución. El límite por tramo usa siempre el total. Se mantienen el editor de consola y los ejecutores anteriores. `docs/INTERFAZ_GRAFICA.md` explica uso, criterios y medición de EXP aislada.

Se corrigió el refresco del teclado entre pedidos consecutivos: al elegir 5, ingresar un exponente y volver al menú, la salida se muestra sin pausar. La detección de progreso considera instrucciones, salida y eventos, incluso si ambos extremos del tramo están en espera de teclado. Se añadieron regresiones de dos lecturas seguidas y de la calculadora completa sin pausas.

Se tomó como punto de partida nuestra versión experimental y se incorporaron las operaciones útiles del archivo Lc-3.rar. Se conservaron los formatos de los programas y servicios que ya estaban integrados, en lugar de mezclar decodificadores incompatibles.

## Cambios del núcleo y ensamblador

Se añadieron SUB, MUL, MULU, DIVU, CLZ y MOV. Los desplazamientos SHL/SHR/SAR de la versión experimental se mantienen; ASR es un alias de SAR para reconocer también el nombre usado en el RAR.

ADD y AND entre registros tenían dos bits sin uso, [4:3]. Se utilizan como suboperación de cada familia. Los códigos principales siguen siendo los cinco bits [15:11], las instrucciones siguen ocupando dos bytes, y los inmediatos y offsets de la base conservan sus tamaños. Se actualizó también el desensamblador para que el depurador muestre los nombres nuevos.

DIVU por cero devuelve cero, como en el RAR. MULU devuelve la parte alta sin signo, no la parte baja. MOV y CLZ son operaciones de dos registros y deben tener el campo Rt en cero; una codificación inválida de ese campo genera excepción.

Se agregó tráfico acumulado de memoria, además de las estadísticas de direcciones únicas. El núcleo, la consola del depurador y el CSV distinguen ambas medidas. El ejecutable sigue devolviendo un código de error si hubo una excepción, incluso si el manejador termina con HALT.

## Cambios en programas

La raíz recíproca de Newton del Grupo 9 mantiene su algoritmo y sus seis vueltas. Se reemplaza la primitiva SQ9_MULQ por un producto de 32 bits obtenido con MUL/MULU y un ajuste con SHL/SHR. También se reemplaza la extracción de bits para dividir por dos por SHR. Se mantiene floor(a*b/256) sin perder la palabra alta del producto.

Se conservaron las traducciones previas de Booth, multiplicación/logaritmo CORDIC y conversión Q. EXP conserva sus seis pasos generales y sus rutas rápidas. La etiqueta interna ASR del logaritmo pasó a G11_ASR_TRUNC para no colisionar con la nueva palabra reservada; se renombró también una etiqueta SUB de las pruebas.

El generador de módulos aplica ahora las optimizaciones después de regenerar la adaptación base. Se verificó en una copia de prueba que produce los mismos bytes de todos los módulos finales. El ejemplo alu_integrada.asm comprueba las nuevas operaciones y muestra OK o ERROR.

## Decisiones que se conservaron de nuestra versión

- Ensamblador y núcleo como ejecutables separados.
- Sistema mínimo preensamblado durante la compilación.
- Padding automático y comprobación de direcciones pares.
- `.EXTERNAL` con aislamiento de etiquetas y resolución recursiva.
- Alcances de carga/salto y operandos inmediatos de cinco bits de ADD/AND.
- TRAP por pila supervisora y RTI, para conservar la interfaz existente.
- LDBL con conservación de la mitad alta; LDBS para byte con signo.
- Caracteres por palabra en STRINGZ, para conservar los servicios del menú.
- Métricas de tamaño y direcciones únicas, ahora acompañadas de tráfico acumulado.

Se portaron ideas y semánticas aritméticas, no los objetos ni todo el código del RAR. La semántica de LDBL, los offsets y TRAP del RAR siguen siendo diferentes. No se introdujeron instrucciones de exponencial, raíz, logaritmo ni trigonometría en la CPU.

## EXP optimizada el 26 de noviembre de 2026

Se reemplazaron la extraccion de bits de la escala, las restas de tabla, el producto repetido por un digito y el redondeo bit a bit por SHL/SHR, SUB y productos MUL/MULU con acarreo en base 2^15. No se cambio el algoritmo multiplicativo de seis pasos, su tabla, la convencion de registros ni los resultados. La rutina conserva las rutas rapidas anteriores y no modifica R6.

Se agregaron una prueba independiente en ejemplos/exp_isa3c.asm, el comparador exhaustivo tests/test_exp_optimized.c y la referencia anterior en tests/exp_previa. La optimizacion queda registrada en tools/optimizaciones_modulos.json para que regenerar los fuentes no la borre. Ver EXP_OPTIMIZADA.md para las mediciones.

## Corrección del pegado en el editor el 26 de noviembre de 2026

El editor normalizaba saltos al cargar archivos, pero no al pegar texto con LF. Se añadió `gui_editor.c`: intercepta WM_PASTE y convierte LF, CRLF y CR a CRLF antes de reemplazar la selección con una operación que admite Deshacer. Se reutiliza la misma conversión al abrir fuentes. No se modifica el portapapeles ni el núcleo. La compilación y CMake incluyen el módulo y la nueva prueba del control EDIT real de Windows, con 44 comprobaciones correctas.

## Título de la interfaz del Grupo 6

El encabezado y la barra de título muestran ISA Grupo 6. Se amplió el espacio del encabezado para que el nombre completo quede visible.
