"""Pruebas de simulator/registers.py (ejecutar desde la carpeta raíz Lab3C)."""

import unittest

from simulator.registers import Registers, RegisterAccessError, to_signed16


def flags_as_text(regs):
    """Devuelve 'N', 'Z' o 'P' si hay exactamente una activa; si no, 'INVALIDO'."""
    n, z, p = regs.condition_codes
    if (n + z + p) != 1:
        return "INVALIDO"
    return "N" if n else ("Z" if z else "P")


class TestInitialization(unittest.TestCase):

    def setUp(self):
        self.regs = Registers()

    def test_eight_registers(self):
        self.assertEqual(Registers.COUNT, 8)
        self.assertEqual(len(self.regs.values()), 8)

    def test_all_registers_start_at_zero(self):
        for i in range(8):
            with self.subTest(register=i):
                self.assertEqual(self.regs.read(i), 0)

    def test_pc_starts_at_zero(self):
        self.assertEqual(self.regs.pc, 0)

    def test_ir_starts_at_zero(self):
        self.assertEqual(self.regs.ir, 0)

    def test_flags_start_with_z_active(self):
        self.assertEqual(self.regs.condition_codes, (False, True, False))
        self.assertFalse(self.regs.n)
        self.assertTrue(self.regs.z)
        self.assertFalse(self.regs.p)


class TestGeneralRegisters(unittest.TestCase):

    def setUp(self):
        self.regs = Registers()

    def test_write_read_each_register(self):
        for i in range(8):
            with self.subTest(register=i):
                self.regs.write(i, 0x1000 + i)
                self.assertEqual(self.regs.read(i), 0x1000 + i)

    def test_registers_are_independent(self):
        for i in range(8):
            self.regs.write(i, (i + 1) * 0x0111)
        for i in range(8):
            with self.subTest(register=i):
                self.assertEqual(self.regs.read(i), (i + 1) * 0x0111)
        self.assertEqual(self.regs.values(),
                         tuple((i + 1) * 0x0111 for i in range(8)))

    def test_value_above_16_bits_is_masked(self):
        self.regs.write(0, 0x12345)
        self.assertEqual(self.regs.read(0), 0x2345)
        self.regs.write(1, 0x10000)
        self.assertEqual(self.regs.read(1), 0x0000)

    def test_negative_value_is_twos_complement(self):
        self.regs.write(2, -1)
        self.assertEqual(self.regs.read(2), 0xFFFF)
        self.regs.write(3, -2)
        self.assertEqual(self.regs.read(3), 0xFFFE)
        self.regs.write(4, -32768)
        self.assertEqual(self.regs.read(4), 0x8000)

    def test_max_and_min_values(self):
        self.regs.write(5, 0xFFFF)
        self.assertEqual(self.regs.read(5), 0xFFFF)
        self.regs.write(5, 0)
        self.assertEqual(self.regs.read(5), 0)

    def test_write_does_not_change_flags(self):
        self.regs.write(0, 0x8000)   # negativo, pero write NO actualiza banderas
        self.assertEqual(self.regs.condition_codes, (False, True, False))


class TestRegisterValidation(unittest.TestCase):

    def setUp(self):
        self.regs = Registers()

    def test_negative_index_raises(self):
        with self.assertRaises(RegisterAccessError):
            self.regs.read(-1)
        with self.assertRaises(RegisterAccessError):
            self.regs.write(-1, 5)

    def test_index_above_7_raises(self):
        for idx in (8, 9, 100):
            with self.subTest(index=idx):
                with self.assertRaises(RegisterAccessError):
                    self.regs.read(idx)
                with self.assertRaises(RegisterAccessError):
                    self.regs.write(idx, 5)

    def test_non_integer_index_raises(self):
        for bad in ("0", 1.0, 1.5, None, [1]):
            with self.subTest(index=bad):
                with self.assertRaises(RegisterAccessError):
                    self.regs.read(bad)
                with self.assertRaises(RegisterAccessError):
                    self.regs.write(bad, 5)

    def test_bool_index_raises(self):
        for bad in (True, False):
            with self.subTest(index=bad):
                with self.assertRaises(RegisterAccessError):
                    self.regs.read(bad)
                with self.assertRaises(RegisterAccessError):
                    self.regs.write(bad, 5)

    def test_non_integer_value_raises(self):
        for bad in ("5", 1.5, None, True):
            with self.subTest(value=bad):
                with self.assertRaises(RegisterAccessError):
                    self.regs.write(0, bad)

    def test_failed_write_leaves_registers_unchanged(self):
        with self.assertRaises(RegisterAccessError):
            self.regs.write(8, 0x1234)
        with self.assertRaises(RegisterAccessError):
            self.regs.write(0, "x")
        self.assertEqual(self.regs.values(), (0,) * 8)


class TestPcIr(unittest.TestCase):

    def setUp(self):
        self.regs = Registers()

    def test_pc_write_read(self):
        self.regs.pc = 0x3000
        self.assertEqual(self.regs.pc, 0x3000)

    def test_ir_write_read(self):
        self.regs.ir = 0x1021
        self.assertEqual(self.regs.ir, 0x1021)

    def test_pc_is_masked_to_16_bits(self):
        self.regs.pc = 0x12345
        self.assertEqual(self.regs.pc, 0x2345)
        self.regs.pc = -2
        self.assertEqual(self.regs.pc, 0xFFFE)

    def test_ir_is_masked_to_16_bits(self):
        self.regs.ir = 0x1FFFF
        self.assertEqual(self.regs.ir, 0xFFFF)
        self.regs.ir = -1
        self.assertEqual(self.regs.ir, 0xFFFF)

    def test_pc_invalid_type_raises(self):
        for bad in ("0x3000", 1.5, None, True):
            with self.subTest(value=bad):
                with self.assertRaises(RegisterAccessError):
                    self.regs.pc = bad
        self.assertEqual(self.regs.pc, 0)   # no cambió

    def test_ir_invalid_type_raises(self):
        for bad in ("0x1021", 1.5, None, True):
            with self.subTest(value=bad):
                with self.assertRaises(RegisterAccessError):
                    self.regs.ir = bad
        self.assertEqual(self.regs.ir, 0)   # no cambió


class TestNzpFlags(unittest.TestCase):

    def setUp(self):
        self.regs = Registers()

    def test_update_nzp_cases(self):
        cases = [
            (0x0000, "Z"),
            (0x0001, "P"),
            (0x7FFF, "P"),
            (0xFFFF, "N"),
            (0x8000, "N"),
            (0xFFFE, "N"),
        ]
        for value, expected in cases:
            with self.subTest(value=hex(value)):
                self.regs.update_nzp(value)
                self.assertEqual(flags_as_text(self.regs), expected)

    def test_exactly_one_flag_active_after_each_update(self):
        for value in (0x0000, 0x0001, 0x4000, 0x7FFF, 0x8000, 0x8001, 0xFFFF):
            with self.subTest(value=hex(value)):
                self.regs.update_nzp(value)
                self.assertEqual(sum(self.regs.condition_codes), 1)

    def test_update_nzp_masks_value(self):
        self.regs.update_nzp(0x10000)    # 16 bits inferiores = 0 -> Z
        self.assertEqual(flags_as_text(self.regs), "Z")
        self.regs.update_nzp(0x1FFFF)    # 0xFFFF -> N
        self.assertEqual(flags_as_text(self.regs), "N")
        self.regs.update_nzp(-1)         # 0xFFFF -> N
        self.assertEqual(flags_as_text(self.regs), "N")

    def test_update_nzp_invalid_type_raises(self):
        for bad in ("1", 1.5, None, True):
            with self.subTest(value=bad):
                with self.assertRaises(RegisterAccessError):
                    self.regs.update_nzp(bad)

    def test_condition_codes_is_tuple_n_z_p(self):
        self.regs.update_nzp(0xFFFF)
        self.assertEqual(self.regs.condition_codes, (True, False, False))
        self.regs.update_nzp(0)
        self.assertEqual(self.regs.condition_codes, (False, True, False))
        self.regs.update_nzp(5)
        self.assertEqual(self.regs.condition_codes, (False, False, True))

    def test_flags_change_between_updates(self):
        self.regs.update_nzp(1)
        self.assertEqual(flags_as_text(self.regs), "P")
        self.regs.update_nzp(0)
        self.assertEqual(flags_as_text(self.regs), "Z")
        self.regs.update_nzp(0x8000)
        self.assertEqual(flags_as_text(self.regs), "N")


class TestCompare(unittest.TestCase):

    def setUp(self):
        self.regs = Registers()

    def test_to_signed16(self):
        self.assertEqual(to_signed16(0x0000), 0)
        self.assertEqual(to_signed16(0x7FFF), 32767)
        self.assertEqual(to_signed16(0x8000), -32768)
        self.assertEqual(to_signed16(0xFFFF), -1)

    def test_compare_cases(self):
        cases = [
            (0x0001, 0x0002, "N"),
            (0x0002, 0x0002, "Z"),
            (0x0003, 0x0002, "P"),
            (0xFFFF, 0x0001, "N"),   # -1 < 1
            (0x8000, 0x0001, "N"),   # -32768 < 1
            (0x7FFF, 0xFFFF, "P"),   # 32767 > -1
        ]
        for a, b, expected in cases:
            with self.subTest(a=hex(a), b=hex(b)):
                self.regs.update_compare(a, b)
                self.assertEqual(flags_as_text(self.regs), expected)

    def test_compare_avoids_subtraction_overflow(self):
        # 32767 - (-32768) = 65535 -> 0xFFFF (parece negativo) si se restara
        # en 16 bits. La comparación directa debe dar P.
        self.regs.update_compare(0x7FFF, 0x8000)
        self.assertEqual(flags_as_text(self.regs), "P")
        # Caso inverso: -32768 < 32767 -> N.
        self.regs.update_compare(0x8000, 0x7FFF)
        self.assertEqual(flags_as_text(self.regs), "N")

    def test_compare_masks_operands(self):
        self.regs.update_compare(0x1FFFF, 0xFFFF)   # ambos = -1 -> Z
        self.assertEqual(flags_as_text(self.regs), "Z")

    def test_exactly_one_flag_active_after_compare(self):
        for a, b in ((1, 2), (2, 2), (3, 2), (0x8000, 0x7FFF)):
            with self.subTest(a=a, b=b):
                self.regs.update_compare(a, b)
                self.assertEqual(sum(self.regs.condition_codes), 1)

    def test_compare_does_not_modify_registers(self):
        for i in range(8):
            self.regs.write(i, 0x1111 * (i + 1))
        self.regs.pc = 0x3000
        self.regs.ir = 0xABCD
        before = self.regs.values()
        self.regs.update_compare(0x8000, 0x0001)
        self.assertEqual(self.regs.values(), before)
        self.assertEqual(self.regs.pc, 0x3000)
        self.assertEqual(self.regs.ir, 0xABCD)

    def test_compare_invalid_type_raises(self):
        for bad in ("1", 1.5, None, True):
            with self.subTest(value=bad):
                with self.assertRaises(RegisterAccessError):
                    self.regs.update_compare(bad, 1)
                with self.assertRaises(RegisterAccessError):
                    self.regs.update_compare(1, bad)


if __name__ == "__main__":
    unittest.main()
