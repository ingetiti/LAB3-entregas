"""
__main__.py - CLI del simulador (Lab 3c). Etapa 6.3.

Ejecuta un programa binario (el que genera el ensamblador) desde la terminal:

    python3 -m simulator programa.bin [--max-steps N] [--input-file ARCHIVO]

FLUJO
-----
    argparse -> read_binary (loader) -> run_program (runner) -> salida + resumen + código

La CLI NO ejecuta nada por su cuenta: todo el trabajo lo hacen el loader y el runner.
Solo importa esos dos módulos (nunca la CPU, el ensamblador ni el writer).

ARGUMENTOS
----------
  programa              archivo binario a ejecutar (obligatorio)
  --max-steps N         límite de instrucciones, entero positivo. Si se omite rige el
                        valor por defecto de run_program (se lee de su firma, no se
                        duplica aquí)
  --input-file ARCHIVO  texto UTF-8 que leerá GETC. `-` lee el stdin real. Sin esta
                        opción NO se lee el stdin: GETC recibe fin de entrada (EOF)

STDOUT Y STDERR
---------------
  stdout  EXCLUSIVAMENTE lo que escribió el programa (TRAP OUT/PUTS), tal cual, sin
          agregar saltos de línea.
  stderr  el resumen de la simulación y los mensajes de error. Si la salida del
          programa no termina en salto de línea, se agrega uno SOLO en stderr para que
          el resumen no quede pegado en la terminal.
Se hace flush de stdout antes de escribir en stderr. Es una CLI de texto UTF-8: un
carácter que la terminal no pueda representar se reemplaza por `?` en vez de provocar
un traceback.

CÓDIGOS DE SALIDA
-----------------
  0  la ejecución terminó con HALT (HALTED)
  1  NO se usa: Python lo reserva para excepciones internas no controladas
  2  argumentos inválidos (argparse)
  3  error de archivo o de carga (programa o --input-file)
  4  error de ejecución
  5  se alcanzó el límite de instrucciones

TESTABILIDAD
------------
main() devuelve el código en lugar de terminar el proceso y acepta los flujos por
parámetro (los reales de `sys` si no se pasan). Los mensajes de argparse (ayuda y
errores de uso) también respetan esos flujos. Solo `python3 -m simulator` termina el
proceso, mediante SystemExit(main()).
"""

import argparse
import contextlib
import inspect
import sys
from typing import Optional, Sequence, TextIO

from simulator.loader import LoadError, read_binary
from simulator.runner import RunStatus, run_program

__all__ = ["main"]

EXIT_OK = 0                      # HALTED
# El código 1 NO se usa a propósito: es el que da Python ante una excepción no controlada.
EXIT_USAGE = 2                   # argumentos inválidos
EXIT_LOAD = 3                    # archivo inexistente, ilegible o inválido
EXIT_EXECUTION_ERROR = 4         # RunStatus.ERROR
EXIT_INSTRUCTION_LIMIT = 5       # RunStatus.INSTRUCTION_LIMIT

_EXIT_BY_STATUS = {
    RunStatus.HALTED: EXIT_OK,
    RunStatus.ERROR: EXIT_EXECUTION_ERROR,
    RunStatus.INSTRUCTION_LIMIT: EXIT_INSTRUCTION_LIMIT,
}

# El valor por defecto vive en la API pública del runner (firma de run_program): se lee
# de ahí para documentarlo en la ayuda sin duplicarlo ni importar la CPU.
_DEFAULT_MAX_STEPS = inspect.signature(run_program).parameters["max_steps"].default

_EXIT_CODES_HELP = """\
códigos de salida:
  0  la ejecución terminó con HALT
  2  argumentos inválidos
  3  error de archivo o de carga (programa o --input-file)
  4  error de ejecución
  5  se alcanzó el límite de instrucciones

La salida del programa va a stdout; el resumen y los errores, a stderr."""


def _positive_int(text: str) -> int:
    """Convierte `text` en un entero >= 1 (tipo de --max-steps)."""
    try:
        value = int(text)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"se esperaba un entero positivo, se recibió {text!r}") from None
    if value < 1:
        raise argparse.ArgumentTypeError(
            f"se esperaba un entero positivo (mayor o igual que 1), se recibió {value}")
    return value


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python3 -m simulator",
        description="Ejecuta un programa binario de la ISA de Lab 3c y muestra su salida "
                    "y un resumen de la simulación.",
        epilog=_EXIT_CODES_HELP,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("programa", help="archivo binario a ejecutar")
    parser.add_argument(
        "--max-steps", type=_positive_int, default=_DEFAULT_MAX_STEPS, metavar="N",
        help="límite de instrucciones a ejecutar, entero positivo "
             "(por defecto: %(default)s)")
    parser.add_argument(
        "--input-file", metavar="ARCHIVO",
        help="texto UTF-8 que leerá GETC; '-' lee el stdin. Sin esta opción, GETC "
             "recibe fin de entrada (EOF) y no se lee el stdin")
    return parser


def _write(stream: TextIO, text: str) -> None:
    """Escribe `text` sin traceback si el flujo no puede codificar algún carácter.

    Si el flujo no sabe representar un carácter (por ejemplo, con PYTHONIOENCODING=ascii),
    se escribe el texto con `?` en su lugar. TextIOWrapper codifica el texto completo
    antes de escribir, así que un intento fallido no deja salida a medias.
    """
    try:
        stream.write(text)
    except UnicodeEncodeError:
        encoding = getattr(stream, "encoding", None) or "ascii"
        stream.write(text.encode(encoding, errors="replace").decode(encoding))


def _fail(stderr: TextIO, message: str) -> None:
    _write(stderr, f"error: {message}\n")
    stderr.flush()


def _read_input(path: Optional[str], stdin: TextIO) -> str:
    """Texto que leerá GETC. Sin `path` es "" y NO se toca el stdin.

    `-` lee del flujo stdin y cualquier otro valor es un archivo. Se decodifica SIEMPRE
    como UTF-8 estricto y sin traducir saltos de línea (un CRLF llega a GETC como CR LF).
    Lanza OSError o UnicodeDecodeError, que main convierte en el código 3.
    """
    if path is None:
        return ""
    if path == "-":
        buffer = getattr(stdin, "buffer", None)
        raw = buffer.read() if buffer is not None else stdin.read()
    else:
        with open(path, "rb") as input_file:
            raw = input_file.read()
    return raw.decode("utf-8") if isinstance(raw, bytes) else raw


def _describe_os_error(error: OSError) -> str:
    return error.strerror or str(error)


def _summary(result) -> str:
    state = result.status.name
    if result.ok:
        state = f"{state} ({result.halt_reason})"
    lines = [
        "--- Resumen de la simulación ---",
        f"Estado:            {state}",
        f"Instrucciones:     {result.instruction_count}",
        f"Memoria escrita:   {result.memory_bytes_written} de {result.memory_size} bytes",
        f"PC final:          0x{result.pc:04X}",
    ]
    if result.status is RunStatus.ERROR:
        lines.append(f"error de ejecución: {result.error_type}: {result.error_message}")
    elif result.status is RunStatus.INSTRUCTION_LIMIT:
        lines.append("aviso: se alcanzó el límite de instrucciones antes de que el programa "
                     "terminara")
        lines.append("       (¿bucle infinito, programa largo o falta HALT?). "
                     "Use --max-steps para ampliarlo.")
    return "\n".join(lines) + "\n"


def main(argv: Optional[Sequence[str]] = None, *, stdin: Optional[TextIO] = None,
         stdout: Optional[TextIO] = None, stderr: Optional[TextIO] = None) -> int:
    """Ejecuta la CLI y devuelve el código de salida (ver el docstring del módulo).

    argv    argumentos sin el nombre del programa; si es None se usa sys.argv[1:]
    stdin, stdout, stderr
            flujos de texto; si no se pasan, los reales de `sys`. Todos los mensajes,
            incluidos los de argparse, se escriben en ellos.
    """
    stdin = sys.stdin if stdin is None else stdin
    stdout = sys.stdout if stdout is None else stdout
    stderr = sys.stderr if stderr is None else stderr

    # argparse escribe en sys.stdout / sys.stderr: se redirigen a los flujos recibidos.
    try:
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            args = _build_parser().parse_args(argv)
    except SystemExit as request:            # --help (0) o error de uso (2)
        return request.code if isinstance(request.code, int) else EXIT_OK

    try:
        program = read_binary(args.programa)
    except LoadError as error:
        _fail(stderr, f"no se pudo cargar {args.programa!r}: {error}")
        return EXIT_LOAD
    except OSError as error:
        _fail(stderr, f"no se pudo abrir {args.programa!r}: {_describe_os_error(error)}")
        return EXIT_LOAD

    source_name = "stdin" if args.input_file == "-" else repr(args.input_file)
    try:
        input_text = _read_input(args.input_file, stdin)
    except UnicodeDecodeError as error:
        _fail(stderr, f"la entrada {source_name} no es UTF-8 válido "
                      f"(byte {error.start}: {error.reason})")
        return EXIT_LOAD
    except OSError as error:
        _fail(stderr, f"no se pudo leer la entrada {source_name}: "
                      f"{_describe_os_error(error)}")
        return EXIT_LOAD

    result = run_program(program, stdin=input_text, max_steps=args.max_steps)

    _write(stdout, result.output)
    stdout.flush()
    separator = "\n" if result.output and not result.output.endswith("\n") else ""
    _write(stderr, separator + _summary(result))
    stderr.flush()
    return _EXIT_BY_STATUS[result.status]


if __name__ == "__main__":
    raise SystemExit(main())
