"""
sim.py - Simulador funcional (línea de comandos) de 16 bits
=============================================================================
Capa que conecta archivos <-> núcleo. No acepta assembly directo: solo .hex o .bin.

Formato de entrada (ambos representan la misma secuencia de bytes):
  .bin : bytes crudos. Bytes 0-1 = dirección de origen .ORIG (Little-Endian).
  .hex : texto, un byte por token de 2 dígitos hex (espacios/saltos de línea
         libres, ';' o '#' inician comentario). Primeros 2 bytes = .ORIG (Little-Endian).

Uso: python sim.py programa.hex [--max-steps N] [--trace] [--dump-regs] [--contar-os]
"""

import argparse
import re
import sys
from typing import Dict, Tuple

from core import CPU, CPUException
from isa import NUM_REGS, disassemble, get_cc_name, to_int16

_HEX_SYM_RE = re.compile(r"^\s*;\s*@SYM\s+x([0-9A-Fa-f]{1,4})\s+(\S+)")


def load_hex_symbols(path: str) -> Dict[str, int]:
    """Lee las etiquetas incrustadas (`; @SYM xADDR ETIQUETA`) de un archivo .hex, si existen."""
    if not path.lower().endswith(".hex"):
        return {}
    syms: Dict[str, int] = {}
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            m = _HEX_SYM_RE.match(line)
            if m:
                addr = int(m.group(1), 16) & 0xFFFF
                name = m.group(2)
                syms[name] = addr
                if "-" in name:
                    short = name.split("-", 1)[1]
                    syms.setdefault(short, addr)
    return syms


def load_image(path: str) -> Tuple[int, bytes]:
    """Lee un .hex/.bin y devuelve (origen, bytes_del_programa)."""
    if path.lower().endswith(".hex"):
        with open(path, "r", encoding="utf-8") as f:
            text = re.sub(r"[;#].*", "", f.read())
        tokens = text.split()
        try:
            raw = bytes(int(t, 16) for t in tokens)
        except ValueError as e:
            raise ValueError(f"{path}: token hexadecimal inválido ({e})")
    else:
        with open(path, "rb") as f:
            raw = f.read()
    if len(raw) < 2:
        raise ValueError(f"{path}: archivo vacío o sin dirección de origen")
    origin = raw[0] | (raw[1] << 8)
    return origin, raw[2:]


def dump_regs(cpu: CPU):
    for i in range(0, NUM_REGS, 2):
        print("  " + "    ".join(
            f"R{j}: x{cpu.regs[j]:04X} ({to_int16(cpu.regs[j]):>6})" for j in (i, i + 1)))
    print(f"  PC: x{cpu.pc:04X}   CC: [{get_cc_name(cpu.cond)}]")


def trace_step(cpu: CPU):
    at = cpu.pc
    instr = cpu.mem.peek16(at)
    before = list(cpu.regs)
    cpu.step()
    changes = ", ".join(f"R{i}=x{cpu.regs[i]:04X}" for i in range(NUM_REGS) if cpu.regs[i] != before[i])
    print(f"\n[x{at:04X}] x{instr:04X}  {disassemble(instr, at, cpu.symbols):<24} {changes}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Simulador funcional de la ISA Skynet (16 bits)")
    ap.add_argument("program", help="archivo .hex o .bin")
    ap.add_argument("--max-steps", type=int, default=None, help="límite de instrucciones")
    ap.add_argument("--trace", action="store_true", help="traza de cada instrucción")
    ap.add_argument("--dump-regs", action="store_true", help="registros al terminar")
    ap.add_argument("--contar-os", action="store_true", default=False,
                    help="ejecuta y contabiliza las rutinas de OS adaptadas para TRAP (por defecto desactivado)")
    args = ap.parse_args(argv)

    try:
        origin, blob = load_image(args.program)
    except (OSError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    cpu = CPU(input_fn=lambda: ord(sys.stdin.read(1) or "\0"), contar_os=args.contar_os)
    if args.contar_os:
        cpu.symbols.update(cpu._os_symbols)
    cpu.load_program(origin, blob)

    status = 0
    try:
        while not cpu.halted:
            if args.max_steps is not None and cpu.instr_count >= args.max_steps:
                print(f"\n[Aviso] límite de {args.max_steps} instrucciones alcanzado.")
                break
            trace_step(cpu) if args.trace else cpu.step()
    except CPUException as e:
        print(f"\n{e}", file=sys.stderr)
        status = 2

    print("\n--- Resultados ---")
    st = cpu.stats()
    for k, v in st.items():
        if not args.contar_os and k in ("instrucciones_usuario", "instrucciones_os"):
            continue
        print(f"  {k}: {v}")
    if args.dump_regs:
        dump_regs(cpu)
    return status


if __name__ == "__main__":
    sys.exit(main())
