"""
symbols.py - Primera pasada del ensamblador (ISA Lab 3c). Etapa 5.3.

Recibe el Program que produce assembler.parser y calcula el MAPA DE MEMORIA:
  - la dirección de cada sentencia que ocupa memoria,
  - la tabla de símbolos locales y los símbolos externos,
  - los bytes de relleno que alinean las instrucciones,
  - el origen, la primera dirección libre y el tamaño total.

NO codifica instrucciones, NO calcula desplazamientos PC-relative, NO genera
reubicaciones y NO modifica el Program recibido (es inmutable).

REGLAS DE TAMAÑO (el contador de direcciones trabaja en BYTES)
--------------------------------------------------------------
  instrucción   2 bytes (PC_INCREMENT)
  .FILL         2 bytes (una palabra)
  .BLKW n       2 * n bytes
  .STRINGZ "s"  len(s) + 1 bytes (un byte por carácter y el terminador 0)
  .ORIG .END .EXTERNAL   0 bytes (no ocupan memoria)

ORIGEN
------
.ORIG debe recibir una dirección PAR (x0000, x0002, ... xFFFE). Un programa
ejecutable no puede empezar en una dirección impar (la CPU exige un PC alineado
para hacer fetch) y NO se inserta relleno silencioso para compensar un origen
incorrecto: un .ORIG impar es un error. La regla es solo sobre el origen; los
datos siguen pudiendo empezar en direcciones impares. El parser acepta cualquier
dirección de 16 bits: esta regla se aplica acá, en la etapa de direcciones.

ALINEACIÓN
----------
Las instrucciones deben comenzar en dirección par. Como el origen es par, el
contador solo puede quedar impar DESPUÉS de datos de longitud impar (p. ej. una
cadena). Si entonces sigue una instrucción, se inserta un byte de relleno 0x00 y
la instrucción queda en la dirección siguiente. Los datos NO se alinean: pueden
comenzar en cualquier dirección. El relleno se registra en SymbolTable.padding.

ETIQUETAS
---------
Una etiqueta apunta a la dirección de la sentencia de su línea. Una etiqueta
SOLA en su línea queda pendiente y se asocia a la próxima sentencia que ocupe
memoria (si es una instrucción: a su dirección YA ALINEADA, nunca al byte de
relleno), o al contador actual si antes aparece .END o termina el programa.
.ORIG y .EXTERNAL no ocupan memoria, así que no resuelven etiquetas pendientes.

SÍMBOLOS EXTERNOS
-----------------
.EXTERNAL nombre declara que el símbolo se define fuera del programa; NO le
asigna dirección. `externals` guarda solo los NOMBRES declarados: el símbolo no
aparece en `symbols` ni en `line_addresses`, y su dirección queda SIN RESOLVER en
esta etapa (no se inventan direcciones ficticias). Una referencia a un símbolo
declarado así es válida. Las direcciones las proporcionará el codificador (etapa
siguiente) mediante un mapping nombre -> dirección. Repetir un .EXTERNAL con el
mismo nombre es inofensivo; declararlo y además definirlo como etiqueta local es
un error.

CONTENIDO DE SymbolTable.line_addresses
---------------------------------------
Una entrada por cada línea cuya sentencia OCUPA MEMORIA (instrucción, .FILL,
.BLKW, .STRINGZ): número de línea -> dirección de su primer byte (ya
alineada). No aparecen las líneas de etiqueta pendiente, ni .ORIG, .END o
.EXTERNAL: la dirección de una etiqueta se consulta en `symbols`.

ERRORES
-------
Se acumulan y se lanzan juntos como SymbolErrors; si hay alguno NO se devuelve
ninguna tabla. Aunque el parser ya valida varias cosas, acá se vuelven a
comprobar las que protegen el cálculo de direcciones (duplicados, .ORIG, tamaños,
rangos), para no depender de que el Program venga de parse_program.

Un símbolo puede valer x10000 (etiqueta al final de una memoria completamente
ocupada): es una dirección exclusiva, no direccionable. Quien la use (el
codificador) debe validar su rango.
"""

import dataclasses
from dataclasses import dataclass
from types import MappingProxyType
from typing import FrozenSet, Mapping, Tuple

from assembler.parser import (
    BlkwDirective,
    EndDirective,
    ExternalDirective,
    FillDirective,
    Instruction,
    LabelRef,
    OrigDirective,
    Program,
    StringzDirective,
)
from simulator.isa import BYTE_BITS, MEMORY_SIZE, PC_INCREMENT, WORD_BITS

__all__ = ["Padding", "SymbolError", "SymbolErrors", "SymbolTable", "build_symbol_table"]

WORD_BYTES = WORD_BITS // BYTE_BITS         # 2
INSTRUCTION_BYTES = PC_INCREMENT            # 2


# ======================================================================
# Errores (misma forma que ParseError / ParseErrors)
# ======================================================================
class SymbolError(Exception):
    """Un problema de la primera pasada, con su línea (o None si es global)."""

    def __init__(self, message, line_number=None, source=None):
        self.message = message
        self.line_number = line_number
        self.source = source
        prefix = f"línea {line_number}: " if line_number is not None else ""
        super().__init__(prefix + message)


class SymbolErrors(Exception):
    """Todos los problemas de la primera pasada, juntos."""

    def __init__(self, errors):
        self.errors = tuple(errors)
        detail = "\n".join(f"  {error}" for error in self.errors)
        super().__init__(f"{len(self.errors)} error(es) en la primera pasada:\n{detail}")


# ======================================================================
# Resultado (inmutable, también en sus colecciones internas)
# ======================================================================
@dataclass(frozen=True)
class Padding:
    """Un relleno de alineación."""
    address: int        # dirección del byte de relleno (valor 0x00)
    size: int           # cantidad de bytes de relleno
    line_number: int    # línea de la instrucción que lo exigió


@dataclass(frozen=True)
class SymbolTable:
    """Mapa de memoria del programa. Todas las colecciones son de solo lectura.

    symbols         nombre de etiqueta -> dirección (Mapping de solo lectura)
    externals       nombres declarados con .EXTERNAL (frozenset); SIN dirección:
                    se resuelven después, no están en `symbols`
    line_addresses  línea -> dirección, solo líneas que ocupan memoria
    padding         rellenos insertados, en orden de dirección (tuple)
    origin          dirección del .ORIG (siempre PAR)
    end_address     primera dirección libre tras el programa (puede ser x10000)
    """
    symbols: Mapping[str, int]
    externals: FrozenSet[str]
    line_addresses: Mapping[int, int]
    padding: Tuple[Padding, ...]
    origin: int
    end_address: int

    def __post_init__(self):
        # Se copian y congelan las colecciones aunque quien construya la
        # tabla pase diccionarios o listas modificables.
        object.__setattr__(self, "symbols", MappingProxyType(dict(self.symbols)))
        object.__setattr__(self, "externals", frozenset(self.externals))
        object.__setattr__(self, "line_addresses",
                           MappingProxyType(dict(self.line_addresses)))
        object.__setattr__(self, "padding", tuple(self.padding))

    def __hash__(self):
        # El hash automático de una dataclass congelada falla con los
        # MappingProxyType; se calcula a partir de sus contenidos.
        return hash((frozenset(self.symbols.items()), self.externals,
                     frozenset(self.line_addresses.items()), self.padding,
                     self.origin, self.end_address))

    @property
    def size(self):
        """Bytes ocupados desde el origen, INCLUYENDO el relleno."""
        return self.end_address - self.origin


# ======================================================================
# Utilidades
# ======================================================================
def _error(errors, line, message):
    errors.append(SymbolError(message, line.line_number, line.source))


def _hex(address):
    return f"x{address:04X}"


def _size_of(statement):
    """Bytes que ocupa una sentencia; None si no ocupa memoria o es desconocida.

    Lanza ValueError si el tamaño no se puede calcular (.BLKW inválido).
    """
    if isinstance(statement, Instruction):
        return INSTRUCTION_BYTES
    if isinstance(statement, FillDirective):
        return WORD_BYTES
    if isinstance(statement, StringzDirective):
        return len(statement.text) + 1
    if isinstance(statement, BlkwDirective):
        count = statement.count
        if isinstance(count, bool) or not isinstance(count, int) or count < 1:
            raise ValueError(f".BLKW requiere una cantidad entera >= 1, se recibió {count!r}")
        return count * WORD_BYTES
    return None


def _occupies_memory(statement):
    return isinstance(statement, (Instruction, FillDirective, StringzDirective, BlkwDirective))


def _label_refs(statement):
    """Todas las referencias a etiquetas dentro de una sentencia.

    Recorre los campos de forma genérica (también dentro de tuplas), así que
    sigue funcionando si una directiva futura admite referencias.
    """
    if not dataclasses.is_dataclass(statement):
        return
    for field in dataclasses.fields(statement):
        yield from _refs_in(getattr(statement, field.name))


def _refs_in(value):
    if isinstance(value, LabelRef):
        yield value
    elif isinstance(value, tuple):
        for item in value:
            yield from _refs_in(item)


# ======================================================================
# Pasadas internas
# ======================================================================
def _check_names(lines, errors):
    """Duplicados y conflictos local/externo. No necesita direcciones.

    Devuelve (nombres locales, nombres externos).
    """
    labels = {}                 # etiqueta -> línea de su primera definición
    externals = {}              # símbolo externo -> línea de su primera declaración
    for line in lines:
        if line.label is not None:
            if line.label in labels:
                _error(errors, line, f"etiqueta '{line.label}' duplicada: ya está "
                                     f"definida en la línea {labels[line.label]}")
            else:
                labels[line.label] = line.line_number
                if line.label in externals:
                    _error(errors, line, f"la etiqueta '{line.label}' entra en conflicto "
                                         f"con el símbolo externo declarado en la línea "
                                         f"{externals[line.label]}")
        if isinstance(line.statement, ExternalDirective):
            name = line.statement.name
            externals.setdefault(name, line.line_number)    # repetir .EXTERNAL es inofensivo
            if name in labels:
                _error(errors, line, f"el símbolo externo '{name}' entra en conflicto "
                                     f"con la etiqueta definida en la línea {labels[name]}")
    return set(labels), set(externals)


def _layout(lines, errors):
    """Asigna direcciones. Devuelve (origin, end_address, symbols, line_addresses, padding)."""
    origin = None               # None hasta que haya un .ORIG válido y bien ubicado
    counter = None              # dirección de la próxima sentencia (bytes)
    orig_line = None            # línea del primer .ORIG (válido o no)
    first_memory_line = None    # primera sentencia que ocupa memoria ANTES de un .ORIG
    end_line = None
    overflowed = False
    pending = []                # etiquetas esperando una dirección
    symbols = {}
    line_addresses = {}
    padding = []

    def bind(address):
        for name in pending:
            symbols.setdefault(name, address)       # ante duplicados gana la primera
        pending.clear()

    for line in lines:
        statement = line.statement
        if end_line is not None:
            _error(errors, line, f"no puede haber sentencias ni etiquetas después de "
                                 f".END (declarado en la línea {end_line})")
            continue

        if isinstance(statement, OrigDirective):
            if line.label is not None:
                _error(errors, line, f".ORIG no admite etiqueta (se encontró '{line.label}')")
            if orig_line is not None:
                _error(errors, line, f"solo se admite un .ORIG (el primero está en la "
                                     f"línea {orig_line})")
                continue
            orig_line = line.line_number
            if first_memory_line is not None:
                _error(errors, line, f".ORIG debe aparecer antes de cualquier sentencia que "
                                     f"ocupe memoria (la línea {first_memory_line} ya ocupa memoria)")
                continue
            address = statement.address
            if (isinstance(address, bool) or not isinstance(address, int)
                    or not 0 <= address < MEMORY_SIZE):
                _error(errors, line, f".ORIG fuera de rango: {address!r} "
                                     f"(se admiten direcciones de x0000 a xFFFF)")
                continue
            if address % PC_INCREMENT != 0:
                _error(errors, line, f".ORIG debe recibir una dirección par: {_hex(address)} "
                                     f"es impar (las instrucciones ocupan {INSTRUCTION_BYTES} "
                                     f"bytes y el PC debe estar alineado; por ejemplo, use "
                                     f"{_hex(address - 1)})")
                continue
            origin = counter = address
            continue

        if line.label is not None:
            if isinstance(statement, ExternalDirective):
                _error(errors, line, f".EXTERNAL no admite etiqueta (se encontró '{line.label}')")
            else:
                pending.append(line.label)
        if statement is None or isinstance(statement, ExternalDirective):
            continue

        if isinstance(statement, EndDirective):
            end_line = line.line_number
            if counter is not None:
                bind(counter)
            continue

        try:
            size = _size_of(statement)
        except ValueError as problem:
            _error(errors, line, str(problem))
            continue
        if size is None:
            _error(errors, line, f"sentencia no reconocida: {type(statement).__name__}")
            continue

        if counter is None:                         # todavía no hay .ORIG utilizable
            if first_memory_line is None:
                first_memory_line = line.line_number
            pending.clear()
            continue

        pad = (-counter) % PC_INCREMENT if isinstance(statement, Instruction) else 0
        needed = pad + size
        if counter + needed > MEMORY_SIZE:
            note = f" (incluye {pad} byte de relleno de alineación)" if pad else ""
            _error(errors, line, f"desbordamiento de memoria: la sentencia necesita "
                                 f"{needed} byte(s){note} desde {_hex(counter)} y la memoria "
                                 f"termina en xFFFF")
            overflowed = True
            break                                   # no se avanza el contador
        if pad:
            padding.append(Padding(counter, pad, line.line_number))
            counter += pad
        bind(counter)                               # etiquetas pendientes + la de esta línea
        line_addresses[line.line_number] = counter
        counter += size

    if orig_line is None:
        errors.append(SymbolError(
            "falta la directiva .ORIG: es obligatoria y debe aparecer antes de "
            "cualquier sentencia que ocupe memoria"))
    elif counter is not None and end_line is None and not overflowed:
        bind(counter)                               # etiquetas pendientes al final
    return origin, counter, symbols, line_addresses, padding


def _check_references(lines, defined, errors):
    for line in lines:
        if line.statement is None:
            continue
        for reference in _label_refs(line.statement):
            if reference.name not in defined:
                _error(errors, line, f"referencia a un símbolo no definido: "
                                     f"'{reference.name}' (defínalo con una etiqueta o "
                                     f"decláralo con .EXTERNAL)")


# ======================================================================
# API pública
# ======================================================================
def build_symbol_table(program):
    """Primera pasada: devuelve la SymbolTable de `program`.

    Lanza SymbolErrors, con TODOS los problemas encontrados, si el programa
    no permite construir un mapa de memoria correcto.
    """
    if not isinstance(program, Program):
        raise TypeError(f"se esperaba un Program, se recibió {type(program).__name__}")
    errors = []
    lines = program.lines
    labels, externals = _check_names(lines, errors)
    origin, end_address, symbols, line_addresses, padding = _layout(lines, errors)
    _check_references(lines, labels | externals, errors)
    if errors:
        # Los errores globales (sin línea) primero; después, por línea.
        errors.sort(key=lambda e: (e.line_number is not None, e.line_number or 0))
        raise SymbolErrors(errors)
    return SymbolTable(symbols, frozenset(externals), line_addresses,
                       tuple(padding), origin, end_address)