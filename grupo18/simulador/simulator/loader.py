"""
loader.py - Lectura de programas binarios para el simulador (Lab 3c). Etapa 6.1.

Interpreta el archivo que genera el ensamblador y lo entrega como un LoadedProgram
(origen + bytes). NO ejecuta nada, NO toca la CPU ni la memoria y NO importa el
paquete del ensamblador: el simulador debe poder funcionar sin él. Quien cargue el
programa en la CPU (el runner, etapa 6.2) hará `cpu.load_program(p.data, p.origin)`.

FORMATO DEL ARCHIVO (formato B: origen + payload)
-------------------------------------------------
    desplazamiento  tamaño   contenido
    --------------  -------  ---------------------------------------------------
    0               2 bytes  origen, Little Endian (primero el byte BAJO)
    2               N bytes  payload: imagen exacta de la memoria desde `origen`

  - No hay magic, versión ni longitud: el payload mide `tamaño del archivo - 2`.
  - Un archivo de exactamente 2 bytes es VÁLIDO (programa sin bytes).
  - El payload se devuelve tal cual: ni se reordena ni se interpreta. Puede
    contener relleno de alineación y datos, y tener longitud impar.

Este contrato es el inverso de assembler.writer.serialize_binary. Como el loader no
puede importar al ensamblador, la consistencia entre ambos la garantizan los tests
de ida y vuelta (tests/test_loader.py), no el código.

ERRORES
-------
  LoadError  el CONTENIDO no cumple el formato: archivo vacío, origen incompleto,
             origen impar, o programa que no entra en memoria / archivo demasiado
             grande.
  OSError    problemas del sistema de archivos (no existe, es un directorio,
             permisos...): se propaga TAL CUAL, sin capturarse ni traducirse.
  TypeError  argumento de tipo incorrecto (no es bytes, o la ruta no es válida).

Las reglas de ubicación (origen par y programa dentro de la memoria) están en un
solo lugar, `_placement_problem`, que usan tanto parse_binary como LoadedProgram.
"""

from dataclasses import dataclass

from simulator.isa import BYTE_BITS, MEMORY_SIZE, PC_INCREMENT, WORD_BITS

__all__ = ["LoadError", "LoadedProgram", "parse_binary", "read_binary"]

ORIGIN_BYTES = WORD_BITS // BYTE_BITS               # 2: el origen ocupa una palabra
MAX_FILE_SIZE = ORIGIN_BYTES + MEMORY_SIZE          # origen + memoria completa


class LoadError(Exception):
    """El contenido del archivo no cumple el formato de programa binario."""


def _hex(address):
    return f"x{address:04X}"


def _placement_problem(origin, length):
    """Describe por qué (origen, longitud) no es una ubicación válida, o devuelve None."""
    if not 0 <= origin < MEMORY_SIZE:
        return (f"el origen {origin} está fuera del rango de direcciones "
                f"(x0000 a {_hex(MEMORY_SIZE - 1)})")
    if origin % PC_INCREMENT:
        return (f"el origen {_hex(origin)} es impar: las instrucciones deben comenzar "
                f"en direcciones pares")
    if origin + length > MEMORY_SIZE:
        return (f"el programa ({length} bytes) no cabe en memoria desde {_hex(origin)}: "
                f"el espacio llega hasta {_hex(MEMORY_SIZE - 1)}")
    return None


@dataclass(frozen=True)
class LoadedProgram:
    """Programa leído de un archivo, listo para entregar a CPU.load_program.

    origin  dirección de carga (par, 0..0xFFFE)
    data    bytes del programa (inmutables); puede estar vacío

    Garantiza que el programa entra en memoria desde `origin`. Un LoadedProgram
    inválido no puede existir: el constructor lanza TypeError o ValueError.
    """
    origin: int
    data: bytes

    def __post_init__(self):
        if isinstance(self.origin, bool) or not isinstance(self.origin, int):
            raise TypeError(f"origin debe ser un entero, se recibió {self.origin!r}")
        if not isinstance(self.data, (bytes, bytearray)):
            raise TypeError(f"data debe ser bytes, se recibió {type(self.data).__name__}")
        object.__setattr__(self, "data", bytes(self.data))      # copia inmutable
        problem = _placement_problem(self.origin, len(self.data))
        if problem:
            raise ValueError(problem)


def parse_binary(content):
    """Interpreta los bytes de un archivo (formato B) y devuelve un LoadedProgram.

    Función pura: no hace E/S. Lanza LoadError si el contenido no cumple el formato
    y TypeError si `content` no es bytes ni bytearray.
    """
    if not isinstance(content, (bytes, bytearray)):
        raise TypeError(f"se esperaban bytes, se recibió {type(content).__name__}")
    if len(content) == 0:
        raise LoadError(f"el archivo está vacío: se esperaban al menos {ORIGIN_BYTES} "
                        f"bytes con el origen del programa")
    if len(content) < ORIGIN_BYTES:
        raise LoadError(f"origen incompleto: el archivo tiene {len(content)} byte(s) y el "
                        f"origen ocupa {ORIGIN_BYTES}")
    if len(content) > MAX_FILE_SIZE:
        raise LoadError(f"archivo demasiado grande: supera el máximo de {MAX_FILE_SIZE} bytes "
                        f"({ORIGIN_BYTES} de origen + {MEMORY_SIZE} de memoria)")
    origin = int.from_bytes(content[:ORIGIN_BYTES], "little")
    payload = bytes(content[ORIGIN_BYTES:])
    problem = _placement_problem(origin, len(payload))
    if problem:
        raise LoadError(problem)
    return LoadedProgram(origin, payload)


def read_binary(path):
    """Lee el archivo `path` (str o os.PathLike) y devuelve su LoadedProgram.

    Se leen como máximo MAX_FILE_SIZE + 1 bytes: un archivo gigante se rechaza sin
    cargarlo entero en memoria. Los OSError del sistema de archivos se propagan.
    """
    with open(path, "rb") as binary_file:        # "rb": sin traducción de saltos de línea
        content = binary_file.read(MAX_FILE_SIZE + 1)
    return parse_binary(content)
