#include "../Tabla.h"

int main() {

    // Inicializar y convertir las tablas
    float tabla_original[91];
    int16_t tabla_q1_14[91];

    iniciar_tabla(tabla_original);
    copiar_y_convertirQ1_14(tabla_q1_14, tabla_original);

    // Variables de entrada y resultados
    float angulo;

    int16_t seno_q1_14;
    int16_t coseno_q1_14;

    double radianes;
    double seno_obtenido;
    double coseno_obtenido;

    double seno_esperado;
    double coseno_esperado;

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

    int casos_especiales = 0;
    int errores_casos_especiales = 0;

    int16_t seno_especial_esperado;
    int16_t coseno_especial_esperado;

    // Recorrer todos los valores representables de Q3.12
    for (int valor_q3_12 = 0; valor_q3_12 <= DOSxPI; valor_q3_12++) {

        // Convertir la entrada Q3.12 a radianes
        angulo = (float)valor_q3_12 / 4096.0f;

        // Calcular seno y coseno mediante nuestra funcion
        calcular_seno_coseno_Q1_14(
            tabla_q1_14,
            angulo,
            seno_q1_14,
            coseno_q1_14
        );

        // Convertir los resultados Q1.14 a decimal
        seno_obtenido = (double)seno_q1_14 / 16384.0;
        coseno_obtenido = (double)coseno_q1_14 / 16384.0;

        // Calcular los valores matematicos esperados
        radianes = (double)valor_q3_12 / 4096.0;

        seno_esperado = sin(radianes);
        coseno_esperado = cos(radianes);

        // Calcular errores absolutos
        error_seno = fabs(seno_obtenido - seno_esperado);
        error_coseno = fabs(coseno_obtenido - coseno_esperado);

        // Acumular errores
        error_seno_acumulado += error_seno;
        error_coseno_acumulado += error_coseno;

        error_seno_cuadratico += error_seno * error_seno;
        error_coseno_cuadratico += error_coseno * error_coseno;

        // Registrar errores maximos
        if (error_seno > error_seno_maximo) {
            error_seno_maximo = error_seno;
            referencia_error_seno = valor_q3_12;
        }

        if (error_coseno > error_coseno_maximo) {
            error_coseno_maximo = error_coseno;
            referencia_error_coseno = valor_q3_12;
        }

        // Verificar los casos especiales
        if (
            valor_q3_12 == 0 ||
            valor_q3_12 == PI_sobre_2 ||
            valor_q3_12 == PI ||
            valor_q3_12 == TRESxPI_sobre_2 ||
            valor_q3_12 == DOSxPI
        ) {

            casos_especiales++;

            if (valor_q3_12 == 0 || valor_q3_12 == DOSxPI) {
                seno_especial_esperado = 0;
                coseno_especial_esperado = UNO;
            }
            else if (valor_q3_12 == PI_sobre_2) {
                seno_especial_esperado = UNO;
                coseno_especial_esperado = 0;
            }
            else if (valor_q3_12 == PI) {
                seno_especial_esperado = 0;
                coseno_especial_esperado = MENOS_1;
            }
            else {
                seno_especial_esperado = MENOS_1;
                coseno_especial_esperado = 0;
            }

            if (
                seno_q1_14 != seno_especial_esperado ||
                coseno_q1_14 != coseno_especial_esperado
            ) {
                errores_casos_especiales++;
            }
        }
    }

    // Mostrar resultados
    cout << fixed << setprecision(10);

    cout << "\n========== PRUEBA INTEGRAL ==========\n";

    cout << "\nReferencias evaluadas: " << DOSxPI + 1 << "\n";

    cout << "\n--------------- SENO ---------------\n";

    cout << "Error absoluto maximo: "
         << error_seno_maximo << "\n";

    cout << "Referencia con mayor error: "
         << referencia_error_seno << "\n";

    cout << "Error absoluto promedio: "
         << error_seno_acumulado / (DOSxPI + 1) << "\n";

    cout << "Error RMS: "
         << sqrt(error_seno_cuadratico / (DOSxPI + 1)) << "\n";

    cout << "\n--------------- COSENO ---------------\n";

    cout << "Error absoluto maximo: "
         << error_coseno_maximo << "\n";

    cout << "Referencia con mayor error: "
         << referencia_error_coseno << "\n";

    cout << "Error absoluto promedio: "
         << error_coseno_acumulado / (DOSxPI + 1) << "\n";

    cout << "Error RMS: "
         << sqrt(error_coseno_cuadratico / (DOSxPI + 1)) << "\n";

    cout << "\n---------- CASOS ESPECIALES ----------\n";

    cout << "Casos especiales evaluados: "
         << casos_especiales << "\n";

    cout << "Errores en casos especiales: "
         << errores_casos_especiales << "\n";

    return 0;
}
