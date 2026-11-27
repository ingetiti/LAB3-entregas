#include "../Tabla.h"

int main() {

    double error_maximo = 0;
    double error_acumulado = 0;
    double error;
    double esperado;

    int referencia_error_maximo = 0;
    int errores_monotonicidad = 0;

    float resultado;
    float grados_anterior = -1;

    cout << fixed << setprecision(8);

    // Evaluar las 6435 referencias posibles
    for (int referencia = 0; referencia < 6435; referencia++) {

        resultado = convertir_referencia_a_grados(referencia);

        esperado = ((double)referencia / 4096.0) * 180.0 / 3.14159265358979323846;

        error = fabs(resultado - esperado);

        error_acumulado += error;

        if (error > error_maximo) {
            error_maximo = error;
            referencia_error_maximo = referencia;
        }

        // Comprobar que los grados aumenten correctamente
        if (referencia > 0 && resultado < grados_anterior) {
            errores_monotonicidad++;
        }

        grados_anterior = resultado;
    }

    cout << "\n===== RESULTADOS =====\n";

    cout << "Referencias evaluadas: 6435\n";

    cout << "Error absoluto maximo: " << error_maximo << " grados\n";

    cout << "Error absoluto promedio: " << error_acumulado / 6435.0 << " grados\n";

    cout << "Referencia con mayor error: " << referencia_error_maximo << "\n";

    cout << "Errores de monotonicidad: " << errores_monotonicidad << "\n";

    cout << "\n===== CASOS PARTICULARES =====\n";

    int casos[7] = {0, 1, 2048, 4096, 5000, 6000, 6434};

    for (int i = 0; i < 7; i++) {
        cout << "Referencia Q3.12: " << casos[i] << " -> Grados: " << convertir_referencia_a_grados(casos[i]) << endl;
    }

    return 0;
}
