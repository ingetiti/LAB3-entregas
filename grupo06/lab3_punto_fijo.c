#include <stdio.h>
#include <stdint.h> // Necesaria para usar int16_t (entero de 16 bits)
#include <inttypes.h>

// Corrimiento aritmético a la derecha, también para valores negativos.
static int32_t corrimiento_derecha(int32_t valor, unsigned bits) {
    if (valor >= 0) {
        return valor >> bits;
    }
    return -1 - ((-1 - valor) >> bits);
}

// Verifica el resultado antes de convertirlo al entero de 16 bits del formato Q.
static void mostrar_resultado(const char *operacion, int32_t valor, int32_t escala) {
    if (valor < INT16_MIN || valor > INT16_MAX) {
        printf("%s: fuera de rango para el formato de salida.\n", operacion);
        return;
    }
    int16_t resultado = (int16_t)valor;
    printf("%s: %d -> Real: %g\n", operacion, (int)resultado, (double)resultado / escala);
}

int main(void) {
    // --- PUNTO 1: Declaración de variables e ingreso de datos en punto flotante ---
    float numero1;
    float numero2;

    // Ingreso del primer número (recomendado entre -8 y 7.99 para no desbordar Q3.12)
    printf("Ingrese el primer numero (use punto decimal): ");
    while (scanf("%f", &numero1) != 1) {
        if (feof(stdin) || ferror(stdin)) {
            return 1;
        }
        printf("Error: Entrada no valida. Ingrese un numero con punto decimal: ");
        int caracter;
        while ((caracter = getchar()) != '\n' && caracter != EOF) {
        }
    }

    // Ingreso del segundo número (recomendado entre -128 y 127.99 para no desbordar Q7.8)
    printf("Ingrese el segundo numero (use punto decimal): ");
    while (scanf("%f", &numero2) != 1) {
        if (feof(stdin) || ferror(stdin)) {
            return 1;
        }
        printf("Error: Entrada no valida. Ingrese un numero con punto decimal: ");
        int caracter;
        while ((caracter = getchar()) != '\n' && caracter != EOF) {
        }
    }

    if (!(numero1 >= -8.0f && numero1 <= 32767.0f / 4096.0f) ||
        !(numero2 >= -128.0f && numero2 <= 32767.0f / 256.0f)) {
        puts("Error: Un numero esta fuera del rango de su formato Q.");
        return 1;
    }

    // --- PUNTO 2: Conversión a Formato Q (Punto Fijo) ---

    // Convertimos numero1 a Q3.12
    // Multiplicamos por 4096 (que es 2^12) y hacemos casting a int16_t
    int16_t num1_Q3_12 = (int16_t)(numero1 * 4096.0f);

    // Convertimos numero2 a Q7.8
    // Multiplicamos por 256 (que es 2^8) y hacemos casting a int16_t
    int16_t num2_Q7_8 = (int16_t)(numero2 * 256.0f);

    // Mostramos los resultados
    printf("\n--- Resultados de la conversion ---\n");
    printf("Numero 1 original: %g -> Guardado en Q3.12 como: %d\n", numero1, num1_Q3_12);
    printf("Numero 2 original: %g -> Guardado en Q7.8 como: %d\n", numero2, num2_Q7_8);

    // --- PUNTO 3: Compatibilización de formatos y Suma/Resta ---

    // Convertimos num1 (Q3.12) a formato Q7.8
    // Operación utilizada: Desplazamiento de bits a la derecha (>>) en 4 posiciones.
    int32_t num1_convertido_a_Q7_8 = corrimiento_derecha(num1_Q3_12, 4);

    // Ahora que ambos números están en Q7.8, se pueden sumar y restar de forma directa
    int32_t suma_Q7_8 = num1_convertido_a_Q7_8 + num2_Q7_8;
    int32_t resta_Q7_8 = num1_convertido_a_Q7_8 - num2_Q7_8;

    printf("\n--- Punto 3: Suma y Resta (Formatos Compatibilizados) ---\n");
    mostrar_resultado("Suma (en Q7.8)", suma_Q7_8, 256);
    mostrar_resultado("Resta num1 - num2 (en Q7.8)", resta_Q7_8, 256);

    // --- PUNTO 4: Multiplicación y Ajuste de Formato ---

    // 1. Multiplicación cruda: Q3.12 * Q7.8 = Q10.20
    // Usamos int32_t (32 bits) para evitar desborde al multiplicar.
    int32_t mult_raw = (int32_t)num1_Q3_12 * (int32_t)num2_Q7_8;

    // 2. Ajuste: Conservar en Q7.8. Desplazamos 12 posiciones a la derecha.
    int32_t mult_Q7_8 = corrimiento_derecha(mult_raw, 12);

    printf("\n--- Punto 4: Multiplicacion ---\n");
    printf("Multiplicacion (cruda en Q10.20): %" PRId32 "\n", mult_raw);
    mostrar_resultado("Multiplicacion ajustada a Q7.8", mult_Q7_8, 256);

    // --- PUNTO 5: División conservando la mayor resolución posible ---

    // Elegimos el formato Q3.12 para mantener 12 bits fraccionarios en el resultado.
    // Sumamos 8 bits de ceros al numerador ANTES de dividir (desplazamiento a la izquierda).
    // En C, multiplicar por 256 aplica el mismo factor sin desplazar un entero negativo.
    int32_t num1_ampliado = (int32_t)num1_Q3_12 * 256;

    printf("\n--- Punto 5: Division ---\n");
    if (num2_Q7_8 == 0) {
        puts("Error: El divisor es cero en Q7.8.");
        return 1;
    }

    int32_t division_Q3_12 = num1_ampliado / num2_Q7_8;
    mostrar_resultado("Division ajustada a Q3.12", division_Q3_12, 4096);

    return 0;
}
