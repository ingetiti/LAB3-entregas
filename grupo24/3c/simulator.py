#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path


SIGN16 = tuple(value - 65536 if value & 0x8000 else value for value in range(65536))
SIGN8 = tuple(value - 256 if value & 0x80 else value for value in range(256))

EXT_LI16 = 0x00
EXT_LDABS = 0x01
EXT_STABS = 0x02
EXT_ZEXT8 = 0x03
EXT_SEXT8 = 0x04
EXT_SHLV = 0x05
EXT_ADDI16 = 0x06
EXT_SUBI16 = 0x07
EXT_ANDI16 = 0x08
EXT_ORI16 = 0x09
EXT_XORI16 = 0x0A
EXT_CMP16 = 0x0B
EXT_BR16 = 0x0C
EXT_LENGTHS = frozenset(range(EXT_LI16, EXT_BR16 + 1))


class ExecutionError(Exception):
    pass


class AlignmentError(ExecutionError):
    pass


class Simulator:
    OPCODES = {
        "ADD": 0, "SUB": 1, "AND": 2, "OR": 3, "XOR": 4,
        "NOT": 5, "CMP": 6, "MOV": 7, "SHL": 8, "SHR": 9,
        "ASR": 10, "SWAP": 11, "MUL": 12, "MULH": 13,
        "DIV": 14, "REM": 15, "LOADL": 16, "LOADH": 17,
        "LOAD": 18, "STOREL": 19, "STOREH": 20, "STORE": 21,
        "BR": 22, "JSR": 23, "JMP": 24, "RET": 25,
        "TRAP": 26, "NOP": 27, "SIGN": 28, "SE": 29,
        "TEST": 30, "RESERVED": 31,
        "LI16": 31, "MOVU": 31, "LDABS": 31, "STABS": 31, "ZEXT8": 31,
        "SEXT8": 31, "SHLV": 31, "ADDI16": 31, "SUBI16": 31,
        "ANDI16": 31, "ORI16": 31, "XORI16": 31, "CMP16": 31, "BR16": 31,
    }

    def __init__(self, memory=None, pc=None, input_chars=None, batch=False):
        self.memory = bytearray(memory if memory is not None else 65536)
        self.registers = [0] * 8
        self.pc = pc if pc is not None else 0
        self.initial_pc = self.pc
        self.flags = {"N": False, "Z": True, "P": False, "C": False, "V": False}
        self.instructions = 0
        self.halted = False
        self.batch = batch
        self.input_chars = list(input_chars or [])
        self.occupied = set()
        self.peak_occupied = 0
        self.code_bytes = 0
        self.written = set()
        self.image_bytes = 0

    def _load_bytes(self, raw):
        if len(raw) < 4:
            raise ExecutionError("imagen demasiado corta")
        origin = raw[0] | (raw[1] << 8)
        if origin & 1:
            raise ExecutionError("direccion de carga origen impar")
        image = raw[2:]
        if origin + len(image) > 65536:
            raise ExecutionError("imagen excede los 65536 bytes")
        self.memory[origin:origin + len(image)] = image
        self.pc = origin
        self.initial_pc = origin
        self.occupied.update(range(origin, origin + len(image)))
        self.peak_occupied = len(self.occupied)
        self.code_bytes = len(image)
        self.written.update(range(origin, origin + len(image)))
        self.image_bytes = len(raw)
        return origin, len(image)

    def load_image(self, path):
        try:
            raw = Path(path).read_bytes()
        except OSError as exc:
            raise ExecutionError(str(exc)) from exc
        return self._load_bytes(raw)

    def load_hex(self, path):
        try:
            text = Path(path).read_text(encoding="ascii")
        except OSError as exc:
            raise ExecutionError(str(exc)) from exc
        raw = bytearray()
        for token in text.split():
            try:
                value = int(token, 16)
            except ValueError as exc:
                raise ExecutionError("byte hexadecimal invalido: " + token) from exc
            if value < 0 or value > 255:
                raise ExecutionError("byte hexadecimal fuera de rango: " + token)
            raw.append(value)
        return self._load_bytes(raw)

    def load_memory(self, memory, origin):
        if origin & 1:
            raise ExecutionError("direccion de carga origen impar")
        if not memory:
            raise ExecutionError("memoria vacia")
        minimum = min(memory)
        maximum = max(memory)
        if minimum != origin:
            raise ExecutionError("la memoria ensamblada no comienza en .ORIG")
        if maximum >= 65536:
            raise ExecutionError("imagen excede los 65536 bytes")
        for address, value in memory.items():
            self.memory[address] = value
        self.pc = origin
        self.initial_pc = origin
        self.occupied.update(memory)
        self.peak_occupied = len(self.occupied)
        self.written.update(memory)
        self.code_bytes = len(memory)
        self.image_bytes = maximum - origin + 1
        return origin, self.image_bytes

    def set_result_flags(self, value):
        value &= 0xffff
        signed = SIGN16[value]
        self.flags["N"] = signed < 0
        self.flags["Z"] = value == 0
        self.flags["P"] = signed > 0

    def read_word(self, address):
        if address & 1:
            raise AlignmentError(f"carga de palabra en direccion impar: 0x{address:04X}")
        if address < 0 or address + 1 >= 65536:
            raise ExecutionError(f"direccion fuera de rango: 0x{address:04X}")
        return self.memory[address] | (self.memory[address + 1] << 8)

    def write_word(self, address, value):
        if address & 1:
            raise AlignmentError(f"almacenamiento de palabra en direccion impar: 0x{address:04X}")
        if address < 0 or address + 1 >= 65536:
            raise ExecutionError(f"direccion fuera de rango: 0x{address:04X}")
        self.memory[address] = value & 0xff
        self.memory[address + 1] = (value >> 8) & 0xff
        self.occupied.add(address)
        self.occupied.add(address + 1)
        self.written.add(address)
        self.written.add(address + 1)
        self.peak_occupied = max(self.peak_occupied, len(self.occupied))

    def read_byte(self, address):
        if address < 0 or address >= 65536:
            raise ExecutionError(f"direccion fuera de rango: 0x{address:04X}")
        return self.memory[address]

    def write_byte(self, address, value):
        if address < 0 or address >= 65536:
            raise ExecutionError(f"direccion fuera de rango: 0x{address:04X}")
        self.memory[address] = value & 0xff
        self.occupied.add(address)
        self.written.add(address)
        self.peak_occupied = max(self.peak_occupied, len(self.occupied))

    def reset_counters(self):
        self.instructions = 0
        self.occupied.clear()
        self.peak_occupied = 0
        self.written.clear()
        self.code_bytes = 0

    def check_destination(self, destination):
        if destination < 0 or destination >= 65536:
            raise ExecutionError(f"salto fuera de rango: 0x{destination & 0xffff:04X}")
        if destination & 1:
            raise AlignmentError(f"salto a direccion impar: 0x{destination:04X}")
        return destination

    def condition_met(self, code):
        if code == 0:
            return False
        if code == 1:
            return self.flags["P"]
        if code == 2:
            return self.flags["Z"]
        if code == 3:
            return self.flags["N"] or self.flags["Z"]
        if code == 4:
            return self.flags["N"]
        if code == 5:
            return self.flags["N"] or self.flags["P"]
        if code == 6:
            return self.flags["N"] or self.flags["Z"] or self.flags["P"]
        return True

    def execute(self, max_instructions=1000000):
        memory = self.memory
        while not self.halted:
            if self.instructions >= max_instructions:
                raise ExecutionError("limite de instrucciones excedido")
            if self.pc & 1:
                raise AlignmentError(f"fetch en direccion impar: 0x{self.pc:04X}")
            if self.pc > 65534:
                raise ExecutionError(f"fetch fuera de rango: 0x{self.pc:04X}")

            current_pc = self.pc
            ir = memory[current_pc] | (memory[current_pc + 1] << 8)
            opcode = (ir >> 11) & 31
            length = 4 if opcode == 31 and (ir & 0xff) in EXT_LENGTHS else 2
            if current_pc + length > 0xffff:
                raise ExecutionError(f"fetch fuera de rango: 0x{current_pc:04X}")
            extension = memory[current_pc + 2] | (memory[current_pc + 3] << 8) if length == 4 else None
            self.pc = (current_pc + length) & 0xffff
            self.instructions += 1
            self.execute_instruction(ir, current_pc, extension)
        return self.registers[:], self.instructions

    def execute_instruction(self, ir, pc, extension=None):
        opcode = (ir >> 11) & 31
        rd = (ir >> 8) & 7
        rs1 = (ir >> 5) & 7
        rs2 = (ir >> 2) & 7
        imm8 = ir & 0xff
        imm5 = ir & 31
        immediate_mode = bool(ir & 1)

        if imm5 & 16:
            imm5_signed = imm5 - 32
        else:
            imm5_signed = imm5

        if imm8 & 128:
            imm8_signed = imm8 - 256
        else:
            imm8_signed = imm8

        imm7 = (ir >> 1) & 0x7f
        imm7_signed = imm7 - 128 if imm7 & 64 else imm7

        if opcode in (0, 1, 2, 3, 4) and immediate_mode:
            left = self.registers[rd]
            if opcode == 0:
                result = left + imm7_signed
                self.flags["C"] = left + imm7_signed > 0xffff
                signed_result = SIGN16[left] + imm7_signed
                self.flags["V"] = signed_result < -32768 or signed_result > 32767
            elif opcode == 1:
                result = left - imm7_signed
                self.flags["C"] = (left & 0xffff) >= (imm7_signed & 0xffff)
                signed_result = SIGN16[left] - imm7_signed
                self.flags["V"] = signed_result < -32768 or signed_result > 32767
            elif opcode == 2:
                result = left & imm7
            elif opcode == 3:
                result = left | imm7
            else:
                result = left ^ imm7
            self.registers[rd] = result & 0xffff
            self.set_result_flags(result)

        elif opcode in (0, 1, 2, 3, 4):
            left = self.registers[rs1]
            right = self.registers[rs2]
            if opcode == 0:
                result = left + right
                self.flags["C"] = result > 0xffff
                signed_result = SIGN16[left] + SIGN16[right]
                self.flags["V"] = signed_result < -32768 or signed_result > 32767
            elif opcode == 1:
                result = left - right
                left_unsigned = left & 0xffff
                right_unsigned = right & 0xffff
                self.flags["C"] = left_unsigned >= right_unsigned
                signed_result = SIGN16[left] - SIGN16[right]
                self.flags["V"] = signed_result < -32768 or signed_result > 32767
            elif opcode == 2:
                result = left & right
            elif opcode == 3:
                result = left | right
            else:
                result = left ^ right
            self.registers[rd] = result & 0xffff
            self.set_result_flags(result)

        elif opcode == 5:
            rs = (ir >> 5) & 7
            self.registers[rd] = (~self.registers[rs]) & 0xffff
            self.set_result_flags(self.registers[rd])

        elif opcode == 6:
            if immediate_mode:
                left = SIGN16[self.registers[rd]]
                right = imm7_signed
            elif ir & 2:
                left = SIGN16[self.registers[rs1]]
                right = SIGN16[self.registers[rs2]]
            else:
                left = SIGN16[self.registers[rd]]
                right = SIGN16[self.registers[rs1]]
            result = left - right
            truncated = result & 0xffff
            self.flags["N"] = SIGN16[truncated] < 0
            self.flags["Z"] = truncated == 0
            self.flags["P"] = SIGN16[truncated] > 0
            left_unsigned = left & 0xffff
            right_unsigned = right & 0xffff
            self.flags["C"] = left_unsigned >= right_unsigned
            self.flags["V"] = result < -32768 or result > 32767

        elif opcode == 7:
            rd = (ir >> 8) & 7
            self.registers[rd] = imm8_signed & 0xffff
            self.set_result_flags(self.registers[rd])

        elif opcode in (8, 9, 10):
            if immediate_mode:
                count = imm7
            else:
                count = self.registers[rs2] & 31
            if count > 15:
                raise ExecutionError("desplazamiento mayor a 15")
            value = self.registers[rd] if immediate_mode else self.registers[rs1]
            if count == 0:
                result = value
            elif opcode == 8:
                result = (value << count) & 0xffff
            elif opcode == 9:
                result = value >> count
            else:
                result = (SIGN16[value] >> count) & 0xffff
            self.registers[rd] = result
            self.set_result_flags(result)

        elif opcode == 11:
            rs = ((ir >> 1) & 7) if immediate_mode else rd
            value = self.registers[rs]
            self.registers[rd] = ((value << 8) | (value >> 8)) & 0xffff
            self.set_result_flags(self.registers[rd])

        elif opcode in (12, 13, 14, 15):
            left = SIGN16[self.registers[rs1]]
            right = SIGN16[self.registers[rs2]]
            if opcode == 12:
                result = (left * right) & 0xffff
            elif opcode == 13:
                result = ((left * right) >> 16) & 0xffff
            elif right == 0:
                raise ExecutionError("division por cero")
            elif opcode == 14:
                quotient = abs(left) // abs(right)
                result = -quotient if (left < 0) != (right < 0) else quotient
            else:
                remainder = abs(left) % abs(right)
                result = -remainder if left < 0 else remainder
            self.registers[rd] = result & 0xffff
            self.set_result_flags(result)

        elif opcode in (16, 17, 18, 19, 20, 21):
            rt = rd
            rb = rs1
            address = self.registers[rb] + imm5_signed
            if address < 0 or address >= 65536:
                raise ExecutionError(f"direccion efectiva fuera de rango: 0x{address & 0xffff:04X}")
            if opcode == 16:
                self.registers[rt] = self.read_byte(address)
                self.set_result_flags(self.registers[rt])
            elif opcode == 17:
                self.registers[rt] = self.read_byte(address) << 8
                self.set_result_flags(self.registers[rt])
            elif opcode == 18:
                self.registers[rt] = self.read_word(address)
                self.set_result_flags(self.registers[rt])
            elif opcode == 19:
                self.write_byte(address, self.registers[rt] & 0xff)
            elif opcode == 20:
                self.write_byte(address, (self.registers[rt] >> 8) & 0xff)
            else:
                self.write_word(address, self.registers[rt])

        elif opcode == 22:
            code = (ir >> 8) & 7
            offset = ir & 0xff
            if offset & 128:
                offset -= 256
            if self.condition_met(code):
                self.pc = self.check_destination(pc + 2 + offset)

        elif opcode == 23:
            if (ir & (1 << 10)) != 0:
                rb = (ir >> 5) & 7
                destination = self.registers[rb]
            else:
                offset = ir & 0x3ff
                if offset & 0x200:
                    offset -= 0x400
                destination = pc + 2 + offset
            self.registers[7] = (pc + 2) & 0xffff
            self.pc = self.check_destination(destination)

        elif opcode == 24:
            rb = (ir >> 5) & 7
            self.pc = self.check_destination(self.registers[rb])

        elif opcode == 25:
            rb = (ir >> 5) & 7
            if rb == 0:
                rb = 7
            if rb == 7 and self.registers[rb] == 0:
                self.halted = True
                return
            self.pc = self.check_destination(self.registers[rb])

        elif opcode == 26:
            vector = ir & 0x7ff
            if vector == 0:
                self.halted = True
            elif vector == 0x20:
                if self.input_chars:
                    char = ord(self.input_chars.pop(0))
                elif self.batch:
                    char = 10
                else:
                    char = ord(sys.stdin.read(1) or '\n')
                self.registers[0] = char & 0xffff
            elif vector == 0x21:
                sys.stdout.write(chr(self.registers[0] & 0xff))
                sys.stdout.flush()
            elif vector == 0x22:
                address = self.registers[0]
                while True:
                    char = self.read_byte(address)
                    if char == 0:
                        break
                    sys.stdout.write(chr(char))
                    address = (address + 1) & 0xffff
            elif vector == 0x23:
                if self.input_chars:
                    chars = []
                    while self.input_chars:
                        char = self.input_chars.pop(0)
                        if char in " \t\r\n":
                            break
                        chars.append(char)
                    line = "".join(chars)
                elif self.batch:
                    line = ""
                else:
                    line = sys.stdin.readline()
                try:
                    value = int(line.strip())
                except ValueError:
                    value = 0
                self.registers[0] = value & 0xffff
            elif vector == 0x25:
                self.halted = True
            else:
                raise ExecutionError(f"trap desconocido: 0x{vector:03X}")

        elif opcode == 27:
            pass

        elif opcode == 28:
            rs = (ir >> 5) & 7
            self.registers[rd] = SIGN8[self.registers[rs] & 0xff] & 0xffff
            self.set_result_flags(self.registers[rd])

        elif opcode == 29:
            self.registers[rd] = imm8_signed & 0xffff
            self.set_result_flags(self.registers[rd])

        elif opcode == 30:
            rs = (ir >> 8) & 7
            if immediate_mode:
                result = self.registers[rs] & (imm7_signed & 0xffff)
            elif ir & (1 << 1):
                result = self.registers[rs] & self.registers[(ir >> 2) & 7]
            else:
                result = self.registers[rs] & self.registers[rs]
            self.set_result_flags(result)

        elif opcode == 31:
            func = ir & 0xff
            if func not in EXT_LENGTHS or extension is None:
                raise ExecutionError("opcode RESERVED ejecutado")
            if func in (EXT_LI16, EXT_LDABS):
                if func == EXT_LI16:
                    value = extension
                else:
                    address = extension
                    if address & 1:
                        raise AlignmentError(f"carga de palabra en direccion impar: 0x{address:04X}")
                    value = self.read_word(address)
                self.registers[rd] = value & 0xffff
                self.set_result_flags(self.registers[rd])
            elif func == EXT_STABS:
                self.write_word(extension, self.registers[rd])
            elif func in (EXT_ZEXT8, EXT_SEXT8):
                rs = (extension >> 13) & 7
                if func == EXT_ZEXT8:
                    value = self.registers[rs] & 0xff
                else:
                    value = SIGN8[self.registers[rs] & 0xff] & 0xffff
                self.registers[rd] = value
                self.set_result_flags(value)
            elif func == EXT_SHLV:
                rs1 = (extension >> 13) & 7
                rs2 = (extension >> 10) & 7
                count = self.registers[rs2] & 15
                value = self.registers[rs1]
                result = (value << count) & 0xffff if count else value
                self.registers[rd] = result
                self.set_result_flags(result)
            elif func in (EXT_ADDI16, EXT_SUBI16, EXT_ANDI16, EXT_ORI16, EXT_XORI16):
                left = self.registers[rd]
                right = extension
                signed_result = SIGN16[left]
                if func == EXT_ADDI16:
                    result = left + right
                    signed_result += SIGN16[right]
                    self.flags["C"] = result > 0xffff
                    self.flags["V"] = signed_result < -32768 or signed_result > 32767
                elif func == EXT_SUBI16:
                    result = left - right
                    signed_result -= SIGN16[right]
                    self.flags["C"] = (left & 0xffff) >= (right & 0xffff)
                    self.flags["V"] = signed_result < -32768 or signed_result > 32767
                elif func == EXT_ANDI16:
                    result = left & right
                elif func == EXT_ORI16:
                    result = left | right
                else:
                    result = left ^ right
                self.registers[rd] = result & 0xffff
                self.set_result_flags(result)
            elif func == EXT_CMP16:
                left = SIGN16[self.registers[rd]]
                right = SIGN16[extension]
                result = left - right
                truncated = result & 0xffff
                self.flags["N"] = SIGN16[truncated] < 0
                self.flags["Z"] = truncated == 0
                self.flags["P"] = SIGN16[truncated] > 0
                self.flags["C"] = (self.registers[rd] & 0xffff) >= (extension & 0xffff)
                self.flags["V"] = result < -32768 or result > 32767
            elif func == EXT_BR16:
                if extension & 1:
                    raise AlignmentError(f"salto BR16 a direccion impar: 0x{extension:04X}")
                if extension > 0xfffe:
                    raise ExecutionError(f"salto fuera de rango: 0x{extension:04X}")
                self.pc = extension

        else:
            raise ExecutionError(f"opcode desconocido: {opcode}")

    def load_decimal(self, path):
        try:
            tokens = Path(path).read_text(encoding="ascii").split()
        except OSError as exc:
            raise ExecutionError(str(exc)) from exc
        if not tokens:
            raise ExecutionError("imagen decimal vacia")
        raw = bytearray()
        for token in tokens:
            try:
                value = int(token, 10)
            except ValueError as exc:
                raise ExecutionError("valor decimal invalido: " + token) from exc
            if value < 0 or value > 255:
                raise ExecutionError("byte decimal fuera de rango: " + token)
            raw.append(value)
        return self._load_bytes(raw)

def main(argv=None):
    parser = argparse.ArgumentParser(description="Simulador funcional de la ISA de 16 bits")
    parser.add_argument("image", help="imagen binaria, hexadecimal o decimal")
    parser.add_argument("--format", choices=("bin", "hex", "dec"), default=None)
    parser.add_argument("--batch", action="store_true")
    parser.add_argument("--input", default="")
    parser.add_argument("--max-instructions", type=int, default=1000000)
    parser.add_argument("--results", nargs=2, metavar=("BASE", "COUNT"))
    parser.add_argument("--reset-counters", action="store_true")
    args = parser.parse_args(argv)

    simulator = Simulator(batch=args.batch, input_chars=list(args.input))
    try:
        if args.reset_counters:
            simulator.reset_counters()
        suffix = Path(args.image).suffix.lower()
        image_format = args.format or ("dec" if suffix == ".dec" else "hex" if suffix in (".hex", ".txt") else "bin")
        if image_format == "hex":
            origin, size = simulator.load_hex(args.image)
        elif image_format == "dec":
            origin, size = simulator.load_decimal(args.image)
        else:
            origin, size = simulator.load_image(args.image)

        registers, instructions = simulator.execute(args.max_instructions)
        print("HALT")
        print("PC:", f"0x{simulator.pc:04X}")
        print("Instrucciones:", instructions)
        print("Bytes de imagen (con cabecera):", size + 2)
        print("Memoria ocupada por codigo:", simulator.code_bytes)
        print("Memoria de datos escrita:", len(simulator.written - set(range(origin, origin + size))))
        print("Memoria total utilizada:", len(simulator.occupied))
        print("Pico de memoria ocupada:", simulator.peak_occupied)
        print("Registros:", " ".join(f"R{i}=0x{value:04X}" for i, value in enumerate(registers)))

        if args.results:
            base_text, count_text = args.results
            base = int(base_text, 16)
            count = int(count_text, 10)
            if count < 0:
                raise ExecutionError("cantidad de resultados negativa")
            print("Resultados:")
            for index in range(count):
                address = base + index * 2
                if address & 1:
                    raise ExecutionError(f"direccion de resultado impar: 0x{address:04X}")
                if address > 0xfffe:
                    raise ExecutionError("direccion de resultado fuera de rango")
                print(f"0x{address:04X}: 0x{simulator.read_word(address):04X}")
        return 0
    except ExecutionError as exc:
        print("Error:", exc, file=sys.stderr)
        print("PC:", f"0x{simulator.pc:04X}", file=sys.stderr)
        print("Instrucciones:", simulator.instructions, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
