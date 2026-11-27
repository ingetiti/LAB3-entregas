#include <iostream>
#include <stdint.h>
#include <iomanip>

using namespace std;

// Constantes Q3.12 en radianes.
const int16_t PI_sobre_2 = 6434;       // pi/2  ≈ 90°
const int16_t PI = 12868;              // pi    ≈ 180°
const int16_t TRESxPI_sobre_2 = 19302; // 3pi/2 ≈ 270°
const int16_t DOSxPI = 25736;          // 2pi   ≈ 360°

int16_t convertirQ3_12(float valor) {
    float escalado = valor * 4096.0f;

    if (escalado >= 0.0f) {
        return (int16_t)(escalado + 0.5f);
    }

    return (int16_t)(escalado - 0.5f);
}

// Identifica el cuadrante, calcula el angulo de referencia
// y determina los signos del seno y del coseno.
void determinar_cuadrante(float angulo, int16_t &referencia, int &cuadrante, int &signo_seno, int &signo_cos) {
    int16_t diferencia;
    int16_t Q3_12 = convertirQ3_12(angulo);

    cout << fixed << setprecision(6);
    cout << "\n--- CONVERSION A Q3.12 ---" << endl;
    cout << "Angulo ingresado: " << angulo << " radianes" << endl;
    cout << "Entero Q3.12: " << Q3_12 << endl;

    // DEMOSTRACION: equivalencia aproximada en grados.
    // Esta conversion solo se muestra para facilitar la explicacion;
    // la logica del cuadrante trabaja con valores Q3.12 en radianes.
    float grados = ((float)Q3_12 / 4096.0f) * (180.0f / 3.14159265f);
    cout << "Equivalente aproximado en grados (demostracion): " << grados << " grados" << endl;

    // Identificar el cuadrante y calcular el angulo de referencia.
    if (Q3_12 == 0 || Q3_12 == DOSxPI) {
        referencia = 0;
        cuadrante = 0;
        signo_seno = 0;
        signo_cos = 1;
        cout << "\nCaso especial: 0 o 2xPI" << endl;
    } else {
        diferencia = Q3_12 - PI_sobre_2;

        if (diferencia < 0) {
            cuadrante = 1;
            referencia = Q3_12;
            signo_seno = 1;
            signo_cos = 1;
        } else if (diferencia == 0) {
            cuadrante = 0;
            referencia = PI_sobre_2;
            signo_seno = 1;
            signo_cos = 0;
            cout << "\nCaso especial: pi/2" << endl;
        } else {
            diferencia = Q3_12 - PI;

            if (diferencia < 0) {
                cuadrante = 2;
                referencia = PI - Q3_12;
                signo_seno = 1;
                signo_cos = -1;
            } else if (diferencia == 0) {
                cuadrante = 0;
                referencia = 0;
                signo_seno = 0;
                signo_cos = -1;
                cout << "\nCaso especial: pi" << endl;
            } else {
                diferencia = Q3_12 - TRESxPI_sobre_2;

                if (diferencia < 0) {
                    cuadrante = 3;
                    referencia = Q3_12 - PI;
                    signo_seno = -1;
                    signo_cos = -1;
                } else if (diferencia == 0) {
                    cuadrante = 0;
                    referencia = PI_sobre_2;
                    signo_seno = -1;
                    signo_cos = 0;
                    cout << "\nCaso especial: 3*pi/2" << endl;
                } else {
                    cuadrante = 4;
                    referencia = DOSxPI - Q3_12;
                    signo_seno = -1;
                    signo_cos = 1;
                }
            }
        }
    }

    cout << "\n--- RESULTADOS ---" << endl;
    cout << "Cuadrante: " << cuadrante << endl;
    cout << "Referencia Q3.12: " << referencia << endl;
    cout << "Referencia en radianes: "<< (float)referencia / 4096.0f << endl;
    cout << "Signo del seno: " << signo_seno << endl;
    cout << "Signo del coseno: " << signo_cos << endl;
}

int main() {
    float anguloDecimal;
    int16_t referencia;
    int cuadrante;
    int signo_seno;
    int signo_cos;

    cout << "Ingrese el angulo en radianes (entre 0 y aproximadamente 6.2832): ";
    cin >> anguloDecimal;

    determinar_cuadrante(anguloDecimal, referencia, cuadrante, signo_seno, signo_cos);

    return 0;
}
