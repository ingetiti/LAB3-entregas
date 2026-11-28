# Grupo 04 · POW

**Consigna:** Exponenciación binaria

## Integrantes
<!-- Completar en el primer Pull Request -->
- Villalba, Agustin (@AgustinV16)
- SARI FERNÁNDEZ, Maximiliano Gastón (@usuario-github)
- SOLIS, Carlos Esteban (@usuario-github)

## Archivos
<!-- Qué archivo hace qué -->
#### Lab 3-b
- `potencia.asm`: Codigo correspondiente a la exponenciacion binaria en Assembly
- `expo_b.c`: Codigo correspondiente a la exponenciacion binaria en lenguaje de alto nivel (C)

#### Lab 3-a
- `formatoQ.c`: Codigo correspondiente a la transformacion de formatos Q3.12 a Q7.8 en lenguaje de alto nivel (C)
- `formato.asm`: Codigo correspondiente a la transformacion de formatos Q3.12 a Q7.8 en Assembly

## Cómo probarlo
<!-- Pasos para ensamblar y ejecutar, y un ejemplo de entrada y salida -->
La implementación en Assembly se encuentra funcionando y publicado en el simulador desarrollado por el Grupo 8.

El porgrama se llama correctamente como subrutina y utiliza los registro R0 y R1 como base y exponente, respectivamente.

Para poder cargar el programa se deben seguir los pasos indicados por el grupo 27.

### Formatos de punto fijo
- Entrada: Q15, con signo y 16 bits.
- Salida: Q15, con signo y 16 bits.

### Rangos de valores
- Entrada: 
    - Base: [-32,768 ; +32,767].
    
    - Exponente: $$E_{\max} = \lfloor \log_{\vert{}B\vert{}} (32\,767) \rfloor$$
- Salida: [-32,768 ; +32,767].

### Resolución de los formatos
La resolución indica cuál es el menor incremento que puede representarse entre dos valores consecutivos. Se calcula dividiendo 1 por 2 elevado a la cantidad de bits destinados a la parte fraccionaria.

El tratarse de numeros enteros la resolucion es de 1.

## Bitácora de desarrollo

### 7 de octubre de 2026 – Inicio del laboratorio
Comenzamos por trabajar en el Lab 3a referido a los formatos de punto fijo.

### 14 de octubre de 2026 – Asignación
Se nos asignó la implementación de la función de Exponenciación Binaria (exponenciación rápida por cuadrados sucesivos) en lenguaje Assembly para la LC-3.
A partir de esta asignación comenzamos a investigar la lógica del algoritmo para reducir la complejidad temporal de $O(E)$ a $O(\log_2 E)$.
El principal desafío consistió en adaptar el algoritmo a las limitaciones del procesador: calcular la potencia de una base entera (incluyendo bases negativas) con un exponente entero no negativo, controlando la paridad del exponente y gestionando el signo final mediante complemento a dos (NOT y +1) sin utilizar subrutinas complejas de división de punto fijo.

### 28 de octubre de 2026 – Organización del trabajo con Git y GitHub
Creamos nuestras cuentas de Git y GitHub para organizar el control de versiones del proyecto y subir los archivos correspondientes.
Esto nos permitió estructurar el código fuente en Assembly (.asm), los scripts de simulación y el informe explicativo, garantizando la trazabilidad de los cambios realizados.

### 29 de octubre de 2026 – Finalización del proyecto e informe
Trabajamos en la finalización del código en ensamblador y en la redacción del informe técnico.
En esta etapa documentamos detalladamente la estructura de los bucles lógicos (LOOP_W, M_LOOP1, D_LOOP y M_LOOP2), el tratamiento de la paridad mediante máscaras de bits (AND), la conversión del signo de la base a positivo temporal para operar, y la saturación/guardado del resultado final en la celda FINAL_RES.
También analizamos la precisión matemática del algoritmo, verificando que opera con 0 LSB de error al tratarse de aritmética entera exacta Q15.0.

### 1 de noviembre de 2026 – Verificación de compatibilidad y rangos
Realizamos pruebas de validación sobre el rango de datos aceptado por nuestro algoritmo. Confirmamos que la base puede ser cualquier entero de 16 bits en complemento a dos y el exponente debe ser un entero no negativo ($E \ge 0$).
Comprobamos los límites de desbordamiento de 16 bits (rango $[-32\,768, 32\,767]$) y verificamos casos de prueba clave como $(-2)^{13} = -8192$ (xE000 en memoria).

### 2 de noviembre de 2026 – Optimización de registros y simulación
Nos enfocamos en depurar y optimizar el rendimiento del código Assembly. Eliminamos todos los accesos innecesarios a memoria RAM dentro de los bucles críticos, manteniendo las banderas de signo y paridad directamente en los registros $R_5$ y $R_6$.
Verificamos que la rutina ejecutara únicamente 1 acceso a memoria al finalizar la computación (ST R3, FINAL_RES), maximizando la velocidad de procesamiento en el simulador LC-3.

### 3 de noviembre de 2026 – Depuración autónoma del programa
Dedicamos la jornada a revisar exhaustivamente la traza de ejecución de los registros ($R_0$ a $R_6$) paso a paso durante la exponenciación binaria.
Verificamos el conteo de instrucciones promedio ($\approx 180$ instrucciones para el caso de prueba $(-2)^{13}$) y aseguramos que el programa finalizara correctamente mediante la instrucción HALT sin dejar bucles infinitos ni estados inconsistentes.

### 4 de noviembre de 2026 – Revisión final del proyecto
Realizamos la comprobación final de todos los componentes del trabajo: la exactitud del código Assembly frente a las especificaciones del TP, la coherencia de la documentación del informe y la correcta compilación en el entorno de prueba.

### 6 de noviembre de 2026 – Presentación del LABORATORIO 3
Realizamos la carga de los archivos correspondientes a nuestro grupo en el repositorio de GitHub.

### 9 de noviembre de 2026 - Correccion ERROR Subrutina
Recibimos una devolucion del primer codigo. Este no respetaba las restricciones de diseño del grupo 8.
Se adapto todo el codigo para respetar esta estructura. Conservando correctamente los estados de los registros sin modificar nada y devolviendo el resultado en R0.
