#include <stdint.h>
#include <stdio.h>

int main(void) {
	double numero1;
	double numero2;
	int16_t numero1Q3_12;
	int16_t numero2Q7_8;

	printf("Ingrese el primer numero para representarlo en Q3.12: ");
	if (scanf("%lf", &numero1) != 1) {
		printf("Entrada no valida.\n");
		return 1;
	}

	printf("Ingrese el segundo numero para representarlo en Q7.8: ");
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

	printf("\nPrimer numero en Q3.12: entero almacenado = %d, valor aproximado = %.6f\n",
		   (int)numero1Q3_12, (double)numero1Q3_12 / 4096.0);
	printf("Segundo numero en Q7.8: entero almacenado = %d, valor aproximado = %.6f\n",
		   (int)numero2Q7_8, (double)numero2Q7_8 / 256.0);

	return 0;
}

