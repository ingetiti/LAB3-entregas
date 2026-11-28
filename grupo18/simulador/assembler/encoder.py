"""
encoder.py - Segunda pasada del ensamblador (ISA Lab 3c). Etapa 5.4.

Recibe el Program (parser) y la SymbolTable (symbols) y produce los BYTES de
código máquina: el contenido exacto que irá a memoria desde el origen.

NO analiza texto, NO asigna direcciones y NO recalcula el mapa de memoria: las
direcciones de cada sentencia y el relleno de alineación vienen de la
SymbolTable. El codificador solo las RESPETA y comprueba que lo que él emite
coincida con ese mapa (si no coincide, es un error, no un ajuste silencioso).

FUENTE ÚNICA DE VERDAD
----------------------
Opcodes, formatos y operandos salen de simulator.isa (INSTRUCTIONS_BY_MNEMONIC);
la POSICIÓN de cada campo sale de FORMAT_FIELDS/get_field. Acá no hay ninguna
constante de bit: el ancho de cada campo se consulta, así que decoder y
encoder no pueden desincronizarse. Es la operación inversa de
decoder.extract_field: en vez de extraer un valor de un campo, lo inserta.

SEMÁNTICA DE LOS SALTOS (idéntica a la de la CPU)
-------------------------------------------------
  BR, JSR : destino = (PC_siguiente + 2 * offset) mod 65536   (offset en PALABRAS)
  LEA     : dirección = (PC_siguiente + offset) mod 65536     (offset en BYTES)
donde PC_siguiente = dirección de la instrucción + 2 (también módulo 65536).
Para codificar una etiqueta se invierte esa fórmula: la diferencia se calcula
módulo 65536 e interpretada con signo, que es el único representante que puede
caber en el campo. Por eso, desde xFFFE se llega a x0000 con offset 0.

  - BR y JSR exigen un destino PAR (la CPU rechaza saltar a una dirección impar).
  - LEA admite destinos impares: apunta a datos (por ejemplo, una cadena).
  - x10000 (etiqueta tras una memoria llena) no es direccionable: error.
  - Un offset escrito como número (BR #3, LEA R0, #-2) se usa tal cual, con
    la misma validación de rango.

SÍMBOLOS EXTERNOS
-----------------
`external_symbols` es un mapping nombre -> dirección (0..65535). Se rechazan
claves no declaradas con .EXTERNAL y claves que pisen un símbolo local. Un
externo declarado pero no usado no necesita dirección. Un externo usado sin
dirección es un error. En .FILL se codifica la dirección absoluta; en BR, JSR
y LEA se calcula el desplazamiento y, si no cabe, se informa el error de rango.

DIRECTIVAS
----------
  .FILL v      2 bytes Little Endian (número -32768..65535, o dirección)
  .BLKW n      2*n bytes en cero
  .STRINGZ s   un byte por carácter (códigos 1..255) y un 0 final
  .ORIG .END .EXTERNAL   no generan bytes

ERRORES
-------
Se acumulan (uno por línea como máximo, más los errores globales) y se lanzan
juntos como EncodeErrors. Si hay alguno NO se devuelve ningún EncodedProgram.
"""

from dataclasses import dataclass
from typing import Mapping, Optional

from assembler.parser import (
    BlkwDirective,
    EndDirective,
    ExternalDirective,
    FillDirective,
    Immediate,
    Instruction,
    LabelRef,
    OrigDirective,
    Program,
    Register,
    StringzDirective,
)
from assembler.symbols import SymbolTable
from simulator.isa import (
    BYTE_BITS,
    BYTE_MASK,
    FORMAT_FIELDS,
    INSTRUCTIONS_BY_MNEMONIC,
    MEMORY_SIZE,
    MODE_IMMEDIATE,
    MODE_REGISTER,
    PC_INCREMENT,
    REGISTER_COUNT,
    WORD_BITS,
    WORD_MASK,
    InstructionFormat,
    OperandKind,
    get_field,
)

__all__ = ["EncodeError", "EncodeErrors", "EncodedProgram", "encode_program"]

WORD_BYTES = WORD_BITS // BYTE_BITS         # 2
_FILL_RANGE = (-(1 << (WORD_BITS - 1)), WORD_MASK)      # -32768..65535
_STRING_CODE_RANGE = (1, BYTE_MASK)                     # 1..255 (el 0 es el terminador)

_REG = OperandKind.REGISTER
_REG_OR_IMM4 = OperandKind.REG_OR_IMM4
_SHIFT = OperandKind.SHIFT_AMOUNT


# ======================================================================
# Errores (misma forma que ParseError/ParseErrors y SymbolError/SymbolErrors)
# ======================================================================
class EncodeError(Exception):
    """Un problema de la segunda pasada, con su línea (o None si es global)."""

    def __init__(self, message, line_number=None, source=None):
        self.message = message
        self.line_number = line_number
        self.source = source
        prefix = f"línea {line_number}: " if line_number is not None else ""
        super().__init__(prefix + message)


class EncodeErrors(Exception):
    """Todos los problemas de la segunda pasada, juntos."""

    def __init__(self, errors):
        self.errors = tuple(errors)
        detail = "\n".join(f"  {error}" for error in self.errors)
        super().__init__(f"{len(self.errors)} error(es) de codificación:\n{detail}")


class _OperandError(Exception):
    """Problema dentro de una sentencia. encode_program lo convierte en EncodeError."""


# ======================================================================
# Resultado (inmutable)
# ======================================================================
@dataclass(frozen=True)
class EncodedProgram:
    """Código máquina listo para cargar en memoria.

    origin  dirección del primer byte (PAR)
    data    bytes del programa, INCLUYENDO relleno y datos (de solo lectura)

    Encaja con CPU.load_program(data, address): `cpu.load_program(p.data, p.origin)`.
    `end_address` y `size` se derivan de los otros dos campos, así que nunca
    pueden contradecirse.
    """
    origin: int
    data: bytes

    def __post_init__(self):
        if isinstance(self.origin, bool) or not isinstance(self.origin, int):
            raise TypeError(f"origin debe ser un entero, se recibió {self.origin!r}")
        if not isinstance(self.data, (bytes, bytearray)):
            raise TypeError(f"data debe ser bytes, se recibió {type(self.data).__name__}")
        object.__setattr__(self, "data", bytes(self.data))      # copia inmutable
        if not 0 <= self.origin < MEMORY_SIZE or self.origin % PC_INCREMENT:
            raise ValueError(f"origin debe ser una dirección par de x0000 a xFFFE, "
                             f"se recibió {self.origin}")
        if self.origin + len(self.data) > MEMORY_SIZE:
            raise ValueError(f"el programa ({len(self.data)} bytes) no cabe en memoria "
                             f"desde {_hex(self.origin)}")

    @property
    def size(self):
        """Cantidad de bytes del programa."""
        return len(self.data)

    @property
    def end_address(self):
        """Primera dirección libre tras el programa (puede ser x10000)."""
        return self.origin + len(self.data)


# ======================================================================
# Utilidades
# ======================================================================
def _hex(address):
    return f"x{address:04X}"


def _is_int(value):
    # bool es subclase de int en Python; se rechaza explícitamente.
    return isinstance(value, int) and not isinstance(value, bool)


def _signed_range(width):
    return -(1 << (width - 1)), (1 << (width - 1)) - 1


def _pack(fmt, **values):
    """Arma una palabra de 16 bits: inserta cada valor en su campo de `fmt`.

    Los campos no mencionados (los reservados, o DR en CMP) quedan en 0, que es
    lo que exige el decoder. Los valores ya vienen con la forma en que se
    guardan (sin signo, dentro del ancho del campo): cualquier otra cosa es un
    error del codificador, no del programa de usuario, y se informa como tal.
    """
    fields = {field.name: field for field in FORMAT_FIELDS[fmt]}
    word = 0
    for name, value in values.items():
        if name not in fields:
            raise ValueError(f"el formato {fmt.name} no tiene un campo '{name}'")
        field = fields[name]
        if not _is_int(value) or not 0 <= value < (1 << field.width):
            raise ValueError(f"valor {value!r} no cabe en el campo '{name}' de "
                             f"{fmt.name} ({field.width} bits)")
        word |= value << field.low
    return word


def _unsigned_field(fmt, name, value, what):
    """Valida `value` contra el campo SIN signo (fmt, name) y lo devuelve."""
    width = get_field(fmt, name).width
    high = (1 << width) - 1
    if not _is_int(value) or not 0 <= value <= high:
        raise _OperandError(f"{what} {value!r} fuera de rango (0 a {high})")
    return value


def _signed_field(fmt, name, value, what):
    """Valida `value` contra el campo CON signo (fmt, name); devuelve su complemento a dos."""
    width = get_field(fmt, name).width
    low, high = _signed_range(width)
    if not _is_int(value) or not low <= value <= high:
        raise _OperandError(f"{what} {value!r} fuera de rango ({low} a {high})")
    return value & ((1 << width) - 1)


# ======================================================================
# Resolución de símbolos
# ======================================================================
class _Resolver:
    """Traduce un nombre a una dirección usando la SymbolTable y los externos."""

    def __init__(self, table, externals):
        self._table = table
        self._externals = externals             # solo entradas VÁLIDAS

    def address_of(self, name):
        if name in self._table.symbols:
            return self._table.symbols[name]
        if name in self._table.externals:
            if name not in self._externals:
                raise _OperandError(
                    f"el símbolo externo '{name}' no tiene una dirección válida: "
                    f"indíquela en external_symbols")
            return self._externals[name]
        raise _OperandError(f"referencia a un símbolo no definido: '{name}'")

    def addressable(self, name):
        """Dirección de `name`, exigiendo que exista en memoria (0..xFFFF)."""
        address = self.address_of(name)
        if not 0 <= address <= WORD_MASK:
            raise _OperandError(
                f"la etiqueta '{name}' vale {_hex(address)}, que no es una dirección "
                f"válida (la memoria llega hasta xFFFF)")
        return address


def _check_external_symbols(external_symbols, table, errors):
    """Valida el mapping de externos. Devuelve {nombre: dirección} solo con las entradas válidas."""
    if external_symbols is None:
        return {}
    if not isinstance(external_symbols, Mapping):
        raise TypeError(f"external_symbols debe ser un mapping nombre -> dirección, "
                        f"se recibió {type(external_symbols).__name__}")
    valid = {}
    for name, address in external_symbols.items():
        if not isinstance(name, str):
            errors.append(EncodeError(f"external_symbols: la clave {name!r} no es un nombre (texto)"))
            continue
        if name in table.symbols:
            errors.append(EncodeError(
                f"external_symbols: '{name}' pisaría a la etiqueta local del mismo "
                f"nombre (definida en {_hex(table.symbols[name])})"))
            continue
        if name not in table.externals:
            errors.append(EncodeError(
                f"external_symbols: '{name}' no fue declarado con .EXTERNAL"))
            continue
        if not _is_int(address) or not 0 <= address <= WORD_MASK:
            errors.append(EncodeError(
                f"external_symbols: la dirección de '{name}' debe ser un entero de "
                f"x0000 a xFFFF, se recibió {address!r}"))
            continue
        valid[name] = address
    return valid


# ======================================================================
# Operandos
# ======================================================================
def _register(operand, position):
    if (not isinstance(operand, Register) or not _is_int(operand.number)
            or not 0 <= operand.number < REGISTER_COUNT):
        raise _OperandError(f"el operando {position} debe ser un registro (R0-R7, SP o LR)")
    return operand.number


def _pc_relative(operand, instruction, address, spec, resolver, unit_bytes, unit_name):
    """Offset (con signo, en `unit_name`) de un operando LABEL_WORDS / LABEL_BYTES.

    Invierte la fórmula de la CPU: destino = (PC_siguiente + unit_bytes*offset) mod 2^16.
    """
    field_name = "offset"
    if isinstance(operand, Immediate):
        return _signed_field(spec.fmt, field_name, operand.value, "el desplazamiento")
    if not isinstance(operand, LabelRef):
        raise _OperandError("el operando debe ser una etiqueta o un desplazamiento numérico")

    target = resolver.addressable(operand.name)
    if unit_bytes == PC_INCREMENT and target % PC_INCREMENT:
        raise _OperandError(
            f"el destino '{operand.name}' ({_hex(target)}) es una dirección impar: "
            f"{instruction.mnemonic} solo puede saltar a direcciones pares")

    next_pc = (address + PC_INCREMENT) & WORD_MASK
    delta = (target - next_pc) & WORD_MASK              # diferencia mod 2^16...
    if delta >= 1 << (WORD_BITS - 1):                   # ...leída con signo
        delta -= 1 << WORD_BITS
    offset = delta // unit_bytes                        # exacto: ambas direcciones son pares

    low, high = _signed_range(get_field(spec.fmt, field_name).width)
    if not low <= offset <= high:
        raise _OperandError(
            f"el destino '{operand.name}' ({_hex(target)}) está fuera de alcance desde "
            f"{_hex(address)}: requiere un desplazamiento de {offset} {unit_name} y "
            f"{instruction.mnemonic} admite de {low} a {high}")
    return offset & ((1 << get_field(spec.fmt, field_name).width) - 1)


# ======================================================================
# Codificadores por formato (cada uno devuelve la palabra de 16 bits)
# ======================================================================
def _second_operand(operand, kind):
    """(mode, operand2) del formato A para un operando REG_OR_IMM4 o SHIFT_AMOUNT."""
    fmt = InstructionFormat.A
    if kind is _SHIFT:
        if not isinstance(operand, Immediate):
            raise _OperandError("la cantidad de desplazamiento debe ser un número")
        return MODE_IMMEDIATE, _unsigned_field(fmt, "operand2", operand.value,
                                               "la cantidad de desplazamiento")
    if isinstance(operand, Register):
        return MODE_REGISTER, _register(operand, 3)         # SR2 ocupa los 3 bits bajos
    if isinstance(operand, Immediate):
        return MODE_IMMEDIATE, _signed_field(fmt, "operand2", operand.value, "el inmediato")
    raise _OperandError("el último operando debe ser un registro o un número")


def _encode_format_a(spec, instruction, address, resolver):
    fmt = InstructionFormat.A
    ops, kinds = instruction.operands, spec.operands
    if kinds == (_REG, _REG):                               # NOT dr, sr1
        return _pack(fmt, opcode=spec.opcode, dr=_register(ops[0], 1),
                     sr1=_register(ops[1], 2))
    if kinds in ((_REG, _REG, _REG_OR_IMM4), (_REG, _REG, _SHIFT)):
        mode, operand2 = _second_operand(ops[2], kinds[2])  # ADD..XOR y shifts
        return _pack(fmt, opcode=spec.opcode, dr=_register(ops[0], 1),
                     sr1=_register(ops[1], 2), mode=mode, operand2=operand2)
    if kinds == (_REG, _REG_OR_IMM4):                       # CMP sr1, sr2|imm (sin DR)
        mode, operand2 = _second_operand(ops[1], kinds[1])
        return _pack(fmt, opcode=spec.opcode, sr1=_register(ops[0], 1),
                     mode=mode, operand2=operand2)
    raise ValueError(f"{spec.mnemonic}: operandos de formato A sin codificación definida")


def _encode_format_b(spec, instruction, address, resolver):
    ops = instruction.operands                              # (reg, base, offset5)
    if not isinstance(ops[2], Immediate):
        raise _OperandError("el desplazamiento debe ser un número")
    return _pack(InstructionFormat.B, opcode=spec.opcode,
                 reg=_register(ops[0], 1), base=_register(ops[1], 2),
                 offset=_signed_field(InstructionFormat.B, "offset", ops[2].value,
                                      "el desplazamiento"))


def _encode_format_c(spec, instruction, address, resolver):
    fmt = InstructionFormat.C
    if not _is_int(instruction.nzp):
        raise _OperandError("BR requiere la máscara de condiciones nzp")
    nzp = _unsigned_field(fmt, "nzp", instruction.nzp, "la máscara nzp")
    offset = _pc_relative(instruction.operands[0], instruction, address, spec,
                          resolver, PC_INCREMENT, "palabras")
    return _pack(fmt, opcode=spec.opcode, nzp=nzp, offset=offset)


def _encode_jsr(spec, instruction, address, resolver):
    offset = _pc_relative(instruction.operands[0], instruction, address, spec,
                          resolver, PC_INCREMENT, "palabras")
    return _pack(InstructionFormat.JSR, opcode=spec.opcode, offset=offset)


def _encode_jump_reg(spec, instruction, address, resolver):
    return _pack(InstructionFormat.JUMP_REG, opcode=spec.opcode,
                 base=_register(instruction.operands[0], 1))


def _encode_lea(spec, instruction, address, resolver):
    offset = _pc_relative(instruction.operands[1], instruction, address, spec,
                          resolver, 1, "bytes")
    return _pack(InstructionFormat.LEA, opcode=spec.opcode,
                 dr=_register(instruction.operands[0], 1), offset=offset)


def _encode_trap(spec, instruction, address, resolver):
    operand = instruction.operands[0]
    if not isinstance(operand, Immediate):
        raise _OperandError("el vector debe ser un número")
    return _pack(InstructionFormat.TRAP, opcode=spec.opcode,
                 vector=_unsigned_field(InstructionFormat.TRAP, "vector",
                                        operand.value, "el vector"))


def _encode_no_operands(spec, instruction, address, resolver):
    return _pack(InstructionFormat.NO_OPERANDS, opcode=spec.opcode)


_FORMAT_ENCODERS = {
    InstructionFormat.A: _encode_format_a,
    InstructionFormat.B: _encode_format_b,
    InstructionFormat.C: _encode_format_c,
    InstructionFormat.JSR: _encode_jsr,
    InstructionFormat.JUMP_REG: _encode_jump_reg,
    InstructionFormat.LEA: _encode_lea,
    InstructionFormat.TRAP: _encode_trap,
    InstructionFormat.NO_OPERANDS: _encode_no_operands,
}


def _encode_instruction(instruction, address, resolver):
    """Bytes (Little Endian) de una instrucción ubicada en `address`."""
    spec = INSTRUCTIONS_BY_MNEMONIC.get(instruction.mnemonic)
    if spec is None:
        raise _OperandError(f"mnemónico desconocido '{instruction.mnemonic}'")
    if len(instruction.operands) != len(spec.operands):
        raise _OperandError(
            f"{spec.mnemonic} requiere {len(spec.operands)} operando(s), "
            f"se recibieron {len(instruction.operands)}")
    word = _FORMAT_ENCODERS[spec.fmt](spec, instruction, address, resolver)
    return word.to_bytes(WORD_BYTES, "little")


# ======================================================================
# Directivas que generan bytes
# ======================================================================
def _encode_fill(directive, resolver):
    value = directive.value
    if isinstance(value, Immediate):
        low, high = _FILL_RANGE
        if not _is_int(value.value) or not low <= value.value <= high:
            raise _OperandError(f".FILL {value.value!r} fuera de rango ({low} a {high})")
        word = value.value & WORD_MASK                      # complemento a dos de 16 bits
    elif isinstance(value, LabelRef):
        word = resolver.addressable(value.name)             # dirección absoluta
    else:
        raise _OperandError(".FILL requiere un número o una etiqueta")
    return word.to_bytes(WORD_BYTES, "little")


def _encode_blkw(directive):
    count = directive.count
    if not _is_int(count) or count < 1:
        raise _OperandError(f".BLKW requiere una cantidad entera >= 1, se recibió {count!r}")
    return bytes(count * WORD_BYTES)


def _encode_stringz(directive):
    low, high = _STRING_CODE_RANGE
    codes = []
    for character in directive.text:
        code = ord(character)
        if not low <= code <= high:
            raise _OperandError(
                f".STRINGZ: el carácter {character!r} (código {code}) no cabe en un "
                f"byte distinto de cero ({low} a {high})")
        codes.append(code)
    return bytes(codes) + b"\x00"


def _encode_statement(statement, address, resolver):
    if isinstance(statement, Instruction):
        return _encode_instruction(statement, address, resolver)
    if isinstance(statement, FillDirective):
        return _encode_fill(statement, resolver)
    if isinstance(statement, BlkwDirective):
        return _encode_blkw(statement)
    return _encode_stringz(statement)


_MEMORY_STATEMENTS = (Instruction, FillDirective, BlkwDirective, StringzDirective)
_NO_BYTES_STATEMENTS = (OrigDirective, EndDirective, ExternalDirective)


# ======================================================================
# API pública
# ======================================================================
def encode_program(program, symbol_table, external_symbols=None):
    """Segunda pasada: devuelve el EncodedProgram de `program`.

    `symbol_table` debe ser la que build_symbol_table calculó para ESE program.
    `external_symbols` es un mapping opcional nombre -> dirección para los
    símbolos declarados con .EXTERNAL.

    Lanza EncodeErrors, con TODOS los problemas encontrados, si el programa no
    puede codificarse; en ese caso no se devuelve nada.
    """
    if not isinstance(program, Program):
        raise TypeError(f"se esperaba un Program, se recibió {type(program).__name__}")
    if not isinstance(symbol_table, SymbolTable):
        raise TypeError(f"se esperaba una SymbolTable, se recibió {type(symbol_table).__name__}")

    errors = []
    resolver = _Resolver(symbol_table,
                         _check_external_symbols(external_symbols, symbol_table, errors))

    output = bytearray()
    cursor: Optional[int] = symbol_table.origin   # None = layout desincronizado por un error previo
    pending_padding = {pad.address: pad for pad in symbol_table.padding}
    seen_lines = set()

    def fail(line, message):
        errors.append(EncodeError(message, line.line_number, line.source))

    for line in program.lines:
        statement = line.statement
        if statement is None or isinstance(statement, (EndDirective, ExternalDirective)):
            continue
        if isinstance(statement, OrigDirective):
            if statement.address != symbol_table.origin:
                fail(line, f".ORIG {_hex(statement.address)} no coincide con el origen de la "
                           f"tabla de símbolos ({_hex(symbol_table.origin)}): ¿la tabla "
                           f"se construyó con otro programa?")
            continue
        if not isinstance(statement, _MEMORY_STATEMENTS):
            fail(line, f"sentencia no reconocida: {type(statement).__name__}")
            continue

        address = symbol_table.line_addresses.get(line.line_number)
        if address is None:
            fail(line, "la tabla de símbolos no tiene dirección para esta línea: "
                       "¿se construyó con otro programa?")
            cursor = None
            continue
        seen_lines.add(line.line_number)

        # --- consistencia con el mapa de memoria (no se recalcula nada) ---
        resync = cursor is None
        if not resync and address < cursor:
            fail(line, f"la sentencia está en {_hex(address)} pero el código anterior "
                       f"ya llega hasta {_hex(cursor)}: las sentencias se superponen")
            cursor = None
            continue
        if not resync and address > cursor:
            gap = address - cursor
            padding = pending_padding.pop(cursor, None)
            if padding is None or padding.size != gap:
                fail(line, f"entre {_hex(cursor)} y {_hex(address)} hay {gap} byte(s) sin "
                           f"relleno de alineación registrado en la tabla de símbolos")
                cursor = None
                continue
            if not isinstance(statement, Instruction):
                fail(line, f"la tabla de símbolos registra relleno antes de un dato "
                           f"({_hex(cursor)}): solo las instrucciones se alinean")
                cursor = None
                continue
            output.extend(bytes(gap))                       # relleno de alineación (0x00)
        if isinstance(statement, Instruction) and address % PC_INCREMENT:
            fail(line, f"la instrucción está en la dirección impar {_hex(address)}: "
                       f"las instrucciones deben estar alineadas a {PC_INCREMENT} bytes")
            cursor = None
            continue

        # --- codificación propiamente dicha ---
        try:
            encoded = _encode_statement(statement, address, resolver)
        except _OperandError as problem:
            fail(line, str(problem))
            cursor = None
            continue
        output.extend(encoded)
        cursor = address + len(encoded)

    # --- comprobaciones finales de consistencia con la tabla ---
    for number in sorted(set(symbol_table.line_addresses) - seen_lines):
        errors.append(EncodeError(
            f"la tabla de símbolos tiene una dirección para la línea {number}, que no "
            f"ocupa memoria en este programa: ¿se construyó con otro programa?"))
    for address in sorted(pending_padding):
        pad = pending_padding[address]
        errors.append(EncodeError(
            f"la tabla de símbolos registra {pad.size} byte(s) de relleno en "
            f"{_hex(address)} que el programa no necesita", pad.line_number))
    if cursor is not None and cursor != symbol_table.end_address:
        errors.append(EncodeError(
            f"el código termina en {_hex(cursor)} pero la tabla de símbolos indica "
            f"{_hex(symbol_table.end_address)}"))

    if errors:
        # Los errores globales (sin línea) primero; después, por línea.
        errors.sort(key=lambda e: (e.line_number is not None, e.line_number or 0))
        raise EncodeErrors(errors)
    return EncodedProgram(symbol_table.origin, bytes(output))