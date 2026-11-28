# Conversor de Decimal a Binario y Hexadecimal en LC-3

## Integrantes
- Garay, Carlos Ezequiel (@ezegaray14)
- Leopolino, Joaquín Fabián (@joakoleo)
- Pacheco, Agustin Santiago Ramón (@agusspachecoo)

## Sobre el proyecto

Este módulo contiene subrutinas de conversión diseñadas para integrarse como carga de trabajo (*workload*) en el banco de algoritmos (benchmark) del simulador LC-3. Su objetivo principal es recibir un valor numérico entero y generar su representación visual en consola en bases binaria y hexadecimal.

Para mantener la compatibilidad con la interfaz acordada con los demás grupos, el parseo y la lectura desde teclado quedan a cargo del menú principal del sistema. Las subrutinas principales (`SUB_BASE_BIN` y `SUB_BASE_HEX`) reciben el valor a convertir directamente como un entero de 16 bits en complemento a dos, a través del registro `R0`, justo al momento de ser invocadas.

El algoritmo que armamos prioriza una estructura iterativa compacta para ahorrar memoria:
- **Binario (`SUB_BASE_BIN`):** Itera exactamente 16 veces. En cada vuelta, se fija en el bit de signo (MSB), imprime el carácter ASCII ('0' o '1') usando `OUT`, y desplaza el acumulador una posición a la izquierda (`ADD R2, R2, R2`).
- **Hexadecimal (`SUB_BASE_HEX`):** Usa un bucle anidado. El de afuera itera 4 veces (una por cada dígito hexadecimal), y el de adentro itera otras 4 veces para ir acumulando los bits del *nibble* actual. Una vez que se tiene el valor del *nibble* (de 0 a 15), se le suma el valor correspondiente para obtener su código ASCII ('0'-'9' o 'A'-'F') y se imprime.

En ambas subrutinas nos aseguramos de guardar y restaurar el estado de la máquina en memoria (incluyendo el valor original de entrada) antes de ejecutar el `RET`, para no pisar registros de otras funciones.

## Interfaz de las Subrutinas

- **`SUB_BASE_BIN`**: 
  - **Entrada**: `R0` (Entero de 16 bits con signo).
  - **Salida**: Imprime en consola "Binario: " seguido de los 16 caracteres ('0' o '1') y un salto de línea.
  
- **`SUB_BASE_HEX`**: 
  - **Entrada**: `R0` (Entero de 16 bits con signo).
  - **Salida**: Imprime en consola "Hexadecimal: " seguido de los 4 caracteres ('0'-'9', 'A'-'F') y un salto de línea.

## Rango de valores aceptados

| Base de entrada | Formato admitido | Límites exactos |
|---|---|---|
| Interna (R0) | Entero en complemento a dos de 16 bits | `-32768` a `32767` |

Los valores numéricos se manejan siempre como patrones de 16 bits en complemento a dos. Por lo tanto, los valores desde `x8000` hasta `xFFFF` representan los números decimales negativos (de `-32768` a `-1`), mientras que de `x0000` a `x7FFF` cubren los positivos y el cero (de `0` a `32767`). 

## Formato punto fijo

Todo el sistema trabaja internamente con enteros de 16 bits en **complemento a dos**, usando formato **Q15.0**. Esto quiere decir que se toma como un número entero sin decimales: **1 bit de signo y 15 bits de magnitud**.

- El bit de más a la izquierda marca el signo: `0` para los positivos/cero y `1` para los negativos.
- Los 15 bits restantes dan el valor, expresando los negativos mediante el complemento a dos.
- Como no hay bits fraccionarios, el factor de escala es `2^0 = 1`. Básicamente, el número guardado en el registro es exactamente el valor que representa.

Este formato nos alcanza perfecto para cubrir el rango completo de `-32768` a `32767` y nos sirve como base común para hacer las conversiones.

## Rango de salida

La salida siempre respeta el tamaño fijo de 16 bits:

- **Binario:** Siempre imprime los 16 caracteres completos (de `0000000000000000` a `1111111111111111`), rellenando con ceros a la izquierda si hace falta.
- **Hexadecimal:** Imprime exactamente 4 dígitos en mayúsculas (de `0000` a `FFFF`), también conservando los ceros a la izquierda. El signo negativo ya está contemplado en el propio valor (cuando empieza con 8 o más).

Le agregamos una etiqueta adelante (`Binario: ` o `Hexadecimal: `) a cada salida para que quede claro en consola qué se está mostrando y mantenga un formato ordenado que permita comparar visualmente los resultados.

## Precisión

Como trabajamos puramente con aritmética entera de 16 bits y desplazamientos a nivel de bit, la conversión tiene **precisión absoluta**. No hay divisiones con decimales ni redondeos donde se pueda perder información. El valor exacto que entra en `R0` es el que se transforma bit a bit y se imprime en pantalla.