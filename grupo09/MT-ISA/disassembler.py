"""Lossless disassembly of binary images for LC-3 and Lab 3c."""

from collections.abc import Collection


_RELATIVE = {2: "LD", 3: "ST", 10: "LDI", 11: "STI", 14: "LEA"}
_FAR_RELATIVE = {28: "LD", 29: "ST", 30: "LEA", 31: "BR"}
_TRAPS = ("GETC", "OUT", "PUTS", "IN", "PUTSP", "HALT", "PUTSB")
_SHIFT = ("SHL", "LSR", "ASR")
_ALU = {13: ("ADD", "AND", "SUB", "XOR"), 27: ("ADC", "SBC", "OR", None)}
_MEMORY = {6: "LDR", 7: "STR", 22: "LDBL", 23: "LDBH", 24: "STBL", 25: "STBH"}


def _signed(value: int, width: int) -> int:
    top = 1 << (width - 1)
    field = value & (2 * top - 1)
    return (field ^ top) - top


def _reg(word: int, position: int) -> str:
    return f"R{(word >> position) & 7}"


def _pair(word: int, position: int) -> str:
    return f"R{2 * ((word >> position) & 3)}"


def _branch(word: int, mask: int, offset: int) -> str | None:
    if not mask:
        return "NOP" if word == 0 else None
    flags = "".join(flag for bit, flag in zip((4, 2, 1), "nzp") if mask & bit)
    return f"BR{flags} #{offset}"


def _shift_instruction(word: int, opcode: int) -> str | None:
    if word & 0x10:
        if word & 8:
            return None
        amount = _reg(word, 0)
    else:
        amount = f"#{word & 15}"
    if opcode == 19:
        kind = (word >> 5) & 3
        if kind == 3:
            return None
        return f"{_SHIFT[kind]}W {_pair(word, 9)}, {_pair(word, 7)}, {amount}"
    return f"{_SHIFT[opcode - 16]} {_reg(word, 8)}, {_reg(word, 5)}, {amount}"


def _decode(word: int, original: bool, *, v2: bool = False) -> str | None:
    opcode_shift = 12 if original else 11
    dst_shift = opcode_shift - 3
    base_shift = opcode_shift - 6
    base_mask = 7 << base_shift
    opcode = word >> opcode_shift
    fields = word & ((1 << opcode_shift) - 1)
    dst = _reg(word, dst_shift)
    base = _reg(word, base_shift)
    offset = _signed(word, dst_shift)

    if v2:
        if word & 0xFE00 == 0x2200:
            return f"LDRX {_reg(word, 6)}, {_reg(word, 3)}, {_reg(word, 0)}"
        if word & 0xFE07 == 0x4201:
            return f"STR.POST {_reg(word, 6)}, {_reg(word, 3)}"
    if opcode == 0:
        return _branch(word, (word >> dst_shift) & 7, offset)
    if opcode in _RELATIVE:
        return f"{_RELATIVE[opcode]} {dst}, #{offset}"
    if opcode in (1, 5):
        operation = "ADD" if opcode == 1 else "AND"
        if original and not fields & 32:
            if fields & 24:
                return None
            operand = _reg(word, 0)
        else:
            operand = f"#{_signed(word, 5)}"
        return f"{operation} {dst}, {base}, {operand}"
    if opcode == 4:
        if fields & (1 << (opcode_shift - 1)):
            return f"JSR #{_signed(fields, opcode_shift - 1)}"
        return f"JSRR {base}" if not fields & ~base_mask else None
    if opcode == 8:
        return "RTI" if fields == 0 else None
    if opcode == 9:
        mask = (1 << base_shift) - 1
        return f"NOT {dst}, {base}" if fields & mask == mask else None
    if opcode == 12:
        if fields & ~base_mask:
            return None
        return "RET" if base == "R7" else f"JMP {base}"
    if opcode == 15:
        width = 8 if original else 7
        if fields >= (1 << width):
            return None
        if 0x20 <= fields <= (0x25 if original else 0x26):
            return _TRAPS[fields - 0x20]
        return f"TRAP x{fields:02X}"
    if opcode in (6, 7) or (not original and opcode in _MEMORY):
        return f"{_MEMORY[opcode]} {dst}, {base}, #{_signed(word, base_shift)}"
    if original:
        return None

    if opcode in _ALU:
        operation = _ALU[opcode][word & 3]
        return f"{operation} {dst}, {base}, {_reg(word, 2)}" if operation else None
    if 16 <= opcode <= 19:
        return _shift_instruction(word, opcode)
    if opcode == 20:
        if fields & 3:
            return None
        operation = "MULUW" if fields & 4 else "MULW"
        return f"{operation} {_pair(word, 9)}, {_reg(word, 6)}, {_reg(word, 3)}"
    if opcode == 21:
        if fields & 7:
            return None
        operation = "DIVUW" if fields & 8 else "DIVW"
        return f"{operation} {_pair(word, 9)}, {_pair(word, 7)}, {_reg(word, 4)}"
    if opcode == 26:
        return f"SEXT8 {dst}, {base}" if not fields & 31 else None
    if opcode in _FAR_RELATIVE:
        offset = word & 0xFF
        if not offset & 128:
            offset -= 256
        if opcode == 31:
            return _branch(word, (word >> dst_shift) & 7, offset)
        return f"{_FAR_RELATIVE[opcode]} {dst}, #{offset}"
    return None


def instruction_mnemonic(word: int, *, target: str) -> str | None:
    """Return the canonical mnemonic for a word in the given ISA."""
    if target not in {"lc3", "lab3c", "lab3c-v2"}:
        raise ValueError(f"destino desconocido: {target}")
    operation = _decode(word, target == "lc3", v2=target == "lab3c-v2")
    return operation.partition(" ")[0].upper() if operation else None


def disassemble(
    image: bytes,
    *,
    target: str = "lab3c",
    instruction_addresses: Collection[int] | None = None,
) -> str:
    """Render assembly that reproduces the image byte for byte.

    With an address map only marked words are decoded. Otherwise each full
    word is interpreted as a possible instruction. Unrepresentable encodings
    are emitted as .FILL and remaining bytes as .BYTE on Lab 3c.
    """
    if target not in {"lc3", "lab3c", "lab3c-v2"}:
        raise ValueError(f"destino desconocido: {target}")
    if len(image) < 2:
        raise ValueError("la imagen requiere un origen de dos bytes")
    original = target == "lc3"
    v2 = target == "lab3c-v2"
    origin = int.from_bytes(image[:2], "big")
    payload = image[2:]
    if original and len(payload) % 2:
        raise ValueError("el contenido LC-3 requiere palabras completas")
    if not original and origin % 2:
        raise ValueError("la dirección de origen del programa debe estar alineada")
    scale = 2 if original else 1
    if origin * scale + len(payload) > 0x10000 * scale:
        raise ValueError("la imagen supera el espacio de direcciones de 16 bits")

    positions = None
    if instruction_addresses is not None:
        positions = set()
        for address in instruction_addresses:
            if type(address) is not int:
                raise ValueError("el mapa debe indicar direcciones enteras")
            position = (address - origin) * scale
            if position < 0 or position + 2 > len(payload) or position % 2:
                raise ValueError(f"dirección de instrucción inválida en el mapa: x{address:04X}")
            positions.add(position)

    lines = [f".ORIG x{origin:04X}"]
    position = 0
    while position < len(payload):
        is_instruction = positions is None or position in positions
        word_available = position + 2 <= len(payload)
        if (original or is_instruction) and word_available:
            word = int.from_bytes(payload[position:position + 2], "big")
            operation = _decode(word, original, v2=v2) if is_instruction else None
            lines.append(f"    {operation or f'.FILL x{word:04X}'}")
            position += 2
        else:
            end = min(position + 16, len(payload))
            if positions is not None:
                end = next((offset for offset in range(position + 1, end) if offset in positions), end)
            values = ", ".join(f"x{value:02X}" for value in payload[position:end])
            lines.append(f"    .BYTE {values}")
            position = end
    lines.append(".END")
    return "\n".join(lines) + "\n"
