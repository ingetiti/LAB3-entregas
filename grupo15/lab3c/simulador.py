"""Simulador de la ISA del grupo 15. Ejecuta código máquina."""

import argparse
from io import StringIO
from pathlib import Path
import sys


MEMORIA_PC = {
    0b00010: "LD", 0b00011: "ST", 0b01010: "LDI", 0b01011: "STI", 0b01110: "LEA",
}
MEMORIA_BASE = {
    0b00110: "LDR", 0b00111: "STR", 0b10011: "LDBL",
    0b10100: "LDBH", 0b10101: "STBL", 0b10111: "STBH",
}
CORRIMIENTOS = {0b10000: "SHL", 0b10001: "LSR", 0b10010: "ASR"}
TRAPS = {0x20: "GETC", 0x21: "OUT", 0x22: "PUTS", 0x23: "IN", 0x24: "PUTSP", 0x25: "HALT"}
LIMITE_PREDETERMINADO = 1_000_000
TABLA_SO = 0x0200
BASE_PILA_SO = 0x0400
TOPE_PILA_SO = 0x0500


def con_signo(valor, bits):
    """Interpreta un patrón de bits como un número en complemento a dos."""
    if valor & (1 << (bits - 1)):
        return valor - (1 << bits)
    return valor


def direccion_relativa(siguiente_pc, palabra, bits):
    """El campo cuenta palabras. El PC contiene una dirección de byte."""
    offset = con_signo(palabra & ((1 << bits) - 1), bits)
    return (siguiente_pc + 2 * offset) & 0xFFFF


class Simulador:
    def __init__(self, archivo, entrada=None, salida=None):
        if len(archivo) < 4:
            raise ValueError("El archivo debe contener dos bytes de origen y al menos una instrucción.")

        self.origen = int.from_bytes(archivo[:2], "big")
        programa = archivo[2:]
        if self.origen % 2:
            raise ValueError("El origen debe ser una dirección par.")
        if self.origen + len(programa) > 65536:
            raise ValueError("El programa excede las 65.536 direcciones de memoria.")

        self.memoria = bytearray(65536)
        sistema = Path(__file__).with_name("so").joinpath("servicios.obj").read_bytes()
        self.bytes_so = len(sistema) - 2
        if (int.from_bytes(sistema[:2], "big") != TABLA_SO
                or not 12 < self.bytes_so <= BASE_PILA_SO - TABLA_SO or self.bytes_so % 2):
            raise ValueError("El objeto del sistema operativo es inválido.")
        for inicio, fin in ((TABLA_SO, TABLA_SO + self.bytes_so), (BASE_PILA_SO, TOPE_PILA_SO)):
            if self.origen < fin and self.origen + len(programa) > inicio:
                raise ValueError("El programa se superpone con el sistema operativo o su pila.")
        self.memoria[TABLA_SO:TABLA_SO + self.bytes_so] = sistema[2:]
        self.memoria[self.origen:self.origen + len(programa)] = programa
        self.bytes_programa = len(programa)
        self.registros = [0] * 8
        self.registros[6] = 0xFD00
        self.pc = self.origen
        self.psr = 0b010  # Inicialmente está activa la condición Z.
        self.detenido = False
        self.instrucciones_ejecutadas = 0
        self.instrucciones_so = 0
        self.nivel_so = 0
        self.pila_usuario = None
        self.retornos_externos = []
        self.apagar = False
        self.entrada = entrada
        self.salida = salida

    @staticmethod
    def comprobar_direccion_palabra(direccion):
        if not 0 <= direccion <= 0xFFFE or direccion % 2:
            raise ValueError(f"Dirección de palabra inválida: x{direccion:04X}.")

    def leer_palabra(self, direccion):
        self.comprobar_direccion_palabra(direccion)
        return (self.memoria[direccion] << 8) | self.memoria[direccion + 1]

    def guardar_palabra(self, direccion, valor):
        self.comprobar_direccion_palabra(direccion)
        self.memoria[direccion:direccion + 2] = (valor & 0xFFFF).to_bytes(2, "big")

    def actualizar_nzp(self, valor):
        if valor == 0:
            self.psr = 0b010
        elif valor & 0x8000:
            self.psr = 0b100
        else:
            self.psr = 0b001

    def condicion(self):
        return {0b100: "N", 0b010: "Z", 0b001: "P"}[self.psr]

    @staticmethod
    def comprobar_salto(direccion):
        if direccion % 2:
            raise ValueError(f"Destino de salto impar: x{direccion:04X}.")

    def leer_caracter(self):
        entrada = sys.stdin if self.entrada is None else self.entrada
        if entrada is sys.stdin and entrada.isatty():
            if sys.platform == "win32":
                from msvcrt import getwch

                caracter = getwch()
                while caracter in ("\x00", "\xe0"):
                    getwch()  # Las teclas especiales ocupan dos lecturas.
                    caracter = getwch()
                if caracter == "\r":
                    caracter = "\n"
            else:
                import termios
                import tty

                fd = entrada.fileno()
                modo = termios.tcgetattr(fd)
                try:
                    tty.setcbreak(fd)
                    caracter = entrada.read(1)
                finally:
                    termios.tcsetattr(fd, termios.TCSADRAIN, modo)
        else:
            caracter = entrada.read(1)
        if caracter == "":
            raise ValueError("No quedan caracteres de entrada para el TRAP.")
        if ord(caracter) > 255:
            raise ValueError("El TRAP requiere caracteres de ocho bits.")
        return caracter

    def escribir_texto(self, texto):
        salida = sys.stdout if self.salida is None else self.salida
        salida.write(texto)
        salida.flush()

    @property
    def instrucciones_usuario(self):
        return self.instrucciones_ejecutadas - self.instrucciones_so

    def leer_dato(self, direccion):
        if direccion in (0xFE00, 0xFE04):
            return 0x8000  # Consola síncrona. La lectura de teclado espera una tecla.
        if direccion == 0xFE02:
            return ord(self.leer_caracter())
        if direccion == 0xFFFE:
            return 0 if self.apagar else 0x8000
        return self.leer_palabra(direccion)

    def guardar_dato(self, direccion, valor):
        if direccion == 0xFE06:
            self.escribir_texto(chr(valor & 0xFF))
        elif direccion == 0xFFFE:
            self.apagar = not (valor & 0x8000)
            if not self.nivel_so:
                self.detenido = self.apagar
        else:
            self.guardar_palabra(direccion, valor)

    def atender_trap(self, vector, retorno):
        nombre = TRAPS.get(vector, f"TRAP x{vector:02X}")
        if vector in TRAPS:
            siguiente_pc = self.leer_palabra(TABLA_SO + 2 * (vector - 0x20))
            self.comprobar_salto(siguiente_pc)
            # Cada servicio recibe su propio marco, también cuando PUTS llama a OUT.
            pila = self.registros[6] if self.nivel_so else TOPE_PILA_SO
            if not BASE_PILA_SO <= pila - 6 <= TOPE_PILA_SO - 6:
                raise ValueError("Sin espacio en la pila del sistema operativo.")
            if not self.nivel_so:
                self.pila_usuario = self.registros[6]
            self.guardar_palabra(pila - 6, retorno)
            self.guardar_palabra(pila - 4, self.psr)
            self.guardar_palabra(pila - 2, self.registros[7] if self.nivel_so else retorno)
            self.registros[6] = pila - 6
            self.nivel_so += 1
        else:
            siguiente_pc = self.leer_palabra(2 * vector)
            if siguiente_pc == 0:
                raise ValueError(f"TRAP x{vector:02X} sin servicio definido.")
            self.comprobar_salto(siguiente_pc)
            self.retornos_externos.append(retorno)

        self.registros[7] = retorno
        return siguiente_pc, f"{nombre} -> PC=x{siguiente_pc:04X}, R7=x{retorno:04X}"

    def paso(self):
        """Busca, interpreta y ejecuta una instrucción de 16 bits."""
        if self.detenido:
            raise ValueError("El programa ya terminó con HALT.")

        direccion = self.pc
        desde_so = bool(self.nivel_so or self.retornos_externos)
        palabra = self.leer_palabra(direccion)
        siguiente_pc = (direccion + 2) & 0xFFFF
        opcode = palabra >> 11
        destino = (palabra >> 8) & 0b111
        origen = (palabra >> 5) & 0b111
        resultado = None

        # Los registros almacenan patrones de 16 bits. El signo se interpreta
        # solamente donde lo requiere la operación.
        if opcode in (0b00001, 0b00101):
            if palabra & 0b11000:
                raise ValueError(f"Bits reservados incorrectos en x{direccion:04X}.")
            segundo = palabra & 0b111
            nombre = "ADD" if opcode == 0b00001 else "AND"
            a = self.registros[origen]
            b = self.registros[segundo]
            resultado = a + b if nombre == "ADD" else a & b
            descripcion = f"{nombre} R{destino},R{origen},R{segundo}"

        elif opcode in (0b10110, 0b11000):
            inmediato = con_signo(palabra & 0b11111, 5)
            nombre = "ADD" if opcode == 0b10110 else "AND"
            a = self.registros[origen]
            resultado = a + inmediato if nombre == "ADD" else a & inmediato
            descripcion = f"{nombre} R{destino},R{origen},#{inmediato}"

        elif opcode == 0b01001:
            if palabra & 0b11111 != 0b11111:
                raise ValueError(f"Bits reservados incorrectos en NOT, x{direccion:04X}.")
            resultado = ~self.registros[origen]
            descripcion = f"NOT R{destino},R{origen}"

        elif opcode in CORRIMIENTOS:
            nombre = CORRIMIENTOS[opcode]
            if palabra & 0b10000:
                raise ValueError(f"Bit reservado incorrecto en {nombre}, x{direccion:04X}.")
            cantidad = palabra & 0b1111
            valor = self.registros[origen]
            if nombre == "SHL":
                resultado = valor << cantidad
            elif nombre == "LSR":
                resultado = valor >> cantidad
            else:
                resultado = con_signo(valor, 16) >> cantidad
            descripcion = f"{nombre} R{destino},R{origen},#{cantidad}"

        elif opcode in MEMORIA_PC or opcode in MEMORIA_BASE:
            if opcode in MEMORIA_PC:
                nombre = MEMORIA_PC[opcode]
                direccion_dato = direccion_relativa(siguiente_pc, palabra, 8)
            else:
                nombre = MEMORIA_BASE[opcode]
                offset = con_signo(palabra & 0b11111, 5)
                if nombre in ("LDR", "STR"):
                    offset *= 2
                direccion_dato = (self.registros[origen] + offset) & 0xFFFF

            if nombre in ("LDI", "STI"):
                direccion_dato = self.leer_palabra(direccion_dato)

            descripcion = f"{nombre} R{destino},[x{direccion_dato:04X}]"
            if nombre in ("LD", "LDI", "LDR"):
                resultado = self.leer_dato(direccion_dato)
            elif nombre == "LEA":
                resultado = direccion_dato
                descripcion = f"LEA R{destino},x{direccion_dato:04X}"
            elif nombre == "LDBL":
                resultado = con_signo(self.memoria[direccion_dato], 8)
            elif nombre == "LDBH":
                resultado = (self.memoria[direccion_dato] << 8) | (self.registros[destino] & 0xFF)
            elif nombre in ("ST", "STI", "STR"):
                valor = self.registros[destino]  # En los guardados, el campo indica el registro fuente.
                self.guardar_dato(direccion_dato, valor)
                descripcion += f" -> memoria=x{valor:04X}"
            else:
                valor = self.registros[destino]
                if nombre == "STBH":
                    valor >>= 8
                valor &= 0xFF
                self.memoria[direccion_dato] = valor
                descripcion += f" -> memoria=x{valor:02X}"

        elif opcode == 0b00000:
            mascara = (palabra >> 8) & 0b111
            objetivo = direccion_relativa(siguiente_pc, palabra, 8)
            if mascara & self.psr:
                siguiente_pc = objetivo
            sufijo = "".join(letra for letra, bit in (("n", 4), ("z", 2), ("p", 1)) if mascara & bit)
            descripcion = f"BR{sufijo} x{objetivo:04X}" if mascara else "NOP"
            descripcion += f" -> PC=x{siguiente_pc:04X}"

        elif opcode in (0b00100, 0b01100):
            if opcode == 0b00100 and palabra & 0x0400:
                objetivo = direccion_relativa(siguiente_pc, palabra, 10)
                descripcion = f"JSR x{objetivo:04X}"
            else:
                if palabra & 0x071F:
                    raise ValueError(f"Bits reservados incorrectos en x{direccion:04X}.")
                # JSRR R7 usa el valor anterior de R7 como destino del salto.
                objetivo = self.registros[origen]
                self.comprobar_salto(objetivo)
                if opcode == 0b00100:
                    descripcion = f"JSRR R{origen}"
                else:
                    descripcion = "RET" if origen == 7 else f"JMP R{origen}"

            if opcode == 0b00100:
                self.registros[7] = siguiente_pc
                descripcion += f" -> PC=x{objetivo:04X}, R7=x{siguiente_pc:04X}"
            else:
                descripcion += f" -> PC=x{objetivo:04X}"
            siguiente_pc = objetivo

        elif opcode == 0b01000:
            if palabra & 0x07FF:
                raise ValueError(f"Bits reservados incorrectos en RTI, x{direccion:04X}.")
            pila = self.registros[6]
            objetivo = self.leer_palabra(pila)
            psr = self.leer_palabra((pila + 2) & 0xFFFF)
            self.comprobar_salto(objetivo)
            if psr not in (0b001, 0b010, 0b100):
                raise ValueError(f"PSR inválido en RTI: x{psr:04X}.")
            self.psr = psr
            if self.nivel_so:
                self.registros[7] = self.leer_palabra(pila + 4)
                self.registros[6] = pila + 6
                self.nivel_so -= 1
                if not self.nivel_so:
                    self.registros[6] = self.pila_usuario
                    self.pila_usuario = None
                    self.detenido = self.apagar  # HALT devuelve los registros antes de parar.
            else:
                self.registros[6] = (pila + 4) & 0xFFFF
            siguiente_pc = objetivo
            descripcion = f"RTI -> PC=x{objetivo:04X}, R6=x{self.registros[6]:04X}"

        elif opcode == 0b01111:
            if palabra & 0x0700:
                raise ValueError(f"Bits reservados incorrectos en TRAP, x{direccion:04X}.")
            vector = palabra & 0xFF
            siguiente_pc, descripcion = self.atender_trap(vector, siguiente_pc)

        else:
            raise ValueError(f"Opcode reservado {opcode:05b} en x{direccion:04X}.")

        if resultado is not None:
            self.registros[destino] = resultado & 0xFFFF
            self.actualizar_nzp(self.registros[destino])
            descripcion += f" -> R{destino}={con_signo(self.registros[destino], 16)}"

        self.pc = siguiente_pc
        self.instrucciones_ejecutadas += 1
        if desde_so:
            self.instrucciones_so += 1
        if (not self.nivel_so and self.retornos_externos and opcode in (0b01100, 0b01000)
                and siguiente_pc == self.retornos_externos[-1]):
            self.retornos_externos.pop()
        modo = "SO" if desde_so else "usuario"
        return f"x{direccion:04X}  x{palabra:04X}  {descripcion}; NZP={self.condicion()} [{modo}]"

    def ejecutar(self, traza=False, limite=LIMITE_PREDETERMINADO):
        if limite < 1:
            raise ValueError("El límite de instrucciones debe ser positivo.")
        while not self.detenido:
            if self.instrucciones_ejecutadas >= limite:
                raise ValueError("Se alcanzó el límite de instrucciones sin terminar con HALT.")
            descripcion = self.paso()
            if traza:
                print(descripcion)


def main():
    parser = argparse.ArgumentParser(
        description="Simulador de JochISA. Carga código máquina .obj."
    )
    parser.add_argument("entrada", type=Path, help="Archivo .obj generado por nuestro ensamblador")
    parser.add_argument("--traza", action="store_true", help="Mostrar cada instrucción ejecutada")
    parser.add_argument("--limite", type=int, default=LIMITE_PREDETERMINADO, help="Máximo de instrucciones")
    parser.add_argument("--entrada", dest="texto_entrada", help="Texto para GETC e IN (por defecto, la terminal)")
    args = parser.parse_args()

    try:
        archivo = args.entrada.read_bytes()
        entrada = StringIO(args.texto_entrada) if args.texto_entrada is not None else None
        simulador = Simulador(archivo, entrada=entrada)
        simulador.ejecutar(traza=args.traza, limite=args.limite)
    except FileNotFoundError as error:
        print(f"Falta el archivo {error.filename}. Consultá el README para ensamblarlo.", file=sys.stderr)
        return 1
    except (ValueError, OSError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    print("\nEstado: detenido por HALT")
    print(f"Origen: x{simulador.origen:04X}")
    for i, valor in enumerate(simulador.registros):
        print(f"R{i} = {con_signo(valor, 16)} (x{valor:04X})")
    print(f"PC: x{simulador.pc:04X}")
    print(f"NZP: {simulador.condicion()}")
    print(f"Instrucciones de usuario: {simulador.instrucciones_usuario}")
    print(f"Instrucciones del SO: {simulador.instrucciones_so}")
    print(f"Instrucciones totales: {simulador.instrucciones_ejecutadas}")
    print(f"Memoria del programa: {simulador.bytes_programa} bytes")
    print(f"Imagen del SO: {simulador.bytes_so} bytes")
    print("Cabecera de origen: 2 bytes, excluidos de la memoria del programa.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
