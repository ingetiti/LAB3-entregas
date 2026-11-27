"""
__main__.py - CLI del ensamblador (Lab 3c). Etapa 6.4.

Ensambla un archivo Assembly y escribe el binario que ejecuta el simulador:

    python3 -m assembler programa.asm [-o salida.bin] [--external NOMBRE=DIRECCIÓN ...]
    python3 -m simulator programa.bin

FLUJO
-----
    argparse -> lectura del fuente (UTF-8) -> assemble -> write_binary -> resumen + código

La CLI NO ensambla ni escribe nada por su cuenta: todo el trabajo lo hacen assemble() y
write_binary(). No analiza texto Assembly, no codifica, no valida direcciones de símbolos
externos y no enlaza: es solo la capa de terminal.

ARGUMENTOS
----------
  fuente                    archivo Assembly (obligatorio, uno solo)
  -o, --output ARCHIVO      binario de salida. Por defecto, el fuente con la extensión
                            reemplazada por `.bin` (si no tiene extensión, se agrega).
                            Un binario existente se sobrescribe; el directorio de destino
                            debe existir (no se crean directorios)
  --external NOMBRE=DIR     dirección de un símbolo declarado con .EXTERNAL; se puede
                            repetir. DIR: x3100, 0x3100 o decimal (3100). La CLI solo
                            comprueba la sintaxis, que el nombre no esté vacío y que no se
                            repita; el rango y la declaración los valida el ensamblador

PROTECCIÓN DEL FUENTE
---------------------
Nunca se escribe sobre el archivo fuente. Se comparan las rutas ya resueltas (rutas
relativas y absolutas, `./`, enlaces simbólicos) y, si ambos existen, también su identidad
en disco (os.path.samefile, que detecta los enlaces duros). Si salida y fuente son el mismo
archivo, el código es 2 y no se toca ningún byte. No hay opción para forzarlo.

STDOUT Y STDERR
---------------
  stdout  vacío al ensamblar (con éxito o sin él). Solo recibe el texto de --help.
  stderr  el resumen, los errores y las estadísticas.
Un carácter que la terminal no pueda representar se reemplaza por `?` en lugar de provocar
un traceback.

CÓDIGOS DE SALIDA
-----------------
  0  ensamblado correcto
  1  NO se usa: Python lo reserva para excepciones internas no controladas
  2  argumentos inválidos (argparse, --external, salida igual al fuente)
  3  error de lectura del fuente (no existe, es un directorio, permisos, no es UTF-8)
  4  error de ensamblado (sintaxis, mapa de memoria o codificación)
  5  error de escritura del binario

Si el ensamblado falla no se escribe nada y un binario anterior queda intacto.

TESTABILIDAD
------------
main() devuelve el código en lugar de terminar el proceso y acepta los flujos por
parámetro (los reales de `sys` si no se pasan). Los mensajes de argparse también respetan
esos flujos. Solo `python3 -m assembler` termina el proceso, mediante SystemExit(main()).
"""

import argparse
import contextlib
import os
import re
import sys
from typing import List, Optional, Sequence, Tuple, TextIO

from assembler.assembler import ASSEMBLY_ERRORS, assemble
from assembler.encoder import EncodeErrors
from assembler.parser import ParseErrors
from assembler.symbols import SymbolErrors
from assembler.writer import write_binary

__all__ = ["main"]

EXIT_OK = 0                      # ensamblado correcto
# El código 1 NO se usa a propósito: es el que da Python ante una excepción no controlada.
EXIT_USAGE = 2                   # argumentos inválidos
EXIT_READ = 3                    # el fuente no se pudo leer
EXIT_ASSEMBLY = 4                # error de sintaxis, de símbolos o de codificación
EXIT_WRITE = 5                   # el binario no se pudo escribir

DEFAULT_EXTENSION = ".bin"

_PHASE_BY_ERROR = {
    ParseErrors: "sintaxis",
    SymbolErrors: "mapa de memoria",
    EncodeErrors: "codificación",
}

_EXIT_CODES_HELP = """\
códigos de salida:
  0  ensamblado correcto
  1  no se usa (Python lo reserva para excepciones no controladas)
  2  argumentos inválidos (incluida una salida igual al fuente)
  3  error de lectura del fuente
  4  error de ensamblado
  5  error de escritura del binario

Nunca se sobrescribe el fuente. Si el ensamblado falla no se escribe el binario y uno
anterior queda intacto. Los errores y el resumen van a stderr; stdout queda vacío.

ejemplos:
  python3 -m assembler programa.asm
  python3 -m assembler programa.asm -o build/programa.bin
  python3 -m assembler programa.asm --external BUFFER=x3100 --external RUTINA=0x3200"""

_HEXADECIMAL_ADDRESS = re.compile(r"(?:0[xX]|[xX])([0-9a-fA-F]+)")
_DECIMAL_ADDRESS = re.compile(r"[0-9]+")


class _SafeText:
    """Flujo que reemplaza con `?` lo que el destino no sabe codificar (para argparse)."""

    def __init__(self, stream: TextIO) -> None:
        self._stream = stream

    def write(self, text: str) -> None:
        _write(self._stream, text)

    def flush(self) -> None:
        self._stream.flush()


def _address(text: str) -> Optional[int]:
    """Valor de una dirección escrita como x3100, 0x3100 o decimal; None si no es válida.

    Solo se comprueba la sintaxis: el rango (x0000 a xFFFF) lo valida el ensamblador.
    """
    text = text.strip()
    try:
        hexadecimal = _HEXADECIMAL_ADDRESS.fullmatch(text)
        if hexadecimal:
            return int(hexadecimal.group(1), 16)
        if _DECIMAL_ADDRESS.fullmatch(text):
            return int(text, 10)
    except ValueError:                      # decimal con miles de dígitos (límite de Python)
        return None
    return None


def _external_argument(text: str) -> Tuple[str, int]:
    """Convierte NOMBRE=DIRECCIÓN en (nombre, dirección) (tipo de --external)."""
    name, separator, written = text.partition("=")
    if not separator:
        raise argparse.ArgumentTypeError(
            f"se esperaba NOMBRE=DIRECCIÓN, se recibió {text!r}")
    name = name.strip()
    if not name:
        raise argparse.ArgumentTypeError(
            f"el nombre del símbolo está vacío en {text!r}")
    address = _address(written)
    if address is None:
        raise argparse.ArgumentTypeError(
            f"dirección inválida {written.strip()!r} para '{name}': use x3100, 0x3100 "
            f"o un número decimal (3100)")
    return name, address


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python3 -m assembler",
        description="Ensambla un archivo Assembly de la ISA de Lab 3c y escribe el binario "
                    "que ejecuta `python3 -m simulator`.",
        epilog=_EXIT_CODES_HELP,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        allow_abbrev=False,
    )
    parser.add_argument("fuente", help="archivo Assembly (UTF-8) a ensamblar")
    parser.add_argument(
        "-o", "--output", metavar="ARCHIVO",
        help="binario de salida (por defecto: el fuente con la extensión reemplazada por "
             ".bin). Se sobrescribe si existe, salvo que sea el propio fuente; el "
             "directorio de destino debe existir")
    parser.add_argument(
        "--external", action="append", type=_external_argument, default=[],
        metavar="NOMBRE=DIRECCIÓN",
        help="dirección de un símbolo declarado con .EXTERNAL; se puede repetir. "
             "DIRECCIÓN: x3100, 0x3100 o decimal (3100)")
    return parser


def _write(stream: TextIO, text: str) -> None:
    """Escribe `text` sin traceback si el flujo no puede codificar algún carácter."""
    try:
        stream.write(text)
    except UnicodeEncodeError:
        encoding = getattr(stream, "encoding", None) or "ascii"
        stream.write(text.encode(encoding, errors="replace").decode(encoding))


def _fail(stderr: TextIO, message: str) -> None:
    _write(stderr, f"error: {message}\n")
    stderr.flush()


def _describe_os_error(error: OSError) -> str:
    return error.strerror or str(error)


def _parse_args(argv: Optional[Sequence[str]], stdout: TextIO, stderr: TextIO):
    """Devuelve (argumentos, None) o (None, código) si hay que terminar ya (ayuda o uso)."""
    parser = _build_parser()
    # argparse escribe en sys.stdout / sys.stderr: se redirigen a los flujos recibidos.
    try:
        with contextlib.redirect_stdout(_SafeText(stdout)), \
                contextlib.redirect_stderr(_SafeText(stderr)):
            args = parser.parse_args(argv)
            seen = set()
            for name, _address_value in args.external:
                if name in seen:
                    parser.error(f"el símbolo externo '{name}' se indicó más de una vez")
                seen.add(name)
    except SystemExit as request:            # --help (0) o error de uso (2)
        return None, request.code if isinstance(request.code, int) else EXIT_OK
    return args, None


def _default_output(source: str) -> str:
    """El fuente con la extensión reemplazada por .bin (o agregada si no tiene)."""
    return os.path.splitext(source)[0] + DEFAULT_EXTENSION


def _canonical(path: str) -> str:
    return os.path.normcase(os.path.realpath(path))


def _same_file(source: str, output: str) -> bool:
    """True si `output` es el mismo archivo que `source` (rutas resueltas o identidad)."""
    if _canonical(source) == _canonical(output):
        return True
    try:
        return os.path.samefile(source, output)      # enlaces duros u otras equivalencias
    except OSError:                                  # alguno no existe: no pueden ser el mismo
        return False


def _read_source(path: str) -> str:
    """Texto Assembly del archivo: UTF-8 estricto, tolera un BOM, no traduce saltos de línea.

    Lanza OSError o UnicodeDecodeError, que main convierte en el código 3.
    """
    with open(path, "rb") as source_file:
        raw = source_file.read()
    return raw.decode("utf-8-sig")


def _report_assembly_errors(stderr: TextIO, source_name: str, failure) -> None:
    """Escribe TODOS los errores de la fase que falló (con línea y texto si los hay)."""
    errors = failure.errors
    phase = _PHASE_BY_ERROR[type(failure)]
    lines: List[str] = []
    for error in errors:
        if error.line_number is not None:
            lines.append(f"{source_name}:{error.line_number}: error: {error.message}")
        else:
            lines.append(f"{source_name}: error: {error.message}")
        if error.source is not None:
            prefix = f"{error.line_number:>5}" if error.line_number is not None else "     "
            lines.append(f"  {prefix} | {error.source.rstrip()}")
    noun = "error" if len(errors) == 1 else "errores"
    lines.append(f"ensamblado fallido en la fase de {phase}: {len(errors)} {noun}; "
                 f"no se escribió ningún binario")
    _write(stderr, "\n".join(lines) + "\n")
    stderr.flush()


def _summary(source: str, output: str, program) -> str:
    unit = "byte" if program.size == 1 else "bytes"
    return "\n".join([
        "--- Resumen del ensamblado ---",
        f"Fuente:            {source}",
        f"Binario:           {output}",
        f"Origen:            0x{program.origin:04X}",
        f"Tamaño:            {program.size} {unit}",
        f"Dirección final:   0x{program.end_address:04X} (primera dirección libre)",
    ]) + "\n"


def main(argv: Optional[Sequence[str]] = None, *, stdout: Optional[TextIO] = None,
         stderr: Optional[TextIO] = None) -> int:
    """Ejecuta la CLI y devuelve el código de salida (ver el docstring del módulo).

    argv    argumentos sin el nombre del programa; si es None se usa sys.argv[1:]
    stdout, stderr
            flujos de texto; si no se pasan, los reales de `sys`. Todos los mensajes,
            incluidos los de argparse, se escriben en ellos.
    """
    stdout = sys.stdout if stdout is None else stdout
    stderr = sys.stderr if stderr is None else stderr

    args, code = _parse_args(argv, stdout, stderr)
    if args is None:
        return code

    source_path = args.fuente
    output_path = args.output if args.output is not None else _default_output(source_path)

    if _same_file(source_path, output_path):
        _fail(stderr, f"la salida {output_path!r} es el propio archivo fuente; "
                      f"nunca se sobrescribe el fuente (elija otro destino con -o)")
        return EXIT_USAGE

    try:
        source = _read_source(source_path)
    except UnicodeDecodeError as error:
        _fail(stderr, f"el fuente {source_path!r} no es UTF-8 válido "
                      f"(byte {error.start}: {error.reason})")
        return EXIT_READ
    except OSError as error:
        _fail(stderr, f"no se pudo leer el fuente {source_path!r}: "
                      f"{_describe_os_error(error)}")
        return EXIT_READ

    try:
        program = assemble(source, external_symbols=dict(args.external))
    except ASSEMBLY_ERRORS as failure:
        _report_assembly_errors(stderr, source_path, failure)
        return EXIT_ASSEMBLY

    try:
        write_binary(program, output_path)
    except OSError as error:
        _fail(stderr, f"no se pudo escribir el binario {output_path!r}: "
                      f"{_describe_os_error(error)}")
        return EXIT_WRITE

    _write(stderr, _summary(source_path, output_path, program))
    stderr.flush()
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
