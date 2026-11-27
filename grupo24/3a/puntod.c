#include <stdint.h>
#include <stdio.h>

int main(void) {
    double numero1;
    double numero2;
    int16_t numero1Q3_12;
    int16_t numero2Q7_8;
    int32_t productoIntermedio;
    int32_t productoAjustado;
    int16_t resultadoFinalQ7_8;

    printf("Ingrese el primer numero (rango [-8.0, 8.0) para Q3.12): ");
    if (scanf("%lf", &numero1) != 1) {
        printf("Entrada no valida.\n");
        return 1;
    }

    printf("Ingrese el segundo numero (rango [-128.0, 128.0) para Q7.8): ");
    if (scanf("%lf", &numero2) != 1) {
        printf("Entrada no valida.\n");
        return 1;
    }

    /* Validacion de limites de entrada */
    if (numero1 < -8.0 || numero1 >= 8.0) {
        printf("El primer numero esta fuera de rango para Q3.12.\n");
        return 1;
    }

    if (numero2 < -128.0 || numero2 >= 128.0) {
        printf("El segundo numero esta fuera de rango para Q7.8.\n");
        return 1;
    }

    /* Conversion de flotante a representacion Q (Punto 2) */
    numero1Q3_12 = (int16_t)(numero1 * 4096.0); // 1 << 12
    numero2Q7_8  = (int16_t)(numero2 * 256.0);  // 1 << 8

    /* 
     * Multiplicacion (Punto 4):
     * Al multiplicar (A * 2^12) * (B * 2^8) obtenemos (A * B) * 2^20.
     * Es obligatorio operar en 32 bits (int32_t) para evitar overflow.
     */
    productoIntermedio = (int32_t)numero1Q3_12 * (int32_t)numero2Q7_8;

    /*
     * Ajuste de formato:
     * El formato destino elegido es Q7.8 (8 bits fraccionarios).
     * Como el producto intermedio tiene 20 bits fraccionarios,
     * debemos descartar 12 bits de fraccion (20 - 8 = 12).
     * Se realiza mediante un desplazamiento aritmetico a la derecha: >> 12
     * (o division entera por 2^12 = 4096).
     */
    productoAjustado = productoIntermedio >> 12;

    printf("\n--- Detalle de la Multiplicacion ---\n");
    printf("Operando 1 en Q3.12:  entero = %d | real = %.6f\n", 
           (int)numero1Q3_12, (double)numero1Q3_12 / 4096.0);
    printf("Operando 2 en Q7.8:   entero = %d | real = %.6f\n", 
           (int)numero2Q7_8, (double)numero2Q7_8 / 256.0);
    printf("Producto intermedio (formato Q10.20): %ld\n", (long)productoIntermedio);

    /* Verificacion de rango para 16 bits */
    if (productoAjustado < INT16_MIN || productoAjustado > INT16_MAX) {
        printf("Error: El resultado ajustado (%ld) desborda el rango de 16 bits en Q7.8 [-128, 128).\n", 
               (long)productoAjustado);
    } else {
        resultadoFinalQ7_8 = (int16_t)productoAjustado;
        printf("Resultado ajustado a Q7.8:\n");
        printf("  - Entero almacenado: %d\n", (int)resultadoFinalQ7_8);
        printf("  - Valor decimal reconstruido: %.6f\n", (double)resultadoFinalQ7_8 / 256.0);
        printf("  - Valor teorico flotante esperado: %.6f\n", numero1 * numero2);
    }

    return 0; // Colocar breakpoint aqui para inspeccionar variables en ZinjaI
}