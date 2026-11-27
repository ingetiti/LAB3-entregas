# Bitácora de Investigación - Grupo 23 (Lab 3a)

## Sesión 1
- *Fecha y hora:* 30/09/2026 - 18:00 hs a 20:15 hs 
- *Objetivo del día:* Analizar los formatos de representación de números en punto fijo en alto nivel (Lab 3a).
- *Actividades realizadas:* 
  - Creación de la estructura de carpetas (grupo23/alto_nivel y grupo23/asm).
  - Análisis del código lab3a.cpp. Pruebas de conversión de float a formatos Q3.12 y Q7.8 y manejo de desbordes.
- *Observaciones y hallazgos:* Observamos que la división requiere agrandar el dividendo (corrimiento de 16 bits a la izquierda) para no perder resolución en la parte fraccionaria.
- *Dificultades u obstáculos:* Comprender por qué conviene hacer un cast a int32_t de los operandos antes de multiplicar dos números de 16 bits en C++: el producto en Q20 necesita 32 bits, y el cast explícito garantiza ese tamaño sin depender del ancho de int (en una máquina con int de 16 bits, como la LC-3, se perdería la parte alta).
- *Plan para la siguiente sesión:* Traducir los conceptos de corrimiento y multiplicación a Assembly de la LC-3.

## Sesión 2
- *Fecha y hora:* 06/10/2026 - 18:00 hs a 20:15 hs
- *Objetivo del día:* Implementar las operaciones aritméticas de punto fijo en Assembly LC-3 (lab3a.asm).
- *Actividades realizadas:*
  - Codificación de lab3a.asm.
  - Implementación de la subrutina SHL32 para simular corrimientos, ya que la LC-3 carece de esta instrucción nativa.
  - Implementación de la subrutina MULS para la multiplicación de 16x16 bits con resultado en 32 bits.
- *Observaciones y hallazgos:* Para lograr un corrimiento a la derecha, que la LC-3 no tiene, utilizamos el truco de correr un par de 32 bits a la izquierda y tomar la parte alta: correr 16 − k lugares a la izquierda equivale a correr k lugares a la derecha. Para pasar de Q3.12 a Q7.8 (4 a la derecha) se corren 12 bits a la izquierda, y para llevar el producto de Q20 a Q7.8 (12 a la derecha) se corren 4 bits a la izquierda.
- *Dificultades u obstáculos:* Entender cómo detectar y propagar el acarreo en la suma de 32 bits dentro de la LC-3. Lo solucionamos monitoreando el bit 15 de los registros antes de la suma.
- *Plan para la siguiente sesión:* Entregar el Pull Request del Lab 3a y comenzar el algoritmo SQRT non-restoring en C++ para el Lab 3b.
