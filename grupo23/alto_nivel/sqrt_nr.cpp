// =====================================================================
// Lab 3b - Grupo 23 - SQRT por el metodo NON-RESTORING (alto nivel, C++)
// Arquitectura de Computadoras (IC221) - FI-UNaM - 2026
//
// Algoritmo: raiz cuadrada entera "no restauradora" de Li y Chu (1996).
// Saca UN bit de la raiz por iteracion usando solo sumas, restas y
// corrimientos (lo mismo que tiene la LC-3).
//
// Compilar:  g++ -std=c++14 -Wall -g -o sqrt_nr sqrt_nr.cpp
//            (tambien compila con -std=c++17 o -std=c++20)
// Uso:       ./sqrt_nr traza <x> <n> <k>   -> muestra cada iteracion
//            ./sqrt_nr analisis            -> barre todas las entradas
//            ./sqrt_nr verificar           -> compara con el modelo LC-3
//   x: numero con coma, n: bits fraccionarios del formato de entrada
//      (par, entre 0 y 14), k: iteraciones (bits de la raiz), entre 8 y 15.
//   Solo con k <= 13 todos los valores intermedios entran en 16 bits con
//   signo, que es lo que necesita la LC-3 (el modulo usa k = 13).
// =====================================================================
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <string>

// Lo que devuelve el nucleo del algoritmo
struct ResultadoRaiz {
    uint32_t raiz;        // Q: raiz entera (k bits)
    int32_t  resto;       // R = D - Q*Q, ya corregido (0 <= R <= 2Q)
    int32_t  maxInterm;   // mayor |valor intermedio| (para ver si entra en 16 bits)
};

const int K_MIN = 8;      // con k < 8 el corrimiento 2k - 16 seria negativo
const int K_MAX = 15;     // con k > 15 el radicando de 2k bits no entra en 32 bits

std::string hex16(int v)
{
    std::ostringstream s;
    s << 'x' << std::hex << std::uppercase << std::setw(4) << std::setfill('0')
      << static_cast<uint16_t>(v);
    return s.str();
}

// ---------------------------------------------------------------------
// Nucleo: raiz entera de D (radicando de 2k bits), k iteraciones.
//   R = resto parcial (con signo), Q = raiz parcial.
//   En cada iteracion:
//     1) se "bajan" los 2 bits siguientes de D al resto:  R = 4R + par
//     2) si el resto era >= 0  ->  R = R - (4Q + 1)   (probar con un 1)
//        si el resto era <  0  ->  R = R + (4Q + 3)   (corregir y probar)
//     3) el nuevo bit de la raiz es 1 si R >= 0, 0 si R < 0.
//   No hay paso de "restaurar" (volver a sumar lo restado): el error se
//   arrastra con signo y se corrige en la iteracion siguiente.
// ---------------------------------------------------------------------
ResultadoRaiz raiz_nr(uint32_t D, int k, bool traza = false)
{
    int32_t R = 0, mx = 0;
    uint32_t Q = 0;
    for (int i = k - 1; i >= 0; i--) {
        int32_t par = static_cast<int32_t>((D >> (2 * i)) & 3);   // 2 bits de D
        int32_t T = R * 4 + par;                                  // R << 2 | par
        if (R >= 0) R = T - static_cast<int32_t>(4 * Q + 1);
        else        R = T + static_cast<int32_t>(4 * Q + 3);
        Q = 2 * Q + (R >= 0 ? 1 : 0);                             // nuevo bit
        mx = std::max({mx, std::abs(T), std::abs(R), static_cast<int32_t>(4 * Q + 3)});
        if (traza)
            std::cout << "  it " << std::setw(2) << k - i << " | par " << (par >> 1) << (par & 1)
                      << " | R = " << std::setw(7) << R << " | bit " << (R >= 0 ? 1 : 0)
                      << " | Q = " << std::setw(6) << Q << " (" << hex16(static_cast<int>(Q)) << ")\n";
    }
    if (R < 0) R += static_cast<int32_t>(2 * Q + 1);   // correccion final del resto
    return {Q, R, mx};                                  // ahora R = D - Q*Q
}

// ---------------------------------------------------------------------
// Envoltura de punto fijo.
//   Entrada x en Qm.n (n par, x >= 0). Con D = x << (2k - 16) la raiz
//   sale con f = n/2 + k - 8 bits fraccionarios:
//       sqrt(X * 2^-n) = sqrt(X * 2^(2k-16)) * 2^-(n/2 + k - 8)
//   (en la LC-3 esto es gratis: X va en la parte alta del radicando y
//   la parte baja es 0).
//   redondeo = true: si R > Q se suma 1 (redondeo al mas cercano), porque
//   (Q + 1/2)^2 = Q^2 + Q + 1/4  ->  la raiz real supera Q + 1/2 si R > Q.
//   Devuelve -32768 (x8000) si x < 0 (no hay raiz real) o si k esta
//   fuera de [K_MIN, K_MAX].
// ---------------------------------------------------------------------
int16_t sqrt_q(int16_t x, int k, bool redondeo, int32_t* maxInterm = nullptr, bool traza = false)
{
    if (x < 0 || k < K_MIN || k > K_MAX) return INT16_MIN;
    uint32_t D = static_cast<uint32_t>(x) << (2 * k - 16);
    ResultadoRaiz r = raiz_nr(D, k, traza);
    if (maxInterm) *maxInterm = r.maxInterm;
    uint32_t Q = r.raiz;
    if (redondeo && r.resto > static_cast<int32_t>(Q)) Q++;
    return static_cast<int16_t>(Q);
}

// ---------------------------------------------------------------------
// Modelo del modulo SQRT_NR en assembly (modulo_sqrt_nr.asm, version con
// pila): reproduce sus ramas con aritmetica de 16 bits, devuelve lo que
// quedaria en R0 y cuenta las instrucciones LC-3 ejecutadas (con RET).
// ---------------------------------------------------------------------
int16_t modelo_lc3(int16_t x, int& instrucciones)
{
    int n = 2;                                   // ADD R0,R0,#0 ; BRn
    if (x < 0) { instrucciones = n + 2; return INT16_MIN; }   // LD R0 ; RET
    n += 5 + 4;                                  // apilar R1-R4 ; inicializar
    uint16_t r0 = static_cast<uint16_t>(x);
    int16_t R = 0;
    uint16_t Q = 0;
    for (int it = 0; it < 13; it++) {
        int b1 = (r0 >> 15) & 1; r0 = static_cast<uint16_t>(r0 << 1);
        int b0 = (r0 >> 15) & 1; r0 = static_cast<uint16_t>(r0 << 1);
        n += 17 + b1 + b0;                       // bajar el par, 4Q, test, nuevo bit, contador
        int16_t T  = static_cast<int16_t>(R * 4 + b1 * 2 + b0);
        int16_t q4 = static_cast<int16_t>(4 * Q);
        if (R >= 0) { n += 5; R = static_cast<int16_t>(T - q4 - 1); }
        else        { n += 2; R = static_cast<int16_t>(T + q4 + 3); }
        Q = static_cast<uint16_t>(2 * Q + (R >= 0 ? 1 : 0));
        if (R >= 0) n += 1;
    }
    n += 2;
    if (R < 0) { n += 3; R = static_cast<int16_t>(R + 2 * Q + 1); }
    n += 4;
    if (static_cast<int16_t>(R - Q) > 0) { n += 1; Q++; }
    n += 1 + 6;                                  // ADD R0 ; desapilar y RET
    instrucciones = n;
    return static_cast<int16_t>(Q);
}

// Recorre las 32 768 entradas positivas de un formato y mide el error
void analisis(int n, int k, bool redondeo)
{
    const int f = n / 2 + k - 8;
    double maxErr = 0, maxRel = 0, suma = 0;
    int32_t mx = 0, m = 0;
    long exactos = 0;
    int16_t ymax = 0;
    for (int32_t X = 0; X <= 32767; X++) {
        int16_t y = sqrt_q(static_cast<int16_t>(X), k, redondeo, &m);
        mx = std::max(mx, m);
        ymax = std::max(ymax, y);
        double real = std::sqrt(X / static_cast<double>(1 << n));
        double err = std::fabs(y / static_cast<double>(1 << f) - real);
        suma += err;
        maxErr = std::max(maxErr, err);
        if (X > 0) maxRel = std::max(maxRel, err / real);
        if (err == 0) exactos++;
    }
    std::cout << std::setprecision(6) << std::fixed
              << "Q" << 15 - n << '.' << n << " -> Q" << 15 - f << '.' << f << " | k=" << std::setw(2) << k
              << " | " << (redondeo ? "redondeo" : "truncado")
              << " | entrada [0, " << 32767 / static_cast<double>(1 << n) << "] salida [0, "
              << ymax / static_cast<double>(1 << f) << "]" << std::scientific << std::setprecision(3)
              << " | resolucion " << 1.0 / (1 << f)
              << " | error max " << maxErr << " (" << std::fixed << std::setprecision(2) << maxErr * (1 << f)
              << " LSB) medio " << std::scientific << std::setprecision(3) << suma / 32768
              << " | rel max " << std::setprecision(2) << maxRel
              << " | exactos " << exactos << " | max|interm| " << mx
              << (mx <= 32767 ? " (entra en 16 bits)" : " (NO entra en 16 bits)") << '\n';
}

// Compara el modelo del assembly con sqrt_q (Q7.8, k = 13, redondeo) para
// las 65 536 entradas posibles e informa las instrucciones ejecutadas.
int verificar()
{
    long diferencias = 0;
    int imin = 1 << 30, imax = 0, xmin = 0, xmax = 0, ineg = 0;
    double suma = 0;
    for (int32_t X = -32768; X <= 32767; X++) {
        int ins = 0;
        int16_t asmR0 = modelo_lc3(static_cast<int16_t>(X), ins);
        int16_t cpp   = sqrt_q(static_cast<int16_t>(X), 13, true);
        if (asmR0 != cpp) {
            if (diferencias < 5)
                std::cout << "difiere x = " << hex16(X) << ": C++ " << hex16(cpp) << ", LC-3 " << hex16(asmR0) << '\n';
            diferencias++;
        }
        if (X < 0) { ineg = ins; continue; }
        suma += ins;
        if (ins < imin) { imin = ins; xmin = X; }
        if (ins > imax) { imax = ins; xmax = X; }
    }
    std::cout << "entradas comparadas: 65536 | diferencias: " << diferencias << '\n'
              << std::fixed << std::setprecision(1)
              << "instrucciones (x >= 0): min " << imin << " (x = " << hex16(xmin) << "), max " << imax
              << " (x = " << hex16(xmax) << "), promedio " << suma / 32768 << " | (x < 0): " << ineg << '\n';
    return diferencias == 0 ? 0 : 1;
}

void uso()
{
    std::cout << "Uso: sqrt_nr traza <x> <n> <k>   (n par entre 0 y 14, k entre "
              << K_MIN << " y " << K_MAX << ")\n"
              << "     sqrt_nr analisis\n"
              << "     sqrt_nr verificar\n";
}

int main(int argc, char** argv)
{
    const std::string modo = argc >= 2 ? argv[1] : "analisis";
    if (modo == "traza") {
        if (argc < 5) { uso(); return 1; }
        double xv = std::atof(argv[2]);
        int n = std::atoi(argv[3]), k = std::atoi(argv[4]);
        if (n < 0 || n > 14 || n % 2 != 0 || k < K_MIN || k > K_MAX) { uso(); return 1; }
        double escalado = xv * (1 << n);
        if (escalado > 32767.0 || escalado < -32768.0) {
            std::cout << "x = " << xv << " no entra en Q" << 15 - n << '.' << n << '\n';
            return 1;
        }
        int16_t X = static_cast<int16_t>(escalado);
        int f = n / 2 + k - 8;
        std::cout << "x = " << xv << " en Q" << 15 - n << '.' << n << " = " << X << " (" << hex16(X)
                  << "), k = " << k << " -> raiz en Q" << 15 - f << '.' << f << '\n';
        int16_t y  = sqrt_q(X, k, false, nullptr, true);     // con traza
        int16_t yr = sqrt_q(X, k, true);
        if (X < 0) {
            std::cout << "x < 0: no hay raiz real, se devuelve " << hex16(y) << " (codigo de error)\n";
            return 0;
        }
        std::cout << std::fixed << std::setprecision(8)
                  << "truncado: " << y << " (" << hex16(y) << ") = " << y / static_cast<double>(1 << f)
                  << " | redondeado: " << yr << " (" << hex16(yr) << ") = " << yr / static_cast<double>(1 << f)
                  << " | sqrt real = " << std::sqrt(X / static_cast<double>(1 << n)) << '\n';
        return 0;
    }
    if (modo == "verificar") return verificar();
    if (modo != "analisis") { uso(); return 1; }
    // analisis: formatos de entrada habituales del benchmark
    for (int n : {8, 10, 12})
        for (int k = 12; k <= 14; k++)
            for (bool r : {false, true})
                analisis(n, k, r);
    return 0;
}
