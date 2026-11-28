"""Two-pass assembler and module linker for LC-3 and Lab 3c."""
from __future__ import annotations

import argparse
import ast
from dataclasses import dataclass, field
from hashlib import sha256
import json
from pathlib import Path
import re


class AssemblyError(ValueError):
    """Invalid or unresolved assembly source."""


@dataclass
class Statement:
    number: int
    label: str | None
    operation: str
    arguments: tuple[str, ...]
    address: int = 0
    size: int = 0


@dataclass
class Module:
    path: Path
    statements: list[Statement]
    imports: dict[str, tuple[Module, str]] = field(default_factory=dict)
    labels: dict[str, int] = field(default_factory=dict)
    start: int = 0
    stop: int = 0

    @property
    def name(self) -> str:
        return self.path.stem.upper()


@dataclass(frozen=True)
class Assembly:
    image: bytes
    origin: int
    symbols: dict[str, int]
    ranges: dict[str, tuple[int, int]]
    instruction_addresses: tuple[int, ...] = ()


_PCREL = {"LD": 2, "ST": 3, "LDI": 10, "STI": 11, "LEA": 14}
_WORD_MEMORY = {"LDR": 6, "STR": 7}
_BYTE_MEMORY = {"LDBL": 22, "LDBH": 23, "STBL": 24, "STBH": 25}
_TRAPS = dict(zip(("GETC", "OUT", "PUTS", "IN", "PUTSP", "HALT", "PUTSB"), range(0x20, 0x27)))
_ALU = {"ADD": 0, "AND": 1, "SUB": 2, "XOR": 3}
_EXTRA_ALU = {"ADC": 0, "SBC": 1, "OR": 2}
_SHIFTS = {"SHL": 0, "LSR": 1, "ASR": 2}
_WIDE_ARITHMETIC = {"MULW", "MULUW", "DIVW", "DIVUW"}
_V2_OPS = {"LDRX", "STR.POST"}
_DIRECTIVES = {".ORIG", ".FILL", ".BLKW", ".STRINGZ", ".BYTE", ".ASCIZ", ".ALIGN", ".END", ".EXTERNAL"}
_OPS = (
    _PCREL.keys() | _WORD_MEMORY.keys() | _BYTE_MEMORY.keys() | _TRAPS.keys()
    | _ALU.keys() | _EXTRA_ALU.keys() | _SHIFTS.keys() | {name + "W" for name in _SHIFTS}
    | _WIDE_ARITHMETIC | {"RTI", "NOT", "JSR", "JSRR", "JMP", "RET", "TRAP", "NOP", "SEXT8"}
)
_BRANCH = re.compile(r"BR[NZP]*\Z")
_LABEL = re.compile(r"[A-Za-z_][A-Za-z_0-9]*\Z")
_REGISTER = re.compile(r"R([0-7])\Z", re.IGNORECASE)
_TOKEN = re.compile(r'"(?:\\.|[^"\\])*"|;.*|[^\s,;"]+|[^\s,;]')
_NUMBER = re.compile(r"#?([+-]?)(?:(?:x|0x)([0-9a-f]+)|(?:b|0b)([01]+)|([0-9]+))\Z", re.IGNORECASE)
_FAR = {"LD": 28, "ST": 29, "LEA": 30, "BR": 31}
_ZERO_ARITY = {"RTI", "RET", "NOP"} | _TRAPS.keys()
_NEW_REGISTER_OPS = _BYTE_MEMORY.keys() | _EXTRA_ALU.keys() | _SHIFTS.keys() | {
    "SUB", "XOR", "SEXT8", "SHLW", "LSRW", "ASRW", "LDRX"
} | _WIDE_ARITHMETIC


def _error(module: Module, statement: Statement, message: str) -> AssemblyError:
    return AssemblyError(f"{module.path.name}:{statement.number}: {message}")


def _arity(arguments: tuple[str, ...], expected: int) -> None:
    if len(arguments) != expected:
        raise AssemblyError(f"se esperaban {expected} operandos y se recibieron {len(arguments)}")


def _number(token: str) -> int | None:
    match = _NUMBER.fullmatch(token)
    if match is None:
        return None
    sign, hexadecimal, binary, decimal = match.groups()
    if hexadecimal is not None:
        value = int(hexadecimal, 16)
    elif binary is not None:
        value = int(binary, 2)
    else:
        value = int(decimal)
    return -value if sign == "-" else value


def _integer(token: str) -> int:
    value = _number(token)
    if value is None:
        raise AssemblyError(f"se esperaba un entero: {token}")
    return value


def _signed(value: int, width: int) -> int:
    if not -(1 << (width - 1)) <= value < 1 << (width - 1):
        raise AssemblyError(f"{value} fuera de rango para {width} bits con signo")
    return value & ((1 << width) - 1)


def _unsigned(value: int, width: int) -> int:
    if not 0 <= value < 1 << width:
        raise AssemblyError(f"{value} fuera de rango para {width} bits sin signo")
    return value


def _data(value: int, width: int) -> int:
    if not -(1 << (width - 1)) <= value < 1 << width:
        raise AssemblyError(f"{value} fuera de rango para un dato de {width} bits")
    return value & ((1 << width) - 1)


def _register(token: str) -> int:
    match = _REGISTER.fullmatch(token)
    if match is None:
        raise AssemblyError(f"registro inválido: {token}")
    return int(match[1])


def _pair(token: str) -> int:
    register = _register(token)
    if register % 2:
        raise AssemblyError(f"un par debe comenzar en R0, R2, R4 o R6: {token}")
    return register // 2


def _string(token: str) -> bytes:
    try:
        value = ast.literal_eval(token)
        if isinstance(value, str):
            return value.encode("latin-1") + b"\0"
    except (SyntaxError, ValueError):
        pass
    raise AssemblyError("se esperaba una cadena entre comillas con caracteres Latin-1")


def _parse(path: Path, v2: bool) -> Module:
    module = Module(path, [])
    operations = _OPS | _V2_OPS if v2 else _OPS
    try:
        lines = path.read_text(encoding="utf-8-sig").splitlines()
    except UnicodeDecodeError:
        lines = path.read_text(encoding="latin-1").splitlines()
    for number, line in enumerate(lines, 1):
        tokens = [token for token in _TOKEN.findall(line) if not token.startswith(";")]
        if not tokens:
            continue
        first = tokens[0].upper()
        label = None
        # Legacy sources can use names added to the Lab 3c mnemonic set as labels.
        second = tokens[1].upper() if len(tokens) > 1 else ""
        legacy_label = first in _NEW_REGISTER_OPS and (second in operations or second in _DIRECTIVES)
        if legacy_label or first.endswith(":") or not (first in operations or first.startswith(".") or _BRANCH.fullmatch(first)):
            label = tokens.pop(0).removesuffix(":").upper()
            if not _LABEL.fullmatch(label):
                if label in _V2_OPS and not v2:
                    raise AssemblyError(f"{path.name}:{number}: {label} requiere el destino lab3c-v2")
                raise AssemblyError(f"{path.name}:{number}: etiqueta inválida: {label}")
        operation = tokens.pop(0).upper() if tokens else ""
        statement = Statement(number, label, operation, tuple(tokens))
        if operation and not (operation in operations or operation in _DIRECTIVES or _BRANCH.fullmatch(operation)):
            if not v2 and (operation in _V2_OPS or label in _V2_OPS):
                mnemonic = operation if operation in _V2_OPS else label
                raise _error(module, statement, f"{mnemonic} requiere el destino lab3c-v2")
            raise _error(module, statement, f"operación desconocida: {operation}")
        module.statements.append(statement)
        if operation == ".END":
            break
    return module


def _module_index(source: Path, directories: tuple[Path, ...]) -> dict[str, Path]:
    index: dict[str, Path] = {}
    for directory in (*directories, source.parent):
        for path in sorted(Path(directory).iterdir()):
            if path.is_file() and path.suffix.lower() == ".asm":
                index.setdefault(path.stem.upper(), path.resolve())
    index[source.stem.upper()] = source
    return index


def _load_modules(
    source: Path,
    directories: tuple[Path, ...],
    aliases: dict[str, str],
    v2: bool,
) -> list[Module]:
    available = _module_index(source, directories)
    loaded: dict[Path, Module] = {}

    def load(path: Path) -> Module:
        if path in loaded:
            return loaded[path]
        module = _parse(path, v2)
        loaded[path] = module
        for statement in module.statements:
            if statement.operation != ".EXTERNAL":
                continue
            try:
                _arity(statement.arguments, 1)
                reference = statement.arguments[0].upper()
                module_name, separator, symbol = reference.rpartition("-")
                if not separator or not module_name or not _LABEL.fullmatch(symbol):
                    raise AssemblyError(f"referencia externa inválida: {reference}")
                module_name = aliases.get(module_name, module_name)
                dependency = available.get(module_name)
                if dependency is None:
                    matches = [path for name, path in available.items() if re.sub(r"^G\d+_", "", name) == module_name]
                    if len(matches) != 1:
                        issue = "ambiguo" if matches else "no encontrado"
                        raise AssemblyError(f"módulo {issue}: {module_name}")
                    dependency = matches[0]
                module.imports[reference] = (load(dependency), symbol)
            except AssemblyError as error:
                raise _error(module, statement, str(error)) from error
        return module

    load(source)
    return list(loaded.values())


def _statement_size(statement: Statement, unit: int, address: int) -> int:
    operation, symbols = statement.operation, statement.arguments
    if not operation:
        return 0
    if operation in {".END", ".EXTERNAL"}:
        _arity(symbols, int(operation == ".EXTERNAL"))
        return 0
    if operation == ".ALIGN":
        _arity(symbols, 1)
        boundary = _integer(symbols[0])
        if boundary <= 0 or boundary & (boundary - 1):
            raise AssemblyError(".ALIGN requiere una potencia de dos positiva")
        return -address % boundary
    if operation == ".FILL":
        _arity(symbols, 1)
        return unit
    if operation == ".BLKW":
        _arity(symbols, 1)
        count = _integer(symbols[0])
        if count < 0:
            raise AssemblyError(".BLKW requiere una cantidad no negativa")
        return unit * count
    if operation in {".STRINGZ", ".ASCIZ"}:
        _arity(symbols, 1)
        return len(_string(symbols[0])) * (unit if operation == ".STRINGZ" else 1)
    if operation == ".BYTE":
        if not symbols:
            raise AssemblyError(".BYTE requiere al menos un dato")
        return len(symbols)
    return unit


def _layout(modules: list[Module], unit: int) -> int:
    origin = 0x3000
    entry = modules[0]
    declarations = [statement for statement in entry.statements if statement.operation == ".ORIG"]
    if declarations:
        statement = declarations[0]
        try:
            _arity(statement.arguments, 1)
            origin = _unsigned(_integer(statement.arguments[0]), 16)
        except AssemblyError as error:
            raise _error(entry, statement, str(error)) from error
    if origin % unit:
        raise AssemblyError("la dirección de origen del programa debe estar alineada")

    address = origin
    for module in modules:
        address += -address % unit
        module.start = address
        pending: list[Statement] = []
        saw_content = False
        saw_origin = False
        for statement in module.statements:
            operation = statement.operation
            try:
                if operation == ".ORIG":
                    if statement.label or saw_content or saw_origin:
                        raise AssemblyError(".ORIG debe aparecer una sola vez al comienzo del módulo")
                    _arity(statement.arguments, 1)
                    _unsigned(_integer(statement.arguments[0]), 16)
                    saw_origin = True
                    continue
                if statement.label:
                    pending.append(statement)
                if not operation or operation == ".EXTERNAL":
                    continue
                if operation in {".BYTE", ".ASCIZ"} and unit == 1:
                    raise AssemblyError(f"{operation} requiere el destino lab3c")
                if operation not in {".BYTE", ".ASCIZ", ".ALIGN", ".END"}:
                    address += -address % unit
                statement.address = address
                statement.size = _statement_size(statement, unit, address)
                if address + statement.size > 0x10000:
                    raise AssemblyError("la imagen supera el espacio de direcciones de 16 bits")
                label_address = address + statement.size if operation == ".ALIGN" else address
                _bind(module, pending, label_address)
                pending.clear()
                address += statement.size
                saw_content |= operation != ".END"
            except AssemblyError as error:
                raise _error(module, statement, str(error)) from error
        _bind(module, pending, address)
        module.stop = address
    return origin


def _bind(module: Module, statements: list[Statement], address: int) -> None:
    for statement in statements:
        label = statement.label
        if label in module.labels:
            raise AssemblyError(f"etiqueta duplicada: {label}")
        module.labels[label] = address


def _value(token: str, module: Module) -> int:
    symbol = token.upper()
    if symbol in module.labels:
        return module.labels[symbol]
    if symbol in module.imports:
        dependency, exported_label = module.imports[symbol]
        if exported_label not in dependency.labels:
            raise AssemblyError(f"{dependency.name} no define {exported_label}")
        return dependency.labels[exported_label]
    number = _number(token)
    if number is None:
        raise AssemblyError(f"símbolo no definido: {token}")
    return number


def _offset(token: str, module: Module, statement: Statement, unit: int) -> int:
    symbol = token.upper()
    number = _number(token)
    if number is not None and symbol not in module.labels and symbol not in module.imports:
        return number
    target = _unsigned(_value(token, module), 16)
    if target % unit:
        raise AssemblyError(f"dirección relativa sin alinear: {token}")
    delta = (target - (statement.address + unit)) & 0xFFFF
    if delta & 0x8000:
        delta -= 0x10000
    return delta // unit


def _relative_word(operation: str, opcode: int, prefix: int, offset: int, unit: int) -> int:
    if unit == 1:
        return (opcode << 12) | (prefix << 9) | _signed(offset, 9)
    if operation in _FAR and not -128 <= offset <= 127:
        opcode = _FAR[operation]
        encoded = _signed(offset, 9) & 0xFF
    else:
        encoded = _signed(offset, 8)
    return (opcode << 11) | (prefix << 8) | encoded


def _shift_amount(token: str) -> int:
    if _REGISTER.fullmatch(token):
        return 0x10 | _register(token)
    return _unsigned(_integer(token), 4)


def _instruction(module: Module, statement: Statement, unit: int) -> int:
    operation, args = statement.operation, statement.arguments
    original = unit == 1
    shift = 12 if original else 11
    dst_shift, base_shift = shift - 3, shift - 6
    if operation == "LDRX":
        _arity(args, 3)
        destination, base, index = map(_register, args)
        return 0x2200 | (destination << 6) | (base << 3) | index
    if operation == "STR.POST":
        _arity(args, 2)
        source, base = map(_register, args)
        return 0x4201 | (source << 6) | (base << 3)
    if operation in _ZERO_ARITY:
        _arity(args, 0)
        if operation in _TRAPS:
            if original and operation == "PUTSB":
                raise AssemblyError("PUTSB requiere el destino lab3c")
            return (15 << shift) | _TRAPS[operation]
        return {"NOP": 0, "RET": (12 << shift) | (7 << base_shift), "RTI": 8 << shift}[operation]
    if _BRANCH.fullmatch(operation):
        _arity(args, 1)
        mask = sum(bit for flag, bit in zip("NZP", (4, 2, 1)) if flag in operation[2:])
        return _relative_word("BR", 0, mask or 7, _offset(args[0], module, statement, unit), unit)
    if operation in _PCREL:
        _arity(args, 2)
        offset = _offset(args[1], module, statement, unit)
        return _relative_word(operation, _PCREL[operation], _register(args[0]), offset, unit)
    if operation in {"JMP", "JSRR", "JSR", "TRAP"}:
        _arity(args, 1)
        if operation == "TRAP":
            return (15 << shift) | _unsigned(_integer(args[0]), 8 if original else 7)
        if operation == "JSR":
            return (4 << shift) | (1 << (shift - 1)) | _signed(_offset(args[0], module, statement, unit), shift - 1)
        opcode = 12 if operation == "JMP" else 4
        return (opcode << shift) | (_register(args[0]) << base_shift)
    if operation in {"NOT", "SEXT8"}:
        _arity(args, 2)
        opcode = 9 if operation == "NOT" else 26
        if original and operation == "SEXT8":
            raise AssemblyError("SEXT8 requiere el destino lab3c")
        registers = (_register(args[0]) << dst_shift) | (_register(args[1]) << base_shift)
        trailing = (1 << base_shift) - 1 if operation == "NOT" else 0
        return (opcode << shift) | registers | trailing
    if operation in _WORD_MEMORY or operation in _BYTE_MEMORY:
        _arity(args, 3)
        if operation in _BYTE_MEMORY and original:
            raise AssemblyError(f"{operation} requiere el destino lab3c")
        opcode = (_WORD_MEMORY | _BYTE_MEMORY)[operation]
        registers = (_register(args[0]) << dst_shift) | (_register(args[1]) << base_shift)
        return (opcode << shift) | registers | _signed(_integer(args[2]), base_shift)
    if operation in _ALU or operation in _EXTRA_ALU:
        _arity(args, 3)
        base = (_register(args[0]) << dst_shift) | (_register(args[1]) << base_shift)
        register = _REGISTER.fullmatch(args[2])
        if operation in {"ADD", "AND"} and (original or register is None):
            opcode = 1 if operation == "ADD" else 5
            if register:
                operand = int(register[1])
            else:
                operand = (32 if original else 0) | _signed(_integer(args[2]), 5)
            return (opcode << shift) | base | operand
        if original:
            raise AssemblyError(f"{operation} requiere el destino lab3c")
        opcode, variant = (13, _ALU[operation]) if operation in _ALU else (27, _EXTRA_ALU[operation])
        return (opcode << 11) | base | (_register(args[2]) << 2) | variant
    if original:
        raise AssemblyError(f"{operation} requiere el destino lab3c")
    _arity(args, 3)
    if operation in _SHIFTS:
        opcode = 16 + _SHIFTS[operation]
        return (opcode << 11) | (_register(args[0]) << 8) | (_register(args[1]) << 5) | _shift_amount(args[2])
    if operation.endswith("W") and operation[:-1] in _SHIFTS:
        registers = (_pair(args[0]) << 9) | (_pair(args[1]) << 7)
        operation_bits = _SHIFTS[operation[:-1]] << 5
        return (19 << 11) | registers | operation_bits | _shift_amount(args[2])
    if operation in {"MULW", "MULUW"}:
        registers = (_pair(args[0]) << 9) | (_register(args[1]) << 6) | (_register(args[2]) << 3)
        return (20 << 11) | registers | (4 if operation == "MULUW" else 0)
    if operation in {"DIVW", "DIVUW"}:
        registers = (_pair(args[0]) << 9) | (_pair(args[1]) << 7) | (_register(args[2]) << 4)
        return (21 << 11) | registers | (8 if operation == "DIVUW" else 0)
    raise AssemblyError(f"operación desconocida: {operation}")


def _word(value: int) -> bytes:
    return value.to_bytes(2, "big")


def _emit(modules: list[Module], origin: int, unit: int) -> bytes:
    scale = 2 // unit
    payload = bytearray((modules[-1].stop - origin) * scale)
    for module in modules:
        for statement in module.statements:
            operation, args = statement.operation, statement.arguments
            if not statement.size or operation in {".BLKW", ".ALIGN"}:
                continue
            try:
                if operation == ".FILL":
                    data = _word(_data(_value(args[0], module), 16))
                elif operation == ".BYTE":
                    data = bytes(_data(_value(token, module), 8) for token in args)
                elif operation in {".ASCIZ", ".STRINGZ"}:
                    characters = _string(args[0])
                    data = characters if operation == ".ASCIZ" else b"".join(_word(char) for char in characters)
                else:
                    data = _word(_instruction(module, statement, unit))
            except AssemblyError as error:
                raise _error(module, statement, str(error)) from error
            position = (statement.address - origin) * scale
            payload[position:position + len(data)] = data
    return _word(origin) + payload


def assemble(
    source: str | Path,
    *,
    target: str = "lab3c",
    module_dirs: tuple[Path, ...] = (),
    aliases: dict[str, str] | None = None,
) -> Assembly:
    """Assemble and link reachable modules. The image starts with a two-byte origin."""
    if target not in {"lab3c", "lab3c-v2", "lc3"}:
        raise AssemblyError(f"destino desconocido: {target}")
    unit = 1 if target == "lc3" else 2
    normalized_aliases = {key.upper(): value.upper() for key, value in (aliases or {}).items()}
    modules = _load_modules(Path(source).resolve(), tuple(module_dirs), normalized_aliases, v2=target == "lab3c-v2")
    origin = _layout(modules, unit)
    for module in modules:
        for reference, (dependency, label) in module.imports.items():
            if label not in dependency.labels:
                raise AssemblyError(f"{module.path.name}: referencia {reference} sin definir")
    return Assembly(
        _emit(modules, origin, unit),
        origin,
        {f"{module.name}-{label}": value for module in modules for label, value in module.labels.items()},
        {module.name: (module.start, module.stop) for module in modules},
        tuple(
            statement.address
            for module in modules
            for statement in module.statements
            if statement.size and statement.operation not in _DIRECTIVES
        ),
    )


def write_map(path: Path, assembly: Assembly, target: str) -> None:
    """Write an optional map identifying instructions and the image they came from."""
    content = {
        "target": target,
        "origin": assembly.origin,
        "sha256": sha256(assembly.image).hexdigest(),
        "symbols": assembly.symbols,
        "ranges": assembly.ranges,
        "instruction_addresses": assembly.instruction_addresses,
    }
    path.write_text(json.dumps(content, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="archivo ensamblador principal")
    parser.add_argument("-o", "--output", required=True, type=Path, help="imagen binaria")
    parser.add_argument("-I", "--module-dir", action="append", type=Path, default=[], help="directorio de búsqueda de módulos")
    parser.add_argument("--alias", action="append", default=[], metavar="NOMBRE=MÓDULO")
    parser.add_argument("--target", choices=("lab3c", "lab3c-v2", "lc3"), default="lab3c")
    parser.add_argument("--map", type=Path, help="mapa JSON de símbolos y módulos")
    args = parser.parse_args()
    try:
        aliases = dict(item.split("=", 1) for item in args.alias)
        result = assemble(args.source, target=args.target, module_dirs=tuple(args.module_dir), aliases=aliases)
        args.output.write_bytes(result.image)
        if args.map:
            write_map(args.map, result, args.target)
    except (OSError, ValueError) as error:
        parser.exit(1, f"error: {error}\n")


if __name__ == "__main__":
    main()
