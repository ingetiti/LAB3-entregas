#include <stdint.h>
#include <stdio.h>

int main(void) {
    double numero1;
    double numero2;
    int16_t numero1Q3_12;
    int16_t numero2Q7_8;
    int32_t dividendoExtendido;
    int32_t cocienteQ3_12;
    int16_t resultadoFinal;

    printf("Ingrese el dividendo (rango [-8.0, 8.0) para Q3.12): ");
    if (scanf("%lf", &numero1) != 1) {
        printf("Entrada no valida.\n");
        return 1;
    }

    printf("Ingrese el divisor (rango [-128.0, 128.0) para Q7.8, distinto de 0): ");
    if (scanf("%lf", &numero2) != 1) {
        printf("Entrada no valida.\n");
        return 1;
    }

    if (numero2 == 0.0) {
        printf("Error: Division por cero no permitida.\n");
        return 1;
    }

    /* Validacion de limites segun formato */
    if (numero1 < -8.0 || numero1 >= 8.0) {
        printf("El dividendo esta fuera de rango para Q3.12.\n");
        return 1;
    }

    if (numero2 < -128.0 || numero2 >= 128.0) {
        printf("El divisor esta fuera de rango para Q7.8.\n");
        return 1;
    }

    /* Conversion a formatos Q iniciales */
    numero1Q3_12 = (int16_t)(numero1 * 4096.0); // 1 << 12
    numero2Q7_8  = (int16_t)(numero2 * 256.0);  // 1 << 8

    if (numero2Q7_8 == 0) {
        printf("Error: El divisor en formato Q7.8 se redondeo a 0 (underflow).\n");
        return 1;
    }

    /*
     * Division (Punto 5):
     * Formato elegido para el resultado: Q3.12 (12 bits fraccionarios).
     * Para que (Dividendo / Divisor) tenga 12 bits fraccionarios,
     * el dividendo debe tener internamente: 12 + 8 = 20 bits fraccionarios.
     * Como numero1Q3_12 ya tiene 12 bits fraccionarios, lo desplazamos 8 bits a la izquierda.
     */
    dividendoExtendido = ((int32_t)numero1Q3_12) << 8;

    /* Realizamos la division entera con signo */
    cocienteQ3_12 = dividendoExtendido / numero2Q7_8;

    printf("\n--- Detalle de la Division en Punto Fijo ---\n");
    printf("Dividendo en Q3.12:  entero = %d | real = %.6f\n", 
           (int)numero1Q3_12, (double)numero1Q3_12 / 4096.0);
    printf("Divisor en Q7.8:     entero = %d | real = %.6f\n", 
           (int)numero2Q7_8, (double)numero2Q7_8 / 256.0);
    printf("Dividendo escalado en 32 bits (Q11.20): %ld\n", (long)dividendoExtendido);

    /* Verificacion de rango para 16 bits en formato Q3.12 [-8.0, 8.0) */
    if (cocienteQ3_12 < INT16_MIN || cocienteQ3_12 > INT16_MAX) {
        printf("Error de Overflow: El cociente excede el rango de representacion en Q3.12 [-8.0, 8.0).\n");
    } else {
        resultadoFinal = (int16_t)cocienteQ3_12;
        printf("Resultado en formato Q3.12:\n");
        printf("  - Entero almacenado: %d\n", (int)resultadoFinal);
        printf("  - Valor decimal reconstruido: %.6f\n", (double)resultadoFinal / 4096.0);
        printf("  - Valor teorico flotante esperado: %.6f\n", numero1 / numero2);
    }

    return 0; // Colocar breakpoint aqui para inspeccionar variables
}