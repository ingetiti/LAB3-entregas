#include <stdint.h> //Para usar enteros de 16 bits
#include <stdio.h>

int main(int argc, char *argv[]) {
	
	float num1, num2, resultado, multi_float; //La "f" indica que el número es float 
	int16_t num1_int, num2_int, resultado_int, divi;
	int32_t multi, numerador;
	
	printf("Ingrese el primer valor\n");
	scanf("%f", &num1);
	
	printf("Ingrese el segundo valor\n");
	scanf("%f", &num2);
	
	num1_int = (int16_t)(num1 * 128); //Q7
	num2_int = (int16_t)(num2 * 64); //Q6
	
	num2_int = num2_int * 2; //Pasar de Q6 a Q7	
	
	printf("num1 = %d, num2 = %d\n", num1_int, num2_int);
	
	resultado_int = num1_int + num2_int; //Suma y guarda pero en formato Q8
	resultado = (float)(resultado_int) / 128.00; //Pasarlo a número con coma
	
	printf("resultado_int = %d, resultado = %f\n", resultado_int, resultado);
	
	multi = ((int32_t)(num2_int) * (int32_t)(num1_int));
	multi_float = (int16_t)(multi * 1.00/128.00); //Pasarlo de Q14 a Q7 y con el cast forzamos que lo lea en un espacio de 16 bits
	
	printf("Resultado de la multiplicación con la precision de 16 bits = %f\n", (float)(multi_float * 1.00/128.00));
	
	numerador = ((int32_t)(num1_int) * 128);
	divi = (int16_t)(numerador / num2_int);
	
	printf("Resultado de la división = %f\n", ((float)(divi) * 1.00/128.00));
	
	printf("Ver que mierda dice la ia = %f", (1.00/128.00));
	
	return 0;
}
