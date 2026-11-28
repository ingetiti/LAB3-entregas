#!/usr/bin/env python3
import argparse
import math
from pathlib import Path

from assembler import Assembler
from simulator import Simulator


ROOT = Path(__file__).resolve().parent
ROUTINES = ROOT / "benchmark" / "real_routines.asm"


def q114(value):
    return round(value * (1 << 14)) & 0xffff


def byte_pair(value):
    return value & 0xff, (value >> 8) & 0xff


def gcd(a, b):
    while b:
        a, b = b, a % b
    return a


def integer_sqrt(value):
    return math.isqrt(value)


def parse_hex_ascii(value):
    low, high = byte_pair(value)
    first = chr(high)
    second = chr(low)
    return int(first + second, 16)


CASES = [
    ("CORDIC_DIV", "Q15", "CORDIC_DIV", 64, lambda value: (value << 8) & 0xffff),
    ("MULT_SHIFT_ADD", "Q16.16", "MULT_SHIFT_ADD", 0x0505, lambda value: byte_pair(value)[0] * byte_pair(value)[1]),
    ("POTENCIA", "entero", "POTENCIA", 5, lambda value: 1 << value),
    ("POW_MULT_SUCESIVA", "Q7.8", "POW_MULT_SUCESIVA", 3, lambda value: 2 ** value),
    ("EXP", "Q7.8", "EXP", 1, lambda value: round(math.exp(0) * 256) & 0xffff),
    ("MCM", "Q15.0", "MCM", 0x0C12, lambda value: byte_pair(value)[0] * byte_pair(value)[1] // gcd(*byte_pair(value))),
    ("MCD", "Q15.0", "MCD", 0x0C12, lambda value: gcd(*byte_pair(value))),
    ("DIVISION_LARGA", "Q7.8", "DIVISION_LARGA", 0x0101, lambda value: byte_pair(value)[1] // byte_pair(value)[0]),
    ("RAIZ_DQ16", "Q15.16", "RAIZ_DQ16", 16, integer_sqrt),
    ("CORDIC_LOG", "Q3.12", "CORDIC_LOG", 1, lambda value: round(math.log2(value)) & 0xffff),
    ("DIV_NEWTON", "Q7.8", "DIV_NEWTON", 0x0804, lambda value: byte_pair(value)[1] // byte_pair(value)[0]),
    ("LN_BORCHARDT", "Q8.7", "LN_BORCHARDT", 1, lambda value: round(math.log(value)) & 0xffff),
    ("CONVERSION_Q312_Q78", "Q3.12->Q7.8", "CONVERSION_Q312_Q78", 512, lambda value: (value >> 4) & 0xffff),
    ("MULT_BOOTH", "Q7.8", "MULT_BOOTH", 0x0505, lambda value: byte_pair(value)[0] * byte_pair(value)[1]),
    ("MULT_CORDIC", "Q7.8", "MULT_CORDIC", 0x0304, lambda value: byte_pair(value)[0] * byte_pair(value)[1]),
    ("REDUCCION_ARGUMENTO", "Q3.12", "REDUCCION_ARGUMENTO", 0x1922, lambda value: value & 0x3fff),
    ("SENO_TAYLOR", "Q1.14", "SENO_TAYLOR", 2, lambda value: q114(math.sin(math.pi / 3))),
    ("TABLA_SENO", "Q1.14", "TABLA_SENO", 2, lambda value: q114(math.sin(math.pi / 3))),
    ("TABLA_COSENO", "Q1.14", "TABLA_COSENO", 2, lambda value: q114(math.cos(math.pi / 3))),
    ("RAIZ_NON_RESTORING", "Q6.9", "RAIZ_NON_RESTORING", 256, integer_sqrt),
    ("CONVERSION_HEX", "texto", "CONVERSION_HEX", 0x3241, parse_hex_ascii),
    ("CONVERSION_BIN", "texto", "CONVERSION_BIN", 10, lambda value: value & 0xf),
    ("CIRCLE_SHIFT", "16 bits", "CIRCLE_SHIFT", 1, lambda value: (value << 7) & 0xffff),
    ("FROM_QM_N", "Q15.16", "FROM_QM_N", 0x0204, lambda value: value & 0xffff),
    ("TO_QM_N", "Qm.n", "TO_QM_N", 0x0204, lambda value: value & 0xffff),
    ("FROMDEC", "texto", "FROMDEC", 42, lambda value: value & 0xffff),
    ("TODEC", "texto", "TODEC", 42, lambda value: value & 0xffff),
    ("GETC_GETLINE_OUTVAL", "I/O", "GETC_GETLINE_OUTVAL", 0, lambda value: value & 0xffff),
    ("SENO_CHEBYSHEV_PADE", "Q1.14", "SENO_CHEBYSHEV_PADE", 2, lambda value: q114(math.sin(math.pi / 2))),
    ("MATH_HELPERS_DQ16", "Q15.16", "MATH_HELPERS_DQ16", 16, integer_sqrt),
    ("SQRT_NR_Q8", "Q7.8", "SQRT_NR_Q8", 4, lambda value: (integer_sqrt(value) * 256) & 0xffff),
]


def build_source(routine, routines_text):
    harness = [
        ".ORIG x3000",
        "LDABS R0 0x5000",
        f"JSR {routine}",
        "STABS R0 0x4000",
        "HALT",
        "",
    ]
    return "\n".join(harness + [routines_text.rstrip(), ""])


def run_case(case, output_dir, routines_text):
    name, qformat, routine, input_word, reference = case
    source = build_source(routine, routines_text)
    source_path = Path(output_dir) / f"real_{name}.asm"
    source_path.write_text(source, encoding="utf-8")

    assembler = Assembler()
    memory = assembler.assemble([source_path])
    simulator = Simulator(batch=True)
    origin, image_size = simulator.load_memory(memory, assembler.origins[0])
    simulator.write_word(0x5000, input_word)
    simulator.write_word(0x5002, 0x4000)
    simulator.execute(100000)

    actual = simulator.read_word(0x4000)
    expected = reference(input_word) & 0xffff
    code_end = origin + image_size
    return {
        "name": name,
        "format": qformat,
        "routine": routine,
        "input": input_word,
        "expected": expected,
        "actual": actual,
        "absolute_error": abs(actual - expected),
        "instructions": simulator.instructions,
        "halted": simulator.halted,
        "pc": simulator.pc,
        "image_bytes": image_size,
        "code_bytes": simulator.code_bytes,
        "data_bytes": len(simulator.written - set(range(origin, code_end))),
        "memory_observed": len(simulator.occupied),
        "peak_memory": simulator.peak_occupied,
        "source": str(source_path),
    }


def summarize_rows(rows):
    instructions = [row["instructions"] for row in rows]
    return {
        "rows": rows,
        "global_instructions": sum(instructions),
        "min_instructions": min(instructions),
        "max_instructions": max(instructions),
        "mean_instructions": sum(instructions) / len(instructions),
        "image_bytes": sum(row["image_bytes"] for row in rows),
        "code_bytes": sum(row["code_bytes"] for row in rows),
        "data_bytes": sum(row["data_bytes"] for row in rows),
        "memory_observed": sum(row["memory_observed"] for row in rows),
        "peak_memory": sum(row["peak_memory"] for row in rows),
        "max_peak_memory": max(row["peak_memory"] for row in rows),
        "halted": all(row["halted"] for row in rows),
        "max_absolute_error": max(row["absolute_error"] for row in rows),
    }


def run_all(output_dir):
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    routines_text = ROUTINES.read_text(encoding="utf-8")
    rows = [run_case(case, directory, routines_text) for case in CASES]
    return summarize_rows(rows)


def format_report(result):
    lines = [
        "# Benchmark real de la calculadora",
        "",
        "Cada interfaz se ejecuta en un programa ensamblado propio que lee su operando desde 0x5000, llama a una rutina ISA real y escribe el resultado en 0x4000.",
        "",
        "| # | Interfaz | Formato | Entrada | Esperado | Ejecutado | Instrucciones | Bytes imagen | Bytes datos | Pico memoria | Error | Estado |",
        "|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for index, row in enumerate(result["rows"], 1):
        state = "PASS" if row["absolute_error"] == 0 and row["halted"] else "FAIL"
        lines.append(
            f"| {index} | {row['name']} | {row['format']} | 0x{row['input']:04X} | "
            f"0x{row['expected']:04X} | 0x{row['actual']:04X} | {row['instructions']} | "
            f"{row['image_bytes']} | {row['data_bytes']} | {row['peak_memory']} | "
            f"{row['absolute_error']} | {state} |"
        )
    lines.extend([
        "",
        "## Totales",
        "",
        f"- Instrucciones globales: {result['global_instructions']}",
        f"- Minimo por interfaz: {result['min_instructions']}",
        f"- Maximo por interfaz: {result['max_instructions']}",
        f"- Promedio por interfaz: {result['mean_instructions']:.2f}",
        f"- Bytes de imagen acumulados: {result['image_bytes']}",
        f"- Bytes de codigo acumulados: {result['code_bytes']}",
        f"- Bytes de datos acumulados: {result['data_bytes']}",
        f"- Bytes observados acumulados: {result['memory_observed']}",
        f"- Pico de memoria acumulado: {result['peak_memory']}",
        f"- Pico maximo por interfaz: {result['max_peak_memory']}",
        f"- Error absoluto maximo: {result['max_absolute_error']}",
        f"- HALT en todas las interfaces: {'si' if result['halted'] else 'no'}",
    ])
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description="Benchmark real de interfaces matematicas")
    parser.add_argument("-o", "--output", default="REAL_BENCHMARK.md")
    parser.add_argument("--sources-dir", default="benchmark/real")
    args = parser.parse_args(argv)

    result = run_all(args.sources_dir)
    Path(args.output).write_text(format_report(result), encoding="utf-8")
    for row in result["rows"]:
        print(
            f"{row['name']}: instrucciones={row['instructions']}, "
            f"error={row['absolute_error']}, estado={'PASS' if row['halted'] and row['absolute_error'] == 0 else 'FAIL'}"
        )
    print("Instrucciones globales:", result["global_instructions"])
    print("Reporte:", args.output)


if __name__ == "__main__":
    raise SystemExit(main())
