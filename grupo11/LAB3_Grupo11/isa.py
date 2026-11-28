"""Definiciones comunes de la ISA del grupo 11 (ISA-G11).

Este modulo es la unica fuente de verdad de la codificacion: lo usan el
ensamblador y el simulador.

Resumen
-------
* Instrucciones de 16 bits, opcode fijo de 5 bits (bits 15..11).
* 8 registros de 16 bits R0..R7 (R7 = enlace de JSR/JSRR, R6 = puntero de pila).
* Memoria direccionable por byte, 2^16 direcciones, palabras de 16 bits
  en formato big-endian (byte par = byte alto de la palabra).
* PC de 16 bits, siempre par; se incrementa de a 2.
* Codigos de condicion N, Z, P (signo del resultado) mas V (overflow) y C (acarreo).
"""

# ---------------------------------------------------------------- opcodes
OPCODES = {
    'NOP': 0,   'ADD': 1,   'SUB': 2,   'AND': 3,   'OR': 4,    'STK': 5,
    'SHR': 6,   'ADDI': 9,  'ANDI': 10, 'SHI': 11,           # 7 y 8: reservados
    'MOVI': 12, 'MOVHI': 13, 'CMP': 14, 'CMPI': 15, 'UN': 16,
    'LDW': 17,  'LDBL': 18, 'LDBH': 19, 'STW': 20,  'STBL': 21, 'STBH': 22,
    'LD': 23,   'ST': 24,   'LEA': 25,
    'BR': 26,   'BRL': 27,  'JSR': 28,  'JR': 29,   'TRAP': 30, 'LDWX': 31,
}
OPNAME = {v: k for k, v in OPCODES.items()}
assert len(OPCODES) == 30 and len(OPNAME) == 30   # 2 opcodes (7 y 8) reservados

# ------------------------------------------------- campo f (bits 1..0) tipo R
# ADD: 0 ADD, 1 ADC | SUB: 0 SUB, 1 SBC | AND: 0 AND, 1 BIC (a & ~b)
# OR: 0 OR, 1 XOR | SHR: tipo de desplazamiento
SHIFT_TYPES = {'LSL': 0, 'LSR': 1, 'ASR': 2, 'ROL': 3}

# ---------------------------------------------------------- operaciones UN
UN_OPS = {'MOV': 0, 'NOT': 1, 'NEG': 2, 'SEXT': 3, 'ZEXT': 4, 'SWAP': 5,
          'ABS': 6, 'CLZ': 7}

# ---------------------------------------------------- condiciones de salto
# Se usan 4 bits.  0..6 reproducen los BRn/BRz/BRp de la LC-3.
COND = {
    'AL': 0,   # siempre
    'EQ': 1,   # Z
    'NE': 2,   # !Z
    'LT': 3,   # N
    'GE': 4,   # !N
    'GT': 5,   # P
    'LE': 6,   # !P
    'VS': 7,   # V
    'VC': 8,   # !V
    'CS': 9,   # C           (tras CMP/SUB: sin prestamo, a >= b sin signo)
    'CC': 10,  # !C          (a < b sin signo)
    'SLT': 11,  # N != V     (a < b con signo, correcto aun con overflow)
    'SGE': 12,  # N == V
    'SGT': 13,  # !Z && N == V
    'SLE': 14,  # Z || N != V
    'UGT': 15,  # C && !Z    (a > b sin signo)
}
COND_NAME = {v: k for k, v in COND.items()}


def cond_inversa(c):
    """Condicion opuesta (para expandir saltos fuera de rango)."""
    if c == COND['AL']:
        raise ValueError('AL no tiene inversa')
    if c == COND['UGT']:
        raise ValueError('UGT no tiene inversa codificable')
    return c + 1 if c % 2 == 1 else c - 1


def cond_cumple(c, n, z, v, carry):
    """Evalua una condicion con los flags actuales (n,z,v,carry booleanos)."""
    p = (not n) and (not z)
    if c == 0:
        return True
    if c == 1:
        return z
    if c == 2:
        return not z
    if c == 3:
        return n
    if c == 4:
        return not n
    if c == 5:
        return p
    if c == 6:
        return not p
    if c == 7:
        return v
    if c == 8:
        return not v
    if c == 9:
        return carry
    if c == 10:
        return not carry
    if c == 11:
        return n != v
    if c == 12:
        return n == v
    if c == 13:
        return (not z) and (n == v)
    if c == 14:
        return z or (n != v)
    return carry and (not z)          # 15 UGT


# ----------------------------------------------------------- vectores TRAP
TRAP_GETC = 0x20     # R0 <- caracter leido (byte bajo)
TRAP_OUT = 0x21      # escribe el byte bajo de R0
TRAP_PUTS = 0x22     # escribe la cadena de bytes (terminada en 0) en [R0]
TRAP_IN = 0x23       # pide un caracter (con eco) -> R0
TRAP_HALT = 0x25     # detiene la maquina
TRAP_NAMES = {TRAP_GETC: 'GETC', TRAP_OUT: 'OUT', TRAP_PUTS: 'PUTS',
              TRAP_IN: 'IN', TRAP_HALT: 'HALT'}


# ------------------------------------------------------------- utilidades
def sext(valor, bits):
    """Extiende el signo de un campo de `bits` bits."""
    valor &= (1 << bits) - 1
    if valor & (1 << (bits - 1)):
        valor -= 1 << bits
    return valor


def a_signo16(v):
    v &= 0xFFFF
    return v - 0x10000 if v & 0x8000 else v


def base_pc_relativa(direccion_instr):
    """Base de LD/ST/LEA: Align4(PC+2)."""
    return (direccion_instr + 2) & ~3 & 0xFFFF


def formato_instr(w):
    """Texto legible de una instruccion (para la traza del simulador)."""
    op = (w >> 11) & 31
    nom = OPNAME.get(op, '?')
    dr = (w >> 8) & 7
    s1 = (w >> 5) & 7
    s2 = (w >> 2) & 7
    f = w & 3
    if op == 0:
        return 'NOP'
    if op in (7, 8):
        return 'RESERVADO'
    if op in (1, 2, 3, 4):
        n = {1: ['ADD', 'ADC'], 2: ['SUB', 'SBC'], 3: ['AND', 'BIC'],
             4: ['OR', 'XOR']}[op][f]
        return f'{n} R{dr},R{s1},R{s2}'
    if op == 5:
        return f'{"POP" if (w >> 7) & 1 else "PUSH"} R{dr}'
    if op == 6:
        n = ['LSL', 'LSR', 'ASR', 'ROL'][f]
        return f'{n} R{dr},R{s1},R{s2}'
    if op in (9, 10):
        return f'{nom} R{dr},R{s1},#{sext(w, 5)}'
    if op == 11:
        n = ['LSL', 'LSR', 'ASR', 'ROL'][(w >> 3) & 3]
        return f'{n} R{dr},R{s1},#{(w & 7) + 1}'
    if op in (12, 13):
        return f'{nom} R{dr},#{sext(w, 8)}'
    if op == 14:
        return f'CMP R{s1},R{s2}'
    if op == 15:
        return f'CMPI R{dr},#{sext(w, 8)}'
    if op == 16:
        n = {v: k for k, v in UN_OPS.items()}.get(w & 31, '?')
        return f'{n} R{dr},R{s1}'
    if op in (17, 20):
        return f'{nom} R{dr},R{s1},#{sext(w, 5) * 2}'
    if op in (18, 19, 21, 22):
        return f'{nom} R{dr},R{s1},#{sext(w, 5)}'
    if op in (23, 24, 25):
        return f'{nom} R{dr},#{sext(w, 8)}(pc)'
    if op == 26:
        return f'BR{COND_NAME[(w >> 7) & 15]} #{sext(w, 7)}'
    if op == 27:
        return f'BRL #{sext(w, 11)}'
    if op == 28:
        return f'JSR #{sext(w, 11)}'
    if op == 29:
        return f'{"JSRR" if (w >> 7) & 1 else "JMP"} R{dr}'
    if op == 30:
        return f'TRAP x{w & 255:02X}'
    if op == 31:
        n = ['LDX', 'STX', 'LDBX', 'STBX'][f]
        return f'{n} R{dr},R{s1},R{s2}'
    return '?'
