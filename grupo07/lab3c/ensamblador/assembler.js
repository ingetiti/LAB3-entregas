/*
 * assembler.js - Ensamblador de 2 pasadas multimódulo (Grupo 7, Lab 3c)
 * ======================================================================
 * Convierte módulos .asm en código máquina hexadecimal/binario. No conoce la
 * CPU ni el DOM; consulta la tabla unificada ISA (isa.js).
 *
 * Salida: los 2 primeros bytes son la dirección .ORIG en little-endian
 * (byte bajo primero), seguidos de los bytes del programa.
 *
 * Convenciones de la ISA (v2 con aceleración aritmética):
 *   - Opcode en bits [15:11] (5 bits), memoria de 64 KB direccionable por byte.
 *   - PC-relativos ×4 (LD, ST, LEA): base = (addr + 2) & 0xFFFC,
 *     desplazamiento = (destino - base) / 4. Sus destinos de datos se alinean
 *     automáticamente a múltiplos de 4 bytes.
 *   - PC-relativos ×2 (BR, JSR): desplazamiento = (destino - (addr + 2)) / 2.
 *   - Offsets en bytes (sin escalar): LDB, LDH, LDBS, STB, STH.
 *   - Con operando numérico, el número es directamente el valor del campo de
 *     offset (unidades de 4 bytes en LD/ST/LEA, palabras en BR/JSR).
 *   - ADD/AND con inmediato se codifican como alias de ADDI/ANDI (imm5: -16..15).
 *
 * Directivas:
 *   .ORIG addr (par)   .END   .FILL v[,v...] (palabra de 16 bits o etiqueta)
 *   .BLKW n (n palabras)      .BLKB n (n bytes)      .BYTE v[,v...]
 *   .STRINGZ "texto" (1 byte por carácter + NUL)     .EXTERNAL símbolo[,símbolo...]
 *
 * Alineación: antes de cada instrucción, .FILL o .BLKW, si el contador de
 * ubicación es impar se inserta 1 byte 0x00 de relleno. Además, si una
 * etiqueta destino de LD/ST/LEA precede a un dato, se rellenan 1..3 bytes 0x00
 * hasta que el contador sea múltiplo de 4 antes de asignar las etiquetas.
 *
 * Multimódulo: solo el primer módulo define .ORIG (en módulos posteriores se
 * ignora con advertencia y se ubican a continuación). Las etiquetas son locales
 * a su módulo y NO distinguen mayúsculas. En .EXTERNAL MODULO-ETIQUETA, MODULO
 * se resuelve en orden: (1) coincidencia exacta, (2) prefijo G<n>_ del módulo
 * que declara, (3) prefijo G27_, (4) único módulo terminado en _MODULO.
 */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) {
    const ISA = (root && typeof root.ISA !== 'undefined') ? root.ISA : require('./isa.js');
    module.exports = factory(ISA);
  } else {
    root.Assembler = factory(root.ISA);
  }
}(typeof globalThis !== 'undefined' ? globalThis : (typeof self !== 'undefined' ? self : this), function (ISA) {
  'use strict';

  const DIRECTIVES = new Set(['.ORIG', '.END', '.FILL', '.BLKW', '.BLKB', '.BYTE', '.STRINGZ', '.EXTERNAL']);
  const LABEL_RE = /^[A-Za-z_][A-Za-z0-9_]*$/;
  // Símbolo externo: ETIQUETA o MODULO-ETIQUETA (MODULO = nombre del archivo sin .asm).
  const EXT_RE = /^(?:[A-Za-z0-9_.]+-)?[A-Za-z_][A-Za-z0-9_]*$/;

  const MNEMONICS = new Set();
  for (const spec of ISA.INSTRUCTIONS) {
    if (Array.isArray(spec.mnemonics)) {
      for (const m of spec.mnemonics) MNEMONICS.add(m.toUpperCase());
    }
  }

  const key = n => n.toUpperCase(); // las etiquetas no distinguen mayúsculas (como en la LC-3)
  const baseName = n => n.replace(/\.asm$/i, '').toUpperCase();
  const hex4 = v => (v & 0xFFFF).toString(16).toUpperCase().padStart(4, '0');
  const hex2 = v => (v & 0xFF).toString(16).toUpperCase().padStart(2, '0');
  const isOp = t => {
    const u = t.toUpperCase();
    return u[0] === '.' || ISA.findByMnemonic(u) !== null;
  };

  /* ---------- análisis léxico ---------- */

  function stripComment(s) {
    let q = false;
    for (let i = 0; i < s.length; i++) {
      const c = s[i];
      if (q && c === '\\') { i++; continue; }
      if (c === '"') q = !q;
      else if (!q && c === ';') return s.slice(0, i);
    }
    return s;
  }

  function getComment(s) {
    let q = false;
    for (let i = 0; i < s.length; i++) {
      const c = s[i];
      if (q && c === '\\') { i++; continue; }
      if (c === '"') q = !q;
      else if (!q && c === ';') return s.slice(i);
    }
    return '';
  }

  const TOKEN_RE = /^([^\s,]+)[\s,]*(.*)$/;

  // Devuelve { labels, op, args, error }.
  function parseLine(raw) {
    const out = { labels: [], op: null, args: '', error: null };
    let rest = stripComment(raw).trim();
    let first = true;
    while (rest) {
      const m = TOKEN_RE.exec(rest);
      rest = m[2];
      const colon = m[1].endsWith(':');
      const tok = colon ? m[1].slice(0, -1) : m[1];
      if (!colon && isOp(tok)) { out.op = tok; out.args = rest; return out; }
      if (colon || (first && !out.labels.length)) {
        out.labels.push(tok);
        if (!colon) { // etiqueta sin ':' -> lo que sigue debe ser una instrucción o directiva
          if (!rest) return out;
          const m2 = TOKEN_RE.exec(rest);
          if (!isOp(m2[1])) {
            out.error = (/^(r[0-7]\b|#|x[0-9a-f]+$)/i.test(m2[1]))
              ? `Instrucción desconocida '${tok}'`
              : `'${m2[1]}' no es una instrucción ni una directiva`;
            return out;
          }
          out.op = m2[1]; out.args = m2[2];
          return out;
        }
        first = false;
        continue;
      }
      out.error = `No se reconoce '${tok}'`;
      return out;
    }
    return out;
  }

  function parseNumber(tok) {
    let m;
    if ((m = /^#([+-]?\d+)$/.exec(tok))) return parseInt(m[1], 10);
    if ((m = /^([+-]?)(?:0x|x)([0-9a-f]+)$/i.exec(tok))) return (m[1] === '-' ? -1 : 1) * parseInt(m[2], 16);
    if ((m = /^([+-]?)0b([01]+)$/i.exec(tok))) return (m[1] === '-' ? -1 : 1) * parseInt(m[2], 2);
    if (/^[+-]?\d+$/.test(tok)) return parseInt(tok, 10);
    return null;
  }

  function parseReg(tok) {
    const m = /^R([0-7])$/i.exec(tok);
    return m ? parseInt(m[1], 10) : null;
  }

  function parseString(s) {
    s = s.trim();
    if (s.length < 2 || s[0] !== '"' || s[s.length - 1] !== '"') throw new Error('.STRINGZ espera una cadena entre comillas dobles');
    const body = s.slice(1, -1);
    const esc = { n: 10, t: 9, r: 13, '0': 0, '\\': 92, '"': 34 };
    const out = [];
    for (let i = 0; i < body.length; i++) {
      const c = body[i];
      if (c === '\\') {
        const e = body[++i];
        if (!(e in esc)) throw new Error(`Secuencia de escape '\\${e ?? ''}' no soportada (usar \\n \\t \\r \\0 \\\\ \\")`);
        out.push(esc[e]);
      } else {
        const code = c.charCodeAt(0);
        if (code > 255) throw new Error(`El carácter '${c}' no entra en 1 byte`);
        out.push(code);
      }
    }
    return out;
  }

  const splitArgs = s => s.split(/[\s,]+/).filter(Boolean);

  /* ---------- ensamblador ---------- */

  // modules: [{ name, source }]
  function assemble(modules) {
    const errors = [], warnings = [];
    const mods = modules.map((m, i) => ({
      name: m.name || `modulo${i + 1}`, source: String(m.source || ''),
      symbols: new Map(), externals: new Map(), quad: new Set(), preExternals: new Set(), quadRefs: [], fillTargets: new Map()
    }));
    const items = [];
    let lc = null, origin = null, overflowed = false;

    // Resuelve el módulo destino (sin distinguir mayúsculas) en orden:
    // (1) exacto, (2) prefijo G<n>_ del módulo que declara, (3) G27_, (4) único sufijo _MODULO.
    const findModuleByName = (mod, modPart) => {
      const others = mods.filter(o => o !== mod);
      const exact = others.find(o => baseName(o.name) === modPart);
      if (exact) return exact;
      const pm = /^(G\d+_)/.exec(baseName(mod.name));
      if (pm) {
        const sameGroup = others.find(o => baseName(o.name) === pm[1] + modPart);
        if (sameGroup) return sameGroup;
      }
      const g27 = others.find(o => baseName(o.name) === 'G27_' + modPart);
      if (g27) return g27;
      const suf = '_' + modPart;
      const bySuf = others.filter(o => baseName(o.name).endsWith(suf));
      return bySuf.length === 1 ? bySuf[0] : null;
    };

    /* ===== pre-escaneo: destinos de LD / ST / LEA para alineación a 4 bytes ===== */
    mods.forEach(mod => {
      const lines = mod.source.split(/\r?\n/);
      for (let li = 0; li < lines.length; li++) {
        const pl = parseLine(lines[li]);
        if (pl.error || !pl.op) continue;
        const op = pl.op.toUpperCase();
        if (op === '.END') break;
        if (op === '.EXTERNAL') {
          for (const n of splitArgs(pl.args)) mod.preExternals.add(key(n));
        } else if (op === 'LD' || op === 'ST' || op === 'LEA') {
          const a = splitArgs(pl.args);
          if (a.length >= 2 && parseNumber(a[1]) === null) mod.quadRefs.push(a[1]);
        }
      }
    });

    mods.forEach(mod => {
      for (const tok of mod.quadRefs) {
        const k = key(tok), dash = k.lastIndexOf('-');
        if (dash >= 0) {
          const target = findModuleByName(mod, k.slice(0, dash));
          if (target) target.quad.add(k.slice(dash + 1));
        } else if (mod.preExternals.has(k)) {
          mods.forEach(o => { if (o !== mod) o.quad.add(k); });
        } else {
          mod.quad.add(k);
        }
      }
    });

    /* ===== pasada 1: tamaños y tabla de símbolos ===== */
    mods.forEach((mod, mi) => {
      const E = (line, message) => errors.push({ module: mod.name, line, message });
      const W = (line, message) => warnings.push({ module: mod.name, line, message });
      let pending = [];   // etiquetas esperando la próxima instrucción o dato
      let ended = false;
      let moduleAligned = mi === 0;

      const defineLabels = (kind, extra) => {
        for (const lb of pending) {
          if (mod.symbols.has(key(lb.name))) E(lb.line, `Etiqueta '${lb.name}' duplicada (ya definida en la línea ${mod.symbols.get(key(lb.name)).line})`);
          else {
            mod.symbols.set(key(lb.name), { name: lb.name, addr: lc, line: lb.line, kind });
            if (kind === 'fill' && extra && Array.isArray(extra.args) && extra.args.length === 1 && parseNumber(extra.args[0]) === null) {
              mod.fillTargets.set(key(lb.name), extra.args[0]);
            }
          }
        }
        pending = [];
      };

      const place = (kind, line, text, size, align, extra) => {
        if (lc === null) {
          lc = origin = 0x3000;
          W(line, 'El primer módulo no tiene .ORIG: se asume x3000');
        }
        if ((!moduleAligned || align) && (lc & 1)) {
          items.push({ kind: 'pad', addr: lc, size: 1, mod, line, text: '(relleno de alineación)' });
          lc++;
        }
        moduleAligned = true;
        const quadLabels = pending.filter(lb => mod.quad.has(key(lb.name)));
        if (quadLabels.length) {
          if (kind === 'instr') {
            for (const lb of quadLabels) {
              E(lb.line, `La etiqueta '${lb.name}' se usa en LD/ST/LEA pero está en código: moverla a la zona de datos (los destinos de LD/ST/LEA se alinean a 4 bytes)`);
            }
          } else {
            const rem = lc & 3;
            if (rem !== 0) {
              const padSize = 4 - rem;
              items.push({ kind: 'pad', addr: lc, size: padSize, mod, line, text: '(relleno de alineación a 4)' });
              lc += padSize;
            }
          }
        }
        defineLabels(kind, extra);
        items.push(Object.assign({ kind, addr: lc, size, mod, line, text }, extra));
        lc += size;
        if (lc > 0x10000 && !overflowed) { overflowed = true; E(line, 'El programa excede los 64 KB de memoria'); }
      };

      const lines = mod.source.split(/\r?\n/);
      for (let li = 0; li < lines.length && !ended; li++) {
        const line = li + 1;
        const raw = lines[li];
        const pl = parseLine(raw);
        if (pl.error) { E(line, pl.error); continue; }
        for (const name of pl.labels) {
          if (!LABEL_RE.test(name)) E(line, `Etiqueta inválida '${name}'`);
          else if (parseReg(name) !== null || isOp(name) || /^x[0-9a-f]+$/i.test(name)) E(line, `El nombre '${name}' está reservado (registro, mnemónico o parecido a un literal hexadecimal)`);
          else pending.push({ name, line });
        }
        if (!pl.op) continue;
        const op = pl.op.toUpperCase();
        const text = raw.trim();
        try {
          if (op[0] !== '.') {
            place('instr', line, text, 2, true, { mnemonic: op, args: splitArgs(pl.args) });
            continue;
          }
          if (!DIRECTIVES.has(op)) throw new Error(`Directiva desconocida ${op}`);
          switch (op) {
            case '.ORIG': {
              if (mi > 0) {
                W(line, '.ORIG ignorado: solo el primer módulo define el origen');
                break;
              }
              const v = parseNumber(pl.args.trim());
              if (v === null || v < 0 || v > 0xFFFF) throw new Error('.ORIG espera una dirección entre x0000 y xFFFF');
              if (v & 1) throw new Error(`.ORIG x${hex4(v)} es impar: el origen debe ser par`);
              if (lc === null) { lc = origin = v; }
              else throw new Error('.ORIG repetido o después de código: usar uno solo al comienzo del primer módulo');
              moduleAligned = true;
              break;
            }
            case '.END': ended = true; break;
            case '.EXTERNAL': {
              const names = splitArgs(pl.args);
              if (!names.length) throw new Error('.EXTERNAL espera al menos un símbolo');
              for (const n of names) {
                if (!EXT_RE.test(n)) E(line, `Símbolo externo inválido '${n}' (usar ETIQUETA o MODULO-ETIQUETA)`);
                else mod.externals.set(key(n), { name: n, line });
              }
              break;
            }
            case '.FILL': {
              const vals = splitArgs(pl.args);
              if (!vals.length) throw new Error('.FILL espera un valor o una etiqueta');
              place('fill', line, text, 2 * vals.length, true, { args: vals });
              break;
            }
            case '.BYTE': {
              const vals = splitArgs(pl.args);
              if (!vals.length) throw new Error('.BYTE espera al menos un valor');
              place('byte', line, text, vals.length, false, { args: vals });
              break;
            }
            case '.BLKW': case '.BLKB': {
              const n = parseNumber(pl.args.trim());
              if (n === null || n < 1) throw new Error(`${op} espera una cantidad mayor o igual a 1`);
              const w = op === '.BLKW';
              place(w ? 'blkw' : 'blkb', line, text, w ? 2 * n : n, w, {});
              break;
            }
            case '.STRINGZ': {
              const bytes = parseString(pl.args);
              place('string', line, text, bytes.length + 1, false, { bytes });
              break;
            }
          }
        } catch (e) { E(line, e.message); }
      }
      if (!ended) W(lines.length, 'Falta la directiva .END');
      if (pending.length) { if (lc === null) lc = origin = 0x3000; defineLabels('end'); }
    });

    // Busca un símbolo externo: 'MODULO-ETIQUETA' (vía findModuleByName) o 'ETIQUETA' (en cualquier otro módulo).
    const findExternal = (mod, name) => {
      const k = key(name), dash = k.lastIndexOf('-');
      if (dash >= 0) {
        const modPart = k.slice(0, dash), lab = k.slice(dash + 1);
        const target = findModuleByName(mod, modPart);
        if (!target) return { error: `el módulo '${name.slice(0, dash)}' no existe (módulos: ${mods.filter(o => o !== mod).map(o => baseName(o.name).toLowerCase()).join(', ') || 'ninguno'})` };
        const sym = target.symbols.get(lab);
        return sym ? { sym } : { error: `'${name.slice(dash + 1)}' no está definido en el módulo ${target.name}` };
      }
      const found = mods.filter(o => o !== mod && o.symbols.has(k));
      if (found.length === 1) return { sym: found[0].symbols.get(k) };
      if (found.length > 1) return { error: `'${name}' está definido en varios módulos (${found.map(f => f.name).join(', ')}): usar MODULO-ETIQUETA` };
      return { error: `'${name}' no está definido en ningún otro módulo` };
    };

    // Cada .EXTERNAL debe existir en otro módulo y no estar definido localmente.
    mods.forEach(mod => {
      for (const [k, ext] of mod.externals) {
        if (mod.symbols.has(k)) errors.push({ module: mod.name, line: ext.line, message: `'${ext.name}' se declara .EXTERNAL pero está definido en este mismo módulo` });
        else { const f = findExternal(mod, ext.name); if (f.error) errors.push({ module: mod.name, line: ext.line, message: `.EXTERNAL ${ext.name}: ${f.error}` }); }
      }
    });

    /* ===== pasada 2: codificación (vía tabla unificada ISA) ===== */
    const resolve = (mod, name) => {
      const k = key(name);
      if (mod.symbols.has(k)) return mod.symbols.get(k).addr;
      if (mod.externals.has(k)) {
        const f = findExternal(mod, name);
        if (f.error) throw new Error(f.error);
        return f.sym.addr;
      }
      const other = mods.find(o => o !== mod && o.symbols.has(k));
      if (other) throw new Error(`Símbolo '${name}' definido en ${other.name}: falta declarar .EXTERNAL ${name}`);
      throw new Error(`Símbolo '${name}' no definido (si está en otro módulo, falta declarar .EXTERNAL ${name})`);
    };

    const reg = tok => {
      const r = parseReg(tok);
      if (r === null) throw new Error(`Se esperaba un registro R0-R7 y se encontró '${tok}'`);
      return r;
    };

    const imm = (tok, lo, hi, what) => {
      const n = parseNumber(tok);
      if (n === null) throw new Error(`Se esperaba un número para ${what} y se encontró '${tok}'`);
      if (n < lo || n > hi) throw new Error(`${what} ${n} fuera de rango (${lo}..${hi})`);
      return n;
    };

    function encodeInstr(it) {
      const m = it.mnemonic, a = it.args, mod = it.mod;
      const spec = ISA.findByMnemonic(m);
      if (!spec || !spec.encode) throw new Error(`Instrucción '${m}' no implementada`);
      const ctx = {
        args: a,
        reg,
        parseReg,
        imm,
        need: n => { if (a.length !== n) throw new Error(`${m} espera ${n} operando(s) y recibió ${a.length}`); },
        pcrel: (tok, bits, scaled) => {
          const n = parseNumber(tok);
          let off;
          if (n !== null) off = n;
          else {
            const target = resolve(mod, tok);
            const d = target - (it.addr + 2);
            if (scaled) {
              if (d & 1) throw new Error(`'${tok}' (x${hex4(target)}) está en dirección impar: ${m} trabaja con direcciones pares`);
              off = d / 2;
            } else off = d;
          }
          const lo = -(1 << (bits - 1)), hi = (1 << (bits - 1)) - 1;
          if (off < lo || off > hi) throw new Error(`${m}: destino '${tok}' fuera de alcance (offset ${off} ${scaled ? 'palabras' : 'bytes'}, rango ${lo}..${hi})`);
          return off & ((1 << bits) - 1);
        },
        pcrel4: (tok, bits) => {
          const n = parseNumber(tok);
          let off;
          if (n !== null) off = n;
          else {
            const target = resolve(mod, tok);
            const base = (it.addr + 2) & ~3;
            const d = target - base;
            if (d & 3) throw new Error(`destino '${tok}' (x${hex4(target)}) no está alineado a 4 bytes`);
            off = d / 4;
          }
          const lo = -(1 << (bits - 1)), hi = (1 << (bits - 1)) - 1;
          if (off < lo || off > hi) throw new Error(`${m}: destino '${tok}' fuera de alcance (offset ${off} unidades de 4 bytes, rango ${lo}..${hi})`);
          return off & ((1 << bits) - 1);
        }
      };
      return spec.encode(m, a, ctx);
    }

    const word = w => [w & 0xFF, (w >> 8) & 0xFF];

    function emit(it) {
      switch (it.kind) {
        case 'pad': return new Array(it.size).fill(0);
        case 'gap': case 'blkb': case 'blkw': return new Array(it.size).fill(0);
        case 'instr': return word(encodeInstr(it));
        case 'string': return it.bytes.concat([0]);
        case 'byte': return it.args.map(t => {
          const n = parseNumber(t);
          if (n === null) throw new Error(`.BYTE espera números y se encontró '${t}'`);
          if (n < -128 || n > 255) throw new Error(`.BYTE ${n} fuera de rango (-128..255)`);
          return n & 0xFF;
        });
        case 'fill': {
          const out = [];
          for (const t of it.args) {
            const n = parseNumber(t);
            let v;
            if (n !== null) {
              if (n < -32768 || n > 65535) throw new Error(`.FILL ${n} fuera de rango (-32768..65535)`);
              v = n;
            } else v = resolve(it.mod, t);
            out.push(...word(v));
          }
          return out;
        }
      }
      return [];
    }

    const out = [];
    const listing = [];
    for (const it of items) {
      let bytes;
      try { bytes = emit(it); }
      catch (e) { errors.push({ module: it.mod.name, line: it.line, message: e.message }); bytes = new Array(it.size).fill(0); }
      for (const b of bytes) out.push(b);
      listing.push({ addr: it.addr, bytes, module: it.mod.name, line: it.line, text: it.text, kind: it.kind });
    }

    /* ===== avisos heurísticos para detectar código escrito para la LC-3 original ===== */
    const BLOCK_END_OPS = new Set(['JMP', 'RET', 'JSR', 'JSRR', 'TRAP', 'GETC', 'OUT', 'PUTS', 'IN', 'HALT', 'RTI']);
    const isBlockEndOp = m => BLOCK_END_OPS.has(m) || /^BR[NZP]*$/.test(m);
    const WORD_MEM_OPS = new Set(['LDR', 'LDW', 'STR', 'STW']);
    const CLOBBER_DR_OPS = new Set(['AND', 'ANDI', 'NOT', 'SUB', 'ABS', 'MUL', 'MULH', 'DIV', 'REM', 'SHR', 'SAR', 'LDB', 'LDH', 'LDBS']);

    const resolveSymInfo = (mod, tok) => {
      const k = key(tok);
      if (mod.symbols.has(k)) return { mod, sym: mod.symbols.get(k) };
      if (mod.externals.has(k)) {
        const f = findExternal(mod, tok);
        if (f.sym) {
          const targetMod = mods.find(o => o !== mod && o.symbols.get(key(f.sym.name)) === f.sym) || mod;
          return { mod: targetMod, sym: f.sym };
        }
      }
      return null;
    };

    const isStringzTarget = (mod, tok, depth = 0) => {
      if (depth > 2) return false;
      const info = resolveSymInfo(mod, tok);
      if (!info) return false;
      if (info.sym.kind === 'string') return true;
      if (info.sym.kind === 'fill') {
        const ptr = info.mod.fillTargets.get(key(info.sym.name));
        if (ptr) return isStringzTarget(info.mod, ptr, depth + 1);
      }
      return false;
    };

    mods.forEach(mod => {
      const modLines = mod.source.split(/\r?\n/);
      const isSilenced = line => /^;\s*@ok(?:\b|$)/i.test(getComment(modLines[line - 1] || ''));
      const W = (line, message) => { if (!isSilenced(line)) warnings.push({ module: mod.name, line, message }); };
      const modInstrs = items.filter(it => it.mod === mod && it.kind === 'instr');
      const blocks = [];
      let cur = [];
      for (const it of modInstrs) {
        cur.push(it);
        if (isBlockEndOp(it.mnemonic)) {
          blocks.push(cur);
          cur = [];
        }
      }
      if (cur.length) blocks.push(cur);

      for (const blk of blocks) {
        // Registros usados como base de LDR/LDW/STR/STW en algún punto de este bloque lineal.
        const baseRegs = new Set();
        for (const it of blk) {
          if (WORD_MEM_OPS.has(it.mnemonic) && it.args.length >= 2) {
            const br = parseReg(it.args[1]);
            if (br !== null) baseRegs.add(br);
          }
        }

        const strReg = new Array(8).fill(false);
        const lblReg = new Array(8).fill(false);
        const scaledReg = new Array(8).fill(false);
        const indexedBase = new Array(8).fill(null);
        const clearReg = r => { strReg[r] = false; lblReg[r] = false; scaledReg[r] = false; indexedBase[r] = null; };

        for (const it of blk) {
          const m = it.mnemonic, a = it.args;
          if ((m === 'LEA' || m === 'LD') && a.length >= 2) {
            const dr = parseReg(a[0]);
            if (dr !== null) {
              clearReg(dr);
              if (parseNumber(a[1]) === null) {
                lblReg[dr] = true;
                if (isStringzTarget(mod, a[1])) strReg[dr] = true;
              }
            }
          } else if (WORD_MEM_OPS.has(m) && a.length >= 2) {
            const r0 = parseReg(a[0]), br = parseReg(a[1]);
            if (br !== null && strReg[br]) {
              W(it.line, 'texto: usar LDB/STB, un byte por carácter');
            }
            if (br !== null && indexedBase[br] && !indexedBase[br].warned) {
              W(indexedBase[br].line, 'índice de tabla: ¿falta multiplicar por 2?');
              indexedBase[br].warned = true;
            }
            if ((m === 'LDR' || m === 'LDW') && r0 !== null) clearReg(r0);
          } else if ((m === 'ADD' || m === 'ADDI') && a.length >= 3) {
            const dr = parseReg(a[0]), s1 = parseReg(a[1]), s2 = parseReg(a[2]);
            const immVal = s2 === null ? parseNumber(a[2]) : null;
            if (dr !== null && s1 !== null) {
              if (immVal !== null) {
                if (dr === 6 && (Math.abs(immVal) % 2 === 1)) {
                  W(it.line, 'el puntero de pila debe moverse de a 2 bytes');
                } else if (dr === s1 && dr !== 6 && (immVal === 1 || immVal === -1) && baseRegs.has(dr) && !strReg[dr]) {
                  W(it.line, 'posible puntero a palabras: debería avanzar 2');
                }
                if (dr === s1) {
                  scaledReg[dr] = false;
                  indexedBase[dr] = null;
                } else if (immVal === 0) {
                  strReg[dr] = strReg[s1];
                  lblReg[dr] = lblReg[s1];
                  scaledReg[dr] = scaledReg[s1];
                  indexedBase[dr] = null;
                } else {
                  clearReg(dr);
                }
              } else if (s2 !== null) {
                if (s1 === s2) {
                  clearReg(dr);
                  scaledReg[dr] = true;
                } else {
                  const baseIsS1 = dr === s1 && lblReg[s1] && !strReg[s1] && !scaledReg[s2];
                  const baseIsS2 = dr === s2 && lblReg[s2] && !strReg[s2] && !scaledReg[s1];
                  const isStrAdd = (dr === s1 && strReg[s1]) || (dr === s2 && strReg[s2]);
                  if (baseIsS1 || baseIsS2) {
                    lblReg[dr] = true;
                    strReg[dr] = false;
                    scaledReg[dr] = false;
                    indexedBase[dr] = { line: it.line, warned: false };
                  } else if (isStrAdd) {
                    strReg[dr] = true;
                    lblReg[dr] = true;
                    scaledReg[dr] = false;
                    indexedBase[dr] = null;
                  } else {
                    clearReg(dr);
                  }
                }
              }
            }
          } else if (m === 'SHL' && a.length >= 3) {
            const dr = parseReg(a[0]);
            if (dr !== null) { clearReg(dr); scaledReg[dr] = true; }
          } else if (CLOBBER_DR_OPS.has(m) && a.length >= 1) {
            const dr = parseReg(a[0]);
            if (dr !== null) clearReg(dr);
          }
        }
      }
    });

    const sortByModLine = (x, y) => (mods.findIndex(m => m.name === x.module) - mods.findIndex(m => m.name === y.module)) || (x.line - y.line);
    errors.sort(sortByModLine);
    warnings.sort(sortByModLine);
    if (errors.length) return { ok: false, errors, warnings };

    const bytes = new Uint8Array(2 + out.length);
    bytes[0] = origin & 0xFF; bytes[1] = (origin >> 8) & 0xFF;
    bytes.set(out, 2);

    const symbols = [];
    mods.forEach(mod => mod.symbols.forEach(s => symbols.push({ name: s.name, addr: s.addr, module: mod.name, kind: s.kind })));
    symbols.sort((p, q) => p.addr - q.addr);

    const listingText = listing.map(l => {
      const b = l.kind === 'instr' || l.kind === 'fill'
        ? l.bytes.reduce((acc, _, i) => (i % 2 ? acc : acc.concat(hex4(l.bytes[i] | ((l.bytes[i + 1] || 0) << 8)))), []).join(' ')
        : l.bytes.slice(0, 8).map(hex2).join(' ') + (l.bytes.length > 8 ? ' ...' : '');
      return `x${hex4(l.addr)}  ${b.padEnd(24)} ${l.text}`;
    }).join('\n');

    return {
      ok: true, errors, warnings, bytes, hex: toHex(bytes), origin, size: out.length,
      endAddr: origin + out.length, symbols, listing, listingText
    };
  }

  // Hexadecimal puro: bytes en pares, 16 por línea. Los 2 primeros bytes son el origen (little-endian).
  function toHex(bytes) {
    const lines = [];
    for (let i = 0; i < bytes.length; i += 16) {
      lines.push(Array.from(bytes.slice(i, i + 16), hex2).join(' '));
    }
    return lines.join('\n');
  }

  const formatMessages = list => list.map(e => `${e.module}:${e.line}: ${e.message}`).join('\n');

  /* ---------- importación pura de módulos desde .zip o lotes .asm ---------- */
  // entries: [{ path (o ruta), text (o texto), dir? }]
  // Devuelve { main, modules, ignored, warnings } sin tocar DOM ni JSZip.
  function processModuleEntries(entries) {
    const warnings = [];
    const seen = new Map();
    const accepted = [];
    let ignored = 0;

    for (const raw of (entries || [])) {
      if (!raw || raw.dir) continue;
      const rawPath = raw.path !== undefined ? raw.path : raw.ruta;
      const rawText = raw.text !== undefined ? raw.text : raw.texto;
      const norm = String(rawPath || '').replace(/\\/g, '/').replace(/^(\.\/|\/)+/, '');
      if (!norm || norm.endsWith('/')) continue;
      const segs = norm.split('/').filter(Boolean);
      if (!segs.length) continue;
      if (segs.some(s => s.toUpperCase() === '__MACOSX' || s.startsWith('.'))) {
        ignored++;
        continue;
      }
      const fileName = segs[segs.length - 1];
      if (!/\.asm$/i.test(fileName)) {
        ignored++;
        continue;
      }
      const moduleName = fileName.replace(/\.asm$/i, '');
      const k = moduleName.toUpperCase();
      if (seen.has(k)) {
        const first = seen.get(k);
        warnings.push(`Archivo duplicado '${norm}': ya existe '${first.path}' (se conserva el primero).`);
        ignored++;
        continue;
      }
      const item = {
        name: moduleName + '.asm',
        moduleName,
        source: String(rawText ?? ''),
        path: norm,
        depth: segs.length - 1
      };
      seen.set(k, item);
      accepted.push(item);
    }

    if (!accepted.length) {
      return { main: null, modules: [], ignored, warnings };
    }

    const mains = accepted.filter(m => /^main/i.test(m.moduleName));
    let mainMod;
    if (mains.length) {
      mains.sort((a, b) => (a.depth - b.depth) || a.path.toLowerCase().localeCompare(b.path.toLowerCase()));
      mainMod = mains[0];
    } else {
      const sorted = accepted.slice().sort((a, b) => a.moduleName.toLowerCase().localeCompare(b.moduleName.toLowerCase()));
      mainMod = sorted[0];
      warnings.push(`No se encontró ningún archivo que empiece con "main": se usa '${mainMod.moduleName}' como módulo principal.`);
    }

    const rest = accepted
      .filter(m => m !== mainMod)
      .sort((a, b) => a.moduleName.toLowerCase().localeCompare(b.moduleName.toLowerCase()));

    return {
      main: mainMod,
      modules: [mainMod, ...rest],
      ignored,
      warnings
    };
  }

  // Combina los módulos existentes con los importados según modo: 'replace' o 'add'.
  function mergeModuleLists(existing, imported, mode) {
    const incoming = Array.isArray(imported) ? imported : (imported && Array.isArray(imported.modules) ? imported.modules : []);
    if (mode === 'replace') {
      return {
        modules: incoming.map(m => ({ name: m.name, source: m.source })),
        activeIndex: 0
      };
    }
    const out = (existing || []).map(m => ({ name: m.name, source: m.source }));
    let firstIdx = -1;
    for (const m of incoming) {
      const idx = out.findIndex(x => baseName(x.name) === baseName(m.name));
      if (idx >= 0) {
        out[idx].name = m.name;
        out[idx].source = m.source;
        if (firstIdx < 0) firstIdx = idx;
      } else {
        out.push({ name: m.name, source: m.source });
        if (firstIdx < 0) firstIdx = out.length - 1;
      }
    }
    return {
      modules: out,
      activeIndex: firstIdx >= 0 ? firstIdx : 0
    };
  }

  return {
    assemble, toHex, formatMessages, parseNumber, MNEMONICS, TRAP_ALIAS: ISA.TRAP_ALIAS,
    processModuleEntries, mergeModuleLists
  };
}));
