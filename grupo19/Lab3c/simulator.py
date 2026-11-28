"""Functional simulator for the byte-addressed 16-bit ISA.

The simulator accepts only linked binary objects (.bin/.obj) or their
whitespace-separated hexadecimal representation (.hex). It never parses ASM.

Besides running the program it reports:
  * total executed instructions and a per-mnemonic instruction mix;
  * memory use: loaded image, peak stack, dynamic data written outside the
    image/stack, and distinct bytes touched;
  * per-operation metrics for programs that print a "==NAME==" banner before
    each operation (as the benchmark menu does), together with the values the
    operation printed (operands and result).

Usage:
    python simulator.py program.hex
    python simulator.py program.bin --json metrics.json --hide-output
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path


MASK16 = 0xFFFF
ADDRESS_SPACE = 1 << 16
DEFAULT_INSTRUCTION_LIMIT = 10_000_000

OP_BR = 0x00
OP_ALU = 0x01
OP_LOG = 0x02
OP_ANDI = 0x03
OP_UNARY = 0x04
OP_ADDI = 0x05
OP_MOVI = 0x06
OP_MOVH = 0x07
OP_SHL = 0x08
OP_SHR = 0x09
OP_ROT = 0x0A
OP_LDBL = 0x0B
OP_LDBS = 0x0C
OP_LDBH = 0x0D
OP_STBL = 0x0E
OP_STBH = 0x0F
OP_LDW = 0x10
OP_STW = 0x11
OP_LDPC = 0x12
OP_STPC = 0x13
OP_LEA = 0x14
OP_JSR = 0x15
OP_JR = 0x16
OP_STACK = 0x17
OP_TRAP = 0x18
OP_SHIFTV = 0x19
OP_JMPM = 0x1A
OP_JSRM = 0x1B
OP_LDPM = 0x1C
OP_STPM = 0x1D
OP_LDW16 = 0x1E
OP_STW16 = 0x1F

SUPPORTED_TRAPS = {0x20, 0x21, 0x22, 0x23, 0x25}

OPCODE_NAMES = {
    value: name[3:]
    for name, value in list(globals().items())
    if name.startswith("OP_") and isinstance(value, int)
}

# Banner printed by the benchmark menu before each operation, e.g.
# "==SENO TRIGONOMETRICO (TAYLOR)==" or "==LOGARITMO== (BORCHARDT)".
BANNER = re.compile(r"^==\s*(.*?)\s*==\s*(.*)$")
PROLOGUE_NAME = "(arranque / interfaz)"

# Flags stored per byte in Machine.touched.
T_READ, T_WRITE, T_FETCH = 1, 2, 4


class SimulatorError(Exception):
    """Base class for object loading and execution failures."""


class InputFormatError(SimulatorError):
    """Raised when an input file is not a supported object format."""


class ExecutionError(SimulatorError):
    """Raised when the simulated program cannot continue."""


class AlignmentError(ExecutionError):
    """Raised for an odd instruction PC, word access, or jump target."""


class StackError(ExecutionError):
    """Raised when the implicit stack exceeds its valid push depth."""


@dataclass(frozen=True)
class ObjectImage:
    origin: int
    initial_sp: int
    data: bytes


@dataclass
class SectionStats:
    """Metrics of one operation (the span between two banners)."""

    name: str
    start_instruction: int
    start_stack_depth: int = 0
    instructions: int = 0
    max_stack_bytes: int = 0
    data_reads: int = 0
    data_writes: int = 0
    written: set = field(default_factory=set, repr=False)
    lines: list = field(default_factory=list)

    @property
    def bytes_written(self) -> int:
        return len(self.written)


@dataclass(frozen=True)
class ExecutionResult:
    output: str
    registers: tuple[int, ...]
    pc: int
    instructions_executed: int
    image_bytes: int
    max_stack_bytes: int
    # --- extended metrics ---
    sections: tuple = ()
    opcode_counts: tuple = ()          # ((mnemonic, count), ...) sorted desc
    data_reads: int = 0
    data_writes: int = 0
    dynamic_data_bytes: int = 0        # written bytes outside image and stack
    touched_bytes: int = 0             # distinct bytes read/written/fetched
    total_memory_bytes: int = 0        # image + peak stack + dynamic data


def parse_object(data: bytes) -> ObjectImage:
    if len(data) < 6:
        raise InputFormatError(
            "object image must contain the 4-byte header and at least one instruction word"
        )

    origin = int.from_bytes(data[0:2], "little")
    initial_sp = int.from_bytes(data[2:4], "little")
    image_data = data[4:]

    if origin & 1:
        raise InputFormatError(f"object origin x{origin:04X} is not word-aligned")
    if origin + len(image_data) > ADDRESS_SPACE:
        raise InputFormatError(
            f"object image at x{origin:04X} extends beyond the 64 KiB address space"
        )
    return ObjectImage(origin, initial_sp, image_data)


def load_object_file(path: Path) -> ObjectImage:
    suffix = path.suffix.casefold()
    if suffix not in {".bin", ".obj", ".hex"}:
        raise InputFormatError(
            "only binary .bin/.obj and hexadecimal .hex objects are accepted; ASM is not accepted"
        )

    if suffix == ".hex":
        try:
            text = path.read_text(encoding="ascii")
        except UnicodeDecodeError as error:
            raise InputFormatError("hex object must contain ASCII hexadecimal digits only") from error
        compact = "".join(text.split())
        if not compact or len(compact) % 2 or re.fullmatch(r"[0-9A-Fa-f]+", compact) is None:
            raise InputFormatError(
                "hex object must contain an even number of hexadecimal digits"
            )
        return parse_object(bytes.fromhex(compact))

    return parse_object(path.read_bytes())


def _sign_extend(value: int, bits: int) -> int:
    sign_bit = 1 << (bits - 1)
    return value - (1 << bits) if value & sign_bit else value


def _signed16(value: int) -> int:
    return _sign_extend(value & MASK16, 16)


class Machine:
    def __init__(self, image: ObjectImage, input_bytes: bytes = b"") -> None:
        self.memory = bytearray(ADDRESS_SPACE)
        end = image.origin + len(image.data)
        self.memory[image.origin:end] = image.data
        self.origin = image.origin
        self.image_bytes = len(image.data)
        self.pc = image.origin
        self.registers = [0] * 8
        self.sp = image.initial_sp
        self.n = False
        self.z = True
        self.p = False
        self.c = False
        self.v = False
        self.halted = False
        self.instructions_executed = 0
        self.input_bytes = input_bytes
        self.input_index = 0
        self.output: list[str] = []
        self.stack_depth = 0
        self.max_stack_bytes = 0
        # --- instrumentation ---
        self.initial_sp = image.initial_sp
        self.touched = bytearray(ADDRESS_SPACE)
        self.opcode_counter: Counter = Counter()
        self.data_reads = 0
        self.data_writes = 0
        self.sections: list[SectionStats] = []
        self.current: SectionStats | None = None
        self._line: list[str] = []
        self._line_start = 0
        self._open_section(PROLOGUE_NAME, 0)

    # ------------------------------------------------------------------
    # Instrumentation helpers
    # ------------------------------------------------------------------
    def _open_section(self, name: str, start_instruction: int) -> None:
        if self.current is not None:
            self.current.instructions = start_instruction - self.current.start_instruction
        section = SectionStats(
            name=name,
            start_instruction=start_instruction,
            start_stack_depth=self.stack_depth,
            max_stack_bytes=self.stack_depth,
        )
        self.sections.append(section)
        self.current = section

    def _emit(self, character: str) -> None:
        """Append one output character and detect operation banners."""
        self.output.append(character)
        if not self._line:
            self._line_start = self.instructions_executed
        if character == "\n":
            self._finish_line()
        else:
            self._line.append(character)

    def _finish_line(self) -> None:
        text = "".join(self._line).strip()
        self._line.clear()
        if not text:
            return
        banner = BANNER.match(text)
        if banner:
            name = f"{banner.group(1)} {banner.group(2)}".strip()
            self._open_section(name, self._line_start)
        else:
            assert self.current is not None
            self.current.lines.append(text)

    def _mark(self, address: int, flag: int) -> None:
        self.touched[address & MASK16] |= flag

    def _read_byte(self, address: int) -> int:
        address &= MASK16
        self.touched[address] |= T_READ
        self.data_reads += 1
        self.current.data_reads += 1
        return self.memory[address]

    def _write_byte(self, address: int, value: int) -> None:
        address &= MASK16
        self.touched[address] |= T_WRITE
        self.data_writes += 1
        self.current.data_writes += 1
        self.current.written.add(address)
        self.memory[address] = value & 0xFF

    def _set_nzp(self, value: int) -> None:
        value &= MASK16
        self.n = bool(value & 0x8000)
        self.z = value == 0
        self.p = not self.n and not self.z

    def _write_register(self, index: int, value: int) -> None:
        value &= MASK16
        self.registers[index] = value
        self._set_nzp(value)

    def _read_word(self, address: int, instruction_pc: int, fetch: bool = False) -> int:
        address &= MASK16
        if address & 1:
            raise AlignmentError(
                f"unaligned word read at x{address:04X} (instruction at x{instruction_pc:04X})"
            )
        upper = (address + 1) & MASK16
        if fetch:
            self.touched[address] |= T_FETCH
            self.touched[upper] |= T_FETCH
        else:
            self.touched[address] |= T_READ
            self.touched[upper] |= T_READ
            self.data_reads += 1
            self.current.data_reads += 1
        return self.memory[address] | (self.memory[upper] << 8)

    def _write_word(self, address: int, value: int, instruction_pc: int) -> None:
        address &= MASK16
        if address & 1:
            raise AlignmentError(
                f"unaligned word write at x{address:04X} (instruction at x{instruction_pc:04X})"
            )
        upper = (address + 1) & MASK16
        self.memory[address] = value & 0xFF
        self.memory[upper] = (value >> 8) & 0xFF
        self.touched[address] |= T_WRITE
        self.touched[upper] |= T_WRITE
        self.data_writes += 1
        self.current.data_writes += 1
        self.current.written.add(address)
        self.current.written.add(upper)

    def _check_target(self, target: int, instruction_pc: int) -> int:
        target &= MASK16
        if target & 1:
            raise AlignmentError(
                f"unaligned jump target x{target:04X} (instruction at x{instruction_pc:04X})"
            )
        return target

    @staticmethod
    def _pc_relative(next_pc: int, offset: int) -> int:
        return (next_pc + 2 * offset) & MASK16

    def _set_arithmetic_flags(
        self,
        result: int,
        carry_or_borrow: bool,
        signed_overflow: bool,
    ) -> int:
        result &= MASK16
        self.c = carry_or_borrow
        self.v = signed_overflow
        self._set_nzp(result)
        return result

    def _add(self, left: int, right: int, carry_in: int = 0) -> int:
        unsigned_result = left + right + carry_in
        signed_result = _signed16(left) + _signed16(right) + carry_in
        return self._set_arithmetic_flags(
            unsigned_result,
            unsigned_result > MASK16,
            not -0x8000 <= signed_result <= 0x7FFF,
        )

    def _subtract(self, left: int, right: int, borrow_in: int = 0) -> int:
        unsigned_result = left - right - borrow_in
        signed_result = _signed16(left) - _signed16(right) - borrow_in
        return self._set_arithmetic_flags(
            unsigned_result,
            left < right + borrow_in,
            not -0x8000 <= signed_result <= 0x7FFF,
        )

    def _branch_taken(self, condition: int) -> bool:
        conditions = (
            True,
            self.n,
            self.z,
            self.p,
            self.n or self.z,
            self.n or self.p,
            self.z or self.p,
            False,
            self.c,
            not self.c,
            self.v,
            not self.v,
            self.n != self.v,
            self.n == self.v,
            not self.z and self.n == self.v,
            self.z or self.n != self.v,
        )
        return conditions[condition]

    def _input_character(self, instruction_pc: int) -> int:
        if self.input_index >= len(self.input_bytes):
            raise ExecutionError(
                f"input exhausted for TRAP GETC/IN at PC x{instruction_pc:04X}"
            )
        value = self.input_bytes[self.input_index]
        self.input_index += 1
        return value

    def _trap(self, vector: int, instruction_pc: int) -> None:
        if vector not in SUPPORTED_TRAPS:
            raise ExecutionError(
                f"unsupported TRAP x{vector:02X} at PC x{instruction_pc:04X}"
            )
        if vector == 0x20:
            self._write_register(0, self._input_character(instruction_pc))
        elif vector == 0x21:
            self._emit(chr(self.registers[0] & 0xFF))
        elif vector == 0x22:
            address = self.registers[0]
            for _ in range(ADDRESS_SPACE):
                value = self._read_byte(address)
                if value == 0:
                    return
                self._emit(chr(value))
                address = (address + 1) & MASK16
            raise ExecutionError(
                f"PUTS found no NUL terminator from x{self.registers[0]:04X}"
            )
        elif vector == 0x23:
            value = self._input_character(instruction_pc)
            self._emit(chr(value))
            self._write_register(0, value)
        else:
            self.halted = True

    def _stack_push(self, mask: int, instruction_pc: int) -> None:
        selected = [register for register in range(8) if mask & (1 << register)]
        byte_count = len(selected) * 2
        if self.sp & 1:
            raise AlignmentError(
                f"unaligned stack pointer x{self.sp:04X} at PC x{instruction_pc:04X}"
            )
        if self.sp < byte_count:
            raise StackError(
                f"stack overflow below x0000 at PC x{instruction_pc:04X}"
            )

        new_sp = self.sp - byte_count
        for index, register in enumerate(selected):
            address = new_sp + index * 2
            self._write_word(address, self.registers[register], instruction_pc)
        self.sp = new_sp
        self.stack_depth += byte_count
        self.max_stack_bytes = max(self.max_stack_bytes, self.stack_depth)
        self.current.max_stack_bytes = max(self.current.max_stack_bytes, self.stack_depth)

    def _stack_pop(self, mask: int, instruction_pc: int) -> None:
        selected = [register for register in range(8) if mask & (1 << register)]
        byte_count = len(selected) * 2
        if self.sp & 1:
            raise AlignmentError(
                f"unaligned stack pointer x{self.sp:04X} at PC x{instruction_pc:04X}"
            )
        if self.stack_depth < byte_count:
            raise StackError(
                f"stack underflow: requested {byte_count} bytes with "
                f"{self.stack_depth} bytes pushed at PC x{instruction_pc:04X}"
            )

        restored = [
            self._read_word(self.sp + index * 2, instruction_pc)
            for index in range(len(selected))
        ]
        for register, value in zip(selected, restored):
            self.registers[register] = value
        self.sp += byte_count
        self.stack_depth -= byte_count

    def step(self) -> None:
        if self.halted:
            return

        instruction_pc = self.pc
        self.pc = self._check_target(self.pc, instruction_pc)
        word = self._read_word(instruction_pc, instruction_pc, fetch=True)
        next_pc = (instruction_pc + 2) & MASK16
        self.pc = next_pc
        self.instructions_executed += 1

        opcode = word >> 11
        self.opcode_counter[opcode] += 1
        fields = word & 0x7FF
        rd = (word >> 8) & 0x7
        rs1 = (word >> 5) & 0x7

        if opcode == OP_BR:
            condition = (word >> 7) & 0xF
            if self._branch_taken(condition):
                offset = _sign_extend(word & 0x7F, 7)
                self.pc = self._check_target(
                    self._pc_relative(next_pc, offset), instruction_pc
                )
            return

        if opcode in {OP_ALU, OP_LOG}:
            function = word & 0x3
            rs2 = (word >> 2) & 0x7
            left = self.registers[rs1]
            right = self.registers[rs2]
            if opcode == OP_ALU:
                if function == 0:
                    result = self._add(left, right)
                elif function == 1:
                    result = self._subtract(left, right)
                elif function == 2:
                    result = self._add(left, right, int(self.c))
                else:
                    result = self._subtract(left, right, int(self.c))
                self.registers[rd] = result
            elif function == 0:
                self._write_register(rd, left & right)
            elif function == 1:
                self._write_register(rd, left | right)
            elif function == 2:
                self._write_register(rd, left ^ right)
            else:
                if rd != 0:
                    raise ExecutionError(
                        f"invalid CMP destination field at PC x{instruction_pc:04X}"
                    )
                result = self._subtract(left, right)
            return

        if opcode in {OP_ANDI, OP_ADDI}:
            immediate = _sign_extend(word & 0x1F, 5)
            if opcode == OP_ADDI:
                result = self._add(self.registers[rs1], immediate & MASK16)
                self.registers[rd] = result
            else:
                self._write_register(
                    rd, self.registers[rs1] & (immediate & MASK16)
                )
            return

        if opcode == OP_UNARY:
            if word & 0x7:
                raise ExecutionError(
                    f"invalid UNARY reserved bits at PC x{instruction_pc:04X}"
                )
            function = (word >> 3) & 0x3
            source = self.registers[rs1]
            if function == 0:
                self._write_register(rd, ~source)
            elif function == 1:
                self.registers[rd] = self._subtract(0, source)
            else:
                raise ExecutionError(
                    f"invalid UNARY function {function} at PC x{instruction_pc:04X}"
                )
            return

        if opcode == OP_MOVI:
            self._write_register(rd, _sign_extend(word & 0xFF, 8))
            return

        if opcode == OP_MOVH:
            self._write_register(
                rd,
                (self.registers[rd] & 0xFF) | ((word & 0xFF) << 8),
            )
            return

        if opcode == OP_SHL:
            if word & 1:
                raise ExecutionError(
                    f"invalid SHL reserved bit at PC x{instruction_pc:04X}"
                )
            source = self.registers[rs1]
            count = (word >> 1) & 0xF
            if count:
                self.c = bool((source >> (16 - count)) & 1)
            self._write_register(rd, source << count)
            return

        if opcode == OP_SHR:
            source = self.registers[rs1]
            mode = (word >> 4) & 1
            count = word & 0xF
            if count:
                self.c = bool((source >> (count - 1)) & 1)
            result = (
                _signed16(source) >> count
                if mode
                else source >> count
            )
            self._write_register(rd, result)
            return

        if opcode == OP_ROT:
            if word & 0xF:
                raise ExecutionError(
                    f"invalid ROT reserved bits at PC x{instruction_pc:04X}"
                )
            source = self.registers[rs1]
            old_carry = int(self.c)
            if (word >> 4) & 1:
                self.c = bool(source & 0x8000)
                result = ((source << 1) & MASK16) | old_carry
            else:
                self.c = bool(source & 1)
                result = (source >> 1) | (old_carry << 15)
            self._write_register(rd, result)
            return

        if opcode in {
            OP_LDBL, OP_LDBS, OP_LDBH, OP_STBL, OP_STBH,
            OP_LDW, OP_STW, OP_LDW16, OP_STW16,
        }:
            base = self.registers[rs1]
            offset = _sign_extend(word & 0x1F, 5)
            if opcode in {OP_LDW16, OP_STW16}:
                offset += 16
            word_access = opcode in {OP_LDW, OP_STW, OP_LDW16, OP_STW16}
            address = (base + (2 * offset if word_access else offset)) & MASK16

            if opcode == OP_LDBL:
                self._write_register(rd, self._read_byte(address))
            elif opcode == OP_LDBS:
                self._write_register(rd, _sign_extend(self._read_byte(address), 8))
            elif opcode == OP_LDBH:
                self._write_register(
                    rd,
                    (self.registers[rd] & 0x00FF) | (self._read_byte(address) << 8),
                )
            elif opcode == OP_STBL:
                self._write_byte(address, self.registers[rd] & 0xFF)
            elif opcode == OP_STBH:
                self._write_byte(address, (self.registers[rd] >> 8) & 0xFF)
            elif opcode in {OP_LDW, OP_LDW16}:
                self._write_register(rd, self._read_word(address, instruction_pc))
            else:
                self._write_word(address, self.registers[rd], instruction_pc)
            return

        if opcode in {OP_LDPC, OP_STPC, OP_LEA, OP_LDPM, OP_STPM}:
            offset = _sign_extend(word & 0xFF, 8)
            address = self._pc_relative(next_pc, offset)
            if opcode == OP_LDPC:
                self._write_register(rd, self._read_word(address, instruction_pc))
            elif opcode == OP_STPC:
                self._write_word(address, self.registers[rd], instruction_pc)
            elif opcode == OP_LEA:
                self._write_register(rd, address)
            else:
                pointer = self._read_word(address, instruction_pc)
                if opcode == OP_LDPM:
                    self._write_register(rd, self._read_word(pointer, instruction_pc))
                else:
                    self._write_word(pointer, self.registers[rd], instruction_pc)
            return

        if opcode == OP_JSR:
            offset = _sign_extend(fields, 11)
            self.registers[7] = next_pc
            self.pc = self._check_target(
                self._pc_relative(next_pc, offset), instruction_pc
            )
            return

        if opcode == OP_JR:
            if word & 0x3F:
                raise ExecutionError(
                    f"invalid JR reserved bits at PC x{instruction_pc:04X}"
                )
            function = (word >> 9) & 0x3
            base_register = (word >> 6) & 0x7
            if function == 0:
                target = self.registers[base_register]
            elif function == 1:
                self.registers[7] = next_pc
                target = self.registers[base_register]
            elif function == 2 and base_register == 7:
                target = self.registers[7]
            else:
                raise ExecutionError(
                    f"invalid JR function/register at PC x{instruction_pc:04X}"
                )
            self.pc = self._check_target(target, instruction_pc)
            return

        if opcode == OP_STACK:
            if word & 1:
                raise ExecutionError(
                    f"invalid STACK reserved bit at PC x{instruction_pc:04X}"
                )
            function = (word >> 9) & 0x3
            mask = (word >> 1) & 0xFF
            if mask == 0:
                raise ExecutionError(
                    f"empty STACK register mask at PC x{instruction_pc:04X}"
                )
            if function == 0:
                self._stack_push(mask, instruction_pc)
            elif function in {1, 2}:
                if function == 2 and not mask & (1 << 7):
                    raise ExecutionError(
                        f"POPR mask must include R7 at PC x{instruction_pc:04X}"
                    )
                self._stack_pop(mask, instruction_pc)
                if function == 2:
                    self.pc = self._check_target(self.registers[7], instruction_pc)
            else:
                raise ExecutionError(
                    f"invalid STACK function {function} at PC x{instruction_pc:04X}"
                )
            return

        if opcode == OP_TRAP:
            if fields & 0x700:
                raise ExecutionError(
                    f"invalid TRAP reserved bits at PC x{instruction_pc:04X}"
                )
            self._trap(word & 0xFF, instruction_pc)
            return

        if opcode == OP_SHIFTV:
            function = word & 0x3
            source = self.registers[rs1]
            count_register = (word >> 2) & 0x7
            count = self.registers[count_register] & 0xF
            if count == 0:
                result = source
            elif function == 0:
                self.c = bool((source >> (16 - count)) & 1)
                result = source << count
            elif function == 1:
                self.c = bool((source >> (count - 1)) & 1)
                result = source >> count
            elif function == 2:
                self.c = bool((source >> (count - 1)) & 1)
                result = _signed16(source) >> count
            else:
                self.c = bool((source >> (16 - count)) & 1)
                result = ((source << count) | (source >> (16 - count))) & MASK16
            self._write_register(rd, result)
            return

        if opcode in {OP_JMPM, OP_JSRM}:
            offset = _sign_extend(fields, 11)
            pointer_address = self._pc_relative(next_pc, offset)
            target = self._read_word(pointer_address, instruction_pc)
            if opcode == OP_JSRM:
                self.registers[7] = next_pc
            self.pc = self._check_target(target, instruction_pc)
            return

        raise ExecutionError(
            f"illegal opcode {opcode:05b} at PC x{instruction_pc:04X}"
        )

    def run(self, max_instructions: int = DEFAULT_INSTRUCTION_LIMIT) -> ExecutionResult:
        if max_instructions < 1:
            raise ValueError("max_instructions must be positive")
        while not self.halted:
            if self.instructions_executed >= max_instructions:
                raise ExecutionError(
                    f"instruction limit exceeded ({max_instructions}) at PC x{self.pc:04X}"
                )
            self.step()
        return self._build_result()

    def _build_result(self) -> ExecutionResult:
        if self._line:
            self._finish_line()
        assert self.current is not None
        self.current.instructions = self.instructions_executed - self.current.start_instruction

        image_lo, image_hi = self.origin, self.origin + self.image_bytes
        stack_lo, stack_hi = self.initial_sp - self.max_stack_bytes, self.initial_sp
        dynamic = sum(
            1
            for address, flags in enumerate(self.touched)
            if flags & T_WRITE
            and not image_lo <= address < image_hi
            and not stack_lo <= address < stack_hi
        )
        touched = sum(1 for flags in self.touched if flags)
        mix = tuple(
            (OPCODE_NAMES.get(opcode, f"?{opcode}"), count)
            for opcode, count in self.opcode_counter.most_common()
        )
        return ExecutionResult(
            output="".join(self.output),
            registers=tuple(self.registers),
            pc=self.pc,
            instructions_executed=self.instructions_executed,
            image_bytes=self.image_bytes,
            max_stack_bytes=self.max_stack_bytes,
            sections=tuple(self.sections),
            opcode_counts=mix,
            data_reads=self.data_reads,
            data_writes=self.data_writes,
            dynamic_data_bytes=dynamic,
            touched_bytes=touched,
            total_memory_bytes=self.image_bytes + self.max_stack_bytes + dynamic,
        )


def _positive_integer(value: str) -> int:
    try:
        number = int(value, 10)
    except ValueError as error:
        raise argparse.ArgumentTypeError("must be an integer") from error
    if number < 1:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return number


def _split_lines(lines: list[str]) -> tuple[list[str], str]:
    """Printed lines of an operation -> (operands, result). Result is the last line."""
    if not lines:
        return [], ""
    return lines[:-1], lines[-1]


def format_report(result: ExecutionResult) -> str:
    rows: list[str] = []
    total = max(result.instructions_executed, 1)
    operations = [s for s in result.sections if s.name != PROLOGUE_NAME]
    prologue = [s for s in result.sections if s.name == PROLOGUE_NAME]

    if operations:
        rows.append("")
        rows.append("=== Resultados y metricas por operacion ===")
        rows.append("(instrucciones incluyen el despacho del menu y la impresion de cada operacion)")
        for index, section in enumerate(operations, start=1):
            operands, answer = _split_lines(section.lines)
            share = 100.0 * section.instructions / total
            rows.append("")
            rows.append(f"[{index:2d}] {section.name}")
            if operands:
                rows.append("     entradas : " + " ; ".join(operands))
            rows.append(f"     resultado: {answer if answer else '(sin salida)'}")
            rows.append(
                f"     instrucciones: {section.instructions} ({share:.1f}%) | "
                f"pila max: {section.max_stack_bytes} B | "
                f"lecturas/escrituras de datos: {section.data_reads}/{section.data_writes} | "
                f"bytes distintos escritos: {section.bytes_written}"
            )

        rows.append("")
        rows.append("=== Tabla resumen ===")
        header = f"{'#':>3}  {'Operacion':<46}{'Instr.':>9}{'%':>7}{'Pila B':>8}{'Rd':>7}{'Wr':>7}{'B esc.':>8}"
        rows.append(header)
        rows.append("-" * len(header))
        for index, section in enumerate(operations, start=1):
            rows.append(
                f"{index:>3}  {section.name[:45]:<46}{section.instructions:>9}"
                f"{100.0 * section.instructions / total:>7.1f}{section.max_stack_bytes:>8}"
                f"{section.data_reads:>7}{section.data_writes:>7}{section.bytes_written:>8}"
            )
        if prologue and prologue[0].instructions:
            rows.append(f"{'':>3}  {PROLOGUE_NAME:<46}{prologue[0].instructions:>9}"
                        f"{100.0 * prologue[0].instructions / total:>7.1f}")

    rows.append("")
    rows.append("=== Memoria ===")
    rows.append(f"Imagen cargada (codigo + datos estaticos): {result.image_bytes} bytes")
    rows.append(f"Pila maxima:                               {result.max_stack_bytes} bytes")
    rows.append(f"Datos dinamicos (fuera de imagen y pila):  {result.dynamic_data_bytes} bytes")
    rows.append(f"MEMORIA TOTAL UTILIZADA:                   {result.total_memory_bytes} bytes")
    rows.append(f"Bytes distintos accedidos (r/w/fetch):     {result.touched_bytes} bytes")
    rows.append(f"Accesos de datos: {result.data_reads} lecturas, {result.data_writes} escrituras")

    rows.append("")
    rows.append("=== Mezcla de instrucciones ===")
    for name, count in result.opcode_counts:
        rows.append(f"{name:<7}{count:>9}  {100.0 * count / total:5.1f}%")
    return "\n".join(rows)


def result_to_dict(result: ExecutionResult) -> dict:
    operations = []
    for section in result.sections:
        operands, answer = _split_lines(section.lines)
        operations.append({
            "name": section.name,
            "instructions": section.instructions,
            "max_stack_bytes": section.max_stack_bytes,
            "data_reads": section.data_reads,
            "data_writes": section.data_writes,
            "bytes_written": section.bytes_written,
            "inputs": operands,
            "result": answer,
            "printed_lines": section.lines,
        })
    return {
        "instructions_executed": result.instructions_executed,
        "memory": {
            "image_bytes": result.image_bytes,
            "max_stack_bytes": result.max_stack_bytes,
            "dynamic_data_bytes": result.dynamic_data_bytes,
            "total_bytes": result.total_memory_bytes,
            "touched_bytes": result.touched_bytes,
            "data_reads": result.data_reads,
            "data_writes": result.data_writes,
        },
        "final_pc": result.pc,
        "final_registers": list(result.registers),
        "instruction_mix": dict(result.opcode_counts),
        "operations": operations,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run a binary or hexadecimal object for the 16-bit ISA."
    )
    parser.add_argument(
        "object_file",
        type=Path,
        help="linked object file (.bin/.obj) or hexadecimal object (.hex); ASM is not accepted",
    )
    parser.add_argument(
        "--input",
        default="",
        help="Latin-1 input bytes supplied to GETC and IN traps",
    )
    parser.add_argument(
        "--max-instructions",
        type=_positive_integer,
        default=DEFAULT_INSTRUCTION_LIMIT,
        help=f"instruction limit (default: {DEFAULT_INSTRUCTION_LIMIT})",
    )
    parser.add_argument(
        "--json",
        type=Path,
        metavar="FILE",
        help="also write all metrics and per-operation results to FILE as JSON",
    )
    parser.add_argument(
        "--hide-output",
        action="store_true",
        help="do not echo the raw program output (the per-operation report is still shown)",
    )
    args = parser.parse_args(argv)

    try:
        image = load_object_file(args.object_file)
        try:
            input_bytes = args.input.encode("latin-1")
        except UnicodeEncodeError as error:
            raise InputFormatError("--input must contain Latin-1 characters only") from error
        result = Machine(image, input_bytes).run(args.max_instructions)
    except (OSError, SimulatorError, ValueError) as error:
        print(f"Simulator error: {error}", file=sys.stderr)
        return 1

    if not args.hide_output:
        print("Program output:")
        if result.output:
            print(result.output, end="" if result.output.endswith("\n") else "\n")
    print("Final registers: " + " ".join(
        f"R{index}=x{value:04X}" for index, value in enumerate(result.registers)
    ))
    print(f"Final PC: x{result.pc:04X}")
    print(f"Instructions executed: {result.instructions_executed}")
    print(f"Memory used: {result.image_bytes} bytes")
    print(f"Maximum stack used: {result.max_stack_bytes} bytes")
    print(format_report(result))
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(
            json.dumps(result_to_dict(result), indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(f"\nMetricas escritas en {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())