#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
simulador.py - Simulador funcional de la ISA-NZP (LC-3 expandida, byte-addressable).

Uso:
    python simulador.py programa.bin [opciones]
    python simulador.py --carpeta build [opciones]        (modo lote, v2)

    --carpeta DIR         simula cada .bin de la carpeta y muestra un resumen
                          (estado, instrucciones, salida). No aborta si uno falla.
    --regs R0=5,R1=0x180  valores iniciales de registros (útil para módulos)

    --traza               muestra cada instrucción ejecutada y los registros
    --entrada "texto"     texto para GETC/IN (admite \\n); sin esto lee stdin
    --max N               límite de instrucciones (por defecto 5.000.000)
    --pila 0xFE00         valor inicial de R6
    --volcar 0x4000:8     muestra 8 palabras desde esa dirección (repetible)
    --perfil              instrucciones ejecutadas por etiqueta (usa programa.sym)
    --permitir-sqr        habilita SQR (prohibida por el enunciado)
    --silencioso          no imprime la salida del programa

Modo LC-3 clásico (compatibilidad): si el .bin empieza con la cabecera "LC3C"
(lo genera el ensamblador cuando el fuente es LC-3 original: LD/ST/LDR/STR,
ADD con inmediato de 5 bits, etc.) el simulador ejecuta un LC-3 de 65536
PALABRAS: direcciones de palabra, PC += 1, .STRINGZ de un carácter por
palabra, TRAPs iguales. Se elige solo, no hace falta ninguna opción.

El archivo de entrada es el .bin (o .hex) del ensamblador: los 2 primeros bytes
son la dirección de origen y a partir de ahí va la imagen. El PC arranca en el
origen. No se acepta assembly.

Semántica (resumen; los formatos de bits están en isa.py)
  - Memoria de 64 KB, big-endian. PC += 2. Palabras (LDH/STH) en direcciones
    pares; si no, excepción. Saltar o retornar a una dirección impar también.
  - N, Z, P los modifican: ADD AND NOT LDB LDH LD MUL DIV MOD SHF SQR.
    No los modifican: LEA, STB, STH, ST, saltos y TRAP.
  - LDB  H=0: DR = byte con extensión de signo (int8 -> int16)
         H=1: DR[15:8] = byte, DR[7:0] se conserva
    STB  H=0: guarda SR[7:0]      H=1: guarda SR[15:8]
  - MUL: producto con signo, se guardan los 16 bits bajos (entero, no Q).
    DIV/MOD: con signo, truncan hacia cero; MOD tiene el signo del dividendo.
    División por cero: excepción.
  - SHF: tipo 00 SHL, 01 SHR lógico, 10 SAR aritmético.
  - TRAP guarda PC+2 en R7 (como la LC-3), salvo HALT, que detiene la
    máquina sin tocar R7. Servicios: x20 GETC, x21 OUT, x22 PUTS (cadena de
    bytes), x23 IN, x24 PUTSP, x25 HALT.
  - RTI no está soportada (no hay interrupciones ni modo supervisor).
"""
import argparse
import bisect
import math
import re
import sys
from collections import Counter, deque

import isa
import isa_lc3


class ErrorSimulador(Exception):
    pass


class SimuladorLC3Exp:
    paso_dir = 2                 # bytes por palabra al volcar memoria
    etiqueta_modo = ""

    def __init__(self, entrada="", eco=True, max_instrucciones=5_000_000,
                 pila_inicial=isa.PILA_INICIAL, stdin_interactivo=False):
        # Memoria de 2^16 bytes (byte-addressable)
        self.memoria = bytearray(65536)
        self.registros = [0] * 8
        self.pc = isa.ORIGEN_DEFECTO
        self.n, self.z, self.p = False, True, False
        self.corriendo = True
        self.motivo = None
        self.error = None
        # entrada / salida
        self.entrada = deque(entrada)
        self.stdin_interactivo = stdin_interactivo
        self.eco = eco
        self.salida = []
        # límites y métricas
        self.max_instrucciones = max_instrucciones
        self.pila_inicial = pila_inicial & 0xFFFE
        self.registros[6] = self.pila_inicial
        self.instrucciones = 0
        self.histograma = Counter()
        self.tocado = bytearray(65536)      # bytes leídos/escritos/cargados
        self.escrito = bytearray(65536)     # bytes escritos durante la ejecución
        self.imagen_origen, self.imagen_tam = 0, 0
        self.sp_min = self.pila_inicial
        self.perfilar = False
        self.perfil_pc = Counter()
        self.simbolos = []

    # ------------------------------------------------------------- carga
    def cargar_bytes(self, datos):
        if len(datos) < 2:
            raise ErrorSimulador("archivo vacío: faltan los 2 bytes de origen")
        origen = isa.unpack_word(datos[0], datos[1])
        cuerpo = datos[2:]
        if origen % 2:
            raise ErrorSimulador(f"origen impar (x{origen:04X})")
        if origen + len(cuerpo) > 65536:
            raise ErrorSimulador("el programa no entra en 64 KB")
        self.memoria[origen:origen + len(cuerpo)] = cuerpo
        for i in range(origen, origen + len(cuerpo)):
            self.tocado[i] = 1
        self.imagen_origen, self.imagen_tam = origen, len(cuerpo)
        self.pc = origen

    @staticmethod
    def _leer_archivo(ruta):
        with open(ruta, "rb") as f:
            datos = f.read()
        if ruta.lower().endswith(".hex"):
            texto = datos.decode("ascii", errors="ignore")
            texto = re.sub(r"[;#].*", "", texto)
            hexa = re.sub(r"\s+", "", texto)
            try:
                return bytes.fromhex(hexa)
            except ValueError:
                raise ErrorSimulador("el .hex tiene caracteres no "
                                     "hexadecimales o dígitos impares")
        return datos

    def cargar_programa(self, archivo_binario):
        self.cargar_bytes(self._leer_archivo(archivo_binario))

    def cargar_simbolos(self, ruta):
        sims = []
        with open(ruta) as f:
            for linea in f:
                p = linea.split()
                if len(p) == 2:
                    sims.append((int(p[1], 16), p[0]))
        self.simbolos = sorted(sims)

    # ---------------------------------------------------------- memoria
    def leer_palabra(self, direccion):
        direccion &= 0xFFFF
        if direccion % 2:
            raise ErrorSimulador(
                f"acceso a palabra en dirección impar x{direccion:04X}")
        self.tocado[direccion] = self.tocado[direccion + 1] = 1
        return isa.unpack_word(self.memoria[direccion],
                               self.memoria[direccion + 1])

    def escribir_palabra(self, direccion, valor):
        direccion &= 0xFFFF
        if direccion % 2:
            raise ErrorSimulador(
                f"acceso a palabra en dirección impar x{direccion:04X}")
        b = isa.pack_word(valor)
        self.memoria[direccion], self.memoria[direccion + 1] = b[0], b[1]
        self.tocado[direccion] = self.tocado[direccion + 1] = 1
        self.escrito[direccion] = self.escrito[direccion + 1] = 1

    def leer_byte(self, direccion):
        direccion &= 0xFFFF
        self.tocado[direccion] = 1
        return self.memoria[direccion]

    def escribir_byte(self, direccion, valor):
        direccion &= 0xFFFF
        self.memoria[direccion] = valor & 0xFF
        self.tocado[direccion] = self.escrito[direccion] = 1

    # ------------------------------------------------------------ flags
    def actualizar_cond(self, valor):
        valor &= 0xFFFF
        self.n = (valor & 0x8000) != 0
        self.z = valor == 0
        self.p = not self.n and not self.z

    # ------------------------------------------------------------ E/S
    def _emitir(self, texto):
        self.salida.append(texto)
        if self.eco:
            sys.stdout.write(texto)
            sys.stdout.flush()

    def _leer_caracter(self):
        if self.entrada:
            return self.entrada.popleft()
        if self.stdin_interactivo:
            c = sys.stdin.read(1)
            if c:
                return c
        raise ErrorSimulador("se acabó la entrada: el programa pidió un "
                             "carácter (GETC/IN) y no hay más (use --entrada)")

    def _trap(self, vect):
        R = self.registros
        if vect == 0x20:                                    # GETC
            R[0] = ord(self._leer_caracter()) & 0xFF
        elif vect == 0x21:                                  # OUT
            self._emitir(chr(R[0] & 0xFF))
        elif vect == 0x22:                                  # PUTS
            a, out = R[0], []
            for _ in range(65536):
                b = self.leer_byte(a)
                if b == 0:
                    break
                out.append(chr(b))
                a = (a + 1) & 0xFFFF
            self._emitir("".join(out))
        elif vect == 0x23:                                  # IN
            self._emitir("Input a character> ")
            c = self._leer_caracter()
            R[0] = ord(c) & 0xFF
            self._emitir(c)
        elif vect == 0x24:                                  # PUTSP
            a, out = R[0] & 0xFFFE, []
            for _ in range(32768):
                w = self.leer_palabra(a)
                lo, hi = w & 0xFF, w >> 8
                if lo == 0:
                    break
                out.append(chr(lo))
                if hi == 0:
                    break
                out.append(chr(hi))
                a = (a + 2) & 0xFFFF
            self._emitir("".join(out))
        elif vect == 0x25:                                  # HALT
            self.corriendo = False
            self.motivo = "HALT"
        else:
            raise ErrorSimulador(f"TRAP x{vect:02X} no soportado")

    # ------------------------------------------------------------- step
    def step(self):
        pc = self.pc
        if pc % 2:
            raise ErrorSimulador(
                f"PC impar (x{pc:04X}): salto o retorno a una dirección "
                f"no alineada")
        w = self.leer_palabra(pc)
        try:
            ins = isa.decodificar(w)
        except isa.InstruccionInvalida as e:
            raise ErrorSimulador(f"instrucción inválida: {e}")
        mn = ins.mn
        R = self.registros
        sig = (pc + 2) & 0xFFFF           # PC incrementado
        nuevo_pc = sig

        if mn == "ADD" or mn == "AND":
            a = R[ins.sr1]
            b = (R[ins.sr2] if ins.imm is None else ins.imm & 0xFFFF)
            v = ((a + b) if mn == "ADD" else (a & b)) & 0xFFFF
            R[ins.dr] = v
            self.actualizar_cond(v)
        elif mn == "NOT":
            R[ins.dr] = ~R[ins.sr1] & 0xFFFF
            self.actualizar_cond(R[ins.dr])
        elif mn == "BR":
            if ((ins.nzp & 4 and self.n) or (ins.nzp & 2 and self.z)
                    or (ins.nzp & 1 and self.p)):
                nuevo_pc = (sig + 2 * ins.off) & 0xFFFF
        elif mn == "LDH":
            R[ins.dr] = self.leer_palabra(R[ins.sr1] + 2 * ins.off)
            self.actualizar_cond(R[ins.dr])
        elif mn == "STH":
            self.escribir_palabra(R[ins.sr1] + 2 * ins.off, R[ins.dr])
        elif mn == "LDB":
            b = self.leer_byte(R[ins.sr1] + ins.off)
            if ins.h == 0:
                R[ins.dr] = b | 0xFF00 if b & 0x80 else b
            else:
                R[ins.dr] = (b << 8) | (R[ins.dr] & 0xFF)
            self.actualizar_cond(R[ins.dr])
        elif mn == "STB":
            v = R[ins.dr]
            self.escribir_byte(R[ins.sr1] + ins.off,
                               (v >> 8) & 0xFF if ins.h else v & 0xFF)
        elif mn == "LEA":
            R[ins.dr] = (sig + 2 * ins.off) & 0xFFFF
        elif mn == "LD":
            R[ins.dr] = self.leer_palabra(sig + 2 * ins.off)
            self.actualizar_cond(R[ins.dr])
        elif mn == "ST":
            self.escribir_palabra(sig + 2 * ins.off, R[ins.dr])
        elif mn == "JSR":
            R[7] = sig
            nuevo_pc = (sig + 2 * ins.off) & 0xFFFF
        elif mn == "JSRR" or mn == "JMP":
            destino = R[ins.sr1]
            if mn == "JMP" and ins.sr1 == 7 and destino == 0:
                raise ErrorSimulador(
                    "RET con R7=0: nadie llamó a esta rutina (¿es un módulo "
                    "y no un programa? necesita un principal que haga JSR/"
                    "JSRR, o use benchmark.py)")
            if destino % 2:
                raise ErrorSimulador(
                    f"salto a dirección impar x{destino:04X}")
            if mn == "JSRR":
                R[7] = sig
            nuevo_pc = destino
        elif mn == "TRAP":
            if ins.vect != 0x25:          # HALT detiene la máquina: R7 queda
                R[7] = sig
            self._trap(ins.vect)
        elif mn == "MUL":
            v = (isa.a_signed16(R[ins.sr1]) * isa.a_signed16(R[ins.sr2])) \
                & 0xFFFF
            R[ins.dr] = v
            self.actualizar_cond(v)
        elif mn == "DIV" or mn == "MOD":
            a, b = isa.a_signed16(R[ins.sr1]), isa.a_signed16(R[ins.sr2])
            if b == 0:
                raise ErrorSimulador(f"{mn} por cero")
            q = abs(a) // abs(b)
            if (a < 0) != (b < 0):
                q = -q
            v = (q if mn == "DIV" else a - q * b) & 0xFFFF
            R[ins.dr] = v
            self.actualizar_cond(v)
        elif mn == "SHF":
            v, c = R[ins.sr1], ins.cant
            if ins.tipo == 0:
                v = (v << c) & 0xFFFF
            elif ins.tipo == 1:
                v = v >> c
            else:
                v = (isa.a_signed16(v) >> c) & 0xFFFF
            R[ins.dr] = v
            self.actualizar_cond(v)
        elif mn == "SQR":
            if not isa.CONFIG["sqr"]:
                raise ErrorSimulador(
                    "SQR está prohibida por el enunciado del Lab 3 "
                    "(use --permitir-sqr si el grupo la habilita)")
            a = isa.a_signed16(R[ins.sr1])
            if a < 0:
                raise ErrorSimulador("SQR de un número negativo")
            R[ins.dr] = math.isqrt(a)
            self.actualizar_cond(R[ins.dr])
        elif mn == "RTI":
            raise ErrorSimulador("RTI no soportada: el simulador no modela "
                                 "interrupciones")
        else:
            raise ErrorSimulador(f"instrucción sin implementar: {mn}")

        self.pc = nuevo_pc
        self.instrucciones += 1
        self.histograma[mn] += 1
        if self.perfilar:
            self.perfil_pc[pc] += 1
        if R[6] < self.sp_min:
            self.sp_min = R[6]

    # --------------------------------------------------------------- run
    def _linea_traza(self, pc):
        try:
            w = self.leer_palabra(pc)
            txt = isa.desensamblar(w, pc)
        except ErrorSimulador:
            w, txt = 0, "(fuera de alineación)"
        regs = " ".join(f"R{i}={self.registros[i]:04X}" for i in range(8))
        cc = ("N" if self.n else "-") + ("Z" if self.z else "-") + \
             ("P" if self.p else "-")
        return f"{pc:04X}: {w:04X}  {txt.split(';')[0].strip():<26} {cc}  {regs}"

    def run(self, traza=False):
        try:
            while self.corriendo:
                if self.instrucciones >= self.max_instrucciones:
                    raise ErrorSimulador(
                        f"se alcanzó el límite de {self.max_instrucciones} "
                        f"instrucciones (¿bucle infinito?)")
                if traza:
                    print(self._linea_traza(self.pc))
                self.step()
        except ErrorSimulador as e:
            self.error = f"{e}  [PC=x{self.pc:04X}]"
            self.corriendo = False
            self.motivo = "EXCEPCION"
        return self.motivo

    # ----------------------------------------------------------- reporte
    def uso_memoria(self):
        imagen = self.imagen_tam
        escritos = sum(self.escrito)
        total = sum(self.tocado)
        pila = max(0, self.pila_inicial - self.sp_min)
        return {"imagen": imagen, "escritos": escritos,
                "pila_max": pila, "total_tocados": total}

    def perfil_por_simbolo(self):
        if not self.simbolos:
            return {}
        dirs = [a for a, _ in self.simbolos]
        res = Counter()
        for pc, n in self.perfil_pc.items():
            i = bisect.bisect_right(dirs, pc) - 1
            res[self.simbolos[i][1] if i >= 0 else "(sin etiqueta)"] += n
        return res

    def reporte(self, volcados=(), perfil=False):
        L = ["", "=== RESULTADOS ===",
             f"Motivo de parada       : {self.motivo}"]
        if self.etiqueta_modo:
            L.append(f"Modo                   : {self.etiqueta_modo}")
        if self.error:
            L.append(f"Excepción              : {self.error}")
        L.append(f"Instrucciones ejecutadas: {self.instrucciones}")
        L.append("Registros              : " + "  ".join(
            f"R{i}=x{v:04X}({isa.a_signed16(v)})"
            for i, v in enumerate(self.registros)))
        L.append(f"Flags                  : N={int(self.n)} Z={int(self.z)} "
                 f"P={int(self.p)}")
        m = self.uso_memoria()
        L.append(f"Memoria                : imagen {m['imagen']} bytes "
                 f"(x{self.imagen_origen:04X}..), "
                 f"escritos {m['escritos']} bytes, "
                 f"pila máx {m['pila_max']} bytes, "
                 f"total tocados {m['total_tocados']} bytes")
        top = ", ".join(f"{k}:{v}" for k, v in self.histograma.most_common(8))
        L.append(f"Instrucciones más usadas: {top}")
        for ini, cant in volcados:
            pal = []
            for k in range(cant):
                try:
                    pal.append(f"{self.leer_palabra(ini + self.paso_dir * k):04X}")
                except ErrorSimulador:
                    pal.append("????")
            L.append(f"Memoria x{ini:04X}      : " + " ".join(pal))
        if perfil:
            pr = self.perfil_por_simbolo()
            if pr:
                L.append("Instrucciones por etiqueta (región hasta la "
                         "siguiente):")
                for k, v in pr.most_common(15):
                    L.append(f"   {k:<22} {v:>9}  "
                             f"({100.0 * v / self.instrucciones:5.1f}%)")
            else:
                L.append("(sin perfil: falta el archivo .sym)")
        return "\n".join(L)


class SimuladorLC3Clasico(SimuladorLC3Exp):
    """LC-3 original: memoria de 65536 palabras, direcciones de palabra."""
    paso_dir = 1
    etiqueta_modo = "LC-3 clásico (direcciones de palabra)"

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.mem = [0] * 65536
        self.memoria = None
        self.pc = isa.ORIGEN_DEFECTO
        self.pila_inicial = self.registros[6] = self.pila_inicial & 0xFFFF
        self.sp_min = self.pila_inicial

    # -------------------------------------------------------------- carga
    def cargar_bytes(self, datos):
        if datos[:4] != isa_lc3.MAGIC:
            raise ErrorSimulador("no es un binario LC-3 clásico (falta la "
                                 "cabecera LC3C)")
        datos = datos[4:]
        if len(datos) < 2:
            raise ErrorSimulador("archivo vacío: falta el origen")
        origen = isa.unpack_word(datos[0], datos[1])
        cuerpo = datos[2:]
        if len(cuerpo) % 2:
            raise ErrorSimulador("la imagen tiene un número impar de bytes")
        n = len(cuerpo) // 2
        if origen + n > 65536:
            raise ErrorSimulador("el programa no entra en 64K palabras")
        for i in range(n):
            self.mem[origen + i] = isa.unpack_word(cuerpo[2 * i],
                                                   cuerpo[2 * i + 1])
            self.tocado[origen + i] = 1
        self.imagen_origen, self.imagen_tam = origen, len(cuerpo)
        self.pc = origen

    def leer_palabra(self, direccion):
        d = direccion & 0xFFFF
        self.tocado[d] = 1
        return self.mem[d]

    def escribir_palabra(self, direccion, valor):
        d = direccion & 0xFFFF
        self.mem[d] = valor & 0xFFFF
        self.tocado[d] = self.escrito[d] = 1

    def leer_byte(self, direccion):
        raise ErrorSimulador("el LC-3 clásico no direcciona bytes")

    escribir_byte = leer_byte

    def uso_memoria(self):
        """Mismas magnitudes que el modo nuevo, en bytes (2 por palabra)."""
        return {"imagen": self.imagen_tam,
                "escritos": 2 * sum(self.escrito),
                "pila_max": 2 * max(0, self.pila_inicial - self.sp_min),
                "total_tocados": 2 * sum(self.tocado)}

    # --------------------------------------------------------------- TRAP
    def _trap(self, vect):
        R = self.registros
        if vect == 0x22:                       # PUTS: un carácter por palabra
            a, out = R[0], []
            for _ in range(65536):
                w = self.leer_palabra(a) & 0xFFFF
                if w == 0:
                    break
                out.append(chr(w & 0xFF))
                a = (a + 1) & 0xFFFF
            self._emitir("".join(out))
        elif vect == 0x24:                     # PUTSP: dos caracteres/palabra
            a, out = R[0], []
            for _ in range(65536):
                w = self.leer_palabra(a)
                lo, hi = w & 0xFF, w >> 8
                if lo == 0:
                    break
                out.append(chr(lo))
                if hi == 0:
                    break
                out.append(chr(hi))
                a = (a + 1) & 0xFFFF
            self._emitir("".join(out))
        else:
            super()._trap(vect)                # GETC, OUT, IN, HALT

    # --------------------------------------------------------------- step
    def step(self):
        pc = self.pc & 0xFFFF
        mem, R = self.mem, self.registros
        self.tocado[pc] = 1
        w = mem[pc]
        op = w >> 12
        sig = (pc + 1) & 0xFFFF
        nuevo = sig
        dr = (w >> 9) & 7

        if op == 1 or op == 5:                               # ADD / AND
            a = R[(w >> 6) & 7]
            if w & 0x20:
                b = w & 0x1F
                if b & 0x10:
                    b |= 0xFFE0
            else:
                b = R[w & 7]
            v = ((a + b) & 0xFFFF) if op == 1 else (a & b)
            R[dr] = v
            self._cc(v)
            mn = "ADD" if op == 1 else "AND"
        elif op == 0:                                        # BR
            nzp = dr
            if (nzp & 4 and self.n) or (nzp & 2 and self.z) or \
                    (nzp & 1 and self.p):
                o = w & 0x1FF
                nuevo = (sig + (o - 512 if o & 0x100 else o)) & 0xFFFF
            mn = "BR"
        elif op == 2 or op == 10 or op == 14 or op == 3 or op == 11:
            o = w & 0x1FF
            ea = (sig + (o - 512 if o & 0x100 else o)) & 0xFFFF
            if op == 2:                                      # LD
                R[dr] = self.leer_palabra(ea)
                self._cc(R[dr])
                mn = "LD"
            elif op == 10:                                   # LDI
                R[dr] = self.leer_palabra(self.leer_palabra(ea))
                self._cc(R[dr])
                mn = "LDI"
            elif op == 14:                                   # LEA
                R[dr] = ea
                if isa_lc3.LEA_FIJA_CC:
                    self._cc(ea)
                mn = "LEA"
            elif op == 3:                                    # ST
                self.escribir_palabra(ea, R[dr])
                mn = "ST"
            else:                                            # STI
                self.escribir_palabra(self.leer_palabra(ea), R[dr])
                mn = "STI"
        elif op == 6 or op == 7:                             # LDR / STR
            o = w & 0x3F
            ea = (R[(w >> 6) & 7] + (o - 64 if o & 0x20 else o)) & 0xFFFF
            if op == 6:
                R[dr] = self.leer_palabra(ea)
                self._cc(R[dr])
                mn = "LDR"
            else:
                self.escribir_palabra(ea, R[dr])
                mn = "STR"
        elif op == 9:                                        # NOT
            R[dr] = ~R[(w >> 6) & 7] & 0xFFFF
            self._cc(R[dr])
            mn = "NOT"
        elif op == 12:                                       # JMP / RET
            nuevo = R[(w >> 6) & 7]
            if (w >> 6) & 7 == 7 and nuevo == 0:
                raise ErrorSimulador(
                    "RET con R7=0: nadie llamó a esta rutina (¿es un módulo "
                    "y no un programa? necesita un principal que haga JSR/"
                    "JSRR, o use benchmark.py)")
            mn = "JMP"
        elif op == 4:                                        # JSR / JSRR
            if w & 0x800:
                o = w & 0x7FF
                destino = (sig + (o - 2048 if o & 0x400 else o)) & 0xFFFF
            else:
                destino = R[(w >> 6) & 7]
            R[7] = sig
            nuevo = destino
            mn = "JSR"
        elif op == 15:                                       # TRAP
            vect = w & 0xFF
            if vect != 0x25:
                R[7] = sig
            self._trap(vect)
            mn = "TRAP"
        elif op == 8:
            raise ErrorSimulador("RTI no soportada: el simulador no modela "
                                 "interrupciones")
        else:
            raise ErrorSimulador(f"instrucción inválida: opcode reservado "
                                 f"(x{w:04X})")

        self.pc = nuevo
        self.instrucciones += 1
        self.histograma[mn] += 1
        if self.perfilar:
            self.perfil_pc[pc] += 1
        # Algunos módulos usan R6 como registro común (p. ej. puntero a una
        # tabla): solo cuenta como pila si cae cerca del tope de la pila.
        if self.sp_min > R[6] > self.pila_inicial - 0x2000:
            self.sp_min = R[6]

    def _cc(self, v):
        self.n = (v & 0x8000) != 0
        self.z = v == 0
        self.p = not self.n and not self.z

    def _linea_traza(self, pc):
        w = self.leer_palabra(pc)
        txt = isa_lc3.desensamblar(w, pc)
        regs = " ".join(f"R{i}={self.registros[i]:04X}" for i in range(8))
        cc = ("N" if self.n else "-") + ("Z" if self.z else "-") + \
             ("P" if self.p else "-")
        return f"{pc:04X}: {w:04X}  {txt.split(';')[0].strip():<26} {cc}  {regs}"


def crear_simulador(datos, **kw):
    """Elige la clase según la cabecera del binario ya leído."""
    clase = (SimuladorLC3Clasico if datos[:4] == isa_lc3.MAGIC
             else SimuladorLC3Exp)
    sim = clase(**kw)
    sim.cargar_bytes(datos)
    return sim


def _entero(s):
    return int(s, 0)


def _parsear_regs(texto):
    """'R0=5,R1=0x180' -> {0: 5, 1: 384}"""
    regs = {}
    for par in re.split(r"[,\s]+", texto.strip()):
        if not par:
            continue
        nombre, _, valor = par.partition("=")
        m = re.fullmatch(r"[Rr]([0-7])", nombre)
        if not m or not valor:
            raise ValueError(f"registro mal escrito: '{par}' (use R0=5)")
        regs[int(m.group(1))] = int(valor, 0) & 0xFFFF
    return regs


def simular_archivo(ruta, entrada="", max_instrucciones=5_000_000,
                    pila=isa.PILA_INICIAL, regs=None, eco=False,
                    stdin_interactivo=False, perfil=False):
    """Carga y ejecuta un .bin/.hex. Devuelve el simulador ya ejecutado; si
    no se pudo cargar, lanza ErrorSimulador/OSError."""
    sim = crear_simulador(SimuladorLC3Exp._leer_archivo(ruta), entrada=entrada,
                          eco=eco, max_instrucciones=max_instrucciones,
                          pila_inicial=pila,
                          stdin_interactivo=stdin_interactivo)
    sim.perfilar = perfil
    for r, v in (regs or {}).items():
        sim.registros[r] = v & 0xFFFF
    if perfil:
        try:
            sim.cargar_simbolos(re.sub(r"\.(bin|hex)$", "", ruta,
                                       flags=re.I) + ".sym")
        except OSError:
            pass
    sim.run()
    return sim


def clasificar(sim):
    """OK | ENTRADA | LIMITE | EXCEPCION"""
    if sim.motivo == "HALT":
        return "OK"
    err = sim.error or ""
    if "se acabó la entrada" in err:
        return "ENTRADA"
    if "límite de" in err:
        return "LIMITE"
    return "EXCEPCION"


def _main_carpeta(a, entrada):
    import os
    if not os.path.isdir(a.carpeta):
        print(f"No existe la carpeta: {a.carpeta}", file=sys.stderr)
        return 1
    dir_bins = os.path.join(a.carpeta, "bin") if os.path.isdir(os.path.join(a.carpeta, "bin")) else a.carpeta
    bins = sorted(f for f in os.listdir(dir_bins)
                  if f.lower().endswith(".bin"))
    if not bins:
        print(f"No hay .bin en {a.carpeta}", file=sys.stderr)
        return 1
    regs = _parsear_regs(a.regs) if a.regs else {}
    cuenta = Counter()
    print(f"{'programa':<34} {'estado':<10} {'instr':>9}  detalle")
    for f in bins:
        ruta = os.path.join(dir_bins, f)
        try:
            sim = simular_archivo(ruta, entrada, a.max, a.pila, regs)
        except (ErrorSimulador, OSError) as e:
            cuenta["CARGA"] += 1
            print(f"{f:<34} {'CARGA':<10} {'-':>9}  {e}")
            continue
        est = clasificar(sim)
        cuenta[est] += 1
        det = sim.error if sim.error else (
            "salida: " + repr("".join(sim.salida)[:40]) if sim.salida else "")
        print(f"{f:<34} {est:<10} {sim.instrucciones:>9}  {det}")
    print("\nResumen: " + ", ".join(f"{k}={v}" for k, v in cuenta.items()))
    return 0 if set(cuenta) == {"OK"} else 1


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Simulador funcional de la ISA LC-3 expandida")
    ap.add_argument("programa", nargs="?",
                    help="archivo .bin o .hex del ensamblador")
    ap.add_argument("--carpeta", metavar="DIR",
                    help="modo lote: simula cada .bin de la carpeta")
    ap.add_argument("--regs", default=None,
                    help="registros iniciales, p. ej. R0=5,R1=0x180")
    ap.add_argument("--traza", action="store_true")
    ap.add_argument("--entrada", default=None)
    ap.add_argument("--max", type=int, default=5_000_000)
    ap.add_argument("--pila", type=_entero, default=isa.PILA_INICIAL)
    ap.add_argument("--volcar", action="append", default=[],
                    help="DIR:CANT palabras, p. ej. 0x3100:4")
    ap.add_argument("--perfil", action="store_true")
    ap.add_argument("--permitir-sqr", action="store_true")
    ap.add_argument("--silencioso", action="store_true")
    a = ap.parse_args(argv)
    if a.permitir_sqr:
        isa.CONFIG["sqr"] = True
    entrada = ""
    if a.entrada is not None:
        entrada = a.entrada.encode().decode("unicode_escape")
    if a.carpeta:
        return _main_carpeta(a, entrada)
    if not a.programa:
        ap.error("indique un .bin o use --carpeta DIR")
    regs_ini = {}
    if a.regs:
        try:
            regs_ini = _parsear_regs(a.regs)
        except ValueError as e:
            ap.error(str(e))
    try:
        sim = crear_simulador(SimuladorLC3Exp._leer_archivo(a.programa),
                              entrada=entrada, eco=not a.silencioso,
                              max_instrucciones=a.max, pila_inicial=a.pila,
                              stdin_interactivo=a.entrada is None)
        sim.perfilar = a.perfil
        for r, v in regs_ini.items():
            sim.registros[r] = v
    except (ErrorSimulador, OSError) as e:
        print(f"No se pudo cargar el programa: {e}", file=sys.stderr)
        return 1
    if a.perfil:
        try:
            sim.cargar_simbolos(re.sub(r"\.(bin|hex)$", "", a.programa,
                                       flags=re.I) + ".sym")
        except OSError:
            pass
    volcados = []
    for v in a.volcar:
        d, _, c = v.partition(":")
        volcados.append((_entero(d), _entero(c or "1")))
    sim.run(traza=a.traza)
    print(sim.reporte(volcados, a.perfil))
    return 0 if sim.motivo == "HALT" else 1


if __name__ == "__main__":
    sys.exit(main())
