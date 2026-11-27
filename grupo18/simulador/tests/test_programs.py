"""Pruebas de integración de los programas Assembly (ejecutar desde la carpeta raíz Lab3C).

Por ahora cubre INSERTION_SORT (insertion_sort.asm) en dos niveles:

  1. La RUTINA sola. Se extrae del archivo real (no es una copia: si la rutina cambia,
     se prueba la versión nueva), se ensambla con un llamador mínimo y se ejecuta en la
     CPU del simulador con arreglos y bases de memoria elegidos por el test.
  2. El PROGRAMA completo: ensamblado y ejecutado, debe terminar en HALT e imprimir
     exactamente el mensaje de éxito de su propio harness.

Ninguna expectativa sale del código que se prueba: la referencia es sorted() de Python
sobre los valores interpretados como enteros de 16 bits con signo. Los casos aleatorios
usan random.Random con semilla fija, así que son reproducibles.

Contrato de INSERTION_SORT que se verifica (ver el comentario de la rutina en el .asm):
  entrada  R0 = dirección del primer elemento, R1 = n (cantidad de palabras)
  salida   a[0..n-1] ordenado ascendente, con signo, en el lugar
  conserva R0 y R6; no modifica R7 (retorna con JMP R7); no escribe fuera de a[0..n-1]
"""

import random
import re
import unittest
from pathlib import Path

from assembler.assembler import assemble
from simulator.cpu import CPU, EXECUTION_ERRORS
from simulator.loader import LoadedProgram
from simulator.memory import Memory
from simulator.runner import RunStatus, run_program

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SORT_SOURCE = PROJECT_ROOT / "insertion_sort.asm"

CALLER_ORIGIN = 0x1000              # el llamador y la rutina viven en x1000..
RETURN_ADDRESS = CALLER_ORIGIN + 2  # PC siguiente al JSR: lo que JSR guarda en R7
R6_SENTINEL = 0x1234                # valor que la rutina debe conservar en R6
MARGIN = 16                         # bytes vigilados antes y después del arreglo
FILL_BYTE = 0xA5                    # contenido conocido de esos márgenes
MAX_STEPS = 100_000                 # el peor caso legítimo (n=40 inverso) usa ~6.000

# Bases pedidas: regiones baja, justo antes de x8000, x8000 y siguiente, y el final de
# la memoria. x7FFE y x7FF0 hacen que el arreglo CRUCE de x7FFF (positivo con signo) a
# x8000 (negativo con signo).
BASES = (0x4000, 0x7FF0, 0x7FFE, 0x8000, 0x8002, 0xFFE0)


# ----------------------------------------------------------------------
# Utilidades
# ----------------------------------------------------------------------
def to_signed16(value):
    value &= 0xFFFF
    return value - 0x10000 if value & 0x8000 else value


def extract_routine(source):
    """Bloque de la rutina: desde la línea `INSERTION_SORT:` hasta el primer JMP R7 tras IS_END.

    Falla con un mensaje claro si el archivo ya no tiene esas marcas, en lugar de
    probar en silencio otra cosa.
    """
    # Recorrido por líneas (sin expresiones regulares anidadas, que pueden tardar un
    # tiempo exponencial si entre IS_END y JMP R7 hay otras líneas).
    lines = source.splitlines(keepends=True)
    starts = [i for i, line in enumerate(lines) if line.rstrip() == "INSERTION_SORT:"]
    if len(starts) != 1:
        raise AssertionError("insertion_sort.asm debe tener exactamente una línea "
                             "'INSERTION_SORT:'")
    in_end = False
    for index in range(starts[0], len(lines)):
        code = lines[index].split(";", 1)[0].strip()
        if code == "IS_END:":
            in_end = True
        elif in_end and re.fullmatch(r"JMP\s+R7", code, re.IGNORECASE):
            return "".join(lines[starts[0]:index + 1])
    raise AssertionError("insertion_sort.asm no contiene el bloque "
                         "'INSERTION_SORT:' ... 'IS_END:' ... 'JMP R7'")


def build_caller(routine):
    """Programa mínimo: JSR INSERTION_SORT ; HALT ; <rutina>."""
    source = (f".ORIG x{CALLER_ORIGIN:04X}\n"
              "    JSR INSERTION_SORT\n"
              "    HALT\n"
              f"{routine}"
              ".END\n")
    return assemble(source)


class RecordingMemory(Memory):
    """Memory que anota cada dirección escrita mientras `recording` es True."""

    def __init__(self):
        super().__init__()
        self.recording = False
        self.writes = set()

    def write_byte(self, address, value):
        if self.recording:
            self.writes.add(address)
        super().write_byte(address, value)

    def write_word(self, address, value):
        if self.recording:
            self.writes.update((address, address + 1))
        super().write_word(address, value)


def run_sort(program, base, values, word_before=None):
    """Ejecuta la rutina sobre `values` ubicados en `base`. Devuelve un dict con el estado.

    word_before  si se indica, se escribe en base-2 (la palabra anterior al arreglo).
    """
    memory = RecordingMemory()
    cpu = CPU(memory=memory)
    cpu.load_program(program.data, program.origin)
    end = base + 2 * len(values)
    low, high = max(base - MARGIN, 0), min(end + MARGIN, memory.SIZE)
    for address in range(low, high):
        memory.write_byte(address, FILL_BYTE)
    if word_before is not None:
        memory.write_word(base - 2, word_before & 0xFFFF)
    for index, value in enumerate(values):
        memory.write_word(base + 2 * index, value & 0xFFFF)
    outside = [a for a in range(low, high) if not base <= a < end]
    before = {a: memory.read_byte(a) for a in outside}
    cpu.registers.write(0, base)
    cpu.registers.write(1, len(values))
    cpu.registers.write(6, R6_SENTINEL)

    memory.recording = True
    error = None
    try:
        cpu.run(MAX_STEPS)
    except EXECUTION_ERRORS as exc:          # p. ej. bucle sin fin o acceso inválido
        error = f"{type(exc).__name__}: {exc}"
    memory.recording = False

    return {
        "result": [to_signed16(memory.read_word(base + 2 * i)) for i in range(len(values))],
        "outside_writes": sorted(a for a in memory.writes if not base <= a < end),
        "margin_changed": [a for a in outside if memory.read_byte(a) != before[a]],
        "registers": cpu.registers.values(),
        "halt_reason": cpu.halt_reason,
        "error": error,
        "pc": cpu.registers.pc,
        "instructions": cpu.instruction_count,
    }


def random_cases(seed, count, max_length):
    """Arreglos reproducibles: mezcla de valores chicos (muchos repetidos), extremos y al azar."""
    rng = random.Random(seed)
    extremes = (-32768, -32767, -1, 0, 1, 32766, 32767)
    cases = []
    for _ in range(count):
        length = rng.randint(0, max_length)
        values = []
        for _ in range(length):
            kind = rng.random()
            if kind < 0.35:
                values.append(rng.randint(-3, 3))          # repetidos, negativos y cero
            elif kind < 0.55:
                values.append(rng.choice(extremes))        # extremos de 16 bits
            else:
                values.append(rng.randint(-32768, 32767))
        cases.append(values)
    return cases


# Casos fijos representativos (los mismos tipos que el harness del .asm).
FIXED_CASES = {
    "vacío": [],
    "un elemento": [-42],
    "dos invertidos": [1, -1],
    "negativos, positivos y cero": [-5, 3, -1, 0, -8, 2, -3, 1],
    "repetidos": [4, -2, 4, 0, -2, 0, 4, -2],
    "ya ordenado": [-3, -1, 0, 0, 2, 5, 9],
    "orden inverso": [9, 7, 5, 2, 0, -1, -4, -6, -9],
    "todos iguales": [7, 7, 7, 7, 7],
    "extremos de 16 bits": [32767, -32768, 0, -1, 1, -32768, 32767],
    "16 elementos inversos": list(range(16, 0, -1)),
}


# ----------------------------------------------------------------------
# Pruebas
# ----------------------------------------------------------------------
class InsertionSortRoutineMixin:
    """Verificaciones comunes del contrato sobre una ejecución."""

    def assert_contract(self, state, base, values):
        self.assertIsNone(state["error"], "la ejecución no terminó normalmente")
        self.assertEqual(state["halt_reason"], "HALT", "la rutina no volvió al llamador")
        self.assertEqual(state["pc"], RETURN_ADDRESS + 2, "no terminó en el HALT del llamador")
        self.assertEqual(state["result"], sorted(values), "el arreglo no quedó ordenado")
        self.assertEqual(state["outside_writes"], [],
                         "la rutina escribió fuera del arreglo: "
                         + ", ".join(f"x{a:04X}" for a in state["outside_writes"]))
        self.assertEqual(state["margin_changed"], [], "cambió memoria junto al arreglo")
        registers = state["registers"]
        self.assertEqual(registers[0], base, "R0 (base) no se conservó")
        self.assertEqual(registers[6], R6_SENTINEL, "R6 no se conservó")
        self.assertEqual(registers[7], RETURN_ADDRESS,
                         "R7 cambió: la rutina no debe modificarlo")


class TestInsertionSortRoutine(InsertionSortRoutineMixin, unittest.TestCase):
    """La rutina real, extraída de insertion_sort.asm, en distintas bases y datos."""

    @classmethod
    def setUpClass(cls):
        cls.source = SORT_SOURCE.read_text(encoding="utf-8")
        cls.program = build_caller(extract_routine(cls.source))

    def test_fixed_cases_in_every_base(self):
        """Casos representativos en las seis bases (el mayor, 16 palabras, entra justo en xFFE0)."""
        executed = 0
        for base in BASES:
            for name, values in FIXED_CASES.items():
                if base + 2 * len(values) > 0x10000:
                    continue
                with self.subTest(base=f"x{base:04X}", caso=name):
                    self.assert_contract(run_sort(self.program, base, values), base, values)
                    executed += 1
        self.assertEqual(executed, len(BASES) * len(FIXED_CASES))  # todos entran en xFFE0

    def test_random_arrays_in_every_base(self):
        """Arreglos aleatorios reproducibles (semilla fija), de 0 a 40 elementos."""
        for base in BASES:
            max_length = min(40, (0x10000 - base) // 2)
            for number, values in enumerate(random_cases(seed=base, count=25,
                                                         max_length=max_length)):
                with self.subTest(base=f"x{base:04X}", caso=number, n=len(values)):
                    self.assert_contract(run_sort(self.program, base, values), base, values)

    def test_array_ending_exactly_at_the_end_of_memory(self):
        """El último elemento ocupa xFFFE..xFFFF: no hay acceso fuera de la memoria."""
        for length in (1, 2, 16):
            values = random_cases(seed=length, count=1, max_length=length)[0]
            values = (values + [0] * length)[:length]
            base = 0x10000 - 2 * length
            with self.subTest(base=f"x{base:04X}", n=length):
                self.assert_contract(run_sort(self.program, base, values), base, values)

    def test_signed_comparison_of_elements(self):
        """x8000 (-32768) es el menor y x7FFF (32767) el mayor: comparación con signo."""
        values = [0x7FFF, -0x8000, 0x7FFE, -0x7FFF, 0, -1, 1]
        state = run_sort(self.program, 0x4000, values)
        self.assert_contract(state, 0x4000, values)
        self.assertEqual(state["result"][0], -32768)
        self.assertEqual(state["result"][-1], 32767)

    def test_equal_elements_are_not_shifted(self):
        """El bucle interno se detiene en a[j-1] <= key (no en <): los iguales no se mueven.

        Con 10 elementos iguales el costo debe ser idéntico al de 10 elementos ya
        ordenados (ningún desplazamiento). Con '<' cada inserción desplazaría a todos.
        """
        equal = run_sort(self.program, 0x4000, [5] * 10)
        self.assert_contract(equal, 0x4000, [5] * 10)
        ordered = run_sort(self.program, 0x4000, list(range(10)))
        self.assertEqual(equal["instructions"], ordered["instructions"])

    def test_reverse_order_costs_more_than_sorted_order(self):
        """Mejor caso O(n) y peor caso O(n^2): sirve para detectar un algoritmo distinto."""
        ordered = run_sort(self.program, 0x4000, list(range(16)))["instructions"]
        reverse = run_sort(self.program, 0x4000, list(range(16, 0, -1)))["instructions"]
        self.assertLess(ordered, reverse)
        # 16 elementos: 15 inserciones; en orden inverso, 120 desplazamientos.
        self.assertGreater(reverse, 120 * 6)


class TestSignedAddressRegression(InsertionSortRoutineMixin, unittest.TestCase):
    """Regresión del defecto de la versión original: comparar DIRECCIONES con signo.

    La versión anterior decidía "llegué al principio del arreglo" con CMP + BRn sobre
    direcciones. CMP compara con signo, así que si el arreglo cruza o empieza en x8000
    el bucle se detenía antes de tiempo o seguía por debajo del arreglo. La rutina
    actual usa la igualdad de direcciones (BRz), que no depende del signo.
    """

    # x7FFE: el arreglo cruza de x7FFF a x8000. x8000: empieza en la frontera.
    # La palabra anterior al arreglo (x7000) es MAYOR que todos sus elementos: si la
    # rutina la mirara, la desplazaría dentro del arreglo y perdería un elemento.
    POISONED_BASES = (0x7FFE, 0x8000)
    WORD_BEFORE = 0x7000
    VALUES = [3, -5, 2, -8, 0, 1]

    @classmethod
    def setUpClass(cls):
        cls.source = SORT_SOURCE.read_text(encoding="utf-8")
        cls.routine = extract_routine(cls.source)

    def check_routine(self, routine):
        """Devuelve la lista de fallas de `routine` en las bases que cruzan x8000."""
        program = build_caller(routine)
        failures = []
        for base in self.POISONED_BASES:
            state = run_sort(program, base, self.VALUES, word_before=self.WORD_BEFORE)
            if (state["result"] != sorted(self.VALUES) or state["outside_writes"]
                    or state["error"] or state["halt_reason"] != "HALT"):
                failures.append((base, state["result"], state["outside_writes"]))
        return failures

    def test_current_routine_handles_bases_around_x8000(self):
        program = build_caller(self.routine)
        for base in self.POISONED_BASES:
            with self.subTest(base=f"x{base:04X}"):
                state = run_sort(program, base, self.VALUES, word_before=self.WORD_BEFORE)
                self.assert_contract(state, base, self.VALUES)

    def test_the_regression_check_detects_the_old_defect(self):
        """Meta-prueba: con la comparación con signo de la versión vieja, la regresión falla.

        La prueba `R3 == R0` (BRz) se reemplaza por la condición LITERAL de la versión
        original: "&a[j-1] < base" con CMP (con signo) y BRn. R5 está libre en ese punto
        (la instrucción siguiente lo sobrescribe). Debe fallar en AMBAS bases:
          x7FFE: &a[j-1] >= x8000 es negativo y "menor" que la base: corta antes.
          x8000: &a[j-1] = x7FFE es positivo y "mayor" que la base: sigue por debajo
                 del arreglo, lee x7000 y lo mete en el arreglo.
        Si este test dejara de fallar, la regresión ya no protegería contra el defecto.
        """
        original = "    CMP R3, R0\n    BRz IS_PLACE"
        self.assertEqual(self.routine.count(original), 1,
                         "la rutina cambió: actualizar la mutación de esta meta-prueba")
        mutant = self.routine.replace(
            original, "    ADD R5, R3, #-2\n    CMP R5, R0\n    BRn IS_PLACE")
        failing_bases = [base for base, *_ in self.check_routine(mutant)]
        self.assertEqual(failing_bases, list(self.POISONED_BASES),
                         "la comparación de direcciones con signo no falló en todas las bases")
        self.assertEqual(self.check_routine(self.routine), [])


class TestInsertionSortProgram(unittest.TestCase):
    """El programa completo insertion_sort.asm con su propio harness de 10 casos."""

    def test_program_halts_with_the_exact_success_message(self):
        encoded = assemble(SORT_SOURCE.read_text(encoding="utf-8"))
        result = run_program(LoadedProgram(encoded.origin, encoded.data))
        self.assertIs(result.status, RunStatus.HALTED, result.error_message)
        self.assertEqual(result.halt_reason, "HALT")
        self.assertNotIn("ERROR", result.output)
        self.assertEqual(result.output, "OK: INSERTION SORT - 10 CASOS")

    def test_program_reports_a_wrong_result(self):
        """Si un valor esperado del harness es incorrecto, el programa lo informa."""
        source = SORT_SOURCE.read_text(encoding="utf-8")
        target = "EXP1:\n    .FILL #-8\n"
        self.assertEqual(source.count(target), 1, "cambió la tabla del caso 1")
        encoded = assemble(source.replace(target, "EXP1:\n    .FILL #-7\n"))
        result = run_program(LoadedProgram(encoded.origin, encoded.data))
        self.assertIs(result.status, RunStatus.HALTED)
        self.assertEqual(result.output, "ERROR SORT: CONTENIDO")


if __name__ == "__main__":
    unittest.main()
