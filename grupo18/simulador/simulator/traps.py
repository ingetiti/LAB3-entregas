"""
traps.py - Servicios TRAP e interfaz de entrada/salida (ISA Lab 3c).

Por qué es un módulo aparte:
  - Separa la entrada/salida (consola, archivos, pruebas) del núcleo de la
    CPU: la CPU solo sabe "ejecutar TRAP v"; qué significa cada vector se
    resuelve acá.
  - Permite probar los servicios sin teclado ni pantalla, inyectando flujos
    de texto en memoria (io.StringIO).

Interfaz de E/S (cualquier objeto con estos dos métodos sirve):
  read_char() -> str | None   un carácter, o None si no hay más entrada (EOF)
  write(text)                 escribe texto

Servicios (inspirados en LC-3; en esta ISA los caracteres son de 8 bits):
  x20 GETC  Lee un carácter y lo deja en R0 (bits 15..8 = 0). Fin de entrada:
            R0 = 0xFFFF (-1). Caracteres mayores a 0xFF se reemplazan por '?'.
  x21 OUT   Escribe el carácter de los 8 bits bajos de R0.
  x22 PUTS  Escribe la cadena que comienza en la dirección R0 (un carácter
            por BYTE) hasta encontrar un byte 0.
  x25 HALT  Detiene la ejecución.

Los servicios no modifican las banderas N/Z/P.
"""

import sys

# Los vectores se definen en isa.py; se re-exportan con los mismos nombres.
from simulator.isa import BYTE_MASK, TRAP_GETC, TRAP_HALT, TRAP_OUT, TRAP_PUTS  # noqa: F401

EOF_VALUE = 0xFFFF      # lo que ve el programa cuando se acaba la entrada


class UnknownTrapError(Exception):
    """El vector del TRAP no corresponde a ningún servicio definido."""


class ConsoleIO:
    """E/S por flujos de texto. Por defecto, la consola (stdin/stdout)."""

    def __init__(self, stdin=None, stdout=None):
        self.stdin = stdin if stdin is not None else sys.stdin
        self.stdout = stdout if stdout is not None else sys.stdout

    def read_char(self):
        char = self.stdin.read(1)
        return char if char else None       # '' significa fin de entrada

    def write(self, text):
        self.stdout.write(text)
        self.stdout.flush()


class TrapServices:
    """Resuelve los vectores TRAP usando una interfaz de E/S."""

    def __init__(self, io):
        self._io = io
        self._services = {
            TRAP_GETC: self._getc,
            TRAP_OUT: self._out,
            TRAP_PUTS: self._puts,
            TRAP_HALT: self._halt,
        }

    def handle(self, vector, registers, memory):
        """Ejecuta el servicio `vector`.

        Devuelve True si el programa debe detenerse, False en caso contrario.
        Lanza UnknownTrapError si el vector no existe.
        """
        service = self._services.get(vector)
        if service is None:
            raise UnknownTrapError(f"Vector TRAP desconocido: x{vector:02X}")
        return bool(service(registers, memory))

    # --- servicios -----------------------------------------------------
    def _getc(self, registers, memory):
        char = self._io.read_char()
        if char is None:
            value = EOF_VALUE
        else:
            code = ord(char)
            value = code if code <= BYTE_MASK else ord("?")
        registers.write(0, value)

    def _out(self, registers, memory):
        self._io.write(chr(registers.read(0) & BYTE_MASK))

    def _puts(self, registers, memory):
        address = registers.read(0)
        chars = []
        # Se lee TODA la cadena antes de escribir: si falta el terminador y
        # se sale de la memoria, Memory lanza MemoryAccessError sin que
        # haya salido texto parcial.
        while True:
            byte = memory.read_byte(address)
            if byte == 0:
                break
            chars.append(chr(byte))
            address += 1
        self._io.write("".join(chars))

    def _halt(self, registers, memory):
        return True