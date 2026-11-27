"""Pruebas de simulator/memory.py (ejecutar desde la carpeta raíz Lab3C)."""

import unittest

from simulator.memory import Memory, MemoryAccessError


class TestMemory(unittest.TestCase):

    def setUp(self):
        self.mem = Memory()

    # --- Tamaño e inicialización ---
    def test_size_is_65536(self):
        self.assertEqual(self.mem.size, 65536)
        self.assertEqual(len(self.mem._data), 65536)

    def test_initialized_with_zeros(self):
        self.assertEqual(self.mem.read_byte(0x0000), 0)
        self.assertEqual(self.mem.read_byte(0x8000), 0)
        self.assertEqual(self.mem.read_byte(0xFFFF), 0)
        self.assertEqual(self.mem.read_word(0x1234), 0)

    # --- Bytes ---
    def test_byte_write_read(self):
        self.mem.write_byte(0x2000, 0xAB)
        self.assertEqual(self.mem.read_byte(0x2000), 0xAB)

    def test_byte_value_is_masked_to_8_bits(self):
        self.mem.write_byte(0x10, 0x1FF)
        self.assertEqual(self.mem.read_byte(0x10), 0xFF)
        self.mem.write_byte(0x11, -1)  # complemento a dos
        self.assertEqual(self.mem.read_byte(0x11), 0xFF)

    # --- Palabras ---
    def test_word_write_read(self):
        self.mem.write_word(0x4000, 0xBEEF)
        self.assertEqual(self.mem.read_word(0x4000), 0xBEEF)

    def test_word_value_is_masked_to_16_bits(self):
        self.mem.write_word(0x20, 0x1ABCD)
        self.assertEqual(self.mem.read_word(0x20), 0xABCD)
        self.mem.write_word(0x30, -1)
        self.assertEqual(self.mem.read_word(0x30), 0xFFFF)

    def test_little_endian_mandatory_example(self):
        self.mem.write_word(0x3000, 0x1234)
        self.assertEqual(self.mem.read_byte(0x3000), 0x34)
        self.assertEqual(self.mem.read_byte(0x3001), 0x12)
        self.assertEqual(self.mem.read_word(0x3000), 0x1234)

    def test_word_access_from_odd_address(self):
        self.mem.write_word(0x3001, 0xCAFE)
        self.assertEqual(self.mem.read_byte(0x3001), 0xFE)
        self.assertEqual(self.mem.read_byte(0x3002), 0xCA)
        self.assertEqual(self.mem.read_word(0x3001), 0xCAFE)

    def test_word_at_last_valid_position(self):
        self.mem.write_word(0xFFFE, 0x1234)
        self.assertEqual(self.mem.read_word(0xFFFE), 0x1234)

    # --- Excepciones ---
    def test_read_out_of_range(self):
        for addr in (-1, 0x10000, 0x20000):
            with self.subTest(addr=addr):
                with self.assertRaises(MemoryAccessError):
                    self.mem.read_byte(addr)

    def test_write_out_of_range(self):
        for addr in (-1, 0x10000):
            with self.subTest(addr=addr):
                with self.assertRaises(MemoryAccessError):
                    self.mem.write_byte(addr, 1)
                with self.assertRaises(MemoryAccessError):
                    self.mem.write_word(addr, 1)

    def test_read_word_at_0xFFFF_raises(self):
        with self.assertRaises(MemoryAccessError):
            self.mem.read_word(0xFFFF)

    def test_write_word_at_0xFFFF_raises(self):
        with self.assertRaises(MemoryAccessError):
            self.mem.write_word(0xFFFF, 0x1234)

    def test_failed_word_write_leaves_memory_untouched(self):
        with self.assertRaises(MemoryAccessError):
            self.mem.write_word(0xFFFF, 0x1234)
        self.assertEqual(self.mem.read_byte(0xFFFF), 0)  # sin escritura parcial
        self.assertEqual(self.mem.used_bytes, 0)

    def test_non_integer_address_raises(self):
        for bad in ("10", 1.5, None, True):
            with self.subTest(bad=bad):
                with self.assertRaises(MemoryAccessError):
                    self.mem.read_byte(bad)

    # --- Bytes utilizados ---
    def test_used_bytes_initially_zero(self):
        self.assertEqual(self.mem.used_bytes, 0)

    def test_used_bytes_counts_distinct_addresses(self):
        self.mem.write_byte(0x100, 1)
        self.mem.write_byte(0x100, 2)   # misma dirección: no suma
        self.mem.write_byte(0x101, 3)
        self.assertEqual(self.mem.used_bytes, 2)

    def test_write_word_uses_two_bytes_and_overlap_counts_once(self):
        self.mem.write_word(0x200, 0x1111)
        self.assertEqual(self.mem.used_bytes, 2)
        self.mem.write_word(0x201, 0x2222)  # solapa 0x201
        self.assertEqual(self.mem.used_bytes, 3)

    def test_reads_do_not_count_as_used(self):
        self.mem.read_byte(0x500)
        self.mem.read_word(0x600)
        self.assertEqual(self.mem.used_bytes, 0)


if __name__ == "__main__":
    unittest.main()
