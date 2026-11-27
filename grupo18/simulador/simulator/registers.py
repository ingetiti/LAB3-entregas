"""
registers.py - Registros del procesador (ISA Lab 3c).

Contiene:
  - R0..R7: ocho registros generales de 16 bits.
      * R6 se usa por convención como SP y R7 como LR (link register),
        pero aquí NO tienen ningún comportamiento especial.
  - PC e IR: registros internos de 16 bits.
  - Banderas de condición N, Z, P (booleanos; siempre exactamente una activa).

Este módulo solo almacena estado. No incrementa el PC, no maneja la pila
ni decodifica instrucciones: eso es responsabilidad de la CPU.
"""

NUM_REGISTERS = 8
WORD_MASK = 0xFFFF      # limita valores a 16 bits
SIGN_BIT = 0x8000       # bit 15: bit de signo en complemento a dos


class RegisterAccessError(Exception):
    """Acceso inválido a registros (índice o valor incorrecto)."""


def to_signed16(value):
    """Interpreta los 16 bits inferiores de `value` como entero con signo.

    Ejemplos: 0x7FFF -> 32767, 0x8000 -> -32768, 0xFFFF -> -1.
    """
    value &= WORD_MASK
    return value - 0x10000 if value & SIGN_BIT else value


class Registers:
    """Banco de registros: R0-R7, PC, IR y banderas N/Z/P."""

    COUNT = NUM_REGISTERS

    def __init__(self):
        self._r = [0] * NUM_REGISTERS   # R0..R7, todos en cero
        self._pc = 0
        self._ir = 0
        # Estado inicial coherente con registros en cero: Z activa.
        self._n = False
        self._z = True
        self._p = False

    # ------------------------------------------------------------------
    # Validaciones internas
    # ------------------------------------------------------------------
    @staticmethod
    def _check_int(name, value):
        # bool es subclase de int en Python; se rechaza explícitamente.
        if isinstance(value, bool) or not isinstance(value, int):
            raise RegisterAccessError(
                f"{name} debe ser un entero, se recibió "
                f"{type(value).__name__} ({value!r})"
            )

    def _check_index(self, index):
        self._check_int("El índice de registro", index)
        if not 0 <= index < NUM_REGISTERS:
            raise RegisterAccessError(
                f"Índice de registro inválido: {index} "
                f"(válido: 0-{NUM_REGISTERS - 1})"
            )

    # ------------------------------------------------------------------
    # Registros generales R0..R7
    # ------------------------------------------------------------------
    def read(self, index):
        """Devuelve el contenido (0..65535) del registro `index`."""
        self._check_index(index)
        return self._r[index]

    def write(self, index, value):
        """Escribe `value` (limitado a 16 bits) en el registro `index`.

        No modifica las banderas: la CPU decide cuándo actualizarlas.
        """
        self._check_index(index)
        self._check_int("El valor", value)
        self._r[index] = value & WORD_MASK

    def values(self):
        """Copia de R0..R7 como tupla (útil para mostrar el estado final)."""
        return tuple(self._r)

    # ------------------------------------------------------------------
    # PC e IR
    # ------------------------------------------------------------------
    @property
    def pc(self):
        """Program Counter (16 bits)."""
        return self._pc

    @pc.setter
    def pc(self, value):
        self._check_int("El valor de PC", value)
        self._pc = value & WORD_MASK

    @property
    def ir(self):
        """Instruction Register (16 bits)."""
        return self._ir

    @ir.setter
    def ir(self, value):
        self._check_int("El valor de IR", value)
        self._ir = value & WORD_MASK

    # ------------------------------------------------------------------
    # Banderas N, Z, P (solo lectura desde fuera)
    # ------------------------------------------------------------------
    @property
    def n(self):
        """True si el último resultado fue negativo."""
        return self._n

    @property
    def z(self):
        """True si el último resultado fue cero."""
        return self._z

    @property
    def p(self):
        """True si el último resultado fue positivo."""
        return self._p

    @property
    def condition_codes(self):
        """Tupla (N, Z, P) con el estado de las tres banderas."""
        return (self._n, self._z, self._p)

    def _set_flags(self, n, z, p):
        # Único punto donde se escriben las banderas: garantiza que
        # siempre se asignen las tres a la vez.
        self._n, self._z, self._p = n, z, p

    def update_nzp(self, value):
        """Actualiza N/Z/P según un resultado de 16 bits (complemento a dos).

        El valor se enmascara a 16 bits (no se rechaza por estar fuera de rango).
        """
        self._check_int("El valor", value)
        value &= WORD_MASK
        if value == 0:
            self._set_flags(False, True, False)
        elif value & SIGN_BIT:
            self._set_flags(True, False, False)
        else:
            self._set_flags(False, False, True)

    def update_compare(self, a, b):
        """Actualiza N/Z/P comparando `a` y `b` como enteros CON SIGNO.

        N si a < b, Z si a == b, P si a > b. No usa una resta de 16 bits,
        así que no hay problemas de desbordamiento (la ISA no tiene V).
        No modifica ningún registro.
        """
        self._check_int("El operando a", a)
        self._check_int("El operando b", b)
        sa, sb = to_signed16(a), to_signed16(b)
        self._set_flags(sa < sb, sa == sb, sa > sb)

    def __repr__(self):
        regs = " ".join(f"R{i}=0x{v:04X}" for i, v in enumerate(self._r))
        n, z, p = self.condition_codes
        return (f"Registers({regs} PC=0x{self._pc:04X} IR=0x{self._ir:04X} "
                f"N={int(n)} Z={int(z)} P={int(p)})")
