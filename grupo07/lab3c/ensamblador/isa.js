/*
 * isa.js - Especificación unificada de la ISA de 5 bits de opcode (Grupo 7, Lab 3c)
 * ==================================================================================
 * Única fuente de verdad para el conjunto de instrucciones (Pasos 1, 2 y 5).
 * Cada instrucción se define en un único registro con:
 *   - opcode:     código de operación de 5 bits en IR[15:11] (0..31)
 *   - name:       nombre mostrado en la grilla de 32 opcodes
 *   - mnemonics:  mnemónicos/alias aceptados por el ensamblador
 *   - updatesNZP: si la instrucción actualiza las banderas de condición N, Z, P
 *   - encode:     función que codifica una instrucción desde mnemónico y operandos
 *   - exec:       función que ejecuta la palabra IR sobre una instancia de CPU
 *   - disasm:     función única de desensamblado (IR, dirección -> texto)
 *
 * Convenciones (ISA Grupo 7 - v2 con aceleración aritmética):
 *   - Memoria de 64 KB direccionable por byte, little-endian.
 *   - Instrucciones de 16 bits alineadas a dirección par. Fetch: IR <- mem16[PC]; PC <- PC + 2.
 *   - Offsets escalados << 2 (múltiplos de 4 con base PC' & 0xFFFC): LD, ST, LEA.
 *   - Offsets escalados << 1 (palabras): BR, JSR, LDW (LDR), STW (STR).
 *   - Offsets en bytes (sin escalar): LDB, LDH, LDBS, STB, STH.
 *   - ADD y AND son solo de registros (bits [4:3] = 00). El ensamblador codifica
 *     ADD/AND con inmediato como alias de ADDI/ANDI (imm5 con signo, -16..15).
 *   - Instrucciones nuevas (Paso 5): SUB, ABS, MUL, MULH, DIV, REM, SHL, SHR, SAR,
 *     ADDI, ANDI. Todas actualizan N, Z, P.
 *   - Flags N, Z, P: los actualizan ADD, AND, NOT, LD, LDW, LDB, LDH, LDBS y las
 *     11 instrucciones nuevas (SUB, ABS, MUL, MULH, DIV, REM, SHL, SHR, SAR, ADDI, ANDI).
 *     No los actualizan: LEA, ST, STW, STB, STH, BR, JSR, JSRR, JMP, RET, TRAP.
 *   - Casos límite documentados:
 *       * ABS(x8000) = x8000 (sin falta).
 *       * DIV de x8000 por xFFFF da x8000 (desborda y se trunca a 16 bits, sin falta).
 *       * DIV / REM con divisor = 0 lanzan falta CPUError('DIV0', 'División por cero (divisor = 0 en DIV/REM)').
 *       * SHL / SHR / SAR usan únicamente los 4 bits bajos de SR2 (n = SR2 & 0xF).
 *
 * Opcodes libres reservados: 29 (11101), 30 (11110) y 31 (11111).
 */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.ISA = factory();
}(typeof globalThis !== 'undefined' ? globalThis : (typeof self !== 'undefined' ? self : this), function () {
  'use strict';

  const TRAP_ALIAS = { GETC: 0x20, OUT: 0x21, PUTS: 0x22, IN: 0x23, HALT: 0x25 };
  const TRAP_NAMES = { 0x20: 'GETC', 0x21: 'OUT', 0x22: 'PUTS', 0x23: 'IN', 0x25: 'HALT' };
  const BR_RE = /^BR(N?)(Z?)(P?)$/;
  const s16 = v => (v << 16) >> 16;

  const encodeReg3 = opcode => (_m, a, ctx) => {
    ctx.need(3);
    return (opcode << 11) | (ctx.reg(a[0]) << 8) | (ctx.reg(a[1]) << 5) | ctx.reg(a[2]);
  };

  const disasmReg3 = mnemonic => ir =>
    `${mnemonic} R${(ir >> 8) & 7}, R${(ir >> 5) & 7}, R${ir & 7}`;

  const encodeImm5 = (opcode, name) => (_m, a, ctx) => {
    ctx.need(3);
    const dr = ctx.reg(a[0]), s1 = ctx.reg(a[1]);
    if (ctx.parseReg(a[2]) !== null) throw new Error(`${name} espera un inmediato`);
    const v = ctx.imm(a[2], -16, 15, `Inmediato imm5 de ${name}`);
    return (opcode << 11) | (dr << 8) | (s1 << 5) | (v & 0x1F);
  };

  const disasmImm5 = mnemonic => (ir, _addr, u) =>
    `${mnemonic} R${(ir >> 8) & 7}, R${(ir >> 5) & 7}, #${u.sext(ir, 5)}`;

  const encodeMemByteOrWord = opcode => (_m, a, ctx) => {
    ctx.need(3);
    const off = ctx.imm(a[2], -16, 15, 'offset5');
    return (opcode << 11) | (ctx.reg(a[0]) << 8) | (ctx.reg(a[1]) << 5) | (off & 0x1F);
  };

  const disasmBaseOff5 = mnemonic => (ir, _addr, u) =>
    `${mnemonic} R${(ir >> 8) & 7}, R${(ir >> 5) & 7}, #${u.sext(ir, 5)}`;

  const ea4 = (cpu, ir, npc) => ((npc & 0xFFFC) + (cpu._sext(ir, 8) << 2)) & 0xFFFF;

  const INSTRUCTIONS = [
    {
      opcode: 0,
      name: 'BR',
      mnemonics: ['NOP'],
      mnemonicPattern: BR_RE,
      updatesNZP: false,
      encode(m, _a, ctx) {
        if (m === 'NOP') { ctx.need(0); return 0; }
        const br = BR_RE.exec(m);
        ctx.need(1);
        let n = br[1] ? 1 : 0, z = br[2] ? 1 : 0, p = br[3] ? 1 : 0;
        if (!n && !z && !p) n = z = p = 1;
        return (0 << 11) | (n << 10) | (z << 9) | (p << 8) | ctx.pcrel(ctx.args[0], 8, true);
      },
      exec(cpu, ir, npc) {
        const n = (ir >> 10) & 1, z = (ir >> 9) & 1, p = (ir >> 8) & 1;
        if ((n && cpu.n) || (z && cpu.z) || (p && cpu.p)) cpu._jump(npc + (cpu._sext(ir, 8) << 1));
      },
      disasm(ir, addr, u) {
        if (ir === 0) return 'NOP';
        const f = ((ir >> 10) & 1 ? 'n' : '') + ((ir >> 9) & 1 ? 'z' : '') + ((ir >> 8) & 1 ? 'p' : '');
        return `BR${f} ${u.tgt(addr, u.sext(ir, 8) << 1)}`;
      }
    },
    {
      opcode: 1,
      name: 'ADD',
      mnemonics: ['ADD'],
      updatesNZP: true,
      encode(_m, a, ctx) {
        ctx.need(3);
        const dr = ctx.reg(a[0]), s1 = ctx.reg(a[1]), s2 = ctx.parseReg(a[2]);
        if (s2 !== null) return (1 << 11) | (dr << 8) | (s1 << 5) | s2;
        const v = ctx.imm(a[2], -16, 15, 'Inmediato imm5 de ADDI');
        return (27 << 11) | (dr << 8) | (s1 << 5) | (v & 0x1F);
      },
      exec(cpu, ir) {
        cpu._reserved((ir & 0x18) === 0, ir);
        const r = cpu.regs, dr = (ir >> 8) & 7, s1 = (ir >> 5) & 7;
        cpu._wreg(dr, r[s1] + r[ir & 7]);
      },
      disasm: disasmReg3('ADD')
    },
    {
      opcode: 2,
      name: 'LD',
      mnemonics: ['LD'],
      updatesNZP: true,
      encode(_m, a, ctx) {
        ctx.need(2);
        return (2 << 11) | (ctx.reg(a[0]) << 8) | ctx.pcrel4(a[1], 8);
      },
      exec(cpu, ir, npc) {
        const dr = (ir >> 8) & 7;
        cpu._wreg(dr, cpu._rd16(ea4(cpu, ir, npc)));
      },
      disasm(ir, addr, u) {
        return `LD R${(ir >> 8) & 7}, ${u.tgt4(addr, u.sext(ir, 8))}`;
      }
    },
    {
      opcode: 3,
      name: 'ST',
      mnemonics: ['ST'],
      updatesNZP: false,
      encode(_m, a, ctx) {
        ctx.need(2);
        return (3 << 11) | (ctx.reg(a[0]) << 8) | ctx.pcrel4(a[1], 8);
      },
      exec(cpu, ir, npc) {
        const sr = (ir >> 8) & 7;
        cpu._wr16(ea4(cpu, ir, npc), cpu.regs[sr]);
      },
      disasm(ir, addr, u) {
        return `ST R${(ir >> 8) & 7}, ${u.tgt4(addr, u.sext(ir, 8))}`;
      }
    },
    {
      opcode: 4,
      name: 'JSR/JSRR',
      mnemonics: ['JSR', 'JSRR'],
      updatesNZP: false,
      encode(m, a, ctx) {
        ctx.need(1);
        return m === 'JSR'
          ? (4 << 11) | 0x400 | ctx.pcrel(a[0], 10, true)
          : (4 << 11) | (ctx.reg(a[0]) << 5);
      },
      exec(cpu, ir, npc) {
        const r = cpu.regs, s1 = (ir >> 5) & 7;
        if (ir & 0x400) {
          r[7] = npc;
          cpu._jump(npc + (cpu._sext(ir, 10) << 1));
        } else {
          cpu._reserved((ir & 0x31F) === 0, ir);
          const t = r[s1];
          r[7] = npc;
          cpu._jump(t);
        }
      },
      disasm(ir, addr, u) {
        const s1 = (ir >> 5) & 7;
        return (ir & 0x400) ? `JSR ${u.tgt(addr, u.sext(ir, 10) << 1)}` : `JSRR R${s1}`;
      }
    },
    {
      opcode: 5,
      name: 'AND',
      mnemonics: ['AND'],
      updatesNZP: true,
      encode(_m, a, ctx) {
        ctx.need(3);
        const dr = ctx.reg(a[0]), s1 = ctx.reg(a[1]), s2 = ctx.parseReg(a[2]);
        if (s2 !== null) return (5 << 11) | (dr << 8) | (s1 << 5) | s2;
        const v = ctx.imm(a[2], -16, 15, 'Inmediato imm5 de ANDI');
        return (28 << 11) | (dr << 8) | (s1 << 5) | (v & 0x1F);
      },
      exec(cpu, ir) {
        cpu._reserved((ir & 0x18) === 0, ir);
        const r = cpu.regs, dr = (ir >> 8) & 7, s1 = (ir >> 5) & 7;
        cpu._wreg(dr, r[s1] & r[ir & 7]);
      },
      disasm: disasmReg3('AND')
    },
    {
      opcode: 6,
      name: 'LDW',
      mnemonics: ['LDW', 'LDR'],
      updatesNZP: true,
      encode: encodeMemByteOrWord(6),
      exec(cpu, ir) {
        const dr = (ir >> 8) & 7, s1 = (ir >> 5) & 7;
        cpu._wreg(dr, cpu._rd16(cpu.regs[s1] + (cpu._sext(ir, 5) << 1)));
      },
      disasm: disasmBaseOff5('LDW')
    },
    {
      opcode: 7,
      name: 'STW',
      mnemonics: ['STW', 'STR'],
      updatesNZP: false,
      encode: encodeMemByteOrWord(7),
      exec(cpu, ir) {
        const sr = (ir >> 8) & 7, s1 = (ir >> 5) & 7;
        cpu._wr16(cpu.regs[s1] + (cpu._sext(ir, 5) << 1), cpu.regs[sr]);
      },
      disasm: disasmBaseOff5('STW')
    },
    {
      opcode: 8,
      name: 'RTI',
      mnemonics: ['RTI'],
      updatesNZP: false,
      encode(_m, _a, ctx) {
        ctx.need(0);
        return 8 << 11;
      },
      exec(cpu, ir) {
        cpu._reserved((ir & 0x7FF) === 0, ir);
        cpu._fail('UNSUPPORTED', 'RTI no está soportada en este simulador');
      },
      disasm() { return 'RTI'; }
    },
    {
      opcode: 9,
      name: 'NOT',
      mnemonics: ['NOT'],
      updatesNZP: true,
      encode(_m, a, ctx) {
        ctx.need(2);
        return (9 << 11) | (ctx.reg(a[0]) << 8) | (ctx.reg(a[1]) << 5) | 0x1F;
      },
      exec(cpu, ir) {
        const dr = (ir >> 8) & 7, s1 = (ir >> 5) & 7;
        cpu._reserved((ir & 0x1F) === 0x1F, ir);
        cpu._wreg(dr, ~cpu.regs[s1]);
      },
      disasm(ir) {
        return `NOT R${(ir >> 8) & 7}, R${(ir >> 5) & 7}`;
      }
    },
    {
      opcode: 10,
      name: 'SUB',
      mnemonics: ['SUB'],
      updatesNZP: true,
      encode: encodeReg3(10),
      exec(cpu, ir) {
        cpu._reserved((ir & 0x18) === 0, ir);
        const r = cpu.regs, dr = (ir >> 8) & 7, s1 = (ir >> 5) & 7;
        cpu._wreg(dr, r[s1] - r[ir & 7]);
      },
      disasm: disasmReg3('SUB')
    },
    {
      opcode: 11,
      name: 'ABS',
      mnemonics: ['ABS'],
      updatesNZP: true,
      encode(_m, a, ctx) {
        ctx.need(2);
        return (11 << 11) | (ctx.reg(a[0]) << 8) | (ctx.reg(a[1]) << 5);
      },
      exec(cpu, ir) {
        // ABS(x8000) = x8000 (desborda y queda igual, sin falta).
        cpu._reserved((ir & 0x1F) === 0, ir);
        const dr = (ir >> 8) & 7, s1 = (ir >> 5) & 7;
        const v = s16(cpu.regs[s1]);
        cpu._wreg(dr, v < 0 ? -v : v);
      },
      disasm(ir) {
        return `ABS R${(ir >> 8) & 7}, R${(ir >> 5) & 7}`;
      }
    },
    {
      opcode: 12,
      name: 'JMP/RET',
      mnemonics: ['JMP', 'RET'],
      updatesNZP: false,
      encode(m, a, ctx) {
        if (m === 'RET') { ctx.need(0); return (12 << 11) | (7 << 5); }
        ctx.need(1);
        return (12 << 11) | (ctx.reg(a[0]) << 5);
      },
      exec(cpu, ir) {
        const s1 = (ir >> 5) & 7;
        cpu._reserved((ir & 0x71F) === 0, ir);
        cpu._jump(cpu.regs[s1]);
      },
      disasm(ir) {
        const s1 = (ir >> 5) & 7;
        return s1 === 7 ? 'RET' : `JMP R${s1}`;
      }
    },
    {
      opcode: 13,
      name: 'MUL',
      mnemonics: ['MUL'],
      updatesNZP: true,
      encode: encodeReg3(13),
      exec(cpu, ir) {
        cpu._reserved((ir & 0x18) === 0, ir);
        const r = cpu.regs, dr = (ir >> 8) & 7, s1 = (ir >> 5) & 7;
        const p = Math.imul(s16(r[s1]), s16(r[ir & 7]));
        cpu._wreg(dr, p & 0xFFFF);
      },
      disasm: disasmReg3('MUL')
    },
    {
      opcode: 14,
      name: 'LEA',
      mnemonics: ['LEA'],
      updatesNZP: false,
      encode(_m, a, ctx) {
        ctx.need(2);
        return (14 << 11) | (ctx.reg(a[0]) << 8) | ctx.pcrel4(a[1], 8);
      },
      exec(cpu, ir, npc) {
        const dr = (ir >> 8) & 7;
        cpu.regs[dr] = ea4(cpu, ir, npc);
      },
      disasm(ir, addr, u) {
        return `LEA R${(ir >> 8) & 7}, ${u.tgt4(addr, u.sext(ir, 8))}`;
      }
    },
    {
      opcode: 15,
      name: 'TRAP',
      mnemonics: ['TRAP', ...Object.keys(TRAP_ALIAS)],
      updatesNZP: false,
      encode(m, a, ctx) {
        if (TRAP_ALIAS[m] !== undefined) {
          ctx.need(0);
          return (15 << 11) | TRAP_ALIAS[m];
        }
        ctx.need(1);
        return (15 << 11) | ctx.imm(a[0], 0, 127, 'Vector TRAP');
      },
      exec(cpu, ir, npc) {
        cpu._trap(ir, npc);
      },
      disasm(ir, _addr, u) {
        const v = ir & 0x7F;
        return TRAP_NAMES[v] || `TRAP x${u.hex2(v)}`;
      }
    },
    {
      opcode: 16,
      name: 'LDB',
      mnemonics: ['LDB'],
      updatesNZP: true,
      encode: encodeMemByteOrWord(16),
      exec(cpu, ir) {
        const r = cpu.regs, dr = (ir >> 8) & 7, s1 = (ir >> 5) & 7;
        cpu._wreg(dr, (r[dr] & 0xFF00) | cpu._rd8(r[s1] + cpu._sext(ir, 5)));
      },
      disasm: disasmBaseOff5('LDB')
    },
    {
      opcode: 17,
      name: 'LDH',
      mnemonics: ['LDH'],
      updatesNZP: true,
      encode: encodeMemByteOrWord(17),
      exec(cpu, ir) {
        const r = cpu.regs, dr = (ir >> 8) & 7, s1 = (ir >> 5) & 7;
        cpu._wreg(dr, (r[dr] & 0x00FF) | (cpu._rd8(r[s1] + cpu._sext(ir, 5)) << 8));
      },
      disasm: disasmBaseOff5('LDH')
    },
    {
      opcode: 18,
      name: 'STB',
      mnemonics: ['STB'],
      updatesNZP: false,
      encode: encodeMemByteOrWord(18),
      exec(cpu, ir) {
        const r = cpu.regs, sr = (ir >> 8) & 7, s1 = (ir >> 5) & 7;
        cpu._wr8(r[s1] + cpu._sext(ir, 5), r[sr]);
      },
      disasm: disasmBaseOff5('STB')
    },
    {
      opcode: 19,
      name: 'STH',
      mnemonics: ['STH'],
      updatesNZP: false,
      encode: encodeMemByteOrWord(19),
      exec(cpu, ir) {
        const r = cpu.regs, sr = (ir >> 8) & 7, s1 = (ir >> 5) & 7;
        cpu._wr8(r[s1] + cpu._sext(ir, 5), r[sr] >> 8);
      },
      disasm: disasmBaseOff5('STH')
    },
    {
      opcode: 20,
      name: 'LDBS',
      mnemonics: ['LDBS'],
      updatesNZP: true,
      encode: encodeMemByteOrWord(20),
      exec(cpu, ir) {
        const r = cpu.regs, dr = (ir >> 8) & 7, s1 = (ir >> 5) & 7;
        cpu._wreg(dr, cpu._sext(cpu._rd8(r[s1] + cpu._sext(ir, 5)), 8));
      },
      disasm: disasmBaseOff5('LDBS')
    },
    {
      opcode: 21,
      name: 'MULH',
      mnemonics: ['MULH'],
      updatesNZP: true,
      encode: encodeReg3(21),
      exec(cpu, ir) {
        cpu._reserved((ir & 0x18) === 0, ir);
        const r = cpu.regs, dr = (ir >> 8) & 7, s1 = (ir >> 5) & 7;
        const p = Math.imul(s16(r[s1]), s16(r[ir & 7]));
        cpu._wreg(dr, (p >> 16) & 0xFFFF);
      },
      disasm: disasmReg3('MULH')
    },
    {
      opcode: 22,
      name: 'DIV',
      mnemonics: ['DIV'],
      updatesNZP: true,
      encode: encodeReg3(22),
      exec(cpu, ir) {
        // Cociente entero con signo truncado hacia cero.
        // Caso límite: DIV(x8000, xFFFF) = x8000 (desborda y se trunca a 16 bits, sin falta).
        cpu._reserved((ir & 0x18) === 0, ir);
        const r = cpu.regs, dr = (ir >> 8) & 7, s1 = (ir >> 5) & 7;
        const b = s16(r[ir & 7]);
        if (b === 0) cpu._fail('DIV0', 'División por cero (divisor = 0 en DIV/REM)');
        cpu._wreg(dr, Math.trunc(s16(r[s1]) / b) & 0xFFFF);
      },
      disasm: disasmReg3('DIV')
    },
    {
      opcode: 23,
      name: 'REM',
      mnemonics: ['REM'],
      updatesNZP: true,
      encode: encodeReg3(23),
      exec(cpu, ir) {
        // Resto entero con el signo del dividendo (SR1 = cociente * SR2 + resto).
        cpu._reserved((ir & 0x18) === 0, ir);
        const r = cpu.regs, dr = (ir >> 8) & 7, s1 = (ir >> 5) & 7;
        const b = s16(r[ir & 7]);
        if (b === 0) cpu._fail('DIV0', 'División por cero (divisor = 0 en DIV/REM)');
        cpu._wreg(dr, (s16(r[s1]) % b) & 0xFFFF);
      },
      disasm: disasmReg3('REM')
    },
    {
      opcode: 24,
      name: 'SHL',
      mnemonics: ['SHL'],
      updatesNZP: true,
      encode: encodeReg3(24),
      exec(cpu, ir) {
        cpu._reserved((ir & 0x18) === 0, ir);
        const r = cpu.regs, dr = (ir >> 8) & 7, s1 = (ir >> 5) & 7;
        const n = r[ir & 7] & 0xF;
        cpu._wreg(dr, (r[s1] << n) & 0xFFFF);
      },
      disasm: disasmReg3('SHL')
    },
    {
      opcode: 25,
      name: 'SHR',
      mnemonics: ['SHR'],
      updatesNZP: true,
      encode: encodeReg3(25),
      exec(cpu, ir) {
        cpu._reserved((ir & 0x18) === 0, ir);
        const r = cpu.regs, dr = (ir >> 8) & 7, s1 = (ir >> 5) & 7;
        const n = r[ir & 7] & 0xF;
        cpu._wreg(dr, (r[s1] & 0xFFFF) >>> n);
      },
      disasm: disasmReg3('SHR')
    },
    {
      opcode: 26,
      name: 'SAR',
      mnemonics: ['SAR'],
      updatesNZP: true,
      encode: encodeReg3(26),
      exec(cpu, ir) {
        cpu._reserved((ir & 0x18) === 0, ir);
        const r = cpu.regs, dr = (ir >> 8) & 7, s1 = (ir >> 5) & 7;
        const n = r[ir & 7] & 0xF;
        cpu._wreg(dr, (s16(r[s1]) >> n) & 0xFFFF);
      },
      disasm: disasmReg3('SAR')
    },
    {
      opcode: 27,
      name: 'ADDI',
      mnemonics: ['ADDI'],
      updatesNZP: true,
      encode: encodeImm5(27, 'ADDI'),
      exec(cpu, ir) {
        const r = cpu.regs, dr = (ir >> 8) & 7, s1 = (ir >> 5) & 7;
        cpu._wreg(dr, r[s1] + cpu._sext(ir, 5));
      },
      disasm: disasmImm5('ADDI')
    },
    {
      opcode: 28,
      name: 'ANDI',
      mnemonics: ['ANDI'],
      updatesNZP: true,
      encode: encodeImm5(28, 'ANDI'),
      exec(cpu, ir) {
        const r = cpu.regs, dr = (ir >> 8) & 7, s1 = (ir >> 5) & 7;
        cpu._wreg(dr, r[s1] & cpu._sext(ir, 5));
      },
      disasm: disasmImm5('ANDI')
    }
  ];

  const BY_OPCODE = new Array(32).fill(null);
  const OPNAMES = new Array(32).fill('(libre)');
  const BY_MNEMONIC = new Map();
  const PATTERNS = [];

  for (const spec of INSTRUCTIONS) {
    BY_OPCODE[spec.opcode] = spec;
    OPNAMES[spec.opcode] = spec.name;
    if (Array.isArray(spec.mnemonics)) {
      for (const m of spec.mnemonics) BY_MNEMONIC.set(m.toUpperCase(), spec);
    }
    if (spec.mnemonicPattern) PATTERNS.push(spec);
  }

  function findByMnemonic(mnemonic) {
    const u = String(mnemonic || '').toUpperCase();
    const direct = BY_MNEMONIC.get(u);
    if (direct) return direct;
    for (const spec of PATTERNS) {
      if (spec.mnemonicPattern.test(u)) return spec;
    }
    return null;
  }

  return {
    INSTRUCTIONS,
    BY_OPCODE,
    OPNAMES,
    TRAP_ALIAS,
    TRAP_NAMES,
    findByMnemonic
  };
}));
