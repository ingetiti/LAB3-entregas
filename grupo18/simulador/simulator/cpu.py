"""
cpu.py - CPU del simulador (ISA Lab 3c).

Integra Memory, Registers y decode() y ejecuta el ciclo Fetch-Decode-Execute:

  1. Fetch:   lee la palabra de 16 bits en la dirección PC (debe ser par).
  2. PC += 2  (el PC ya apunta a la instrucción siguiente durante Execute).
  3. Decode:  decode(word) -> DecodedInstruction.
  4. Execute: realiza la operación y actualiza registros, memoria y banderas.
  5. Se incrementa el contador de instrucciones (HALT también cuenta).

Banderas N/Z/P - qué instrucciones las actualizan:
  SI:  ADD SUB AND OR XOR NOT SHL SHR SAR  (resultado)
       LDW LDBL LDBH LDI                   (valor cargado)
       CMP                                 (comparación con signo, sin resultado)
  NO:  STW STBL STBH STI BR JSR JMP JSRR LEA TRAP NOP HALT
  (LEA calcula una dirección, no un dato con signo: no toca las banderas.)

Excepciones "precisas": si step() falla, el PC vuelve a apuntar a la
instrucción que falló, no se cuenta como ejecutada y ninguna instrucción
escribe registros o memoria antes de poder fallar.
"""

from simulator.decoder import InvalidInstructionError, decode, sign_extend
from simulator.isa import (
    BYTE_MASK,
    LINK_REGISTER,
    MODE_IMMEDIATE,
    NZP_N,
    NZP_P,
    NZP_Z,
    PC_INCREMENT,
    WORD_MASK,
)
from simulator.memory import Memory, MemoryAccessError
from simulator.registers import Registers, to_signed16
from simulator.traps import ConsoleIO, TrapServices, UnknownTrapError

DEFAULT_MAX_STEPS = 100_000       # límite por defecto de run()


# ----------------------------------------------------------------------
# Excepciones propias de la CPU
# (MemoryAccessError, InvalidInstructionError y UnknownTrapError se reutilizan)
# ----------------------------------------------------------------------
class CPUError(Exception):
    """Base de los errores propios de la CPU."""


class MisalignedAddressError(CPUError):
    """Búsqueda de instrucción o salto a una dirección impar."""


class ExecutionLimitError(CPUError):
    """run() alcanzó el límite de instrucciones sin que el programa terminara."""


class CPUHaltedError(CPUError):
    """Se pidió ejecutar una instrucción con la CPU ya detenida."""


# Todo lo que puede interrumpir una simulación (útil para el futuro main.py).
EXECUTION_ERRORS = (CPUError, MemoryAccessError, InvalidInstructionError,
                    UnknownTrapError)

# Operaciones aritmético-lógicas de dos operandos (16 bits sin signo).
# El resultado se recorta a 16 bits al escribirlo.
_ALU_OPERATIONS = {
    "ADD": lambda a, b: a + b,
    "SUB": lambda a, b: a - b,
    "AND": lambda a, b: a & b,
    "OR": lambda a, b: a | b,
    "XOR": lambda a, b: a ^ b,
}


class CPU:
    """Procesador de 16 bits: memoria + registros + decodificador + TRAP."""

    def __init__(self, memory=None, registers=None, io=None):
        self.memory = memory if memory is not None else Memory()
        self.registers = registers if registers is not None else Registers()
        self._io = io if io is not None else ConsoleIO()
        self._traps = TrapServices(self._io)
        self._halted = False
        self._halt_reason = None
        self._instruction_count = 0
        # mnemónico -> método que ejecuta esa instrucción
        self._handlers = {
            "ADD": self._exec_alu, "SUB": self._exec_alu,
            "AND": self._exec_alu, "OR": self._exec_alu,
            "XOR": self._exec_alu,
            "NOT": self._exec_not,
            "SHL": self._exec_shift, "SHR": self._exec_shift,
            "SAR": self._exec_shift,
            "CMP": self._exec_cmp,
            "LDW": self._exec_ldw, "STW": self._exec_stw,
            "LDBL": self._exec_ldbl, "LDBH": self._exec_ldbh,
            "STBL": self._exec_stbl, "STBH": self._exec_stbh,
            "LDI": self._exec_ldi, "STI": self._exec_sti,
            "BR": self._exec_br,
            "JSR": self._exec_jsr, "JSRR": self._exec_jsrr,
            "JMP": self._exec_jmp,
            "LEA": self._exec_lea,
            "TRAP": self._exec_trap,
            "NOP": self._exec_nop, "HALT": self._exec_halt,
        }

    # ------------------------------------------------------------------
    # Consultas
    # ------------------------------------------------------------------
    @property
    def io(self):
        """Dispositivo de entrada/salida usado por los TRAP."""
        return self._io

    @property
    def halted(self):
        return self._halted

    @property
    def halt_reason(self):
        """'HALT', 'TRAP x25' o None si la CPU sigue activa."""
        return self._halt_reason

    @property
    def instruction_count(self):
        """Instrucciones ejecutadas con éxito (HALT incluido)."""
        return self._instruction_count

    @property
    def memory_used(self):
        """Direcciones distintas escritas (programa cargado + datos + pila)."""
        return self.memory.used_bytes

    # ------------------------------------------------------------------
    # Carga de programas
    # ------------------------------------------------------------------
    def load_program(self, data, address, set_pc=True):
        """Copia `data` (bytes) en memoria desde `address`.

        Si set_pc es True, el PC pasa a valer `address`. Se valida que todo
        el bloque entre en memoria ANTES de escribir, así que un fallo no
        deja una carga parcial. No se exige que `address` sea par: esa
        restricción es de las instrucciones y se verifica en el Fetch.
        """
        if not isinstance(data, (bytes, bytearray)):
            raise TypeError(
                f"El programa debe ser bytes o bytearray, se recibió "
                f"{type(data).__name__}"
            )
        if isinstance(address, bool) or not isinstance(address, int):
            raise MemoryAccessError("La dirección de carga debe ser un entero")
        if address < 0 or address + len(data) > self.memory.SIZE:
            raise MemoryAccessError(
                f"El programa ({len(data)} bytes) no cabe en memoria desde "
                f"0x{address & 0xFFFFFFFF:04X}"
            )
        for offset, byte in enumerate(data):
            self.memory.write_byte(address + offset, byte)
        if set_pc:
            self.registers.pc = address

    # ------------------------------------------------------------------
    # Ejecución
    # ------------------------------------------------------------------
    def step(self):
        """Ejecuta UNA instrucción y devuelve su DecodedInstruction."""
        if self._halted:
            raise CPUHaltedError("La CPU está detenida; no se puede ejecutar step()")
        start_pc = self.registers.pc
        try:
            decoded = self._fetch_and_decode()
            self._handlers[decoded.mnemonic](decoded)
        except Exception:
            self.registers.pc = start_pc        # excepción precisa
            raise
        self._instruction_count += 1
        return decoded

    def run(self, max_steps=DEFAULT_MAX_STEPS):
        """Ejecuta hasta HALT (o TRAP x25). Devuelve las instrucciones de esta llamada.

        Lanza ExecutionLimitError si se ejecutan `max_steps` instrucciones y
        la CPU sigue sin detenerse. Si la CPU ya estaba detenida devuelve 0.
        """
        if isinstance(max_steps, bool) or not isinstance(max_steps, int) or max_steps < 1:
            raise ValueError(f"max_steps debe ser un entero >= 1, se recibió {max_steps!r}")
        executed = 0
        while not self._halted:
            if executed >= max_steps:
                raise ExecutionLimitError(
                    f"Se alcanzó el límite de {max_steps} instrucciones sin "
                    f"HALT (PC=0x{self.registers.pc:04X})"
                )
            self.step()
            executed += 1
        return executed

    # ------------------------------------------------------------------
    # Fetch / Decode
    # ------------------------------------------------------------------
    def _fetch_and_decode(self):
        pc = self.registers.pc
        self._check_aligned(pc, "Búsqueda de instrucción")
        word = self.memory.read_word(pc)
        self.registers.ir = word
        self.registers.pc = pc + PC_INCREMENT   # el setter enmascara a 16 bits
        return decode(word)                     # InvalidInstructionError si no es válida

    @staticmethod
    def _check_aligned(address, what):
        if address % PC_INCREMENT != 0:
            raise MisalignedAddressError(
                f"{what} en dirección impar 0x{address:04X}: las instrucciones "
                f"deben comenzar en direcciones pares"
            )

    # ------------------------------------------------------------------
    # Auxiliares de Execute
    # ------------------------------------------------------------------
    def _write_result(self, register, value):
        """Escribe el resultado (16 bits) y actualiza N/Z/P."""
        value &= WORD_MASK
        self.registers.write(register, value)
        self.registers.update_nzp(value)

    def _operand2(self, d):
        """Segundo operando del formato A como patrón de 16 bits."""
        if d.mode == MODE_IMMEDIATE:
            return d.imm & WORD_MASK            # inmediato con signo -> 16 bits
        return self.registers.read(d.sr2)

    def _effective_address(self, d):
        """EA = (R[BASE] + offset con signo) mod 65536."""
        return (self.registers.read(d.base) + d.offset) & WORD_MASK

    def _halt(self, reason):
        self._halted = True
        self._halt_reason = reason

    def _jump(self, target):
        self._check_aligned(target, "Salto")
        self.registers.pc = target

    def _call(self, target):
        """Guarda el PC ya incrementado en R7 y salta (R7 se escribe al final)."""
        self._check_aligned(target, "Salto")
        self.registers.write(LINK_REGISTER, self.registers.pc)
        self.registers.pc = target

    # ------------------------------------------------------------------
    # Aritmética y lógica
    # ------------------------------------------------------------------
    def _exec_alu(self, d):
        a = self.registers.read(d.sr1)
        b = self._operand2(d)
        self._write_result(d.dr, _ALU_OPERATIONS[d.mnemonic](a, b))

    def _exec_not(self, d):
        self._write_result(d.dr, ~self.registers.read(d.sr1))

    def _exec_shift(self, d):
        value = self.registers.read(d.sr1)
        amount = d.imm                          # 0..15, sin signo
        if d.mnemonic == "SHL":
            result = value << amount
        elif d.mnemonic == "SHR":
            result = value >> amount            # lógico: entra 0 por la izquierda
        else:                                   # SAR: conserva el bit de signo
            result = to_signed16(value) >> amount
        self._write_result(d.dr, result)

    def _exec_cmp(self, d):
        a = self.registers.read(d.sr1)
        b = d.imm if d.mode == MODE_IMMEDIATE else self.registers.read(d.sr2)
        self.registers.update_compare(a, b)     # comparación con signo directa

    # ------------------------------------------------------------------
    # Memoria (todas calculan EA y leen/escriben ANTES de modificar registros)
    # ------------------------------------------------------------------
    def _exec_ldw(self, d):
        self._write_result(d.reg, self.memory.read_word(self._effective_address(d)))

    def _exec_stw(self, d):
        self.memory.write_word(self._effective_address(d), self.registers.read(d.reg))

    def _exec_ldbl(self, d):
        byte = self.memory.read_byte(self._effective_address(d))
        self._write_result(d.reg, sign_extend(byte, 8))

    def _exec_ldbh(self, d):
        # EA+1 sin módulo: si EA = 0xFFFF, Memory rechaza 0x10000.
        byte = self.memory.read_byte(self._effective_address(d) + 1)
        self._write_result(d.reg, sign_extend(byte, 8))

    def _exec_stbl(self, d):
        self.memory.write_byte(self._effective_address(d),
                               self.registers.read(d.reg) & BYTE_MASK)

    def _exec_stbh(self, d):
        self.memory.write_byte(self._effective_address(d) + 1,
                               self.registers.read(d.reg) & BYTE_MASK)

    def _exec_ldi(self, d):
        pointer = self.memory.read_word(self._effective_address(d))
        self._write_result(d.reg, self.memory.read_word(pointer))

    def _exec_sti(self, d):
        pointer = self.memory.read_word(self._effective_address(d))
        self.memory.write_word(pointer, self.registers.read(d.reg))

    # ------------------------------------------------------------------
    # Saltos y subrutinas (el PC ya está incrementado)
    # ------------------------------------------------------------------
    def _exec_br(self, d):
        n, z, p = self.registers.condition_codes
        taken = ((bool(d.nzp & NZP_N) and n)
                 or (bool(d.nzp & NZP_Z) and z)
                 or (bool(d.nzp & NZP_P) and p))
        if taken:
            # Offset en PALABRAS: x PC_INCREMENT (2 bytes) lo pasa a bytes.
            self._jump((self.registers.pc + PC_INCREMENT * d.offset) & WORD_MASK)

    def _exec_jsr(self, d):
        self._call((self.registers.pc + PC_INCREMENT * d.offset) & WORD_MASK)

    def _exec_jsrr(self, d):
        # El destino se lee ANTES de escribir R7 (JSRR R7 es válido).
        self._call(self.registers.read(d.base))

    def _exec_jmp(self, d):
        self._jump(self.registers.read(d.base))

    def _exec_lea(self, d):
        # Offset en BYTES. Puede dar direcciones impares (son datos).
        self.registers.write(d.dr, (self.registers.pc + d.offset) & WORD_MASK)

    # ------------------------------------------------------------------
    # Sistema
    # ------------------------------------------------------------------
    def _exec_trap(self, d):
        if self._traps.handle(d.vector, self.registers, self.memory):
            self._halt(f"TRAP x{d.vector:02X}")

    def _exec_nop(self, d):
        pass

    def _exec_halt(self, d):
        self._halt("HALT")