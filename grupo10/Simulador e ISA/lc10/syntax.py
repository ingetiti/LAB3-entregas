"""Partes de la ventana que no dependen de tkinter (se pueden probar sin pantalla)."""
from __future__ import annotations

import re

from .assembler import is_mnemonic

_TOKEN = re.compile(r'''
    (?P<string>"(?:\\.|[^"\\\n])*"?)
  | (?P<comment>;[^\n]*)
  | (?P<directive>\.[A-Za-z]+)
  | (?P<reg>\b[Rr][0-7]\b)
  | (?P<number>\#-?[0-9A-Za-z_]+|(?<!\w)-?(?:0[xX][0-9A-Fa-f]+|0[bB][01]+|[xX][0-9A-Fa-f]+|\d+)\b)
  | (?P<word>[A-Za-z_][A-Za-z0-9_]*(?:-[A-Za-z_][A-Za-z0-9_]*)?:?)
''', re.X)


def highlight_spans(text: str) -> list[tuple[str, int, int, int]]:
    """[(etiqueta, línea (desde 1), columna inicial, columna final)] para colorear el código."""
    spans = []
    for ln, line in enumerate(text.split("\n"), 1):
        slot = 0            # 0: se espera etiqueta o instrucción, 1: instrucción, 2: operandos
        for m in _TOKEN.finditer(line):
            kind, (a, b) = m.lastgroup, m.span()
            if kind in ("string", "comment", "number", "reg"):
                spans.append((kind, ln, a, b))
            elif kind == "directive":
                spans.append(("directive", ln, a, b))
                slot = 2
            else:
                tok = m.group()
                if slot == 0 and (tok.endswith(":") or not is_mnemonic(tok)):
                    spans.append(("label_def", ln, a, b))
                    slot = 1
                elif slot < 2:
                    spans.append(("mnemonic" if is_mnemonic(tok) else "unknown", ln, a, b))
                    slot = 2
                else:
                    spans.append(("label_ref", ln, a, b))
    return spans


def parse_input_escapes(text: str) -> str:
    """La entrada de GETC/IN admite \\n, \\t y \\\\."""
    return re.sub(r"\\([nt\\])", lambda m: {"n": "\n", "t": "\t", "\\": "\\"}[m.group(1)], text)
