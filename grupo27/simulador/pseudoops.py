'''
Módulo de Pseudo-operaciones (Directivas del Ensamblador) para la ISA-G27.

Este archivo define y documenta todas las directivas y pseudo-operaciones
reconocidas por el ensamblador para la arquitectura ISA-G27 (arquitectura de
16 bits basada en la LC-3, con direccionamiento por bytes y formato Little-Endian).

A diferencia de las instrucciones de máquina de la ISA (definidas en instrucciones.py),
las pseudo-operaciones no corresponden a códigos de operación (OPCODES) ejecutados
directamente por el procesador, sino que son instrucciones dirigidas al ensamblador
para guiar la organización del código, la reserva y asignación de memoria, y el
enlace entre diferentes módulos y archivos fuente.

=============================================================================
LISTADO DE DIRECTIVAS Y PSEUDO-OPERACIONES DE LA ISA-G27:
=============================================================================

1. .ORIG <direccion>
   - Define la dirección de inicio en memoria del programa principal.
   - Solo afecta al programa principal (los módulos externos se ensamblan a
     continuación del programa principal en memoria contigua).
   - Ejemplo: .ORIG x3000

2. .END
   - Marca el final del programa o módulo en el archivo actual.
   - El ensamblador detiene el procesamiento de líneas tras encontrar esta directiva.
   - Ejemplo: .END

3. .EXTERNAL <archivo-etiqueta>
   - Declara etiquetas definidas en otros archivos o programas que serán
     utilizadas en el archivo actual.
   - Sintaxis: .EXTERNAL nombre_archivo-etiqueta
   - Permite que el ensamblador en su primera pasada registre la dependencia
     y cargue el archivo correspondiente para resolver la dirección de la etiqueta.
   - Ejemplo: .EXTERNAL math_lib-sqrt

4. .FILL <valor>
   - Inicializa 1 Word (16 bits / 2 Bytes) de memoria con el valor numérico especificado
     o la dirección de una etiqueta.
   - En memoria, almacena la parte alta a la izquierda y la parte baja a la derecha
     siguiendo la convención Little-Endian definida para la ISA-G27.
   - Ejemplo: .FILL #42, .FILL xFFFF

5. .FILLB <valor>
   - Inicializa 1 Byte (8 bits) de memoria con el valor numérico especificado.
   - Ejemplo: .FILLB #10, .FILLB x0A

6. .BLKW <cantidad>
   - Reserva un bloque de memoria de <cantidad> Words (cada Word ocupa 2 Bytes).
   - El espacio reservado se inicializa por defecto en blanco (ceros).
   - Ejemplo: .BLKW #10 (reserva 10 Words = 20 Bytes de memoria)

7. .BLKB <cantidad>
   - Reserva un bloque de memoria de <cantidad> Bytes (8 bits cada uno).
   - Ejemplo: .BLKB #5 (reserva 5 Bytes de memoria)

8. .STRINGZ "<cadena>"
   - Inicializa una secuencia continua de memoria con los caracteres ASCII de
     la cadena de texto (1 Byte por carácter), seguida automáticamente por
     un carácter nulo '\\0' (1 Byte con valor 0) que actúa como delimitador.
   - Ejemplo: .STRINGZ "Hola Mundo"

=============================================================================
REGLAS DE ALINEACIÓN Y PADDING EN MEMORIA:
=============================================================================
- La memoria de la ISA-G27 está direccionada por Byte (2^16 posiciones de 8 bits).
- Las instrucciones ocupan exactamente 1 Word (2 Bytes) y comienzan en una
  dirección par; el ensamblador agrega padding solo antes de una instrucción
  cuando la dirección actual es impar.
- Las pseudo-operaciones con ALIGN=True también se ubican en una dirección par;
  si la dirección actual es impar, el ensamblador inserta un byte de padding.
- Las pseudo-operaciones con ALIGN=False o ALIGN=None no agregan padding.
=============================================================================
'''


# Clase base para las pseudo-operaciones
class BASE_PSEUDOOP:
    """Interfaz para las pseudo-operaciones del ensamblador.

    Cada ensamblador retorna KIND y DATA. Para MEMORY, DATA es una lista de
    enteros entre 0 y 255. ORIG devuelve una dirección, EXTERNAL referencias
    externas y END indica que no se procesen más líneas del módulo.
    """
    MNEMONICS = []
    FORMATS = []
    ALIGN = None

    def __init__(self, *args, **kwargs):
        pass

    @staticmethod
    def _memory_result(data):
        if not isinstance(data, list) or any(
            type(value) is not int or not 0 <= value <= 0xFF for value in data
        ):
            raise ValueError("DATA de memoria debe ser una lista de enteros entre 0 y 255")
        return {"KIND": "MEMORY", "DATA": data}

    @classmethod
    def s_asemble_method(cls, format_idx, arguments):
        """Retorna un descriptor KIND/DATA que consume el ensamblador."""
        raise NotImplementedError(f"{cls.__name__} debe implementar s_asemble_method")


# ---------------------------------------------------------------------------
# Directivas de control de ensamblado
# ---------------------------------------------------------------------------

class PseudoOp_ORIG(BASE_PSEUDOOP):
    """Define la dirección de inicio en memoria del programa principal."""
    MNEMONICS = [".ORIG"]
    FORMATS = [[".ORIG", "ADDRESS"]]
    ALIGN = True

    @classmethod
    def s_asemble_method(cls, format_idx, arguments):
        # Recibe como argumento la direccion de origen, y lo devuelve como 2 numeros de 8 bits
        address = int(arguments[1]) & 0xFFFF
        return {"KIND": "ORIG", "DATA": [(address >> 8) & 0xFF, address & 0xFF ]}


class PseudoOp_END(BASE_PSEUDOOP):
    """Define el final del programa o módulo en el archivo actual."""
    MNEMONICS = [".END"]
    FORMATS = [[".END"]]
    ALIGN = None

    @classmethod
    def s_asemble_method(cls, format_idx, arguments):
        return {"KIND": "END", "DATA": []}


class PseudoOp_EXTERNAL(BASE_PSEUDOOP):
    """Declara una etiqueta perteneciente a otro archivo o módulo externo."""
    MNEMONICS = [".EXTERNAL"]
    FORMATS = [[".EXTERNAL", "EXT_SYMBOL"]]
    ALIGN = None

    @classmethod
    def s_asemble_method(cls, format_idx, arguments):
        return {"KIND": "EXTERNAL", "DATA": []}


# ---------------------------------------------------------------------------
# Directivas de asignación y reserva de memoria
# ---------------------------------------------------------------------------

class PseudoOp_FILL(BASE_PSEUDOOP):
    """Define e inicializa 1 Word (16 bits / 2 Bytes) en memoria."""
    MNEMONICS = [".FILL"]
    FORMATS = [[".FILL", "VALUE_16"]]
    ALIGN = True

    @classmethod
    def s_asemble_method(cls, format_idx, arguments):
        data = int(arguments[1]) & 0xFFFF
        return cls._memory_result([data >> 8, data & 0xFF])


class PseudoOp_FILLB(BASE_PSEUDOOP):
    """Define e inicializa 1 Byte (8 bits) en memoria."""
    MNEMONICS = [".FILLB"]
    FORMATS = [[".FILLB", "VALUE_8"]]
    ALIGN = False

    @classmethod
    def s_asemble_method(cls, format_idx, arguments):
        data = int(arguments[1])
        return cls._memory_result([data & 0xFF])


class PseudoOp_BLKW(BASE_PSEUDOOP):
    """Reserva un bloque de Words en blanco (2 Bytes por Word)."""
    MNEMONICS = [".BLKW"]
    FORMATS = [[".BLKW", "COUNT"]]
    ALIGN = True

    @classmethod
    def s_asemble_method(cls, format_idx, arguments):
        count = int(arguments[1])
        if count < 0:
            raise ValueError(".BLKW requiere una cantidad no negativa")
        return cls._memory_result([0] * (2 * count))


class PseudoOp_BLKB(BASE_PSEUDOOP):
    """Reserva un bloque de Bytes en blanco (1 Byte por posición)."""
    MNEMONICS = [".BLKB"]
    FORMATS = [[".BLKB", "COUNT"]]
    ALIGN = False

    @classmethod
    def s_asemble_method(cls, format_idx, arguments):
        count = int(arguments[1])
        if count < 0:
            raise ValueError(".BLKB requiere una cantidad no negativa")
        return cls._memory_result([0] * count)


class PseudoOp_STRINGZ(BASE_PSEUDOOP):
    """Define una cadena de caracteres ASCII de 8 bits terminada en nulo ('\\0')."""
    MNEMONICS = [".STRINGZ"]
    FORMATS = [[".STRINGZ", "STRING"]]
    ALIGN = True

    @classmethod
    def s_asemble_method(cls, format_idx, arguments):
        text = str(arguments[1])
        data = list(text.encode("ascii", errors="replace"))
        data.append(0)
        return cls._memory_result(data)


# Lista de todas las pseudo-operaciones disponibles
PSEUDOOPS = [
    PseudoOp_ORIG,
    PseudoOp_END,
    PseudoOp_EXTERNAL,
    PseudoOp_FILL,
    PseudoOp_FILLB,
    PseudoOp_BLKW,
    PseudoOp_BLKB,
    PseudoOp_STRINGZ,
]

# Diccionario de búsqueda por directiva
PSEUDOOP_BY_MNEMONIC = {}
for _pop in PSEUDOOPS:
    for _m in _pop.MNEMONICS:
        PSEUDOOP_BY_MNEMONIC[_m.upper()] = _pop
