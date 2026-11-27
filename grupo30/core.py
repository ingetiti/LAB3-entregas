"""
core.py - Núcleo de ejecución (Memory + CPU) de la ISA Skynet (16 bits)
=========================================================================
Desacoplado de archivos, consola y GUI. La E/S se inyecta con callbacks
(output_fn / input_fn). Implementa la memoria byte-addressable de 64 KB
Little-Endian con métricas y el procesador de 32 opcodes con flags NZP.
"""

import os
from typing import Callable, Dict, Optional, Set, Tuple

from isa import *   # noqa: F401,F403  (única fuente de verdad)


# ======================= Carga cacheada del OS =======================
DEFAULT_OS_ASM = os.path.join(os.path.dirname(os.path.abspath(__file__)), "os_rutinas.asm")
_OS_IMAGE_CACHE: Dict[Tuple[str, float], Tuple[int, bytes, Dict[int, str]]] = {}


def load_os_image(os_asm_path: Optional[str] = None) -> Tuple[int, bytes, Dict[int, str]]:
    """Ensambla (con caché por ruta y mtime) las rutinas del OS para nuestra ISA."""
    path = os.path.abspath(os_asm_path or DEFAULT_OS_ASM)
    mtime = os.path.getmtime(path)
    key = (path, mtime)
    cached = _OS_IMAGE_CACHE.get(key)
    if cached is not None:
        return cached

    from assembler import Assembler  # Import diferido para evitar ciclos
    asm = Assembler()
    origin, blob = asm.assemble([path])
    symbols = {
        addr & MASK16: name
        for name, addr in asm.symbols.items()
        if "-" not in name
    }
    res = (origin, blob, symbols)
    _OS_IMAGE_CACHE[key] = res
    return res


# ======================= Excepciones =======================
class CPUException(Exception):
    """Cualquier error de ejecución: termina el programa con mensaje claro."""

class OddPCException(CPUException): pass
class InvalidOpcodeException(CPUException): pass
class MemoryAccessException(CPUException): pass
class TrapException(CPUException): pass


# ======================= Memoria =======================
class Memory:
    """64 KB byte addressable, Little-Endian, con estadísticas de uso."""

    def __init__(self, size: int = MEM_SIZE):
        self.size = size
        self.data = bytearray(size)
        self.mmio_read16: Optional[Callable[[int], Optional[int]]] = None
        self.mmio_write16: Optional[Callable[[int, int], bool]] = None
        self.reset_stats()

    def reset_stats(self):
        self.reads = 0                      # bytes de datos leídos
        self.writes = 0                     # bytes de datos escritos
        self.fetches = 0                    # palabras de instrucción leídas
        self.read_addrs: Set[int] = set()
        self.written_addrs: Set[int] = set()
        self.fetched_addrs: Set[int] = set()

    @property
    def touched(self) -> Set[int]:
        return self.read_addrs | self.written_addrs | self.fetched_addrs

    def _check(self, addr: int):
        if not (0 <= addr < self.size):
            raise MemoryAccessException(f"Acceso fuera de rango: dirección x{addr:04X} ({addr})")

    def read8(self, addr: int) -> int:
        addr &= MASK16
        self._check(addr)
        self.reads += 1
        self.read_addrs.add(addr)
        return self.data[addr]

    def write8(self, addr: int, val: int):
        addr &= MASK16
        self._check(addr)
        self.writes += 1
        self.written_addrs.add(addr)
        self.data[addr] = val & MASK8

    def read16(self, addr: int) -> int:
        addr &= MASK16
        if self.mmio_read16 is not None:
            val = self.mmio_read16(addr)
            if val is not None:
                self._check(addr)
                self._check((addr + 1) & MASK16)
                self.reads += 2
                self.read_addrs.add(addr)
                self.read_addrs.add((addr + 1) & MASK16)
                return val & MASK16
        b0 = self.read8(addr)
        b1 = self.read8((addr + 1) & MASK16)
        return b0 | (b1 << 8)

    def write16(self, addr: int, val: int):
        addr &= MASK16
        if self.mmio_write16 is not None and self.mmio_write16(addr, val & MASK16):
            self._check(addr)
            self._check((addr + 1) & MASK16)
            self.writes += 2
            self.written_addrs.add(addr)
            self.written_addrs.add((addr + 1) & MASK16)
            return
        self.write8(addr, val & MASK8)
        self.write8((addr + 1) & MASK16, (val >> 8) & MASK8)

    def fetch16(self, addr: int) -> int:
        """Búsqueda de instrucción: se contabiliza aparte de los datos."""
        addr &= MASK16
        self._check(addr)
        self._check((addr + 1) & MASK16)
        self.fetches += 1
        self.fetched_addrs.update((addr, (addr + 1) & MASK16))
        return self.data[addr] | (self.data[(addr + 1) & MASK16] << 8)

    def peek16(self, addr: int) -> int:
        """Lectura SIN estadísticas (para debugger/desensamblador)."""
        addr &= MASK16
        return self.data[addr] | (self.data[(addr + 1) & MASK16] << 8)

    def load_bytes(self, origin: int, blob: bytes):
        """Carga inicial del programa (no cuenta como uso de memoria de ejecución)."""
        if origin < 0 or origin + len(blob) > self.size:
            raise MemoryAccessException("El programa no entra en la memoria de 64 KB")
        self.data[origin:origin + len(blob)] = blob


# ======================= CPU =======================
class CPU:
    def __init__(self,
                 output_fn: Optional[Callable[[str], None]] = None,
                 input_fn: Optional[Callable[[], int]] = None,
                 contar_os: bool = False,
                 os_asm_path: Optional[str] = None):
        self.mem = Memory()
        self.output_fn = output_fn or (lambda s: print(s, end=""))
        self.input_fn = input_fn or (lambda: 0)
        self.contar_os = bool(contar_os)
        self.os_asm_path = os_asm_path
        self.symbols: Dict[int, str] = {}       # {dirección: etiqueta}, opcional
        self._os_origin: int = 0
        self._os_code_start: int = 0
        self._os_code_end: int = 0
        self._os_symbols: Dict[int, str] = {}
        self._os_loaded: bool = False
        self._in_os: bool = False
        self._os_halt_pending: bool = False
        self._saved_user_nzp: Optional[Tuple[bool, bool, bool]] = None
        self._table = self._build_table()
        self.reset()

    # ---------- modo OS y E/S mapeada en memoria (MMIO) ----------
    def set_contar_os(self, enabled: bool):
        """Activa o desactiva el modo de rutinas de OS (por defecto False)."""
        self.contar_os = bool(enabled)

    def _mmio_read16(self, addr: int) -> Optional[int]:
        if addr == MMIO_KBSR:
            return 0x8000
        if addr == MMIO_KBDR:
            return self.input_fn() & MASK8
        if addr == MMIO_DSR:
            return 0x8000
        if addr == MMIO_MCR:
            return 0x0000 if (self.halted or self._os_halt_pending) else 0x8000
        return None

    def _mmio_write16(self, addr: int, val: int) -> bool:
        if addr == MMIO_DDR:
            self.output_fn(chr(val & MASK8))
            return True
        if addr == MMIO_MCR:
            if (val & 0x8000) == 0:
                if self._in_os:
                    # Permite que OS_TRAP_HALT restaure registros y ejecute RET antes de detener
                    self._os_halt_pending = True
                else:
                    self.halted = True
            return True
        return False

    def _install_os(self):
        """Carga las rutinas ensambladas del OS en memoria baja (sin sumar estadísticas)."""
        origin, blob, os_syms = load_os_image(self.os_asm_path)
        self.mem.load_bytes(origin, blob)
        self._os_origin = origin
        self._os_code_start = OS_CODE_ORIG
        self._os_code_end = origin + len(blob)
        self._os_symbols = os_syms
        self._os_loaded = True
        self.mem.mmio_read16 = self._mmio_read16
        self.mem.mmio_write16 = self._mmio_write16

    def _is_os_addr(self, addr: int) -> bool:
        return self.contar_os and self._os_loaded and (self._os_code_start <= addr < self._os_code_end)

    def _is_os_or_mmio_addr(self, addr: int) -> bool:
        if addr >= MMIO_KBSR:
            return True
        if not (self.contar_os and self._os_loaded):
            return False
        return (addr < 0x0100) or (self._os_code_start <= addr < self._os_code_end)

    def user_dynamic_memory_bytes(self) -> int:
        """Bytes de memoria de usuario usados fuera del binario cargado (pila/datos dinámicos, sin OS)."""
        prog_start = self.program_origin
        prog_end = prog_start + self.program_size
        return sum(
            1 for a in self.mem.touched
            if not (prog_start <= a < prog_end) and not self._is_os_or_mmio_addr(a)
        )

    def user_memory_bytes(self) -> int:
        """Espacio total de memoria de usuario usado (programa + pila/datos dinámicos, sin contar OS)."""
        return self.program_size + self.user_dynamic_memory_bytes()

    # ---------- estado ----------
    def reset(self, pc: int = DEFAULT_ORIGIN, clear_memory: bool = False):
        self.regs = [0] * NUM_REGS
        self.regs[SP_REG] = SP_INIT             # R6 = 0xFE00 (puntero de pila SP)
        self.pc = pc & MASK16
        self.n = False
        self.z = True
        self.p = False
        self.halted = False
        self.instr_count = 0
        self.user_instr_count = 0
        self.os_instr_count = 0
        self._in_os = False
        self._os_halt_pending = False
        self._saved_user_nzp = None
        if not hasattr(self, "program_origin"):
            self.program_origin = pc & MASK16
            self.program_size = 0
        if clear_memory:
            self.mem.data = bytearray(self.mem.size)
            self.program_origin = pc & MASK16
            self.program_size = 0
        if self.contar_os:
            self._install_os()
        else:
            self.mem.mmio_read16 = None
            self.mem.mmio_write16 = None
            self._os_origin = 0
            self._os_code_start = 0
            self._os_code_end = 0
            self._os_symbols = {}
            self._os_loaded = False
        self.mem.reset_stats()

    def load_program(self, origin: int, blob: bytes):
        if self.contar_os:
            if not self._os_loaded:
                self._install_os()
            if origin < self._os_code_end and (origin + len(blob)) > self._os_origin:
                raise MemoryAccessException(
                    f"Colisión de memoria con zona del OS [x{self._os_origin:04X}, x{self._os_code_end:04X})"
                )
        self.mem.load_bytes(origin, blob)
        self.program_origin = origin & MASK16
        self.program_size = len(blob)
        self.pc = origin & MASK16

    @property
    def cond(self) -> int:
        return (FL_N if self.n else 0) | (FL_Z if self.z else 0) | (FL_P if self.p else 0)

    def _set_nzp(self, val: int):
        s = to_int16(val)
        self.n, self.z, self.p = (s < 0), (s == 0), (s > 0)

    def _write_reg(self, r: int, val: int, set_flags: bool = True):
        self.regs[r] = to_uint16(val)
        if set_flags:
            self._set_nzp(self.regs[r])

    # ---------- ciclo de instrucción ----------
    def step(self) -> bool:
        """Fetch -> decode -> execute de UNA instrucción. False si la CPU se detuvo."""
        if self.halted:
            return False
        if self.pc & 1:
            raise OddPCException(f"Excepción: PC en dirección impar (x{self.pc:04X})")
        at = self.pc
        in_os_step = self._is_os_addr(at)
        instr = self.mem.fetch16(at)                        # FETCH
        self.pc = to_uint16(at + INSTR_SIZE)                # PC -> siguiente (PC + 2)
        handler = self._table.get(f_opcode(instr))          # DECODE
        if handler is None:
            raise InvalidOpcodeException(
                f"Excepción: opcode inválido {f_opcode(instr)} "
                f"(x{instr:04X}) en x{at:04X}")
        handler(instr)                                      # EXECUTE
        self.instr_count += 1
        if in_os_step:
            self.os_instr_count += 1
        else:
            self.user_instr_count += 1
        if self.contar_os and self._in_os:
            if self.halted or not self._is_os_addr(self.pc):
                if self._saved_user_nzp is not None:
                    self.n, self.z, self.p = self._saved_user_nzp
                    self._saved_user_nzp = None
                self._in_os = False
                if self._os_halt_pending:
                    self._os_halt_pending = False
                    self.halted = True
        return not self.halted

    def run(self, max_steps: Optional[int] = None) -> int:
        while not self.halted:
            if max_steps is not None and self.instr_count >= max_steps:
                break
            self.step()
        return self.instr_count

    def stats(self) -> dict:
        m = self.mem
        return {
            "instrucciones": self.instr_count,
            "instrucciones_usuario": self.user_instr_count,
            "instrucciones_os": self.os_instr_count,
            "palabras_buscadas": m.fetches,
            "bytes_leidos": m.reads,
            "bytes_escritos": m.writes,
            "direcciones_tocadas": len(m.touched),
            "direcciones_leidas": len(m.read_addrs),
            "direcciones_escritas": len(m.written_addrs),
            "memoria_programa_bytes": self.program_size,
            "memoria_pila_datos_bytes": self.user_dynamic_memory_bytes(),
            "memoria_usuario_bytes": self.user_memory_bytes(),
        }

    # ==================== Opcodes Bloque A (0 a 15) ====================
    def _op_br(self, i: int):
        # 0: BR / NOP. No modifica NZP
        if f_nzp(i) & self.cond:
            self.pc = to_uint16(self.pc + f_off8(i) * INSTR_SIZE)

    def _op_add(self, i: int):
        # 1: ADD. Modular 16b, actualiza NZP
        dr = f_dr(i)
        sr1 = self.regs[f_sr1(i)]
        op2 = self.regs[f_sr2(i)] if f_bit4(i) == 0 else to_uint16(f_imm4(i))
        self._write_reg(dr, sr1 + op2)

    def _op_ld(self, i: int):
        # 2: LD. Palabra 16b Little-Endian desde PC+2 + 2*off8. Actualiza NZP
        ea = to_uint16(self.pc + f_off8(i) * INSTR_SIZE)
        self._write_reg(f_dr(i), self.mem.read16(ea))

    def _op_st(self, i: int):
        # 3: ST. Palabra 16b Little-Endian en PC+2 + 2*off8. No modifica NZP
        ea = to_uint16(self.pc + f_off8(i) * INSTR_SIZE)
        self.mem.write16(ea, self.regs[f_dr(i)])

    def _op_jsr(self, i: int):
        # 4: JSR / JSRR. Guarda R7 = PC+2. No modifica NZP
        target = to_uint16(self.pc + f_off10(i) * INSTR_SIZE) if f_bit10(i) == 1 else self.regs[f_sr1(i)]
        self.regs[LINK_REG] = self.pc
        self.pc = target

    def _op_and(self, i: int):
        # 5: AND. Actualiza NZP
        dr = f_dr(i)
        sr1 = self.regs[f_sr1(i)]
        op2 = self.regs[f_sr2(i)] if f_bit4(i) == 0 else to_uint16(f_imm4(i))
        self._write_reg(dr, sr1 & op2)

    def _op_ldr(self, i: int):
        # 6: LDR. Palabra 16b desde (BaseR + 2*off5) con bit 0 forzado a 0. Actualiza NZP
        ea = to_uint16(self.regs[f_sr1(i)] + f_off5(i) * INSTR_SIZE) & ~1
        self._write_reg(f_dr(i), self.mem.read16(ea))

    def _op_str(self, i: int):
        # 7: STR. Palabra 16b en (BaseR + 2*off5) con bit 0 forzado a 0. No modifica NZP
        ea = to_uint16(self.regs[f_sr1(i)] + f_off5(i) * INSTR_SIZE) & ~1
        self.mem.write16(ea, self.regs[f_dr(i)])

    def _op_ldb(self, i: int):
        # 8: LDB. Carga 1 byte con sign-extend a 16b. Actualiza NZP
        ea = to_uint16(self.regs[f_sr1(i)] + f_off5(i))
        self._write_reg(f_dr(i), to_int8(self.mem.read8(ea)))

    def _op_not(self, i: int):
        # 9: NOT. Inversión bit a bit (~SR1). Actualiza NZP
        self._write_reg(f_dr(i), ~self.regs[f_sr1(i)])

    def _op_ldh(self, i: int):
        # 10: LDH. Carga 1 byte en DR[15:8] conservando DR[7:0]. NZP sobre el DR completo
        ea = to_uint16(self.regs[f_sr1(i)] + f_off5(i))
        b = self.mem.read8(ea)
        dr = f_dr(i)
        val = (b << 8) | (self.regs[dr] & MASK8)
        self._write_reg(dr, val)

    def _op_sth(self, i: int):
        # 11: STH. Guarda SR[15:8] en BaseR + off5. No modifica NZP
        ea = to_uint16(self.regs[f_sr1(i)] + f_off5(i))
        self.mem.write8(ea, (self.regs[f_dr(i)] >> 8) & MASK8)

    def _op_jmp(self, i: int):
        # 12: JMP / RET (RET = JMP R7). No modifica NZP
        self.pc = self.regs[f_sr1(i)]

    def _op_stb(self, i: int):
        # 13: STB. Guarda SR[7:0] en BaseR + off5. No modifica NZP
        ea = to_uint16(self.regs[f_sr1(i)] + f_off5(i))
        self.mem.write8(ea, self.regs[f_dr(i)] & MASK8)

    def _op_lea(self, i: int):
        # 14: LEA. DR = PC+2 + 2*off8. NO modifica NZP
        ea = to_uint16(self.pc + f_off8(i) * INSTR_SIZE)
        self._write_reg(f_dr(i), ea, set_flags=False)

    def _op_trap(self, i: int):
        # 15: TRAP. R7 = PC+2. No modifica NZP
        self.regs[LINK_REG] = self.pc
        vec = f_trap7(i)
        if not self.contar_os:
            self.handle_trap(vec)
            return
        entry_addr = to_uint16(OS_TVT_BASE + vec * INSTR_SIZE)
        target = self.mem.read16(entry_addr)
        if target == 0:
            raise TrapException(f"TRAP x{vec:02X} no implementado")
        if not self._in_os:
            self._saved_user_nzp = (self.n, self.z, self.p)
            self._in_os = True
        self.pc = target

    # ==================== Opcodes Bloque B (16 a 31) ====================
    def _op_sub(self, i: int):
        # 16: SUB. DR = SR1 - op2 (modular 16b). Actualiza NZP
        dr = f_dr(i)
        sr1 = self.regs[f_sr1(i)]
        op2 = self.regs[f_sr2(i)] if f_bit4(i) == 0 else to_uint16(f_imm4(i))
        self._write_reg(dr, sr1 - op2)

    def _op_or(self, i: int):
        # 17: OR. Actualiza NZP
        dr = f_dr(i)
        sr1 = self.regs[f_sr1(i)]
        op2 = self.regs[f_sr2(i)] if f_bit4(i) == 0 else to_uint16(f_imm4(i))
        self._write_reg(dr, sr1 | op2)

    def _op_xor(self, i: int):
        # 18: XOR. Actualiza NZP
        dr = f_dr(i)
        sr1 = self.regs[f_sr1(i)]
        op2 = self.regs[f_sr2(i)] if f_bit4(i) == 0 else to_uint16(f_imm4(i))
        self._write_reg(dr, sr1 ^ op2)

    def _op_cmp(self, i: int):
        # 19: CMP. SR1 - op2 en 17 bits exactos, solo actualiza NZP (no modifica registros)
        s1 = to_int16(self.regs[f_sr1(i)])
        op2 = to_int16(self.regs[f_sr2(i)]) if f_bit4(i) == 0 else f_imm4(i)
        diff = s1 - op2
        self.n = diff < 0
        self.z = diff == 0
        self.p = diff > 0

    def _op_addi(self, i: int):
        # 20: ADDI / MOVI. M=0: ADDI (Rd += imm7); M=1: MOVI (Rd = imm7). Modular 16b, actualiza NZP
        rd = f_dr(i)
        imm7 = f_imm7(i)
        if f_bit7(i) == 0:
            self._write_reg(rd, self.regs[rd] + imm7)
        else:
            self._write_reg(rd, imm7)

    def _op_shl(self, i: int):
        # 21: SHL. Desplazamiento lógico izquierda (0..15). Actualiza NZP
        amt = (self.regs[f_sr2(i)] & 0xF) if f_bit4(i) == 0 else f_uimm4(i)
        self._write_reg(f_dr(i), self.regs[f_sr1(i)] << amt)

    def _op_asr(self, i: int):
        # 22: ASR. Desplazamiento aritmético derecha con extensión de signo (0..15). Actualiza NZP
        amt = (self.regs[f_sr2(i)] & 0xF) if f_bit4(i) == 0 else f_uimm4(i)
        s1 = to_int16(self.regs[f_sr1(i)])
        self._write_reg(f_dr(i), s1 >> amt)

    def _op_lsr(self, i: int):
        # 23: LSR. Desplazamiento lógico derecha con ceros (0..15). Actualiza NZP
        amt = (self.regs[f_sr2(i)] & 0xF) if f_bit4(i) == 0 else f_uimm4(i)
        u1 = self.regs[f_sr1(i)] & MASK16
        self._write_reg(f_dr(i), u1 >> amt)

    def _op_mull(self, i: int):
        # 24: MULL / MULH. Producto 32b con signo: x=0 MULL [15:0], x=1 MULH [31:16]. Actualiza NZP
        s1 = to_int16(self.regs[f_sr1(i)])
        s2 = to_int16(self.regs[f_sr2(i)])
        prod_u32 = (s1 * s2) & MASK32
        res = (prod_u32 >> 16) & MASK16 if f_bit3(i) == 1 else prod_u32 & MASK16
        self._write_reg(f_dr(i), res)

    def _op_div(self, i: int):
        # 25: DIV / REM. x=0 DIV (trunc hacia 0), x=1 REM (signo del dividendo). Actualiza NZP
        s1 = to_int16(self.regs[f_sr1(i)])
        s2 = to_int16(self.regs[f_sr2(i)])
        is_rem = f_bit3(i) == 1

        if s2 == 0:
            if is_rem:
                res = s1
            else:
                if s1 > 0: res = 0x7FFF
                elif s1 < 0: res = -32768   # 0x8000
                else: res = 0
        elif s1 == -32768 and s2 == -1:
            res = 0 if is_rem else 0x7FFF
        else:
            sign = -1 if (s1 < 0) ^ (s2 < 0) else 1
            q = (abs(s1) // abs(s2)) * sign
            r = (abs(s1) % abs(s2)) * (-1 if s1 < 0 else 1)
            res = r if is_rem else q

        self._write_reg(f_dr(i), res)

    def _op_mulq(self, i: int):
        # 26: MULQ. (Rd * Rs) en 32b, redondeo simétrico al más cercano (+2^(n-1)), satura [-32768, 32767]. Actualiza NZP
        rd = f_dr(i)
        s1 = to_int16(self.regs[rd])
        s2 = to_int16(self.regs[f_sr1(i)])
        n = f_n5(i)

        prod = s1 * s2
        is_neg = prod < 0
        mag = abs(prod)
        mag_rounded = mag if n == 0 else mag + (1 << (n - 1))
        shifted = mag_rounded >> n
        res = -shifted if is_neg else shifted

        if res > 32767: res = 32767
        elif res < -32768: res = -32768
        self._write_reg(rd, res)

    def _op_divq(self, i: int):
        # 27: DIVQ. (Rd << n) / Rs en 32b, redondeo simétrico (si 2*|r| >= |Rs| -> +1), satura. Actualiza NZP
        rd = f_dr(i)
        s1 = to_int16(self.regs[rd])
        s2 = to_int16(self.regs[f_sr1(i)])
        n = f_n5(i)

        if s2 == 0:
            if s1 > 0: res = 0x7FFF
            elif s1 < 0: res = -32768       # 0x8000
            else: res = 0
        else:
            num = s1 << n
            is_neg = ((num < 0) ^ (s2 < 0)) if num != 0 else False
            mag_num = abs(num)
            mag_den = abs(s2)
            q = mag_num // mag_den
            r = mag_num % mag_den
            if 2 * r >= mag_den:
                q += 1
            res = -q if is_neg else q

            if res > 32767: res = 32767
            elif res < -32768: res = -32768

        self._write_reg(rd, res)

    def _op_pushm(self, i: int):
        # 28: PUSHM / POPM. Bit 6 (R6) se ignora. D=0 PUSHM (R7..R0), D=1 POPM (R0..R7). No modifican NZP
        is_pop = f_bit10(i) == 1
        mask = f_mask8(i)
        if not is_pop:
            # PUSHM: R7 hasta R0
            for r in range(NUM_REGS - 1, -1, -1):
                if r == SP_REG:
                    continue
                if mask & (1 << r):
                    self.regs[SP_REG] = to_uint16(self.regs[SP_REG] - 2)
                    self.mem.write16(self.regs[SP_REG], self.regs[r])
        else:
            # POPM: R0 hasta R7
            for r in range(NUM_REGS):
                if r == SP_REG:
                    continue
                if mask & (1 << r):
                    self.regs[r] = self.mem.read16(self.regs[SP_REG])
                    self.regs[SP_REG] = to_uint16(self.regs[SP_REG] + 2)

    def _op_neg(self, i: int):
        # 29: NEG. DR = -SR1, satura -32768 -> +32767. Actualiza NZP
        s1 = to_int16(self.regs[f_sr1(i)])
        res = 32767 if s1 == -32768 else -s1
        self._write_reg(f_dr(i), res)

    def _op_abs(self, i: int):
        # 30: ABS. DR = |SR1|, satura -32768 -> +32767. Actualiza NZP
        s1 = to_int16(self.regs[f_sr1(i)])
        res = 32767 if s1 == -32768 else abs(s1)
        self._write_reg(f_dr(i), res)

    def _op_ldbu(self, i: int):
        # 31: LDBU. Carga 1 byte sin signo (zero-extend: DR[15:8]=0). Actualiza NZP
        ea = to_uint16(self.regs[f_sr1(i)] + f_off5(i))
        self._write_reg(f_dr(i), self.mem.read8(ea))

    # ==================== Servicios TRAP ====================
    def handle_trap(self, vec: int):
        r0 = self.regs[0]
        if vec == TRAP_HALT:
            self.halted = True
        elif vec == TRAP_OUT:
            self.output_fn(chr(r0 & MASK8))
        elif vec == TRAP_PUTS:                              # 1 char/byte, termina en \0
            addr, chars = r0, []
            while (b := self.mem.read8(addr)) != 0:
                chars.append(chr(b))
                addr = to_uint16(addr + 1)
            self.output_fn("".join(chars))
        elif vec == TRAP_PUTI:
            self.output_fn(str(to_int16(r0)))
        elif vec == TRAP_GETC:
            self.regs[0] = self.input_fn() & MASK8
        elif vec == TRAP_IN:
            self.output_fn("Input a character: ")
            self.regs[0] = self.input_fn() & MASK8
            self.output_fn(chr(self.regs[0]))
        else:
            raise TrapException(f"TRAP x{vec:02X} no implementado")

    # ==================== Tabla de despacho ====================
    def _build_table(self):
        return {
            OP_BR:    self._op_br,
            OP_ADD:   self._op_add,
            OP_LD:    self._op_ld,
            OP_ST:    self._op_st,
            OP_JSR:   self._op_jsr,
            OP_AND:   self._op_and,
            OP_LDR:   self._op_ldr,
            OP_STR:   self._op_str,
            OP_LDB:   self._op_ldb,
            OP_NOT:   self._op_not,
            OP_LDH:   self._op_ldh,
            OP_STH:   self._op_sth,
            OP_JMP:   self._op_jmp,
            OP_STB:   self._op_stb,
            OP_LEA:   self._op_lea,
            OP_TRAP:  self._op_trap,
            OP_SUB:   self._op_sub,
            OP_OR:    self._op_or,
            OP_XOR:   self._op_xor,
            OP_CMP:   self._op_cmp,
            OP_ADDI:  self._op_addi,
            OP_SHL:   self._op_shl,
            OP_ASR:   self._op_asr,
            OP_LSR:   self._op_lsr,
            OP_MULL:  self._op_mull,
            OP_DIV:   self._op_div,
            OP_MULQ:  self._op_mulq,
            OP_DIVQ:  self._op_divq,
            OP_PUSHM: self._op_pushm,
            OP_NEG:   self._op_neg,
            OP_ABS:   self._op_abs,
            OP_LDBU:  self._op_ldbu,
        }
