"""Pruebas de simulator/isa.py (ejecutar desde la carpeta raíz Lab3C).

Las tablas "esperadas" están escritas a mano desde la especificación y son
independientes del módulo: así la prueba no se compara contra sí misma.
"""

import ast
import dataclasses
import unittest
from pathlib import Path

from simulator import cpu, decoder, isa, memory, registers, traps
from simulator.isa import (
    INSTRUCTIONS,
    INSTRUCTIONS_BY_MNEMONIC,
    INSTRUCTIONS_BY_OPCODE,
    RESERVED_OPCODES,
    InstructionFormat,
    InstructionSpec,
    OperandKind,
)

F = InstructionFormat
K = OperandKind

EXPECTED_OPCODES = {
    "ADD": 0, "SUB": 1, "AND": 2, "OR": 3, "XOR": 4, "NOT": 5,
    "SHL": 6, "SHR": 7, "SAR": 8, "CMP": 9,
    "LDW": 10, "STW": 11, "LDBL": 12, "LDBH": 13, "STBL": 14, "STBH": 15,
    "BR": 16, "JSR": 17, "JMP": 18, "LEA": 19, "LDI": 20, "STI": 21,
    "TRAP": 22, "NOP": 23, "HALT": 24, "JSRR": 25,
}

EXPECTED_FORMATS = {
    **dict.fromkeys(("ADD", "SUB", "AND", "OR", "XOR", "NOT",
                     "SHL", "SHR", "SAR", "CMP"), F.A),
    **dict.fromkeys(("LDW", "STW", "LDBL", "LDBH", "STBL", "STBH",
                     "LDI", "STI"), F.B),
    "BR": F.C, "JSR": F.JSR, "JMP": F.JUMP_REG, "JSRR": F.JUMP_REG,
    "LEA": F.LEA, "TRAP": F.TRAP, "NOP": F.NO_OPERANDS, "HALT": F.NO_OPERANDS,
}

EXPECTED_OPERANDS = {
    **dict.fromkeys(("ADD", "SUB", "AND", "OR", "XOR"),
                    (K.REGISTER, K.REGISTER, K.REG_OR_IMM4)),
    "NOT": (K.REGISTER, K.REGISTER),
    **dict.fromkeys(("SHL", "SHR", "SAR"),
                    (K.REGISTER, K.REGISTER, K.SHIFT_AMOUNT)),
    "CMP": (K.REGISTER, K.REG_OR_IMM4),
    **dict.fromkeys(("LDW", "STW", "LDBL", "LDBH", "STBL", "STBH", "LDI", "STI"),
                    (K.REGISTER, K.REGISTER, K.OFFSET5)),
    "BR": (K.LABEL_WORDS,),
    "JSR": (K.LABEL_WORDS,),
    "JMP": (K.REGISTER,),
    "JSRR": (K.REGISTER,),
    "LEA": (K.REGISTER, K.LABEL_BYTES),
    "TRAP": (K.VECTOR,),
    "NOP": (),
    "HALT": (),
}

def minimal_valid_word(spec):
    """Palabra válida más simple de una instrucción: opcode y todo lo demás en 0.

    Los shifts son la excepción: exigen M = 1 (modo inmediato).
    """
    word = spec.opcode << 11
    if K.SHIFT_AMOUNT in spec.operands:
        word |= 1 << 4
    return word


def project_imports(module):
    """Módulos 'simulator.*' que importa el archivo fuente de `module`."""
    tree = ast.parse(Path(module.__file__).read_text(encoding="utf-8"))
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            if node.module.startswith("simulator"):
                found.add(node.module)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("simulator"):
                    found.add(alias.name)
    return found


# ----------------------------------------------------------------------
# 8. Constantes de arquitectura
# ----------------------------------------------------------------------
class TestArchitectureConstants(unittest.TestCase):

    def test_widths_and_masks(self):
        self.assertEqual(isa.WORD_BITS, 16)
        self.assertEqual(isa.WORD_MASK, 0xFFFF)
        self.assertEqual(isa.BYTE_BITS, 8)
        self.assertEqual(isa.BYTE_MASK, 0xFF)
        self.assertEqual(isa.OPCODE_BITS, 5)

    def test_registers(self):
        self.assertEqual(isa.REGISTER_COUNT, 8)
        self.assertEqual(isa.REGISTER_MASK, 0b111)
        self.assertEqual(isa.SP_REGISTER, 6)
        self.assertEqual(isa.LINK_REGISTER, 7)
        for register in (isa.SP_REGISTER, isa.LINK_REGISTER):
            self.assertTrue(0 <= register < isa.REGISTER_COUNT)

    def test_memory_and_pc(self):
        self.assertEqual(isa.MEMORY_SIZE, 65536)
        self.assertEqual(isa.PC_INCREMENT, 2)

    def test_nzp_masks_follow_agreed_bit_order(self):
        self.assertEqual(isa.NZP_N, 0b100)
        self.assertEqual(isa.NZP_Z, 0b010)
        self.assertEqual(isa.NZP_P, 0b001)
        self.assertEqual(isa.NZP_N | isa.NZP_Z | isa.NZP_P, 0b111)

    def test_addressing_modes(self):
        self.assertEqual(isa.MODE_REGISTER, 0)
        self.assertEqual(isa.MODE_IMMEDIATE, 1)

    def test_trap_vectors(self):
        self.assertEqual(isa.TRAP_GETC, 0x20)
        self.assertEqual(isa.TRAP_OUT, 0x21)
        self.assertEqual(isa.TRAP_PUTS, 0x22)
        self.assertEqual(isa.TRAP_HALT, 0x25)


# ----------------------------------------------------------------------
# 1-7. Tabla de instrucciones
# ----------------------------------------------------------------------
class TestInstructionTable(unittest.TestCase):

    def test_there_are_26_instructions(self):
        self.assertEqual(len(INSTRUCTIONS), 26)
        self.assertEqual(len(INSTRUCTIONS_BY_OPCODE), 26)
        self.assertEqual(len(INSTRUCTIONS_BY_MNEMONIC), 26)

    def test_mnemonic_opcode_pairs_match_specification(self):
        self.assertEqual(
            {spec.mnemonic: spec.opcode for spec in INSTRUCTIONS},
            EXPECTED_OPCODES,
        )

    def test_opcodes_are_unique_and_consecutive(self):
        opcodes = [spec.opcode for spec in INSTRUCTIONS]
        self.assertEqual(len(set(opcodes)), 26)
        self.assertEqual(opcodes, list(range(26)))

    def test_mnemonics_are_unique_uppercase_words(self):
        mnemonics = [spec.mnemonic for spec in INSTRUCTIONS]
        self.assertEqual(len(set(mnemonics)), 26)
        for mnemonic in mnemonics:
            with self.subTest(mnemonic=mnemonic):
                self.assertTrue(mnemonic.isalpha() and mnemonic.isupper())

    def test_every_instruction_has_a_valid_format_matching_the_spec(self):
        for spec in INSTRUCTIONS:
            with self.subTest(mnemonic=spec.mnemonic):
                self.assertIsInstance(spec.fmt, InstructionFormat)
                self.assertEqual(spec.fmt, EXPECTED_FORMATS[spec.mnemonic])

    def test_all_eight_formats_are_used(self):
        self.assertEqual(len(InstructionFormat), 8)
        self.assertEqual({spec.fmt for spec in INSTRUCTIONS}, set(InstructionFormat))

    def test_lookup_by_opcode(self):
        for mnemonic, opcode in EXPECTED_OPCODES.items():
            with self.subTest(opcode=opcode):
                self.assertEqual(INSTRUCTIONS_BY_OPCODE[opcode].mnemonic, mnemonic)

    def test_lookup_by_mnemonic(self):
        for mnemonic, opcode in EXPECTED_OPCODES.items():
            with self.subTest(mnemonic=mnemonic):
                self.assertEqual(INSTRUCTIONS_BY_MNEMONIC[mnemonic].opcode, opcode)

    def test_both_indexes_return_the_same_object(self):
        for spec in INSTRUCTIONS:
            self.assertIs(INSTRUCTIONS_BY_OPCODE[spec.opcode], spec)
            self.assertIs(INSTRUCTIONS_BY_MNEMONIC[spec.mnemonic], spec)

    def test_unknown_lookups_fail(self):
        for opcode in (26, 31, 32, -1):
            self.assertNotIn(opcode, INSTRUCTIONS_BY_OPCODE)
        for mnemonic in ("FOO", "add", "", "BRnzp"):      # distingue mayúsculas
            self.assertNotIn(mnemonic, INSTRUCTIONS_BY_MNEMONIC)
        with self.assertRaises(KeyError):
            INSTRUCTIONS_BY_OPCODE[26]

    def test_reserved_opcodes_are_not_valid_instructions(self):
        self.assertEqual(RESERVED_OPCODES, frozenset(range(26, 32)))
        for opcode in range(26, 32):
            with self.subTest(opcode=opcode):
                self.assertNotIn(opcode, INSTRUCTIONS_BY_OPCODE)
        self.assertFalse(RESERVED_OPCODES & set(INSTRUCTIONS_BY_OPCODE))
        self.assertEqual(len(RESERVED_OPCODES) + len(INSTRUCTIONS), 32)

    def test_indexes_are_read_only(self):
        with self.assertRaises(TypeError):
            INSTRUCTIONS_BY_OPCODE[26] = INSTRUCTIONS[0]
        with self.assertRaises(TypeError):
            del INSTRUCTIONS_BY_MNEMONIC["ADD"]

    def test_specs_are_immutable(self):
        with self.assertRaises(dataclasses.FrozenInstanceError):
            INSTRUCTIONS[0].opcode = 7
        self.assertIsInstance(INSTRUCTIONS, tuple)

    def test_opcode_must_fit_in_five_bits(self):
        InstructionSpec("OK", 31, F.A, ())                 # 31 cabe
        for bad in (32, -1, 100):
            with self.subTest(opcode=bad):
                with self.assertRaises(ValueError):
                    InstructionSpec("BAD", bad, F.A, ())

    def test_duplicates_are_rejected_when_building_indexes(self):
        first = InstructionSpec("AAA", 1, F.A, ())
        same_opcode = InstructionSpec("BBB", 1, F.A, ())
        same_mnemonic = InstructionSpec("AAA", 2, F.A, ())
        with self.assertRaises(ValueError):
            isa._index((first, same_opcode), "opcode")
        with self.assertRaises(ValueError):
            isa._index((first, same_mnemonic), "mnemonic")
        self.assertEqual(len(isa._index((first,), "opcode")), 1)


# ----------------------------------------------------------------------
# Operandos esperados (información para el ensamblador)
# ----------------------------------------------------------------------
class TestOperands(unittest.TestCase):

    def test_operands_match_specification(self):
        for spec in INSTRUCTIONS:
            with self.subTest(mnemonic=spec.mnemonic):
                self.assertIsInstance(spec.operands, tuple)
                self.assertEqual(spec.operands, EXPECTED_OPERANDS[spec.mnemonic])

    def test_shifts_take_an_unsigned_amount_never_a_register(self):
        for mnemonic in ("SHL", "SHR", "SAR"):
            with self.subTest(mnemonic=mnemonic):
                operands = INSTRUCTIONS_BY_MNEMONIC[mnemonic].operands
                self.assertEqual(operands[-1], K.SHIFT_AMOUNT)
                self.assertNotIn(K.REG_OR_IMM4, operands)

    def test_offset_units_are_words_for_br_jsr_and_bytes_for_lea(self):
        self.assertEqual(INSTRUCTIONS_BY_MNEMONIC["BR"].operands, (K.LABEL_WORDS,))
        self.assertEqual(INSTRUCTIONS_BY_MNEMONIC["JSR"].operands, (K.LABEL_WORDS,))
        self.assertEqual(INSTRUCTIONS_BY_MNEMONIC["LEA"].operands[-1], K.LABEL_BYTES)

    def test_operands_are_consistent_with_the_format(self):
        by_format = {
            F.B: (K.REGISTER, K.REGISTER, K.OFFSET5),
            F.C: (K.LABEL_WORDS,),
            F.JSR: (K.LABEL_WORDS,),
            F.JUMP_REG: (K.REGISTER,),
            F.LEA: (K.REGISTER, K.LABEL_BYTES),
            F.TRAP: (K.VECTOR,),
            F.NO_OPERANDS: (),
        }
        for spec in INSTRUCTIONS:
            if spec.fmt in by_format:
                with self.subTest(mnemonic=spec.mnemonic):
                    self.assertEqual(spec.operands, by_format[spec.fmt])
        for spec in INSTRUCTIONS:                          # formato A: 2 o 3 operandos
            if spec.fmt == F.A:
                self.assertIn(len(spec.operands), (2, 3))


# ----------------------------------------------------------------------
# 9. Las definiciones compartidas coinciden con las de los demás módulos
# ----------------------------------------------------------------------
class TestSharedWithDecoder(unittest.TestCase):

    def test_decoder_reexports_the_shared_names(self):
        self.assertIs(decoder.Format, isa.InstructionFormat)
        for name in ("MODE_REGISTER", "MODE_IMMEDIATE", "NZP_N", "NZP_Z",
                     "NZP_P", "WORD_MASK"):
            with self.subTest(name=name):
                self.assertEqual(getattr(decoder, name), getattr(isa, name))

    def test_decoder_opcode_table_is_derived_from_isa(self):
        expected = {s.opcode: (s.mnemonic, s.fmt) for s in INSTRUCTIONS}
        self.assertEqual(decoder.OPCODE_TABLE, expected)
        self.assertEqual(len(decoder.OPCODE_TABLE), 26)

    def test_decoder_agrees_with_isa_for_every_instruction(self):
        for spec in INSTRUCTIONS:
            with self.subTest(mnemonic=spec.mnemonic):
                decoded = decoder.decode(minimal_valid_word(spec))
                self.assertEqual(decoded.mnemonic, spec.mnemonic)
                self.assertEqual(decoded.opcode, spec.opcode)
                self.assertEqual(decoded.fmt, spec.fmt)

    def test_decoder_rejects_exactly_the_reserved_opcodes(self):
        for opcode in range(1 << isa.OPCODE_BITS):
            with self.subTest(opcode=opcode):
                if opcode in RESERVED_OPCODES:
                    with self.assertRaises(decoder.ReservedOpcodeError):
                        decoder.decode(opcode << 11)
                else:
                    spec = INSTRUCTIONS_BY_OPCODE[opcode]
                    decoder.decode(minimal_valid_word(spec))   # no debe lanzar


class TestSharedWithOtherModules(unittest.TestCase):

    def test_cpu_uses_the_shared_constants(self):
        self.assertEqual(cpu.WORD_MASK, isa.WORD_MASK)
        self.assertEqual(cpu.BYTE_MASK, isa.BYTE_MASK)
        self.assertEqual(cpu.LINK_REGISTER, isa.LINK_REGISTER)

    def test_traps_use_the_shared_vectors(self):
        for name in ("TRAP_GETC", "TRAP_OUT", "TRAP_PUTS", "TRAP_HALT"):
            with self.subTest(name=name):
                self.assertEqual(getattr(traps, name), getattr(isa, name))

    def test_every_isa_trap_vector_has_a_service(self):
        services = traps.TrapServices(io=None)._services
        self.assertEqual(
            set(services),
            {isa.TRAP_GETC, isa.TRAP_OUT, isa.TRAP_PUTS, isa.TRAP_HALT},
        )

    def test_memory_agrees_with_isa(self):
        # memory.py y registers.py ya estaban verificados y no se modificaron:
        # estas pruebas impiden que sus constantes se desalineen de isa.py.
        self.assertEqual(memory.MEMORY_SIZE, isa.MEMORY_SIZE)
        self.assertEqual(memory.Memory.SIZE, isa.MEMORY_SIZE)
        self.assertEqual(memory.BYTE_MASK, isa.BYTE_MASK)
        self.assertEqual(memory.WORD_MASK, isa.WORD_MASK)

    def test_registers_agree_with_isa(self):
        self.assertEqual(registers.NUM_REGISTERS, isa.REGISTER_COUNT)
        self.assertEqual(registers.Registers.COUNT, isa.REGISTER_COUNT)
        self.assertEqual(registers.WORD_MASK, isa.WORD_MASK)
        self.assertEqual(registers.SIGN_BIT, 1 << (isa.WORD_BITS - 1))


# ----------------------------------------------------------------------
# Sin dependencias circulares
# ----------------------------------------------------------------------
class TestDependencyGraph(unittest.TestCase):

    def test_dependency_graph_is_layered(self):
        expected = {
            isa: set(),
            memory: set(),
            registers: set(),
            decoder: {"simulator.isa"},
            traps: {"simulator.isa"},
            cpu: {"simulator.isa", "simulator.decoder", "simulator.memory",
                  "simulator.registers", "simulator.traps"},
        }
        for module, imports in expected.items():
            with self.subTest(module=module.__name__):
                self.assertEqual(project_imports(module), imports)


if __name__ == "__main__":
    unittest.main()
