'''Conjunto de instrucciones (ISA) para el simulador y ensamblador'''


def get_bits(value, high, low=None, unsigned=False):
    """
    Extrae un bit específico o un rango de bits de un valor numérico.

    Parámetros:
    - value (int): Valor numérico del cual extraer los bits.
    - high (int): Índice del bit más significativo o bit individual si low es None.
    - low (int, opcional): Índice del bit menos significativo. Si es None, extrae solo el bit `high`.
    - unsigned (bool): Si es True, retorna el valor sin signo.
                       Si es False (por defecto para rangos > 1 bit), interpreta el resultado
                       con signo usando complemento a 2 (útil para inmediatos con signo como IMM4 o palabras de 16 bits).
                       Para un único bit, siempre devuelve 0 o 1.

    Retorna:
    - int: Valor resultante de los bits seleccionados.
    """
    if not isinstance(value, int):
        value = int(value)

    # Caso de un solo bit:
    if low is None:
        return (value >> high) & 1

    # Asegurar que high >= low:
    if low > high:
        high, low = low, high

    width = high - low + 1

    # Un solo bit siempre es 0 o 1:
    if width == 1:
        return (value >> low) & 1

    mask = (1 << width) - 1
    raw = (value >> low) & mask

    if unsigned:
        return raw

    # Extensión de signo (complemento a 2) si unsigned=False:
    sign_bit = 1 << (width - 1)
    if raw & sign_bit:
        return raw - (1 << width)
    return raw


def get_nzp(value):
    """Calcula los códigos de condición NZP (Negative=0b100, Zero=0b010, Positive=0b001)"""
    signed_val = get_bits(value, 15, 0)
    n = 0b100 if signed_val <  0 else 0b000
    z = 0b010 if signed_val == 0 else 0b000
    p = 0b001 if signed_val >  0 else 0b000
    return n | z | p


def get_oc(overflow=False, carry=False):
    """Calcula los códigos de condición OC (Overflow=0b10, Carry=0b01)"""
    o = 0b10 if overflow else 0b00
    c = 0b01 if carry else 0b00
    return o | c


# ---------------------------------------------------------------------------
# Helper para ensamblado de operaciones tipo ALU (con valores ya numéricos)
# ---------------------------------------------------------------------------

def _assemble_alu_op(cls, format_idx, arguments):
    """
    Ensambla instrucciones ALU que reciben operandos ya numéricos:
    format_idx 0 -> [mnemonic, DR, SR1, SR2]  (modo registro = 0)
    format_idx 1 -> [mnemonic, DR, SR1, IMM4] (modo inmediato = 1)
    """
    dr = int(arguments[1])
    sr1 = int(arguments[2])
    if format_idx == 0:
        sr2 = int(arguments[3])
        val = (cls.OPCODE << 11) | ((dr & 7) << 8) | ((sr1 & 7) << 5) | (sr2 & 7)
    else:
        imm4 = int(arguments[3]) & 0xF
        val = (cls.OPCODE << 11) | ((dr & 7) << 8) | ((sr1 & 7) << 5) | (1 << 4) | imm4
    return cls(val)



# ---------------------------------------------------------------------------
# Clase base de instrucción
# ---------------------------------------------------------------------------

class BASE_INSTRUCTION():
    OPCODE = -1
    MNEMONICS = []
    FORMATS = []

    def __init__(self, instruction_value):
        self.VALUE = instruction_value

    def __int__(self):
        return self.VALUE

    def __index__(self):
        return self.VALUE

    def __str__(self):
        return self.disasemble()

    def __repr__(self):
        return f"<{self.__class__.__name__} {self.disasemble()} ({self.VALUE:#06x})>"

    def disasemble(self):
        return f"{self.__class__.__name__} {self.VALUE:#06x}"

    disassemble = disasemble

    @classmethod
    def s_asemble_method(cls, format_idx, arguments):
        """
        Devuelve la instancia de la instrucción ensamblada.
        Recibe:
        - format_idx (int): Índice correspondiente al formato en FORMATS.
        - arguments (list): [MNEMONIC, arg1, arg2, ...] donde los operandos ya han sido
          parseados a formato numérico (enteros) por el ensamblador.
        """
        raise NotImplementedError(f"{cls.__name__} debe implementar s_asemble_method")

    # FETCH es una etapa únicamente simulada a nivel del simulador...
    def on_decode(self, machine):
        ...

    def on_execute(self, machine):
        ...

    def on_memory(self, machine):
        ...

    def on_writeback(self, machine):
        ...



# ---------------------------------------------------------------------------
# Clases de instrucciones
# ---------------------------------------------------------------------------

# 0: BR (BRNZP)
class Instruction_BRNZP(BASE_INSTRUCTION):
    OPCODE = 0
    MNEMONICS = ["BR", "BRN", "BRZ", "BRP", "BRNZ", "BRNP", "BRZP", "BRNZP", "NOP"]
    FORMATS = [["BR", "PCOFFSET8"],
               ["BRN", "PCOFFSET8"],
               ["BRZ", "PCOFFSET8"],
               ["BRP", "PCOFFSET8"],
               ["BRNZ", "PCOFFSET8"],
               ["BRNP", "PCOFFSET8"],
               ["BRZP", "PCOFFSET8"],
               ["BRNZP", "PCOFFSET8"],
               ["NOP"]]

    def __init__(self, instruction_value):
        super().__init__(instruction_value)
        self.NZP       = get_bits(instruction_value, 10,  8, unsigned=True)
        self.PCOFFSET8 = get_bits(instruction_value,  7,  0)

    def on_decode(self, machine):
        if hasattr(machine, 'conditional_branch_setup'):
            machine.conditional_branch_setup()
        return super().on_decode(machine)

    def on_execute(self, machine):
        self.destination = (machine.PC + 2 + (2 * self.PCOFFSET8)) & 0xFFFF
        self.condition = bool(machine.NZP & self.NZP)
        return super().on_execute(machine)

    def on_writeback(self, machine):
        if hasattr(machine, 'conditional_branch_result'):
            machine.conditional_branch_result(self.condition, self.destination)
        elif self.condition:
            machine.PC = self.destination
        return super().on_writeback(machine)

    @classmethod
    def s_asemble_method(cls, format_idx, arguments):
        mnemonic = str(arguments[0]).upper()
        if mnemonic == "NOP":
            return cls((cls.OPCODE << 11) | (0b111 << 8))
        pcoffset8 = int(arguments[1]) & 0xFF
        cond = mnemonic[2:].lower()
        if not cond:
            nzp = 0b111
        else:
            n = 1 if 'n' in cond else 0
            z = 1 if 'z' in cond else 0
            p = 1 if 'p' in cond else 0
            nzp = (n << 2) | (z << 1) | p
        val = (cls.OPCODE << 11) | ((nzp & 7) << 8) | pcoffset8
        return cls(val)

    def disasemble(self):
        cond = ("n" if self.NZP & 4 else "") + ("z" if self.NZP & 2 else "") + ("p" if self.NZP & 1 else "")
        if self.NZP == 0b111:
            cond = "nzp"
        return f"BR{cond} #{self.PCOFFSET8}"


# 1: BR (BROC)
class Instruction_BROC(BASE_INSTRUCTION):
    OPCODE = 1
    MNEMONICS = ["BRO", "BRC", "BROC"]
    FORMATS = [["BRO", "PCOFFSET8"],
               ["BRC", "PCOFFSET8"],
               ["BROC", "PCOFFSET8"]]

    def __init__(self, instruction_value):
        super().__init__(instruction_value)
        self.OC        = get_bits(instruction_value, 10,  9, unsigned=True)
        self.PCOFFSET8 = get_bits(instruction_value,  7,  0)

    def on_decode(self, machine):
        if hasattr(machine, 'conditional_branch_setup'):
            machine.conditional_branch_setup()
        return super().on_decode(machine)

    def on_execute(self, machine):
        self.destination = (machine.PC + 2 + (2 * self.PCOFFSET8)) & 0xFFFF
        self.condition = bool(machine.OC & self.OC)
        return super().on_execute(machine)

    def on_writeback(self, machine):
        if hasattr(machine, 'conditional_branch_result'):
            machine.conditional_branch_result(self.condition, self.destination)
        elif self.condition:
            machine.PC = self.destination
        return super().on_writeback(machine)

    @classmethod
    def s_asemble_method(cls, format_idx, arguments):
        mnemonic = str(arguments[0]).upper()
        pcoffset8 = int(arguments[1]) & 0xFF
        cond = mnemonic[2:].lower()
        o = 1 if 'o' in cond else 0
        c = 1 if 'c' in cond else 0
        oc = (o << 1) | c
        val = (cls.OPCODE << 11) | ((oc & 3) << 9) | pcoffset8
        return cls(val)

    def disasemble(self):
        cond = ("o" if self.OC & 2 else "") + ("c" if self.OC & 1 else "")
        return f"BR{cond} #{self.PCOFFSET8}"


# 2: ADD
class Instruction_ADD(BASE_INSTRUCTION):
    OPCODE = 2
    MNEMONICS = ["ADD"]
    FORMATS = [["ADD", "REG", "REG", "REG"], ["ADD", "REG", "REG", "IMM4"]]

    def __init__(self, instruction_value):
        super().__init__(instruction_value)
        self.DR   = get_bits(instruction_value, 10,  8, unsigned=True)
        self.SR1  = get_bits(instruction_value,  7,  5, unsigned=True)
        self.MODE = get_bits(instruction_value,  4)
        self.SR2  = get_bits(instruction_value,  2,  0, unsigned=True)
        self.IMM4 = get_bits(instruction_value,  3,  0)

    def on_execute(self, machine):
        self.operand_1 = machine.REG[self.SR1]
        if self.MODE == 0:
            self.operand_2 = machine.REG[self.SR2]
        else: # self.MODE == 1
            self.operand_2 = self.IMM4

        full_sum = self.operand_1 + self.operand_2
        self.result = get_bits(full_sum, 15, 0)
        u1 = self.operand_1 & 0xFFFF
        u2 = self.operand_2 & 0xFFFF
        self.carry = 1 if ((u1 + u2) > 0xFFFF) else 0
        self.overflow = 1 if ((~(self.operand_1 ^ self.operand_2) & (self.operand_1 ^ self.result) & 0x8000) != 0) else 0
        return super().on_execute(machine)

    def on_writeback(self, machine):
        machine.REG[self.DR] = self.result
        machine.NZP = get_nzp(self.result)
        machine.OC = get_oc(self.overflow, self.carry)
        return super().on_writeback(machine)

    @classmethod
    def s_asemble_method(cls, format_idx, arguments):
        return _assemble_alu_op(cls, format_idx, arguments)

    def disasemble(self):
        if self.MODE == 0:
            return f"ADD R{self.DR}, R{self.SR1}, R{self.SR2}"
        return f"ADD R{self.DR}, R{self.SR1}, #{self.IMM4}"


# 3: ADC
class Instruction_ADC(BASE_INSTRUCTION):
    OPCODE = 3
    MNEMONICS = ["ADC"]
    FORMATS = [["ADC", "REG", "REG", "REG"], ["ADC", "REG", "REG", "IMM4"]]

    def __init__(self, instruction_value):
        super().__init__(instruction_value)
        self.DR   = get_bits(instruction_value, 10,  8, unsigned=True)
        self.SR1  = get_bits(instruction_value,  7,  5, unsigned=True)
        self.MODE = get_bits(instruction_value,  4)
        self.SR2  = get_bits(instruction_value,  2,  0, unsigned=True)
        self.IMM4 = get_bits(instruction_value,  3,  0)

    def on_execute(self, machine):
        self.operand_1 = machine.REG[self.SR1]
        if self.MODE == 0:
            self.operand_2 = machine.REG[self.SR2]
        else: # self.MODE == 1
            self.operand_2 = self.IMM4

        c_in = machine.OC & 1
        full_sum = self.operand_1 + self.operand_2 + c_in
        self.result = get_bits(full_sum, 15, 0)
        u1 = self.operand_1 & 0xFFFF
        u2 = self.operand_2 & 0xFFFF
        self.carry = 1 if ((u1 + u2 + c_in) > 0xFFFF) else 0
        self.overflow = 1 if ((~(self.operand_1 ^ self.operand_2) & (self.operand_1 ^ self.result) & 0x8000) != 0) else 0
        return super().on_execute(machine)

    def on_writeback(self, machine):
        machine.REG[self.DR] = self.result
        machine.NZP = get_nzp(self.result)
        machine.OC = get_oc(self.overflow, self.carry)
        return super().on_writeback(machine)

    @classmethod
    def s_asemble_method(cls, format_idx, arguments):
        return _assemble_alu_op(cls, format_idx, arguments)

    def disasemble(self):
        if self.MODE == 0:
            return f"ADC R{self.DR}, R{self.SR1}, R{self.SR2}"
        return f"ADC R{self.DR}, R{self.SR1}, #{self.IMM4}"


# 4: LD
class Instruction_LD(BASE_INSTRUCTION):
    OPCODE = 4
    MNEMONICS = ["LD"]
    FORMATS = [["LD", "REG", "PCOFFSET8"]]

    def __init__(self, instruction_value):
        super().__init__(instruction_value)
        self.DR        = get_bits(instruction_value, 10,  8, unsigned=True)
        self.PCOFFSET8 = get_bits(instruction_value,  7,  0)

    def on_execute(self, machine):
        self.address = (machine.PC + 2 + (2 * self.PCOFFSET8)) & 0xFFFF
        return super().on_execute(machine)

    def on_memory(self, machine):
        if hasattr(machine, 'read_word'):
            self.data = machine.read_word(self.address)
        else:
            high = machine.MEMORY[self.address]
            low = machine.MEMORY[(self.address + 1) & 0xFFFF]
            self.data = get_bits((high << 8) | low, 15, 0)
        return super().on_memory(machine)

    def on_writeback(self, machine):
        machine.REG[self.DR] = self.data
        machine.NZP = get_nzp(self.data)
        return super().on_writeback(machine)

    @classmethod
    def s_asemble_method(cls, format_idx, arguments):
        dr = int(arguments[1])
        pcoffset8 = int(arguments[2]) & 0xFF
        val = (cls.OPCODE << 11) | ((dr & 7) << 8) | pcoffset8
        return cls(val)

    def disasemble(self):
        return f"LD R{self.DR}, #{self.PCOFFSET8}"


# 5: LDB
class Instruction_LDB(BASE_INSTRUCTION):
    OPCODE = 5
    MNEMONICS = ["LDB"]
    FORMATS = [["LDB", "REG", "BPCOFFSET8"]]

    def __init__(self, instruction_value):
        super().__init__(instruction_value)
        self.DR         = get_bits(instruction_value, 10,  8, unsigned=True)
        self.BPCOFFSET8 = get_bits(instruction_value,  7,  0)

    def on_execute(self, machine):
        self.address = (machine.PC + 2 + self.BPCOFFSET8) & 0xFFFF
        return super().on_execute(machine)

    def on_memory(self, machine):
        if hasattr(machine, 'read_byte'):
            self.data = machine.read_byte(self.address)
        else:
            self.data = machine.MEMORY[self.address]
        return super().on_memory(machine)

    def on_writeback(self, machine):
        machine.REG[self.DR] = self.data
        machine.NZP = get_nzp(self.data)
        return super().on_writeback(machine)

    @classmethod
    def s_asemble_method(cls, format_idx, arguments):
        dr = int(arguments[1])
        bpcoffset8 = int(arguments[2]) & 0xFF
        val = (cls.OPCODE << 11) | ((dr & 7) << 8) | bpcoffset8
        return cls(val)

    def disasemble(self):
        return f"LDB R{self.DR}, #{self.BPCOFFSET8}"


# 6: ST
class Instruction_ST(BASE_INSTRUCTION):
    OPCODE = 6
    MNEMONICS = ["ST"]
    FORMATS = [["ST", "REG", "PCOFFSET8"]]

    def __init__(self, instruction_value):
        super().__init__(instruction_value)
        self.SR        = get_bits(instruction_value, 10,  8, unsigned=True)
        self.PCOFFSET8 = get_bits(instruction_value,  7,  0)

    def on_execute(self, machine):
        self.address = (machine.PC + 2 + (2 * self.PCOFFSET8)) & 0xFFFF
        self.data = machine.REG[self.SR]
        return super().on_execute(machine)

    def on_memory(self, machine):
        if hasattr(machine, 'write_word'):
            machine.write_word(self.address, self.data)
        else:
            machine.MEMORY[self.address] = (self.data >> 8) & 0xFF
            machine.MEMORY[(self.address + 1) & 0xFFFF] = self.data & 0xFF
        return super().on_memory(machine)

    @classmethod
    def s_asemble_method(cls, format_idx, arguments):
        sr = int(arguments[1])
        pcoffset8 = int(arguments[2]) & 0xFF
        val = (cls.OPCODE << 11) | ((sr & 7) << 8) | pcoffset8
        return cls(val)

    def disasemble(self):
        return f"ST R{self.SR}, #{self.PCOFFSET8}"


# 7: STB
class Instruction_STB(BASE_INSTRUCTION):
    OPCODE = 7
    MNEMONICS = ["STB"]
    FORMATS = [["STB", "REG", "BPCOFFSET8"]]

    def __init__(self, instruction_value):
        super().__init__(instruction_value)
        self.SR         = get_bits(instruction_value, 10,  8, unsigned=True)
        self.BPCOFFSET8 = get_bits(instruction_value,  7,  0)

    def on_execute(self, machine):
        self.address = (machine.PC + 2 + self.BPCOFFSET8) & 0xFFFF
        self.data = machine.REG[self.SR] & 0xFF
        return super().on_execute(machine)

    def on_memory(self, machine):
        if hasattr(machine, 'write_byte'):
            machine.write_byte(self.address, self.data)
        else:
            machine.MEMORY[self.address] = self.data
        return super().on_memory(machine)

    @classmethod
    def s_asemble_method(cls, format_idx, arguments):
        sr = int(arguments[1])
        bpcoffset8 = int(arguments[2]) & 0xFF
        val = (cls.OPCODE << 11) | ((sr & 7) << 8) | bpcoffset8
        return cls(val)

    def disasemble(self):
        return f"STB R{self.SR}, #{self.BPCOFFSET8}"


# 8: JSR / JSRR
class Instruction_JSR(BASE_INSTRUCTION):
    OPCODE = 8
    MNEMONICS = ["JSR", "JSRR"]
    FORMATS = [["JSR", "PCOFFSET10"], ["JSRR", "REG"]]

    def __init__(self, instruction_value):
        super().__init__(instruction_value)
        self.MODE       = get_bits(instruction_value, 10)
        self.PCOFFSET10 = get_bits(instruction_value,  9,  0)
        self.BASER      = get_bits(instruction_value,  7,  5, unsigned=True)

    def on_execute(self, machine):
        self.return_address = (machine.PC + 2) & 0xFFFF
        if self.MODE == 1:
            self.destination = (machine.PC + 2 + (2 * self.PCOFFSET10)) & 0xFFFF
        else: # self.MODE == 0 (JSRR)
            self.destination = machine.REG[self.BASER] & 0xFFFF
        return super().on_execute(machine)

    def on_writeback(self, machine):
        machine.REG[7] = self.return_address
        if hasattr(machine, 'unconditional_branch'):
            machine.unconditional_branch(self.destination)
        else:
            machine.PC = self.destination
        return super().on_writeback(machine)

    @classmethod
    def s_asemble_method(cls, format_idx, arguments):
        if format_idx == 0:
            pcoffset10 = int(arguments[1]) & 0x3FF
            val = (cls.OPCODE << 11) | (1 << 10) | pcoffset10
        else:
            baser = int(arguments[1])
            val = (cls.OPCODE << 11) | ((baser & 7) << 5)
        return cls(val)

    def disasemble(self):
        if self.MODE == 1:
            return f"JSR #{self.PCOFFSET10}"
        return f"JSRR R{self.BASER}"


# 9: AND
class Instruction_AND(BASE_INSTRUCTION):
    OPCODE = 9
    MNEMONICS = ["AND"]
    FORMATS = [["AND", "REG", "REG", "REG"], ["AND", "REG", "REG", "IMM4"]]

    def __init__(self, instruction_value):
        super().__init__(instruction_value)
        self.DR   = get_bits(instruction_value, 10,  8, unsigned=True)
        self.SR1  = get_bits(instruction_value,  7,  5, unsigned=True)
        self.MODE = get_bits(instruction_value,  4)
        self.SR2  = get_bits(instruction_value,  2,  0, unsigned=True)
        self.IMM4 = get_bits(instruction_value,  3,  0)

    def on_execute(self, machine):
        self.operand_1 = machine.REG[self.SR1]
        if self.MODE == 0:
            self.operand_2 = machine.REG[self.SR2]
        else: # self.MODE == 1
            self.operand_2 = self.IMM4
        self.result = get_bits(self.operand_1 & self.operand_2, 15, 0)
        return super().on_execute(machine)

    def on_writeback(self, machine):
        machine.REG[self.DR] = self.result
        machine.NZP = get_nzp(self.result)
        return super().on_writeback(machine)

    @classmethod
    def s_asemble_method(cls, format_idx, arguments):
        return _assemble_alu_op(cls, format_idx, arguments)

    def disasemble(self):
        if self.MODE == 0:
            return f"AND R{self.DR}, R{self.SR1}, R{self.SR2}"
        return f"AND R{self.DR}, R{self.SR1}, #{self.IMM4}"


# 10: LDR
class Instruction_LDR(BASE_INSTRUCTION):
    OPCODE = 10
    MNEMONICS = ["LDR"]
    FORMATS = [["LDR", "REG", "REG", "UOFFSET5"]]

    def __init__(self, instruction_value):
        super().__init__(instruction_value)
        self.DR       = get_bits(instruction_value, 10,  8, unsigned=True)
        self.BASER    = get_bits(instruction_value,  7,  5, unsigned=True)
        self.UOFFSET5 = get_bits(instruction_value,  4,  0, unsigned=True)

    def on_execute(self, machine):
        self.address = (machine.REG[self.BASER] + (2 * self.UOFFSET5)) & 0xFFFF
        return super().on_execute(machine)

    def on_memory(self, machine):
        if hasattr(machine, 'read_word'):
            self.data = machine.read_word(self.address)
        else:
            high = machine.MEMORY[self.address]
            low = machine.MEMORY[(self.address + 1) & 0xFFFF]
            self.data = get_bits((high << 8) | low, 15, 0)
        return super().on_memory(machine)

    def on_writeback(self, machine):
        machine.REG[self.DR] = self.data
        machine.NZP = get_nzp(self.data)
        return super().on_writeback(machine)

    @classmethod
    def s_asemble_method(cls, format_idx, arguments):
        dr = int(arguments[1])
        baser = int(arguments[2])
        uoffset5 = int(arguments[3]) & 0x1F
        val = (cls.OPCODE << 11) | ((dr & 7) << 8) | ((baser & 7) << 5) | uoffset5
        return cls(val)

    def disasemble(self):
        return f"LDR R{self.DR}, R{self.BASER}, #{self.UOFFSET5}"


# 11: LDRB
class Instruction_LDRB(BASE_INSTRUCTION):
    OPCODE = 11
    MNEMONICS = ["LDRB"]
    FORMATS = [["LDRB", "REG", "REG", "BUOFFSET5"]]

    def __init__(self, instruction_value):
        super().__init__(instruction_value)
        self.DR        = get_bits(instruction_value, 10,  8, unsigned=True)
        self.BASER     = get_bits(instruction_value,  7,  5, unsigned=True)
        self.BUOFFSET5 = get_bits(instruction_value,  4,  0, unsigned=True)

    def on_execute(self, machine):
        self.address = (machine.REG[self.BASER] + self.BUOFFSET5) & 0xFFFF
        return super().on_execute(machine)

    def on_memory(self, machine):
        if hasattr(machine, 'read_byte'):
            self.data = machine.read_byte(self.address)
        else:
            self.data = machine.MEMORY[self.address]
        return super().on_memory(machine)

    def on_writeback(self, machine):
        machine.REG[self.DR] = self.data
        machine.NZP = get_nzp(self.data)
        return super().on_writeback(machine)

    @classmethod
    def s_asemble_method(cls, format_idx, arguments):
        dr = int(arguments[1])
        baser = int(arguments[2])
        buoffset5 = int(arguments[3]) & 0x1F
        val = (cls.OPCODE << 11) | ((dr & 7) << 8) | ((baser & 7) << 5) | buoffset5
        return cls(val)

    def disasemble(self):
        return f"LDRB R{self.DR}, R{self.BASER}, #{self.BUOFFSET5}"


# 12: STR
class Instruction_STR(BASE_INSTRUCTION):
    OPCODE = 12
    MNEMONICS = ["STR"]
    FORMATS = [["STR", "REG", "REG", "UOFFSET5"]]

    def __init__(self, instruction_value):
        super().__init__(instruction_value)
        self.SR       = get_bits(instruction_value, 10,  8, unsigned=True)
        self.BASER    = get_bits(instruction_value,  7,  5, unsigned=True)
        self.UOFFSET5 = get_bits(instruction_value,  4,  0, unsigned=True)

    def on_execute(self, machine):
        self.address = (machine.REG[self.BASER] + (2 * self.UOFFSET5)) & 0xFFFF
        self.data = machine.REG[self.SR]
        return super().on_execute(machine)

    def on_memory(self, machine):
        if hasattr(machine, 'write_word'):
            machine.write_word(self.address, self.data)
        else:
            machine.MEMORY[self.address] = (self.data >> 8) & 0xFF
            machine.MEMORY[(self.address + 1) & 0xFFFF] = self.data & 0xFF
        return super().on_memory(machine)

    @classmethod
    def s_asemble_method(cls, format_idx, arguments):
        sr = int(arguments[1])
        baser = int(arguments[2])
        uoffset5 = int(arguments[3]) & 0x1F
        val = (cls.OPCODE << 11) | ((sr & 7) << 8) | ((baser & 7) << 5) | uoffset5
        return cls(val)

    def disasemble(self):
        return f"STR R{self.SR}, R{self.BASER}, #{self.UOFFSET5}"


# 13: STRB
class Instruction_STRB(BASE_INSTRUCTION):
    OPCODE = 13
    MNEMONICS = ["STRB"]
    FORMATS = [["STRB", "REG", "REG", "BUOFFSET5"]]

    def __init__(self, instruction_value):
        super().__init__(instruction_value)
        self.SR        = get_bits(instruction_value, 10,  8, unsigned=True)
        self.BASER     = get_bits(instruction_value,  7,  5, unsigned=True)
        self.BUOFFSET5 = get_bits(instruction_value,  4,  0, unsigned=True)

    def on_execute(self, machine):
        self.address = (machine.REG[self.BASER] + self.BUOFFSET5) & 0xFFFF
        self.data = machine.REG[self.SR] & 0xFF
        return super().on_execute(machine)

    def on_memory(self, machine):
        if hasattr(machine, 'write_byte'):
            machine.write_byte(self.address, self.data)
        else:
            machine.MEMORY[self.address] = self.data
        return super().on_memory(machine)

    @classmethod
    def s_asemble_method(cls, format_idx, arguments):
        sr = int(arguments[1])
        baser = int(arguments[2])
        buoffset5 = int(arguments[3]) & 0x1F
        val = (cls.OPCODE << 11) | ((sr & 7) << 8) | ((baser & 7) << 5) | buoffset5
        return cls(val)

    def disasemble(self):
        return f"STRB R{self.SR}, R{self.BASER}, #{self.BUOFFSET5}"


# 14: XOR / NOT
class Instruction_XOR(BASE_INSTRUCTION):
    OPCODE = 14
    MNEMONICS = ["XOR", "NOT"]
    FORMATS = [["XOR", "REG", "REG", "REG"], ["XOR", "REG", "REG", "IMM4"], ["NOT", "REG", "REG"]]

    def __init__(self, instruction_value):
        super().__init__(instruction_value)
        self.DR   = get_bits(instruction_value, 10,  8, unsigned=True)
        self.SR1  = get_bits(instruction_value,  7,  5, unsigned=True)
        self.MODE = get_bits(instruction_value,  4)
        self.SR2  = get_bits(instruction_value,  2,  0, unsigned=True)
        self.IMM4 = get_bits(instruction_value,  3,  0)

    def on_execute(self, machine):
        self.operand_1 = machine.REG[self.SR1]
        if self.MODE == 0:
            self.operand_2 = machine.REG[self.SR2]
        else: # self.MODE == 1 (incluye NOT cuando imm4 es #-1 / 0b1111)
            self.operand_2 = self.IMM4
        self.result = get_bits(self.operand_1 ^ self.operand_2, 15, 0)
        return super().on_execute(machine)

    def on_writeback(self, machine):
        machine.REG[self.DR] = self.result
        machine.NZP = get_nzp(self.result)
        return super().on_writeback(machine)

    @classmethod
    def s_asemble_method(cls, format_idx, arguments):
        dr = int(arguments[1])
        if format_idx == 2 or str(arguments[0]).upper() == "NOT":
            sr = int(arguments[2])
            val = (cls.OPCODE << 11) | ((dr & 7) << 8) | ((sr & 7) << 5) | (1 << 4) | 0xF
        elif format_idx == 0:
            sr1 = int(arguments[2])
            sr2 = int(arguments[3])
            val = (cls.OPCODE << 11) | ((dr & 7) << 8) | ((sr1 & 7) << 5) | (sr2 & 7)
        else: # format_idx == 1
            sr1 = int(arguments[2])
            imm4 = int(arguments[3]) & 0xF
            val = (cls.OPCODE << 11) | ((dr & 7) << 8) | ((sr1 & 7) << 5) | (1 << 4) | imm4
        return cls(val)

    def disasemble(self):
        if self.MODE == 1 and (self.IMM4 & 0xF) == 0xF:
            return f"NOT R{self.DR}, R{self.SR1}"
        if self.MODE == 0:
            return f"XOR R{self.DR}, R{self.SR1}, R{self.SR2}"
        return f"XOR R{self.DR}, R{self.SR1}, #{self.IMM4}"


# 15: LEA
class Instruction_LEA(BASE_INSTRUCTION):
    OPCODE = 15
    MNEMONICS = ["LEA"]
    FORMATS = [["LEA", "REG", "BPCOFFSET8"]]

    def __init__(self, instruction_value):
        super().__init__(instruction_value)
        self.DR         = get_bits(instruction_value, 10,  8, unsigned=True)
        self.BPCOFFSET8 = get_bits(instruction_value,  7,  0)

    def on_execute(self, machine):
        self.address = (machine.PC + 2 + self.BPCOFFSET8) & 0xFFFF
        return super().on_execute(machine)

    def on_writeback(self, machine):
        machine.REG[self.DR] = self.address
        return super().on_writeback(machine)

    @classmethod
    def s_asemble_method(cls, format_idx, arguments):
        dr = int(arguments[1])
        bpcoffset8 = int(arguments[2]) & 0xFF
        val = (cls.OPCODE << 11) | ((dr & 7) << 8) | bpcoffset8
        return cls(val)

    def disasemble(self):
        return f"LEA R{self.DR}, #{self.BPCOFFSET8}"


# 16: RTI
class Instruction_RTI(BASE_INSTRUCTION):
    OPCODE = 16
    MNEMONICS = ["RTI"]
    FORMATS = [["RTI"]]

    def __init__(self, instruction_value):
        super().__init__(instruction_value)

    def on_execute(self, machine):
        if hasattr(machine, 'return_from_interrupt'):
            machine.return_from_interrupt()
        return super().on_execute(machine)

    @classmethod
    def s_asemble_method(cls, format_idx, arguments):
        return cls(cls.OPCODE << 11)

    def disasemble(self):
        return "RTI"


# 17: SEXT / BEXT
class Instruction_SEXT(BASE_INSTRUCTION):
    OPCODE = 17
    MNEMONICS = ["SEXT", "BEXT"]
    FORMATS = [["SEXT", "REG", "REG", "REG"], ["SEXT", "REG", "REG", "UNSH4"], ["BEXT", "REG", "REG"]]

    def __init__(self, instruction_value):
        super().__init__(instruction_value)
        self.DR    = get_bits(instruction_value, 10,  8, unsigned=True)
        self.SR1   = get_bits(instruction_value,  7,  5, unsigned=True)
        self.MODE  = get_bits(instruction_value,  4)
        self.SR2   = get_bits(instruction_value,  2,  0, unsigned=True)
        self.CPSH4 = get_bits(instruction_value,  3,  0, unsigned=True)

    def on_execute(self, machine):
        val = machine.REG[self.SR1]
        n = self.CPSH4 if self.MODE == 1 else (machine.REG[self.SR2] & 0xF)
        if n <= 0:
            self.result = 0
        elif n >= 16:
            self.result = val
        else:
            self.result = get_bits(val, n - 1, 0, unsigned=False)
        return super().on_execute(machine)

    def on_writeback(self, machine):
        machine.REG[self.DR] = self.result
        machine.NZP = get_nzp(self.result)
        return super().on_writeback(machine)

    @classmethod
    def s_asemble_method(cls, format_idx, arguments):
        dr = int(arguments[1])
        if format_idx == 2 or str(arguments[0]).upper() == "BEXT":
            sr = int(arguments[2])
            val = (cls.OPCODE << 11) | ((dr & 7) << 8) | ((sr & 7) << 5) | (1 << 4) | 8
        elif format_idx == 0:
            sr1 = int(arguments[2])
            sr2 = int(arguments[3])
            val = (cls.OPCODE << 11) | ((dr & 7) << 8) | ((sr1 & 7) << 5) | (sr2 & 7)
        else: # format_idx == 1
            sr1 = int(arguments[2])
            cpsh4 = int(arguments[3]) & 0xF
            val = (cls.OPCODE << 11) | ((dr & 7) << 8) | ((sr1 & 7) << 5) | (1 << 4) | cpsh4
        return cls(val)

    def disasemble(self):
        if self.MODE == 1 and self.CPSH4 == 8:
            return f"BEXT R{self.DR}, R{self.SR1}"
        if self.MODE == 1:
            return f"SEXT R{self.DR}, R{self.SR1}, #{self.CPSH4}"
        return f"SEXT R{self.DR}, R{self.SR1}, R{self.SR2}"


# 18: LDI
class Instruction_LDI(BASE_INSTRUCTION):
    OPCODE = 18
    MNEMONICS = ["LDI"]
    FORMATS = [["LDI", "REG", "PCOFFSET8"]]

    def __init__(self, instruction_value):
        super().__init__(instruction_value)
        self.DR        = get_bits(instruction_value, 10,  8, unsigned=True)
        self.PCOFFSET8 = get_bits(instruction_value,  7,  0)

    def on_execute(self, machine):
        self.ptr_address = (machine.PC + 2 + (2 * self.PCOFFSET8)) & 0xFFFF
        return super().on_execute(machine)

    def on_memory(self, machine):
        if hasattr(machine, 'read_word'):
            self.address = machine.read_word(self.ptr_address)
            self.data = machine.read_word(self.address)
        else:
            p_high = machine.MEMORY[self.ptr_address]
            p_low = machine.MEMORY[(self.ptr_address + 1) & 0xFFFF]
            self.address = ((p_high << 8) | p_low) & 0xFFFF
            high = machine.MEMORY[self.address]
            low = machine.MEMORY[(self.address + 1) & 0xFFFF]
            self.data = get_bits((high << 8) | low, 15, 0)
        return super().on_memory(machine)

    def on_writeback(self, machine):
        machine.REG[self.DR] = self.data
        machine.NZP = get_nzp(self.data)
        return super().on_writeback(machine)

    @classmethod
    def s_asemble_method(cls, format_idx, arguments):
        dr = int(arguments[1])
        pcoffset8 = int(arguments[2]) & 0xFF
        val = (cls.OPCODE << 11) | ((dr & 7) << 8) | pcoffset8
        return cls(val)

    def disasemble(self):
        return f"LDI R{self.DR}, #{self.PCOFFSET8}"


# 19: LDIB
class Instruction_LDIB(BASE_INSTRUCTION):
    OPCODE = 19
    MNEMONICS = ["LDIB"]
    FORMATS = [["LDIB", "REG", "BPCOFFSET8"]]

    def __init__(self, instruction_value):
        super().__init__(instruction_value)
        self.DR         = get_bits(instruction_value, 10,  8, unsigned=True)
        self.BPCOFFSET8 = get_bits(instruction_value,  7,  0)

    def on_execute(self, machine):
        self.ptr_address = (machine.PC + 2 + self.BPCOFFSET8) & 0xFFFF
        return super().on_execute(machine)

    def on_memory(self, machine):
        if hasattr(machine, 'read_word') and hasattr(machine, 'read_byte'):
            self.address = machine.read_word(self.ptr_address)
            self.data = machine.read_byte(self.address)
        else:
            p_high = machine.MEMORY[self.ptr_address]
            p_low = machine.MEMORY[(self.ptr_address + 1) & 0xFFFF]
            self.address = ((p_high << 8) | p_low) & 0xFFFF
            self.data = machine.MEMORY[self.address]
        return super().on_memory(machine)

    def on_writeback(self, machine):
        machine.REG[self.DR] = self.data
        machine.NZP = get_nzp(self.data)
        return super().on_writeback(machine)

    @classmethod
    def s_asemble_method(cls, format_idx, arguments):
        dr = int(arguments[1])
        bpcoffset8 = int(arguments[2]) & 0xFF
        val = (cls.OPCODE << 11) | ((dr & 7) << 8) | bpcoffset8
        return cls(val)

    def disasemble(self):
        return f"LDIB R{self.DR}, #{self.BPCOFFSET8}"


# 20: STI
class Instruction_STI(BASE_INSTRUCTION):
    OPCODE = 20
    MNEMONICS = ["STI"]
    FORMATS = [["STI", "REG", "PCOFFSET8"]]

    def __init__(self, instruction_value):
        super().__init__(instruction_value)
        self.SR        = get_bits(instruction_value, 10,  8, unsigned=True)
        self.PCOFFSET8 = get_bits(instruction_value,  7,  0)

    def on_execute(self, machine):
        self.ptr_address = (machine.PC + 2 + (2 * self.PCOFFSET8)) & 0xFFFF
        self.data = machine.REG[self.SR]
        return super().on_execute(machine)

    def on_memory(self, machine):
        if hasattr(machine, 'read_word') and hasattr(machine, 'write_word'):
            self.address = machine.read_word(self.ptr_address)
            machine.write_word(self.address, self.data)
        else:
            p_high = machine.MEMORY[self.ptr_address]
            p_low = machine.MEMORY[(self.ptr_address + 1) & 0xFFFF]
            self.address = ((p_high << 8) | p_low) & 0xFFFF
            machine.MEMORY[self.address] = (self.data >> 8) & 0xFF
            machine.MEMORY[(self.address + 1) & 0xFFFF] = self.data & 0xFF
        return super().on_memory(machine)

    @classmethod
    def s_asemble_method(cls, format_idx, arguments):
        sr = int(arguments[1])
        pcoffset8 = int(arguments[2]) & 0xFF
        val = (cls.OPCODE << 11) | ((sr & 7) << 8) | pcoffset8
        return cls(val)

    def disasemble(self):
        return f"STI R{self.SR}, #{self.PCOFFSET8}"


# 21: STIB
class Instruction_STIB(BASE_INSTRUCTION):
    OPCODE = 21
    MNEMONICS = ["STIB"]
    FORMATS = [["STIB", "REG", "BPCOFFSET8"]]

    def __init__(self, instruction_value):
        super().__init__(instruction_value)
        self.SR         = get_bits(instruction_value, 10,  8, unsigned=True)
        self.BPCOFFSET8 = get_bits(instruction_value,  7,  0)

    def on_execute(self, machine):
        self.ptr_address = (machine.PC + 2 + self.BPCOFFSET8) & 0xFFFF
        self.data = machine.REG[self.SR] & 0xFF
        return super().on_execute(machine)

    def on_memory(self, machine):
        if hasattr(machine, 'read_word') and hasattr(machine, 'write_byte'):
            self.address = machine.read_word(self.ptr_address)
            machine.write_byte(self.address, self.data)
        else:
            p_high = machine.MEMORY[self.ptr_address]
            p_low = machine.MEMORY[(self.ptr_address + 1) & 0xFFFF]
            self.address = ((p_high << 8) | p_low) & 0xFFFF
            machine.MEMORY[self.address] = self.data
        return super().on_memory(machine)

    @classmethod
    def s_asemble_method(cls, format_idx, arguments):
        sr = int(arguments[1])
        bpcoffset8 = int(arguments[2]) & 0xFF
        val = (cls.OPCODE << 11) | ((sr & 7) << 8) | bpcoffset8
        return cls(val)

    def disasemble(self):
        return f"STIB R{self.SR}, #{self.BPCOFFSET8}"


# 22: JMP / RET
class Instruction_JMP(BASE_INSTRUCTION):
    OPCODE = 22
    MNEMONICS = ["JMP", "RET"]
    FORMATS = [["JMP", "REG"], ["RET"]]

    def __init__(self, instruction_value):
        super().__init__(instruction_value)
        self.BASER = get_bits(instruction_value, 7, 5, unsigned=True)

    def on_execute(self, machine):
        self.destination = machine.REG[self.BASER] & 0xFFFF
        return super().on_execute(machine)

    def on_writeback(self, machine):
        if hasattr(machine, 'unconditional_branch'):
            machine.unconditional_branch(self.destination)
        else:
            machine.PC = self.destination
        return super().on_writeback(machine)

    @classmethod
    def s_asemble_method(cls, format_idx, arguments):
        if format_idx == 1 or str(arguments[0]).upper() == "RET":
            baser = 7
        else:
            baser = int(arguments[1])
        val = (cls.OPCODE << 11) | ((baser & 7) << 5)
        return cls(val)

    def disasemble(self):
        if self.BASER == 7:
            return "RET"
        return f"JMP R{self.BASER}"


def _execute_shift(val, n, overflow_bits=False):
    """
    Ejecuta un desplazamiento lógico de 16 bits.
    - n > 0: desplazamiento a izquierda por min(n, 16) bits.
    - n < 0: desplazamiento a derecha por min(-n, 16) bits.
    - overflow_bits=True (SHFO/SHRO): devuelve los bits que sobresalen hacia el
      registro auxiliar adyacente (a la izquierda en LSH, a la derecha en RSH).
    """
    u_val = val & 0xFFFF
    if n > 0:
        shift_amount = min(n, 16)
        carry = (u_val >> (16 - shift_amount)) & 1
        shifted = (u_val << shift_amount) & 0xFFFF
        aux = (u_val >> (16 - shift_amount)) & 0xFFFF
        out_raw = aux if overflow_bits else shifted
        result = get_bits(out_raw, 15, 0)
        shifted_signed = get_bits(shifted, 15, 0)
        overflow = 1 if ((val << shift_amount) != shifted_signed) else 0
    elif n < 0:
        shift_amount = min(-n, 16)
        carry = (u_val >> (shift_amount - 1)) & 1
        shifted = u_val >> shift_amount
        aux = (u_val << (16 - shift_amount)) & 0xFFFF
        out_raw = aux if overflow_bits else shifted
        result = get_bits(out_raw, 15, 0)
        overflow = 0
    else:
        result = 0 if overflow_bits else val
        carry = 0
        overflow = 0
    return result, carry, overflow


# 23: SHF (SHF / LSH / RSH)
class Instruction_SHF(BASE_INSTRUCTION):
    OPCODE = 23
    MNEMONICS = ["SHF", "LSH", "RSH"]
    FORMATS = [["SHF", "REG", "REG", "NSH5"], ["LSH", "REG", "REG", "UNSH4"], ["RSH", "REG", "REG", "CPSH4"]]

    def __init__(self, instruction_value):
        super().__init__(instruction_value)
        self.DR   = get_bits(instruction_value, 10,  8, unsigned=True)
        self.SR   = get_bits(instruction_value,  7,  5, unsigned=True)
        self.NSH5 = get_bits(instruction_value,  4,  0)

    def on_execute(self, machine):
        self.result, self.carry, self.overflow = _execute_shift(
            machine.REG[self.SR], self.NSH5, overflow_bits=False
        )
        return super().on_execute(machine)

    def on_writeback(self, machine):
        machine.REG[self.DR] = self.result
        machine.NZP = get_nzp(self.result)
        machine.OC = get_oc(self.overflow, self.carry)
        return super().on_writeback(machine)

    @classmethod
    def s_asemble_method(cls, format_idx, arguments):
        dr = int(arguments[1])
        sr = int(arguments[2])
        shift_val = int(arguments[3])
        if format_idx == 1 or str(arguments[0]).upper() == "LSH":
            nsh5 = shift_val & 0xF
        elif format_idx == 2 or str(arguments[0]).upper() == "RSH":
            nsh5 = (-shift_val) & 0x1F
        else:
            nsh5 = shift_val & 0x1F
        val = (cls.OPCODE << 11) | ((dr & 7) << 8) | ((sr & 7) << 5) | nsh5
        return cls(val)

    def disasemble(self):
        if self.NSH5 >= 0:
            return f"LSH R{self.DR}, R{self.SR}, #{self.NSH5}"
        return f"SHF R{self.DR}, R{self.SR}, #{self.NSH5}"


# 24: SHFO (SHFO / LSHO / RSHO)
class Instruction_SHFO(BASE_INSTRUCTION):
    OPCODE = 24
    MNEMONICS = ["SHFO", "LSHO", "RSHO"]
    FORMATS = [["SHFO", "REG", "REG", "NSH5"], ["LSHO", "REG", "REG", "UNSH4"], ["RSHO", "REG", "REG", "CPSH4"]]

    def __init__(self, instruction_value):
        super().__init__(instruction_value)
        self.DR   = get_bits(instruction_value, 10,  8, unsigned=True)
        self.SR   = get_bits(instruction_value,  7,  5, unsigned=True)
        self.NSH5 = get_bits(instruction_value,  4,  0)

    def on_execute(self, machine):
        self.result, self.carry, self.overflow = _execute_shift(
            machine.REG[self.SR], self.NSH5, overflow_bits=True
        )
        return super().on_execute(machine)

    def on_writeback(self, machine):
        machine.REG[self.DR] = self.result
        machine.NZP = get_nzp(self.result)
        machine.OC = get_oc(self.overflow, self.carry)
        return super().on_writeback(machine)

    @classmethod
    def s_asemble_method(cls, format_idx, arguments):
        dr = int(arguments[1])
        sr = int(arguments[2])
        shift_val = int(arguments[3])
        if format_idx == 1 or str(arguments[0]).upper() == "LSHO":
            nsh5 = shift_val & 0xF
        elif format_idx == 2 or str(arguments[0]).upper() == "RSHO":
            nsh5 = (-shift_val) & 0x1F
        else:
            nsh5 = shift_val & 0x1F
        val = (cls.OPCODE << 11) | ((dr & 7) << 8) | ((sr & 7) << 5) | nsh5
        return cls(val)

    def disasemble(self):
        if self.NSH5 >= 0:
            return f"LSHO R{self.DR}, R{self.SR}, #{self.NSH5}"
        return f"SHFO R{self.DR}, R{self.SR}, #{self.NSH5}"


# 25: SHR (SHR / SHRO)
class Instruction_SHR(BASE_INSTRUCTION):
    OPCODE = 25
    MNEMONICS = ["SHR", "SHRO"]
    FORMATS = [["SHR", "REG", "REG", "REG"], ["SHRO", "REG", "REG", "REG"]]

    def __init__(self, instruction_value):
        super().__init__(instruction_value)
        self.DR   = get_bits(instruction_value, 10,  8, unsigned=True)
        self.SR1  = get_bits(instruction_value,  7,  5, unsigned=True)
        self.MODE = get_bits(instruction_value,  4) # 0 = SHR, 1 = SHRO
        self.SR2  = get_bits(instruction_value,  2,  0, unsigned=True)

    def on_execute(self, machine):
        n = get_bits(machine.REG[self.SR2], 4, 0) # 5 bits signed from SR2
        self.result, self.carry, self.overflow = _execute_shift(
            machine.REG[self.SR1], n, overflow_bits=(self.MODE == 1)
        )
        return super().on_execute(machine)

    def on_writeback(self, machine):
        machine.REG[self.DR] = self.result
        machine.NZP = get_nzp(self.result)
        machine.OC = get_oc(self.overflow, self.carry)
        return super().on_writeback(machine)

    @classmethod
    def s_asemble_method(cls, format_idx, arguments):
        dr = int(arguments[1])
        sr1 = int(arguments[2])
        sr2 = int(arguments[3])
        mode = 1 if str(arguments[0]).upper() == "SHRO" else 0
        val = (cls.OPCODE << 11) | ((dr & 7) << 8) | ((sr1 & 7) << 5) | (mode << 4) | (sr2 & 7)
        return cls(val)

    def disasemble(self):
        mnem = "SHRO" if self.MODE == 1 else "SHR"
        return f"{mnem} R{self.DR}, R{self.SR1}, R{self.SR2}"


# 26: OR
class Instruction_OR(BASE_INSTRUCTION):
    OPCODE = 26
    MNEMONICS = ["OR"]
    FORMATS = [["OR", "REG", "REG", "REG"], ["OR", "REG", "REG", "IMM4"]]

    def __init__(self, instruction_value):
        super().__init__(instruction_value)
        self.DR   = get_bits(instruction_value, 10,  8, unsigned=True)
        self.SR1  = get_bits(instruction_value,  7,  5, unsigned=True)
        self.MODE = get_bits(instruction_value,  4)
        self.SR2  = get_bits(instruction_value,  2,  0, unsigned=True)
        self.IMM4 = get_bits(instruction_value,  3,  0)

    def on_execute(self, machine):
        self.operand_1 = machine.REG[self.SR1]
        if self.MODE == 0:
            self.operand_2 = machine.REG[self.SR2]
        else: # self.MODE == 1
            self.operand_2 = self.IMM4
        self.result = get_bits(self.operand_1 | self.operand_2, 15, 0)
        return super().on_execute(machine)

    def on_writeback(self, machine):
        machine.REG[self.DR] = self.result
        machine.NZP = get_nzp(self.result)
        return super().on_writeback(machine)

    @classmethod
    def s_asemble_method(cls, format_idx, arguments):
        return _assemble_alu_op(cls, format_idx, arguments)

    def disasemble(self):
        if self.MODE == 0:
            return f"OR R{self.DR}, R{self.SR1}, R{self.SR2}"
        return f"OR R{self.DR}, R{self.SR1}, #{self.IMM4}"


# 27: MUL
class Instruction_MUL(BASE_INSTRUCTION):
    OPCODE = 27
    MNEMONICS = ["MUL"]
    FORMATS = [["MUL", "REG", "REG", "REG"], ["MUL", "REG", "REG", "IMM4"]]

    def __init__(self, instruction_value):
        super().__init__(instruction_value)
        self.DR   = get_bits(instruction_value, 10,  8, unsigned=True)
        self.SR1  = get_bits(instruction_value,  7,  5, unsigned=True)
        self.MODE = get_bits(instruction_value,  4)
        self.SR2  = get_bits(instruction_value,  2,  0, unsigned=True)
        self.IMM4 = get_bits(instruction_value,  3,  0)

    def on_execute(self, machine):
        self.operand_1 = machine.REG[self.SR1]
        if self.MODE == 0:
            self.operand_2 = machine.REG[self.SR2]
        else: # self.MODE == 1
            self.operand_2 = self.IMM4

        product = self.operand_1 * self.operand_2
        self.result = get_bits(product, 15, 0)
        self.overflow = 1 if (product < -32768 or product > 32767) else 0
        u_prod = (self.operand_1 & 0xFFFF) * (self.operand_2 & 0xFFFF)
        self.carry = 1 if (u_prod > 0xFFFF) else 0
        return super().on_execute(machine)

    def on_writeback(self, machine):
        machine.REG[self.DR] = self.result
        machine.NZP = get_nzp(self.result)
        machine.OC = get_oc(self.overflow, self.carry)
        return super().on_writeback(machine)

    @classmethod
    def s_asemble_method(cls, format_idx, arguments):
        return _assemble_alu_op(cls, format_idx, arguments)

    def disasemble(self):
        if self.MODE == 0:
            return f"MUL R{self.DR}, R{self.SR1}, R{self.SR2}"
        return f"MUL R{self.DR}, R{self.SR1}, #{self.IMM4}"


# 28: MULH
class Instruction_MULH(BASE_INSTRUCTION):
    OPCODE = 28
    MNEMONICS = ["MULH"]
    FORMATS = [["MULH", "REG", "REG", "REG"], ["MULH", "REG", "REG", "IMM4"]]

    def __init__(self, instruction_value):
        super().__init__(instruction_value)
        self.DR   = get_bits(instruction_value, 10,  8, unsigned=True)
        self.SR1  = get_bits(instruction_value,  7,  5, unsigned=True)
        self.MODE = get_bits(instruction_value,  4)
        self.SR2  = get_bits(instruction_value,  2,  0, unsigned=True)
        self.IMM4 = get_bits(instruction_value,  3,  0)

    def on_execute(self, machine):
        self.operand_1 = machine.REG[self.SR1]
        if self.MODE == 0:
            self.operand_2 = machine.REG[self.SR2]
        else: # self.MODE == 1
            self.operand_2 = self.IMM4

        product = self.operand_1 * self.operand_2
        self.result = get_bits(product >> 16, 15, 0)
        return super().on_execute(machine)

    def on_writeback(self, machine):
        machine.REG[self.DR] = self.result
        machine.NZP = get_nzp(self.result)
        return super().on_writeback(machine)

    @classmethod
    def s_asemble_method(cls, format_idx, arguments):
        return _assemble_alu_op(cls, format_idx, arguments)

    def disasemble(self):
        if self.MODE == 0:
            return f"MULH R{self.DR}, R{self.SR1}, R{self.SR2}"
        return f"MULH R{self.DR}, R{self.SR1}, #{self.IMM4}"


# 29: DIV
class Instruction_DIV(BASE_INSTRUCTION):
    OPCODE = 29
    MNEMONICS = ["DIV"]
    FORMATS = [["DIV", "REG", "REG", "REG"], ["DIV", "REG", "REG", "IMM4"]]

    def __init__(self, instruction_value):
        super().__init__(instruction_value)
        self.DR   = get_bits(instruction_value, 10,  8, unsigned=True)
        self.SR1  = get_bits(instruction_value,  7,  5, unsigned=True)
        self.MODE = get_bits(instruction_value,  4)
        self.SR2  = get_bits(instruction_value,  2,  0, unsigned=True)
        self.IMM4 = get_bits(instruction_value,  3,  0)

    def on_execute(self, machine):
        self.operand_1 = machine.REG[self.SR1]
        if self.MODE == 0:
            self.operand_2 = machine.REG[self.SR2]
        else: # self.MODE == 1
            self.operand_2 = self.IMM4

        if self.operand_2 == 0:
            self.overflow = 1
            self.result = 0
            if hasattr(machine, 'raise_div_zero_exception'):
                machine.raise_div_zero_exception()
        else:
            self.overflow = 0
            quotient = int(self.operand_1 / self.operand_2)
            self.result = get_bits(quotient, 15, 0)
        return super().on_execute(machine)

    def on_writeback(self, machine):
        machine.REG[self.DR] = self.result
        machine.NZP = get_nzp(self.result)
        machine.OC = (machine.OC & 0b01) | (0b10 if self.overflow else 0b00)
        return super().on_writeback(machine)

    @classmethod
    def s_asemble_method(cls, format_idx, arguments):
        return _assemble_alu_op(cls, format_idx, arguments)

    def disasemble(self):
        if self.MODE == 0:
            return f"DIV R{self.DR}, R{self.SR1}, R{self.SR2}"
        return f"DIV R{self.DR}, R{self.SR1}, #{self.IMM4}"


# 30: MOD
class Instruction_MOD(BASE_INSTRUCTION):
    OPCODE = 30
    MNEMONICS = ["MOD"]
    FORMATS = [["MOD", "REG", "REG", "REG"], ["MOD", "REG", "REG", "IMM4"]]

    def __init__(self, instruction_value):
        super().__init__(instruction_value)
        self.DR   = get_bits(instruction_value, 10,  8, unsigned=True)
        self.SR1  = get_bits(instruction_value,  7,  5, unsigned=True)
        self.MODE = get_bits(instruction_value,  4)
        self.SR2  = get_bits(instruction_value,  2,  0, unsigned=True)
        self.IMM4 = get_bits(instruction_value,  3,  0)

    def on_execute(self, machine):
        self.operand_1 = machine.REG[self.SR1]
        if self.MODE == 0:
            self.operand_2 = machine.REG[self.SR2]
        else: # self.MODE == 1
            self.operand_2 = self.IMM4

        if self.operand_2 == 0:
            self.overflow = 1
            self.result = 0
            if hasattr(machine, 'raise_div_zero_exception'):
                machine.raise_div_zero_exception()
        else:
            self.overflow = 0
            q = int(self.operand_1 / self.operand_2)
            rem = self.operand_1 - (q * self.operand_2)
            self.result = get_bits(rem, 15, 0)
        return super().on_execute(machine)

    def on_writeback(self, machine):
        machine.REG[self.DR] = self.result
        machine.NZP = get_nzp(self.result)
        machine.OC = (machine.OC & 0b01) | (0b10 if self.overflow else 0b00)
        return super().on_writeback(machine)

    @classmethod
    def s_asemble_method(cls, format_idx, arguments):
        # argumentos ya parseados a enteros por el ensamblador
        return _assemble_alu_op(cls, format_idx, arguments)

    def disasemble(self):
        if self.MODE == 0:
            return f"MOD R{self.DR}, R{self.SR1}, R{self.SR2}"
        return f"MOD R{self.DR}, R{self.SR1}, #{self.IMM4}"


# 31: TRAP
class Instruction_TRAP(BASE_INSTRUCTION):
    OPCODE = 31
    MNEMONICS = ["TRAP", "GETC", "OUT", "PUTS", "IN", "PUTSW", "HALT"]
    FORMATS = [["TRAP", "TRAPVEC8"], ["GETC"], ["OUT"], ["PUTS"], ["IN"], ["PUTSW"], ["HALT"]]

    def __init__(self, instruction_value):
        super().__init__(instruction_value)
        self.TRAPVEC8 = get_bits(instruction_value, 7, 0, unsigned=True)

    def on_execute(self, machine):
        self.return_address = (machine.PC + 2) & 0xFFFF
        return super().on_execute(machine)

    def on_writeback(self, machine):
        machine.REG[7] = self.return_address
        if hasattr(machine, 'trap'):
            machine.trap(self.TRAPVEC8)
        return super().on_writeback(machine)

    @classmethod
    def s_asemble_method(cls, format_idx, arguments):
        # argumentos ya parseados a enteros por el ensamblador
        if format_idx == 0:
            trapvec8 = int(arguments[1]) & 0xFF
        else:
            m = str(arguments[0]).upper()
            trap_aliases = {
                "GETC":  0x20,
                "OUT":   0x21,
                "PUTS":  0x22,
                "IN":    0x23,
                "PUTSW": 0x24,
                "HALT":  0x25,
            }
            if m not in trap_aliases:
                raise ValueError(f"Mnemónico no válido para TRAP: '{m}'")
            trapvec8 = trap_aliases[m]

        val = (cls.OPCODE << 11) | trapvec8
        return cls(val)

    def disasemble(self):
        trap_names = {
            0x20: "GETC",
            0x21: "OUT",
            0x22: "PUTS",
            0x23: "IN",
            0x24: "PUTSW",
            0x25: "HALT",
        }
        if self.TRAPVEC8 in trap_names:
            return trap_names[self.TRAPVEC8]
        return f"TRAP x{self.TRAPVEC8:02X}"



# ---------------------------------------------------------------------------
# Aliases y constantes
# ---------------------------------------------------------------------------

Instruction_JSRR = Instruction_JSR
Instruction_NOT  = Instruction_XOR
Instruction_BEXT = Instruction_SEXT
Instruction_RET  = Instruction_JMP
Instruction_LSH  = Instruction_SHF
Instruction_RSH  = Instruction_SHF
Instruction_LSHO = Instruction_SHFO
Instruction_RSHO = Instruction_SHFO
Instruction_SHRO = Instruction_SHR

TRAP_GETC  = 0x20
TRAP_OUT   = 0x21
TRAP_PUTS  = 0x22
TRAP_IN    = 0x23
TRAP_PUTSW = 0x24
TRAP_HALT  = 0x25


# Conjunto de instrucciones reconocidas indexadas por OPCODE (0 a 31)
INSTRUCTIONS = [
    Instruction_BRNZP,  # 0
    Instruction_BROC,   # 1
    Instruction_ADD,    # 2
    Instruction_ADC,    # 3
    Instruction_LD,     # 4
    Instruction_LDB,    # 5
    Instruction_ST,     # 6
    Instruction_STB,    # 7
    Instruction_JSR,    # 8 (JSR / JSRR)
    Instruction_AND,    # 9
    Instruction_LDR,    # 10
    Instruction_LDRB,   # 11
    Instruction_STR,    # 12
    Instruction_STRB,   # 13
    Instruction_XOR,    # 14 (XOR / NOT)
    Instruction_LEA,    # 15
    Instruction_RTI,    # 16
    Instruction_SEXT,   # 17 (SEXT / BEXT)
    Instruction_LDI,    # 18
    Instruction_LDIB,   # 19
    Instruction_STI,    # 20
    Instruction_STIB,   # 21
    Instruction_JMP,    # 22 (JMP / RET)
    Instruction_SHF,    # 23 (SHF / LSH / RSH)
    Instruction_SHFO,   # 24 (SHFO / LSHO / RSHO)
    Instruction_SHR,    # 25 (SHR / SHRO)
    Instruction_OR,     # 26
    Instruction_MUL,    # 27
    Instruction_MULH,   # 28
    Instruction_DIV,    # 29
    Instruction_MOD,    # 30
    Instruction_TRAP,   # 31
]

INSTRUCTIONS_BY_OPCODE = {inst.OPCODE: inst for inst in INSTRUCTIONS}

# Tabla de búsqueda por mnemónico para ensamblado
INSTRUCTION_BY_MNEMONIC = {}
for _inst in INSTRUCTIONS:
    for _m in getattr(_inst, 'MNEMONICS', []):
        INSTRUCTION_BY_MNEMONIC[_m.upper()] = _inst

INSTRUCTION_BY_MNEMONIC["JSRR"] = Instruction_JSR
INSTRUCTION_BY_MNEMONIC["NOT"]  = Instruction_XOR
INSTRUCTION_BY_MNEMONIC["BEXT"] = Instruction_SEXT
INSTRUCTION_BY_MNEMONIC["RET"]  = Instruction_JMP
INSTRUCTION_BY_MNEMONIC["LSH"]  = Instruction_SHF
INSTRUCTION_BY_MNEMONIC["RSH"]  = Instruction_SHF
INSTRUCTION_BY_MNEMONIC["LSHO"] = Instruction_SHFO
INSTRUCTION_BY_MNEMONIC["RSHO"] = Instruction_SHFO
INSTRUCTION_BY_MNEMONIC["SHRO"] = Instruction_SHR


def decode_instruction(instruction_value):
    """
    Decodifica un valor de 16 bits instanciando la clase correspondiente según su OPCODE (bits 15..11).
    """
    opcode = (instruction_value >> 11) & 0x1F
    inst_class = INSTRUCTIONS_BY_OPCODE.get(opcode)
    if inst_class is not None:
        return inst_class(instruction_value)
    raise ValueError(f"Opcode no reconocido: {opcode:#07b} ({opcode}) en instrucción {instruction_value:#018b}")
