// =====================================================================
// Lab 3a - Actividades en lenguaje de alto nivel (puntos 1 a 5) - C++
// Arquitectura de Computadoras (IC221) - FI-UNaM - 2026
//
// x se guarda en Q3.12 y y en Q7.8 (formatos distintos, como pide el punto 2).
// Compilar:  g++ -std=c++14 -Wall -g -o lab3a lab3a.cpp
// Depurar:   poner breakpoints en las lineas marcadas con  // BP
//            y vigilar (watch) las variables que se indican al lado.
// =====================================================================
#include <cstdint>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <string>

// Muestra un entero de 16 bits en hexa con 4 digitos (estilo LC-3: x1B33)
std::string hex16(int v)
{
    std::ostringstream s;
    s << 'x' << std::hex << std::uppercase << std::setw(4) << std::setfill('0')
      << static_cast<uint16_t>(v);
    return s.str();
}

// Lo mismo para 32 bits (el producto Q20): xFFC2CD40
std::string hex32(int32_t v)
{
    std::ostringstream s;
    s << 'x' << std::hex << std::uppercase << std::setw(8) << std::setfill('0')
      << static_cast<uint32_t>(v);
    return s.str();
}

// Formato Q -> numero con coma, solo para mostrar: N * 2^-n
double q_a_real(int64_t q, int n) { return static_cast<double>(q) / static_cast<double>(1LL << n); }

// --- Punto 2: float -> formato Q (casting a entero de 16 bits) ---------
// Multiplicar por 2^n corre la coma n lugares; el cast se queda con la
// parte entera (trunca hacia 0). Antes se controla el rango (saturacion).
int16_t float_a_q(float v, int n, bool& desborde)
{
    float escalado = v * static_cast<float>(1 << n);   // v * 2^n
    desborde = (escalado > 32767.0f || escalado < -32768.0f);
    if (escalado > 32767.0f)  escalado = 32767.0f;     // saturar
    if (escalado < -32768.0f) escalado = -32768.0f;
    return static_cast<int16_t>(escalado);             // casting
}

// --- Punto 3: cambiar de formato Q --------------------------------------
// Q3.12 -> Q7.8: se pierden 4 bits fraccionarios -> corrimiento a la
// derecha de 4 bits. En C++20 >> sobre un negativo es aritmetico (copia el
// signo) por norma. Nunca desborda.
int16_t q12_a_q8(int16_t x) { return static_cast<int16_t>(x >> 4); }

// Q7.8 -> Q3.12: se ganan 4 bits fraccionarios -> corrimiento a la
// izquierda de 4 bits (= multiplicar por 16). Desborda si |y| >= 8.
int16_t q8_a_q12(int16_t y, bool& desborde)
{
    desborde = (y > 2047 || y < -2048);
    return static_cast<int16_t>(y * 16);
}

int main()
{
    float x, y;                   // punto 1: numeros con coma
    bool ovx, ovy, ovy12;

    // ---- Punto 1 ----
    std::cout << "x = ";
    if (!(std::cin >> x)) return 1;
    std::cout << "y = ";
    if (!(std::cin >> y)) return 1;
    std::cout << std::fixed << std::setprecision(8);
    std::cout << "\n[1] x = " << x << "   y = " << y << "   (float)\n";     // BP: x, y

    // ---- Punto 2 ----
    int16_t xq12 = float_a_q(x, 12, ovx);                                // BP: xq12
    int16_t yq8  = float_a_q(y, 8, ovy);                                 // BP: yq8
    std::cout << "[2] x en Q3.12 = " << std::setw(6) << xq12 << " (" << hex16(xq12)
              << ") -> representa " << q_a_real(xq12, 12) << (ovx ? "  DESBORDA Q3.12" : "") << '\n';
    std::cout << "    y en Q7.8  = " << std::setw(6) << yq8 << " (" << hex16(yq8)
              << ") -> representa " << q_a_real(yq8, 8) << (ovy ? "  DESBORDA Q7.8" : "") << '\n';

    // ---- Punto 3: se compatibiliza al formato de MAYOR RANGO (Q7.8) ----
    int16_t xq8  = q12_a_q8(xq12);                                       // BP: xq8
    int16_t yq12 = q8_a_q12(yq8, ovy12);
    int16_t sumaq8  = static_cast<int16_t>(xq8 + yq8);
    int16_t restaq8 = static_cast<int16_t>(xq8 - yq8);                   // BP: sumaq8, restaq8
    std::cout << "[3] x en Q7.8  = " << std::setw(6) << xq8 << " (" << hex16(xq8)
              << ") -> " << q_a_real(xq8, 8) << "   (x >> 4)\n";
    std::cout << "    y en Q3.12 = " << std::setw(6) << yq12 << " (" << hex16(yq12)
              << ") -> " << q_a_real(yq12, 12) << "   (y << 4)" << (ovy12 ? "  NO ENTRA: |y| >= 8" : "") << '\n';
    std::cout << "    x+y en Q7.8 = " << std::setw(6) << sumaq8 << " (" << hex16(sumaq8)
              << ") -> " << q_a_real(sumaq8, 8) << '\n';
    std::cout << "    x-y en Q7.8 = " << std::setw(6) << restaq8 << " (" << hex16(restaq8)
              << ") -> " << q_a_real(restaq8, 8) << '\n';

    // ---- Punto 4: Q12 * Q8 = Q20 (en 32 bits) ----
    int32_t prodq20 = static_cast<int32_t>(xq12) * static_cast<int32_t>(yq8);  // BP: prodq20
    int32_t ajustado = prodq20 >> 12;                    // Q20 -> Q8: 12 a la derecha
    int16_t prodq8 = static_cast<int16_t>(ajustado);
    std::cout << "[4] x*y en Q20 = " << prodq20 << " (" << hex32(prodq20) << ") -> " << q_a_real(prodq20, 20) << '\n';
    std::cout << "    x*y en Q7.8 = " << std::setw(6) << prodq8 << " (" << hex16(prodq8)
              << ") -> " << q_a_real(prodq8, 8) << "   (>> 12)"
              << ((ajustado > 32767 || ajustado < -32768) ? "  NO ENTRA EN Q7.8" : "") << '\n';

    // ---- Punto 5: division con la mayor resolucion posible ------------
    // Qa / Qb = Q(a-b): Q12 / Q8 daria Q4 (solo 4 bits fraccionarios).
    // Para no perder resolucion se agranda el dividendo: mas bits y
    // corrimiento de 16 a la izquierda -> Q28 / Q8 = Q20 (20 bits fracc.).
    // (int64_t solo para cubrir el caso extremo -32768 / -1.)
    // Despues se elige el formato de 16 bits con MAS bits fraccionarios en
    // el que entre el cociente: se cuentan los bits enteros que necesita.
    if (yq8 == 0) {
        std::cout << "[5] division por cero\n";
    } else {
        int64_t dividendo = static_cast<int64_t>(xq12) * 65536;   // Q28
        int64_t cocq20 = dividendo / yq8;                          // Q20
        int m = 0;                                                 // bits enteros
        while ((cocq20 >> (20 - (15 - m))) > 32767 || (cocq20 >> (20 - (15 - m))) < -32768)
            m++;                                                   // hasta que entre
        int n = 15 - m;                                            // bits fraccionarios
        int16_t coc = static_cast<int16_t>(cocq20 >> (20 - n));    // BP: cocq20, m, coc
        double real = q_a_real(xq12, 12) / q_a_real(yq8, 8);
        std::cout << "[5] x/y en Q20 = " << cocq20 << " -> " << q_a_real(cocq20, 20) << '\n';
        std::cout << "    formato elegido: Q" << m << '.' << n << "  -> " << std::setw(6) << coc
                  << " (" << hex16(coc) << ") -> " << q_a_real(coc, n)
                  << std::scientific << std::setprecision(2) << "  (error " << q_a_real(coc, n) - real << ")\n";
    }
    return 0;
}
