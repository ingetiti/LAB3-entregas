#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Simulador funcional de la ISA-G11 (nucleo de ejecucion).

Uso:
    python simulador.py programa.bin|.hex|.dec [opciones]

Recibe el benchmark ya ensamblado (binario, hexadecimal o decimal; el primer
dato es la direccion de origen), lo ejecuta y muestra la salida del programa,
la cantidad de instrucciones ejecutadas y el uso de memoria.

Opciones utiles:
    --max-instr N      tope de instrucciones (por defecto 50.000.000)
    --entrada "texto"  datos para GETC/IN (tambien --entrada-archivo F)
    --traza            imprime cada instruccion ejecutada
    --regs             muestra los registros al terminar
    --volcado DIR N    muestra N palabras de memoria desde DIR al terminar
    --json F           guarda las estadisticas en un archivo JSON
"""
import argparse
import json
import os
import sys

from isa import (OPNAME, cond_cumple, formato_instr, sext, TRAP_GETC, TRAP_OUT,
                 TRAP_PUTS, TRAP_IN, TRAP_HALT, TRAP_NAMES)


class ExcepcionMaquina(Exception):
    pass


CLASES = {
    'aritmetico-logicas': {'ADD', 'SUB', 'AND', 'OR', 'ADDI', 'ANDI', 'SHR', 'SHI',
                           'MOVI', 'MOVHI', 'CMP', 'CMPI', 'UN'},
    'memoria': {'LDW', 'LDBL', 'LDBH', 'STW', 'STBL', 'STBH', 'LD', 'ST', 'LEA', 'LDWX', 'STK'},
    'control': {'BR', 'BRL', 'JSR', 'JR', 'TRAP'},
    'nop': {'NOP'},
}


class Maquina:
    def __init__(self, entrada=b'', max_instr=50_000_000, traza=False, salida=None):
        self.mem = bytearray(65536)
        self.tocado = bytearray(65536)     # 1 = buscado como instruccion, 2 = leido, 4 = escrito
        self.R = [0] * 8
        self.pc = 0
        self.N = self.Z = self.V = self.C = False
        self.total = 0
        self.por_op = {n: 0 for n in OPNAME.values()}
        self.traps = {}
        self.puts_chars = 0                # caracteres emitidos por PUTS (para estimar el costo del SO)
        self.entrada = bytearray(entrada)
        self.eof_lecturas = 0
        self.usar_stdin = True             # False: nunca bloquear esperando el teclado (lo usa la interfaz grafica)
        self.max_instr = max_instr
        self.traza = traza
        self.out = salida if salida is not None else sys.stdout.buffer
        self.salida_bytes = 0
        self.detenida = False
        self.motivo = ''
        self.origen = 0
        self.tam_imagen = 0
        self.r6_min = 0x10000
        self.saltos = [0, 0]               # [tomados, no tomados] de BR condicionales
        self.perfil = None                 # opcional: dict pc -> veces ejecutada
        self.pcs = None                    # opcional: lista de PC en orden de ejecucion

    # ------------------------------------------------------------ carga
    def cargar(self, origen, datos):
        if origen + len(datos) > 65536:
            raise ExcepcionMaquina('la imagen no entra en la memoria de 64 KiB')
        self.mem[origen:origen + len(datos)] = datos
        self.origen = origen
        self.tam_imagen = len(datos)
        self.pc = origen

    # ------------------------------------------------------------ flags
    def nz(self, r):
        self.N = bool(r & 0x8000)
        self.Z = r == 0

    def sumar(self, a, b, cin=0):
        s = a + b + cin
        r = s & 0xFFFF
        self.C = s > 0xFFFF
        self.V = bool((~(a ^ b)) & (a ^ r) & 0x8000)
        self.nz(r)
        return r

    # ------------------------------------------------------------ memoria
    def leer_w(self, a):
        if a & 1:
            raise ExcepcionMaquina(f'acceso a palabra en direccion impar x{a:04X}')
        self.tocado[a] |= 2
        self.tocado[a + 1] |= 2
        return (self.mem[a] << 8) | self.mem[a + 1]

    def escribir_w(self, a, v):
        if a & 1:
            raise ExcepcionMaquina(f'acceso a palabra en direccion impar x{a:04X}')
        self.tocado[a] |= 4
        self.tocado[a + 1] |= 4
        self.mem[a] = (v >> 8) & 255
        self.mem[a + 1] = v & 255

    def leer_b(self, a):
        self.tocado[a] |= 2
        return self.mem[a]

    def escribir_b(self, a, v):
        self.tocado[a] |= 4
        self.mem[a] = v & 255

    # ------------------------------------------------------------ E/S
    def escribir_salida(self, b):
        self.out.write(bytes(b))
        self.salida_bytes += len(b)

    def leer_caracter(self):
        if self.entrada:
            return self.entrada.pop(0)
        if self.usar_stdin and self.eof_lecturas == 0 and sys.stdin is not None and sys.stdin.isatty():
            try:
                linea = sys.stdin.readline().encode('utf-8')
                if linea:
                    self.entrada.extend(linea)
                    return self.entrada.pop(0)
            except Exception:
                pass
        self.eof_lecturas += 1
        return 0x0A

    # ------------------------------------------------------------ TRAP
    def trap(self, v):
        self.traps[v] = self.traps.get(v, 0) + 1
        R = self.R
        if v == TRAP_HALT:
            self.detenida = True
            self.motivo = 'HALT'
        elif v == TRAP_OUT:
            self.escribir_salida([R[0] & 255])
        elif v == TRAP_PUTS:
            a = R[0]
            buf = bytearray()
            while True:
                c = self.leer_b(a)
                if c == 0:
                    break
                buf.append(c)
                a = (a + 1) & 0xFFFF
            self.puts_chars += len(buf)
            self.escribir_salida(buf)
        elif v == TRAP_GETC:
            R[0] = self.leer_caracter()
        elif v == TRAP_IN:
            self.escribir_salida(b'Ingrese un caracter: ')
            c = self.leer_caracter()
            self.escribir_salida([c])
            R[0] = c
        else:
            raise ExcepcionMaquina(f'TRAP desconocido x{v:02X}')

    # ------------------------------------------------------------ ejecucion
    def paso(self):
        pc = self.pc
        if pc & 1:
            raise ExcepcionMaquina(f'salto a direccion impar x{pc:04X}')
        self.tocado[pc] |= 1
        self.tocado[pc + 1] |= 1
        w = (self.mem[pc] << 8) | self.mem[pc + 1]
        op = w >> 11
        R = self.R
        dr = (w >> 8) & 7
        s1 = (w >> 5) & 7
        s2 = (w >> 2) & 7
        f = w & 3
        nxt = (pc + 2) & 0xFFFF
        if op not in OPNAME:
            raise ExcepcionMaquina(f'instruccion reservada (opcode {op}) en x{pc:04X}')
        self.total += 1
        self.por_op[OPNAME[op]] += 1
        if self.perfil is not None:
            self.perfil[pc] = self.perfil.get(pc, 0) + 1
        if self.pcs is not None:
            self.pcs.append(pc)
        if self.traza:
            sys.stderr.write(f'{pc:04X}: {w:04X}  {formato_instr(w)}\n')

        if op == 0:                                   # NOP
            pass
        elif op == 1:                                 # ADD / ADC
            R[dr] = self.sumar(R[s1], R[s2], int(self.C) if f == 1 else 0)
        elif op == 2:                                 # SUB / SBC
            R[dr] = self.sumar(R[s1], (~R[s2]) & 0xFFFF, int(self.C) if f == 1 else 1)
        elif op == 3:                                 # AND / BIC
            r = R[s1] & (R[s2] if f == 0 else ~R[s2] & 0xFFFF)
            R[dr] = r
            self.nz(r)
            self.V = False
        elif op == 4:                                 # OR / XOR
            r = (R[s1] | R[s2]) if f == 0 else (R[s1] ^ R[s2])
            R[dr] = r
            self.nz(r)
            self.V = False
        elif op == 5:                                 # PUSH / POP
            if w & 0x80:
                R[dr] = self.leer_w(R[6])
                R[6] = (R[6] + 2) & 0xFFFF
            else:
                R[6] = (R[6] - 2) & 0xFFFF
                self.escribir_w(R[6], R[dr])
                if R[6] < self.r6_min:
                    self.r6_min = R[6]
        elif op == 6 or op == 11:                     # desplazamientos
            if op == 6:
                tipo, amt = f, R[s2] & 15
            else:
                tipo, amt = (w >> 3) & 3, (w & 7) + 1
            self.desplazar(dr, R[s1], tipo, amt)
        elif op == 9:                                 # ADDI
            R[dr] = self.sumar(R[s1], sext(w, 5) & 0xFFFF)
        elif op == 10:                                # ANDI
            r = R[s1] & (sext(w, 5) & 0xFFFF)
            R[dr] = r
            self.nz(r)
            self.V = False
        elif op == 12:                                # MOVI
            r = sext(w, 8) & 0xFFFF
            R[dr] = r
            self.nz(r)
            self.V = False
        elif op == 13:                                # MOVHI
            r = ((w & 255) << 8) | (R[dr] & 255)
            R[dr] = r
            self.nz(r)
            self.V = False
        elif op == 14:                                # CMP
            self.sumar(R[s1], (~R[s2]) & 0xFFFF, 1)
        elif op == 15:                                # CMPI
            self.sumar(R[dr], (~(sext(w, 8) & 0xFFFF)) & 0xFFFF, 1)
        elif op == 16:                                # UN
            self.unaria(dr, R[s1], w & 31)
        elif op in (17, 18, 19):                      # LDW / LDBL / LDBH
            if op == 17:
                a = (R[s1] + sext(w, 5) * 2) & 0xFFFF
                r = self.leer_w(a)
            elif op == 18:
                a = (R[s1] + sext(w, 5)) & 0xFFFF
                r = sext(self.leer_b(a), 8) & 0xFFFF
            else:
                a = (R[s1] + sext(w, 5)) & 0xFFFF
                r = (self.leer_b(a) << 8) | (R[dr] & 255)
            R[dr] = r
            self.nz(r)
            self.V = False
        elif op in (20, 21, 22):                      # STW / STBL / STBH
            if op == 20:
                self.escribir_w((R[s1] + sext(w, 5) * 2) & 0xFFFF, R[dr])
            elif op == 21:
                self.escribir_b((R[s1] + sext(w, 5)) & 0xFFFF, R[dr] & 255)
            else:
                self.escribir_b((R[s1] + sext(w, 5)) & 0xFFFF, R[dr] >> 8)
        elif op in (23, 24, 25):                      # LD / ST / LEA (PC-relativos)
            ea = (((pc + 2) & ~3) + 4 * sext(w, 8)) & 0xFFFF
            if op == 23:
                r = self.leer_w(ea)
                R[dr] = r
                self.nz(r)
                self.V = False
            elif op == 24:
                self.escribir_w(ea, R[dr])
            else:
                R[dr] = ea
        elif op == 26:                                # BR condicional
            if cond_cumple((w >> 7) & 15, self.N, self.Z, self.V, self.C):
                nxt = (pc + 2 + 2 * sext(w, 7)) & 0xFFFF
                self.saltos[0] += 1
            else:
                self.saltos[1] += 1
        elif op == 27:                                # BRL
            nxt = (pc + 2 + 2 * sext(w, 11)) & 0xFFFF
        elif op == 28:                                # JSR
            R[7] = nxt
            nxt = (pc + 2 + 2 * sext(w, 11)) & 0xFFFF
        elif op == 29:                                # JMP / JSRR / RET
            destino = R[dr]
            if w & 0x80:
                R[7] = nxt
            nxt = destino
        elif op == 30:                                # TRAP
            self.trap(w & 255)
        elif op == 31:                                # LDX / STX / LDBX / STBX
            idx = R[s2]
            idx = idx - 0x10000 if idx & 0x8000 else idx
            if f < 2:
                a = (R[s1] + 2 * idx) & 0xFFFF
            else:
                a = (R[s1] + idx) & 0xFFFF
            if f == 0:
                r = self.leer_w(a)
                R[dr] = r
                self.nz(r)
                self.V = False
            elif f == 1:
                self.escribir_w(a, R[dr])
            elif f == 2:
                r = sext(self.leer_b(a), 8) & 0xFFFF
                R[dr] = r
                self.nz(r)
                self.V = False
            else:
                self.escribir_b(a, R[dr] & 255)
        self.pc = nxt

    def desplazar(self, dr, a, tipo, amt):
        R = self.R
        if amt == 0:
            r = a
        elif tipo == 0:
            r = (a << amt) & 0xFFFF
            self.C = bool((a >> (16 - amt)) & 1)
        elif tipo == 1:
            r = a >> amt
            self.C = bool((a >> (amt - 1)) & 1)
        elif tipo == 2:
            sa = a - 0x10000 if a & 0x8000 else a
            r = (sa >> amt) & 0xFFFF
            self.C = bool((sa >> (amt - 1)) & 1)
        else:
            r = ((a << amt) | (a >> (16 - amt))) & 0xFFFF
            self.C = bool(r & 1)
        R[dr] = r
        self.nz(r)
        self.V = False

    def unaria(self, dr, a, sub):
        R = self.R
        self.V = False
        if sub == 0:
            r = a
        elif sub == 1:
            r = ~a & 0xFFFF
        elif sub == 2:
            r = (-a) & 0xFFFF
            self.V = a == 0x8000
            self.C = a == 0
        elif sub == 3:
            r = sext(a, 8) & 0xFFFF
        elif sub == 4:
            r = a & 255
        elif sub == 5:
            r = ((a & 255) << 8) | (a >> 8)
        elif sub == 6:
            r = (-a) & 0xFFFF if a & 0x8000 else a
            self.V = a == 0x8000
        elif sub == 7:
            r = 16 - a.bit_length()
        else:
            raise ExcepcionMaquina(f'operacion UN desconocida: {sub}')
        R[dr] = r
        self.nz(r)

    def correr(self):
        try:
            while not self.detenida:
                if self.total >= self.max_instr:
                    self.detenida = True
                    self.motivo = f'limite de {self.max_instr} instrucciones'
                    break
                self.paso()
        except ExcepcionMaquina as e:
            self.detenida = True
            self.motivo = f'EXCEPCION en PC=x{self.pc:04X}: {e}'
        except KeyboardInterrupt:
            self.detenida = True
            self.motivo = 'interrumpido por el usuario'
        try:
            self.out.flush()
        except Exception:
            pass

    # ------------------------------------------------------------ estadisticas
    def estadisticas(self):
        t = self.tocado
        buscados = sum(1 for x in t if x & 1)
        leidos = sum(1 for x in t if (x & 2) and not (x & 1))
        escritos = sum(1 for x in t if x & 4)
        fin = self.origen + self.tam_imagen
        fuera = sum(1 for i, x in enumerate(t) if (x & 4) and not (self.origen <= i < fin))
        tocados = [i for i, x in enumerate(t) if x]
        clases = {}
        for c, ops in CLASES.items():
            clases[c] = sum(self.por_op[o] for o in ops)
        st = {
            'motivo_parada': self.motivo,
            'instrucciones_ejecutadas': self.total,
            'por_clase': clases,
            'por_instruccion': {k: v for k, v in sorted(self.por_op.items(), key=lambda x: -x[1]) if v},
            'traps': {TRAP_NAMES.get(k, f'x{k:02X}'): v for k, v in self.traps.items()},
            'puts_caracteres': self.puts_chars,
            'saltos_condicionales': {'tomados': self.saltos[0], 'no_tomados': self.saltos[1]},
            'memoria': {
                'origen': f'x{self.origen:04X}',
                'imagen_bytes': self.tam_imagen,
                'imagen_palabras': self.tam_imagen // 2,
                'bytes_de_instrucciones_ejecutados_distintos': buscados,
                'bytes_de_datos_leidos_distintos': leidos,
                'bytes_escritos_distintos': escritos,
                'bytes_escritos_fuera_de_la_imagen': fuera,
                'direccion_minima_tocada': f'x{tocados[0]:04X}' if tocados else None,
                'direccion_maxima_tocada': f'x{tocados[-1]:04X}' if tocados else None,
                'R6_minimo': f'x{self.r6_min:04X}' if self.r6_min != 0x10000 else None,
            },
            'bytes_de_salida': self.salida_bytes,
            'lecturas_de_entrada_agotada': self.eof_lecturas,
        }
        return st


def imprimir_resumen(m, st, f=sys.stderr):
    print('\n=========== Resumen de la ejecucion ===========', file=f)
    print(f'Parada: {st["motivo_parada"]}', file=f)
    print(f'Instrucciones ejecutadas: {st["instrucciones_ejecutadas"]:,}'.replace(',', '.'), file=f)
    for c, n in st['por_clase'].items():
        if n:
            print(f'  {c:20} {n:>12,}'.replace(',', '.'), file=f)
    mem = st['memoria']
    print('Memoria:', file=f)
    print(f'  imagen cargada en {mem["origen"]}: {mem["imagen_bytes"]} bytes ({mem["imagen_palabras"]} palabras)', file=f)
    print(f'  bytes de codigo realmente ejecutados: {mem["bytes_de_instrucciones_ejecutados_distintos"]}', file=f)
    print(f'  bytes de datos leidos: {mem["bytes_de_datos_leidos_distintos"]} | escritos: {mem["bytes_escritos_distintos"]}'
          f' (fuera de la imagen: {mem["bytes_escritos_fuera_de_la_imagen"]})', file=f)
    print(f'  direcciones tocadas: {mem["direccion_minima_tocada"]} .. {mem["direccion_maxima_tocada"]}', file=f)
    if st['traps']:
        print('TRAPs:', ', '.join(f'{k}={v}' for k, v in st['traps'].items()), file=f)
    if st['lecturas_de_entrada_agotada']:
        print(f'Aviso: {st["lecturas_de_entrada_agotada"]} lectura(s) con la entrada agotada (se devolvio salto de linea)', file=f)


def leer_imagen(ruta):
    """Devuelve (origen, bytes) desde .bin / .hex / .dec."""
    with open(ruta, 'rb') as f:
        crudo = f.read()
    ext = os.path.splitext(ruta)[1].lower()
    if ext == '.bin':
        if len(crudo) < 2:
            raise ExcepcionMaquina('archivo .bin vacio')
        return (crudo[0] << 8) | crudo[1], crudo[2:]
    texto = crudo.decode('utf-8', errors='replace')
    vals = []
    for linea in texto.splitlines():
        linea = linea.split(';')[0].split('//')[0].strip()
        if not linea:
            continue
        for tok in linea.replace(',', ' ').split():
            t = tok.lower()
            if ext == '.hex':
                t = t[2:] if t.startswith('0x') else t.lstrip('x')
                vals.append(int(t, 16))
            else:
                vals.append(int(t, 10))
    if not vals:
        raise ExcepcionMaquina('archivo sin datos')
    origen = vals[0]
    datos = bytearray()
    for v in vals[1:]:
        datos += bytes([(v >> 8) & 255, v & 255])
    return origen, bytes(datos)


def main(argv=None):
    ap = argparse.ArgumentParser(description='Simulador funcional de la ISA-G11')
    ap.add_argument('programa', help='.bin, .hex o .dec (primer dato = origen)')
    ap.add_argument('--max-instr', type=int, default=50_000_000)
    ap.add_argument('--entrada', default='', help='texto para GETC/IN')
    ap.add_argument('--entrada-archivo')
    ap.add_argument('--traza', action='store_true')
    ap.add_argument('--regs', action='store_true')
    ap.add_argument('--volcado', nargs=2, metavar=('DIR', 'N'))
    ap.add_argument('--json', help='guarda las estadisticas en este archivo')
    ap.add_argument('--silencio', action='store_true', help='no muestra el resumen')
    ap.add_argument('--so', action='store_true',
                    help='agrega al resumen la estimacion de instrucciones del SO (modelo calibrado con la catedra)')
    ap.add_argument('--perfil', help='guarda cuantas veces se ejecuto cada direccion (JSON)')
    a = ap.parse_args(argv)
    entrada = a.entrada.encode('utf-8').decode('unicode_escape').encode('latin-1', 'replace') if a.entrada else b''
    if a.entrada_archivo:
        with open(a.entrada_archivo, 'rb') as f:
            entrada += f.read()
    try:
        origen, datos = leer_imagen(a.programa)
        m = Maquina(entrada=entrada, max_instr=a.max_instr, traza=a.traza)
        if a.perfil:
            m.perfil = {}
        m.cargar(origen, datos)
    except (ExcepcionMaquina, OSError, ValueError) as e:
        print('ERROR:', e, file=sys.stderr)
        return 1
    m.correr()
    st = m.estadisticas()
    if not a.silencio:
        imprimir_resumen(m, st)
    if a.so:
        import costo_so
        r = costo_so.calcular(st, costo_so.COEF_CATEDRA)
        pt = lambda n: f'{n:,}'.replace(',', '.')
        print(f'Instrucciones de usuario: {pt(r["usuario"])} | SO (estimado): {pt(r["so"])} | '
              f'total: {pt(r["total"])}', file=sys.stderr)
    if a.regs:
        print('Registros:', ' '.join(f'R{i}=x{v:04X}' for i, v in enumerate(m.R)),
              f'| PC=x{m.pc:04X} N={int(m.N)} Z={int(m.Z)} V={int(m.V)} C={int(m.C)}', file=sys.stderr)
    if a.volcado:
        d, n = int(a.volcado[0], 0), int(a.volcado[1], 0)
        for i in range(n):
            ad = (d + 2 * i) & 0xFFFF
            print(f'x{ad:04X}: x{(m.mem[ad] << 8) | m.mem[(ad + 1) & 0xFFFF]:04X}', file=sys.stderr)
    if a.perfil:
        with open(a.perfil, 'w', encoding='utf-8') as f:
            json.dump({str(k): v for k, v in m.perfil.items()}, f)
    if a.json:
        with open(a.json, 'w', encoding='utf-8') as f:
            json.dump(st, f, indent=2, ensure_ascii=False)
    return 0 if st['motivo_parada'] == 'HALT' else 2


if __name__ == '__main__':
    sys.exit(main())
