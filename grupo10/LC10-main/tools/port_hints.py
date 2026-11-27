"""Decisiones tomadas a mano para el puerto LC-3 -> LC10 (las lee tools/lc3_to_lc10.py).

El traductor cambia cada instrucción por su equivalente, pero no puede saber qué registro es un puntero a
caracteres, a palabras o un simple número. Esa información, que sale de leer cada módulo, queda acá:

  char     "ALL" | "LDR" | "STR" | {líneas}: los LDR/STR indicados leen o escriben caracteres (1 byte):
           pasan a LDL/STL con el mismo offset. El resto de los LDR/STR son palabras: LDW/STW con offset x2.
  blkb     etiquetas de buffers de texto: `.BLKW n` pasa a `.BLKB n` (un byte por carácter).
  scale    registros que son puntero de pila de palabras: `ADD Rx, Rx, #k` pasa a #2k (bytes).
  bias     {registro: palabras}: el registro apunta esas palabras más adelante del inicio del bloque, para que
           los offsets (que en LC-3 llegan a 31) entren en el rango -16..15 de LDW/STW.
  sub      [(regex, [líneas LC10])]: reemplaza toda línea cuya operación (normalizada, en mayúsculas) coincida.
  replace  {línea LC-3: [líneas LC10]}: reemplaza esa línea; [] la elimina.
  extra    [líneas de datos que se agregan al final].

Las líneas de reemplazo se escriben en LC10; un ADD con inmediato grande se expande solo.
"""

DOS = lambda r, k: [f"ADD {r}, {r}, {k}"]
IDX = lambda d, b, i: [f"ADD {d}, {b}, {i}", f"ADD {d}, {d}, {i}"]       # d = b + 2*i (índice de palabras -> bytes)

HINTS = {
    # ------------------------------------------------------------------ grupo 27
    "g27_getline.asm": {"char": "ALL"},
    "g27_getcfiltered.asm": {"char": "ALL"},
    "g27_fromhex.asm": {"char": "ALL"},
    "g27_fromdec.asm": {"char": "ALL"},
    "g27_getval_buffer.asm": {"blkb": {"BUFFER"}},
    "g27_todec.asm": {
        "char": "STR",
        "sub": [
            (r"ADD R5 R5 #8", ["ADD R5, R5, #16"]),      # empezar en el 5to dígito: 8 palabras = 16 bytes
            (r"ADD R5 R5 #2", ["ADD R5, R5, #4"]),       # expresiones.incr(2): 2 palabras = 4 bytes
        ],
    },
    "g27_main_menu_PROGRESO.asm": {
        "char": {126, 128},                              # char + '\0' dentro de aux_0 (se lee con fromhex)
        "sub": [
            (r"ADD R0 R0 #1", ["ADD R0, R0, #2"]),       # cursor_de_op.incr(): palabra
            (r"ADD R1 R1 R0", ["ADD R1, R1, R0", "ADD R1, R1, R0"]),   # nodo.next.peek(offset)
            (r"ADD R5 R5 R0", ["ADD R5, R5, R0", "ADD R5, R5, R0"]),   # tabla_de_nodos.peek(indice)
            (r"ADD R0 R0 R1", ["ADD R0, R0, R1", "ADD R0, R0, R1"]),   # vector_de_textos.peek(n)
            (r"ADD R4 R4 #4", ["ADD R4, R4, #4", "ADD R4, R4, #4"]),   # cursor_de_op.incr(4): palabras
        ],
        # el ST de op_cursor queda a más de 128 palabras de los primeros usos: se llega con un puntero
        "replace": {
            105: ["ADD R1, R1, #2"],                     # cursor_de_op.incr(): palabra
            461: ["LD R1, main_menu_op_cursor_ptr", "STW R4, R1, #0"],
        },
        "extra": ["main_menu_op_cursor_ptr .FILL main_menu_op_cursor"],
    },
    # ------------------------------------------------------------------ pilas de palabras en R6
    "g5_Mul_Sucesiva_POW.asm": {"scale": {"R6"}},
    "g18_booth.asm": {"scale": {"R6"}},
    "g23_modulo_sqrt_nr.asm": {"scale": {"R6"}},
    "g22_Tabla_SIN_y_COS.asm": {
        "scale": {"R6"},
        "replace": {287: IDX("R5", "R5", "R4")},         # TABLA_SENO_203[R4]
    },
    # ------------------------------------------------------------------ tablas de palabras con índice
    "g11_CORDICLog.asm": {"replace": {54: IDX("R5", "R5", "R4"), 71: IDX("R5", "R5", "R4"), 86: IDX("R5", "R5", "R4")}},
    "g12_subrutina_grupo_12.asm": {"replace": {99: IDX("R4", "R4", "R3")}},
    "g14_log_borchardt_q8_7.asm": {"replace": {219: IDX("R1", "R1", "R2")}},
    "g19_cordic_multiplicacion.asm": {"replace": {257: ["ADD R2, R2, #2"], 349: ["ADD R6, R6, #2"]}},
    # ------------------------------------------------------------------ EXP: bloque de trabajo con offsets hasta 17
    "g6_EXP.asm": {
        "bias": {"R5": 8},
        "replace": {
            167: ["PTR_TRABAJO .FILL TRABAJO_MID"],     # R5 apunta a la palabra 8 del bloque
            368: ["TRABAJO .BLKW #8", "TRABAJO_MID .BLKW #10"],
            196: ["ADD R3, R3, #-4"],                   # dígito anterior de la fila: 2 palabras
            261: ["ADD R0, R0, #68"],                   # 17 constantes de dos palabras por fila: 34 palabras = 68 bytes
            262: [], 263: [],
            310: ["ADD R3, R5, #7", "ADD R3, R3, #7"],  # &TRABAJO[15] = R5 + 7 palabras
            346: ["ADD R3, R3, #-2"],                   # palabra anterior
        },
    },
}
