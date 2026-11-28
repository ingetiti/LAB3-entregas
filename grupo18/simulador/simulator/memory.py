"""
memory.py - Memoria principal del simulador (ISA Lab 3c).

Características (según la especificación):
  - 65.536 bytes (0x0000 a 0xFFFF), inicializados en cero.
  - Direccionamiento por byte (byte-addressable).
  - Palabras de 16 bits almacenadas en Little Endian.
  - Las palabras pueden empezar en direcciones pares o impares.
  - Se registra qué direcciones fueron escritas (para medir uso de memoria).

Este módulo NO controla la alineación de instrucciones: eso es
responsabilidad de la CPU (Fetch y saltos), no de la memoria.
"""

MEMORY_SIZE = 0x10000   # 65.536 bytes
BYTE_MASK = 0xFF        # para limitar valores a 8 bits
WORD_MASK = 0xFFFF      # para limitar valores a 16 bits


class MemoryAccessError(Exception):
    """Acceso inválido a memoria (dirección fuera de rango o tipo incorrecto)."""


class Memory:
    """Memoria de 64 KiB, byte-addressable, Little Endian."""

    SIZE = MEMORY_SIZE

    def __init__(self):
        # bytearray: 64 KiB mutables, todos en cero, cada celda limitada a 0..255.
        self._data = bytearray(self.SIZE)
        # Conjunto de direcciones que recibieron al menos una escritura.
        self._written = set()

    # ------------------------------------------------------------------
    # Propiedades
    # ------------------------------------------------------------------
    @property
    def size(self):
        """Cantidad total de bytes de la memoria."""
        return len(self._data)

    @property
    def used_bytes(self):
        """Cantidad de direcciones DISTINTAS que recibieron una escritura."""
        return len(self._written)

    @property
    def written_addresses(self):
        """Copia inmutable del conjunto de direcciones escritas."""
        return frozenset(self._written)

    # ------------------------------------------------------------------
    # Validaciones internas
    # ------------------------------------------------------------------
    @staticmethod
    def _check_int(name, value):
        # bool es subclase de int en Python; lo rechazamos para evitar
        # errores sutiles como read_byte(True).
        if isinstance(value, bool) or not isinstance(value, int):
            raise MemoryAccessError(
                f"{name} debe ser un entero, se recibió {type(value).__name__}"
            )

    def _check_range(self, address, length):
        """Verifica que address .. address+length-1 estén dentro de memoria."""
        self._check_int("La dirección", address)
        last = address + length - 1
        if address < 0 or last >= self.SIZE:
            if length == 1:
                raise MemoryAccessError(
                    f"Dirección 0x{address & 0xFFFFFFFF:04X} fuera de rango "
                    f"(válido: 0x0000-0x{self.SIZE - 1:04X})"
                )
            raise MemoryAccessError(
                f"Acceso de {length} bytes desde 0x{address & 0xFFFFFFFF:04X} "
                f"excede los límites de memoria "
                f"(última dirección válida: 0x{self.SIZE - 1:04X})"
            )

    # ------------------------------------------------------------------
    # Acceso a bytes
    # ------------------------------------------------------------------
    def read_byte(self, address):
        """Devuelve el byte (0..255) almacenado en `address`."""
        self._check_range(address, 1)
        return self._data[address]

    def write_byte(self, address, value):
        """Escribe `value` (limitado a 8 bits) en `address`."""
        self._check_range(address, 1)
        self._check_int("El valor", value)
        self._data[address] = value & BYTE_MASK
        self._written.add(address)

    # ------------------------------------------------------------------
    # Acceso a palabras (Little Endian)
    # ------------------------------------------------------------------
    def read_word(self, address):
        """Lee una palabra de 16 bits desde `address` y `address+1`."""
        self._check_range(address, 2)
        low = self._data[address]        # byte menos significativo
        high = self._data[address + 1]   # byte más significativo
        return low | (high << 8)

    def write_word(self, address, value):
        """Escribe `value` (limitado a 16 bits) en Little Endian.

        Se valida el rango de AMBOS bytes antes de escribir, de modo que
        un fallo nunca deja la memoria escrita a medias.
        """
        self._check_range(address, 2)
        self._check_int("El valor", value)
        value &= WORD_MASK
        self._data[address] = value & BYTE_MASK           # byte bajo
        self._data[address + 1] = (value >> 8) & BYTE_MASK  # byte alto
        self._written.add(address)
        self._written.add(address + 1)
