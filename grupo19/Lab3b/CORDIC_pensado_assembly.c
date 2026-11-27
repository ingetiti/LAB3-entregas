#include <stdio.h>
#include <stdint.h>
#include <math.h>

// version del CORDIC lineal pensada para el LC-3:
//  - solo se usan palabras de 16 bits con signo (int16_t)
//  - los valores de 32 bits (y, current_x) se simulan con una estructura de 2 palabras: hi y lo
//  - no se usa >>, <<, * ni / : solo sumas, AND, NOT y comparaciones con cero (lo que tiene el LC-3)
//
// el valor de 32 bits es:  hi * 65536 + lo   (lo se interpreta sin signo, como los 16 bits de abajo)
// en memoria del LC-3 una estructura son 2 palabras seguidas: hi en la direccion base y lo en la siguiente

typedef struct {
    int16_t hi;     // parte alta (bits 31..16)
    int16_t lo;     // parte baja (bits 15..0)
} int32_par;

// pesos de cada iteracion: 2^14, 2^13, ..., 2^0
// reemplaza a "current_z /= 2", ya que el LC-3 no puede dividir ni desplazar
// en assembly esto se escribe con .FILL
int16_t tabla_z[15] = {16384, 8192, 4096, 2048, 1024, 512, 256, 128,
                       64, 32, 16, 8, 4, 2, 1};

// ------------------------------------------------------------------
// funciones de 16 bits
// ------------------------------------------------------------------

// corre un bit hacia la derecha (rellena con 0 a la izquierda)
// se copia bit por bit: 'm' apunta al bit que se lee y 'r' al bit donde se escribe
// ambas se desplazan hacia la izquierda sumandose a si mismas (duplicar = sumar consigo mismo)
int16_t desplazar_der_logico(int16_t x) {
    int16_t m = 2;      // mascara, empieza en el bit 1
    int16_t r = 1;      // destino, empieza en el bit 0
    int16_t res = 0;

    for (int k = 0; k < 15; k++) {
        if ((x & m) != 0) {
            res = res + r;
        }
        m = m + m;
        r = r + r;
    }
    return res;
}

// corre un bit hacia la derecha copiando el signo (para que los negativos sigan siendo negativos)
int16_t desplazar_der_aritmetico(int16_t x) {
    int16_t res = desplazar_der_logico(x);

    if (x < 0) {
        res = res - 32768;      // prende el bit 15 (0x8000)
    }
    return res;
}

// ------------------------------------------------------------------
// funciones de 32 bits (estructura hi/lo)
// ------------------------------------------------------------------

// a = a + b
// el LC-3 no avisa cuando la suma de los lo se pasa de 16 bits (acarreo), asi que se deduce mirando los signos:
//  - los dos lo "grandes" (bit 15 en 1)                      -> hay acarreo
//  - uno grande y el otro no, y el resultado quedo "chico"   -> hay acarreo
//  - cualquier otro caso                                     -> no hay acarreo
void suma32(int32_par *a, int32_par *b) {
    int16_t lo;
    int16_t acarreo;
    int16_t a_grande = (a->lo < 0);
    int16_t b_grande = (b->lo < 0);

    lo = a->lo + b->lo;

    if (a_grande && b_grande) {
        acarreo = 1;
    } else if ((a_grande != b_grande) && (lo >= 0)) {
        acarreo = 1;
    } else {
        acarreo = 0;
    }

    a->hi = a->hi + b->hi + acarreo;
    a->lo = lo;
}

// a = a - b
// restar es sumar el opuesto; el opuesto en complemento a 2 es invertir los bits (NOT) y sumar 1
void resta32(int32_par *a, int32_par *b) {
    int32_par opuesto;

    opuesto.hi = ~b->hi;
    opuesto.lo = ~b->lo;

    opuesto.lo = opuesto.lo + 1;
    if (opuesto.lo == 0) {      // el +1 desbordo la parte baja, se lleva 1 a la parte alta
        opuesto.hi = opuesto.hi + 1;
    }

    suma32(a, &opuesto);
}

// v = v / 2 (corre un bit a la derecha manteniendo el signo)
// el bit mas bajo de hi pasa a ser el bit mas alto de lo
void desplazar_der_32(int32_par *v) {
    int16_t bit_bajo_hi = v->hi & 1;    // se guarda antes de modificar hi

    v->lo = desplazar_der_logico(v->lo);
    if (bit_bajo_hi == 1) {
        v->lo = v->lo - 32768;          // lo "recibe" el bit en la posicion 15
    }
    v->hi = desplazar_der_aritmetico(v->hi);
}

// arma x = a_q8 * 2^14 sin multiplicar
// como 2^14 = 2^16 / 4, el numero queda: hi = a_q8 / 4 (con signo) y lo = (resto de a_q8 / 4) * 2^14
void preparar_x(int16_t a_q8, int32_par *x) {
    int16_t resto = a_q8 & 3;           // los 2 bits bajos de a_q8

    x->hi = desplazar_der_aritmetico(desplazar_der_aritmetico(a_q8));

    for (int k = 0; k < 14; k++) {      // resto * 2^14, duplicando 14 veces
        resto = resto + resto;
    }
    x->lo = resto;
}

// ------------------------------------------------------------------
// CORDIC lineal: y = a_q8 * b_q8 (resultado en Q16, guardado en la estructura y)
// ------------------------------------------------------------------
void cordic_multiplicacion(int16_t a_q8, int16_t b_q8, int32_par *y, int16_t *iteraciones) {
    int16_t z;                  // multiplicador que voy vaciando
    int16_t current_z;          // constante movil (peso de la iteracion)
    int32_par current_x;        // multiplicando movil (32 bits)
    int16_t i;

    // se inicializa a z con el multiplicador
    z = b_q8;

    // se inicializa el acumulador en 0
    y->hi = 0;
    y->lo = 0;

    // current_x arranca en a_q8 * 2^14 para no perder decimales al dividir por 2
    preparar_x(a_q8, &current_x);

    for (i = 0; i < 15; i++) {
        if (z == 0) break;

        current_z = tabla_z[i];

        if (z > 0) {
            z = z - current_z;
            suma32(y, &current_x);
        } else {
            z = z + current_z;
            resta32(y, &current_x);
        }

        desplazar_der_32(&current_x);
    }

    *iteraciones = i;
}

// pasa y (Q16, 32 bits) a Q7.8 de 16 bits con redondeo: (y + 128) >> 8
// devuelve 1 si el resultado no entra en 16 bits (desbordamiento), 0 si esta bien
// y no se modifica: se trabaja sobre una copia
int16_t reducir_q78(int32_par *y, int16_t *resultado_q78) {
    int32_par copia;
    int32_par medio_escalon;
    int16_t parte_baja = 0;
    int16_t chequeo;

    copia.hi = y->hi;
    copia.lo = y->lo;

    // se suma 128 (medio escalon de los 256 que se descartan) para que redondee y no corte
    medio_escalon.hi = 0;
    medio_escalon.lo = 128;
    suma32(&copia, &medio_escalon);

    // entra en 16 bits solo si hi esta entre -128 y 127; sumando 128 queda entre 0 y 255
    // (en LC-3: AND con 0xFF00 y ver si da 0)
    chequeo = copia.hi + 128;
    if ((chequeo & -256) != 0) {
        return 1;
    }

    // parte_baja = byte alto de lo, leyendo el signo de lo y duplicando 8 veces
    for (int k = 0; k < 8; k++) {
        parte_baja = parte_baja + parte_baja;
        if (copia.lo < 0) {
            parte_baja = parte_baja + 1;
        }
        copia.lo = copia.lo + copia.lo;
    }

    // hi * 256: se duplica 8 veces
    for (int k = 0; k < 8; k++) {
        copia.hi = copia.hi + copia.hi;
    }

    *resultado_q78 = copia.hi + parte_baja;
    return 0;
}

int main(void) {
    // variables
    float a, b, resultado;
    int32_t a_entero, b_entero;     // solo para validar el rango antes de pasar a int16_t
    int16_t a_q8, b_q8;
    int32_par y;                    // acumulador de 32 bits (Q16)
    int16_t y_q78;                  // resultado ya reducido a Q7.8
    int16_t iteraciones;
    int16_t desbordamiento;

    printf("--- MULTIPLICACION POR CORDIC (32 bits con 2 registros de 16) ---\n");
    printf("Ingrese el primer factor: ");
    scanf("%f", &a);

    printf("Ingrese el segundo factor: ");
    scanf("%f", &b);

    // casteo de float a punto fijo formato Q7.8 --> multiplica por 2^8
    a_entero = lroundf(a * 256.0f);
    b_entero = lroundf(b * 256.0f);

    // a puede valer entre -128 y 127.996 (Q7.8 completo)
    // b no puede ser -128: con los pesos de la tabla el maximo que se llega a "pesar" es 127.996
    if (a_entero < -32768 || a_entero > 32767 || b_entero < -32767 || b_entero > 32767) {
        printf("Entrada fuera de rango Q7.8\n");
        return 1;
    }
    a_q8 = (int16_t)a_entero;
    b_q8 = (int16_t)b_entero;

    cordic_multiplicacion(a_q8, b_q8, &y, &iteraciones);
    desbordamiento = reducir_q78(&y, &y_q78);

    printf("Iteraciones realizadas: %i\n", iteraciones);
    printf("Acumulador y (hi:lo): %04X:%04X\n", y.hi & 0xFFFF, y.lo & 0xFFFF);
    printf("Resultado directo (float original): %f\n", a * b);
    // se divide por 65536 ya que se multiplico por 2^8 dos veces (una para cada factor)
    printf("Resultado ideal cuantizado: %f\n", (float)((int32_t)a_q8 * b_q8) / 65536.0f);

    if (desbordamiento) {
        printf("DESBORDAMIENTO: el resultado no entra en Q7.8 (maximo 127.996)\n");
        return 0;
    }

    resultado = (float)y_q78 / 256.0f;
    printf("Resultado en formato Q7.8: %i\n", y_q78);
    printf("Resultado convertido en decimal: %f\n", resultado);

    return 0;
}