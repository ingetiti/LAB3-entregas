from __future__ import annotations

import argparse
import ast
import re
import sys

from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple


# ============================================================
# CONSTANTES DE LA ARQUITECTURA
# ============================================================

MEMORY_SIZE = 0x10000          # 2^16 bytes
MASK_16 = 0xFFFF

# NOP:  00000 | 000 | 00000000  (BR con condicion nzp = 000: nunca salta)
#       Es la palabra 0x0000, igual que en la LC-3 original.
#       El opcode 0x0F quedo libre y ahora es ADDC.
NOP = 0x0000


# ============================================================
# OPCODES DE NUESTRA ISA
# ============================================================

OP = {
    "BR":   0x00,
    "ADD":  0x01,
    "LDW":  0x02,
    "STW":  0x03,
    "JSR":  0x04,
    "AND":  0x05,
    "LDR":  0x06,
    "STR":  0x07,
    "MULH": 0x08,   # parte ALTA (bits 31..16) del producto con signo (antes RTI)
    "NOT":  0x09,
    "LDBL": 0x0A,
    "STBL": 0x0B,
    "JMP":  0x0C,
    "LDBH": 0x0D,
    "LEA":  0x0E,
    "ADDC": 0x0F,   # suma con acarreo: DR = SR1 + SR2 + C (antes NOP)
    "STBH": 0x10,
    "LDBR": 0x11,
    "STRB": 0x12,
    "SUB":  0x13,
    "MUL":  0x14,
    "DIV":  0x15,
    "SHL":  0x17,
    "SHR":  0x18,
    "TRAP": 0x1F,
}


# ============================================================
# OPCODES EXTENDIDOS
# ============================================================
#
# Opcodes liberados al eliminar MOD (0x16), CMP (0x19) y OR (0x1A),
# más los 4 reservados (0x1B-0x1E). Se usan para ampliar el rango
# de offsets, sin gastar bits de formato:
#
#   ADDI  : ADD con inmediato de 5 bits (-16..15)
#           5 | DR | SR1 | imm5
#
#   X = "extendido": el opcode extendido aporta el BIT 8 (signo) del
#   offset. El ensamblador elige solo cuál usar; para el programador
#   es la misma instrucción.
#
#   BR, LDW, STW, LEA : offset de 9 bits en PALABRAS (-256..255)
#       opcode base     -> offset =   low8        (0 .. 255)
#       opcode extendido-> offset = low8 - 256    (-256 .. -1)
#
#   LDR, STR          : offset de 6 bits en PALABRAS (-32..31)
#                       dirección = BaseR + 2 * offset  (como la LC-3b)
#       opcode base     -> offset =   low5        (0 .. 31)
#       opcode extendido-> offset = low5 - 32     (-32 .. -1)

OP_EXT = {
    "ADDI": 0x16,
    "BR":   0x19,
    "LDW":  0x1A,
    "STW":  0x1B,
    "LEA":  0x1C,
    "LDR":  0x1D,
    "STR":  0x1E,
}


# ============================================================
# ALIAS (compatibilidad con el benchmark escrito para LC-3)
# ============================================================
#
# El benchmark del profesor usa LD / ST (LC-3 original).
# En esta ISA esas instrucciones son LDW / STW.

ALIASES = {
    "LD": "LDW",
    "ST": "STW",
}


# ============================================================
# REGISTROS
# ============================================================

REGISTERS = {
    "R0": 0,
    "R1": 1,
    "R2": 2,
    "R3": 3,
    "R4": 4,
    "R5": 5,
    "R6": 6,
    "R7": 7,
}


# ============================================================
# MNEMÓNICOS Y DIRECTIVAS
# ============================================================

MNEMONICS = set(OP.keys()) | set(ALIASES.keys()) | {
    # Pseudo-instrucciones
    "JSRR",
    "RET",
    "NOP",      # = BR nzp 000 (0x0000)
    "RTI",      # variante de JMP (01100 001 000 00000)
    "HALT",
    "GETC",
    "OUT",
    "PUTS",
    "IN",

    # Alias de branch
    "BRN",
    "BRZ",
    "BRP",
    "BRNZ",
    "BRNP",
    "BRZP",
    "BRNZP",
}

DIRECTIVES = {
    ".ORIG",
    ".END",
    ".EXTERNAL",
    ".FILL",
    ".BLKW",
    ".STRINGZ",
}


# ============================================================
# EXCEPCIONES
# ============================================================

class AssemblerError(ValueError):
    pass


# ============================================================
# ESTRUCTURAS
# ============================================================

@dataclass
class ProgramEntry:
    address: int
    kind: str

    text: str = ""
    value: Optional[int] = None

    lineno: int = 0
    size: int = 0


@dataclass
class LinkedSource:
    path: Path
    source: str

    symbols: Dict[str, int | None]

    origin: int
    size: int

    external_references: List[str]

    external_targets: Dict[str, Tuple[Path, str]] = field(
        default_factory=dict
    )

    base: int = 0


# ============================================================
# UTILIDADES
# ============================================================

def parse_int(token: str) -> int:
    """
    Convierte números escritos como:
        123  #123  x1234  0x1234  b1010  0b1010
    """

    token = token.strip()

    if not token:
        raise ValueError("Token vacío")

    lower = token.lower()

    if lower.startswith("0x"):
        return int(token, 16)

    if lower.startswith("0b"):
        return int(token, 2)

    if lower.startswith("x"):
        return int(token[1:], 16)

    if lower.startswith("#"):
        return int(token[1:], 10)

    if lower.startswith("b"):
        return int(token[1:], 2)

    return int(token, 10)


def split_operands(value: str) -> List[str]:
    """
    Separa "R1, R2, #5" en ["R1", "R2", "#5"]
    """

    value = value.strip()

    if not value:
        return []

    return [
        part
        for part in re.split(r"\s*,\s*|\s+", value)
        if part
    ]


def parse_register(token: str) -> int:
    token = token.strip().upper()

    if token not in REGISTERS:
        raise AssemblerError(f"Registro inválido: {token!r}")

    return REGISTERS[token]


def is_register_token(token: str) -> bool:
    """R0, R7, pero también R9 (para dar 'Registro inválido')."""
    return re.fullmatch(r"R\d+", token.strip().upper()) is not None


def fits_signed(value: int, bits: int) -> bool:
    minimum = -(1 << (bits - 1))
    maximum = (1 << (bits - 1)) - 1

    return minimum <= value <= maximum


def encode_signed(value: int, bits: int) -> int:
    if not fits_signed(value, bits):
        raise ValueError(f"Valor {value} no entra en {bits} bits")

    return value & ((1 << bits) - 1)


def condition_mask(mnemonic: str) -> int:
    """
    BR=111  BRN=100  BRZ=010  BRP=001
    BRNZ=110  BRNP=101  BRZP=011  BRNZP=111
    """

    mnemonic = mnemonic.upper()

    if mnemonic == "BR":
        return 0b111

    if not mnemonic.startswith("BR"):
        raise AssemblerError(f"No es una instrucción BR: {mnemonic}")

    suffix = mnemonic[2:]

    mask = 0

    if "N" in suffix:
        mask |= 0b100

    if "Z" in suffix:
        mask |= 0b010

    if "P" in suffix:
        mask |= 0b001

    if mask == 0:
        raise AssemblerError(f"Condición BR inválida: {mnemonic}")

    return mask


# ============================================================
# ASSEMBLER
# ============================================================

class Assembler:

    def __init__(
        self,
        external_addresses: Optional[Dict[str, int]] = None,
        origin_override: Optional[int] = None,
    ):

        self.external_addresses = dict(external_addresses or {})

        self.origin_override = origin_override

        self.reset()

    # --------------------------------------------------------
    # RESET
    # --------------------------------------------------------

    def reset(self):

        self.symbols: Dict[str, int | None] = {}

        self.externals: set[str] = set()

        self.external_references: List[str] = []

        self.entries: List[ProgramEntry] = []

        self.origin = self.origin_override

        self.pc = (
            self.origin_override
            if self.origin_override is not None
            else 0
        )

        self.has_origin = self.origin_override is not None

    # --------------------------------------------------------
    # ASSEMBLE
    # --------------------------------------------------------

    def assemble(self, source: str) -> bytes:

        self.reset()

        self._pass1(source)

        self._pass2()

        return self._build_image()

    # --------------------------------------------------------
    # OUTPUT FORMAT
    # --------------------------------------------------------

    def assemble_string(
        self,
        source: str,
        output_format: str = "hex",
    ) -> str | bytes:

        data = self.assemble(source)

        fmt = output_format.lower()

        if fmt == "obj":
            return data

        if fmt == "hex":
            return " ".join(f"{byte:02X}" for byte in data)

        if fmt == "bin":
            return " ".join(f"{byte:08b}" for byte in data)

        if fmt == "dec":
            return " ".join(str(byte) for byte in data)

        raise AssemblerError(
            f"Formato de salida inválido: {output_format}"
        )

    def assemble_file(
        self,
        path: str | Path,
        output_format: str = "hex",
    ) -> str | bytes:

        source = Path(path).read_text(encoding="utf-8-sig")

        return self.assemble_string(source, output_format)

    # ========================================================
    # ETIQUETAS
    # ========================================================

    def _extract_label(
        self,
        line: str,
    ) -> Tuple[Optional[str], str]:

        line = line.strip()

        if not line:
            return None, ""

        # CASO 1:  LABEL:   /   LABEL: INSTRUCCION

        match = re.match(
            r"^([A-Za-z_][A-Za-z0-9_]*):(.*)$",
            line,
        )

        if match:
            return match.group(1), match.group(2).strip()

        parts = line.split(None, 1)

        first = parts[0]
        first_upper = first.upper()

        # CASO 2: la línea empieza con instrucción o directiva

        if first_upper in MNEMONICS or first_upper in DIRECTIVES:
            return None, line

        # Los registros nunca son etiquetas

        if first_upper in REGISTERS:
            return None, line

        # CASO 3: etiqueta sola (sin ':')

        if len(parts) == 1:

            if re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", first):
                return first, ""

            return None, line

        # CASO 4: etiqueta sin ':' seguida de instrucción/directiva

        if re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", first):

            second = parts[1].split(None, 1)[0].upper()

            if second in MNEMONICS or second in DIRECTIVES:
                return first, parts[1].strip()

        return None, line

    def _validate_label(
        self,
        label: str,
        lineno: int,
    ):
        """
        Comprueba que una etiqueta sea válida y que no esté redefinida.
        """

        if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", label):

            raise AssemblerError(
                f"Línea {lineno}: "
                f"nombre de etiqueta inválido: '{label}'"
            )

        upper_label = label.upper()

        if upper_label in MNEMONICS or upper_label in DIRECTIVES:

            raise AssemblerError(
                f"Línea {lineno}: '{label}' es una palabra reservada"
            )

        # Las etiquetas son case-sensitive en este assembler.

        if label in self.symbols:

            raise AssemblerError(
                f"Línea {lineno}: etiqueta redefinida: '{label}'"
            )

    def _bind_labels(
        self,
        pending: List[str],
        lineno: int,
        align: bool,
    ):
        """
        Asigna las etiquetas pendientes al PC actual.

        Si 'align' es True y el PC es impar, primero inserta un
        byte de relleno (nunca se ejecuta), de modo que las
        etiquetas apunten a la dirección PAR donde realmente
        queda la instrucción / palabra que las sigue.
        """

        if align and (self.pc & 1):

            self.entries.append(
                ProgramEntry(
                    address=self.pc,
                    kind="padding",
                    value=0,
                    text="ALIGN",
                    lineno=lineno,
                    size=1,
                )
            )

            self.pc += 1

        for label in pending:
            self.symbols[label] = self.pc

        pending.clear()

    # ========================================================
    # PASADA 1
    # ========================================================

    def _pass1(self, source: str):

        saw_end = False

        # Etiquetas que esperan a la siguiente instrucción/dato
        # (así quedan alineadas junto con ella).
        pending: List[str] = []

        for lineno, raw_line in enumerate(
            source.splitlines(),
            start=1,
        ):

            line = raw_line.split(";", 1)[0].strip()

            if not line:
                continue

            label, remainder = self._extract_label(line)

            if label:

                self._validate_label(label, lineno)

                if label in pending:
                    raise AssemblerError(
                        f"Línea {lineno}: "
                        f"etiqueta redefinida: '{label}'"
                    )

                if not self.has_origin:
                    raise AssemblerError(
                        f"Línea {lineno}: etiqueta antes de .ORIG"
                    )

                pending.append(label)

            if not remainder:
                continue

            parts = remainder.split(None, 1)

            mnemonic = parts[0].upper()

            args = parts[1].strip() if len(parts) > 1 else ""

            # =================================================
            # .ORIG
            # =================================================

            if mnemonic == ".ORIG":

                if self.has_origin and self.origin_override is None:
                    raise AssemblerError(
                        f"Línea {lineno}: múltiples .ORIG"
                    )

                if not args:
                    raise AssemblerError(
                        f"Línea {lineno}: .ORIG requiere una dirección"
                    )

                address = parse_int(args)

                if not 0 <= address <= 0xFFFF:
                    raise AssemblerError(
                        f"Línea {lineno}: .ORIG fuera de rango"
                    )

                if address & 1:
                    raise AssemblerError(
                        f"Línea {lineno}: "
                        ".ORIG debe ser una dirección par"
                    )

                if self.origin_override is not None:
                    self.pc = self.origin_override
                else:
                    self.pc = address

                self.origin = self.pc

                self.has_origin = True

                self._bind_labels(pending, lineno, align=False)

                continue

            # =================================================
            # TODO LO DEMÁS REQUIERE .ORIG
            # =================================================

            if not self.has_origin:
                raise AssemblerError(
                    f"Línea {lineno}: "
                    "el programa debe comenzar con .ORIG"
                )

            # =================================================
            # .END
            # =================================================

            if mnemonic == ".END":

                self._bind_labels(pending, lineno, align=False)

                saw_end = True

                break

            # =================================================
            # .EXTERNAL
            # =================================================

            if mnemonic == ".EXTERNAL":

                self._bind_labels(pending, lineno, align=False)

                names = re.split(r"[\s,]+", args) if args else []

                for name in names:

                    if name:
                        self.externals.add(name)
                        self.external_references.append(name)

                continue

            # =================================================
            # .FILL   (palabra de 16 bits -> dirección par)
            # =================================================

            if mnemonic == ".FILL":

                if not args:
                    raise AssemblerError(
                        f"Línea {lineno}: .FILL requiere un valor"
                    )

                self._bind_labels(pending, lineno, align=True)

                self.entries.append(
                    ProgramEntry(
                        address=self.pc,
                        kind="fill",
                        text=args,
                        lineno=lineno,
                        size=2,
                    )
                )

                self.pc += 2

                continue

            # =================================================
            # .BLKW   (palabras de 16 bits -> dirección par)
            # =================================================

            if mnemonic == ".BLKW":

                if not args:
                    raise AssemblerError(
                        f"Línea {lineno}: .BLKW requiere una cantidad"
                    )

                count = self._resolve_numeric_expr(args, lineno)

                if count < 0:
                    raise AssemblerError(
                        f"Línea {lineno}: .BLKW no puede ser negativo"
                    )

                self._bind_labels(pending, lineno, align=True)

                size = count * 2

                self.entries.append(
                    ProgramEntry(
                        address=self.pc,
                        kind="blkw",
                        text=str(count),
                        lineno=lineno,
                        size=size,
                    )
                )

                self.pc += size

                continue

            # =================================================
            # .STRINGZ   (bytes; comienza en dirección par)
            # =================================================

            if mnemonic == ".STRINGZ":

                payload = self._parse_string_literal(args, lineno)

                # Se alinea a dirección par: LEA direcciona en palabras.
                self._bind_labels(pending, lineno, align=True)

                size = len(payload) + 1

                self.entries.append(
                    ProgramEntry(
                        address=self.pc,
                        kind="stringz",
                        text=payload,
                        lineno=lineno,
                        size=size,
                    )
                )

                self.pc += size

                continue

            # =================================================
            # INSTRUCCIÓN
            # =================================================

            if mnemonic not in MNEMONICS:
                raise AssemblerError(
                    f"Línea {lineno}: "
                    f"instrucción desconocida '{mnemonic}'"
                )

            # Las instrucciones (16 bits) deben comenzar en dirección
            # par. Si hay datos de a byte antes, se inserta relleno
            # (no se ejecuta). Las etiquetas pendientes se asignan
            # DESPUÉS de alinear, para que apunten a la instrucción.

            self._bind_labels(pending, lineno, align=True)

            self.entries.append(
                ProgramEntry(
                    address=self.pc,
                    kind="instruction",
                    text=remainder,
                    lineno=lineno,
                    size=2,
                )
            )

            self.pc += 2

            if self.pc > MEMORY_SIZE:
                raise AssemblerError(
                    f"Línea {lineno}: "
                    "el programa excede los 64 KiB de memoria"
                )

        if not self.has_origin:
            raise AssemblerError("Falta .ORIG")

        if not saw_end:
            raise AssemblerError("Falta .END")

    # ========================================================
    # PASADA 2
    # ========================================================

    def _pass2(self):

        final_entries: List[ProgramEntry] = []

        def add_byte(address: int, value: int, lineno: int):
            final_entries.append(
                ProgramEntry(
                    address=address,
                    kind="byte",
                    value=value & 0xFF,
                    lineno=lineno,
                    size=1,
                )
            )

        for entry in self.entries:

            # Relleno de alineación

            if entry.kind == "padding":

                add_byte(entry.address, 0, entry.lineno)

            # .FILL  (big endian)

            elif entry.kind == "fill":

                value = self._resolve_numeric_expr(
                    entry.text,
                    entry.lineno,
                )

                value &= MASK_16

                add_byte(entry.address, value >> 8, entry.lineno)
                add_byte(entry.address + 1, value, entry.lineno)

            # .BLKW

            elif entry.kind == "blkw":

                for i in range(int(entry.text)):

                    address = entry.address + i * 2

                    add_byte(address, 0, entry.lineno)
                    add_byte(address + 1, 0, entry.lineno)

            # .STRINGZ

            elif entry.kind == "stringz":

                payload = entry.text

                for i, char in enumerate(payload):
                    add_byte(entry.address + i, ord(char), entry.lineno)

                add_byte(
                    entry.address + len(payload),
                    0,
                    entry.lineno,
                )

            # INSTRUCCIÓN (16 bits, big endian)

            elif entry.kind == "instruction":

                encoded = self._encode_instruction(
                    entry.text,
                    entry.lineno,
                    entry.address,
                )

                add_byte(entry.address, encoded >> 8, entry.lineno)
                add_byte(entry.address + 1, encoded, entry.lineno)

        self.entries = final_entries

    # ========================================================
    # EXPRESIONES
    # ========================================================

    def _resolve_single_atom(
        self,
        atom: str,
        lineno: int,
    ) -> int:

        atom = atom.strip()

        if not atom:
            return 0

        # Símbolo externo ya resuelto

        if atom in self.external_addresses:
            return self.external_addresses[atom]

        # Símbolo externo aún no resuelto

        if atom in self.externals:
            raise AssemblerError(
                f"Línea {lineno}: símbolo externo no resuelto: {atom}"
            )

        # Símbolo local

        if atom in self.symbols:

            value = self.symbols[atom]

            if value is None:
                raise AssemblerError(
                    f"Línea {lineno}: símbolo no resuelto: {atom}"
                )

            return int(value)

        # Número

        try:
            return parse_int(atom)

        except ValueError as exc:
            raise AssemblerError(
                f"Línea {lineno}: literal o símbolo inválido '{atom}'"
            ) from exc

    def _resolve_numeric_expr(
        self,
        expr: str,
        lineno: int,
    ) -> int:

        expr = expr.strip()

        if not expr:
            return 0

        # 1) Nombre completo de símbolo externo.
        #    Los externos con formato MODULO-SIMBOLO contienen '-',
        #    así que hay que consultarlos ANTES de partir por +/-.

        if expr in self.external_addresses:
            return self.external_addresses[expr]

        if expr in self.externals:
            raise AssemblerError(
                f"Línea {lineno}: símbolo externo no resuelto: {expr}"
            )

        # 2) Etiqueta completa (evita que una etiqueta como 'x1' o
        #    'b101' se interprete como número hexa/binario).

        local = self.symbols.get(expr)

        if local is not None:
            return int(local)

        # 3) Número simple

        try:
            return parse_int(expr)
        except ValueError:
            pass

        # 4) Expresiones: LABEL + 4, LABEL - 4, 4 + LABEL,
        #    MODULO-SIMBOLO + 2, etc.
        #    Los nombres externos con '-' se protegen antes de partir.

        protected: Dict[str, str] = {}

        dashed = sorted(
            (
                name
                for name in (
                    set(self.externals)
                    | set(self.external_addresses)
                )
                if "-" in name
            ),
            key=len,
            reverse=True,
        )

        for index, name in enumerate(dashed):

            if name in expr:
                key = f"__EXT{index}__"
                protected[key] = name
                expr = expr.replace(name, key)

        def atom_value(token: str) -> int:
            token = token.strip()
            return self._resolve_single_atom(
                protected.get(token, token),
                lineno,
            )

        parts = re.split(r"([+-])", expr)

        current = atom_value(parts[0])

        index = 1

        while index < len(parts):

            operator = parts[index]

            right = atom_value(parts[index + 1])

            if operator == "+":
                current += right
            else:
                current -= right

            index += 2

        return current

    # ========================================================
    # STRING
    # ========================================================

    def _parse_string_literal(
        self,
        value: str,
        lineno: int,
    ) -> str:

        value = value.strip()

        if len(value) < 2 or value[0] != '"' or value[-1] != '"':
            raise AssemblerError(
                f"Línea {lineno}: "
                ".STRINGZ debe utilizar comillas dobles"
            )

        try:
            return ast.literal_eval(value)

        except (SyntaxError, ValueError) as exc:
            raise AssemblerError(
                f"Línea {lineno}: cadena inválida"
            ) from exc

    # ========================================================
    # RESOLUCIÓN DE DIRECCIONES
    # ========================================================

    def _resolve_address(
        self,
        token: str,
        lineno: int,
    ) -> int:

        return self._resolve_numeric_expr(token, lineno)

    # ========================================================
    # PC RELATIVE
    # ========================================================

    def _pc_offset(
        self,
        target: int,
        pc: int,
        bits: int,
        mnemonic: str,
        lineno: int,
        scale: int = 1,
    ) -> int:
        """
        scale = 1 -> el offset se expresa en BYTES
        scale = 2 -> el offset se expresa en PALABRAS (el destino
                     debe ser una dirección par)
        """

        # PC después del fetch = PC + 2
        # distancia en bytes = destino - (PC + 2)

        distance = target - (pc + 2)

        if distance % scale != 0:
            raise AssemblerError(
                f"Línea {lineno}: "
                f"{mnemonic} requiere un destino en dirección par "
                f"(destino x{target & 0xFFFF:04X})"
            )

        offset = distance // scale

        minimum = -(1 << (bits - 1))
        maximum = (1 << (bits - 1)) - 1

        if offset < minimum or offset > maximum:
            unit = "palabras" if scale == 2 else "bytes"
            raise AssemblerError(
                f"Línea {lineno}: "
                f"{mnemonic} offset {offset} {unit} "
                f"fuera de rango [{minimum}, {maximum}]"
            )

        return encode_signed(offset, bits)

    def _pc_offset_ext(
        self,
        name: str,
        target: int,
        pc: int,
        scale: int,
        mnemonic: str,
        lineno: int,
    ) -> Tuple[int, int]:
        """
        Offset PC-relative de 9 bits (-256..255).

        Devuelve (opcode, low8): el bit 8 (signo) se codifica
        eligiendo el opcode base o el extendido.
        """

        encoded = self._pc_offset(
            target, pc, 9, mnemonic, lineno, scale=scale
        )

        opcode = (
            OP_EXT[name] if (encoded >> 8) & 1 else OP[name]
        )

        return opcode, encoded & 0xFF

    # ========================================================
    # INMEDIATOS
    # ========================================================

    def _immediate(
        self,
        token: str,
        bits: int,
        mnemonic: str,
        lineno: int,
    ) -> int:

        value = self._resolve_numeric_expr(token, lineno)

        if not fits_signed(value, bits):

            minimum = -(1 << (bits - 1))
            maximum = (1 << (bits - 1)) - 1

            raise AssemblerError(
                f"Línea {lineno}: "
                f"inmediato {value} fuera de rango para {mnemonic}. "
                f"Rango: [{minimum}, {maximum}]"
            )

        return encode_signed(value, bits)

    # ========================================================
    # ADD / AND / SUB / MUL / DIV / MOD
    # ========================================================

    def _encode_three_operand(
        self,
        mnemonic: str,
        args: List[str],
        lineno: int,
    ) -> int:

        if len(args) != 3:
            raise AssemblerError(
                f"Línea {lineno}: "
                f"{mnemonic} requiere DR, SR1, SR2/imm4"
            )

        dr = parse_register(args[0])

        sr1 = parse_register(args[1])

        third = args[2]

        base = (OP[mnemonic] << 11) | (dr << 8) | (sr1 << 5)

        # Modo registro

        if is_register_token(third):
            return base | parse_register(third)

        # Modo inmediato

        if mnemonic == "ADDC":
            raise AssemblerError(
                f"Línea {lineno}: ADDC solo admite registros (DR, SR1, SR2)"
            )

        if mnemonic == "ADD":

            # ADD con inmediato -> ADDI (imm5, -16..15)

            imm = self._immediate(third, 5, "ADD", lineno)

            return (
                (OP_EXT["ADDI"] << 11)
                | (dr << 8)
                | (sr1 << 5)
                | imm
            )

        imm = self._immediate(third, 4, mnemonic, lineno)

        return base | (1 << 4) | imm

    # ========================================================
    # ENCODER PRINCIPAL
    # ========================================================

    def _encode_instruction(
        self,
        instruction: str,
        lineno: int,
        pc: int,
    ) -> int:

        tokens = split_operands(instruction)

        if not tokens:
            return NOP

        mnemonic = tokens[0].upper()

        # LD -> LDW, ST -> STW
        mnemonic = ALIASES.get(mnemonic, mnemonic)

        args = tokens[1:]

        # ====================================================
        # BR
        # ====================================================

        if mnemonic.startswith("BR"):

            if len(args) != 1:
                raise AssemblerError(
                    f"Línea {lineno}: {mnemonic} requiere un destino"
                )

            target = self._resolve_address(args[0], lineno)

            # Offset de 9 bits en PALABRAS (opcode base/extendido)
            opcode, low8 = self._pc_offset_ext(
                "BR", target, pc, 2, mnemonic, lineno
            )

            return (
                (opcode << 11)
                | (condition_mask(mnemonic) << 8)
                | low8
            )

        # ====================================================
        # ADD AND SUB MUL DIV MOD
        # ====================================================

        if mnemonic in {"ADD", "ADDC", "AND", "SUB", "MUL", "MULH", "DIV"}:
            return self._encode_three_operand(mnemonic, args, lineno)

        # ====================================================
        # SHL / SHR
        # ====================================================

        if mnemonic in {"SHL", "SHR"}:

            if len(args) != 3:
                raise AssemblerError(
                    f"Línea {lineno}: {mnemonic} requiere DR, SR1, imm4"
                )

            dr = parse_register(args[0])

            sr = parse_register(args[1])

            # El desplazamiento es SIN signo (0..15): se necesitan
            # shifts de 8 o más para formatos de punto fijo (Q7.8, etc.).
            amount = self._resolve_numeric_expr(args[2], lineno)

            if not 0 <= amount <= 15:
                raise AssemblerError(
                    f"Línea {lineno}: "
                    f"desplazamiento {amount} fuera de rango "
                    f"para {mnemonic}. Rango: [0, 15]"
                )

            return (
                (OP[mnemonic] << 11)
                | (dr << 8)
                | (sr << 5)
                | (1 << 4)
                | amount
            )

        # ====================================================
        # LDW STW LDBL STBL LDBH LEA STBH   (PC-relative, 8 bits)
        # ====================================================

        if mnemonic in {
            "LDW",
            "STW",
            "LDBL",
            "STBL",
            "LDBH",
            "LEA",
            "STBH",
        }:

            if len(args) != 2:
                raise AssemblerError(
                    f"Línea {lineno}: "
                    f"{mnemonic} requiere registro y destino"
                )

            reg = parse_register(args[0])

            target = self._resolve_address(args[1], lineno)

            # LDW / STW / LEA: offset de 9 bits en PALABRAS
            # (el destino debe ser par).
            if mnemonic in {"LDW", "STW", "LEA"}:

                opcode, low8 = self._pc_offset_ext(
                    mnemonic, target, pc, 2, mnemonic, lineno
                )

                return (opcode << 11) | (reg << 8) | low8

            # Accesos a byte: offset de 8 bits en BYTES.
            offset = self._pc_offset(
                target, pc, 8, mnemonic, lineno, scale=1
            )

            return (OP[mnemonic] << 11) | (reg << 8) | offset

        # ====================================================
        # LDR STR LDBR STRB   (base + offset5)
        # ====================================================

        if mnemonic in {"LDR", "STR", "LDBR", "STRB"}:

            if len(args) != 3:
                raise AssemblerError(
                    f"Línea {lineno}: "
                    f"{mnemonic} requiere registro, BaseR, offset5"
                )

            reg = parse_register(args[0])

            base = parse_register(args[1])

            if mnemonic in {"LDR", "STR"}:

                # offset de 6 bits en PALABRAS (-32..31);
                # el bit 5 va en el opcode. Dirección = BaseR + 2*offset
                encoded = self._immediate(args[2], 6, mnemonic, lineno)

                opcode = (
                    OP_EXT[mnemonic]
                    if (encoded >> 5) & 1
                    else OP[mnemonic]
                )

                return (
                    (opcode << 11)
                    | (reg << 8)
                    | (base << 5)
                    | (encoded & 0x1F)
                )

            offset = self._immediate(args[2], 5, mnemonic, lineno)

            return (
                (OP[mnemonic] << 11)
                | (reg << 8)
                | (base << 5)
                | offset
            )

        # ====================================================
        # JSR
        # ====================================================

        if mnemonic == "JSR":

            if len(args) != 1:
                raise AssemblerError(
                    f"Línea {lineno}: JSR requiere un destino"
                )

            target = self._resolve_address(args[0], lineno)

            # Offset en PALABRAS
            offset = self._pc_offset(
                target, pc, 10, "JSR", lineno, scale=2
            )

            return (OP["JSR"] << 11) | (1 << 10) | offset

        # ====================================================
        # JSRR   00100 | 0 | 00 | BaseR | 00000
        # ====================================================

        if mnemonic == "JSRR":

            if len(args) != 1:
                raise AssemblerError(
                    f"Línea {lineno}: JSRR requiere BaseR"
                )

            base = parse_register(args[0])

            return (OP["JSR"] << 11) | (base << 5)

        # ====================================================
        # JMP   01100 | 000 | BaseR | 00000
        # ====================================================

        if mnemonic == "JMP":

            if len(args) != 1:
                raise AssemblerError(
                    f"Línea {lineno}: JMP requiere BaseR"
                )

            base = parse_register(args[0])

            return (OP["JMP"] << 11) | (base << 5)

        # ====================================================
        # RET  (= JMP R7)
        # ====================================================

        if mnemonic == "RET":

            if args:
                raise AssemblerError(
                    f"Línea {lineno}: RET no lleva operandos"
                )

            return (OP["JMP"] << 11) | (7 << 5)

        # ====================================================
        # RTI   01100 | 001 | 000 | 00000
        #       (variante de JMP: el campo DR=001 la distingue;
        #        no gasta un opcode propio)
        # ====================================================

        if mnemonic == "RTI":

            if args:
                raise AssemblerError(
                    f"Línea {lineno}: RTI no lleva operandos"
                )

            return (OP["JMP"] << 11) | (1 << 8)

        # ====================================================
        # NOT   01001 | DR | SR | 11111
        # ====================================================

        if mnemonic == "NOT":

            if len(args) != 2:
                raise AssemblerError(
                    f"Línea {lineno}: NOT requiere DR, SR"
                )

            dr = parse_register(args[0])

            sr = parse_register(args[1])

            return (OP["NOT"] << 11) | (dr << 8) | (sr << 5) | 0x1F

        # ====================================================
        # NOP
        # ====================================================

        if mnemonic == "NOP":

            if args:
                raise AssemblerError(
                    f"Línea {lineno}: NOP no lleva operandos"
                )

            return NOP

        # ====================================================
        # TRAP
        # ====================================================

        if mnemonic == "TRAP":

            if len(args) != 1:
                raise AssemblerError(
                    f"Línea {lineno}: TRAP requiere un vector"
                )

            vector = self._resolve_numeric_expr(args[0], lineno)

            if not 0 <= vector <= 0x7F:
                raise AssemblerError(
                    f"Línea {lineno}: "
                    "vector TRAP fuera de rango 0..127"
                )

            return (OP["TRAP"] << 11) | vector

        # ====================================================
        # HALT  (TRAP x25)
        # ====================================================

        if mnemonic == "HALT":
            return (OP["TRAP"] << 11) | 0x25

        # ====================================================
        # ALIAS DE TRAP
        # ====================================================

        if mnemonic in {"GETC", "OUT", "PUTS", "IN"}:

            vectors = {
                "GETC": 0x20,
                "OUT":  0x21,
                "PUTS": 0x22,
                "IN":   0x23,
            }

            return (OP["TRAP"] << 11) | vectors[mnemonic]

        raise AssemblerError(
            f"Línea {lineno}: "
            f"instrucción no soportada '{mnemonic}'"
        )

    # ========================================================
    # CONSTRUIR IMAGEN
    # ========================================================

    def _build_image(self) -> bytes:

        if self.origin is None:
            raise AssemblerError("Falta .ORIG")

        image = bytearray()

        # Primeros dos bytes: dirección de origen

        image.append((self.origin >> 8) & 0xFF)
        image.append(self.origin & 0xFF)

        # Código y datos

        for entry in self.entries:

            if entry.value is None:
                continue

            image.append(entry.value & 0xFF)

        return bytes(image)


# ============================================================
# FUNCIONES DE UTILIDAD
# ============================================================

def assemble_source(
    source: str,
    output_format: str = "hex",
) -> str | bytes:

    return Assembler().assemble_string(source, output_format)


def assemble_file(
    path: str | Path,
    output_format: str = "hex",
) -> str | bytes:

    return Assembler().assemble_file(path, output_format)


# ============================================================
# LINKER
# ============================================================

class ProjectLinker:

    def __init__(
        self,
        module_dir: str | Path,
    ):

        self.module_dir = Path(module_dir)

        self.module_files = (
            sorted(self.module_dir.rglob("*.asm"))
            if self.module_dir.is_dir()
            else []
        )

        self.files_by_stem: Dict[str, List[Path]] = {}

        for path in self.module_files:

            self.files_by_stem.setdefault(
                path.stem.casefold(),
                [],
            ).append(path)

        self.units: Dict[Path, LinkedSource] = {}

        self.unit_order: List[LinkedSource] = []

    # ========================================================

    def assemble_file(
        self,
        source_path: str | Path,
        output_format: str = "hex",
    ) -> str | bytes:

        root_path = Path(source_path).resolve()

        pending = deque([(root_path, True)])

        queued_paths = {root_path}

        # ----------------------------------------------------
        # Descubrir módulos
        # ----------------------------------------------------

        while pending:

            path, is_root = pending.popleft()

            unit = self._load_unit(path, is_root)

            for reference in unit.external_references:

                module_name, separator, symbol = reference.partition("-")

                if separator:

                    if not module_name or not symbol:
                        raise AssemblerError(
                            f".EXTERNAL inválido: {reference!r}. "
                            "Se esperaba MODULO-SIMBOLO."
                        )

                    module_path = self._find_module(module_name, symbol)

                else:

                    module_path = self._find_exporting_module(reference)

                    symbol = reference

                module_path = module_path.resolve()

                unit.external_targets[reference] = (module_path, symbol)

                if module_path not in queued_paths:

                    queued_paths.add(module_path)

                    pending.append((module_path, False))

        # ----------------------------------------------------
        # Asignar direcciones
        # ----------------------------------------------------

        root = self.units[root_path]

        root.base = root.origin

        next_address = root.base + root.size

        if next_address > MEMORY_SIZE:
            raise AssemblerError(
                "El programa principal excede los 64 KiB"
            )

        for unit in self.unit_order:

            if unit is root:
                continue

            # Los módulos también deben comenzar en dirección par.

            if next_address & 1:
                next_address += 1

            unit.base = next_address

            next_address += unit.size

            if next_address > MEMORY_SIZE:
                raise AssemblerError(
                    "El programa enlazado excede los 64 KiB"
                )

        # ----------------------------------------------------
        # Generar imagen final
        # ----------------------------------------------------

        output = bytearray()

        # Primeros dos bytes: origen del programa principal.

        output.append((root.base >> 8) & 0xFF)
        output.append(root.base & 0xFF)

        current_address = root.base

        for unit in self.unit_order:

            if unit.base < current_address:
                raise AssemblerError("Solapamiento de módulos")

            # Relleno entre módulos.

            if unit.base > current_address:

                output.extend(b"\x00" * (unit.base - current_address))

                current_address = unit.base

            assembler = Assembler(
                external_addresses=self._external_addresses(unit),
                origin_override=unit.base,
            )

            data = assembler.assemble(unit.source)

            # data[0:2] = origin (ya escrito para todo el proyecto)

            output.extend(data[2:])

            current_address += len(data) - 2

        return self._format_output(bytes(output), output_format)

    # ========================================================

    def _format_output(
        self,
        data: bytes,
        output_format: str,
    ) -> str | bytes:

        fmt = output_format.lower()

        if fmt == "obj":
            return data

        if fmt == "hex":
            return " ".join(f"{byte:02X}" for byte in data)

        if fmt == "bin":
            return " ".join(f"{byte:08b}" for byte in data)

        if fmt == "dec":
            return " ".join(str(byte) for byte in data)

        raise AssemblerError(
            f"Formato de salida inválido: {output_format}"
        )

    # ========================================================

    def _load_unit(
        self,
        path: Path,
        is_root: bool,
    ) -> LinkedSource:

        resolved = path.resolve()

        if resolved in self.units:
            return self.units[resolved]

        source = resolved.read_text(encoding="utf-8-sig")

        analyzer = Assembler(
            origin_override=None if is_root else 0
        )

        analyzer._pass1(source)

        if analyzer.origin is None:
            raise AssemblerError(f"Falta .ORIG en {resolved}")

        unit = LinkedSource(
            path=resolved,
            source=source,
            symbols=dict(analyzer.symbols),
            origin=analyzer.origin,
            size=analyzer.pc - analyzer.origin,
            external_references=list(analyzer.external_references),
        )

        self.units[resolved] = unit

        self.unit_order.append(unit)

        return unit

    # ========================================================

    def _find_module(
        self,
        module_name: str,
        symbol: str,
    ) -> Path:

        candidates = self.files_by_stem.get(module_name.casefold(), [])

        if not candidates:

            candidates = self.files_by_stem.get(
                f"g27_{module_name}".casefold(),
                [],
            )

        if len(candidates) > 1:
            raise AssemblerError(
                f"Nombre de módulo ambiguo: {module_name}"
            )

        if candidates:

            candidate = candidates[0]

            if not self._defines_label(candidate, symbol):
                raise AssemblerError(
                    f"El módulo {candidate.name} no define '{symbol}'"
                )

            return candidate

        matches = [
            path
            for path in self.module_files
            if self._defines_label(path, symbol)
        ]

        if len(matches) == 1:
            return matches[0]

        if not matches:
            raise AssemblerError(
                f"No se encontró el módulo {module_name} "
                f"ni una definición de {symbol}"
            )

        raise AssemblerError(
            f"El símbolo {symbol} aparece en varios módulos"
        )

    # ========================================================

    def _find_exporting_module(
        self,
        symbol: str,
    ) -> Path:

        matches = [
            path
            for path in self.module_files
            if self._defines_label(path, symbol)
        ]

        if len(matches) == 1:
            return matches[0]

        if not matches:
            raise AssemblerError(
                f"No se encontró una definición de {symbol}"
            )

        raise AssemblerError(
            f"El símbolo externo {symbol} aparece en varios módulos"
        )

    # ========================================================

    @staticmethod
    def _defines_label(
        path: Path,
        symbol: str,
    ) -> bool:
        """
        True si el archivo define la etiqueta 'symbol'.

        Usa el mismo criterio que el ensamblador (_extract_label),
        así que detecta:  'LABEL:',  'LABEL' sola en su línea,
        y  'LABEL INSTRUCCION'.
        """

        source = path.read_text(encoding="utf-8-sig")

        helper = Assembler()

        for raw in source.splitlines():

            line = raw.split(";", 1)[0].strip()

            if not line:
                continue

            label, _ = helper._extract_label(line)

            if label == symbol:
                return True

        return False

    # ========================================================

    def _external_addresses(
        self,
        unit: LinkedSource,
    ) -> Dict[str, int]:

        addresses: Dict[str, int] = {}

        for reference, (target_path, symbol) in (
            unit.external_targets.items()
        ):

            target = self.units[target_path]

            symbol_address = target.symbols.get(symbol)

            if symbol_address is None:
                raise AssemblerError(
                    f"El módulo {target.path.name} no define '{symbol}'"
                )

            address = (
                target.base
                + int(symbol_address)
                - target.origin
            )

            if not 0 <= address <= 0xFFFF:
                raise AssemblerError(
                    f"La dirección enlazada de {reference} "
                    "está fuera de memoria"
                )

            addresses[reference] = address

        return addresses


# ============================================================
# FUNCIÓN PARA PROYECTOS
# ============================================================

def assemble_project_file(
    path: str | Path,
    output_format: str = "hex",
    module_dir: str | Path | None = None,
) -> str | bytes:

    source_path = Path(path)

    if module_dir is None:
        module_dir = source_path.parent / "lib"

    linker = ProjectLinker(module_dir)

    return linker.assemble_file(source_path, output_format)


# ============================================================
# MAIN
# ============================================================

def main(
    argv: Optional[Sequence[str]] = None,
) -> int:

    parser = argparse.ArgumentParser(
        description=(
            "Ensamblador para la ISA personalizada del Laboratorio 3c"
        )
    )

    parser.add_argument(
        "source",
        type=str,
        help="Archivo .asm",
    )

    parser.add_argument(
        "--format",
        choices=["hex", "bin", "dec", "obj"],
        default="hex",
        help="Formato de salida",
    )

    parser.add_argument(
        "--link-dir",
        type=str,
        help="Carpeta con módulos .asm. Por defecto: ./lib",
    )

    args = parser.parse_args(argv)

    source_path = Path(args.source)

    output_suffix = {
        "hex": ".hex",
        "bin": ".bin",
        "dec": ".dec",
        "obj": ".obj",
    }[args.format]

    output_path = source_path.with_suffix(output_suffix)

    try:

        output = assemble_project_file(
            source_path,
            args.format,
            args.link_dir,
        )

    except FileNotFoundError as exc:

        print(
            f"ERROR: archivo no encontrado: {exc.filename}",
            file=sys.stderr,
        )

        return 1

    except AssemblerError as exc:

        print(f"ERROR: {exc}", file=sys.stderr)

        return 1

    try:

        if isinstance(output, bytes):
            output_path.write_bytes(output)

        else:
            output_path.write_text(output + "\n", encoding="ascii")

    except OSError as exc:

        print(
            f"ERROR: no se pudo escribir el archivo: {exc}",
            file=sys.stderr,
        )

        return 1

    print(f"Archivo generado: {output_path}")

    return 0


# ============================================================
# EJECUCIÓN
# ============================================================

if __name__ == "__main__":

    raise SystemExit(main())
