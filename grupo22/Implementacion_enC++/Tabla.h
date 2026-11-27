#ifndef TABLA_H
#define TABLA_H

//LINK - Librerias
#include <iostream>
#include <stdint.h>
#include <cmath>
#include <cstdint>
#include <iomanip>

//NOTE -  Config
using namespace std; // Para evitar redundancia de std::

//SECTION - Valores necesarios
#define Total_valores 91 //LINK Total de valores en la tabla

//NOTE - Info
//  ? Constantes que están representadas en formato fijo Q3.12 
//  ? y expresadas en radianes.
//  ! son aproximaciones porque estamos representando 
//  ! números reales con una cantidad finita de bits.
const int16_t PI_sobre_2      = 6434;        //NOTE  π/2 rad ≈ 90° en Q3.12
const int16_t PI              = 12868;      //NOTE  π rad ≈ 180° en Q3.12
const int16_t TRESxPI_sobre_2 = 19302;     //NOTE  3π/2 rad ≈ 270° en Q3.12
const int16_t DOSxPI          = 25736;    //NOTE  2π rad ≈ 360° en Q3.12
const int16_t MENOS_1         = -16384;  //NOTE -1 Escalado
const int16_t UNO             = 16384;  //NOTE  1 Escalado
//!SECTION

//LINK - Convertir a Q1.14
int convertirQ1_14(float valor) {
    float escalado = valor * 16384.0f;

    // ? Aplicar redondeo:
    if (escalado >= 0.0f) {             // en caso de que se trate de un positivo
        return (int)(escalado + 0.5f); // redondea 0.5
    }
    
    return (int)(escalado - 0.5f); // en caso de negativo -0.5
    // si el numero se encuentra en los .50 lo redondeara hacia el siguiente
    // caso contrario no
}

//LINK - Convertir a Q3.12
int16_t convertirQ3_12(float valor) {
    float escalado = valor * 4096.0f;

    // ? Aplicar redondeo: 
    if (escalado >= 0.0f) {
        return (int16_t)(escalado + 0.5f);
    }

    return (int16_t)(escalado - 0.5f);    
}

//LINK - Inicializar tabla
void iniciar_tabla(float tabla[]){
    // ! Cada indice representa un seno en especifico
    tabla[0] = 0.000000000000000;
    tabla[1] = 0.017452406437284;
    tabla[2] = 0.034899496702501;
    tabla[3] = 0.052335956242944;
    tabla[4] = 0.069756473744125;
    tabla[5] = 0.087155742747658;
    tabla[6] = 0.104528463267653;
    tabla[7] = 0.121869343405147;
    tabla[8] = 0.139173100960065;
    tabla[9] = 0.156434465040231;
    tabla[10] = 0.173648177666930;
    tabla[11] = 0.190808995376545;
    tabla[12] = 0.207911690817759;
    tabla[13] = 0.224951054343865;
    tabla[14] = 0.241921895599668;
    tabla[15] = 0.258819045102521;
    tabla[16] = 0.275637355816999;
    tabla[17] = 0.292371704722737;
    tabla[18] = 0.309016994374947;
    tabla[19] = 0.325568154457157;
    tabla[20] = 0.342020143325669;
    tabla[21] = 0.358367949545300;
    tabla[22] = 0.374606593415912;
    tabla[23] = 0.390731128489274;
    tabla[24] = 0.406736643075800;
    tabla[25] = 0.422618261740699;
    tabla[26] = 0.438371146789077;
    tabla[27] = 0.453990499739547;
    tabla[28] = 0.469471562785891;
    tabla[29] = 0.484809620246337;
    tabla[30] = 0.500000000000000;
    tabla[31] = 0.515038074910054;
    tabla[32] = 0.529919264233205;
    tabla[33] = 0.544639035015027;
    tabla[34] = 0.559192903470747;
    tabla[35] = 0.573576436351046;
    tabla[36] = 0.587785252292473;
    tabla[37] = 0.601815023152048;
    tabla[38] = 0.615661475325658;
    tabla[39] = 0.629320391049837;
    tabla[40] = 0.642787609686539;
    tabla[41] = 0.656059028990507;
    tabla[42] = 0.669130606358858;
    tabla[43] = 0.681998360062498;
    tabla[44] = 0.694658370458997;
    tabla[45] = 0.707106781186548;
    tabla[46] = 0.719339800338651;
    tabla[47] = 0.731353701619170;
    tabla[48] = 0.743144825477394;
    tabla[49] = 0.754709580222772;
    tabla[50] = 0.766044443118978;
    tabla[51] = 0.777145961456971;
    tabla[52] = 0.788010753606722;
    tabla[53] = 0.798635510047293;
    tabla[54] = 0.809016994374947;
    tabla[55] = 0.819152044288992;
    tabla[56] = 0.829037572555042;
    tabla[57] = 0.838670567945424;
    tabla[58] = 0.848048096156426;
    tabla[59] = 0.857167300702112;
    tabla[60] = 0.866025403784439;
    tabla[61] = 0.874619707139396;
    tabla[62] = 0.882947592858927;
    tabla[63] = 0.891006524188368;
    tabla[64] = 0.898794046299167;
    tabla[65] = 0.906307787036650;
    tabla[66] = 0.913545457642601;
    tabla[67] = 0.920504853452440;
    tabla[68] = 0.927183854566787;
    tabla[69] = 0.933580426497202;
    tabla[70] = 0.939692620785908;
    tabla[71] = 0.945518575599317;
    tabla[72] = 0.951056516295154;
    tabla[73] = 0.956304755963035;
    tabla[74] = 0.961261695938319;
    tabla[75] = 0.965925826289068;
    tabla[76] = 0.970295726275996;
    tabla[77] = 0.974370064785235;
    tabla[78] = 0.978147600733806;
    tabla[79] = 0.981627183447664;
    tabla[80] = 0.984807753012208;
    tabla[81] = 0.987688340595138;
    tabla[82] = 0.990268068741570;
    tabla[83] = 0.992546151641322;
    tabla[84] = 0.994521895368273;
    tabla[85] = 0.996194698091746;
    tabla[86] = 0.997564050259824;
    tabla[87] = 0.998629534754574;
    tabla[88] = 0.999390827019096;
    tabla[89] = 0.999847695156391;
    tabla[90] = 1.000000000000000;
}

//LINK - Hacer copia y convertir Q1.14
void copiar_y_convertirQ1_14(int16_t copia[], float tabla_principal[]){
    // ! Toma los valores originales en decimal de la tabla
    // ! y los convierte a enteros escalados
    
    // ? se tendra una segunda tabla que almacene estos valores
    // asi no se modifican los valores originales a futuras pruebas de ser 
    // necesarias
    for (int i=0; i<Total_valores; i++){
        copia[i]=convertirQ1_14(tabla_principal[i]);
    }
}

//LINK - Muestra de valores en formato obj
void muestra_tabla_assembly(int16_t tabla_copia[]){
    cout<<"TABLA_SENO"<<endl;
    for (int i=0; i<Total_valores; i++){
        cout<<"\t.FILL #"<<tabla_copia[i]<<" ; Resultado de seno("<<i<<")"<<endl;
    }

    // ? Para copiar y pegar para cuando tengamos que armar el assembly
}

//LINK - Muestra de valores (normal)
void muestra_tabla_C(float tabla[]){

    for (int i = 0; i < 91; i++) {
        cout <<"Indice ["<<i<<"] = " <<tabla[i] << endl;
        // printf("Indice [%i] = %.16f\n", i, tabla[i]);
    }

    // la misma muestra de assembly solo que ver unicamente los valores cargados
}

//LINK - Identificar cuadrante
void determinar_cuadrante(float angulo, int16_t &referencia, int &cuadrante, int &signo_seno, int &signo_cos){
    int16_t diferencia, Q3_12;
    // ! 1. Convertir la entrada decimal a Q3.12.
    Q3_12 = convertirQ3_12(angulo);

    // ! 2. Identificar el cuadrante y calcular la referencia.
    if (Q3_12 == 0 || Q3_12 == DOSxPI) {
        referencia = 0;
        cuadrante = 0;
        signo_seno = 0;
        signo_cos = 1;

        // ? Caso especial: 0 o 2xPI (360)
    } 
    
    else {
        diferencia = Q3_12 - PI_sobre_2;

        if (diferencia < 0) {
            cuadrante = 1;
            referencia = Q3_12;
            signo_seno = 1;
            signo_cos = 1;

            // ? Cuadrante 1
        } 
        
        else if (diferencia == 0) {
            cuadrante = 0;
            referencia = PI_sobre_2;
            signo_seno = 1;
            signo_cos = 0;

            // ? Caso especial: pi/2 (90)
        } 
        
        else {
            diferencia = Q3_12 - PI;

            if (diferencia < 0) {
                cuadrante = 2;
                referencia = PI - Q3_12;
                signo_seno = 1;
                signo_cos = -1;

                // ? Cuadrante 2
            } 
            
            else if (diferencia == 0) {
                cuadrante = 0;
                referencia = 0;
                signo_seno = 0;
                signo_cos = -1;

                // ? Caso especial: pi (180)
            } 
            
            else {
                diferencia = Q3_12 - TRESxPI_sobre_2;

                if (diferencia < 0) {
                    cuadrante = 3;
                    referencia = Q3_12 - PI;
                    signo_seno = -1;
                    signo_cos = -1;

                    // ? Cuadrante 3
                } 
                
                else if (diferencia == 0) {
                    cuadrante = 0;
                    referencia = PI_sobre_2;
                    signo_seno = -1;
                    signo_cos = 0;

                    // ? Caso especial: 3*pi/2 (270)
                } 
                
                else {
                    cuadrante = 4;
                    referencia = DOSxPI - Q3_12;
                    signo_seno = -1;
                    signo_cos = 1;

                    // ? Cuadrante 4
                }
            }
        }
    }

    // ? Sobre el signo:
    // 1: el resultado es positivo.
    // -1: el resultado es negativo.
    // 0: el resultado es exactamente cero en ese caso especial.
}


//LINK - Convertir referencia Q3.12 a grados decimales
float convertir_referencia_a_grados(int16_t referencia_q3_12) {

    double radianes;
    double grados;

    radianes = (double)referencia_q3_12 / 4096.0;
    grados = radianes * 180.0 / 3.14159265358979323846;

    return (float)grados;
}


//LINK - Interpolar un valor de seno en formato Q1.14
int16_t interpolarQ1_14(int16_t tabla[], float grados) {

    // ! Variables temporales para determinar los INDICES de los vecinos
    int indice_inferior;
    int indice_superior;

    float fraccion; // ! Variable temporal para guardar la parte decimal del angulo ingresado
    
    // ! Variables temporales para determinar los VALORES de los vecinos
    float valor_inferior; 
    float valor_superior;
    
    float resultado; // ? Resultado final

    // Controlar los limites de la tabla
    if (grados <= 0) {
        return (int16_t)tabla[0];
    }

    if (grados >= 90) {
        return (int16_t)tabla[90];
    }

    // Obtener los indices vecinos
    indice_inferior = (int)grados;
    indice_superior = indice_inferior + 1;

    // Obtener la parte decimal del angulo
    fraccion = grados - indice_inferior;

    // Obtener los valores vecinos de la tabla
    valor_inferior = tabla[indice_inferior];
    valor_superior = tabla[indice_superior];

    // Calcular la interpolacion lineal
    resultado = valor_inferior + fraccion * (valor_superior - valor_inferior);

    // Redondear al entero mas cercano
    return (int16_t)(resultado + 0.5);
}

//LINK - Calcular seno y coseno finales en Q1.14
void calcular_seno_coseno_Q1_14(int16_t tabla[], float angulo, int16_t &resultado_seno, int16_t &resultado_coseno){
    int16_t referencia; // ! Angulo de referencia de la simetria
    int cuadrante; // ? Variable temporal para determinar el cuandrante seleccionado
    int signo_seno, signo_cos; // ! Variables para determinar signos (y usado tambien para casos especiales)

    int16_t seno_referencia, coseno_referencia; // ! Valores de refencia 

    float grados_referencia, grados_coseno; // ! Angulos de referencia determinados

    // ! 1. Determinar cuadrante, referencia y signos
    determinar_cuadrante(angulo,referencia,cuadrante,signo_seno,signo_cos);

    // ! 2. Resolver los casos especiales
    if (cuadrante == 0) {

        resultado_seno = signo_seno * UNO;
        resultado_coseno = signo_cos * UNO;

    } 
    
    else {

        // ! 3. Convertir la referencia a grados
        grados_referencia = convertir_referencia_a_grados(referencia);

        // ! 4. Interpolar el seno
        seno_referencia = interpolarQ1_14(tabla,grados_referencia);

        // ! 5. Obtener el coseno mediante cofuncion
        grados_coseno = 90.0f - grados_referencia;

        coseno_referencia = interpolarQ1_14(tabla,grados_coseno);

        // ! 6. Aplicar los signos correspondientes
        resultado_seno = seno_referencia * signo_seno;
        resultado_coseno = coseno_referencia * signo_cos;

        // ? Dilema para futuro: el -1 capaz deberia estar escalado... (pa pensar noma)
    }
}

#endif /* TABLA_H */