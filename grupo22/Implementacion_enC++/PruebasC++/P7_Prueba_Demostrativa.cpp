#include "../Tabla.h"

int main() {

    // ==========================================
    // 1. INICIALIZACION DE LAS TABLAS
    // ==========================================

    float tabla_original[91];
    int16_t tabla_q1_14[91];

    iniciar_tabla(tabla_original);
    copiar_y_convertirQ1_14(tabla_q1_14,tabla_original);

    
    // ==========================================
    // 2. MOSTRAR TABLAS
    // ==========================================
    
    cout << "\n========================================\n";
    cout << "          TABLA ORIGINAL DE SENO\n";
    cout << "========================================\n";
    
    muestra_tabla_C(tabla_original);
    
    cout << "\n========================================\n";
    cout << "       TABLA CONVERTIDA A Q1.14\n";
    cout << "========================================\n";
    
    muestra_tabla_assembly(tabla_q1_14);
    
    // ==========================================
    // 3. INGRESAR ANGULO
    // ==========================================
    
    float angulo;
    float grados;
    
    cout << "\n========================================\n";
    cout << "             INGRESO DE ANGULO\n";
    cout << "========================================\n";
    
    cout << "Ingrese un angulo en radianes (entre 0 y 2*pi): ";
    cin >> angulo;
    
    // ==========================================
    // 4. CONVERSIONES INICIALES
    // ==========================================
    
    int16_t angulo_q3_12;
    
    angulo_q3_12 = convertirQ3_12(angulo);
    grados = angulo * 180.0f / 3.14159265358979323846f;
    
    cout << "\n========================================\n";
    cout << "           CONVERSION DEL ANGULO\n";
    cout << "========================================\n";
    
    printf("Angulo ingresado: %f radianes\n", angulo);
    
//     cout << fixed << setprecision(8);

    printf("Angulo en grados: %f grados\n", grados);
    cout << "Representacion Q3.12: "<< angulo_q3_12 << "\n";

    // ==========================================
    // 5. DETERMINAR CUADRANTE Y REFERENCIA
    // ==========================================

    int16_t referencia;

    int cuadrante;
    int signo_seno;
    int signo_cos;

    determinar_cuadrante(angulo,referencia,cuadrante,signo_seno,signo_cos);

    cout << "\n========================================\n";
    cout << "       DETERMINACION DEL CUADRANTE\n";
    cout << "========================================\n";

    cout << "Cuadrante: "<< cuadrante << "\n";

    cout << "Referencia Q3.12: "<< referencia << "\n";

    cout << "Signo del seno: "<< signo_seno << "\n";

    cout << "Signo del coseno: "<< signo_cos << "\n";

    // ==========================================
    // 6. ANALIZAR CASO ESPECIAL O NORMAL
    // ==========================================

    float grados_referencia;
    float grados_coseno;

    if (cuadrante == 0) {

        cout << "\nTipo de entrada: CASO ESPECIAL\n";

        cout << "No se requiere interpolacion.\n";

        cout << "Los signos representan directamente ";
        cout << "los valores matematicos del seno y coseno.\n";

    } 
    
    else {

        cout << "\nTipo de entrada: CASO NORMAL\n";

        grados_referencia = convertir_referencia_a_grados(referencia);

        grados_coseno = 90.0f - grados_referencia;

        cout << "Referencia en grados: " << grados_referencia << "\n";

        cout << "Angulo para el coseno (cofuncion): " << grados_coseno << "\n";
    }

    // ==========================================
    // 7. CALCULAR SENO Y COSENO FINALES
    // ==========================================

    int16_t seno_q1_14;
    int16_t coseno_q1_14;

    calcular_seno_coseno_Q1_14(tabla_q1_14,angulo,seno_q1_14,coseno_q1_14);

    // Convertir resultados Q1.14 a decimal
    float seno_decimal;
    float coseno_decimal;

    seno_decimal = (float)seno_q1_14 / 16384.0f;
    coseno_decimal = (float)coseno_q1_14 / 16384.0f;

    // ==========================================
    // 8. MOSTRAR RESULTADOS FINALES
    // ==========================================

    cout << "\n========================================\n";
    cout << "          RESULTADOS FINALES\n";
    cout << "========================================\n";

    cout << "\nSENO:\n";
    cout << "Resultado Q1.14: "<< seno_q1_14 << "\n";
    cout << "Resultado decimal: "<< seno_decimal << "\n";

    cout << "\nCOSENO:\n";
    cout << "Resultado Q1.14: "<< coseno_q1_14 << "\n";
    cout << "Resultado decimal: "<< coseno_decimal << "\n";

    cout << "\n========================================\n";
    cout << "          FIN DE LA EJECUCION\n";
    cout << "========================================\n";

    return 0;
}
