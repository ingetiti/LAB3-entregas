#include <stdio.h>

int main(void) {
	double numero1;
	double numero2;

	printf("Ingrese el primer numero con decimales: ");
	scanf("%lf", &numero1);

	printf("Ingrese el segundo numero con decimales: ");
	scanf("%lf", &numero2);

	printf("Primer numero: %f\n", numero1);
	printf("Segundo numero: %f\n", numero2);

	return 0;
}
