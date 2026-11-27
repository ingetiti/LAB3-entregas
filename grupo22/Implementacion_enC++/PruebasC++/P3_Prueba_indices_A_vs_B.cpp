
#include <iostream>
#include <cmath>
#include <cstdint>
#include "../Tabla.h"


// LINK - Comparar metodos de calculo del indice
inline void probarMetodosIndice() {

    const int32_t PI_MEDIO_Q312 = 6434;
    const int32_t ESCALA_Q312 = 4096;
    const double PI = 3.14159265358979323846;

    int totalPruebas = 0;
    int diferencias = 0;

    int maxDiferenciaIndices = 0;
    int referenciaDiferente = 0;
    int indiceAEnDiferencia = 0;
    int indiceBEnDiferencia = 0;

    double maxErrorA = 0.0;
    double maxErrorB = 0.0;

    // Recorrer todas las referencias posibles del primer cuadrante.
    for (int32_t referencia = 0;
         referencia <= PI_MEDIO_Q312;
         referencia++) {

        // -----------------------------------------
        // OPCION A: convertir a grados y redondear
        // -----------------------------------------
        double grados = ((double)referencia / ESCALA_Q312)
                        * (180.0 / PI);

        int indiceA = (int)round(grados);

        // -----------------------------------------
        // OPCION B: calcular el indice directamente
        // con aritmetica entera
        // -----------------------------------------
        int32_t numerador = referencia * 90 + PI_MEDIO_Q312 / 2;

        int indiceB = numerador / PI_MEDIO_Q312;

        // -----------------------------------------
        // INDICE MATEMATICO IDEAL (sin redondear)
        // -----------------------------------------
        double indiceIdeal =
            ((double)referencia * 90.0) / PI_MEDIO_Q312;

        double errorA = fabs(indiceA - indiceIdeal);
        double errorB = fabs(indiceB - indiceIdeal);

        if (errorA > maxErrorA) {
            maxErrorA = errorA;
        }

        if (errorB > maxErrorB) {
            maxErrorB = errorB;
        }

        // -----------------------------------------
        // COMPARACION ENTRE AMBOS METODOS
        // -----------------------------------------
        int diferenciaActual = abs(indiceA - indiceB);

        if (diferenciaActual > 0) {
            diferencias++;

            if (diferenciaActual > maxDiferenciaIndices) {
                maxDiferenciaIndices = diferenciaActual;
                referenciaDiferente = referencia;
                indiceAEnDiferencia = indiceA;
                indiceBEnDiferencia = indiceB;
            }
        }

        totalPruebas++;
    }

    // -----------------------------------------
    // MOSTRAR RESULTADOS
    // -----------------------------------------
    cout << "\n===== PRUEBA COMPARATIVA DE INDICES =====\n";

    cout << "\nTotal de referencias probadas: "
         << totalPruebas << "\n";

    cout << "\n--- Comparacion A vs. B ---\n";

    cout << "Referencias con indices diferentes: "
         << diferencias << "\n";

    cout << "Referencias con indices iguales: "
         << totalPruebas - diferencias << "\n";

    cout << "Maxima diferencia entre indices: "
         << maxDiferenciaIndices << "\n";

    if (diferencias > 0) {
        cout << "Referencia donde se registro la maxima diferencia: "
             << referenciaDiferente << "\n";

        cout << "Indice A: " << indiceAEnDiferencia << "\n";
        cout << "Indice B: " << indiceBEnDiferencia << "\n";
    }

    cout << fixed << setprecision(6);

    cout << "\n--- Error respecto al indice ideal ---\n";

    cout << "Maximo error de A (indices): "
         << maxErrorA << "\n";

    cout << "Maximo error de B (indices): "
         << maxErrorB << "\n";

    cout << "\n===== FIN DE LA PRUEBA =====\n";
}


void probarDiferenciaPuntual() {

    const int32_t referencia = 4754;
    const double PI_REAL = 3.14159265358979323846;

    float tablaOriginal[Total_valores];
    int16_t tablaQ14[Total_valores];

    iniciar_tabla(tablaOriginal);
    copiar_y_convertirQ1_14(tablaQ14, tablaOriginal);

    // Angulo representado por la referencia Q3.12.
    double angulo = (double)referencia / 4096.0;
    double grados = angulo * 180.0 / PI_REAL;

    // Opcion A: conversion a grados.
    int indiceA = (int)round(grados);

    // Opcion B: calculo entero directo.
    int32_t numerador =
        referencia * 90 + PI_sobre_2 / 2;

    int indiceB = numerador / PI_sobre_2;

    // Valores matematicos ideales.
    double senoReal = sin(angulo);
    double cosenoReal = cos(angulo);

    // Resultados de tabla en formato Q1.14.
    double senoA = tablaQ14[indiceA] / 16384.0;
    double cosenoA = tablaQ14[90 - indiceA] / 16384.0;

    double senoB = tablaQ14[indiceB] / 16384.0;
    double cosenoB = tablaQ14[90 - indiceB] / 16384.0;

    cout << fixed << setprecision(9);

    cout << "\n===== ANALISIS DE REFERENCIA 4754 =====\n";

    cout << "Referencia Q3.12: " << referencia << "\n";
    cout << "Angulo en radianes: " << angulo << "\n";
    cout << "Angulo en grados: " << grados << "\n";

    cout << "\n--- VALORES MATEMATICOS ---\n";
    cout << "Seno ideal: " << senoReal << "\n";
    cout << "Coseno ideal: " << cosenoReal << "\n";

    cout << "\n--- OPCION A ---\n";
    cout << "Indice: " << indiceA << "\n";
    cout << "Indice complementario: " << 90 - indiceA << "\n";
    cout << "Seno tabla: " << senoA << "\n";
    cout << "Error seno: " << fabs(senoA - senoReal) << "\n";
    cout << "Coseno tabla: " << cosenoA << "\n";
    cout << "Error coseno: " << fabs(cosenoA - cosenoReal) << "\n";

    cout << "\n--- OPCION B ---\n";
    cout << "Indice: " << indiceB << "\n";
    cout << "Indice complementario: " << 90 - indiceB << "\n";
    cout << "Seno tabla: " << senoB << "\n";
    cout << "Error seno: " << fabs(senoB - senoReal) << "\n";
    cout << "Coseno tabla: " << cosenoB << "\n";
    cout << "Error coseno: " << fabs(cosenoB - cosenoReal) << "\n";

    cout << "\n===== FIN DEL ANALISIS =====\n";
}


// LINK - Comparar indices y resultados usando la tabla real
void probarIndicesConTabla() {

    const int32_t ESCALA_Q312 = 4096;
    const double PI_REAL = 3.14159265358979323846;

    // Tabla original y tabla convertida a Q1.14.
    float tablaOriginal[Total_valores];
    int16_t tablaQ14[Total_valores];

    iniciar_tabla(tablaOriginal);
    copiar_y_convertirQ1_14(tablaQ14, tablaOriginal);

    int totalPruebas = 0;
    int indicesDiferentes = 0;

    double maxErrorSenoA = 0.0;
    double maxErrorCosenoA = 0.0;
    double maxErrorSenoB = 0.0;
    double maxErrorCosenoB = 0.0;

    int referenciaErrorSenoA = 0;
    int referenciaErrorCosenoA = 0;
    int referenciaErrorSenoB = 0;
    int referenciaErrorCosenoB = 0;

    int referenciaDiferente = -1;
    int indiceAEnDiferencia = -1;
    int indiceBEnDiferencia = -1;

    for (int32_t referencia = 0;
         referencia <= PI_sobre_2;
         referencia++) {

        // Angulo real representado por la referencia Q3.12.
        double angulo = (double)referencia / ESCALA_Q312;

        // OPCION A: convertir a grados y redondear.
        double grados = angulo * 180.0 / PI_REAL;
        int indiceA = (int)round(grados);

        // OPCION B: calculo entero directo.
        int32_t numerador =
            referencia * 90 + PI_sobre_2 / 2;

        int indiceB = numerador / PI_sobre_2;

        // Valores matematicos ideales para ese angulo.
        double senoReal = sin(angulo);
        double cosenoReal = cos(angulo);

        // Resultados de la tabla Q1.14, convertidos a decimal.
        double senoA = tablaQ14[indiceA] / 16384.0;
        double cosenoA = tablaQ14[90 - indiceA] / 16384.0;

        double senoB = tablaQ14[indiceB] / 16384.0;
        double cosenoB = tablaQ14[90 - indiceB] / 16384.0;

        // Errores absolutos respecto a la funcion matematica.
        double errorSenoA = fabs(senoA - senoReal);
        double errorCosenoA = fabs(cosenoA - cosenoReal);

        double errorSenoB = fabs(senoB - senoReal);
        double errorCosenoB = fabs(cosenoB - cosenoReal);

        // Registrar el peor error de seno de A.
        if (errorSenoA > maxErrorSenoA) {
            maxErrorSenoA = errorSenoA;
            referenciaErrorSenoA = referencia;
        }

        // Registrar el peor error de coseno de A.
        if (errorCosenoA > maxErrorCosenoA) {
            maxErrorCosenoA = errorCosenoA;
            referenciaErrorCosenoA = referencia;
        }

        // Registrar el peor error de seno de B.
        if (errorSenoB > maxErrorSenoB) {
            maxErrorSenoB = errorSenoB;
            referenciaErrorSenoB = referencia;
        }

        // Registrar el peor error de coseno de B.
        if (errorCosenoB > maxErrorCosenoB) {
            maxErrorCosenoB = errorCosenoB;
            referenciaErrorCosenoB = referencia;
        }

        // Registrar las diferencias entre los indices.
        if (indiceA != indiceB) {
            indicesDiferentes++;

            referenciaDiferente = referencia;
            indiceAEnDiferencia = indiceA;
            indiceBEnDiferencia = indiceB;
        }

        totalPruebas++;
    }

    cout << fixed;

    cout << setprecision(9);
    cout << "\n===== PRUEBA CON TABLA Q1.14 =====\n";

    cout << "\nTotal de referencias: "
         << totalPruebas << "\n";

    cout << "Indices diferentes entre A y B: "
         << indicesDiferentes << "\n";

    if (referenciaDiferente >= 0) {
        cout << "\n--- Diferencia de indices ---\n";
        cout << "Referencia Q3.12: "
             << referenciaDiferente << "\n";
        cout << "Indice A: " << indiceAEnDiferencia << "\n";
        cout << "Indice B: " << indiceBEnDiferencia << "\n";
    }

    cout << "\n--- Error maximo de seno ---\n";
    cout << "A: " << maxErrorSenoA
         << " (referencia " << referenciaErrorSenoA << ")\n";
    cout << "B: " << maxErrorSenoB
         << " (referencia " << referenciaErrorSenoB << ")\n";

    cout << "\n--- Error maximo de coseno ---\n";
    cout << "A: " << maxErrorCosenoA
         << " (referencia " << referenciaErrorCosenoA << ")\n";
    cout << "B: " << maxErrorCosenoB
         << " (referencia " << referenciaErrorCosenoB << ")\n";

    cout << "\n===== FIN DE LA PRUEBA =====\n";
}


//LINK - Comparar errores
void compararErrorAcumulado() {

    const int32_t ESCALA_Q312 = 4096;
    const double PI_REAL = 3.14159265358979323846;

    float tablaOriginal[Total_valores];
    int16_t tablaQ14[Total_valores];

    iniciar_tabla(tablaOriginal);
    copiar_y_convertirQ1_14(tablaQ14, tablaOriginal);

    int totalPruebas = 0;
    int indicesDiferentes = 0;

    // Sumas de errores absolutos.
    double sumaErrorSenoA = 0.0;
    double sumaErrorCosenoA = 0.0;
    double sumaErrorSenoB = 0.0;
    double sumaErrorCosenoB = 0.0;

    // Sumas de errores cuadrados para calcular el RMS.
    double sumaCuadradosSenoA = 0.0;
    double sumaCuadradosCosenoA = 0.0;
    double sumaCuadradosSenoB = 0.0;
    double sumaCuadradosCosenoB = 0.0;

    // Cantidad de veces que cada metodo tiene menor error.
    int senoMejorA = 0;
    int senoMejorB = 0;
    int cosenoMejorA = 0;
    int cosenoMejorB = 0;

    for (int32_t referencia = 0;
         referencia <= PI_sobre_2;
         referencia++) {

        double angulo = (double)referencia / ESCALA_Q312;

        // OPCION A: convertir a grados y redondear.
        double grados = angulo * 180.0 / PI_REAL;
        int indiceA = (int)round(grados);

        // OPCION B: calculo directo con enteros.
        int32_t numerador =
            referencia * 90 + PI_sobre_2 / 2;

        int indiceB = numerador / PI_sobre_2;

        if (indiceA != indiceB) {
            indicesDiferentes++;
        }

        // Valores matematicos de referencia.
        double senoReal = sin(angulo);
        double cosenoReal = cos(angulo);

        // Resultados de la tabla Q1.14 convertidos a decimal.
        double senoA = tablaQ14[indiceA] / 16384.0;
        double cosenoA = tablaQ14[90 - indiceA] / 16384.0;

        double senoB = tablaQ14[indiceB] / 16384.0;
        double cosenoB = tablaQ14[90 - indiceB] / 16384.0;

        // Errores absolutos.
        double errorSenoA = fabs(senoA - senoReal);
        double errorCosenoA = fabs(cosenoA - cosenoReal);

        double errorSenoB = fabs(senoB - senoReal);
        double errorCosenoB = fabs(cosenoB - cosenoReal);

        // Acumular errores absolutos.
        sumaErrorSenoA += errorSenoA;
        sumaErrorCosenoA += errorCosenoA;
        sumaErrorSenoB += errorSenoB;
        sumaErrorCosenoB += errorCosenoB;

        // Acumular errores cuadrados.
        sumaCuadradosSenoA += errorSenoA * errorSenoA;
        sumaCuadradosCosenoA += errorCosenoA * errorCosenoA;
        sumaCuadradosSenoB += errorSenoB * errorSenoB;
        sumaCuadradosCosenoB += errorCosenoB * errorCosenoB;

        // Comparar que metodo es mas preciso en cada funcion.
        if (errorSenoA < errorSenoB) {
            senoMejorA++;
        } else if (errorSenoB < errorSenoA) {
            senoMejorB++;
        }

        if (errorCosenoA < errorCosenoB) {
            cosenoMejorA++;
        } else if (errorCosenoB < errorCosenoA) {
            cosenoMejorB++;
        }

        totalPruebas++;
    }

    // Calcular errores medios.
    double promedioSenoA = sumaErrorSenoA / totalPruebas;
    double promedioCosenoA = sumaErrorCosenoA / totalPruebas;

    double promedioSenoB = sumaErrorSenoB / totalPruebas;
    double promedioCosenoB = sumaErrorCosenoB / totalPruebas;

    // Calcular RMS: raiz del promedio de los errores cuadrados.
    double rmsSenoA = sqrt(sumaCuadradosSenoA / totalPruebas);
    double rmsCosenoA = sqrt(sumaCuadradosCosenoA / totalPruebas);

    double rmsSenoB = sqrt(sumaCuadradosSenoB / totalPruebas);
    double rmsCosenoB = sqrt(sumaCuadradosCosenoB / totalPruebas);

    cout << fixed << setprecision(10);

    cout << "\n===== COMPARACION DE ERROR ACUMULADO =====\n";

    cout << "Referencias evaluadas: " << totalPruebas << "\n";
    cout << "Indices diferentes: " << indicesDiferentes << "\n";

    cout << "\n--- ERROR ABSOLUTO PROMEDIO ---\n";
    cout << "Seno A:   " << promedioSenoA << "\n";
    cout << "Seno B:   " << promedioSenoB << "\n";
    cout << "Coseno A: " << promedioCosenoA << "\n";
    cout << "Coseno B: " << promedioCosenoB << "\n";

    cout << "\n--- ERROR RMS ---\n";
    cout << "Seno A:   " << rmsSenoA << "\n";
    cout << "Seno B:   " << rmsSenoB << "\n";
    cout << "Coseno A: " << rmsCosenoA << "\n";
    cout << "Coseno B: " << rmsCosenoB << "\n";

    cout << "\n--- VICTORIAS POR MENOR ERROR ---\n";
    cout << "Seno: A mejor en " << senoMejorA
         << " referencias; B mejor en " << senoMejorB << "\n";

    cout << "Coseno: A mejor en " << cosenoMejorA
         << " referencias; B mejor en " << cosenoMejorB << "\n";

    cout << "\n===== FIN DE LA PRUEBA =====\n";
}



int main() {

    probarMetodosIndice();
    probarDiferenciaPuntual();
    compararErrorAcumulado();

    return 0;
}
