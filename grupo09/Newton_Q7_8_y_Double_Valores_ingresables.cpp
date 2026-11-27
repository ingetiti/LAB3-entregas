#include <cstdint>
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <cmath>

using namespace std;

constexpr int32_t ESCALA = 256; // 2^8 (Q7.8)

// Multiplica dos valores Q7.8 y controla desbordamientos de 16 bits
int16_t multiplicar_q(int16_t a, int16_t b) {
	if (a < 0 || b < 0) {
		throw invalid_argument("Operando negativo detectado en la multiplicacion.");
	}
	
	const int32_t producto = static_cast<int32_t>(a) * b;
	const int32_t ajustado = producto / ESCALA; // Trunca hacia cero
	
	if (ajustado > numeric_limits<int16_t>::max()) {
		throw overflow_error("Desbordamiento aritmetico: El resultado supera los 16 bits con signo.");
	}
	return static_cast<int16_t>(ajustado);
}

int main() {
	cout << fixed << setprecision(9);
	cout << "========================================================\n";
	cout << "  Laboratorio: SQRT Newton-Raphson Q7.8 (Con Limites)  \n";
	cout << "========================================================\n\n";
	
	double x_decimal;
	cout << "Ingrese el valor de x a calcular: ";
	if (!(cin >> x_decimal)) {
		cerr << "[Error] Entrada invalida.\n";
		return 1;
	}
	
	// 1. Validar ceros o negativos (fuera del dominio real de la raíz)
	if (x_decimal <= 0.0) {
		cerr << "\n[Violacion de Dominio] El prototipo requiere x > 0. No se admiten ceros ni negativos.\n";
		return 1;
	}
	
	// Convertir el número decimal a formato Q7.8 multiplicando por la escala
	double x_escalado_d = x_decimal * ESCALA;
	
	// Verificar si cabe en un int16_t antes de castear
	if (x_escalado_d > numeric_limits<int16_t>::max()) {
		cerr << "\n[Violacion de Rango] El numero es demasiado grande para ser representado en Q7.8 (Desborda los 16 bits).\n";
		return 1;
	}
	
	int16_t x = static_cast<int16_t>(x_escalado_d);
	
	cout << "\nValor ingresado: " << x_decimal 
		<< " | Q7.8 entero: " << x 
		<< " (Hex: 0x" << hex << x << dec << ")\n";
	
	// 2. Controlar si se pasa de la restricción del prototipo (4 <= x <= 16)
	constexpr int16_t X_MIN = 4 * ESCALA;   // 1024
	constexpr int16_t X_MAX = 16 * ESCALA;  // 4096
	
	if (x < X_MIN || x > X_MAX) {
		cout << "\n[ADVERTENCIA]: El valor esta FUERA de la restriccion del prototipo (4 <= x <= 16)[cite: 3].\n";
		cout << "El sistema intentara procesarlo, pero es muy probable que ocurra un desbordamiento o divergencia.\n";
		cout << "-------------------------------------------------------------------\n";
	} else {
		cout << "[OK] El valor esta dentro del rango estricto del prototipo (4 <= x <= 16)[cite: 3].\n";
		cout << "-------------------------------------------------------------------\n";
	}
	
	// Semilla inicial fija del prototipo: y = 0.25 -> 0.25 * 256 = 64[cite: 3]
	int16_t y = 64; 
	constexpr int16_t TRES_Q = 3 * ESCALA;
	int iteraciones = 6;
	
	try {
		for (int i = 0; i < iteraciones; ++i) {
			const int16_t y2 = multiplicar_q(y, y);
			const int16_t xy2 = multiplicar_q(x, y2);
			
			// Validación clave: si x es muy grande, xy2 supera a 3.0 en Q7.8 (768)
			int32_t factor_check = static_cast<int32_t>(TRES_Q) - xy2;
			if (factor_check < 0) {
				throw overflow_error("El factor de correccion (3 - x*y^2) se volvio negativo debido a un valor de x fuera de rango.");
			}
			const int16_t factor = static_cast<int16_t>(factor_check);
			
			const int16_t producto = multiplicar_q(factor, y);
			y = producto / 2;
			
			const int16_t raiz_q = multiplicar_q(x, y);
			cout << "Iteracion " << (i + 1)
				<< " | y_Q = " << y
				<< " | sqrt_Q = " << raiz_q
				<< " | sqrt(x) ~= " << (static_cast<double>(raiz_q) / ESCALA) << '\n';
		}
		
		const int16_t raiz_final_q = multiplicar_q(x, y);
		cout << "-------------------------------------------------------------------\n";
		cout << "Resultado final Q7.8 (entero): " << raiz_final_q << '\n';
		cout << "Resultado decimal aproximado: " << (static_cast<double>(raiz_final_q) / ESCALA) << '\n';
		cout << "Referencia std::sqrt: " << std::sqrt(x_decimal) << '\n';
		
	} catch (const exception& e) {
		cerr << "\n[Excepcion atrapada]: " << e.what() << '\n';
		cerr << "-> El algoritmo fallo porque no se respetaron los limites operativos de Q7.8.\n";
		return 1;
	}
	
	return 0;
}
