#include "../Tabla.h"

int main() {

    // Tabla de prueba: valores de seno de 0 a 90 grados en Q1.14
    float tabla_original[91];
    int16_t tabla_q1_14[91];

    double radianes;
    double valor_seno;
    double valor_coseno;

    // Variables para los resultados de interpolacion
    float grados;
    float grados_coseno;

    int16_t seno_q1_14;
    int16_t coseno_q1_14;

    double seno_obtenido;
    double coseno_obtenido;

    // Variables para medir errores
    double error_seno;
    double error_coseno;

    double error_seno_maximo = 0;
    double error_coseno_maximo = 0;

    double error_seno_acumulado = 0;
    double error_coseno_acumulado = 0;

    double error_seno_cuadratico = 0;
    double error_coseno_cuadratico = 0;

    int referencia_error_seno = 0;
    int referencia_error_coseno = 0;

    iniciar_tabla(tabla_original);
    copiar_y_convertirQ1_14(tabla_q1_14,tabla_original);

    // Evaluar las 6435 referencias posibles
     for (int referencia = 0; referencia < 6435; referencia++) {

          // Convertir la referencia Q3.12 a grados
          grados = convertir_referencia_a_grados(referencia);

          // Interpolar el seno
          seno_q1_14 = interpolarQ1_14(tabla_q1_14, grados);

          // Convertir el resultado Q1.14 a decimal
          seno_obtenido = (double)seno_q1_14 / 16384.0;

          // Calcular el valor esperado
          radianes = (double)referencia / 4096.0;
          valor_seno = sin(radianes);

          // Calcular error absoluto
          error_seno = fabs(seno_obtenido - valor_seno);

          error_seno_acumulado += error_seno;
          error_seno_cuadratico += error_seno * error_seno;

          if (error_seno > error_seno_maximo) {
               error_seno_maximo = error_seno;
               referencia_error_seno = referencia;
          }


          // Obtener el coseno mediante cofuncion
          grados_coseno = 90.0 - grados;

          coseno_q1_14 = interpolarQ1_14(tabla_q1_14, grados_coseno);

          coseno_obtenido = (double)coseno_q1_14 / 16384.0;

          valor_coseno = cos(radianes);

          error_coseno = fabs(coseno_obtenido - valor_coseno);

          error_coseno_acumulado += error_coseno;
          error_coseno_cuadratico += error_coseno * error_coseno;

          if (error_coseno > error_coseno_maximo) {
               error_coseno_maximo = error_coseno;
               referencia_error_coseno = referencia;
          }
     }

    // Mostrar resultados
    cout << fixed << setprecision(10);

    cout << "\n========== RESULTADOS DE INTERPOLACION ==========\n";

    cout << "\nReferencias evaluadas: 6435\n";

    cout << "\n--------------- SENO ---------------\n";

    cout << "Error absoluto maximo: " << error_seno_maximo << "\n";

    cout << "Referencia con mayor error: " << referencia_error_seno << "\n";

    cout << "Error absoluto promedio: " << error_seno_acumulado / 6435.0 << "\n";

    cout << "Error RMS: " << sqrt(error_seno_cuadratico / 6435.0) << "\n";

    cout << "\n--------------- COSENO ---------------\n";

    cout << "Error absoluto maximo: " << error_coseno_maximo << "\n";

    cout << "Referencia con mayor error: " << referencia_error_coseno << "\n";

    cout << "Error absoluto promedio: " << error_coseno_acumulado / 6435.0 << "\n";

    cout << "Error RMS: " << sqrt(error_coseno_cuadratico / 6435.0) << "\n";

    return 0;
}