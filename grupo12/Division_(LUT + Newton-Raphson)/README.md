# Grupo 12 · División

**Consigna:** Por LUT + reducción de rango e interpolación por Newton-Raphson

## Integrantes
<!-- Completar en el primer Pull Request -->
- Dose Rivarola, Agustín Ezequiel (@doseagustin)
- Radovitzky Z S, Gonzalo (@tzAnT00)
- Miller, Enrique Adrian (@enriquemiller2007-bit)

## Archivos
<!-- Qué archivo hace qué -->
- `div_newton.asm`: Contiene la subrutina principal `DIV_NEWTON`, el bloque lógico de signos, y la subrutina interna `MULT_MODULO` de 32 bits.
Todo el código está adaptado como módulo Callee-Saved puro (preservando R7 y sin utilizar R6) para acoplarse a la interfaz del Grupo 27.

## Cómo probarlo
<!-- Pasos para ensamblar y ejecutar, y un ejemplo de entrada y salida -->
Al estar estructurado como subrutina, espera que los datos ya estén cargados en los registros correspondientes. 
Para probarlo de forma aislada en el simulador, se debe inyectar un "Test Bench" (un programa principal con `.ORIG`)
justo por encima del código que cargue los registros y haga el llamado por ejemplo:

```assembly
.ORIG x3000
    ; --- PROGRAMA PRINCIPAL DE PRUEBA (TEST BENCH) ---
    LD R0, VALOR_A
    LD R1, VALOR_B
    
    JSR DIV_NEWTON
    
    ST R0, RESULTADO_FINAL
    HALT

    ; Variables para el Test Bench
    VALOR_A         .FILL x0C00     ; 12.0 en Q7.8
    VALOR_B         .FILL x0600     ; 6.0 en Q7.8
    RESULTADO_FINAL .BLKW #1
```

**Ejemplo de entrada y salida:**
1. Cargar el Dividendo en formato Q7.8 en el registro `R0` (Ejemplo: `x0C00` para `12.0`).
2. Cargar el Divisor en formato Q7.8 en el registro `R1` (Ejemplo: `x0600` para `6.0`).
3. Ejecutar el salto a la subrutina mediante `JSR DIV_NEWTON`.
4. El programa procesará el signo, reducirá el rango, calculará por Newton-Raphson y desnormalizará.
5. El resultado final se alojará en el registro `R0` (Ejemplo: `x0200` para `2.0`).

## Especificaciones Técnicas
*   **Formato de Punto Fijo:** Las entradas (`R0`, `R1`) y la salida (`R0`) operan estrictamente en formato **Q7.8** (1 bit de signo, 7 bits enteros, 8 bits fraccionarios).
Durante la iteración matemática, el núcleo escala a **Q3.12** para no perder resolución en los productos.
*   **Rango de Valores:** La función procesa correctamente dividendos y divisores en el rango de [-128.0, +127.996] (rango máximo del formato Q7.8 en 16 bits).
*   **Precisión Alcanzada:** $0.003906$ (peso matemático del bit menos significativo en la porción fraccionaria).

## Bitácora de Avances
*   **Fase 1: Prototipado y Formatos:** Análisis de la iteración de Newton-Raphson y definición de los formatos de punto fijo (Q7.8 externo y Q3.12 interno).
*   **Fase 2: Reducción de Rango:** Implementación en assembly de una búsqueda dinámica del bit más significativo (MSB) para acotar cualquier divisor ingresado a la ventana
 segura de convergencia `[0.5, 1.0)`.
*   **Fase 3: Resolución de Overflow (16 bits):** Desarrollo de una subrutina propia de multiplicación (*Shift-and-Add*) a 32 bits.
  Esto resolvió el problema de desbordamiento de registros que ocurría al multiplicar valores Q3.12 antes de la desnormalización.
*   **Fase 4: Adaptación Arquitectónica:** Migración del código a una subrutina *Callee-Saved* estricta. Se purgó el uso del registro `R6`
  (para evitar conflictos de Stack Pointer con las interrupciones del simulador del Grupo 8) y se implementó el resguardo seguro del `R7` en memoria.
*   **Fase 5: Lógica de Signos:** Incorporación de una rutina inicial de Valor Absoluto mediante "Complemento a 2" y un seguimiento de bandera con máscara XOR.
  Esto permite que el algoritmo soporte divisiones con números negativos mientras la matemática de interpolación opera de forma segura con valores positivos.
