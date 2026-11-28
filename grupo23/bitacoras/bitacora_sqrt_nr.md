# Bitácora de Investigación - Grupo 23 (Laboratorio 3b: SQRT Non-Restoring)
- Tema asignado: SQRT (raíz cuadrada) por el método non-restoring.
- Alto nivel: el algoritmo se desarrolló en C++ (ZinjaI) y (Visual Studio Code).
- Bajo nivel: assembly de la ISA LC-3, ejecutado y depurado en el simulador de la LC-3.
- Control de versiones: Git y GitHub, sobre el fork del repositorio de la cátedra (carpetas grupo23/alto_nivel y grupo23/asm).

## Sesión 1
- *Fecha y hora:* 07/10/2026 - 18:00 hs a 20:15 hs
- *Objetivo del día:* Conocer el tema asignado al grupo y entender qué calcula el algoritmo SQRT non-restoring antes de implementarlo.
- *Actividades realizadas:* 
  - Sorteo de los temas del laboratorio entre los grupos: al Grupo 23 le tocó la raíz cuadrada por el método non-restoring.
  - Revisión de lo que pide la consigna para el análisis en alto nivel: funcionamiento del algoritmo, número de iteraciones, formato de punto fijo, rango y precisión.
  - Búsqueda de información sobre el algoritmo: qué objetivo tiene, cómo funciona y en qué se diferencia del método restoring.
- *Observaciones y hallazgos:* Es un método dígito a dígito que calcula la raíz cuadrada usando solamente sumas, restas y corrimientos, sin multiplicar ni dividir; esto resulta conveniente para la LC-3, que no tiene instrucciones de multiplicación ni de corrimiento. En cada iteración se incorporan dos bits del radicando y se obtiene un bit de la raíz. Cuando el resto parcial da negativo, el método restoring lo restaura sumando lo que se restó; el non-restoring conserva el resto negativo y en la iteración siguiente suma en lugar de restar, evitando ese paso extra.
- *Dificultades u obstáculos:* Comprender por qué conservar el resto negativo, en lugar de restaurarlo, no altera el resultado final.
- *Plan para la siguiente sesión:* Analizar el algoritmo en C++, depurarlo y verificar su funcionamiento.

## Sesión 2
- *Fecha y hora:* 21/10/2026 - 18:00 hs a 19:45 hs
- *Objetivo del día:* Implementar el algoritmo en un lenguaje de alto nivel para depurarlo, estudiarlo y entenderlo antes de pasar a assembly, como indica la consigna.
- *Actividades realizadas:* 
  - Análisis de cómo plantear el algoritmo non-restoring en C++ y escritura del código.
  - Ejecución y depuración paso a paso, siguiendo en cada iteración el valor del resto, de la raíz y de los dos bits incorporados del radicando.
  - Verificación de los resultados con distintos valores de entrada.
  - Desarrollo del código, una en C++ (ZinjaI) y otra en (Visual Studio Code).
- *Observaciones y hallazgos:* El algoritmo necesita una iteración por cada par de bits del radicando. Para cumplir con la consigna de punto fijo, definimos trabajar con 13 iteraciones ($k=13$). Al cargar la entrada (en formato Q7.8) en la mitad alta del registro, logramos ganar bits fraccionarios automáticamente, obteniendo el resultado en formato Q6.9. El límite de 13 iteraciones se eligió porque es el máximo posible antes de que el resto parcial desborde el límite de 16 bits con signo de la LC-3.
- *Dificultades u obstáculos:* Se trabajó con lenguajes y entornos distintos, por lo que hubo que definir cuál de las dos versiones se tomaba como base para pasar a assembly.
- *Plan para la siguiente sesión:* Pasar a assembly de la LC-3 el algoritmo verificado en C++ y comprobar que funcione correctamente.

## Sesión 3
- *Fecha y hora:* 21/10/2026 - 19:45 hs a 20:15 hs
- *Objetivo del día:* Compartir el avance de los algoritmos con otros grupos y establecer criterios de integración para los módulos del simulador LC-3.
- *Actividades realizadas:* 
  - Puesta en común del análisis de los algoritmos en alto nivel (C++) con los demás equipos de laboratorio.
  - Análisis de los requisitos para la futura subida de los algoritmos como módulos en la página del simulador de la cátedra.
  - Relación de los desafíos del trabajo práctico con los contenidos teóricos de arquitectura vistos en clase.
- *Observaciones y hallazgos:* Se evidenció que conocer cómo se están desarrollando las distintas funciones es vital. Comprendimos la importancia fundamental de establecer criterios comunes de desarrollo para garantizar que todos los programas puedan integrarse correctamente sin conflictos de interfaz.
- *Dificultades u obstáculos:* Dificultades u obstáculos: Ninguna significativa en esta sesión.
- *Plan para la siguiente sesión:* Contactar a los grupos con temáticas afines (como SQRT Newton-Raphson) para unificar y definir los formatos numéricos de punto fijo.

## Sesión 4
- *Fecha y hora:* 22/10/2026 - 15:15 hs a 15:25 hs
- *Objetivo del día:* Coordinar los formatos de punto fijo con el Grupo 9 (encargado de SQRT Newton-Raphson) para asegurar la compatibilidad del sistema.
- *Actividades realizadas:* 
  - Comunicación directa con los integrantes del Grupo 9 para consultar qué formatos de punto fijo estaban utilizando en su algoritmo.
  - Intercambio de información sobre cómo cada equipo resolvió la representación de los números reales en la arquitectura.
- *Observaciones y hallazgos:* Confirmamos que mantener una compatibilidad estricta entre las funciones matemáticas que formarán parte del mismo sistema central es un paso crítico antes de codificar la versión final en Assembly.
- *Dificultades u obstáculos:* Ninguna significativa en esta sesión.
- *Plan para la siguiente sesión:* Retomar el trabajo de código para pasar a assembly de la LC-3 el algoritmo SQRT non-restoring, aplicando los criterios de formato acordados.

## Sesión 5
- *Fecha y hora:* 28/10/2026 - 18:00 hs a 19:50 hs
- *Objetivo del día:* Pasar a assembly de la LC-3 el algoritmo ya verificado en C++ y comprobar que funcione correctamente.
- *Actividades realizadas:* 
  - Planificación del uso de los registros de la LC-3 para el radicando, la raíz, el resto y el contador de iteraciones.
  - Codificación de la rutina SQRT non-restoring en assembly de la LC-3.
  - Ejecución y depuración del programa en el simulador de la LC-3.
  - Comparación de los resultados del assembly con los de la versión en C++ para los mismos valores de entrada; los resultados coincidieron en todos los casos.
- *Observaciones y hallazgos:* La LC-3 no tiene instrucciones de multiplicación ni de corrimiento, por lo que los desplazamientos que pide el algoritmo (multiplicar por 2 o por 4 el resto y la raíz) se resuelven sumando un registro consigo mismo. Contar con el código en C++ ya verificado sirvió como referencia para validar el resultado del assembly.
- *Dificultades u obstáculos:* La LC-3 no tiene instrucción de resta, por lo que las restas del algoritmo se resolvieron con complemento a dos (NOT, sumar 1 y luego sumar). Además, como no hay instrucciones de corrimiento, para extraer los bits del radicando utilizamos el truco de evaluar su signo (bit 15) mediante un ADD con cero y saltos condicionales, sumando luego el registro consigo mismo para desplazarlo a la izquierda.
- *Plan para la siguiente sesión:* Subir al repositorio los códigos de C++ y assembly, ya verificados.

## Sesión 6
- *Fecha y hora:* 28/10/2026 - 20:00 hs a 20:15 hs 
- *Objetivo del día:* Acordar los parámetros de integración de los programas con el grupo encargado de la interfaz principal.
- *Actividades realizadas:*
  - Comunicación con el Grupo 27, encargado del desarrollo de la interfaz de la calculadora.
  - Planificación de la arquitectura de integración para acoplar los distintos programas desarrollados por cada grupo.
  - Establecimiento de acuerdos sobre los registros específicos que utilizaríamos y los formatos numéricos que debíamos respetar para que las funciones pudieran comunicarse correctamente.
- *Observaciones y hallazgos:* Definir anticipadamente el uso de los registros y los formatos de punto fijo es un paso fundamental, ya que garantiza que las funciones matemáticas operen correctamente con el menú central sin generar errores de incompatibilidad ni corromper los datos del sistema.
- *Dificultades u obstáculos:* Coordinar los estándares de desarrollo e interfaces con el otro equipo.
- *Plan para la siguiente sesión:* Subir al repositorio del grupo los códigos (C++ y assembly) actualizados y prepararlos para la prueba de integración final.

## Sesión 7
- *Fecha y hora:* 06/11/2026 - 18:30 hs a 20:00 hs
- *Objetivo del día:* Subir al repositorio del grupo los códigos de SQRT non-restoring (C++ y assembly) una vez confirmado que funcionan correctamente.
- *Actividades realizadas:* 
  - Revisión final de ambos códigos antes de subirlos.
  - Subida de los archivos de C++ y de assembly al fork del repositorio de la cátedra, en las carpetas grupo23/alto_nivel y grupo23/asm creadas.
- *Observaciones y hallazgos:* Como el fork y la estructura de carpetas ya estaban configurados, solo fue necesario sumar los archivos. Subir el código recién después de verificarlo mantiene un historial limpio y permite volver atrás si una actualización posterior rompe el funcionamiento. Con esto, la rutina queda disponible para integrarse al benchmark junto con las de los demás grupos.
- *Dificultades u obstáculos:* Ninguna significativa en esta sesión.
- *Plan para la siguiente sesión:* Coordinar con los demás grupos la integración de la rutina al benchmark y preparar el informe y la defensa oral (15 minutos) del Laboratorio 3.

## Sesión 8
- *Fecha y hora:* 09/11/2026 - 18:30 hs a 20:00 hs
- *Objetivo del día:* Coordinar y aplicar actualizaciones al código Assembly para cumplir estrictamente con los requerimientos e interfaz del Grupo 27.
- *Actividades realizadas:* 
  - Coordinación de cambios estructurales en el código .asm.
  - Actualización de la subrutina para que reciba el radicando exclusivamente en R0 (formato Q7.8) y devuelva el resultado en R0 (formato Q6.9).
  - Implementación de la gestión autónoma de registros internos mediante instrucciones de resguardo (ST y LD), evitando interferencias con el entorno principal. 
- *Observaciones y hallazgos:* Al independizar los registros, la subrutina se comporta como una caja negra segura y lista para ser llamada desde cualquier controlador de menú sin efectos colaterales.
- *Dificultades u obstáculos:* Asegurar la compatibilidad exacta de la interfaz de registros con los parámetros esperados por la calculadora general.
- *Plan para la siguiente sesión:*  Probar la integración real del código actualizado en la plataforma de simulación web lc3.lgrum.xyz.

## Sesión 9
- *Fecha y hora:* 10/11/2026 - 08:30 hs a 10:15 hs
- *Objetivo del día:* Verificar el funcionamiento del nuevo código Assembly en el simulador web y presentarlo ante el jefe de la cátedra.
- *Actividades realizadas:* 
  - Verificación y corroboración del correcto funcionamiento de la rutina actualizada en lc3.lgrum.xyz.
  - Presentación de la actualización ante el Ing. Carballo (ante la ausencia temporal de la tutora Ing. Patricia Feltan), obteniendo su visto bueno y la directiva de subirlo como módulo.
  - Realización de una puesta en común con un integrante del Grupo 10 sobre el uso y comportamiento de los módulos en la plataforma.
  - Pruebas iniciales de integración utilizando el archivo main.asm y el menú principal provisto por el Grupo 27.
  - Publicación de la primera versión (v1) del archivo modulo_sqrt_nr.asm en la plataforma mediante el botón "PUBLICAR", siguiendo la indicación del Ing. Carballo.
- *Observaciones y hallazgos:* El Ing. Carballo validó el progreso y orientó sobre el proceso formal de subida en la plataforma. La interacción con otros grupos facilitó el intercambio de experiencias sobre las herramientas del simulador.
- *Dificultades u obstáculos:* Ninguna significativa en esta sesión.
- *Plan para la siguiente sesión:* Configurar correctamente y resolver los requerimientos de sintaxis del enlazador web.

## Sesión 10
- *Fecha y hora:* 10/11/2026 - 17:30 hs a 18:15 hs
- *Objetivo del día:* Ejecutar pruebas funcionales de punta a punta en la consola de la calculadora con el módulo ya publicado en el simulador.
- *Actividades realizadas:* 
  - Pruebas de ejecución interactiva en la pestaña Consola, navegando al menú de raíz cuadrada y seleccionando la opción correspondiente.
  - Autenticación en la plataforma utilizando las credenciales asignadas al Grupo 23.
  - Verificación de la versión publicada del archivo modulo_sqrt_nr.asm en el servidor web.
  - Localización definitiva del módulo publicado dentro del apartado "Otros grupos" de la plataforma, confirmando su disponibilidad global para el proyecto.
- *Observaciones y hallazgos:* La calculadora presentó errores de cálculos, se verificó nuevamente el código asm pero al parecer es error del main.
- *Dificultades u obstáculos:* Presunto error de cálculos ya que al calcular la raíz de 12 arroja 12,23 como resultado.
- *Plan para la siguiente sesión:* Solucionar el inconveniente de cálculos, preparar el informe del Laboratorio 3 y ultimar los detalles del lab3 "b" para continuar con el lab3 "c".

## Sesión 11
- *Fecha y hora:* 11/11/2026 - 17:15 hs a 18:15 hs
- *Objetivo del día:* Solucionar el error de visualización en consola y estructurar la futura defensa oral del Laboratorio 3.
- *Actividades realizadas:* 
  - Análisis de resultados de integración en el simulador web de la LC-3 (lc3.lgrum.xyz).
  - Verificación de cálculos en pantalla: al realizar la raíz cuadrada de 12, la consola ahora arroja el resultado correcto de 3.46 aproximadamente.
  - Confirmación de que el Grupo 27 actualizó el código del menú principal, solucionando el problema de compatibilidad en la impresión.
  - Estructuración de la presentación de 15 minutos para la defensa oral junto al Grupo 9.
- *Observaciones y hallazgos:* Se confirmó que nuestra subrutina siempre operó de manera correcta a nivel matemático. El error previo se debía exclusivamente a que la interfaz no estaba preparada para imprimir nuestro resultado en formato Q6.9. Con la actualización del main, nuestra caja negra funciona y se comunica a la perfección con el resto del sistema.
- *Dificultades u obstáculos:* Ninguna significativa en esta sesión. El módulo ya se encuentra estable y 100% funcional.
- *Plan para la siguiente sesión:* Seguir trabajando en el laboratorio y prepararnos para la futura defensa ante la cátedra.