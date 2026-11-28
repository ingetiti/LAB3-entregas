#!/usr/bin/env python3
"""
Simulador funcional de la ISA LOVELACE (Lab 3c, Grupo 23).

Recibe la imagen generada por el ensamblador (.hex o .bin: los dos primeros
bytes son la direccion de origen) y la ejecuta. Los TRAP ejecutan el sistema
operativo de la ISA (so_g23.hex) en modo supervisor.

Informa:
  * la salida de la calculadora (consola);
  * instrucciones ejecutadas: el total y, entre parentesis, las del programa
    (un TRAP cuenta 1, como el simulador web del Grupo 8) y las del SO que
    atiende los TRAP (la catedra pidio contar las dos, 25/11/2026);
  * uso de memoria del programa (bytes y palabras).

Uso:
  python simulador.py <programa.hex|.bin> [--map programa.map] [--perfil salida.json]
                      [--teclado "texto"] [--max N] [--etiquetas programa.sym [N]]
  python simulador.py <programa.hex> --desensamblar    listado de la imagen en assembly
  python simulador.py <programa.hex> --traza N         muestra las primeras N instrucciones
  python simulador.py <programa.hex> --depurar         depurador interactivo (paso a paso,
                                                       puntos de parada, memoria, registros)
  (si existe programa.sym junto al .hex, se usan sus etiquetas; o --sym archivo.sym)
"""
import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from isa import (OP, KBSR, KBDR, DSR, DDR, MCR, FLAG_C, FLAG_V, sext, mnemonico, desensamblar)


class Excepcion(Exception):
    pass


def cargar_imagen(path):
    if path.lower().endswith(".bin"):
        data = open(path, "rb").read()
    else:
        data = bytes(int(t, 16) for t in open(path).read().split())
    origin = (data[0] << 8) | data[1]
    return origin, data[2:]


class CPU:
    def __init__(self, imagen, so=None, teclado="", max_steps=50_000_000):
        self.mem = bytearray(0x10000)
        if so:
            o, d = so
            self.mem[o:o + len(d)] = d
        origin, data = imagen
        self.mem[origin:origin + len(data)] = data
        self.origin, self.size = origin, len(data)
        self.R = [0] * 8
        self.R[6] = 0xFDFE                 # pila de usuario (alineada)
        self.ssp, self.usp = 0x3000, 0
        self.priv = 1
        self.pc = origin
        self.n = self.z = self.p = 0
        self.z = 1
        self.c = self.v = 0
        self.kbd = list(teclado)
        self.out = []
        self.halted = False
        self.max_steps = max_steps
        self.parada = set()     # puntos de interrupcion (direcciones)
        self.count = 0          # programa (criterio web)
        self.count_so = 0
        self.hits = Counter()
        self.hits_so = Counter()             # direcciones del SO ejecutadas (modelo de ciclos)
        self.ops = Counter()

    # ---- memoria ----
    def rw(self, a):
        a &= 0xFFFF
        if a & 1:
            raise Excepcion(f"lectura de palabra en direccion impar x{a:04X} (PC x{self.pc:04X})")
        if a >= 0xFE00:
            if a == KBSR:
                if not self.kbd and getattr(self, "fin_sin_teclado", False):
                    self.halted = True          # guion de teclado terminado
                return 0x8000 if self.kbd else 0
            if a == KBDR:
                return ord(self.kbd.pop(0)) if self.kbd else 0
            if a == DSR:
                return 0x8000
            if a == MCR:
                return 0 if self.halted else 0x8000
        return self.mem[a] | (self.mem[a + 1] << 8)

    def ww(self, a, v):
        a &= 0xFFFF
        if a & 1:
            raise Excepcion(f"escritura de palabra en direccion impar x{a:04X} (PC x{self.pc:04X})")
        if a >= 0xFE00:
            if a == DDR:
                self.out.append(chr(v & 0xFF))
                return
            if a == MCR:
                if not v & 0x8000:
                    self.halted = True
                return
        self.mem[a] = v & 0xFF
        self.mem[a + 1] = (v >> 8) & 0xFF

    def rb(self, a):
        return self.mem[a & 0xFFFF]

    def wb(self, a, v):
        self.mem[a & 0xFFFF] = v & 0xFF

    # ---- banderas ----
    def nzp(self, v):
        v &= 0xFFFF
        self.n, self.z, self.p = (v >> 15), int(v == 0), int(v != 0 and not v >> 15)

    def suma(self, a, b, cin=0):
        r = a + b + cin
        self.c = int(r > 0xFFFF)
        r &= 0xFFFF
        self.v = int(((a ^ r) & (b ^ r) & 0x8000) != 0)
        self.nzp(r)
        return r

    def psr(self):
        return (self.priv << 15) | (self.c << 4) | (self.v << 3) | (self.n << 2) | (self.z << 1) | self.p

    def set_psr(self, p):
        self.priv = p >> 15
        self.c, self.v = (p >> 4) & 1, (p >> 3) & 1
        self.n, self.z, self.p = (p >> 2) & 1, (p >> 1) & 1, p & 1

    def cond(self, nzp):
        return (nzp & 4 and self.n) or (nzp & 2 and self.z) or (nzp & 1 and self.p)

    def salto(self, destino):
        if destino & 1:
            raise Excepcion(f"salto a direccion impar x{destino:04X} (PC x{self.pc:04X})")
        self.pc = destino & 0xFFFF

    # ---- ciclo de instruccion ----
    def run(self, pasos=None):
        """Ejecuta hasta HALT, un punto de parada o 'pasos' instrucciones del
        programa (los TRAP se ejecutan completos, como una sola instruccion)."""
        R = self.R
        inicio = self.count
        primera = True
        while not self.halted:
            if self.count + self.count_so >= self.max_steps:
                raise Excepcion("limite de pasos alcanzado (posible lazo infinito)")
            pc = self.pc
            if self.priv and pasos is not None and self.count - inicio >= pasos:
                return "pasos"
            if pc in self.parada and self.priv and not (primera and pasos is not None):
                return "parada"
            primera = False
            w = self.rw(pc)
            if self.priv:
                self.count += 1
                self.hits[pc] += 1
            else:
                self.count_so += 1
                self.hits_so[pc] += 1
            self.pc = npc = (pc + 2) & 0xFFFF
            op = w >> 11
            self.ops[mnemonico(w) if self.priv else "(SO)"] += 1
            dr, s1 = (w >> 8) & 7, (w >> 5) & 7
            if op in (0, 1):                                    # BR
                if self.cond((w >> 9) & 7):
                    self.salto(npc + 2 * sext(w, 9))
            elif op == OP["ADDI"]:
                R[dr] = self.suma(R[s1], sext(w, 5) & 0xFFFF)
            elif op == OP["ALU"]:
                s2, f = (w >> 2) & 7, w & 3
                if f == 0:
                    R[dr] = self.suma(R[s1], R[s2])
                elif f == 1:                                    # SUB: C = 1 si no hubo prestamo
                    R[dr] = self.suma(R[s1], (~R[s2]) & 0xFFFF, 1)
                elif f == 2:
                    R[dr] = self.suma(R[s1], R[s2], self.c)
                else:                                           # ADDX: base + 2*indice
                    R[dr] = self.suma(R[s1], (2 * R[s2]) & 0xFFFF)
            elif op in (OP["LD"], OP["LD"] + 1):
                d = (w >> 9) & 7
                R[d] = self.rw(npc + 2 * sext(w, 9))
                self.nzp(R[d])
            elif op in (OP["ST"], OP["ST"] + 1):
                self.ww(npc + 2 * sext(w, 9), R[(w >> 9) & 7])
            elif op == OP["BRR"]:
                v = R[dr]
                n, z = v >> 15, v == 0
                c = (w >> 5) & 7
                if (c & 4 and n) or (c & 2 and z) or (c & 1 and not n and not z):
                    self.salto(npc + 2 * sext(w, 5))
            elif op == OP["JSR"]:
                R[7] = npc
                self.salto(npc + 2 * sext(w, 11))
            elif op == OP["ANDI"]:
                R[dr] = R[s1] & (sext(w, 5) & 0xFFFF)
                self.nzp(R[dr])
            elif op == OP["LOG"]:
                s2, f = (w >> 2) & 7, w & 3
                a, b = R[s1], R[s2]
                R[dr] = (a & b, a | b, a ^ b, (~a) & 0xFFFF)[f]
                self.nzp(R[dr])
            elif op in (OP["LDR"], OP["LDR"] + 1):
                d, b = (w >> 9) & 7, (w >> 6) & 7
                R[d] = self.rw(R[b] + 2 * sext(w, 6))
                self.nzp(R[d])
            elif op in (OP["STR"], OP["STR"] + 1):
                self.ww(R[(w >> 6) & 7] + 2 * sext(w, 6), R[(w >> 9) & 7])
            elif op == OP["RTI"]:
                if self.priv:
                    raise Excepcion(f"RTI en modo usuario (x{pc:04X})")
                self.pc = self.rw(R[6])
                p = self.rw(R[6] + 2)
                R[6] = (R[6] + 4) & 0xFFFF
                self.set_psr(p)
                if self.priv:
                    self.ssp, R[6] = R[6], self.usp
            elif op in (OP["SHL"], OP["SHA"]):
                n, f, v = (w & 0xF) + 1, (w >> 4) & 1, R[s1]
                if op == OP["SHL"] and f == 0:                  # LSL
                    self.c = (v >> (16 - n)) & 1
                    r = (v << n) & 0xFFFF
                elif op == OP["SHL"]:                           # LSR
                    self.c = (v >> (n - 1)) & 1
                    r = v >> n
                elif f == 0:                                    # ASR
                    sv = sext(v, 16)
                    self.c = (sv >> (n - 1)) & 1
                    r = (sv >> n) & 0xFFFF
                else:                                           # RLC: rota 17 bits (C:valor)
                    x = (self.c << 16) | v
                    for _ in range(n):
                        x = ((x << 1) | (x >> 16)) & 0x1FFFF
                    self.c, r = x >> 16, x & 0xFFFF
                R[dr] = r
                self.nzp(r)
            elif op == OP["LDB"]:
                R[dr] = sext(self.rb(R[s1] + sext(w, 5)), 8) & 0xFFFF
                self.nzp(R[dr])
            elif op == OP["LDBH"]:
                R[dr] = (R[dr] & 0x00FF) | (self.rb(R[s1] + sext(w, 5)) << 8)
                self.nzp(R[dr])
            elif op == OP["STB"]:
                self.wb(R[s1] + sext(w, 5), R[dr])
            elif op == OP["STBH"]:
                self.wb(R[s1] + sext(w, 5), R[dr] >> 8)
            elif op == OP["DBP"]:
                R[dr] = (R[dr] - 1) & 0xFFFF
                self.nzp(R[dr])
                if self.p:
                    self.salto(npc + 2 * sext(w, 8))
            elif op == OP["JMP"]:
                destino = R[s1]
                if w & 0x400:
                    R[7] = npc
                self.salto(destino)
            elif op == OP["BRX"]:
                c = (w >> 8) & 7
                if c > 5:
                    raise Excepcion(f"instruccion invalida x{w:04X} en x{pc:04X} (condicion BRX reservada)")
                ok = (self.c, not self.c, self.v, not self.v,
                      self.c and not self.z, (not self.c) or self.z)[c]
                if ok:
                    self.salto(npc + 2 * sext(w, 8))
            elif op == OP["PUSHPOP"]:
                mask = w & 0xFF
                if mask & 0x40:
                    raise Excepcion(f"instruccion invalida x{w:04X} en x{pc:04X} (R6 en PUSH/POP)")
                if w & 0x400:                                   # POP R0..R7
                    for r in range(8):
                        if mask >> r & 1:
                            R[r] = self.rw(R[6])
                            R[6] = (R[6] + 2) & 0xFFFF
                else:                                           # PUSH R7..R0
                    for r in range(7, -1, -1):
                        if mask >> r & 1:
                            R[6] = (R[6] - 2) & 0xFFFF
                            self.ww(R[6], R[r])
            elif op in (OP["LEA"], OP["LEA"] + 1):
                R[(w >> 9) & 7] = (npc + 2 * sext(w, 9)) & 0xFFFF
            elif op == OP["MUL"]:
                s2, f = (w >> 2) & 7, w & 3
                a, b = R[s1], R[s2]
                if f == 0:                                      # MUL: 16 bits bajos
                    p = sext(a, 16) * sext(b, 16)
                    self.v = int(not -32768 <= p <= 32767)      # V = 1 si no entra en 16 bits
                    r = p & 0xFFFF
                elif f == 1:                                    # MULH: 16 altos, con signo
                    r = ((sext(a, 16) * sext(b, 16)) >> 16) & 0xFFFF
                elif f == 2:                                    # MULHU: 16 altos, sin signo
                    r = (a * b) >> 16
                else:
                    raise Excepcion(f"instruccion invalida x{w:04X} en x{pc:04X} (MUL reservada)")
                R[dr] = r
                self.nzp(r)
            elif op == OP["DIV"]:
                s2, f = (w >> 2) & 7, w & 3
                a, b = R[s1], R[s2]
                self.v = 0
                if f in (0, 1):                                 # con signo, cociente truncado a 0
                    x, y = sext(a, 16), sext(b, 16)
                    if y == 0:
                        self.v = 1
                        r = 0xFFFF if f == 0 else a
                    elif x == -32768 and y == -1:
                        self.v = 1
                        r = 0x8000 if f == 0 else 0
                    else:
                        q = abs(x) // abs(y) * (1 if (x < 0) == (y < 0) else -1)
                        r = (q if f == 0 else x - q * y) & 0xFFFF
                else:                                           # sin signo
                    if b == 0:
                        self.v = 1
                        r = 0xFFFF if f == 2 else a
                    else:
                        r = a // b if f == 2 else a % b
                R[dr] = r
                self.nzp(r)
            elif op == OP["TRAP"]:
                self.trap(w & 0xFF)
            else:
                raise Excepcion(f"instruccion invalida x{w:04X} en x{pc:04X}")

    def trap(self, vec):
        R = self.R
        old = self.psr()
        if self.priv:
            self.usp, R[6] = R[6], self.ssp
        self.priv = 0
        R[6] = (R[6] - 2) & 0xFFFF
        self.ww(R[6], old)
        R[6] = (R[6] - 2) & 0xFFFF
        self.ww(R[6], self.pc)
        self.salto(self.rw(2 * vec))


def perfil_por_modulo(cpu, map_path):
    rangos = []
    for line in open(map_path, encoding="utf-8"):
        p = line.split()
        if p[0] != "TOTAL":
            rangos.append((int(p[0][1:], 16), int(p[1][1:], 16), p[3]))
    por_mod = Counter()
    for a, n in cpu.hits.items():
        for lo, hi, k in rangos:
            if lo <= a <= hi:
                por_mod[k] += n
                break
    return por_mod


# ------------------------------------------------- desensamblado y depuracion --
def cargar_simbolos(path):
    """Tabla .sym del ensamblador -> {direccion: 'modulo:ETIQUETA'}."""
    if not path or not os.path.exists(path):
        return {}
    s = {}
    for line in open(path, encoding="utf-8"):
        a, n = line.split()
        s.setdefault(int(a[1:], 16), n.split(":", 1)[-1] if n.startswith("entrada:") else n)
    return s


def linea(cpu, a, sim):
    w = cpu.rw(a)
    etq = sim.get(a, "")
    return f"x{a:04X}  {w:04X}  {etq[:28]:28s} {desensamblar(w, a, sim)}"


def listado(cpu, sim, desde=None, n=None):
    a = cpu.origin if desde is None else desde
    fin = cpu.origin + cpu.size if n is None else a + 2 * n
    while a < fin:
        print(linea(cpu, a, sim))
        a += 2


def estado(cpu):
    regs = "  ".join(f"R{i}=x{v:04X}" for i, v in enumerate(cpu.R))
    fl = "".join(c for c, b in zip("NZPCV", (cpu.n, cpu.z, cpu.p, cpu.c, cpu.v)) if b)
    return f"{regs}  PC=x{cpu.pc:04X}  [{fl}]"


def traza(cpu, n, sim):
    """Ejecuta n instrucciones mostrando cada una y los registros que cambian."""
    for _ in range(n):
        if cpu.halted:
            break
        antes = list(cpu.R)
        txt = linea(cpu, cpu.pc, sim)
        cpu.run(pasos=1)
        cambios = " ".join(f"R{i}=x{v:04X}" for i, (a, v) in enumerate(zip(antes, cpu.R)) if a != v)
        print(f"{txt:70s} {cambios}")


def depurar(cpu, sim):
    ayuda = ("s [n]  ejecutar n instrucciones (traza)   c  continuar hasta parada o HALT\n"
             "b DIR|ETIQUETA  punto de parada          r  registros y banderas\n"
             "m DIR [n]  ver memoria (palabras)        d [DIR] [n]  desensamblar\n"
             "q  salir")
    nombres = {}
    for k, v in sim.items():
        nombres.setdefault(v.split(":")[-1].upper(), k)    # etiqueta sola (SQRT_NR)
        nombres[v.upper()] = k                              # modulo:etiqueta
    print("Depurador de la ISA LOVELACE. 'h' muestra la ayuda.")
    print(estado(cpu))
    while not cpu.halted:
        try:
            cmd = input("(g23) ").replace("﻿", "").split()
        except EOFError:
            break
        if not cmd:
            continue
        c, args = cmd[0].lower(), cmd[1:]

        def dir_(t):
            t = t.upper()
            return nombres[t] if t in nombres else int(t.lstrip("X"), 16)
        try:
            if c == "h":
                print(ayuda)
            elif c == "s":
                traza(cpu, int(args[0]) if args else 1, sim)
            elif c == "c":
                r = cpu.run()
                print("".join(cpu.out), end="")
                cpu.out.clear()
                print(f"\n[{r or 'HALT'}] {estado(cpu)}")
            elif c == "b":
                cpu.parada.add(dir_(args[0]))
                print("paradas:", ", ".join(f"x{a:04X}" for a in sorted(cpu.parada)))
            elif c == "r":
                print(estado(cpu))
            elif c == "m":
                a = dir_(args[0]) & ~1
                for k in range(int(args[1]) if len(args) > 1 else 8):
                    print(f"x{a + 2 * k:04X}  x{cpu.rw(a + 2 * k):04X}")
            elif c == "d":
                listado(cpu, sim, dir_(args[0]) if args else cpu.pc, int(args[1]) if len(args) > 1 else 10)
            elif c == "q":
                break
            else:
                print(ayuda)
        except (KeyError, ValueError, IndexError) as e:
            print("comando invalido:", e)
        except Excepcion as e:
            print("EXCEPCION:", e)
            break
    print("".join(cpu.out), end="")


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    aqui = os.path.dirname(os.path.abspath(__file__))
    so = cargar_imagen(os.path.join(aqui, "so_g23.hex"))
    teclado = argv[argv.index("--teclado") + 1] if "--teclado" in argv else ""
    teclado = teclado.replace("\\n", "\n")          # "\n" escrito en la linea de comandos = Enter
    mx = int(argv[argv.index("--max") + 1]) if "--max" in argv else 50_000_000
    cpu = CPU(cargar_imagen(argv[1]), so, teclado, mx)
    sim = cargar_simbolos(argv[argv.index("--sym") + 1] if "--sym" in argv
                          else os.path.splitext(argv[1])[0] + ".sym")
    if "--desensamblar" in argv:
        listado(cpu, sim)
        return 0
    if "--depurar" in argv:
        depurar(cpu, sim)
        return 0
    try:
        if "--traza" in argv:
            traza(cpu, int(argv[argv.index("--traza") + 1]), sim)
        cpu.run()
    except Excepcion as e:
        print("".join(cpu.out))
        print("EXCEPCION:", e)
        return 1
    print("".join(cpu.out))
    print("=" * 60)
    print(f"Instrucciones ejecutadas: {cpu.count + cpu.count_so}  (programa {cpu.count}, SO {cpu.count_so})")
    print(f"Memoria: {cpu.size} bytes = {cpu.size // 2} palabras  "
          f"x{cpu.origin:04X}-x{cpu.origin + cpu.size - 1:04X}")
    print("\nPor instruccion:")
    for k, v in cpu.ops.most_common():
        if k != "(SO)":
            print(f"  {k:6s} {v:9d} {100 * v / cpu.count:6.2f} %")
    pm = None
    if "--map" in argv:
        pm = perfil_por_modulo(cpu, argv[argv.index("--map") + 1])
        print("\nPor modulo:")
        for k, v in pm.most_common():
            print(f"  {k:40s} {v:9d} {100 * v / cpu.count:6.2f} %")
    if "--etiquetas" in argv:
        # perfil por etiqueta (zona de codigo) usando la tabla de simbolos .sym
        import bisect
        sym = sorted((int(l.split()[0][1:], 16), l.split()[1])
                     for l in open(argv[argv.index("--etiquetas") + 1], encoding="utf-8"))
        ks = [s[0] for s in sym]
        pl = Counter()
        for a, n in cpu.hits.items():
            i = bisect.bisect_right(ks, a) - 1
            pl[sym[i][1] if i >= 0 else "?"] += n
        print("\nZonas mas costosas:")
        for k, v in pl.most_common(int(argv[argv.index("--etiquetas") + 2]) if len(argv) > argv.index("--etiquetas") + 2 and argv[argv.index("--etiquetas") + 2].isdigit() else 25):
            print(f"  {k:55s} {v:8d} {100 * v / cpu.count:6.2f} %")
    if "--perfil" in argv:
        with open(argv[argv.index("--perfil") + 1], "w", encoding="utf-8") as fh:
            json.dump({"instrucciones": cpu.count, "instrucciones_so": cpu.count_so,
                       "bytes": cpu.size, "por_instruccion": dict(cpu.ops),
                       "por_modulo": dict(pm or {}), "salida": "".join(cpu.out)},
                      fh, ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
