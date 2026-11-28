"""Lógica de la interfaz gráfica del LC10, sin tkinter.

`Session` junta el ensamblador y el simulador para que una ventana (o una prueba)
pueda: ensamblar varios archivos, cargar una imagen ya ensamblada, ejecutar paso a
paso o por tandas con puntos de parada, y consultar qué cambió en cada paso.
No hay ninguna lógica de ISA acá: todo lo hacen `assembler.py` y `simulator.py`.

Estados (`Session.state`)
  empty    todavía no hay ningún programa cargado
  ready    programa cargado; se puede avanzar (todavía no terminó)
  halted   terminó con HALT
  fault    terminó con una excepción (`message` dice cuál)
"""
from __future__ import annotations

import time
from dataclasses import dataclass

from . import isa
from .assembler import Result as AsmResult
from .assembler import assemble
from .image import Image
from .simulator import Fault, Machine, summary_line
from .system import in_system

SYS_LO, SYS_HI = isa.SYS_LO, isa.SYS_HI

M16 = isa.M16
FLAG_NAMES = ("N", "Z", "P", "C", "V")


@dataclass
class Snapshot:
    """Estado de la máquina en un instante, para saber después qué cambió."""
    regs: list
    flags: tuple
    pc: int
    mem: bytes
    count: int


@dataclass
class Change:
    regs: set          # índices de registros que cambiaron
    flags: set         # letras de banderas que cambiaron
    pc_from: int       # PC antes del paso
    count: int         # instrucciones ejecutadas desde el snapshot


class Session:
    def __init__(self) -> None:
        self.asm: AsmResult | None = None
        self.image: Image | None = None
        self.machine: Machine | None = None
        self.state = "empty"
        self.message = ""
        self.input_text = ""
        self.trace_enabled = False
        self.trace_keep = 5000                 # líneas de traza que se conservan
        self.listing_lines: list[str] = []
        self.listing_addrs: list[int] = []
        self._listing_index: dict[int, int] = {}
        self._by_addr: dict[int, tuple[str, int]] = {}
        self._by_line: dict[tuple[str, int], int] = {}
        self._out_cursor = 0
        self.last_pc: int | None = None        # dirección de la última instrucción ejecutada

    # ------------------------------------------------------------------ cargar
    def assemble(self, sources: list[tuple[str, str]], input_text: str = "") -> AsmResult:
        """Ensambla y deja el programa listo para ejecutar. Si hay error de ensamblado
        (`AsmError`), se propaga y la sesión no cambia."""
        res = assemble(sources)
        self.asm = res
        self.image = res.image
        self._by_addr, self._by_line = {}, {}
        for addr, _size, file, line, kind in res.srcmap:
            if kind == "instr":
                self._by_addr[addr] = (file, line)
                self._by_line.setdefault((file, line), addr)
        self._build_listing_from_asm(res)
        self.start(input_text)
        return res

    def load_image(self, image: Image, input_text: str = "") -> None:
        """Carga una imagen ya ensamblada (como la que recibe el simulador de línea de comandos)."""
        self.asm = None
        self.image = image
        self._by_addr, self._by_line = {}, {}
        self._build_listing_from_image(image)
        self.start(input_text)

    def start(self, input_text: str | None = None) -> None:
        """Máquina nueva con la imagen cargada (reinicio completo: registros, memoria, contadores)."""
        if self.image is None:
            return
        if input_text is not None:
            self.input_text = input_text
        m = Machine()
        m.trace = self.trace_enabled
        m.load(self.image)
        m.set_input(self.input_text)
        self.machine = m
        self.state, self.message = "ready", ""
        self._out_cursor = 0
        self.last_pc = None

    # ---------------------------------------------------------------- listado
    def _build_listing_from_asm(self, res: AsmResult) -> None:
        lines, addrs = [], []
        for addr, b, text, kind in res.listing:
            if kind in ("instr", "word"):
                lines.append(f"x{addr:04X}  {b[0] | b[1] << 8:04X}  {text}")
            else:
                shown = " ".join(f"{x:02X}" for x in b[:6]) + (" ..." if len(b) > 6 else "")
                lines.append(f"x{addr:04X}  [{shown}]  {text}")
            addrs.append(addr)
        self._set_listing(lines, addrs)

    def _build_listing_from_image(self, image: Image) -> None:
        lines, addrs = [], []
        for i in range(0, len(image.data), 2):
            addr = (image.origin + i) & M16
            word = image.data[i] | image.data[i + 1] << 8
            lines.append(f"x{addr:04X}  {word:04X}  {isa.disassemble(word, addr)}")
            addrs.append(addr)
        self._set_listing(lines, addrs)

    def _set_listing(self, lines: list[str], addrs: list[int]) -> None:
        self.listing_lines, self.listing_addrs = lines, addrs
        self._listing_index = {}
        for i, a in enumerate(addrs):
            self._listing_index.setdefault(a, i)

    def listing_line_for(self, addr: int) -> int | None:
        """Índice (desde 0) de la línea del listado que empieza en `addr`."""
        return self._listing_index.get(addr)

    # -------------------------------------------------- relación fuente <-> dirección
    def location_of(self, addr: int) -> tuple[str, int] | None:
        """(archivo, línea) de la instrucción que está en `addr`, si hay fuente."""
        return self._by_addr.get(addr)

    def pc_location(self) -> tuple[str, int] | None:
        return self._by_addr.get(self.machine.pc) if self.machine else None

    def addr_of_line(self, file: str, line: int) -> int | None:
        """Dirección de la instrucción de esa línea (None si la línea no tiene código)."""
        return self._by_line.get((file, line))

    def breakpoint_addrs(self, lines: set[tuple[str, int]]) -> set[int]:
        return {a for fl in lines if (a := self._by_line.get(fl)) is not None}

    # ------------------------------------------------------------------ cambios
    def snapshot(self) -> Snapshot:
        m = self.machine
        return Snapshot(list(m.regs), (m.n, m.z, m.p, m.c, m.v), m.pc, bytes(m.mem), m.count)

    def diff(self, snap: Snapshot) -> Change:
        m = self.machine
        flags = (m.n, m.z, m.p, m.c, m.v)
        return Change(
            regs={i for i, (a, b) in enumerate(zip(snap.regs, m.regs)) if a != b},
            flags={FLAG_NAMES[i] for i in range(5) if snap.flags[i] != flags[i]},
            pc_from=snap.pc,
            count=m.count - snap.count,
        )

    def changed_bytes(self, snap: Snapshot, lo: int, hi: int) -> set[int]:
        """Direcciones de [lo, hi) cuyo contenido es distinto del snapshot."""
        mem = self.machine.mem
        return {a for a in range(max(lo, 0), min(hi, isa.MEM_SIZE)) if snap.mem[a] != mem[a]}

    # --------------------------------------------------------------- ejecución
    def _finish_if_needed(self) -> None:
        if self.machine.halted:
            self.state, self.message = "halted", "HALT"

    # tope de instrucciones del SO que un paso recorre de una vez (un PUTS de toda la memoria ronda las 400.000)
    OS_STEP_LIMIT = 2_000_000

    def step(self) -> str:
        """Ejecuta una instrucción del usuario. Devuelve el estado.

        Un TRAP cuenta como un solo paso: la rutina del SO que llama se ejecuta entera (el contador sí suma
        sus instrucciones). Si la máquina quedó dentro del SO (una corrida que se cortó por tiempo), el paso
        termina la rutina en curso."""
        if self.state != "ready":
            return self.state
        m = self.machine
        if not in_system(m.pc):
            self.last_pc = m.pc
        try:
            m.step()
            budget = self.OS_STEP_LIMIT
            while in_system(m.pc) and not m.halted and budget:
                m.step()
                budget -= 1
        except Fault as e:
            self.state, self.message = "fault", str(e)
        else:
            self._finish_if_needed()
        self._trim_trace()
        return self.state

    def run_chunk(self, breakpoints=(), budget_s: float = 0.03, limit: int | None = None,
                  max_steps: int | None = None, check_first: bool = False) -> str:
        """Ejecuta durante `budget_s` segundos como máximo.

        Devuelve 'running' (se acabó el tiempo y se puede seguir llamando), 'breakpoint',
        'halted', 'fault' o 'limit'. La primera instrucción siempre se ejecuta, así que se puede
        continuar desde un punto de parada.

        `limit` es un contador de instrucciones (`machine.count`) que no se debe pasar: cuando se
        llega a él se devuelve 'limit' sin ejecutar nada más (la sesión sigue 'ready'). Sirve para
        que un bucle infinito no corra sin fin; quien llama decide el valor (p. ej. count + N).

        `max_steps` limita cuántas instrucciones se ejecutan en esta llamada (devuelve 'running' al
        llegar a ese número); sirve para correr a una velocidad máxima de instrucciones por segundo.

        Con `check_first=True` también se mira si la primera instrucción está en un punto de parada.
        Hay que pasarlo al seguir una ejecución que se cortó por tiempo o por `max_steps` (si no, un
        punto de parada justo en el corte se saltearía); al arrancar de nuevo desde un punto de
        parada se deja en False.
        """
        if self.state != "ready":
            return self.state
        m = self.machine
        bps = breakpoints if isinstance(breakpoints, (set, frozenset)) else set(breakpoints)
        deadline = time.perf_counter() + budget_s
        result = "running"
        first = not check_first
        steps = 0
        last = self.last_pc if in_system(m.pc) and self.last_pc is not None else m.pc
        try:
            while True:
                for _ in range(256):
                    if limit is not None and m.count >= limit:
                        result = "limit"
                        break
                    if not first and bps and m.pc in bps:
                        result = "breakpoint"
                        break
                    if max_steps is not None and steps >= max_steps:
                        break
                    first = False
                    if not SYS_LO <= m.pc < SYS_HI:          # last_pc es siempre una instrucción del usuario
                        last = m.pc
                    m.step()
                    steps += 1
                    if m.halted:
                        self._finish_if_needed()
                        result = "halted"
                        break
                if (result != "running" or (max_steps is not None and steps >= max_steps)
                        or time.perf_counter() >= deadline):
                    break
        except Fault as e:
            self.state, self.message = "fault", str(e)
            result = "fault"
        self.last_pc = last
        self._trim_trace()
        return result

    def _trim_trace(self) -> None:
        log = self.machine.trace_log
        if len(log) > 2 * self.trace_keep:
            del log[:-self.trace_keep]

    def set_trace(self, enabled: bool) -> None:
        self.trace_enabled = enabled
        if self.machine:
            self.machine.trace = enabled

    def trace_text(self) -> str:
        if not self.machine:
            return ""
        return "\n".join(self.machine.trace_log[-self.trace_keep:])

    # ------------------------------------------------------------- salida / datos
    def take_output(self) -> str:
        """Texto que la máquina escribió desde la última llamada."""
        if not self.machine:
            return ""
        out = self.machine.out
        text = "".join(out[self._out_cursor:])
        self._out_cursor = len(out)
        return text

    def read_memory(self, addr: int, n: int) -> bytes:
        addr &= M16
        return bytes(self.machine.mem[addr:addr + n]) if self.machine else b""

    def summary(self) -> str:
        """'N instrucciones · M palabras · xA–xB', como la barra del simulador de la cátedra."""
        m = self.machine
        if not m:
            return ""
        return summary_line(m.count, m.image_bytes, m.image_origin, m.os_count)

    def metrics_text(self) -> str:
        """Resumen de métricas del simulador hasta el momento."""
        if not self.machine:
            return "Todavía no hay un programa cargado."
        reason = "halt" if self.state == "halted" else "fault" if self.state == "fault" else "limit"
        res = self.machine.result(reason, self.message)
        status = {"empty": "sin programa", "ready": "en curso o detenido (no terminó)",
                  "halted": "terminó con HALT", "fault": f"EXCEPCIÓN: {self.message}"}[self.state]
        lines = [f"Estado: {status}",
                 f"LC10 · {res.summary()}",
                 f"Instrucciones ejecutadas: {res.instructions} (usuario {res.user_instructions} + SO {res.os_instructions})",
                 "",
                 "Memoria",
                 f"  {res.memory_line()}",
                 f"  bytes de la imagen cargada:      {res.image_bytes}",
                 f"  bytes de instrucciones leídos:   {res.fetched_bytes} (distintos)",
                 f"  bytes de datos leídos:           {res.bytes_read} (distintos)",
                 f"  bytes de datos escritos:         {res.bytes_written} (distintos)"]
        if res.min_addr is not None:
            lines.append(f"  direcciones tocadas (extremos):  x{res.min_addr:04X} .. x{res.max_addr:04X}")
        lines += ["", "Instrucciones por tipo"]
        total = max(res.instructions, 1)
        for name, n in sorted(res.histogram.items(), key=lambda kv: (-kv[1], kv[0])):
            lines.append(f"  {name:<6} {n:>10}  {100 * n / total:5.1f} %")
        return "\n".join(lines)

    def symbols_text(self) -> str:
        from .assembler import format_map
        return format_map(self.asm) if self.asm else "(sin símbolos: el programa se cargó desde una imagen)"
