import os
import re
import sys


class ModuloASM:
    """Módulo .asm independiente con tabla de símbolos local (arquitectura Ernie-Core)."""

    def __init__(self, ruta, es_principal=False):
        self.ruta = ruta
        self.es_principal = es_principal
        nombre_base = os.path.splitext(os.path.basename(ruta))[0]
        if '-' in nombre_base:
            raise ValueError(
                f"Nombre de archivo/módulo inválido '{nombre_base}': "
                "el carácter '-' está reservado exclusivamente para .EXTERNAL MODULO-ETIQUETA"
            )
        self.nombre = nombre_base.upper()
        self.tabla_simbolos = {}      # etiqueta (case-sensitive) -> direccion (int)
        self.externos = set()         # conjunto de tuplas (MODULO_UPPER, etiqueta)
        self.lista_instrucciones = [] # lista de (addr, texto_instruccion)
        self.lineas_datos = []        # lista de (addr_inicio, partes, linea)
        self.labels_stringz = set()   # etiquetas que apuntan a un .STRINGZ
        self.addr_inicio = 0
        self.addr_fin = 0


class Ensamblador:
    # Opcodes cuyo primer operando es un registro de DESTINO (DR).
    # Se usan en modo --strict para detectar inicialización explícita de R6.
    DEST_OPS = frozenset({
        'ADD', 'AND', 'NOT', 'LDI', 'LD', 'LEA', 'LDR', 'LDBL', 'LDBH',
        'LDW', 'MUL', 'MULH', 'DIV', 'LSL', 'LSR', 'ASR',
    })

    def __init__(self, ruta_entrada, ruta_salida, modulos_extra=None, strict=False):
        self.ruta_entrada = ruta_entrada
        self.ruta_salida = ruta_salida
        self.rutas_modulos = [ruta_entrada] + list(modulos_extra or [])
        self.strict = bool(strict)

        self.pc = 0x0000
        self.origen = 0x0000
        self.modulos = []
        self.tabla_simbolos = {}        # tabla del módulo principal (compatibilidad)
        self.tabla_simbolos_global = {} # (MODULO_UPPER, etiqueta) -> direccion
        self.externos = []
        self.lista_instrucciones = []
        self.memoria_binaria = bytearray()

        self.opcodes = {
            'BR': '00000', 'ADD': '00001', 'LD': '00010', 'ST': '00011',
            'JSR': '00100', 'AND': '00101', 'LDR': '00110', 'STR': '00111',
            'JSRR': '00100', 'RTI': '01000', 'NOT': '01001', 'LDI': '01010', 'STI': '01011',
            'JMP': '01100', 'RET': '01100', 'LEA': '01110', 'TRAP': '01111',
            'LDBL': '10000', 'LDBH': '10001', 'LDW': '10010', 'STBL': '10011',
            'STBH': '10100', 'STW': '10101', 'MUL': '10110', 'MULH': '10111',
            'DIV': '11000', 'LSL': '11001', 'LSR': '11010', 'ASR': '11011',
        }

        # Pseudo-instrucciones TRAP sin operandos (case-insensitive).
        # Se expanden a: [15:11]=01111 | [10:8]=000 | [7:0]=trapvect8
        self.pseudo_trap = {
            'GETC': 0x20, 'OUT': 0x21, 'PUTS': 0x22,
            'IN': 0x23, 'PUTSP': 0x24, 'HALT': 0x25,
        }

    def alinear_pc_par(self):
        if self.pc % 2 != 0:
            self.pc += 1
            return True
        return False

    def parse_num(self, s):
        s = s.strip()
        if not s:
            raise ValueError('número vacío')
        if s.startswith('#'):
            return int(s[1:], 10)
        if s.startswith('-#'):
            return -int(s[2:], 10)
        if s.startswith('x') or s.startswith('X'):
            return int(s[1:], 16)
        if s.startswith('-x') or s.startswith('-X'):
            return -int(s[2:], 16)
        return int(s, 0)

    def reg(self, s):
        s = s.strip().upper()
        if not s.startswith('R') or not s[1:].isdigit():
            raise ValueError('registro invalido: ' + s)
        r = int(s[1:])
        if r < 0 or r > 7:
            raise ValueError('registro fuera de rango R0-R7: ' + s)
        return r

    def etiqueta_sin_colon(self, token):
        up = token.upper()
        if up in self.opcodes:
            return False
        if up in self.pseudo_trap:
            return False
        if up.startswith('BR') and all(c in 'NZP' for c in up[2:]):
            return False
        if up.startswith('.'):
            return False
        if up.startswith('R') and up[1:].isdigit():
            return False
        if up in ('NZP', 'N', 'Z', 'P', 'NP', 'NZ', 'ZP'):
            return False
        try:
            self.parse_num(token)
            return False
        except Exception:
            pass
        return True

    def _parsear_external(self, token):
        """Valida formato MODULO-ETIQUETA (exactamente un '-') y normaliza módulo."""
        if token.count('-') != 1:
            raise ValueError(
                f"Formato .EXTERNAL inválido '{token}': debe ser MODULO-ETIQUETA con exactamente un '-'"
            )
        mod, etiq = token.split('-', 1)
        if not mod or not etiq:
            raise ValueError(
                f"Formato .EXTERNAL inválido '{token}': módulo y etiqueta deben ser no vacíos"
            )
        return mod.upper(), etiq

    def _validar_etiqueta_local(self, etiqueta):
        if '-' in etiqueta:
            raise ValueError(
                f"Nombre de etiqueta inválido '{etiqueta}': "
                "el carácter '-' está reservado exclusivamente para .EXTERNAL MODULO-ETIQUETA"
            )

    def _avanzar_pc_directiva(self, modulo, partes, linea):
        cmd = partes[0].upper()
        if cmd == '.ORIG':
            val = self.parse_num(partes[1])
            if val % 2 != 0:
                raise ValueError('direccion .ORIG impar')
            if modulo.es_principal:
                self.pc = val
                self.origen = val
                modulo.addr_inicio = val
            # En módulos secundarios, .ORIG se ignora (regla M4)
        elif cmd in ('.FILL', '.BLKW'):
            self.alinear_pc_par()
            if cmd == '.BLKW':
                n = self.parse_num(partes[1])
                if n < 0:
                    raise ValueError(f".BLKW requiere cantidad no negativa: {n}")
                self.pc += 2 * n
            else:
                self.pc += 2
        elif cmd == '.BYTE':
            self.pc += 1
        elif cmd == '.STRINGZ':
            m = re.search(r'"(.*?)"', linea)
            if not m:
                # §8: .STRINGZ exige comillas balanceadas en una sola línea.
                raise ValueError(
                    f".STRINGZ mal formada (comillas no balanceadas o multilínea): '{linea}'"
                )
            # .STRINGZ almacena 1 carácter por palabra de 16 bits
            # (2 bytes por carácter) + palabra nula final.
            self.alinear_pc_par()
            self.pc += 2 * (len(m.group(1)) + 1)
        elif cmd == '.EXTERNAL':
            tokens = [t for t in re.split(r'[,\s]+', linea[len(partes[0]):].strip()) if t]
            if not tokens:
                raise ValueError('.EXTERNAL requiere al menos un símbolo MODULO-ETIQUETA')
            for t in tokens:
                mod_ext, etiq_ext = self._parsear_external(t)
                modulo.externos.add((mod_ext, etiq_ext))
                self.externos.append(f"{mod_ext}-{etiq_ext}")

    def _pasada_uno_modulo(self, modulo):
        if modulo.es_principal:
            self.pc = 0x0000
            self.origen = 0x0000
            modulo.addr_inicio = 0x0000
        else:
            self.alinear_pc_par()
            modulo.addr_inicio = self.pc

        with open(modulo.ruta, 'r', encoding='utf-8') as archivo:
            for linea_raw in archivo:
                linea = linea_raw.split(';')[0].strip()
                if not linea:
                    continue
                if linea.upper().startswith('.END'):
                    continue
                if linea.startswith('.'):
                    partes = re.split(r'\s+', linea)
                    cmd = partes[0].upper()
                    if cmd in ('.FILL', '.BLKW'):
                        self.alinear_pc_par()
                    addr_antes = self.pc
                    self._avanzar_pc_directiva(modulo, partes, linea)
                    if cmd in ('.FILL', '.BLKW', '.BYTE', '.STRINGZ'):
                        modulo.lineas_datos.append((addr_antes, partes, linea))
                    continue

                etiqueta = None
                resto = linea
                if ':' in linea:
                    etiqueta, resto = linea.split(':', 1)
                    etiqueta = etiqueta.strip()
                    resto = resto.strip()
                else:
                    partes = re.split(r'\s+', linea)
                    if partes and self.etiqueta_sin_colon(partes[0]):
                        etiqueta = partes[0]
                        resto = ' '.join(partes[1:]).strip()

                if etiqueta:
                    self._validar_etiqueta_local(etiqueta)
                    if etiqueta in modulo.tabla_simbolos:
                        raise ValueError(
                            f"Etiqueta duplicada '{etiqueta}' en módulo '{modulo.nombre}'"
                        )
                    # Alinear PC antes de registrar etiqueta si precede a palabra/instrucción
                    if resto:
                        if resto.startswith('.'):
                            cmd_resto = re.split(r'\s+', resto)[0].upper()
                            if cmd_resto in ('.FILL', '.BLKW', '.STRINGZ'):
                                self.alinear_pc_par()
                        else:
                            self.alinear_pc_par()
                    modulo.tabla_simbolos[etiqueta] = self.pc
                    if resto.startswith('.'):
                        cmd_resto2 = re.split(r'\s+', resto)[0].upper()
                        if cmd_resto2 == '.STRINGZ':
                            modulo.labels_stringz.add(etiqueta)

                if not resto:
                    continue

                if resto.startswith('.'):
                    partes = re.split(r'\s+', resto)
                    cmd = partes[0].upper()
                    if cmd in ('.FILL', '.BLKW'):
                        self.alinear_pc_par()
                    addr_antes = self.pc
                    self._avanzar_pc_directiva(modulo, partes, resto)
                    if cmd in ('.FILL', '.BLKW', '.BYTE', '.STRINGZ'):
                        modulo.lineas_datos.append((addr_antes, partes, resto))
                    continue

                # Instrucción normal (alineación par PC+2)
                self.alinear_pc_par()
                addr = self.pc
                modulo.lista_instrucciones.append((addr, resto))
                self.lista_instrucciones.append((addr, resto))
                self.pc += 2

        self.alinear_pc_par()
        modulo.addr_fin = self.pc

    def pasada_uno(self):
        self.modulos = []
        self.tabla_simbolos_global = {}
        self.lista_instrucciones = []
        self.externos = []

        for idx, ruta in enumerate(self.rutas_modulos):
            modulo = ModuloASM(ruta, es_principal=(idx == 0))
            self._pasada_uno_modulo(modulo)
            self.modulos.append(modulo)
            for etiq, addr in modulo.tabla_simbolos.items():
                self.tabla_simbolos_global[(modulo.nombre, etiq)] = addr

        if self.modulos:
            self.tabla_simbolos = self.modulos[0].tabla_simbolos

    def _resolver_simbolo(self, modulo, token):
        """
        Resuelve un símbolo local o externo MODULO-ETIQUETA.
        Retorna (direccion, es_externo).
        """
        if '-' in token and not token.startswith('-'):
            mod_ref, etiq_ref = self._parsear_external(token)
            clave = (mod_ref, etiq_ref)
            if clave not in modulo.externos:
                raise ValueError(
                    f"Error de enlace: símbolo externo '{token}' no declarado con .EXTERNAL "
                    f"en módulo '{modulo.nombre}'"
                )
            if clave not in self.tabla_simbolos_global:
                raise ValueError(
                    f"Error de enlace: símbolo externo '{token}' no definido en ningún módulo enlazado"
                )
            return self.tabla_simbolos_global[clave], True

        if token in modulo.tabla_simbolos:
            return modulo.tabla_simbolos[token], False

        raise ValueError(
            f"Etiqueta '{token}' no definida en módulo '{modulo.nombre}'"
        )

    def nzp_bits(self, s):
        s = s.upper()
        n = '1' if 'N' in s else '0'
        z = '1' if 'Z' in s else '0'
        p = '1' if 'P' in s else '0'
        return n + z + p

    def codificar(self, addr, instr, modulo=None):
        if modulo is None:
            modulo = self.modulos[0]

        partes = re.split(r'[,\s]+', instr.strip())
        cmd = partes[0].upper()

        # Pseudo-instrucciones TRAP sin operandos (case-insensitive):
        # GETC/OUT/PUTS/IN/PUTSP/HALT -> 01111 000 <trapvect8>
        if cmd in self.pseudo_trap:
            if len(partes) > 1:
                raise ValueError(f'{cmd} no recibe operandos')
            trapvect = self.pseudo_trap[cmd]
            return self.opcodes['TRAP'] + '000' + format(trapvect & 0xFF, '08b')

        es_br = (cmd == 'BR') or (cmd.startswith('BR') and all(c in 'NZP' for c in cmd[2:]))
        if not es_br and cmd not in self.opcodes:
            raise ValueError('instruccion desconocida: ' + cmd)
        op = self.opcodes['BR'] if es_br else self.opcodes[cmd]

        # --strict (d): prohíbe inicialización explícita de R6 en módulos de usuario.
        if self.strict and (not es_br) and cmd in self.DEST_OPS:
            if len(partes) >= 2 and self.reg(partes[1]) == 6:
                raise ValueError(
                    f"Inicialización explícita de R6 prohibida en modo --strict "
                    f"('{cmd}' con destino R6). R6 lo inicializa el simulador (P3S v3)."
                )

        if es_br:
            nzp_suf = cmd[2:]
            idx = 1
            while idx < len(partes) and all(c in 'NZP' for c in partes[idx].upper()):
                nzp_suf += partes[idx].upper()
                idx += 1
            if nzp_suf == '':
                if self.strict:
                    # --strict (a): BR sin sufijo es error.
                    raise ValueError(
                        "BR sin sufijo de condición ('BR label') prohibido en modo --strict; "
                        "use BRnzp/BRn/BRz/BRp/BRnp/BRnz o BRnzp para salto incondicional."
                    )
                # §8/§10: sin --strict, 'BR' sin sufijo = salto incondicional nzp=111.
                nzp_suf = 'NZP'
            nzp = self.nzp_bits(nzp_suf)
            if idx >= len(partes):
                raise ValueError('BR requiere etiqueta destino')
            target_tok = partes[idx]
            target, es_ext = self._resolver_simbolo(modulo, target_tok)
            if target % 2 != 0:
                raise ValueError(f"salto a direccion impar causaria exception fatal: 0x{target:04X}")
            off = (target - (addr + 2)) >> 1
            if off < -128 or off > 127:
                if es_ext:
                    raise ValueError(
                        f"Error de enlace: '{target_tok}' en BR fuera de rango PCoffset8 "
                        f"[-128, +127] palabras (offset={off}). "
                        f"Sugerencia: use '.FILL {target_tok}' + 'JSRR' para salto indirecto."
                    )
                raise ValueError(f'offset de salto BR fuera de rango [-128, +127]: {off}')
            return op + nzp + format(off & 0xFF, '08b')

        if cmd in ('ADD', 'AND', 'MUL', 'MULH', 'DIV'):
            dr = self.reg(partes[1])
            sr1 = self.reg(partes[2])
            third = partes[3]
            if third.upper().startswith('R'):
                mode = '0'
                src = '0' + format(self.reg(third), '03b')
            else:
                val = self.parse_num(third)
                if val < -8 or val > 15:
                    raise ValueError(f'valor inmediato fuera de rango para {cmd}: {val}')
                if self.strict and 8 <= val <= 15:
                    # --strict (b): rechaza imm4 en 8..15 (se sign-extend a negativo).
                    raise ValueError(
                        f"--strict: inmediato imm4={val} en rango 8..15 para {cmd} "
                        f"(fuera de [-8, +7]); se interpretaría como negativo por sign-extend."
                    )
                mode = '1'
                src = format(val & 0xF, '04b')
            return op + format(dr, '03b') + format(sr1, '03b') + mode + src

        if cmd == 'NOT':
            dr = self.reg(partes[1])
            sr = self.reg(partes[2])
            return op + format(dr, '03b') + format(sr, '03b') + '11111'

        if cmd in ('LSL', 'LSR', 'ASR'):
            dr = self.reg(partes[1])
            sr = self.reg(partes[2])
            val = self.parse_num(partes[3])
            if val < 0 or val > 15:
                raise ValueError(f'inmediato fuera de rango [0, 15] para {cmd}: {val}')
            if self.strict and 8 <= val <= 15:
                # --strict (b): rechaza imm4 en 8..15 (fuera de [-8, +7]).
                raise ValueError(
                    f"--strict: inmediato imm4={val} en rango 8..15 para {cmd} "
                    f"(fuera de [-8, +7])."
                )
            return op + format(dr, '03b') + format(sr, '03b') + '0' + format(val & 0xF, '04b')

        if cmd in ('LDBL', 'LDBH', 'STBL', 'STBH', 'LDW', 'STW', 'LDR', 'STR'):
            dr = self.reg(partes[1])
            base = self.reg(partes[2])
            off_val = self.parse_num(partes[3])
            if off_val < -16 or off_val > 15:
                raise ValueError(f'offset5 fuera de rango [-16, +15] para {cmd}: {off_val}')
            return op + format(dr, '03b') + format(base, '03b') + format(off_val & 0x1F, '05b')

        if cmd in ('LD', 'ST', 'LEA', 'LDI', 'STI'):
            dr = self.reg(partes[1])
            target_tok = partes[2]
            target, es_ext = self._resolver_simbolo(modulo, target_tok)
            if target % 2 != 0:
                raise ValueError(
                    f"acceso palabra/PC-relativo a direccion impar en {cmd}: 0x{target:04X}"
                )
            off = (target - (addr + 2)) >> 1
            if off < -128 or off > 127:
                if es_ext:
                    raise ValueError(
                        f"Error de enlace: '{target_tok}' en {cmd} fuera de rango PCoffset8 "
                        f"[-128, +127] palabras (offset={off}). "
                        f"Sugerencia: use '.FILL {target_tok}' + 'JSRR' (o carga indirecta)."
                    )
                raise ValueError(f'offset8 fuera de rango [-128, +127] para {cmd}: {off}')
            return op + format(dr, '03b') + format(off & 0xFF, '08b')

        if cmd in ('JMP', 'RET'):
            base = 7 if cmd == 'RET' else self.reg(partes[1])
            return op + format(base, '03b') + '00000000'

        if cmd == 'JSR':
            if partes[1].upper().startswith('R') and partes[1][1:].isdigit():
                base = self.reg(partes[1])
                return '00100' + '0' + format(base, '03b') + '0000000'
            target_tok = partes[1]
            target, es_ext = self._resolver_simbolo(modulo, target_tok)
            if target % 2 != 0:
                raise ValueError(f"salto a direccion impar causaria exception fatal: 0x{target:04X}")
            off = (target - (addr + 2)) >> 1
            if off < -512 or off > 511:
                if es_ext:
                    raise ValueError(
                        f"Error de enlace: '{target_tok}' en JSR fuera de rango PCoffset10 "
                        f"[-512, +511] palabras (offset={off}). "
                        f"Sugerencia: use '.FILL {target_tok}' + 'JSRR' para salto indirecto."
                    )
                raise ValueError(f'offset10 fuera de rango [-512, +511] para JSR: {off}')
            return '00100' + '1' + format(off & 0x3FF, '010b')

        if cmd == 'JSRR':
            base = self.reg(partes[1])
            return '00100' + '0' + format(base, '03b') + '0000000'

        if cmd == 'RTI':
            return op + '00000000000'

        if cmd == 'TRAP':
            v = self.parse_num(partes[1])
            if v < 0 or v > 0xFF:
                raise ValueError(f'vector de trampa fuera de rango 8 bits: {v}')
            return op + '000' + format(v & 0xFF, '08b')

        raise ValueError('no codificado: ' + cmd)

    def _bytes_directiva_modulo(self, modulo, partes, linea, addr_inicio):
        entradas = {}
        cmd = partes[0].upper()
        pc = addr_inicio
        if cmd == '.FILL':
            tok = partes[1]
            es_num_prefijo = tok.startswith(('#', 'x', 'X', '-#', '-x', '-X'))
            val = None
            es_numero = False
            if es_num_prefijo:
                val = self.parse_num(tok)
                es_numero = True
            else:
                try:
                    val = self.parse_num(tok)
                    es_numero = True
                except ValueError:
                    es_numero = False

            if not es_numero:
                if ('-' in tok and not tok.startswith('-')) or tok in modulo.tabla_simbolos:
                    val, _ = self._resolver_simbolo(modulo, tok)
                else:
                    raise ValueError(f"Operando inválido en .FILL: '{tok}'")
            entradas[pc] = (val & 0xFFFF).to_bytes(2, 'big')
            return entradas, pc + 2
        if cmd == '.BLKW':
            n = self.parse_num(partes[1])
            entradas[pc] = b'\x00\x00' * n
            return entradas, pc + 2 * n
        if cmd == '.BYTE':
            val = self.parse_num(partes[1])
            entradas[pc] = bytes([val & 0xFF])
            return entradas, pc + 1
        if cmd == '.STRINGZ':
            m = re.search(r'"(.*?)"', linea)
            s = m.group(1) if m else ''
            b = b''.join((ord(c) & 0xFF).to_bytes(2, 'big') for c in s) + b'\x00\x00'
            entradas[pc] = b
            pc += len(b)
            if pc % 2 != 0:
                entradas[pc] = b'\x00'
                pc += 1
            return entradas, pc
        return entradas, pc

    def _validar_strict_punteros(self, modulo):
        """
        --strict (e): detecta incrementos +1 sobre punteros a palabras/.STRINGZ.

        Emplea dos heurísticas complementarias:

        1. Linaje desde 'LEA Rd, LABEL' (LABEL en modulo.labels_stringz):
           propaga la marca de puntero a través de copias de registro
           ('ADD Rd, Rs, #0' y 'AND Rd, Rs, Rs') e invalida la marca cuando
           'Rd' se sobreescribe con otra instrucción destino (DEST_OPS).

        2. Patrón de recorrido de string/palabra recibido por parámetro:
           dentro de un mismo bloque lineal (estado reiniciado ante cualquier
           etiqueta intermedia o instrucción de salto BR/JMP/JSR/JSRR/RET), si
           un registro 'BaseR' se desreferencia con 'LDR Rd, BaseR, #0' (o
           'LDW Rd, BaseR, #0') y posteriormente se incrementa con
           'ADD BaseR, BaseR, #1' (o 'ADD Rd2, BaseR, #1'), se emite error:
           en una arquitectura byte-addressable los punteros a palabra/`.STRINGZ`
           avanzan +2.

        Un contador aritmético común que no provenga de 'LEA' sobre `.STRINGZ` ni
        haya sido desreferenciado con 'LDR/LDW' en el bloque lineal sigue pasando
        sin error (evita falsos positivos).
        """
        if not self.strict:
            return

        def es_salto(c):
            if c in ('JMP', 'JSR', 'JSRR', 'RET'):
                return True
            return c == 'BR' or (c.startswith('BR') and all(ch in 'NZP' for ch in c[2:]))

        # Direcciones con etiqueta asociada: marcan inicio de un bloque lineal.
        addrs_etiqueta = set(modulo.tabla_simbolos.values())

        reg_string = {}  # reg -> True si su valor es dirección de un .STRINGZ (linaje LEA)
        reg_deref = {}   # reg -> True si fue desreferenciado con LDR/LDW #0 en el bloque
        prev_salto = False

        for addr, instr in modulo.lista_instrucciones:
            partes = re.split(r'[,\s]+', instr.strip())
            if not partes:
                continue
            cmd = partes[0].upper()

            # Reinicio del estado de punteros por parámetro ante etiqueta
            # intermedia o instrucción de salto (nuevo bloque lineal).
            if prev_salto or addr in addrs_etiqueta:
                reg_deref.clear()

            # --- LEA: linaje de punteros a .STRINGZ ---
            if cmd == 'LEA' and len(partes) >= 3:
                rd = self.reg(partes[1])
                if partes[2] in modulo.labels_stringz:
                    reg_string[rd] = True
                else:
                    reg_string.pop(rd, None)
                reg_deref.pop(rd, None)
                prev_salto = False
                continue

            # --- ADD: copia (#0), incremento (+1) o invalidación de Rd ---
            if cmd == 'ADD' and len(partes) >= 4:
                rd = self.reg(partes[1])
                rs = self.reg(partes[2])
                third = partes[3]
                es_reg = third.upper().startswith('R') and third[1:].isdigit()
                if es_reg:
                    # ADD Rd, Rs, Rt -> Rd sobreescrito (no es copia ni +1).
                    reg_string.pop(rd, None)
                    reg_deref.pop(rd, None)
                else:
                    try:
                        val = self.parse_num(third)
                    except ValueError:
                        val = None
                    if val == 0:
                        # ADD Rd, Rs, #0 -> copia de Rs en Rd: propagar marcas.
                        if reg_string.get(rs):
                            reg_string[rd] = True
                        else:
                            reg_string.pop(rd, None)
                        if reg_deref.get(rs):
                            reg_deref[rd] = True
                        else:
                            reg_deref.pop(rd, None)
                    else:
                        if val == 1 and (reg_string.get(rs) or reg_deref.get(rs)):
                            origen = '.STRINGZ (LEA)' if reg_string.get(rs) else 'LDR/LDW #0'
                            raise ValueError(
                                f"--strict: incremento +1 sobre puntero a palabra/.STRINGZ "
                                f"(ADD R{rd}, R{rs}, #1; origen {origen}) en módulo "
                                f"'{modulo.nombre}'. En byte-addressable los punteros a "
                                f"palabra avanzan +2."
                            )
                        # Cualquier otro inmediato sobreescribe Rd.
                        reg_string.pop(rd, None)
                        reg_deref.pop(rd, None)
                prev_salto = False
                continue

            # --- AND: copia (Rd, Rs, Rs) o invalidación de Rd ---
            if cmd == 'AND' and len(partes) >= 4:
                rd = self.reg(partes[1])
                rs = self.reg(partes[2])
                third = partes[3]
                es_reg = third.upper().startswith('R') and third[1:].isdigit()
                if es_reg and self.reg(third) == rs:
                    # AND Rd, Rs, Rs -> copia de Rs en Rd: propagar marcas.
                    if reg_string.get(rs):
                        reg_string[rd] = True
                    else:
                        reg_string.pop(rd, None)
                    if reg_deref.get(rs):
                        reg_deref[rd] = True
                    else:
                        reg_deref.pop(rd, None)
                else:
                    reg_string.pop(rd, None)
                    reg_deref.pop(rd, None)
                prev_salto = False
                continue

            # --- LDR/LDW: marcar BaseR desreferenciado (offset #0) e invalidar Rd ---
            if cmd in ('LDR', 'LDW') and len(partes) >= 4:
                rd = self.reg(partes[1])
                base = self.reg(partes[2])
                try:
                    off = self.parse_num(partes[3])
                except ValueError:
                    off = None
                if off == 0 and base != rd:
                    # BaseR se usa como puntero a palabra/.STRINGZ en este bloque.
                    reg_deref[base] = True
                reg_string.pop(rd, None)
                reg_deref.pop(rd, None)
                prev_salto = False
                continue

            # --- Resto de instrucciones con destino: invalidar Rd ---
            if cmd in self.DEST_OPS and len(partes) >= 2:
                try:
                    rd = self.reg(partes[1])
                except ValueError:
                    rd = None
                if rd is not None:
                    reg_string.pop(rd, None)
                    reg_deref.pop(rd, None)

            prev_salto = es_salto(cmd)

    def pasada_dos(self):
        instrucciones = {}
        datos = {}

        for modulo in self.modulos:
            # Validar que todo .EXTERNAL declarado exista en la tabla global si se referencia,
            # o al menos verificar integridad al resolver.
            self._validar_strict_punteros(modulo)
            for addr, instr in modulo.lista_instrucciones:
                instrucciones[addr] = self.codificar(addr, instr, modulo=modulo)

            for addr_d, partes, linea in modulo.lineas_datos:
                nuevas, _ = self._bytes_directiva_modulo(modulo, partes, linea, addr_d)
                datos.update(nuevas)

        direcciones = [self.origen] + list(instrucciones.keys()) + list(datos.keys())
        maxaddr = max(
            [self.origen + 2, self.pc]
            + [a + 2 for a in instrucciones.keys()]
            + [a + len(b) for a, b in datos.items()]
        )
        img = bytearray(maxaddr - self.origen)

        for a, code in instrucciones.items():
            val = int(code, 2)
            off = a - self.origen
            img[off:off + 2] = val.to_bytes(2, 'big')

        for a, b in datos.items():
            off = a - self.origen
            img[off:off + len(b)] = b

        out = bytearray()
        out += (self.origen & 0xFFFF).to_bytes(2, 'big')
        out += img
        self.memoria_binaria = out

    def guardar_binario(self):
        with open(self.ruta_salida, 'wb') as archivo:
            archivo.write(self.memoria_binaria)

    def imprimir_mapa(self, out=None):
        """
        Volca por 'out' (stdout por defecto) el mapa de módulos enlazados
        (Bloque 1) y la tabla de símbolos globales/locales (Bloque 2).

        No escribe ningún archivo en disco (ni .map ni .bin): la salida es
        exclusivamente de consola. Debe invocarse sólo tras un ensamblado y
        enlazado exitoso (pasada_uno + pasada_dos) para no volcar un mapa
        incompleto.
        """
        if out is None:
            out = sys.stdout

        # --- Bloque 1: Mapa de Módulos Enlazados ---
        print("=" * 72, file=out)
        print("MAPA DE MÓDULOS ENLAZADOS", file=out)
        print("=" * 72, file=out)
        print("%-30s %-14s %-14s %-16s" % (
            "MÓDULO", "INICIO (HEX)", "FIN (HEX)", "TAMAÑO (BYTES)"), file=out)
        total_bytes = 0
        for modulo in self.modulos:
            nombre_archivo = os.path.basename(modulo.ruta)
            tam = modulo.addr_fin - modulo.addr_inicio
            total_bytes += tam
            print("%-30s 0x%04X       0x%04X       0x%04X" % (
                nombre_archivo,
                modulo.addr_inicio & 0xFFFF,
                modulo.addr_fin & 0xFFFF,
                tam & 0xFFFF), file=out)
        print("TOTAL: %d bytes ocupados" % total_bytes, file=out)
        print(file=out)

        # --- Bloque 2: Tabla de Símbolos Globales y Locales ---
        print("=" * 72, file=out)
        print("TABLA DE SÍMBOLOS GLOBALES Y LOCALES", file=out)
        print("=" * 72, file=out)
        print("%-16s %-28s %-26s %-8s" % (
            "DIRECCIÓN (0xXXXX)", "ETIQUETA / SÍMBOLO",
            "MÓDULO ORIGEN", "ALCANCE"), file=out)

        # Un símbolo es GLOBAL si algún módulo lo referencia vía .EXTERNAL
        # (MODULO-ETIQUETA resuelto); en caso contrario es LOCAL.
        externos_globales = set()
        for modulo in self.modulos:
            for par in modulo.externos:
                externos_globales.add(par)

        filas = []
        for modulo in self.modulos:
            nombre_archivo = os.path.basename(modulo.ruta)
            for etiq, addr in modulo.tabla_simbolos.items():
                alcance = "GLOBAL" if (modulo.nombre, etiq) in externos_globales else "LOCAL"
                filas.append((addr & 0xFFFF, etiq, nombre_archivo, alcance))
        filas.sort(key=lambda f: f[0])
        for addr, etiq, nombre_archivo, alcance in filas:
            print("0x%04X           %-28s %-26s %-8s" % (
                addr, etiq, nombre_archivo, alcance), file=out)
        if not filas:
            print("(sin símbolos definidos)", file=out)
        print(file=out)

    def ejecutar(self):
        self.pasada_uno()
        self.pasada_dos()
        self.guardar_binario()


if __name__ == "__main__":
    args = sys.argv[1:]
    strict = False
    syntax = False
    map_mode = False
    if '--strict' in args:
        strict = True
        args = [a for a in args if a != '--strict']
    if '--syntax' in args:
        syntax = True
        args = [a for a in args if a != '--syntax']
    if '--map' in args:
        map_mode = True
        args = [a for a in args if a != '--map']

    sufijo = " (strict)" if strict else ""

    if syntax:
        # Modo --syntax: validación en seco (dry-run). No exige <salida.bin>
        # ni escribe ningún archivo binario en disco. Ejecuta pasada_uno() y
        # pasada_dos() y reporta código de salida 0 (OK) o distinto de 0 (error).
        if len(args) < 1:
            print("Uso: python ernie_assembler.py --syntax [--strict] <main.asm> [modulos_extra.asm ...]")
            sys.exit(2)
        ensamblador = Ensamblador(args[0], None, args[1:], strict=strict)
        try:
            ensamblador.pasada_uno()
            ensamblador.pasada_dos()
        except (ValueError, OSError) as e:
            print(f"Error de sintaxis: {e}", file=sys.stderr)
            sys.exit(1)
        print("Sintaxis OK" + sufijo)
        sys.exit(0)

    if map_mode:
        # Modo --map: ensambla/enlaza y volca el mapa por consola (stdout).
        # No escribe archivo .map. Sólo genera .bin si se provee <salida.bin>.
        # Firma: --map [--strict] <main.asm> [salida.bin] [modulos_extra.asm ...]
        if len(args) < 1:
            print(
                "Uso: python ernie_assembler.py --map [--strict] <main.asm> "
                "[salida.bin] [modulos_extra.asm ...]",
                file=sys.stderr,
            )
            sys.exit(2)
        # Desambiguación de <salida.bin> opcional: se reconoce únicamente si el
        # segundo argumento termina en '.bin'; si no, todos los args[1:] son
        # módulos .asm (no se genera binario).
        if len(args) >= 2 and args[1].lower().endswith('.bin'):
            ruta_salida = args[1]
            modulos_extra = args[2:]
        else:
            ruta_salida = None
            modulos_extra = args[1:]
        ensamblador = Ensamblador(args[0], ruta_salida, modulos_extra, strict=strict)
        try:
            ensamblador.pasada_uno()
            ensamblador.pasada_dos()
        except (ValueError, OSError) as e:
            # Error de ensamblado/enlace/strict: error en stderr, sin volcar mapa.
            print(f"Error de ensamblado: {e}", file=sys.stderr)
            sys.exit(1)
        # Sólo tras éxito total se volca el mapa completo (stdout).
        ensamblador.imprimir_mapa()
        if ruta_salida is not None:
            ensamblador.guardar_binario()
            print(
                "Ensamblado OK" + sufijo + " (binario generado: %s)" % ruta_salida,
                file=sys.stderr,
            )
        sys.exit(0)

    if len(args) < 2:
        print("Uso: python ernie_assembler.py [--strict] <main.asm> <salida.bin> [modulos_extra ...] (arquitectura Ernie-Core)")
    else:
        ensamblador = Ensamblador(args[0], args[1], args[2:], strict=strict)
        ensamblador.ejecutar()
        print("Ensamblado OK" + sufijo)
