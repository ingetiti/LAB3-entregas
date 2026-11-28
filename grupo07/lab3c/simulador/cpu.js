/*
 * cpu.js - Núcleo de ejecución del simulador funcional (Grupo 7, Lab 3c)
 * ======================================================================
 * Recibe SOLO código máquina (binario o hexadecimal); no entiende assembly.
 * Formato de imagen: los 2 primeros bytes son la dirección de origen (.ORIG)
 * en little-endian (byte bajo primero), el resto son los bytes del programa.
 *
 * Convenciones (ISA Grupo 7 - v2 con aceleración aritmética):
 *   - Memoria de 64 KB direccionable por byte, little-endian.
 *   - Instrucciones de 16 bits, opcode de 5 bits en IR[15:11], alineadas a
 *     dirección par. Fetch: IR <- mem16[PC]; PC <- PC + 2.
 *   - Offsets escalados << 2 (base PC' & 0xFFFC): LD, ST, LEA.
 *   - Offsets escalados << 1 (en palabras): BR, JSR, LDW, STW.
 *   - Offsets en bytes (sin escalar): LDB, LDH, LDBS, STB, STH.
 *   - LEA no modifica N, Z, P. Las cargas (LD, LDW, LDB, LDH, LDBS) y todas las
 *     instrucciones aritméticas/lógicas nuevas (SUB, ABS, MUL, MULH, DIV, REM,
 *     SHL, SHR, SAR, ADDI, ANDI) sí los actualizan.
 *   - Saltar a una dirección impar, o acceder a una palabra de 16 bits en
 *     dirección impar, produce una falta (FAULT) y el simulador se detiene.
 *   - División/resto por cero en DIV/REM produce falta DIV0.
 *   - TRAP: R7 <- PC'. GETC, OUT, PUTS, IN y HALT se resuelven de forma
 *     nativa (no hace falta tabla de vectores); otros vectores saltan a
 *     mem16[vect << 1] y fallan si esa entrada vale 0.
 *   - RTI no está soportada (falta UNSUPPORTED; o ILLEGAL si IR[10:0] != 0).
 *
 * Métricas: instrucciones totales y por opcode, y uso de memoria en bytes
 * con historial de banderas por byte (1=fetch, 2=lectura, 4=escritura, 8=cargado).
 */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) {
    const ISA = (root && typeof root.ISA !== 'undefined') ? root.ISA : require('../ensamblador/isa.js');
    module.exports = factory(ISA);
  } else {
    root.CPU = factory(root.ISA);
  }
}(typeof globalThis !== 'undefined' ? globalThis : (typeof self !== 'undefined' ? self : this), function (ISA) {
  'use strict';

  const MEM_SIZE = 0x10000;
  const TRACE_SIZE = 15;

  // Costo estimado (en instrucciones) de las rutinas nativas del SO para cada TRAP.
  // Calibrado contra el SO del grupo 8 (lc3.lgrum.xyz). PUTS_PER_CHAR incluye el OUT
  // interno (4 instrucciones del bucle + 1 TRAP + 8 de la rutina OUT). IN incluye su
  // PUTS de 19 caracteres, GETC y OUT.
  const OS_COST = {
    GETC: 12,
    OUT: 8,
    IN: 282,
    PUTS_BASE: 10,
    PUTS_PER_CHAR: 13,
    HALT: 103
  };

  const hex4 = v => (v & 0xFFFF).toString(16).toUpperCase().padStart(4, '0');
  const hex2 = v => (v & 0xFF).toString(16).toUpperCase().padStart(2, '0');
  // Extensión de signo de un campo de 'bits' bits.
  const sext = (v, bits) => { const m = 1 << (bits - 1); v &= (1 << bits) - 1; return (v ^ m) - m; };

  const OPNAMES = ISA.OPNAMES.slice();
  const DISASM_UTILS = {
    sext,
    hex4,
    hex2,
    tgt: (addr, d) => 'x' + hex4(((addr + 2) & 0xFFFF) + d),
    tgt4: (addr, off) => 'x' + hex4((((addr + 2) & 0xFFFC) + (off << 2)) & 0xFFFF)
  };

  class CPUError extends Error {
    constructor(kind, message) { super(message); this.kind = kind; }
  }

  class CPU {
    constructor(options = {}) {
      this.mem = new Uint8Array(MEM_SIZE);
      this.touch = new Uint8Array(MEM_SIZE); // bits: 1=fetch 2=lectura 4=escritura 8=cargado
      this.regs = new Uint16Array(8);
      this.initialSP = options.initialSP ?? 0xFE00;           // valor inicial de R6
      this.maxInstructions = options.maxInstructions ?? 5000000;
      this.osCost = options.osCost ? Object.assign({}, CPU.OS_COST, options.osCost) : CPU.OS_COST;
      this.onOutput = options.onOutput || null;
      this.opNames = OPNAMES.slice();
      this.isaTable = ISA.BY_OPCODE.slice();
      this.extensions = new Array(32).fill(null);             // ver registerInstruction()
      this.disasmExt = new Array(32).fill(null);
      this.image = null;
      this._trPc = new Uint16Array(TRACE_SIZE);
      this._trIr = new Uint16Array(TRACE_SIZE);
      this._trRegs = new Uint16Array(TRACE_SIZE * 8);
      this._trHead = 0;
      this._trCount = 0;
      this._resetState();
    }

    _resetState() {
      this.regs.fill(0);
      this.pc = 0; this.ir = 0;
      this.n = false; this.z = true; this.p = false;
      this.status = 'READY';          // READY | RUNNING | WAIT_INPUT | HALTED | FAULT | LIMIT
      this.fault = null;              // { kind, message, pc }
      this.instrCount = 0;
      this.osInstrCount = 0;
      this.opCount = new Array(32).fill(0);
      this.nReads = 0; this.nWrites = 0;
      this.input = [];
      this.output = '';
      this._trHead = 0;
      this._trCount = 0;
    }

    /* ---------- carga ---------- */

    // bytes: Uint8Array | Array. Los 2 primeros bytes = origen (little-endian).
    load(bytes) {
      if (!bytes || bytes.length < 2) throw new Error('Imagen vacía: faltan los 2 bytes de origen');
      const origin = bytes[0] | (bytes[1] << 8);
      if (origin & 1) throw new Error(`Origen impar x${hex4(origin)}: las instrucciones deben empezar en dirección par`);
      const data = Uint8Array.from(Array.prototype.slice.call(bytes, 2));
      if (origin + data.length > MEM_SIZE) throw new Error('La imagen excede los 64 KB de memoria');
      this.image = { origin, data };
      this.reset();
    }

    loadHex(text) { this.load(CPU.parseHex(text)); }

    // Vuelve al estado inicial recargando la imagen (la memoria no cargada queda en 0).
    reset() {
      this.mem.fill(0);
      this.touch.fill(0);
      this._resetState();
      if (!this.image) return;
      const { origin, data } = this.image;
      this.mem.set(data, origin);
      for (let i = 0; i < data.length; i++) this.touch[origin + i] |= 8;
      this.regs[6] = this.initialSP;
      this.pc = origin;
    }

    /* ---------- E/S de consola ---------- */

    pushInput(text) { for (const ch of String(text)) this.input.push(ch.charCodeAt(0) & 0xFF); }

    _out(s) {
      this.output += s;
      if (this.onOutput) this.onOutput(s);
    }

    /* ---------- acceso a memoria (con métricas) ---------- */

    _rd8(a) { a &= 0xFFFF; this.touch[a] |= 2; this.nReads++; return this.mem[a]; }

    _wr8(a, v) { a &= 0xFFFF; this.touch[a] |= 4; this.nWrites++; this.mem[a] = v & 0xFF; }

    _rd16(a) {
      a &= 0xFFFF;
      if (a & 1) throw new CPUError('ALIGN', `Lectura de palabra en dirección impar x${hex4(a)}`);
      this.touch[a] |= 2; this.touch[a + 1] |= 2; this.nReads++;
      return this.mem[a] | (this.mem[a + 1] << 8);
    }

    _wr16(a, v) {
      a &= 0xFFFF;
      if (a & 1) throw new CPUError('ALIGN', `Escritura de palabra en dirección impar x${hex4(a)}`);
      this.touch[a] |= 4; this.touch[a + 1] |= 4; this.nWrites++;
      this.mem[a] = v & 0xFF; this.mem[a + 1] = (v >> 8) & 0xFF;
    }

    // Acceso sin contar métricas (para la interfaz y las pruebas).
    peek8(a) { return this.mem[a & 0xFFFF]; }
    peek16(a) { a &= 0xFFFE; return this.mem[a] | (this.mem[a + 1] << 8); }
    poke8(a, v) { this.mem[a & 0xFFFF] = v & 0xFF; }
    poke16(a, v) { a &= 0xFFFE; this.mem[a] = v & 0xFF; this.mem[a + 1] = (v >> 8) & 0xFF; }

    /* ---------- helpers de ejecución ---------- */

    _sext(v, bits) { return sext(v, bits); }

    _fail(kind, message) { throw new CPUError(kind, message); }

    _setCC(v) { v &= 0xFFFF; this.n = (v & 0x8000) !== 0; this.z = v === 0; this.p = !this.n && !this.z; }

    _wreg(r, v) { this.regs[r] = v; this._setCC(this.regs[r]); }

    _jump(t) {
      t &= 0xFFFF;
      if (t & 1) throw new CPUError('ALIGN', `Salto a dirección impar x${hex4(t)}`);
      this.pc = t;
    }

    _reserved(ok, ir) {
      if (!ok) throw new CPUError('ILLEGAL', `Instrucción ilegal x${hex4(ir)}: bits reservados distintos del formato`);
    }

    /* ---------- ciclo de instrucción ---------- */

    // Ejecuta una instrucción. Devuelve el estado: RUNNING | WAIT_INPUT | HALTED | FAULT | LIMIT.
    step() {
      if (this.status === 'HALTED' || this.status === 'FAULT') return this.status;
      if (this.instrCount >= this.maxInstructions) { this.status = 'LIMIT'; return this.status; }
      const ia = this.pc;
      let executed = false;
      let ir = 0;
      try {
        if (ia & 1) throw new CPUError('ALIGN', `PC en dirección impar x${hex4(ia)}: las instrucciones deben estar alineadas`);
        this.touch[ia] |= 1; this.touch[ia + 1] |= 1;
        ir = this.mem[ia] | (this.mem[ia + 1] << 8);
        const op = ir >>> 11;
        // GETC / IN sin entrada disponible: esperar sin consumir la instrucción.
        if (op === 15 && ((ir & 0x7F) === 0x20 || (ir & 0x7F) === 0x23) && this.input.length === 0) {
          this.status = 'WAIT_INPUT';
          return this.status;
        }
        this.ir = ir;
        this.pc = (ia + 2) & 0xFFFF;
        this.instrCount++;
        this.opCount[op]++;
        this.status = 'RUNNING';
        executed = true;
        this._exec(ir, this.pc);
      } catch (e) {
        if (!(e instanceof CPUError)) throw e;
        this.fault = { kind: e.kind, message: e.message, pc: ia };
        this.status = 'FAULT';
      } finally {
        if (executed) {
          const slot = this._trHead;
          this._trPc[slot] = ia;
          this._trIr[slot] = ir;
          const off = slot << 3;
          const r = this.regs;
          const tr = this._trRegs;
          tr[off] = r[0]; tr[off + 1] = r[1]; tr[off + 2] = r[2]; tr[off + 3] = r[3];
          tr[off + 4] = r[4]; tr[off + 5] = r[5]; tr[off + 6] = r[6]; tr[off + 7] = r[7];
          this._trHead = slot + 1 === TRACE_SIZE ? 0 : slot + 1;
          if (this._trCount < TRACE_SIZE) this._trCount++;
        }
      }
      return this.status;
    }

    // Devuelve hasta las últimas 15 instrucciones ejecutadas (más antigua -> más reciente).
    getTrace() {
      const n = this._trCount;
      const out = new Array(n);
      const start = n < TRACE_SIZE ? 0 : this._trHead;
      for (let i = 0; i < n; i++) {
        const slot = (start + i) % TRACE_SIZE;
        const pc = this._trPc[slot];
        const ir = this._trIr[slot];
        const off = slot << 3;
        const tr = this._trRegs;
        out[i] = {
          pc,
          ir,
          disasm: this.disasm(ir, pc),
          regs: [
            tr[off], tr[off + 1], tr[off + 2], tr[off + 3],
            tr[off + 4], tr[off + 5], tr[off + 6], tr[off + 7]
          ]
        };
      }
      return out;
    }

    // Ejecuta hasta maxSteps instrucciones o hasta que el estado deje de ser RUNNING.
    run(maxSteps = 100000) {
      let s = this.status;
      for (let i = 0; i < maxSteps; i++) {
        s = this.step();
        if (s !== 'RUNNING') break;
      }
      return s;
    }

    // npc = PC' (ya incrementado en 2). Consulta la tabla unificada de la ISA.
    _exec(ir, npc) {
      const op = ir >>> 11;
      const ext = this.extensions[op];
      if (ext) { ext(this, ir, npc); return; }
      const spec = this.isaTable[op];
      if (spec && spec.exec) { spec.exec(this, ir, npc); return; }
      throw new CPUError('ILLEGAL', `Opcode no definido ${op.toString(2).padStart(5, '0')} en x${hex4(npc - 2)}`);
    }

    _trap(ir, npc) {
      this._reserved((ir & 0x780) === 0, ir);
      const r = this.regs;
      const vect = ir & 0x7F;
      r[7] = npc;
      switch (vect) {
        case 0x20:                                                          // GETC
          r[0] = this.input.shift();
          this.osInstrCount += this.osCost.GETC;
          break;
        case 0x21:                                                          // OUT
          this._out(String.fromCharCode(r[0] & 0xFF));
          this.osInstrCount += this.osCost.OUT;
          break;
        case 0x22: {                                                        // PUTS (1 byte por carácter)
          let a = r[0], s = '', guard = 0;
          for (;;) {
            const c = this._rd8(a);
            if (c === 0) break;
            s += String.fromCharCode(c);
            a = (a + 1) & 0xFFFF;
            if (++guard > MEM_SIZE) throw new CPUError('PUTS', 'PUTS sin terminador NUL');
          }
          this._out(s);
          this.osInstrCount += this.osCost.PUTS_BASE + this.osCost.PUTS_PER_CHAR * s.length;
          break;
        }
        case 0x23: {                                                        // IN
          this._out('Input a character> ');
          const c = this.input.shift();
          this._out(String.fromCharCode(c));
          r[0] = c;
          this.osInstrCount += this.osCost.IN;
          break;
        }
        case 0x25:                                                          // HALT (sin banner)
          this.status = 'HALTED';
          this.osInstrCount += this.osCost.HALT;
          break;
        default: {
          const h = this._rd16(vect << 1);
          if (h === 0) throw new CPUError('TRAP', `TRAP x${hex2(vect)} sin rutina (vector vacío)`);
          this._jump(h);
        }
      }
    }

    /* ---------- extensiones (Paso 5) ---------- */

    // Registra una instrucción nueva en un opcode libre.
    //   exec(cpu, ir, npc): ejecuta; puede usar cpu.regs, cpu._wreg(r, v), cpu._jump(t), cpu._rd16(a), ...
    //   disasm(ir, addr): opcional, devuelve el texto para el desensamblador.
    registerInstruction(op, name, exec, disasm) {
      if (!Number.isInteger(op) || op < 0 || op > 31 || this.opNames[op] !== '(libre)') {
        throw new Error(`El opcode ${op} no está libre`);
      }
      if (typeof exec !== 'function') throw new Error('registerInstruction requiere función de ejecución');
      this.opNames[op] = name;
      this.extensions[op] = exec;
      this.disasmExt[op] = disasm || null;
      this.isaTable[op] = { opcode: op, name, exec, disasm: disasm || null };
    }

    disasm(ir, addr = 0) {
      const op = ir >>> 11;
      if (this.extensions[op]) {
        const d = this.disasmExt[op];
        return d ? d(ir, addr, DISASM_UTILS) : `${this.opNames[op]} x${hex4(ir & 0x7FF)}`;
      }
      return CPU.disassemble(ir, addr);
    }

    /* ---------- métricas ---------- */

    metrics() {
      let loaded = 0, touched = 0, footprint = 0, code = 0, rd = 0, wr = 0;
      for (let i = 0; i < MEM_SIZE; i++) {
        const t = this.touch[i];
        if (!t) continue;
        footprint++;
        if (t & 8) loaded++;
        if (t & 7) touched++;
        if (t & 1) code++;
        if (t & 2) rd++;
        if (t & 4) wr++;
      }
      return {
        instructions: this.instrCount,
        osInstructions: this.osInstrCount,
        instructionsWithOS: this.instrCount + this.osInstrCount,
        byOpcode: this.opCount.slice(),               // 32 contadores, índice = opcode
        opNames: this.opNames.slice(),
        loadedBytes: loaded,                           // código y datos cargados de la imagen
        writtenBytes: wr,                              // bytes distintos escritos en memoria al ejecutar
        touchedBytes: touched,                         // bytes distintos usados al ejecutar (fetch, lectura o escritura)
        footprintBytes: footprint,                     // cargados U tocados
        codeBytesFetched: code,
        dataBytesRead: rd,
        dataBytesWritten: wr,
        memReads: this.nReads,                         // accesos de datos (cada palabra cuenta 1)
        memWrites: this.nWrites
      };
    }

    /* ---------- utilidades estáticas ---------- */

    // Texto hexadecimal -> Uint8Array. Ignora espacios, comas, saltos de línea,
    // prefijos 0x y comentarios (desde ';' o '//' hasta fin de línea).
    static parseHex(text) {
      const clean = String(text).replace(/(;|\/\/)[^\n]*/g, '').replace(/0x/gi, '').replace(/[\s,]+/g, '');
      if (!/^[0-9a-f]*$/i.test(clean)) throw new Error('Hexadecimal inválido: hay caracteres que no son 0-9 A-F');
      if (clean.length % 2) throw new Error('Hexadecimal inválido: cantidad impar de dígitos');
      const out = new Uint8Array(clean.length / 2);
      for (let i = 0; i < out.length; i++) out[i] = parseInt(clean.substr(i * 2, 2), 16);
      return out;
    }

    // Desensamblador único de una palabra (addr = dirección de la instrucción).
    static disassemble(ir, addr = 0) {
      const op = ir >>> 11;
      const spec = ISA.BY_OPCODE[op];
      if (spec && spec.disasm) return spec.disasm(ir, addr, DISASM_UTILS);
      return `.WORD x${hex4(ir)}`;
    }
  }

  CPU.OS_COST = OS_COST;
  CPU.CPUError = CPUError;
  CPU.OPNAMES = OPNAMES;
  CPU.MEM_SIZE = MEM_SIZE;
  CPU.TRACE_SIZE = TRACE_SIZE;
  CPU.hex4 = hex4;
  CPU.hex2 = hex2;
  CPU.sext = sext;
  return CPU;
}));
