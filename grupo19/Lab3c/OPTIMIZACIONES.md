# Optimizaciones del benchmark por funcionalidad

Este documento describe las optimizaciones y adaptaciones implementadas en
`benchmark_optimizado`, agrupadas por la funcionalidad visible del benchmark,
no por archivo fuente. Cuando una rutina usa varios módulos auxiliares, se
documentan juntos en la misma sección.

La nueva ISA no incorpora instrucciones de multiplicacion ni division. Las
rutinas matematicas siguen siendo algoritmos de software; aprovechan
desplazamientos, comparaciones, banderas de acarreo, operaciones de 32 bits
con pares de registros y la pila hardware. La presencia de una optimizacion
no implica que toda entrada ejecute menos instrucciones que en LC-3: los
conteos son dinamicos y las instrucciones de cada ISA no tienen el mismo
costo.

## Funcionalidades ordenadas por grupo

Las funcionalidades se presentan en orden ascendente segun el numero de grupo de sus modulos; las rutinas del mismo grupo permanecen juntas. La interfaz y los helpers compartidos tambien aparecen en su posicion por grupo.

### Division CORDIC — operacion 18

**Modulos:** [g1_cordic_division.asm](benchmark_optimizado/lib/g1_cordic_division.asm).

- Conserva el metodo lineal/vectoring y sus 16 pasos. La iteracion inicial
  esta fuera del lazo, por lo que el ciclo principal ejecuta 15 iteraciones.
- Actualiza el residuo mediante `SHL` y suma/resta del divisor, y actualiza
  el resultado con desplazamiento y `INC/DEC`.
- Preserva solo los registros auxiliares que usa con `PUSHM/POPM`; no
  requiere tabla de constantes ni subrutinas de desplazamiento.

### Multiplicacion basica shift-and-add — operacion 14

**Modulos:** [g3_MultiplicacionSHIFTandADD.asm](benchmark_optimizado/lib/g3_MultiplicacionSHIFTandADD.asm).

- Obtiene el signo con XOR y magnitudes con `NEG`; acumula el producto
  Q16.16 en dos registros.
- Procesa los bits del multiplicador con `LSR` y suma solo cuando el bit es
  uno. La pareja `ADD+ADC` propaga el acarreo de la palabra baja a la alta.
- Desplaza el multiplicando de 32 bits con `SHL+RLC` y termina cuando el
  multiplicador ya no tiene bits activos, en vez de completar siempre todas
  las iteraciones.
- Preserva registros con `PUSHM/POPR` y es reentrante, sin variables
  estaticas de respaldo.
- La rutina LC-3 tiene un error de acarreo documentado en [README.md](README.md);
  por eso su salida no se usa como referencia para esta operacion.

### Potencia por exponenciacion binaria — operacion 12

**Modulos:** [g4_potencia.asm](benchmark_optimizado/lib/g4_potencia.asm).

- Descompone el exponente con `LSR #1`; el bit extraido en `C` determina si se
  multiplica el acumulador.
- Eleva la base al cuadrado solo si quedan bits del exponente, evitando la
  ultima multiplicacion que no se utilizaria.
- Calcula el signo final a partir del signo de la base y la paridad del
  exponente, en vez de aplicar signo en cada iteracion.
- Conserva el algoritmo entero y usa sumas sucesivas para los productos,
  junto con `CLR`, `NEG`, `DEC` y la pila hardware.

### Potencia por multiplicaciones sucesivas — operacion 11

**Modulos:** [g5_Mul_Sucesiva_POW.asm](benchmark_optimizado/lib/g5_Mul_Sucesiva_POW.asm).

- Mantiene la definicion de potencia como multiplicaciones sucesivas, pero
  maneja explicitamente exponentes 0 y 1, base cero, exponentes negativos y
  overflow para terminar pronto en esos casos.
- Su multiplicacion Q7.8 separa partes enteras y fraccionarias con
  desplazamientos de 8 bits, en lugar de dividir repetidamente por 256.
- La parte entera se obtiene por sumas; la fraccionaria acumula productos de
  bytes y propaga cada acarreo de 256 al resultado.
- Verifica overflow durante las sumas y evita continuar el ciclo una vez
  detectado.

### Exponenciacion `e^x` — operacion 10

**Modulos:** [g6_EXP.asm](benchmark_optimizado/lib/g6_EXP.asm).

- Reduce el argumento con multiplos de ln(2), representando el residuo en
  tres limbos de 15 bits; aplica simetria para entradas negativas.
- Selecciona cada digito de la reduccion mediante pruebas binarias
  `16, 8, 4, 2, 1` contra una tabla de constantes, y resta una vez el digito
  seleccionado.
- Calcula seis pasos de la aproximacion mediante tabla y acumulacion de
  productos pequenos. Las operaciones entre limbos propagan acarreo con
  `ADC`.
- `REDONDEA` empaqueta los limbos en palabras, usa desplazamientos variables
  (`SRLV/SHLV`) y vuelve a desempaquetar; evita un ciclo por cada bit del
  desplazamiento.
- Detecta saturacion y resultados redondeados a cero, dejando estado y numero
  de iteraciones disponibles para la interfaz.

### Maximo comun divisor — operacion 21

**Modulos:** [g7_mcd.asm](benchmark_optimizado/lib/g7_mcd.asm).

- Implementa Euclides por restas sucesivas, evitando una division general
  para hallar el resto.
- Calcula magnitudes, trata operandos cero antes del ciclo y compara/resta
  directamente con `CMP/SUB`.
- Solo preserva el registro que modifica; el resultado es exacto para el
  rango de entrada documentado.

### Minimo comun multiplo — operacion 22

**Modulos:** [g7_mcm.asm](benchmark_optimizado/lib/g7_mcm.asm).

- Obtiene el MCD por Euclides y divide el menor por el MCD antes de
  multiplicar, reduciendo el riesgo de overflow intermedio.
- La division y la multiplicacion restantes usan restas/sumas sucesivas,
  con deteccion de overflow dentro del ciclo.
- Casos cero terminan antes de los ciclos; el indicador de overflow se forma
  con `MOVH` en vez de cargar una constante desde memoria.

### Raiz cuadrada Newton-Raphson en Q15.16 — operacion 9

**Modulos:** [g9_sqrt_nr_dq16.asm](benchmark_optimizado/lib/g9_sqrt_nr_dq16.asm),
[g9_sqrt_nr_q8.asm](benchmark_optimizado/lib/g9_sqrt_nr_q8.asm) y
[g9_sq9_math_helpers.asm](benchmark_optimizado/lib/g9_sq9_math_helpers.asm).

- Normaliza el radicando mediante potencias de cuatro para llevarlo al rango
  `[4, 16]`; luego ejecuta Newton-Raphson en Q7.8 y revierte la escala.
- La conversion Q15.16/Q7.8 usa desplazamientos de palabras y redondeo
  directo, evitando conversiones genericas.
- En el nucleo Q7.8, `SQ9_MULQ` separa la palabra en bytes alto y bajo y
  acumula sus productos con los bits del multiplicador.
- La multiplicacion procesa dos bits por vuelta y termina anticipadamente
  cuando el multiplicador restante es cero. Este desenrollado redujo la
  seccion Newton-Raphson medida de 2.463 a 2.358 instrucciones, sin cambiar
  sus iteraciones Newton.
- El helper de rotacion de 32 bits intercambia las palabras para desplazamientos
  de 16 o mas y solo itera el desplazamiento residual. El camino principal
  tambien usa conversiones de escala por desplazamientos directos.

### Division larga — operacion 16

**Modulos:** [g10_division_larga.asm](benchmark_optimizado/lib/g10_division_larga.asm).

- Alinea el dividendo de 32 bits con `SRLV/SHLV` en una sola operacion
  variable, evitando un ciclo de desplazamientos de entrada.
- Conserva la division restauradora de 16 pasos; la comparacion sin signo
  usa el prestamo de `CMP` (`BRc/BRnc`) para decidir si se resta el divisor.
- Detecta divisor cero y cociente fuera de rango antes/despues del ciclo, y
  devuelve estado y saturacion definidos.
- La entrada publica Q7.8 llama al mismo motor con desplazamiento de escala
  ocho, sin duplicar la division.

### Logaritmo CORDIC — operacion 20

**Modulos:** [g11_CORDICLog.asm](benchmark_optimizado/lib/g11_CORDICLog.asm).

- Normaliza el argumento por duplicaciones y guarda el exponente `k`; al
  final corrige el resultado restando `k*ln(2)`.
- Mantiene el CORDIC hiperbolico con la secuencia fija
  `1,2,3,4,4,5,...,12`.
- Usa `SRLV` como desplazamiento variable. Para `y` negativo, niega antes y
  despues del desplazamiento para conservar el truncamiento hacia cero, sin
  llamar a un helper de desplazamiento aritmetico.
- Los acumuladores y el estado temporal permanecen en registros/variables
  locales del modulo; las entradas no positivas y los resultados menores
  que el rango Q3.12 se saturan.

### Division Newton-Raphson — operacion 17

**Modulos:** [g12_subrutina_grupo_12.asm](benchmark_optimizado/lib/g12_subrutina_grupo_12.asm).

- Normaliza el divisor y usa una LUT de ocho valores como aproximacion
  inicial del reciproco.
- Ejecuta dos iteraciones `X = X * (2 - D*X)` y una multiplicacion final por
  el dividendo absoluto.
- La normalizacion/desnormalizacion usa desplazamientos variables en vez de
  rutinas de desplazamiento por un bit.
- `MULT_MODULO` hace la multiplicacion Q3.12 mediante un acumulador de 32 bits,
  `SHL/RLC`, deteccion de bit por acarreo y suma condicionada.
- El signo se maneja por separado; divisor cero devuelve el valor de error
  documentado por el modulo.

### Logaritmo por Borchardt — operacion 19

**Modulos:** [g14_log_borchardt_q8_7.asm](benchmark_optimizado/lib/g14_log_borchardt_q8_7.asm).

- Normaliza el argumento por potencias de dos y lleva el valor a un intervalo
  acotado antes de evaluar el nucleo.
- El nucleo de Borchardt usa cuatro iteraciones aritmetico-geometricas y una
  LUT de 128 raices cuadradas, evitando recalcular cada raiz iterativamente.
- El cambio de base se calcula como `ln(x)/ln(b)` con auxiliares de
  multiplicacion y division sin signo, y redondeo del cociente.
- Los desplazamientos fijos por 1 y 7 se expresan directamente con
  `LSR/SHL`; las comparaciones de rango usan `CMP`. La pila hardware reemplaza
  el respaldo manual.
- Rechaza argumentos/base fuera del dominio y evita la division cuando
  `ln(b)` es cero.

### Conversion Q3.12 a Q7.8 — operacion 23

**Modulos:** [g15_G15_Q312_Q78.asm](benchmark_optimizado/lib/g15_G15_Q312_Q78.asm).

- Sustituye el calculo equivalente a `(R0 * 16) >> 8` en 32 bits por un unico
  `ASR #4`. Es exacto para la conversion con signo definida por el contrato.

### Multiplicacion Booth — operacion 15

**Modulos:** [g18_booth.asm](benchmark_optimizado/lib/g18_booth.asm).

- Mantiene las 16 iteraciones Booth, pero mantiene `A`, `Q`, `QM1` y el
  contador en registros en lugar de variables de memoria.
- Los desplazamientos de una posicion se hacen con `ASR/LSR` y `RRC`,
  reemplazando subrutinas de desplazamiento repetidas.
- Extrae directamente `P[23:8]` con `SHL`, `LSR` y `OR`, sin un ciclo de
  ocho desplazamientos.
- Conserva la regla especial para `A' == 0x8000`, calcula el indicador de
  overflow y retorna las banderas del resultado.

### Multiplicacion CORDIC — operacion 13

**Modulos:** [g19_cordic_multiplicacion.asm](benchmark_optimizado/lib/g19_cordic_multiplicacion.asm).

- Prepara `current_x` en Q16 con dos desplazamientos, sin una subrutina de
  escalado.
- Actualiza las palabras alta y baja del acumulador con `ADD+ADC` y
  `SUB+SBC`; el desplazamiento aritmetico de 32 bits usa `ASR+RRC`.
- Genera el angulo `current_z` desplazando desde 16384, eliminando la tabla
  de angulos almacenada en memoria.
- Termina cuando `z` llega a cero. La conversion final a Q7.8, el redondeo y
  la comprobacion de overflow se resuelven con desplazamientos y operaciones
  de registro.
- Rechaza el divisor/operando `-32768`, cuya magnitud no es representable en
  16 bits.

### Reduccion de argumento a `[-pi/2, pi/2]` — operacion 1

**Modulos:** [g20_Cordic_reduccion_de_argumento.asm](benchmark_optimizado/lib/g20_Cordic_reduccion_de_argumento.asm).

- Conserva la reduccion por sumas o restas sucesivas de pi.
- Mantiene pi y pi/2 en registros y usa `CMP` con ramas con signo, evitando
  cargar las constantes desde memoria en cada vuelta.
- Usa `PUSHM/POPM` para preservar los registros auxiliares con la pila
  hardware.
- La rutina LC-3 correspondiente se deja intacta. Su comparacion mediante
  `R0 - 6434` puede desbordar para ciertas entradas negativas; ese defecto de
  la referencia esta documentado en [README.md](README.md). Las pruebas de
  esos extremos validan la reduccion esperada, no la salida LC-3 defectuosa.

### Seno por serie de Taylor — operacion 2

**Modulos:** [g21_senotaylor_subrutina.asm](benchmark_optimizado/lib/g21_senotaylor_subrutina.asm).

- Reduce el angulo por cuadrantes a un angulo del primer cuadrante y conserva
  el signo por separado.
- Calcula los terminos de la serie usando multiplicacion sin signo
  `16x16 -> 32` y division larga `32/16`, ambas implementadas en el mismo
  modulo.
- `MULT_U32` procesa primero los bits bajos del multiplicador con
  *shift-and-add* y termina cuando ya no quedan bits activos, en vez de
  ejecutar siempre las 16 iteraciones.
- La division evita las 16 iteraciones de la parte alta cuando el dividendo
  cabe en 16 bits. La extraccion del resultado Q3.12 se hace con
  desplazamientos y combinacion de palabras, sin una rutina bit a bit.
- La variante LSB-first produjo la misma salida para los 3.601 angulos validos
  probados. En la medicion de esa optimizacion, la seccion Taylor paso de
  2.306 a 2.272 instrucciones.

### Seno y coseno por tabla — operaciones 3 y 5

**Modulos:** [g22_Tabla_SIN_y_COS.asm](benchmark_optimizado/lib/g22_Tabla_SIN_y_COS.asm).

- Seno y coseno comparten `CALCULAR_AMBOS_V3`: se determina el cuadrante, se
  calcula la referencia del seno y la del coseno por cofuncion, y se
  reutiliza la interpolacion del primer cuadrante.
- La tabla almacena muestras espaciadas 32 unidades Q3.12. El indice se
  obtiene con `LSR #5`; el resto con una mascara. Esto sustituye la
  extraccion bit a bit descrita en el fuente como 66 y 67 instrucciones por
  extracciones directas.
- Interpola entre dos muestras consecutivas mediante el resto de cinco bits,
  redondeando el producto antes de sumarlo a la muestra actual.
- El direccionamiento de palabras escala el indice a bytes con un
  desplazamiento, y la preservacion de registros usa `PUSHM/POPR`.

### Raiz cuadrada por metodo non-restoring — operacion 8

**Modulos:** [g23_modulo_sqrt_nr.asm](benchmark_optimizado/lib/g23_modulo_sqrt_nr.asm).

- Conserva el algoritmo digito a digito: cada una de las 13 iteraciones
  produce un bit de la raiz y baja dos bits del radicando.
- Usa `SHL/RLC` para desplazar el radicando y el resto parcial; actualiza el
  resto con suma o resta segun su signo, sin division ni tabla.
- Corrige el resto al final y redondea comparandolo con la raiz parcial.
- Las 13 iteraciones son fijas para mantener el resto parcial dentro del
  rango con signo de 16 bits. `PUSHM/POPM` reemplaza el guardado manual de
  registros.

### Conversion e impresion hexadecimal y binaria — operaciones 6 y 7

**Modulos:** [g24_conversor_lc3_max.asm](benchmark_optimizado/lib/g24_conversor_lc3_max.asm).

- Hexadecimal: extrae cada nibble directamente con `LSR #12`, desplaza el
  siguiente nibble con `SHL #4` y genera el caracter ASCII con sumas de
  constantes inmediatas.
- Binario: desplaza el valor a la izquierda; el bit saliente en `C` decide
  si se imprime `0` o `1`, sin mascara ni desplazamiento auxiliar.
- Ambas rutinas preservan registros con la pila hardware y cargan constantes
  con `MOVI`.

### Menu y despacho de operaciones

**Modulos:** [g27_main_menu_PROGRESO.asm](benchmark_optimizado/lib/g27_main_menu_PROGRESO.asm).

- `PUSHM/POPR` reemplazan variables de respaldo para los registros.
- `JSRM` llama a subrutinas a traves de punteros cercanos sin cargar un
  registro temporal con cada direccion.
- Usa `MOVI/CLR` para constantes y cero, y actualiza punteros de palabras en
  bytes (`+2`, `+8`) con el escalado de indices necesario.
- Los buffers de caracter usan `STBL`; los helpers de entrada/salida se
  llaman a traves de los punteros enlazados del menu.

### Lectura y conversion de entradas

**Modulos:** [g27_getline.asm](benchmark_optimizado/lib/g27_getline.asm),
[g27_getcfiltered.asm](benchmark_optimizado/lib/g27_getcfiltered.asm),
[g27_getval.asm](benchmark_optimizado/lib/g27_getval.asm),
[g27_getval_buffer.asm](benchmark_optimizado/lib/g27_getval_buffer.asm),
[g27_fromdec.asm](benchmark_optimizado/lib/g27_fromdec.asm),
[g27_fromhex.asm](benchmark_optimizado/lib/g27_fromhex.asm).

- `GETLINE` almacena un byte por caracter con `STBL`, limita la escritura
  antes del terminador y usa `CMP/BRnc` para comprobar el limite del buffer.
- `GETCFILTERED` recorre rangos de caracteres de dos en dos bytes y usa
  comparaciones con signo para aceptar o descartar la tecla.
- `FROMHEX` convierte cada digito con `SHL #4` y suma el nibble; marca
  entrada invalida y mas de cuatro digitos.
- `FROMDEC` forma `entero*10` con desplazamientos y sumas, procesa la
  fraccion decimal con operaciones de 32 bits y obtiene los bits
  fraccionarios por desplazamientos, resta de mil millones y redondeo.
- Las sumas/restas de varias palabras usan `ADC/SBC` directamente; por eso
  `FROMDEC` no necesita llamar a `SUMOVER`.
- `GETVAL` integra lectura, parseo y conversion de formato. Usa `JSRM`,
  `PUSHM/POPR` y operaciones inmediatas para evitar punteros temporales y
  variables de respaldo.

### Conversion de formatos Q y presentacion decimal

**Modulos:** [g27_to_qm_n.asm](benchmark_optimizado/lib/g27_to_qm_n.asm),
[g27_from_qm_n.asm](benchmark_optimizado/lib/g27_from_qm_n.asm),
[g27_todec.asm](benchmark_optimizado/lib/g27_todec.asm),
[g27_outval.asm](benchmark_optimizado/lib/g27_outval.asm).

- `TO_QM_N`/`FROM_QM_N` convierten entre Qm.n y Q15.16 con
  `SHLV/SRLV/SRAV`, casos directos para `n=0` y `n=16`, y redondeo usando el
  primer bit descartado. Evitan llamadas a `CIRCLSH` y mascaras iterativas.
- `TODEC` escribe caracteres con `STBL`, genera signos y digitos con
  operaciones de registro y deja de emitir decimales cuando el formato lo
  permite.
- La fraccion decimal se convierte sumando contribuciones de cuatro nibbles
  consultadas en LUT, con suma de 32 bits `ADD/ADC`, en lugar de procesar
  cada bit de la fraccion por separado.
- `OUTVAL` convierte el valor al formato solicitado, comparte el buffer y
  llama directamente a `TODEC` con `JSRM`.

### Pausa y helpers aritmeticos/de bits

**Modulos:** [g27_pause.asm](benchmark_optimizado/lib/g27_pause.asm),
[g27_sumover.asm](benchmark_optimizado/lib/g27_sumover.asm) y
[g27_circlsh.asm](benchmark_optimizado/lib/g27_circlsh.asm).

- `PAUSE` usa `PUSHM/POPM`, constantes inmediatas y el contrato de que `TRAP`
  preserva `R7`.
- `SUMOVER` usa el flag nativo de acarreo y `ADD` para devolver suma y carry,
  sin reconstruir el acarreo con comparaciones.
- `CIRCLSH` reduce la rotacion de dos palabras a intercambios de palabras y
  desplazamientos variables directos, en vez de rotar un bit por iteracion.
- Los dos ultimos helpers se mantienen como utilidades de biblioteca; el
  menu actual no los importa en la ruta automatica.

### Seno Chebyshev-Pade — operacion 4

**Modulos:** [g30_seno_cheb_pade.asm](benchmark_optimizado/lib/g30_seno_cheb_pade.asm).

- Mantiene el nucleo racional `x * (1 - A*u) / (1 + B*u)`, con `u = x^2/2`,
  reduccion de rango, aritmetica Q1.14 y redondeo explicito.
- Las multiplicaciones forman productos de 32 bits con desplazamientos,
  rotaciones con acarreo y suma de redondeo; no dependen de multiplicacion
  por hardware.
- `DIVF` realiza una division restauradora de 14 pasos. Sus comparaciones
  usan el acarreo de `CMP` como comparacion sin signo; asi se manejan
  correctamente restos que, al duplicarse, tienen activado el bit de signo.
- Incluye una ruta para la entrada Q3.12 minima `-8`, cuya magnitud no cabe
  como entero positivo de 16 bits, y preserva el signo a traves de la
  multiplicacion final.
- Estas correcciones hacen coincidir los resultados de `-8` y `0x7fff` con
  LC-3 en las pruebas de limites. En `0x7fff`, el resultado anterior estaba
  dos LSB por debajo.

## Optimizaciones evaluadas y no incorporadas

- Se considero aplicar Horner al CORDIC, pero no se incorporo: Horner evalua
  polinomios; las rutinas CORDIC presentes actualizan coordenadas mediante
  iteraciones y no tienen ese polinomio como nucleo. No se atribuye una
  mejora medida a esa idea.
- Las optimizaciones de Newton-Raphson de raiz y de multiplicacion Taylor
  cambiaron la implementacion interna de los ciclos, no el algoritmo
  matematico ni el numero de iteraciones Newton/terminos Taylor.

## Validacion y resultados conocidos

- El benchmark automatico actual ejecuto **29.037 instrucciones** en la
  nueva ISA; la referencia LC-3 ejecuto **357.505** en la misma configuracion.
  Los conteos son trabajo dinamico, no una comparacion directa de tiempo o
  rendimiento entre ISA.
- La optimizacion del multiplicador interno de raiz redujo esa seccion de
  2.463 a 2.358 instrucciones en la medicion correspondiente.
- La optimizacion de `MULT_U32` en Taylor redujo la seccion de 2.306 a 2.272
  instrucciones y mantuvo la salida en los 3.601 angulos probados.
- Los limites agregados para reduccion de argumento y Chebyshev-Pade tienen
  pruebas de regresion. La suite completa reporto 38 pruebas aprobadas en la
  ultima validacion.
- La multiplicacion shift-and-add LC-3 tiene un error de acarreo y la
  reduccion de argumento LC-3 tiene un limite de overflow con signo. Ambos
  defectos pertenecen a la referencia original, se mantienen sin modificar y
  estan descritos en [README.md](README.md).
