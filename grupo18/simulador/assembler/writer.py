"""
writer.py - Escritura del programa ensamblado en un archivo binario (Lab 3c). Etapa 5.6.

Toma el EncodedProgram que devuelve assemble() y lo guarda en disco. No parsea,
no calcula direcciones, no codifica, no ejecuta y no modifica el programa: solo
da forma de archivo a un resultado que ya existe.

FORMATO DEL ARCHIVO (formato B: origen + payload)
-------------------------------------------------
    desplazamiento  tamaño   contenido
    --------------  -------  ---------------------------------------------------
    0               2 bytes  origen (EncodedProgram.origin), Little Endian:
                             primero el byte BAJO y después el ALTO
    2               N bytes  payload (EncodedProgram.data), copiado tal cual

  - No hay magic, versión ni campo de longitud: el tamaño del payload es
    `tamaño del archivo - 2`. Un programa sin bytes produce un archivo de 2 bytes.
  - El payload ya está en el orden de memoria (el encoder emitió cada palabra en
    Little Endian), así que no se reordena ni se interpreta: es la imagen exacta de
    lo que debe quedar en memoria desde `origen`. Incluye el relleno de alineación
    y los datos. Puede tener longitud impar (por ejemplo, tras un .STRINGZ).
  - Solo el origen es un campo multibyte propio del archivo; se guarda en Little
    Endian, igual que las palabras de la ISA, para poder leerlo como una palabra
    de la máquina.

Ejemplo: .ORIG x3000 / ADD R0, R0, #1 / HALT   ->   00 30 | 11 00 00 C0

Cargarlo después en la CPU es: leer los 2 primeros bytes como origen y entregar el
resto, junto con ese origen, a CPU.load_program(data, address). Ese lector (loader)
no forma parte de esta etapa.

ERRORES
-------
  TypeError  `program` no es un EncodedProgram (no se acepta `bytes` sueltos: sin
             el origen no alcanzan para cargar el programa).
  OSError    cualquier problema del sistema operativo (ruta inexistente, es un
             directorio, permisos, disco lleno...) se propaga TAL CUAL, sin
             capturarse ni traducirse. No se crean directorios y un archivo
             existente se SOBRESCRIBE.

El contenido se construye completo ANTES de abrir el archivo: con un `program`
inválido no se toca el disco y un archivo existente no se trunca.
"""

from assembler.encoder import EncodedProgram
from simulator.isa import BYTE_BITS, WORD_BITS

__all__ = ["serialize_binary", "write_binary"]

ORIGIN_BYTES = WORD_BITS // BYTE_BITS        # 2: el origen ocupa una palabra


def serialize_binary(program):
    """Bytes del archivo (formato B) de `program`. Función pura: no hace E/S."""
    if not isinstance(program, EncodedProgram):
        raise TypeError(f"se esperaba un EncodedProgram, se recibió {type(program).__name__}")
    return program.origin.to_bytes(ORIGIN_BYTES, "little") + program.data


def write_binary(program, path):
    """Guarda `program` en `path` (formato B). Sobrescribe si el archivo existe.

    `path` puede ser str o cualquier objeto os.PathLike. No devuelve nada.
    Lanza TypeError si `program` no es un EncodedProgram y propaga los OSError.
    """
    content = serialize_binary(program)          # primero valida; después toca el disco
    with open(path, "wb") as binary_file:        # "wb": sin traducción de saltos de línea
        binary_file.write(content)
