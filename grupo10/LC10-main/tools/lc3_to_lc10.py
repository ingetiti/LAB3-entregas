"""Traductor LC-3 (dialecto de la cátedra) a LC10.

    python tools/lc3_to_lc10.py RUTA\\lc3-project [-o asm/bench10] [--main main_grupo27.asm]

Usa el enlazador de la cátedra (assembler_LC3.py) solo para saber qué módulo resuelve cada `.EXTERNAL`;
no lo modifica. Traduce el programa principal y cada módulo que este alcanza, y escribe un `.asm` de LC10
por archivo (mismo nombre) más `informe.txt` con lo que hay que revisar a mano.

Traducción línea a línea:
  * ADD/AND/NOT/LD/ST/LEA/BR*/JSR/JSRR/JMP/RET/TRAP/HALT/GETC/OUT/PUTS/IN: la misma instrucción.
  * ADD con inmediato fuera de -8..7 (en LC-3 llega a -16..15): varios ADD seguidos (mismo resultado y mismas
    banderas finales). AND fuera de rango: se avisa.
  * LDR/STR: LDW/STW con el offset en bytes (x2): en LC10 las direcciones son de byte. Los accesos a
    caracteres se marcan en `port_hints.py` y pasan a LDL/STL.
  * LDI: LD + LDW. STI: se avisa (necesita un registro de apoyo).
  * .FILL / .BLKW / .STRINGZ: igual. `.STRINGZ` pasa a un byte por carácter y los buffers de texto se
    declaran `.BLKB` en `port_hints.py`.
  * .EXTERNAL MODULO-ETIQUETA: el módulo se renombra al del archivo que lo resuelve (LC10 exige que el
    nombre del módulo sea el del archivo).

Alcance de las instrucciones (en LC10 LD/ST/BR llegan a ±128 palabras, LEA a ±128 bytes; en LC-3, a ±256):
  * un LEA fuera de alcance se cambia por `LD Rd, puntero` (misma cantidad de instrucciones; cuesta una
    palabra por etiqueta);
  * los datos se parten en bloques (cada etiqueta que solo usan LD/ST empieza uno) y se mueven a un punto
    del código al que no se llega por continuación (detrás de un BR/RET/JMP/HALT), el que deje todas las
    referencias dentro de alcance;
  * un salto fuera de alcance recibe un trampolín (otro BR, en un punto intermedio).
"""
from __future__ import annotations

import argparse
import importlib.util
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from lc10 import assembler as A10  # noqa: E402

try:
    from port_hints import HINTS  # noqa: E402
except ImportError:
    HINTS = {}

VALID_LC3 = {"ADD", "AND", "BR", "BRN", "BRZ", "BRP", "BRNZ", "BRNP", "BRZP", "BRNZP", "HALT", "JSR", "JSRR", "JMP",
             "LD", "LDI", "LDR", "LEA", "NOT", "RET", "ST", "STI", "STR", "TRAP", "NOP", "MOV", "CMP", "GETC", "OUT",
             "PUTS", "IN"}
TRAPS = {"GETC", "OUT", "PUTS", "IN"}
LIMITES = {"LD": (-128, 127), "ST": (-128, 127), "BR": (-128, 127), "LEA": (-128, 127), "JSR": (-1024, 1023)}


def cargar(nombre, ruta):
    spec = importlib.util.spec_from_file_location(nombre, ruta)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[nombre] = mod
    spec.loader.exec_module(mod)
    return mod


def split_ops(texto: str) -> list[str]:
    return [p for p in re.split(r"\s+|,", texto.strip()) if p]


@dataclass(eq=False)
class Rec:
    """Una línea de salida."""
    label: str | None = None
    kind: str = "text"          # code | data | dir | text
    text: str = ""              # operación y operandos ya formateados
    comment: str = ""
    mnem: str = ""
    args: list = field(default_factory=list)
    src: int = 0
    chunk: int | None = None
    tag: str = ""               # 'ptr' | 'tramp'

    def render(self) -> str:
        cab = self.label or ""
        cab = cab.ljust(24) if len(cab) < 24 else cab + " "
        linea = (cab + self.text) if (self.text or self.label) else ""
        if self.comment:
            linea = f"{linea:<56}; {self.comment}" if linea.strip() else f"; {self.comment}"
        return linea.rstrip()

    def target(self) -> str | None:
        """Etiqueta local a la que apunta (para BR/JSR/LD/ST/LEA)."""
        if self.kind != "code":
            return None
        if self.mnem in ("LD", "ST", "LEA"):
            return self.args[1]
        if self.mnem.startswith("BR") or self.mnem == "JSR":
            return self.args[0]
        return None

    def set_target(self, label: str):
        i = 1 if self.mnem in ("LD", "ST", "LEA") else 0
        self.args[i] = label
        self.text = self.fmt()

    def fmt(self) -> str:
        return f"{self.mnem:<6}{', '.join(self.args)}" if self.args else self.mnem


def incondicional(r: Rec) -> bool:
    if r.kind != "code":
        return False
    m = r.mnem.upper()
    return m in ("RET", "JMP", "HALT") or m in ("BR", "BRNZP")


class Modulo:
    def __init__(self, ruta: Path, es_main: bool, refs: dict, asm):
        self.ruta, self.es_main, self.refs, self.asm = ruta, es_main, refs, asm
        self.hints = HINTS.get(ruta.name, {})
        self.recs: list[Rec] = []
        self.avisos: list[tuple[int, str, str]] = []
        self.ldrstr: list[tuple[int, str]] = []
        self.movidos: list[str] = []
        self._chunk_ids = 0

    # ----------------------------------------------------------- utilidades
    def aviso(self, ln: int, tipo: str, msg: str):
        self.avisos.append((ln, tipo, msg))

    def qual(self, tok: str) -> str:
        return self.refs.get(tok, tok)

    def num(self, tok: str) -> int | None:
        try:
            return int(self.asm._parse_int(tok))
        except (ValueError, TypeError):
            return None

    def numero_texto(self, tok: str) -> str | None:
        try:
            if A10.parse_number(tok) is not None:
                return tok
        except ValueError:
            pass
        v = self.num(tok)
        return None if v is None else f"#{v}"

    def add(self, **kw) -> Rec:
        r = Rec(**kw)
        self.recs.append(r)
        return r

    def code(self, label, mnem, args, comment="", src=0):
        r = self.add(label=label, kind="code", mnem=mnem, args=list(args), comment=comment, src=src)
        r.text = r.fmt()
        return r

    # ----------------------------------------------------------- traducción
    def traducir(self):
        fuente = self.ruta.read_text(encoding="utf-8-sig")
        hay_end = False
        previo = None
        reemplazos = self.hints.get("replace", {})
        subs = [(re.compile(p), lineas) for p, lineas in self.hints.get("sub", [])]
        for ln, raw in enumerate(fuente.splitlines(), 1):
            partes = raw.split(";", 1)
            codigo, comentario = partes[0].strip(), (partes[1].strip() if len(partes) > 1 else "")
            if not codigo:
                self.add(kind="text", comment=comentario, src=ln)
                continue
            etiqueta, resto = None, codigo
            toks = codigo.split(None, 1)
            primero = toks[0]
            if not codigo.startswith("."):
                if primero.endswith(":"):
                    etiqueta, resto = primero[:-1], (toks[1] if len(toks) > 1 else "")
                elif primero.upper() not in VALID_LC3:
                    etiqueta, resto = primero, (toks[1] if len(toks) > 1 else "")
            if etiqueta and (A10.is_mnemonic(etiqueta) or A10.REG_RE.match(etiqueta) or not A10.LABEL_RE.match(etiqueta)):
                self.aviso(ln, "ERROR", f"la etiqueta {etiqueta} no es válida en LC10 (nombre de instrucción o carácter inválido)")
            norma = " ".join(resto.upper().replace(",", " ").split())
            sustituto = reemplazos.get(ln)
            if sustituto is None:
                sustituto = next((lineas for rx, lineas in subs if rx.fullmatch(norma)), None)
            if sustituto is not None:
                if not sustituto and (etiqueta or comentario):
                    self.add(label=etiqueta, kind="text", comment=comentario, src=ln)
                for k, linea in enumerate(sustituto):
                    self._linea_literal(linea, etiqueta if k == 0 else None, comentario if k == 0 else "", ln)
                previo = None
                continue
            if not resto:
                self.add(label=etiqueta, kind="text", comment=comentario, src=ln)
                continue
            partes_op = resto.split(None, 1)
            op = partes_op[0].upper()
            oper = partes_op[1].strip() if len(partes_op) > 1 else ""

            if op == ".ORIG":
                if self.es_main:
                    self.add(label=etiqueta, kind="dir", text=f".ORIG {oper}", comment=comentario, src=ln)
                else:
                    self.add(kind="text", comment=f"(se quitó .ORIG {oper}: los módulos de LC10 no llevan origen)", src=ln)
                continue
            if op == ".END":
                hay_end = True
                break
            if op == ".EXTERNAL":
                for k, nombre in enumerate(n for n in re.split(r"[\s,]+", oper) if n):
                    self.add(kind="dir", text=f".EXTERNAL {self.qual(nombre)}", comment=comentario if k == 0 else "", src=ln)
                continue
            if op == ".FILL":
                n = self.numero_texto(oper)
                if n is None and not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_\-]*", oper):
                    self.aviso(ln, "ERROR", f".FILL con una expresión: {oper}")
                self.add(label=etiqueta, kind="data", text=f".FILL {n if n is not None else self.qual(oper)}", comment=comentario, src=ln)
                previo = None
                continue
            if op == ".BLKW":
                n = self.numero_texto(oper) or oper
                if etiqueta in self.hints.get("blkb", ()):
                    self.add(label=etiqueta, kind="data", text=f".BLKB {n}", comment=comentario or "buffer de texto: un byte por carácter", src=ln)
                else:
                    self.add(label=etiqueta, kind="data", text=f".BLKW {n}", comment=comentario, src=ln)
                continue
            if op == ".STRINGZ":
                if re.search(r"\\x|\\a|\\b|\\f|\\v|\\u", oper):
                    self.aviso(ln, "REVISAR", "escape de cadena que LC10 no reconoce")
                self.add(label=etiqueta, kind="data", text=f".STRINGZ {oper}", comment=comentario, src=ln)
                continue
            if op.startswith("."):
                self.aviso(ln, "ERROR", f"directiva no traducida: {op}")
                continue

            if previo and op.startswith("BR") and op not in ("BR", "BRNZP"):
                self.aviso(ln, "REVISAR", f"salto condicional justo después de {previo}: en LC-3 de la cátedra esa instrucción "
                                          "modifica N Z P (LEA con el valor, TRAP con el signo de R1); en LC10 el LEA no, y tras un TRAP las banderas "
                                          "son las que deja la rutina del SO (docs/ISA.md, sección 5)")
            self.instruccion(ln, etiqueta, op, split_ops(oper), comentario)
            previo = "LEA" if op == "LEA" else ("TRAP" if op in TRAPS or op == "TRAP" else None)
        if not hay_end:
            self.aviso(0, "ERROR", "no se encontró .END")
        for linea in self.hints.get("extra", []):
            self._linea_literal(linea, None, "(agregado a mano)", 0)
        etiquetas: dict[str, str] = {}
        for r in self.recs:
            if r.label:
                k = r.label.upper()
                if k in etiquetas and etiquetas[k] != r.label:
                    self.aviso(0, "ERROR", f"las etiquetas {etiquetas[k]} y {r.label} solo se distinguen por mayúsculas")
                etiquetas[k] = r.label

    def _linea_literal(self, linea: str, etiqueta, comentario, ln):
        """Línea de LC10 escrita a mano en port_hints.py (formato: [ETIQUETA] OPERACIÓN operandos)."""
        s = linea.strip()
        toks = s.split(None, 1)
        etq = etiqueta
        if toks and toks[0].endswith(":"):
            etq, s = toks[0][:-1], (toks[1] if len(toks) > 1 else "")
        elif toks and not toks[0].startswith(".") and not A10.is_mnemonic(toks[0].upper()) and toks[0].upper() not in VALID_LC3:
            etq, s = toks[0], (toks[1] if len(toks) > 1 else "")
        if not s:
            self.add(label=etq, kind="text", comment=comentario, src=ln)
            return
        op, _, rest = s.partition(" ")
        if op.startswith("."):
            self.add(label=etq, kind="data", text=s, comment=comentario or "(a mano)", src=ln)
        elif op.upper() == "ADD" and len(split_ops(rest)) == 3 and not A10.REG_RE.match(split_ops(rest)[2]):
            self.instruccion(ln, etq, "ADD", split_ops(rest), comentario or "(a mano)")
        else:
            self.code(etq, op, split_ops(rest), comentario or "(a mano)", ln)

    def instruccion(self, ln, etiqueta, op, a, comentario):
        C = self.code
        if op in ("ADD", "AND"):
            if len(a) != 3:
                self.aviso(ln, "ERROR", f"{op} con {len(a)} operandos")
                return
            if A10.REG_RE.match(a[2]):
                C(etiqueta, op, a, comentario, ln)
                return
            v = self.num(a[2])
            if v is not None and op == "ADD" and a[0].upper() in self.hints.get("scale", ()) and a[0].upper() == a[1].upper():
                v *= 2
                comentario = (comentario + " " if comentario else "") + "(palabras -> bytes)"
            if v is None:
                self.aviso(ln, "ERROR", f"{op}: inmediato simbólico {a[2]}")
                C(etiqueta, op, a, comentario, ln)
            elif -8 <= v <= 7:
                C(etiqueta, op, [a[0], a[1], f"#{v}"], comentario, ln)
            elif op == "ADD":
                self.aviso(ln, "INFO", f"ADD #{v} se expande en varios ADD (LC10 llega a -8..7)")
                resto, primero = v, True
                while resto:
                    paso = max(-8, min(7, resto))
                    C(etiqueta if primero else None, "ADD", [a[0], a[1] if primero else a[0], f"#{paso}"],
                      (comentario or f"ADD {a[0]}, {a[1]}, #{v}") if primero else "(sigue)", ln)
                    resto -= paso
                    primero = False
            else:
                self.aviso(ln, "ERROR", f"AND con inmediato {v}: no entra en 4 bits; resolver a mano")
                C(etiqueta, op, [a[0], a[1], f"#{v}"], (comentario + " " if comentario else "") + "<<< REVISAR", ln)
        elif op == "NOT":
            C(etiqueta, "NOT", a, comentario, ln)
        elif op in ("LD", "ST", "LEA"):
            C(etiqueta, op, [a[0], self.qual(a[1])], comentario, ln)
        elif op == "LDI":
            self.aviso(ln, "REVISAR", "LDI se traduce como LD + LDW")
            C(etiqueta, "LD", [a[0], self.qual(a[1])], comentario, ln)
            C(None, "LDW", [a[0], a[0], "#0"], "(LDI)", ln)
        elif op == "STI":
            self.aviso(ln, "ERROR", "STI no tiene traducción mecánica (necesita un registro de apoyo)")
            self.add(label=etiqueta, kind="text", comment=f"STI {', '.join(a)}   <<< REVISAR", src=ln)
        elif op in ("LDR", "STR"):
            k = self.num(a[2])
            if k is None:
                self.aviso(ln, "ERROR", f"{op} con offset simbólico {a[2]}")
                return
            ch = self.hints.get("char", ())
            if ch == "ALL" or (ch == "LDR" and op == "LDR") or (ch == "STR" and op == "STR") or (not isinstance(ch, str) and ln in ch):
                nm = "LDL" if op == "LDR" else "STL"
                self.ldrstr.append((ln, f"{op} {', '.join(a)}  -> {nm} (carácter)"))
                if not -16 <= k <= 15:
                    self.aviso(ln, "ERROR", f"{op} con offset {k}: fuera de -16..15")
                C(etiqueta, nm, [a[0], a[1], f"#{k}"], comentario, ln)
            else:
                nm = "LDW" if op == "LDR" else "STW"
                k -= self.hints.get("bias", {}).get(a[1].upper(), 0)
                if not -16 <= k <= 15:
                    self.aviso(ln, "ERROR", f"{op} con offset {k}: LDW/STW llegan a -16..15 palabras")
                self.ldrstr.append((ln, f"{op} {', '.join(a)}  -> {nm} (palabra)"))
                C(etiqueta, nm, [a[0], a[1], f"#{2 * k}"], comentario, ln)
        elif op.startswith("BR"):
            fl = op[2:]
            C(etiqueta, "BR" + fl.lower() if fl else "BR", [self.qual(a[0])], comentario, ln)
        elif op == "JSR":
            C(etiqueta, "JSR", [self.qual(a[0])], comentario, ln)
        elif op in ("JSRR", "JMP"):
            C(etiqueta, op, a, comentario, ln)
        elif op in ("RET", "HALT", "NOP", "GETC", "OUT", "PUTS", "IN"):
            C(etiqueta, op, [], comentario, ln)
        elif op == "TRAP":
            C(etiqueta, "TRAP", a, comentario, ln)
        else:
            self.aviso(ln, "ERROR", f"instrucción no soportada: {op}")
            self.add(label=etiqueta, kind="text", comment=f"{op} {' '.join(a)}   <<< REVISAR", src=ln)

    # ----------------------------------------------------------- texto, disposición y alcance
    def texto(self) -> str:
        return "\n".join(r.render() for r in self.recs) + "\n.END\n"

    def disposicion(self):
        """Ensambla la salida y devuelve (módulo, {id(rec): offset})."""
        mod = A10.first_pass(self.ruta.name, self.texto(), self.es_main)
        porlinea = {it.line: it.offset for it in mod.items if it.kind != "bytes" or not it.pad}
        offs = {}
        for i, r in enumerate(self.recs):
            if i + 1 in porlinea:
                offs[id(r)] = porlinea[i + 1]
        return mod, offs

    def violaciones(self):
        """[(rec, exceso)] de las instrucciones cuyo destino queda fuera de alcance, y la suma de excesos."""
        mod, offs = self.disposicion()
        res, total = [], 0
        for r in self.recs:
            dest = r.target()
            if dest is None or "-" in dest:
                continue
            key = dest.upper()
            if key not in mod.symbols or id(r) not in offs:
                continue
            delta = mod.symbols[key] - (offs[id(r)] + 2)
            tipo = "BR" if r.mnem.startswith("BR") else r.mnem
            lo, hi = LIMITES[tipo]
            val = delta if tipo == "LEA" else delta // 2
            exc = max(lo - val, val - hi, 0)
            if exc:
                res.append((r, exc, val))
                total += exc
        return res, total

    # bloques de datos ----------------------------------------------------
    def preparar_bloques(self):
        """Asigna `chunk` a los datos. Cada etiqueta que solo usan LD/ST empieza un bloque; el resto de las
        líneas continúa el bloque anterior (las tablas y vectores quedan enteros)."""
        solo_ldst: dict[str, bool] = {}
        for r in self.recs:
            d = r.target()
            if d is None:
                continue
            k = d.upper()
            solo_ldst[k] = solo_ldst.get(k, True) and r.mnem in ("LD", "ST")
        for r in self.recs:       # punteros .FILL a etiquetas locales también usan la etiqueta
            if r.kind == "data" and r.text.startswith(".FILL"):
                a = r.text.split(None, 1)[1].strip()
                if a.upper() in solo_ldst:
                    solo_ldst[a.upper()] = False
        n = len(self.recs)
        actual = None
        i = 0
        while i < n:
            r = self.recs[i]
            esdato = r.kind == "data" or (r.kind == "text" and r.label and not r.text and self._sigue_dato(i))
            if not esdato:
                i += 1
                actual = None
                continue
            cabeza = actual is None or (r.label and solo_ldst.get(r.label.upper(), False))
            if cabeza:
                self._chunk_ids += 1
                actual = self._chunk_ids
            r.chunk = actual
            i += 1
        ptr = self.adyacencias()
        previo = None
        for r in self.recs:
            if r.chunk is None:
                continue
            if previo is not None and r.chunk != previo.chunk and r.label and solo_ldst.get(r.label.upper(), False):
                etqs = [x.label for x in self.recs if x.chunk == previo.chunk and x.label and x.label.upper() in ptr]
                if etqs:
                    self.aviso(r.src, "ADYACENCIA", f"{r.label} (solo LD/ST) sigue al bloque de {', '.join(etqs)} (se usa como base de puntero): "
                                                    "si el código lee más allá de esa etiqueta, revisar")
            previo = r
        # comentarios y líneas en blanco dentro de una corrida de datos siguen al bloque anterior
        for i, r in enumerate(self.recs):
            if r.kind == "text" and not r.label and r.chunk is None:
                ant = self.recs[i - 1].chunk if i else None
                sig = next((x.chunk for x in self.recs[i + 1:] if x.kind != "text" or x.label), None)
                if ant is not None and sig is not None:
                    r.chunk = ant

    def _sigue_dato(self, i: int) -> bool:
        """Una etiqueta sola en una línea es de datos si lo que sigue (sin contar comentarios) es un dato."""
        for r in self.recs[i + 1:]:
            if r.kind == "data":
                return True
            if r.kind == "code":
                return False
        return False

    def posiciones(self, excluir: int):
        """Índices (insertar antes de recs[i]) a los que no se llega por continuación y que no parten un bloque."""
        pos = []
        previo_incond = True
        for i, r in enumerate(self.recs):
            ant = self.recs[i - 1] if i else None
            dentro = ant is not None and ant.chunk is not None and ant.chunk == r.chunk
            etq_sola = ant is not None and ant.kind == "text" and ant.label and not ant.text
            if previo_incond and not dentro and not etq_sola and r.chunk != excluir:
                pos.append(i)
            if r.kind == "code":
                previo_incond = incondicional(r)
        if previo_incond:
            pos.append(len(self.recs))
        return pos

    def mover(self, chunk: int, pos_rec: Rec | None):
        piezas = [r for r in self.recs if r.chunk == chunk]
        self.recs = [r for r in self.recs if r.chunk != chunk]
        i = self.recs.index(pos_rec) if pos_rec is not None else len(self.recs)
        self.recs[i:i] = piezas

    def nuevo_bloque(self, recs: list[Rec], antes_de: Rec | None = None) -> int:
        self._chunk_ids += 1
        for r in recs:
            r.chunk = self._chunk_ids
        i = self.recs.index(antes_de) if antes_de is not None else len(self.recs)
        self.recs[i:i] = recs
        return self._chunk_ids

    def reparar(self):
        self.preparar_bloques()
        punteros: dict[str, str] = {}
        tramps = 0
        atascados: set[tuple[int, str]] = set()      # (id del rec, destino) que ningún movimiento mejora

        def puntero(dest: str) -> str:
            if dest.upper() not in punteros:
                etq = f"{dest.replace('-', '_')}_ptr"
                punteros[dest.upper()] = etq
                self.nuevo_bloque([Rec(label=etq, kind="data", text=f".FILL {dest}", comment="dirección de " + dest, tag="ptr")])
            return punteros[dest.upper()]

        for _ in range(300):
            viol, total = self.violaciones()
            if not viol:
                return
            # 1. mover el bloque de datos de la peor violación, si algún lugar lo mejora
            progreso = False
            for r, exc, val in sorted(viol, key=lambda v: -v[1]):
                dest = r.target()
                chunk = self._chunk_de(dest)
                if chunk is None or (id(r), dest) in atascados:
                    continue
                mejor = None
                for p in self.posiciones(chunk):
                    ref = self.recs[p] if p < len(self.recs) else None
                    copia = list(self.recs)
                    self.mover(chunk, ref)
                    try:
                        _, tot = self.violaciones()
                    except A10.AsmError:
                        tot = 10 ** 9
                    self.recs = copia
                    if mejor is None or tot < mejor[0]:
                        mejor = (tot, ref)
                if mejor is not None and mejor[0] < total:
                    self.mover(chunk, mejor[1])
                    self.movidos.append(dest)
                    progreso = True
                    break
                atascados.add((id(r), dest))
            if progreso:
                continue
            # 2. LEA lejano -> LD de un puntero (misma cantidad de instrucciones)
            lea = [v for v in viol if v[0].mnem == "LEA"]
            if lea:
                for r, _, _ in lea:
                    dest = r.target()
                    r.mnem = "LD"
                    r.set_target(puntero(dest))
                    r.comment = (r.comment + " " if r.comment else "") + f"(LEA {dest} quedaba lejos)"
                continue
            # 3. BR lejano -> trampolín (otro BR en un punto intermedio)
            br = [v for v in viol if v[0].mnem.startswith("BR") and v[0].tag != "tramp"
                  and (not self._movible(v[0].target()) or (id(v[0]), v[0].target()) in atascados)]
            if br:
                r, _, _ = br[0]
                tramps += 1
                etq = f"{r.target()}_tr{tramps}"
                tr = Rec(label=etq, kind="code", mnem="BR", args=[r.target()], comment=f"trampolín de BR {r.target()}", tag="tramp")
                tr.text = tr.fmt()
                r.set_target(etq)
                self.nuevo_bloque([tr])
                continue
            # 4. último recurso para los LD: la dirección sale de un puntero cercano y se lee con LDW
            lds = [v for v in viol if v[0].mnem == "LD" and v[0].tag != "ldi"]
            if lds:
                for r, _, _ in lds:
                    dest = r.target()
                    r.set_target(puntero(dest))
                    r.tag = "ldi"
                    r.comment = (r.comment + " " if r.comment else "") + f"(LD {dest} quedaba lejos)"
                    ldw = Rec(kind="code", mnem="LDW", args=[r.args[0], r.args[0], "#0"], comment=f"(lee {dest})")
                    ldw.text = ldw.fmt()
                    self.recs.insert(self.recs.index(r) + 1, ldw)
                continue
            return

    def _chunk_de(self, etiqueta: str | None) -> int | None:
        if etiqueta is None:
            return None
        for r in self.recs:
            if r.label and r.label.upper() == etiqueta.upper():
                return r.chunk
        return None

    def _movible(self, etiqueta: str | None) -> bool:
        return self._chunk_de(etiqueta) is not None

    def adyacencias(self):
        """Avisa de bloques de datos que se separaron de un bloque anterior con una etiqueta usada como base de puntero."""
        base = set()
        for r in self.recs:
            if r.mnem == "LEA":
                base.add(r.args[1].upper())
        for r in self.recs:
            if r.kind == "data" and r.text.startswith(".FILL"):
                a = r.text.split(None, 1)[1].strip().upper()
                base.add(a)
        return base


def informar(m: Modulo, informe: list):
    informe.append(f"== {m.ruta.name}")
    for ln, tipo, msg in sorted(m.avisos, key=lambda x: (x[0], x[1])):
        if tipo != "INFO":
            informe.append(f"  [{tipo}] fuente {ln}: {msg}")
    for ln, d in m.ldrstr:
        informe.append(f"  [LDR/STR] fuente {ln}: {d}")
    if m.movidos:
        informe.append(f"  [MOVIDOS] {', '.join(sorted(set(m.movidos)))}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("carpeta")
    ap.add_argument("-o", "--salida", default=str(RAIZ / "asm" / "bench10"))
    ap.add_argument("--main", default="main_grupo27.asm")
    ap.add_argument("--solo", nargs="*", default=[], help="traducir solo estos archivos (por nombre)")
    args = ap.parse_args()
    base = Path(args.carpeta).resolve()
    asm = cargar("asm_lc3_catedra", base / "assembler_LC3.py")
    enlazador = asm.ProjectLinker(base / "lib")
    enlazador.assemble_file(base / args.main, "obj")
    salida = Path(args.salida)
    salida.mkdir(parents=True, exist_ok=True)
    informe, total = [], {}
    for k, unidad in enumerate(enlazador.unit_order):
        refs = {ref: f"{ruta.stem}-{simbolo}" for ref, (ruta, simbolo) in unidad.external_targets.items()}
        if args.solo and unidad.path.name not in args.solo:
            continue
        m = Modulo(unidad.path, k == 0, refs, asm)
        m.traducir()
        try:
            m.reparar()
            _, rest = m.violaciones()
            viol, _ = m.violaciones()
            for r, exc, val in viol:
                m.aviso(r.src, "ALCANCE", f"{r.mnem} {r.target()}: {val} (límite {LIMITES['BR' if r.mnem.startswith('BR') else r.mnem]})")
        except A10.AsmError as e:
            m.aviso(0, "ERROR", f"la salida no ensambla: {e.msg} (línea {e.line})")
        (salida / unidad.path.name).write_text(m.texto(), encoding="utf-8", newline="\n")
        informar(m, informe)
        for _, tipo, _ in m.avisos:
            total[tipo] = total.get(tipo, 0) + 1
    (salida / "informe.txt").write_text("\n".join(informe) + "\n", encoding="utf-8")
    print("resumen:", total)
    print(f"escrito en {salida}")


if __name__ == "__main__":
    main()
