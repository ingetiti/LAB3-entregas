"""Simulador funcional (núcleo de ejecución) de la ISA LC10.

Recibe una imagen (binario, hexadecimal, decimal o texto binario; nunca assembly),
la ejecuta y devuelve: los resultados (registros, memoria y salida por consola),
la cantidad de instrucciones ejecutadas y el uso de memoria.

Modelo de máquina
  * 8 registros de 16 bits, PC de 16 bits que avanza de a 2 (siempre par)
  * memoria de 64 KiB direccionable por byte, little-endian
  * banderas N, Z, P (resultado), C (acarreo) y V (desborde con signo)
  * una instrucción por paso; no hay modelo de ciclos (es un simulador funcional)
  * sistema operativo mínimo en memoria alta (lc10/os_lc10.asm): TRAP salta a sus rutinas, que se ejecutan
    como cualquier código; sus instrucciones se cuentan aparte (usuario + SO = total)

Excepciones (terminan la ejecución con un mensaje, no se propagan como error de Python):
  PC impar, acceso a palabra en dirección impar, opcode reservado.

Métricas
  instrucciones ejecutadas  cantidad de instrucciones completadas, las del usuario más las del SO
                            (las rutinas de TRAP); `Result.os_instructions` da las del SO por separado
  histograma                cuántas veces se ejecutó cada instrucción
  memoria                   bytes de la imagen cargada, bytes distintos leídos y escritos
                            como datos, y dirección mínima y máxima tocada
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from functools import lru_cache
from dataclasses import dataclass, field
from pathlib import Path

from . import isa, system
from .image import Image, ImageError
from .syntax import parse_input_escapes

M16 = isa.M16
SIGN = 0x8000
SYS_LO, SYS_HI = isa.SYS_LO, isa.SYS_HI
IO_BASE, IO_END = isa.IO_BASE, isa.IO_END

_decode = lru_cache(maxsize=1 << 16)(isa.decode)   # el decodificador es puro: se puede memorizar


class Fault(Exception):
    """Excepción de la máquina (se convierte en el motivo de parada)."""


@dataclass
class Result:
    reason: str                      # 'halt' | 'fault' | 'limit'
    message: str
    instructions: int
    histogram: Counter
    image_bytes: int
    bytes_read: int
    bytes_written: int
    min_addr: int | None
    max_addr: int | None
    output: str
    pc: int
    regs: list
    flags: dict
    fetched_bytes: int = 0
    image_origin: int | None = None
    touched_bytes: int = 0                          # bytes distintos usados (instrucciones + datos leídos + escritos)
    touched_in_image: int = 0                       # de esos, los que están dentro de la imagen cargada
    outside_ranges: list = field(default_factory=list)   # [(desde, hasta)] usados fuera de la imagen (p. ej. la pila)
    os_instructions: int = 0                        # de `instructions`, las que ejecutó el SO (rutinas de TRAP)
    os_histogram: Counter = field(default_factory=Counter)

    @property
    def user_instructions(self) -> int:
        return self.instructions - self.os_instructions

    @property
    def touched_outside(self) -> int:
        return self.touched_bytes - self.touched_in_image

    def memory_line(self) -> str:
        """Uso de memoria en una línea: la imagen y los bytes distintos usados, dentro y fuera de ella."""
        text = f"imagen {self.image_bytes} bytes ({self.image_bytes // 2} palabras"
        if self.image_origin is not None and self.image_bytes:
            text += f", x{self.image_origin:04X}–x{(self.image_origin + self.image_bytes - 1) & M16:04X}"
        text += f"); usados {self.touched_bytes} bytes distintos: {self.touched_in_image} dentro de la imagen"
        text += f" y {self.touched_outside} fuera"
        if self.outside_ranges:
            shown = ", ".join(f"x{a:04X}–x{b:04X}" for a, b in self.outside_ranges[:4])
            text += f" ({shown}{', ...' if len(self.outside_ranges) > 4 else ''})"
        return text

    def summary(self) -> str:
        """Resumen como el de la barra del simulador de la cátedra: instrucciones, palabras y rango."""
        return summary_line(self.instructions, self.image_bytes, self.image_origin, self.os_instructions)

    @property
    def ok(self) -> bool:
        return self.reason == "halt"


@dataclass
class Machine:
    mem: bytearray = field(default_factory=lambda: bytearray(isa.MEM_SIZE))
    regs: list = field(default_factory=lambda: [0] * isa.N_REGS)
    pc: int = 0
    n: int = 0
    z: int = 1
    p: int = 0
    c: int = 0
    v: int = 0
    halted: bool = False
    out: list = field(default_factory=list)
    inp: bytearray = field(default_factory=bytearray)
    count: int = 0                           # instrucciones ejecutadas: usuario + SO
    os_count: int = 0                        # de esas, las que ejecutó el SO (PC dentro de la zona del sistema)
    hist: Counter = field(default_factory=Counter)
    os_hist: Counter = field(default_factory=Counter)
    read_set: set = field(default_factory=set)
    write_set: set = field(default_factory=set)
    fetch_set: set = field(default_factory=set)
    image_bytes: int = 0
    image_origin: int | None = None          # origen de la (primera) imagen cargada
    eof_fault: bool = False                  # True: GETC/IN sin entrada detiene la ejecución (como la cátedra)
    trace: bool = False
    trace_log: list = field(default_factory=list)

    def __post_init__(self) -> None:
        system.install(self.mem)             # el SO y la tabla de vectores, como una ROM

    @property
    def user_count(self) -> int:
        return self.count - self.os_count

    # ------------------------------------------------------------------ carga
    def load(self, image: Image, set_pc: bool = True) -> None:
        if image.data and image.origin < SYS_HI and image.origin + len(image.data) > SYS_LO:
            raise ImageError(f"la imagen (x{image.origin:04X}–x{image.origin + len(image.data) - 1:04X}) invade la zona "
                             f"del sistema (x{SYS_LO:04X}–x{SYS_HI - 1:04X}: tabla de vectores TRAP, rutinas del SO y dispositivos)")
        self.mem[image.origin:image.origin + len(image.data)] = image.data
        if self.image_origin is None:
            self.image_origin = image.origin
        self.image_bytes += len(image.data)
        if set_pc:
            self.pc = image.origin

    def set_input(self, text: str | bytes) -> None:
        """Texto que leen GETC e IN, un byte por carácter (los que no entran en un byte pasan a '?')."""
        self.inp = bytearray(text.encode("latin-1", errors="replace") if isinstance(text, str) else text)

    # ----------------------------------------------------------------- memoria
    def rb(self, addr: int) -> int:
        addr &= M16
        if IO_BASE <= addr < IO_END:
            w = self.dev_read(addr & ~1)
            return w >> 8 if addr & 1 else w & 0xFF
        self.read_set.add(addr)
        return self.mem[addr]

    def wb(self, addr: int, value: int) -> None:
        addr &= M16
        if IO_BASE <= addr < IO_END:
            if not addr & 1:
                self.dev_write(addr, value & 0xFF)
            return
        self.write_set.add(addr)
        self.mem[addr] = value & 0xFF

    def rw(self, addr: int) -> int:
        addr &= M16
        if addr & 1:
            raise Fault(f"acceso a palabra en dirección impar x{addr:04X} (PC=x{(self.pc - 2) & M16:04X})")
        if IO_BASE <= addr < IO_END:
            return self.dev_read(addr)
        self.read_set.update((addr, addr + 1))
        return self.mem[addr] | self.mem[addr + 1] << 8

    def ww(self, addr: int, value: int) -> None:
        addr &= M16
        if addr & 1:
            raise Fault(f"acceso a palabra en dirección impar x{addr:04X} (PC=x{(self.pc - 2) & M16:04X})")
        if IO_BASE <= addr < IO_END:
            self.dev_write(addr, value & M16)
            return
        self.write_set.update((addr, addr + 1))
        self.mem[addr] = value & 0xFF
        self.mem[addr + 1] = value >> 8 & 0xFF

    # ------------------------------------------------------------ dispositivos
    def dev_read(self, addr: int) -> int:
        """Registros de los dispositivos (mapeados en memoria, como en la LC-3)."""
        if addr == isa.IO_KBSR:                  # estado del teclado: bit 15 = hay un carácter
            if not self.inp and self.eof_fault:
                self._rewind()                   # se queda esperando una tecla: la lectura no se completó
                raise Fault("no hay más caracteres disponibles en la entrada")
            return 0x8000                        # sin entrada y sin detener: "listo" para leer el fin (xFFFF)
        if addr == isa.IO_KBDR:                  # dato del teclado; sin más caracteres da xFFFF (-1)
            return self.inp.pop(0) if self.inp else M16
        if addr == isa.IO_DSR:                   # estado de la pantalla: siempre lista
            return 0x8000
        if addr == isa.IO_MCR:                   # control de la máquina: bit 15 = en marcha
            return 0 if self.halted else 0x8000
        return 0                                 # DDR no se lee

    def dev_write(self, addr: int, value: int) -> None:
        if addr == isa.IO_DDR:                   # dato de la pantalla: escribe el byte bajo
            self.out.append(chr(value & 0xFF))
        elif addr == isa.IO_MCR and not value & 0x8000:
            self.halted = True                   # bit 15 en 0: se detiene la máquina

    def _rewind(self) -> None:
        """Deshace la instrucción en curso (queda sin completar, como esperando una tecla)."""
        at = (self.pc - 2) & M16
        name = _decode(self.mem[at] | self.mem[(at + 1) & M16] << 8)[0]
        self.pc = at
        self.count -= 1
        self.hist[name] -= 1
        if SYS_LO <= at < SYS_HI:
            self.os_count -= 1
            self.os_hist[name] -= 1
        if self.trace and self.trace_log:
            self.trace_log.pop()

    # ---------------------------------------------------------------- banderas
    def set_nzp(self, r: int) -> None:
        r &= M16
        self.n = r >> 15
        self.z = int(r == 0)
        self.p = int(not self.n and not self.z)

    def cond(self, code: int) -> bool:
        n, z, c, v = self.n, self.z, self.c, self.v
        return bool([c, not c, v, not v, n != v, n == v, not z and n == v, z or n != v][code])

    # --------------------------------------------------------------- aritmética
    def add_with(self, a: int, b: int, cin: int, store_flags: bool = True) -> int:
        """a + b + cin con acarreo y desborde; actualiza N, Z, P, C, V."""
        full = a + b + cin
        r = full & M16
        if store_flags:
            self.c = full >> 16 & 1
            self.v = int(bool(not (a ^ b) & SIGN and (a ^ r) & SIGN))
            self.set_nzp(r)
        return r

    def jump(self, target: int) -> None:
        target &= M16
        if target & 1:
            raise Fault(f"salto a dirección impar x{target:04X} (PC=x{(self.pc - 2) & M16:04X})")
        self.pc = target

    # ------------------------------------------------------------------ un paso
    def step(self) -> None:
        if self.pc & 1:
            raise Fault(f"PC impar: x{self.pc:04X}")
        at = self.pc
        word = self.mem[at] | self.mem[(at + 1) & M16] << 8
        self.fetch_set.update((at, (at + 1) & M16))
        self.pc = (at + 2) & M16
        try:
            name, f = _decode(word)
        except isa.IsaError as e:
            self.pc = at
            raise Fault(f"{e} (PC=x{at:04X}, palabra x{word:04X})") from None
        self.hist[name] += 1
        self.count += 1
        if SYS_LO <= at < SYS_HI:                  # instrucción de una rutina del SO
            self.os_count += 1
            self.os_hist[name] += 1
        if self.trace:
            self.trace_log.append(f"x{at:04X}  {word:04X}  {isa.disassemble(word, at)}")
        R = self.regs
        _, fmt = isa.BY_NAME[name]

        def operand2() -> int:
            return R[f["src"]] if f["mode"] == "r" else f["src"] & M16

        if name == "BR":
            if (f["n"] and self.n) or (f["z"] and self.z) or (f["p"] and self.p):
                self.jump(self.pc + 2 * f["off"])
        elif name == "BRX":
            if self.cond(f["cond"]):
                self.jump(self.pc + 2 * f["off"])
        elif name in ("ADD", "SUB", "ADC", "SBC", "CMP"):
            a = R[f["sr1"]]
            b = operand2()
            if name == "ADD":
                r = self.add_with(a, b, 0)
            elif name == "ADC":
                r = self.add_with(a, b, self.c)
            elif name in ("SUB", "CMP"):
                r = self.add_with(a, ~b & M16, 1)
            else:  # SBC
                r = self.add_with(a, ~b & M16, self.c)
            if name != "CMP":
                R[f["dr"]] = r
        elif name in ("AND", "OR", "XOR"):
            a, b = R[f["sr1"]], operand2()
            r = a & b if name == "AND" else a | b if name == "OR" else a ^ b
            R[f["dr"]] = r & M16
            self.set_nzp(r)
        elif name == "NOT":
            R[f["dr"]] = ~R[f["sr"]] & M16
            self.set_nzp(R[f["dr"]])
        elif name == "NEG":
            a = R[f["sr"]]
            R[f["dr"]] = self.add_with(0, ~a & M16, 1)
        elif fmt == "MD":
            self.muldiv(name, f)
        elif name == "PUSH":                       # de R7 a R0: el registro más bajo queda en la dirección más baja
            for r in range(7, -1, -1):
                if f["mask"] >> r & 1:
                    sp = (R[isa.SP] - 2) & M16
                    self.ww(sp, R[r])
                    R[isa.SP] = sp
        elif name == "POP":                        # de R0 a R7: deshace un PUSH con la misma máscara
            for r in range(8):
                if f["mask"] >> r & 1:
                    sp = R[isa.SP]
                    R[r] = self.rw(sp)
                    R[isa.SP] = (sp + 2) & M16
        elif name in ("DIVREMU", "DIVREM"):
            self.divrem(name, f)
        elif name in ("SHL", "SHR", "SAR"):
            a = R[f["sr1"]]
            amt = f["src"] if f["mode"] == "i" else R[f["src"]] & 0x1F
            if amt == 0:
                r = a
            elif name == "SHL":
                r = (a << amt) & M16
                self.c = (a >> (16 - amt)) & 1 if amt <= 16 else 0
            elif name == "SHR":
                r = a >> amt if amt < 16 else 0
                self.c = (a >> (amt - 1)) & 1 if amt <= 16 else 0
            else:
                sa = isa.to_s16(a)
                r = (sa >> min(amt, 15)) & M16
                self.c = (a >> (amt - 1)) & 1 if amt <= 16 else a >> 15
            R[f["dr"]] = r
            self.set_nzp(r)
        elif name == "ROTC":
            a = R[f["sr"]]
            if f["right"]:
                r = a >> 1 | self.c << 15
                self.c = a & 1
            else:
                r = (a << 1 | self.c) & M16
                self.c = a >> 15
            R[f["dr"]] = r
            self.set_nzp(r)
        elif name == "LDW":
            R[f["reg"]] = self.rw(R[f["base"]] + 2 * f["off"])
            self.set_nzp(R[f["reg"]])
        elif name == "LDL":
            R[f["reg"]] = isa.sext(self.rb(R[f["base"]] + f["off"]), 8) & M16
            self.set_nzp(R[f["reg"]])
        elif name == "LDH":
            R[f["reg"]] = (R[f["reg"]] & 0x00FF) | self.rb(R[f["base"]] + f["off"]) << 8
            self.set_nzp(R[f["reg"]])
        elif name == "STW":
            self.ww(R[f["base"]] + 2 * f["off"], R[f["reg"]])
        elif name == "STL":
            self.wb(R[f["base"]] + f["off"], R[f["reg"]] & 0xFF)
        elif name == "STH":
            self.wb(R[f["base"]] + f["off"], R[f["reg"]] >> 8)
        elif name == "LD":
            R[f["reg"]] = self.rw(self.pc + 2 * f["off"])
            self.set_nzp(R[f["reg"]])
        elif name == "ST":
            self.ww(self.pc + 2 * f["off"], R[f["reg"]])
        elif name == "LEA":
            R[f["reg"]] = (self.pc + f["off"]) & M16          # offset en bytes
        elif name == "MOVI":
            R[f["dr"]] = f["imm"] & M16
            self.set_nzp(R[f["dr"]])
        elif name == "JSR":
            R[7] = self.pc
            self.jump(self.pc + 2 * f["off"])
        elif name == "JR":
            target = R[f["base"]]
            if f["link"]:
                R[7] = self.pc
            self.jump(target)
        elif name == "TRAP":
            self.trap(f["vect"])
        else:  # pragma: no cover
            raise Fault(f"instrucción sin implementar: {name}")

    def muldiv(self, name: str, f: dict) -> None:
        """MUL, MULH, MULHU, DIV, DIVU, REM, REMU: enteros de 16 bits.

        Todas dejan N, Z, P según el resultado y no tocan C. V (desborde con signo):
          MUL            V = 1 si el producto con signo no entra en 16 bits
          MULH, MULHU    V no cambia
          DIV/DIVU/REM/REMU  V = 1 si el divisor es 0 o si es -32768 / -1 (solo con signo), si no 0
        División por cero: el cociente da todo unos (0xFFFF) y el resto es el dividendo; no hay excepción.
        -32768 / -1 con signo: cociente 0x8000 y resto 0.
        """
        R = self.regs
        a, b = R[f["sr1"]], R[f["sr2"]]
        sa, sb = isa.to_s16(a), isa.to_s16(b)
        if name == "MUL":
            p = sa * sb
            r = p & M16
            self.v = int(isa.to_s16(r) != p)
        elif name == "MULH":
            r = (sa * sb >> 16) & M16
        elif name == "MULHU":
            r = (a * b >> 16) & M16
        else:
            signed = name in ("DIV", "REM")
            x, y = (sa, sb) if signed else (a, b)
            if y == 0:
                q, rem, self.v = M16, x, 1
            elif signed and x == -32768 and y == -1:
                q, rem, self.v = 0x8000, 0, 1
            else:
                q = abs(x) // abs(y)
                q = -q if (x < 0) != (y < 0) else q          # truncado hacia cero
                rem, self.v = x - q * y, 0
            r = q if name in ("DIV", "DIVU") else rem
        R[f["dr"]] = r & M16
        self.set_nzp(r)

    def divrem(self, name: str, f: dict) -> None:
        """DIVREMU / DIVREM DR, SR1, SR2: DR = cociente y SR1 = resto, en una sola instrucción.

        Dan exactamente lo mismo que DIVU (o DIV) DR, SR1, SR2 seguida de REMU (o REM) SR1, SR1, SR2
        (las dos con los valores de antes): mismos casos especiales (división por cero, -32768 / -1).
        Banderas: N, Z, P según el cociente; V como DIV/DIVU; C no cambia.
        """
        R = self.regs
        a, b = R[f["sr1"]], R[f["sr2"]]
        signed = name == "DIVREM"
        x, y = (isa.to_s16(a), isa.to_s16(b)) if signed else (a, b)
        if y == 0:
            q, rem, self.v = M16, x, 1
        elif signed and x == -32768 and y == -1:
            q, rem, self.v = 0x8000, 0, 1
        else:
            q = abs(x) // abs(y)
            q = -q if (x < 0) != (y < 0) else q
            rem, self.v = x - q * y, 0
        R[f["sr1"]] = rem & M16
        R[f["dr"]] = q & M16
        self.set_nzp(q & M16)

    def trap(self, vect: int) -> None:
        """TRAP vv: R7 = PC y PC = palabra de la tabla de vectores (xFB00 + 2·vv); la rutina es código del SO."""
        at = isa.TRAP_TABLE + 2 * vect
        entry = self.mem[at] | self.mem[at + 1] << 8
        if entry == 0:
            raise Fault(f"TRAP x{vect:02X} no implementado")
        self.regs[7] = self.pc
        self.jump(entry)

    # ---------------------------------------------------------------- ejecución
    def run(self, max_instructions: int = 10_000_000, stop_at: int | None = None) -> Result:
        reason, message = "limit", f"se alcanzó el límite de {max_instructions} instrucciones"
        try:
            while self.count < max_instructions:
                if stop_at is not None and self.pc == stop_at:
                    reason, message = "halt", f"se llegó a x{stop_at:04X}"
                    break
                self.step()
                if self.halted:
                    reason, message = "halt", "HALT"
                    break
        except Fault as e:
            reason, message = "fault", str(e)
        return self.result(reason, message)

    def result(self, reason: str, message: str) -> Result:
        def user(addrs):                           # lo que usa el programa: sin la zona del sistema (SO y E/S)
            return {a for a in addrs if not SYS_LO <= a < SYS_HI}
        read_set, write_set, fetch_set = user(self.read_set), user(self.write_set), user(self.fetch_set)
        touched = read_set | write_set
        used = touched | fetch_set
        lo = self.image_origin if self.image_origin is not None else 0
        hi = lo + self.image_bytes
        inside = sum(1 for a in used if lo <= a < hi)
        return Result(
            reason=reason, message=message, instructions=self.count, histogram=Counter(self.hist),
            image_bytes=self.image_bytes, bytes_read=len(read_set), bytes_written=len(write_set),
            min_addr=min(used) if used else None,
            max_addr=max(used) if used else None,
            output="".join(self.out), pc=self.pc, regs=list(self.regs),
            flags={"N": self.n, "Z": self.z, "P": self.p, "C": self.c, "V": self.v},
            fetched_bytes=len(fetch_set), image_origin=self.image_origin,
            touched_bytes=len(used), touched_in_image=inside, outside_ranges=_ranges(a for a in used if not lo <= a < hi),
            os_instructions=self.os_count, os_histogram=Counter(self.os_hist),
        )


def _ranges(addrs) -> list:
    """Direcciones sueltas -> [(desde, hasta)] contiguos, ordenados."""
    out: list = []
    for a in sorted(addrs):
        if out and a == out[-1][1] + 1:
            out[-1] = (out[-1][0], a)
        else:
            out.append((a, a))
    return out


def summary_line(instructions: int, image_bytes: int, origin: int | None, os_instructions: int = 0) -> str:
    """'15.822 usuario + 10.901 SO = 26.723 instrucciones · 4963 palabras · x3000–x4D82'.

    Es el formato de la barra de estado del simulador de la cátedra con el contador actualizado por el grupo 8
    ('357.505 usuario + 22.074 SO = 379.579 instrucciones'). `instructions` es el total (usuario + SO). Palabras =
    bytes de la imagen / 2 (con el relleno de alineación); el rango va del primer al último byte.
    Sin instrucciones del SO (el programa no llamó a ningún TRAP) se muestra solo el total."""
    def n(v: int) -> str:
        return f"{v:,}".replace(",", ".")
    if os_instructions:
        text = f"{n(instructions - os_instructions)} usuario + {n(os_instructions)} SO = {n(instructions)} instrucciones"
    else:
        text = f"{n(instructions)} instrucciones"
    text += f" · {image_bytes // 2} palabras"
    if origin is not None and image_bytes:
        text += f" · x{origin:04X}–x{(origin + image_bytes - 1) & M16:04X}"
    return text


def run_image(image: Image, input_text: str = "", max_instructions: int = 10_000_000, trace: bool = False,
              eof_fault: bool = False):
    m = Machine()
    m.trace = trace
    m.eof_fault = eof_fault
    m.load(image)
    m.set_input(input_text)
    return m, m.run(max_instructions)


def format_result(res: Result, show_regs: bool = True) -> str:
    lines = []
    if res.output:
        lines.append("--- salida ---")
        lines.append(res.output.rstrip("\n"))
        lines.append("--------------")
    status = {"halt": "terminó (HALT)", "fault": "EXCEPCIÓN", "limit": "límite alcanzado"}[res.reason]
    lines.append(f"Estado: {status}" + ("" if res.reason == "halt" else f": {res.message}"))
    lines.append(f"LC10 · {res.summary()}")
    lines.append(f"Instrucciones ejecutadas: {res.instructions} (usuario {res.user_instructions} + SO {res.os_instructions})")
    lines.append(f"Memoria: {res.memory_line()}")
    lines.append(f"  detalle: instrucciones leídas de {res.fetched_bytes} bytes; datos leídos {res.bytes_read} bytes "
                 f"y escritos {res.bytes_written} bytes distintos")
    if show_regs:
        lines.append("Registros: " + "  ".join(f"R{i}=x{v:04X}({isa.to_s16(v)})" for i, v in enumerate(res.regs)))
        lines.append("Banderas: " + " ".join(f"{k}={v}" for k, v in res.flags.items()) + f"   PC=x{res.pc:04X}")
    hist = ", ".join(f"{k}:{v}" for k, v in sorted(res.histogram.items(), key=lambda kv: -kv[1]))
    lines.append(f"Instrucciones por tipo: {hist}")
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="lc10.simulator", description="Simulador funcional de la ISA LC10")
    ap.add_argument("image", help="archivo del programa ensamblado (.bin, .hex, .dec o .bits)")
    ap.add_argument("--format", choices=("bin", "hex", "dec", "bits"), help="formato del archivo (por defecto, la extensión)")
    ap.add_argument("--input", default="", help="texto que leen GETC e IN (admite \\n, \\t y \\\\)")
    ap.add_argument("--input-file", metavar="ARCHIVO", help="archivo de texto (UTF-8) que leen GETC e IN, tal cual")
    ap.add_argument("--fin-entrada", choices=("detener", "menos1"), default="detener",
                    help="qué hace GETC/IN cuando se acaba la entrada: detener la ejecución con un aviso, como el "
                         "simulador de la cátedra (por defecto), o devolver xFFFF (-1)")
    ap.add_argument("--max", type=int, default=10_000_000, help="máximo de instrucciones")
    ap.add_argument("--dump", action="append", default=[], metavar="DIR:BYTES",
                    help="muestra memoria al terminar, por ejemplo --dump 0x3100:16 (se puede repetir)")
    ap.add_argument("--trace", action="store_true", help="muestra cada instrucción ejecutada")
    ap.add_argument("--no-regs", action="store_true")
    args = ap.parse_args(argv)
    try:
        image = Image.load(args.image, args.format)
    except (ImageError, OSError, UnicodeDecodeError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    if args.input_file:
        try:
            text = Path(args.input_file).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            print(f"error: {e}", file=sys.stderr)
            return 1
    else:
        text = parse_input_escapes(args.input)
    try:
        m, res = run_image(image, text, args.max, args.trace, eof_fault=args.fin_entrada == "detener")
    except ImageError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    if args.trace:
        print("\n".join(m.trace_log))
    print(format_result(res, not args.no_regs))
    for spec in args.dump:
        addr_s, _, n_s = spec.partition(":")
        addr, n = int(addr_s, 0), int(n_s or "16", 0)
        rows = []
        for i in range(0, n, 16):
            chunk = m.mem[(addr + i) & M16:(addr + i + min(16, n - i)) & M16 or None]
            rows.append(f"x{(addr + i) & M16:04X}: " + " ".join(f"{b:02X}" for b in chunk))
        print("\n".join(rows))
    return {"halt": 0, "fault": 2}.get(res.reason, 3)       # 3 = límite de instrucciones


if __name__ == "__main__":
    sys.exit(main())
