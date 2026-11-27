"""
debugger.py - Depurador interactivo para la ISA Skynet (16 bits)
=============================================================================
Controla ejecución paso a paso (step), puntos de interrupción (breakpoints),
inspección de registros, banderas, desensamblado en tiempo real y memoria.
"""

from bisect import bisect_right
from typing import Callable, Dict, List, Optional, Set, Tuple

from core import CPU, CPUException
from isa import (
    INSTR_SIZE, MASK16, MMIO_DDR, MMIO_DSR, MMIO_KBDR, MMIO_KBSR, MMIO_MCR,
    NUM_REGS, OS_CODE_ORIG, OS_TVT_BASE, SP_REG, TRAP_NAMES,
    disassemble, get_cc_name, to_int16,
)

_MMIO_LABELS = {
    MMIO_KBSR: "MMIO: KBSR",
    MMIO_KBDR: "MMIO: KBDR",
    MMIO_DSR:  "MMIO: DSR",
    MMIO_DDR:  "MMIO: DDR",
    MMIO_MCR:  "MMIO: MCR",
}


class Debugger:
    def __init__(self,
                 cpu: Optional[CPU] = None,
                 output_fn: Optional[Callable[[str], None]] = None,
                 input_fn: Optional[Callable[[], int]] = None,
                 contar_os: bool = False):
        self.output_buffer: List[str] = []
        self.output_fn = output_fn or self.output_buffer.append
        self.input_fn = input_fn or (lambda: 0)
        self.cpu = cpu or CPU(output_fn=self.output_fn, input_fn=self.input_fn, contar_os=contar_os)
        self.breakpoints: Set[int] = set()
        self.symbols: Dict[int, str] = {}           # {dir: etiqueta corta} para desensamblado
        self.addr_labels: Dict[int, str] = {}       # {dir: MODULO-ETIQUETA} para identificar grupo/función
        self.symbol_map: Dict[str, int] = {}        # {NOMBRE_UPPER: dir} para búsqueda directa
        self._sorted_user_addrs: List[int] = []
        self._sorted_os_addrs: List[int] = []
        self.origin: int = 0x3000
        self.blob: bytes = b""

    def _sync_symbols(self):
        merged: Dict[int, str] = {}
        if self.cpu.contar_os:
            merged.update(self.cpu._os_symbols)
            self._sorted_os_addrs = sorted(self.cpu._os_symbols.keys())
        else:
            self._sorted_os_addrs = []
        merged.update(self.symbols)
        self.cpu.symbols = merged
        self._sorted_user_addrs = sorted(self.addr_labels.keys())

    def set_contar_os(self, enabled: bool):
        """Activa o desactiva el conteo/ejecución de rutinas OS y reinicia la CPU."""
        self.cpu.set_contar_os(enabled)
        self.reset()

    def load_program(self, origin: int, blob: bytes, symbols: Optional[Dict[str, int]] = None):
        self.origin = origin & MASK16
        self.blob = blob
        self.cpu.reset(self.origin, clear_memory=True)
        self.output_buffer.clear()
        self.symbols.clear()
        self.addr_labels.clear()
        self.symbol_map.clear()
        if symbols:
            for name, addr in symbols.items():
                a = addr & MASK16
                key = name.upper()
                self.symbol_map[key] = a
                if "-" in name:
                    # Prefiere etiqueta calificada MODULO-FUNCION para identificar grupo/función
                    self.addr_labels.setdefault(a, name)
                else:
                    self.symbols[a] = name
            # Rellenar direcciones que solo tenían etiqueta sin guion o solo con guion
            for name, addr in symbols.items():
                a = addr & MASK16
                self.symbols.setdefault(a, name)
                self.addr_labels.setdefault(a, name)
        self._sync_symbols()
        self.cpu.load_program(self.origin, self.blob)

    def get_exact_label(self, addr: int) -> str:
        """Devuelve la etiqueta exacta en `addr`, o cadena vacía si no inicia etiqueta allí."""
        addr &= MASK16
        if addr in self.addr_labels:
            return self.addr_labels[addr]
        if self.cpu.contar_os and addr in self.cpu._os_symbols:
            return self.cpu._os_symbols[addr]
        return ""

    def get_addr_label(self, addr: int) -> str:
        """Devuelve la etiqueta exacta o la subrutina/sección propietaria de `addr`
        (ej. 'G18_BOOTH-MULT_BOOTH' en el inicio y '↳ G18_BOOTH-MULT_BOOTH +4' en su cuerpo)."""
        addr &= MASK16
        exact = self.get_exact_label(addr)
        if exact:
            return exact

        # Si está dentro del programa de usuario cargado, mostrar subrutina propietaria + offset
        if self.blob and self._sorted_user_addrs and (self.origin <= addr < self.origin + len(self.blob)):
            idx = bisect_right(self._sorted_user_addrs, addr) - 1
            if idx >= 0:
                base = self._sorted_user_addrs[idx]
                return f"↳ {self.addr_labels[base]} +{addr - base}"

        # Zonas del OS y MMIO cuando contar_os=True
        if self.cpu.contar_os:
            if OS_CODE_ORIG <= addr < self.cpu._os_code_end and self._sorted_os_addrs:
                idx = bisect_right(self._sorted_os_addrs, addr) - 1
                if idx >= 0:
                    base = self._sorted_os_addrs[idx]
                    return f"↳ {self.cpu._os_symbols[base]} +{addr - base}"
            if addr in _MMIO_LABELS:
                return _MMIO_LABELS[addr]
            if OS_TVT_BASE <= addr < 0x0100 and (addr & 1) == 0:
                vec = (addr - OS_TVT_BASE) // INSTR_SIZE
                if vec in TRAP_NAMES:
                    return f"TVT: {TRAP_NAMES[vec]} (x{vec:02X})"

        return ""

    def get_symbol_entries(self) -> List[Tuple[int, str]]:
        """Lista ordenada por dirección de [(dir, etiqueta_calificada)] incluyendo OS si aplica."""
        combined: Dict[int, str] = {}
        if self.cpu.contar_os:
            combined.update(self.cpu._os_symbols)
        combined.update(self.addr_labels)
        return sorted(combined.items(), key=lambda x: x[0])

    def resolve_target(self, query: str) -> Optional[int]:
        """Resuelve una dirección hex (x3004, 0x3004, 3004), entrada 'xADDR | LABEL'
        o nombre/subcadena de función o grupo (ej. 'G18_BOOTH', 'MULT_BOOTH', 'TAYLOR')."""
        q = query.strip()
        if not q:
            return None
        # Formato del selector: "x311A | G1_CORDIC_DIVISION-CORDIC_DIV"
        if "|" in q:
            q = q.split("|", 1)[0].strip()

        # 1. Intento como dirección hexadecimal (x3004, 0x3004 o hex puro de 1..4 dígitos)
        raw = q.lower()
        hex_part = None
        if raw.startswith("0x"):
            hex_part = raw[2:]
        elif raw.startswith("x") and len(raw) > 1:
            hex_part = raw[1:]
        elif all(c in "0123456789abcdef" for c in raw) and 1 <= len(raw) <= 4:
            # Solo tratar como hex puro si no existe como nombre exacto de símbolo
            if q.upper() not in self.symbol_map:
                hex_part = raw
        if hex_part is not None and hex_part and all(c in "0123456789abcdef" for c in hex_part):
            val = int(hex_part, 16)
            if 0 <= val <= MASK16:
                return val & ~1

        # 2. Búsqueda exacta por símbolo (usuario y OS)
        q_up = q.upper()
        if q_up in self.symbol_map:
            return self.symbol_map[q_up] & ~1
        if self.cpu.contar_os:
            for a, name in self.cpu._os_symbols.items():
                if name.upper() == q_up:
                    return a & ~1

        # 3. Búsqueda por coincidencia parcial (priorizando coincidencias de módulo/función)
        entries = self.get_symbol_entries()
        for a, name in entries:
            if q_up in name.upper():
                return a & ~1
        for name, a in self.symbol_map.items():
            if q_up in name:
                return a & ~1
        return None

    def reset(self):
        self.cpu.reset(self.origin, clear_memory=True)
        self._sync_symbols()
        if self.blob:
            self.cpu.load_program(self.origin, self.blob)
        self.output_buffer.clear()

    def toggle_breakpoint(self, addr: int) -> bool:
        addr &= MASK16
        if addr in self.breakpoints:
            self.breakpoints.remove(addr)
            return False
        else:
            self.breakpoints.add(addr)
            return True

    def step(self) -> Tuple[bool, str]:
        """Ejecuta una instrucción. Devuelve (sigue_activo, mensaje_de_cambios)."""
        if self.cpu.halted:
            return False, "CPU detenida (HALT)"
        at = self.cpu.pc
        instr = self.cpu.mem.peek16(at)
        dis = disassemble(instr, at, self.cpu.symbols)
        regs_before = list(self.cpu.regs)
        try:
            active = self.cpu.step()
        except CPUException as e:
            return False, f"Excepción en x{at:04X}: {e}"

        changes = []
        for r in range(NUM_REGS):
            if self.cpu.regs[r] != regs_before[r]:
                changes.append(f"R{r}: x{regs_before[r]:04X}->x{self.cpu.regs[r]:04X} ({to_int16(self.cpu.regs[r])})")
        change_str = ", ".join(changes) if changes else "sin cambios en registros"
        return active, f"[x{at:04X}] x{instr:04X}  {dis:<24} ({change_str})"

    def run_until_break(self, max_steps: int = 50000) -> Tuple[bool, str]:
        steps = 0
        while not self.cpu.halted and steps < max_steps:
            if self.cpu.pc in self.breakpoints and steps > 0:
                return True, f"Breakpoint alcanzado en x{self.cpu.pc:04X}"
            active, msg = self.step()
            steps += 1
            if not active:
                return False, msg
            if self.cpu.pc in self.breakpoints:
                return True, f"Breakpoint alcanzado en x{self.cpu.pc:04X}"
        if self.cpu.halted:
            return False, "Programa finalizado (HALT)"
        return True, f"Límite de {max_steps} pasos alcanzado"

    def get_instructions_window(self, center_pc: Optional[int] = None, count: int = 15) -> List[Tuple[int, int, str, bool, bool]]:
        """Devuelve [(dirección, código_máquina, desensamblado, es_pc_actual, tiene_breakpoint), ...]."""
        center = self.cpu.pc if center_pc is None else center_pc
        start = max(0, (center - (count // 2) * INSTR_SIZE) & ~1)
        res = []
        curr = start
        for _ in range(count):
            if curr >= self.cpu.mem.size - 1:
                break
            code = self.cpu.mem.peek16(curr)
            dis = disassemble(code, curr, self.cpu.symbols)
            is_pc = (curr == self.cpu.pc)
            is_bp = (curr in self.breakpoints)
            res.append((curr, code, dis, is_pc, is_bp))
            curr = (curr + INSTR_SIZE) & MASK16
        return res

    def get_memory_slice(self, start_addr: int, count: int) -> List[Tuple[int, str, int, str, bool, bool]]:
        """Devuelve [(dir, etiqueta, código, desensamblado, es_pc, tiene_bp), ...]
        desde `start_addr` alineado a par sin envolver más allá de xFFFE."""
        curr = max(0, min(self.cpu.mem.size - INSTR_SIZE, start_addr & ~1))
        res = []
        for _ in range(count):
            if curr > self.cpu.mem.size - INSTR_SIZE:
                break
            code = self.cpu.mem.peek16(curr)
            label = self.get_addr_label(curr)
            dis = disassemble(code, curr, self.cpu.symbols)
            is_pc = (curr == self.cpu.pc)
            is_bp = (curr in self.breakpoints)
            res.append((curr, label, code, dis, is_pc, is_bp))
            curr += INSTR_SIZE
        return res
