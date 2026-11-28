#!/usr/bin/env python3
import argparse
import math
import tempfile
from pathlib import Path

from assembler import Assembler, write_output
from simulator import Simulator


ROOT = Path(__file__).resolve().parent


BENCHMARKS = {
    "migrated_easy": (
        "benchmark/migrated_easy.asm", 0x4000,
        [0x0006, 0x0024, 0x0020, 0x1922, 0x002A, 0x000A],
    ),
    "migrated_core_v2": (
        "benchmark/migrated_core_v2.asm", 0x4000,
        [0x0001, 0x0020, 0x0004, 0x1922, 0x002A, 0x000A],
    ),
    "migrated_cordic_div": (
        "benchmark/migrated_cordic_div.asm", 0x4000,
        [0x4000, 0xC000],
    ),
    "migrated_sqrt": (
        "benchmark/migrated_sqrt.asm", 0x4000,
        [0x0004, 0x0008],
    ),
    "migrated_sincos_table": (
        "benchmark/migrated_sincos_table.asm", 0x4000,
        [0x376D, 0x2000, 0x4000, 0x0000],
    ),
    "phase4_core": (
        "benchmark/phase4_core.asm", 0x4000,
        [0x0019, 0x0001, 0x0006, 0x0020, 0x0020, 0x0004],
    ),
    "phase4_integral": (
        "benchmark/phase4_integral.asm", 0x4000,
        [
            0x0080, 0x0019, 0x0020, 0x0008, 0x0100, 0x0024, 0x0006, 0x0001,
            0x0004, 0x0000, 0x0002, 0x0000, 0x0020, 0x0019, 0x000C, 0x0000,
            0x1922, 0x4000, 0x4000, 0x0010, 0x002A, 0x000A, 0x0080, 0x0204,
            0x0204, 0x002A, 0x002A, 0x0000, 0x4000, 0x0004, 0x0200,
        ],
    ),
}


def fixed_point_sine_q114(radians):
    value = math.sin(radians)
    word = round(value * (1 << 14))
    return word & 0xffff


def fixed_point_cos_q114(radians):
    value = math.cos(radians)
    word = round(value * (1 << 14))
    return word & 0xffff


def run_benchmark(source, output_dir, base_address, expected):
    source_path = Path(source)
    if not source_path.is_absolute():
        source_path = ROOT / source_path
    assembler = Assembler()
    memory = assembler.assemble([source_path])
    if not assembler.origins:
        raise RuntimeError("missing .ORIG")

    origin = assembler.origins[0]
    maximum = max(memory)

    simulator = Simulator(batch=True)
    origin_loaded, image_size = simulator.load_memory(memory, origin)
    simulator.execute(10000)

    count = len(expected)
    actual = [simulator.read_word(base_address + index * 2) for index in range(count)]
    errors = [abs(actual[index] - expected[index]) for index in range(count)]

    return {
        "source": str(source_path),
        "origin": origin_loaded,
        "instructions": simulator.instructions,
        "memory_observed": len(simulator.occupied),
        "peak_memory": simulator.peak_occupied,
        "image_bytes": image_size,
        "actual": actual,
        "expected": expected,
        "absolute_errors": errors,
        "max_absolute_error": max(errors),
        "halted": simulator.halted,
        "pc": simulator.pc,
    }


def run_all(output_dir):
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    results = {}
    for name, (source, base_address, expected) in BENCHMARKS.items():
        try:
            results[name] = run_benchmark(source, directory, base_address, expected)
        except Exception as exc:
            results[name] = {
                "source": str(source),
                "origin": 0,
                "instructions": 0,
                "memory_observed": 0,
                "peak_memory": 0,
                "image_bytes": 0,
                "actual": [],
                "expected": expected,
                "absolute_errors": [],
                "max_absolute_error": 1,
                "halted": False,
                "pc": 0,
                "error": str(exc),
            }
    return results


def format_markdown(results):
    lines = [
        "# Metricas automaticas de benchmarks migrados",
        "",
        "| Benchmark | Instrucciones | Bytes imagen | Memoria observada | Pico memoria | PC HALT | Error absoluto maximo | Estado |",
        "|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for name, result in results.items():
        state = "PASS" if result["max_absolute_error"] == 0 else "FAIL"
        lines.append(
            f"| {name} | {result['instructions']} | {result['image_bytes']} | "
            f"{result['memory_observed']} | {result['peak_memory']} | 0x{result['pc']:04X} | "
            f"{result['max_absolute_error']} | {state} |"
        )

    lines.extend(["", "## Referencias matematicas", ""])
    pi3_sin = fixed_point_sine_q114(math.pi / 3)
    pi3_cos = fixed_point_cos_q114(math.pi / 3)
    pi2_sin = fixed_point_sine_q114(math.pi / 2)
    pi2_cos = fixed_point_cos_q114(math.pi / 2)
    lines.extend([
        "| Referencia | Valor hexadecimal |",
        "|---|---:|",
        f"| sin(pi/3) Q1.14 | 0x{pi3_sin:04X} |",
        f"| cos(pi/3) Q1.14 | 0x{pi3_cos:04X} |",
        f"| sin(pi/2) Q1.14 | 0x{pi2_sin:04X} |",
        f"| cos(pi/2) Q1.14 | 0x{pi2_cos:04X} |",
    ])
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description="Generador de metricas del benchmark migrado")
    parser.add_argument("-o", "--output", default="BENCHMARK_METRICS.md")
    args = parser.parse_args(argv)

    with tempfile.TemporaryDirectory() as directory:
        results = run_all(directory)

    Path(args.output).write_text(format_markdown(results), encoding="utf-8")
    for name, result in results.items():
        state = "PASS" if result["max_absolute_error"] == 0 else "FAIL"
        print(
            f"{name}: {state}, instructions={result['instructions']}, "
            f"memory={result['memory_observed']}, max_error={result['max_absolute_error']}"
        )
    print("Reporte:", args.output)


if __name__ == "__main__":
    raise SystemExit(main())
