# Grupo 19 · Multiplicación

**Consigna:** Por CORDIC (Modo Lineal)

## Integrantes
- Javier, Santiago Lucas Nahuel (@lucasjavierr)
- Ruiz Diaz, Avril Aylin (@avrilruizdiaz)

## Archivos
Este proyecto implementa la multiplicación utilizando el algoritmo CORDIC en modo lineal, trabajando con números en punto fijo formato **Q7.8** (16 bits en complemento a 2).

- `CORDIC_multiplicacion_Q78.c`: Implementación matemática base en lenguaje C.
- `CORDIC_pensado_assembly.c`: Implementación en C adaptada a las limitaciones del procesador LC-3. No utiliza multiplicaciones, divisiones ni corrimientos nativos, y simula el uso de registros de 32 bits mediante estructuras de dos palabras de 16 bits.
- `CORDIC_mul.asm`: Programa completo en ensamblador para LC-3 que ejecuta el algoritmo CORDIC lineal clásico.
- `CORDIC_mul_horner.asm`: Programa optimizado en ensamblador para LC-3 usando la variante de Horner. Evita los costosos desplazamientos de bits a la derecha, sustituyéndolos por sumas (duplicaciones).

## Cómo funciona
El programa recibe dos factores por teclado y calcula su producto. Debido a que el procesador LC-3 no posee unidad de punto flotante, se utiliza el formato Q7.8 para representar decimales. 
Para convertir un número real a Q7.8, se debe multiplicar por 256. 
*   **Ejemplo:** `2.0` se ingresa como `512`. `3.25` se ingresa como `832`.
El resultado devuelto también estará en formato Q7.8 (para obtener el valor real, se debe dividir el resultado entre 256).

**Nota de rango:** El formato Q7.8 en 16 bits soporta valores entre `-32768` y `32767`. Por lo tanto, el resultado máximo que puede almacenar el producto real es aproximadamente `127.996`. Si la multiplicación supera este valor, el programa detectará el desbordamiento.

## Cómo probarlo
Los archivos `.asm` están preparados para ejecutarse en cualquier simulador de LC-3 (por ejemplo, [lc3.lgrum.xyz](https://lc3.lgrum.xyz/)).

### Pasos para la ejecución:
1. Copia el código de `CORDIC_mul_horner.asm` (o `CORDIC_mul.asm`) en el simulador y presiona el botón **Assemble**.
2. Inicia la ejecución presionando **Run**. *(Recomendación: asegúrate de que la velocidad de ejecución o "Execution Speed" esté configurada al máximo).*
3. Haz clic directamente dentro de la **consola de texto** (el recuadro negro) del simulador para que registre tu teclado.
4. **Ingreso del Primer Factor:** Escribe el número convertido a Q7.8 (ej: `512` para representar 2.0) y presiona la tecla **Enter**.
5. **Ingreso del Segundo Factor:** Escribe el segundo número (ej: `768` para representar 3.0) y vuelve a presionar **Enter**.
6. **Lectura del resultado:** Si estás usando el simulador web, la consola es pequeña y el resultado suele quedar oculto arriba. **Haz scroll (desplázate hacia arriba)** dentro de la consola negra para poder leer la línea que dice: `Resultado en formato Q7.8: 1536`.

### Ejemplos de prueba rápida:
*   **2.0 x 3.0 = 6.0**
    *   Ingresar: `512` [Enter] y `768` [Enter]
    *   Salida esperada: `1536`
*   **-2.5 x 2.0 = -5.0**
    *   Ingresar: `-640` [Enter] y `512` [Enter]
    *   Salida esperada: `-1280`
*   **Caso de Desbordamiento (ej. 10.0 x 15.0 = 150.0)**
    *   Ingresar: `2560` [Enter] y `3840` [Enter]
    *   Salida esperada: `DESBORDAMIENTO: no entra en Q7.8`