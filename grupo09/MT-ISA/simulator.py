"""Machine-code execution for the original LC-3 and the Grupo 9 byte ISA."""

import argparse
from collections import Counter
import json
from pathlib import Path
import sys


TARGETS = ("lc3", "lab3c", "lab3c-v2")


class MachineError(RuntimeError):
    pass


def signed(value, width):
    sign = 1 << (width - 1)
    return (value ^ sign) - sign


class Machine:
    def __init__(self, image, *, target="lab3c", input_data="", interactive=False):
        if target not in TARGETS:
            raise ValueError(f"ISA desconocida: {target}")
        self.target = target
        self.legacy = target == "lc3"
        self.stride = 1 if self.legacy else 2
        self.memory = bytearray(131072 if self.legacy else 65536)
        if len(image) < 4 or (self.legacy and len(image) % 2):
            raise MachineError("Imagen binaria incompleta")
        self.origin = int.from_bytes(image[:2], "big")
        start = self.origin * 2 if self.legacy else self.origin
        end = start + len(image) - 2
        if start % 2 or end > len(self.memory):
            raise MachineError("Origen impar o imagen fuera de memoria")
        self.memory[start:end] = image[2:]
        self.image_bytes = end - start
        self.pc = self.origin
        self.registers = [0] * 8
        self.registers[6] = 0x7800 if self.legacy else 0xF000
        self.cc = 2
        self.carry = 0
        self.user = True
        self.halted = False
        self.steps = 0
        self.pc_counts = Counter()
        self.opcode_counts = Counter()
        self.trap_counts = Counter()
        self.extension_counts = Counter()
        self.read_bytes = set()
        self.written_bytes = set()
        self.fetched_bytes = set()
        self.data_bytes_read = 0
        self.data_bytes_written = 0
        self._output = []
        self._input = iter(input_data)
        self.interactive = interactive
        self.on_step = None

    @property
    def output(self):
        return "".join(self._output)

    def metrics(self):
        return {
            "instructions": self.steps,
            "image_bytes": self.image_bytes,
            "fetched_unique_bytes": len(self.fetched_bytes),
            "read_unique_bytes": len(self.read_bytes),
            "written_unique_bytes": len(self.written_bytes),
            "data_unique_bytes": len(self.read_bytes | self.written_bytes),
            "accessed_unique_bytes": len(self.fetched_bytes | self.read_bytes | self.written_bytes),
            "data_bytes_read": self.data_bytes_read,
            "data_bytes_written": self.data_bytes_written,
            "extension_counts": dict(self.extension_counts),
            "traps": {f"x{k:02X}": v for k, v in self.trap_counts.items()},
        }

    def _word_index(self, address):
        address &= 0xFFFF
        if self.legacy:
            return address * 2
        if address % 2:
            raise MachineError(f"Dirección de palabra impar x{address:04X}")
        return address

    def read_word(self, address, *, track=False):
        index = self._word_index(address)
        if track:
            self.read_bytes.update((index, index + 1))
            self.data_bytes_read += 2
        return (self.memory[index] << 8) | self.memory[index + 1]

    def _store_word(self, address, value):
        index = self._word_index(address)
        self.written_bytes.update((index, index + 1))
        self.data_bytes_written += 2
        self.memory[index] = (value >> 8) & 0xFF
        self.memory[index + 1] = value & 0xFF

    def _read_byte(self, address):
        address &= 0xFFFF
        self.read_bytes.add(address)
        self.data_bytes_read += 1
        return self.memory[address]

    def _store_byte(self, address, value):
        address &= 0xFFFF
        self.written_bytes.add(address)
        self.data_bytes_written += 1
        self.memory[address] = value & 0xFF

    def _set_cc(self, value, bits=16):
        value &= (1 << bits) - 1
        self.cc = 2 if value == 0 else (4 if value >> (bits - 1) else 1)

    def _set(self, register, value):
        self.registers[register] = value & 0xFFFF
        self._set_cc(value)

    def _pair(self, low):
        return self.registers[low] | (self.registers[low + 1] << 16)

    def _set_pair(self, low, value):
        self.registers[low] = value & 0xFFFF
        self.registers[low + 1] = (value >> 16) & 0xFFFF
        self._set_cc(value, 32)

    def _jump(self, address):
        address &= 0xFFFF
        if not self.legacy and address % 2:
            raise MachineError(f"Destino de salto impar x{address:04X}")
        self.pc = address

    def _write_output(self, value):
        self._output.append(value)
        if self.interactive:
            print(value, end="", flush=True)

    def _get_input(self):
        char = next(self._input, None)
        if char is None and self.interactive:
            char = sys.stdin.read(1)
        if not char:
            raise MachineError("El programa solicitó entrada y se agotaron los caracteres")
        return char

    def _trap(self, vector):
        self.trap_counts[vector] += 1
        self.registers[7] = self.pc
        if vector in (0x20, 0x23):
            if vector == 0x23:
                self._write_output("Enter a character: ")
            char = self._get_input()
            self._set(0, ord(char))
            if vector == 0x23:
                self._write_output(char)
        elif vector == 0x21:
            self._write_output(chr(self.registers[0] & 0xFF))
        elif vector in (0x22, 0x24) or (vector == 0x26 and not self.legacy):
            address = self.registers[0]
            packed_bytes = vector == 0x26
            step = 1 if packed_bytes else self.stride
            read = self._read_byte if packed_bytes else lambda addr: self.read_word(addr, track=True)
            for _ in range(65536 // step):
                unit = read(address)
                if unit == 0:
                    break
                self._write_output(chr(unit & 0xFF))
                if vector == 0x24 and unit >> 8:
                    self._write_output(chr(unit >> 8))
                address += step
            else:
                raise MachineError("Cadena sin terminador")
        elif vector == 0x25:
            self.halted = True
        else:
            handler = self.read_word(vector * self.stride, track=True)
            if handler == 0:
                raise MachineError(f"TRAP x{vector:02X} sin manejador")
            self._jump(handler)

    def _shift(self, value, count, kind, width):
        if count == 0:
            return value
        mask = (1 << width) - 1
        if kind == 0:
            self.carry = (value >> (width - count)) & 1 if count <= width else 0
            return (value << count) & mask
        if kind in (1, 2):
            operand = signed(value, width) if kind == 2 else value
            self.carry = (operand >> (count - 1)) & 1
            return (operand >> count) & mask
        raise MachineError("Modo de desplazamiento reservado")

    def _wide_arithmetic(self, opcode, instruction):
        dst = ((instruction >> 9) & 3) * 2
        if opcode == 20:
            left = self.registers[(instruction >> 6) & 7]
            right = self.registers[(instruction >> 3) & 7]
            if not instruction & 4:
                left, right = signed(left, 16), signed(right, 16)
            self._set_pair(dst, left * right)
            return
        numerator = self._pair(((instruction >> 7) & 3) * 2)
        divisor = self.registers[(instruction >> 4) & 7]
        unsigned = bool(instruction & 8)
        if not unsigned:
            numerator, divisor = signed(numerator, 32), signed(divisor, 16)
        if divisor == 0:
            raise MachineError("División por cero")
        quotient = abs(numerator) // abs(divisor)
        if (numerator < 0) != (divisor < 0):
            quotient = -quotient
        lower, upper = (0, 65535) if unsigned else (-32768, 32767)
        if not lower <= quotient <= upper:
            raise MachineError("Cociente fuera del rango de 16 bits")
        self.registers[dst + 1] = (numerator - quotient * divisor) & 0xFFFF
        self._set(dst, quotient)

    def _alu(self, operation, dst, left, right):
        if operation in ("ADD", "ADC"):
            value = left + right + (self.carry if operation == "ADC" else 0)
            self.carry = int(value > 0xFFFF)
        elif operation in ("SUB", "SBC"):
            value = left - right - (1 - self.carry if operation == "SBC" else 0)
            self.carry = int(value >= 0)
        elif operation == "AND":
            value = left & right
        elif operation == "XOR":
            value = left ^ right
        else:
            value = left | right
        self._set(dst, value)

    def _execute(self, instruction, opcode):
        regs = self.registers
        if self.target == "lab3c-v2":
            if instruction & 0xFE00 == 0x2200:
                dest = (instruction >> 6) & 7
                base = regs[(instruction >> 3) & 7]
                index = regs[instruction & 7]
                self._set(dest, self.read_word(base + 2 * index, track=True))
                self.extension_counts["LDRX"] += 1
                return
            if instruction & 0xFE07 == 0x4201:
                source = (instruction >> 6) & 7
                base = (instruction >> 3) & 7
                address = regs[base]
                self._store_word(address, regs[source])
                self._alu("ADD", base, address, self.stride)
                self.extension_counts["STR.POST"] += 1
                return
        field = instruction & 0x7FF
        if not self.legacy and opcode >= 28:
            opcode = {28: 2, 29: 3, 30: 14, 31: 0}[opcode]
            displacement = (field & 0xFF) - (256 if not field & 0x80 else 0)
        else:
            width = 9 if self.legacy else 8
            displacement = signed(instruction & ((1 << width) - 1), width)
        relative = self.pc + self.stride * displacement
        dst = (instruction >> (9 if self.legacy else 8)) & 7
        base = (instruction >> (6 if self.legacy else 5)) & 7
        reg_right = regs[instruction & 7]
        if opcode == 0:
            if self.cc & dst:
                self._jump(relative)
        elif opcode in (1, 5):
            operand = signed(instruction & 31, 5)
            if self.legacy and not instruction & 32:
                operand = reg_right
            self._alu("ADD" if opcode == 1 else "AND", dst, regs[base], operand & 0xFFFF)
        elif opcode == 2:
            self._set(dst, self.read_word(relative, track=True))
        elif opcode == 3:
            self._store_word(relative, regs[dst])
        elif opcode == 4:
            link_bit = 1 << (11 if self.legacy else 10)
            target = self.pc + signed(instruction & (link_bit - 1), link_bit.bit_length() - 1) * self.stride
            if not instruction & link_bit:
                target = regs[(instruction >> 6) & 7] if self.legacy else regs[(instruction >> 5) & 7]
            regs[7] = self.pc
            self._jump(target)
        elif opcode in (6, 7):
            width = 6 if self.legacy else 5
            address = regs[base] + self.stride * signed(instruction & ((1 << width) - 1), width)
            if opcode == 6:
                self._set(dst, self.read_word(address, track=True))
            else:
                self._store_word(address, regs[dst])
        elif opcode == 8:
            if self.user:
                raise MachineError("RTI requiere modo supervisor")
            self._jump(self.read_word(regs[6], track=True))
            psr = self.read_word(regs[6] + self.stride, track=True)
            regs[6] = (regs[6] + 2 * self.stride) & 0xFFFF
            self.cc, self.user = psr & 7, bool(psr & 0x8000)
        elif opcode == 9:
            self._set(dst, ~regs[base])
        elif opcode == 10:
            address = self.read_word(relative, track=True)
            self._set(dst, self.read_word(address, track=True))
        elif opcode == 11:
            address = self.read_word(relative, track=True)
            self._store_word(address, regs[dst])
        elif opcode == 12:
            self._jump(regs[base])
        elif opcode == 13 and not self.legacy:
            operation = ("ADD", "AND", "SUB", "XOR")[field & 3]
            self._alu(operation, dst, regs[base], regs[(field >> 2) & 7])
        elif opcode == 14:
            self._set(dst, relative)
        elif opcode == 15:
            self._trap(field & (0xFF if self.legacy else 0x7F))
        elif 16 <= opcode <= 19:
            count = regs[field & 7] if field & 16 else field & 15
            if opcode == 19:
                pair_dst = ((field >> 9) & 3) * 2
                pair_src = ((field >> 7) & 3) * 2
                value = self._shift(self._pair(pair_src), count, (field >> 5) & 3, 32)
                self._set_pair(pair_dst, value)
            else:
                self._set(dst, self._shift(regs[base], count, opcode - 16, 16))
        elif opcode in (20, 21):
            self._wide_arithmetic(opcode, instruction)
        elif opcode in (22, 23, 24, 25):
            address = regs[base] + signed(field & 31, 5)
            shift = 8 if opcode in (23, 25) else 0
            if opcode <= 23:
                mask = 0xFF << shift
                self._set(dst, (regs[dst] & ~mask) | (self._read_byte(address) << shift))
            else:
                self._store_byte(address, regs[dst] >> shift)
        elif opcode == 26:
            self._set(dst, signed(regs[base] & 255, 8))
        elif opcode == 27 and field & 3 < 3:
            operation = ("ADC", "SBC", "OR")[field & 3]
            self._alu(operation, dst, regs[base], regs[(field >> 2) & 7])
        else:
            raise MachineError(f"Instrucción reservada x{instruction:04X}")

    def step(self):
        pc = self.pc
        try:
            index = self._word_index(pc)
            instruction = (self.memory[index] << 8) | self.memory[index + 1]
            opcode = instruction >> (12 if self.legacy else 11)
            self.pc = (pc + self.stride) & 0xFFFF
            if self.on_step is not None:
                self.on_step(self, pc)
            self.steps += 1
            self.pc_counts[pc] += 1
            self.opcode_counts[opcode] += 1
            self.fetched_bytes.update((index, index + 1))
            self._execute(instruction, opcode)
        except MachineError as error:
            raise MachineError(f"PC x{pc:04X}: {error}") from error

    def execute(self, max_steps=10_000_000):
        while not self.halted and self.steps < max_steps:
            self.step()
        if not self.halted:
            raise MachineError(f"Se alcanzó el límite de {max_steps} instrucciones en x{self.pc:04X}")
        return self


def run(image, *, target="lab3c", input_data="", max_steps=10_000_000, on_step=None):
    machine = Machine(image, target=target, input_data=input_data)
    machine.on_step = on_step
    return machine.execute(max_steps)


def main():
    parser = argparse.ArgumentParser(description="Simula código máquina y reporta métricas.")
    parser.add_argument("image", type=Path, help="Binario con origen de dos bytes")
    parser.add_argument("--target", choices=TARGETS, default="lab3c")
    parser.add_argument("--input-file", type=Path)
    parser.add_argument("--interactive", action="store_true")
    parser.add_argument("--max-steps", type=int, default=10_000_000)
    parser.add_argument("--metrics", type=Path, help="Escribe las métricas JSON en un archivo")
    options = parser.parse_args()
    try:
        machine = Machine(
            options.image.read_bytes(),
            target=options.target,
            input_data=options.input_file.read_text() if options.input_file else "",
            interactive=options.interactive,
        ).execute(options.max_steps)
        if not options.interactive:
            print(machine.output, end="")
        metrics = json.dumps(machine.metrics(), indent=2)
        if options.metrics:
            options.metrics.write_text(metrics + "\n", encoding="utf-8")
        else:
            print(metrics, file=sys.stderr)
    except (OSError, MachineError) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
