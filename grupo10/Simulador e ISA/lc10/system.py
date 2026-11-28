"""El sistema operativo mínimo de LC10: ensambla `os_lc10.asm` y arma la tabla de vectores TRAP.

`Machine` lo instala al crearse (como la ROM de la LC-3): el código del SO queda en xFD40, la tabla de
vectores en xFB00 y los registros de los dispositivos en xFE00. Todo lo que está en [SYS_LO, SYS_HI)
es del sistema: sus instrucciones se cuentan como "SO" y no entra en las métricas de memoria del usuario.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from . import isa
from .assembler import assemble

OS_SOURCE = Path(__file__).with_name("os_lc10.asm")

# vector TRAP -> etiqueta de la rutina en os_lc10.asm
VECTOR_LABELS = {
    isa.TRAP_GETC: "S_GETC",
    isa.TRAP_OUT: "S_OUT",
    isa.TRAP_PUTS: "S_PUTS",
    isa.TRAP_IN: "S_IN",
    isa.TRAP_HALT: "S_HALT",
}


@lru_cache(maxsize=1)
def build() -> tuple[int, bytes, dict]:
    """(origen, bytes del SO, {vector: dirección de la rutina}). Se ensambla una sola vez."""
    res = assemble([(OS_SOURCE.name, OS_SOURCE.read_text(encoding="utf-8"))], system_area=True)
    mod = OS_SOURCE.stem.upper()
    vectors = {v: res.symbols[f"{mod}-{lab}"] for v, lab in VECTOR_LABELS.items()}
    return res.image.origin, res.image.data, vectors


def symbols() -> dict:
    """Etiquetas del SO -> dirección (para mostrarlas en el listado y en los tests)."""
    res = assemble([(OS_SOURCE.name, OS_SOURCE.read_text(encoding="utf-8"))], system_area=True)
    return {k.split("-", 1)[1]: v for k, v in res.symbols.items()}


def install(mem: bytearray) -> None:
    """Copia el SO y la tabla de vectores a una memoria nueva."""
    origin, data, vectors = build()
    mem[origin:origin + len(data)] = data
    for vect, addr in vectors.items():
        at = isa.TRAP_TABLE + 2 * vect
        mem[at] = addr & 0xFF
        mem[at + 1] = addr >> 8


def in_system(addr: int) -> bool:
    return isa.SYS_LO <= addr < isa.SYS_HI
