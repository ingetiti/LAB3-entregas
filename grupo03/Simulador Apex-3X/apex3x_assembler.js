class Apex3XAssembler {
  static OPC = { BR:0, ADD:1, LD:2, ST:3, JSR:4, AND:5, LDR:6, STR:7, RTI:8, NOT:9, LDBL:10, STBL:11, JMP:12, BRC:13, LEA:14, TRAP:15,
    LDBH:16, STBH:17, LDX:18, PUSHM:19, POPM:20, MOVI:21, MOVH:22, SHL:23, SHR:24, SUB:25, ADC:26, MUL:27, MULQ:28, DIV:29, DIVQ:30 };
  static UN = { NOT:31, NEG:30, ABS:29, SXT:28, SWAB:27, CLZ:26 };
  static TRAPS = { GETC:0x20, OUT:0x21, PUTS:0x22, IN:0x23, HALT:0x25 };
  static MN = new Set(('ADD AND SUB NOT NEG ABS SXT SWAB CLZ JMP RET JSR JSRR LD ST LDR STR LEA TRAP RTI LDBL LDBH STBL STBH ' +
    'LDXW LDXB LDXSB PUSHM POPM MOVI MOVH SHL LSL ROL SHR LSR ASR ADC SBC MUL MULH MULHU DIV REM DIVU REMU GETC OUT PUTS IN HALT').split(' '));

  static num(t) {
    t = (t || '').trim().replace(/^#/, '');
    if (/^[-+]?\d+$/.test(t)) return parseInt(t, 10);
    const m = /^(-?)(?:0?x)([0-9a-f]+)$/i.exec(t);
    return m ? (m[1] ? -1 : 1) * parseInt(m[2], 16) : NaN;
  }
  static isMn(u) { return this.MN.has(u) || /^BR[NZP]{0,3}$/.test(u) || /^BRN?C$/.test(u) || /^(MULQ|DIVQ)(8|12|14|15)$/.test(u); }

  static assemble(src, o = {}) {
    const E = [], S = {}, I = [];
    let org = o.base ?? 0x3000, pc = org, orgSet = false, done = false;
    const fail = (ln, m) => E.push('Línea ' + ln + ': ' + m);

    src.split('\n').forEach((raw, i) => {
      if (done) return;
      const ln = i + 1;
      let q = false, cut = raw.length;
      for (let k = 0; k < raw.length; k++) {
        if (raw[k] === '"') q = !q; else if (raw[k] === ';' && !q) { cut = k; break; }
      }
      let l = raw.slice(0, cut).trim();
      if (!l) return;
      const first = l.match(/^[^\s,]+/)[0];
      const fu = first.replace(/:$/, '').toUpperCase();
      const rt = ((l.slice(first.length).trim().match(/^[^\s,]+/) || [''])[0]).toUpperCase();
      if (first.endsWith(':') || (!first.startsWith('.') && (!this.isMn(fu) || (rt && (this.isMn(rt) || rt[0] === '.'))))) {
        if (!/^[A-Za-z_]\w*$/.test(first.replace(/:$/, ''))) return fail(ln, 'etiqueta o instrucción inválida: ' + first);
        if (S[fu] !== undefined) fail(ln, 'etiqueta repetida: ' + first); else S[fu] = pc;
        l = l.slice(first.length).trim();
        if (!l) return;
      }
      const mm = l.match(/^(\S+)\s*(.*)$/), op = mm[1].toUpperCase(), args = mm[2];
      const unk = () => fail(ln, (l !== raw.slice(0, cut).trim() ? 'instrucción desconocida: ' + first.replace(/:$/, '') + ' (o falta la instrucción tras la etiqueta ' + first + ')' : 'instrucción desconocida: ' + op));
      const it = { ln, addr: pc, op, args, src: raw.trim(), w: [] };
      let size = 2;
      if (op === '.END') { done = true; return; }
      if (op === '.ORIG') {
        if (o.ignoreOrig) return;
        const v = this.num(args);
        if (orgSet || I.length) return fail(ln, '.ORIG debe ir una sola vez, al principio');
        if (isNaN(v) || v < 0 || v > 0xFFFF || (v & 1)) return fail(ln, '.ORIG inválido (dirección par de 16 bits): ' + args);
        org = pc = v; orgSet = true; return;
      }
      if (op === '.EXTERNAL') size = 0;
      else if (op === '.BLKW') { const n = this.num(args); if (isNaN(n) || n < 0) return fail(ln, '.BLKW necesita un número'); size = 2 * n; }
      else if (op === '.STRINGZ') {
        const m = args.match(/^"((?:[^"\\]|\\.)*)"$/);
        if (!m) return fail(ln, '.STRINGZ necesita una cadena entre comillas');
        it.bytes = [...m[1].replace(/\\(.)/g, (_, c) => ({ n: '\n', t: '\t', 0: '\0' }[c] ?? c))].map(c => c.charCodeAt(0) & 255).concat(0);
        size = (it.bytes.length + 1) & ~1;
      } else if (op === '.BYTE') {
        it.bytes = args.split(/[\s,]+/).filter(Boolean).map(t => this.num(t) & 255);
        size = (it.bytes.length + 1) & ~1;
      } else if (op.startsWith('.') && op !== '.FILL') return fail(ln, 'directiva desconocida: ' + op);
      else if (op !== '.FILL' && !this.isMn(op)) return unk();
      it.size = size; I.push(it); pc += size;
    });

    I.forEach(it => {
      try { it.w = this.encode(it, S, o); } catch (e) { fail(it.ln, e.message); }
    });
    const bytes = new Uint8Array(pc - org);
    I.forEach(it => it.w.forEach((w, k) => { bytes[it.addr - org + 2 * k] = w & 255; bytes[it.addr - org + 2 * k + 1] = w >> 8; }));
    return { origin: org, bytes, size: bytes.length, syms: S, errors: E, listing: I, hasOrig: orgSet };
  }

  // ---- Enlazador: mods = [{name, src}]. El módulo con .ORIG va primero; los demás se ubican a continuación. ----
  static link(mods) {
    const dummy = () => 0;
    let mi = mods.findIndex(m => /^\s*\.ORIG/im.test(m.src)); if (mi < 0) mi = 0;
    const run = (base, ext) => mods.map((m, i) => this.assemble(m.src, { base: base[i], ext, ignoreOrig: i !== mi }));
    const base = mods.map(() => 0x3000);
    let res = run(base, dummy), pc = res[mi].origin;
    [mi].concat(mods.map((_, i) => i).filter(i => i !== mi)).forEach(i => { base[i] = pc; pc += res[i].size; });
    res = run(base, dummy);
    const find = key => {
      const [mod, ...r] = key.split('-'), lab = r.join('-');
      for (let i = 0; i < mods.length; i++) {
        const n = mods[i].name.toUpperCase();
        if (n === mod || n.replace(/^G\d+_/, '') === mod) { const a = res[i].syms[lab]; if (a !== undefined) return a; }
      }
    };
    res = run(base, find);
    const errors = [];
    res.forEach((r, i) => r.errors.forEach(e => errors.push((mods.length > 1 ? mods[i].name + ': ' : '') + e)));
    const lo = Math.min(...res.map(r => r.origin)), hi = Math.max(...res.map(r => r.origin + r.size));
    if (hi > 0x10000) errors.push('el programa enlazado no entra en memoria (termina en x' + hi.toString(16) + ')');
    const bytes = new Uint8Array(Math.max(0, hi - lo));
    if (!errors.length) res.forEach(r => bytes.set(r.bytes, r.origin - lo));
    const listing = [].concat(...res.map((r, i) => r.listing.filter(x => x.size).map(x => Object.assign({}, x, { src: (i === mi ? '' : mods[i].name + ': ') + x.src }))));
    const allSyms = {};
    res.forEach((r, i) => {
      Object.entries(r.syms).forEach(([k, v]) => {
        allSyms[mods[i].name + ':' + k] = v;
      });
    });
    return { origin: lo, bytes, size: bytes.length, syms: res[mi].syms, allSyms, errors, listing, hasOrig: true,
      modules: mods.map((m, i) => ({ name: m.name, base: res[i].origin, size: res[i].size })) };
  }
  // ---- Formatos de archivo: 2 primeros bytes = dirección de origen (little-endian) ----
  static toBin(r) { const u = new Uint8Array(r.size + 2); u[0] = r.origin & 255; u[1] = r.origin >> 8; u.set(r.bytes, 2); return u; }
  static toHex(r) {
    const h = v => v.toString(16).toUpperCase().padStart(4, '0'), L = [h(r.origin)];
    for (let k = 0; k < r.size; k += 2) L.push(h(r.bytes[k] | ((r.bytes[k + 1] || 0) << 8)));
    return L.join('\n') + '\n';
  }
  static fromBin(u) {
    if (u.length < 2) throw Error('archivo .bin vacío');
    return { origin: u[0] | (u[1] << 8), bytes: Uint8Array.from(u.subarray(2)), size: u.length - 2, syms: {}, errors: [], listing: [] };
  }
  static fromHex(t) {
    const w = t.replace(/;.*$/gm, '').split(/\s+/).filter(Boolean).map(x => /^#/.test(x) ? parseInt(x.slice(1), 10) & 0xFFFF : parseInt(x.replace(/^0?x/i, ''), 16) & 0xFFFF);
    if (!w.length || w.some(isNaN)) throw Error('archivo hexadecimal inválido');
    const bytes = new Uint8Array((w.length - 1) * 2);
    w.slice(1).forEach((v, k) => { bytes[2 * k] = v & 255; bytes[2 * k + 1] = v >> 8; });
    return { origin: w[0], bytes, size: bytes.length, syms: {}, errors: [], listing: [] };
  }

  static encode(it, S, o = {}) {
    const op = it.op, addr = it.addr, A = it.args.split(/[\s,]+/).filter(Boolean), O = this.OPC;
    const F = (...p) => p.reduce((v, [x, w]) => (v << w) | (x & ((1 << w) - 1)), 0);
    const R = t => { const m = /^R([0-7])$/i.exec(t || ''); if (!m) throw Error('registro inválido: ' + (t || 'falta operando')); return +m[1]; };
    const isR = t => /^R[0-7]$/i.test(t || '');
    const V = (t, lo, hi, w) => { const n = this.num(t); if (isNaN(n) || n < lo || n > hi) throw Error(w + ' fuera de rango (' + lo + ' a ' + hi + '): ' + (t || 'falta')); return n; };
    const OFF = (t, bits) => {
      const lim = 1 << (bits - 1), key = (t || '').toUpperCase();
      if (S[key] !== undefined) {
        const d = S[key] - (addr + 2);
        if (d & 1) throw Error('destino impar: ' + t);
        const o = d / 2;
        if (o < -lim || o >= lim) throw Error(t + ' está fuera de alcance (±' + lim * 2 + ' bytes)');
        return o;
      }
      if (/^[A-Za-z_]/.test(t || '')) throw Error('etiqueta no definida: ' + t);
      return V(t, -lim, lim - 1, 'offset');
    };
    const BYTES = (n, lo, hi, even) => { if (even && (n & 1)) throw Error('el desplazamiento debe ser par (acceso de 16 bits)'); return n; };
    const rr = (o, mid) => F([O[o], 5], [R(A[0]), 3], [R(A[1]), 3], mid);

    if (op === '.EXTERNAL') return [];
    if (op === '.FILL') {
      const key = (A[0] || '').toUpperCase();
      if (S[key] !== undefined) return [S[key]];
      if (/^[A-Z_]\w*-[A-Z_]\w*$/.test(key)) { const v = o.ext && o.ext(key); if (v === undefined) throw Error('símbolo externo no resuelto: ' + A[0]); return [v & 0xFFFF]; }
      return [V(A[0], -32768, 65535, 'valor') & 0xFFFF];
    }
    if (op === '.BLKW') return new Array(this.num(it.args)).fill(0);
    if (it.bytes) { const w = []; for (let k = 0; k < it.bytes.length; k += 2) w.push(it.bytes[k] | ((it.bytes[k + 1] || 0) << 8)); return w; }
    if (/^BR[NZP]{0,3}$/.test(op)) {
      const f = op.length === 2 ? 7 : (op.includes('N') ? 4 : 0) | (op.includes('Z') ? 2 : 0) | (op.includes('P') ? 1 : 0);
      return [F([0, 5], [f, 3], [OFF(A[0], 8), 8])];
    }
    if (/^BRN?C$/.test(op)) {
      const f = op === 'BRC' ? 4 : 2;
      return [F([O.BRC, 5], [f, 3], [OFF(A[0], 8), 8])];
    }
    let m;
    if ((m = /^(MULQ|DIVQ)(8|12|14|15)$/.exec(op))) return [F([O[m[1]], 5], [R(A[0]), 3], [R(A[1]), 3], [{ 8: 0, 12: 1, 14: 2, 15: 3 }[m[2]], 2], [R(A[2]), 3])];
    switch (op) {
      case 'ADD': case 'AND': case 'SUB': {
        const mid = isR(A[2]) ? [[0, 2], [R(A[2]), 3]] : [[1, 1], [V(A[2], -8, 7, 'inmediato imm4'), 4]];
        return [F([O[op], 5], [R(A[0]), 3], [R(A[1]), 3], ...mid)];
      }
      case 'NOT': case 'NEG': case 'ABS': case 'SXT': case 'SWAB': case 'CLZ': return [F([9, 5], [R(A[0]), 3], [R(A[1]), 3], [this.UN[op], 5])];
      case 'JMP': return [F([12, 5], [0, 3], [R(A[0]), 3], [0, 5])];
      case 'RET': return [F([12, 5], [0, 3], [7, 3], [0, 5])];
      case 'JSR': return [F([4, 5], [1, 1], [OFF(A[0], 10), 10])];
      case 'JSRR': return [F([4, 5], [0, 3], [R(A[0]), 3], [0, 5])];
      case 'LD': case 'ST': case 'LEA': return [F([O[op], 5], [R(A[0]), 3], [OFF(A[1], 8), 8])];
      case 'LDR': case 'STR': return [rr(op, [BYTES(V(A[2], -32, 30, 'desplazamiento en bytes'), 0, 0, true) / 2, 5])];
      case 'LDBL': case 'LDBH': case 'STBL': case 'STBH': return [rr(op, [V(A[2], -16, 15, 'desplazamiento en bytes'), 5])];
      case 'LDXW': case 'LDXB': case 'LDXSB': return [F([18, 5], [R(A[0]), 3], [R(A[1]), 3], [{ LDXW: 0, LDXB: 1, LDXSB: 2 }[op], 2], [R(A[2]), 3])];
      case 'TRAP': return [F([15, 5], [0, 4], [V(A[0], 0, 127, 'vector'), 7])];
      case 'GETC': case 'OUT': case 'PUTS': case 'IN': case 'HALT': return [F([15, 5], [0, 4], [this.TRAPS[op], 7])];
      case 'RTI': return [F([8, 5], [0, 11])];
      case 'PUSHM': case 'POPM': return [F([O[op], 5], [0, 3], [V(A[0], 0, 255, 'máscara'), 8])];
      case 'MOVI': case 'MOVH': return [F([O[op], 5], [R(A[0]), 3], [V(A[1], -128, 255, 'imm8'), 8])];
      case 'SHL': case 'LSL': case 'ROL': case 'SHR': case 'LSR': case 'ASR': {
        const t = op === 'ROL' || op === 'ASR' ? 1 : 0, o = /^(SHL|LSL|ROL)$/.test(op) ? 23 : 24;
        const mid = isR(A[2]) ? [[0, 1], [t, 1], [R(A[2]), 3]] : [[1, 1], [t, 1], [V(A[2], 1, 8, 'cantidad') - 1, 3]];
        return [F([o, 5], [R(A[0]), 3], [R(A[1]), 3], ...mid)];
      }
      case 'ADC': case 'SBC': {
        const s = op === 'SBC' ? 1 : 0;
        const mid = isR(A[2]) ? [[0, 1], [s, 1], [R(A[2]), 3]] : [[1, 1], [s, 1], [V(A[2], 0, 7, 'inmediato imm3'), 3]];
        return [F([26, 5], [R(A[0]), 3], [R(A[1]), 3], ...mid)];
      }
      case 'MUL': case 'MULH': case 'MULHU': return [F([27, 5], [R(A[0]), 3], [R(A[1]), 3], [{ MUL: 0, MULH: 1, MULHU: 2 }[op], 2], [R(A[2]), 3])];
      case 'DIV': case 'REM': case 'DIVU': case 'REMU': return [F([29, 5], [R(A[0]), 3], [R(A[1]), 3], [{ DIV: 0, REM: 1, DIVU: 2, REMU: 3 }[op], 2], [R(A[2]), 3])];
    }
    throw Error('instrucción desconocida: ' + op);
  }
}

const LC3XAssembler = Apex3XAssembler;
if (typeof module !== 'undefined') {
  module.exports = Apex3XAssembler;
  module.exports.Apex3XAssembler = Apex3XAssembler;
  module.exports.LC3XAssembler = LC3XAssembler;
}
if (typeof window !== 'undefined') {
  window.Apex3XAssembler = Apex3XAssembler;
  window.LC3XAssembler = LC3XAssembler;
}
