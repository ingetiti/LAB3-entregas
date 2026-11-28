#!/usr/bin/env python3
"""
Eliminacion de codigo y datos muertos en el enlazado (opcion -D del ensamblador).

Equivale al "--gc-sections" de un enlazador: se conserva solo lo que el
programa de entrada puede usar y se borra el resto ANTES de asignar
direcciones, asi la imagen ocupa menos bytes. No cambia ninguna instruccion
que se ejecuta.

Que se conserva (calculo de punto fijo, solo cuentan las referencias que
aparecen en elementos que a su vez se conservan):
  * CODIGO: lo alcanzable por el flujo de control desde la primera instruccion
    del programa de entrada o desde cualquier etiqueta de codigo nombrada
    (BR/JSR/DBP/BRR/BRX, y destinos de JSRR/JMP tomados de cualquier .FILL o
    LEA). La caida a la siguiente instruccion se sigue salvo despues de BR
    incondicional, JMP, RET, RTI y HALT.
  * DATOS: un bloque (.FILL/.BLKW/.STRINGZ con las palabras sin etiqueta que
    le siguen) se conserva si su etiqueta se nombra. Si alguna etiqueta de una
    racha contigua de datos tiene su DIRECCION tomada (LEA, .FILL etiqueta o
    referencia desde otro modulo), se conserva la racha entera, porque se puede
    recorrer con LDR/STR Rx, Rbase, #k (por ejemplo GUARDADO_R1..R7 del G21).
  * Si un modulo nombra una etiqueta de fin de modulo, el modulo queda entero.
"""
import re

BR_INCOND = re.compile(r"^BR(NZP)?$")
CORTA_FLUJO = ("JMP", "RET", "RTI", "HALT")


def _salta_a(op, args):
    if (op.startswith("BR") or op in ("JSR", "DBP")) and args:
        return args[-1].upper()
    return None


def _corta(op):
    return bool(BR_INCOND.match(op)) or op in CORTA_FLUJO


def eliminar(prog):
    """Borra de prog.modules los elementos muertos. Devuelve la lista de
    bloques eliminados: (modulo, linea_desde, linea_hasta, bytes, etiquetas)."""
    mods = prog.modules
    info = {}
    for m in mods:
        idx = {}
        for i, it in enumerate(m.items):
            for p in it[6]:
                idx[p] = i
        dato = [it[1].startswith(".") for it in m.items]
        # rachas contiguas de datos y bloques (etiqueta + palabras sin etiqueta)
        racha, bloque = [None] * len(m.items), [None] * len(m.items)
        r = b = -1
        for i, it in enumerate(m.items):
            if dato[i]:
                if i == 0 or not dato[i - 1]:
                    r += 1
                if i == 0 or not dato[i - 1] or it[6]:
                    b += 1
                racha[i], bloque[i] = r, b
        info[m.key] = (idx, dato, racha, bloque)

    vivo = {m.key: set() for m in mods}
    entero = set()
    while True:
        refs, direccion = set(), set()
        for m in mods:
            for i in vivo[m.key] | (set(range(len(m.items))) if m.key in entero else set()):
                op, args = m.items[i][1], m.items[i][2]
                for a in args:
                    u = a.upper()
                    if u in m.labels:
                        refs.add((m.key, u))
                        if op in ("LEA", ".FILL"):
                            direccion.add((m.key, u))
                    elif u in m.externals:
                        ref, _, lab = u.partition("-")
                        k = prog.resolve_key(m, ref.lower())
                        refs.add((k, lab))
                        direccion.add((k, lab))
        cambio = False
        for m in mods:
            idx, dato, racha, bloque = info[m.key]
            v = vivo[m.key]
            antes = len(v)
            if m.key not in entero and any((m.key, t) in refs for t in m.tail_labels):
                entero.add(m.key)
                cambio = True
            if m.key in entero:
                v.update(range(len(m.items)))
                continue
            # codigo alcanzable
            pila = [0] if m.is_entry else []
            pila += [idx[l] for (k, l) in refs if k == m.key and l in idx and not dato[idx[l]]]
            visto = set()
            while pila:
                i = pila.pop()
                while i < len(m.items) and not dato[i] and i not in visto:
                    visto.add(i)
                    op, args = m.items[i][1], m.items[i][2]
                    d = _salta_a(op, args)
                    if d and d in idx:
                        pila.append(idx[d])
                    if _corta(op):
                        break
                    i += 1
            v.update(visto)
            # datos
            rachas_dir = {racha[idx[l]] for (k, l) in direccion
                          if k == m.key and l in idx and dato[idx[l]]}
            bloques_ref = {bloque[idx[l]] for (k, l) in refs
                           if k == m.key and l in idx and dato[idx[l]]}
            for i in range(len(m.items)):
                if dato[i] and (racha[i] in rachas_dir or bloque[i] in bloques_ref):
                    v.add(i)
            cambio |= len(v) != antes
        if not cambio:
            break

    quitados = []
    for m in mods:
        v = vivo[m.key]
        i = 0
        while i < len(m.items):
            if i in v:
                i += 1
                continue
            j = i
            while j < len(m.items) and j not in v:
                j += 1
            bloque = m.items[i:j]
            quitados.append((m.key, bloque[0][0], bloque[-1][0], sum(it[4] for it in bloque),
                             [p for it in bloque for p in it[6]]))
            i = j
        if len(v) != len(m.items):
            m.items = [it for k, it in enumerate(m.items) if k in v]
            m.relayout()
    return quitados
