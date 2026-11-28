"""
Optimizacion de mirilla (peephole) del ensamblador de la ISA LOVELACE.

Fusiona pares de instrucciones de codigo LC-3 en las instrucciones nuevas:

  A) ADD Rx, Rx, #-1  +  BRp L   ->  DBP Rx, L
     DBP deja N/Z/P igual que el ADD, asi que el resultado es el mismo.

  B) ADD Rx, Rx, #0   +  BRc L   ->  BRRc Rx, L     (c = n, z, p o combinacion)
     BRR no modifica las banderas: solo se fusiona si un analisis de
     "banderas vivas" demuestra que ninguna instruccion posterior (por el camino
     de salto ni por el que sigue) lee las banderas que dejaba el ADD.

Condiciones comunes: nadie salta a la segunda instruccion del par (no tiene
etiqueta), el destino queda dentro del alcance de la instruccion nueva (si no,
se deshace la fusion) y el modulo no usa las banderas C/V (codigo escrito a
mano para la ISA LOVELACE con ADC o BRC, por ejemplo, no se toca).
"""
import re

REG_RE = re.compile(r"^R([0-7])$", re.I)
BR_RE = re.compile(r"^BR(N?Z?P?)$")
USAN_CV = {"ADC", "RLC", "BRC", "BRNC", "BRV", "BRNV", "BRHI", "BRLS"}   # leen C o V
FIJAN_NZP = {"ADD", "AND", "NOT", "SUB", "ADC", "ADDX", "OR", "XOR", "LD", "LDR",
             "LDB", "LDBH", "LSL", "LSR", "ASR", "RLC", "DBP",
             "MUL", "MULH", "MULHU", "DIV", "REM", "DIVU", "REMU"}
TRANSPARENTES = {"ST", "STR", "STB", "STBH", "LEA", "PUSH", "POP", "NOP", "TRAP",
                 "GETC", "OUT", "PUTS", "IN", "PUTSP"}   # los TRAP vuelven con RTI (PSR restaurado)


def _imm(tok):
    t = tok.strip()
    try:
        if t.startswith("#"):
            return int(t[1:])
        if t[:1] in "xX":
            return int(t[1:], 16)
        return int(t)
    except ValueError:
        return None


def _cond(op):
    m = BR_RE.match(op)
    if not m:
        return None
    return m.group(1) or "NZP"


def optimizar_modulo(m, tipos=("DBP", "BRR")):
    """tipos: fusiones permitidas (se pueden apagar por separado para medir su aporte)."""
    items = m.items
    if any(it[1] in USAN_CV for it in items):
        return {}
    lab_idx = {}
    for i, it in enumerate(items):
        for p in it[6]:
            lab_idx[p] = i
    for p in m.tail_labels:
        lab_idx[p] = len(items)

    def banderas_muertas(inicio):
        """True si desde 'inicio' ninguna instruccion lee N/Z/P antes de que se
        vuelvan a escribir (siguiendo saltos incondicionales)."""
        pendientes, vistos = [inicio], set()
        while pendientes:
            i = pendientes.pop()
            pasos = 0
            while True:
                if i in vistos:
                    break
                vistos.add(i)
                pasos += 1
                if i >= len(items) or pasos > 60:
                    return False
                op = items[i][1]
                if op.startswith("."):
                    return False                    # caeria en datos
                if op in FIJAN_NZP:
                    break                           # banderas reescritas: camino seguro
                if op == "HALT":
                    break
                c = _cond(op)
                if c == "NZP":
                    destino = items[i][2][0].upper()
                    if destino not in lab_idx:
                        return False
                    i = lab_idx[destino]
                    continue
                if c is not None:
                    return False                    # BR condicional: lee las banderas
                if op in TRANSPARENTES:
                    i += 1
                    continue
                return False                        # JSR, JMP, RET, BRR, etc.: conservador
        return True

    nuevos, cuenta = [], {}
    i = 0
    while i < len(items):
        it = items[i]
        sig = items[i + 1] if i + 1 < len(items) else None
        fus = None
        if (it[1] == "ADD" and sig is not None and not sig[6] and len(it[2]) == 3
                and REG_RE.match(it[2][0]) and it[2][0].upper() == it[2][1].upper()):
            k = _imm(it[2][2]) if not REG_RE.match(it[2][2]) else None
            c = _cond(sig[1])
            if c is not None and sig[2]:
                destino = sig[2][0].upper()
                if k == -1 and c == "P" and destino in lab_idx and "DBP" in tipos:
                    fus = ("DBP", [it[2][0], sig[2][0]], 8)
                elif ("BRR" in tipos and k == 0 and c != "NZP" and destino in lab_idx
                      and banderas_muertas(i + 2) and banderas_muertas(lab_idx[destino])):
                    fus = ("BRR" + c, [it[2][0], sig[2][0]], 5)
        if fus:
            op, args, bits = fus
            nuevos.append([it[0], op, args, 0, 2, 0, it[6], (it, sig, bits)])
            i += 2
        else:
            nuevos.append(it)
            i += 1

    # verificar alcances; deshacer las fusiones que queden fuera de rango
    while True:
        m.items = nuevos
        m.relayout()
        deshacer = []
        for j, it in enumerate(nuevos):
            if len(it) > 7:
                bits = it[7][2]
                d = m.labels[it[2][1].upper()] - (it[3] + 2)
                pal = d // 2
                if not -(1 << (bits - 1)) <= pal <= (1 << (bits - 1)) - 1:
                    deshacer.append(j)
        if not deshacer:
            break
        for j in reversed(deshacer):
            a, b, _ = nuevos[j][7]
            nuevos[j:j + 1] = [a, b]
    for it in nuevos:
        if len(it) > 7:
            k = "DBP" if it[1] == "DBP" else "BRR"
            cuenta[k] = cuenta.get(k, 0) + 1
    return cuenta
