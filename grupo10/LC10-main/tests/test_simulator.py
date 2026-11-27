import random
import unittest

from lc10 import isa
from lc10.assembler import assemble
from lc10.simulator import Machine, run_image

M = 0xFFFF
s16 = isa.to_s16


def exec1(name, regs=None, flags=None, pc=0x3000, **fields):
    """Ejecuta una sola instrucción sobre una máquina con `regs` y `flags` dados."""
    m = Machine()
    m.pc = pc
    w = isa.encode(name, **fields)
    m.mem[pc], m.mem[pc + 1] = w & 0xFF, w >> 8
    if regs:
        m.regs[:] = regs
    for k, v in (flags or {}).items():
        setattr(m, k, v)
    m.step()
    return m


def run_asm(src, regs=None, inp="", max_instr=100000, stop_at=None):
    """Ensambla, corre hasta el HALT y devuelve (máquina, resultado, ensamblado).

    HALT es un TRAP: R7 pasa a ser la dirección de retorno y la rutina del SO deja las banderas en Z. Para mirar
    R7 o las banderas tal como las dejó el programa, `stop_at="ETIQUETA"` detiene la corrida antes de esa instrucción."""
    res = assemble([("prog.asm", src)])
    m = Machine()
    m.load(res.image)
    m.set_input(inp)
    if regs:
        m.regs[:] = regs
    r = m.run(max_instr, stop_at=res.symbols["PROG-" + stop_at.upper()] if stop_at else None)
    return m, r, res


class TestAlu(unittest.TestCase):
    def setUp(self):
        self.rnd = random.Random(3)

    def rand16(self):
        return self.rnd.choice([0, 1, 0x7FFF, 0x8000, 0xFFFF, self.rnd.getrandbits(16), self.rnd.getrandbits(16)])

    def test_add_adc_flags_against_signed_reference(self):
        for _ in range(3000):
            a, b, cin = self.rand16(), self.rand16(), self.rnd.randrange(2)
            for name in ("ADD", "ADC"):
                c = cin if name == "ADC" else 0
                m = exec1(name, regs=[0, a, b, 0, 0, 0, 0, 0], flags={"c": cin}, dr=0, sr1=1, mode="r", src=2)
                total = a + b + c
                self.assertEqual(m.regs[0], total & M)
                self.assertEqual(m.c, total >> 16)
                self.assertEqual(m.v, int(not -32768 <= s16(a) + s16(b) + c <= 32767))
                self.assertEqual((m.n, m.z, m.p), (int(s16(total) < 0), int(total & M == 0), int(s16(total) > 0)))

    def test_sub_sbc_cmp_flags_against_signed_reference(self):
        for _ in range(3000):
            a, b, cin = self.rand16(), self.rand16(), self.rnd.randrange(2)
            for name in ("SUB", "SBC", "CMP"):
                borrow_in = 0 if name != "SBC" else 1 - cin
                fields = {"sr1": 1, "mode": "r", "src": 2} if name == "CMP" else {"dr": 0, "sr1": 1, "mode": "r", "src": 2}
                m = exec1(name, regs=[0x1234, a, b, 0, 0, 0, 0, 0], flags={"c": cin}, **fields)
                diff = a - b - borrow_in
                self.assertEqual(m.regs[0], 0x1234 if name == "CMP" else diff & M)
                self.assertEqual(m.c, int(diff >= 0), "C = 1 cuando NO hay préstamo")
                self.assertEqual(m.v, int(not -32768 <= s16(a) - s16(b) - borrow_in <= 32767))

    def test_immediate_forms_sign_extend(self):
        m = exec1("ADD", regs=[0, 10, 0, 0, 0, 0, 0, 0], dr=0, sr1=1, mode="i", src=-3)
        self.assertEqual(m.regs[0], 7)
        m = exec1("AND", regs=[0, 0xFFFF, 0, 0, 0, 0, 0, 0], dr=0, sr1=1, mode="i", src=-8)
        self.assertEqual(m.regs[0], 0xFFF8)

    def test_logic_ops_keep_carry_and_overflow(self):
        for name, f in (("AND", lambda a, b: a & b), ("OR", lambda a, b: a | b), ("XOR", lambda a, b: a ^ b)):
            m = exec1(name, regs=[0, 0xF0F0, 0x3C3C, 0, 0, 0, 0, 0], flags={"c": 1, "v": 1}, dr=0, sr1=1, mode="r", src=2)
            self.assertEqual((m.regs[0], m.c, m.v), (f(0xF0F0, 0x3C3C), 1, 1))
        m = exec1("NOT", regs=[0, 0x00FF, 0, 0, 0, 0, 0, 0], flags={"c": 1}, dr=0, sr=1)
        self.assertEqual((m.regs[0], m.c, m.n), (0xFF00, 1, 1))

    def test_neg(self):
        for a in (0, 1, 5, 0x7FFF, 0x8000, 0xFFFF):
            m = exec1("NEG", regs=[0, a, 0, 0, 0, 0, 0, 0], dr=0, sr=1)
            self.assertEqual(m.regs[0], -a & M)
            self.assertEqual(m.v, int(a == 0x8000))
            self.assertEqual(m.c, int(a == 0))

    def test_shifts_against_reference(self):
        for _ in range(2000):
            a = self.rand16()
            for amt in range(0, 32):
                for name in ("SHL", "SHR", "SAR"):
                    if amt <= 15:
                        m = exec1(name, regs=[0, a, 0, 0, 0, 0, 0, 0], flags={"c": 1, "v": 1}, dr=0, sr1=1, mode="i", src=amt)
                        self._check_shift(name, a, amt, m, 1)
                    m = exec1(name, regs=[0, a, amt, 0, 0, 0, 0, 0], flags={"c": 1, "v": 1}, dr=0, sr1=1, mode="r", src=2)
                    self._check_shift(name, a, amt, m, 1)
            if _ > 60:
                break

    def _check_shift(self, name, a, amt, m, c_before):
        if name == "SHL":
            exp = (a << amt) & M
            carry = c_before if amt == 0 else ((a << amt) >> 16) & 1 if amt <= 16 else 0
        elif name == "SHR":
            exp = a >> amt if amt < 32 else 0
            carry = c_before if amt == 0 else (a >> (amt - 1)) & 1 if amt <= 16 else 0
        else:
            exp = (s16(a) >> min(amt, 31)) & M
            carry = c_before if amt == 0 else (a >> (amt - 1)) & 1 if amt <= 16 else a >> 15
        self.assertEqual((m.regs[0], m.c, m.v), (exp, carry, 1), f"{name} {a:#06x} por {amt}")

    def test_rotate_through_carry_builds_32_bit_shifts(self):
        for _ in range(500):
            hi, lo = self.rnd.getrandbits(16), self.rnd.getrandbits(16)
            # (hi:lo) << 1  =  SHL lo; RCL hi
            m = exec1("SHL", regs=[lo, hi, 0, 0, 0, 0, 0, 0], dr=0, sr1=0, mode="i", src=1)
            m.pc = 0x3000
            w = isa.encode("ROTC", dr=1, sr=1, right=0)
            m.mem[0x3000], m.mem[0x3001] = w & 0xFF, w >> 8
            m.step()
            full = (hi << 16 | lo) << 1
            self.assertEqual((m.regs[1] << 16 | m.regs[0]), full & 0xFFFFFFFF)
            self.assertEqual(m.c, full >> 32)
            # (hi:lo) >> 1  =  SHR hi; RCR lo
            m = exec1("SHR", regs=[lo, hi, 0, 0, 0, 0, 0, 0], dr=1, sr1=1, mode="i", src=1)
            w = isa.encode("ROTC", dr=0, sr=0, right=1)
            m.mem[0x3002], m.mem[0x3003] = w & 0xFF, w >> 8
            m.step()
            full = (hi << 16 | lo) >> 1
            self.assertEqual((m.regs[1] << 16 | m.regs[0]), full)

    def test_32_bit_add_and_sub_with_carry_chain(self):
        for _ in range(500):
            a, b = self.rnd.getrandbits(32), self.rnd.getrandbits(32)
            for name_lo, name_hi, exp in (("ADD", "ADC", a + b), ("SUB", "SBC", a - b)):
                m = Machine()
                m.pc = 0x3000
                m.regs[:] = [a & M, a >> 16, b & M, b >> 16, 0, 0, 0, 0]
                prog = [isa.encode(name_lo, dr=0, sr1=0, mode="r", src=2), isa.encode(name_hi, dr=1, sr1=1, mode="r", src=3)]
                for i, w in enumerate(prog):
                    m.mem[0x3000 + 2 * i], m.mem[0x3001 + 2 * i] = w & 0xFF, w >> 8
                m.step()
                m.step()
                self.assertEqual(m.regs[1] << 16 | m.regs[0], exp & 0xFFFFFFFF, (name_lo, a, b))


class TestBranches(unittest.TestCase):
    def test_nzp_branch_taken_matches_flags(self):
        for n in (0, 1):
            for z in (0, 1):
                for p in (0, 1):
                    if n + z + p != 1:
                        continue
                    for bn in (0, 1):
                        for bz in (0, 1):
                            for bp in (0, 1):
                                m = exec1("BR", flags={"n": n, "z": z, "p": p}, n=bn, z=bz, p=bp, off=5)
                                taken = (bn and n) or (bz and z) or (bp and p)
                                self.assertEqual(m.pc, 0x3000 + 2 + 10 if taken else 0x3002)

    def test_signed_and_unsigned_conditions_after_cmp(self):
        rnd = random.Random(4)
        vals = [0, 1, 2, 0x7FFF, 0x8000, 0x8001, 0xFFFF, 0x1234, 0xF234]
        pairs = [(a, b) for a in vals for b in vals] + [(rnd.getrandbits(16), rnd.getrandbits(16)) for _ in range(2000)]
        for a, b in pairs:
            m = exec1("CMP", regs=[0, a, b, 0, 0, 0, 0, 0], sr1=1, mode="r", src=2)
            sa, sb = s16(a), s16(b)
            expect = {"C": a >= b, "NC": a < b, "LT": sa < sb, "GE": sa >= sb, "GT": sa > sb, "LE": sa <= sb,
                      "V": not -32768 <= sa - sb <= 32767, "NV": -32768 <= sa - sb <= 32767}
            for name, exp in expect.items():
                self.assertEqual(m.cond(isa.COND_NAMES.index(name)), bool(exp), f"{name} cmp {a:#x},{b:#x}")


class TestMemory(unittest.TestCase):
    def test_byte_and_word_access_little_endian(self):
        src = """.ORIG x3000
            LEA  R1, BUF
            MOVI R0, #-2              ; xFFFE
            STW  R0, R1               ; palabra en BUF: FE FF
            LDL  R2, R1, #0           ; byte bajo, extiende el signo -> xFFFE
            LDL  R3, R1, #1           ; byte alto en la parte baja  -> xFFFF
            MOVI R4, #0x12
            SHL  R4, R4, #8           ; x1200
            STH  R4, R1, #1           ; byte alto de R4 (x12) en BUF+1
            STL  R0, R1, #2           ; byte bajo de R0 (xFE) en BUF+2
            LDW  R5, R1               ; xFFFE -> ahora x12FE
            LDH  R6, R1, #2           ; R6[15:8] = BUF+2 = xFE, conserva R6[7:0]
            HALT
        BUF .BLKW 2
        .END"""
        m, r, res = run_asm(src, regs=[0, 0, 0, 0, 0, 0, 0x0055, 0])
        self.assertTrue(r.ok, r.message)
        buf = res.symbols["PROG-BUF"]
        self.assertEqual(list(m.mem[buf:buf + 4]), [0xFE, 0x12, 0xFE, 0x00])
        self.assertEqual((m.regs[2], m.regs[3], m.regs[5], m.regs[6]), (0xFFFE, 0xFFFF, 0x12FE, 0xFE55))

    def test_int8_array_sum_uses_signed_bytes(self):
        """Datos de 8 bits con signo: LDL extiende el signo, STL guarda el byte bajo."""
        vals = [-128, 127, -1, 5, -77, 100, 0, -3, 42]
        data = ", ".join(str(v) for v in vals)
        src = f""".ORIG x3000
            LEA  R1, ARR
            MOVI R2, #{len(vals)}
            CLR  R0
        L   LDL  R3, R1
            ADD  R0, R0, R3
            ADD  R1, R1, #1
            ADD  R2, R2, #-1
            BRp  L
            LEA  R4, SUM8
            STL  R0, R4
            HALT
        ARR .BYTE {data}
        SUM8 .BYTE 0
        .END"""
        m, r, res = run_asm(src)
        self.assertTrue(r.ok, r.message)
        self.assertEqual(isa.to_s16(m.regs[0]), sum(vals))
        self.assertEqual(m.mem[res.symbols["PROG-SUM8"]], sum(vals) & 0xFF)

    def test_ldl_sign_extends_and_sets_flags(self):
        src = ".ORIG x3000\nLEA R1, B\nLDL R0, R1\nFIN HALT\nB .BYTE 0x80\n.END\n"
        m, r, _ = run_asm(src, stop_at="FIN")
        self.assertEqual(m.regs[0], 0xFF80)
        self.assertEqual(m.n, 1)

    def test_pc_relative_ld_st_lea(self):
        src = """.ORIG x3000
            LD   R0, K
            ADD  R0, R0, #1
            ST   R0, V
            LEA  R1, V
            HALT
        K   .FILL #41
        V   .FILL #0
        .END"""
        m, r, res = run_asm(src)
        self.assertEqual(m.regs[0], 42)
        self.assertEqual(m.mem[res.symbols["PROG-V"]], 42)
        self.assertEqual(m.regs[1], res.symbols["PROG-V"])

    def test_misaligned_word_access_is_a_fault(self):
        for op in ("LDW R0, R1", "STW R0, R1"):
            src = f".ORIG x3000\nLEA R1, B\nADD R1, R1, #1\n{op}\nHALT\nB .BLKW 2\n.END\n"
            m, r, _ = run_asm(src)
            self.assertEqual(r.reason, "fault")
            self.assertIn("dirección impar", r.message)

    def test_odd_jump_target_is_a_fault(self):
        src = ".ORIG x3000\nMOVI R1, #1\nJMP R1\nHALT\n.END\n"
        m, r, _ = run_asm(src)
        self.assertEqual(r.reason, "fault")
        self.assertIn("impar", r.message)

    def test_odd_pc_and_reserved_opcode(self):
        m = Machine()
        m.pc = 0x3001
        self.assertEqual(m.run().reason, "fault")
        m = Machine()
        m.pc = 0x3000
        w = 31 << 11                                     # PUSH sin registros: combinación reservada
        m.mem[0x3000], m.mem[0x3001] = w & 0xFF, w >> 8
        r = m.run()
        self.assertEqual(r.reason, "fault")
        self.assertIn("reservada", r.message)
        m = Machine()
        m.pc = 0x3000
        w = 29 << 11 | 3 << 3                            # MUL con fn = 3: variante reservada
        m.mem[0x3000], m.mem[0x3001] = w & 0xFF, w >> 8
        r = m.run()
        self.assertEqual(r.reason, "fault")
        self.assertIn("variante reservada", r.message)

    def test_address_wraps_at_64k(self):
        m, r, _ = run_asm(".ORIG x3000\nMOVI R1, #-1\nMOVI R0, #7\nSTL R0, R1, #1\nHALT\n.END\n")  # xFFFF + 1 -> 0
        self.assertEqual(m.mem[0], 7)


class TestMulDiv(unittest.TestCase):
    """MUL/MULH/MULHU y DIV/DIVU/REM/REMU contra referencias de Python con enteros."""

    def setUp(self):
        self.rnd = random.Random(5)

    def rand16(self):
        return self.rnd.choice([0, 1, 2, 10, 0x7FFF, 0x8000, 0x8001, 0xFFFF, 0xFFFE, self.rnd.getrandbits(16),
                                self.rnd.getrandbits(16), self.rnd.getrandbits(8), (-self.rnd.getrandbits(8)) & M])

    def run1(self, name, a, b, flags=None):
        return exec1(name, regs=[0, a, b, 0, 0, 0, 0, 0], flags=flags or {}, dr=0, sr1=1, sr2=2)

    def nzp(self, r):
        return (int(s16(r) < 0), int(r & M == 0), int(s16(r) > 0))

    def test_mul_low_high_signed_and_unsigned(self):
        for _ in range(4000):
            a, b = self.rand16(), self.rand16()
            ps, pu = s16(a) * s16(b), a * b
            m = self.run1("MUL", a, b, {"c": 1, "v": 0})
            self.assertEqual(m.regs[0], ps & M)
            self.assertEqual(m.regs[0], pu & M, "la parte baja es la misma con y sin signo")
            self.assertEqual(m.v, int(s16(ps & M) != ps), "V = el producto con signo no entra en 16 bits")
            self.assertEqual(m.c, 1, "MUL no toca C")
            self.assertEqual((m.n, m.z, m.p), self.nzp(ps & M))
            m = self.run1("MULH", a, b, {"c": 1, "v": 1})
            self.assertEqual(m.regs[0], ps >> 16 & M)
            self.assertEqual((m.c, m.v), (1, 1), "MULH no toca C ni V")
            self.assertEqual((m.n, m.z, m.p), self.nzp(ps >> 16 & M))
            m = self.run1("MULHU", a, b, {"c": 0, "v": 1})
            self.assertEqual(m.regs[0], pu >> 16 & M)
            self.assertEqual((m.c, m.v), (0, 1))

    def test_mul_and_mulh_give_the_full_32_bit_product(self):
        for _ in range(500):
            a, b = self.rand16(), self.rand16()
            lo = self.run1("MUL", a, b).regs[0]
            full = (self.run1("MULH", a, b).regs[0] << 16 | lo)
            self.assertEqual(full, (s16(a) * s16(b)) & 0xFFFFFFFF)
            full_u = (self.run1("MULHU", a, b).regs[0] << 16 | lo)
            self.assertEqual(full_u, a * b)

    def test_division_family_against_reference(self):
        for _ in range(4000):
            a, b = self.rand16(), self.rand16()
            sa, sb = s16(a), s16(b)
            for name in ("DIV", "DIVU", "REM", "REMU"):
                signed = name in ("DIV", "REM")
                x, y = (sa, sb) if signed else (a, b)
                m = self.run1(name, a, b, {"c": 1, "v": 0})
                if y == 0:
                    q, rem, v = M, x & M, 1                  # sin excepción: cociente todo unos, resto = dividendo
                elif signed and x == -32768 and y == -1:
                    q, rem, v = 0x8000, 0, 1
                else:
                    q = abs(x) // abs(y) * (-1 if (x < 0) != (y < 0) else 1)
                    rem, v = x - q * y, 0
                    if signed:
                        self.assertTrue(abs(rem) < abs(y) and (rem == 0 or (rem < 0) == (x < 0)), "resto con el signo del dividendo")
                    q, rem = q & M, rem & M
                want = q if name in ("DIV", "DIVU") else rem
                self.assertEqual(m.regs[0], want, (name, a, b))
                self.assertEqual(m.v, v, (name, a, b))
                self.assertEqual(m.c, 1, "la división no toca C")
                self.assertEqual((m.n, m.z, m.p), self.nzp(want))

    def test_signed_division_truncates_toward_zero(self):
        for a, b, q, r in [(7, 2, 3, 1), (-7, 2, -3, -1), (7, -2, -3, 1), (-7, -2, 3, -1), (1, 3, 0, 1), (-1, 3, 0, -1)]:
            self.assertEqual(s16(self.run1("DIV", a & M, b & M).regs[0]), q)
            self.assertEqual(s16(self.run1("REM", a & M, b & M).regs[0]), r)

    def test_registers_may_overlap(self):
        m = exec1("MUL", regs=[0, 7, 0, 0, 0, 0, 0, 0], dr=1, sr1=1, sr2=1)
        self.assertEqual(m.regs[1], 49)
        m = exec1("DIV", regs=[0, 100, 7, 0, 0, 0, 0, 0], dr=2, sr1=1, sr2=2)
        self.assertEqual(m.regs[2], 14)

    def test_fixed_point_q7_8_multiply_with_scaling_by_the_program(self):
        """Q7.8 x Q7.8 -> Q7.8 truncando: (a*b) >> 8 con MUL, MULH y desplazamientos (el programa escala)."""
        src = """.ORIG x3000
            MUL   R3, R1, R2        ; parte baja
            MULH  R4, R1, R2        ; parte alta
            SHR   R3, R3, #8
            SHL   R4, R4, #8
            OR    R0, R3, R4
            HALT
            .END"""
        for _ in range(500):
            a, b = self.rand16(), self.rand16()
            m, r, _ = run_asm(src, regs=[0, a, b, 0, 0, 0, 0, 0])
            self.assertEqual(m.regs[0], (s16(a) * s16(b) >> 8) & M)
        # 13,828125 x 7,23828125 en Q7.8 = 3540 x 1853 = 6559620; >> 8 = 25623 (100,08984375 en Q7.8)
        m, r, _ = run_asm(src, regs=[0, 3540, 1853, 0, 0, 0, 0, 0])
        self.assertEqual(m.regs[0], 3540 * 1853 >> 8)

    def test_muldiv_count_as_one_instruction_each(self):
        m, r, _ = run_asm(".ORIG x3000\nMUL R0, R1, R2\nDIV R3, R1, R2\nHALT\n.END\n", regs=[0, 9, 3, 0, 0, 0, 0, 0])
        self.assertEqual((m.regs[0], m.regs[3]), (27, 3))
        self.assertEqual(r.user_instructions, 3)
        self.assertEqual((r.histogram["MUL"], r.histogram["DIV"]), (1, 1))


class TestOpcode31(unittest.TestCase):
    """PUSH/POP de varios registros y DIVREMU/DIVREM (cociente y resto en una instrucción)."""

    def setUp(self):
        self.rnd = random.Random(31)

    def test_divrem_equals_div_then_rem(self):
        vals = [0, 1, 2, 7, 10, 100, 0x7FFF, 0x8000, 0x8001, 0xFFFF, 0xFFFE]
        cases = [(a, b) for a in vals for b in vals] + [(self.rnd.getrandbits(16), self.rnd.getrandbits(16))
                                                         for _ in range(3000)]
        for fused, div, rem in (("DIVREMU", "DIVU", "REMU"), ("DIVREM", "DIV", "REM")):
            for a, b in cases:
                c0 = self.rnd.randrange(2)
                regs = [0x1111, a, b, 0, 0, 0, 0, 0]
                m = exec1(fused, regs=regs, flags={"c": c0}, dr=3, sr1=1, sr2=2)
                q = exec1(div, regs=regs, dr=3, sr1=1, sr2=2)
                r = exec1(rem, regs=regs, dr=1, sr1=1, sr2=2)
                self.assertEqual((m.regs[3], m.regs[1], m.regs[2]), (q.regs[3], r.regs[1], b), (fused, a, b))
                self.assertEqual((m.n, m.z, m.p, m.v), (q.n, q.z, q.p, q.v), "banderas como el cociente")
                self.assertEqual(m.c, c0, "C no cambia")
                self.assertEqual(m.count, 1)

    def test_divrem_when_the_divisor_is_also_the_destination(self):
        m = exec1("DIVREMU", regs=[0, 100, 7, 0, 0, 0, 0, 0], dr=2, sr1=1, sr2=2)   # DR = SR2
        self.assertEqual((m.regs[2], m.regs[1]), (14, 2))                         # 100 = 14*7 + 2

    def test_push_pop_restores_and_leaves_sp_where_it_was(self):
        for _ in range(300):
            mask = self.rnd.choice([m for m in range(1, 256) if not m >> 6 & 1])
            regs = [self.rnd.getrandbits(16) for _ in range(8)]
            regs[6] = self.rnd.choice([0, 0xFE00, 0x8000])
            m = exec1("PUSH", regs=list(regs), flags={"n": 1, "z": 0, "p": 0, "c": 1, "v": 1}, mask=mask)
            k = bin(mask).count("1")
            self.assertEqual(m.regs[6], (regs[6] - 2 * k) & M)
            self.assertEqual((m.n, m.z, m.p, m.c, m.v), (1, 0, 0, 1, 1), "PUSH no toca las banderas")
            stored = [m.mem[(m.regs[6] + 2 * i) & M] | m.mem[(m.regs[6] + 2 * i + 1) & M] << 8 for i in range(k)]
            self.assertEqual(stored, [regs[r] for r in range(8) if mask >> r & 1], "el registro más bajo, más abajo")
            for r in range(8):
                if r != 6:
                    m.regs[r] = 0
            w = isa.encode("POP", mask=mask)
            m.mem[m.pc], m.mem[m.pc + 1] = w & 0xFF, w >> 8
            m.step()
            for r in range(8):
                expect = regs[r] if (mask >> r & 1 or r == 6) else 0
                self.assertEqual(m.regs[r], expect, f"R{r} mask={mask:08b}")
            self.assertEqual(m.count, 2)

    def test_push_from_zero_wraps_to_the_top_of_memory(self):
        m = exec1("PUSH", regs=[0, 0x1234, 0, 0, 0, 0, 0, 0x5678], mask=0b10000010)
        self.assertEqual(m.regs[6], 0xFFFC)
        self.assertEqual(m.mem[0xFFFC:0x10000], bytes([0x34, 0x12, 0x78, 0x56]))

    def test_odd_stack_pointer_is_an_exception(self):
        m, r, _ = run_asm("        .ORIG x3000\n        MOVI R6, #1\n        PUSH R1\n        HALT\n        .END\n")
        self.assertEqual(r.reason, "fault")
        self.assertIn("impar", r.message)

    def test_subroutine_with_push_pop(self):
        src = """\
        .ORIG x3000
        MOVI R1, #5
        MOVI R2, #9
        JSR  RUT
        HALT
RUT     PUSH R1, R2, R7
        MOVI R1, #0
        MOVI R2, #0
        JSR  HOJA
        POP  R1, R2, R7
        RET
HOJA    RET
        .END
"""
        m, r, _ = run_asm(src)
        self.assertEqual(r.reason, "halt")
        self.assertEqual((m.regs[1], m.regs[2], m.regs[6]), (5, 9, 0))
        self.assertEqual(m.hist["PUSH"], 1)
        self.assertEqual(m.hist["POP"], 1)


class TestControl(unittest.TestCase):
    def test_jsr_saves_pc_plus_2_and_ret_returns(self):
        src = """.ORIG x3000
            JSR SUB1
        AQUI HALT
        SUB1 MOVI R0, #9
            RET
        .END"""
        m, r, res = run_asm(src, stop_at="AQUI")                    # antes del HALT, que cambiaría R7
        self.assertEqual(m.regs[7], res.symbols["PROG-AQUI"])     # PC+2 de la instrucción JSR
        self.assertEqual(m.regs[0], 9)
        self.assertTrue(r.ok)
        self.assertEqual(r.instructions, 3)                         # JSR, MOVI, RET
        m, r, res = run_asm(src)                                    # completo: el HALT (TRAP) deja en R7 la dirección que sigue
        self.assertEqual((r.user_instructions, r.os_instructions), (4, 2))
        self.assertEqual(m.regs[7], 0)                              # la rutina HALT del SO usa R7 como auxiliar

    def test_jsrr_and_jmp(self):
        src = """.ORIG x3000
            LEA R3, F
            JSRR R3
            LEA R2, FIN
            JMP R2
            MOVI R5, #1            ; no debe ejecutarse
        FIN HALT
        F   MOVI R0, #3
            RET
        .END"""
        m, r, _ = run_asm(src)
        self.assertEqual((m.regs[0], m.regs[5]), (3, 0))

    def test_jsrr_r7_reads_target_before_linking(self):
        src = ".ORIG x3000\nLEA R7, F\nJSRR R7\nHALT\nF MOVI R0, #1\nRET\n.END\n"
        m, r, _ = run_asm(src)
        self.assertTrue(r.ok)
        self.assertEqual(m.regs[0], 1)

    def test_nop_is_all_zero_word_and_does_nothing(self):
        m = Machine()
        m.pc = 0x3000
        m.regs[:] = [1, 2, 3, 4, 5, 6, 7, 8]
        m.step()
        self.assertEqual((m.pc, m.regs, m.c, m.v), (0x3002, [1, 2, 3, 4, 5, 6, 7, 8], 0, 0))

    def test_loop_counts_instructions_and_stats(self):
        src = """.ORIG x3000
            MOVI R1, #10
            CLR  R0
        L   ADD  R0, R0, #3
            ADD  R1, R1, #-1
            BRp  L
            ST   R0, RES
            HALT
        RES .FILL #0
        .END"""
        m, r, res = run_asm(src)
        self.assertEqual(m.regs[0], 30)
        self.assertEqual(r.user_instructions, 2 + 10 * 3 + 2)
        self.assertEqual(r.histogram["ADD"], 20)
        self.assertEqual(r.bytes_written, 2)
        self.assertEqual(r.image_bytes, len(res.image.data))
        self.assertEqual(r.fetched_bytes, 2 * 7)          # 7 instrucciones distintas
        self.assertEqual(r.min_addr, 0x3000)

    def test_memory_use_inside_and_outside_the_image(self):
        src = """.ORIG x3000
            MOVI R6, #0          ; pila en la parte alta de la memoria: R6 = x0000 - 2 = xFFFE
            ADD  R6, R6, #-2
            STW  R1, R6, #0      ; dos bytes fuera de la imagen
            LD   R2, DATO        ; dos bytes de datos dentro de la imagen
            HALT
        DATO .FILL x1234
        .END"""
        m, r, res = run_asm(src)
        self.assertEqual(r.touched_bytes, 10 + 2 + 2)          # 5 instrucciones (fetch), DATO, pila
        self.assertEqual(r.touched_in_image, 12)
        self.assertEqual(r.touched_outside, 2)
        self.assertEqual(r.outside_ranges, [(0xFFFE, 0xFFFF)])
        self.assertIn("usados 14 bytes distintos: 12 dentro de la imagen y 2 fuera (xFFFE–xFFFF)", r.memory_line())
        self.assertIn("imagen 12 bytes (6 palabras, x3000–x300B)", r.memory_line())

    def test_traps(self):
        src = """.ORIG x3000
            GETC
            OUT                  ; repite el primer carácter
            IN                   ; lee y muestra el segundo
            LEA R0, MSG
            PUTS
            GETC                 ; fin de la entrada -> -1
            HALT
        MSG .STRINGZ "!ok"
        .END"""
        m, r, _ = run_asm(src, inp="ab")
        self.assertEqual(r.output, "a" + "b" + "!ok")
        self.assertEqual(m.regs[0], 0xFFFF)

    def test_instruction_limit(self):
        m, r, _ = run_asm(".ORIG x3000\nL BR L\n.END\n", max_instr=50)
        self.assertEqual(r.reason, "limit")
        self.assertEqual(r.instructions, 50)

    def test_run_from_file_formats(self):
        import tempfile
        from pathlib import Path
        from lc10.image import Image
        res = assemble([("p.asm", ".ORIG x3000\nMOVI R0, #77\nHALT\n.END\n")])
        with tempfile.TemporaryDirectory() as d:
            for fmt in ("bin", "hex", "dec", "bits"):
                p = Path(d) / f"p.{fmt}"
                res.image.save(p)
                m, r = run_image(Image.load(p))
                self.assertEqual((r.ok, m.regs[0]), (True, 77), fmt)


if __name__ == "__main__":
    unittest.main()
