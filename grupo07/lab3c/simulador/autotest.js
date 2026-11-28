/*
 * autotest.js - Batería de verificación automática (Sección 11, Grupo 7, Lab 3c - v2)
 * ===================================================================================
 * Tabla de casos de prueba basada en la especificación de las secciones 10 y 11:
 *   11.1 Codificaciones de palabras de 16 bits (ISA base + 11 instrucciones nuevas)
 *   11.2 Imágenes completas en hexadecimal
 *   11.3 Comportamiento de instrucciones, E/S, alineación, DIV0, R6 inicial y HALT
 *   11.4 Métricas por byte (fetch, lectura, escritura, huella)
 *   11.5 Errores esperados del ensamblador y enlace multimódulo (g27_ y .ORIG)
 *   11.6 Programa de integración (main.asm + mcd_mcm.asm)
 */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) {
    const CPU = (root && typeof root.CPU !== 'undefined') ? root.CPU : require('./cpu.js');
    const Assembler = (root && typeof root.Assembler !== 'undefined') ? root.Assembler : require('../ensamblador/assembler.js');
    const EJEMPLOS = (root && typeof root.EJEMPLOS !== 'undefined') ? root.EJEMPLOS : require('../ejemplos/ejemplos.js');
    module.exports = factory(CPU, Assembler, EJEMPLOS);
  } else {
    root.Autotest = factory(root.CPU, root.Assembler, root.EJEMPLOS);
  }
}(typeof globalThis !== 'undefined' ? globalThis : (typeof self !== 'undefined' ? self : this), function (CPU, Assembler, EJEMPLOS) {
  'use strict';

  const hex4 = v => CPU.hex4(v);
  const s16 = v => (v << 16) >> 16;

  function asmOne(src) {
    return Assembler.assemble([{ name: 'test.asm', source: src }]);
  }

  function runAsm(src, opts = {}) {
    const r = asmOne(src);
    if (!r.ok) throw new Error('Error al ensamblar: ' + Assembler.formatMessages(r.errors));
    const cpu = new CPU({ maxInstructions: opts.maxInstructions ?? 5000000 });
    cpu.load(r.bytes);
    if (opts.input) cpu.pushInput(opts.input);
    const status = cpu.run(opts.maxSteps ?? 5000000);
    return { asm: r, cpu, status };
  }

  function symAddr(asm, name) {
    const s = asm.symbols.find(x => x.name.toUpperCase() === name.toUpperCase());
    if (!s) throw new Error(`Símbolo '${name}' no encontrado`);
    return s.addr;
  }

  function assert(cond, msg) {
    if (!cond) throw new Error(msg);
  }

  /* ===== 11.1 Codificaciones ===== */
  // Tercer elemento opcional: true si usa plantilla con dato (T .FILL #0) en vez de T NOP.
  const ENC_CASES = [
    ['ADD R1, R1, #1', 0xD921],
    ['ADD R3, R5, #-8', 0xDBB8],
    ['ADD R1, R2, R3', 0x0943],
    ['ADDI R1, R1, #1', 0xD921],
    ['AND R6, R2, R1', 0x2E41],
    ['AND R0, R0, #0', 0xE000],
    ['ANDI R2, R2, #-16', 0xE250],
    ['NOT R2, R1', 0x4A3F],
    ['SUB R1, R2, R3', 0x5143],
    ['ABS R1, R2', 0x5940],
    ['MUL R1, R2, R3', 0x6943],
    ['MULH R1, R2, R3', 0xA943],
    ['DIV R1, R2, R3', 0xB143],
    ['REM R1, R2, R3', 0xB943],
    ['SHL R1, R2, R3', 0xC143],
    ['SHR R1, R2, R3', 0xC943],
    ['SAR R1, R2, R3', 0xD143],
    ['BRnzp T', 0x0700],
    ['BRz T', 0x0200],
    ['LD R2, T', 0x1201, true],
    ['ST R7, T', 0x1F01, true],
    ['LEA R4, T', 0x7401, true],
    ['JSR T', 0x2400],
    ['RET', 0x60E0],
    ['LDW R3, R6, #1', 0x33C1],
    ['STW R3, R6, #-16', 0x3BD0],
    ['LDB R3, R6, #15', 0x83CF],
    ['LDH R3, R6, #-1', 0x8BDF],
    ['LDBS R1, R2, #0', 0xA140],
    ['STB R1, R2, #1', 0x9141],
    ['STH R1, R2, #1', 0x9941],
    ['TRAP x25', 0x7825],
    ['HALT', 0x7825],
    ['GETC', 0x7820],
    ['OUT', 0x7821],
    ['PUTS', 0x7822],
    ['JSRR R3', 0x2060],
    ['JMP R2', 0x6040],
    ['NOP', 0x0000],
    ['RTI', 0x4000]
  ];

  const TESTS = [];

  for (const [instr, expected, useDataTarget] of ENC_CASES) {
    TESTS.push({
      section: '11.1 Codificaciones',
      name: `${instr} -> x${hex4(expected)}`,
      run() {
        const tail = useDataTarget ? 'T .FILL #0' : 'T NOP';
        const r = asmOne(`.ORIG x3000\n${instr}\n${tail}\n.END`);
        assert(r.ok, Assembler.formatMessages(r.errors));
        const word = r.bytes[2] | (r.bytes[3] << 8);
        assert(word === expected, `Se esperaba x${hex4(expected)}, se obtuvo x${hex4(word)}`);
        return `x${hex4(word)}`;
      }
    });
  }

  /* ===== 11.2 Imagen completa ===== */
  TESTS.push({
    section: '11.2 Imagen completa',
    name: '.ORIG x3000 + ADD R1,R1,#1 + HALT -> 00 30 21 D9 25 78',
    run() {
      const r = asmOne('.ORIG x3000\nADD R1, R1, #1\nHALT\n.END');
      assert(r.ok, Assembler.formatMessages(r.errors));
      const got = Array.from(r.bytes, b => CPU.hex2(b)).join(' ');
      assert(got === '00 30 21 D9 25 78', `Obtenido: ${got}`);
      return got;
    }
  });

  TESTS.push({
    section: '11.2 Imagen completa',
    name: '.ORIG x3000, HALT, S .STRINGZ "ab", ADD R0,R0,#0 (alineación)',
    run() {
      const r = asmOne('.ORIG x3000\nHALT\nS .STRINGZ "ab"\nADD R0, R0, #0\n.END');
      assert(r.ok, Assembler.formatMessages(r.errors));
      const got = Array.from(r.bytes, b => CPU.hex2(b)).join(' ');
      const sAddr = symAddr(r, 'S');
      assert(got === '00 30 25 78 61 62 00 00 00 D8', `Hex obtenido: ${got}`);
      assert(sAddr === 0x3002, `S = x${hex4(sAddr)} (esperado x3002)`);
      return `S=x${hex4(sAddr)}, ${got}`;
    }
  });

  /* ===== 11.3 Comportamiento ===== */
  TESTS.push({
    section: '11.3 Comportamiento',
    name: 'LDB, LDH, LDBS y LDW sobre D .FILL xBEEF',
    run() {
      const { cpu } = runAsm(
        '.ORIG x3000\nLEA R1, D\nLDB R0, R1, #0\nLDH R2, R1, #1\nLDBS R3, R1, #0\nLDW R4, R1, #0\nHALT\nD .FILL xBEEF\n.END'
      );
      assert(cpu.regs[0] === 0x00EF, `R0=x${hex4(cpu.regs[0])}`);
      assert(cpu.regs[2] === 0xBE00, `R2=x${hex4(cpu.regs[2])}`);
      assert(cpu.regs[3] === 0xFFEF, `R3=x${hex4(cpu.regs[3])}`);
      assert(cpu.regs[4] === 0xBEEF, `R4=x${hex4(cpu.regs[4])}`);
      assert(cpu.instrCount === 6, `instr=${cpu.instrCount}`);
      assert(cpu.n && !cpu.z && !cpu.p, 'NZP esperado = N');
      return 'R0=x00EF R2=xBE00 R3=xFFEF R4=xBEEF (6 instr, N)';
    }
  });

  TESTS.push({
    section: '11.3 Comportamiento',
    name: 'LDB preserva mitad alta (R0=xFFFF -> xFFBE)',
    run() {
      const { cpu } = runAsm(
        '.ORIG x3000\nLEA R1, D\nAND R0, R0, #0\nADD R0, R0, #-1\nLDB R0, R1, #1\nHALT\nD .FILL xBEEF\n.END'
      );
      assert(cpu.regs[0] === 0xFFBE, `R0=x${hex4(cpu.regs[0])}`);
      return 'R0=xFFBE';
    }
  });

  TESTS.push({
    section: '11.3 Comportamiento',
    name: 'LDH preserva mitad baja (R0=5 -> xEF05)',
    run() {
      const { cpu } = runAsm(
        '.ORIG x3000\nLEA R1, D\nAND R0, R0, #0\nADD R0, R0, #5\nLDH R0, R1, #0\nHALT\nD .FILL xBEEF\n.END'
      );
      assert(cpu.regs[0] === 0xEF05, `R0=x${hex4(cpu.regs[0])}`);
      return 'R0=xEF05';
    }
  });

  TESTS.push({
    section: '11.3 Comportamiento',
    name: 'STB xFFFF en D+0 y STH x0001 en D+1 -> LDW = x00FF',
    run() {
      const { cpu } = runAsm(
        '.ORIG x3000\nLEA R1, D\nAND R0, R0, #0\nADD R0, R0, #-1\nSTB R0, R1, #0\nAND R0, R0, #0\nADD R0, R0, #1\nSTH R0, R1, #1\nLDW R2, R1, #0\nHALT\nD .FILL #0\n.END'
      );
      assert(cpu.regs[2] === 0x00FF, `R2=x${hex4(cpu.regs[2])}`);
      return 'R2=x00FF';
    }
  });

  TESTS.push({
    section: '11.3 Comportamiento',
    name: 'LDR R0, R1, #1 escala offset por palabra -> x0002',
    run() {
      const { cpu } = runAsm(
        '.ORIG x3000\nLEA R1, D\nLDR R0, R1, #1\nHALT\nD .FILL #1\n.FILL #2\n.END'
      );
      assert(cpu.regs[0] === 0x0002, `R0=x${hex4(cpu.regs[0])}`);
      return 'R0=x0002';
    }
  });

  TESTS.push({
    section: '11.3 Comportamiento',
    name: 'LEA no modifica NZP (ADD #-1 · LEA · BRn OK)',
    run() {
      const { cpu } = runAsm(
        '.ORIG x3000\nAND R0, R0, #0\nADD R0, R0, #-1\nLEA R1, X\nBRn OK\nAND R2, R2, #0\nHALT\nOK AND R2, R2, #0\nADD R2, R2, #7\nHALT\nX .FILL #0\n.END'
      );
      assert(cpu.regs[2] === 7, `R2=${cpu.regs[2]} (no saltó)`);
      return 'Salto tomado';
    }
  });

  TESTS.push({
    section: '11.3 Comportamiento',
    name: 'LD sí actualiza NZP (LD R0, X con #-5 · BRn OK)',
    run() {
      const { cpu } = runAsm(
        '.ORIG x3000\nLD R0, X\nBRn OK\nAND R2, R2, #0\nHALT\nOK AND R2, R2, #0\nADD R2, R2, #7\nHALT\nX .FILL #-5\n.END'
      );
      assert(cpu.regs[2] === 7, `R2=${cpu.regs[2]} (no saltó)`);
      return 'Salto tomado';
    }
  });

  TESTS.push({
    section: '11.3 Comportamiento',
    name: 'JSR guarda retorno en R7 (R0 = x3002)',
    run() {
      const { cpu } = runAsm(
        '.ORIG x3000\nJSR F\nHALT\nF ADD R0, R7, #0\nHALT\n.END'
      );
      assert(cpu.regs[0] === 0x3002, `R0=x${hex4(cpu.regs[0])}`);
      return 'R0=x3002';
    }
  });

  TESTS.push({
    section: '11.3 Comportamiento',
    name: 'GETC · OUT · HALT con entrada Z',
    run() {
      const { cpu } = runAsm('.ORIG x3000\nGETC\nOUT\nHALT\n.END', { input: 'Z' });
      assert(cpu.regs[0] === 0x005A, `R0=x${hex4(cpu.regs[0])}`);
      assert(cpu.output === 'Z', `Salida=${JSON.stringify(cpu.output)}`);
      assert(cpu.instrCount === 3, `instr=${cpu.instrCount}`);
      return 'R0=x005A, consola="Z", 3 instr';
    }
  });

  TESTS.push({
    section: '11.3 Comportamiento',
    name: 'LEA R0, S · PUTS · HALT con "hola" (1 byte/carácter)',
    run() {
      const { cpu } = runAsm('.ORIG x3000\nLEA R0, S\nPUTS\nHALT\nS .STRINGZ "hola"\n.END');
      assert(cpu.output === 'hola', `Salida=${JSON.stringify(cpu.output)}`);
      return 'consola="hola"';
    }
  });

  TESTS.push({
    section: '11.3 Comportamiento',
    name: 'Salto a dirección impar (LEA D · ADD #1 · JMP R0) -> ALIGN x3009',
    run() {
      const { cpu, status } = runAsm('.ORIG x3000\nLEA R0, D\nADD R0, R0, #1\nJMP R0\nHALT\nD .FILL #0\n.END');
      assert(status === 'FAULT', `Estado=${status}`);
      assert(cpu.fault && cpu.fault.kind === 'ALIGN', `Falta=${cpu.fault && cpu.fault.kind}`);
      assert(/x3009/i.test(cpu.fault.message), `Mensaje: ${cpu.fault.message}`);
      assert(cpu.regs[0] === 0x3009, `R0=x${hex4(cpu.regs[0])}`);
      assert(cpu.pc === 0x3006, `PC=x${hex4(cpu.pc)} (esperado x3006)`);
      return `ALIGN: ${cpu.fault.message}`;
    }
  });

  TESTS.push({
    section: '11.3 Comportamiento',
    name: 'LDW sobre dirección impar -> falta ALIGN',
    run() {
      const { cpu, status } = runAsm('.ORIG x3000\nLEA R1, T\nADD R1, R1, #1\nLDW R0, R1, #0\nHALT\nT .FILL #42\n.END');
      assert(status === 'FAULT' && cpu.fault && cpu.fault.kind === 'ALIGN', `Estado=${status}`);
      return `ALIGN: ${cpu.fault.message}`;
    }
  });

  TESTS.push({
    section: '11.3 Comportamiento',
    name: 'RTI -> falta UNSUPPORTED',
    run() {
      const { cpu, status } = runAsm('.ORIG x3000\nRTI\nHALT\n.END');
      assert(status === 'FAULT' && cpu.fault && cpu.fault.kind === 'UNSUPPORTED', `Estado=${status}`);
      return `UNSUPPORTED: ${cpu.fault.message}`;
    }
  });

  TESTS.push({
    section: '11.3 Comportamiento',
    name: 'Carga inicial de R6 = xFE00 (y tras Reiniciar)',
    run() {
      const r = asmOne('.ORIG x3000\nHALT\n.END');
      const cpu = new CPU();
      cpu.load(r.bytes);
      assert(cpu.regs[6] === 0xFE00, `R6 inicial=x${hex4(cpu.regs[6])}`);
      cpu.step();
      cpu.reset();
      assert(cpu.regs[6] === 0xFE00, `R6 tras reset=x${hex4(cpu.regs[6])}`);
      return 'R6=xFE00';
    }
  });

  TESTS.push({
    section: '11.3 Comportamiento',
    name: 'HALT no escribe banner en consola',
    run() {
      const { cpu, status } = runAsm('.ORIG x3000\nHALT\n.END');
      assert(status === 'HALTED', `Estado=${status}`);
      assert(cpu.output === '', `Consola no vacía: ${JSON.stringify(cpu.output)}`);
      return 'Consola limpia ("")';
    }
  });

  TESTS.push({
    section: '11.3 Comportamiento',
    name: 'Bits reservados / opcode libre 31 -> ILLEGAL, RTI reservado -> ILLEGAL, registerInstruction (Paso 5)',
    run() {
      const c = new CPU();
      // ADD con bit 4 = 1 -> 0x0810 -> ILLEGAL (ADD ahora es solo registros)
      c.load(new Uint8Array([0x00, 0x30, 0x10, 0x08]));
      assert(c.step() === 'FAULT' && c.fault.kind === 'ILLEGAL', 'ADD bit4=1 debe dar ILLEGAL');
      // ADD con bit 3 = 1 -> 0x0808 -> ILLEGAL
      c.load(new Uint8Array([0x00, 0x30, 0x08, 0x08]));
      assert(c.step() === 'FAULT' && c.fault.kind === 'ILLEGAL', 'ADD bit3=1 debe dar ILLEGAL');
      // RTI con IR[10:0] != 0 -> 0x4001 -> ILLEGAL
      c.load(new Uint8Array([0x00, 0x30, 0x01, 0x40]));
      assert(c.step() === 'FAULT' && c.fault.kind === 'ILLEGAL', 'RTI con bits reservados != 0 debe dar ILLEGAL');
      // Opcode libre 31 (11111) -> 0xF800
      c.load(new Uint8Array([0x00, 0x30, 0x00, 0xF8]));
      assert(c.step() === 'FAULT' && c.fault.kind === 'ILLEGAL', 'Opcode libre 31 debe dar ILLEGAL');
      assert(c.disasm(0xF800, 0x3000) === '.WORD xF800', 'Opcode libre desensambla como .WORD xF800');
      // registerInstruction falla en ocupado (op=1) y funciona en libre (op=31)
      let failedBusy = false;
      try { c.registerInstruction(1, 'DUP', () => {}); } catch (_e) { failedBusy = true; }
      assert(failedBusy, 'Debe fallar al registrar en opcode ocupado');
      c.registerInstruction(31, 'TEST5', (cpu, ir) => { cpu._wreg((ir >> 8) & 7, 99); }, () => 'TEST5');
      assert(c.metrics().opNames[31] === 'TEST5', 'opNames[31] debe mostrar TEST5');
      assert(c.disasm(0xF800, 0x3000) === 'TEST5', 'disasm debe usar la función registrada');
      return 'ILLEGAL (bit4/bit3/RTI/op31), .WORD xF800 y registerInstruction(31) OK';
    }
  });

  TESTS.push({
    section: '11.3 Comportamiento',
    name: 'Desensamblador único: NOP, RET, HALT, LEA/LD (×4), nuevas instrucciones y .WORD',
    run() {
      assert(CPU.disassemble(0x0000, 0x3000) === 'NOP', 'NOP');
      assert(CPU.disassemble(0x60E0, 0x3000) === 'RET', 'RET');
      assert(CPU.disassemble(0x7825, 0x3000) === 'HALT', 'HALT');
      assert(CPU.disassemble(0x7403, 0x3000) === 'LEA R4, x300C', 'LEA escalado x4');
      assert(CPU.disassemble(0x1201, 0x3000) === 'LD R2, x3004', 'LD escalado x4');
      assert(CPU.disassemble(0xB322, 0x3000) === 'DIV R3, R1, R2', 'DIV');
      assert(CPU.disassemble(0x5940, 0x3000) === 'ABS R1, R2', 'ABS');
      assert(CPU.disassemble(0xD921, 0x3000) === 'ADDI R1, R1, #1', 'ADDI');
      assert(CPU.disassemble(0xC322, 0x3000) === 'SHL R3, R1, R2', 'SHL');
      return 'NOP, RET, HALT, LEA/LD x4, DIV, ABS, ADDI, SHL verificados';
    }
  });

  /* ===== 11.3 Comportamiento: instrucciones nuevas y alcance ×4 ===== */
  TESTS.push({
    section: '11.3 Comportamiento',
    name: 'DIV/REM con signo (-7 y 2) -> R3=xFFFD (-3), R4=xFFFF (-1), 5 instr',
    run() {
      const { cpu } = runAsm('.ORIG x3000\nADD R1, R0, #-7\nADD R2, R0, #2\nDIV R3, R1, R2\nREM R4, R1, R2\nHALT\n.END');
      assert(cpu.regs[3] === 0xFFFD, `R3=x${hex4(cpu.regs[3])}`);
      assert(cpu.regs[4] === 0xFFFF, `R4=x${hex4(cpu.regs[4])}`);
      assert(cpu.instrCount === 5, `instr=${cpu.instrCount}`);
      return 'R3=xFFFD (-3), R4=xFFFF (-1), 5 instr';
    }
  });

  TESTS.push({
    section: '11.3 Comportamiento',
    name: 'DIV/REM con signo (7 y -2) -> R3=xFFFD (-3), R4=x0001',
    run() {
      const { cpu } = runAsm('.ORIG x3000\nADD R1, R0, #7\nADD R2, R0, #-2\nDIV R3, R1, R2\nREM R4, R1, R2\nHALT\n.END');
      assert(cpu.regs[3] === 0xFFFD, `R3=x${hex4(cpu.regs[3])}`);
      assert(cpu.regs[4] === 0x0001, `R4=x${hex4(cpu.regs[4])}`);
      return 'R3=xFFFD (-3), R4=x0001';
    }
  });

  TESTS.push({
    section: '11.3 Comportamiento',
    name: 'MUL y MULH (20000 x 20000) -> R2=x8400, R3=x17D7',
    run() {
      const { cpu } = runAsm('.ORIG x3000\nLD R1, A\nMUL R2, R1, R1\nMULH R3, R1, R1\nHALT\nA .FILL #20000\n.END');
      assert(cpu.regs[2] === 0x8400, `R2=x${hex4(cpu.regs[2])}`);
      assert(cpu.regs[3] === 0x17D7, `R3=x${hex4(cpu.regs[3])}`);
      return 'R2=x8400, R3=x17D7';
    }
  });

  TESTS.push({
    section: '11.3 Comportamiento',
    name: 'MUL y MULH negativos (-3 x 5) -> R3=xFFF1, R4=xFFFF',
    run() {
      const { cpu } = runAsm('.ORIG x3000\nADD R1, R0, #-3\nADD R2, R0, #5\nMUL R3, R1, R2\nMULH R4, R1, R2\nHALT\n.END');
      assert(cpu.regs[3] === 0xFFF1, `R3=x${hex4(cpu.regs[3])}`);
      assert(cpu.regs[4] === 0xFFFF, `R4=x${hex4(cpu.regs[4])}`);
      return 'R3=xFFF1, R4=xFFFF';
    }
  });

  TESTS.push({
    section: '11.3 Comportamiento',
    name: 'SUB con banderas (3 - 5) -> R3=xFFFE, N=1',
    run() {
      const { cpu } = runAsm('.ORIG x3000\nADD R1, R0, #3\nADD R2, R0, #5\nSUB R3, R1, R2\nHALT\n.END');
      assert(cpu.regs[3] === 0xFFFE, `R3=x${hex4(cpu.regs[3])}`);
      assert(cpu.n && !cpu.z && !cpu.p, 'NZP esperado = N');
      return 'R3=xFFFE, N=1';
    }
  });

  TESTS.push({
    section: '11.3 Comportamiento',
    name: 'ABS (-5 -> 5 y x8000 -> x8000 sin falta)',
    run() {
      const { cpu } = runAsm('.ORIG x3000\nADD R1, R0, #-5\nABS R2, R1\nLD R3, M\nABS R4, R3\nHALT\nM .FILL x8000\n.END');
      assert(cpu.regs[2] === 5, `R2=${cpu.regs[2]}`);
      assert(cpu.regs[4] === 0x8000, `R4=x${hex4(cpu.regs[4])}`);
      return 'R2=5, R4=x8000';
    }
  });

  TESTS.push({
    section: '11.3 Comportamiento',
    name: 'SHL, SHR y SAR -> R3=x4000, R4=xC000, R6=x0010',
    run() {
      const { cpu } = runAsm('.ORIG x3000\nLD R1, V\nADD R2, R0, #1\nSHR R3, R1, R2\nSAR R4, R1, R2\nADD R5, R0, #4\nADD R2, R0, #1\nSHL R6, R2, R5\nHALT\nV .FILL x8000\n.END');
      assert(cpu.regs[3] === 0x4000, `R3=x${hex4(cpu.regs[3])}`);
      assert(cpu.regs[4] === 0xC000, `R4=x${hex4(cpu.regs[4])}`);
      assert(cpu.regs[6] === 0x0010, `R6=x${hex4(cpu.regs[6])}`);
      return 'R3=x4000, R4=xC000, R6=x0010';
    }
  });

  TESTS.push({
    section: '11.3 Comportamiento',
    name: 'Desplazamiento usa solo 4 bits (17 & 15 = 1) -> R3=x0002',
    run() {
      const { cpu } = runAsm('.ORIG x3000\nADD R1, R0, #1\nADD R2, R0, #15\nADD R2, R2, #2\nSHL R3, R1, R2\nHALT\n.END');
      assert(cpu.regs[3] === 0x0002, `R3=x${hex4(cpu.regs[3])}`);
      return 'R3=x0002';
    }
  });

  TESTS.push({
    section: '11.3 Comportamiento',
    name: 'División por cero (DIV) -> falta DIV0',
    run() {
      const { cpu, status } = runAsm('.ORIG x3000\nADD R1, R0, #5\nDIV R2, R1, R0\nHALT\n.END');
      assert(status === 'FAULT', `Estado=${status}`);
      assert(cpu.fault && cpu.fault.kind === 'DIV0', `Falta=${cpu.fault && cpu.fault.kind}`);
      return `DIV0: ${cpu.fault.message}`;
    }
  });

  TESTS.push({
    section: '11.3 Comportamiento',
    name: 'Resto por cero (REM) -> falta DIV0',
    run() {
      const { cpu, status } = runAsm('.ORIG x3000\nADD R1, R0, #5\nREM R2, R1, R0\nHALT\n.END');
      assert(status === 'FAULT', `Estado=${status}`);
      assert(cpu.fault && cpu.fault.kind === 'DIV0', `Falta=${cpu.fault && cpu.fault.kind}`);
      return `DIV0: ${cpu.fault.message}`;
    }
  });

  TESTS.push({
    section: '11.3 Comportamiento',
    name: 'ADDI/ANDI (alias imm5) -> R1=x000F, R2=x0000',
    run() {
      const { cpu } = runAsm('.ORIG x3000\nADD R1, R0, #15\nAND R2, R1, #-16\nHALT\n.END');
      assert(cpu.regs[1] === 0x000F, `R1=x${hex4(cpu.regs[1])}`);
      assert(cpu.regs[2] === 0x0000, `R2=x${hex4(cpu.regs[2])}`);
      return 'R1=x000F, R2=x0000';
    }
  });

  TESTS.push({
    section: '11.3 Comportamiento',
    name: 'LD con alcance ×4 (~444 bytes) -> R0=77, 2 instr',
    run() {
      const { cpu } = runAsm('.ORIG x3000\nLD R0, D\nHALT\n.BLKB 440\nD .FILL #77\n.END');
      assert(cpu.regs[0] === 77, `R0=${cpu.regs[0]}`);
      assert(cpu.instrCount === 2, `instr=${cpu.instrCount}`);
      return 'R0=77, 2 instr';
    }
  });

  TESTS.push({
    section: '11.3 Comportamiento',
    name: 'Alineación automática a 4 (B1 .BYTE #1 · D .FILL #5) -> D=x3008, R0=5',
    run() {
      const { asm, cpu } = runAsm('.ORIG x3000\nLD R0, D\nHALT\nB1 .BYTE #1\nD .FILL #5\n.END');
      const dAddr = symAddr(asm, 'D');
      assert((dAddr & 3) === 0 && dAddr === 0x3008, `D=x${hex4(dAddr)} (esperado x3008)`);
      assert(cpu.regs[0] === 5, `R0=${cpu.regs[0]}`);
      return `D=x${hex4(dAddr)}, R0=5`;
    }
  });

  /* ===== 11.4 Métricas ===== */
  TESTS.push({
    section: '11.4 Métricas',
    name: 'LEA R1,D · LDW R0,R1,#0 · STB R0,R1,#3 · HALT (4 instr, 12/11/12, 1 rd, 1 wr)',
    run() {
      const { cpu } = runAsm(
        '.ORIG x3000\nLEA R1, D\nLDW R0, R1, #0\nSTB R0, R1, #3\nHALT\nD .FILL x1234\n.FILL #0\n.END'
      );
      const m = cpu.metrics();
      assert(m.instructions === 4, `Instr=${m.instructions}`);
      assert(m.loadedBytes === 12, `Cargados=${m.loadedBytes}`);
      assert(m.touchedBytes === 11, `Tocados=${m.touchedBytes}`);
      assert(m.footprintBytes === 12, `Huella=${m.footprintBytes}`);
      assert(m.memReads === 1, `Lecturas=${m.memReads}`);
      assert(m.memWrites === 1, `Escrituras=${m.memWrites}`);
      assert(m.codeBytesFetched === 8, `Fetch=${m.codeBytesFetched}`);
      assert(m.dataBytesRead === 2, `DataRead=${m.dataBytesRead}`);
      assert(m.dataBytesWritten === 1, `DataWrite=${m.dataBytesWritten}`);
      return '4 instr · 12 cargados · 11 tocados (8f+2r+1w) · huella 12 · 1 rd · 1 wr';
    }
  });

  /* ===== 11.5 Errores esperados del ensamblador y enlazador ===== */
  const ERR_CASES = [
    ['ADD R2, R0, #-17 -> imm5 fuera de rango', [{ name: 't.asm', source: '.ORIG x3000\nADD R2, R0, #-17\n.END' }], /imm5.*fuera de rango/i],
    ['ADDI R1, R2, R3 -> ADDI espera un inmediato', [{ name: 't.asm', source: '.ORIG x3000\nADDI R1, R2, R3\n.END' }], /ADDI espera un inmediato/i],
    ['LDB R0, R1, #16 -> offset5 fuera de rango', [{ name: 't.asm', source: '.ORIG x3000\nLDB R0, R1, #16\n.END' }], /offset5.*fuera de rango/i],
    ['LEA R0, F a >512 bytes (.BLKB 600) -> fuera de alcance', [{ name: 't.asm', source: '.ORIG x3000\nLEA R0, F\n.BLKB 600\nF .FILL #1\n.END' }], /fuera de alcance/i],
    ['LD R0, T con T en código -> error etiqueta en código', [{ name: 't.asm', source: '.ORIG x3000\nLD R0, T\nT HALT\n.END' }], /código/i],
    ['A NOP y a NOP en mismo módulo -> etiqueta duplicada', [{ name: 't.asm', source: '.ORIG x3000\nA NOP\na NOP\n.END' }], /duplicada/i],
    ['JSR OTRO sin .EXTERNAL -> falta declarar .EXTERNAL', [{ name: 'a.asm', source: '.ORIG x3000\nJSR OTRO\n.END' }, { name: 'b.asm', source: 'OTRO RET\n.END' }], /falta declarar \.EXTERNAL/i],
    ['.EXTERNAL nada-SALUDAR -> módulo no existe', [{ name: 'a.asm', source: '.ORIG x3000\n.EXTERNAL nada-SALUDAR\nNOP\n.END' }], /módulo 'nada' no existe/i]
  ];

  for (const [name, mods, re] of ERR_CASES) {
    TESTS.push({
      section: '11.5 Errores del ensamblador',
      name,
      run() {
        const r = Assembler.assemble(mods);
        assert(!r.ok && r.errors.length > 0, 'Debió fallar el ensamblado');
        const msg = r.errors.map(e => e.message).join(' | ');
        assert(re.test(msg), `Mensaje inesperado: ${msg}`);
        return msg;
      }
    });
  }

  TESTS.push({
    section: '11.5 Errores del ensamblador',
    name: 'Enlazador: .EXTERNAL util-F resuelve archivo g27_util.asm sin errores',
    run() {
      const r = Assembler.assemble([
        { name: 'a.asm', source: '.ORIG x3000\n.EXTERNAL util-F\nJSR util-F\nHALT\n.END' },
        { name: 'g27_util.asm', source: 'F RET\n.END' }
      ]);
      assert(r.ok, Assembler.formatMessages(r.errors));
      const fAddr = symAddr(r, 'F');
      assert(fAddr === 0x3004, `F=x${hex4(fAddr)} (esperado x3004)`);
      return `Enlazado OK (F=x${hex4(fAddr)})`;
    }
  });

  TESTS.push({
    section: '11.5 Errores del ensamblador',
    name: 'Enlazador: g9_a.asm con .EXTERNAL b-F resuelve contra g9_b.asm',
    run() {
      const r = Assembler.assemble([
        { name: 'g9_a.asm', source: '.ORIG x3000\n.EXTERNAL b-F\nJSR b-F\nHALT\n.END' },
        { name: 'g9_b.asm', source: 'F RET\n.END' }
      ]);
      assert(r.ok, Assembler.formatMessages(r.errors));
      const fAddr = symAddr(r, 'F');
      assert(fAddr === 0x3004, `F=x${hex4(fAddr)} (esperado x3004)`);
      return `Enlazado OK (F=x${hex4(fAddr)})`;
    }
  });

  TESTS.push({
    section: '11.5 Errores del ensamblador',
    name: 'Enlazador: .ORIG x4000 en segundo módulo se ignora con advertencia',
    run() {
      const r = Assembler.assemble([
        { name: 'a.asm', source: '.ORIG x3000\nHALT\n.END' },
        { name: 'b.asm', source: '.ORIG x4000\nF RET\n.END' }
      ]);
      assert(r.ok, Assembler.formatMessages(r.errors));
      assert(r.warnings.some(w => /\.ORIG ignorado/i.test(w.message)), 'Debe advertir que .ORIG fue ignorado');
      const fAddr = symAddr(r, 'F');
      assert(fAddr === 0x3002, `F=x${hex4(fAddr)} (debe quedar a continuación en x3002, no en x4000)`);
      return `Advertencia emitida, F=x${hex4(fAddr)}`;
    }
  });

  /* ===== 11.6 Programa de integración (main + mcd_mcm) ===== */
  function modsWithInputs(a, b) {
    const m = EJEMPLOS['main.asm']
      .replace(/DATO_A\s+\.FILL\s+#?\S+/, `DATO_A      .FILL #${a}`)
      .replace(/DATO_B\s+\.FILL\s+#?\S+/, `DATO_B      .FILL #${b}`);
    return [
      { name: 'main.asm', source: m },
      { name: 'mcd_mcm.asm', source: EJEMPLOS['mcd_mcm.asm'] }
    ];
  }

  TESTS.push({
    section: '11.6 Integración (MCD/MCM)',
    name: 'Ensamblado multimódulo: 126 bytes desde x3000 hasta x307D',
    run() {
      const r = Assembler.assemble(modsWithInputs(48, 180));
      assert(r.ok, Assembler.formatMessages(r.errors));
      assert(r.size === 126, `Tamaño=${r.size}`);
      assert(r.origin === 0x3000, `Origen=x${hex4(r.origin)}`);
      assert(r.endAddr - 1 === 0x307D, `Fin=x${hex4(r.endAddr - 1)}`);
      return '126 bytes (x3000..x307D)';
    }
  });

  const INT_CASES = [
    [48, 180, 12, 720, 44, 100, 126, 126],
    [1000, 999, 1, -32768, 35, null, null, null],
    [32767, 1, 1, 32767, 32, null, null, null]
  ];

  for (const [a, b, expMcd, expMcm, expInstr, expTouched, expLoaded, expFoot] of INT_CASES) {
    TESTS.push({
      section: '11.6 Integración (MCD/MCM)',
      name: `DATO_A=${a}, DATO_B=${b} -> MCD=${expMcd}, MCM=${expMcm}, ${expInstr} instr`,
      run() {
        const r = Assembler.assemble(modsWithInputs(a, b));
        assert(r.ok, Assembler.formatMessages(r.errors));
        const cpu = new CPU({ maxInstructions: 5000000 });
        cpu.load(r.bytes);
        const st = cpu.run(5000000);
        assert(st === 'HALTED', `Estado=${st}`);
        const gotMcd = s16(cpu.peek16(symAddr(r, 'RES_MCD')));
        const gotMcm = s16(cpu.peek16(symAddr(r, 'RES_MCM')));
        const m = cpu.metrics();
        assert(gotMcd === expMcd, `RES_MCD=${gotMcd} (esperado ${expMcd})`);
        assert(gotMcm === expMcm, `RES_MCM=${gotMcm} (esperado ${expMcm})`);
        assert(cpu.output === 'MCD y MCM calculados\n', `Consola=${JSON.stringify(cpu.output)}`);
        assert(m.instructions === expInstr, `Instr=${m.instructions} (esperado ${expInstr})`);
        if (expTouched !== null) assert(m.touchedBytes === expTouched, `Tocados=${m.touchedBytes}`);
        if (expLoaded !== null) assert(m.loadedBytes === expLoaded, `Cargados=${m.loadedBytes}`);
        if (expFoot !== null) assert(m.footprintBytes === expFoot, `Huella=${m.footprintBytes}`);
        return `MCD=${gotMcd}, MCM=${gotMcm}, ${m.instructions} instr` +
          (expTouched !== null ? `, ${m.touchedBytes} tocados, ${m.loadedBytes} cargados, huella ${m.footprintBytes}` : '');
      }
    });
  }

  /* ===== 11.7 Importación (.zip / lotes .asm) ===== */
  TESTS.push({
    section: '11.7 Importación (.zip / .asm)',
    name: 'Ignora archivos no-.asm, __MACOSX y ocultos (con punto)',
    run() {
      const res = Assembler.processModuleEntries([
        { ruta: '__MACOSX/proj/._main.asm', texto: '; basura mac' },
        { ruta: '__MACOSX/lib/util.asm', texto: '; basura mac' },
        { ruta: 'proj/.DS_Store', texto: 'bin' },
        { ruta: 'proj/.oculto.asm', texto: '; oculto' },
        { ruta: 'proj/README.md', texto: '# doc' },
        { ruta: 'proj/datos.txt', texto: '123' },
        { ruta: 'proj/main.ASM', texto: '.ORIG x3000\nHALT\n.END' },
        { ruta: 'proj/lib/math.asm', texto: 'F RET\n.END' }
      ]);
      assert(res.modules.length === 2, `Módulos=${res.modules.length} (esperado 2)`);
      assert(res.ignored === 6, `Ignorados=${res.ignored} (esperado 6)`);
      assert(res.main && res.main.moduleName === 'main', `Main=${res.main && res.main.moduleName}`);
      assert(res.modules[1].moduleName === 'math', `Segundo=${res.modules[1].moduleName}`);
      return `2 módulos, 6 ignorados, main=${res.main.moduleName}`;
    }
  });

  TESTS.push({
    section: '11.7 Importación (.zip / .asm)',
    name: 'Detecta main más cercano a la raíz y avisa si no existe ningún main',
    run() {
      const r1 = Assembler.processModuleEntries([
        { path: 'sub/profundo/main_viejo.asm', text: '.ORIG x3000\nHALT\n.END' },
        { path: 'main_app.asm', text: '.ORIG x3000\nHALT\n.END' },
        { path: 'lib/aux.asm', text: 'A RET\n.END' }
      ]);
      assert(r1.main && r1.main.moduleName === 'main_app', `Main=${r1.main && r1.main.moduleName}`);
      assert(r1.modules[0] === r1.main, 'El main debe quedar primero');
      assert(r1.warnings.length === 0, `Avisos inesperados: ${r1.warnings.join('; ')}`);

      const r2 = Assembler.processModuleEntries([
        { path: 'lib/zeta.asm', text: 'Z RET\n.END' },
        { path: 'lib/alfa.asm', text: 'A RET\n.END' }
      ]);
      assert(r2.main && r2.main.moduleName === 'alfa', `Fallback=${r2.main && r2.main.moduleName}`);
      assert(r2.warnings.some(w => /main/i.test(w)), 'Debe avisar que no se encontró main');
      return `Con main -> main_app; sin main -> alfa + aviso`;
    }
  });

  TESTS.push({
    section: '11.7 Importación (.zip / .asm)',
    name: 'Nombres duplicados en carpetas distintas: conserva el primero y avisa',
    run() {
      const res = Assembler.processModuleEntries([
        { path: 'main.asm', text: '.ORIG x3000\nHALT\n.END' },
        { path: 'dir1/util.asm', text: 'UNO RET\n.END' },
        { path: 'dir2/UTIL.asm', text: 'DOS RET\n.END' }
      ]);
      assert(res.modules.length === 2, `Módulos=${res.modules.length} (esperado 2)`);
      assert(res.ignored === 1, `Ignorados=${res.ignored} (esperado 1)`);
      const util = res.modules.find(m => m.moduleName.toLowerCase() === 'util');
      assert(util && util.source.includes('UNO'), 'Debe conservar el primer archivo encontrado');
      assert(res.warnings.some(w => /duplicado/i.test(w)), 'Debe emitir aviso de duplicado');
      return `Conservó dir1/util.asm + aviso`;
    }
  });

  TESTS.push({
    section: '11.7 Importación (.zip / .asm)',
    name: 'Modo reemplazar vs agregar (sobrescribe coincidencias y conserva el resto)',
    run() {
      const existing = [
        { name: 'main.asm', source: 'OLD_MAIN' },
        { name: 'viejo.asm', source: 'VIEJO' },
        { name: 'util.asm', source: 'UTIL_V1' }
      ];
      const imported = Assembler.processModuleEntries([
        { path: 'main.asm', text: 'NEW_MAIN' },
        { path: 'lib/UTIL.asm', text: 'UTIL_V2' },
        { path: 'lib/nuevo.asm', text: 'NUEVO' }
      ]);

      const rep = Assembler.mergeModuleLists(existing, imported, 'replace');
      assert(rep.modules.length === 3, `Replace len=${rep.modules.length}`);
      assert(!rep.modules.some(m => m.name === 'viejo.asm'), 'Replace debe descartar módulos anteriores');
      assert(rep.modules[0].source === 'NEW_MAIN', 'Replace debe poner el nuevo main primero');

      const add = Assembler.mergeModuleLists(existing, imported, 'add');
      assert(add.modules.length === 4, `Add len=${add.modules.length} (esperado 4)`);
      const byName = Object.fromEntries(add.modules.map(m => [m.name.toLowerCase(), m.source]));
      assert(byName['main.asm'] === 'NEW_MAIN', 'Add debe sobrescribir main');
      assert(byName['viejo.asm'] === 'VIEJO', 'Add debe conservar viejo.asm');
      assert(byName['util.asm'] === 'UTIL_V2', 'Add debe sobrescribir util (sin distinguir mayúsculas)');
      assert(byName['nuevo.asm'] === 'NUEVO', 'Add debe agregar nuevo.asm');
      return `replace=3 módulos, add=4 módulos (sobrescribió main y util)`;
    }
  });

  /* ===== 11.8 Avisos de compatibilidad LC-3 ===== */
  TESTS.push({
    section: '11.8 Avisos LC-3',
    name: 'Aviso 1: LDR/LDW/STR/STW con base cargada desde .STRINGZ',
    run() {
      const src = [
        '.ORIG x3000',
        'LEA R1, MSG',
        'LDR R0, R1, #0',
        'HALT',
        'MSG .STRINGZ "hola"',
        '.END'
      ].join('\n');
      const r = Assembler.assemble([{ name: 'str_warn.asm', source: src }]);
      assert(r.ok, 'Debe ensamblar sin errores (solo aviso)');
      const w = r.warnings.find(x => x.message === 'texto: usar LDB/STB, un byte por carácter');
      assert(!!w, `Falta aviso esperado. Avisos: ${Assembler.formatMessages(r.warnings)}`);
      assert(w.module === 'str_warn.asm' && w.line === 3, `Ubicación=${w.module}:${w.line}`);
      return `${w.module}:${w.line}: ${w.message}`;
    }
  });

  TESTS.push({
    section: '11.8 Avisos LC-3',
    name: 'Aviso 2: ADD/ADDI sobre R6 con inmediato impar',
    run() {
      const src = [
        '.ORIG x3000',
        'ADD R6, R6, #-1',
        'ADDI R6, R6, #3',
        'ADD R6, R6, #-2',
        'HALT',
        '.END'
      ].join('\n');
      const r = Assembler.assemble([{ name: 'pila.asm', source: src }]);
      assert(r.ok, 'Debe ensamblar sin errores');
      const ws = r.warnings.filter(x => x.message === 'el puntero de pila debe moverse de a 2 bytes');
      assert(ws.length === 2, `Esperados 2 avisos de pila, obtenidos ${ws.length}`);
      assert(ws[0].line === 2 && ws[1].line === 3, `Líneas=${ws.map(x => x.line).join(',')}`);
      return `Detectados en líneas 2 y 3 (ignora #-2)`;
    }
  });

  TESTS.push({
    section: '11.8 Avisos LC-3',
    name: 'Aviso 3: ADD Rx,Rx,#1 o #-1 cuando Rx es base de LDR/LDW/STR/STW en el mismo bloque',
    run() {
      const src = [
        '.ORIG x3000',
        'LDR R0, R1, #0',
        'ADD R1, R1, #1',
        'ADD R2, R2, #-1',
        'STW R0, R2, #0',
        'ADD R3, R3, #1',
        'HALT',
        '.END'
      ].join('\n');
      const r = Assembler.assemble([{ name: 'ptr.asm', source: src }]);
      assert(r.ok, 'Debe ensamblar sin errores');
      const ws = r.warnings.filter(x => x.message === 'posible puntero a palabras: debería avanzar 2');
      assert(ws.length === 2, `Esperados 2 avisos, obtenidos ${ws.length}: ${Assembler.formatMessages(r.warnings)}`);
      assert(ws[0].line === 3 && ws[1].line === 4, `Líneas=${ws.map(x => x.line).join(',')}`);
      return `Detectados en líneas 3 y 4 (ignora R3 sin acceso a memoria)`;
    }
  });

  TESTS.push({
    section: '11.8 Avisos LC-3',
    name: 'Aviso 4: ADD Rb,Rb,Ri seguido de LDW/STW/LDR/STR con Rb desde LEA/LD',
    run() {
      const src = [
        '.ORIG x3000',
        'LEA R1, TAB',
        'ADD R1, R1, R2',
        'LDW R0, R1, #0',
        'LEA R3, TAB',
        'ADD R4, R4, R4',
        'ADD R3, R3, R4',
        'LDW R0, R3, #0',
        'HALT',
        'TAB .BLKW #4',
        '.END'
      ].join('\n');
      const r = Assembler.assemble([{ name: 'tabla.asm', source: src }]);
      assert(r.ok, 'Debe ensamblar sin errores');
      const ws = r.warnings.filter(x => x.message === 'índice de tabla: ¿falta multiplicar por 2?');
      assert(ws.length === 1, `Esperado 1 aviso, obtenidos ${ws.length}: ${Assembler.formatMessages(r.warnings)}`);
      assert(ws[0].line === 3, `Línea=${ws[0].line} (esperado 3)`);
      return `Detectado en línea 3 (no avisa si R4 ya se multiplicó por 2)`;
    }
  });

  TESTS.push({
    section: '11.8 Avisos LC-3',
    name: 'Comentario "; @ok" silencia avisos en esa línea (con o sin texto después)',
    run() {
      const src = [
        '.ORIG x3000',
        'LEA R1, MSG',
        'LDR R0, R1, #0 ; @ok lectura de 2 bytes intencional',
        'ADD R6, R6, #-1 ; @ok',
        'LDR R0, R2, #0',
        'ADD R2, R2, #1 ; @ok puntero de bytes',
        'LEA R3, TAB',
        'ADD R3, R3, R4 ; @ok R4 ya viene en bytes',
        'LDW R0, R3, #0',
        'ADD R6, R6, #1 ; sin silenciar',
        'HALT',
        'MSG .STRINGZ "hola"',
        'TAB .BLKW #4',
        '.END'
      ].join('\n');
      const r = Assembler.assemble([{ name: 'ok_comment.asm', source: src }]);
      assert(r.ok, 'Debe ensamblar sin errores');
      assert(r.warnings.length === 1, `Esperado 1 aviso (solo línea 10), obtenidos ${r.warnings.length}: ${Assembler.formatMessages(r.warnings)}`);
      assert(r.warnings[0].line === 10, `Línea=${r.warnings[0].line} (esperado 10)`);
      assert(r.warnings[0].message === 'el puntero de pila debe moverse de a 2 bytes', `Mensaje=${r.warnings[0].message}`);
      return 'Silenció líneas 3, 4, 6 y 8; mantuvo aviso en línea 10';
    }
  });

  TESTS.push({
    section: '11.8 Avisos LC-3',
    name: 'El proyecto integrado main.asm + mcd_mcm.asm ensambla con 0 avisos',
    run() {
      const r = Assembler.assemble(modsWithInputs(48, 180));
      assert(r.ok, Assembler.formatMessages(r.errors));
      assert(r.warnings.length === 0, `Avisos inesperados: ${Assembler.formatMessages(r.warnings)}`);
      return '0 avisos';
    }
  });

  /* ===== 11.9 Traza de fallo (FAULT) ===== */
  TESTS.push({
    section: '11.9 Traza de fallo',
    name: 'Buffer circular de 15 instrucciones registra PC, desensamblado y R0..R7 al fallar',
    run() {
      const src = [
        '.ORIG x3000',
        'AND R0, R0, #0',
        'ADDI R0, R0, #12',
        'LOOP ADD R0, R0, #-1',
        'BRp LOOP',
        'AND R1, R1, #0',
        'ADD R1, R1, #1',
        'LDW R2, R1, #0',
        'HALT',
        '.END'
      ].join('\n');
      const r = Assembler.assemble([{ name: 'fault_test.asm', source: src }]);
      assert(r.ok, Assembler.formatMessages(r.errors));
      const cpu = new CPU();
      cpu.load(r.bytes);
      const st = cpu.run(1000);
      assert(st === 'FAULT', `Estado=${st} (esperado FAULT)`);
      assert(cpu.fault && cpu.fault.kind === 'ALIGN', `Fault=${cpu.fault && cpu.fault.kind}`);
      const tr = cpu.getTrace();
      assert(tr.length === 15, `Traza=${tr.length} (esperado 15)`);
      const last = tr[tr.length - 1];
      assert(last.pc === cpu.fault.pc, `Último PC=x${hex4(last.pc)} vs fault=x${hex4(cpu.fault.pc)}`);
      assert(/LDW/i.test(last.disasm), `Disasm=${last.disasm}`);
      assert(Array.isArray(last.regs) && last.regs.length === 8, 'Debe incluir R0..R7');
      assert(last.regs[1] === 1, `R1=${last.regs[1]} (esperado 1)`);
      return `15 entradas; fallo en x${hex4(last.pc)} (${last.disasm}, R1=${last.regs[1]})`;
    }
  });

  /* ===== 11.10 Consola: entrada tecla por tecla (GETC) ===== */
  TESTS.push({
    section: '11.10 Consola (Tecla por tecla)',
    name: 'GETC tecla por tecla: menú sin \\n sobrante + edición con Backspace (8) y Enter (\\n)',
    run() {
      const src = [
        '.ORIG x3000',
        'GETC',                // lee opción de menú en R0 (sin esperar \n)
        'ADD R1, R0, #0',      // guarda opción en R1
        'LEA R2, BUF',         // puntero de escritura
        'LOOP GETC',           // lee dígitos de la línea siguiente
        'ADD R3, R0, #-10',    // ¿Enter ('\n')?
        'BRz DONE',
        'ADD R3, R0, #-8',     // ¿Backspace (8)?
        'BRnp STORE',
        'ADD R2, R2, #-1',     // retrocede 1 byte en BUF
        'BRnzp LOOP',
        'STORE STB R0, R2, #0',
        'ADD R2, R2, #1',
        'BRnzp LOOP',
        'DONE AND R0, R0, #0',
        'STB R0, R2, #0',
        'HALT',
        'BUF .BLKB #8',
        '.END'
      ].join('\n');
      const r = Assembler.assemble([{ name: 'menu_getc.asm', source: src }]);
      assert(r.ok, Assembler.formatMessages(r.errors));
      const cpu = new CPU();
      cpu.load(r.bytes);

      // 1) Se detiene esperando la tecla del menú
      assert(cpu.run(500) === 'WAIT_INPUT', `Esperado WAIT_INPUT inicial, obtenido ${cpu.status}`);

      // 2) Manda solo '2' (sin '\n'): debe leer '2' en R1 y volver a WAIT_INPUT para el número
      cpu.pushInput('2');
      cpu.status = 'RUNNING';
      assert(cpu.run(500) === 'WAIT_INPUT', `Tras tecla de menú debe esperar número (WAIT_INPUT), obtenido ${cpu.status}`);
      assert(cpu.regs[1] === 50, `Opción de menú R1=${cpu.regs[1]} (esperado 50 = '2')`);
      assert(cpu.input.length === 0, `Cola debe quedar vacía (sin \\n sobrante), len=${cpu.input.length}`);

      // 3) Manda tecla por tecla: '9', Backspace (8), '7', '5', Enter ('\n')
      for (const ch of ['9', String.fromCharCode(8), '7', '5', '\n']) {
        cpu.pushInput(ch);
        cpu.status = 'RUNNING';
        cpu.run(500);
      }
      assert(cpu.status === 'HALTED', `Estado final=${cpu.status} (esperado HALTED)`);
      const bufAddr = symAddr(r, 'BUF');
      const got = String.fromCharCode(cpu.mem[bufAddr], cpu.mem[bufAddr + 1]);
      assert(got === '75' && cpu.mem[bufAddr + 2] === 0, `BUF=${JSON.stringify(got)} (esperado "75" + NUL)`);
      assert(cpu.input.length === 0, `Cola residual=${cpu.input.length}`);
      return `Menú='2', línea="75" tras BS(8) y \\n, 0 bytes sobrantes`;
    }
  });

  /* ===== 11.7 Instrucciones del SO ===== */
  TESTS.push({
    section: '11.7 Instrucciones del SO',
    name: 'HALT: instrCount=1, osInstrCount=OS_COST.HALT, instructionsWithOS=1+OS_COST.HALT',
    run() {
      const { cpu } = runAsm('.ORIG x3000\nHALT\n.END');
      const m = cpu.metrics();
      assert(cpu.instrCount === 1, `instrCount=${cpu.instrCount} (esperado 1)`);
      assert(cpu.osInstrCount === CPU.OS_COST.HALT, `osInstrCount=${cpu.osInstrCount} (esperado ${CPU.OS_COST.HALT})`);
      assert(m.osInstructions === CPU.OS_COST.HALT, `osInstructions=${m.osInstructions}`);
      assert(m.instructionsWithOS === 1 + CPU.OS_COST.HALT, `instructionsWithOS=${m.instructionsWithOS}`);
      return `usuario=1, SO=${m.osInstructions}, total=${m.instructionsWithOS}`;
    }
  });

  TESTS.push({
    section: '11.7 Instrucciones del SO',
    name: 'GETC + OUT + HALT con entrada Z -> GETC + OUT + HALT',
    run() {
      const { cpu } = runAsm('.ORIG x3000\nGETC\nOUT\nHALT\n.END', { input: 'Z' });
      const exp = CPU.OS_COST.GETC + CPU.OS_COST.OUT + CPU.OS_COST.HALT;
      assert(cpu.instrCount === 3, `instrCount=${cpu.instrCount}`);
      assert(cpu.osInstrCount === exp, `osInstrCount=${cpu.osInstrCount} (esperado ${exp})`);
      assert(cpu.metrics().instructionsWithOS === 3 + exp, 'instructionsWithOS incorrecto');
      return `SO=${cpu.osInstrCount} (GETC+OUT+HALT)`;
    }
  });

  TESTS.push({
    section: '11.7 Instrucciones del SO',
    name: 'LEA R0,S + PUTS + HALT ("hola") -> PUTS_BASE + 4*PUTS_PER_CHAR + HALT',
    run() {
      const { cpu } = runAsm('.ORIG x3000\nLEA R0, S\nPUTS\nHALT\nS .STRINGZ "hola"\n.END');
      const exp = CPU.OS_COST.PUTS_BASE + 4 * CPU.OS_COST.PUTS_PER_CHAR + CPU.OS_COST.HALT;
      assert(cpu.output === 'hola', `Salida=${JSON.stringify(cpu.output)}`);
      assert(cpu.osInstrCount === exp, `osInstrCount=${cpu.osInstrCount} (esperado ${exp})`);
      return `SO=${cpu.osInstrCount} (4 caracteres)`;
    }
  });

  TESTS.push({
    section: '11.7 Instrucciones del SO',
    name: 'IN + HALT con entrada Z -> OS_COST.IN + OS_COST.HALT',
    run() {
      const { cpu } = runAsm('.ORIG x3000\nIN\nHALT\n.END', { input: 'Z' });
      const exp = CPU.OS_COST.IN + CPU.OS_COST.HALT;
      assert(cpu.regs[0] === 0x5A, `R0=x${hex4(cpu.regs[0])}`);
      assert(cpu.osInstrCount === exp, `osInstrCount=${cpu.osInstrCount} (esperado ${exp})`);
      return `SO=${cpu.osInstrCount} (IN+HALT)`;
    }
  });

  TESTS.push({
    section: '11.7 Instrucciones del SO',
    name: 'reset() deja osInstrCount en 0 y options.osCost permite recalibrar',
    run() {
      const r = asmOne('.ORIG x3000\nHALT\n.END');
      const cpu = new CPU({ osCost: { HALT: 77 } });
      cpu.load(r.bytes);
      cpu.run(100);
      assert(cpu.osInstrCount === 77, `Con override osCost.HALT=77 -> ${cpu.osInstrCount}`);
      cpu.reset();
      assert(cpu.osInstrCount === 0, `Tras reset osInstrCount=${cpu.osInstrCount} (esperado 0)`);
      assert(cpu.metrics().osInstructions === 0 && cpu.metrics().instructionsWithOS === 0, 'Métricas tras reset deben ser 0');
      return 'reset() -> osInstrCount=0; options.osCost OK';
    }
  });

  TESTS.push({
    section: '11.7 Instrucciones del SO',
    name: 'TRAP a vector no nativo (x30) no suma instrucciones al SO',
    run() {
      const r = asmOne('.ORIG x3000\nTRAP x30\nHALT\n.END');
      const cpu = new CPU();
      cpu.load(r.bytes);
      // Vector x30 -> dirección x3100 con instrucción RET (0x60E0)
      cpu.poke16(0x30 << 1, 0x3100);
      cpu.poke16(0x3100, 0x60E0);
      cpu.step(); // TRAP x30
      cpu.step(); // RET
      assert(cpu.instrCount === 2, `instrCount=${cpu.instrCount} (esperado 2)`);
      assert(cpu.osInstrCount === 0, `TRAP no nativo sumó al SO: ${cpu.osInstrCount}`);
      cpu.step(); // HALT
      assert(cpu.status === 'HALTED', `Estado=${cpu.status}`);
      assert(cpu.osInstrCount === CPU.OS_COST.HALT, `Tras HALT osInstrCount=${cpu.osInstrCount}`);
      return `TRAP x30 + RET -> SO=0; con HALT -> SO=${cpu.osInstrCount}`;
    }
  });

  TESTS.push({
    section: '11.7 Instrucciones del SO',
    name: 'metrics().writtenBytes coincide con dataBytesWritten',
    run() {
      const { cpu } = runAsm('.ORIG x3000\nLEA R1, BUF\nSTW R0, R1, #0\nSTW R0, R1, #0\nSTB R0, R1, #2\nHALT\nBUF .BLKB #4\n.END');
      const m = cpu.metrics();
      assert(m.writtenBytes === m.dataBytesWritten, `writtenBytes=${m.writtenBytes} vs dataBytesWritten=${m.dataBytesWritten}`);
      assert(m.writtenBytes === 3, `writtenBytes=${m.writtenBytes} (esperado 3 bytes distintos)`);
      assert(m.memWrites === 3, `memWrites=${m.memWrites} (esperado 3 escrituras)`);
      return `writtenBytes=${m.writtenBytes} === dataBytesWritten`;
    }
  });

  TESTS.push({
    section: '11.7 Instrucciones del SO',
    name: 'Referencia calibrada contra simulador del grupo 8 (7 casos)',
    run() {
      const cases = [
        ['solo HALT', '.ORIG x3000\nHALT\n.END', '', 1, 103],
        ['LD+OUT+HALT', '.ORIG x3000\nLD R0, L\nOUT\nHALT\nL .FILL x41\n.END', '', 3, 111],
        ['LD+3xOUT+HALT', '.ORIG x3000\nLD R0, L\nOUT\nOUT\nOUT\nHALT\nL .FILL x41\n.END', '', 5, 127],
        ['PUTS vacío', '.ORIG x3000\nLEA R0, T\nPUTS\nHALT\nT .FILL x0000\n.END', '', 3, 113],
        ['PUTS 10 chars', '.ORIG x3000\nLEA R0, T\nPUTS\nHALT\nT .STRINGZ "ABCDEFGHIJ"\n.END', '', 3, 243],
        ['GETC+HALT', '.ORIG x3000\nGETC\nHALT\n.END', 'Z', 2, 115],
        ['IN+HALT', '.ORIG x3000\nIN\nHALT\n.END', 'Z', 2, 385]
      ];
      for (const [label, src, input, expUser, expOS] of cases) {
        const { cpu } = runAsm(src, input ? { input } : {});
        const m = cpu.metrics();
        assert(m.instructions === expUser, `${label}: usuario=${m.instructions} (esperado ${expUser})`);
        assert(m.osInstructions === expOS, `${label}: SO=${m.osInstructions} (esperado ${expOS})`);
        assert(m.instructionsWithOS === expUser + expOS, `${label}: conSO=${m.instructionsWithOS}`);
      }
      return '7/7 exactos (103, 111, 127, 113, 243, 115, 385)';
    }
  });

  function runAll() {
    const results = [];
    let passed = 0;
    for (const t of TESTS) {
      try {
        const detail = t.run();
        passed++;
        results.push({ section: t.section, name: t.name, ok: true, detail: detail || 'OK' });
      } catch (e) {
        results.push({ section: t.section, name: t.name, ok: false, detail: e.message || String(e) });
      }
    }
    return { total: TESTS.length, passed, failed: TESTS.length - passed, results };
  }

  return { TESTS, runAll };
}));
