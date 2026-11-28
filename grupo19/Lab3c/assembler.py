"""Assembler and recursive linker for the 16-bit ISA in NUEVA_ISA.md.

Usage:
    python assembler.py program.asm --format bin
    python assembler.py program.asm --format hex -o program.hex
    python assembler.py program.asm --format asm
    python assembler.py program.asm --format hex --map program.map

The binary format starts with little-endian .ORIG and .STACK words, followed by
the linked byte-addressed image. The ASM format is a linked source listing.
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


OPCODES = {
    "BR": 0x00,
    "ALU": 0x01,
    "LOG": 0x02,
    "ANDI": 0x03,
    "UNARY": 0x04,
    "ADDI": 0x05,
    "MOVI": 0x06,
    "MOVH": 0x07,
    "SHL": 0x08,
    "SHR": 0x09,
    "ROT": 0x0A,
    "LDBL": 0x0B,
    "LDBS": 0x0C,
    "LDBH": 0x0D,
    "STBL": 0x0E,
    "STBH": 0x0F,
    "LDW": 0x10,
    "STW": 0x11,
    "LDPC": 0x12,
    "STPC": 0x13,
    "LEA": 0x14,
    "JSR": 0x15,
    "JR": 0x16,
    "STACK": 0x17,
    "TRAP": 0x18,
    "SHIFTV": 0x19,
    "JMPM": 0x1A,
    "JSRM": 0x1B,
    "LDPM": 0x1C,
    "STPM": 0x1D,
    "LDW16": 0x1E,
    "STW16": 0x1F,
}

DIRECTIVES = {
    ".ORIG", ".END", ".EXTERNAL", ".FILL", ".BLKW", ".BLKB",
    ".BYTE", ".STRINGZ", ".STACK",
}

BRANCH_CONDITIONS = {
    "BR": 0,
    "BRNZP": 0,
    "BRALWAYS": 0,
    "BRN": 1,
    "BRZ": 2,
    "BRP": 3,
    "BRNZ": 4,
    "BRNP": 5,
    "BRZP": 6,
    "BRNEVER": 7,
    "BRC": 8,
    "BRNC": 9,
    "BRV": 10,
    "BRNV": 11,
    "BRLT": 12,
    "BRGE": 13,
    "BRGT": 14,
    "BRLE": 15,
}
INSTRUCTIONS = set(BRANCH_CONDITIONS) | {
    "ADD", "SUB", "ADC", "SBC", "AND", "OR", "XOR", "CMP",
    "ANDI", "ADDI", "NOT", "NEG", "MOVI", "MOVH", "MOV", "CLR",
    "INC", "DEC", "LI", "SHL", "LSR", "ASR", "RRC", "RLC",
    "SHLV", "SRLV", "SRAV", "ROLV",
    "LDBL", "LDBS", "LDBH", "STBL", "STBH", "LDW", "STW",
    "LDW16", "STW16", "LDPC", "STPC", "LDPM", "STPM", "LEA",
    "LD", "ST", "LDR", "STR", "JSR", "JSRR", "JMP", "RET",
    "JMPM", "JSRM", "PUSHM", "POPM", "POPR", "PUSH", "POP",
    "TRAP", "GETC", "OUT", "PUTS", "IN", "HALT", "NOP",
}
TRAPS = {"GETC": 0x20, "OUT": 0x21, "PUTS": 0x22, "IN": 0x23, "HALT": 0x25}
MASK16 = 0xFFFF
MEMORY_SIZE = 1 << 16
DEFAULT_STACK = 0xFFFE


class AssemblyError(Exception):
    """Raised when source cannot be assembled or linked."""


@dataclass
class Statement:
    path: Path
    scope: str
    line_number: int
    source: str
    label: str | None
    op: str | None
    args: tuple[str, ...]
    raw_args: str
    address: int = 0
    size: int = 0
    padding: int = 0
    relaxed: str | None = None

    def fail(self, message: str) -> AssemblyError:
        return AssemblyError(f"{self.path}:{self.line_number}: {message}")


@dataclass(frozen=True)
class External:
    alias: str
    symbol: str
    path: Path


@dataclass
class AssemblyImage:
    origin: int
    stack: int
    image: bytes
    listing: str
    symbols: dict[str, int]
    code_bytes: int = 0
    data_bytes: int = 0
    padding_bytes: int = 0
    modules: int = 1
    symbol_map: str = ""

    def object_bytes(self) -> bytes:
        return self.origin.to_bytes(2, "little") + self.stack.to_bytes(2, "little") + self.image


def _norm(name: str) -> str:
    return name.strip().rstrip(":").casefold()


def _strip_comment(line: str) -> str:
    quote: str | None = None
    escaped = False
    for index, character in enumerate(line):
        if escaped:
            escaped = False
        elif character == "\\" and quote:
            escaped = True
        elif quote:
            if character == quote:
                quote = None
        elif character in {"'", '"'}:
            quote = character
        elif character == ";":
            return line[:index]
    return line


def _split_operands(raw: str, op: str) -> tuple[str, ...]:
    if not raw.strip():
        return ()
    if op == ".STRINGZ":
        return (raw.strip(),)

    result: list[str] = []
    current: list[str] = []
    quote: str | None = None
    escaped = False
    braces = 0
    for character in raw:
        if escaped:
            current.append(character)
            escaped = False
        elif character == "\\" and quote:
            current.append(character)
            escaped = True
        elif quote:
            current.append(character)
            if character == quote:
                quote = None
        elif character in {"'", '"'}:
            current.append(character)
            quote = character
        elif character == "{":
            braces += 1
            current.append(character)
        elif character == "}":
            braces -= 1
            current.append(character)
        elif (character == "," or character.isspace()) and braces == 0:
            if current:
                result.append("".join(current).strip())
                current.clear()
        else:
            current.append(character)
    if current:
        result.append("".join(current).strip())
    return tuple(result)


def _parse_line(path: Path, scope: str, line_number: int, line: str) -> Statement | None:
    code = _strip_comment(line).strip()
    if not code:
        return None

    label: str | None = None
    if ":" in code.split()[0]:
        token, _, remainder = code.partition(":")
        label = token.strip()
        code = remainder.strip()
        if not code:
            return Statement(path, scope, line_number, line.rstrip(), label, None, (), "")

    match = re.match(r"^(\S+)(?:\s+(.*))?$", code)
    assert match is not None
    first, remainder = match.groups()
    remainder = remainder or ""
    first_upper = first.upper()

    if label is None and first_upper not in INSTRUCTIONS and first_upper not in DIRECTIVES:
        label = first
        if not remainder.strip():
            return Statement(path, scope, line_number, line.rstrip(), label, None, (), "")
        match = re.match(r"^(\S+)(?:\s+(.*))?$", remainder.strip())
        assert match is not None
        first, remainder = match.groups()
        remainder = remainder or ""
        first_upper = first.upper()

    if first_upper not in INSTRUCTIONS and first_upper not in DIRECTIVES:
        raise AssemblyError(f"{path}:{line_number}: unknown operation {first!r}")
    return Statement(
        path=path,
        scope=scope,
        line_number=line_number,
        source=line.rstrip(),
        label=label,
        op=first_upper,
        args=_split_operands(remainder, first_upper),
        raw_args=remainder.strip(),
    )


def _number(token: str, statement: Statement | None = None) -> int:
    original = token
    text = token.strip()
    if text.startswith("#"):
        text = text[1:]
    if not text:
        error = "invalid numeric literal"
        raise statement.fail(f"{error} {original!r}") if statement else AssemblyError(error)

    sign = 1
    if text[0] in "+-":
        sign = -1 if text[0] == "-" else 1
        text = text[1:]
    lowered = text.casefold()
    try:
        if lowered.startswith("0x"):
            return sign * int(text[2:], 16)
        if lowered.startswith("0b"):
            return sign * int(text[2:], 2)
        if lowered.startswith("x"):
            return sign * int(text[1:], 16)
        if lowered.startswith("b"):
            return sign * int(text[1:], 2)
        return sign * int(text, 10)
    except ValueError as error:
        message = f"invalid numeric literal {original!r}"
        if statement is not None:
            raise statement.fail(message) from error
        raise AssemblyError(message) from error


def _signed(value: int, bits: int, statement: Statement, field: str) -> int:
    low, high = -(1 << (bits - 1)), (1 << (bits - 1)) - 1
    if not low <= value <= high:
        raise statement.fail(f"{field} {value} is outside {low}..{high}")
    return value & ((1 << bits) - 1)


def _word_bytes(value: int) -> bytes:
    return (value & MASK16).to_bytes(2, "little")


def _latin1_string(statement: Statement) -> bytes:
    if len(statement.args) != 1:
        raise statement.fail(".STRINGZ expects one quoted string")
    try:
        value = ast.literal_eval(statement.args[0])
    except (SyntaxError, ValueError) as error:
        raise statement.fail(f"invalid .STRINGZ string: {error}") from error
    if not isinstance(value, str):
        raise statement.fail(".STRINGZ argument must be a string")
    try:
        return value.encode("latin-1") + b"\x00"
    except UnicodeEncodeError as error:
        raise statement.fail(".STRINGZ supports Latin-1 characters only") from error


def _register(token: str, statement: Statement) -> int:
    match = re.fullmatch(r"(?i)R([0-7])", token.strip())
    if match is None:
        raise statement.fail(f"expected register R0..R7, got {token!r}")
    return int(match.group(1))


def _register_list(token: str, statement: Statement) -> list[int]:
    text = token.strip()
    if not (text.startswith("{") and text.endswith("}")):
        text = "{" + text + "}"
    names = [name.strip() for name in text[1:-1].split(",") if name.strip()]
    if not names:
        raise statement.fail("register list cannot be empty")
    registers = [_register(name, statement) for name in names]
    if len(set(registers)) != len(registers):
        raise statement.fail("register list contains duplicates")
    return registers


def _is_instruction(op: str | None) -> bool:
    return op in INSTRUCTIONS


def _branch_inverse(condition: int) -> int:
    return {0: 7, 1: 6, 2: 5, 3: 4, 4: 3, 5: 2, 6: 1, 7: 0,
            8: 9, 9: 8, 10: 11, 11: 10, 12: 13, 13: 12, 14: 15, 15: 14}[condition]


class Assembler:
    """Two-pass assembler/linker with short-instruction relaxation."""

    def __init__(self, include_dirs: Iterable[Path] = ()) -> None:
        self.include_dirs = [Path(path).resolve() for path in include_dirs]
        self.root_scope = ""
        self.source_root = Path(".").resolve()
        self.scopes: dict[str, list[Statement]] = {}
        self.scope_paths: dict[str, Path] = {}
        self.scope_order: list[str] = []
        self.imports: dict[str, list[External]] = {}
        self.statements: list[Statement] = []
        self.symbols: dict[tuple[str, str], int] = {}
        self.origin = 0
        self.stack = DEFAULT_STACK
        self.end_address = 0

    def _find_module(self, source_name: str, including: Path) -> Path:
        stem = Path(source_name).stem.casefold()
        directories = (
            including.parent,
            including.parent / "lib",
            self.source_root,
            self.source_root / "lib",
            *self.include_dirs,
        )
        matches: list[Path] = []
        for directory in directories:
            if not directory.is_dir():
                continue
            for candidate in directory.iterdir():
                if candidate.is_file() and candidate.suffix.casefold() == ".asm":
                    name = candidate.stem.casefold()
                    if name == stem or name.endswith(stem):
                        matches.append(candidate.resolve())
        unique = list(dict.fromkeys(matches))
        exact = [path for path in unique if path.stem.casefold() == stem]
        selected = exact or unique
        if not selected:
            raise AssemblyError(f"{including}: external source {source_name!r} was not found")
        if len(selected) != 1:
            listing = ", ".join(str(path) for path in selected)
            raise AssemblyError(f"{including}: external source {source_name!r} is ambiguous: {listing}")
        return selected[0]

    @staticmethod
    def _external_parts(statement: Statement) -> tuple[str, str, str]:
        if len(statement.args) != 1 or "-" not in statement.args[0]:
            raise statement.fail(".EXTERNAL syntax must be source-file-SYMBOL")
        source_name, symbol = statement.args[0].rsplit("-", 1)
        if not source_name or not symbol:
            raise statement.fail("invalid .EXTERNAL source-file-SYMBOL")
        return _norm(statement.args[0]), _norm(symbol), source_name

    def _read_scope(self, path: Path) -> str:
        path = path.resolve()
        scope = str(path).casefold()
        if scope in self.scopes:
            return scope
        self.scopes[scope] = []
        self.scope_paths[scope] = path
        self.scope_order.append(scope)
        try:
            lines = path.read_text(encoding="utf-8-sig").splitlines()
        except UnicodeDecodeError:
            lines = path.read_text(encoding="cp1252").splitlines()

        statements: list[Statement] = []
        for line_number, line in enumerate(lines, start=1):
            statement = _parse_line(path, scope, line_number, line)
            if statement is not None:
                statements.append(statement)
                if statement.op == ".END":
                    break
        self.scopes[scope] = statements

        external_refs: list[External] = []
        for statement in statements:
            if statement.op != ".EXTERNAL":
                continue
            alias, symbol, source_name = self._external_parts(statement)
            module_path = self._find_module(source_name, path)
            external_refs.append(External(alias, symbol, module_path))
        self.imports[scope] = external_refs
        for ref in external_refs:
            self._read_scope(ref.path)
        return scope

    def _resolve(self, expression: str, statement: Statement) -> int:
        text = expression.strip()
        try:
            return _number(text, statement)
        except AssemblyError:
            pass

        delta = 0
        arithmetic = re.fullmatch(
            r"(.+?)([+-])(#?(?:\d+|x[\da-fA-F]+|0x[\da-fA-F]+))",
            text,
            re.IGNORECASE,
        )
        name = text
        if arithmetic:
            name, sign, amount = arithmetic.groups()
            delta = _number(amount, statement) * (1 if sign == "+" else -1)

        normalized = _norm(name)
        local = self.symbols.get((statement.scope, normalized))
        if local is not None:
            return local + delta
        root = self.symbols.get((self.root_scope, normalized))
        if root is not None:
            return root + delta

        imported_targets: set[int] = set()
        for ref in self.imports.get(statement.scope, []):
            module_scope = str(ref.path.resolve()).casefold()
            target = self.symbols.get((module_scope, ref.symbol))
            if target is not None and normalized in {ref.alias, ref.symbol}:
                imported_targets.add(target)
            elif target is not None and normalized == ref.symbol:
                imported_targets.add(target)
        if len(imported_targets) == 1:
            return imported_targets.pop() + delta
        if len(imported_targets) > 1:
            raise statement.fail(f"ambiguous imported symbol {name!r}")
        raise statement.fail(f"undefined symbol {name!r}")

    def _get_root_settings(self, root: list[Statement]) -> None:
        origins = [statement for statement in root if statement.op == ".ORIG"]
        if len(origins) != 1 or len(origins[0].args) != 1:
            source = origins[0].path if origins else self.source_root
            raise AssemblyError(f"{source}: expected exactly one .ORIG with one address")
        self.origin = _number(origins[0].args[0], origins[0])
        if not 0 <= self.origin < MEMORY_SIZE:
            raise origins[0].fail(".ORIG must be in 0..65535")
        if self.origin & 1:
            raise origins[0].fail(".ORIG must be even so the first instruction is aligned")

        stacks = [statement for statement in root if statement.op == ".STACK"]
        if len(stacks) > 1:
            raise stacks[1].fail(".STACK may appear only once in the root source")
        if stacks:
            if len(stacks[0].args) != 1:
                raise stacks[0].fail(".STACK expects one initial stack address")
            self.stack = _number(stacks[0].args[0], stacks[0])
            if not 0 <= self.stack <= MASK16 or self.stack & 1:
                raise stacks[0].fail(".STACK must be an even address in 0..65535")

    def _initial_size(self, statement: Statement) -> int:
        op = statement.op
        if op is None or op in {".ORIG", ".END", ".EXTERNAL", ".STACK"}:
            return 0
        if op in INSTRUCTIONS:
            if statement.relaxed == "branch-long":
                return 4 if BRANCH_CONDITIONS[op] == 0 else 6
            if statement.relaxed in {"jsr-long", "pc-memory-long"}:
                return 6
            if statement.relaxed == "lea-long":
                return 4
            return 4 if op == "LI" else 2
        if op == ".FILL":
            return 2
        if op == ".BLKW":
            if len(statement.args) != 1:
                raise statement.fail(".BLKW expects one word count")
            count = _number(statement.args[0], statement)
            if count < 0:
                raise statement.fail(".BLKW count cannot be negative")
            return count * 2
        if op == ".BLKB":
            if len(statement.args) != 1:
                raise statement.fail(".BLKB expects one byte count")
            count = _number(statement.args[0], statement)
            if count < 0:
                raise statement.fail(".BLKB count cannot be negative")
            return count
        if op == ".BYTE":
            if not statement.args:
                raise statement.fail(".BYTE expects at least one value")
            return len(statement.args)
        if op == ".STRINGZ":
            return len(_latin1_string(statement))
        raise statement.fail(f"unsupported directive {op}")

    def _layout(self) -> None:
        root = self.scopes[self.root_scope]
        self._get_root_settings(root)
        self.statements = []
        for scope in self.scope_order:
            for statement in self.scopes[scope]:
                if statement.op in {".EXTERNAL", ".END", ".STACK"}:
                    continue
                if statement.op == ".ORIG" and scope != self.root_scope:
                    continue
                self.statements.append(statement)

        self.symbols.clear()
        pc = self.origin
        for statement in self.statements:
            is_word = statement.op in {".FILL", ".BLKW"} or _is_instruction(statement.op)
            statement.padding = 1 if is_word and pc & 1 else 0
            pc += statement.padding
            statement.address = pc
            if statement.label:
                key = (statement.scope, _norm(statement.label))
                if key in self.symbols:
                    raise statement.fail(f"duplicate label {statement.label!r}")
                self.symbols[key] = pc
            statement.size = self._initial_size(statement)
            pc += statement.size
            if pc > MEMORY_SIZE:
                raise statement.fail("linked image extends beyond 65536 bytes")
        self.end_address = pc

    def _pc_offset(self, target: int, statement: Statement, bits: int) -> int:
        if target & 1:
            raise statement.fail(f"PC-relative target x{target:04X} is not word-aligned")
        byte_delta = target - (statement.address + 2)
        if byte_delta & 1:
            raise statement.fail(f"PC-relative target x{target:04X} is not word-aligned")
        return _signed(byte_delta // 2, bits, statement, "PC-relative word offset")

    def _relax(self) -> None:
        for _ in range(64):
            self._layout()
            changed = False
            for statement in self.statements:
                op = statement.op
                if op in BRANCH_CONDITIONS and statement.relaxed is None:
                    if len(statement.args) != 1:
                        raise statement.fail(f"{op} expects one target")
                    target = self._resolve(statement.args[0], statement)
                    try:
                        self._pc_offset(target, statement, 7)
                    except AssemblyError as error:
                        if "outside" not in str(error):
                            raise
                        condition = BRANCH_CONDITIONS[op]
                        statement.relaxed = "branch-long"
                        statement.size = 4 if condition == 0 else 6
                        changed = True
                elif op == "JSR" and statement.relaxed is None:
                    if len(statement.args) != 1:
                        raise statement.fail("JSR expects one target")
                    target = self._resolve(statement.args[0], statement)
                    try:
                        self._pc_offset(target, statement, 11)
                    except AssemblyError as error:
                        if "outside" not in str(error):
                            raise
                        statement.relaxed = "jsr-long"
                        statement.size = 6
                        changed = True
                elif op in {"LDPC", "STPC", "LD", "ST"} and statement.relaxed is None:
                    if len(statement.args) != 2:
                        raise statement.fail(f"{op} expects a register and a label")
                    target = self._resolve(statement.args[1], statement)
                    try:
                        self._pc_offset(target, statement, 8)
                    except AssemblyError as error:
                        if "outside" not in str(error):
                            raise
                        statement.relaxed = "pc-memory-long"
                        statement.size = 6
                        changed = True
                elif op == "LEA" and statement.relaxed is None:
                    if len(statement.args) != 2:
                        raise statement.fail("LEA expects a register and a label")
                    target = self._resolve(statement.args[1], statement)
                    if target & 1:
                        statement.relaxed = "lea-long"
                        statement.size = 4
                        changed = True
                        continue
                    try:
                        self._pc_offset(target, statement, 8)
                    except AssemblyError as error:
                        if "outside" not in str(error):
                            raise
                        statement.relaxed = "lea-long"
                        statement.size = 4
                        changed = True
            if not changed:
                self._layout()
                return
        raise AssemblyError("instruction relaxation did not converge")

    def _word(self, statement: Statement, opcode: int, fields: int = 0) -> bytes:
        if not 0 <= opcode <= 0x1F or not 0 <= fields <= 0x7FF:
            raise statement.fail(f"invalid instruction encoding fields: opcode={opcode}, fields={fields}")
        return _word_bytes((opcode << 11) | fields)

    def _pc_word(self, statement: Statement, opcode: int, register: int, target: int, bits: int) -> bytes:
        offset = self._pc_offset(target, statement, bits)
        return self._word(statement, opcode, (register << (bits)) | offset)

    def _load_constant(self, statement: Statement, register: int, value: int) -> bytes:
        if not -0x8000 <= value <= MASK16:
            raise statement.fail(f"LI value {value} is outside -32768..65535")
        low, high = value & 0xFF, (value >> 8) & 0xFF
        movi = self._word(statement, OPCODES["MOVI"], (register << 8) | low)
        movh = self._word(statement, OPCODES["MOVH"], (register << 8) | high)
        return movi + movh

    def _branch_encoding(self, statement: Statement, condition: int, target: int) -> bytes:
        if statement.relaxed == "branch-long":
            if condition == 0:
                return self._word(statement, OPCODES["JMPM"], 0) + _word_bytes(target)
            inverse = _branch_inverse(condition)
            skip = (inverse << 7) | 2
            return (
                self._word(statement, OPCODES["BR"], skip)
                + self._word(statement, OPCODES["JMPM"], 0)
                + _word_bytes(target)
            )
        offset = self._pc_offset(target, statement, 7)
        return self._word(statement, OPCODES["BR"], (condition << 7) | offset)

    def _encode_instruction(self, statement: Statement) -> bytes:
        op = statement.op
        args = statement.args
        assert op is not None

        def expect(count: int) -> None:
            if len(args) != count:
                raise statement.fail(f"{op} expects {count} operand(s), got {len(args)}")

        def reg(index: int) -> int:
            return _register(args[index], statement)

        def value(index: int) -> int:
            return self._resolve(args[index], statement)

        if op in BRANCH_CONDITIONS:
            expect(1)
            return self._branch_encoding(statement, BRANCH_CONDITIONS[op], value(0))

        if op in {"ADD", "SUB", "ADC", "SBC", "AND", "OR", "XOR", "CMP"}:
            if op == "CMP":
                expect(2)
                rd, rs1, rs2 = 0, reg(0), reg(1)
            else:
                expect(3)
                rd, rs1 = reg(0), reg(1)
                if op in {"ADD", "AND"} and args[2].startswith("#"):
                    immediate = _signed(self._resolve(args[2], statement), 5, statement, "imm5")
                    opcode = OPCODES["ADDI"] if op == "ADD" else OPCODES["ANDI"]
                    return self._word(statement, opcode, (rd << 8) | (rs1 << 5) | immediate)
                rs2 = reg(2)
            function = {
                "ADD": 0, "SUB": 1, "ADC": 2, "SBC": 3,
                "AND": 0, "OR": 1, "XOR": 2, "CMP": 3,
            }[op]
            opcode = OPCODES["ALU"] if op in {"ADD", "SUB", "ADC", "SBC"} else OPCODES["LOG"]
            return self._word(statement, opcode, (rd << 8) | (rs1 << 5) | (rs2 << 2) | function)

        if op in {"ADDI", "ANDI"}:
            expect(3)
            rd, rs = reg(0), reg(1)
            immediate = _signed(self._resolve(args[2], statement), 5, statement, "imm5")
            return self._word(statement, OPCODES[op], (rd << 8) | (rs << 5) | immediate)

        if op in {"NOT", "NEG"}:
            expect(2)
            function = 0 if op == "NOT" else 1
            return self._word(
                statement,
                OPCODES["UNARY"],
                (reg(0) << 8) | (reg(1) << 5) | (function << 3),
            )

        if op in {"MOVI", "MOVH"}:
            expect(2)
            rd = reg(0)
            immediate = self._resolve(args[1], statement)
            if op == "MOVI":
                immediate = _signed(immediate, 8, statement, "imm8")
            elif not 0 <= immediate <= 0xFF:
                raise statement.fail(f"MOVH imm8 {immediate} is outside 0..255")
            return self._word(statement, OPCODES[op], (rd << 8) | immediate)

        if op == "LI":
            expect(2)
            return self._load_constant(statement, reg(0), value(1))

        if op == "MOV":
            expect(2)
            return self._word(statement, OPCODES["ADDI"], (reg(0) << 8) | (reg(1) << 5))

        if op == "CLR":
            expect(1)
            return self._word(statement, OPCODES["MOVI"], reg(0) << 8)

        if op in {"INC", "DEC"}:
            if len(args) == 1:
                rd = rs = reg(0)
            elif len(args) == 2:
                rd, rs = reg(0), reg(1)
            else:
                raise statement.fail(f"{op} expects one or two registers")
            immediate = 1 if op == "INC" else -1
            return self._word(
                statement,
                OPCODES["ADDI"],
                (rd << 8) | (rs << 5) | _signed(immediate, 5, statement, "imm5"),
            )

        if op in {"SHL", "LSR", "ASR"}:
            expect(3)
            rd, rs = reg(0), reg(1)
            count = self._resolve(args[2], statement)
            if not 0 <= count <= 15:
                raise statement.fail("shift count must be in 0..15")
            if op == "SHL":
                fields = (rd << 8) | (rs << 5) | (count << 1)
                return self._word(statement, OPCODES["SHL"], fields)
            mode = 1 if op == "ASR" else 0
            fields = (rd << 8) | (rs << 5) | (mode << 4) | count
            return self._word(statement, OPCODES["SHR"], fields)

        if op in {"RRC", "RLC"}:
            expect(2)
            direction = 0 if op == "RRC" else 1
            return self._word(statement, OPCODES["ROT"], (reg(0) << 8) | (reg(1) << 5) | (direction << 4))

        if op in {"SHLV", "SRLV", "SRAV", "ROLV"}:
            expect(3)
            function = {"SHLV": 0, "SRLV": 1, "SRAV": 2, "ROLV": 3}[op]
            fields = (reg(0) << 8) | (reg(1) << 5) | (reg(2) << 2) | function
            return self._word(statement, OPCODES["SHIFTV"], fields)

        if op in {"LDBL", "LDBS", "LDBH", "STBL", "STBH", "LDW", "STW", "LDW16", "STW16", "LDR", "STR"}:
            expect(3)
            mnemonic = {"LDR": "LDW", "STR": "STW"}.get(op, op)
            rt, rb = reg(0), reg(1)
            offset = self._resolve(args[2], statement)
            if mnemonic in {"LDW", "STW", "LDW16", "STW16"}:
                if mnemonic in {"LDW", "STW"} and 16 <= offset <= 31:
                    mnemonic += "16"
                    offset -= 16
                elif mnemonic in {"LDW16", "STW16"}:
                    if not 0 <= offset <= 31:
                        raise statement.fail(f"{mnemonic} word offset must be in 0..31")
                    offset -= 16
                field = _signed(offset, 5, statement, "word offset")
            else:
                field = _signed(offset, 5, statement, "byte offset")
            return self._word(
                statement,
                OPCODES[mnemonic],
                (rt << 8) | (rb << 5) | field,
            )

        if op in {"LDPC", "STPC", "LD", "ST", "LDPM", "STPM", "LEA"}:
            expect(2)
            mnemonic = {"LD": "LDPC", "ST": "STPC"}.get(op, op)
            register = reg(0)
            target = value(1)
            if statement.relaxed == "pc-memory-long":
                indirect = OPCODES["LDPM" if mnemonic in {"LDPC"} else "STPM"]
                word = self._word(statement, indirect, (register << 8) | 1)
                skip = self._word(statement, OPCODES["BR"], 1)
                return word + skip + _word_bytes(target)
            if mnemonic in {"LDPC", "STPC"}:
                return self._pc_word(
                    statement,
                    OPCODES[mnemonic],
                    register,
                    target,
                    8,
                )
            if mnemonic in {"LDPM", "STPM"}:
                return self._pc_word(statement, OPCODES[mnemonic], register, target, 8)
            if statement.relaxed == "lea-long":
                return self._load_constant(statement, register, target)
            return self._pc_word(statement, OPCODES["LEA"], register, target, 8)

        if op == "JSR":
            expect(1)
            target = value(0)
            if statement.relaxed == "jsr-long":
                call = self._word(statement, OPCODES["JSRM"], 1)
                skip = self._word(statement, OPCODES["BR"], 1)
                return call + skip + _word_bytes(target)
            return self._word(statement, OPCODES["JSR"], self._pc_offset(target, statement, 11))

        if op in {"JMPM", "JSRM"}:
            expect(1)
            target = value(0)
            return self._word(statement, OPCODES[op], self._pc_offset(target, statement, 11))

        if op in {"JMP", "JSRR", "RET"}:
            if op == "RET":
                expect(0)
                function, base = 2, 7
            else:
                expect(1)
                function, base = (0 if op == "JMP" else 1), reg(0)
            return self._word(statement, OPCODES["JR"], (function << 9) | (base << 6))

        if op in {"PUSHM", "POPM", "POPR", "PUSH", "POP"}:
            expect(1)
            operation = {"PUSH": "PUSHM", "POP": "POPM"}.get(op, op)
            registers = _register_list(args[0], statement)
            if operation == "POPR" and 7 not in registers:
                raise statement.fail("POPR register list must include R7")
            mask = sum(1 << register for register in registers)
            function = {"PUSHM": 0, "POPM": 1, "POPR": 2}[operation]
            return self._word(statement, OPCODES["STACK"], (function << 9) | (mask << 1))

        if op in {"TRAP", "GETC", "OUT", "PUTS", "IN", "HALT"}:
            if op == "TRAP":
                expect(1)
                vector = self._resolve(args[0], statement)
            else:
                expect(0)
                vector = TRAPS[op]
            if not 0 <= vector <= 0xFF:
                raise statement.fail("TRAP vector must be in 0..255")
            return self._word(statement, OPCODES["TRAP"], vector)

        if op == "NOP":
            expect(0)
            return self._word(statement, OPCODES["BR"], 7 << 7)
        raise statement.fail(f"unsupported instruction {op!r}")

    def _data_bytes(self, statement: Statement) -> bytes:
        op = statement.op
        if op == ".FILL":
            if len(statement.args) != 1:
                raise statement.fail(".FILL expects one value")
            value = self._resolve(statement.args[0], statement)
            if not -0x8000 <= value <= MASK16:
                raise statement.fail(".FILL value must be in -32768..65535")
            return _word_bytes(value)
        if op == ".BYTE":
            values = []
            for arg in statement.args:
                try:
                    value = _number(arg, statement)
                except AssemblyError:
                    try:
                        character = ast.literal_eval(arg)
                    except (SyntaxError, ValueError) as error:
                        raise statement.fail(f"invalid .BYTE value {arg!r}") from error
                    if not isinstance(character, str) or len(character) != 1:
                        raise statement.fail(".BYTE character values must contain one character")
                    value = ord(character)
                if not -128 <= value <= 255:
                    raise statement.fail(f".BYTE value {value} is outside -128..255")
                values.append(value & 0xFF)
            return bytes(values)
        if op == ".STRINGZ":
            return _latin1_string(statement)
        if op == ".BLKB":
            return bytes(statement.size)
        if op == ".BLKW":
            return bytes(statement.size)
        return b""

    def assemble(self, source_file: Path) -> AssemblyImage:
        source_file = Path(source_file).resolve()
        if not source_file.is_file():
            raise AssemblyError(f"source file not found: {source_file}")
        self.root_scope = str(source_file).casefold()
        self.source_root = source_file.parent
        self._read_scope(source_file)
        self._relax()

        memory = bytearray(self.end_address - self.origin)
        listing_rows = [
            "; Linked new-ISA source listing",
            f"; origin=x{self.origin:04X} stack=x{self.stack:04X}; emitted bytes are little-endian",
            "; address  size  bytes                         source",
        ]
        active_path: Path | None = None
        for statement in self.statements:
            if active_path != statement.path:
                active_path = statement.path
                listing_rows.append(f"; source: {active_path}")
            if statement.padding:
                pad_address = statement.address - statement.padding
                listing_rows.append(
                    f"x{pad_address:04X}     {statement.padding:4d}  "
                    f"{'00':<29} ; alignment padding"
                )
            op = statement.op
            if op is None or op in {".ORIG", ".STACK"}:
                if statement.label:
                    listing_rows.append(
                        f"x{statement.address:04X}          {'':<29} {statement.label}:"
                    )
                continue
            if op in INSTRUCTIONS:
                emitted = self._encode_instruction(statement)
            else:
                emitted = self._data_bytes(statement)
            if len(emitted) != statement.size:
                raise statement.fail(
                    f"internal size mismatch: layout reserved {statement.size} bytes, "
                    f"encoder emitted {len(emitted)}"
                )
            begin = statement.address - self.origin
            memory[begin:begin + len(emitted)] = emitted
            shown = " ".join(f"{byte:02X}" for byte in emitted[:16])
            if len(emitted) > 16:
                shown += f" ... ({len(emitted)} bytes)"
            source_text = statement.source.strip()
            listing_rows.append(
                f"x{statement.address:04X}     {statement.size:4d}  {shown:<29} {source_text}"
            )

        code_bytes = sum(s.size for s in self.statements if s.op in INSTRUCTIONS)
        data_bytes = sum(
            s.size for s in self.statements
            if s.op in {".FILL", ".BLKW", ".BLKB", ".BYTE", ".STRINGZ"}
        )
        padding_bytes = sum(s.padding for s in self.statements)
        map_rows = ["; address  module / label"]
        for (scope, label), address in sorted(self.symbols.items(), key=lambda kv: kv[1]):
            module = self.scope_paths[scope].stem
            map_rows.append(f"x{address:04X}     {module}:{label}")

        root_symbols = {
            label: address
            for (scope, label), address in self.symbols.items()
            if scope == self.root_scope
        }
        return AssemblyImage(
            origin=self.origin,
            stack=self.stack,
            image=bytes(memory),
            listing="\n".join(listing_rows) + "\n",
            symbols=root_symbols,
            code_bytes=code_bytes,
            data_bytes=data_bytes,
            padding_bytes=padding_bytes,
            modules=len(self.scope_order),
            symbol_map="\n".join(map_rows) + "\n",
        )


def _hex_bytes(data: bytes, width: int = 16) -> str:
    return "\n".join(
        " ".join(f"{byte:02X}" for byte in data[offset:offset + width])
        for offset in range(0, len(data), width)
    ) + ("\n" if data else "")


def _default_output(source: Path, output_format: str) -> Path:
    suffix = {"bin": ".bin", "hex": ".hex", "asm": ".asm"}[output_format]
    return source.with_suffix(suffix)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Assemble and recursively link a program for the new 16-bit ISA."
    )
    parser.add_argument("source", type=Path, help="new-ISA assembly source file")
    parser.add_argument(
        "-f", "--format",
        choices=("bin", "hex", "asm"),
        default="bin",
        help="output format: binary object, hexadecimal bytes, or linked ASM listing (default: bin)",
    )
    parser.add_argument("-o", "--output", type=Path, help="output path (default: source with format extension)")
    parser.add_argument(
        "-I", "--include",
        action="append",
        default=[],
        type=Path,
        metavar="DIR",
        help="additional directory to search for .EXTERNAL modules (repeatable)",
    )
    parser.add_argument(
        "--map",
        type=Path,
        metavar="FILE",
        help="also write a symbol map (address, module:label) of all linked modules",
    )
    args = parser.parse_args(argv)

    try:
        image = Assembler(args.include).assemble(args.source)
        output_path = args.output or _default_output(args.source, args.format)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if args.format == "bin":
            output_path.write_bytes(image.object_bytes())
        elif args.format == "hex":
            output_path.write_text(_hex_bytes(image.object_bytes()), encoding="ascii")
        else:
            output_path.write_text(image.listing, encoding="utf-8")
        print(
            f"Ensamblado correcto: origen x{image.origin:04X}, "
            f"{len(image.image)} bytes de imagen, formato {args.format}, "
            f"salida {output_path}"
        )
        print(
            f"Desglose de imagen: {image.code_bytes} B de codigo, {image.data_bytes} B de datos, "
            f"{image.padding_bytes} B de alineacion; {image.modules} modulo(s) enlazado(s)"
        )
        if args.map:
            args.map.parent.mkdir(parents=True, exist_ok=True)
            args.map.write_text(image.symbol_map, encoding="utf-8")
            print(f"Mapa de simbolos escrito en {args.map}")
    except (AssemblyError, OSError, ValueError) as error:
        print(f"Error de ensamblado: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())