'''
Ensamblador para la arquitectura ISA-G27.

Traduce programas escritos en lenguaje ensamblador de la ISA-G27 a código máquina
ejecutable por el simulador.

Características principales:
- Ensamblado de dos pasadas (Pass 1: tabla de símbolos y cálculo de direcciones;
  Pass 2: resolución de etiquetas y generación de código binario).
- Resolución y enlazado continuo de módulos externos mediante .EXTERNAL.
- Soporte para formatos de entrada: archivo .asm, texto directo, o mapa de archivos.
- Soporte para formatos de salida: archivo .hex (2 caracteres hex por línea, por defecto),
  archivo .bin (8 caracteres binarios por línea), o lista en memoria de valores.
- Inclusión por defecto de la dirección .ORIG en los dos primeros bytes de la salida.
- Manejo automático de alineación y padding de 1 Byte para instrucciones y Words
  tras datos impares de 8 bits (.FILLB o .STRINGZ).
- Generación opcional de archivo de tabla de símbolos (.sym).
'''

import os
import sys
import re
import argparse
from pathlib import Path

try:
    from . import instrucciones
    from . import pseudoops
except ImportError:
    import instrucciones
    import pseudoops


# ---------------------------------------------------------------------------
# Utilidades de Parseo y Formato
# ---------------------------------------------------------------------------

def strip_comments(line: str) -> str:
    """
    Elimina los comentarios iniciados con ';' respetando las cadenas entre comillas.
    """
    in_quote = False
    quote_char = ''
    result = []
    i = 0
    n = len(line)
    while i < n:
        c = line[i]
        if in_quote:
            result.append(c)
            if c == '\\':
                if i + 1 < n:
                    i += 1
                    result.append(line[i])
            elif c == quote_char:
                in_quote = False
        else:
            if c in ('"', "'"):
                in_quote = True
                quote_char = c
                result.append(c)
            elif c == ';':
                break
            else:
                result.append(c)
        i += 1
    return ''.join(result).strip()


def unescape_string(s: str) -> str:
    """
    Parsea las secuencias de escape estándar (\n, \t, \r, \0, \\, \", \') en una cadena.
    """
    escape_map = {
        'n': '\n',
        't': '\t',
        'r': '\r',
        '0': '\0',
        '\\': '\\',
        '"': '"',
        "'": "'",
    }
    result = []
    i = 0
    n = len(s)
    while i < n:
        if s[i] == '\\' and i + 1 < n:
            next_char = s[i + 1]
            if next_char in escape_map:
                result.append(escape_map[next_char])
                i += 2
                continue
        result.append(s[i])
        i += 1
    return ''.join(result)


def is_register(token: str) -> bool:
    """Verifica si un token representa un registro válido (R0 a R7, insensible a mayúsculas)."""
    if not isinstance(token, str):
        return False
    t = token.strip()
    return bool(re.match(r'^[rR][0-7]$', t))


def parse_register(token: str) -> int:
    """Convierte un token de registro (ej. 'R3' o 'r3') a su índice entero (0 a 7)."""
    t = token.strip()
    if is_register(t):
        return int(t[1])
    raise ValueError(f"Registro inválido: '{token}'. Se esperaba R0..R7.")


_OPERAND_SPECS = {
    "IMM4":       {"kind": "int", "bits": 4,  "signed": True},
    "NSH5":       {"kind": "int", "bits": 5,  "signed": True},
    "UNSH4":      {"kind": "int", "bits": 4,  "signed": False},
    "CPSH4":      {"kind": "int", "min": 1,   "max": 16},
    "UOFFSET5":   {"kind": "int", "bits": 5,  "signed": False},
    "BUOFFSET5":  {"kind": "int", "bits": 5,  "signed": False},
    "TRAPVEC8":   {"kind": "int", "bits": 8,  "signed": False},
    "PCOFFSET8":  {"kind": "pcoffset", "bits": 8,  "signed": True, "is_byte": False},
    "PCOFFSET10": {"kind": "pcoffset", "bits": 10, "signed": True, "is_byte": False},
    "BPCOFFSET8": {"kind": "pcoffset", "bits": 8,  "signed": True, "is_byte": True},
    "ADDRESS":    {"kind": "int", "bits": 16, "signed": False},
    "VALUE_16":   {"kind": "int", "bits": 16, "signed": True, "allow_unsigned_symbol": True},
    "VALUE_8":    {"kind": "int", "bits": 8,  "signed": True, "allow_unsigned_symbol": True},
    "VALUE":      {"kind": "int", "bits": 16, "signed": True, "allow_unsigned_symbol": True},
    "COUNT":      {"kind": "int", "min": 0,   "max": 0xFFFF},
}


def parse_number_info(token) -> tuple:
    """
    Parsea un token numérico a (valor_entero, es_literal_de_bits).

    - Decimales (#123, #-45, 123, -45) y literales de carácter ('A') permiten signo
      y devuelven es_literal_de_bits=False.
    - Hexadecimales (xFFFF, 0xFF) y binarios (b1010, 0b1010) NO aceptan signo '-' ni '+'
      y devuelven es_literal_de_bits=True.
    """
    if isinstance(token, int) and not isinstance(token, bool):
        return token, False
    if not isinstance(token, str):
        raise ValueError(f"Literal numérico inválido: '{token}'")

    t = token.strip()
    if not t:
        raise ValueError("Literal numérico vacío")

    # Decimal con prefijo #: #123, #-123, #+123
    if t.startswith('#'):
        if re.match(r'^#[+-]?[0-9]+$', t):
            return int(t[1:], 10), False
        raise ValueError(f"Literal decimal inválido: '{token}'")

    # Hexadecimal sin signo: x..., X..., 0x..., 0X...
    if re.match(r'^(?:0[xX]|[xX])[0-9a-fA-F]+$', t):
        hex_part = t[2:] if t.lower().startswith('0x') else t[1:]
        return int(hex_part, 16), True

    # Binario sin signo: b..., B..., 0b..., 0B...
    if re.match(r'^(?:0[bB]|[bB])[01]+$', t):
        bin_part = t[2:] if t.lower().startswith('0b') else t[1:]
        return int(bin_part, 2), True

    # Carácter entre comillas simples: 'c', '\n'
    if len(t) >= 3 and t.startswith("'") and t.endswith("'"):
        inner = unescape_string(t[1:-1])
        if len(inner) == 1:
            return ord(inner), False
        raise ValueError(f"Literal de carácter inválido: '{token}'")

    # Decimal simple sin prefijo (acepta signo)
    if re.match(r'^[+-]?[0-9]+$', t):
        return int(t, 10), False

    raise ValueError(f"Literal numérico inválido: '{token}'")


def is_number(token) -> bool:
    """Determina si un token puede ser interpretado como un valor numérico válido."""
    try:
        parse_number_info(token)
        return True
    except ValueError:
        return False


def parse_number(token) -> int:
    """Parsea un token numérico en decimal, hexadecimal, binario o carácter literal a entero."""
    value, _ = parse_number_info(token)
    return value


def _validate_numeric_operand(operand_type: str, value: int, is_bit_literal: bool = False,
                              resolved_symbol: bool = False) -> int:
    """Valida que un operando numérico esté dentro del rango exacto permitido por su tipo."""
    spec = _OPERAND_SPECS.get(operand_type)
    if spec is None:
        raise ValueError(f"Tipo de operando no soportado: '{operand_type}'")

    if "min" in spec and "max" in spec:
        min_val, max_val = spec["min"], spec["max"]
    else:
        bits = spec["bits"]
        if resolved_symbol and spec.get("allow_unsigned_symbol"):
            min_val, max_val = 0, (1 << bits) - 1
        elif is_bit_literal or not spec.get("signed", False):
            min_val, max_val = 0, (1 << bits) - 1
        else:
            min_val = -(1 << (bits - 1))
            max_val = (1 << (bits - 1)) - 1

    if not (min_val <= value <= max_val):
        raise ValueError(
            f"Valor fuera de rango para {operand_type}: {value} "
            f"(rango permitido: [{min_val}, {max_val}])"
        )
    return value


def _split_tokens(text: str, line_num: int = 0) -> list:
    """
    Divide una línea en tokens usando comas y espacios como delimitadores,
    preservando intactas las cadenas entre comillas dobles y literales entre comillas simples.
    """
    tokens = []
    current = []
    in_quote = False
    quote_char = ''
    i = 0
    n = len(text)

    while i < n:
        c = text[i]
        if in_quote:
            current.append(c)
            if c == '\\':
                if i + 1 < n:
                    i += 1
                    current.append(text[i])
                else:
                    raise ValueError(f"Secuencia de escape incompleta en línea {line_num}")
            elif c == quote_char:
                in_quote = False
        else:
            if c in ('"', "'"):
                in_quote = True
                quote_char = c
                current.append(c)
            elif c == ',' or c.isspace():
                if current:
                    tokens.append(''.join(current))
                    current.clear()
            else:
                current.append(c)
        i += 1

    if in_quote:
        raise ValueError(f"Literal entre comillas sin cerrar en línea {line_num}")
    if current:
        tokens.append(''.join(current))
    return tokens


def _instruction_classes():
    """Obtiene clases de instrucción desde los registros disponibles."""
    classes = list(getattr(instrucciones, "INSTRUCTIONS", ()) or ())
    for registry_name in ("INSTRUCTION_BY_OPCODE", "INSTRUCTIONS_BY_OPCODE",
                          "INSTRUCTION_BY_MNEMONIC"):
        registry = getattr(instrucciones, registry_name, None)
        if isinstance(registry, dict):
            classes.extend(registry.values())

    unique_classes = []
    seen = set()
    for inst_cls in classes:
        class_id = id(inst_cls)
        if class_id not in seen:
            unique_classes.append(inst_cls)
            seen.add(class_id)
    return unique_classes


def _instruction_class_for(mnemonic: str):
    """Busca una instrucción usando los índices y metadatos del módulo."""
    name = mnemonic.upper()
    by_mnemonic = getattr(instrucciones, "INSTRUCTION_BY_MNEMONIC", {})
    if isinstance(by_mnemonic, dict) and name in by_mnemonic:
        return by_mnemonic[name]

    for inst_cls in _instruction_classes():
        names = getattr(inst_cls, "MNEMONICS", ())
        if any(str(candidate).upper() == name for candidate in names):
            return inst_cls
    return None


def _known_instruction_mnemonics():
    names = set()
    by_mnemonic = getattr(instrucciones, "INSTRUCTION_BY_MNEMONIC", {})
    if isinstance(by_mnemonic, dict):
        names.update(str(name).upper() for name in by_mnemonic)
    for inst_cls in _instruction_classes():
        names.update(str(name).upper()
                     for name in getattr(inst_cls, "MNEMONICS", ()))
    return names


def _pseudoop_classes():
    """Obtiene pseudo-operaciones desde las listas y tablas disponibles."""
    classes = list(getattr(pseudoops, "PSEUDOOPS", ()) or ())
    classes.extend(getattr(pseudoops, "PRESUDOOPS", ()) or ())
    for registry_name in ("PSEUDOOP_BY_MNEMONIC",):
        registry = getattr(pseudoops, registry_name, None)
        if isinstance(registry, dict):
            classes.extend(registry.values())

    unique_classes = []
    seen = set()
    for pseudoop_cls in classes:
        class_id = id(pseudoop_cls)
        if class_id not in seen:
            unique_classes.append(pseudoop_cls)
            seen.add(class_id)
    return unique_classes


def _pseudoop_class_for(mnemonic: str):
    """Busca una pseudo-operación por mnemónico en sus registros."""
    name = mnemonic.upper()
    by_mnemonic = getattr(pseudoops, "PSEUDOOP_BY_MNEMONIC", {})
    if isinstance(by_mnemonic, dict) and name in by_mnemonic:
        return by_mnemonic[name]

    for pseudoop_cls in _pseudoop_classes():
        names = getattr(pseudoop_cls, "MNEMONICS", ())
        if any(str(candidate).upper() == name for candidate in names):
            return pseudoop_cls
    return None


def _known_pseudoop_mnemonics():
    names = set()
    by_mnemonic = getattr(pseudoops, "PSEUDOOP_BY_MNEMONIC", {})
    if isinstance(by_mnemonic, dict):
        names.update(str(name).upper() for name in by_mnemonic)
    for pseudoop_cls in _pseudoop_classes():
        names.update(str(name).upper()
                     for name in getattr(pseudoop_cls, "MNEMONICS", ()))
    return names


# ---------------------------------------------------------------------------
# Resultado del Ensamblado
# ---------------------------------------------------------------------------

class AssemblyResult:
    """
    Objeto que almacena el resultado del ensamblado de un programa ISA-G27.
    Ofrece interfaces como lista, string y métodos de volcado a diferentes formatos.
    """
    def __init__(self, data_bytes, orig_address, program_bytes, output_file=None, symbol_table=None, modules=None):
        self.bytes = bytearray(data_bytes)
        self.orig_address = orig_address
        self.program_bytes = bytearray(program_bytes)
        self.output_file = output_file
        self.symbol_table = symbol_table or {}
        self.modules = modules or []

    def to_hex_lines(self):
        """Retorna una lista con las líneas en formato hexadecimal (2 caracteres por byte)."""
        return [f"{b:02X}" for b in self.bytes]

    def to_bin_lines(self):
        """Retorna una lista con las líneas en formato binario (8 caracteres por byte)."""
        return [f"{b:08b}" for b in self.bytes]

    def to_int_list(self):
        """Retorna una lista con los valores numéricos enteros de cada byte."""
        return list(self.bytes)

    def __iter__(self):
        return iter(self.to_hex_lines())

    def __len__(self):
        return len(self.bytes)

    def __getitem__(self, idx):
        return self.to_hex_lines()[idx]

    def __str__(self):
        if self.output_file:
            return str(self.output_file)
        return "\n".join(self.to_hex_lines())

    def __repr__(self):
        file_desc = f" file='{self.output_file}'" if self.output_file else ""
        return f"<AssemblyResult bytes={len(self.bytes)} orig={self.orig_address:#06x}{file_desc}>"


# ---------------------------------------------------------------------------
# Estructuras intermedias de Parseo
# ---------------------------------------------------------------------------

class ParsedLine:
    """Representa una línea analizada del código fuente ensamblador."""
    def __init__(self, line_num: int, raw_line: str, label=None, mnemonic=None, operands=None):
        self.line_num = line_num
        self.raw_line = raw_line
        self.label = label
        self.mnemonic = mnemonic.upper() if mnemonic else None
        self.operands = operands or []

        self.is_instruction = False
        self.is_pseudoop = False
        self.address = 0
        self.pad_bytes = 0
        self.pseudoop_result = None

        if self.mnemonic:
            if _instruction_class_for(self.mnemonic) is not None:
                self.is_instruction = True
            elif _pseudoop_class_for(self.mnemonic) is not None:
                self.is_pseudoop = True


class ModuleAST:
    """Representa el conjunto de líneas analizadas y símbolos de un módulo/archivo."""
    def __init__(self, name: str, lines=None, file_path=None, source_label=None):
        self.name = name
        self.lines = lines or []
        self.file_path = file_path
        self.source_label = source_label or file_path or name
        self.symbols = {}
        self.symbol_names = {}
        self.external_imports = {}
        self.external_symbols = {}
        self.start_address = 0
        self.end_address = 0
        self.external_dependencies = []
        self.external_dependency_lines = {}


class AssemblyError(ValueError):
    """Error de ensamblado enriquecido con la ubicación de su línea fuente."""


# ---------------------------------------------------------------------------
# Clase Principal del Ensamblador
# ---------------------------------------------------------------------------

class Assembler:
    """
    Ensamblador de programas para la ISA-G27.

    Traduce código fuente ensamblador a código máquina Little-Endian en bytes,
    resolviendo símbolos internos y referencias externas (.EXTERNAL).
    """

    def __init__(self, por_defecto=None, output_format="hex", output_file=None,
                 include_orig=True, links=False, search_dirs=None):
        """
        Inicializa las opciones por defecto del ensamblador.

        Parámetros:
        - por_defecto (str o dict): Formato de salida inicial o configuración base.
        - output_format (str): 'hex' (por defecto), 'bin', o 'list'/'python'.
        - output_file (str o Path): Ruta del archivo de salida.
        - include_orig (bool): Si es True (por defecto), incluye la dirección de inicio
                               en los dos primeros bytes del archivo ensamblado.
        - links (bool): Si es True, genera un archivo de símbolos (.sym).
        - search_dirs (list): Directorios adicionales donde buscar módulos para .EXTERNAL.
        """
        if isinstance(por_defecto, dict):
            self.output_format = por_defecto.get("output_format", output_format)
            self.output_file = por_defecto.get("output_file", output_file)
            self.include_orig = por_defecto.get("include_orig", include_orig)
            self.links = por_defecto.get("links", links)
            self.search_dirs = por_defecto.get("search_dirs", search_dirs or [])
        elif isinstance(por_defecto, str) and por_defecto in ("hex", "bin", "list", "python"):
            self.output_format = por_defecto
            self.output_file = output_file
            self.include_orig = include_orig
            self.links = links
            self.search_dirs = search_dirs or []
        else:
            self.output_format = output_format
            self.output_file = output_file
            self.include_orig = include_orig
            self.links = links
            self.search_dirs = search_dirs or []

    def __call__(self, source=None, *args, **kwargs):
        """Permite invocar la instancia directamente: Assemble('programa.asm')."""
        if source is None and args:
            source = args[0]
            args = args[1:]
        return self.assemble(source, *args, **kwargs)

    def assemble(self, source, output_format=None, output_file=None,
                 include_orig=None, links=None, search_dirs=None,
                 file_map=None, main_file="main") -> AssemblyResult:
        """
        Ensambla un programa ISA-G27 completo.

        Parámetros:
        - source: Ruta a archivo .asm, texto con el programa, o diccionario de archivos.
        - output_format: 'hex', 'bin', o 'list' (invalida la opción por defecto).
        - output_file: Nombre/ruta del archivo resultante.
        - include_orig: Incluir .ORIG en los primeros dos bytes (bool).
        - links: Generar archivo de símbolos (.sym) (bool).
        - search_dirs: Directorios adicionales donde buscar archivos .EXTERNAL.
        - file_map: Diccionario opcional {'nombre_archivo': 'contenido_asm'}.
        - main_file: Nombre clave del archivo principal en file_map.
        """
        out_fmt = (output_format or self.output_format or "hex").lower()
        inc_orig = self.include_orig if include_orig is None else bool(include_orig)
        gen_links = self.links if links is None else bool(links)

        effective_search_dirs = list(self.search_dirs or [])
        if search_dirs:
            if isinstance(search_dirs, (list, tuple)):
                effective_search_dirs.extend(search_dirs)
            else:
                effective_search_dirs.append(search_dirs)

        input_file_path = None
        source_is_file = False
        main_source_label = None

        # Determinar el tipo de origen (archivo, diccionario o texto directo)
        if isinstance(source, dict):
            f_map = dict(source)
            if not f_map:
                raise ValueError("El diccionario de archivos fuente está vacío")
            norm_target = self._normalize_mod_name(main_file)
            matched_key = None
            for k in f_map:
                if self._normalize_mod_name(k) == norm_target:
                    matched_key = k
                    break
            if matched_key is not None:
                main_code = f_map[matched_key]
                main_name = self._normalize_mod_name(matched_key)
                main_source_label = str(matched_key)
            elif main_file == "main":
                first_key, first_val = next(iter(f_map.items()))
                main_code = first_val
                main_name = self._normalize_mod_name(first_key)
                main_source_label = str(first_key)
            else:
                raise FileNotFoundError(
                    f"No se pudo encontrar el archivo principal '{main_file}' en el diccionario"
                )
            base_dir = os.getcwd()
        elif isinstance(source, (str, Path)) and os.path.isfile(str(source)):
            input_file_path = Path(source).resolve()
            source_is_file = True
            base_dir = str(input_file_path.parent)
            main_name = input_file_path.stem
            main_source_label = str(input_file_path)
            with open(input_file_path, 'r', encoding='utf-8', errors='replace') as f:
                main_code = f.read()
            f_map = dict(file_map or {})
        elif isinstance(source, (str, Path)) and not str(source).count('\n') and Path(str(source)).suffix.lower() == '.asm':
            # Buscar sin sensibilidad a mayúsculas/minúsculas en el directorio padre
            cand_path = Path(source)
            found_ci = self._find_file_case_insensitive(cand_path)
            if found_ci is not None:
                input_file_path = found_ci.resolve()
                source_is_file = True
                base_dir = str(input_file_path.parent)
                main_name = input_file_path.stem
                main_source_label = str(input_file_path)
                with open(input_file_path, 'r', encoding='utf-8', errors='replace') as f:
                    main_code = f.read()
                f_map = dict(file_map or {})
            else:
                raise FileNotFoundError(f"No se pudo encontrar el archivo fuente especificado: {source}")
        else:
            # Cadena de texto directa
            main_code = str(source)
            main_name = "main"
            main_source_label = "<texto>"
            base_dir = os.getcwd()
            f_map = dict(file_map or {})

        # Agregar base_dir y el directorio actual a search_dirs
        if base_dir not in effective_search_dirs:
            effective_search_dirs.insert(0, base_dir)
        project_root = self._find_project_root(base_dir)
        if project_root and project_root not in effective_search_dirs:
            effective_search_dirs.append(project_root)

        # Cargar y parsear módulos principales y externos
        modules_ast = self._load_all_modules(
            main_code=main_code,
            main_name=main_name,
            main_file_path=str(input_file_path) if input_file_path else None,
            main_source_label=main_source_label,
            file_map=f_map,
            search_dirs=effective_search_dirs
        )

        # Primera pasada: asignación de memoria y tabla de símbolos
        symbol_table, orig_address = self._pass_1(modules_ast)
        modules_by_norm = {self._normalize_mod_name(m.name): m for m in modules_ast}

        # Resolver .EXTERNAL cuando ya existen las direcciones de todos los módulos.
        self._assemble_external_pseudoops(modules_ast, modules_by_norm)

        # Segunda pasada: generación de instrucciones y bytes
        emitted_bytes = self._pass_2(modules_ast)

        # Preparar bytes finales con o sin dirección de origen
        if inc_orig:
            orig_high = (orig_address >> 8) & 0xFF
            orig_low = orig_address & 0xFF
            final_bytes = bytearray([orig_high, orig_low]) + emitted_bytes
        else:
            final_bytes = emitted_bytes

        # Determinar nombre del archivo de salida
        actual_output_file = output_file or self.output_file
        if not actual_output_file:
            ext = ".bin" if out_fmt == "bin" else ".hex"
            if source_is_file and input_file_path:
                actual_output_file = str(input_file_path.with_suffix(ext))
            else:
                actual_output_file = f"program{ext}"

        result = AssemblyResult(
            data_bytes=final_bytes,
            orig_address=orig_address,
            program_bytes=emitted_bytes,
            output_file=actual_output_file,
            symbol_table=symbol_table,
            modules=[m.name for m in modules_ast]
        )

        # Escribir archivo de salida si el formato lo requiere
        if out_fmt in ("hex", "bin") or output_file is not None:
            self._write_output_file(result, out_fmt, actual_output_file)

        # Generar archivo de enlaces/símbolos si se solicitó
        if gen_links:
            sym_file_path = str(Path(actual_output_file).with_suffix(".sym"))
            self._write_symbol_file(symbol_table, sym_file_path)

        return result

    # -----------------------------------------------------------------------
    # Carga y Resolución de Módulos Externos (.EXTERNAL)
    # -----------------------------------------------------------------------

    def _find_project_root(self, start_dir: str):
        """Intenta localizar el directorio raíz 'grupo27' ascendiendo en el árbol de carpetas."""
        cur = Path(start_dir).resolve()
        for p in [cur] + list(cur.parents):
            if (p / "grupo27").is_dir():
                return str(p / "grupo27")
            if p.name.lower() == "grupo27":
                return str(p)
        return None

    def _find_file_case_insensitive(self, path: Path):
        """Busca un archivo por nombre insensible a mayúsculas/minúsculas en su carpeta."""
        parent = path.parent if str(path.parent) else Path(".")
        if not parent.is_dir():
            return None
        target_lower = path.name.lower()
        for entry in parent.iterdir():
            if entry.is_file() and entry.name.lower() == target_lower:
                return entry
        return None

    def _is_known_mnemonic(self, token: str) -> bool:
        upper = token.upper()
        return (
            upper in _known_instruction_mnemonics()
            or upper in _known_pseudoop_mnemonics()
        )

    def _run_at_source(self, source_label, line_num, operation, *args, **kwargs):
        """Ejecuta una operación de una línea y adjunta su origen si falla."""
        try:
            return operation(*args, **kwargs)
        except Exception as error:
            if getattr(error, "_assembler_source_context", False):
                raise
            message = f"{source_label}:{line_num}: {error}"
            try:
                contextual_error = type(error)(message)
            except (TypeError, ValueError):
                contextual_error = AssemblyError(message)
            try:
                contextual_error._assembler_source_context = True
            except AttributeError:
                pass
            raise contextual_error from error

    @staticmethod
    def _source_error(source_label, line_num, message):
        return AssemblyError(f"{source_label}:{line_num}: {message}")

    def _is_external_pseudoop(self, pline: ParsedLine) -> bool:
        if not pline.is_pseudoop or not pline.mnemonic:
            return False
        pseudoop_cls = _pseudoop_class_for(pline.mnemonic)
        if pseudoop_cls is None:
            return False
        return any(
            str(field).upper() == "EXT_SYMBOL"
            for fmt in getattr(pseudoop_cls, "FORMATS", ())
            for field in fmt
        )

    def _pseudoop_padding(self, pline: ParsedLine, address: int) -> int:
        pseudoop_cls = _pseudoop_class_for(pline.mnemonic)
        if pseudoop_cls is None:
            raise ValueError(f"Pseudo-operación no registrada: '{pline.mnemonic}'")
        alignment = getattr(pseudoop_cls, "ALIGN", None)
        if alignment is None or alignment is False:
            return 0
        if alignment is not True:
            raise ValueError(
                f"ALIGN inválido para '{pline.mnemonic}': se esperaba True, False o None"
            )
        return address & 1

    def _split_external_ref(self, ref: str) -> tuple:
        """Separa una referencia externa 'archivo-etiqueta' validando ambas partes."""
        text = str(ref).strip()
        if '-' not in text:
            raise ValueError(
                f"Referencia .EXTERNAL inválida '{ref}': "
                "se esperaba el formato 'nombre_de_archivo-etiqueta'"
            )
        dep_file, dep_label = text.split('-', 1)
        dep_file = dep_file.strip()
        dep_label = dep_label.strip()
        if not dep_file or not dep_label:
            raise ValueError(
                f"Referencia .EXTERNAL inválida '{ref}': "
                "se esperaba el formato 'nombre_de_archivo-etiqueta'"
            )
        return dep_file, dep_label

    def _tokenize_line(self, line_num: int, raw_line: str) -> ParsedLine:
        """Divide una línea de código fuente en etiqueta, mnemónico y operandos."""
        cleaned = strip_comments(raw_line)
        if not cleaned:
            return ParsedLine(line_num, raw_line)

        tokens = _split_tokens(cleaned, line_num=line_num)
        if not tokens:
            return ParsedLine(line_num, raw_line)

        # Verificar uso inválido de ':' (espacio antes de ':', ':' suelto o ':' en operandos)
        if tokens[0].startswith(':'):
            raise ValueError(
                f"Sintaxis de etiqueta inválida (':' sin etiqueta) en la línea {line_num}"
            )
        if len(tokens) >= 2 and tokens[1].startswith(':'):
            raise ValueError(
                f"Espacio inválido entre la etiqueta '{tokens[0]}' y ':' en la línea {line_num}"
            )
        for tok in tokens[1:]:
            if not (tok.startswith('"') or tok.startswith("'")) and ':' in tok:
                raise ValueError(
                    f"Uso inesperado de ':' en '{tok}' en la línea {line_num}"
                )

        first_tok = tokens[0]
        is_quoted_first = first_tok.startswith('"') or first_tok.startswith("'")

        if not is_quoted_first and ':' in first_tok:
            lbl_part, rest = first_tok.split(':', 1)
            if not lbl_part or ':' in rest:
                raise ValueError(
                    f"Sintaxis de etiqueta inválida '{first_tok}' en la línea {line_num}"
                )
            label = lbl_part
            rem = ([rest] + tokens[1:]) if rest else tokens[1:]
            if not rem:
                return ParsedLine(line_num, raw_line, label=label, mnemonic=None, operands=[])
            mnemonic_tok = rem[0]
            operands = rem[1:]
        elif not is_quoted_first and self._is_known_mnemonic(first_tok):
            return ParsedLine(
                line_num, raw_line, label=None, mnemonic=first_tok, operands=tokens[1:]
            )
        else:
            if is_quoted_first:
                raise ValueError(
                    f"Token inicial inválido '{first_tok}' en la línea {line_num}"
                )
            label = first_tok
            if len(tokens) == 1:
                return ParsedLine(line_num, raw_line, label=label, mnemonic=None, operands=[])
            mnemonic_tok = tokens[1]
            operands = tokens[2:]

        if not self._is_known_mnemonic(mnemonic_tok):
            raise ValueError(
                f"Instrucción o directiva desconocida '{mnemonic_tok}' en la línea {line_num}"
            )
        return ParsedLine(
            line_num, raw_line, label=label, mnemonic=mnemonic_tok, operands=operands
        )

    def _assemble_pseudoop(self, pline: ParsedLine, resolver=None,
                            allow_unresolved=False, operands=None) -> dict:
        """Invoca la pseudo-operación registrada y valida su descriptor de retorno."""
        pseudoop_cls = _pseudoop_class_for(pline.mnemonic)
        if pseudoop_cls is None:
            raise ValueError(f"Pseudo-operación no registrada: '{pline.mnemonic}'")

        m = pline.mnemonic.upper()
        formats = getattr(pseudoop_cls, "FORMATS", ())
        if not formats:
            raise ValueError(
                f"La pseudo-operación '{pline.mnemonic}' no declara formatos ensamblables"
            )

        matching_formats = [
            (format_idx, pseudo_format)
            for format_idx, pseudo_format in enumerate(formats)
            if str(pseudo_format[0]).upper() in (m, "MNEMONIC")
        ]
        if not matching_formats:
            raise ValueError(
                f"La pseudo-operación '{pline.mnemonic}' no tiene formato declarado para '{m}'"
            )

        operands = list(pline.operands if operands is None else operands)
        defaulted_empty_string = False
        if not operands:
            for _, pseudo_format in matching_formats:
                operand_types = [str(field).upper() for field in pseudo_format[1:]]
                if operand_types == ["COUNT"]:
                    operands = ["1"]
                    break
                if operand_types == ["STRING"]:
                    operands = ['""']
                    defaulted_empty_string = True
                    break

        conversion_errors = []
        selected = None
        for format_idx, pseudo_format in matching_formats:
            operand_types = [str(field).upper() for field in pseudo_format[1:]]
            if len(operand_types) != len(operands):
                if not (operand_types == ["EXT_SYMBOL"] and operands):
                    continue
                operand_types *= len(operands)

            try:
                arguments = [pline.mnemonic]
                for operand_type, operand in zip(operand_types, operands):
                    if operand_type == "STRING":
                        if isinstance(operand, str) and len(operand) >= 2 and operand.startswith('"') and operand.endswith('"'):
                            value = unescape_string(operand[1:-1])
                        elif defaulted_empty_string:
                            value = ""
                        else:
                            raise ValueError(
                                f"se esperaba una cadena entre comillas dobles: '{operand}'"
                            )
                    elif operand_type == "EXT_SYMBOL":
                        value = operand
                    elif operand_type in (
                        "ADDRESS", "COUNT", "VALUE", "VALUE_8", "VALUE_16"
                    ):
                        if is_number(operand):
                            num_val, is_bit_lit = parse_number_info(operand)
                            value = _validate_numeric_operand(
                                operand_type, num_val, is_bit_literal=is_bit_lit
                            )
                        elif resolver is not None and operand_type.startswith("VALUE"):
                            sym_addr = resolver(operand)
                            value = _validate_numeric_operand(
                                operand_type, sym_addr, resolved_symbol=True
                            )
                        elif allow_unresolved and operand_type.startswith("VALUE"):
                            value = 0
                        else:
                            raise ValueError(
                                f"se esperaba un valor numérico válido para {operand_type}: '{operand}'"
                            )
                    else:
                        value = operand
                    arguments.append(value)
            except (KeyError, ValueError) as error:
                conversion_errors.append(error)
                continue
            selected = (format_idx, arguments)
            break

        if selected is None:
            if conversion_errors:
                raise ValueError(
                    f"Operandos inválidos para '{pline.mnemonic}': {conversion_errors[0]}"
                ) from conversion_errors[0]
            expected = sorted({len(fmt) - 1 for _, fmt in matching_formats})
            raise ValueError(
                f"Cantidad de operandos inválida para '{pline.mnemonic}': "
                f"{len(pline.operands)}; se esperaba "
                f"{', '.join(str(count) for count in expected)}"
            )

        format_idx, arguments = selected
        assemble_method = getattr(pseudoop_cls, "s_asemble_method", None)
        if not callable(assemble_method):
            raise TypeError(
                f"La pseudo-operación '{pline.mnemonic}' no implementa s_asemble_method"
            )
        result = assemble_method(format_idx, arguments)
        if not isinstance(result, dict) or "KIND" not in result:
            raise TypeError(
                f"Retorno inválido de '{pline.mnemonic}': se esperaba un descriptor "
                "con KIND"
            )
        if result["KIND"] == "EXTERNAL":
            return result
        if "DATA" not in result:
            raise TypeError(
                f"Retorno inválido de '{pline.mnemonic}': falta DATA para "
                f"KIND='{result['KIND']}'"
            )
        data = result["DATA"]
        if not isinstance(data, list) or any(
            type(value) is not int or not 0 <= value <= 0xFF
            for value in data
        ):
            raise ValueError(
                f"DATA inválido en '{pline.mnemonic}': "
                "se esperaba una lista de enteros entre 0 y 255"
            )
        if result["KIND"] == "ORIG" and len(data) != 2:
            raise ValueError(
                f"DATA inválido en '{pline.mnemonic}': ORIG debe devolver dos bytes"
            )
        return result

    def _load_all_modules(self, main_code: str, main_name: str, main_file_path: str,
                          main_source_label: str, file_map: dict,
                          search_dirs: list) -> list:
        """Carga y analiza el módulo principal y resuelve todas sus dependencias .EXTERNAL."""
        loaded_modules = {}
        queued_norms = {self._normalize_mod_name(main_name)}
        queue = [(main_name, main_code, main_file_path, main_source_label)]
        modules_ast = []

        while queue:
            mod_name, code, f_path, source_label = queue.pop(0)
            norm_name = self._normalize_mod_name(mod_name)
            if norm_name in loaded_modules:
                continue

            parsed_lines = []
            external_deps = []
            external_dependency_lines = {}
            external_imports = {}

            for line_idx, raw_line in enumerate(code.splitlines(), start=1):
                pline = self._run_at_source(
                    source_label, line_idx, self._tokenize_line, line_idx, raw_line
                )
                parsed_lines.append(pline)

                if pline.is_pseudoop:
                    if self._is_external_pseudoop(pline):
                        if not pline.operands:
                            raise self._source_error(
                                source_label, pline.line_num,
                                f"La directiva '{pline.mnemonic}' requiere al menos una referencia "
                            )
                        for op in pline.operands:
                            dep_file, dep_label = self._run_at_source(
                                source_label,
                                pline.line_num,
                                self._split_external_ref,
                                op,
                            )
                            norm_dep = self._normalize_mod_name(dep_file)
                            external_imports[(norm_dep, dep_label.lower())] = f"{dep_file}-{dep_label}"
                            if norm_dep not in {self._normalize_mod_name(d) for d in external_deps}:
                                external_deps.append(dep_file)
                                external_dependency_lines[norm_dep] = pline.line_num
                        continue

                    result = self._run_at_source(
                        source_label,
                        pline.line_num,
                        self._assemble_pseudoop,
                        pline,
                        allow_unresolved=True,
                    )
                    pline.pseudoop_result = result
                    kind = result["KIND"]
                    if kind == "END":
                        break

            mod_ast = ModuleAST(
                name=mod_name,
                lines=parsed_lines,
                file_path=f_path,
                source_label=source_label,
            )
            mod_ast.external_dependencies = external_deps
            mod_ast.external_dependency_lines = external_dependency_lines
            mod_ast.external_imports = external_imports
            loaded_modules[norm_name] = mod_ast
            modules_ast.append(mod_ast)

            # Cargar dependencias externas requeridas
            for dep in external_deps:
                norm_dep = self._normalize_mod_name(dep)
                if norm_dep not in loaded_modules and norm_dep not in queued_norms:
                    line_num = external_dependency_lines[norm_dep]
                    dep_code, dep_path, dep_source_label = self._run_at_source(
                        source_label,
                        line_num,
                        self._resolve_external_file,
                        dep,
                        file_map,
                        search_dirs,
                    )
                    queued_norms.add(norm_dep)
                    queue.append((dep, dep_code, dep_path, dep_source_label))

        return modules_ast

    def _normalize_mod_name(self, name: str) -> str:
        """Normaliza el nombre del módulo para búsquedas insensibles a mayúsculas/minúsculas."""
        s = name.strip().lower()
        if s.endswith(".asm"):
            s = s[:-4]
        return s

    def _resolve_external_file(self, mod_name: str, file_map: dict, search_dirs: list):
        """Busca el contenido de un módulo externo en el mapa de archivos o en el disco."""
        norm = self._normalize_mod_name(mod_name)

        # 1. Buscar en file_map (insensible a mayúsculas/minúsculas y extensión .asm)
        for k, v in file_map.items():
            if self._normalize_mod_name(k) == norm:
                return v, None, str(k)

        # 2. Buscar en directorios de disco (insensible a mayúsculas/minúsculas)
        target_lower = f"{norm}.asm"
        for sdir in search_dirs:
            if not sdir or not os.path.exists(sdir):
                continue
            for root, _, files in os.walk(sdir):
                files_lower = {f.lower(): f for f in files}
                if target_lower in files_lower:
                    full_path = os.path.join(root, files_lower[target_lower])
                    try:
                        with open(full_path, 'r', encoding='utf-8', errors='replace') as f:
                            return f.read(), full_path, full_path
                    except OSError as e:
                        raise OSError(f"Error al leer el archivo externo '{full_path}': {e}")

        raise FileNotFoundError(
            f"No se pudo encontrar el archivo fuente para el módulo externo '{mod_name}'. "
            f"Directorios explorados: {search_dirs}"
        )

    # -----------------------------------------------------------------------
    # Pasada 1: Asignación de Direcciones de Memoria y Tabla de Símbolos
    # -----------------------------------------------------------------------

    def _pass_1(self, modules_ast: list) -> tuple:
        """
        Calcula las direcciones de memoria de cada instrucción/pseudo-op y genera
        la tabla global de símbolos. Maneja alineación y padding de Bytes.
        """
        current_pc = 0x3000
        orig_address = 0x3000
        symbol_table = {}

        for mod_idx, mod in enumerate(modules_ast):
            is_main = (mod_idx == 0)

            mod.start_address = current_pc
            pending_labels = []

            for pline in mod.lines:
                if pline.label:
                    pending_labels.append((pline.label, pline.line_num))

                if pline.mnemonic is None:
                    # Línea que solo contiene etiqueta
                    continue

                if self._is_external_pseudoop(pline):
                    continue

                if pline.is_instruction:
                    data_size = 2
                    pline.pad_bytes = (-current_pc) % 2
                    current_pc += pline.pad_bytes
                else:
                    result = pline.pseudoop_result
                    if result is None:
                        result = self._run_at_source(
                            mod.source_label,
                            pline.line_num,
                            self._assemble_pseudoop,
                            pline,
                            allow_unresolved=True,
                        )
                        pline.pseudoop_result = result
                    kind = result["KIND"]
                    if kind == "END":
                        break
                    if kind == "EXTERNAL":
                        continue
                    if kind == "ORIG":
                        if is_main:
                            orig_data = result["DATA"]
                            orig_address = (orig_data[0] << 8) | orig_data[1]
                            current_pc = orig_address
                            pline.pad_bytes = self._run_at_source(
                                mod.source_label,
                                pline.line_num,
                                self._pseudoop_padding,
                                pline,
                                current_pc,
                            )
                            current_pc += pline.pad_bytes
                            for lbl, lbl_line in pending_labels:
                                self._register_symbol(
                                    symbol_table, mod, lbl, current_pc, lbl_line
                                )
                            pending_labels.clear()
                        continue
                    if kind != "MEMORY":
                        raise self._source_error(
                            mod.source_label,
                            pline.line_num,
                            f"Tipo de pseudo-operación no soportado: '{kind}'",
                        )

                    pline.pad_bytes = self._run_at_source(
                        mod.source_label,
                        pline.line_num,
                        self._pseudoop_padding,
                        pline,
                        current_pc,
                    )
                    current_pc += pline.pad_bytes
                    try:
                        data_size = len(bytearray(result["DATA"]))
                    except (TypeError, ValueError) as error:
                        raise self._source_error(
                            mod.source_label,
                            pline.line_num,
                            f"DATA inválido en '{pline.mnemonic}': {error}",
                        ) from error

                # Asignar dirección a las etiquetas pendientes
                pline.address = current_pc
                for lbl, lbl_line in pending_labels:
                    self._register_symbol(symbol_table, mod, lbl, current_pc, lbl_line)
                pending_labels.clear()

                current_pc += data_size

            # Asignar dirección final a etiquetas al final del módulo
            for lbl, lbl_line in pending_labels:
                self._register_symbol(symbol_table, mod, lbl, current_pc, lbl_line)
            pending_labels.clear()

            mod.end_address = current_pc

        return symbol_table, orig_address

    def _assemble_external_pseudoops(self, modules_ast: list, modules_by_norm: dict):
        """Ensambla cada referencia externa verificando que exista en el módulo destino."""
        for mod in modules_ast:
            for pline in mod.lines:
                if not self._is_external_pseudoop(pline):
                    continue
                if not pline.operands:
                    raise self._source_error(
                        mod.source_label,
                        pline.line_num,
                        f"La directiva '{pline.mnemonic}' requiere al menos una referencia",
                    )

                for reference in pline.operands:
                    dep_file, dep_label = self._run_at_source(
                        mod.source_label,
                        pline.line_num,
                        self._split_external_ref,
                        reference,
                    )
                    norm_dep = self._normalize_mod_name(dep_file)
                    target_mod = modules_by_norm.get(norm_dep)
                    if target_mod is None:
                        raise self._source_error(
                            mod.source_label,
                            pline.line_num,
                            f"Módulo externo '{dep_file}' no cargado para '{reference}'",
                        )
                    lbl_key = dep_label.lower()
                    if lbl_key not in target_mod.symbols:
                        raise self._source_error(
                            mod.source_label,
                            pline.line_num,
                            f"Etiqueta externa '{dep_label}' no encontrada en módulo '{dep_file}' "
                            f"(referenciada desde '{mod.name}')",
                        )
                    address = target_mod.symbols[lbl_key]
                    mod.external_symbols[(norm_dep, lbl_key)] = address
                    pline.pseudoop_result = {"KIND": "EXTERNAL", "DATA": []}

    def _register_symbol(self, symbol_table: dict, mod: ModuleAST, label: str,
                         address: int, line_num: int = None):
        """Registra un símbolo en el ámbito aislado del módulo (insensible a mayúsculas)."""
        key = label.lower()
        if key in mod.symbols:
            raise self._source_error(
                mod.source_label,
                line_num or 1,
                f"Etiqueta duplicada '{label}' en módulo '{mod.name}'",
            )
        mod.symbols[key] = address
        mod.symbol_names[key] = label
        symbol_table[f"{mod.name}-{label}"] = address

    # -----------------------------------------------------------------------
    # Pasada 2: Generación de Código Máquina y Resolución de Operandos
    # -----------------------------------------------------------------------

    def _pass_2(self, modules_ast: list) -> bytearray:
        """Traduce cada línea a bytes de memoria en orden contiguo."""
        emitted_bytes = bytearray()

        for mod in modules_ast:
            resolver = self._create_symbol_resolver(mod)

            for pline in mod.lines:
                if pline.mnemonic is None:
                    continue

                pseudo_result = None
                if pline.is_pseudoop:
                    pseudo_result = pline.pseudoop_result
                    if pseudo_result is None or pseudo_result["KIND"] == "MEMORY":
                        pseudo_result = self._run_at_source(
                            mod.source_label,
                            pline.line_num,
                            self._assemble_pseudoop,
                            pline,
                            resolver=resolver,
                        )
                    kind = pseudo_result["KIND"]
                    if kind == "END":
                        break
                    if kind == "EXTERNAL":
                        continue
                    if kind == "ORIG":
                        emitted_bytes.extend(b"\x00" * pline.pad_bytes)
                        continue
                    if kind != "MEMORY":
                        raise self._source_error(
                            mod.source_label,
                            pline.line_num,
                            f"Tipo de pseudo-operación no soportado: '{kind}'",
                        )

                # 1. Emitir padding de byte si fue requerido para alinear
                if pline.pad_bytes > 0:
                    emitted_bytes.extend(b"\x00" * pline.pad_bytes)

                # 2. Instrucciones de máquina
                if pline.is_instruction:
                    inst_cls = _instruction_class_for(pline.mnemonic)
                    if inst_cls is None:
                        raise self._source_error(
                            mod.source_label,
                            pline.line_num,
                            f"Instrucción no registrada: '{pline.mnemonic}'",
                        )
                    format_idx, args = self._run_at_source(
                        mod.source_label,
                        pline.line_num,
                        self._match_instruction_format,
                        inst_cls,
                        pline.mnemonic,
                        pline.operands,
                        pline.address,
                        resolver,
                    )
                    inst_obj = self._run_at_source(
                        mod.source_label,
                        pline.line_num,
                        inst_cls.s_asemble_method,
                        format_idx,
                        args,
                    )

                    val = int(inst_obj) & 0xFFFF
                    # Formato Little-Endian para palabras de 16 bits:
                    # parte alta en dirección base, parte baja en dirección + 1
                    emitted_bytes.append((val >> 8) & 0xFF)
                    emitted_bytes.append(val & 0xFF)

                elif pseudo_result is not None:
                    try:
                        emitted_bytes.extend(bytearray(pseudo_result["DATA"]))
                    except (TypeError, ValueError) as error:
                        raise self._source_error(
                            mod.source_label,
                            pline.line_num,
                            f"DATA inválido en '{pline.mnemonic}': {error}",
                        ) from error

        return emitted_bytes

    def _create_symbol_resolver(self, mod: ModuleAST):
        """Crea una función de resolución aislada al módulo y sus .EXTERNAL declarados."""
        def resolve(sym_str: str) -> int:
            s = sym_str.strip()
            s_lower = s.lower()

            # 1. Búsqueda local estricta en el módulo actual (insensible a mayúsculas)
            if s_lower in mod.symbols:
                return mod.symbols[s_lower]

            # 2. Búsqueda de referencia externa 'archivo-etiqueta' importada en este módulo
            if '-' in s:
                dep_file, dep_label = s.split('-', 1)
                dep_key = (self._normalize_mod_name(dep_file), dep_label.strip().lower())
                if dep_key in mod.external_imports:
                    if dep_key in mod.external_symbols:
                        return mod.external_symbols[dep_key]
                    raise KeyError(
                        f"Etiqueta externa '{sym_str}' declarada pero no enlazada "
                        f"en el módulo '{mod.name}'"
                    )

            # 3. Expresiones aritméticas simples: ETIQUETA + N o ETIQUETA - N
            m = re.match(r"^(.+)\s*([+-])\s*([^+\-\s]+)$", s)
            if m and is_number(m.group(3).strip()):
                base_sym = m.group(1).strip()
                sign = m.group(2)
                offset_val = parse_number(m.group(3).strip())
                base_addr = resolve(base_sym)
                return (base_addr + offset_val) if sign == '+' else (base_addr - offset_val)

            if '-' in s:
                raise KeyError(
                    f"Etiqueta externa '{sym_str}' no declarada con .EXTERNAL en el módulo '{mod.name}'"
                )

            raise KeyError(
                f"Etiqueta o símbolo no encontrado: '{sym_str}' en módulo '{mod.name}'. "
                f"Símbolos disponibles: {list(mod.symbol_names.values())[:10]}..."
            )
        return resolve

    def _resolve_pcoffset(self, operand_type: str, op_str: str, current_pc: int,
                          resolver) -> int:
        """
        Calcula y valida el desplazamiento relativo al PC (PCOFFSET / BPCOFFSET).
        """
        spec = _OPERAND_SPECS[operand_type]
        bits = spec["bits"]
        is_byte = spec["is_byte"]

        if is_number(op_str):
            val, is_bit_lit = parse_number_info(op_str)
            return _validate_numeric_operand(operand_type, val, is_bit_literal=is_bit_lit)

        target_addr = resolver(op_str)
        pc_next = current_pc + 2
        diff = target_addr - pc_next

        if not is_byte:
            if diff % 2 != 0:
                raise ValueError(
                    f"Destino desalineado para {operand_type}: '{op_str}' "
                    f"(destino={target_addr:#06x}, pc+2={pc_next:#06x}, diff={diff})"
                )
            offset = diff // 2
        else:
            offset = diff

        return _validate_numeric_operand(operand_type, offset, is_bit_literal=False)

    def _match_instruction_format(self, inst_cls, mnemonic: str, operands: list,
                                  current_pc: int, resolver) -> tuple:
        """
        Selecciona un formato compatible desde FORMATS en instrucciones.py y valida operandos.
        """
        m = mnemonic.upper()
        formats = getattr(inst_cls, "FORMATS", ())
        if not formats:
            raise ValueError(f"La instrucción '{m}' no declara formatos ensamblables")

        matching_formats = []
        for format_idx, inst_format in enumerate(formats):
            fmt_mnemonic = str(inst_format[0]).upper()
            if fmt_mnemonic in (m, "MNEMONIC"):
                matching_formats.append((format_idx, inst_format))

        if not matching_formats:
            raise ValueError(
                f"La instrucción '{m}' no tiene un formato declarado en {inst_cls.__name__}.FORMATS"
            )

        conversion_errors = []
        for format_idx, inst_format in matching_formats:
            operand_types = [str(field).upper() for field in inst_format[1:]]
            if len(operand_types) != len(operands):
                continue
            parsed = [m]
            failed = False
            for op_idx, (operand_type, operand) in enumerate(zip(operand_types, operands)):
                try:
                    parsed.append(self._parse_format_operand(
                        operand_type, operand, current_pc, resolver
                    ))
                except (KeyError, ValueError) as error:
                    score = (op_idx, 0 if (operand_type == "REG" and is_number(operand)) else 1)
                    conversion_errors.append((score, error))
                    failed = True
                    break
            if not failed:
                return format_idx, parsed

        if conversion_errors:
            best_error = max(conversion_errors, key=lambda item: item[0])[1]
            raise ValueError(
                f"Operandos inválidos para '{m}': {best_error}"
            ) from best_error

        expected = sorted({len(fmt) - 1 for _, fmt in matching_formats})
        raise ValueError(
            f"Cantidad de operandos inválida para '{m}': {len(operands)}; "
            f"se esperaba {', '.join(str(count) for count in expected)}"
        )

    def _parse_format_operand(self, operand_type: str, operand: str,
                              current_pc: int, resolver) -> int:
        """Convierte y valida un operando según el tipo declarado en FORMATS."""
        if operand_type == "REG":
            return parse_register(operand)
        spec = _OPERAND_SPECS.get(operand_type)
        if spec is None:
            raise ValueError(f"Tipo de operando no reconocido en FORMATS: '{operand_type}'")
        if spec["kind"] == "pcoffset":
            return self._resolve_pcoffset(
                operand_type, operand, current_pc, resolver=resolver
            )
        if is_number(operand):
            num_val, is_bit_lit = parse_number_info(operand)
            return _validate_numeric_operand(operand_type, num_val, is_bit_literal=is_bit_lit)
        raise ValueError(f"se esperaba un valor numérico válido para {operand_type}: '{operand}'")

    # -----------------------------------------------------------------------
    # Escritura de Archivos de Salida
    # -----------------------------------------------------------------------

    def _write_output_file(self, result: AssemblyResult, output_format: str, output_file: str):
        """Escribe el archivo resultante en disco (.hex o .bin)."""
        parent = os.path.dirname(os.path.abspath(output_file))
        if parent and not os.path.exists(parent):
            os.makedirs(parent, exist_ok=True)

        if output_format == "bin":
            lines = result.to_bin_lines()
        else: # "hex" por defecto
            lines = result.to_hex_lines()

        with open(output_file, 'w', encoding='utf-8') as f:
            for line in lines:
                f.write(line + '\n')

    def _write_symbol_file(self, symbol_table: dict, sym_file_path: str):
        """Genera un archivo de tabla de símbolos legible (.sym)."""
        parent = os.path.dirname(os.path.abspath(sym_file_path))
        if parent and not os.path.exists(parent):
            os.makedirs(parent, exist_ok=True)

        with open(sym_file_path, 'w', encoding='utf-8') as f:
            f.write("// Symbol Table - ISA-G27 Assembler\n")
            f.write(f"// {'Symbol Name':<32} {'Address':<8}\n")
            f.write(f"// {'-' * 32} {'-' * 8}\n")
            for name in sorted(symbol_table.keys()):
                addr = symbol_table[name]
                f.write(f"{name:<34} x{addr:04X}\n")


# ---------------------------------------------------------------------------
# Instancia Global por Defecto
# ---------------------------------------------------------------------------

Assemble = Assembler()


# ---------------------------------------------------------------------------
# Interfaz de Línea de Comandos (CLI)
# ---------------------------------------------------------------------------

def main():
    """Punto de entrada de línea de comandos para el ensamblador."""
    parser = argparse.ArgumentParser(
        description="Ensamblador para la arquitectura ISA-G27 (Little-Endian, direccionada por Byte)"
    )
    parser.add_argument("source", help="Archivo ensamblador (.asm) o cadena con el código fuente")
    parser.add_argument("-o", "--output", dest="output_file", default=None,
                        help="Ruta del archivo de salida (.hex, .bin)")
    parser.add_argument("-f", "--format", dest="format", choices=["hex", "bin", "list", "python"],
                        default="hex", help="Formato de salida (hex, bin, list). Por defecto: hex")
    parser.add_argument("--no-orig", dest="no_orig", action="store_true",
                        help="No incluir la dirección de inicio .ORIG en los primeros 2 bytes de salida")
    parser.add_argument("-s", "--sym", "--links", dest="links", action="store_true",
                        help="Generar archivo de tabla de símbolos (.sym)")
    parser.add_argument("-I", "--include", dest="include_dirs", action="append", default=[],
                        help="Directorios adicionales para buscar módulos externos (.EXTERNAL)")

    args = parser.parse_args()

    asm = Assembler(
        output_format=args.format,
        output_file=args.output_file,
        include_orig=not args.no_orig,
        links=args.links,
        search_dirs=args.include_dirs
    )

    try:
        res = asm(args.source)
        if args.format in ("list", "python"):
            print(res.to_hex_lines())
        else:
            print(f"Ensamblado exitoso: '{res.output_file}' ({len(res.bytes)} bytes, .ORIG {res.orig_address:#06x})")
            if args.links:
                sym_path = str(Path(res.output_file).with_suffix(".sym"))
                print(f"Archivo de símbolos generado: '{sym_path}'")
    except Exception as e:
        print(f"Error durante el ensamblado: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
