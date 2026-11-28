#!/usr/bin/env python3
import argparse
import re
import shlex
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

OPCODES = {
    "ADD": 0, "SUB": 1, "AND": 2, "OR": 3, "XOR": 4, "NOT": 5,
    "CMP": 6, "MOV": 7, "SHL": 8, "SHR": 9, "ASR": 10, "SWAP": 11,
    "MUL": 12, "MULH": 13, "DIV": 14, "REM": 15,
    "LOADL": 16, "LOADH": 17, "LOAD": 18, "STOREL": 19, "STOREH": 20,
    "STORE": 21, "BR": 22, "JSR": 23, "JSRR": 23, "JMP": 24, "RET": 25,
    "TRAP": 26, "HALT": 26, "NOP": 27, "SIGN": 28, "SE": 29, "TEST": 30,
    "RESERVED": 31,
    "LI16": 31, "MOVU": 31, "LDABS": 31, "STABS": 31, "ZEXT8": 31,
    "SEXT8": 31, "SHLV": 31, "ADDI16": 31, "SUBI16": 31, "ANDI16": 31,
    "ORI16": 31, "XORI16": 31, "CMP16": 31, "BR16": 31,
}

EXT_OPCODES = {
    "LI16": 0x00, "MOVU": 0x00, "LDABS": 0x01, "STABS": 0x02,
    "ZEXT8": 0x03, "SEXT8": 0x04, "SHLV": 0x05, "ADDI16": 0x06,
    "SUBI16": 0x07, "ANDI16": 0x08, "ORI16": 0x09, "XORI16": 0x0A,
    "CMP16": 0x0B, "BR16": 0x0C,
}

EXT_IMMEDIATE = {
    "LI16", "MOVU", "LDABS", "STABS", "ADDI16", "SUBI16",
    "ANDI16", "ORI16", "XORI16", "CMP16", "BR16",
}

DEFAULT_ORIGIN = 0x3000


class AssemblyError(Exception):
    pass

@dataclass
class Line:
    address: int
    text: str
    source: str
    line_number: int


@lru_cache(maxsize=8192)
def strip_comment(text: str) -> str:
    if ';' not in text and '"' not in text and "'" not in text:
        return text.strip()
    in_string = False
    quote = ""
    escaped = False
    out = []
    for char in text:
        if escaped:
            out.append(char)
            escaped = False
            continue
        if char == "\\" and in_string:
            out.append(char)
            escaped = True
            continue
        if char in ('"', "'"):
            if not in_string:
                in_string = True
                quote = char
            elif quote == char:
                in_string = False
            out.append(char)
            continue
        if char == ";" and not in_string:
            break
        out.append(char)
    return " ".join("".join(out).strip().split())


@lru_cache(maxsize=4096)
def parse_int(value: str) -> int:
    value = value.strip()
    if re.fullmatch(r"[+-]?#?0x[0-9A-Fa-f]+", value):
        return int(value.replace("#", ""), 16)
    if re.fullmatch(r"[+-]?#?x[0-9A-Fa-f]+", value):
        sign = -1 if value.startswith("-") else 1
        return sign * int(value.lstrip("+-#xX").replace("#", ""), 16)
    if re.fullmatch(r"[+-]?#?-?[0-9]+", value):
        return int(value.replace("#", ""), 10)
    if len(value) >= 2 and value[0] == "'" and value[-1] == "'":
        return ord(value[1])
    raise AssemblyError("valor entero invalido: " + value)


@lru_cache(maxsize=64)
def register(value: str) -> int:
    match = re.fullmatch(r"R([0-7])", value.strip(), re.I)
    if not match:
        raise AssemblyError("registro invalido: " + value)
    return int(match.group(1))


def signed(value: int, bits: int) -> int:
    limit = 1 << (bits - 1)
    if value < -limit or value >= (1 << (bits - 1)):
        raise AssemblyError("inmediato fuera de rango: " + str(value))
    return value & ((1 << bits) - 1)


@lru_cache(maxsize=8192)
def split_operands(text: str):
    return tuple(item.strip() for item in text.split(',')) if ',' in text else tuple(text.split())


def expression(value: str, symbols: dict, origin: int) -> int:
    value = value.strip()
    if value in symbols:
        return symbols[value]
    if re.fullmatch(r"[+-]?#?0?x[0-9A-Fa-f]+", value, re.I) or re.fullmatch(r"[+-]?#?x[0-9A-Fa-f]+", value, re.I):
        return parse_int(value)
    if re.fullmatch(r"[+-]?#?-?[0-9]+", value):
        return parse_int(value)
    match = re.fullmatch(r"([A-Za-z_][\w]*)-([A-Za-z_][\w]*)", value)
    if match:
        left, right = match.groups()
        if left in symbols and right in symbols:
            return symbols[right] - symbols[left]
    match = re.fullmatch(r"([A-Za-z_][\w]*)\s*([+-])\s*(.+)", value)
    if match:
        name, op, rest = match.groups()
        if name in symbols:
            adjustment = expression(rest, symbols, origin)
            return symbols[name] + adjustment if op == '+' else symbols[name] - adjustment
    raise AssemblyError("simbolo o expresion no definida: " + value)


class Assembler:
    def __init__(self, peephole=False):
        self.peephole = peephole
        self.code_addresses = set()
        self.symbols = {}
        self.externals = set()
        self.globals = set()
        self.memory = {}
        self.paddings = []
        self.origins = []
        self.lines = []
        self.undefined = []

    def _instruction_size(self, mnemonic):
        return 4 if mnemonic.upper() in EXT_OPCODES else 2

    def assemble(self, paths):
        modules = []
        for path in paths:
            modules.append((Path(path), Path(path).read_text(encoding="utf-8-sig")))
        self._first_pass(modules)
        missing_globals = sorted(name for name in self.globals if name not in self.symbols)
        if missing_globals:
            raise AssemblyError("simbolos .GLOBAL no definidos: " + ", ".join(missing_globals))
        self._second_pass(modules)
        if self.peephole:
            self._apply_peephole()
        if self.undefined:
            raise AssemblyError("simbolos externos no resueltos: " + ", ".join(sorted(set(self.undefined))))
        return self.memory

    def _first_pass(self, modules):
        for path, text in modules:
            lc = None
            module_origin = None
            for number, raw in enumerate(text.splitlines(), 1):
                line = strip_comment(raw)
                if not line:
                    continue
                parts = line.split(None, 1)
                head = parts[0]
                tail = parts[1].strip() if len(parts) > 1 else ""
                if head.upper() == ".ORIG":
                    lc = parse_int(tail)
                    module_origin = lc
                    if lc & 1:
                        raise AssemblyError(f"{path}:{number}: .ORIG debe ser par")
                    self.origins.append(lc)
                    continue
                if head.upper() == ".END":
                    break
                if lc is None:
                    lc = DEFAULT_ORIGIN
                    self.origins.append(lc)

                if head.upper() == ".GLOBAL":
                    declaration = tail.strip()
                    if declaration:
                        for exported_name in (name.strip() for name in declaration.split(',')):
                            if exported_name:
                                self.globals.add(exported_name)
                    continue
                if head.upper() == ".EXTERNAL":
                    declaration = tail.strip()
                    if '-' in declaration:
                        external_name = declaration.rsplit('-', 1)[1]
                    else:
                        external_name = declaration
                    self.externals.add(external_name)
                    continue

                label = None
                remaining = line
                if not head.startswith('.'):
                    if not re.match(r"^[A-Za-z_][\w]*", head):
                        raise AssemblyError(f"{path}:{number}: etiqueta invalida")
                    if len(parts) == 1:
                        if head.upper() not in OPCODES and head.upper() not in BR_MNEMONICS:
                            label = head
                            remaining = ""
                        else:
                            remaining = line
                    elif head.upper() not in OPCODES and head.upper() not in BR_MNEMONICS:
                        label = head
                        remaining = tail
                        if remaining:
                            first = remaining.split(None, 1)[0].upper()
                            if first.startswith('.'):
                                pass
                    else:
                        label = None
                        remaining = line

                if label:
                    if label in self.symbols:
                        raise AssemblyError(f"{path}:{number}: simbolo duplicado: {label}")
                    self.symbols[label] = lc

                if not remaining:
                    continue
                instruction = remaining.split(None, 1)
                mnemonic = instruction[0].upper()
                operand_text = instruction[1].strip() if len(instruction) > 1 else ""
                if mnemonic == '.FILL':
                    if lc & 1:
                        raise AssemblyError(f"{path}:{number}: .FILL debe iniciar en direccion par")
                    lc += 2
                elif mnemonic == '.BLKW':
                    if lc & 1:
                        raise AssemblyError(f"{path}:{number}: .BLKW debe iniciar en direccion par")
                    count = expression(operand_text, self.symbols, lc)
                    if count < 0:
                        raise AssemblyError(f"{path}:{number}: .BLKW no admite cantidad negativa")
                    lc += 2 * count
                elif mnemonic == '.BYTE':
                    lc += 1
                    if lc & 1:
                        lc += 1
                elif mnemonic == '.STRINGZ':
                    try:
                        value = shlex.split(operand_text)[0]
                    except Exception:
                        raise AssemblyError(f"{path}:{number}: .STRINGZ invalida")
                    lc += len(value.encode('utf-8')) + 1
                    if lc & 1:
                        lc += 1
                elif mnemonic == '.ALIGN2':
                    if lc & 1:
                        lc += 1
                elif mnemonic.startswith('.'):
                    if mnemonic not in ('.GLOBAL', '.EXTERNAL'):
                        raise AssemblyError(f"{path}:{number}: directiva desconocida: {mnemonic}")
                else:
                    if lc & 1:
                        raise AssemblyError(f"{path}:{number}: instruccion en direccion impar")
                    lc += self._instruction_size(mnemonic)

    def _second_pass(self, modules):
        for path, text in modules:
            lc = None
            for number, raw in enumerate(text.splitlines(), 1):
                line = strip_comment(raw)
                if not line:
                    continue
                parts = line.split(None, 1)
                head = parts[0]
                tail = parts[1].strip() if len(parts) > 1 else ""
                if head.upper() == '.ORIG':
                    lc = parse_int(tail)
                    continue
                if head.upper() == '.END':
                    break
                if lc is None:
                    lc = DEFAULT_ORIGIN
                if head.upper() == '.EXTERNAL':
                    continue
                if head.upper() == '.GLOBAL':
                    continue

                label = None
                remaining = line
                if not head.startswith('.'):
                    if len(parts) == 1:
                        if head.upper() not in OPCODES and head.upper() not in BR_MNEMONICS:
                            label = head
                            remaining = ""
                        else:
                            remaining = line
                    elif head.upper() in OPCODES or head.upper() in BR_MNEMONICS or head.upper().startswith('.'):
                        remaining = line
                    else:
                        label = head
                        remaining = tail

                if not remaining:
                    continue
                instruction = remaining.split(None, 1)
                mnemonic = instruction[0].upper()
                operand_text = instruction[1].strip() if len(instruction) > 1 else ""

                if mnemonic == '.FILL':
                    if operand_text in self.externals and operand_text not in self.symbols:
                        self.undefined.append(operand_text)
                        value = 0
                    else:
                        value = expression(operand_text, self.symbols, lc)
                    self._store_word(lc, value & 0xffff)
                    lc += 2
                elif mnemonic == '.BLKW':
                    count = expression(operand_text, self.symbols, lc)
                    for _ in range(count):
                        self._store_word(lc, 0)
                        lc += 2
                elif mnemonic == '.BYTE':
                    value = expression(operand_text, self.symbols, lc)
                    self._store_byte(lc, value & 0xff)
                    lc += 1
                    if lc & 1:
                        self.paddings.append((lc, path, number))
                        self._store_byte(lc, 0)
                        lc += 1
                elif mnemonic == '.STRINGZ':
                    try:
                        value = shlex.split(operand_text)[0]
                    except Exception:
                        raise AssemblyError(f"{path}:{number}: .STRINGZ invalida")
                    data = value.encode('utf-8') + b'\0'
                    for byte in data:
                        self._store_byte(lc, byte)
                        lc += 1
                    if lc & 1:
                        self.paddings.append((lc, path, number))
                        self._store_byte(lc, 0)
                        lc += 1
                elif mnemonic == '.ALIGN2':
                    if lc & 1:
                        self.paddings.append((lc, path, number))
                        lc += 1
                elif mnemonic.startswith('.'):
                    continue
                else:
                    encoded = self._encode(mnemonic, operand_text, lc, path, number)
                    words = encoded if isinstance(encoded, (list, tuple)) else (encoded,)
                    for word in words:
                        self.code_addresses.add(lc)
                        self._store_word(lc, word)
                        lc += 2

    def _read_word(self, address):
        if address not in self.memory or address + 1 not in self.memory:
            return None
        return self.memory[address] | (self.memory[address + 1] << 8)

    def _replace_word(self, address, value):
        self.memory[address] = value & 0xff
        self.memory[address + 1] = (value >> 8) & 0xff

    def _apply_peephole(self):
        skip = set()
        for address in sorted(self.code_addresses):
            word = self._read_word(address)
            if word is not None and ((word >> 11) & 31) == OPCODES['RESERVED']:
                if (word & 0xff) in set(EXT_OPCODES.values()):
                    skip.add(address + 2)
        for address in sorted(self.code_addresses):
            if address in skip:
                continue
            first = self._read_word(address)
            if first is None or ((first >> 11) & 31) == OPCODES['RESERVED']:
                continue
            if address + 2 not in self.code_addresses:
                continue
            second = self._read_word(address + 2)
            if second is None:
                continue
            opcode = (first >> 11) & 31
            if opcode != OPCODES['MOV']:
                continue
            rd = (first >> 8) & 7
            if (second >> 11) & 31 != OPCODES['SHL'] or not second & 1:
                continue
            if (second >> 8) & 7 != rd:
                continue
            immediate = first & 0xff
            if immediate & 0x80:
                immediate -= 0x100
            shift = (second >> 1) & 0x7f
            if shift > 15:
                continue
            value = (immediate << shift) & 0xffff
            self._replace_word(address, (31 << 11) | (rd << 8) | EXT_OPCODES['LI16'])
            self._replace_word(address + 2, value)
            if address + 4 in self.code_addresses:
                third = self._read_word(address + 4)
                if third is not None:
                    not_opcode = (third >> 11) & 31
                    not_rd = (third >> 8) & 7
                    not_rs1 = (third >> 5) & 7
                    not_rs2 = (third >> 2) & 7
                    if (not_opcode == OPCODES['NOT'] and not third & 1
                            and not_rd == rd and not_rs1 == rd and not_rs2 == rd):
                        self._replace_word(address + 2, value ^ 0xffff)
                        self._replace_word(address + 4, OPCODES['NOP'] << 11)

    def _store_byte(self, address, value):
        if address < 0 or address > 0xffff:
            raise AssemblyError("direccion fuera de memoria: " + str(address))
        if address in self.memory:
            raise AssemblyError("solapamiento de modulo en direccion: 0x%04X" % address)
        self.memory[address] = value & 0xff

    def _store_word(self, address, value):
        if address & 1:
            raise AssemblyError("palabra almacenada en direccion impar: " + hex(address))
        if address > 0xfffe:
            raise AssemblyError("direccion fuera de memoria: " + hex(address))
        self._store_byte(address, value & 0xff)
        self._store_byte(address + 1, (value >> 8) & 0xff)

    def _encode(self, mnemonic, operands, lc, path, number):
        mn = mnemonic.upper()
        args = split_operands(operands)
        if mn in BR_MNEMONICS:
            return self._encode_br(mn, operands, lc)
        if mn == 'HALT':
            if args:
                raise AssemblyError("HALT no acepta operandos")
            return (OPCODES['TRAP'] << 11)
        if mn not in OPCODES:
            raise AssemblyError(f"{path}:{number}: mnemónico desconocido: {mnemonic}")
        opcode = OPCODES[mn]
        args = split_operands(operands)

        if mn in EXT_OPCODES:
            return self._encode_ext(mn, args, lc, path, number)

        if mn in ('ADD','SUB','AND','OR','XOR','CMP','SHL','SHR','ASR','MUL','MULH','DIV','REM'):
            if len(args) == 3:
                rd = register(args[0])
                rs1 = register(args[1])
                if args[2].upper().startswith('R'):
                    rs2 = register(args[2])
                    mode = 1 << 1 if mn == 'CMP' else 0
                    return (opcode << 11) | (rd << 8) | (rs1 << 5) | (rs2 << 2) | mode
                if mn not in ('ADD','SUB','AND','OR','XOR','CMP','SHL','SHR','ASR'):
                    raise AssemblyError("inmediato no valido para " + mn)
                if rs1 != rd:
                    raise AssemblyError(f"{path}:{number}: formato RI requiere el mismo registro destino y origen")
                value = expression(args[2], self.symbols, lc)
                return self._encode_alu_immediate(opcode, rd, mn, value)
            if len(args) == 2 and mn in ('ADD','SUB','AND','OR','XOR','CMP','SHL','SHR','ASR'):
                rd = register(args[0])
                if args[1].upper().startswith('R') and mn == 'CMP':
                    return (opcode << 11) | (rd << 8) | (register(args[1]) << 5)
                if args[1].upper().startswith('R'):
                    raise AssemblyError("formato RI requiere un inmediato")
                value = expression(args[1], self.symbols, lc)
                return self._encode_alu_immediate(opcode, rd, mn, value)
        if mn == 'NOT':
            if len(args) != 2:
                raise AssemblyError("NOT requiere dos registros")
            rd, rs = args
            return (opcode << 11) | (register(rd) << 8) | (register(rs) << 5)
        if mn in ('MOV','SE'):
            if len(args) != 2:
                raise AssemblyError("formato de operandos invalido: " + mn)
            rd = register(args[0])
            if re.fullmatch(r"R[0-7]", args[1], re.I):
                raise AssemblyError(mn + " solo acepta inmediato; use OR Rd, Rs, R0 para copiar")
            value = expression(args[1], self.symbols, lc)
            return (opcode << 11) | (rd << 8) | signed(value, 8)
        if mn == 'SIGN':
            if len(args) != 2:
                raise AssemblyError("SIGN requiere dos registros")
            return (opcode << 11) | (register(args[0]) << 8) | (register(args[1]) << 5)
        if mn == 'TEST':
            if len(args) == 1:
                return (opcode << 11) | (register(args[0]) << 8)
            if len(args) == 2:
                rd = register(args[0])
                if args[1].upper().startswith('R'):
                    return (opcode << 11) | (rd << 8) | (1 << 1) | (register(args[1]) << 2)
                value = expression(args[1], self.symbols, lc)
                return (opcode << 11) | (rd << 8) | 1 | (signed(value, 7) << 1)
            raise AssemblyError("TEST requiere uno o dos operandos")
        if mn == 'SWAP':
            if len(args) == 1:
                return (opcode << 11) | (register(args[0]) << 8)
            if len(args) == 2:
                return (opcode << 11) | (register(args[0]) << 8) | 1 | (register(args[1]) << 1)
            raise AssemblyError("SWAP requiere uno o dos registros")
        if mn in ('LOADL','LOADH','LOAD','STOREL','STOREH','STORE'):
            match = re.fullmatch(r"([^,]+?)\s*(?:,\s*|\s+)([+-]?[^()]*)\((R[0-7])\)", operands)
            if not match:
                match = re.fullmatch(r"([^,\s]+)\s*,\s*([^()]+)\((R[0-7])\)", operands)
            if not match:
                raise AssemblyError("formato de memoria invalido: " + operands)
            rt = register(match.group(1).strip())
            imm = signed(expression(match.group(2).strip(), self.symbols, lc), 5)
            rb = register(match.group(3))
            return (opcode << 11) | (rt << 8) | (rb << 5) | (imm & 31)
        if mn == 'NOP':
            if args:
                raise AssemblyError("NOP no acepta operandos")
            return (opcode << 11)
        if mn == 'RESERVED':
            return (opcode << 11)
        if mn == 'RET':
            if len(args) == 1:
                rb = register(args[0])
            elif not args:
                rb = 7
            else:
                raise AssemblyError("RET admite solo Rn o ningun operando")
            return (opcode << 11) | (rb << 5)
        if mn == 'JMP':
            if len(args) != 1:
                raise AssemblyError("JMP requiere un registro")
            return (opcode << 11) | (register(args[0]) << 5)
        if mn == 'JSR':
            if len(args) != 1:
                raise AssemblyError("JSR requiere una etiqueta")
            if args[0] in self.externals and args[0] not in self.symbols:
                self.undefined.append(args[0])
                target = lc + 2
            else:
                target = expression(args[0], self.symbols, lc)
            offset = target - (lc + 2)
            if offset & 1:
                raise AssemblyError("destino JSR impar")
            if offset < -512 or offset > 511:
                raise AssemblyError("desplazamiento JSR fuera de rango")
            return (opcode << 11) | (offset & 0x3ff)
        if mn == 'JSRR':
            if len(args) != 1:
                raise AssemblyError("JSRR requiere un registro")
            rb = register(args[0])
            return (opcode << 11) | (1 << 10) | (rb << 5)
        if mn == 'TRAP':
            if len(args) != 1:
                raise AssemblyError("TRAP requiere vector")
            vector = expression(args[0], self.symbols, lc)
            if vector < 0 or vector > 0x7ff:
                raise AssemblyError("vector TRAP fuera de rango")
            return (opcode << 11) | vector
        raise AssemblyError("codificacion no implementada: " + mn)

    def _encode_ext(self, mnemonic, args, lc, path, number):
        func = EXT_OPCODES[mnemonic]
        first = (OPCODES[mnemonic] << 11) | func
        if mnemonic == 'BR16':
            expected = 1
        elif mnemonic in ('LI16', 'MOVU', 'LDABS', 'STABS', 'ADDI16', 'SUBI16',
                          'ANDI16', 'ORI16', 'XORI16', 'CMP16', 'ZEXT8', 'SEXT8'):
            expected = 2
        elif mnemonic == 'SHLV':
            expected = 3
        else:
            raise AssemblyError("codificacion EXT no implementada: " + mnemonic)
        if len(args) != expected:
            raise AssemblyError(f"{path}:{number}: {mnemonic} requiere {expected} operando(s)")

        if mnemonic == 'BR16':
            target = expression(args[0], self.symbols, lc)
            if target & 1:
                raise AssemblyError(f"{path}:{number}: destino BR16 impar")
            return (first, target & 0xffff)

        rd = register(args[0])
        first |= rd << 8
        if mnemonic in EXT_IMMEDIATE:
            value = expression(args[1], self.symbols, lc)
            if value < -32768 or value > 65535:
                raise AssemblyError(f"{path}:{number}: valor EXT fuera de rango: {value}")
            return (first, value & 0xffff)
        if mnemonic in ('ZEXT8', 'SEXT8'):
            return (first, (register(args[1]) << 13) & 0xffff)
        return (first, ((register(args[1]) << 13) | (register(args[2]) << 10)) & 0xffff)

    def _encode_alu_immediate(self, opcode, rd, mnemonic, value):
        if mnemonic in ('SHL','SHR','ASR'):
            if value < 0 or value > 15:
                raise AssemblyError("desplazamiento fuera de rango: " + str(value))
            imm = value
        elif mnemonic in ('AND','OR','XOR') and 0 <= value <= 127:
            imm = value
        else:
            imm = signed(value, 7)
        return (opcode << 11) | (rd << 8) | 1 | (imm << 1)

    def _encode_br(self, mnemonic, operands, lc):
        condition_codes = {
            "BR": 7, "BRP": 1, "BRZ": 2, "BRNZ": 3, "BRN": 4,
            "BRNP": 5, "BRNZP": 6, "BRZP": 6,
        }
        cond = condition_codes[mnemonic]
        args = split_operands(operands)
        if len(args) != 1:
            raise AssemblyError("BR requiere una etiqueta")
        target = expression(args[0], self.symbols, lc)
        if target & 1:
            raise AssemblyError("destino BR impar")
        offset = target - (lc + 2)
        if offset < -128 or offset > 127:
            raise AssemblyError("desplazamiento BR fuera de rango")
        return (OPCODES['BR'] << 11) | (cond << 8) | (offset & 0xff)

BR_MNEMONICS = {'BR','BRP','BRZ','BRNZ','BRN','BRNP','BRNZP','BRZP'}


def write_output(path, memory, origin, fmt):
    if not memory:
        raise AssemblyError("imagen vacia")
    addresses = sorted(memory)
    minimum = min(addresses)
    maximum = max(addresses)
    if minimum != origin:
        raise AssemblyError("la imagen comienza en una direccion distinta de .ORIG")
    data = bytearray([origin & 0xff, (origin >> 8) & 0xff])
    for address in range(origin, maximum + 1):
        data.append(memory.get(address, 0))
    if fmt == 'bin':
        Path(path).write_bytes(bytes(data))
    elif fmt == 'dec':
        Path(path).write_text(' '.join(str(byte) for byte in data) + '\n', encoding='ascii')
    else:
        Path(path).write_text(' '.join(f'{byte:02X}' for byte in data) + '\n', encoding='ascii')


def main(argv=None):
    parser = argparse.ArgumentParser(description='Ensamblador y enlazador de la ISA de 16 bits')
    parser.add_argument('sources', nargs='+', help='archivos .asm')
    parser.add_argument('-o', '--output', default='program.hex', help='archivo de salida')
    parser.add_argument('--format', choices=('hex','bin','dec'), default='hex')
    parser.add_argument('--peephole', action='store_true', help='fusiona MOV+SHL en LI16')
    args = parser.parse_args(argv)
    assembler = Assembler(peephole=args.peephole)
    try:
        memory = assembler.assemble(args.sources)
        if not assembler.origins:
            raise AssemblyError("no se encontro .ORIG")
        origin = assembler.origins[0]
        write_output(args.output, memory, origin, args.format)
        for address, path, number in assembler.paddings:
            print(f"Alineacion: padding 0x00 agregado en 0x{address:04X} ({path}:{number})")
        print(f"Ensamblado: {args.output} ({len(memory)} bytes)")
        print(f"Origen: 0x{origin:04X}")
        return 0
    except (AssemblyError, OSError) as exc:
        print("Error:", exc, file=sys.stderr)
        return 1

if __name__ == '__main__':
    raise SystemExit(main())
