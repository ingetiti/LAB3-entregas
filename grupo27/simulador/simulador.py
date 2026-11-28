'''Simulador de la arquitectura espesificada'''

# El simulador será similar al ensamblador.
# Estara desacoplado de los demas modulos, pero buscara en instrucciones.py las instrucciones
# a travez de las listas dedicadas para esto como son INSTRUCTIONS, INSTRUCTIONS_BY_OPCODE y INSTRUCTIONS_BY_MNEMONIC
# Tambien tendrá capacidad para ejecutarce como clase de python y a travez de la funcion main que correra cuando se ejecute
# este archivo solo (igual que como funciona el ensamblador)
# De manera por defecto se tendria que poder ejecutar un programa en cualquiera de los formatos que ensambla el ensamblador (tanto como lista de python, como archivo .hex o .bin) en modo de un solo ciclo por instruccion.
# De momento haremos que en modo un solo ciclo, cada instruccion se ejecuta en un ciclo, y en los demas modos cada etapa toma un ciclo del reloj.
#
# Se tendra una o mas banderas para mostrar estadisticas como:
# - Instrucciones ejecutadas (en espacio del programa, en espacio del sistema operativo, totales)
# - Ciclos ejecutados (depende de si se ejecuta en modo de un solo ciclo, multi ciclo, o pipeline)
# - Lectura de memoria (en espacio del programa, en espacio del sistema operativo, totales)
# - Escritura de memoria (en espacio del programa, en espacio del sistema operativo, totales)
# - Total de accesos a memoria (en espacio del programa, en espacio del sistema operativo, totales)

import argparse
import inspect
import json
import os
import re
import sys
from pathlib import Path

try:
    from . import instrucciones, predictores
except ImportError:
    import instrucciones
    import predictores


_WORD_COUNT = 1 << 16
_DEFAULT_MAX_CYCLES = 1_000_000
_PRIVILEGE_BIT = 0x8000
_SPECIAL_GETC = 0x8001
_SPECIAL_OUT = 0x8002
_INVALID_KEY_CODE = 0x9F
_INVALID_OUTPUT_CHARACTER = "?"


def _read_console_byte():
    if os.name.lower() == "nt":
        import msvcrt

        character = msvcrt.getwch()
        if character in ("\x00", "\xe0"):
            scan_code = msvcrt.getwch()
            if not scan_code:
                raise EOFError("No se recibió el código de la tecla especial")
            return 0x80 | (ord(scan_code[0]) & 0x1F)
    else:
        character = sys.stdin.read(1)

    if not character:
        raise EOFError("No hay una tecla disponible para GETC")
    if character[0] in ("\r", "\n"):
        return 0x0A
    code = ord(character[0])
    return code if code <= 0xFF else _INVALID_KEY_CODE


class _SpecialInstruction(instrucciones.BASE_INSTRUCTION):
    def on_execute(self, machine):
        return machine._execute_special(self.VALUE)


class _PipelineEntry:
    def __init__(self, instruction, address):
        self.instruction = instruction
        self.address = address
        self.completed_stages = set()


def _normalise_name(value):
    return re.sub(r"[^a-z0-9]", "", str(value).lower())


def _available_predictors():
    return [
        candidate
        for _, candidate in inspect.getmembers(predictores, inspect.isclass)
        if candidate is not predictores.BASE_PREDICTOR
        and issubclass(candidate, predictores.BASE_PREDICTOR)
    ]


def _make_predictor(value):
    if value is None:
        default = getattr(predictores, "Predictor_Never_taken", None)
        if default is not None:
            return default()
        candidates = _available_predictors()
        if not candidates:
            raise RuntimeError("predictores.py no define predictores utilizables")
        return candidates[0]()

    if isinstance(value, predictores.BASE_PREDICTOR):
        return value

    if inspect.isclass(value) and issubclass(value, predictores.BASE_PREDICTOR):
        return value()

    if isinstance(value, str):
        name = _normalise_name(value)
        for candidate in _available_predictors():
            if name in (
                _normalise_name(candidate.__name__),
                _normalise_name(candidate.NAME),
            ):
                return candidate()
        raise ValueError(f"Predictor no reconocido: {value!r}")

    raise TypeError("predictor debe ser un nombre, una clase o una instancia de predictor")


class Simulador:
    """Ejecuta imágenes binarias usando las etapas declaradas por cada instrucción."""

    _MODE_NAMES = {
        "single": "single",
        "singlecycle": "single",
        "monociclo": "single",
        "mono": "single",
        "multi": "multi",
        "multicycle": "multi",
        "multiciclo": "multi",
        "pipeline": "pipeline",
    }

    def __init__(
        self,
        program=None,
        mode="single",
        predictor=None,
        include_orig=True,
        start_address=None,
        trap_handlers=None,
        max_cycles=_DEFAULT_MAX_CYCLES,
        load_os=True,
        os_path=None,
        user_stack_pointer=0xFE00,
        supervisor_stack_pointer=0x3000,
        input_fn=None,
        output_fn=None,
    ):
        try:
            self.mode = self._MODE_NAMES[_normalise_name(mode)]
        except KeyError as error:
            valid_modes = ", ".join(sorted(set(self._MODE_NAMES.values())))
            raise ValueError(f"Modo no reconocido: {mode!r}. Modos válidos: {valid_modes}") from error

        self.predictor = _make_predictor(predictor)
        self.max_cycles = max_cycles
        if max_cycles is not None and (not isinstance(max_cycles, int) or max_cycles < 1):
            raise ValueError("max_cycles debe ser un entero positivo o None")

        self.MEMORY = bytearray(_WORD_COUNT)
        self.REG = [0] * 8
        self.PC = 0
        self._NZP = 0b010
        self._PSR = 0b010
        self.USP = self._validate_stack_pointer("user_stack_pointer", user_stack_pointer)
        self.SSP = self._validate_stack_pointer("supervisor_stack_pointer", supervisor_stack_pointer)
        self.REG[6] = self.USP
        self.OC = 0
        self.halted = False
        self.input_fn = input_fn
        self.output_fn = sys.stdout.write if output_fn is None else output_fn
        self._flush_output = output_fn is None

        self._program_memory = bytearray(_WORD_COUNT)
        self._program_memory[0x3000:0xFE00] = b"\x01" * (0xFE00 - 0x3000)
        self._active_pc = None
        self._control_transfer = None
        self._branch_predictions = {}
        self._multi_entry = None
        self._multi_stages = []
        self._multi_stage_index = 0
        self._pipeline = {"fetch": None, "decode": None, "execute": None, "memory": None, "writeback": None}
        self._fetch_pc = 0
        self._pipeline_redirect = None
        self._stats = {
            "cycles": 0,
            "instructions": {"program": 0, "system": 0},
            "memory_reads": {"program": 0, "system": 0},
            "memory_writes": {"program": 0, "system": 0},
            "pipeline_stalls": 0,
        }

        self.trap_handlers = {}
        halt_vector = getattr(instrucciones, "TRAP_HALT", None)
        if halt_vector is not None:
            self.trap_handlers[halt_vector] = self._halt_service
        if trap_handlers:
            self.trap_handlers.update(trap_handlers)

        if load_os:
            self.load_os_image(os_path)

        if program is not None:
            self.load_program(
                program,
                include_orig=include_orig,
                start_address=start_address,
            )
        elif start_address is not None:
            self.PC = self._parse_address(start_address) & 0xFFFF
            self._fetch_pc = self.PC

    @property
    def NZP(self):
        return self._NZP

    @NZP.setter
    def NZP(self, value):
        self._NZP = int(value) & 0b111
        self._PSR = (self._PSR & ~0b111) | self._NZP

    @property
    def PSR(self):
        return self._PSR

    @PSR.setter
    def PSR(self, value):
        self._PSR = int(value) & 0xFFFF
        self._NZP = self._PSR & 0b111

    @property
    def privileged(self):
        return bool(self.PSR & _PRIVILEGE_BIT)

    @staticmethod
    def _validate_stack_pointer(name, value):
        pointer = Simulador._parse_address(value)
        if not 0 <= pointer < _WORD_COUNT or pointer & 1:
            raise ValueError(f"{name} debe ser una dirección par dentro de memoria")
        return pointer

    def load_os_image(self, path=None):
        """Carga OS.hex en memoria como código del sistema."""
        os_path = Path(path) if path is not None else Path(__file__).with_name("OS.hex")
        if not os_path.is_file():
            raise FileNotFoundError(f"No se encontró la imagen del sistema operativo: {os_path}")
        if os_path.stat().st_size == 0:
            raise ValueError(f"La imagen del sistema operativo está vacía: {os_path}")
        return self.load_program(os_path, space="system")

    @staticmethod
    def _parse_address(value):
        if isinstance(value, str):
            token = value.strip()
            if token.lower().startswith("x"):
                return int(token[1:], 16)
            return int(token, 0)
        return int(value)

    @staticmethod
    def _parse_byte(token, image_format="auto"):
        value = token.strip()
        if not value:
            raise ValueError("Se encontró una línea vacía donde se esperaba un byte")

        if image_format == "bin":
            if not re.fullmatch(r"[01]{8}", value):
                raise ValueError(f"Byte binario inválido: {value!r}")
            return int(value, 2)

        if image_format == "hex":
            if re.fullmatch(r"[0-9a-fA-F]{2}", value):
                return int(value, 16)
            if re.fullmatch(r"0[xX][0-9a-fA-F]{1,2}", value):
                return int(value, 16)
            raise ValueError(f"Byte hexadecimal inválido: {value!r}")

        if re.fullmatch(r"[01]{8}", value):
            return int(value, 2)
        if re.fullmatch(r"[0-9a-fA-F]{2}", value):
            return int(value, 16)
        try:
            number = int(value, 0)
        except ValueError:
            number = int(value, 10)
        if not 0 <= number <= 0xFF:
            raise ValueError(f"Valor fuera del rango de byte: {value!r}")
        return number

    @classmethod
    def _read_image(cls, source):
        if hasattr(source, "program_bytes") and hasattr(source, "orig_address"):
            return bytearray(source.program_bytes), int(source.orig_address)

        image_format = "auto"
        if isinstance(source, (str, Path)):
            path = Path(source)
            is_file = False
            try:
                is_file = path.is_file()
            except OSError:
                pass

            if is_file:
                text = path.read_text(encoding="utf-8")
                suffix = path.suffix.lower()
                if suffix == ".bin":
                    image_format = "bin"
                elif suffix == ".hex":
                    image_format = "hex"
            else:
                if isinstance(source, Path) or (
                    "\n" not in str(source)
                    and Path(source).suffix.lower() in (".hex", ".bin")
                ):
                    raise FileNotFoundError(f"No se encontró la imagen: {source}")
                text = str(source)
            lines = text.splitlines()
            byte_values = [cls._parse_byte(line, image_format) for line in lines if line.strip()]
            return bytearray(byte_values), None

        try:
            values = list(source)
        except TypeError as error:
            raise TypeError("El programa debe ser una ruta, texto o iterable de bytes") from error

        byte_values = []
        for value in values:
            if isinstance(value, int):
                if not 0 <= value <= 0xFF:
                    raise ValueError(f"Valor fuera del rango de byte: {value!r}")
                byte_values.append(value)
            elif isinstance(value, str):
                byte_values.append(cls._parse_byte(value))
            else:
                raise TypeError(f"Valor de byte no válido: {value!r}")
        return bytearray(byte_values), None

    def load_program(
        self,
        program,
        include_orig=True,
        start_address=None,
        space="program",
    ):
        """Carga bytes; por defecto consume los dos primeros como dirección inicial."""
        if space not in ("program", "system"):
            raise ValueError("space debe ser 'program' o 'system'")

        image, object_address = self._read_image(program)
        if object_address is not None:
            address = object_address if start_address is None else self._parse_address(start_address)
            data = image
        elif include_orig:
            if len(image) < 2:
                raise ValueError("La imagen debe incluir dos bytes de dirección inicial")
            address = (image[0] << 8) | image[1]
            data = image[2:]
            if start_address is not None:
                address = self._parse_address(start_address)
        else:
            address = 0 if start_address is None else self._parse_address(start_address)
            data = image

        if not 0 <= address < _WORD_COUNT:
            raise ValueError(f"Dirección inicial fuera de memoria: {address:#x}")
        if not data:
            raise ValueError("La imagen no contiene bytes de programa")
        if len(data) > _WORD_COUNT:
            raise ValueError("La imagen excede el tamaño de la memoria")

        for offset, byte in enumerate(data):
            location = (address + offset) & 0xFFFF
            self.MEMORY[location] = byte
            self._program_memory[location] = 1 if space == "program" else 0

        if space == "program":
            self.PC = address
            self._fetch_pc = address
            self.halted = False
        return address

    def read_byte(self, address):
        address = int(address) & 0xFFFF
        self._record_memory_access("read", address)
        return self.MEMORY[address]

    def read_word(self, address):
        address = int(address) & 0xFFFF
        self._record_memory_access("read", address)
        high = self.MEMORY[address]
        low = self.MEMORY[(address + 1) & 0xFFFF]
        return (high << 8) | low

    def write_byte(self, address, value):
        address = int(address) & 0xFFFF
        self._record_memory_access("write", address)
        self.MEMORY[address] = int(value) & 0xFF

    def write_word(self, address, value):
        address = int(address) & 0xFFFF
        value = int(value) & 0xFFFF
        self._record_memory_access("write", address)
        self.MEMORY[address] = (value >> 8) & 0xFF
        self.MEMORY[(address + 1) & 0xFFFF] = value & 0xFF

    def _record_memory_access(self, operation, address):
        space = "program" if self._program_memory[address] else "system"
        counter = "memory_reads" if operation == "read" else "memory_writes"
        self._stats[counter][space] += 1

    def _fetch(self, address):
        instruction_value = self.read_word(address)
        if instruction_value in (_SPECIAL_GETC, _SPECIAL_OUT):
            instruction = _SpecialInstruction(instruction_value)
        else:
            instruction = instrucciones.decode_instruction(instruction_value)
        return _PipelineEntry(instruction, address)

    @staticmethod
    def _stage_is_overridden(instruction, stage):
        method_name = f"on_{stage}"
        method = getattr(type(instruction), method_name)
        base_method = getattr(instrucciones.BASE_INSTRUCTION, method_name)
        return method is not base_method

    def _invoke_stage(self, entry, stage):
        if not self._stage_is_overridden(entry.instruction, stage):
            return
        method_name = f"on_{stage}"
        self.PC = entry.address
        self._active_pc = entry.address
        try:
            getattr(entry.instruction, method_name)(self)
        finally:
            self._active_pc = None

    def _required_multicycle_stages(self, instruction):
        stages = ["fetch"]
        stages.extend(
            stage
            for stage in ("decode", "execute", "memory", "writeback")
            if self._stage_is_overridden(instruction, stage)
        )
        return stages

    def _count_instruction(self, address):
        space = "program" if self._program_memory[address & 0xFFFF] else "system"
        self._stats["instructions"][space] += 1

    def _finish_nonpipeline_instruction(self, entry):
        self._count_instruction(entry.address)
        if self._control_transfer is None:
            self.PC = (entry.address + 2) & 0xFFFF
        else:
            self.PC = self._control_transfer
        self._fetch_pc = self.PC
        self._control_transfer = None
        self._multi_entry = None
        self._multi_stages = []
        self._multi_stage_index = 0

    def _step_single(self):
        entry = self._fetch(self.PC)
        self._control_transfer = None
        self._stats["cycles"] += 1
        for stage in ("decode", "execute", "memory", "writeback"):
            self._invoke_stage(entry, stage)
        self._finish_nonpipeline_instruction(entry)
        return True

    def _step_multi(self):
        if self._multi_entry is None:
            entry = self._fetch(self.PC)
            self._control_transfer = None
            self._multi_entry = entry
            self._multi_stages = self._required_multicycle_stages(entry.instruction)
            self._multi_stage_index = 1
            self._stats["cycles"] += 1
            if len(self._multi_stages) == 1:
                self._finish_nonpipeline_instruction(entry)
            return True

        entry = self._multi_entry
        stage = self._multi_stages[self._multi_stage_index]
        self._stats["cycles"] += 1
        self._invoke_stage(entry, stage)
        self._multi_stage_index += 1
        if self._multi_stage_index == len(self._multi_stages):
            self._finish_nonpipeline_instruction(entry)
        return True

    def _fetch_pipeline_entry(self):
        entry = self._fetch(self._fetch_pc)
        self._fetch_pc = (self._fetch_pc + 2) & 0xFFFF
        return entry

    def _discard_branch_predictions(self, entries):
        for entry in entries:
            if entry is not None:
                self._branch_predictions.pop(entry.address, None)

    def _step_pipeline(self):
        self._stats["cycles"] += 1
        previous = self._pipeline
        writeback = previous["writeback"]
        memory = previous["memory"]
        execute = previous["execute"]
        decode = previous["decode"]
        fetched = previous["fetch"]

        self._pipeline_redirect = None
        if writeback is not None:
            self._invoke_stage(writeback, "writeback")
            self._count_instruction(writeback.address)

        if self._pipeline_redirect is not None:
            target = self._pipeline_redirect
            self._pipeline_redirect = None
            self._fetch_pc = target
            self._discard_branch_predictions((memory, execute, decode, fetched))
            self._pipeline = dict.fromkeys(previous, None)
            self.PC = self._fetch_pc
            return True

        if memory is not None:
            self._invoke_stage(memory, "memory")

        early_redirect = None
        if execute is not None:
            self._invoke_stage(execute, "execute")
            early_redirect = self._pipeline_redirect
            self._pipeline_redirect = None
            prediction = self._branch_predictions.get(execute.address)
            if early_redirect is not None:
                self._fetch_pc = early_redirect
            elif prediction:
                target = getattr(execute.instruction, "destination", None)
                if target is None:
                    raise RuntimeError(
                        "Una instrucción que configura predicción de salto debe definir "
                        "'destination' al terminar on_execute"
                    )
                self._fetch_pc = int(target) & 0xFFFF
                early_redirect = self._fetch_pc

        if decode is not None and early_redirect is None:
            if "decode" not in decode.completed_stages:
                self._invoke_stage(decode, "decode")
                decode.completed_stages.add("decode")

        if early_redirect is not None:
            self._discard_branch_predictions((decode, fetched))
            next_pipeline = {
                "writeback": memory,
                "memory": execute,
                "execute": None,
                "decode": None,
                "fetch": None,
            }
            if not self.halted:
                next_pipeline["fetch"] = self._fetch_pipeline_entry()
            self._pipeline = next_pipeline
        else:
            next_pipeline = {
                "writeback": memory,
                "memory": execute,
                "execute": None,
                "decode": None,
                "fetch": fetched,
            }
            stalled = False
            if decode is not None:
                if memory is None and execute is None:
                    next_pipeline["execute"] = decode
                    next_pipeline["decode"] = fetched
                    next_pipeline["fetch"] = None
                else:
                    next_pipeline["decode"] = decode
                    self._stats["pipeline_stalls"] += 1
                    stalled = True
            else:
                next_pipeline["decode"] = fetched
                next_pipeline["fetch"] = None

            if not stalled and not self.halted:
                next_pipeline["fetch"] = self._fetch_pipeline_entry()
            self._pipeline = next_pipeline

        self.PC = self._fetch_pc
        return True

    def step(self):
        """Avanza una instrucción en mono ciclo o un ciclo en los otros modos."""
        if self.halted:
            return False
        if self.mode == "single":
            return self._step_single()
        if self.mode == "multi":
            return self._step_multi()
        return self._step_pipeline()

    def run(self, max_cycles=None):
        """Ejecuta hasta una llamada de parada o hasta alcanzar el límite de ciclos."""
        limit = self.max_cycles if max_cycles is None else max_cycles
        if limit is not None and (not isinstance(limit, int) or limit < 1):
            raise ValueError("max_cycles debe ser un entero positivo o None")
        initial_cycles = self._stats["cycles"]
        while not self.halted:
            if limit is not None and self._stats["cycles"] - initial_cycles >= limit:
                raise TimeoutError(f"El simulador superó el límite de {limit} ciclos")
            self.step()
        return self.get_stats()

    def conditional_branch_setup(self):
        """Registra la predicción de la instrucción activa."""
        address = self.PC if self._active_pc is None else self._active_pc
        prediction = bool(self.predictor.predict(pc=address))
        self._branch_predictions[address] = prediction
        return prediction

    def conditional_branch_result(self, taken, destination):
        """Actualiza el predictor y aplica el resultado real del salto."""
        address = self.PC if self._active_pc is None else self._active_pc
        actual = bool(taken)
        prediction = self._branch_predictions.pop(address, None)
        correct = self.predictor.update(address, actual, destination)

        if self.mode == "pipeline":
            predicted = (actual if correct else not actual) if prediction is None else prediction
            if predicted != actual:
                next_address = destination if actual else (address + 2)
                self._pipeline_redirect = int(next_address) & 0xFFFF
        elif actual:
            self._control_transfer = int(destination) & 0xFFFF
        return correct

    def unconditional_branch(self, destination):
        """Solicita una transferencia de control desde una instrucción."""
        target = int(destination) & 0xFFFF
        if self.mode == "pipeline":
            self._pipeline_redirect = target
        else:
            self._control_transfer = target

    def trap(self, vector):
        """Ejecuta un servicio registrado o entra al vector del sistema operativo."""
        vector = int(vector) & 0xFF
        handler = self.trap_handlers.get(vector)
        if handler is not None:
            target = handler(self)
            if target is not None:
                self.unconditional_branch(target)
            return

        saved_status = self.PSR
        return_address = self.REG[7] & 0xFFFF
        if self.privileged:
            self.SSP = self.REG[6] & 0xFFFF
        else:
            self.USP = self.REG[6] & 0xFFFF
            self.REG[6] = self.SSP

        # RTI pops PC first, so the saved return address is placed on top of PSR.
        self._push_word(saved_status)
        self._push_word(return_address)
        self.SSP = self.REG[6] & 0xFFFF
        self.PSR = saved_status | _PRIVILEGE_BIT
        handler_address = self.read_word((vector * 2) & 0xFFFF)
        self.unconditional_branch(handler_address)

    def _push_word(self, value):
        stack_pointer = self.REG[6] & 0xFFFF
        if stack_pointer & 1 or stack_pointer < 2:
            raise OverflowError(f"Pila fuera de memoria al apilar en {stack_pointer:#06x}")
        stack_pointer -= 2
        self.write_word(stack_pointer, value)
        self.REG[6] = stack_pointer

    def _pop_word(self):
        stack_pointer = self.REG[6] & 0xFFFF
        if stack_pointer & 1 or stack_pointer > 0xFFFC:
            raise OverflowError(f"Pila fuera de memoria al desapilar en {stack_pointer:#06x}")
        value = self.read_word(stack_pointer)
        self.REG[6] = stack_pointer + 2
        return value

    def _halt_service(self, machine):
        machine.halted = True
        return machine.REG[7]

    def raise_div_zero_exception(self):
        raise ZeroDivisionError("La instrucción intentó dividir por cero")

    def return_from_interrupt(self):
        if not self.privileged:
            raise PermissionError("RTI solo puede ejecutarse en modo privilegiado")

        return_address = self._pop_word()
        saved_status = self._pop_word()
        self.SSP = self.REG[6] & 0xFFFF
        if not saved_status & _PRIVILEGE_BIT:
            self.REG[6] = self.USP
        self.PSR = saved_status
        self.unconditional_branch(return_address)

    def _execute_special(self, instruction_value):
        if instruction_value == _SPECIAL_GETC:
            self.REG[0] = self._read_input_byte()
        elif instruction_value == _SPECIAL_OUT:
            value = self.REG[0] & 0xFF
            if value == 0x0A:
                character = "\n"
            elif value == 0x09:
                character = "\t"
            else:
                character = chr(value)
                if not character.isprintable():
                    character = _INVALID_OUTPUT_CHARACTER
            self.output_fn(character)
            if self._flush_output:
                sys.stdout.flush()
        else:
            raise ValueError(f"Instrucción especial del simulador desconocida: {instruction_value:#06x}")
        self.return_from_interrupt()

    def _read_input_byte(self):
        if self.input_fn is None:
            return _read_console_byte()

        value = self.input_fn()
        if isinstance(value, int):
            return 0x0A if value in (0x0D, 0x0A) else value & 0xFF
        if isinstance(value, bytes):
            if not value:
                raise EOFError("GETC no recibió ningún carácter")
            code = value[0]
            if code in (0x00, 0xE0):
                return 0x80 | (value[1] & 0x1F) if len(value) > 1 else _INVALID_KEY_CODE
            return 0x0A if code in (0x0D, 0x0A) else code
        if isinstance(value, str):
            if not value:
                raise EOFError("GETC no recibió ningún carácter")
            character = value[0]
            if character in ("\r", "\n"):
                return 0x0A
            code = ord(character)
            return code if code <= 0xFF else _INVALID_KEY_CODE
        raise TypeError("input_fn debe devolver una tecla como int, bytes o str")

    def _total(self, counter):
        return counter["program"] + counter["system"]

    def get_stats(self):
        """Devuelve contadores independientes por espacio de memoria y totales."""
        instructions = dict(self._stats["instructions"])
        memory_reads = dict(self._stats["memory_reads"])
        memory_writes = dict(self._stats["memory_writes"])
        accesses = {
            space: memory_reads[space] + memory_writes[space]
            for space in ("program", "system")
        }
        return {
            "mode": self.mode,
            "cycles": self._stats["cycles"],
            "instructions": {
                **instructions,
                "total": self._total(instructions),
            },
            "memory_reads": {
                **memory_reads,
                "total": self._total(memory_reads),
            },
            "memory_writes": {
                **memory_writes,
                "total": self._total(memory_writes),
            },
            "memory_accesses": {
                **accesses,
                "total": self._total(accesses),
            },
            "pipeline_stalls": self._stats["pipeline_stalls"],
            "halted": self.halted,
            "pc": self.PC,
            "predictor": self.predictor.get_stats(),
        }


Simulator = Simulador


def _cli_predictor_names():
    return [candidate.__name__ for candidate in _available_predictors()]


def main():
    parser = argparse.ArgumentParser(description="Simulador de la arquitectura ISA-G27")
    parser.add_argument("program", help="Archivo .hex o .bin")
    parser.add_argument(
        "-m",
        "--mode",
        choices=("single", "multi", "pipeline"),
        default="single",
        help="Modo de ejecución (por defecto: single)",
    )
    parser.add_argument(
        "--predictor",
        choices=_cli_predictor_names(),
        default=None,
        help="Predictor de saltos para el modo pipeline",
    )
    parser.add_argument(
        "--no-origin",
        action="store_true",
        help="La imagen no empieza con los dos bytes de dirección inicial",
    )
    parser.add_argument("--start-address", type=Simulador._parse_address)
    parser.add_argument("--no-os", action="store_true", help="No cargar OS.hex")
    parser.add_argument("--os-image", help="Ruta alternativa a OS.hex")
    parser.add_argument("--max-cycles", type=int, default=_DEFAULT_MAX_CYCLES)
    args = parser.parse_args()

    simulator = Simulador(
        args.program,
        mode=args.mode,
        predictor=args.predictor,
        include_orig=not args.no_origin,
        start_address=args.start_address,
        max_cycles=args.max_cycles,
        load_os=not args.no_os,
        os_path=args.os_image,
    )
    print("\n\n" + json.dumps(simulator.run(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
