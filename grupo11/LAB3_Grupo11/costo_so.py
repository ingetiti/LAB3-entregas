# -*- coding: utf-8 -*-
"""Estimacion de las instrucciones del sistema operativo (SO) para la ISA-G11.

En esta ISA los servicios GETC, OUT, PUTS, IN y HALT los resuelve el simulador: cada TRAP
cuenta como UNA instruccion de usuario y no se simula el codigo del SO. La catedra, en cambio,
informa para la LC-3 "usuario + SO" (357.505 + 22.074 = 379.579), donde el SO si ejecuta codigo
(rutinas que sondean el registro de estado de la pantalla, guardan y restauran registros...).

Para poder comparar, este modulo estima el costo del SO a partir de lo que SI se mide en el
simulador: cuantas veces se invoco cada servicio y cuantos caracteres emitio PUTS.

    instrucciones_SO = OUT * c_out + PUTS * c_puts + caracteres_PUTS * c_char
                       + GETC * c_getc + IN * c_in + HALT * c_halt

Los coeficientes del modelo "catedra" estan CALIBRADOS: la catedra solo publico el total (22.074)
y no el desglose por servicio, asi que se eligieron valores razonables (OUT = 6 como en el SO
de Patt y Patel; HALT ~ mensaje de parada) que reproducen exactamente ese total con la misma
secuencia de servicios del benchmark (76 OUT, 133 PUTS, 1.541 caracteres, 1 HALT).
Son una estimacion, no una medicion; se pueden editar en la interfaz.
"""

# Datos oficiales de la catedra para la LC-3 (mensaje del grupo 8).
LC3_USUARIO = 357_505
LC3_SO = 22_074
LC3_TOTAL = LC3_USUARIO + LC3_SO            # 379.579

# Secuencia de servicios del benchmark (idem en la LC-3 y en la ISA-G11).
BENCH_OUT, BENCH_PUTS, BENCH_CHARS, BENCH_HALT = 76, 133, 1541, 1

PROMPT_IN = 21                               # "Ingrese un caracter: "

COEF_CATEDRA = {
    'OUT': 6,
    'PUTS_fijo': 22,
    'PUTS_por_caracter': 12,
    'GETC': 6,
    'IN': 6 + (22 + 12 * PROMPT_IN) + 6,     # GETC + prompt por PUTS + eco por OUT
    'HALT': 200,
}
COEF_NATIVO = {k: 0 for k in COEF_CATEDRA}   # TRAP nativo: sin costo extra

MODELOS = {
    'Calibrado con la cátedra': COEF_CATEDRA,
    'Nativo (TRAP = 1 instrucción)': COEF_NATIVO,
}

SERVICIOS = ('OUT', 'PUTS', 'GETC', 'IN', 'HALT')


def llamadas(stats):
    """Cantidad de invocaciones por servicio a partir de las estadisticas del simulador."""
    t = stats.get('traps', {})
    return {s: int(t.get(s, 0)) for s in SERVICIOS}


def calcular(stats, coef):
    """Devuelve el detalle del SO estimado y los totales.

    stats: salida de Maquina.estadisticas(). coef: dict con las claves de COEF_CATEDRA.
    """
    n = llamadas(stats)
    chars = int(stats.get('puts_caracteres', 0))
    filas = [
        ('OUT', n['OUT'], 0, coef['OUT'] * n['OUT']),
        ('PUTS', n['PUTS'], chars,
         coef['PUTS_fijo'] * n['PUTS'] + coef['PUTS_por_caracter'] * chars),
        ('GETC', n['GETC'], 0, coef['GETC'] * n['GETC']),
        ('IN', n['IN'], 0, coef['IN'] * n['IN']),
        ('HALT', n['HALT'], 0, coef['HALT'] * n['HALT']),
    ]
    so = sum(f[3] for f in filas)
    usuario = int(stats['instrucciones_ejecutadas'])
    return {'filas': filas, 'so': so, 'usuario': usuario, 'total': usuario + so}


def es_benchmark(stats):
    """True si la secuencia de servicios coincide con la del benchmark de la catedra."""
    n = llamadas(stats)
    return (n['OUT'], n['PUTS'], int(stats.get('puts_caracteres', 0)), n['HALT'], n['GETC'], n['IN']) == \
           (BENCH_OUT, BENCH_PUTS, BENCH_CHARS, BENCH_HALT, 0, 0)
