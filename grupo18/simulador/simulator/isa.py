"""
isa.py - Definición única de la arquitectura (ISA Lab 3c).

Es la fuente de verdad que comparten el simulador (decoder, cpu, traps) y el
futuro ensamblador. Contiene SOLO definiciones: no ejecuta nada ni importa
otros módulos del proyecto (así no puede haber dependencias circulares).

Contenido:
  1. Constantes de arquitectura (anchos, máscaras, registros, memoria, PC).
  2. Banderas N/Z/P, modos del formato A y vectores TRAP.
  3. Formatos de instrucción (InstructionFormat), los CAMPOS DE BITS de cada
     formato (BitField, FORMAT_FIELDS) y los tipos de operando.
  4. La tabla de las 26 instrucciones (INSTRUCTIONS) y sus índices.

Lo que NO está acá, a propósito:
  - Comportamiento del simulador (EOF de GETC, límite de run(), operaciones
    de la ALU): pertenece a cada módulo.
  - La interpretación de los campos (signo, campos reservados, reglas de cada
    instrucción): es semántica y sigue en decoder.py. Acá solo se describe DÓNDE
    está cada campo; decodificador y codificador comparten esa descripción.
"""

from dataclasses import dataclass
from enum import Enum, auto
from types import MappingProxyType

# ----------------------------------------------------------------------
# 1. Constantes de arquitectura
# ----------------------------------------------------------------------
WORD_BITS = 16
WORD_MASK = (1 << WORD_BITS) - 1        # 0xFFFF
BYTE_BITS = 8
BYTE_MASK = (1 << BYTE_BITS) - 1        # 0xFF
OPCODE_BITS = 5

REGISTER_COUNT = 8                      # R0..R7
REGISTER_MASK = REGISTER_COUNT - 1      # 0b111: un campo de registro tiene 3 bits
SP_REGISTER = 6                         # R6: puntero de pila (solo convención)
LINK_REGISTER = 7                       # R7: JSR y JSRR guardan aquí el retorno

MEMORY_SIZE = 1 << WORD_BITS            # 65.536 bytes (0x0000..0xFFFF)
PC_INCREMENT = 2                        # una instrucción ocupa 2 bytes

# ----------------------------------------------------------------------
# 2. Banderas, modos y vectores TRAP
# ----------------------------------------------------------------------
# Máscara NZP del salto condicional: bit 2 = N, bit 1 = Z, bit 0 = P.
NZP_N = 0b100
NZP_Z = 0b010
NZP_P = 0b001

# Valores del bit M del formato A.
MODE_REGISTER = 0
MODE_IMMEDIATE = 1

# Servicios TRAP definidos por nuestro simulador (inspirados en LC-3).
TRAP_GETC = 0x20
TRAP_OUT = 0x21
TRAP_PUTS = 0x22
TRAP_HALT = 0x25


# ----------------------------------------------------------------------
# 3. Formatos de instrucción y tipos de operando
# ----------------------------------------------------------------------
class InstructionFormat(Enum):
    """Formato de codificación de una instrucción."""
    A = "A"                      # [OP:5][DR:3][SR1:3][M:1][OP2:4]
    B = "B"                      # [OP:5][REG:3][BASE:3][OFFSET:5]
    C = "C"                      # [OP:5][NZP:3][PCOFFSET:8]
    JSR = "JSR"                  # [OP:5][OFFSET:11]
    JUMP_REG = "JUMP_REG"        # [OP:5][BASE:3][CEROS:8]   (JMP y JSRR)
    LEA = "LEA"                  # [OP:5][DR:3][OFFSET:8]
    TRAP = "TRAP"                # [OP:5][VECTOR:8][CEROS:3]
    NO_OPERANDS = "NO_OPERANDS"  # [OP:5][CEROS:11]          (NOP y HALT)


# ----------------------------------------------------------------------
# Campos de bits de cada formato
# ----------------------------------------------------------------------
@dataclass(frozen=True)
class BitField:
    """Un campo de bits dentro de una instrucción de 16 bits.

    `high` y `low` son los índices de bit (ambos incluidos); el bit 15 es el
    más significativo y el 0 el menos significativo. Ejemplo: el opcode ocupa
    BitField("opcode", 15, 11) y tiene un ancho de 5 bits.
    """
    name: str
    high: int
    low: int

    def __post_init__(self):
        if not isinstance(self.name, str) or not self.name:
            raise TypeError(f"el nombre de un campo debe ser un texto no vacío, "
                            f"se recibió {self.name!r}")
        for label, value in (("high", self.high), ("low", self.low)):
            # bool es subclase de int en Python; se rechaza explícitamente.
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(f"campo '{self.name}': {label} debe ser un entero, "
                                f"se recibió {value!r}")
        if not 0 <= self.low <= self.high <= WORD_BITS - 1:
            raise ValueError(
                f"campo '{self.name}': los límites deben cumplir "
                f"0 <= low <= high <= {WORD_BITS - 1}, se recibió {self.high}..{self.low}"
            )

    @property
    def width(self):
        """Cantidad de bits del campo."""
        return self.high - self.low + 1


# El opcode es el mismo campo en todos los formatos: el decodificador lo
# necesita ANTES de saber de qué formato es la instrucción.
OPCODE_FIELD = BitField("opcode", WORD_BITS - 1, WORD_BITS - OPCODE_BITS)


def _check_layout(owner, fields):
    """Comprueba que `fields` cubra EXACTAMENTE los 16 bits, sin superposiciones.

    Los campos deben declararse de mayor a menor bit. Lanza ValueError con el
    problema concreto; `owner` identifica al formato en el mensaje.
    """
    fields = tuple(fields)
    if not fields:
        raise ValueError(f"{owner}: no tiene campos")
    for field in fields:
        if not isinstance(field, BitField):
            raise TypeError(f"{owner}: se esperaba un BitField, se recibió {field!r}")
    names = [field.name for field in fields]
    if len(set(names)) != len(names):
        raise ValueError(f"{owner}: hay nombres de campo repetidos: {names}")
    ordered = sorted(fields, key=lambda field: field.high, reverse=True)
    if ordered != list(fields):
        raise ValueError(f"{owner}: los campos deben declararse de mayor a menor bit")
    expected_high = WORD_BITS - 1
    for field in fields:
        if field.high > expected_high:
            raise ValueError(f"{owner}: el campo '{field.name}' ({field.high}..{field.low}) "
                             f"se superpone con el anterior")
        if field.high < expected_high:
            raise ValueError(f"{owner}: los bits {expected_high}..{field.high + 1} no "
                             f"pertenecen a ningún campo (antes de '{field.name}')")
        expected_high = field.low - 1
    if expected_high != -1:
        raise ValueError(f"{owner}: los bits {expected_high}..0 no pertenecen a ningún campo")


def _build_format_fields(layouts):
    """Construye y VALIDA la tabla formato -> campos (se ejecuta al importar)."""
    missing = set(InstructionFormat) - set(layouts)
    extra = set(layouts) - set(InstructionFormat)
    if missing or extra:
        raise ValueError(f"FORMAT_FIELDS debe describir exactamente los formatos de "
                         f"InstructionFormat (faltan: {sorted(f.name for f in missing)}, "
                         f"sobran: {sorted(str(f) for f in extra)})")
    table = {}
    for fmt, specs in layouts.items():
        fields = tuple(BitField(*spec) for spec in specs)
        _check_layout(fmt.name, fields)
        if fields[0] != OPCODE_FIELD:
            raise ValueError(f"{fmt.name}: el primer campo debe ser el opcode "
                             f"{OPCODE_FIELD.high}..{OPCODE_FIELD.low}")
        table[fmt] = fields
    return MappingProxyType(table)


_F = InstructionFormat

# Fuente única de la posición de los campos. (nombre, bit alto, bit bajo)
FORMAT_FIELDS = _build_format_fields({
    _F.A:           (("opcode", 15, 11), ("dr", 10, 8), ("sr1", 7, 5),
                     ("mode", 4, 4), ("operand2", 3, 0)),
    _F.B:           (("opcode", 15, 11), ("reg", 10, 8), ("base", 7, 5),
                     ("offset", 4, 0)),
    _F.C:           (("opcode", 15, 11), ("nzp", 10, 8), ("offset", 7, 0)),
    _F.JSR:         (("opcode", 15, 11), ("offset", 10, 0)),
    _F.JUMP_REG:    (("opcode", 15, 11), ("base", 10, 8), ("reserved", 7, 0)),
    _F.LEA:         (("opcode", 15, 11), ("dr", 10, 8), ("offset", 7, 0)),
    _F.TRAP:        (("opcode", 15, 11), ("vector", 10, 3), ("reserved", 2, 0)),
    _F.NO_OPERANDS: (("opcode", 15, 11), ("reserved", 10, 0)),
})


def get_field(fmt, name):
    """Devuelve el BitField `name` del formato `fmt`.

    Lanza KeyError si el formato no existe o no tiene ese campo.
    """
    for field in FORMAT_FIELDS[fmt]:
        if field.name == name:
            return field
    raise KeyError(f"el formato {getattr(fmt, 'name', fmt)} no tiene un campo '{name}'")


class OperandKind(Enum):
    """Qué se espera en cada operando de una instrucción en Assembly.

    El formato por sí solo no alcanza para saberlo (NOT tiene 2 operandos,
    CMP no tiene destino, los shifts no admiten registro), por eso cada
    instrucción declara los suyos. Los rangos son los de la especificación.
    """
    REGISTER = auto()       # R0..R7
    REG_OR_IMM4 = auto()    # registro, o inmediato con signo de 4 bits (-8..+7)
    SHIFT_AMOUNT = auto()   # inmediato SIN signo de 4 bits (0..15)
    OFFSET5 = auto()        # inmediato con signo de 5 bits (-16..+15)
    LABEL_WORDS = auto()    # etiqueta / desplazamiento relativo al PC, en PALABRAS
    LABEL_BYTES = auto()    # etiqueta / desplazamiento relativo al PC, en BYTES
    VECTOR = auto()         # número de servicio sin signo de 8 bits (0..255)


_REG = OperandKind.REGISTER
_REG_OR_IMM4 = OperandKind.REG_OR_IMM4


@dataclass(frozen=True)
class InstructionSpec:
    """Definición única de una instrucción."""
    mnemonic: str
    opcode: int
    fmt: InstructionFormat
    operands: tuple             # tuple de OperandKind, en el orden de Assembly

    def __post_init__(self):
        if not 0 <= self.opcode < (1 << OPCODE_BITS):
            raise ValueError(
                f"{self.mnemonic}: el opcode {self.opcode} no cabe en "
                f"{OPCODE_BITS} bits"
            )


# ----------------------------------------------------------------------
# 4. Tabla de instrucciones (única fuente de opcodes, mnemónicos y formatos)
# ----------------------------------------------------------------------
_A, _B = InstructionFormat.A, InstructionFormat.B
_ARITH_OPERANDS = (_REG, _REG, _REG_OR_IMM4)
_SHIFT_OPERANDS = (_REG, _REG, OperandKind.SHIFT_AMOUNT)
_MEMORY_OPERANDS = (_REG, _REG, OperandKind.OFFSET5)

INSTRUCTIONS = (
    InstructionSpec("ADD",  0b00000, _A, _ARITH_OPERANDS),
    InstructionSpec("SUB",  0b00001, _A, _ARITH_OPERANDS),
    InstructionSpec("AND",  0b00010, _A, _ARITH_OPERANDS),
    InstructionSpec("OR",   0b00011, _A, _ARITH_OPERANDS),
    InstructionSpec("XOR",  0b00100, _A, _ARITH_OPERANDS),
    InstructionSpec("NOT",  0b00101, _A, (_REG, _REG)),
    InstructionSpec("SHL",  0b00110, _A, _SHIFT_OPERANDS),
    InstructionSpec("SHR",  0b00111, _A, _SHIFT_OPERANDS),
    InstructionSpec("SAR",  0b01000, _A, _SHIFT_OPERANDS),
    InstructionSpec("CMP",  0b01001, _A, (_REG, _REG_OR_IMM4)),
    InstructionSpec("LDW",  0b01010, _B, _MEMORY_OPERANDS),
    InstructionSpec("STW",  0b01011, _B, _MEMORY_OPERANDS),
    InstructionSpec("LDBL", 0b01100, _B, _MEMORY_OPERANDS),
    InstructionSpec("LDBH", 0b01101, _B, _MEMORY_OPERANDS),
    InstructionSpec("STBL", 0b01110, _B, _MEMORY_OPERANDS),
    InstructionSpec("STBH", 0b01111, _B, _MEMORY_OPERANDS),
    InstructionSpec("BR",   0b10000, InstructionFormat.C,
                    (OperandKind.LABEL_WORDS,)),
    InstructionSpec("JSR",  0b10001, InstructionFormat.JSR,
                    (OperandKind.LABEL_WORDS,)),
    InstructionSpec("JMP",  0b10010, InstructionFormat.JUMP_REG, (_REG,)),
    InstructionSpec("LEA",  0b10011, InstructionFormat.LEA,
                    (_REG, OperandKind.LABEL_BYTES)),
    InstructionSpec("LDI",  0b10100, _B, _MEMORY_OPERANDS),
    InstructionSpec("STI",  0b10101, _B, _MEMORY_OPERANDS),
    InstructionSpec("TRAP", 0b10110, InstructionFormat.TRAP,
                    (OperandKind.VECTOR,)),
    InstructionSpec("NOP",  0b10111, InstructionFormat.NO_OPERANDS, ()),
    InstructionSpec("HALT", 0b11000, InstructionFormat.NO_OPERANDS, ()),
    InstructionSpec("JSRR", 0b11001, InstructionFormat.JUMP_REG, (_REG,)),
)


def _index(specs, attribute):
    """Índice de solo lectura por `attribute`; rechaza valores repetidos."""
    index = {}
    for spec in specs:
        key = getattr(spec, attribute)
        if key in index:
            raise ValueError(f"{attribute} repetido en la tabla ISA: {key!r}")
        index[key] = spec
    return MappingProxyType(index)


INSTRUCTIONS_BY_OPCODE = _index(INSTRUCTIONS, "opcode")
INSTRUCTIONS_BY_MNEMONIC = _index(INSTRUCTIONS, "mnemonic")

# Opcodes sin instrucción (11010..11111): se DERIVAN, no se escriben a mano.
RESERVED_OPCODES = frozenset(range(1 << OPCODE_BITS)) - frozenset(INSTRUCTIONS_BY_OPCODE)