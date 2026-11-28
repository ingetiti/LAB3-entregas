import re
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from shutil import copytree

from assembler import Assembler
from lc3_simulator import run_benchmark
from simulator import Machine, ObjectImage

_FIXED_RESULT = re.compile(
    r"^\(Q(?P<integer_bits>\d+)\.(?P<fractional_bits>\d+)\)"
    r"\s+(?P<value>-?\d+(?:\.\d+)?)$"
)


def _operation_results(output: str) -> dict[str, str]:
    results: dict[str, list[str]] = {}
    current_operation = None
    for line in output.splitlines():
        banner = re.match(r"^==\s*(.*?)\s*==\s*(.*)$", line)
        if banner:
            current_operation = (
                f"{banner.group(1)} {banner.group(2)}".strip()
            )
            results[current_operation] = []
        elif current_operation is not None and line.strip():
            results[current_operation].append(line.strip())

    return {
        operation: lines[-1]
        for operation, lines in results.items()
        if lines
    }


def _replace_benchmark_input(
    source: str, operation_comment: str, value: int
) -> str:
    pattern = re.compile(
        rf"(?m)^(?P<prefix>[ \t]*\.FILL[ \t]+#\d+[ \t]*;[ \t]*"
        rf"{re.escape(operation_comment)}[^\r\n]*\r?\n[ \t]*\.FILL[ \t]+)"
        r"#-?\d+"
    )
    updated_source, replacements = pattern.subn(
        lambda match: f"{match.group('prefix')}#{value}",
        source,
        count=1,
    )
    if replacements != 1:
        raise AssertionError(
            f"Could not locate the input for {operation_comment}"
        )
    return updated_source


class BenchmarkOptimizationTests(unittest.TestCase):
    def assert_operation_results_match(
        self,
        reference_output: str,
        actual_output: str,
        operation_names: tuple[str, ...] | None = None,
    ) -> None:
        reference = _operation_results(reference_output)
        actual = _operation_results(actual_output)
        if operation_names is None:
            self.assertEqual(
                set(reference),
                set(actual),
                "The benchmark operation sets differ",
            )
        names = operation_names or tuple(reference)

        for name in names:
            self.assertIn(name, reference, f"Missing LC-3 result for {name}")
            self.assertIn(name, actual, f"Missing new-ISA result for {name}")
            expected_result = reference[name]
            actual_result = actual[name]
            expected = _FIXED_RESULT.match(expected_result)
            received = _FIXED_RESULT.match(actual_result)

            if expected is None or received is None:
                self.assertEqual(
                    expected_result,
                    actual_result,
                    f"{name} result differs",
                )
                continue

            self.assertEqual(
                expected.group("integer_bits"),
                received.group("integer_bits"),
                f"{name} integer format differs",
            )
            fractional_bits = int(expected.group("fractional_bits"))
            self.assertEqual(
                fractional_bits,
                int(received.group("fractional_bits")),
                f"{name} fractional format differs",
            )
            difference = abs(
                Decimal(expected.group("value"))
                - Decimal(received.group("value"))
            )
            tolerance = Decimal(1) / (1 << fractional_bits)
            self.assertLessEqual(
                difference,
                tolerance,
                f"{name} differs by {difference}; one Q-format LSB is "
                f"{tolerance}",
            )

    def assert_operation_result_matches_value(
        self,
        output: str,
        operation_name: str,
        expected_value: Decimal,
    ) -> None:
        results = _operation_results(output)
        self.assertIn(operation_name, results)
        result = _FIXED_RESULT.match(results[operation_name])
        self.assertIsNotNone(result, f"{operation_name} is not a Q-format value")
        fractional_bits = int(result.group("fractional_bits"))
        actual_value = Decimal(result.group("value"))
        tolerance = Decimal(1) / (1 << fractional_bits)
        difference = abs(actual_value - expected_value)
        self.assertLessEqual(
            difference,
            tolerance,
            f"{operation_name} differs from its mathematical result by "
            f"{difference}; one Q-format LSB is {tolerance}",
        )

    def test_exp_values_match_lc3_at_sign_and_saturation_boundaries(self) -> None:
        root = Path(__file__).resolve().parent
        values = (-32768, -16384, -4096, -1, 0, 1, 4096, 16384, 32767)

        with tempfile.TemporaryDirectory() as temporary:
            temporary_root = Path(temporary)
            lc3_dir = temporary_root / "benchmark_original"
            isa_dir = temporary_root / "benchmark_optimizado"
            copytree(root / "benchmark_original", lc3_dir)
            copytree(root / "benchmark_optimizado", isa_dir)
            directories = (lc3_dir, isa_dir)
            base_sources = tuple(
                (directory / "main_grupo27.asm").read_text(encoding="latin-1")
                for directory in directories
            )
            marker = ".FILL   #4096   ; 1  (Q3.12)"

            for value in values:
                replacement = f".FILL   #{value}   ; 1  (Q3.12)"
                for directory, base_source in zip(directories, base_sources):
                    self.assertIn(marker, base_source)
                    (directory / "main_grupo27.asm").write_text(
                        base_source.replace(marker, replacement, 1),
                        encoding="latin-1",
                    )

                assembly = Assembler().assemble(isa_dir / "main_grupo27.asm")
                machine = Machine(
                    ObjectImage(assembly.origin, assembly.stack, assembly.image)
                )
                machine.run()
                _, lc3_machine = run_benchmark(lc3_dir, 10_000_000)
                self.assert_operation_results_match(
                    "".join(lc3_machine.output),
                    "".join(machine.output),
                    ("EXPONENCIACION",),
                )

    def test_argument_reduction_matches_expected_values_across_signed_range(
        self,
    ) -> None:
        root = Path(__file__).resolve().parent
        expected_raw_values = {
            -32768: 5833,
            -30000: -4266,
            -26336: -602,
            -26335: -601,
            -26334: -600,
        }

        with tempfile.TemporaryDirectory() as temporary:
            isa_dir = Path(temporary) / "benchmark_optimizado"
            copytree(root / "benchmark_optimizado", isa_dir)
            main = isa_dir / "main_grupo27.asm"
            base_source = main.read_text(encoding="latin-1")

            for value, expected_raw in expected_raw_values.items():
                source = _replace_benchmark_input(
                    base_source, "REDUCCION DE ARGUMENTO:", value
                )
                main.write_text(source, encoding="latin-1")

                assembly = Assembler().assemble(isa_dir / "main_grupo27.asm")
                machine = Machine(
                    ObjectImage(assembly.origin, assembly.stack, assembly.image)
                )
                machine.run()
                self.assert_operation_result_matches_value(
                    "".join(machine.output),
                    "REDUCCION DE ARGUMENTO (CORDIC)",
                    Decimal(expected_raw) / Decimal(1 << 12),
                )

    def test_chebyshev_pade_matches_lc3_at_signed_and_rounding_boundaries(
        self,
    ) -> None:
        root = Path(__file__).resolve().parent
        values = (-32768, -32767, 32766, 32767)

        with tempfile.TemporaryDirectory() as temporary:
            temporary_root = Path(temporary)
            lc3_dir = temporary_root / "benchmark_original"
            isa_dir = temporary_root / "benchmark_optimizado"
            copytree(root / "benchmark_original", lc3_dir)
            copytree(root / "benchmark_optimizado", isa_dir)
            directories = (lc3_dir, isa_dir)
            base_sources = tuple(
                (directory / "main_grupo27.asm").read_text(encoding="latin-1")
                for directory in directories
            )

            for value in values:
                for directory, base_source in zip(directories, base_sources):
                    source = _replace_benchmark_input(
                        base_source, "SENO CHEBYSHEV-PADE:", value
                    )
                    (directory / "main_grupo27.asm").write_text(
                        source, encoding="latin-1"
                    )

                assembly = Assembler().assemble(isa_dir / "main_grupo27.asm")
                machine = Machine(
                    ObjectImage(assembly.origin, assembly.stack, assembly.image)
                )
                machine.run()
                _, lc3_machine = run_benchmark(lc3_dir, 10_000_000)
                self.assert_operation_results_match(
                    "".join(lc3_machine.output),
                    "".join(machine.output),
                    ("SENO TRIGONOMETRICO (CHEVYSHEV-PADE)",),
                )

    def test_taylor_quadrants_match_lc3_at_boundaries(self) -> None:
        root = Path(__file__).resolve().parent
        angles = (
            0,
            1,
            45,
            450,
            899,
            900,
            901,
            1350,
            1799,
            1800,
            2700,
            3599,
            3600,
        )

        with tempfile.TemporaryDirectory() as temporary:
            temporary_root = Path(temporary)
            lc3_dir = temporary_root / "benchmark_original"
            isa_dir = temporary_root / "benchmark_optimizado"
            copytree(root / "benchmark_original", lc3_dir)
            copytree(root / "benchmark_optimizado", isa_dir)
            base_sources = (
                (lc3_dir / "main_grupo27.asm").read_text(encoding="latin-1"),
                (isa_dir / "main_grupo27.asm").read_text(encoding="latin-1"),
            )

            for angle in angles:
                marker = re.compile(
                    r"(?m)^(?P<prefix>\s*\.FILL\s+)#600"
                    r"(?P<suffix>\s*;\s*60 grados, entero\s*)$"
                )
                for directory, base_source in zip(
                    (lc3_dir, isa_dir), base_sources
                ):
                    main = directory / "main_grupo27.asm"
                    updated_source, replacements = marker.subn(
                        lambda match: (
                            f"{match.group('prefix')}#{angle}"
                            f"{match.group('suffix')}"
                        ),
                        base_source,
                        count=1,
                    )
                    self.assertEqual(1, replacements)
                    main.write_text(updated_source, encoding="latin-1")

                assembly = Assembler().assemble(isa_dir / "main_grupo27.asm")
                machine = Machine(
                    ObjectImage(assembly.origin, assembly.stack, assembly.image)
                )
                machine.run()
                _, lc3_machine = run_benchmark(lc3_dir, 10_000_000)
                self.assert_operation_results_match(
                    "".join(lc3_machine.output),
                    "".join(machine.output),
                    ("SENO TRIGONOMETRICO (TAYLOR)",),
                )

    def test_taylor_multiply_handles_unsigned_16_bit_operands(self) -> None:
        root = Path(__file__).resolve().parent
        benchmark_dir = root / "benchmark_optimizado"
        pairs = [
            (0, 0),
            (1, 1),
            (1800, 12868),
            (6434, 6434),
            (32767, 32767),
            (0, 65535),
            (32768, 32768),
            (65535, 1),
            (65535, 65535),
            (32768, 65535),
        ]
        lines = [
            ".ORIG x3000",
            ".EXTERNAL G21_SENOTAYLOR_SUBRUTINA-MULT_U32",
        ]
        for index, (left, right) in enumerate(pairs):
            lines.extend(
                [
                    f"LI R0, #{left}",
                    f"LI R1, #{right}",
                    "JSR MULT_U32",
                    f"STPC R0, HIGH{index}",
                    f"STPC R1, LOW{index}",
                ]
            )
        lines.append("HALT")
        for index in range(len(pairs)):
            lines.extend([f"LOW{index} .BLKW #1", f"HIGH{index} .BLKW #1"])
        lines.append(".END")

        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "multiply.asm"
            source.write_text("\n".join(lines), encoding="ascii")
            assembly = Assembler([benchmark_dir / "lib"]).assemble(source)
            machine = Machine(
                ObjectImage(assembly.origin, assembly.stack, assembly.image)
            )
            machine.run()

        for index, (left, right) in enumerate(pairs):
            low_address = assembly.symbols[f"low{index}"]
            high_address = assembly.symbols[f"high{index}"]
            low = machine.memory[low_address] | (machine.memory[low_address + 1] << 8)
            high = machine.memory[high_address] | (
                machine.memory[high_address + 1] << 8
            )
            self.assertEqual(left * right, (high << 16) | low)

    def test_group15_q312_to_q78_matches_signed_shift(self) -> None:
        root = Path(__file__).resolve().parent
        benchmark_dir = root / "benchmark_optimizado"
        values = (32767, 516, 15, 0, -1, -15, -516, -32768)
        lines = [
            ".ORIG x3000",
            ".EXTERNAL G15_G15_Q312_Q78-G15_Q312_Q78",
        ]
        for index, value in enumerate(values):
            lines.extend(
                [
                    f"LI R0, #{value}",
                    "JSR G15_Q312_Q78",
                    f"STPC R0, RESULT{index}",
                ]
            )
        lines.append("HALT")
        lines.extend(f"RESULT{index} .BLKW #1" for index in range(len(values)))
        lines.append(".END")

        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "qformat.asm"
            source.write_text("\n".join(lines), encoding="ascii")
            assembly = Assembler([benchmark_dir / "lib"]).assemble(source)
            machine = Machine(
                ObjectImage(assembly.origin, assembly.stack, assembly.image)
            )
            machine.run()

        for index, value in enumerate(values):
            address = assembly.symbols[f"result{index}"]
            actual = machine.memory[address] | (machine.memory[address + 1] << 8)
            self.assertEqual(value >> 4 & 0xFFFF, actual)

    def test_group5_fixed_point_multiply_handles_fraction_and_overflow(self) -> None:
        root = Path(__file__).resolve().parent
        benchmark_dir = root / "benchmark_optimizado"
        pairs = (
            (384, 384),
            (0x1234, 0x0567),
            (-0x1234, 0x0567),
            (0x1234, -0x0567),
            (-0x1234, -0x0567),
            (32767, 256),
            (32767, 257),
            (32767, 32767),
        )
        lines = [
            ".ORIG x3000",
            ".EXTERNAL G5_MUL_SUCESIVA_POW-MULT",
        ]
        for index, (left, right) in enumerate(pairs):
            lines.extend(
                [
                    f"LI R0, #{left}",
                    f"LI R1, #{right}",
                    "JSR MULT",
                    f"STPC R0, RESULT{index}",
                ]
            )
        lines.append("HALT")
        lines.extend(f"RESULT{index} .BLKW #1" for index in range(len(pairs)))
        lines.append(".END")

        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "multiply.asm"
            source.write_text("\n".join(lines), encoding="ascii")
            assembly = Assembler([benchmark_dir / "lib"]).assemble(source)
            machine = Machine(
                ObjectImage(assembly.origin, assembly.stack, assembly.image)
            )
            machine.run()

        for index, (left, right) in enumerate(pairs):
            address = assembly.symbols[f"result{index}"]
            actual = machine.memory[address] | (machine.memory[address + 1] << 8)
            magnitude = abs(left * right) // 256
            sign = -1 if (left < 0) != (right < 0) else 1
            expected = 0x8000 if magnitude > 32767 else (sign * magnitude) & 0xFFFF
            self.assertEqual(expected, actual)

    def test_group27_sumover_handles_carry_and_preserves_registers(self) -> None:
        root = Path(__file__).resolve().parent
        benchmark_dir = root / "benchmark_optimizado"
        cases = (
            (0x0000, 0x0000, 0),
            (0xFFFF, 0x0000, 1),
            (0xFFFF, 0x0001, 0),
            (0xFFFF, 0xFFFF, 1),
            (0x7FFF, 0x0000, 1),
            (0x7FFF, 0x8000, 1),
            (0xFFFE, 0x0000, 1),
            (0x0001, 0x0001, 1),
        )
        lines = [
            ".ORIG x3000",
            ".EXTERNAL G27_SUMOVER-SUMOVER",
        ]
        sentinels = (0x1234, 0x5678)
        for index, (left, right, carry_in) in enumerate(cases):
            signed_left = left if left < 0x8000 else left - 0x10000
            signed_right = right if right < 0x8000 else right - 0x10000
            lines.extend(
                [
                    f"LI R0, #{signed_left}",
                    f"LI R1, #{signed_right}",
                    f"LI R2, #{carry_in}",
                    f"LI R3, #{sentinels[0]}",
                    f"LI R4, #{sentinels[1]}",
                    "JSR SUMOVER",
                    f"STPC R0, RESULT{index}",
                    f"STPC R1, PRESERVED_R1_{index}",
                    f"STPC R2, CARRY{index}",
                    f"STPC R3, PRESERVED_R3_{index}",
                    f"STPC R4, PRESERVED_R4_{index}",
                ]
            )
        lines.append("HALT")
        for index in range(len(cases)):
            lines.extend(
                [
                    f"RESULT{index} .BLKW #1",
                    f"CARRY{index} .BLKW #1",
                    f"PRESERVED_R1_{index} .BLKW #1",
                    f"PRESERVED_R3_{index} .BLKW #1",
                    f"PRESERVED_R4_{index} .BLKW #1",
                ]
            )
        lines.append(".END")

        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "sumover.asm"
            source.write_text("\n".join(lines), encoding="ascii")
            assembly = Assembler([benchmark_dir / "lib"]).assemble(source)
            machine = Machine(
                ObjectImage(assembly.origin, assembly.stack, assembly.image)
            )
            machine.run()

        def read_word(label: str) -> int:
            address = assembly.symbols[label.casefold()]
            return machine.memory[address] | (machine.memory[address + 1] << 8)

        for index, (left, right, carry_in) in enumerate(cases):
            total = left + right + carry_in
            self.assertEqual(total & 0xFFFF, read_word(f"result{index}"))
            self.assertEqual(total >> 16, read_word(f"carry{index}"))
            self.assertEqual(right, read_word(f"preserved_r1_{index}"))
            self.assertEqual(sentinels[0], read_word(f"preserved_r3_{index}"))
            self.assertEqual(sentinels[1], read_word(f"preserved_r4_{index}"))

    def test_group9_q8_multiply_splits_operands_with_shifts(self) -> None:
        root = Path(__file__).resolve().parent
        benchmark_dir = root / "benchmark_optimizado"
        values = (
            0,
            1,
            0xFF,
            0x100,
            0x101,
            0x1FF,
            0x200,
            0x3FF,
            0x400,
            0xFFF,
            0x1000,
            0x7FFF,
        )
        multipliers = (0, 1, 64, 127, 128)
        pairs = tuple((value, multiplier) for value in values for multiplier in multipliers)
        lines = [
            ".ORIG x3000",
            ".EXTERNAL G9_SQRT_NR_Q8-SQ9_MULQ",
        ]
        for index, (value, multiplier) in enumerate(pairs):
            signed_value = value if value < 0x8000 else value - 0x10000
            lines.extend(
                [
                    f"LI R0, #{signed_value}",
                    f"LI R1, #{multiplier}",
                    "JSR SQ9_MULQ",
                    f"STPC R0, RESULT{index}",
                ]
            )
        lines.append("HALT")
        lines.extend(f"RESULT{index} .BLKW #1" for index in range(len(pairs)))
        lines.append(".END")

        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "sqrt_multiply.asm"
            source.write_text("\n".join(lines), encoding="ascii")
            assembly = Assembler([benchmark_dir / "lib"]).assemble(source)
            machine = Machine(
                ObjectImage(assembly.origin, assembly.stack, assembly.image)
            )
            machine.run()

        for index, (value, multiplier) in enumerate(pairs):
            address = assembly.symbols[f"result{index}"]
            actual = machine.memory[address] | (machine.memory[address + 1] << 8)
            self.assertEqual(value * multiplier // 256, actual)

    def test_g6_redondea_handles_rounding_boundaries_and_preserves_r6(self) -> None:
        root = Path(__file__).resolve().parent
        benchmark_dir = root / "benchmark_optimizado"
        max_value = (1 << 45) - 1
        cases = []
        for shift in range(1, 45):
            half = 1 << (shift - 1)
            values = {
                0,
                half - 1,
                half,
                half + 1,
                (1 << shift) - 1,
                1 << shift,
                (1 << shift) + 1,
                max_value,
                (0x7FFF << shift) + half,
                (0x3FFFFFFF << shift) + half,
            }
            cases.extend(
                (shift, value) for value in sorted(values) if value <= max_value
            )

        lines = [
            ".ORIG x3000",
            ".EXTERNAL G6_EXP-REDONDEA",
            "LEA R5, WORK",
            "LI R6, #4660",
        ]
        for index, (shift, value) in enumerate(cases):
            high = (value >> 30) & 0x7FFF
            middle = (value >> 15) & 0x7FFF
            low = value & 0x7FFF
            lines.extend(
                [
                    f"LI R0, #{shift}",
                    f"LI R3, #{high}",
                    "STW R3, R5, #15",
                    f"LI R3, #{middle}",
                    "STW R3, R5, #14",
                    f"LI R3, #{low}",
                    "STW R3, R5, #13",
                    "JSR REDONDEA",
                    f"LEA R4, RESULT{index}",
                    "STW R0, R4, #0",
                    "STW R1, R4, #1",
                    "STW R2, R4, #2",
                    "STW R6, R4, #3",
                ]
            )
        lines.extend(["HALT", "WORK .BLKW #18"])
        lines.extend(f"RESULT{index} .BLKW #4" for index in range(len(cases)))
        lines.append(".END")

        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "g6_redondea.asm"
            source.write_text("\n".join(lines), encoding="ascii")
            assembly = Assembler([benchmark_dir / "lib"]).assemble(source)
            machine = Machine(
                ObjectImage(assembly.origin, assembly.stack, assembly.image)
            )
            machine.run()

        for index, (shift, value) in enumerate(cases):
            address = assembly.symbols[f"result{index}"]
            low = machine.memory[address] | (machine.memory[address + 1] << 8)
            middle = machine.memory[address + 2] | (
                machine.memory[address + 3] << 8
            )
            high = machine.memory[address + 4] | (
                machine.memory[address + 5] << 8
            )
            preserved_r6 = machine.memory[address + 6] | (
                machine.memory[address + 7] << 8
            )
            actual = low | (middle << 15) | (high << 30)
            expected = (value + (1 << (shift - 1))) >> shift
            self.assertEqual(expected, actual, f"shift={shift}, value={value}")
            self.assertEqual(0x1234, preserved_r6, f"R6 changed at case {index}")

    def test_todec_fraction_digits_preserve_legacy_truncation(self) -> None:
        root = Path(__file__).resolve().parent
        benchmark_dir = root / "benchmark_optimizado"
        fraction_values = set(range(256))
        for bit in range(16):
            fraction_values.update(
                value
                for value in ((1 << bit) - 1, 1 << bit, (1 << bit) + 1)
                if 0 <= value <= 0xFFFF
            )
        fraction_values.update(
            (index * 40503 + 7919) & 0xFFFF for index in range(64)
        )
        fractions = tuple(sorted(fraction_values))
        lines = [
            ".ORIG x3000",
            ".EXTERNAL G27_TODEC-TODEC",
        ]
        for index, fraction in enumerate(fractions):
            signed_fraction = fraction if fraction < 0x8000 else fraction - 0x10000
            lines.extend(
                [
                    f"LEA R2, BUFFER{index}",
                    "LI R0, #0",
                    f"LI R1, #{signed_fraction}",
                    "LI R3, #4",
                    "JSR TODEC",
                ]
            )
        lines.append("HALT")
        lines.extend(f"BUFFER{index} .BLKB #16" for index in range(len(fractions)))
        lines.append(".END")

        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "todec_fraction.asm"
            source.write_text("\n".join(lines), encoding="ascii")
            assembly = Assembler([benchmark_dir / "lib"]).assemble(source)
            machine = Machine(
                ObjectImage(assembly.origin, assembly.stack, assembly.image)
            )
            machine.run()

        for index, fraction in enumerate(fractions):
            address = assembly.symbols[f"buffer{index}"]
            output = bytearray()
            while machine.memory[address]:
                output.append(machine.memory[address])
                address += 1
            digits = sum(
                (1_000_000_000 << bit) >> 16
                for bit in range(16)
                if fraction & (1 << bit)
            )
            self.assertEqual(f"0.{digits:09d}", output.decode("ascii"))

    def test_todec_small_integers_preserve_formats(self) -> None:
        root = Path(__file__).resolve().parent
        benchmark_dir = root / "benchmark_optimizado"
        cases = (
            (0, 0, 0, "0"),
            (9, 0, 0, "9"),
            (5, -32768, 0, "5.5"),
            (-9, 0, 0, "-9"),
            (9, 0, 1, "+9"),
            (9, 0, 2, "00009"),
            (9, 0, 4, "9.000000000"),
            (10, 0, 0, "10"),
        )
        lines = [
            ".ORIG x3000",
            ".EXTERNAL G27_TODEC-TODEC",
        ]
        for index, (integer, fraction, format_bits, _) in enumerate(cases):
            lines.extend(
                [
                    f"LEA R2, BUFFER{index}",
                    f"LI R0, #{integer}",
                    f"LI R1, #{fraction}",
                    f"LI R3, #{format_bits}",
                    "JSR TODEC",
                ]
            )
        lines.append("HALT")
        lines.extend(f"BUFFER{index} .BLKB #24" for index in range(len(cases)))
        lines.append(".END")

        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "todec_integer.asm"
            source.write_text("\n".join(lines), encoding="ascii")
            assembly = Assembler([benchmark_dir / "lib"]).assemble(source)
            machine = Machine(
                ObjectImage(assembly.origin, assembly.stack, assembly.image)
            )
            machine.run()

        for index, (_, _, _, expected) in enumerate(cases):
            address = assembly.symbols[f"buffer{index}"]
            output = bytearray()
            while machine.memory[address]:
                output.append(machine.memory[address])
                address += 1
            self.assertEqual(expected, output.decode("ascii"))

    def test_taylor_u32_division_handles_narrow_and_wide_dividends(self) -> None:
        root = Path(__file__).resolve().parent
        benchmark_dir = root / "benchmark_optimizado"
        cases = (
            (0, 0, 1),
            (0, 0xFFFF, 3),
            (0, 0xC123, 0x0123),
            (1, 0, 2),
            (0x1234, 0x5678, 0x8000),
        )
        lines = [
            ".ORIG x3000",
            ".EXTERNAL g21_senotaylor_subrutina-DIV_U32_16",
        ]
        for index, (high, low, divisor) in enumerate(cases):
            lines.extend(
                [
                    f"LI R0, #{high}",
                    f"LI R1, #{low}",
                    f"LI R2, #{divisor}",
                    "JSR DIV_U32_16",
                    f"STPC R0, RESULT{index}",
                ]
            )
        lines.append("HALT")
        lines.extend(f"RESULT{index} .BLKW #1" for index in range(len(cases)))
        lines.append(".END")

        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "taylor_division.asm"
            source.write_text("\n".join(lines), encoding="ascii")
            assembly = Assembler([benchmark_dir / "lib"]).assemble(source)
            machine = Machine(
                ObjectImage(assembly.origin, assembly.stack, assembly.image)
            )
            machine.run()

        for index, (high, low, divisor) in enumerate(cases):
            address = assembly.symbols[f"result{index}"]
            result = machine.memory[address] | (machine.memory[address + 1] << 8)
            dividend = (high << 16) | low
            self.assertEqual(dividend // divisor, result)

    def test_g19_cordic_multiply_reports_result_and_status(self) -> None:
        root = Path(__file__).resolve().parent
        benchmark_dir = root / "benchmark_optimizado"
        cases = (
            (768, 1024, 3072, 0),
            (-768, 1024, -3072, 0),
            (25600, 25600, 0, 1),
            (768, -32768, 0, 2),
        )
        lines = [
            ".ORIG x3000",
            ".EXTERNAL G19_CORDIC_MULTIPLICACION-CORDIC_MUL",
        ]
        for index, (left, right, _, _) in enumerate(cases):
            lines.extend(
                [
                    f"LI R0, #{left}",
                    f"LI R1, #{right}",
                    "JSR CORDIC_MUL",
                    f"STPC R0, RESULT{index}",
                    f"STPC R1, STATUS{index}",
                ]
            )
        lines.append("HALT")
        for index in range(len(cases)):
            lines.extend([f"RESULT{index} .BLKW #1", f"STATUS{index} .BLKW #1"])
        lines.append(".END")

        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "cordic_helpers.asm"
            source.write_text("\n".join(lines), encoding="ascii")
            assembly = Assembler([benchmark_dir / "lib"]).assemble(source)
            machine = Machine(
                ObjectImage(assembly.origin, assembly.stack, assembly.image)
            )
            machine.run()

        def read_signed_word(label: str) -> int:
            address = assembly.symbols[label.casefold()]
            value = machine.memory[address] | (machine.memory[address + 1] << 8)
            return value - 0x10000 if value & 0x8000 else value

        for index, (_, _, expected_result, expected_status) in enumerate(cases):
            self.assertEqual(expected_result, read_signed_word(f"result{index}"))
            self.assertEqual(expected_status, read_signed_word(f"status{index}"))

    def test_manual_benchmark_uses_real_multiply_result_and_reduces_instructions(
        self,
    ) -> None:
        root = Path(__file__).resolve().parent
        benchmark_dir = root / "benchmark_optimizado"
        source_dir = root / "benchmark_original"
        assembly = Assembler().assemble(benchmark_dir / "main_grupo27.asm")
        machine = Machine(
            ObjectImage(assembly.origin, assembly.stack, assembly.image)
        )
        machine.run()

        _, lc3_machine = run_benchmark(source_dir, 10_000_000)
        lc3_output = "".join(lc3_machine.output)
        isa_output = "".join(machine.output)
        lc3_results = _operation_results(lc3_output)
        isa_results = _operation_results(isa_output)
        self.assertEqual(set(lc3_results), set(isa_results))
        multiply_operation = "MULTIPLICACION (BASIC)"
        self.assert_operation_results_match(
            lc3_output,
            isa_output,
            tuple(
                name for name in lc3_results if name != multiply_operation
            ),
        )
        expected_product = Decimal(3540 * -1853) / Decimal(1 << 16)
        self.assert_operation_result_matches_value(
            isa_output,
            multiply_operation,
            expected_product,
        )
        self.assertLess(machine.instructions_executed, lc3_machine.steps)


if __name__ == "__main__":
    unittest.main()
