#include <stdint.h>
#include <stdio.h>

int main(int argc, char *argv[]) {
	
	int16_t num1, num2, resultado_suma, resultado_multi_16, resultado_divi;
	int32_t resultado_multi, numerador;
	
	printf("TODO LOS NUMEROS ESTAN EN Q7\n");
	
	printf("Ingrese el primer número en Q7\n");
	scanf("%hd", &num1);
	
	printf("Ingrese el segundo número en Q7\n");
	scanf("%hd", &num2);
	
	resultado_suma = num1 + num2;
	
	printf("Resultado de la suma: %d\n", resultado_suma);
	
	resultado_multi = ((int32_t)(num1) * (int32_t)(num2));//Resultado de la multiplicación pero en Q14
	resultado_multi_16 = (int16_t)((resultado_multi + 64) >> 7);//¿Qué hace ese + 64?Equivale a sumarle 0.5 al número en formato Q antes de cortar los decimales. Si el decimal era igual o mayor a 0.5, la suma hace que el número pase al siguiente entero. Si era menor a 0.5, se queda en el entero actual.
	
	printf("Resultado de la multiiplicación: %hd\n", resultado_multi_16);
	
	numerador = ((int32_t)(num1) << 7);
	resultado_divi = ((numerador + (num2/2)) / (int32_t)(num2));//Para redondear una división entera A / B al número más cercano (en lugar de truncar), la regla matemática es sumarle la mitad del divisor (B / 2) al dividendo (A) antes de dividir.
	
	printf("Resultado de la división: %hd\n", resultado_divi);
	
	return 0;
}

