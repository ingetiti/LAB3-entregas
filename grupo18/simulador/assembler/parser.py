"""
parser.py - Parser del ensamblador (ISA Lab 3c). Etapa 5.2.

Lee texto Assembly y devuelve una representación estructurada (Program).
NO codifica instrucciones, NO asigna direcciones y NO resuelve etiquetas:
eso corresponde a las etapas siguientes, que consumen este resultado sin
volver a analizar el texto.

GRAMÁTICA
---------
  línea       := [etiqueta ":"] [sentencia] [";" comentario]
  sentencia   := instrucción | directiva
  instrucción := MNEMÓNICO [operando {"," operando}]
  directiva   := .ORIG literal | .END | .FILL (literal | símbolo)
               | .BLKW literal | .STRINGZ "cadena" | .EXTERNAL símbolo

LÉXICO
------
  Etiqueta   Letra o '_' seguida de letras, dígitos o '_'. Distingue
             mayúsculas de minúsculas. No puede ser un registro (R0..R9...,
             SP, LR), un mnemónico (incluidas las variantes BRn, BRz...) ni
             parecerse a un literal hexadecimal (x25, xFACE).
  Registro   R0..R7, SP (= R6), LR (= R7). Sin distinguir mayúsculas.
  Literal    #5  #-3   decimal (el signo '-' solo va dentro de '#')
             x25 X25 0x25 0X25   hexadecimal (siempre sin signo)
             Un número sin prefijo (5) NO es válido: así nunca se confunde
             con un decimal ni con una etiqueta.
  Cadena     Entre comillas dobles. Escapes: \\n \\t \\r \\\\ \\"
             Cada carácter debe caber en un byte (códigos 1..255).
  Comentario ';' hasta el fin de línea (salvo dentro de una cadena).
  Mnemónicos y directivas no distinguen mayúsculas de minúsculas.

La instrucción BR admite los sufijos n, z, p, nz, np, zp y nzp (en ese
orden); BR sin sufijo equivale a BRnzp. Son variantes sintácticas de la misma
instrucción: el resultado usa mnemónico "BR" y una máscara `nzp` ya calculada.

VALIDACIONES DE ESTRUCTURA (a nivel de programa)
------------------------------------------------
  - Etiquetas duplicadas.
  - Un solo .ORIG.
  - Después de .END solo se admiten líneas en blanco y comentarios.
  Que existan .ORIG y .END, y que .ORIG vaya primero, se verifica en la
  etapa de direcciones (5.4), no acá.
"""

import re
from dataclasses import dataclass
from typing import Optional, Tuple, Union

from simulator.isa import (
    INSTRUCTIONS_BY_MNEMONIC,
    LINK_REGISTER,
    NZP_N,
    NZP_P,
    NZP_Z,
    SP_REGISTER,
    WORD_BITS,
    WORD_MASK,
    InstructionFormat,
    InstructionSpec,
    OperandKind,
)

__all__ = [
    "BlkwDirective", "EndDirective", "ExternalDirective", "FillDirective",
    "Immediate", "Instruction", "LabelRef", "OrigDirective", "ParseError",
    "ParseErrors", "ParsedLine", "Program", "Register", "Statement",
    "StringzDirective", "normalize_mnemonic", "parse_line", "parse_program",
]


# ======================================================================
# Errores
# ======================================================================
class ParseError(Exception):
    """Error de sintaxis en UNA línea. Guarda el número de línea y el texto."""

    def __init__(self, message, line_number=None, source=None):
        self.message = message
        self.line_number = line_number
        self.source = source
        prefix = f"línea {line_number}: " if line_number is not None else ""
        super().__init__(prefix + message)


class ParseErrors(Exception):
    """Todos los errores de un programa (parse_program no se detiene en el primero)."""

    def __init__(self, errors):
        self.errors = tuple(errors)
        detail = "\n".join(f"  {error}" for error in self.errors)
        super().__init__(f"{len(self.errors)} error(es) de sintaxis:\n{detail}")


# ======================================================================
# Representación del resultado (todas inmutables)
# ======================================================================
@dataclass(frozen=True)
class Register:
    """Operando registro, ya normalizado a su número (SP -> 6, LR -> 7)."""
    number: int


@dataclass(frozen=True)
class Immediate:
    """Operando numérico (#5, x25, 0x25...) como entero de Python."""
    value: int


@dataclass(frozen=True)
class LabelRef:
    """Referencia a una etiqueta, SIN resolver (la dirección se asigna después)."""
    name: str


Operand = Union[Register, Immediate, LabelRef]


class Statement:
    """Base de las sentencias: una instrucción o una directiva."""


@dataclass(frozen=True)
class Instruction(Statement):
    """Instrucción con sus operandos ya validados contra isa.py.

    `mnemonic` es el canónico en mayúsculas (todas las variantes BR son "BR").
    `operands` respeta el orden y los tipos de `spec.operands`.
    `nzp` es la máscara de condiciones (NZP_N | NZP_Z | NZP_P) y solo existe
    en BR; en el resto vale None.
    """
    mnemonic: str
    operands: Tuple[Operand, ...]
    nzp: Optional[int] = None

    @property
    def spec(self) -> InstructionSpec:
        return INSTRUCTIONS_BY_MNEMONIC[self.mnemonic]


@dataclass(frozen=True)
class OrigDirective(Statement):
    """.ORIG addr  - dirección de origen (0..0xFFFF)."""
    address: int


@dataclass(frozen=True)
class EndDirective(Statement):
    """.END - fin del programa."""


@dataclass(frozen=True)
class FillDirective(Statement):
    """.FILL v - una palabra de 16 bits: un número (-32768..65535) o una etiqueta."""
    value: Union[Immediate, LabelRef]


@dataclass(frozen=True)
class BlkwDirective(Statement):
    """.BLKW n - reserva n posiciones (n >= 1).

    La unidad (palabras o bytes) la fija la etapa de direcciones: acá solo se
    valida y se conserva el número.
    """
    count: int


@dataclass(frozen=True)
class StringzDirective(Statement):
    """.STRINGZ "txt" - `text` ya sin comillas y con los escapes resueltos.

    NO incluye el terminador: el byte 0 lo agrega la etapa de codificación.
    """
    text: str


@dataclass(frozen=True)
class ExternalDirective(Statement):
    """.EXTERNAL nombre - declara un símbolo definido fuera del programa."""
    name: str


@dataclass(frozen=True)
class ParsedLine:
    """Una línea significativa del programa.

    `label` es la etiqueta definida en la línea (o None). `statement` es la
    instrucción o directiva (o None si la línea solo tiene una etiqueta).
    Una etiqueta sin sentencia apunta a la próxima sentencia que ocupe memoria.
    """
    line_number: int          # base 1
    source: str               # texto original, útil para mensajes de error
    label: Optional[str] = None
    statement: Optional[Statement] = None


@dataclass(frozen=True)
class Program:
    """Resultado de parse_program: solo las líneas con etiqueta o sentencia.

    Las líneas en blanco y las que solo tienen comentario se descartan, pero
    cada ParsedLine conserva su número de línea original.
    """
    lines: Tuple[ParsedLine, ...] = ()


# ======================================================================
# Rangos de los operandos
# ======================================================================
def _signed_range(bits):
    return -(1 << (bits - 1)), (1 << (bits - 1)) - 1


def _unsigned_range(bits):
    return 0, (1 << bits) - 1


_IMM4_RANGE = _signed_range(4)          # ADD, SUB, AND, OR, XOR, CMP
_SHIFT_RANGE = _unsigned_range(4)       # SHL, SHR, SAR
_OFFSET5_RANGE = _signed_range(5)       # LDW, STW, LDBL, LDBH, STBL, STBH, LDI, STI
_VECTOR_RANGE = _unsigned_range(8)      # TRAP
# Ancho del desplazamiento relativo al PC: depende de la INSTRUCCIÓN, no del
# tipo de operando (BR y LEA usan 8 bits; JSR usa 11).
_PC_OFFSET_BITS = {
    InstructionFormat.C: 8,
    InstructionFormat.JSR: 11,
    InstructionFormat.LEA: 8,
}
_ORIG_RANGE = (0, WORD_MASK)
_FILL_RANGE = (-(1 << (WORD_BITS - 1)), WORD_MASK)      # -32768..65535


def _immediate_range(kind, spec):
    if kind is OperandKind.REG_OR_IMM4:
        return _IMM4_RANGE
    if kind is OperandKind.SHIFT_AMOUNT:
        return _SHIFT_RANGE
    if kind is OperandKind.OFFSET5:
        return _OFFSET5_RANGE
    if kind is OperandKind.VECTOR:
        return _VECTOR_RANGE
    return _signed_range(_PC_OFFSET_BITS[spec.fmt])     # LABEL_WORDS / LABEL_BYTES


def _describe(kind, spec, short=False):
    """Descripción en español de lo que espera un operando (para los errores)."""
    if kind is OperandKind.REGISTER:
        return "registro" if short else "registro (R0-R7, SP o LR)"
    low, high = _immediate_range(kind, spec)
    return {
        OperandKind.REG_OR_IMM4: f"registro o inmediato ({low} a {high})",
        OperandKind.SHIFT_AMOUNT: f"cantidad de desplazamiento inmediata ({low} a {high})",
        OperandKind.OFFSET5: f"desplazamiento inmediato ({low} a {high})",
        OperandKind.LABEL_WORDS: f"etiqueta o desplazamiento en palabras ({low} a {high})",
        OperandKind.LABEL_BYTES: f"etiqueta o desplazamiento en bytes ({low} a {high})",
        OperandKind.VECTOR: f"vector de servicio ({low} a {high})",
    }[kind]


# Qué clases de operando admite cada tipo de operando de isa.py.
_ALLOWED = {
    OperandKind.REGISTER: (Register,),
    OperandKind.REG_OR_IMM4: (Register, Immediate),
    OperandKind.SHIFT_AMOUNT: (Immediate,),
    OperandKind.OFFSET5: (Immediate,),
    OperandKind.LABEL_WORDS: (LabelRef, Immediate),
    OperandKind.LABEL_BYTES: (LabelRef, Immediate),
    OperandKind.VECTOR: (Immediate,),
}


# ======================================================================
# Mnemónicos y variantes de BR
# ======================================================================
_BRANCH = "BR"          # único mnemónico de isa.py que admite sufijo NZP


def _build_branch_suffixes():
    """Sufijo -> máscara NZP. Se genera: '' (BR) = nzp, 'N', 'Z', 'P', 'NZ', ..."""
    letters = (("N", NZP_N), ("Z", NZP_Z), ("P", NZP_P))
    all_bits = NZP_N | NZP_Z | NZP_P
    suffixes = {"": all_bits}               # BR sin sufijo = BRnzp
    for mask in range(1, all_bits + 1):
        suffix = "".join(letter for letter, bit in letters if mask & bit)
        suffixes[suffix] = mask
    return suffixes


_BRANCH_SUFFIX_MASKS = _build_branch_suffixes()


def normalize_mnemonic(token):
    """Normaliza un mnemónico escrito por el usuario.

    Devuelve (mnemónico canónico, nzp) o None si no existe. `nzp` es la
    máscara de condiciones para BR y sus variantes, y None para el resto.
    Es el ÚNICO lugar donde se interpretan las variantes de BR.

        "add"    -> ("ADD", None)      "BRnz" -> ("BR", 0b110)
        "BR"     -> ("BR", 0b111)      "FOO"  -> None
    """
    upper = token.upper()
    if upper == _BRANCH:
        return _BRANCH, _BRANCH_SUFFIX_MASKS[""]
    if upper in INSTRUCTIONS_BY_MNEMONIC:
        return upper, None
    if upper.startswith(_BRANCH) and upper[len(_BRANCH):] in _BRANCH_SUFFIX_MASKS:
        return _BRANCH, _BRANCH_SUFFIX_MASKS[upper[len(_BRANCH):]]
    return None


def _resolve_mnemonic(token):
    resolved = normalize_mnemonic(token)
    if resolved is not None:
        return resolved
    suffix = token.upper()[len(_BRANCH):]
    if token.upper().startswith(_BRANCH) and suffix and set(suffix) <= set("NZP"):
        raise ParseError(
            f"variante de BR inválida '{token}': los sufijos válidos son "
            f"n, z, p, nz, np, zp y nzp (en ese orden)"
        )
    raise ParseError(f"mnemónico desconocido '{token}'")


# ======================================================================
# Nombres (etiquetas y símbolos)
# ======================================================================
_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_REGISTER_NAME = re.compile(r"R[0-7]|SP|LR", re.IGNORECASE)
_REGISTER_LIKE = re.compile(r"R[0-9]+", re.IGNORECASE)
_HEX_LIKE = re.compile(r"x[0-9a-f]+", re.IGNORECASE)


def _name_problem(name):
    """Por qué `name` no puede ser una etiqueta (o None si es válido)."""
    if not _IDENTIFIER.fullmatch(name):
        return ("no es un nombre válido: debe empezar con una letra o '_' "
                "y contener solo letras, dígitos y '_'")
    if _REGISTER_NAME.fullmatch(name) or _REGISTER_LIKE.fullmatch(name):
        return "es un nombre de registro"
    if normalize_mnemonic(name) is not None:
        return "es un mnemónico"
    if _HEX_LIKE.fullmatch(name):
        return "se confunde con un literal hexadecimal"
    return None


# ======================================================================
# Operandos
# ======================================================================
_DECIMAL = re.compile(r"#(-?[0-9]+)")
_HEXADECIMAL = re.compile(r"(?:0[xX]|[xX])([0-9a-fA-F]+)")


def _to_int(text, base, token):
    try:
        return int(text, base)
    except ValueError:                      # p. ej. más de 4300 dígitos decimales
        raise ParseError(f"literal demasiado largo '{token[:20]}...'") from None


def _classify(token):
    """Clasifica un operando: Register, Immediate o LabelRef (o lanza ParseError)."""
    if _REGISTER_NAME.fullmatch(token):
        upper = token.upper()
        if upper == "SP":
            return Register(SP_REGISTER)
        if upper == "LR":
            return Register(LINK_REGISTER)
        return Register(int(upper[1]))
    if _REGISTER_LIKE.fullmatch(token):
        raise ParseError(
            f"registro inexistente '{token}' (válidos: R0-R7, SP, LR)"
        )
    match = _DECIMAL.fullmatch(token)
    if match:
        return Immediate(_to_int(match.group(1), 10, token))
    match = _HEXADECIMAL.fullmatch(token)
    if match:
        return Immediate(_to_int(match.group(1), 16, token))
    if token.startswith("#"):
        raise ParseError(
            f"literal decimal mal formado '{token}': use #n o #-n, por ejemplo #5 o #-3"
        )
    if token[:2] in ("0x", "0X"):
        raise ParseError(
            f"literal hexadecimal mal formado '{token}': use 0x seguido de dígitos "
            f"hexadecimales, por ejemplo 0x25"
        )
    if re.fullmatch(r"-?[0-9]+", token):
        raise ParseError(
            f"literal sin prefijo '{token}': use #{token} para decimal o x/0x para hexadecimal"
        )
    if token[:1].isdigit() or token[:1] == "-":
        raise ParseError(f"operando no reconocido '{token}'")
    if _IDENTIFIER.fullmatch(token):
        problem = _name_problem(token)
        if problem:
            raise ParseError(f"'{token}' {problem}: no puede usarse como etiqueta")
        return LabelRef(token)
    raise ParseError(f"operando no reconocido '{token}'")


def _classify_in(context, token):
    """Como _classify, pero los errores indican en qué instrucción/directiva ocurren."""
    try:
        return _classify(token)
    except ParseError as error:
        raise ParseError(f"{context}: {error.message}") from None


def _found(operand, token, expected_register=False):
    if isinstance(operand, Register):
        return f"el registro {token}"
    if isinstance(operand, Immediate):
        return f"el inmediato {token}"
    text = f"la etiqueta '{token}'"
    if expected_register:
        text += " (¿registro mal escrito? los válidos son R0-R7, SP y LR)"
    return text


def _check_range(value, bounds, token, what):
    """`bounds` = (mínimo, máximo); un máximo None significa "sin tope"."""
    low, high = bounds
    if value >= low and (high is None or value <= high):
        return
    if len(token) > 24:                     # evita imprimir literales enormes
        shown = token[:21] + "..."
    else:
        shown = token if token.startswith("#") else f"{token} (= {value})"
    allowed = (f"se admiten valores a partir de {low}" if high is None
               else f"se admiten valores de {low} a {high}")
    raise ParseError(f"{what} {shown} está fuera de rango: {allowed}")


def _build_operand(spec, written, position, kind, token):
    """Clasifica y valida UN operando de una instrucción."""
    where = f"{written}, operando {position}"
    operand = _classify_in(where, token)
    if not isinstance(operand, _ALLOWED[kind]):
        raise ParseError(
            f"{where}: se esperaba {_describe(kind, spec)}, se encontró "
            f"{_found(operand, token, kind is OperandKind.REGISTER)}"
        )
    if isinstance(operand, Immediate):
        _check_range(operand.value, _immediate_range(kind, spec), token,
                     f"{where}: el inmediato")
    return operand


def _split_operands(written, text):
    text = text.strip()
    if not text:
        return []
    parts = [part.strip() for part in text.split(",")]
    if "" in parts:
        raise ParseError(f"{written}: operando vacío (hay una coma de más)")
    return parts


# ======================================================================
# Instrucciones
# ======================================================================
def _parse_instruction(written, operands_text):
    mnemonic, nzp = _resolve_mnemonic(written)
    spec = INSTRUCTIONS_BY_MNEMONIC[mnemonic]
    tokens = _split_operands(written, operands_text)
    if len(tokens) != len(spec.operands):
        expected = ", ".join(_describe(kind, spec, short=True) for kind in spec.operands) or "ninguno"
        problem = "faltan operandos" if len(tokens) < len(spec.operands) else "sobran operandos"
        raise ParseError(
            f"{written}: {problem}: se esperan {len(spec.operands)} ({expected}) "
            f"y se recibieron {len(tokens)}"
        )
    operands = tuple(
        _build_operand(spec, written, position, kind, token)
        for position, (kind, token) in enumerate(zip(spec.operands, tokens), start=1)
    )
    return Instruction(mnemonic, operands, nzp)


# ======================================================================
# Directivas
# ======================================================================
_STRING_ESCAPES = {"n": "\n", "t": "\t", "r": "\r", "\\": "\\", '"': '"'}


def _directive_operands(written, text, count, meaning):
    tokens = _split_operands(written, text)
    if len(tokens) != count:
        noun = "operando" if count == 1 else "operandos"
        raise ParseError(
            f"{written} espera {count} {noun} ({meaning}), se recibieron {len(tokens)}"
        )
    return tokens


def _numeric(written, token, bounds, what):
    operand = _classify_in(written, token)
    if not isinstance(operand, Immediate):
        raise ParseError(
            f"{written}: se esperaba un literal numérico ({what}), se encontró "
            f"{_found(operand, token)}"
        )
    _check_range(operand.value, bounds, token, f"{written}: el valor")
    return operand.value


def _parse_orig(written, text):
    (token,) = _directive_operands(written, text, 1, "dirección de origen")
    return OrigDirective(_numeric(written, token, _ORIG_RANGE, "dirección de origen"))


def _parse_end(written, text):
    _directive_operands(written, text, 0, "ninguno")
    return EndDirective()


def _parse_fill(written, text):
    (token,) = _directive_operands(written, text, 1, "valor o etiqueta")
    operand = _classify_in(written, token)
    if isinstance(operand, Register):
        raise ParseError(
            f"{written}: se esperaba un número o una etiqueta, se encontró {_found(operand, token)}"
        )
    if isinstance(operand, Immediate):
        _check_range(operand.value, _FILL_RANGE, token, f"{written}: el valor")
    return FillDirective(operand)


def _parse_blkw(written, text):
    (token,) = _directive_operands(written, text, 1, "cantidad de posiciones")
    count = _numeric(written, token, (1, None), "cantidad de posiciones")
    return BlkwDirective(count)


def _parse_external(written, text):
    (token,) = _directive_operands(written, text, 1, "nombre del símbolo")
    operand = _classify_in(written, token)
    if not isinstance(operand, LabelRef):
        raise ParseError(
            f"{written}: se esperaba un nombre de símbolo, se encontró {_found(operand, token)}"
        )
    return ExternalDirective(operand.name)


def _parse_stringz(written, text):
    text = text.strip()
    if not text:
        raise ParseError(
            f"{written} espera 1 operando (una cadena entre comillas dobles), se recibieron 0"
        )
    if text[0] != '"':
        raise ParseError(
            f"{written}: la cadena debe ir entre comillas dobles, se encontró '{text}'"
        )
    chars = []
    index = 1
    while index < len(text):
        char = text[index]
        if char == "\\":
            escape = text[index + 1] if index + 1 < len(text) else ""
            if escape not in _STRING_ESCAPES:
                raise ParseError(
                    f"{written}: secuencia de escape desconocida '\\{escape}' "
                    f"(válidas: \\n \\t \\r \\\\ \\\")"
                )
            chars.append(_STRING_ESCAPES[escape])
            index += 2
        elif char == '"':
            tail = text[index + 1:].strip()
            if tail:
                raise ParseError(
                    f"{written}: texto inesperado después de la cadena: '{tail}'"
                )
            return _make_stringz(written, "".join(chars))
        else:
            chars.append(char)
            index += 1
    raise ParseError(f"{written}: cadena sin cerrar (falta la comilla doble final)")


def _make_stringz(written, value):
    for char in value:
        if not 1 <= ord(char) <= 0xFF:
            raise ParseError(
                f"{written}: el carácter {char!r} (U+{ord(char):04X}) no cabe en un byte "
                f"(se admiten códigos 1 a 255; el terminador 0 se agrega solo)"
            )
    return StringzDirective(value)


_DIRECTIVES = {
    ".ORIG": _parse_orig,
    ".END": _parse_end,
    ".FILL": _parse_fill,
    ".BLKW": _parse_blkw,
    ".STRINGZ": _parse_stringz,
    ".EXTERNAL": _parse_external,
}


def _parse_directive(written, operands_text):
    handler = _DIRECTIVES.get(written.upper())
    if handler is None:
        raise ParseError(
            f"directiva desconocida '{written}' (válidas: {', '.join(_DIRECTIVES)})"
        )
    return handler(written, operands_text)


# ======================================================================
# Líneas
# ======================================================================
_LABEL_PREFIX = re.compile(r'\s*([^\s:"]+)\s*:')
_GLUED_OPERAND = re.compile(r'[,"#]')


def _strip_comment(text):
    """Quita el comentario (';' ...) respetando los ';' dentro de cadenas."""
    in_string = False
    escaped = False
    for index, char in enumerate(text):
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
        elif char == '"':
            in_string = True
        elif char == ";":
            return text[:index]
    return text


def _split_label(code):
    """Separa la etiqueta inicial. Devuelve (etiqueta o None, resto)."""
    if code.lstrip().startswith(":"):
        raise ParseError("falta el nombre de la etiqueta antes de ':'")
    match = _LABEL_PREFIX.match(code)
    if not match:
        return None, code
    name = match.group(1)
    problem = _name_problem(name)
    if problem:
        raise ParseError(f"etiqueta inválida '{name}': {problem}")
    rest = code[match.end():]
    if _LABEL_PREFIX.match(rest):
        raise ParseError("solo se admite una etiqueta por línea")
    return name, rest


def _parse_statement(text):
    parts = text.split(None, 1)
    head = parts[0]
    operands_text = parts[1] if len(parts) > 1 else ""
    glued = _GLUED_OPERAND.search(head)
    if glued and glued.start() > 0:
        raise ParseError(
            f"falta un espacio entre '{head[:glued.start()]}' y sus operandos"
        )
    if head.startswith("."):
        return _parse_directive(head, operands_text)
    return _parse_instruction(head, operands_text)


def _parse_line(text, line_number):
    code = _strip_comment(text)
    label, rest = _split_label(code)
    rest = rest.strip()
    statement = _parse_statement(rest) if rest else None
    if label is not None and isinstance(statement, (OrigDirective, ExternalDirective)):
        name = ".ORIG" if isinstance(statement, OrigDirective) else ".EXTERNAL"
        raise ParseError(f"una etiqueta no tiene sentido en la misma línea que {name}")
    return ParsedLine(line_number, text, label, statement)


def parse_line(text, line_number=1):
    """Analiza UNA línea. Lanza ParseError (con número de línea) si es inválida.

    Una línea en blanco o con solo un comentario devuelve un ParsedLine sin
    etiqueta ni sentencia.
    """
    try:
        return _parse_line(text, line_number)
    except ParseError as error:
        raise ParseError(error.message, line_number, text) from None


def parse_program(source):
    """Analiza un programa completo (str) y devuelve un Program.

    Recoge TODOS los errores y los lanza juntos como ParseErrors. Además de
    la sintaxis de cada línea, comprueba: etiquetas duplicadas, un solo .ORIG
    y que nada aparezca después de .END.
    """
    if not isinstance(source, str):
        raise TypeError(f"el programa debe ser texto (str), se recibió {type(source).__name__}")
    errors = []
    lines = []
    labels = {}             # etiqueta -> línea donde se definió
    orig_line = None
    end_line = None
    for number, text in enumerate(re.split(r"\r\n|\r|\n", source), start=1):
        try:
            parsed = parse_line(text, number)
        except ParseError as error:
            errors.append(error)
            continue
        if parsed.label is None and parsed.statement is None:
            continue                                    # en blanco o solo comentario
        if end_line is not None:
            errors.append(ParseError(
                f"no puede haber etiquetas, instrucciones ni directivas después de "
                f".END (declarado en la línea {end_line})", number, text))
            continue
        if parsed.label is not None:
            if parsed.label in labels:
                errors.append(ParseError(
                    f"etiqueta '{parsed.label}' duplicada: ya está definida en la "
                    f"línea {labels[parsed.label]}", number, text))
                continue
            labels[parsed.label] = number
        if isinstance(parsed.statement, OrigDirective):
            if orig_line is not None:
                errors.append(ParseError(
                    f"solo se admite un .ORIG (el primero está en la línea {orig_line})",
                    number, text))
                continue
            orig_line = number
        elif isinstance(parsed.statement, EndDirective):
            end_line = number
        lines.append(parsed)
    if errors:
        raise ParseErrors(errors)
    return Program(tuple(lines))
