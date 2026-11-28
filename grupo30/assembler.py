"""
assembler.py - Ensamblador de dos pasadas para la ISA Skynet (16 bits)
==================================================================================
Ensamblador independiente del núcleo de ejecución.
Recibe uno o más archivos .asm y genera código máquina en .hex y/o .bin.
Siempre incluye los 2 primeros bytes como la dirección de origen .ORIG en Little-Endian.

Características clave:
  - Dos pasadas con tabla de símbolos global y soporte de .EXTERNAL.
  - Directivas: .ORIG, .END, .FILL, .BLKW, .STRINGZ, .BYTE, .EXTERNAL.
  - Alineación automática a dirección par antes de toda instrucción o palabra (.FILL/.BLKW),
    insertando 0x00 de relleno si la dirección actual es impar.
  - Sin reservar registros temporales:
      Si ADD/SUB tiene inmediato k fuera de [-8, +7] (y dentro de 7 bits [-64, 63]):
        si DR == SR1: emite ADDI DR, #k (o #-k en SUB)
        si DR != SR1: emite MOVI DR, #k seguido de ADD DR, DR, SR1 (o #-k en SUB)
  - Validación estricta con mensajes claros y número de línea:
      Rechaza DIVQ con n > 16, inmediatos/offsets fuera de rango, etiquetas duplicadas/indefinidas.
"""

import argparse
import os
import re
import sys
from typing import Dict, List, Optional, Set, Tuple

from isa import *  # Única fuente de verdad


class AssemblerError(Exception):
    """Error de ensamblado con archivo y número de línea."""
    def __init__(self, filename: str, lineno: int, message: str):
        self.filename = filename
        self.lineno = lineno
        self.message = message
        super().__init__(f"[{os.path.basename(filename)}:{lineno}] {message}")


def parse_int(s: str) -> int:
    """Parsea enteros en decimal (#10, 10), hexadecimal (x3000, 0x3000) o binario (b101, 0b101)."""
    s = s.strip()
    if not s:
        raise ValueError("Cadena numérica vacía")
    sign = -1 if s.startswith("-") else 1
    if s.startswith(("+", "-")):
        s = s[1:].strip()
    if s.startswith("#"):
        return sign * int(s[1:], 10)
    if s.lower().startswith("0x"):
        return sign * int(s[2:], 16)
    if s.lower().startswith("x"):
        return sign * int(s[1:], 16)
    if s.lower().startswith("0b"):
        return sign * int(s[2:], 2)
    if s.lower().startswith("b") and len(s) > 1 and all(c in "01" for c in s[1:]):
        return sign * int(s[1:], 2)
    return sign * int(s, 10)


def try_parse_int(s: str) -> Optional[int]:
    try:
        return parse_int(s)
    except (ValueError, IndexError):
        return None


def parse_reg(s: str) -> int:
    s = s.strip().upper()
    if s.startswith("R") and s[1:].isdigit():
        r = int(s[1:])
        if 0 <= r < NUM_REGS:
            return r
    raise ValueError(f"Registro inválido: '{s}' (debe ser R0..R7)")


def parse_reg_list(s: str) -> int:
    """Parsea una lista de registros para PUSHM / POPM, ej. {R0, R1, R2} o {R1-R4}."""
    s = s.strip()
    if s.startswith("{") and s.endswith("}"):
        inner = s[1:-1].strip()
        if not inner:
            return 0
        mask = 0
        parts = [p.strip() for p in inner.split(",") if p.strip()]
        for p in parts:
            if "-" in p:
                r1_s, r2_s = p.split("-", 1)
                r1 = parse_reg(r1_s)
                r2 = parse_reg(r2_s)
                step = 1 if r1 <= r2 else -1
                for r in range(r1, r2 + step, step):
                    mask |= (1 << r)
            elif ".." in p:
                r1_s, r2_s = p.split("..", 1)
                r1 = parse_reg(r1_s)
                r2 = parse_reg(r2_s)
                step = 1 if r1 <= r2 else -1
                for r in range(r1, r2 + step, step):
                    mask |= (1 << r)
            else:
                r = parse_reg(p)
                mask |= (1 << r)
        return mask & ~(1 << SP_REG)   # El bit 6 (R6) se ignora siempre
    else:
        val = parse_int(s)
        return val & ~(1 << SP_REG)


def parse_stringz(s: str) -> bytes:
    """Parsea una cadena literal entre comillas con secuencias de escape y agrega el byte nulo final."""
    s = s.strip()
    if not (s.startswith('"') and s.endswith('"') and len(s) >= 2):
        raise ValueError(f"Cadena no válida para .STRINGZ: {s}")
    content = s[1:-1]
    res = bytearray()
    i = 0
    while i < len(content):
        if content[i] == '\\' and i + 1 < len(content):
            c = content[i + 1]
            if c == 'n': res.append(ord('\n'))
            elif c == 't': res.append(ord('\t'))
            elif c == 'r': res.append(ord('\r'))
            elif c == '0': res.append(0)
            elif c == '\\': res.append(ord('\\'))
            elif c == '"': res.append(ord('"'))
            elif c == 'x' and i + 3 < len(content):
                res.append(int(content[i+2:i+4], 16))
                i += 2
            else:
                res.append(ord(c))
            i += 2
        else:
            res.append(ord(content[i]))
            i += 1
    res.append(0)
    return bytes(res)


def split_operands(s: str) -> List[str]:
    """Separa operandos delimitados por comas o espacios, respetando comillas y llaves."""
    parts = []
    curr = []
    in_quote = False
    in_brace = False
    escape = False
    for char in s:
        if in_quote:
            curr.append(char)
            if escape:
                escape = False
            elif char == '\\':
                escape = True
            elif char == '"':
                in_quote = False
        elif in_brace:
            curr.append(char)
            if char == '}':
                in_brace = False
        else:
            if char == '"':
                in_quote = True
                curr.append(char)
            elif char == '{':
                in_brace = True
                curr.append(char)
            elif char == ',' or char.isspace():
                if curr:
                    parts.append("".join(curr).strip())
                    curr = []
            else:
                curr.append(char)
    if curr:
        parts.append("".join(curr).strip())
    return [p for p in parts if p]


def strip_comment(line: str) -> str:
    """Remueve comentarios fuera de cadenas literales.
    ';' inicia comentario siempre.
    '#' inicia comentario solo si no forma parte de un prefijo inmediato numérico (ej. #10, #-5).
    """
    in_quote = False
    escape = False
    for idx, c in enumerate(line):
        if in_quote:
            if escape:
                escape = False
            elif c == '\\':
                escape = True
            elif c == '"':
                in_quote = False
        else:
            if c == '"':
                in_quote = True
            elif c == ';':
                return line[:idx]
            elif c == '#':
                rest = line[idx + 1:].lstrip()
                if not rest or not (rest[0].isdigit() or rest[0] in "+-xX"):
                    return line[:idx]
    return line


KNOWN_DIRECTIVES = {".ORIG", ".END", ".FILL", ".BLKW", ".STRINGZ", ".BYTE", ".EXTERNAL"}
BRANCH_MNEMONICS = {"BR", "BRN", "BRZ", "BRP", "BRZP", "BRNP", "BRNZ", "BRNZP"}
TRAP_ALIASES = {"GETC": TRAP_GETC, "OUT": TRAP_OUT, "PUTS": TRAP_PUTS,
                "IN": TRAP_IN, "HALT": TRAP_HALT, "PUTI": TRAP_PUTI}

ALL_KNOWN_MNEMONICS = {
    "BR", "BRN", "BRZ", "BRP", "BRZP", "BRNP", "BRNZ", "BRNZP",
    "ADD", "LD", "ST", "JSR", "JSRR", "AND", "LDR", "STR",
    "LDB", "NOT", "LDH", "STH", "JMP", "RET", "STB", "LEA",
    "TRAP", "SUB", "OR", "XOR", "CMP",
    "ADDI", "MOVI",
    "SHL", "ASR", "LSR",
    "MULL", "MULH",
    "DIV", "REM",
    "MULQ", "DIVQ",
    "PUSHM", "POPM",
    "NEG", "ABS", "LDBU", "NOP",
    "GETC", "OUT", "PUTS", "IN", "HALT", "PUTI",
    ".ORIG", ".END", ".FILL", ".BLKW", ".STRINGZ", ".BYTE", ".EXTERNAL",
}


class SourceLine:
    def __init__(self, filename: str, lineno: int, text: str):
        self.filename = filename
        self.lineno = lineno
        self.raw_text = text
        self.labels: List[str] = []
        self.mnemonic: Optional[str] = None
        self.operand_str: str = ""
        self.operands: List[str] = []


def parse_source_line(filename: str, lineno: int, raw_line: str) -> Optional[SourceLine]:
    clean = strip_comment(raw_line).strip()
    if not clean:
        return None

    line_obj = SourceLine(filename, lineno, raw_line)
    rest = clean

    # 1. Extracción de etiquetas iniciales con dos puntos (ej. "LOOP:")
    while ":" in rest:
        colon_pos = rest.index(":")
        quote_count = rest[:colon_pos].count('"')
        if quote_count % 2 == 1:
            break
        lbl = rest[:colon_pos].strip()
        if not lbl or any(c.isspace() for c in lbl):
            break
        line_obj.labels.append(lbl)
        rest = rest[colon_pos + 1:].strip()

    if not rest:
        return line_obj

    # 2. Si no hay dos puntos, la primera palabra podría ser una etiqueta si no es mnemónico ni directiva
    tokens = rest.split(None, 1)
    first = tokens[0]
    first_upper = first.upper()

    is_opcode = first_upper in ALL_KNOWN_MNEMONICS

    if not is_opcode and len(tokens) > 1 and not line_obj.labels:
        # La primera palabra es una etiqueta sin dos puntos (ej. "LOOP ADD R0, R1, R2")
        line_obj.labels.append(first)
        rest = tokens[1].strip()
        tokens = rest.split(None, 1)
        first = tokens[0]
        first_upper = first.upper()
    elif not is_opcode and len(tokens) == 1 and not line_obj.labels:
        # Etiqueta solitaria en una línea sin dos puntos
        line_obj.labels.append(first)
        return line_obj

    line_obj.mnemonic = first_upper
    if len(tokens) > 1:
        line_obj.operand_str = tokens[1].strip()
        line_obj.operands = split_operands(line_obj.operand_str)
    return line_obj


class Assembler:
    def __init__(self):
        self.symbols: Dict[str, int] = {}
        self.file_symbols: Dict[str, Dict[str, int]] = {}
        self.external_symbols: Set[str] = set()
        self.origin: int = DEFAULT_ORIGIN
        self.origin_defined: bool = False

    @staticmethod
    def _mod_name(filename: str) -> str:
        return os.path.splitext(os.path.basename(filename))[0].upper()

    def _register_label(self, lbl: str, sl: SourceLine, addr: int):
        mod = self._mod_name(sl.filename)
        lbl_key = lbl.upper()
        self.file_symbols.setdefault(mod, {})[lbl_key] = addr
        self.symbols[f"{mod}-{lbl_key}"] = addr
        if lbl_key not in self.symbols:
            self.symbols[lbl_key] = addr

    def assemble(self, filenames: List[str]) -> Tuple[int, bytes]:
        """Ensambla uno o más archivos y devuelve (origen, bytes_del_programa)."""
        parsed_lines: List[SourceLine] = []

        for fn in filenames:
            with open(fn, "r", encoding="utf-8") as f:
                for idx, line in enumerate(f, start=1):
                    parsed = parse_source_line(fn, idx, line)
                    if parsed is not None:
                        parsed_lines.append(parsed)
                        if parsed.mnemonic == ".END":
                            break

        self._pass1(parsed_lines)
        blob = self._pass2(parsed_lines)
        return self.origin, blob

    def _pass1(self, lines: List[SourceLine]):
        """Primera pasada: asigna direcciones a etiquetas por módulo y globales."""
        lc = self.origin
        pending_labels: List[Tuple[str, SourceLine]] = []
        first_file = lines[0].filename if lines else None

        for sl in lines:
            mod = self._mod_name(sl.filename)
            local_syms = self.file_symbols.setdefault(mod, {})

            for lbl in sl.labels:
                lbl_key = lbl.upper()
                if lbl_key in local_syms or any(
                    k.upper() == lbl_key and self._mod_name(s.filename) == mod
                    for k, s in pending_labels
                ):
                    raise AssemblerError(sl.filename, sl.lineno, f"etiqueta duplicada: '{lbl}'")
                pending_labels.append((lbl, sl))

            if sl.mnemonic is None:
                continue

            mnem = sl.mnemonic

            if mnem == ".ORIG":
                if not sl.operands:
                    raise AssemblerError(sl.filename, sl.lineno, ".ORIG requiere dirección")
                addr = try_parse_int(sl.operands[0])
                if addr is None or not (0 <= addr <= MASK16):
                    raise AssemblerError(sl.filename, sl.lineno, f"Dirección .ORIG inválida: {sl.operands[0]}")
                if not self.origin_defined:
                    self.origin = addr
                    self.origin_defined = True
                    lc = addr
                elif sl.filename == first_file and addr >= lc:
                    lc = addr
                else:
                    if lc & 1:
                        lc += 1
                for lbl, lbl_sl in pending_labels:
                    self._register_label(lbl, lbl_sl, lc)
                pending_labels.clear()
                continue

            elif mnem == ".EXTERNAL":
                for op in sl.operands:
                    self.external_symbols.add(op.upper())
                continue

            elif mnem == ".END":
                for lbl, lbl_sl in pending_labels:
                    self._register_label(lbl, lbl_sl, lc)
                pending_labels.clear()
                continue

            elif mnem == ".BYTE":
                for lbl, lbl_sl in pending_labels:
                    self._register_label(lbl, lbl_sl, lc)
                pending_labels.clear()
                if not sl.operands:
                    raise AssemblerError(sl.filename, sl.lineno, ".BYTE requiere un valor")
                lc += 1
                continue

            elif mnem == ".STRINGZ":
                for lbl, lbl_sl in pending_labels:
                    self._register_label(lbl, lbl_sl, lc)
                pending_labels.clear()
                if not sl.operands:
                    raise AssemblerError(sl.filename, sl.lineno, ".STRINGZ requiere una cadena literal")
                try:
                    str_bytes = parse_stringz(sl.operand_str)
                except ValueError as e:
                    raise AssemblerError(sl.filename, sl.lineno, str(e))
                lc += len(str_bytes)
                continue

            if lc & 1:
                lc += 1

            for lbl, lbl_sl in pending_labels:
                self._register_label(lbl, lbl_sl, lc)
            pending_labels.clear()

            if mnem == ".FILL":
                if not sl.operands:
                    raise AssemblerError(sl.filename, sl.lineno, ".FILL requiere un valor o etiqueta")
                lc += 2
                continue

            elif mnem == ".BLKW":
                if not sl.operands:
                    raise AssemblerError(sl.filename, sl.lineno, ".BLKW requiere cantidad de palabras")
                count = try_parse_int(sl.operands[0])
                if count is None or count < 0:
                    raise AssemblerError(sl.filename, sl.lineno, f".BLKW requiere cantidad de palabras (inválido: '{sl.operands[0]}')")
                lc += count * 2
                continue

            expanded = self._check_immediate_expansion(sl)
            if expanded == 2:
                lc += 4
            else:
                lc += 2

        for lbl, lbl_sl in pending_labels:
            self._register_label(lbl, lbl_sl, lc)

    def _check_immediate_expansion(self, sl: SourceLine) -> int:
        """Determina si un ADD o SUB requiere expansión de inmediato:
           Devuelve 1 (1 instrucción: ADD normal o ADDI) o 2 (2 instrucciones: MOVI + ADD)."""
        mnem = sl.mnemonic
        if mnem not in ("ADD", "SUB"):
            return 1

        ops = sl.operands
        if len(ops) == 3:
            dr_s, sr1_s, op2_s = ops[0], ops[1], ops[2]
        elif len(ops) == 2:
            dr_s, sr1_s, op2_s = ops[0], ops[0], ops[1]
        else:
            return 1

        imm = try_parse_int(op2_s)
        if imm is None:
            return 1  # No es inmediato

        # Si cabe en imm4 (-8..+7), no requiere expansión
        if -8 <= imm <= 7:
            return 1

        # Verificar rango de 7 bits
        if mnem == "ADD":
            if not (-64 <= imm <= 63):
                raise AssemblerError(sl.filename, sl.lineno, f"Inmediato #{imm} fuera de rango para ADD (máx 7 bits con signo: [-64, +63])")
        else:  # SUB: -imm debe caber en [-64, +63]
            neg_k = -imm
            if not (-64 <= neg_k <= 63):
                raise AssemblerError(sl.filename, sl.lineno, f"Inmediato #{imm} fuera de rango para SUB (inverso #{neg_k} debe estar en [-64, +63])")

        try:
            dr = parse_reg(dr_s)
            sr1 = parse_reg(sr1_s)
        except ValueError as e:
            raise AssemblerError(sl.filename, sl.lineno, str(e))

        if dr == sr1:
            return 1  # ADDI DR, #k (o #-k en SUB) -> 1 instrucción (2 bytes)
        else:
            return 2  # MOVI DR, #k seguido de ADD DR, DR, SR1 -> 2 instrucciones (4 bytes)

    def _resolve_label_or_imm(self, sl: SourceLine, token: str) -> int:
        val = try_parse_int(token)
        if val is not None:
            return val
        token_upper = token.upper()
        mod = self._mod_name(sl.filename)
        if token_upper in self.file_symbols.get(mod, {}):
            return self.file_symbols[mod][token_upper]
        if token_upper in self.symbols:
            return self.symbols[token_upper]
        raise AssemblerError(sl.filename, sl.lineno, f"etiqueta indefinida: '{token}'")

    def _pass2(self, lines: List[SourceLine]) -> bytes:
        """Segunda pasada: genera el flujo de bytes de código máquina."""
        lc = self.origin
        origin_seen = False
        first_file = lines[0].filename if lines else None
        out = bytearray()

        for sl in lines:
            if sl.mnemonic is None:
                continue

            mnem = sl.mnemonic

            if mnem == ".ORIG":
                addr = try_parse_int(sl.operands[0])
                if not origin_seen:
                    origin_seen = True
                elif sl.filename == first_file and addr is not None and addr > lc:
                    out.extend(b"\x00" * (addr - lc))
                    lc = addr
                else:
                    if lc & 1:
                        out.append(0x00)
                        lc += 1
                continue
            elif mnem == ".EXTERNAL":
                continue
            elif mnem == ".END":
                continue

            elif mnem == ".BYTE":
                if not sl.operands:
                    raise AssemblerError(sl.filename, sl.lineno, ".BYTE requiere un valor")
                val = self._resolve_label_or_imm(sl, sl.operands[0])
                out.append(val & MASK8)
                lc += 1
                continue

            elif mnem == ".STRINGZ":
                str_bytes = parse_stringz(sl.operand_str)
                out.extend(str_bytes)
                lc += len(str_bytes)
                continue

            if lc & 1:
                out.append(0x00)
                lc += 1

            if mnem == ".FILL":
                val = self._resolve_label_or_imm(sl, sl.operands[0])
                out.append(val & MASK8)
                out.append((val >> 8) & MASK8)
                lc += 2
                continue

            elif mnem == ".BLKW":
                try:
                    count = parse_int(sl.operands[0])
                    fill_val = parse_int(sl.operands[1]) if len(sl.operands) > 1 else 0
                except ValueError as e:
                    raise AssemblerError(sl.filename, sl.lineno, str(e))
                for _ in range(count):
                    out.append(fill_val & MASK8)
                    out.append((fill_val >> 8) & MASK8)
                lc += count * 2
                continue

            try:
                instr_bytes = self._encode_instruction(sl, lc)
            except ValueError as e:
                raise AssemblerError(sl.filename, sl.lineno, str(e))
            out.extend(instr_bytes)
            lc += len(instr_bytes)

        return bytes(out)

    def _encode_instruction(self, sl: SourceLine, pc: int) -> bytes:
        """Codifica una instrucción en 2 o 4 bytes."""
        mnem = sl.mnemonic
        ops = sl.operands
        nxt_pc = pc + INSTR_SIZE

        def to_bytes(w: int) -> bytes:
            return bytes([w & MASK8, (w >> 8) & MASK8])

        # --- NOP / RET ---
        if mnem == "NOP":
            return to_bytes(enc_nop())
        if mnem == "RET":
            return to_bytes(enc_ret())

        # --- Saltos condicionales BR ---
        if mnem in BRANCH_MNEMONICS:
            cond_str = mnem[2:]
            if not cond_str:
                nzp = 7
            else:
                n = 4 if "N" in cond_str else 0
                z = 2 if "Z" in cond_str else 0
                p = 1 if "P" in cond_str else 0
                nzp = n | z | p
            if not ops:
                raise AssemblerError(sl.filename, sl.lineno, f"{mnem} requiere etiqueta de destino")
            target = self._resolve_label_or_imm(sl, ops[0])
            delta = target - nxt_pc
            if delta % 2 != 0:
                raise AssemblerError(sl.filename, sl.lineno, f"Dirección de destino de salto impar: x{target:04X}")
            off8 = delta // 2
            if not (-128 <= off8 <= 127):
                raise AssemblerError(sl.filename, sl.lineno, f"offset fuera de rango para {mnem} ({off8} palabras, rango [-128, 127])")
            return to_bytes(enc_br(nzp, off8))

        # --- ADD / SUB con regla de expansión automática ---
        if mnem in ("ADD", "SUB"):
            if len(ops) == 3:
                dr = parse_reg(ops[0])
                sr1 = parse_reg(ops[1])
                op2_s = ops[2]
            elif len(ops) == 2:
                dr = parse_reg(ops[0])
                sr1 = dr
                op2_s = ops[1]
            else:
                raise AssemblerError(sl.filename, sl.lineno, f"{mnem} requiere 2 o 3 operandos")

            imm = try_parse_int(op2_s)
            if imm is None:
                sr2 = parse_reg(op2_s)
                code = enc_add_reg(dr, sr1, sr2) if mnem == "ADD" else enc_sub_reg(dr, sr1, sr2)
                return to_bytes(code)

            # Segundo operando es inmediato
            if -8 <= imm <= 7:
                code = enc_add_imm(dr, sr1, imm) if mnem == "ADD" else enc_sub_imm(dr, sr1, imm)
                return to_bytes(code)

            eff_k = imm if mnem == "ADD" else -imm
            if not (-64 <= eff_k <= 63):
                raise AssemblerError(sl.filename, sl.lineno, f"Inmediato #{imm} fuera de rango para {mnem} (rango 7 bits [-64, 63])")

            if dr == sr1:
                return to_bytes(enc_addi(dr, eff_k))
            else:
                w1 = enc_movi(dr, eff_k)
                w2 = enc_add_reg(dr, dr, sr1)
                return to_bytes(w1) + to_bytes(w2)

        # --- LD / ST / LEA ---
        if mnem in ("LD", "ST", "LEA"):
            if len(ops) != 2:
                raise AssemblerError(sl.filename, sl.lineno, f"{mnem} requiere 2 operandos (DR/SR, ETIQUETA)")
            r = parse_reg(ops[0])
            target = self._resolve_label_or_imm(sl, ops[1])
            delta = target - nxt_pc
            if delta % 2 != 0:
                raise AssemblerError(sl.filename, sl.lineno, f"Dirección de destino impar: x{target:04X}")
            off8 = delta // 2
            if not (-128 <= off8 <= 127):
                raise AssemblerError(sl.filename, sl.lineno, f"offset fuera de rango para {mnem} ({off8} palabras, rango [-128, 127])")
            if mnem == "LD":
                return to_bytes(enc_ld(r, off8))
            elif mnem == "ST":
                return to_bytes(enc_st(r, off8))
            else:
                return to_bytes(enc_lea(r, off8))

        # --- JSR / JSRR ---
        if mnem == "JSR":
            if not ops:
                raise AssemblerError(sl.filename, sl.lineno, "JSR requiere etiqueta de subrutina")
            target = self._resolve_label_or_imm(sl, ops[0])
            delta = target - nxt_pc
            if delta % 2 != 0:
                raise AssemblerError(sl.filename, sl.lineno, f"Dirección de subrutina impar: x{target:04X}")
            off10 = delta // 2
            if not (-512 <= off10 <= 511):
                raise AssemblerError(sl.filename, sl.lineno, f"offset fuera de rango para JSR ({off10} palabras, rango [-512, 511])")
            return to_bytes(enc_jsr(off10))

        if mnem == "JSRR":
            if not ops:
                raise AssemblerError(sl.filename, sl.lineno, "JSRR requiere registro base")
            base = parse_reg(ops[0])
            return to_bytes(enc_jsrr(base))

        if mnem == "JMP":
            if not ops:
                raise AssemblerError(sl.filename, sl.lineno, "JMP requiere registro base")
            base = parse_reg(ops[0])
            return to_bytes(enc_jmp(base))

        # --- Operaciones lógicas AND, OR, XOR ---
        if mnem in ("AND", "OR", "XOR"):
            if len(ops) == 3:
                dr = parse_reg(ops[0])
                sr1 = parse_reg(ops[1])
                op2_s = ops[2]
            elif len(ops) == 2:
                dr = parse_reg(ops[0])
                sr1 = dr
                op2_s = ops[1]
            else:
                raise AssemblerError(sl.filename, sl.lineno, f"{mnem} requiere 2 o 3 operandos")

            imm = try_parse_int(op2_s)
            if imm is None:
                sr2 = parse_reg(op2_s)
                if mnem == "AND": code = enc_and_reg(dr, sr1, sr2)
                elif mnem == "OR": code = enc_or_reg(dr, sr1, sr2)
                else: code = enc_xor_reg(dr, sr1, sr2)
            else:
                if not (-8 <= imm <= 7):
                    raise AssemblerError(sl.filename, sl.lineno, f"Inmediato #{imm} fuera de rango para {mnem} (rango 4 bits con signo [-8, +7])")
                if mnem == "AND": code = enc_and_imm(dr, sr1, imm)
                elif mnem == "OR": code = enc_or_imm(dr, sr1, imm)
                else: code = enc_xor_imm(dr, sr1, imm)
            return to_bytes(code)

        # --- LDR, STR, LDB, STB, LDH, STH, LDBU ---
        if mnem in ("LDR", "STR", "LDB", "STB", "LDH", "STH", "LDBU"):
            if len(ops) != 3:
                raise AssemblerError(sl.filename, sl.lineno, f"{mnem} requiere 3 operandos (DR/SR, BaseR, #offset5)")
            r = parse_reg(ops[0])
            base = parse_reg(ops[1])
            off5 = parse_int(ops[2])
            if not (-16 <= off5 <= 15):
                raise AssemblerError(sl.filename, sl.lineno, f"offset5={off5} fuera de rango para {mnem} (rango [-16, +15])")
            if mnem == "LDR":   code = enc_ldr(r, base, off5)
            elif mnem == "STR":  code = enc_str(r, base, off5)
            elif mnem == "LDB":  code = enc_ldb(r, base, off5)
            elif mnem == "STB":  code = enc_stb(r, base, off5)
            elif mnem == "LDH":  code = enc_ldh(r, base, off5)
            elif mnem == "STH":  code = enc_sth(r, base, off5)
            else:               code = enc_ldbu(r, base, off5)
            return to_bytes(code)

        # --- NOT, NEG, ABS ---
        if mnem in ("NOT", "NEG", "ABS"):
            if len(ops) == 2:
                dr = parse_reg(ops[0])
                sr1 = parse_reg(ops[1])
            elif len(ops) == 1:
                dr = parse_reg(ops[0])
                sr1 = dr
            else:
                raise AssemblerError(sl.filename, sl.lineno, f"{mnem} requiere 1 o 2 registros")
            if mnem == "NOT":   code = enc_not(dr, sr1)
            elif mnem == "NEG": code = enc_neg(dr, sr1)
            else:               code = enc_abs(dr, sr1)
            return to_bytes(code)

        # --- CMP ---
        if mnem == "CMP":
            if len(ops) != 2:
                raise AssemblerError(sl.filename, sl.lineno, "CMP requiere 2 operandos (SR1, SR2 / #imm4)")
            sr1 = parse_reg(ops[0])
            imm = try_parse_int(ops[1])
            if imm is None:
                sr2 = parse_reg(ops[1])
                code = enc_cmp_reg(sr1, sr2)
            else:
                if not (-8 <= imm <= 7):
                    raise AssemblerError(sl.filename, sl.lineno, f"Inmediato #{imm} fuera de rango para CMP (rango [-8, +7])")
                code = enc_cmp_imm(sr1, imm)
            return to_bytes(code)

        # --- ADDI / MOVI directos ---
        if mnem in ("ADDI", "MOVI"):
            if len(ops) == 2:
                rd = parse_reg(ops[0])
                imm7 = parse_int(ops[1])
            elif len(ops) == 3 and mnem == "ADDI":
                rd = parse_reg(ops[0])
                sr1 = parse_reg(ops[1])
                if rd != sr1:
                    raise AssemblerError(sl.filename, sl.lineno, "ADDI requiere Rd == SR1 si se proporcionan 3 operandos")
                imm7 = parse_int(ops[2])
            else:
                raise AssemblerError(sl.filename, sl.lineno, f"{mnem} requiere Rd, #imm7")
            if not (-64 <= imm7 <= 63):
                raise AssemblerError(sl.filename, sl.lineno, f"Inmediato #{imm7} fuera de rango para {mnem} (rango 7 bits [-64, +63])")
            code = enc_addi(rd, imm7) if mnem == "ADDI" else enc_movi(rd, imm7)
            return to_bytes(code)

        # --- SHL, ASR, LSR ---
        if mnem in ("SHL", "ASR", "LSR"):
            if len(ops) != 3:
                raise AssemblerError(sl.filename, sl.lineno, f"{mnem} requiere 3 operandos (DR, SR1, SR2 / #uimm4)")
            dr = parse_reg(ops[0])
            sr1 = parse_reg(ops[1])
            uimm = try_parse_int(ops[2])
            if uimm is None:
                sr2 = parse_reg(ops[2])
                if mnem == "SHL":   code = enc_shl_reg(dr, sr1, sr2)
                elif mnem == "ASR": code = enc_asr_reg(dr, sr1, sr2)
                else:               code = enc_lsr_reg(dr, sr1, sr2)
            else:
                if not (0 <= uimm <= 15):
                    raise AssemblerError(sl.filename, sl.lineno, f"Desplazamiento #{uimm} fuera de rango para {mnem} (rango 0..15)")
                if mnem == "SHL":   code = enc_shl_imm(dr, sr1, uimm)
                elif mnem == "ASR": code = enc_asr_imm(dr, sr1, uimm)
                else:               code = enc_lsr_imm(dr, sr1, uimm)
            return to_bytes(code)

        # --- MULL, MULH, DIV, REM ---
        if mnem in ("MULL", "MULH", "DIV", "REM"):
            if len(ops) != 3:
                raise AssemblerError(sl.filename, sl.lineno, f"{mnem} requiere 3 operandos (DR, SR1, SR2)")
            dr = parse_reg(ops[0])
            sr1 = parse_reg(ops[1])
            sr2 = parse_reg(ops[2])
            if mnem == "MULL":   code = enc_mull(dr, sr1, sr2)
            elif mnem == "MULH": code = enc_mulh(dr, sr1, sr2)
            elif mnem == "DIV":  code = enc_div(dr, sr1, sr2)
            else:               code = enc_rem(dr, sr1, sr2)
            return to_bytes(code)

        # --- MULQ / DIVQ ---
        if mnem in ("MULQ", "DIVQ"):
            if len(ops) != 3:
                raise AssemblerError(sl.filename, sl.lineno, f"{mnem} requiere 3 operandos (Rd, Rs, #n)")
            rd = parse_reg(ops[0])
            rs = parse_reg(ops[1])
            n = parse_int(ops[2])
            if mnem == "MULQ":
                if not (0 <= n <= 31):
                    raise AssemblerError(sl.filename, sl.lineno, f"MULQ n={n} fuera de rango permitido (0..31)")
                code = enc_mulq(rd, rs, n)
            else:
                if not (0 <= n <= 16):
                    raise AssemblerError(sl.filename, sl.lineno, f"DIVQ n={n} fuera de rango permitido (0..16; 17..31 reservado)")
                code = enc_divq(rd, rs, n)
            return to_bytes(code)

        # --- PUSHM / POPM ---
        if mnem in ("PUSHM", "POPM"):
            if not ops:
                raise AssemblerError(sl.filename, sl.lineno, f"{mnem} requiere lista de registros {{R...}} o máscara")
            mask = parse_reg_list(sl.operand_str)
            code = enc_pushm(mask) if mnem == "PUSHM" else enc_popm(mask)
            return to_bytes(code)

        # --- TRAP y alias TRAP ---
        if mnem in TRAP_ALIASES:
            return to_bytes(enc_trap(TRAP_ALIASES[mnem]))

        if mnem == "TRAP":
            if not ops:
                raise AssemblerError(sl.filename, sl.lineno, "TRAP requiere número de vector")
            vec = parse_int(ops[0])
            if not (0 <= vec <= 127):
                raise AssemblerError(sl.filename, sl.lineno, f"Vector de TRAP x{vec:02X} fuera de rango (0..127)")
            return to_bytes(enc_trap(vec))

        raise AssemblerError(sl.filename, sl.lineno, f"Instrucción desconocida: '{mnem}'")


def write_hex_file(path: str, origin: int, blob: bytes, symbols: Optional[Dict[str, int]] = None):
    """Escribe archivo .hex con los 2 primeros bytes = origin Little-Endian, seguidos del programa.
    Si se provee `symbols`, incrusta comentarios `; @SYM xADDR ETIQUETA` junto a cada subrutina/dirección
    de memoria (compatibles con sim.load_image, que ignora comentarios `;`)."""
    if not symbols:
        raw = bytes([origin & MASK8, (origin >> 8) & MASK8]) + blob
        with open(path, "w", encoding="utf-8") as f:
            for i in range(0, len(raw), 16):
                chunk = raw[i:i + 16]
                f.write(" ".join(f"{b:02X}" for b in chunk) + "\n")
        return

    # Agrupar símbolos por dirección (priorizando nombres calificados MODULO-ETIQUETA)
    by_addr: Dict[int, List[str]] = {}
    for name, addr in symbols.items():
        by_addr.setdefault(addr & MASK16, []).append(name)
    cleaned_by_addr: Dict[int, List[str]] = {}
    for addr, names in by_addr.items():
        qualified = sorted(n for n in names if "-" in n)
        short = sorted(n for n in names if "-" not in n)
        cleaned_by_addr[addr] = qualified if qualified else short

    with open(path, "w", encoding="utf-8") as f:
        f.write(f"; Imagen .hex con etiquetas incrustadas | .ORIG x{origin:04X} | {len(blob)} bytes\n")
        f.write(f"{origin & MASK8:02X} {(origin >> 8) & MASK8:02X} ; .ORIG x{origin:04X}\n")

        line_bytes: List[str] = []
        line_start_addr: Optional[int] = None

        def flush_line():
            nonlocal line_bytes, line_start_addr
            if line_bytes:
                f.write(f"{' '.join(line_bytes):<47} ; x{line_start_addr:04X}\n")
                line_bytes = []
                line_start_addr = None

        for offset, b in enumerate(blob):
            addr = (origin + offset) & MASK16
            if addr in cleaned_by_addr:
                flush_line()
                for sym_name in cleaned_by_addr[addr]:
                    f.write(f"; @SYM x{addr:04X} {sym_name}\n")
            if line_start_addr is None:
                line_start_addr = addr
            line_bytes.append(f"{b:02X}")
            if len(line_bytes) == 16:
                flush_line()
        flush_line()

        # Símbolos al final exacto o fuera del rango de bytes (si existieran)
        end_addr = (origin + len(blob)) & MASK16
        emitted_addrs = {(origin + i) & MASK16 for i in range(len(blob))}
        for addr in sorted(cleaned_by_addr):
            if addr not in emitted_addrs:
                for sym_name in cleaned_by_addr[addr]:
                    f.write(f"; @SYM x{addr:04X} {sym_name}\n")


def write_bin_file(path: str, origin: int, blob: bytes):
    """Escribe archivo .bin con los 2 primeros bytes = origin Little-Endian, seguidos del programa."""
    raw = bytes([origin & MASK8, (origin >> 8) & MASK8]) + blob
    with open(path, "wb") as f:
        f.write(raw)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Ensamblador de dos pasadas para la ISA Skynet (16 bits)")
    parser.add_argument("sources", nargs="+", help="uno o más archivos assembly (.asm)")
    parser.add_argument("-o", "--output", help="archivo de salida (.hex o .bin)")
    parser.add_argument("--hex", help="ruta específica para salida .hex")
    parser.add_argument("--bin", help="ruta específica para salida .bin")
    args = parser.parse_args(argv)

    asm = Assembler()
    try:
        origin, blob = asm.assemble(args.sources)
    except AssemblerError as e:
        print(f"Error de ensamblado: {e}", file=sys.stderr)
        return 1
    except OSError as e:
        print(f"Error al abrir archivo: {e}", file=sys.stderr)
        return 1

    hex_out = args.hex
    bin_out = args.bin

    if args.output:
        if args.output.lower().endswith(".bin"):
            bin_out = bin_out or args.output
        else:
            hex_out = hex_out or args.output

    if not hex_out and not bin_out:
        base, _ = os.path.splitext(args.sources[0])
        hex_out = base + ".hex"

    if hex_out:
        write_hex_file(hex_out, origin, blob, symbols=asm.symbols)
        print(f"Generado .hex: {hex_out} (origen x{origin:04X}, {len(blob)} bytes de programa)")

    if bin_out:
        write_bin_file(bin_out, origin, blob)
        print(f"Generado .bin: {bin_out} (origen x{origin:04X}, {len(blob)} bytes de programa)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
