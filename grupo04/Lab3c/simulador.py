from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path
from typing import TextIO


# ============================================================
# CONSTANTES GENERALES
# ============================================================

MEMORY_SIZE = 1 << 16       # 65536 bytes
MASK_16 = 0xFFFF
MASK_8 = 0xFF

PC_START = 0x3000

# Mapa de memoria del sistema (ver so.asm)
USER_BASE = 0x3000          # desde aquí empieza el programa de usuario;
                            # toda instrucción con PC < USER_BASE es del SO
TRAP_TABLE = 0x0000         # 128 palabras; entrada = 2 * vector
INT_TABLE = 0x0100          # 128 palabras; entrada = 0x0100 + 2 * vector
OS_CODE_START = 0x0200      # código y datos del SO (después de las tablas)

# Registros de dispositivos (memory-mapped, palabras en direcciones pares)
DEVICE_BASE = 0xFE00
KBSR = 0xFE00               # bit 15 = dato listo, bit 14 = IE
KBDR = 0xFE02               # dato; leerlo baja "listo"
DSR = 0xFE04                # bit 15 = pantalla lista (siempre)
DDR = 0xFE06                # escribir = imprimir el byte bajo
PSR_ADDR = 0xFFFC           # estado del procesador
MCR = 0xFFFE                # bit 15 = reloj; escribir 0 = detener

# Vectores de la tabla de interrupciones / excepciones
VEC_PRIVILEGE = 0x00        # RTI ejecutada en modo usuario
VEC_ILLEGAL = 0x01          # opcode ilegal
VEC_KEYBOARD = 0x10         # interrupción de teclado
KB_PRIORITY = 4

# Valores iniciales de arranque (los fija el "hardware", como en la LC-3)
BOOT_USER_SP = 0xFE00       # R6 del programa de usuario
BOOT_SUPERVISOR_SP = 0x3000 # pila de supervisor: crece hacia abajo


# ============================================================
# REGISTROS
# ============================================================

R0, R1, R2, R3, R4, R5, R6, R7 = range(8)

REGISTER_COUNT = 8


# ============================================================
# FLAGS
# ============================================================

N_FLAG = 0b100
Z_FLAG = 0b010
P_FLAG = 0b001



# ============================================================
# OPCODES DE LA ISA (deben coincidir con assembly.py)
# ============================================================

OP_BR   = 0x00
OP_ADD  = 0x01
OP_LDW  = 0x02
OP_STW  = 0x03
OP_JSR  = 0x04
OP_AND  = 0x05
OP_LDR  = 0x06
OP_STR  = 0x07
OP_MULH = 0x08   # parte alta del producto (antes RTI)
OP_NOT  = 0x09
OP_LDBL = 0x0A
OP_STBL = 0x0B
OP_JMP  = 0x0C
OP_LDBH = 0x0D
OP_LEA  = 0x0E
OP_ADDC = 0x0F   # suma con acarreo (antes NOP; NOP = BR nzp=000 = 0x0000)
OP_STBH = 0x10
OP_LDBR = 0x11
OP_STRB = 0x12
OP_SUB  = 0x13
OP_MUL  = 0x14
OP_DIV  = 0x15
OP_ADDI = 0x16   # ADD inmediato imm5
OP_SHL  = 0x17
OP_SHR  = 0x18

# Opcodes extendidos: aportan el BIT 8 (signo) del offset de
# BR / LDW / STW / LEA (9 bits, en palabras) y el BIT 5 del offset
# de LDR / STR (6 bits, en bytes). Ver OP_EXT en assembly.py.
OP_BRX  = 0x19
OP_LDWX = 0x1A
OP_STWX = 0x1B
OP_LEAX = 0x1C
OP_LDRX = 0x1D
OP_STRX = 0x1E

OP_TRAP = 0x1F

RESERVED_OPCODES = ()   # no quedan opcodes reservados


# ============================================================
# TRAPS
# ============================================================

TRAP_GETC = 0x20
TRAP_OUT = 0x21
TRAP_PUTS = 0x22
TRAP_IN = 0x23
TRAP_PUTSP = 0x24
TRAP_HALT = 0x25


# ============================================================
# EXCEPCIONES
# ============================================================

class SimulatorError(Exception):
    """Error durante la carga o ejecución del programa."""


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def sign_extend(value: int, bit_count: int) -> int:
    """Extiende con signo un valor de bit_count bits."""
    value &= (1 << bit_count) - 1

    if value & (1 << (bit_count - 1)):
        return value - (1 << bit_count)

    return value


def to_uint16(value: int) -> int:
    return value & MASK_16


def to_uint8(value: int) -> int:
    return value & MASK_8


def signed16(value: int) -> int:
    return sign_extend(value, 16)


def signed8(value: int) -> int:
    return sign_extend(value, 8)


def trunc_div(a: int, b: int) -> int:
    """División entera truncada hacia cero (b != 0)."""
    quotient = abs(a) // abs(b)

    return -quotient if (a < 0) != (b < 0) else quotient


# ============================================================
# SIMULADOR
# ============================================================

class Simulator:

    def __init__(
        self,
        input_stream: TextIO | None = None,
        output_stream: TextIO | None = None,
    ):

        # Memoria BYTE-ADDRESSABLE.
        # Una palabra de 16 bits ocupa dos posiciones y se guarda
        # en BIG-ENDIAN (igual que emite assembly.py):
        #
        #   memory[a]     -> byte alto
        #   memory[a + 1] -> byte bajo

        self.memory = bytearray(MEMORY_SIZE)

        self.registers = [0] * REGISTER_COUNT

        # Pila de usuario inicial (como el reset de la LC-3). Con R6 = 0 la
        # pila daría la vuelta hasta xFFFE, que es el registro MCR.
        self.registers[R6] = BOOT_USER_SP

        self.pc = 0

        self.cc = Z_FLAG

        # Bit de acarreo C (lo actualizan ADD, ADDI, SUB y ADDC)
        self.carry = 0

        self.halted = False

        # Instrucciones ejecutadas (todas) y, dentro de ellas, las que
        # se ejecutaron con PC < USER_BASE (código del SO)
        self.steps = 0
        self.os_steps = 0

        # ---- Estado del procesador (PSR) ----
        # PSR[15] = modo (1 usuario / 0 supervisor), PSR[10:8] = prioridad,
        # PSR[3] = C (acarreo, propio de esta ISA), PSR[2:0] = N Z P
        self.user_mode = True
        self.priority = 0
        self.saved_usp = BOOT_USER_SP
        self.saved_ssp = BOOT_SUPERVISOR_SP

        # ---- Sistema operativo y dispositivos ----
        self.os_loaded = False      # hay SO en memoria (TRAP usa la tabla)
        self.os_code_bytes = 0
        self.os_table_bytes = 0
        self.kb_ie = False          # KBSR[14]
        self.kb_char = None         # carácter pendiente en KBDR
        self.kb_eof = False
        self.key_events = []        # [(paso, carácter)] para pruebas

        # Bytes del programa cargado
        self.program_bytes = 0

        # Direcciones de memoria accedidas
        self.accessed_addresses: set[int] = set()

        self.input_stream = (
            input_stream if input_stream is not None else sys.stdin
        )

        self.output_stream = (
            output_stream if output_stream is not None else sys.stdout
        )

    # ========================================================
    # MEMORIA
    # ========================================================

    def _check_address(self, address: int) -> int:

        if address < 0 or address >= MEMORY_SIZE:
            raise SimulatorError(
                f"Dirección de memoria fuera de rango: {address}"
            )

        return address

    def _read_byte(self, address: int) -> int:

        address &= MASK_16

        if address >= DEVICE_BASE:
            raise SimulatorError(
                f"Acceso a byte en registros de dispositivo x{address:04X} "
                "(solo se permiten palabras)."
            )

        self.accessed_addresses.add(address)

        return self.memory[address]

    def _write_byte(self, address: int, value: int):

        address &= MASK_16

        if address >= DEVICE_BASE:
            raise SimulatorError(
                f"Acceso a byte en registros de dispositivo x{address:04X} "
                "(solo se permiten palabras)."
            )

        self.accessed_addresses.add(address)

        self.memory[address] = value & MASK_8

    def _read_word(self, address: int) -> int:
        """Lee una palabra de 16 bits en Big-Endian."""

        if (address & MASK_16) >= DEVICE_BASE:
            return self._device_read(address & MASK_16)

        high_byte = self._read_byte(address)
        low_byte = self._read_byte(address + 1)

        return (high_byte << 8) | low_byte

    def _write_word(self, address: int, value: int):
        """Escribe una palabra de 16 bits en Big-Endian."""

        value &= MASK_16

        if (address & MASK_16) >= DEVICE_BASE:
            self._device_write(address & MASK_16, value)
            return

        self._write_byte(address, value >> 8)
        self._write_byte(address + 1, value & MASK_8)

    # ========================================================
    # REGISTROS Y FLAGS
    # ========================================================

    def _write_register(self, register: int, value: int):
        """Escribe 16 bits en un registro y actualiza N/Z/P."""

        value &= MASK_16

        self.registers[register] = value

        self._set_condition_codes(value)

    def _set_condition_codes(self, value: int):

        signed = signed16(value)

        if signed < 0:
            self.cc = N_FLAG

        elif signed == 0:
            self.cc = Z_FLAG

        else:
            self.cc = P_FLAG

    # ========================================================
    # CARGA DEL PROGRAMA
    # ========================================================

    def load_object(self, obj: bytes) -> int:
        """
        Carga un archivo de código máquina.

            Bytes 0-1 : ORIGEN (big-endian)
            Resto     : programa (palabras big-endian)

        El programa puede tener una cantidad impar de bytes
        (por ejemplo, si termina en un .STRINGZ).
        """

        if len(obj) < 2:
            raise SimulatorError(
                "El archivo de código máquina debe contener "
                "al menos los dos bytes de origen."
            )

        origin = (obj[0] << 8) | obj[1]

        program = obj[2:]

        if origin % 2 != 0:
            raise SimulatorError(
                f"Dirección inicial impar: x{origin:04X}."
            )

        if origin + len(program) > MEMORY_SIZE:
            raise SimulatorError(
                "El programa excede el espacio de memoria."
            )

        for i, byte in enumerate(program):
            self._write_byte(origin + i, byte)

        self.program_bytes = len(program)

        self.pc = origin

        return origin

    def load_os(self, obj: bytes) -> int:
        """
        Carga la imagen del sistema operativo (formato .obj, igual que un
        programa) y deja la máquina en el estado de arranque: modo usuario,
        R6 = BOOT_USER_SP. No modifica PC ni los contadores del programa.

        Contabilidad de memoria: el SO se cuenta como el programa de usuario:
        sus bytes de código y de datos (desde OS_CODE_START) y las entradas
        no nulas de las tablas de vectores. Se cargan sin pasar por
        _write_byte para no contar el relleno de ceros de las tablas.
        """

        if len(obj) < 2:
            raise SimulatorError("Imagen de SO vacía.")

        origin = (obj[0] << 8) | obj[1]
        image = obj[2:]

        if origin % 2 != 0 or origin + len(image) > DEVICE_BASE:
            raise SimulatorError("Imagen de SO inválida o con origen impar.")

        if origin + len(image) > USER_BASE - 0x100:
            raise SimulatorError(
                "El SO invade la pila de supervisor (debe terminar antes "
                f"de x{USER_BASE - 0x100:04X})."
            )

        self.memory[origin:origin + len(image)] = image

        end = origin + len(image)

        self.os_code_bytes = max(0, end - max(origin, OS_CODE_START))
        self.os_table_bytes = 0

        for address in range(origin, min(end, OS_CODE_START), 2):
            if self.memory[address] or self.memory[address + 1]:
                self.os_table_bytes += 2
                self.accessed_addresses.update((address, address + 1))

        self.accessed_addresses.update(
            range(max(origin, OS_CODE_START), end)
        )

        self.os_loaded = True
        self.user_mode = True
        self.priority = 0
        self.registers[R6] = BOOT_USER_SP
        self.saved_ssp = BOOT_SUPERVISOR_SP

        return origin

    def load_os_file(self, path: str | Path) -> int:

        try:
            obj = Path(path).read_bytes()

        except OSError as exc:
            raise SimulatorError(
                f"No se pudo leer el SO: {exc}"
            ) from exc

        return self.load_os(obj)

    # ========================================================
    # PSR
    # ========================================================

    def _get_psr(self) -> int:

        return (
            ((1 if self.user_mode else 0) << 15)
            | ((self.priority & 0x7) << 8)
            | ((self.carry & 1) << 3)
            | (self.cc & 0x7)
        )

    def _set_psr(self, value: int):

        self.user_mode = bool((value >> 15) & 1)
        self.priority = (value >> 8) & 0x7
        self.carry = (value >> 3) & 1
        self.cc = value & 0x7

    # ========================================================
    # EXCEPCIONES E INTERRUPCIONES
    # ========================================================

    def _push_word(self, value: int):

        self.registers[R6] = (self.registers[R6] - 2) & MASK_16
        self._write_word(self.registers[R6], value)

    def _pop_word(self) -> int:

        value = self._read_word(self.registers[R6])
        self.registers[R6] = (self.registers[R6] + 2) & MASK_16

        return value

    def _enter_interrupt(self, vector: int, priority: int | None = None):
        """
        Secuencia de hardware de una interrupción o excepción (no es una
        instrucción: no incrementa 'steps'):

          1. Si estaba en modo usuario: Saved_USP = R6; R6 = Saved_SSP.
          2. Apila PSR y luego PC (PC = instrucción a reanudar).
          3. Modo supervisor; si es una interrupción, prioridad = la del
             dispositivo.
          4. PC = mem[INT_TABLE + 2 * vector].
        """

        if not self.os_loaded:
            raise SimulatorError(
                f"Excepción/interrupción x{vector:02X} sin SO cargado."
            )

        psr = self._get_psr()

        if self.user_mode:
            self.saved_usp = self.registers[R6]
            self.registers[R6] = self.saved_ssp

        self._push_word(psr)
        self._push_word(self.pc)

        self.user_mode = False

        if priority is not None:
            self.priority = priority

        target = self._read_word(INT_TABLE + 2 * vector)

        if target == 0:
            raise SimulatorError(
                f"Vector de interrupción x{vector:02X} sin rutina."
            )

        self.pc = target

    def _execute_rti(self):

        if self.user_mode:
            # RTI es privilegiada
            self._enter_interrupt(VEC_PRIVILEGE)
            return

        new_pc = self._pop_word()
        new_psr = self._pop_word()

        self._check_jump_address(new_pc)

        self._set_psr(new_psr)

        self.pc = new_pc

        if self.user_mode:
            # Vuelve a la pila de usuario
            self.saved_ssp = self.registers[R6]
            self.registers[R6] = self.saved_usp

    # ========================================================
    # DISPOSITIVOS (memory-mapped)
    # ========================================================

    def _is_tty(self) -> bool:

        return (
            self.input_stream is sys.stdin
            and hasattr(sys.stdin, "isatty")
            and sys.stdin.isatty()
        )

    @staticmethod
    def _tty_key_available() -> bool:

        try:
            import msvcrt  # Windows

            return msvcrt.kbhit()

        except ImportError:
            import select

            return bool(select.select([sys.stdin], [], [], 0)[0])

    def _kb_refill(self, blocking: bool):
        """Intenta dejar un carácter pendiente en KBDR."""

        if self.kb_char is not None:
            return

        # Eventos de teclado programados (pruebas): por número de paso.
        if self.key_events:

            if self.key_events[0][0] <= self.steps:
                self.kb_char = ord(self.key_events.pop(0)[1]) & MASK_8

            return

        if self._is_tty():

            if (blocking and not self.kb_ie) or self._tty_key_available():
                self.kb_char = self._read_key_raw()

            return

        if self.kb_eof:
            return

        character = self.input_stream.read(1)

        if character == "":
            self.kb_eof = True
            return

        self.kb_char = ord(character) & MASK_8

    def _device_read(self, address: int) -> int:

        if address % 2 != 0:
            raise SimulatorError(
                f"Acceso desalineado a dispositivo x{address:04X}."
            )

        if address == KBSR:

            self._kb_refill(blocking=True)

            if (
                self.kb_char is None
                and self.kb_eof
                and not self.key_events
            ):
                raise SimulatorError("No hay más caracteres disponibles.")

            ready = 0x8000 if self.kb_char is not None else 0

            return ready | (0x4000 if self.kb_ie else 0)

        if address == KBDR:

            value = self.kb_char if self.kb_char is not None else 0
            self.kb_char = None

            return value

        if address == DSR:
            return 0x8000

        if address == DDR:
            return 0

        if address == PSR_ADDR:
            return self._get_psr()

        if address == MCR:
            return 0 if self.halted else 0x8000

        raise SimulatorError(
            f"Registro de dispositivo inexistente x{address:04X}."
        )

    def _device_write(self, address: int, value: int):

        if address % 2 != 0:
            raise SimulatorError(
                f"Acceso desalineado a dispositivo x{address:04X}."
            )

        if address == KBSR:
            self.kb_ie = bool(value & 0x4000)

        elif address == DDR:
            self._write_character(value)

        elif address == PSR_ADDR:

            if self.user_mode:
                # Escribir el PSR es privilegiado
                self._enter_interrupt(VEC_PRIVILEGE)

            else:
                self._set_psr(value)

        elif address == MCR:

            if not (value & 0x8000):
                self.halted = True

        elif address in (KBDR, DSR):
            pass   # solo lectura

        else:
            raise SimulatorError(
                f"Registro de dispositivo inexistente x{address:04X}."
            )

    def load_object_file(self, path: str | Path) -> int:

        try:
            obj = Path(path).read_bytes()

        except OSError as exc:
            raise SimulatorError(
                f"No se pudo leer el archivo: {exc}"
            ) from exc

        return self.load_object(obj)

    # ========================================================
    # FETCH
    # ========================================================

    def fetch(self) -> int:
        """Obtiene la instrucción en PC y deja PC = PC + 2."""

        if self.pc % 2 != 0:
            raise SimulatorError(
                f"PC desalineado en x{self.pc:04X}."
            )

        instruction = self._read_word(self.pc)

        self.pc = (self.pc + 2) & MASK_16

        return instruction

    # ========================================================
    # EJECUCIÓN
    # ========================================================

    def run(self, max_steps: int = 1_000_000):

        if max_steps < 1:
            raise SimulatorError(
                "El límite de instrucciones debe ser mayor que cero."
            )

        start_steps = self.steps

        while not self.halted and self.steps - start_steps < max_steps:
            self.step()

        if not self.halted:
            raise SimulatorError(
                f"Se alcanzó el límite de {max_steps} instrucciones."
            )

        return self.steps - start_steps

    # ========================================================
    # DECODIFICACIÓN: AYUDAS
    # ========================================================

    @staticmethod
    def _dr(instruction: int) -> int:
        return (instruction >> 8) & 0x7

    @staticmethod
    def _sr1(instruction: int) -> int:
        return (instruction >> 5) & 0x7

    def _pc_relative(
        self,
        instruction: int,
        scale: int = 1,
        ext: int | None = None,
    ) -> int:
        """
        Dirección PC-relative.

        ext = None -> offset de 8 bits con signo, en BYTES
                      (LDBL, STBL, LDBH, STBH)
        ext = 0/1  -> offset de 9 bits en PALABRAS (scale = 2):
                      el bit 8 (signo) lo aporta el opcode
                      (BR, LDW, STW, LEA)

        self.pc ya vale PC + 2 porque el fetch ya se hizo.
        (igual que assembly.py: destino - (PC + 2))
        """

        if ext is None:
            offset = sign_extend(instruction & 0xFF, 8)

        else:
            offset = sign_extend(
                (ext << 8) | (instruction & 0xFF),
                9,
            )

        return (self.pc + scale * offset) & MASK_16

    def _base_offset(
        self,
        instruction: int,
        ext: int | None = None,
    ) -> int:
        """
        Dirección BaseR + offset (en bytes).

        ext = None -> offset de 5 bits con signo, en BYTES (LDBR, STRB)
        ext = 0/1  -> offset de 6 bits en PALABRAS (se multiplica por 2);
                      el bit 5 (signo) lo aporta el opcode (LDR, STR).
                      Igual que LDW/STW en la LC-3b: BaseR + 2*offset6.
        """

        if ext is None:
            offset = sign_extend(instruction & 0x1F, 5)

        else:
            offset = 2 * sign_extend(
                (ext << 5) | (instruction & 0x1F),
                6,
            )

        return (self.registers[self._sr1(instruction)] + offset) & MASK_16

    def _operand(self, instruction: int) -> int:
        """
        Segundo operando de las instrucciones ALU:
        imm4 con signo (bit 4 = 1) o registro SR2 (con signo).
        """

        if (instruction >> 4) & 0x1:
            return sign_extend(instruction & 0xF, 4)

        return signed16(self.registers[instruction & 0x7])

    # ========================================================
    # DECODIFICACIÓN Y EJECUCIÓN
    # ========================================================

    def step(self):

        # Interrupción de teclado: se atiende entre instrucciones si el
        # dispositivo la habilitó (IE) y su prioridad supera la del PSR.
        if self.kb_ie and self.priority < KB_PRIORITY:

            self._kb_refill(blocking=False)

            if self.kb_char is not None:
                self._enter_interrupt(VEC_KEYBOARD, KB_PRIORITY)

        instruction_address = self.pc

        instruction = self.fetch()

        opcode = (instruction >> 11) & 0x1F

        dr = self._dr(instruction)
        sr1 = self._sr1(instruction)

        # ----------------------------------------------------
        # BR
        # ----------------------------------------------------

        if opcode in (OP_BR, OP_BRX):

            condition = (instruction >> 8) & 0x7

            if condition & self.cc:

                target = self._pc_relative(
                    instruction,
                    scale=2,
                    ext=1 if opcode == OP_BRX else 0,
                )

                self._check_jump_address(target)

                self.pc = target

        # ----------------------------------------------------
        # ADD / SUB / MUL
        # ----------------------------------------------------

        elif opcode == OP_ADD:

            # ADD solo en modo registro: DR = SR1 + SR2
            self.carry = (
                (self.registers[sr1] + self.registers[instruction & 0x7])
                >> 16
            ) & 1
            self._write_register(
                dr,
                signed16(self.registers[sr1])
                + signed16(self.registers[instruction & 0x7]),
            )

        elif opcode == OP_ADDI:

            # ADDI: DR = SR1 + imm5 (-16..15)
            self.carry = (
                (self.registers[sr1]
                 + (sign_extend(instruction & 0x1F, 5) & MASK_16))
                >> 16
            ) & 1
            self._write_register(
                dr,
                signed16(self.registers[sr1])
                + sign_extend(instruction & 0x1F, 5),
            )

        elif opcode == OP_SUB:

            # C = 1 si hubo prestamo (SR1 < SR2 sin signo)
            self.carry = int(
                self.registers[sr1] < (self._operand(instruction) & MASK_16)
            )
            self._write_register(
                dr,
                signed16(self.registers[sr1]) - self._operand(instruction),
            )

        elif opcode == OP_MUL:

            self._write_register(
                dr,
                signed16(self.registers[sr1]) * self._operand(instruction),
            )

        elif opcode == OP_MULH:

            # Parte alta (bits 31..16) del producto CON signo de 32 bits.
            # MUL da los 16 bits bajos y MULH los 16 altos.
            self._write_register(
                dr,
                (signed16(self.registers[sr1])
                 * self._operand(instruction)) >> 16,
            )

        elif opcode == OP_ADDC:

            # ADDC: DR = SR1 + SR2 + C  (solo modo registro)
            total = (
                self.registers[sr1]
                + self.registers[instruction & 0x7]
                + self.carry
            )
            self.carry = (total >> 16) & 1
            self._write_register(dr, total)

        # ----------------------------------------------------
        # DIV (truncado hacia cero)
        # ----------------------------------------------------

        elif opcode == OP_DIV:

            divisor = self._operand(instruction)

            if divisor == 0:
                raise SimulatorError(
                    f"División por cero en x{instruction_address:04X}."
                )

            dividend = signed16(self.registers[sr1])

            self._write_register(dr, trunc_div(dividend, divisor))

        # ----------------------------------------------------
        # AND / NOT
        # ----------------------------------------------------

        elif opcode == OP_AND:

            self._write_register(
                dr,
                self.registers[sr1]
                & (self._operand(instruction) & MASK_16),
            )

        elif opcode == OP_NOT:

            self._write_register(dr, ~self.registers[sr1])

        # ----------------------------------------------------
        # SHL / SHR  (cantidad SIN signo, 0..15)
        # ----------------------------------------------------

        elif opcode == OP_SHL:

            self._write_register(
                dr,
                self.registers[sr1] << (instruction & 0xF),
            )

        elif opcode == OP_SHR:

            # Desplazamiento aritmético
            self._write_register(
                dr,
                signed16(self.registers[sr1]) >> (instruction & 0xF),
            )

        # ----------------------------------------------------
        # LDW / STW (PC-relative)
        # ----------------------------------------------------

        elif opcode in (OP_LDW, OP_LDWX):

            ext = 1 if opcode == OP_LDWX else 0

            self._write_register(
                dr,
                self._read_word(
                    self._pc_relative(instruction, scale=2, ext=ext)
                ),
            )

        elif opcode in (OP_STW, OP_STWX):

            ext = 1 if opcode == OP_STWX else 0

            self._write_word(
                self._pc_relative(instruction, scale=2, ext=ext),
                self.registers[dr],
            )

        # ----------------------------------------------------
        # LDR / STR (BaseR + offset5)
        # ----------------------------------------------------

        elif opcode in (OP_LDR, OP_LDRX):

            ext = 1 if opcode == OP_LDRX else 0

            self._write_register(
                dr,
                self._read_word(self._base_offset(instruction, ext)),
            )

        elif opcode in (OP_STR, OP_STRX):

            ext = 1 if opcode == OP_STRX else 0

            self._write_word(
                self._base_offset(instruction, ext),
                self.registers[dr],
            )

        # ----------------------------------------------------
        # LDBL / LDBH / STBL / STBH (PC-relative, byte)
        # ----------------------------------------------------

        elif opcode == OP_LDBL:

            byte = self._read_byte(self._pc_relative(instruction))

            self._write_register(dr, sign_extend(byte, 8))

        elif opcode == OP_LDBH:

            byte = self._read_byte(self._pc_relative(instruction))

            # El byte se coloca en DR[15:8]
            self._write_register(dr, byte << 8)

        elif opcode == OP_STBL:

            self._write_byte(
                self._pc_relative(instruction),
                self.registers[dr] & MASK_8,
            )

        elif opcode == OP_STBH:

            self._write_byte(
                self._pc_relative(instruction),
                (self.registers[dr] >> 8) & MASK_8,
            )

        # ----------------------------------------------------
        # LDBR / STRB (BaseR + offset5, byte)
        # ----------------------------------------------------

        elif opcode == OP_LDBR:

            byte = self._read_byte(self._base_offset(instruction))

            self._write_register(dr, sign_extend(byte, 8))

        elif opcode == OP_STRB:

            self._write_byte(
                self._base_offset(instruction),
                self.registers[dr] & MASK_8,
            )

        # ----------------------------------------------------
        # LEA
        # ----------------------------------------------------

        elif opcode in (OP_LEA, OP_LEAX):

            ext = 1 if opcode == OP_LEAX else 0

            self._write_register(
                dr,
                self._pc_relative(instruction, scale=2, ext=ext),
            )

        # ----------------------------------------------------
        # JSR / JSRR
        # ----------------------------------------------------

        elif opcode == OP_JSR:

            if (instruction >> 10) & 0x1:

                offset = sign_extend(instruction & 0x3FF, 10)

                # Offset en PALABRAS
                target = (self.pc + 2 * offset) & MASK_16

            else:

                # Se lee la base ANTES de pisar R7
                # (JSRR R7 debe usar el valor anterior de R7).
                target = self.registers[sr1]

            # Guardar PC + 2 (el PC ya fue incrementado)
            self.registers[R7] = self.pc

            self._check_jump_address(target)

            self.pc = target

        # ----------------------------------------------------
        # JMP / RET
        # ----------------------------------------------------

        elif opcode == OP_JMP:

            # Campo DR (bits 10..8): 000 = JMP/RET, 001 = RTI.
            # Cualquier otro valor es una combinación ilegal.
            variant = dr

            if variant == 0:

                target = self.registers[sr1]

                self._check_jump_address(target)

                self.pc = target

            elif variant == 1:

                self._execute_rti()

            else:

                self._enter_interrupt(VEC_ILLEGAL)

        # ----------------------------------------------------
        # TRAP
        # ----------------------------------------------------

        elif opcode == OP_TRAP:

            vector = instruction & 0x7F

            if self.os_loaded:

                # TRAP real: R7 = PC (siguiente instrucción) y salto a la
                # rutina del SO, que se ejecuta (y se cuenta) como código.
                self.registers[R7] = self.pc

                target = self._read_word(TRAP_TABLE + 2 * vector)

                if target == 0:
                    raise SimulatorError(
                        f"TRAP x{vector:02X} sin rutina en la tabla."
                    )

                self.pc = target

            else:

                # Modo heredado (sin SO): el TRAP se resuelve en Python
                # y cuenta como UNA instrucción.
                self._execute_trap(vector)

        # ----------------------------------------------------
        # RESERVADOS / DESCONOCIDOS
        # ----------------------------------------------------

        elif opcode in RESERVED_OPCODES:

            raise SimulatorError(
                f"Opcode reservado x{opcode:02X} "
                f"en x{instruction_address:04X}."
            )

        else:

            raise SimulatorError(
                f"Opcode desconocido x{opcode:02X} "
                f"en x{instruction_address:04X}."
            )

        self.steps += 1

        if instruction_address < USER_BASE:
            self.os_steps += 1

    # ========================================================
    # SALTOS
    # ========================================================

    def _check_jump_address(self, address: int):

        address &= MASK_16

        if address % 2 != 0:
            raise SimulatorError(
                f"Salto a dirección impar x{address:04X}."
            )

    # ========================================================
    # TRAPS
    # ========================================================

    def _read_key_raw(self) -> int:
        """
        Lee UNA tecla sin esperar Enter y sin eco (como el GETC real
        de la LC-3). Enter se entrega como '\\n' (10).
        Solo se usa cuando la entrada es una consola interactiva.
        """

        try:
            import msvcrt  # Windows

            while True:
                ch = msvcrt.getwch()

                if ch == "\x03":
                    raise KeyboardInterrupt

                if ch in ("\x00", "\xe0"):   # tecla especial: se ignora
                    msvcrt.getwch()
                    continue

                if ch == "\r":
                    ch = "\n"

                return ord(ch) & MASK_8

        except ImportError:
            import os
            import termios
            import tty

            fd = sys.stdin.fileno()
            old = termios.tcgetattr(fd)

            try:
                tty.setcbreak(fd)
                data = os.read(fd, 1)
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old)

            if not data:
                raise SimulatorError("No hay más caracteres disponibles.")

            return data[0] & MASK_8

    def _read_character(self) -> int:

        if (
            self.input_stream is sys.stdin
            and hasattr(sys.stdin, "isatty")
            and sys.stdin.isatty()
        ):
            return self._read_key_raw()

        character = self.input_stream.read(1)

        if character == "":
            raise SimulatorError("No hay más caracteres disponibles.")

        return ord(character) & MASK_8

    def _write_character(self, value: int):

        self.output_stream.write(chr(value & MASK_8))

        self.output_stream.flush()

    def _write_text(self, text: str):

        self.output_stream.write(text)

        self.output_stream.flush()

    def _read_string(self, address: int):

        for _ in range(MEMORY_SIZE):

            value = self._read_byte(address)

            if value == 0:
                return

            self._write_character(value)

            address = (address + 1) & MASK_16

        raise SimulatorError("La cadena TRAP no tiene terminador nulo.")

    def _execute_trap(self, vector: int):

        if vector == TRAP_GETC:

            self.registers[R0] = self._read_character()

            self._set_condition_codes(self.registers[R0])

        elif vector == TRAP_OUT:

            self._write_character(self.registers[R0])

        elif vector == TRAP_PUTS:

            self._read_string(self.registers[R0])

        elif vector == TRAP_IN:

            self._write_text("Enter a character: ")

            self.registers[R0] = self._read_character()

            self._write_character(self.registers[R0])

        elif vector == TRAP_PUTSP:

            address = self.registers[R0]

            for _ in range(MEMORY_SIZE):

                word = self._read_word(address)

                if word == 0:
                    return

                # Big-endian: primero el byte alto de la palabra
                # en memoria, luego el bajo (orden de memoria).
                first = (word >> 8) & 0xFF
                second = word & 0xFF

                self._write_character(first)

                if second != 0:
                    self._write_character(second)

                address = (address + 2) & MASK_16

        elif vector == TRAP_HALT:

            self._write_text("\nHALT\n")

            self.halted = True

        else:

            raise SimulatorError(
                f"TRAP x{vector:02X} no implementado."
            )

    # ========================================================
    # ESTADÍSTICAS
    # ========================================================

    def get_stats(self) -> dict[str, int]:

        return {
            "instrucciones_ejecutadas": self.steps,
            "instrucciones_usuario": self.steps - self.os_steps,
            "instrucciones_so": self.os_steps,
            "bytes_programa": self.program_bytes,
            "bytes_so": self.os_code_bytes + self.os_table_bytes,
            "bytes_memoria_usados": len(self.accessed_addresses),
        }

    # ========================================================
    # DEBUG
    # ========================================================

    def print_registers(self):

        print()
        print("===== REGISTROS =====")

        for i in range(REGISTER_COUNT):

            value = self.registers[i]

            print(f"R{i} : x{value:04X}  {signed16(value):6d}")

        print(f"PC : x{self.pc:04X}  {signed16(self.pc):6d}")

        print()

        print(f"FLAGS N/Z/P: {self.cc:03b}   C: {self.carry}")

        print(
            f"PSR: x{self._get_psr():04X}  "
            f"modo: {'usuario' if self.user_mode else 'supervisor'}  "
            f"prioridad: {self.priority}"
        )

    def print_memory(self, start: int, end: int):

        print()
        print("===== MEMORIA =====")

        address = start

        while address <= end:

            print(f"x{address:04X}: {self._read_byte(address):02X}")

            address += 1


# ============================================================
# SISTEMA OPERATIVO POR DEFECTO
# ============================================================

def default_os_image(directory: str | Path | None = None) -> bytes:
    """
    Devuelve la imagen .obj del SO (so.obj junto a este archivo). Si no
    existe, la ensambla desde so.asm.
    """

    base = Path(directory) if directory else Path(__file__).resolve().parent

    obj_path = base / "so.obj"

    if obj_path.exists():
        return obj_path.read_bytes()

    asm_path = base / "so.asm"

    if not asm_path.exists():
        raise SimulatorError(
            f"No se encontró el SO ({obj_path} ni {asm_path})."
        )

    import assembly

    return assembly.assemble_project_file(str(asm_path), "obj", None)


def make_simulator(
    input_stream: TextIO | None = None,
    output_stream: TextIO | None = None,
    with_os: bool = True,
    os_path: str | Path | None = None,
) -> Simulator:
    """Crea un simulador con el SO cargado (o sin él: TRAP heredado)."""

    simulator = Simulator(input_stream, output_stream)

    if with_os:

        if os_path:
            simulator.load_os_file(os_path)

        else:
            simulator.load_os(default_os_image())

    return simulator


# ============================================================
# MAIN
# ============================================================

def main():

    parser = argparse.ArgumentParser(
        description="Simulador funcional de la ISA personalizada."
    )

    parser.add_argument(
        "object_file",
        help="Archivo de código máquina (.obj).",
    )

    parser.add_argument(
        "--max-steps",
        type=int,
        default=1_000_000,
        help="Máximo de instrucciones antes de detener la ejecución.",
    )

    parser.add_argument(
        "--input",
        help="Texto de entrada para los TRAP.",
    )

    parser.add_argument(
        "--os",
        dest="os_path",
        help="Imagen del SO (.obj). Por defecto so.obj junto al simulador "
        "(se ensambla desde so.asm si falta).",
    )

    parser.add_argument(
        "--no-os",
        action="store_true",
        help="No carga el SO: los TRAP se resuelven en Python y cuentan "
        "como una sola instrucción (modo heredado).",
    )

    parser.add_argument(
        "--stats",
        action="store_true",
        help="Muestra estadísticas de ejecución.",
    )

    parser.add_argument(
        "--registers",
        action="store_true",
        help="Muestra los registros al finalizar.",
    )

    args = parser.parse_args()

    input_stream = (
        io.StringIO(args.input) if args.input is not None else sys.stdin
    )

    exit_code = 0

    try:

        simulator = make_simulator(
            input_stream=input_stream,
            output_stream=sys.stdout,
            with_os=not args.no_os,
            os_path=args.os_path,
        )

    except SimulatorError as exc:

        print(f"ERROR: {exc}", file=sys.stderr)

        return 1

    try:

        simulator.load_object_file(args.object_file)

        simulator.run(args.max_steps)

    except SimulatorError as exc:

        print(f"ERROR: {exc}", file=sys.stderr)

        exit_code = 1

    # Los registros y estadísticas se muestran también si hubo
    # error: ayudan a depurar.

    if args.registers:
        simulator.print_registers()

    if args.stats:

        stats = simulator.get_stats()

        print()
        print("===== ESTADÍSTICAS =====")

        print(
            "Instrucciones ejecutadas : "
            f"{stats['instrucciones_ejecutadas']}"
        )

        print(
            "  del usuario            : "
            f"{stats['instrucciones_usuario']}"
        )

        print(
            "  del SO                 : "
            f"{stats['instrucciones_so']}"
        )

        print(
            "Bytes del programa       : "
            f"{stats['bytes_programa']}"
        )

        print(
            "Bytes del SO             : "
            f"{stats['bytes_so']}"
        )

        print(
            "Bytes de memoria usados  : "
            f"{stats['bytes_memoria_usados']}"
        )

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
