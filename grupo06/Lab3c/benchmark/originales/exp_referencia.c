/* Laboratorio 3 - EXP multiplicativa de alta radix (base 16).
 * Compilar: gcc -std=c11 -Wall -Wextra -O2 exp_alta_radix.c -o exp_lab -lm
 * Ejecutar: exp_lab 1.0   |   exp_lab --traza 1.0   |   exp_lab --pruebas
 *
 * Entrada: Q3.12 con signo (int16_t), valor real = entero / 4096.
 * Salida:  Q7.8  con signo (int16_t), valor real = entero / 256.
 * Convencion Q: el bit de signo se cuenta por separado.
 * El calculo usa enteros. exp() solo se usa para validar en el programa PC.
 * Los temporales de 32/64 bits requeriran varias palabras en la LC-3.
 *
 * RECORDATORIO DE PUNTO FIJO:
 *   entero_guardado = redondeo(valor_real * escala)
 *   valor_real     = entero_guardado / escala
 * No hay una coma almacenada en memoria: la escala define su posicion.
 * Ejemplo de entrada: 1.5 se guarda como 6144, porque 6144/4096 = 1.5.
 * Ejemplo de salida:  e^1 se aproxima por 696/256 = 2.71875.
 *
 * Antes de sumar o restar, ambos operandos deben tener la misma escala.
 * La entrada tiene escala 2^12; el nucleo usa escala 2^30 para reducir
 * errores acumulados; la salida se redondea finalmente a escala 2^8.
 * Estos formatos son elecciones de diseno para el ejercicio EXP del PDF.
 */
#include <errno.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define ITERACIONES 6
#define UNO_Q30 UINT32_C(1073741824)
#define LN2_Q30 INT64_C(744261118)
#define MAX_X_SIN_SATURAR 19873

/* Rangos de los formatos externos:
 * Q3.12: [-8, 7.999755859375], paso 1/4096.
 * Q7.8:  [-128, 127.99609375], paso 1/256.
 * EXP devuelve solamente resultados no negativos.
 * 19873/4096 es el mayor x Q3.12 cuyo e^x cabe en la salida.
 */

typedef enum { EXP_OK, EXP_SATURADO, EXP_REDONDEADO_A_CERO } Estado;
typedef struct {
    int16_t valor;
    Estado estado;
    unsigned iteraciones;
} Resultado;

/* Tabla[j-1][d] = redondeo(ln(1 + d*16^(-j)) * 2^30).
 * Constantes precalculadas: no se necesita log() al ejecutar el algoritmo.
 * Se admite d=16 como digito redundante para asegurar la convergencia.
 */
static const uint32_t tabla_log[ITERACIONES][17] = {
    {0, 65095192, 126468572, 184522808, 239598564, 291986604, 341937090, 389666807, 435364845, 479197128, 521310048, 561833416, 600882877, 638561895, 674963409, 710171213, 744261118},
    {0, 4186133, 8356010, 12509755, 16647494, 20769348, 24875440, 28965890, 33040817, 37100337, 41144567, 45173622, 49187615, 53186658, 57170862, 61140337, 65095192},
    {0, 262112, 524160, 786144, 1048064, 1309921, 1571713, 1833442, 2095107, 2356708, 2618245, 2879719, 3141129, 3402475, 3663758, 3924978, 4186133},
    {0, 16384, 32768, 49151, 65534, 81917, 98300, 114682, 131064, 147446, 163828, 180209, 196590, 212971, 229352, 245732, 262112},
    {0, 1024, 2048, 3072, 4096, 5120, 6144, 7168, 8192, 9216, 10240, 11264, 12288, 13312, 14336, 15360, 16384},
    {0, 64, 128, 192, 256, 320, 384, 448, 512, 576, 640, 704, 768, 832, 896, 960, 1024}
};

/* Multiplicar por un digito pequeno usando sumas y desplazamientos. */
static uint64_t multiplicar_digito(uint32_t valor, unsigned digito)
{
    uint64_t suma = 0, termino = valor;
    while (digito != 0) {
        if (digito & 1u) suma += termino;
        termino <<= 1;
        digito >>= 1;
    }
    return suma;
}

/* Rutina que se puede estudiar y luego traducir a assembly.
 * traza=NULL desactiva los mensajes de depuracion.
 * Solo los mensajes de traza convierten temporales a double.
 */
Resultado exp_q3_12(int16_t entrada, FILE *traza)
{
    Resultado resultado = {0, EXP_OK, 0};
    if (entrada > MAX_X_SIN_SATURAR) {
        resultado.valor = INT16_MAX;
        resultado.estado = EXP_SATURADO;
        return resultado;
    }

    /* x = k*ln(2) + r, con 0 <= r < ln(2).
     * Para pasar de escala 2^12 a 2^30, multiplicamos por 2^(30-12).
     * El valor representado no cambia, solo cambia el entero que lo guarda.
     * Multiplicar evita el desplazamiento izquierdo de negativos,
     * que tiene comportamiento indefinido en C11.
     * La division de C trunca hacia cero: se corrige para obtener piso.
     */
    int64_t x_q30 = (int64_t)entrada * INT64_C(262144);
    int k = (int)(x_q30 / LN2_Q30);
    int64_t residuo = x_q30 - (int64_t)k * LN2_Q30;
    if (residuo < 0) {
        --k;
        residuo += LN2_Q30;
    }
    uint32_t acumulador = UNO_Q30; /* E=1, escala interna 2^30. */
    if (traza) {
        fprintf(traza, "Reduccion: k=%d, r=%.10f\n", k,
                (double)residuo / UNO_Q30);
        fprintf(traza, "Cada entero interno se interpreta dividiendolo por 2^30.\n");
        fprintf(traza, "Paso  Digito  Residuo entero  Residuo real     E entero     E real\n");
    }

    for (unsigned j = 1; j <= ITERACIONES; ++j) {
        /* Mayor d tal que ln(1+d*16^-j) <= residuo.
         * La tabla y el residuo tienen escala 2^30: podemos compararlos
         * y restarlos directamente sin desalinear la coma.
         */
        unsigned d = 16;
        while (d > 0 && (int64_t)tabla_log[j - 1][d] > residuo) --d;
        residuo -= tabla_log[j - 1][d];

        /* E <- E*(1+d*16^-j) = E + (E*d)/2^(4j).
         * Se redondea al entero mas cercano en la escala interna.
         * d es un entero sin parte fraccionaria: E*d conserva escala 2^30.
         * Dividir por 2^(4j) aplica el factor 16^-j del algoritmo.
         * Se suma medio divisor antes de desplazar para redondear.
         * El temporal de 64 bits evita perder los bits altos del producto.
         */
        unsigned bits = 4u * j;
        uint64_t producto = multiplicar_digito(acumulador, d);
        acumulador += (uint32_t)((producto + (UINT64_C(1) << (bits - 1))) >> bits);
        ++resultado.iteraciones;
        if (traza) fprintf(traza, "%4u  %6u  %14lld  %.10f  %10llu  %.10f\n", j, d,
                           (long long)residuo, (double)residuo / UNO_Q30,
                           (unsigned long long)acumulador, (double)acumulador / UNO_Q30);
    }

    /* e^x = E*2^k. Pasar de 30 a 8 bits fraccionarios:
     * salida_entera = redondeo(E_entero / 2^(22-k)).
     * Los 22 bits provienen de 30-8. Se incorpora k en el mismo ajuste
     * para aplicar 2^k y redondear una sola vez a la escala de salida.
     * En el dominio admitido, k pertenece a [-12,6], bits a [16,34].
     */
    unsigned bits = (unsigned)(22 - k);
    uint64_t salida = ((uint64_t)acumulador + (UINT64_C(1) << (bits - 1))) >> bits;
    if (salida > INT16_MAX) {
        resultado.valor = INT16_MAX;
        resultado.estado = EXP_SATURADO;
    } else {
        resultado.valor = (int16_t)salida;
        if (salida == 0) resultado.estado = EXP_REDONDEADO_A_CERO;
    }
    return resultado;
}

static const char *nombre_estado(Estado estado)
{
    if (estado == EXP_SATURADO) return "saturado: excede Q7.8";
    if (estado == EXP_REDONDEADO_A_CERO) return "redondeado a cero: menor que medio paso Q7.8";
    return "OK";
}

/* Barrido exhaustivo de las 65536 entradas Q3.12.
 * El error se mide contra exp(x cuantizado), excluyendo saturacion.
 */
static int pruebas(void)
{
    double max_abs = 0, min_abs = HUGE_VAL, max_rel = 0, peor_x = 0;
    unsigned saturados = 0, ceros = 0, diferencias = 0, fallos = 0;
    int16_t anterior = 0;
    for (int32_t n = INT16_MIN; n <= INT16_MAX; ++n) {
        Resultado r = exp_q3_12((int16_t)n, NULL);
        double x = (double)n / 4096.0, referencia = exp(x);
        if (n > INT16_MIN && r.valor < anterior) ++fallos;
        anterior = r.valor;
        if (r.estado == EXP_SATURADO) {
            ++saturados;
            if (n <= MAX_X_SIN_SATURAR || r.valor != INT16_MAX || r.iteraciones != 0) ++fallos;
            continue;
        }
        if (n > MAX_X_SIN_SATURAR || r.iteraciones != ITERACIONES) ++fallos;
        double error = fabs((double)r.valor / 256.0 - referencia);
        if (error < min_abs) min_abs = error;
        if (error > max_abs) { max_abs = error; peor_x = x; }
        if (error / referencia > max_rel) max_rel = error / referencia;
        if (r.estado == EXP_REDONDEADO_A_CERO) ++ceros;
        if ((long)r.valor != lround(referencia * 256.0)) ++diferencias;
        if (error > 1.0 / 256.0) ++fallos;
    }
    if (exp_q3_12(0, NULL).valor != 256) ++fallos;
    printf("Entradas verificadas: 65536\nSaturadas: %u\nRedondeadas a cero: %u\n", saturados, ceros);
    printf("Error absoluto minimo (sin saturacion): %.12g\n", min_abs);
    printf("Error absoluto maximo (sin saturacion): %.12g en x=%.12f\n", max_abs, peor_x);
    printf("Error relativo maximo (sin saturacion): %.6f %%\n", max_rel * 100);
    printf("Diferencias frente al redondeo ideal Q7.8: %u\n", diferencias);
    printf("Fallos (monotonia, estados, iteraciones o error > 1 LSB): %u\n", fallos);
    return fallos ? EXIT_FAILURE : EXIT_SUCCESS;
}

int main(int argc, char **argv)
{
    char linea[128], *fin;
    const char *texto;
    FILE *traza = NULL;
    if (argc == 2 && strcmp(argv[1], "--pruebas") == 0) return pruebas();
    if (argc == 3 && strcmp(argv[1], "--traza") == 0) {
        texto = argv[2];
        traza = stdout;
    } else if (argc == 2) {
        texto = argv[1];
    } else if (argc == 1) {
        printf("Ingrese x en [-8, 7.999755859375], usando punto decimal: ");
        if (!fgets(linea, sizeof linea, stdin)) return EXIT_FAILURE;
        texto = linea;
    } else {
        fprintf(stderr, "Uso: %s [x | --traza x | --pruebas]\n", argv[0]);
        return EXIT_FAILURE;
    }
    errno = 0;
    double x = strtod(texto, &fin);
    if (fin == texto) {
        fprintf(stderr, "Entrada invalida. Use un numero con punto decimal.\n");
        return EXIT_FAILURE;
    }
    while (*fin == ' ' || *fin == '\t' || *fin == '\r' || *fin == '\n') ++fin;
    if (errno == ERANGE || *fin || !isfinite(x) || x < -8 || x > 32767.0 / 4096.0) {
        fprintf(stderr, "Entrada fuera de Q3.12 o invalida.\n");
        return EXIT_FAILURE;
    }
    /* Frontera de entrada: del decimal ingresado al entero Q3.12.
     * lround redondea al entero mas cercano, con empates alejandose de cero.
     * El rango ya se comprobo antes de convertir a int16_t.
     */
    int16_t entrada = (int16_t)lround(x * 4096.0);
    double x_q = (double)entrada / 4096.0;
    Resultado r = exp_q3_12(entrada, traza);
    printf("x solicitado: %.12f\nx Q3.12: %d -> %.12f\n", x, (int)entrada, x_q);
    /* Frontera de salida: dividir por 256 permite mostrar el valor real.
     * Esta conversion a double no forma parte del calculo de EXP.
     */
    printf("Resultado Q7.8: %d -> %.12f\n", (int)r.valor, (double)r.valor / 256.0);
    printf("Referencia exp(x Q3.12): %.12f\n", exp(x_q));
    printf("Error absoluto respecto de x Q3.12: %.12f\n", fabs((double)r.valor / 256.0 - exp(x_q)));
    printf("Iteraciones: %u\nEstado: %s\n", r.iteraciones, nombre_estado(r.estado));
    return EXIT_SUCCESS;
}