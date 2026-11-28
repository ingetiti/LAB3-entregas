"""Ensamblador de la ISA del grupo 15. Enlaza módulos y genera un .obj."""

import argparse
import ast
from dataclasses import dataclass
from pathlib import Path
import re
import sys


OPCODES_MEMORIA_PC = {
    "LD": 0b00010, "ST": 0b00011, "LDI": 0b01010, "STI": 0b01011, "LEA": 0b01110,
}
OPCODES_MEMORIA_BASE = {
    "LDR": 0b00110, "STR": 0b00111, "LDBL": 0b10011,
    "LDBH": 0b10100, "STBL": 0b10101, "STBH": 0b10111,
}
OPCODES_CORRIMIENTO = {"SHL": 0b10000, "LSR": 0b10001, "ASR": 0b10010}
TRAPS = {"GETC": 0x20, "OUT": 0x21, "PUTS": 0x22, "IN": 0x23, "PUTSP": 0x24, "HALT": 0x25}
MNEMONICOS = (
    {"ADD", "AND", "BR", "JSR", "JSRR", "JMP", "RET", "NOT", "RTI", "TRAP", "NOP"}
    | OPCODES_MEMORIA_PC.keys() | OPCODES_MEMORIA_BASE.keys()
    | OPCODES_CORRIMIENTO.keys() | TRAPS.keys()
)
PATRON_ETIQUETA = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
PATRON_BR = re.compile(r"BR[NZP]*")
PATRON_EXTERNA = re.compile(r"([A-Za-z0-9_]+)-([A-Za-z_][A-Za-z0-9_]*)")


@dataclass
class Fila:
    linea: int
    direccion: int
    operacion: str
    operandos: list[str]
    datos: bytes | None


@dataclass
class Modulo:
    nombre: str
    inicio: int
    fin: int
    etiquetas: dict[str, int]
    filas: list[Fila]
    externas: dict[str, int]  # Referencia y línea de su declaración.


def leer_numero(texto):
    """Lee un número escrito con # para decimal, x para hex o b para binario."""
    texto = texto.lower()
    bases = {"#": 10, "x": 16, "b": 2}
    if not texto or texto[0] not in bases:
        raise ValueError(f"Número inválido: {texto!r}. Usá #15, #-1, x000F o b1111.")
    try:
        return int(texto[1:], bases[texto[0]])
    except ValueError:
        raise ValueError(f"Número inválido: {texto!r}.") from None


def leer_registro(texto):
    if not re.fullmatch(r"R[0-7]", texto.upper()):
        raise ValueError(f"Registro inválido: {texto!r}. Se permite R0 a R7.")
    return int(texto[1])


def comprobar_cantidad(operacion, operandos, cantidad):
    if len(operandos) != cantidad:
        raise ValueError(f"{operacion} necesita {cantidad} operandos.")


def quitar_comentario(linea):
    """Ignora el punto y coma mientras esté dentro de una cadena."""
    en_cadena = False
    escape = False
    for i, caracter in enumerate(linea):
        if escape:
            escape = False
        elif en_cadena and caracter == "\\":
            escape = True
        elif caracter == '"':
            en_cadena = not en_cadena
        elif caracter == ";" and not en_cadena:
            return linea[:i]
    return linea


def separar_linea(codigo):
    """Distingue una etiqueta opcional de la operación y sus operandos."""
    primera_palabra = re.fullmatch(r"([^\s,:]+:?)[\s,]*(.*)", codigo)
    if primera_palabra is None:
        raise ValueError("Falta una instrucción o etiqueta.")

    primero, resto = primera_palabra.groups()
    operacion = primero.upper()
    etiqueta = None
    if not (operacion in MNEMONICOS or PATRON_BR.fullmatch(operacion) or primero.startswith(".")):
        etiqueta = primero.removesuffix(":")
        if not PATRON_ETIQUETA.fullmatch(etiqueta):
            raise ValueError(f"Etiqueta inválida: {primero}.")
        if etiqueta.upper() in MNEMONICOS or PATRON_BR.fullmatch(etiqueta.upper()):
            raise ValueError(f"Nombre de etiqueta reservado: {etiqueta}.")
        if not resto:
            return etiqueta, None, []
        partes = re.split(r"[\s,]+", resto, maxsplit=1)
        operacion = partes[0].upper()
        resto = partes[1] if len(partes) > 1 else ""

    if operacion == ".STRINGZ":
        operandos = [resto] if resto else []
    else:
        resto = resto.strip(" \t,")
        operandos = re.split(r"[\s,]+", resto) if resto else []
    return etiqueta, operacion, operandos


def resolver_valor(texto, etiquetas):
    if texto in etiquetas:
        return etiquetas[texto]
    try:
        return leer_numero(texto)
    except ValueError:
        if PATRON_EXTERNA.fullmatch(texto):
            raise ValueError(f"Falta declarar .EXTERNAL {texto}.") from None
        if PATRON_ETIQUETA.fullmatch(texto):
            raise ValueError(f"Etiqueta desconocida: {texto}.") from None
        raise


def codificar_desplazamiento(texto, direccion, etiquetas, bits):
    desplazamiento = resolver_valor(texto, etiquetas)
    if texto in etiquetas:
        # El PC es de 16 bits. Después de xFFFE continúa en x0000.
        diferencia = (desplazamiento - (direccion + 2)) & 0xFFFF
        if diferencia >= 0x8000:
            diferencia -= 0x10000
        if diferencia % 2:
            raise ValueError(f"La etiqueta {texto} debe estar en una dirección par.")
        desplazamiento = diferencia // 2

    limite = 1 << (bits - 1)
    if not -limite <= desplazamiento < limite:
        raise ValueError(
            f"Desplazamiento {texto} fuera de alcance: "
            f"{desplazamiento} palabras. PCoffset{bits} admite de {-limite} a {limite - 1}."
        )
    return desplazamiento & ((1 << bits) - 1)


def codificar_instruccion(operacion, operandos, direccion=0, etiquetas=None):
    """Coloca cada campo en las posiciones definidas en docs/ISA.md."""
    if etiquetas is None:
        etiquetas = {}

    if operacion in TRAPS:
        comprobar_cantidad(operacion, operandos, 0)
        return (0b01111 << 11) | TRAPS[operacion]

    if operacion == "TRAP":
        comprobar_cantidad(operacion, operandos, 1)
        vector = leer_numero(operandos[0])
        if not 0 <= vector <= 255:
            raise ValueError("TRAP admite un vector de 0 a 255.")
        return (0b01111 << 11) | vector

    if operacion in ("NOP", "RTI"):
        comprobar_cantidad(operacion, operandos, 0)
        return (0b01000 << 11) if operacion == "RTI" else 0

    if operacion == "NOT":
        comprobar_cantidad(operacion, operandos, 2)
        destino = leer_registro(operandos[0])
        origen = leer_registro(operandos[1])
        return (0b01001 << 11) | (destino << 8) | (origen << 5) | 0b11111

    if operacion in OPCODES_MEMORIA_PC:
        comprobar_cantidad(operacion, operandos, 2)
        registro = leer_registro(operandos[0])
        offset = codificar_desplazamiento(operandos[1], direccion, etiquetas, 8)
        return (OPCODES_MEMORIA_PC[operacion] << 11) | (registro << 8) | offset

    if PATRON_BR.fullmatch(operacion):
        comprobar_cantidad(operacion, operandos, 1)
        condiciones = operacion[2:] or "NZP"
        if len(condiciones) != len(set(condiciones)):
            raise ValueError(f"Condiciones repetidas en {operacion}.")
        mascara = sum(bit for letra, bit in (("N", 4), ("Z", 2), ("P", 1)) if letra in condiciones)
        offset = codificar_desplazamiento(operandos[0], direccion, etiquetas, 8)
        return (mascara << 8) | offset

    if operacion == "JSR":
        comprobar_cantidad(operacion, operandos, 1)
        offset = codificar_desplazamiento(operandos[0], direccion, etiquetas, 10)
        return (0b00100 << 11) | (1 << 10) | offset

    if operacion in ("JSRR", "JMP", "RET"):
        if operacion == "RET":
            comprobar_cantidad(operacion, operandos, 0)
            base = 7  # RET equivale a JMP R7.
        else:
            comprobar_cantidad(operacion, operandos, 1)
            base = leer_registro(operandos[0])
        opcode = 0b00100 if operacion == "JSRR" else 0b01100
        return (opcode << 11) | (base << 5)

    if not (operacion in ("ADD", "AND") or operacion in OPCODES_CORRIMIENTO or operacion in OPCODES_MEMORIA_BASE):
        raise ValueError(f"Instrucción o directiva desconocida: {operacion}.")

    comprobar_cantidad(operacion, operandos, 3)
    destino = leer_registro(operandos[0])
    origen = leer_registro(operandos[1])
    campos_registros = (destino << 8) | (origen << 5)

    if operacion in OPCODES_CORRIMIENTO:
        cantidad = leer_numero(operandos[2])
        if not 0 <= cantidad <= 15:
            raise ValueError(f"{operacion} admite una cantidad de 0 a 15 posiciones.")
        return (OPCODES_CORRIMIENTO[operacion] << 11) | campos_registros | cantidad

    if operacion in OPCODES_MEMORIA_BASE:
        offset = leer_numero(operandos[2])
        if not -16 <= offset <= 15:
            raise ValueError(f"{operacion} admite un desplazamiento de -16 a 15.")
        return (OPCODES_MEMORIA_BASE[operacion] << 11) | campos_registros | (offset & 0b11111)

    if operandos[2].upper().startswith("R"):
        segundo_origen = leer_registro(operandos[2])
        opcode = {"ADD": 0b00001, "AND": 0b00101}[operacion]
        return (opcode << 11) | campos_registros | segundo_origen

    inmediato = leer_numero(operandos[2])
    if not -16 <= inmediato <= 15:
        raise ValueError(f"{operacion} admite un inmediato de -16 a 15.")
    opcode = {"ADD": 0b10110, "AND": 0b11000}[operacion]
    # & 0b11111 conserva el patrón de cinco bits, también para los negativos.
    return (opcode << 11) | campos_registros | (inmediato & 0b11111)


def medir_fila(operacion, operandos):
    """Devuelve los bytes que ocupa una fila y los datos ya resueltos, si los hay."""
    if operacion == ".BLKW":
        comprobar_cantidad(operacion, operandos, 1)
        palabras = leer_numero(operandos[0])
        if palabras < 0:
            raise ValueError(".BLKW requiere una cantidad de palabras mayor o igual a cero.")
        return 2 * palabras, None
    if operacion == ".BYTE":
        comprobar_cantidad(operacion, operandos, 1)
        valor = leer_numero(operandos[0])
        if not -128 <= valor <= 255:
            raise ValueError(".BYTE admite valores de -128 a 255.")
        return 1, bytes((valor & 0xFF,))
    if operacion == ".STRINGZ":
        comprobar_cantidad(operacion, operandos, 1)
        literal = operandos[0]
        if not re.fullmatch(r'"(?:[^"\\]|\\.)*"', literal):
            raise ValueError(".STRINGZ requiere una sola cadena entre comillas dobles.")
        try:
            caracteres = ast.literal_eval(literal).encode("latin-1")
        except (SyntaxError, ValueError):
            raise ValueError(".STRINGZ requiere caracteres de ocho bits y escapes válidos.") from None
        datos = bytearray(2 * (len(caracteres) + 1))
        datos[1:-1:2] = caracteres
        return len(datos), bytes(datos)
    return 2, None


def error_linea(nombre, numero, mensaje):
    archivo = f"{nombre}: " if nombre else ""
    return ValueError(f"{archivo}Línea {numero}: {mensaje}")


def ubicar(texto, nombre="", inicio=None):
    """Primer recorrido. Ubica las etiquetas de un archivo y mide su tamaño."""
    importado = inicio is not None
    direccion = inicio
    orig_declarado = False
    etiquetas = {}
    pendientes = []
    externas = {}
    filas = []

    for numero_linea, linea in enumerate(texto.splitlines(), 1):
        codigo = quitar_comentario(linea).strip()
        if not codigo:
            continue

        try:
            etiqueta, operacion, operandos = separar_linea(codigo)
            if operacion == ".ORIG":
                comprobar_cantidad(operacion, operandos, 1)
                if etiqueta is not None:
                    raise ValueError(".ORIG no admite una etiqueta.")
                if orig_declarado:
                    raise ValueError("Se permite una sola directiva .ORIG.")
                origen = leer_numero(operandos[0])
                if not 0 <= origen <= 0xFFFF:
                    raise ValueError(".ORIG requiere una dirección de 16 bits.")
                if not importado and origen % 2:
                    raise ValueError("El origen debe ser una dirección par entre x0000 y xFFFE.")
                if not importado:
                    inicio = direccion = origen
                orig_declarado = True
                continue

            if operacion == ".EXTERNAL":
                if etiqueta is not None or not operandos:
                    raise ValueError(".EXTERNAL requiere una o más referencias modulo-simbolo, sin etiqueta local.")
                for referencia in operandos:
                    if not PATRON_EXTERNA.fullmatch(referencia):
                        raise ValueError(f"Referencia inválida en .EXTERNAL: {referencia}.")
                    externas.setdefault(referencia, numero_linea)
                continue

            if direccion is None:
                raise ValueError("El programa principal requiere .ORIG antes de las instrucciones y los datos.")
            if etiqueta is not None:
                if etiqueta in etiquetas or etiqueta in pendientes:
                    raise ValueError(f"Etiqueta repetida: {etiqueta}.")
                pendientes.append(etiqueta)

            if operacion is None:
                continue

            # Una etiqueta sola toma la dirección real de la fila siguiente.
            if operacion not in (".BYTE", ".END") and direccion % 2:
                direccion += 1
            if pendientes and direccion >= 0x10000:
                raise ValueError(f"La etiqueta {pendientes[0]} está fuera de memoria.")
            for etiqueta in pendientes:
                etiquetas[etiqueta] = direccion
            pendientes.clear()

            if operacion == ".END":
                comprobar_cantidad(operacion, operandos, 0)
                return Modulo(nombre, inicio, direccion, etiquetas, filas, externas)

            tamano, datos = medir_fila(operacion, operandos)
            if direccion + tamano > 0x10000:
                raise ValueError("El programa excede las 65.536 direcciones de memoria.")
            if operacion != ".BLKW":
                filas.append(Fila(numero_linea, direccion, operacion, operandos, datos))
            direccion += tamano
        except ValueError as error:
            raise error_linea(nombre, numero_linea, error) from None

    archivo = f"{nombre}: " if nombre else ""
    if inicio is None:
        raise ValueError(f"{archivo}Falta .ORIG.")
    raise ValueError(f"{archivo}Falta .END.")


def buscar_modulo(nombre, archivo_actual, archivos):
    candidatos = archivos.get(nombre.casefold(), [])
    if not candidatos:
        grupo = re.match(r"g\d+_", archivo_actual.stem, re.IGNORECASE)
        if grupo:
            candidatos = archivos.get((grupo[0] + nombre).casefold(), [])
    if not candidatos:
        raise ValueError(f"No se encontró el módulo {nombre}.")
    if len(candidatos) != 1:
        raise ValueError(f"El nombre de módulo {nombre} es ambiguo.")
    return candidatos[0]


def enlazar(ruta, principal, carpeta):
    """Ubica los módulos en orden de descubrimiento y resuelve las referencias."""
    archivos = {ruta.stem.casefold(): [ruta]}
    if carpeta.is_dir():
        for archivo in carpeta.iterdir():
            if archivo.suffix.lower() == ".asm" and archivo.is_file():
                rutas = archivos.setdefault(archivo.stem.casefold(), [])
                destino = archivo.resolve()
                if destino not in rutas:
                    rutas.append(destino)

    en_orden = [(ruta, principal)]
    cargados = {ruta: principal}
    indice = 0
    while indice < len(en_orden):
        ruta_actual, actual = en_orden[indice]
        for referencia, linea in actual.externas.items():
            nombre, simbolo = referencia.split("-")
            try:
                destino = buscar_modulo(nombre, ruta_actual, archivos)
                if destino not in cargados:
                    # Cada módulo empieza en la próxima dirección par.
                    inicio = (en_orden[-1][1].fin + 1) & ~1
                    if inicio >= 0x10000:
                        raise ValueError(f"No hay espacio para enlazar el módulo {destino.name}.")
                    nuevo = ubicar(destino.read_text(encoding="utf-8-sig"), destino.name, inicio)
                    cargados[destino] = nuevo
                    en_orden.append((destino, nuevo))
                modulo = cargados[destino]
                if simbolo not in modulo.etiquetas:
                    raise ValueError(f"{modulo.nombre} no define la etiqueta {simbolo}.")
                actual.etiquetas[referencia] = modulo.etiquetas[simbolo]
            except (OSError, ValueError) as error:
                raise error_linea(actual.nombre, linea, error) from None
        indice += 1
    return [modulo for _, modulo in en_orden]


def emitir(modulos):
    """Segundo recorrido. Escribe código y datos sobre la imagen llena de ceros."""
    origen = modulos[0].inicio
    tamano = modulos[-1].fin - origen
    if tamano == 0:
        raise ValueError("El programa no contiene instrucciones ni datos.")
    imagen = bytearray(tamano)
    for modulo in modulos:
        for fila in modulo.filas:
            try:
                datos = fila.datos
                if fila.operacion == ".FILL":
                    comprobar_cantidad(fila.operacion, fila.operandos, 1)
                    valor = resolver_valor(fila.operandos[0], modulo.etiquetas)
                    if not -32768 <= valor <= 65535:
                        raise ValueError(".FILL admite valores de -32768 a 65535.")
                    datos = (valor & 0xFFFF).to_bytes(2, "big")
                elif datos is None:
                    palabra = codificar_instruccion(
                        fila.operacion, fila.operandos, fila.direccion, modulo.etiquetas
                    )
                    datos = palabra.to_bytes(2, "big")
                offset = fila.direccion - origen
                imagen[offset:offset + len(datos)] = datos
            except ValueError as error:
                raise error_linea(modulo.nombre, fila.linea, error) from None
    return origen.to_bytes(2, "big") + imagen


def ensamblar(texto):
    """Ensambla un programa de un solo archivo a partir de su texto."""
    modulo = ubicar(texto)
    if modulo.externas:
        linea = next(iter(modulo.externas.values()))
        raise error_linea("", linea, "Usá ensamblar_archivo para resolver .EXTERNAL.")
    return emitir([modulo])


def ensamblar_archivo(ruta, carpeta_modulos=None):
    """Carga el principal y busca los módulos en lib o en la carpeta indicada."""
    ruta = Path(ruta).resolve()
    principal = ubicar(ruta.read_text(encoding="utf-8-sig"), ruta.name)
    if not principal.externas:
        return emitir([principal])
    carpeta = ruta.parent / "lib" if carpeta_modulos is None else Path(carpeta_modulos)
    return emitir(enlazar(ruta, principal, carpeta))


def main():
    parser = argparse.ArgumentParser(
        description="Ensamblador de JochISA, la ISA del grupo 15."
    )
    parser.add_argument("entrada", type=Path, help="Archivo de texto .asm")
    parser.add_argument("-o", "--salida", type=Path, help="Archivo .obj de salida")
    parser.add_argument("--modulos", type=Path, help="Carpeta de .EXTERNAL (por defecto, lib junto al principal)")
    args = parser.parse_args()
    salida = args.salida if args.salida is not None else args.entrada.with_suffix(".obj")

    try:
        ruta_salida = salida.resolve()
        if args.entrada.resolve() == ruta_salida or ruta_salida.suffix.lower() == ".asm":
            raise ValueError("La salida .obj debe ser distinta de los archivos .asm.")
        codigo = ensamblar_archivo(args.entrada, args.modulos)
        # Se escribe recién después de validar el programa completo.
        salida.parent.mkdir(parents=True, exist_ok=True)
        salida.write_bytes(codigo)
    except (ValueError, OSError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    origen = int.from_bytes(codigo[:2], "big")
    print(f"Archivo generado: {salida}")
    print(f"Origen: x{origen:04X}")
    tamano = len(codigo) - 2
    if tamano % 2 == 0:
        print(f"Palabras ensambladas: {tamano // 2}")
    print(f"Programa: {tamano} bytes; cabecera de origen: 2 bytes.")
    if len(codigo) <= 64:
        print(f"Bytes del archivo: {codigo.hex(' ').upper()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
