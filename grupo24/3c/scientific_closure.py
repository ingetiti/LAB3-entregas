#!/usr/bin/env python3
from pathlib import Path

from real_benchmark import format_report as format_real_report, run_all


def run_closure(output_dir):
    result = run_all(output_dir)
    return {
        "source": str(Path("benchmark/real_routines.asm")),
        "image": str(Path(output_dir)),
        "instructions": result["global_instructions"],
        "memory_observed": result["memory_observed"],
        "peak_memory": result["peak_memory"],
        "image_bytes": result["image_bytes"],
        "halted": result["halted"],
        "pc": 0,
        "max_absolute_error": result["max_absolute_error"],
        "rows": [
            {
                "name": row["name"],
                "format": row["format"],
                "expected": row["expected"],
                "actual": row["actual"],
                "absolute_error": row["absolute_error"],
            }
            for row in result["rows"]
        ],
        "benchmark": result,
    }


def format_report(result):
    lines = [
        "# Cierre científico con benchmarks reales",
        "",
        "Las 31 interfaces se ejecutan desde fuentes .asm reales mediante el simulador; los valores esperados se calculan en Python de forma independiente.",
        "",
        "| # | Interfaz | Formato | Esperado | Ejecutado | Error absoluto |",
        "|---:|---|---|---:|---:|---:|",
    ]
    for index, row in enumerate(result["rows"], 1):
        lines.append(
            f"| {index} | {row['name']} | {row['format']} | 0x{row['expected']:04X} | "
            f"0x{row['actual']:04X} | {row['absolute_error']} |"
        )
    lines.extend([
        "",
        "## Métricas",
        "",
        f"- Instrucciones dinámicas globales: {result['instructions']}",
        f"- Bytes observados en memoria: {result['memory_observed']}",
        f"- Pico de memoria ocupada: {result['peak_memory']}",
        f"- Bytes de imagen acumulados: {result['image_bytes']}",
        f"- HALT en todas las interfaces: {'sí' if result['halted'] else 'no'}",
        f"- Error absoluto máximo: {result['max_absolute_error']}",
        "",
        format_real_report(result["benchmark"]),
    ])
    return "\n".join(lines)


def main():
    directory = Path("benchmark/real")
    directory.mkdir(parents=True, exist_ok=True)
    result = run_closure(directory)
    Path("SCIENTIFIC_CLOSURE.md").write_text(format_report(result), encoding="utf-8")
    print(f"Interfaces: {len(result['rows'])}")
    print(f"Instrucciones: {result['instructions']}")
    print(f"Memoria observada: {result['memory_observed']}")
    print(f"Error máximo: {result['max_absolute_error']}")
    print("Reporte: SCIENTIFIC_CLOSURE.md")


if __name__ == "__main__":
    main()
