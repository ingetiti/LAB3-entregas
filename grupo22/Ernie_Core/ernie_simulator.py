"""
ernie_simulator.py - Ernie-Core Simulador Funcional LC-3 (5 bits Opcode)
Laboratorio 3C - Basado en ISA_SPEC.md y SIM_SPEC.md.

Características principales:
- Memoria de 64 KB (0x0000 - 0xFFFF) direccionable por byte.
- Carga de archivos .bin con cabecera .ORIG (2 bytes big-endian) + imagen de memoria.
- Ciclo fetch-decode-execute de 16 bits con PC += 2 por instrucción.
- Mapa de opcodes de 5 bits [15:11] (32 opcodes).
- Inicialización automática de pila R6 = STACK_BASE (0xFFFE) al cargar el .bin.
- Escalado offset5 << 1 OBLIGATORIO en accesos de PALABRA (LDR/STR/LDW/STW);
  accesos de BYTE (LDBL/LDBH/STBL/STBH) sin escalar (offset5 directo en bytes).
- Excepción fatal (halt + excepciones_fatales++) en saltos o accesos de palabra a
  dirección impar, división por cero, TRAP reservado u opcodes reservados/inválidos.
- Telemetría integrada multi-módulo (6 métricas).
"""

import sys
import os
import re


def _grupo_desde_nombre(nombre):
    """
    Deriva el grupo (G<N>) parseando el nombre/etiqueta de una subrutina.
    Reconoce prefijos 'G<N>_' o '_G<N>' al inicio (insensible a mayusculas).
    Devuelve 'G<N>' en mayusculas o None si no se identifica.
    """
    if not nombre:
        return None
    m = re.match(r'(?i)^G(\d+)_', nombre) or re.match(r'(?i)^_G(\d+)', nombre)
    return "G%s" % m.group(1) if m else None


MASK_16 = 0xFFFF
MASK_8 = 0xFF
SIGN_BIT_16 = 0x8000
MEMORY_SIZE = 65536
STACK_BASE = 0xFFFE  # Dirección par más alta disponible bajo espacio reservado

# Flags de condición (N, Z, P)
FL_POS = 0b001  # P (> 0)
FL_ZRO = 0b010  # Z (== 0)
FL_NEG = 0b100  # N (< 0)

# Opcodes de 5 bits [15:11] según ISA_SPEC.md
OP_BR    = 0b00000  # 0x00
OP_ADD   = 0b00001  # 0x01
OP_LD    = 0b00010  # 0x02
OP_ST    = 0b00011  # 0x03
OP_JSR   = 0b00100  # 0x04 (JSR / JSRR)
OP_AND   = 0b00101  # 0x05
OP_LDR   = 0b00110  # 0x06
OP_STR   = 0b00111  # 0x07
OP_RTI   = 0b01000  # 0x08
OP_NOT   = 0b01001  # 0x09
OP_LDI   = 0b01010  # 0x0A
OP_STI   = 0b01011  # 0x0B
OP_JMP   = 0b01100  # 0x0C (JMP / RET)
OP_RESV1 = 0b01101  # 0x0D (RESERVED)
OP_LEA   = 0b01110  # 0x0E
OP_TRAP  = 0b01111  # 0x0F
OP_LDBL  = 0b10000  # 0x10
OP_LDBH  = 0b10001  # 0x11
OP_LDW   = 0b10010  # 0x12
OP_STBL  = 0b10011  # 0x13
OP_STBH  = 0b10100  # 0x14
OP_STW   = 0b10101  # 0x15
OP_MUL   = 0b10110  # 0x16
OP_MULH  = 0b10111  # 0x17
OP_DIV   = 0b11000  # 0x18
OP_LSL   = 0b11001  # 0x19
OP_LSR   = 0b11010  # 0x1A
OP_ASR   = 0b11011  # 0x1B
# 0b11100 - 0b11111: RESERVED

# Vectores TRAP (7 bits: 0x00 - 0x7F)
TRAP_GETC  = 0x20
TRAP_OUT   = 0x21
TRAP_PUTS  = 0x22
TRAP_IN    = 0x23
TRAP_PUTSP = 0x24
TRAP_HALT  = 0x25


def sign_extend(val: int, bits: int) -> int:
    """Extiende el bit de signo de un entero de 'bits' bits a entero Python con signo."""
    mask = (1 << bits) - 1
    val &= mask
    if (val >> (bits - 1)) & 1:
        val -= (1 << bits)
    return val


def to_int16(val: int) -> int:
    """Convierte entero de 16 bits sin signo a entero con signo (-32768..32767)."""
    val &= MASK_16
    if val & SIGN_BIT_16:
        return val - 0x10000
    return val


class Simulador:
    """
    Simulador funcional para la arquitectura LC-3 Extendida (5 bits opcode,
    direccionamiento por byte, PC+2).
    """

    def __init__(self, ruta_bin: str = None, input_buffer=None):
        # Buffer de entrada opcional (lista/cola de caracteres) para GETC/IN no interactivos.
        # Se normaliza a lista de caracteres y se preserva al cargar .bin / imágenes.
        self.input_buffer = self._normalizar_buffer(input_buffer)

        # Memoria de 64 KB direccionable por byte
        self.memoria = bytearray(MEMORY_SIZE)

        # 8 registros de propósito general (R0 - R7) de 16 bits
        self.regs = [0] * 8
        self.regs[6] = STACK_BASE

        # Registros de control y estado
        self.origen = 0x0000
        self.pc = 0x0000
        self.halted = False
        self.ultimo_error = None

        # Flags de condición
        self.flag_n = 0
        self.flag_z = 1
        self.flag_p = 0
        self.flag_v = 0
        self.flag_c = 0

        # Control de ocupación máxima de memoria
        self._max_addr_usada = 0

        # Contadores de telemetría (6 métricas integradas)
        self.instrucciones_ejecutadas = 0
        self.desglose_por_familia = {
            "ARITH": 0,
            "SHIFTER": 0,
            "MEMORY": 0,
            "CONTROL": 0,
            "BRANCH": 0,
        }
        self.ciclos_estimados = 0
        self.accesos_memoria = 0
        self.bytes_ocupados = 0
        self.excepciones_fatales = 0

        # --- Estado de perfilado (modo --profile) ---
        # profile_activo: False por defecto; el runner / __main__ lo activan.
        # No se altera en reiniciar_estado para respetar la elección del usuario.
        self.profile_activo = False
        self._init_perfilado()

        # --- Estado de auditoria ABI (modo --check-abi) ---
        # check_abi_activo: False por defecto; el runner / __main__ lo activan.
        # No se altera en reiniciar_estado para respetar la eleccion del usuario
        # (igual que profile_activo). Las estructuras de auditoria se reinician
        # en _init_perfilado.
        self.check_abi_activo = False

        # Mapa de símbolos opcional (modo --map): direccion -> "MODULO::ETIQUETA".
        # Lo rellena el runner / __main__ para enriquecer trazas de excepciones
        # fatales con el nombre del módulo/etiqueta más cercano al PC.
        # No se reinicia en reiniciar_estado (persiste como contexto de carga).
        self.simbolos_mapa = {}

        if ruta_bin is not None:
            self.cargar_bin(ruta_bin)

    def _init_perfilado(self):
        """Inicializa/reinicia las estructuras de perfilado por subrutina y R6."""
        # Pila de marcos activos (call stack de perfilado).
        # Cada marco: {"dir": int, "instrucciones": int, "ciclos": int}
        self._profile_stack = []
        # Estadísticas acumuladas por dirección de entrada de subrutina.
        # dir -> {"llamadas": int, "instrucciones": int, "ciclos": int}
        self._profile_stats = {}
        # Marco retirado (RET) pendiente de finalizar tras la atribución de la
        # instrucción RET (para que el RET se contabilice dentro de la subrutina).
        self._profile_ultimo_ret = None
        # Rastreo de profundidad de pila: mínimo valor alcanzado por R6.
        self.min_R6 = STACK_BASE
        # Mapa opcional direccion -> etiqueta/nombre (lo rellena el runner).
        self.simbolos_perfil = {}
        # Cantidad de marcos abiertos cerrados de forma segura al finalizar.
        self._profile_marcos_cerrados = 0

        # --- Estructuras de auditoria ABI (modo --check-abi) ---
        # Pila de marcos de auditoria. Cada marco es un dict con:
        #   {direccion_subrutina, pc_llamador, r2_entrada, r3_entrada,
        #    r4_entrada, r5_entrada, r6_entrada, r7_entrada}
        self._abi_stack = []
        # Lista de violaciones ABI detectadas (dicts por discrepancia).
        self._abi_violaciones = []
        # Total de llamadas JSR/JSRR inspeccionadas.
        self._abi_llamadas = 0

    def reiniciar_estado(self):
        """Reinicia registros, memoria, flags y telemetría."""
        self.memoria = bytearray(MEMORY_SIZE)
        self.regs = [0] * 8
        self.regs[6] = STACK_BASE
        self.origen = 0x0000
        self.pc = 0x0000
        self.halted = False
        self.ultimo_error = None

        self.flag_n = 0
        self.flag_z = 1
        self.flag_p = 0
        self.flag_v = 0
        self.flag_c = 0

        self._max_addr_usada = 0

        self.instrucciones_ejecutadas = 0
        self.desglose_por_familia = {
            "ARITH": 0,
            "SHIFTER": 0,
            "MEMORY": 0,
            "CONTROL": 0,
            "BRANCH": 0,
        }
        self.ciclos_estimados = 0
        self.accesos_memoria = 0
        self.bytes_ocupados = 0
        self.excepciones_fatales = 0

        # Reinicio de estructuras de perfilado (se conserva profile_activo).
        self._init_perfilado()

    @staticmethod
    def _normalizar_buffer(input_buffer):
        """Normaliza el buffer de entrada a una lista de caracteres individuales."""
        if input_buffer is None:
            return []
        if isinstance(input_buffer, str):
            return list(input_buffer)
        return list(input_buffer)

    def _leer_caracter(self) -> str:
        """Obtiene el siguiente carácter del buffer o, si se agotó, de stdin.
        Retorna un string de longitud 1 ('\\x00' ante EOF de stdin)."""
        if self.input_buffer:
            return self.input_buffer.pop(0)
        ch = sys.stdin.read(1)
        if ch == '':
            return '\x00'
        return ch

    def cargar_bin(self, ruta_bin: str):
        """
        Carga un archivo .bin generado por el ensamblador P5E.
        Formato:
        - Primeros 2 bytes: dirección .ORIG en big-endian.
        - Resto: imagen de memoria desde .ORIG hacia adelante.
        """
        self.reiniciar_estado()
        with open(ruta_bin, "rb") as f:
            data = f.read()

        if len(data) < 2:
            raise ValueError("Archivo .bin inválido: tamaño menor a 2 bytes (falta cabecera .ORIG).")

        self.origen = (data[0] << 8) | data[1]
        if self.origen % 2 != 0:
            self._disparar_excepcion_fatal(f"Dirección .ORIG impar: 0x{self.origen:04X}")
            return

        imagen = data[2:]
        if self.origen + len(imagen) > MEMORY_SIZE:
            raise ValueError("La imagen binaria excede el espacio de memoria de 64 KB.")

        self.memoria[self.origen : self.origen + len(imagen)] = imagen
        self.regs[6] = STACK_BASE
        self.pc = self.origen
        self._max_addr_usada = self.origen + len(imagen)
        self.bytes_ocupados = len(imagen)

    def cargar_imagen(self, origen: int, imagen: bytes):
        """Carga directamente en memoria una imagen de bytes a partir de 'origen'."""
        self.reiniciar_estado()
        if origen % 2 != 0:
            self._disparar_excepcion_fatal(f"Dirección .ORIG impar: 0x{origen:04X}")
            return
        if origen + len(imagen) > MEMORY_SIZE:
            raise ValueError("La imagen excede el espacio de memoria de 64 KB.")

        self.origen = origen & MASK_16
        self.memoria[self.origen : self.origen + len(imagen)] = imagen
        self.pc = self.origen
        self._max_addr_usada = self.origen + len(imagen)
        self.bytes_ocupados = len(imagen)

    def _anotacion_simbolo(self, pc: int) -> str:
        """
        Devuelve una anotación de símbolo para 'pc' usando self.simbolos_mapa
        (direccion -> "MODULO::ETIQUETA"), o '' si no hay mapa o no aplica.

        Formato: ' (MODULO::ETIQUETA +0xNN)' donde NN es el desplazamiento en
        bytes desde la etiqueta más cercana por debajo o igual a 'pc'.
        """
        mapa = getattr(self, "simbolos_mapa", None)
        if not mapa:
            return ""
        pc &= MASK_16
        mejor_addr = None
        mejor_nombre = None
        for addr, nombre in mapa.items():
            addr &= MASK_16
            if addr <= pc and (mejor_addr is None or addr > mejor_addr):
                mejor_addr = addr
                mejor_nombre = nombre
        if mejor_addr is None:
            return ""
        return " (%s +0x%02X)" % (mejor_nombre, (pc - mejor_addr) & 0xFFFF)

    def _disparar_excepcion_fatal(self, mensaje: str):
        """Registra una excepción fatal y detiene la CPU.

        Si hay un mapa de símbolos cargado (simbolos_mapa), enriquece el
        mensaje con la etiqueta/módulo más cercano al PC actual, sin alterar
        la interfaz existente ni las métricas de telemetría.
        """
        self.excepciones_fatales += 1
        self.halted = True
        self.ultimo_error = mensaje + self._anotacion_simbolo(self.pc)

    def _actualizar_nzp(self, val16: int):
        """Actualiza los flags N, Z, P según el valor de 16 bits con signo."""
        val16 &= MASK_16
        if val16 == 0:
            self.flag_n = 0
            self.flag_z = 1
            self.flag_p = 0
        elif val16 & SIGN_BIT_16:
            self.flag_n = 1
            self.flag_z = 0
            self.flag_p = 0
        else:
            self.flag_n = 0
            self.flag_z = 0
            self.flag_p = 1

    @property
    def cond_bits(self) -> int:
        """Devuelve máscara de 3 bits (N=4, Z=2, P=1)."""
        return (self.flag_n << 2) | (self.flag_z << 1) | self.flag_p

    def _registrar_ocupacion(self, addr_fin: int):
        """Actualiza el puntero máximo de memoria utilizado y bytes_ocupados."""
        if addr_fin > self._max_addr_usada:
            self._max_addr_usada = addr_fin
            self.bytes_ocupados = max(0, self._max_addr_usada - self.origen)

    def leer_byte(self, addr: int) -> int:
        """Lee un byte de memoria (sin restricción de paridad)."""
        addr &= MASK_16
        self.accesos_memoria += 1
        return self.memoria[addr]

    def escribir_byte(self, addr: int, val: int):
        """Escribe un byte en memoria (sin restricción de paridad)."""
        addr &= MASK_16
        self.accesos_memoria += 1
        self.memoria[addr] = val & MASK_8
        self._registrar_ocupacion(addr + 1)

    def leer_palabra(self, addr: int) -> int:
        """
        Lee una palabra de 16 bits (big-endian) desde 'addr'.
        Excepción fatal si 'addr' es impar.
        """
        addr &= MASK_16
        if addr % 2 != 0:
            self._disparar_excepcion_fatal(
                f"Excepción fatal: lectura de palabra en dirección impar 0x{addr:04X}"
            )
            return 0
        self.accesos_memoria += 1
        hi = self.memoria[addr]
        lo = self.memoria[(addr + 1) & MASK_16]
        return (hi << 8) | lo

    def escribir_palabra(self, addr: int, val: int):
        """
        Escribe una palabra de 16 bits (big-endian) en 'addr'.
        Excepción fatal si 'addr' es impar.
        """
        addr &= MASK_16
        if addr % 2 != 0:
            self._disparar_excepcion_fatal(
                f"Excepción fatal: escritura de palabra en dirección impar 0x{addr:04X}"
            )
            return
        self.accesos_memoria += 1
        val &= MASK_16
        self.memoria[addr] = (val >> 8) & MASK_8
        self.memoria[(addr + 1) & MASK_16] = val & MASK_8
        self._registrar_ocupacion(addr + 2)

    def fetch(self) -> int:
        """
        Ciclo Fetch: lee la instrucción de 16 bits en PC e incrementa PC += 2.
        Excepción fatal si PC es impar.
        """
        if self.pc % 2 != 0:
            self._disparar_excepcion_fatal(
                f"Excepción fatal: PC impar en fetch (0x{self.pc:04X})"
            )
            return 0
        instr = self.leer_palabra(self.pc)
        self.pc = (self.pc + 2) & MASK_16
        return instr

    def _profile_push(self, dir_entrada: int):
        """Apila un nuevo marco de perfilado para la subrutina que se invoca."""
        self._profile_stack.append({
            "dir": dir_entrada & MASK_16,
            "instrucciones": 0,
            "ciclos": 0,
        })

    def _profile_acumular(self, frame: dict):
        """Acumula un marco finalizado en las estadísticas globales por subrutina."""
        if frame is None:
            return
        clave = frame["dir"]
        entrada = self._profile_stats.get(clave)
        if entrada is None:
            entrada = {"llamadas": 0, "instrucciones": 0, "ciclos": 0}
            self._profile_stats[clave] = entrada
        entrada["llamadas"] += 1
        entrada["instrucciones"] += frame["instrucciones"]
        entrada["ciclos"] += frame["ciclos"]

    def _profile_cerrar_abiertos(self):
        """Cierra de forma segura los marcos aún abiertos (HALT/límite/excepción)."""
        while self._profile_stack:
            frame = self._profile_stack.pop()
            self._profile_acumular(frame)
            self._profile_marcos_cerrados += 1

    def _abi_push(self, dir_subrutina: int, pc_llamador: int):
        """Apila un marco de auditoria ABI con la instantanea de registros.

        Captura R2..R5 (callee-saved), R6 (puntero de pila) y R7 (direccion de
        retorno) en el instante de entrar a la subrutina invocada por JSR/JSRR.
        """
        self._abi_stack.append({
            "direccion_subrutina": dir_subrutina & MASK_16,
            "pc_llamador": pc_llamador & MASK_16,
            "r2_entrada": self.regs[2] & MASK_16,
            "r3_entrada": self.regs[3] & MASK_16,
            "r4_entrada": self.regs[4] & MASK_16,
            "r5_entrada": self.regs[5] & MASK_16,
            "r6_entrada": self.regs[6] & MASK_16,
            "r7_entrada": self.regs[7] & MASK_16,
        })
        self._abi_llamadas += 1

    def _abi_verificar_ret(self):
        """Verifica la ABI al ejecutar RET (JMP R7): desapila y compara.

        Compara R2..R5 (callee-saved), R6 (balance de pila) y R7 (direccion de
        retorno) contra la instantanea tomada en la entrada. Cada discrepancia
        se registra en self._abi_violaciones. Si no hay marco que desapilar se
        registra una violacion de desbalance (RET sin llamada).
        """
        if not self._abi_stack:
            # RET sin JSR/JSRR previo -> desbalance de pila.
            self._abi_violaciones.append({
                "direccion_subrutina": None,
                "pc_llamador": (self.pc - 2) & MASK_16,
                "registro": "R7",
                "esperado": None,
                "observado": self.regs[7] & MASK_16,
                "tipo": "RET sin llamada (desbalance de pila)",
            })
            return

        marco = self._abi_stack.pop()
        dir16 = marco["direccion_subrutina"]
        pc_ll = marco["pc_llamador"]

        # Registros callee-saved R2..R5.
        for idx, r in ((2, "R2"), (3, "R3"), (4, "R4"), (5, "R5")):
            esp = marco["r%d_entrada" % idx]
            obs = self.regs[idx] & MASK_16
            if obs != esp:
                self._abi_violaciones.append({
                    "direccion_subrutina": dir16,
                    "pc_llamador": pc_ll,
                    "registro": r,
                    "esperado": esp,
                    "observado": obs,
                    "tipo": "callee-saved modificado",
                })

        # Balance de pila R6.
        esp6 = marco["r6_entrada"]
        obs6 = self.regs[6] & MASK_16
        if obs6 != esp6:
            self._abi_violaciones.append({
                "direccion_subrutina": dir16,
                "pc_llamador": pc_ll,
                "registro": "R6",
                "esperado": esp6,
                "observado": obs6,
                "tipo": "desbalance de pila",
            })

        # Direccion de retorno R7.
        esp7 = marco["r7_entrada"]
        obs7 = self.regs[7] & MASK_16
        if obs7 != esp7:
            self._abi_violaciones.append({
                "direccion_subrutina": dir16,
                "pc_llamador": pc_ll,
                "registro": "R7",
                "esperado": esp7,
                "observado": obs7,
                "tipo": "direccion de retorno corrupta",
            })

    def _abi_nombre(self, dir16):
        """Nombre de subrutina (etiqueta o 0xXXXX) para auditoria ABI."""
        if dir16 is None:
            return "(desconocida)"
        nombre = self.simbolos_perfil.get(dir16 & MASK_16)
        if not nombre:
            nombre = "0x%04X" % (dir16 & MASK_16)
        return nombre

    def _abi_grupo(self, dir16):
        """Grupo (G<N> o '-') para auditoria ABI (cascada mapa -> etiqueta)."""
        if dir16 is None:
            return "-"
        grupo = None
        mapa_grupo = getattr(self, "simbolos_grupo", None)
        if mapa_grupo:
            grupo = mapa_grupo.get(dir16 & MASK_16)
        if not grupo:
            grupo = _grupo_desde_nombre(self.simbolos_perfil.get(dir16 & MASK_16))
        if not grupo:
            grupo = "-"
        return grupo

    def _reporte_abi(self, titulo="CHECK-ABI", out=None):
        """Imprime por 'out' (stdout por defecto) el reporte de auditoria ABI.

        Muestra el total de llamadas inspeccionadas, el resumen de cumplimiento
        y, si hay violaciones, una tabla con subrutina, grupo, PC de llamada,
        registro, valor esperado vs observado y ocurrencias. Si no hay
        violaciones imprime un mensaje limpio. No altera obtener_telemetria().
        """
        if out is None:
            out = sys.stdout
        violaciones = self._abi_violaciones
        total_llamadas = self._abi_llamadas
        total_viol = len(violaciones)

        print("=" * 70, file=out)
        print("ERNIE-CORE ABI CHECK -- %s" % titulo, file=out)
        print("=" * 70, file=out)
        print("Llamadas JSR/JSRR inspeccionadas : %d" % total_llamadas, file=out)
        llamadas_ok = max(0, total_llamadas - total_viol)
        print("Llamadas OK                      : %d" % llamadas_ok, file=out)
        print("Violaciones ABI detectadas       : %d" % total_viol, file=out)
        print(file=out)

        if total_viol == 0:
            print("No se detectaron violaciones ABI "
                  "(R2..R5, R6 y R7 integros en todas las llamadas).", file=out)
            print(file=out)
            return

        print("-" * 70, file=out)
        print("TABLA DE VIOLACIONES ABI", file=out)
        print("-" * 70, file=out)
        print("{:<22} {:<6} {:<11} {:<5} {:<10} {:<10} {:>5}".format(
            "SUBRUTINA", "GRUPO", "PC LLAMADA", "REG",
            "ESPERADO", "OBSERVADO", "OCUR"), file=out)

        # Agregacion por (subrutina, pc, registro, esperado, observado).
        agg = {}
        orden = []
        for v in violaciones:
            clave = (v["direccion_subrutina"], v["pc_llamador"],
                     v["registro"], v["esperado"], v["observado"])
            if clave not in agg:
                agg[clave] = 0
                orden.append(clave)
            agg[clave] += 1

        for clave in orden:
            dir16, pc_ll, reg, esp, obs = clave
            pc_txt = "0x%04X" % (pc_ll & MASK_16) if pc_ll is not None else "-"
            esp_txt = "0x%04X" % (esp & MASK_16) if esp is not None else "-"
            obs_txt = "0x%04X" % (obs & MASK_16) if obs is not None else "-"
            print("{:<22} {:<6} {:<11} {:<5} {:<10} {:<10} {:>5}".format(
                self._abi_nombre(dir16), self._abi_grupo(dir16), pc_txt, reg,
                esp_txt, obs_txt, agg[clave]), file=out)
        print(file=out)

    def paso(self) -> bool:
        """
        Ejecuta un ciclo fetch-decode-execute.
        Retorna True si la CPU sigue activa, False si se detuvo.
        """
        if self.halted:
            return False

        instr = self.fetch()
        if self.halted:
            return False

        self.instrucciones_ejecutadas += 1
        opcode = (instr >> 11) & 0x1F

        # --- BRANCH ---
        if opcode == OP_BR:
            self.desglose_por_familia["BRANCH"] += 1
            nzp = (instr >> 8) & 0x7
            off8 = sign_extend(instr & 0xFF, 8)
            if nzp & self.cond_bits:
                target = (self.pc + (off8 * 2)) & MASK_16
                if target % 2 != 0:
                    self._disparar_excepcion_fatal(
                        f"Excepción fatal: BR a dirección impar 0x{target:04X}"
                    )
                    self.ciclos_estimados += 2
                    return False
                self.pc = target
                self.ciclos_estimados += 2
            else:
                self.ciclos_estimados += 1
            return True

        # --- ARITHMETIC ---
        elif opcode in (OP_ADD, OP_AND, OP_NOT, OP_MUL, OP_MULH, OP_DIV):
            self.desglose_por_familia["ARITH"] += 1
            self.ciclos_estimados += 1

            dr = (instr >> 8) & 0x7
            sr1 = (instr >> 5) & 0x7

            if opcode == OP_NOT:
                res16 = (~self.regs[sr1]) & MASK_16
                self.regs[dr] = res16
                self._actualizar_nzp(res16)
                return True

            mode = (instr >> 4) & 0x1
            if mode == 0:
                sr2 = instr & 0x7
                op2 = self.regs[sr2]
            else:
                op2 = sign_extend(instr & 0xF, 4) & MASK_16

            val1 = self.regs[sr1]

            if opcode == OP_ADD:
                res32 = val1 + op2
                res16 = res32 & MASK_16
                self.regs[dr] = res16
                self._actualizar_nzp(res16)
                self.flag_c = 1 if res32 > MASK_16 else 0
                s1 = (val1 >> 15) & 1
                s2 = (op2 >> 15) & 1
                sr = (res16 >> 15) & 1
                self.flag_v = 1 if (s1 == s2 and sr != s1) else 0

            elif opcode == OP_AND:
                res16 = (val1 & op2) & MASK_16
                self.regs[dr] = res16
                self._actualizar_nzp(res16)

            elif opcode == OP_MUL:
                s1 = to_int16(val1)
                s2 = to_int16(op2)
                prod = s1 * s2
                res16 = prod & MASK_16
                self.regs[dr] = res16
                self._actualizar_nzp(res16)
                self.flag_v = 1 if (prod < -32768 or prod > 32767) else 0
                self.flag_c = 1 if (val1 * op2) > MASK_16 else 0

            elif opcode == OP_MULH:
                s1 = to_int16(val1)
                s2 = to_int16(op2)
                prod = s1 * s2
                res16 = (prod >> 16) & MASK_16
                self.regs[dr] = res16
                self._actualizar_nzp(res16)

            elif opcode == OP_DIV:
                s1 = to_int16(val1)
                s2 = to_int16(op2)
                if s2 == 0:
                    self.flag_v = 1
                    self._disparar_excepcion_fatal("Excepción fatal: división por cero en DIV")
                    return False
                q = int(s1 / s2)
                res16 = q & MASK_16
                self.regs[dr] = res16
                self._actualizar_nzp(res16)
                self.flag_v = 1 if (s1 == -32768 and s2 == -1) else 0

            return True

        # --- SHIFTER ---
        elif opcode in (OP_LSL, OP_LSR, OP_ASR):
            self.desglose_por_familia["SHIFTER"] += 1
            self.ciclos_estimados += 1

            dr = (instr >> 8) & 0x7
            sr = (instr >> 5) & 0x7
            imm4 = instr & 0xF
            val = self.regs[sr]

            if imm4 == 0:
                res16 = val
                self.flag_c = 0
            elif opcode == OP_LSL:
                self.flag_c = (val >> (16 - imm4)) & 1
                res16 = (val << imm4) & MASK_16
            elif opcode == OP_LSR:
                self.flag_c = (val >> (imm4 - 1)) & 1
                res16 = (val >> imm4) & MASK_16
            else:  # OP_ASR
                self.flag_c = (val >> (imm4 - 1)) & 1
                sval = to_int16(val)
                res16 = (sval >> imm4) & MASK_16

            self.regs[dr] = res16
            self._actualizar_nzp(res16)
            return True

        # --- MEMORY (LOAD / STORE / LEA) ---
        elif opcode in (OP_LD, OP_LDI, OP_LDR, OP_LDBL, OP_LDBH, OP_LDW,
                        OP_ST, OP_STI, OP_STR, OP_STBL, OP_STBH, OP_STW, OP_LEA):
            self.desglose_por_familia["MEMORY"] += 1
            self.ciclos_estimados += 2

            reg = (instr >> 8) & 0x7

            if opcode == OP_LD:
                off8 = sign_extend(instr & 0xFF, 8)
                addr = (self.pc + (off8 * 2)) & MASK_16
                val = self.leer_palabra(addr)
                if self.halted:
                    return False
                self.regs[reg] = val
                self._actualizar_nzp(val)

            elif opcode == OP_LDI:
                off8 = sign_extend(instr & 0xFF, 8)
                ptr_addr = (self.pc + (off8 * 2)) & MASK_16
                target_addr = self.leer_palabra(ptr_addr)
                if self.halted:
                    return False
                val = self.leer_palabra(target_addr)
                if self.halted:
                    return False
                self.regs[reg] = val
                self._actualizar_nzp(val)

            elif opcode in (OP_LDR, OP_LDW):
                base = (instr >> 5) & 0x7
                off5 = sign_extend(instr & 0x1F, 5)
                # P3S v3: escalado obligatorio offset5 << 1 (offset en palabras -> bytes).
                addr = (self.regs[base] + (off5 << 1)) & MASK_16
                val = self.leer_palabra(addr)
                if self.halted:
                    return False
                self.regs[reg] = val
                self._actualizar_nzp(val)

            elif opcode == OP_LDBL:
                base = (instr >> 5) & 0x7
                off5 = sign_extend(instr & 0x1F, 5)
                addr = (self.regs[base] + off5) & MASK_16
                byte_val = self.leer_byte(addr)
                res16 = sign_extend(byte_val, 8) & MASK_16
                self.regs[reg] = res16
                self._actualizar_nzp(res16)

            elif opcode == OP_LDBH:
                base = (instr >> 5) & 0x7
                off5 = sign_extend(instr & 0x1F, 5)
                addr = (self.regs[base] + off5) & MASK_16
                byte_val = self.leer_byte(addr)
                res16 = ((byte_val & MASK_8) << 8) | (self.regs[reg] & MASK_8)
                self.regs[reg] = res16
                self._actualizar_nzp(res16)

            elif opcode == OP_LEA:
                off8 = sign_extend(instr & 0xFF, 8)
                addr = (self.pc + (off8 * 2)) & MASK_16
                self.regs[reg] = addr
                # LEA NO actualiza N, Z, P según SIM_SPEC.md

            elif opcode == OP_ST:
                off8 = sign_extend(instr & 0xFF, 8)
                addr = (self.pc + (off8 * 2)) & MASK_16
                self.escribir_palabra(addr, self.regs[reg])
                if self.halted:
                    return False

            elif opcode == OP_STI:
                off8 = sign_extend(instr & 0xFF, 8)
                ptr_addr = (self.pc + (off8 * 2)) & MASK_16
                target_addr = self.leer_palabra(ptr_addr)
                if self.halted:
                    return False
                self.escribir_palabra(target_addr, self.regs[reg])
                if self.halted:
                    return False

            elif opcode in (OP_STR, OP_STW):
                base = (instr >> 5) & 0x7
                off5 = sign_extend(instr & 0x1F, 5)
                # P3S v3: escalado obligatorio offset5 << 1 (offset en palabras -> bytes).
                addr = (self.regs[base] + (off5 << 1)) & MASK_16
                self.escribir_palabra(addr, self.regs[reg])
                if self.halted:
                    return False

            elif opcode == OP_STBL:
                base = (instr >> 5) & 0x7
                off5 = sign_extend(instr & 0x1F, 5)
                addr = (self.regs[base] + off5) & MASK_16
                self.escribir_byte(addr, self.regs[reg] & MASK_8)

            elif opcode == OP_STBH:
                base = (instr >> 5) & 0x7
                off5 = sign_extend(instr & 0x1F, 5)
                addr = (self.regs[base] + off5) & MASK_16
                self.escribir_byte(addr, (self.regs[reg] >> 8) & MASK_8)

            return True

        # --- CONTROL DE FLUJO ---
        elif opcode in (OP_JSR, OP_JMP, OP_RTI, OP_TRAP):
            self.desglose_por_familia["CONTROL"] += 1

            if opcode == OP_JSR:
                self.ciclos_estimados += 2
                mode = (instr >> 10) & 0x1
                ret_pc = self.pc
                if mode == 1:
                    off10 = sign_extend(instr & 0x3FF, 10)
                    target = (self.pc + (off10 * 2)) & MASK_16
                else:
                    base = (instr >> 7) & 0x7
                    target = self.regs[base]

                if target % 2 != 0:
                    self._disparar_excepcion_fatal(
                        f"Excepción fatal: JSR/JSRR a dirección impar 0x{target:04X}"
                    )
                    return False
                self.regs[7] = ret_pc
                self.pc = target
                # Perfilado: la llamada se consuma -> se apila el marco de la subrutina.
                if self.profile_activo:
                    self._profile_push(target)
                # Auditoria ABI: snapshot de registros callee-saved (R2..R5),
                # puntero de pila (R6) y direccion de retorno (R7) al entrar a la
                # subrutina. R7 ya vale ret_pc (direccion de retorno) en este punto.
                if self.check_abi_activo:
                    self._abi_push(target, ret_pc)

            elif opcode == OP_JMP:
                self.ciclos_estimados += 2
                base = (instr >> 8) & 0x7
                target = self.regs[base]
                if target % 2 != 0:
                    self._disparar_excepcion_fatal(
                        f"Excepción fatal: JMP/RET a dirección impar 0x{target:04X}"
                    )
                    return False
                self.pc = target
                # Perfilado: RET se codifica como JMP R7 (convención LC-3).
                # Al retornar se desapila el marco actual y se deja pendiente de
                # finalización (se acumulará tras atribuir la instrucción RET).
                if self.profile_activo and base == 7 and self._profile_stack:
                    self._profile_ultimo_ret = self._profile_stack.pop()
                # Auditoria ABI: RET se codifica como JMP R7 (base == 7).
                # Se desapila el marco de auditoria y se comparan los registros
                # actuales contra la instantanea tomada en la entrada.
                if self.check_abi_activo and base == 7:
                    self._abi_verificar_ret()

            elif opcode == OP_RTI:
                self.ciclos_estimados += 1
                # Decodificado como NOP en esta fase

            elif opcode == OP_TRAP:
                self.ciclos_estimados += 2
                trapvect8 = instr & 0xFF
                # K.4: trapvect8 fuera de x20-x25 -> Excepción Fatal ANTES de tocar R7
                if trapvect8 < TRAP_GETC or trapvect8 > TRAP_HALT:
                    self._disparar_excepcion_fatal(
                        f"Excepción fatal: TRAP x{trapvect8:02X} reservado/no implementado "
                        f"(fuera de x20-x25) en PC=0x{(self.pc - 2) & MASK_16:04X}"
                    )
                    return False

                # K.2: convención R7 = PC post-fetch (+2), sin alterar N,Z,P,V,C
                self.regs[7] = self.pc

                if trapvect8 == TRAP_GETC:
                    # x20 GETC: 1 carácter sin eco -> R0[7:0], R0[15:8]=0
                    ch = self._leer_caracter()
                    self.regs[0] = ord(ch) & MASK_8

                elif trapvect8 == TRAP_OUT:
                    # x21 OUT: imprime chr(R0[7:0]) en stdout
                    sys.stdout.write(chr(self.regs[0] & MASK_8))

                elif trapvect8 == TRAP_PUTS:
                    # x22 PUTS: 1 carácter por palabra (byte bajo), avance addr += 2
                    addr = self.regs[0] & MASK_16
                    if addr % 2 != 0:
                        self._disparar_excepcion_fatal(
                            f"Excepción fatal: PUTS con R0 impar 0x{addr:04X}"
                        )
                        return False
                    while True:
                        word = self.leer_palabra(addr)
                        if self.halted:
                            return False
                        if word == 0x0000:
                            break
                        sys.stdout.write(chr(word & MASK_8))
                        addr = (addr + 2) & MASK_16

                elif trapvect8 == TRAP_IN:
                    # x23 IN: prompt, 1 carácter con eco -> R0[7:0], R0[15:8]=0
                    sys.stdout.write("Input> ")
                    sys.stdout.flush()
                    ch = self._leer_caracter()
                    sys.stdout.write(ch)  # eco
                    sys.stdout.flush()
                    self.regs[0] = ord(ch) & MASK_8

                elif trapvect8 == TRAP_PUTSP:
                    # x24 PUTSP: 2 caracteres por palabra (bajo y alto), avance addr += 2
                    addr = self.regs[0] & MASK_16
                    if addr % 2 != 0:
                        self._disparar_excepcion_fatal(
                            f"Excepción fatal: PUTSP con R0 impar 0x{addr:04X}"
                        )
                        return False
                    while True:
                        word = self.leer_palabra(addr)
                        if self.halted:
                            return False
                        if word == 0x0000:
                            break
                        lo = word & MASK_8
                        hi = (word >> 8) & MASK_8
                        sys.stdout.write(chr(lo))
                        if hi != 0x00:
                            sys.stdout.write(chr(hi))
                        addr = (addr + 2) & MASK_16

                elif trapvect8 == TRAP_HALT:
                    # x25 HALT: detención limpia, NO es excepción fatal
                    self.halted = True

                return not self.halted

            return not self.halted

        # --- OPCODES RESERVADOS ---
        else:
            self._disparar_excepcion_fatal(
                f"Excepción fatal: opcode reservado 0b{opcode:05b} en PC=0x{(self.pc - 2) & MASK_16:04X}"
            )
            return False

    def ejecutar(self, max_instrucciones: int = 100000):
        """Ejecuta el ciclo fetch-decode-execute hasta halt o límite de instrucciones."""
        while not self.halted and self.instrucciones_ejecutadas < max_instrucciones:
            if self.profile_activo:
                # Marco activo ANTES de ejecutar la instrucción (para atribuir la
                # instrucción actual —incluido el propio JSR/RET— a la subrutina
                # que corresponde) y deltas previos de contadores globales.
                frame_actual = self._profile_stack[-1] if self._profile_stack else None
                prev_instr = self.instrucciones_ejecutadas
                prev_ciclos = self.ciclos_estimados

            self.paso()

            if self.profile_activo:
                di = self.instrucciones_ejecutadas - prev_instr
                dc = self.ciclos_estimados - prev_ciclos
                # La instrucción recién ejecutada pertenece al marco que estaba
                # activo al iniciarla (el JSR suma al llamador; el RET suma al
                # retornado, que se retiró pero seguimos referenciando).
                if frame_actual is not None:
                    frame_actual["instrucciones"] += di
                    frame_actual["ciclos"] += dc
                # Finalizar el marco retirado por un RET (ya con el RET contado).
                if self._profile_ultimo_ret is not None:
                    self._profile_acumular(self._profile_ultimo_ret)
                    self._profile_ultimo_ret = None
                # Rastreo del mínimo valor de R6 (pila descendente).
                r6 = self.regs[6] & MASK_16
                if r6 < self.min_R6:
                    self.min_R6 = r6

        # Cierre seguro de marcos abiertos al detener (HALT/límite/excepción fatal).
        if self.profile_activo and self._profile_stack:
            self._profile_cerrar_abiertos()

    def obtener_telemetria(self) -> dict:
        """Retorna diccionario con las 6 métricas de telemetría integradas."""
        return {
            "instrucciones_ejecutadas": self.instrucciones_ejecutadas,
            "desglose_por_familia": dict(self.desglose_por_familia),
            "ciclos_estimados": self.ciclos_estimados,
            "accesos_memoria": self.accesos_memoria,
            "bytes_ocupados": self.bytes_ocupados,
            "excepciones_fatales": self.excepciones_fatales,
        }

    def obtener_perfilado(self) -> dict:
        """
        Retorna un diccionario con el perfilado por subrutina y el rastreo de
        profundidad de pila (R6). Solo tiene sentido con profile_activo = True.

        Campos:
          - instrucciones_totales / ciclos_totales / halted / excepciones_fatales
          - marcos_cerrados: marcos abiertos cerrados de forma segura al finalizar
          - subrutinas: lista ordenada por instrucciones (desc) de dicts con
            direccion, nombre (etiqueta o 0xXXXX), grupo (G<N> o '-'),
            llamadas, instrucciones, ciclos y porcentaje sobre el total de
            instrucciones ejecutadas.
          - r6_inicial / r6_minimo / profundidad_bytes / profundidad_palabras
        """
        total = self.instrucciones_ejecutadas
        subrutinas = []
        for dir_entrada, st in self._profile_stats.items():
            nombre = self.simbolos_perfil.get(dir_entrada)
            if not nombre:
                nombre = "0x%04X" % (dir_entrada & MASK_16)
            # Grupo (G<N>): primero desde el mapa inyectado por el runner
            # (self.simbolos_grupo); si no existe, se parsea del nombre; si
            # tampoco se identifica, fallback '-'.
            grupo = None
            mapa_grupo = getattr(self, "simbolos_grupo", None)
            if mapa_grupo:
                grupo = mapa_grupo.get(dir_entrada & MASK_16)
            if not grupo:
                grupo = _grupo_desde_nombre(nombre)
            if not grupo:
                grupo = "-"
            instr = st["instrucciones"]
            pct = (100.0 * instr / total) if total > 0 else 0.0
            subrutinas.append({
                "direccion": dir_entrada & MASK_16,
                "nombre": nombre,
                "grupo": grupo,
                "llamadas": st["llamadas"],
                "instrucciones": instr,
                "ciclos": st["ciclos"],
                "porcentaje": pct,
            })
        subrutinas.sort(key=lambda s: s["instrucciones"], reverse=True)

        r6_min = self.min_R6 & MASK_16
        profundidad_bytes = (STACK_BASE - r6_min) & MASK_16
        profundidad_palabras = profundidad_bytes // 2

        return {
            "instrucciones_totales": total,
            "ciclos_totales": self.ciclos_estimados,
            "halted": self.halted,
            "excepciones_fatales": self.excepciones_fatales,
            "marcos_cerrados": self._profile_marcos_cerrados,
            "subrutinas": subrutinas,
            "r6_inicial": STACK_BASE,
            "r6_minimo": r6_min,
            "profundidad_bytes": profundidad_bytes,
            "profundidad_palabras": profundidad_palabras,
        }


def verificar_simulador():
    """
    Suite de verificación interna del simulador:
    1. Prueba con test_p5e_completo_final.bin (si existe o ensamblado en memoria).
    2. Verifica que LD setee N, Z, P basándose en el valor cargado.
    3. Verifica que LEA y ST* no toquen flags.
    4. Verifica excepciones_fatales en saltos y accesos a dirección impar.
    5. Revisa los 6 contadores de telemetría.
    """
    print("=== Verificación de P1S_simulador_funcional.py ===")

    # 1. Prueba con test_p5e_completo_final.bin si existe
    ruta_bin_test = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "Pruebas_ISA",
        "test_p5e_completo_final.bin",
    )
    if os.path.exists(ruta_bin_test):
        sim_bin = Simulador(ruta_bin_test)
        sim_bin.regs[1] = 0x3002  # Dirección par válida para JSRR R1
        sim_bin.ejecutar(max_instrucciones=10)
        print("[OK] test_p5e_completo_final.bin cargado y ejecutado. Telemetría:", sim_bin.obtener_telemetria())
    else:
        print(f"[INFO] No se encontró {ruta_bin_test}; se omitió lectura directa del .bin externo.")

    # Helper para construir instrucción de 16 bits
    def enc_r_off8(op, reg, off8):
        return ((op & 0x1F) << 11) | ((reg & 0x7) << 8) | (off8 & 0xFF)

    def enc_base_off5(op, reg, base, off5):
        return ((op & 0x1F) << 11) | ((reg & 0x7) << 8) | ((base & 0x7) << 5) | (off5 & 0x1F)

    def enc_trap(vect):
        return (OP_TRAP << 11) | (vect & 0x7F)

    # 2. Verificar que LD setee N, Z, P y que LEA y ST* NO toquen flags
    # Programa en x3000:
    # x3000: LD  R1, +3 (apunta a x3008 = 0xFFFF -> N=1, Z=0, P=0)
    # x3002: LEA R2, +3 (apunta a x300A -> NO debe cambiar N=1)
    # x3004: ST  R1, +3 (escribe en x300C -> NO debe cambiar N=1)
    # x3006: TRAP x25 (HALT)
    # x3008: .FILL xFFFF (-1)
    # x300A: .FILL x0042
    # x300C: .FILL x0000
    prog1 = [
        enc_r_off8(OP_LD, 1, 3),
        enc_r_off8(OP_LEA, 2, 3),
        enc_r_off8(OP_ST, 1, 3),
        enc_trap(TRAP_HALT),
        0xFFFF,
        0x0042,
        0x0000,
    ]
    img1 = b"".join(w.to_bytes(2, "big") for w in prog1)
    sim = Simulador()
    sim.cargar_imagen(0x3000, img1)
    sim.ejecutar()

    assert sim.regs[1] == 0xFFFF, "LD debe cargar 0xFFFF"
    assert (sim.flag_n, sim.flag_z, sim.flag_p) == (1, 0, 0), "LD debe setear N=1, Z=0, P=0 y LEA/ST no deben alterarlos"
    assert sim.regs[2] == 0x300A, "LEA debe cargar dirección efectiva 0x300A"
    assert sim.leer_palabra(0x300C) == 0xFFFF, "ST debe escribir 0xFFFF en 0x300C"
    assert sim.excepciones_fatales == 0, "No debe haber excepciones fatales en flujo normal"
    tel1 = sim.obtener_telemetria()
    assert len(tel1) == 6, "Deben existir exactamente 6 métricas de telemetría"
    assert tel1["instrucciones_ejecutadas"] == 4
    print("[OK] Flags LD (N,Z,P), LEA/ST (sin flags) y 6 métricas verificadas:", tel1)

    # 3. Verificar excepción fatal en salto a dirección impar (JMP R1 con R1=0x3001)
    prog2 = [
        (OP_JMP << 11) | (1 << 8),  # JMP R1
        enc_trap(TRAP_HALT),
    ]
    img2 = b"".join(w.to_bytes(2, "big") for w in prog2)
    sim2 = Simulador()
    sim2.cargar_imagen(0x3000, img2)
    sim2.regs[1] = 0x3001
    sim2.ejecutar()
    assert sim2.halted and sim2.excepciones_fatales == 1, "JMP a dirección impar debe generar excepción fatal"
    print("[OK] Excepción fatal en salto impar verificada:", sim2.ultimo_error)

    # 4. Verificar excepción fatal en acceso palabra (LDW) a dirección impar, y byte (LDBL/LDBH) sin restricción
    #    P3S v3: LDW escala offset5<<1; para forzar dirección impar se usa BaseR impar con offset #0.
    prog3 = [
        enc_base_off5(OP_LDBL, 2, 1, 0),  # LDBL R2, R1, #0 (addr 0x3007 impar -> OK, byte sin escalar)
        enc_base_off5(OP_LDW, 3, 1, 0),   # LDW  R3, R1, #0 (addr 0x3007 impar -> Excepción Fatal)
        enc_trap(TRAP_HALT),
        0x12AB,                           # x3006: 0x12, x3007: 0xAB
    ]
    img3 = b"".join(w.to_bytes(2, "big") for w in prog3)
    sim3 = Simulador()
    sim3.cargar_imagen(0x3000, img3)
    sim3.regs[1] = 0x3007
    sim3.ejecutar()
    assert sim3.regs[2] == 0xFFAB, "LDBL debe extender signo de 0xAB a 0xFFAB en dirección impar"
    assert sim3.halted and sim3.excepciones_fatales == 1, "LDW a dirección impar debe generar excepción fatal"
    print("[OK] LDBL en dirección impar y excepción fatal en LDW impar verificadas:", sim3.ultimo_error)
    print("=== Todas las verificaciones pasaron correctamente ===")


def imprimir_reporte_perfilado(sim, titulo="PERFILADO", out=None):
    """
    Imprime por 'out' (stdout por defecto) el reporte de perfilado de 'sim':
    cabecera con telemetría global, tabla por subrutina (desc. por instrucciones)
    y resumen de pico de profundidad de pila (R6). Reutilizado por el runner.
    """
    if out is None:
        out = sys.stdout
    p = sim.obtener_perfilado()

    print("=" * 70, file=out)
    print("ERNIE-CORE PROFILE -- %s" % titulo, file=out)
    print("=" * 70, file=out)
    print("Telemetría global:", file=out)
    print("  Instrucciones ejecutadas : %d" % p["instrucciones_totales"], file=out)
    print("  Ciclos estimados         : %d" % p["ciclos_totales"], file=out)
    print("  Estado halted            : %s" % p["halted"], file=out)
    print("  Excepciones fatales      : %d" % p["excepciones_fatales"], file=out)
    if p["marcos_cerrados"]:
        print("  Marcos abiertos cerrados: %d" % p["marcos_cerrados"], file=out)
    print(file=out)

    print("-" * 70, file=out)
    print("PERFILADO POR SUBRUTINA (ordenado por instrucciones desc.)", file=out)
    print("-" * 70, file=out)
    print("{:<26} {:<8} {:>8} {:>12} {:>10} {:>8}".format(
        "SUBRUTINA", "GRUPO", "LLAMADAS", "INSTR", "CICLOS", "%"), file=out)
    if not p["subrutinas"]:
        print("(sin subrutinas invocadas)", file=out)
    for s in p["subrutinas"]:
        print("{:<26} {:<8} {:>8} {:>12} {:>10} {:>7.2f}%".format(
            s["nombre"], s.get("grupo", "-"), s["llamadas"], s["instrucciones"],
            s["ciclos"], s["porcentaje"]), file=out)
    print(file=out)

    print("-" * 70, file=out)
    print("PICO DE PROFUNDIDAD DE PILA (R6)", file=out)
    print("-" * 70, file=out)
    print("  R6 inicial (STACK_BASE)  : 0x%04X" % p["r6_inicial"], file=out)
    print("  R6 mínimo alcanzado      : 0x%04X" % p["r6_minimo"], file=out)
    print("  Profundidad máxima       : %d bytes (%d palabras)" % (
        p["profundidad_bytes"], p["profundidad_palabras"]), file=out)
    print(file=out)


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "--check-abi":
        # Modo auditoria ABI directo:
        #   python ernie_simulator.py --check-abi <programa.bin>
        if len(sys.argv) < 3:
            print("ERROR: --check-abi requiere la ruta a <programa.bin>.", file=sys.stderr)
            print("Uso: python ernie_simulator.py --check-abi <programa.bin>", file=sys.stderr)
            sys.exit(2)
        ruta_bin = sys.argv[2]
        try:
            sim = Simulador(ruta_bin)
        except (OSError, ValueError) as e:
            print("ERROR al cargar el binario '%s': %s" % (ruta_bin, e), file=sys.stderr)
            sys.exit(1)
        sim.check_abi_activo = True
        sim.ejecutar()
        sim._reporte_abi(titulo="BINARIO %s" % ruta_bin)
        if sim.ultimo_error:
            print("Último error:", sim.ultimo_error, file=sys.stderr)
        hubo_violaciones = len(sim._abi_violaciones) > 0
        sys.exit(1 if (hubo_violaciones or sim.excepciones_fatales > 0) else 0)
    elif len(sys.argv) >= 2 and sys.argv[1] == "--profile":
        # Modo perfilado directo: python ernie_simulator.py --profile <programa.bin>
        if len(sys.argv) < 3:
            print("ERROR: --profile requiere la ruta a <programa.bin>.", file=sys.stderr)
            print("Uso: python ernie_simulator.py --profile <programa.bin>", file=sys.stderr)
            sys.exit(2)
        ruta_bin = sys.argv[2]
        try:
            sim = Simulador(ruta_bin)
        except (OSError, ValueError) as e:
            print("ERROR al cargar el binario '%s': %s" % (ruta_bin, e), file=sys.stderr)
            sys.exit(1)
        sim.profile_activo = True
        sim.ejecutar()
        imprimir_reporte_perfilado(sim, titulo="BINARIO %s" % ruta_bin)
        if sim.ultimo_error:
            print("Último error:", sim.ultimo_error, file=sys.stderr)
        sys.exit(0 if sim.excepciones_fatales == 0 else 1)
    elif len(sys.argv) >= 2:
        sim = Simulador(sys.argv[1])
        sim.ejecutar()
        print("Ejecución finalizada. Telemetría:", sim.obtener_telemetria())
        if sim.ultimo_error:
            print("Último error:", sim.ultimo_error)
    else:
        verificar_simulador()
