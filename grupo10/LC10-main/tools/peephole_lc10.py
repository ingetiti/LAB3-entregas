"""Pase de limpieza para el assembly LC10 que sale del traductor (tools/lc3_to_lc10.py).

    python tools/peephole_lc10.py CARPETA [--salida OTRA] [--solo archivo.asm ...]

Reemplaza tres modismos de LC-3 por la instruccion equivalente de LC10. Los tres dejan el mismo valor en el
registro y las mismas banderas N Z P (que son las unicas que el codigo de la catedra mira):

  1. AND Rx,Rx,#0  seguido de uno o mas ADD Rx,Rx,#k          ->  MOVI Rx,#suma      (suma en -128..127)
  2. NOT Rd,Rs     seguido de ADD Rd,Rd,#1                    ->  NEG Rd,Rs
  3. ADD Rd,Rs,Rs  seguido de ADD Rd,Rd,Rd (k-1 veces)        ->  SHL Rd,Rs,#k       (k en 2..15)

Solo se juntan instrucciones consecutivas, sin etiquetas ni lineas de datos en el medio (una etiqueta en
la primera instruccion se conserva). Las lineas que son solo comentario o estan en blanco entre ellas
se dejan donde estan, despues de la instruccion nueva.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

INSTR = re.compile(r"^(\s+)([A-Za-z]+)\s+([^;]*?)\s*(;.*)?$")
IMM = re.compile(r"^#(-?\d+)$")


def parsear(linea: str):
    """(sangria, mnemonico, [operandos], comentario) si es una linea de instruccion sin etiqueta."""
    if not linea.strip() or linea.lstrip().startswith(";") or not linea[0].isspace():
        return None
    m = INSTR.match(linea.rstrip("\n"))
    if not m:
        return None
    ops = [o.strip() for o in m.group(3).split(",")] if m.group(3) else []
    return m.group(1), m.group(2).upper(), ops, m.group(4) or ""


def es_reg(o: str) -> bool:
    return bool(re.fullmatch(r"[Rr][0-7]", o))


def emitir(sang, mnem, ops, nota):
    return f"{sang}{mnem:<6}{', '.join(ops):<28}; {nota}\n"


def limpiar(texto: str) -> tuple[str, dict]:
    lineas = texto.splitlines(keepends=True)
    out: list[str] = []
    cuenta = {"movi": 0, "neg": 0, "shl": 0, "ahorradas": 0}
    i = 0
    n = len(lineas)

    def siguiente_instr(j):
        """Indice de la proxima linea de instruccion desde j, saltando solo comentarios y blancos."""
        while j < n and (not lineas[j].strip() or lineas[j].lstrip().startswith(";")):
            j += 1
        return j

    while i < n:
        p = parsear(lineas[i])
        if p is None:
            out.append(lineas[i])
            i += 1
            continue
        sang, mn, ops, com = p

        # 1. AND Rx,Rx,#0 + ADD Rx,Rx,#k ...
        if mn == "AND" and len(ops) == 3 and ops[0].upper() == ops[1].upper() and ops[2] == "#0" and es_reg(ops[0]):
            rx = ops[0].upper()
            total, usadas, j, sueltas = 0, [], i + 1, []
            while True:
                k = siguiente_instr(j)
                if k >= n:
                    break
                q = parsear(lineas[k])
                if q is None:
                    break
                _, mn2, ops2, _ = q
                if mn2 == "ADD" and len(ops2) == 3 and ops2[0].upper() == rx and ops2[1].upper() == rx and IMM.match(ops2[2]):
                    total += int(IMM.match(ops2[2]).group(1))
                    sueltas += [l for l in lineas[j:k]]
                    usadas.append(k)
                    j = k + 1
                else:
                    break
            if usadas and -128 <= total <= 127:
                out.append(emitir(sang, "MOVI", [rx, f"#{total}"], f"(AND + {len(usadas)} ADD)"))
                out.extend(sueltas)
                cuenta["movi"] += 1
                cuenta["ahorradas"] += len(usadas)
                i = usadas[-1] + 1
                continue

        # 2. NOT Rd,Rs + ADD Rd,Rd,#1
        if mn == "NOT" and len(ops) == 2 and es_reg(ops[0]) and es_reg(ops[1]):
            k = siguiente_instr(i + 1)
            if k < n:
                q = parsear(lineas[k])
                if q and q[1] == "ADD" and len(q[2]) == 3 and q[2][0].upper() == ops[0].upper() \
                        and q[2][1].upper() == ops[0].upper() and q[2][2] == "#1":
                    out.append(emitir(sang, "NEG", [ops[0].upper(), ops[1].upper()], "(NOT + ADD #1)"))
                    out.extend(lineas[i + 1:k])
                    cuenta["neg"] += 1
                    cuenta["ahorradas"] += 1
                    i = k + 1
                    continue

        # 3. ADD Rd,Rs,Rs + ADD Rd,Rd,Rd ...
        if mn == "ADD" and len(ops) == 3 and es_reg(ops[0]) and es_reg(ops[1]) and ops[1].upper() == ops[2].upper():
            rd, rs = ops[0].upper(), ops[1].upper()
            veces, j, sueltas = 1, i + 1, []
            while True:
                k = siguiente_instr(j)
                if k >= n:
                    break
                q = parsear(lineas[k])
                if q and q[1] == "ADD" and len(q[2]) == 3 and all(o.upper() == rd for o in q[2]):
                    veces += 1
                    sueltas += lineas[j:k]
                    j = k + 1
                else:
                    break
            if 2 <= veces <= 15:
                out.append(emitir(sang, "SHL", [rd, rs, f"#{veces}"], f"({veces} sumas Rd+Rd)"))
                out.extend(sueltas)
                cuenta["shl"] += 1
                cuenta["ahorradas"] += veces - 1
                i = j
                continue

        out.append(lineas[i])
        i += 1
    return "".join(out), cuenta


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("carpeta")
    ap.add_argument("--salida", help="carpeta de salida (por defecto se reescribe en el lugar)")
    ap.add_argument("--solo", nargs="*", default=[], help="procesar solo estos archivos")
    a = ap.parse_args()
    base = Path(a.carpeta)
    dest = Path(a.salida) if a.salida else base
    dest.mkdir(parents=True, exist_ok=True)
    tot = {"movi": 0, "neg": 0, "shl": 0, "ahorradas": 0}
    for f in sorted(base.glob("*.asm")):
        if a.solo and f.name not in a.solo:
            continue
        nuevo, c = limpiar(f.read_text(encoding="utf-8"))
        (dest / f.name).write_text(nuevo, encoding="utf-8")
        if c["ahorradas"]:
            print(f"{f.name:44s} MOVI {c['movi']:3d}  NEG {c['neg']:3d}  SHL {c['shl']:3d}  (-{c['ahorradas']} instrucciones en el texto)")
        for k in tot:
            tot[k] += c[k]
    print(f"total: MOVI {tot['movi']}, NEG {tot['neg']}, SHL {tot['shl']}; instrucciones menos en el texto: {tot['ahorradas']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
