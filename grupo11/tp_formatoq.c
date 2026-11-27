/*
 * TP punto fijo - actividades en alto nivel
 *   Numero A -> Q3.12 (1 signo, 3 enteros, 12 fraccionarios)  rango [-8, 8)
 *   Numero B -> Q7.8  (1 signo, 7 enteros,  8 fraccionarios)  rango [-128, 128)
 * Compilar:            gcc -Wall -o tp tp_qformat.c -lm
 * Depurar con gdb:     gcc -g -DDEBUG -o tp tp_qformat.c -lm   y   gdb ./tp
 *   (en gdb:  run  |  watch a_q  |  display b_q  |  continue  |  info locals)
 * Los BP() son los puntos de interrupcion (solo actuan con -DDEBUG, bajo gdb).
 * En VS Code / CLion se puede poner un breakpoint en cada linea marcada BP().
 */
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <math.h>
#ifdef DEBUG
#include <signal.h>
#define BP() raise(SIGTRAP)
#else
#define BP()
#endif

#define NA 12   /* bits fraccionarios de A (Q3.12) */
#define NB 8    /* bits fraccionarios de B (Q7.8)  */

/* Punto 2: flotante -> entero de 16 bits en Qm.n (casting) */
static int16_t a_q_fmt(double x, int n, int *ovf)
{
    double v = x * (double)(1 << n);                 /* x * 2^n               */
    if (v > 32767.0 || v < -32768.0) { *ovf = 1; v = v > 0 ? 32767.0 : -32768.0; }
    return (int16_t)lround(v);                       /* casting a 16 bits     */
}

/* Punto 3: Qa.from -> Qb.to.  Mas fraccionarios: v * 2^(to-from) (corrimiento
 * a la izquierda).  Menos fraccionarios: v >> (from-to) (corrimiento aritmetico
 * a la derecha, redondea hacia -infinito).  Satura si no entra en 16 bits. */
static int16_t q_convertir(int16_t v, int from, int to, int *ovf)
{
    int32_t t = v;
    if (to > from) t = t * (1 << (to - from));
    else           t = t >> (from - to);
    if (t > 32767)  { t = 32767;  *ovf = 1; }
    if (t < -32768) { t = -32768; *ovf = 1; }
    return (int16_t)t;
}

/* Punto 4: Qa.na x Qb.nb = producto de 32 bits con (na+nb) fraccionarios.
 * Para dejarlo en Q?.nr se desplaza a la derecha (na+nb-nr) bits, sumando
 * antes 2^(s-1) para redondear al mas cercano (sobre el modulo). */
static int16_t q_mul(int16_t a, int na, int16_t b, int nb, int nr, int *ovf)
{
    int32_t p = (int32_t)a * (int32_t)b;
    int s = na + nb - nr;
    int neg = p < 0;
    int64_t m = llabs((long long)p);
    m = (m + ((int64_t)1 << (s - 1))) >> s;
    if (m > 32767) { *ovf = 1; m = neg ? 32768 : 32767; }
    return (int16_t)(neg ? -m : m);
}

/* Punto 5: a/b con la mayor resolucion posible.  El formato del cociente se
 * elige segun su tamano real: ibits = bits enteros necesarios para |a/b|; los
 * 15-ibits restantes son fraccionarios (Q ibits.(15-ibits)).  El dividendo se
 * desplaza s = nr + nb - na bits a la izquierda antes de dividir enteros. */
static int16_t q_div(int16_t a, int na, int16_t b, int nb, int *nr_out)
{
    int64_t ma = llabs((long long)a), mb = llabs((long long)b);
    int64_t iq = (ma << nb) / (mb << na);            /* parte entera de |a/b| */
    int ibits = 0;
    while ((iq >> ibits) > 0) ibits++;
    int nr = 15 - ibits;                             /* fraccionarios del res. */
    int s = nr + nb - na;
    int64_t q = (s >= 0) ? (ma << s) / mb : ma / (mb << -s);   /* trunca a 0  */
    *nr_out = nr;
    return (int16_t)(((a < 0) != (b < 0)) ? -q : q);
}

static void mostrar(const char *nom, int16_t v, int n)
{
    printf("  %-10s raw=%6d (0x%04X)  Q%d.%-2d = %.6f\n",
           nom, v, (uint16_t)v, 15 - n, n, v / (double)(1 << n));
}

int main(void)
{
    double a, b;
    int ovf = 0;

    /* Punto 1: ingreso de dos numeros con coma */
    printf("Ingrese A (Q3.12, entre -8 y 7.99976) y B (Q7.8, entre -128 y 127.996): ");
    if (scanf("%lf %lf", &a, &b) != 2) { printf("Entrada invalida.\n"); return 1; }
    BP();                                            /* BP1: vigilar a, b      */

    /* Punto 2: cada numero en un Q distinto */
    int16_t a_q = a_q_fmt(a, NA, &ovf);              /* A en Q3.12 */
    int16_t b_q = a_q_fmt(b, NB, &ovf);              /* B en Q7.8  */
    if (ovf) { printf("Algun numero esta fuera de rango.\n"); return 1; }
    printf("\nPunto 2 - representacion:\n");
    mostrar("A (Q3.12)", a_q, NA);
    mostrar("B (Q7.8)", b_q, NB);
    BP();                                            /* BP2: vigilar a_q, b_q  */

    /* Punto 3: compatibilizar formatos (ambos a Q7.8) y sumar / restar */
    int16_t a_78 = q_convertir(a_q, NA, NB, &ovf);   /* Q3.12 -> Q7.8: >> 4    */
    int ovs = 0, ovr = 0;
    int32_t sum = (int32_t)a_78 + b_q, dif = (int32_t)a_78 - b_q;
    if (sum > 32767 || sum < -32768) { ovs = 1; sum = sum > 0 ? 32767 : -32768; }
    if (dif > 32767 || dif < -32768) { ovr = 1; dif = dif > 0 ? 32767 : -32768; }
    printf("\nPunto 3 - A pasado a Q7.8 con corrimiento aritmetico a la derecha de %d bits:\n", NA - NB);
    mostrar("A (Q7.8)", a_78, NB);
    int ovb = 0;
    int16_t b_312 = q_convertir(b_q, NB, NA, &ovb);  /* Q7.8 -> Q3.12: << 4    */
    printf("  B en Q3.12 (corrimiento a la izquierda de %d bits): %s\n", NA - NB,
           ovb ? "no entra (|B| >= 8)" : "entra");
    if (!ovb) mostrar("B (Q3.12)", b_312, NA);
    printf("  Suma  A+B (Q7.8): raw=%d -> %.6f  (real %.6f)%s\n", (int)sum, sum / 256.0, a + b, ovs ? "  [DESBORDE]" : "");
    printf("  Resta A-B (Q7.8): raw=%d -> %.6f  (real %.6f)%s\n", (int)dif, dif / 256.0, a - b, ovr ? "  [DESBORDE]" : "");
    BP();                                            /* BP3: vigilar a_78, sum, dif */

    /* Punto 4: multiplicacion, resultado en Q7.8 */
    int ovm = 0;
    int16_t prod = q_mul(a_q, NA, b_q, NB, 8, &ovm); /* (na+nb-nr) = 12 bits   */
    printf("\nPunto 4 - A*B: producto de 32 bits con %d fraccionarios, desplazado %d bits a la derecha (con redondeo) -> Q7.8\n",
           NA + NB, NA + NB - 8);
    mostrar("A*B", prod, 8);
    printf("  real %.6f%s\n", a * b, ovm ? "  [DESBORDE]" : "");
    BP();                                            /* BP4: vigilar prod      */

    /* Punto 5: division */
    printf("\nPunto 5 - A/B:\n");
    if (b_q == 0) printf("  B = 0: division no definida.\n");
    else {
        int nr;
        int16_t q = q_div(a_q, NA, b_q, NB, &nr);
        mostrar("A/B", q, nr);
        printf("  real %.6f   error %.2e   (resolucion 1/2^%d = %.2e)\n",
               a / b, fabs(q / (double)(1 << nr) - a / b), nr, 1.0 / (1 << nr));
        BP();                                        /* BP5: vigilar q, nr     */
    }
    return 0;
}
