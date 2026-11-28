import argparse
import re
import sys
from pathlib import Path


DEFAULT_MAX_INSTRUCTIONS = 1_000_000
OPCODE_ADDX = 0b10010
OPCODE_ADDI5 = 0b11001
OPCODE_LDRX = 0b11010
OPCODE_STRX = 0b11011
OPCODE_MUL = 0b01010  # DR = parte baja (16 bits) del producto con signo SR1 * SR2
OPCODE_MULH = 0b01011  # DR = parte alta (16 bits) del producto con signo SR1 * SR2
OPCODE_SUB = 0b11100  # DR = SR1 - (SR2 | imm4), mismo formato que ADD


def parse_machine_code(source):
    lines = source.splitlines()
    origin = None
    header_entries = []
    word_entries = []

    for line_number, original in enumerate(lines, start=1):
        code, has_comment, comment = original.partition(";")
        if has_comment:
            origin_match = re.search(
                r"\b(?:origen|origin)\s*:\s*(?:(?:0[xX]|[xX])([0-9A-Fa-f]{1,4})|([0-9A-Fa-f]{1,4})|([0-9]{1,5}))\b",
                comment,
                re.IGNORECASE,
            )
            if origin_match:
                if origin_match.group(1) is not None:
                    comment_origin = int(origin_match.group(1), 16)
                elif origin_match.group(2) is not None and re.search(r"[A-Fa-f]", origin_match.group(2)):
                    comment_origin = int(origin_match.group(2), 16)
                else:
                    raw_num = origin_match.group(2) or origin_match.group(3)
                    comment_origin = int(raw_num, 10)
                if not 0 <= comment_origin <= 0xFFFF:
                    raise ValueError(f"línea {line_number}: dirección de origen fuera de rango")
                if origin is not None and origin != comment_origin:
                    raise ValueError(f"línea {line_number}: se indicaron direcciones de origen diferentes")
                origin = comment_origin

        text = code.strip()
        if not text:
            continue
        if text.startswith("@"):
            header_entries.append((line_number, text))
        else:
            word_entries.append((line_number, text))

    # Determinar si las palabras del archivo son claramente decimales, binarias o hexadecimales
    def _infer_format():
        has_binary_header = any(re.fullmatch(r"[01]{16}", t[1:].strip()) for _, t in header_entries)
        has_hex_prefix_header = any(
            re.fullmatch(r"(?:0[xX]|[xX])[0-9A-Fa-f]{1,4}", t[1:].strip())
            or (re.fullmatch(r"[0-9A-Fa-f]{1,4}", t[1:].strip()) and re.search(r"[A-Fa-f]", t[1:].strip()))
            for _, t in header_entries
        )
        has_5digit_dec_header = any(re.fullmatch(r"[0-9]{5}", t[1:].strip()) for _, t in header_entries)

        has_binary_word = any(re.fullmatch(r"[01]{16}", t) for _, t in word_entries)
        has_hex_word = any(
            re.fullmatch(r"(?:0[xX]|[xX])[0-9A-Fa-f]{4}", t)
            or (re.fullmatch(r"[0-9A-Fa-f]{4}", t) and re.search(r"[A-Fa-f]", t))
            for _, t in word_entries
        )
        has_non4_dec_word = any(
            re.fullmatch(r"[0-9]{1,3}|[0-9]{5}", t) for _, t in word_entries
        )

        if has_binary_header or (has_binary_word and not has_hex_prefix_header and not has_5digit_dec_header):
            return "BINARIO"
        if has_5digit_dec_header or (has_non4_dec_word and not has_hex_word and not has_hex_prefix_header):
            return "DECIMAL"
        if has_hex_prefix_header or has_hex_word:
            return "HEXADECIMAL"
        if word_entries and all(re.fullmatch(r"[0-9A-Fa-f]{4}", t) for _, t in word_entries):
            return "HEXADECIMAL"
        if word_entries and all(re.fullmatch(r"[0-9]+", t) for _, t in word_entries):
            return "DECIMAL"
        return "HEXADECIMAL"

    source_format = _infer_format()

    for line_number, text in header_entries:
        header = text[1:].strip()
        if re.fullmatch(r"[01]{16}", header):
            header_format = "BINARIO"
            header_origin = int(header, 2)
        elif re.fullmatch(r"(?:0[xX]|[xX])([0-9A-Fa-f]{1,4})", header):
            header_format = "HEXADECIMAL"
            header_origin = int(re.fullmatch(r"(?:0[xX]|[xX])([0-9A-Fa-f]{1,4})", header).group(1), 16)
        elif re.fullmatch(r"[0-9A-Fa-f]{1,4}", header) and re.search(r"[A-Fa-f]", header):
            header_format = "HEXADECIMAL"
            header_origin = int(header, 16)
        elif re.fullmatch(r"[0-9]{1,5}", header):
            if source_format == "DECIMAL" or len(header) == 5:
                header_format = "DECIMAL"
                header_origin = int(header, 10)
            else:
                header_format = "HEXADECIMAL"
                header_origin = int(header, 16)
        else:
            raise ValueError(
                f"línea {line_number}: dirección inicial inválida ({text}); use @x3000, @<16 bits> o @12288"
            )

        if not 0 <= header_origin <= 0xFFFF or (header_origin & 1):
            raise ValueError(
                f"línea {line_number}: la dirección inicial debe ser par y estar entre x0000 y xFFFF"
            )
        if origin is not None and origin != header_origin:
            raise ValueError(
                f"línea {line_number}: la dirección inicial no coincide con el origen indicado"
            )
        origin = header_origin
        if source_format == "HEXADECIMAL" and header_format == "DECIMAL" and not word_entries:
            source_format = "DECIMAL"

    words = []
    for line_number, text in word_entries:
        if source_format == "BINARIO":
            if not re.fullmatch(r"[01]{16}", text):
                raise ValueError(
                    f"línea {line_number}: palabra binaria inválida ({text}); se requieren 16 bits"
                )
            value = int(text, 2)
        elif source_format == "DECIMAL":
            if not re.fullmatch(r"[0-9]+", text):
                raise ValueError(
                    f"línea {line_number}: palabra decimal inválida ({text})"
                )
            value = int(text, 10)
        else:
            hex_match = re.fullmatch(r"(?:0[xX]|[xX])?([0-9A-Fa-f]{4})", text)
            if hex_match is None:
                raise ValueError(
                    f"línea {line_number}: palabra hexadecimal inválida ({text}); use x0000, 0x0000 o 0000"
                )
            value = int(hex_match.group(1), 16)

        if not 0 <= value <= 0xFFFF:
            raise ValueError(f"línea {line_number}: palabra fuera del rango 0..65535")
        words.append(value)

    if origin is None:
        if len(words) >= 2:
            origin = words.pop(0)
        else:
            raise ValueError(
                "falta la dirección de origen; use @x3000, @<16 bits>, @12288, '; Origen: x3000' o incluya el origen como primera palabra"
            )
    if not 0 <= origin <= 0xFFFF or (origin & 1):
        raise ValueError("la dirección de origen debe ser par y estar entre x0000 y xFFFF")
    if not words:
        raise ValueError("el archivo no contiene palabras de código máquina")
    if origin + len(words) * 2 > 0x10000:
        raise ValueError("el programa excede el espacio de direcciones de 16 bits")

    return origin, words, source_format


def load_machine_code_file(path):
    source = Path(path).read_text(encoding="utf-8-sig")
    return parse_machine_code(source)


load_machine_file = load_machine_code_file


class CPU:
    def __init__(self, memory_size=1 << 16):
        self.memory = bytearray(memory_size)
        self.R = [0] * 8  # Registros
        self.PC = 0  # Program Counter (dirección de byte, siempre par)
        self.IR = 0  # Instruccion actual
        self.running = True  # Verificacion que no se haya desbordado el programa
        self.CC = 0b010  # Conditional Code
        self.V = 0
        self.C = 0
        self.PSR = 0b010
        self.decoded = None
        self.decoded_ir = None
        self.trap_input = ""
        self.trap_input_position = 0
        self.trap_output = []
        self.loaded_addresses = set()
        self.memory_read_addresses = set()
        self.memory_write_addresses = set()
        self.execution_addresses = set()
        self.accessed_addresses = set()
        self.program_origin = None
        self.program_addresses = set()
        self.program_end = None

    def load_program(self, origin, words):
        if not 0 <= origin <= 0xFFFF or (origin & 1):
            raise ValueError("La dirección de origen debe ser par y estar entre x0000 y xFFFF")
        if origin + len(words) * 2 > len(self.memory):
            raise ValueError("El programa excede el tamaño de la memoria")
        self.loaded_addresses.clear()
        self.memory_read_addresses.clear()
        self.memory_write_addresses.clear()
        self.execution_addresses.clear()
        self.accessed_addresses.clear()
        for index, word in enumerate(words):
            address = origin + index * 2
            self.memory[address] = word & 0xFF
            self.memory[address + 1] = (word >> 8) & 0xFF
            self.loaded_addresses.add(address)
            self.loaded_addresses.add(address + 1)
            self.accessed_addresses.add(address)
            self.accessed_addresses.add(address + 1)
        self.PC = origin
        self.running = True
        self.program_origin = origin
        self.program_addresses = {
            (origin + index * 2) & 0xFFFF for index in range(len(words))
        }
        self.program_end = (origin + len(words) * 2) & 0xFFFF

    def load_file(self, path):
        origin, words, source_format = load_machine_code_file(path)
        self.load_program(origin, words)
        return origin, words, source_format

    def get_memory_usage(self):
        loaded_bytes = len(self.loaded_addresses)
        read_bytes = len(self.memory_read_addresses)
        write_bytes = len(self.memory_write_addresses)
        execution_bytes = len(self.execution_addresses)
        total_used_bytes = len(self.accessed_addresses)
        extra_bytes = len(self.accessed_addresses - self.loaded_addresses)
        total_memory = len(self.memory)
        usage_percent = (total_used_bytes / total_memory) * 100.0 if total_memory else 0.0
        loaded_min = min(self.loaded_addresses) if self.loaded_addresses else (self.program_origin or 0)
        loaded_max = max(self.loaded_addresses) if self.loaded_addresses else (self.program_origin or 0)
        return {
            "loaded_bytes": loaded_bytes,
            "loaded_words": loaded_bytes // 2,
            "loaded_min": loaded_min,
            "loaded_max": loaded_max,
            "read_bytes": read_bytes,
            "write_bytes": write_bytes,
            "execution_bytes": execution_bytes,
            "total_used_bytes": total_used_bytes,
            "extra_bytes": extra_bytes,
            "total_memory": total_memory,
            "usage_percent": usage_percent,
        }

    def run(self, max_instructions=DEFAULT_MAX_INSTRUCTIONS, stop_event=None):
        steps = 0
        error_message = None
        reached_end = False
        left_program = False
        stopped_by_user = False

        try:
            while self.running and steps < max_instructions:
                if stop_event is not None and stop_event.is_set():
                    stopped_by_user = True
                    break
                if self.PC & 1:
                    raise ValueError(
                        f"Excepción de alineación: se intentó saltar a la dirección impar PC x{self.PC:04X}"
                    )
                if self.program_addresses and self.PC not in self.program_addresses:
                    reached_end = self.PC == self.program_end
                    left_program = not reached_end
                    break
                self.fetch()
                if not self.running:
                    break
                self.execute()
                steps += 1
        except (IndexError, PermissionError, ValueError) as error:
            error_message = str(error)

        if error_message:
            outcome = f"Ejecución detenida por error: {error_message}"
            status = "La CPU se detuvo por un error."
        elif stopped_by_user:
            outcome = "Ejecución detenida por el usuario."
            status = "Ejecución detenida."
        elif reached_end:
            outcome = "Fin del programa alcanzado (.END)."
            status = "Ejecución finalizada en .END."
        elif left_program:
            outcome = f"Ejecución detenida: PC x{self.PC:04X} fuera del programa cargado."
            status = "La CPU salió del rango del programa cargado."
        elif self.running:
            outcome = f"Se alcanzó el límite de {max_instructions:,} instrucciones; posible bucle."
            status = "Ejecución detenida por límite de instrucciones."
        else:
            outcome = "Programa detenido por HALT."
            status = "Ejecución finalizada."

        return {
            "outcome": outcome,
            "status": status,
            "steps": steps,
            "error_message": error_message,
            "reached_end": reached_end,
            "left_program": left_program,
            "stopped_by_user": stopped_by_user,
            "limit_reached": (
                error_message is None
                and not stopped_by_user
                and not reached_end
                and not left_program
                and self.running
            ),
            "trap_output": "".join(self.trap_output),
            "memory_usage": self.get_memory_usage(),
        }

    def fetch(self):
        if self.PC & 1:
            raise ValueError(
                f"Excepción de alineación: se intentó ejecutar desde la dirección impar PC x{self.PC:04X}"
            )
        if self.PC + 1 < len(self.memory):
            self.IR = self._read_word(self.PC)
            self.PC = (self.PC + 2) & 0xFFFF
            self.decoded = None
            self.decoded_ir = None
        else:
            self.running = False

    def decode(self):
        opcode = (self.IR >> 11) & 0b11111
        instruction = {"opcode": opcode}

        if opcode == 0b00000:  # BR
            instruction["condition"] = (self.IR >> 8) & 0b111
            instruction["condition_codes"] = self.CC
            instruction["offset"] = self._sign_extend(self.IR & 0xFF, 8) * 2

        elif opcode in (0b10011, 0b10100):  # BRV / BRC
            instruction["offset"] = self._sign_extend(self.IR & 0xFF, 8) * 2

        elif opcode in (0b00010, 0b00011):  # LD / ST
            register = (self.IR >> 8) & 0b111
            offset = self._sign_extend(self.IR & 0xFF, 8)
            instruction["register"] = register
            instruction["address"] = ((self.PC // 2 + offset) * 2) & 0xFFFF
            instruction["register_value"] = self.R[register]

        elif opcode in (0b00001, 0b00101, OPCODE_SUB):  # ADD / AND / SUB
            source = (self.IR >> 5) & 0b111
            instruction["destination"] = (self.IR >> 8) & 0b111
            instruction["source_value"] = self.R[source]
            if (self.IR >> 4) & 1:
                instruction["operand"] = self._sign_extend(self.IR & 0xF, 4)
            else:
                instruction["operand"] = self.R[self.IR & 0b111]

        elif opcode in (OPCODE_MUL, OPCODE_MULH):  # MUL / MULH (solo modo registro)
            instruction["destination"] = (self.IR >> 8) & 0b111
            instruction["source_value"] = self.R[(self.IR >> 5) & 0b111]
            instruction["operand"] = self.R[self.IR & 0b111]

        elif opcode == OPCODE_ADDI5:
            source = (self.IR >> 5) & 0b111
            instruction["destination"] = (self.IR >> 8) & 0b111
            instruction["source_value"] = self.R[source]
            instruction["operand"] = self._sign_extend(self.IR & 0x1F, 5)

        elif opcode == OPCODE_ADDX:  # Extended ADD immediate used by fixed-point Q values
            source = (self.IR >> 5) & 0b111
            instruction["destination"] = (self.IR >> 8) & 0b111
            instruction["source_value"] = self.R[source]
            instruction["immediate_address"] = self.PC

        elif opcode == 0b00100:  # JSR / JSRR
            instruction["link_address"] = self.PC // 2
            if (self.IR >> 10) & 1:
                target = self.PC + self._sign_extend(self.IR & 0x3FF, 10) * 2
            else:
                base_register = (self.IR >> 5) & 0b111
                target = self.R[base_register] * 2
            instruction["target"] = target & 0xFFFF

        elif opcode in (0b00110, 0b00111, 0b10101, 0b10110, 0b10111, 0b11000):  # LDR / STR / LDB / STB / LDH / STH
            register = (self.IR >> 8) & 0b111
            base_register = (self.IR >> 5) & 0b111
            offset = self._sign_extend(self.IR & 0x1F, 5)
            instruction["register"] = register
            if opcode in (0b00110, 0b00111):
                address = (self.R[base_register] + offset) * 2
            else:
                address = self.R[base_register] * 2 + offset
            instruction["address"] = address & 0xFFFF
            instruction["register_value"] = self.R[register]

        elif opcode in (OPCODE_LDRX, OPCODE_STRX):
            register = (self.IR >> 8) & 0b111
            base_register = (self.IR >> 5) & 0b111
            instruction["register"] = register
            instruction["base_value"] = self.R[base_register]
            instruction["offset_address"] = self.PC
            instruction["register_value"] = self.R[register]

        elif opcode == 0b01000:  # RTI
            instruction["stack_address"] = self.R[6] * 2

        elif opcode == 0b01001:  # NOT
            source = (self.IR >> 5) & 0b111
            instruction["destination"] = (self.IR >> 8) & 0b111
            instruction["source_value"] = self.R[source]

        elif opcode == 0b01100:  # JMP / RET
            base_register = (self.IR >> 5) & 0b111
            instruction["target"] = (self.R[base_register] * 2) & 0xFFFF

        elif opcode == 0b01110:  # LEA
            instruction["destination"] = (self.IR >> 8) & 0b111
            instruction["address"] = (
                self.PC // 2 + self._sign_extend(self.IR & 0xFF, 8)
            ) & 0xFFFF

        elif opcode == 0b01111:  # TRAP
            instruction["vector"] = self.IR & 0xFF
            instruction["link_address"] = self.PC // 2

        elif opcode in (0b01101, 0b10000, 0b10001):  # LSHF / RSHFL / RSHFA
            instruction["destination"] = (self.IR >> 8) & 0b111
            instruction["source_value"] = self.R[(self.IR >> 5) & 0b111]
            instruction["amount"] = self.IR & 0xF

        self.decoded = instruction
        self.decoded_ir = self.IR
        return instruction

    def execute(self):
        if self.decoded is None or self.decoded_ir != self.IR:
            self.decode()
        instruction = self.decoded
        opcode = instruction["opcode"]

        if opcode == 0b00000:  # BR
            if instruction["condition"] & instruction["condition_codes"]:
                self.PC = (self.PC + instruction["offset"]) & 0xFFFF

        elif opcode in (0b10011, 0b10100):  # BRV / BRC
            flag = self.V if opcode == 0b10011 else self.C
            if flag:
                self.PC = (self.PC + instruction["offset"]) & 0xFFFF

        elif opcode in (0b00001, OPCODE_ADDI5):  # ADD / ADDI5
            self._add_register(
                instruction["destination"],
                instruction["source_value"],
                instruction["operand"],
            )

        elif opcode == OPCODE_SUB:  # SUB
            self._sub_register(
                instruction["destination"],
                instruction["source_value"],
                instruction["operand"],
            )

        elif opcode in (OPCODE_MUL, OPCODE_MULH):  # MUL / MULH
            self._multiply_register(
                instruction["destination"],
                instruction["source_value"],
                instruction["operand"],
                high=opcode == OPCODE_MULH,
            )

        elif opcode == OPCODE_ADDX:  # Extended ADD immediate (formato Q)
            immediate = self._sign_extend(
                self._read_word(instruction["immediate_address"]), 16
            )
            self.PC = (instruction["immediate_address"] + 2) & 0xFFFF
            self._add_register(
                instruction["destination"], instruction["source_value"], immediate
            )

        elif opcode == 0b00010:  # LD
            self._write_register(
                instruction["register"], self._read_word(instruction["address"])
            )

        elif opcode == 0b00011:  # ST
            self._write_word(instruction["address"], instruction["register_value"])

        elif opcode == 0b00100:  # JSR / JSRR
            self.R[7] = instruction["link_address"] & 0xFFFF
            self.PC = instruction["target"]

        elif opcode == 0b00101:  # AND
            self._write_register(
                instruction["destination"],
                instruction["source_value"] & instruction["operand"],
            )

        elif opcode == 0b00110:  # LDR
            self._write_register(
                instruction["register"], self._read_word(instruction["address"])
            )

        elif opcode == 0b00111:  # STR
            self._write_word(instruction["address"], instruction["register_value"])

        elif opcode == OPCODE_LDRX:  # LDRX (offset extendido 16 bits)
            offset = self._sign_extend(
                self._read_word(instruction["offset_address"]), 16
            )
            self.PC = (instruction["offset_address"] + 2) & 0xFFFF
            address = (instruction["base_value"] * 2 + offset * 2) & 0xFFFF
            self._write_register(instruction["register"], self._read_word(address))

        elif opcode == OPCODE_STRX:  # STRX (offset extendido 16 bits)
            offset = self._sign_extend(
                self._read_word(instruction["offset_address"]), 16
            )
            self.PC = (instruction["offset_address"] + 2) & 0xFFFF
            address = (instruction["base_value"] * 2 + offset * 2) & 0xFFFF
            self._write_word(address, instruction["register_value"])

        elif opcode == 0b10101:  # LDB
            value = self._sign_extend(
                self._read_byte(instruction["address"]), 8
            )
            self._write_register(instruction["register"], value)

        elif opcode == 0b10110:  # STB
            self._write_byte(
                instruction["address"], instruction["register_value"]
            )

        elif opcode == 0b10111:  # LDH
            value = self._sign_extend(
                self._read_byte((instruction["address"] + 1) & 0xFFFF), 8
            )
            self._write_register(instruction["register"], value)

        elif opcode == 0b11000:  # STH
            self._write_byte(
                (instruction["address"] + 1) & 0xFFFF,
                instruction["register_value"] >> 8,
            )

        elif opcode == 0b01000:  # RTI
            if self.PSR & 0x8000:
                raise PermissionError("RTI solo se permite en modo supervisor")
            stack_address = instruction["stack_address"]
            self.PC = (self._read_word(stack_address) * 2) & 0xFFFF
            self.PSR = self._read_word(stack_address + 2)
            self.R[6] = (self.R[6] + 2) & 0xFFFF
            self.CC = self.PSR & 0b111

        elif opcode == 0b01001:  # NOT
            self._write_register(
                instruction["destination"], ~instruction["source_value"]
            )

        elif opcode == 0b01100:  # JMP / RET
            self.PC = instruction["target"]

        elif opcode == 0b01110:  # LEA
            self._write_register(instruction["destination"], instruction["address"])

        elif opcode == 0b01111:  # TRAP
            self.R[7] = instruction["link_address"] & 0xFFFF
            self._execute_trap(instruction["vector"])

        elif opcode == 0b01101:  # LSHF
            result = instruction["source_value"] << instruction["amount"]
            self._write_register(instruction["destination"], result)

        elif opcode == 0b10000:  # RSHFL
            result = instruction["source_value"] >> instruction["amount"]
            self._write_register(instruction["destination"], result)

        elif opcode == 0b10001:  # RSHFA
            value = self._sign_extend(instruction["source_value"], 16)
            result = value >> instruction["amount"]
            self._write_register(instruction["destination"], result)

        else:
            raise ValueError(f"Opcode no implementado: {opcode:05b}")

    def _execute_trap(self, vector):
        if vector == 0x25:
            self.running = False
        elif vector == 0x20:
            self.R[0] = self._read_trap_character()
        elif vector == 0x21:
            self.trap_output.append(chr(self.R[0] & 0xFF))
        elif vector == 0x22:
            address = (self.R[0] * 2) & 0xFFFF
            for _ in range(len(self.memory) // 2):
                packed = self._read_word(address)
                low_character = packed & 0xFF
                if low_character == 0:
                    break
                self.trap_output.append(chr(low_character))
                address = (address + 2) & 0xFFFF
            else:
                raise ValueError("PUTS no encontró una palabra terminadora nula")
        elif vector == 0x23:
            self.R[0] = self._read_trap_character()
            self.trap_output.append(chr(self.R[0] & 0xFF))
        elif vector == 0x24:
            address = (self.R[0] * 2) & 0xFFFF
            for _ in range(len(self.memory) // 2):
                packed = self._read_word(address)
                low_character = packed & 0xFF
                high_character = (packed >> 8) & 0xFF
                if low_character == 0:
                    break
                self.trap_output.append(chr(low_character))
                if high_character == 0:
                    break
                self.trap_output.append(chr(high_character))
                address = (address + 2) & 0xFFFF
            else:
                raise ValueError("PUTSP no encontró una palabra terminadora nula")
        else:
            raise ValueError(f"TRAP x{vector:02X} no está implementado")

        if vector != 0x25:
            self.PC = (self.R[7] * 2) & 0xFFFF

    def _read_trap_character(self):
        if self.trap_input_position >= len(self.trap_input):
            raise ValueError("el TRAP requiere un carácter de entrada")
        character = self.trap_input[self.trap_input_position]
        self.trap_input_position += 1
        return ord(character) & 0xFF

    @staticmethod
    def _sign_extend(value, bit_count):
        sign_bit = 1 << (bit_count - 1)
        return (value ^ sign_bit) - sign_bit

    def _read_byte(self, address):
        if not 0 <= address < len(self.memory):
            raise IndexError(f"Direccion de memoria fuera de rango: {address}")
        self.memory_read_addresses.add(address)
        self.execution_addresses.add(address)
        self.accessed_addresses.add(address)
        return self.memory[address]

    def _write_byte(self, address, value):
        if not 0 <= address < len(self.memory):
            raise IndexError(f"Direccion de memoria fuera de rango: {address}")
        self.memory[address] = value & 0xFF
        self.memory_write_addresses.add(address)
        self.execution_addresses.add(address)
        self.accessed_addresses.add(address)

    def _read_word(self, address):
        low_byte = self._read_byte(address)
        high_byte = self._read_byte(address + 1)
        return low_byte | (high_byte << 8)

    def _write_word(self, address, value):
        self._write_byte(address, value)
        self._write_byte(address + 1, value >> 8)

    def _write_register(self, register, value):
        value &= 0xFFFF
        self.R[register] = value
        if value == 0:
            self.CC = 0b010
        elif value & 0x8000:
            self.CC = 0b100
        else:
            self.CC = 0b001
        self.PSR = (self.PSR & ~0b111) | self.CC

    def _add_register(self, destination, source_value, operand):
        source_value &= 0xFFFF
        operand_value = operand & 0xFFFF
        source_signed = self._sign_extend(source_value, 16)
        operand_signed = self._sign_extend(operand_value, 16)
        signed_result = source_signed + operand_signed
        unsigned_result = source_value + operand_value
        self.C = int(unsigned_result > 0xFFFF)
        self.V = int(not -0x8000 <= signed_result <= 0x7FFF)
        self._write_register(destination, unsigned_result)

    def _sub_register(self, destination, source_value, operand):
        # Convencion de flags: C = 1 si hay PRESTAMO sin signo (SR1 < operando);
        # es la inversa de ARM. V = 1 si el resultado no entra en 16 bits con signo.
        source_value &= 0xFFFF
        operand_value = operand & 0xFFFF
        signed_result = self._sign_extend(source_value, 16) - self._sign_extend(operand_value, 16)
        self.C = int(source_value < operand_value)
        self.V = int(not -0x8000 <= signed_result <= 0x7FFF)
        self._write_register(destination, source_value - operand_value)

    def _multiply_register(self, destination, source_value, operand, high):
        # Producto con signo de 16x16 -> 32 bits.
        # MUL : DR = 16 bits bajos. V = 1 si el producto no entra en 16 bits con signo.
        # MULH: DR = 16 bits altos. V = 0.
        # En ambos casos C = 0 y N/Z/P se calculan sobre el valor escrito en DR.
        product = self._sign_extend(source_value & 0xFFFF, 16) * self._sign_extend(operand & 0xFFFF, 16)
        if high:
            self.V = 0
            result = product >> 16
        else:
            self.V = int(not -0x8000 <= product <= 0x7FFF)
            result = product
        self.C = 0
        self._write_register(destination, result)


def format_execution_report(cpu, result, source_name=None, source_format=None):
    memory_usage = result["memory_usage"]
    cc_n = (cpu.CC >> 2) & 1
    cc_z = (cpu.CC >> 1) & 1
    cc_p = cpu.CC & 1

    lines = []
    if source_name is not None:
        header = f"Archivo: {source_name}"
        if source_format is not None and cpu.program_origin is not None:
            header += f" (formato {source_format}, origen x{cpu.program_origin:04X})"
        lines.append(header)

    lines.append(f"Motivo de detención: {result['outcome']}")
    lines.append(f"Instrucciones ejecutadas: {result['steps']}")
    lines.append("")
    lines.append("Uso de memoria:")
    if memory_usage["loaded_bytes"]:
        lines.append(
            f"  Programa cargado (código + datos estáticos): "
            f"{memory_usage['loaded_bytes']} bytes ({memory_usage['loaded_words']} palabras, "
            f"rango x{memory_usage['loaded_min']:04X}-x{memory_usage['loaded_max']:04X})"
        )
    else:
        lines.append("  Programa cargado (código + datos estáticos): 0 bytes (0 palabras)")
    lines.append(
        f"  Lecturas en ejecución: {memory_usage['read_bytes']} direcciones distintas"
    )
    lines.append(
        f"  Escrituras en ejecución: {memory_usage['write_bytes']} direcciones distintas"
    )
    lines.append(
        f"  Memoria accedida durante la ejecución: {memory_usage['execution_bytes']} bytes"
    )
    lines.append(
        f"  Total de memoria utilizada: {memory_usage['total_used_bytes']} bytes "
        f"de {memory_usage['total_memory']} bytes ({memory_usage['usage_percent']:.2f}%)"
    )
    lines.append("")
    lines.append("Estado de la CPU:")
    lines.append(f"  PC = x{cpu.PC:04X}    IR = x{cpu.IR:04X}")
    lines.append(
        f"  CC = {cpu.CC:03b} (N={cc_n}, Z={cc_z}, P={cc_p})    V = {cpu.V}    C = {cpu.C}"
    )
    lines.append("")
    lines.append("Registros:")
    for index, value in enumerate(cpu.R):
        signed_value = value - 0x10000 if value & 0x8000 else value
        lines.append(f"  R{index} = x{value:04X}  (sin signo: {value}, con signo: {signed_value})")

    if result["trap_output"]:
        lines.append("")
        lines.append("Salida de TRAP:")
        lines.append(result["trap_output"])

    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Simulador independiente de CPU para la ISA de 16 bits"
    )
    parser.add_argument(
        "archivo",
        help="archivo de código máquina en formato hexadecimal (@x3000), binario (@0011...) o decimal (@12288)",
    )
    parser.add_argument(
        "-i",
        "--input",
        default="",
        help="cadena de entrada opcional para instrucciones TRAP (GETC / IN)",
    )
    parser.add_argument(
        "-m",
        "--max-instructions",
        "--limite",
        dest="max_instructions",
        type=int,
        default=DEFAULT_MAX_INSTRUCTIONS,
        help=f"límite máximo de instrucciones a ejecutar (por defecto {DEFAULT_MAX_INSTRUCTIONS})",
    )
    args = parser.parse_args(argv)

    if args.max_instructions <= 0:
        print("Error: --max-instructions debe ser un entero positivo.", file=sys.stderr)
        return 1

    cpu = CPU()
    cpu.trap_input = args.input
    try:
        _origin, _words, source_format = cpu.load_file(args.archivo)
    except (OSError, ValueError) as error:
        print(f"{args.archivo}: error: {error}", file=sys.stderr)
        return 1

    result = cpu.run(max_instructions=args.max_instructions)
    print(format_execution_report(cpu, result, source_name=args.archivo, source_format=source_format))
    return 1 if result["error_message"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
