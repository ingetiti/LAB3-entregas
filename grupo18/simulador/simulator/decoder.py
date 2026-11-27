"""
decoder.py - Decodificador de instrucciones (ISA Lab 3c).

Convierte una instrucción de 16 bits en una estructura con sus campos
(DecodedInstruction). NO ejecuta nada: no lee ni escribe registros ni
memoria, y no valida la alineación del PC (eso es tarea de la CPU).

Numeración de bits: el bit 15 es el más significativo y el bit 0 el menos
significativo. El opcode ocupa siempre los bits 15..11.

La POSICIÓN de cada campo no se escribe en este módulo: sale de
isa.FORMAT_FIELDS (extract_field / extract_signed_field). Acá queda la
semántica: signo de los inmediatos y reglas de cada instrucción.

Formatos (de izquierda a derecha, del bit 15 al bit 0):

  A     [OP:5][DR:3][SR1:3][M:1][OP2:4]    ADD SUB AND OR XOR NOT SHL SHR SAR CMP
  B     [OP:5][REG:3][BASE:3][OFFSET:5]    LDW STW LDBL LDBH STBL STBH LDI STI
  C     [OP:5][NZP:3][PCOFFSET:8]          BR
  JSR   [OP:5][OFFSET:11]                  JSR
  JUMP  [OP:5][BASE:3][CEROS:8]            JMP JSRR
  LEA   [OP:5][DR:3][OFFSET:8]             LEA
  TRAP  [OP:5][VECTOR:8][CEROS:3]          TRAP
  NOP   [OP:5][CEROS:11]                   NOP HALT

Convenciones del formato A (decisiones de diseño):
  - M = 0: OP2 = [0][SR2:3]. El bit 3 de OP2 está reservado y debe ser 0.
  - M = 1: OP2 es un inmediato de 4 bits.
      * ADD SUB AND OR XOR CMP: con signo (-8..+7).
      * SHL SHR SAR: SIN signo (0..15), es una cantidad de desplazamiento.
  - SHL, SHR, SAR solo admiten el modo inmediato (M = 1).
  - NOT DR, SR1: M y OP2 no se usan y deben ser 0.
  - CMP SR1, op2: DR no se usa y debe ser 0 (CMP no guarda resultado).
"""

from dataclasses import dataclass
from typing import Optional

# Definiciones compartidas (ver isa.py). Se importan acá y quedan disponibles
# con los mismos nombres de siempre, para no romper a quien haga
# `from simulator.decoder import NZP_N, MODE_IMMEDIATE, ...`.
from simulator.isa import (  # noqa: F401  (algunas son solo re-exportaciones)
    INSTRUCTIONS,
    INSTRUCTIONS_BY_OPCODE,
    MODE_IMMEDIATE,
    MODE_REGISTER,
    NZP_N,
    NZP_P,
    NZP_Z,
    OPCODE_FIELD,
    REGISTER_MASK,
    WORD_MASK,
    InstructionFormat,
    get_field,
)


# ----------------------------------------------------------------------
# Excepciones
# ----------------------------------------------------------------------
class InvalidInstructionError(Exception):
    """La palabra recibida no es una instrucción válida de la ISA."""


class ReservedOpcodeError(InvalidInstructionError):
    """El opcode (11010..11111) está reservado: no es una instrucción."""


class ReservedFieldError(InvalidInstructionError):
    """Un campo que debe valer cero tiene otro valor."""


# ----------------------------------------------------------------------
# Tabla de instrucciones (derivada de isa.py: acá ya no se define nada)
# ----------------------------------------------------------------------
Format = InstructionFormat      # nombre histórico de este módulo (mismo objeto)

# Vista de compatibilidad: opcode -> (mnemónico, formato).
OPCODE_TABLE = {spec.opcode: (spec.mnemonic, spec.fmt) for spec in INSTRUCTIONS}

_SHIFTS = ("SHL", "SHR", "SAR")


# ----------------------------------------------------------------------
# Utilidades de bits
# ----------------------------------------------------------------------
def get_bits(word, high, low):
    """Extrae los bits `high`..`low` (ambos incluidos) de `word`.

    Ejemplo: get_bits(0b1010_0110_1100_0011, 15, 11) == 0b10100.
    """
    width = high - low + 1
    return (word >> low) & ((1 << width) - 1)


def sign_extend(value, bits):
    """Interpreta los `bits` bits inferiores de `value` como entero con signo.

    Ejemplos (5 bits): 0b01111 -> 15, 0b10000 -> -16, 0b11111 -> -1.
    """
    value &= (1 << bits) - 1
    if value & (1 << (bits - 1)):       # bit de signo en 1 -> negativo
        return value - (1 << bits)
    return value


def extract_field(word, fmt, name):
    """Valor SIN signo del campo `name` del formato `fmt` (según isa.FORMAT_FIELDS).

    Ejemplo: extract_field(0x0155, Format.A, "sr1") == 2.
    """
    field = get_field(fmt, name)
    return get_bits(word, field.high, field.low)


def extract_signed_field(word, fmt, name):
    """Como extract_field, pero con signo: el ancho sale de la descripción del campo."""
    field = get_field(fmt, name)
    return sign_extend(get_bits(word, field.high, field.low), field.width)


# ----------------------------------------------------------------------
# Resultado de la decodificación
# ----------------------------------------------------------------------
@dataclass(frozen=True)
class DecodedInstruction:
    """Instrucción descompuesta en campos.

    Solo se completan los campos que existen en la instrucción; el resto
    queda en None. Todos los números ya están interpretados:
      - registros: 0..7
      - imm, offset: enteros de Python con signo (imm de los shifts: sin signo)
      - nzp: 0..7 (ver NZP_N, NZP_Z, NZP_P)
      - vector: 0..255
    `offset` conserva las unidades de la instrucción (BR y JSR: palabras de
    instrucción); convertirlo a bytes es tarea de la CPU.

    Formato B: `reg` es el destino en las cargas (LDW, LDBL, LDBH, LDI) y la
    fuente en los almacenamientos (STW, STBL, STBH, STI).
    """
    word: int                      # instrucción original de 16 bits
    opcode: int                    # 0..25
    mnemonic: str
    fmt: Format
    dr: Optional[int] = None       # registro destino (A, LEA)
    sr1: Optional[int] = None      # primer operando (A)
    sr2: Optional[int] = None      # segundo operando en modo registro (A)
    mode: Optional[int] = None     # bit M: MODE_REGISTER o MODE_IMMEDIATE (A)
    imm: Optional[int] = None      # inmediato (A, modo inmediato)
    reg: Optional[int] = None      # registro de datos (B)
    base: Optional[int] = None     # registro base (B, JMP, JSRR)
    offset: Optional[int] = None   # desplazamiento con signo (B, BR, JSR, LEA)
    nzp: Optional[int] = None      # máscara de condiciones (BR)
    vector: Optional[int] = None   # vector del servicio (TRAP)


# ----------------------------------------------------------------------
# Validaciones internas
# ----------------------------------------------------------------------
def _validate_word(instruction):
    # bool es subclase de int en Python; se rechaza explícitamente.
    if isinstance(instruction, bool) or not isinstance(instruction, int):
        raise InvalidInstructionError(
            f"La instrucción debe ser un entero, se recibió "
            f"{type(instruction).__name__} ({instruction!r})"
        )
    if not 0 <= instruction <= WORD_MASK:
        raise InvalidInstructionError(
            f"Instrucción fuera del rango de 16 bits: {instruction} "
            f"(válido: 0x0000-0xFFFF)"
        )
    return instruction


def _require_zero(word, mnemonic, field, value):
    if value != 0:
        raise ReservedFieldError(
            f"{mnemonic} (0x{word:04X}): el campo {field} debe ser 0, "
            f"se encontró {value:#b}"
        )


def _build(word, opcode, mnemonic, fmt, **fields):
    return DecodedInstruction(word=word, opcode=opcode, mnemonic=mnemonic,
                              fmt=fmt, **fields)


# ----------------------------------------------------------------------
# Decodificadores por formato
# ----------------------------------------------------------------------
def _decode_format_a(word, opcode, mnemonic):
    fmt = Format.A
    dr = extract_field(word, fmt, "dr")
    sr1 = extract_field(word, fmt, "sr1")
    mode = extract_field(word, fmt, "mode")
    op2 = extract_field(word, fmt, "operand2")

    if mnemonic == "NOT":
        # NOT DR, SR1: M y OP2 no se usan y deben ser cero.
        _require_zero(word, mnemonic, "M", mode)
        _require_zero(word, mnemonic, "OP2", op2)
        return _build(word, opcode, mnemonic, fmt, dr=dr, sr1=sr1)

    if mnemonic in _SHIFTS:
        # Siempre modo inmediato. La cantidad es SIN signo (0..15).
        if mode != MODE_IMMEDIATE:
            raise InvalidInstructionError(
                f"{mnemonic} (0x{word:04X}): solo admite modo inmediato "
                f"(M=1), se encontró M=0"
            )
        return _build(word, opcode, mnemonic, fmt,
                      dr=dr, sr1=sr1, mode=mode, imm=op2)

    # ADD, SUB, AND, OR, XOR y CMP comparten el esquema del segundo operando.
    if mnemonic == "CMP":
        _require_zero(word, mnemonic, "DR", dr)
        dr = None                       # CMP no tiene registro destino

    if mode == MODE_REGISTER:
        # OP2 = [bit reservado][SR2]. Ambos subcampos viven DENTRO de `operand2`
        # (que es lo que describe isa.py): SR2 ocupa un campo de registro
        # (REGISTER_MASK) y el bit que queda por encima está reservado: debe ser 0.
        reserved_bit = op2 >> REGISTER_MASK.bit_length()
        _require_zero(word, mnemonic, "bit 3 de OP2", reserved_bit)
        return _build(word, opcode, mnemonic, fmt,
                      dr=dr, sr1=sr1, mode=mode, sr2=op2 & REGISTER_MASK)

    # Modo inmediato: entero con signo de 4 bits (-8..+7).
    return _build(word, opcode, mnemonic, fmt,
                  dr=dr, sr1=sr1, mode=mode,
                  imm=extract_signed_field(word, fmt, "operand2"))


def _decode_format_b(word, opcode, mnemonic):
    # Los 16 bits se usan completos: no hay campos reservados.
    fmt = Format.B
    return _build(word, opcode, mnemonic, fmt,
                  reg=extract_field(word, fmt, "reg"),
                  base=extract_field(word, fmt, "base"),
                  offset=extract_signed_field(word, fmt, "offset"))


def _decode_format_c(word, opcode, mnemonic):
    # NZP = 000 se acepta: es un salto que nunca se cumple.
    fmt = Format.C
    return _build(word, opcode, mnemonic, fmt,
                  nzp=extract_field(word, fmt, "nzp"),
                  offset=extract_signed_field(word, fmt, "offset"))


def _decode_jsr(word, opcode, mnemonic):
    fmt = Format.JSR
    return _build(word, opcode, mnemonic, fmt,
                  offset=extract_signed_field(word, fmt, "offset"))


def _decode_jump_reg(word, opcode, mnemonic):
    fmt = Format.JUMP_REG
    _require_zero(word, mnemonic, "CEROS", extract_field(word, fmt, "reserved"))
    return _build(word, opcode, mnemonic, fmt,
                  base=extract_field(word, fmt, "base"))


def _decode_lea(word, opcode, mnemonic):
    fmt = Format.LEA
    return _build(word, opcode, mnemonic, fmt,
                  dr=extract_field(word, fmt, "dr"),
                  offset=extract_signed_field(word, fmt, "offset"))


def _decode_trap(word, opcode, mnemonic):
    # No se valida que el vector exista: eso lo resuelve la CPU (traps.py).
    fmt = Format.TRAP
    _require_zero(word, mnemonic, "CEROS", extract_field(word, fmt, "reserved"))
    return _build(word, opcode, mnemonic, fmt,
                  vector=extract_field(word, fmt, "vector"))


def _decode_no_operands(word, opcode, mnemonic):
    fmt = Format.NO_OPERANDS
    _require_zero(word, mnemonic, "CEROS", extract_field(word, fmt, "reserved"))
    return _build(word, opcode, mnemonic, fmt)


_DECODERS = {
    Format.A: _decode_format_a,
    Format.B: _decode_format_b,
    Format.C: _decode_format_c,
    Format.JSR: _decode_jsr,
    Format.JUMP_REG: _decode_jump_reg,
    Format.LEA: _decode_lea,
    Format.TRAP: _decode_trap,
    Format.NO_OPERANDS: _decode_no_operands,
}


# ----------------------------------------------------------------------
# Función pública
# ----------------------------------------------------------------------
def decode(instruction):
    """Decodifica una instrucción de 16 bits.

    Devuelve un DecodedInstruction. Lanza InvalidInstructionError (o una de
    sus subclases) si la palabra no es una instrucción válida.
    """
    word = _validate_word(instruction)
    opcode = get_bits(word, OPCODE_FIELD.high, OPCODE_FIELD.low)
    spec = INSTRUCTIONS_BY_OPCODE.get(opcode)
    if spec is None:
        raise ReservedOpcodeError(
            f"Opcode reservado 0b{opcode:05b} en la instrucción 0x{word:04X}"
        )
    return _DECODERS[spec.fmt](word, opcode, spec.mnemonic)