"""
runner.py - Ejecución de un programa cargado y resultado estructurado (Lab 3c). Etapa 6.2.

Conecta el loader con la CPU:

    LoadedProgram --run_program--> CPU nueva --> RunResult

Cada llamada crea una CPU, una memoria y unos registros NUEVOS: ninguna ejecución
puede contaminar a la siguiente. La E/S de la CPU se reemplaza por flujos en memoria
(io.StringIO): la entrada de GETC sale del argumento `stdin` y todo lo que escriben
los TRAP de salida se captura y se devuelve en el resultado. Nunca se toca el
`sys.stdin` ni el `sys.stdout` reales.

CÓMO TERMINA UNA EJECUCIÓN
--------------------------
  HALTED             la CPU se detuvo (HALT o TRAP x25): fin normal.
  INSTRUCTION_LIMIT  se agotó `max_steps` sin que el programa se detuviera. No es
                     necesariamente un fallo del programa (puede ser largo) ni un bucle
                     infinito: es una ejecución INTERRUMPIDA. Un programa sin HALT, o
                     vacío, no falla: la CPU ejecuta ceros (ADD R0,R0,R0) hasta este límite.
  ERROR              la CPU lanzó una excepción de ejecución (instrucción inválida, TRAP
                     desconocido, salto a dirección impar, acceso fuera de memoria...).

La salida emitida ANTES de un error se conserva, la instrucción que falla no se
cuenta (así lo hace la CPU) y `pc` queda apuntando a ella.

QUÉ SE CONVIERTE EN RESULTADO Y QUÉ SE PROPAGA
----------------------------------------------
Solo se convierten en resultado las excepciones de ejecución que declara la CPU en
EXECUTION_ERRORS, es decir, los fallos causados por el PROGRAMA. Los errores de USO
(tipo de argumento inválido, `max_steps` inválido) y los bugs internos se propagan:
no se captura Exception. ExecutionLimitError pertenece a EXECUTION_ERRORS, por eso se
captura ANTES y por separado.
"""

import io
from dataclasses import dataclass
from enum import Enum

from simulator.cpu import CPU, DEFAULT_MAX_STEPS, EXECUTION_ERRORS, ExecutionLimitError
from simulator.loader import LoadedProgram
from simulator.registers import NUM_REGISTERS, WORD_MASK
from simulator.traps import ConsoleIO

__all__ = ["RunResult", "RunStatus", "run_program"]


class RunStatus(Enum):
    """Motivo por el que terminó (o se interrumpió) una ejecución."""
    HALTED = "HALTED"
    INSTRUCTION_LIMIT = "INSTRUCTION_LIMIT"
    ERROR = "ERROR"


def _is_int(value):
    # bool es subclase de int en Python; se rechaza explícitamente.
    return isinstance(value, int) and not isinstance(value, bool)


def _check_int(name, value, minimum, maximum=None):
    if not _is_int(value):
        raise TypeError(f"{name} debe ser un entero, se recibió {value!r}")
    if value < minimum or (maximum is not None and value > maximum):
        limits = f"al menos {minimum}" if maximum is None else f"entre {minimum} y {maximum}"
        raise ValueError(f"{name} debe estar {limits}, se recibió {value}")


def _check_optional_text(name, value):
    if value is not None and not isinstance(value, str):
        raise TypeError(f"{name} debe ser texto o None, se recibió {value!r}")


@dataclass(frozen=True)
class RunResult:
    """Resultado de una ejecución. Inmutable; sus invariantes se validan al construirlo.

    status                motivo de finalización (RunStatus)
    output                todo lo escrito por los TRAP de salida (también si hubo error)
    instruction_count     instrucciones ejecutadas con éxito (HALT cuenta; la que falla, no)
    memory_bytes_written  direcciones distintas escritas, incluida la imagen cargada
    memory_size           tamaño de la memoria en bytes
    pc                    PC final: tras un HALT, la dirección siguiente; en un error o al
                          agotar el límite, la instrucción que no llegó a ejecutarse
    halt_reason           'HALT' o 'TRAP x25' (solo con HALTED)
    error_type            nombre de la clase de la excepción (solo con ERROR)
    error_message         texto de la excepción (solo con ERROR)
    registers             R0..R7 finales, tupla de 8 enteros de 16 bits

    Invariantes:
      HALTED             halt_reason definido; error_type y error_message None
      INSTRUCTION_LIMIT  halt_reason, error_type y error_message None
      ERROR              halt_reason None; error_type y error_message definidos
    """
    status: RunStatus
    output: str
    instruction_count: int
    memory_bytes_written: int
    memory_size: int
    pc: int
    halt_reason: object
    error_type: object
    error_message: object
    registers: tuple

    def __post_init__(self):
        if not isinstance(self.status, RunStatus):
            raise TypeError(f"status debe ser un RunStatus, se recibió {self.status!r}")
        if not isinstance(self.output, str):
            raise TypeError(f"output debe ser texto, se recibió {self.output!r}")
        _check_int("instruction_count", self.instruction_count, 0)
        _check_int("memory_size", self.memory_size, 1)
        _check_int("memory_bytes_written", self.memory_bytes_written, 0, self.memory_size)
        _check_int("pc", self.pc, 0, WORD_MASK)
        if not isinstance(self.registers, tuple) or len(self.registers) != NUM_REGISTERS:
            raise TypeError(f"registers debe ser una tupla de {NUM_REGISTERS} enteros, "
                            f"se recibió {self.registers!r}")
        for number, value in enumerate(self.registers):
            _check_int(f"registers[{number}]", value, 0, WORD_MASK)
        for name in ("halt_reason", "error_type", "error_message"):
            _check_optional_text(name, getattr(self, name))

        has_halt = self.halt_reason is not None
        has_error = self.error_type is not None or self.error_message is not None
        if self.status is RunStatus.HALTED:
            if not has_halt or has_error:
                raise ValueError("HALTED requiere halt_reason y no admite error_type/error_message")
        elif self.status is RunStatus.INSTRUCTION_LIMIT:
            if has_halt or has_error:
                raise ValueError("INSTRUCTION_LIMIT no admite halt_reason, error_type "
                                 "ni error_message")
        else:
            if has_halt or self.error_type is None or self.error_message is None:
                raise ValueError("ERROR requiere error_type y error_message y no admite halt_reason")

    @property
    def ok(self):
        """True exclusivamente si la ejecución terminó con HALT o TRAP x25."""
        return self.status is RunStatus.HALTED


def run_program(program, stdin="", max_steps=DEFAULT_MAX_STEPS):
    """Ejecuta `program` en una CPU nueva y devuelve su RunResult.

    program    un LoadedProgram (TypeError si no lo es)
    stdin      texto completo que leerá GETC; al agotarse, GETC devuelve EOF (0xFFFF).
               No es interactivo. TypeError si no es str
    max_steps  límite de instrucciones; se valida con CPU.run (ValueError si es inválido)

    Los fallos del programa (ver el docstring del módulo) se devuelven en el resultado;
    los errores de uso y los bugs internos se propagan.
    """
    if not isinstance(program, LoadedProgram):
        raise TypeError(f"se esperaba un LoadedProgram, se recibió {type(program).__name__}")
    if not isinstance(stdin, str):
        raise TypeError(f"stdin debe ser texto, se recibió {type(stdin).__name__}")

    captured_output = io.StringIO()
    cpu = CPU(io=ConsoleIO(io.StringIO(stdin), captured_output))
    cpu.load_program(program.data, program.origin)

    status = RunStatus.HALTED
    error_type = error_message = None
    try:
        cpu.run(max_steps)
    except ExecutionLimitError:                  # ANTES que EXECUTION_ERRORS: es subclase
        status = RunStatus.INSTRUCTION_LIMIT
    except EXECUTION_ERRORS as error:
        status = RunStatus.ERROR
        error_type = type(error).__name__
        error_message = str(error)

    return RunResult(
        status=status,
        output=captured_output.getvalue(),
        instruction_count=cpu.instruction_count,
        memory_bytes_written=cpu.memory_used,
        memory_size=cpu.memory.size,
        pc=cpu.registers.pc,
        halt_reason=cpu.halt_reason if status is RunStatus.HALTED else None,
        error_type=error_type,
        error_message=error_message,
        registers=cpu.registers.values(),
    )