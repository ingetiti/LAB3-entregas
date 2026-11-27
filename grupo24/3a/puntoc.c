#include <stdint.h>
#include <stdio.h>

int main(void) {
	double numero1;
	double numero2;
	int16_t numero1Q3_12;
	int16_t numero1Q7_8;
	int16_t numero2Q7_8;
	int32_t suma;
	int32_t resta;

	printf("Ingrese el primer numero (se codificara en Q3.12): ");
	if (scanf("%lf", &numero1) != 1) {
		printf("Entrada no valida.\n");
		return 1;
	}

	printf("Ingrese el segundo numero (se codificara en Q7.8): ");
	if (scanf("%lf", &numero2) != 1) {
		printf("Entrada no valida.\n");
		return 1;
	}

	if (numero1 < -8.0 || numero1 >= 8.0) {
		printf("El primer numero esta fuera del rango de Q3.12 [-8, 8).\n");
		return 1;
	}

	if (numero2 < -128.0 || numero2 >= 128.0) {
		printf("El segundo numero esta fuera del rango de Q7.8 [-128, 128).\n");
		return 1;
	}

	numero1Q3_12 = (int16_t)(numero1 * 4096.0);
	numero2Q7_8 = (int16_t)(numero2 * 256.0);

	/* Q3.12 a Q7.8: descartar 4 bits fraccionarios dividiendo por 2^4. */
	numero1Q7_8 = (int16_t)(numero1Q3_12 / 16);

	suma = (int32_t)numero1Q7_8 + numero2Q7_8;
	resta = (int32_t)numero1Q7_8 - numero2Q7_8;

	printf("\nPrimer valor en Q3.12: %d\n", (int)numero1Q3_12);
	printf("Primer valor convertido a Q7.8: %d (aprox. %.6f)\n",
	       (int)numero1Q7_8, (double)numero1Q7_8 / 256.0);
	printf("Segundo valor en Q7.8: %d\n", (int)numero2Q7_8);

	if (suma < INT16_MIN || suma > INT16_MAX) {
		printf("La suma excede el rango representable en Q7.8.\n");
	} else {
		printf("Suma en Q7.8: entero = %ld, valor = %.6f\n",
		       (long)suma, (double)suma / 256.0);
	}

	if (resta < INT16_MIN || resta > INT16_MAX) {
		printf("La resta excede el rango representable en Q7.8.\n");
	} else {
		printf("Resta en Q7.8: entero = %ld, valor = %.6f\n",
		       (long)resta, (double)resta / 256.0);
	}

	return 0;
}
