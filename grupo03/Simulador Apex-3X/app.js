const DEMO=`; Producto y cociente en Q7.8, pila y acceso por byte
        .ORIG x3000
        LEA   R0, MSG
        PUTS
        MOVI  R1, #x80        ; 1,5 = x0180
        MOVH  R1, #1
        MOVI  R2, #x40        ; 2,25 = x0240
        MOVH  R2, #2
        MULQ8 R3, R1, R2      ; 3,375 = x0360
        DIVQ8 R4, R3, R2      ; vuelve a 1,5
        PUSHM #x1E            ; guarda R1 a R4
        MOVI  R1, #0
        MOVI  R2, #0
        POPM  #x1E
        LEA   R5, BUF
        STBL  R3, R5, #0      ; byte bajo
        STBH  R3, R5, #1      ; byte alto
        LDR   R0, R5, #0      ; palabra completa
        CLZ   R1, R0
        MOVI  R0, #x4F
        OUT
        MOVI  R0, #x4B
        OUT
        HALT
MSG     .STRINGZ "Hola Apex-3X: "
BUF     .BLKW 1
        .END
`;
const EXAMPLES = {
  demo: DEMO,
  muldiv: `; Multiplicación y división en punto fijo Q3.12 (1,5 * -2,25 = -3,375)
        .ORIG x3000
        MOVI  R1, #0
        MOVH  R1, #x18        ; 1,5 en Q3.12 = x1800
        MOVI  R2, #xC0
        MOVH  R2, #xDC        ; -2,25 en Q3.12 = xDCC0
        MULQ12 R3, R1, R2     ; -3,375 = xCA00
        DIVQ12 R4, R3, R1     ; recupera -2,25 = xDCC0
        ABS   R5, R3          ; valor absoluto |R3|
        HALT
        .END
`,
  bytes: `; Recorrido de arreglo por bytes con LDXB, STBL y STBH
        .ORIG x3000
        LEA   R0, TEXTO
        MOVI  R1, #0
        LEA   R2, DEST
BUCLE   LDXB  R3, R0, R1      ; lee byte R0[R1]
        BRz   FIN
        STBL  R3, R2, #0
        ADD   R2, R2, #1
        ADD   R1, R1, #1
        BR    BUCLE
FIN     STBL  R3, R2, #0      ; terminador nulo
        LEA   R0, DEST
        PUTS
        HALT
TEXTO   .STRINGZ "APEX3X-BYTES"
DEST    .BLKW 8
        .END
`,
  subrutina: `; Subrutina de suma 1..N preservando registros con PUSHM/POPM
        .ORIG x3000
        MOVI  R0, #10
        JSR   SUMA_N
        HALT
SUMA_N  PUSHM #x0E            ; guarda R1, R2, R3
        MOVI  R1, #0
        MOVI  R2, #1
LAZO    SUB   R3, R0, R2
        BRn   SALIR
        ADD   R1, R1, R2
        ADD   R2, R2, #1
        BR    LAZO
SALIR   ADD   R0, R1, #0
        POPM  #x0E            ; restaura R1, R2, R3
        RET
        .END
`,
  consola: `; Lectura de línea por GETC y eco en mayúsculas por OUT
        .ORIG x3000
        LEA   R0, PROMPT
        PUTS
LEER    GETC
        MOVI  R1, #10         ; Enter (LF)
        SUB   R2, R0, R1
        BRz   LISTO
        MOVI  R1, #x61        ; 'a'
        SUB   R2, R0, R1
        BRn   IMPR
        MOVI  R1, #x7A        ; 'z'
        SUB   R2, R1, R0
        BRn   IMPR
        MOVI  R1, #x20
        SUB   R0, R0, R1      ; pasar a mayúscula
IMPR    OUT
        BR    LEER
LISTO   MOVI  R0, #10
        OUT
        HALT
PROMPT  .STRINGZ "Escribí abajo y presioná Enter: "
        .END
`
};

const APEX3X_SYNTAX_HINTS = {
  ADD: 'ADD Rd, Rs1, Rs2 | ADD Rd, Rs1, #imm4 (−8 a 7). Suma y actualiza N/Z/P/C.',
  SUB: 'SUB Rd, Rs1, Rs2 | SUB Rd, Rs1, #imm4 (−8 a 7). Resta y actualiza N/Z/P/C.',
  AND: 'AND Rd, Rs1, Rs2 | AND Rd, Rs1, #imm4 (−8 a 7). AND bit a bit.',
  ADC: 'ADC Rd, Rs1, Rs2 | ADC Rd, Rs1, #imm3 (0 a 7). Suma con acarreo C.',
  SBC: 'SBC Rd, Rs1, Rs2 | SBC Rd, Rs1, #imm3 (0 a 7). Resta con préstamo C.',
  NOT: 'NOT Rd, Rs. Complemento a 1 bit a bit.',
  NEG: 'NEG Rd, Rs. Complemento a 2 (−Rs).',
  ABS: 'ABS Rd, Rs. Valor absoluto con signo de 16 bits.',
  SXT: 'SXT Rd, Rs. Extiende el signo del byte bajo (bit 7) a 16 bits.',
  SWAB: 'SWAB Rd, Rs. Intercambia byte alto y byte bajo.',
  CLZ: 'CLZ Rd, Rs. Cuenta ceros iniciales desde el bit 15.',
  MOVI: 'MOVI Rd, #imm8 (−128 a 255). Carga inmediato de 8 bits con extensión de signo.',
  MOVH: 'MOVH Rd, #imm8 (−128 a 255). Carga byte alto preservando el byte bajo.',
  SHL: 'SHL Rd, Rs, #cant (1 a 8) | SHL Rd, Rs, Rc. Desplazamiento lógico a izquierda.',
  LSL: 'LSL Rd, Rs, #cant (1 a 8) | LSL Rd, Rs, Rc. Desplazamiento lógico a izquierda.',
  ROL: 'ROL Rd, Rs, #cant (1 a 8) | ROL Rd, Rs, Rc. Rotación de 16 bits a izquierda.',
  SHR: 'SHR Rd, Rs, #cant (1 a 8) | SHR Rd, Rs, Rc. Desplazamiento lógico a derecha.',
  LSR: 'LSR Rd, Rs, #cant (1 a 8) | LSR Rd, Rs, Rc. Desplazamiento lógico a derecha.',
  ASR: 'ASR Rd, Rs, #cant (1 a 8) | ASR Rd, Rs, Rc. Desplazamiento aritmético (conserva signo).',
  MUL: 'MUL Rd, Rs1, Rs2. Producto de 16 bits bajos (con signo).',
  MULH: 'MULH Rd, Rs1, Rs2. 16 bits altos del producto con signo.',
  MULHU: 'MULHU Rd, Rs1, Rs2. 16 bits altos del producto sin signo.',
  DIV: 'DIV Rd, Rs1, Rs2. Cociente entero con signo (DIVU sin signo).',
  REM: 'REM Rd, Rs1, Rs2. Resto entero con signo (REMU sin signo).',
  MULQ8: 'MULQ8 Rd, Rs1, Rs2. Multiplicación en punto fijo Q7.8 con redondeo.',
  MULQ12: 'MULQ12 Rd, Rs1, Rs2. Multiplicación en punto fijo Q3.12.',
  MULQ14: 'MULQ14 Rd, Rs1, Rs2. Multiplicación en punto fijo Q1.14.',
  MULQ15: 'MULQ15 Rd, Rs1, Rs2. Multiplicación en punto fijo Q0.15.',
  DIVQ8: 'DIVQ8 Rd, Rs1, Rs2. División en punto fijo Q7.8.',
  DIVQ12: 'DIVQ12 Rd, Rs1, Rs2. División en punto fijo Q3.12.',
  DIVQ14: 'DIVQ14 Rd, Rs1, Rs2. División en punto fijo Q1.14.',
  DIVQ15: 'DIVQ15 Rd, Rs1, Rs2. División en punto fijo Q0.15.',
  LD: 'LD Rd, ETIQ. Carga palabra de 16 bits relativa al PC (±256 bytes).',
  ST: 'ST Rs, ETIQ. Almacena palabra de 16 bits relativa al PC (±256 bytes).',
  LEA: 'LEA Rd, ETIQ. Carga dirección efectiva de la etiqueta (no accede a memoria).',
  LDR: 'LDR Rd, Rbase, #offset. Desplazamiento en bytes par (−32 a 30).',
  STR: 'STR Rs, Rbase, #offset. Desplazamiento en bytes par (−32 a 30).',
  LDBL: 'LDBL Rd, Rbase, #offset. Carga byte en Rd[7:0] (offset en bytes −16 a 15).',
  LDBH: 'LDBH Rd, Rbase, #offset. Carga byte en Rd[15:8] preservando Rd[7:0] (−16 a 15).',
  STBL: 'STBL Rs, Rbase, #offset. Guarda Rs[7:0] en byte (offset −16 a 15).',
  STBH: 'STBH Rs, Rbase, #offset. Guarda Rs[15:8] en byte (offset −16 a 15).',
  LDXW: 'LDXW Rd, Rbase, Ridx. Carga palabra en Rbase + 2*Ridx.',
  LDXB: 'LDXB Rd, Rbase, Ridx. Carga byte sin signo en Rbase + Ridx.',
  LDXSB: 'LDXSB Rd, Rbase, Ridx. Carga byte con extensión de signo en Rbase + Ridx.',
  PUSHM: 'PUSHM #máscara (0..255). Apila registros seleccionados (bit i = Ri, R6 es SP).',
  POPM: 'POPM #máscara (0..255). Desapila registros seleccionados desde R6.',
  BR: 'BR[n][z][p] ETIQ. Salto condicional relativo al PC (±256 bytes).',
  BRC: 'BRC ETIQ. Salto condicional si C = 1 relativo al PC (±256 bytes).',
  BRNC: 'BRNC ETIQ. Salto condicional si C = 0 relativo al PC (±256 bytes).',
  JSR: 'JSR ETIQ. Guarda PC en R7 y salta a subrutina (±1024 bytes).',
  JSRR: 'JSRR Rs. Guarda PC en R7 y salta a dirección en Rs.',
  JMP: 'JMP Rs. Salta incondicionalmente a dirección en Rs.',
  RET: 'RET. Retorna de subrutina (equivale a JMP R7).',
  GETC: 'GETC (TRAP x20). Lee un carácter de consola en R0 sin eco.',
  OUT: 'OUT (TRAP x21). Imprime el byte bajo de R0 en consola.',
  PUTS: 'PUTS (TRAP x22). Imprime cadena ASCII terminada en 0 desde dirección R0.',
  IN: 'IN (TRAP x23). Lee un carácter en R0 y hace eco en consola.',
  HALT: 'HALT (TRAP x25). Detiene la ejecución del procesador.',
  '.ORIG': '.ORIG x3000. Define la dirección inicial par de carga del programa.',
  '.FILL': '.FILL valor | ETIQ | MOD-ETIQ. Reserva 16 bits con un valor o dirección.',
  '.BLKW': '.BLKW n. Reserva n palabras de 16 bits (2*n bytes) en cero.',
  '.STRINGZ': '.STRINGZ "texto". Cadena ASCII con terminador nulo (alineada a 16 bits).',
  '.BYTE': '.BYTE b1, b2... Lista de bytes literales (alineado a 16 bits).',
  '.EXTERNAL': '.EXTERNAL MOD-ETIQ. Declara símbolo externo de otro módulo enlazado.',
  '.END': '.END. Marca el fin del código fuente.'
};

const $=id=>document.getElementById(id),hx=(v,n=4)=>((v>>>0)&((1<<(n*4))-1)).toString(16).toUpperCase().padStart(n,'0'),esc=s=>s.replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
const cpu=new Apex3XCPU();
let memReads=0,memWrites=0,prevMem=new Uint8Array(65536);
const rawRd=cpu.rd.bind(cpu),rawRb=cpu.rb.bind(cpu),rawWr=cpu.wr.bind(cpu),rawWb=cpu.wb.bind(cpu);
cpu.rd=a=>{memReads++;return rawRd(a);};
cpu.rb=a=>{memReads++;return rawRb(a);};
cpu.wr=(a,v)=>{memWrites++;return rawWr(a,v);};
cpu.wb=(a,v)=>{memWrites++;return rawWb(a,v);};

let extra=[],img=null,auto=false,prev=new Uint16Array(8),curRow=null;
let breakpoints=new Set(),execHistory=[],listingByAddr=new Map(),lastExecInfo=null,bpPausedAddr=null;
let memSearchHits=[],memSearchIdx=-1;
$('src').value=DEMO;

// ---- Persistencia segura en localStorage (con respaldo en memoria) ----
const safeStorage = (() => {
  const mem = new Map();
  let storageRef = null;
  try {
    const ls = window.localStorage;
    if (ls) {
      const probe = '__apex3x_probe__';
      ls.setItem(probe, '1');
      ls.removeItem(probe);
      storageRef = ls;
    }
  } catch {
    storageRef = null;
  }

  return {
    get(key, fallback = null) {
      try {
        if (storageRef) {
          let val = storageRef.getItem(key);
          if (val === null && key.startsWith('apex3x_')) {
            val = storageRef.getItem(key.replace('apex3x_', 'lc3x_'));
          }
          if (val !== null) {
            mem.set(key, val);
            return val;
          }
        }
      } catch {
        // Fallback silencioso a memoria
      }
      return mem.has(key) ? mem.get(key) : fallback;
    },
    set(key, value) {
      const str = String(value);
      mem.set(key, str);
      try {
        if (storageRef) storageRef.setItem(key, str);
        return true;
      } catch {
        return false;
      }
    },
    remove(key) {
      mem.delete(key);
      try {
        if (storageRef) storageRef.removeItem(key);
      } catch {
        // Ignorar si localStorage no está disponible
      }
    },
    getJSON(key, normalize, fallback) {
      const raw = this.get(key, null);
      if (raw === null || raw === '') return fallback;
      try {
        const parsed = JSON.parse(raw);
        return normalize ? normalize(parsed) : parsed;
      } catch {
        this.remove(key);
        return fallback;
      }
    },
    setJSON(key, obj) {
      try {
        return this.set(key, JSON.stringify(obj));
      } catch {
        return false;
      }
    }
  };
})();

const STORAGE_KEYS = {
  theme: 'apex3x_theme',
  layout: 'apex3x_layout_v1',
  prefs: 'apex3x_prefs_v1'
};

// ---- Preferencias de interfaz (sin guardar programas del usuario) ----
const VALID_BENCH_MODES = new Set(['ambos', 'completo', 'reducido', 'subrutinas']);
const VALID_LST_VIEWS = new Set(['asm', 'hex', 'bin']);
const VALID_CLOCKS = new Set([1, 4, 10, 25]);
const DEFAULT_PREFS = () => ({
  stepLimit: 5000000,
  benchSuite: 'ambos',
  testMaxSteps: 500000,
  testPanelOpen: false,
  editorFontSize: 12.5,
  simClockMHz: 10,
  lstView: 'asm'
});

function normalizePrefs(raw) {
  const def = DEFAULT_PREFS();
  if (!raw || typeof raw !== 'object') return def;

  const stepLimit = Number(raw.stepLimit);
  const testMaxSteps = Number(raw.testMaxSteps);
  const fontSz = Number(raw.editorFontSize);
  const clk = Number(raw.simClockMHz);
  return {
    stepLimit: Number.isInteger(stepLimit) && stepLimit >= 1000 && stepLimit <= 100000000 ? stepLimit : def.stepLimit,
    benchSuite: VALID_BENCH_MODES.has(raw.benchSuite) ? raw.benchSuite : def.benchSuite,
    testMaxSteps: Number.isInteger(testMaxSteps) && testMaxSteps >= 1000 && testMaxSteps <= 50000000 ? testMaxSteps : def.testMaxSteps,
    testPanelOpen: Boolean(raw.testPanelOpen),
    editorFontSize: Number.isFinite(fontSz) ? Math.max(10, Math.min(20, Math.round(fontSz * 2) / 2)) : def.editorFontSize,
    simClockMHz: VALID_CLOCKS.has(clk) ? clk : def.simClockMHz,
    lstView: VALID_LST_VIEWS.has(raw.lstView) ? raw.lstView : def.lstView
  };
}

let uiPrefs = safeStorage.getJSON(STORAGE_KEYS.prefs, normalizePrefs, DEFAULT_PREFS());

function savePrefs() {
  uiPrefs = normalizePrefs(uiPrefs);
  safeStorage.setJSON(STORAGE_KEYS.prefs, uiPrefs);
}

function applyEditorFontSize() {
  $('src').style.fontSize = uiPrefs.editorFontSize + 'px';
  if ($('fontSizeLbl')) $('fontSizeLbl').textContent = uiPrefs.editorFontSize + 'px';
}

function applyPrefs() {
  uiPrefs = normalizePrefs(uiPrefs);
  $('lim').value = String(uiPrefs.stepLimit);
  $('selBenchMode').value = uiPrefs.benchSuite;
  $('tMaxSteps').value = String(uiPrefs.testMaxSteps);
  $('testPanel').classList.toggle('hidden', !uiPrefs.testPanelOpen);
  $('bTestMode').classList.toggle('active', uiPrefs.testPanelOpen);
  if ($('selSimClk')) $('selSimClk').value = String(uiPrefs.simClockMHz);
  document.querySelectorAll('[data-lst-view]').forEach(btn => {
    const active = btn.dataset.lstView === uiPrefs.lstView;
    btn.classList.toggle('on', active);
    btn.setAttribute('aria-selected', active ? 'true' : 'false');
  });
  applyEditorFontSize();
}

// ---- Tema Retro-Moderno (Carbón / Papel) ----
function applyTheme(t){
  const validTheme = t === 'light' ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', validTheme);
  safeStorage.set(STORAGE_KEYS.theme, validTheme);
  $('bTheme').textContent = validTheme === 'dark' ? 'Tema: Carbón' : 'Tema: Papel';
}
applyTheme(safeStorage.get(STORAGE_KEYS.theme, 'dark'));
$('bTheme').onclick = () => {
  const cur = document.documentElement.getAttribute('data-theme') || 'dark';
  applyTheme(cur === 'dark' ? 'light' : 'dark');
};

function copyText(text, onDone) {
  const str = String(text ?? '');
  const finish = (ok) => { if (onDone) onDone(ok); };
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(str).then(() => finish(true)).catch(() => fallbackCopy(str, finish));
    return;
  }
  fallbackCopy(str, finish);
}

function fallbackCopy(str, finish) {
  try {
    const ta = document.createElement('textarea');
    ta.value = str;
    ta.style.position = 'fixed';
    ta.style.opacity = '0';
    document.body.appendChild(ta);
    ta.select();
    const ok = document.execCommand('copy');
    document.body.removeChild(ta);
    finish(ok);
  } catch {
    finish(false);
  }
}

let resolvingBench = false;
async function autoResolveBenchmarkModules(){
  if(resolvingBench) return;
  resolvingBench = true;
  try{
    const res = await fetch('./benchmark/manifest.json', { cache: 'no-store' });
    if(!res.ok) return;
    const manifest = await res.json();
    const existing = new Set(extra.map(m => m.name.toUpperCase()));
    const missing = manifest.modules.filter(f => !existing.has(f.replace(/\.asm$/, '').toUpperCase()));
    if(!missing.length) return;
    const fetched = await Promise.all(missing.map(async file => {
      const r = await fetch('./benchmark/' + file, { cache: 'no-store' });
      if(!r.ok) throw Error('No se pudo cargar ' + file);
      return { name: file.replace(/\.asm$/, ''), src: await r.text() };
    }));
    extra = [...extra, ...fetched];
    assemble();
    if(img && !img.errors.length){
      benchmarkLoaded = true;
      $('benchStatus').textContent = `Módulos del benchmark enlazados automáticamente (${img.modules.length} módulos, ${img.size.toLocaleString('es-AR')} B).`;
    }
  } finally {
    resolvingBench = false;
  }
}

function updateSrcHint() {
  const ta = $('src');
  if (!ta || !$('srcHint')) return;
  const pos = ta.selectionStart || 0;
  const text = ta.value;
  const lineStart = text.lastIndexOf('\n', pos - 1) + 1;
  const lineEndRaw = text.indexOf('\n', pos);
  const lineEnd = lineEndRaw < 0 ? text.length : lineEndRaw;
  const line = text.slice(lineStart, lineEnd).split(';')[0].trim();
  if (!line) {
    $('srcHint').textContent = 'LDR/STR toman desplazamiento en bytes (par, −32 a 30); LDBL/LDBH/STBL/STBH en bytes (−16 a 15). Saltos y LD/ST/LEA usan etiquetas.';
    return;
  }
  const tokens = line.split(/[\s,]+/).filter(Boolean);
  let key = (tokens[0] || '').replace(/:$/, '').toUpperCase();
  if (!APEX3X_SYNTAX_HINTS[key] && !/^BR[NZP]{0,3}$/.test(key) && tokens[1]) {
    key = tokens[1].toUpperCase();
  }
  if (/^BR[NZP]{0,3}$/.test(key)) key = 'BR';
  $('srcHint').textContent = APEX3X_SYNTAX_HINTS[key]
    || 'Tip: usá etiquetas al inicio de línea (ETIQUETA ADD R0, R1, #1) y .ORIG/.END para delimitar el programa.';
}

function jumpToSourceLine(lineNum) {
  const ta = $('src');
  const lines = ta.value.split('\n');
  const idx = Math.max(0, Math.min(lines.length - 1, lineNum - 1));
  let start = 0;
  for (let i = 0; i < idx; i++) start += lines[i].length + 1;
  const end = start + lines[idx].length;
  ta.focus();
  ta.setSelectionRange(start, end);
  const lineH = uiPrefs.editorFontSize * 1.55;
  ta.scrollTop = Math.max(0, idx * lineH - ta.clientHeight / 3);
  updateSrcHint();
}

function getListingTextForView(view) {
  if (!img) return '';
  if (view === 'hex') return Apex3XAssembler.toHex(img);
  if (view === 'bin') {
    const out = [];
    if (img.listing && img.listing.length) {
      for (const it of img.listing) {
        it.w.forEach((w, idx) => {
          const bin = w.toString(2).padStart(16, '0').replace(/(.{4})/g, '$1 ').trim();
          const addr = (it.addr + idx * 2) & 0xFFFF;
          out.push(`x${hx(addr)}  ${bin}  (x${hx(w)})${idx === 0 ? '  ' + it.src : ''}`);
        });
      }
    } else {
      for (let k = 0; k < img.size; k += 2) {
        const w = img.bytes[k] | ((img.bytes[k + 1] || 0) << 8);
        const bin = w.toString(2).padStart(16, '0').replace(/(.{4})/g, '$1 ').trim();
        out.push(`x${hx((img.origin + k) & 0xFFFF)}  ${bin}  (x${hx(w)})`);
      }
    }
    return out.join('\n');
  }
  return (img.listing || []).map(it => {
    const words = it.w.slice(0, 4).map(w => hx(w)).join(' ') + (it.w.length > 4 ? '…' : '');
    return `x${hx(it.addr)}  ${words.padEnd(20, ' ')}  ${it.src}`;
  }).join('\n');
}

function updateBpSummary() {
  if ($('bpSummary')) {
    $('bpSummary').textContent = `${breakpoints.size} BP`;
  }
}

function toggleBreakpoint(addr) {
  if (breakpoints.has(addr)) breakpoints.delete(addr);
  else breakpoints.add(addr);
  updateBpSummary();
  const row = $('L' + addr);
  if (row) row.classList.toggle('bp', breakpoints.has(addr));
}

function renderListing() {
  const lstEl = $('lst');
  if (!img) {
    lstEl.innerHTML = '<div class="help" style="padding:8px 12px">Sin programa ensamblado o cargado.</div>';
    curRow = null;
    updateBpSummary();
    return;
  }

  if (uiPrefs.lstView === 'hex' || uiPrefs.lstView === 'bin') {
    const content = getListingTextForView(uiPrefs.lstView) || '(Sin palabras de código)';
    lstEl.innerHTML = `<pre class="lst-pre m">${esc(content)}</pre>`;
    curRow = null;
    updateBpSummary();
    return;
  }

  if (!img.listing || !img.listing.length) {
    lstEl.innerHTML = '<div class="help" style="padding:8px 12px">Programa binario/hex cargado (cambiá a vista HEX o BIN para inspeccionar palabras).</div>';
    curRow = null;
    updateBpSummary();
    return;
  }

  lstEl.innerHTML = img.listing.map(it => {
    const isBp = breakpoints.has(it.addr) ? ' bp' : '';
    const words = it.w.slice(0, 2).map(w => hx(w)).join(' ') + (it.w.length > 2 ? '…' : '');
    const extraWords = it.w.length > 2 ? ` · Palabras: ${it.w.map(w => hx(w)).join(' ')}` : '';
    return `<div class="row${isBp}" id="L${it.addr}" data-addr="${it.addr}" title="Clic para alternar breakpoint en x${hx(it.addr)}${esc(extraWords)}"><span class="bp-dot" aria-hidden="true"></span><span class="a">x${hx(it.addr)}</span><span class="w">${words}</span><span>${esc(it.src)}</span></div>`;
  }).join('');

  if (curRow) curRow.classList.remove('cur');
  curRow = $('L' + cpu.pc);
  if (curRow) curRow.classList.add('cur');
  updateBpSummary();
}

function say(html){$('msg').innerHTML=html}
function assemble(){
  const r=Apex3XAssembler.link([{name:'principal',src:$('src').value},...extra]);
  if(r.errors.length){
    img=null;
    listingByAddr.clear();
    say(r.errors.map(e=>{
      const m=/Línea\s+(\d+):/i.exec(e);
      if(m) return `<div class="e err-jump" data-line="${m[1]}" title="Clic para ir a la línea ${m[1]}">${esc(e)}</div>`;
      return '<div class="e">'+esc(e)+'</div>';
    }).join(''));
    renderListing();
    refreshTestSymbols();
    render();
    if(!resolvingBench && r.errors.some(e=>e.includes('símbolo externo no resuelto:'))){
      autoResolveBenchmarkModules();
    }
    return;
  }
  img=r;
  listingByAddr = new Map((r.listing || []).map(it => [it.addr, it]));
  for (const bp of [...breakpoints]) {
    if (!listingByAddr.has(bp)) breakpoints.delete(bp);
  }
  reset();
  renderListing();
  say('<span class="k">Ensamblado correcto: '+r.size+' bytes desde x'+hx(r.origin)+'.</span>');
  $('maddr').value=hx(r.origin);
  refreshTestSymbols();
  render();
}

function reset(){
  auto=false;
  bpPausedAddr=null;
  lastExecInfo=null;
  execHistory=[];
  memReads=0;
  memWrites=0;
  cpu.reset();
  prev=new Uint16Array(8);
  if(img){cpu.load(img.origin,img.bytes)}
  prevMem.set(cpu.mem);
  $('bRun').classList.remove('on');
  $('bRun').textContent='Ejecutar';
  render();
}

const OP_CLASSES = {
  ALU: new Set(['ADD','SUB','AND','ADC','SBC','NOT','NEG','ABS','SXT','SWAB','CLZ','SHL','SHR','MUL','MULH','MULHU','DIV','REM','DIVU','REMU','MULQ','DIVQ']),
  CTRL: new Set(['BR','BRC','BRNC','JSR','JMP','RET','RTI']),
  MEM: new Set(['LD','ST','LEA','LDR','STR','LDBL','LDBH','STBL','STBH','LDX','PUSHM','POPM']),
  CONST: new Set(['MOVI','MOVH']),
  SYS: new Set(['TRAP'])
};

function formatSimTime(instrCount, mhz) {
  if (!instrCount) return '0 µs';
  const us = instrCount / mhz;
  if (us < 1) return Math.round(us * 1000) + ' ns';
  if (us < 1000) return us.toFixed(1) + ' µs';
  if (us < 1e6) return (us / 1000).toFixed(2) + ' ms';
  return (us / 1e6).toFixed(3) + ' s';
}

function stepTracked() {
  if (cpu.halted || cpu.waiting) return false;
  bpPausedAddr = null;
  const pc = cpu.pc;
  const ir = cpu.mem[pc] | (cpu.mem[(pc + 1) & 0xFFFF] << 8);
  const item = listingByAddr.get(pc);
  lastExecInfo = { pc, ir, src: item ? item.src : '' };
  const ok = cpu.step();
  if (!cpu.err || cpu.count > 0) {
    execHistory.unshift({ step: cpu.count, pc, ir, src: item ? item.src : '' });
    if (execHistory.length > 32) execHistory.pop();
  }
  return ok;
}

function renderExecHistory() {
  if ($('histCount')) $('histCount').textContent = String(execHistory.length);
  if (!$('execHistory')) return;
  if (!execHistory.length) {
    $('execHistory').innerHTML = '<div class="help" style="margin:2px 0">Ejecutá pasos para ver las últimas instrucciones.</div>';
    return;
  }
  $('execHistory').innerHTML = execHistory.map(h =>
    `<div class="exec-hist-row" data-jump-addr="${h.pc}" title="Clic para centrar memoria en x${hx(h.pc)}"><span>#${h.step}</span><span>x${hx(h.pc)}</span><span>x${hx(h.ir)}</span><span>${esc(h.src || '')}</span></div>`
  ).join('');
}

function render(){
  $('regs').innerHTML=[...cpu.r].map((v,i)=>'<div class="reg'+(v!==prev[i]?' ch':'')+'" data-reg="R'+i+'" data-reg-hex="x'+hx(v)+'" title="Clic para copiar x'+hx(v)+'"><b>R'+i+(i===6?' pila':i===7?' retorno':'')+'</b><span><span class="h">x'+hx(v)+'</span><small>'+((v<<16)>>16)+'</small></span></div>').join('');
  $('flags').innerHTML=['N','Z','P','C'].map(k=>'<span class="f m'+(cpu[k.toLowerCase()]?' on':'')+'">'+k+'</span>').join('')+'<span class="f pc m">PC x'+hx(cpu.pc)+'</span>';
  $('sCnt').textContent=cpu.count.toLocaleString('es-AR');
  if ($('sSo')) $('sSo').textContent=cpu.so.toLocaleString('es-AR');
  if ($('sTot')) $('sTot').textContent=cpu.total.toLocaleString('es-AR');
  if ($('sCycles')) $('sCycles').textContent=(cpu.cycles || cpu.total).toLocaleString('es-AR');
  $('sSize').textContent=cpu.size+' bytes';$('sDat').textContent=cpu.dcnt+' bytes';$('sStk').textContent=(Apex3XCPU.STACK-cpu.minSP)+' bytes';
  if ($('sMemAcc')) $('sMemAcc').textContent = `${memReads.toLocaleString('es-AR')} L / ${memWrites.toLocaleString('es-AR')} E`;
  if ($('sSimTime')) $('sSimTime').textContent = formatSimTime(cpu.cycles || cpu.total, uiPrefs.simClockMHz);

  let statusHtml = '';
  if (cpu.err) {
    const loc = lastExecInfo ? ` en x${hx(lastExecInfo.pc)} (x${hx(lastExecInfo.ir)}${lastExecInfo.src ? ' · ' + esc(lastExecInfo.src) : ''})` : '';
    statusHtml = `<span style="color:var(--err);font-weight:600">Error${loc}: ${esc(cpu.err)}</span>`;
  } else if (cpu.halted) {
    statusHtml = 'Detenida';
  } else if (cpu.waiting) {
    statusHtml = 'Esperando entrada';
  } else if (bpPausedAddr !== null) {
    statusHtml = `<span style="color:var(--am);font-weight:600">Breakpoint en x${hx(bpPausedAddr)}</span>`;
  } else if (auto) {
    statusHtml = 'En ejecución';
  } else if (img) {
    statusHtml = 'Lista';
  } else {
    statusHtml = 'Sin programa';
  }
  $('sSt').innerHTML = statusHtml;

  const totalOps = cpu.count || 0;
  if ($('opBreakdown')) {
    if (!totalOps) {
      $('opBreakdown').innerHTML = '';
    } else {
      const catCounts = { 'ALU / Bits': 0, 'Control / Saltos': 0, 'Memoria / Pila': 0, 'Constantes': 0, 'E/S y Sistema': 0 };
      let extCount = 0;
      for (const [k, v] of Object.entries(cpu.hist)) {
        if (APEX3X_NEW_OPCODES.has(k)) extCount += v;
        if (OP_CLASSES.ALU.has(k)) catCounts['ALU / Bits'] += v;
        else if (OP_CLASSES.CTRL.has(k)) catCounts['Control / Saltos'] += v;
        else if (OP_CLASSES.MEM.has(k)) catCounts['Memoria / Pila'] += v;
        else if (OP_CLASSES.CONST.has(k)) catCounts['Constantes'] += v;
        else catCounts['E/S y Sistema'] += v;
      }
      const extPct = ((100 * extCount) / totalOps).toFixed(1);
      $('opBreakdown').innerHTML = Object.entries(catCounts)
        .filter(([, v]) => v > 0)
        .map(([lbl, v]) => {
          const pct = ((100 * v) / totalOps).toFixed(1);
          return `<div class="hb m"><span>${lbl}</span><i style="width:${Math.max(4, pct)}%"></i><em>${v} (${pct}%)</em></div>`;
        }).join('') + `<div class="help" style="margin-top:2px">Extensiones Apex-3X: ${extCount.toLocaleString('es-AR')} (${extPct}%)</div>`;
    }
  }

  const conEl = $('con');
  if (conEl) {
    const wasNearBottom = (conEl.scrollHeight - conEl.scrollTop - conEl.clientHeight) < 50;
    conEl.textContent = cpu.out;
    if (wasNearBottom || cpu.waiting) {
      conEl.scrollTop = conEl.scrollHeight;
    }
  }

  if ($('lstCurInfo')) {
    const curItem = listingByAddr.get(cpu.pc);
    $('lstCurInfo').textContent = img
      ? `PC x${hx(cpu.pc)}${curItem ? ' · ' + curItem.src : ''}${breakpoints.has(cpu.pc) ? ' [BP]' : ''}`
      : '';
  }
  if (uiPrefs.lstView === 'asm') {
    if(curRow)curRow.classList.remove('cur');curRow=$('L'+cpu.pc);if(curRow){curRow.classList.add('cur');curRow.scrollIntoView({block:'nearest',behavior:'smooth'})}
  }
  renderExecHistory();
  mem();
}

function mem(){
  let a=parseInt($('maddr').value,16)||0;a&=0xFFF0;let o='';
  const hitSet = new Set(memSearchHits);
  for(let r=0;r<16;r++,a=(a+16)&0xFFFF){
    o+='<span class="ad">x'+hx(a)+'</span>  ';let t='';
    for(let k=0;k<16;k++){
      const addr=(a+k)&0xFFFF;
      const b=cpu.mem[addr];
      const isPc=addr===cpu.pc||addr===((cpu.pc+1)&0xFFFF);
      const isCh=b!==prevMem[addr];
      const isHit=hitSet.has(addr);
      const cls=['mem-byte',isPc?'pc':isCh?'mem-ch':'',isHit?'mem-hit':''].filter(Boolean).join(' ');
      o+=`<span class="${cls}" data-maddr="${addr}" title="x${hx(addr)}: x${hx(b,2)} (${b}) — clic para copiar">${hx(b,2)}</span>`+(k===7?'  ':' ');
      t+=b>31&&b<127?esc(String.fromCharCode(b)):'.';
    }
    o+=' <span class="asc">'+t+'</span>\n';
  }
  $('mem').innerHTML=o;
}

function run(){
  auto=true;bpPausedAddr=null;$('bRun').classList.add('on');$('bRun').textContent='Pausar';
  (function tick(){
    if(!auto)return;
    prev=Uint16Array.from(cpu.r);
    prevMem.set(cpu.mem);
    for(let i=0;i<4000&&!cpu.halted&&!cpu.waiting;i++){
      stepTracked();
      const L=+$('lim').value||5e6;
      if(cpu.count>=L){cpu.halted=true;cpu.err='límite de '+L.toLocaleString('es-AR')+' pasos; ¿bucle infinito?';break;}
      if(!cpu.halted && !cpu.waiting && breakpoints.has(cpu.pc)){
        auto=false;
        bpPausedAddr=cpu.pc;
        break;
      }
    }
    if(!auto || cpu.halted || cpu.waiting){
      if(cpu.halted || bpPausedAddr !== null) auto=false;
      $('bRun').classList.toggle('on',auto);
      $('bRun').textContent=auto?'Pausar':'Ejecutar';
      render();
      return;
    }
    render();requestAnimationFrame(tick);
  })();
}

// ---- Modo Prueba de Módulos (Harness Unitario) ----
function parseNum16(s, allowEmpty = false){
  s = (s ?? '').toString().trim();
  if(!s) return allowEmpty ? 0 : NaN;
  let val = NaN;
  if(/^#[+-]?\d+$/.test(s)){
    val = parseInt(s.slice(1), 10);
  } else if(/^(?:0x|x)[0-9a-f]+$/i.test(s)){
    val = parseInt(s.replace(/^(?:0x|x)/i, ''), 16);
  } else if(/^[+-]?\d+$/.test(s)){
    val = parseInt(s, 10);
  } else if(/^[0-9a-f]+$/i.test(s) && /[a-f]/i.test(s)){
    val = parseInt(s, 16);
  } else {
    return NaN;
  }
  if(!Number.isFinite(val) || val < -32768 || val > 65535) return NaN;
  return val & 0xFFFF;
}

function collectAllSymbols(){
  const syms = {};
  if(img && img.syms){
    for(const [k,v] of Object.entries(img.syms)) syms['principal:'+k] = v;
  }
  if(img && img.allSyms){
    for(const [k,v] of Object.entries(img.allSyms)) syms[k] = v;
  }
  return syms;
}

function refreshTestSymbols(){
  const sel = $('selEntry');
  const syms = collectAllSymbols();
  const entries = Object.entries(syms);
  if(!entries.length){
    sel.innerHTML = '<option value="">(Sin etiquetas)</option>';
  } else {
    sel.innerHTML = entries.map(([k,v]) => '<option value="'+v+'">'+esc(k)+' (x'+hx(v)+')</option>').join('');
  }
  $('testModsInfo').textContent = extra.length
    ? `${extra.length + 1} módulos enlazados (suite benchmark Apex-3X).`
    : 'Usando el código del editor principal.';
}

function findSymAddr(pattern){
  const syms = collectAllSymbols();
  const up = pattern.toUpperCase();
  const exact = Object.keys(syms).find(k => k.toUpperCase() === up);
  if(exact !== undefined) return syms[exact];
  const suffix = Object.keys(syms).find(k => k.toUpperCase().endsWith(':' + up));
  return suffix !== undefined ? syms[suffix] : undefined;
}

const APEX3X_NEW_OPCODES = new Set([
  'BRC','BRNC','LDBL','LDBH','STBL','STBH','LDX','PUSHM','POPM','MOVI','MOVH',
  'SHL','SHR','SUB','ADC','MUL','MULQ','DIV','DIVQ','NEG','ABS','SXT','SWAB','CLZ'
]);

const BENCH_OPS = [
  { id: 1,  name: 'Reducción de argumento (Q3.12)',       mod: 'g20_Cordic_reduccion_de_argumento', sym: 'REDUCCION_ARGUMENTO',   r0: 9651,          r1: 0,      q: 12, fmt: 'Q3.12',  exp: -3217, tol: 2 },
  { id: 2,  name: 'Seno Taylor (60° -> Q3.12)',           mod: 'g21_senotaylor_subrutina',          sym: 'CALCULAR_SENO',         r0: 600,           r1: 0,      q: 12, fmt: 'Q3.12',  exp: 3547, tol: 4 },
  { id: 3,  name: 'Seno Tabla (Q3.12 -> Q1.14)',          mod: 'g22_Tabla_SIN_y_COS',               sym: 'SENO_TABLA',            r0: 4289,          r1: 0,      q: 14, fmt: 'Q1.14',  exp: 14188, tol: 8 },
  { id: 4,  name: 'Seno Chebyshev-Padé (Q3.12 -> Q1.14)',mod: 'g30_seno_cheb_pade',                sym: 'SEN_CHEB_PADE',         r0: 4289,          r1: 0,      q: 14, fmt: 'Q1.14',  exp: 14188, tol: 8 },
  { id: 5,  name: 'Coseno Tabla (Q3.12 -> Q1.14)',        mod: 'g22_Tabla_SIN_y_COS',               sym: 'COSENO_TABLA',          r0: 4289,          r1: 0,      q: 14, fmt: 'Q1.14',  exp: 8193, tol: 8 },
  { id: 6,  name: 'Cambio de base a Hex',                 mod: 'g24_conversor_lc3_max',             sym: 'SUB_BASE_HEX',          r0: 1342,          r1: 0,      q: 0,  fmt: 'consola', expOut: 'Hexadecimal: 053E' },
  { id: 7,  name: 'Cambio de base a Bin',                 mod: 'g24_conversor_lc3_max',             sym: 'SUB_BASE_BIN',          r0: 0xFBCA,        r1: 0,      q: 0,  fmt: 'consola', expOut: 'Binario: 1111101111001010' },
  { id: 8,  name: 'SQRT Non-Restoring (Q7.8 -> Q6.9)',    mod: 'g23_modulo_sqrt_nr',                sym: 'SQRT_NR',               r0: 1115,          r1: 0,      q: 9,  fmt: 'Q6.9',   exp: 1069, tol: 2 },
  { id: 9,  name: 'SQRT Newton-Raphson (DQ15.16)',        mod: 'g9_sqrt_nr_dq16',                   sym: 'SQRT_NR_DQ16',          r0: 4,             r1: 23395,  q: 16, fmt: 'Q15.16', exp: 2, tol: 0, exp1: 5724, tol1: 256 },
  { id: 10, name: 'Exponenciación (Q3.12 -> Q7.8)',       mod: 'g6_EXP',                            sym: 'EXP_Q3_12',             r0: 4096,          r1: 0,      q: 8,  fmt: 'Q7.8',   exp: 696, tol: 1 },
  { id: 11, name: 'Potencia Mul. Sucesivas (Q7.8)',       mod: 'g5_Mul_Sucesiva_POW',               sym: 'MUL_SUCESIVA_POW',      r0: (-512)&0xFFFF, r1: 5,      q: 8,  fmt: 'Q7.8',   exp: -8192, tol: 2 },
  { id: 12, name: 'Potencia Exp. Binaria (int)',          mod: 'g4_potencia',                       sym: 'EXP_RAPIDA',            r0: (-2)&0xFFFF,   r1: 5,      q: 0,  fmt: 'int',    exp: -32, tol: 0 },
  { id: 13, name: 'Multiplicación CORDIC (Q7.8)',         mod: 'g19_cordic_multiplicacion',         sym: 'CORDIC_MUL',            r0: 0x0DD4,        r1: 0xF8C3, q: 8,  fmt: 'Q7.8',   exp: -25624, tol: 1 },
  { id: 14, name: 'Multiplicación Shift-Suma (DQ15.16)',  mod: 'g3_MultiplicacionSHIFTandADD',      sym: 'MULTIPLICARSHIFTANDADD',r0: 0x0DD4,        r1: 0xF8C3, q: 16, fmt: 'Q15.16', exp: -6559620, tol: 0, exp32: true },
  { id: 15, name: 'Multiplicación Booth (Q7.8)',          mod: 'g18_booth',                         sym: 'MULT_BOOTH',            r0: 0x0DD4,        r1: 0xF8C3, q: 8,  fmt: 'Q7.8',   exp: -25624, tol: 1 },
  { id: 16, name: 'División Larga (Q7.8)',                mod: 'g10_division_larga',                sym: 'DIV_LONG',              r0: 1630,          r1: 828,    q: 8,  fmt: 'Q7.8',   exp: 504, tol: 1 },
  { id: 17, name: 'División Newton-Raphson (Q7.8)',       mod: 'g12_subrutina_grupo_12',            sym: 'DIV_NEWTON',            r0: 1630,          r1: 828,    q: 8,  fmt: 'Q7.8',   exp: 504, tol: 2 },
  { id: 18, name: 'División CORDIC (Q0.15)',              mod: 'g1_cordic_division',                sym: 'CORDIC_DIV',            r0: 0x2000,        r1: 0x599A, q: 15, fmt: 'Q0.15',  exp: 11703, tol: 2 },
  { id: 19, name: 'Logaritmo Borchardt (Q8.7)',           mod: 'g14_log_borchardt_q8_7',            sym: 'LN_GENERAL_Q8_7',       r0: 0x0100,        r1: 0,      q: 7,  fmt: 'Q8.7',   exp: 89, tol: 0 },
  { id: 20, name: 'Logaritmo CORDIC (Q3.12)',             mod: 'g11_CORDICLog',                     sym: 'CORDIC_LOG_BASE',       r0: 0x2000,        r1: 0,      q: 12, fmt: 'Q3.12',  exp: 2839, tol: 2 },
  { id: 21, name: 'Máximo Común Divisor (int)',           mod: 'g7_mcd',                            sym: 'MCD',                   r0: 48,            r1: 18,     q: 0,  fmt: 'int',    exp: 6, tol: 0 },
  { id: 22, name: 'Mínimo Común Múltiplo (int)',          mod: 'g7_mcm',                            sym: 'MCM',                   r0: 16,            r1: 38,     q: 0,  fmt: 'int',    exp: 304, tol: 0 },
  { id: 23, name: 'Conversión Q3.12 -> Q7.8',             mod: 'g15_G15_Q312_Q78',                  sym: 'G15_Q312_Q78',          r0: 21980,         r1: 0,      q: 8,  fmt: 'Q7.8',   exp: 1374, tol: 1 },
];

let benchmarkLoaded = false;
let lastBenchReport = null;
let prevBenchReport = null;

function formatBenchExpected(op){
  if(op.expOut !== undefined) return `"${op.expOut}"`;
  if(op.exp32) return `${op.exp} (±${op.tol ?? 0})`;
  if(op.exp1 !== undefined){
    const t0 = op.tol ? `±${op.tol}` : '±0';
    const t1 = op.tol1 ? `±${op.tol1}` : '±0';
    return `R0:${op.exp} (${t0}) · R1:${op.exp1} (${t1})`;
  }
  return `${op.exp} (±${op.tol ?? 0})`;
}

function formatBenchResult(r0, r1, out, op){
  const s16 = v => (v << 16) >> 16;
  if(op.fmt === 'consola'){
    const txtOut = (out || '').trim().replace(/\s+/g, ' ');
    return txtOut || `x${hx(r0)} (${s16(r0)})`;
  }
  if(op.exp32){
    const val32 = ((r0 << 16) | (r1 & 0xFFFF)) >> 0;
    const fval = val32 / 65536;
    return `${val32} (x${hx(r0)}:${hx(r1)} · ${fval.toFixed(5)})`;
  }
  if(op.exp1 !== undefined){
    const val = (s16(r0) * 65536 + (r1 & 0xFFFF)) / 65536;
    return `R0:${s16(r0)} · R1:${s16(r1)} (${val.toFixed(5)})`;
  }
  if(op.q === 0) return `${s16(r0)} (x${hx(r0)})`;
  const val = s16(r0) / (1 << op.q);
  return `${s16(r0)} (x${hx(r0)} · ${Number(val.toFixed(6))})`;
}

function renderBenchOpsTable(){
  if(!lastBenchReport || !lastBenchReport.ops || !lastBenchReport.ops.length){
    $('bmOpsWrap').classList.add('hidden');
    $('bmOpsBody').innerHTML = '';
    return;
  }
  $('bmOpsWrap').classList.remove('hidden');
  const allOps = lastBenchReport.ops;
  const sumOps = allOps.reduce((a, x) => a + x.count, 0);
  const sumSo = allOps.reduce((a, x) => a + (x.so || 0), 0);
  const sumTot = allOps.reduce((a, x) => a + (x.total ?? (x.count + (x.so || 0))), 0);
  const passOps = allOps.filter(x => x.ok).length;
  const maxStk = allOps.reduce((a, x) => Math.max(a, x.stack), 0);

  const q = ($('bmOpsFilter') ? $('bmOpsFilter').value : '').trim().toLowerCase();
  const st = $('bmOpsStatusFilter') ? $('bmOpsStatusFilter').value : 'all';
  const filtered = allOps.filter(op => {
    if (st === 'ok' && !op.ok) return false;
    if (st === 'fail' && op.ok) return false;
    if (q && !(`${op.id} ${op.name} ${op.mod} ${op.sym} ${op.expectedText || ''} ${op.result || ''} ${op.estado || ''}`.toLowerCase().includes(q))) return false;
    return true;
  });

  $('bmOpsSummary').textContent = `${passOps}/${allOps.length} PASS · ${sumTot.toLocaleString('es-AR')} instr. totales (${sumOps.toLocaleString('es-AR')} usuario + ${sumSo.toLocaleString('es-AR')} SO) · máx. pila ${maxStk} B` +
    (filtered.length !== allOps.length ? ` (mostrando ${filtered.length})` : '');

  $('bmOpsBody').innerHTML = filtered.map(op => {
    const badge = op.estado || (op.ok ? 'PASS' : 'FAIL');
    const cls = badge === 'PASS' ? 'pass' : badge === 'ERR' ? 'err' : 'fail';
    return `
    <tr>
      <td>${op.id}</td>
      <td>${esc(op.name)}</td>
      <td>${esc(op.mod)}:${esc(op.sym)}</td>
      <td class="num">${op.modSize != null ? op.modSize.toLocaleString('es-AR') : '—'}</td>
      <td class="num">${op.count.toLocaleString('es-AR')}</td>
      <td class="num">${(op.so || 0).toLocaleString('es-AR')}</td>
      <td class="num">${(op.total ?? (op.count + (op.so || 0))).toLocaleString('es-AR')}</td>
      <td class="num">${op.dcnt.toLocaleString('es-AR')}</td>
      <td class="num">${op.stack.toLocaleString('es-AR')}</td>
      <td>${esc(op.expectedText || '—')}</td>
      <td>${esc(op.result)}</td>
      <td><span class="bm-badge ${cls}">${badge}</span></td>
      <td><button type="button" class="bm-act-btn" data-load-bench-op="${op.id}" title="Cargar esta operación en la prueba unitaria">Probar</button></td>
    </tr>
  `;
  }).join('') || '<tr><td colspan="13" style="text-align:center;color:var(--mu)">Sin coincidencias con el filtro.</td></tr>';
}

function renderMetricsPanel(data){
  const so = data.so || 0;
  const tot = data.total ?? (data.count + so);
  $('benchMetrics').classList.remove('hidden');
  $('bmInstr').textContent = tot.toLocaleString('es-AR');
  if ($('bmInstrUser')) $('bmInstrUser').textContent = data.count.toLocaleString('es-AR');
  if ($('bmInstrSo')) $('bmInstrSo').textContent = so.toLocaleString('es-AR');
  if ($('bmCycles')) $('bmCycles').textContent = (data.cycles ?? tot).toLocaleString('es-AR');
  $('bmInstrSub').textContent = data.instrSub || '';
  $('bmSize').textContent = data.size.toLocaleString('es-AR') + ' B';
  $('bmSizeSub').textContent = data.sizeSub || '';
  $('bmData').textContent = data.dcnt.toLocaleString('es-AR') + ' B';
  $('bmDataSub').textContent = data.dataSub || '';
  $('bmStack').textContent = data.picoPila.toLocaleString('es-AR') + ' B';
  $('bmStackSub').textContent = data.stackSub || '';

  if ($('benchDiff')) {
    if (prevBenchReport && prevBenchReport.modo === data.modo) {
      const fmtDelta = (d, unit = '') => (d > 0 ? `+${d.toLocaleString('es-AR')}` : d.toLocaleString('es-AR')) + unit;
      const prevTot = prevBenchReport.total ?? (prevBenchReport.count + (prevBenchReport.so || 0));
      const dInstr = tot - prevTot;
      const dSize = data.size - prevBenchReport.size;
      const dStk = data.picoPila - prevBenchReport.picoPila;
      $('benchDiff').textContent = `Comparación vs ejecución anterior (${data.modo}): ${fmtDelta(dInstr, ' instr. tot.')}, ${fmtDelta(dSize, ' B código')}, ${fmtDelta(dStk, ' B pila')}.`;
      $('benchDiff').classList.remove('hidden');
    } else {
      $('benchDiff').classList.add('hidden');
    }
  }

  const entries = Object.entries(data.hist || {}).sort((a,b) => b[1] - a[1]);
  const total = entries.reduce((acc, [,v]) => acc + v, 0) || 1;
  const maxV = entries.length ? entries[0][1] : 1;
  let newCnt = 0;
  for(const [k,v] of entries) if(APEX3X_NEW_OPCODES.has(k)) newCnt += v;
  const newPct = ((100 * newCnt) / total).toFixed(1);
  $('bmNewOps').textContent = `Opcodes nuevos Apex-3X ejecutados: ${newCnt.toLocaleString('es-AR')} de ${total.toLocaleString('es-AR')} (${newPct}%).`;
  $('bmHist').innerHTML = entries.map(([k,v]) => {
    const pct = ((100 * v) / total).toFixed(1);
    const w = Math.max(3, (100 * v) / maxV);
    const tag = APEX3X_NEW_OPCODES.has(k) ? ' *' : '';
    return `<div class="hb m"><span>${esc(k + tag)}</span><i style="width:${w}%"></i><em>${v.toLocaleString('es-AR')} (${pct}%)</em></div>`;
  }).join('') || '<div class="help">Sin instrucciones ejecutadas.</div>';

  $('bmOut').textContent = data.out ? data.out : '(Sin salida en consola)';

  renderBenchOpsTable();
  renderBenchModuleProfile(data);

  if(data.modules && data.modules.length){
    $('bmModsWrap').classList.remove('hidden');
    $('bmModsCount').textContent = data.modules.length;
    $('bmModsGrid').innerHTML = data.modules.map(m => `
      <div class="bm-mod-item">
        <span>${esc(m.name)}</span>
        <span>x${hx(m.base)} · ${m.size} B</span>
      </div>
    `).join('');
  } else {
    $('bmModsWrap').classList.add('hidden');
  }
}

function renderBenchModuleProfile(data){
  const wrap = $('bmModProfWrap');
  const body = $('bmModProfBody');
  const summary = $('bmModProfSummary');
  if(!wrap || !body || !summary) return;
  const rows = data && data.moduleProfile;
  if(!rows || !rows.length){
    wrap.classList.add('hidden');
    body.innerHTML = '';
    return;
  }
  wrap.classList.remove('hidden');
  const sumInstr = rows.reduce((a, r) => a + r.instr, 0);
  const modCount = rows.filter(r => !r.isOther).length;
  summary.textContent = `${modCount} módulos · suma: ${sumInstr.toLocaleString('es-AR')} instr. de usuario`;
  body.innerHTML = rows.map((r, i) => `
    <tr>
      <td>${i + 1}</td>
      <td>${esc(r.name)}</td>
      <td class="num">${r.instr.toLocaleString('es-AR')}</td>
      <td class="num">${r.pct.toFixed(2).replace('.', ',')}%</td>
      <td class="num">${r.calls.toLocaleString('es-AR')}</td>
    </tr>
  `).join('');
}

async function loadBenchmark(){
  $('benchStatus').textContent = 'Cargando 38 módulos del benchmark...';
  const res = await fetch('./benchmark/manifest.json', { cache: 'no-store' });
  if(!res.ok) throw Error('No se pudo cargar ./benchmark/manifest.json');
  const manifest = await res.json();
  const [mainSrc, ...modSrcs] = await Promise.all([
    fetch('./benchmark/' + manifest.main, { cache: 'no-store' }).then(r => {
      if(!r.ok) throw Error('No se pudo cargar ' + manifest.main);
      return r.text();
    }),
    ...manifest.modules.map(async file => {
      const r = await fetch('./benchmark/' + file, { cache: 'no-store' });
      if(!r.ok) throw Error('No se pudo cargar ' + file);
      return { name: file.replace(/\.asm$/, ''), src: await r.text() };
    })
  ]);
  $('src').value = mainSrc;
  extra = modSrcs;
  assemble();
  if(!img || img.errors.length){
    benchmarkLoaded = false;
    throw Error('Error al ensamblar el benchmark.');
  }
  benchmarkLoaded = true;
  $('benchStatus').textContent = `Benchmark listo: ${img.modules.length} módulos enlazados (${img.size.toLocaleString('es-AR')} bytes desde x${hx(img.origin)}).`;
}

function profileBenchmarkOps(){
  const modSizeMap = {};
  if(img && img.modules) for(const m of img.modules) modSizeMap[m.name.toUpperCase()] = m.size;
  const maxSteps = Math.max(100000, Number($('tMaxSteps').value.trim()) || 500000);
  const retAddr = 0xFF00;
  const sim = new Apex3XCPU();
  const rows = [];
  const aggHist = {};
  let totalInstr = 0;
  let totalSo = 0;
  let totalAll = 0;
  let maxStack = 0;
  let maxDcnt = 0;
  let combinedOut = '';

  const s16 = v => (v << 16) >> 16;
  for(const op of BENCH_OPS){
    const expectedText = formatBenchExpected(op);
    const esperadoVal = op.expOut !== undefined
      ? op.expOut
      : (op.exp1 !== undefined ? { r0: op.exp, r1: op.exp1 } : op.exp);
    const toleranciaVal = op.expOut !== undefined
      ? null
      : (op.exp1 !== undefined ? { r0: op.tol ?? 0, r1: op.tol1 ?? 0 } : (op.tol ?? 0));

    const entry = findSymAddr(`${op.mod}:${op.sym}`) ?? findSymAddr(op.sym);
    if(entry === undefined){
      rows.push({
        id: op.id, name: op.name, mod: op.mod, sym: op.sym,
        modSize: modSizeMap[op.mod.toUpperCase()] ?? null,
        count: 0, so: 0, total: 0, dcnt: 0, stack: 0,
        expectedText, esperado: esperadoVal, tolerancia: toleranciaVal,
        result: 'Símbolo no encontrado', obtenido: null, estado: 'ERR', ok: false
      });
      continue;
    }
    sim.reset();
    sim.load(img.origin, img.bytes);
    sim.mem[retAddr] = 0x25;
    sim.mem[retAddr + 1] = 0x78;
    sim.r[0] = op.r0 & 0xFFFF;
    sim.r[1] = op.r1 & 0xFFFF;
    sim.r[7] = retAddr;
    sim.pc = entry;
    let returnedCleanly = false;
    while(!sim.halted && !sim.waiting && sim.count < maxSteps){
      if(sim.pc === retAddr){ sim.halted = true; returnedCleanly = true; break; }
      sim.step();
    }
    if(!returnedCleanly && !sim.halted && !sim.waiting && sim.pc === retAddr){
      sim.halted = true;
      returnedCleanly = true;
    }
    const stk = Apex3XCPU.STACK - sim.minSP;
    const ranOk = returnedCleanly && !sim.err && !sim.waiting;
    let matched = false;
    let obtainedVal = null;
    if(op.expOut !== undefined){
      obtainedVal = (sim.out || '').trim();
      if(ranOk) matched = (sim.out || '').includes(op.expOut);
    } else if(op.exp32){
      const val32 = ((sim.r[0] << 16) | (sim.r[1] & 0xFFFF)) >> 0;
      obtainedVal = val32;
      if(ranOk) matched = Math.abs(val32 - op.exp) <= (op.tol ?? 0);
    } else {
      const r0s = s16(sim.r[0]);
      const r1s = s16(sim.r[1]);
      obtainedVal = op.exp1 !== undefined ? { r0: r0s, r1: r1s } : r0s;
      if(ranOk){
        matched = Math.abs(r0s - op.exp) <= (op.tol ?? 0);
        if(matched && op.exp1 !== undefined){
          matched = Math.abs(r1s - op.exp1) <= (op.tol1 ?? 0);
        }
      }
    }
    const estado = !ranOk ? 'ERR' : (matched ? 'PASS' : 'FAIL');
    const ok = estado === 'PASS';
    const resultStr = !returnedCleanly && !sim.err && !sim.waiting
      ? `ERR: límite de ${maxSteps} pasos`
      : sim.waiting
        ? 'ERR: esperando entrada'
        : sim.err
          ? 'ERR: ' + sim.err
          : formatBenchResult(sim.r[0], sim.r[1], sim.out, op);

    totalInstr += sim.count;
    totalSo += sim.so;
    totalAll += sim.total;
    if(stk > maxStack) maxStack = stk;
    if(sim.dcnt > maxDcnt) maxDcnt = sim.dcnt;
    for(const [k,v] of Object.entries(sim.hist)) aggHist[k] = (aggHist[k] || 0) + v;
    if(sim.out) combinedOut += `[#${op.id} ${op.sym}] ${sim.out}`;
    rows.push({
      id: op.id, name: op.name, mod: op.mod, sym: op.sym,
      modSize: modSizeMap[op.mod.toUpperCase()] ?? null,
      count: sim.count, so: sim.so, total: sim.total, dcnt: sim.dcnt, stack: stk,
      expectedText, esperado: esperadoVal, tolerancia: toleranciaVal,
      result: resultStr, obtenido: obtainedVal, estado, ok
    });
  }
  return { rows, totalInstr, totalSo, totalAll, maxStack, maxDcnt, aggHist, combinedOut };
}

function runMainBenchmark(reduced){
  const maxSteps = Math.max(500000, Number($('lim').value) || 5000000);
  auto = false;
  bpPausedAddr = null;
  lastExecInfo = null;
  execHistory = [];
  memReads = 0;
  memWrites = 0;
  $('bRun').classList.remove('on');
  $('bRun').textContent = 'Ejecutar';
  cpu.reset();
  cpu.load(img.origin, img.bytes);

  const listing = img.listing || [];
  const modStats = (img.modules || []).map(m => {
    const end = m.base + m.size;
    const firstIt = listing.find(it => it.addr >= m.base && it.addr < end && !/^\.(FILL|BLKW|STRINGZ|BYTE)$/i.test(it.op));
    return {
      name: m.name,
      base: m.base,
      end,
      size: m.size,
      firstInstr: firstIt ? firstIt.addr : m.base,
      instr: 0,
      calls: 0
    };
  });
  let otherInstr = 0;
  let otherCalls = 0;
  let prevWasOther = false;

  const trackStep = () => {
    const pc = cpu.pc;
    const prevCount = cpu.count;
    cpu.step();
    if(cpu.count > prevCount){
      let found = null;
      for(let i = 0; i < modStats.length; i++){
        const m = modStats[i];
        if(pc >= m.base && pc < m.end){ found = m; break; }
      }
      if(found){
        found.instr++;
        if(pc === found.firstInstr) found.calls++;
        prevWasOther = false;
      } else {
        otherInstr++;
        if(!prevWasOther) otherCalls++;
        prevWasOther = true;
      }
    }
  };

  if(reduced){
    const menuAddr = findSymAddr('g27_main_menu_PROGRESO:MAIN_MENU') ?? findSymAddr('MAIN_MENU');
    const progAddr = findSymAddr('principal:PROGRAMA_DEL_MENU') ?? findSymAddr('PROGRAMA_DEL_MENU');
    if(menuAddr === undefined || progAddr === undefined) throw Error('No se encontró MAIN_MENU o PROGRAMA_DEL_MENU');
    const retAddr = 0xFF00;
    cpu.mem[retAddr] = 0x25;
    cpu.mem[retAddr + 1] = 0x78;
    cpu.r[0] = progAddr;
    cpu.r[7] = retAddr;
    cpu.pc = menuAddr;
    while(!cpu.halted && !cpu.waiting && cpu.count < maxSteps){
      if(cpu.pc === retAddr){ cpu.halted = true; break; }
      trackStep();
    }
  } else {
    while(!cpu.halted && !cpu.waiting && cpu.count < maxSteps){
      trackStep();
    }
  }
  if(!cpu.halted && !cpu.waiting && cpu.count >= maxSteps){
    cpu.halted = true;
    cpu.err = 'límite de ' + maxSteps.toLocaleString('es-AR') + ' pasos';
  }
  const totalUser = cpu.count || 1;
  const moduleProfile = modStats.map(m => ({
    name: m.name,
    base: m.base,
    size: m.size,
    firstInstr: m.firstInstr,
    instr: m.instr,
    pct: (100 * m.instr) / totalUser,
    calls: m.calls
  }));
  if(otherInstr > 0){
    moduleProfile.push({
      name: 'Otros',
      base: null,
      size: null,
      firstInstr: null,
      instr: otherInstr,
      pct: (100 * otherInstr) / totalUser,
      calls: otherCalls,
      isOther: true
    });
  }
  moduleProfile.sort((a, b) => (b.instr - a.instr) || (b.calls - a.calls) || (a.base ?? 0x10000) - (b.base ?? 0x10000));

  prev = Uint16Array.from(cpu.r);
  prevMem.set(cpu.mem);
  render();
  return {
    count: cpu.count,
    so: cpu.so,
    total: cpu.total,
    cycles: cpu.cycles || cpu.total,
    size: cpu.size,
    dcnt: cpu.dcnt,
    picoPila: Apex3XCPU.STACK - cpu.minSP,
    hist: Object.assign({}, cpu.hist),
    out: cpu.out,
    err: cpu.err,
    waiting: cpu.waiting,
    moduleProfile
  };
}

async function runBenchmark(){
  const mode = $('selBenchMode').value;
  try{
    if(!benchmarkLoaded || !img || img.modules.length < 30){
      await loadBenchmark();
    }
    if(mode === 'subrutinas'){
      const prof = profileBenchmarkOps();
      const report = {
        modo: 'subrutinas_aisladas',
        count: prof.totalInstr,
        so: prof.totalSo,
        total: prof.totalAll,
        instruccionesUsuario: prof.totalInstr,
        instruccionesSO: prof.totalSo,
        instruccionesTotal: prof.totalAll,
        instrSub: 'Suma de 23 operaciones (cómputo + E/S)',
        size: img.size,
        sizeSub: `${img.modules.length} módulos enlazados desde x${hx(img.origin)}`,
        dcnt: prof.maxDcnt,
        dataSub: 'Máximo de bytes únicos en una subrutina',
        picoPila: prof.maxStack,
        stackSub: 'Pico máximo entre las 23 operaciones',
        hist: prof.aggHist,
        out: prof.combinedOut || '(Las operaciones de consola se reflejan arriba)',
        ops: prof.rows,
        modules: img.modules
      };
      prevBenchReport = lastBenchReport;
      lastBenchReport = report;
      renderMetricsPanel(report);
      $('benchStatus').textContent = `Perfilado completado: ${prof.rows.filter(r=>r.ok).length}/23 PASS · ${prof.totalAll.toLocaleString('es-AR')} instr. (${prof.totalInstr.toLocaleString('es-AR')} usuario + ${prof.totalSo.toLocaleString('es-AR')} SO).`;
      return;
    }

    const reduced = mode === 'reducido';
    const full = runMainBenchmark(reduced);
    let prof = null;
    if(mode === 'ambos'){
      prof = profileBenchmarkOps();
    }
    const report = {
      modo: mode,
      count: full.count,
      so: full.so,
      total: full.total,
      cycles: full.cycles || full.total,
      instruccionesUsuario: full.count,
      instruccionesSO: full.so,
      instruccionesTotal: full.total,
      ciclos: full.cycles || full.total,
      instrSub: prof
        ? `23 ops aisladas: ${prof.totalAll.toLocaleString('es-AR')} (${prof.totalInstr.toLocaleString('es-AR')} u + ${prof.totalSo.toLocaleString('es-AR')} SO)`
        : (reduced ? 'Prueba reducida (3 ops + menú)' : 'Programa completo (23 ops + menú E/S)'),
      size: full.size,
      sizeSub: `${img.modules.length} módulos enlazados desde x${hx(img.origin)}`,
      dcnt: full.dcnt,
      dataSub: `${((100 * full.dcnt) / 65536).toFixed(2)}% de 64 KiB`,
      picoPila: full.picoPila,
      stackSub: `R6 mín: x${hx(Apex3XCPU.STACK - full.picoPila)} (base x${hx(Apex3XCPU.STACK)})`,
      hist: full.hist,
      out: full.out,
      ops: prof ? prof.rows : null,
      moduleProfile: full.moduleProfile,
      modules: img.modules,
      err: full.err
    };
    prevBenchReport = lastBenchReport;
    lastBenchReport = report;
    renderMetricsPanel(report);
    $('benchStatus').textContent = full.err
      ? `Benchmark con error: ${full.err}`
      : `Benchmark completado: ${full.total.toLocaleString('es-AR')} instr. (${full.count.toLocaleString('es-AR')} usuario + ${full.so.toLocaleString('es-AR')} SO) · ${full.size.toLocaleString('es-AR')} B código · ${full.dcnt.toLocaleString('es-AR')} B datos · ${full.picoPila} B pila.`;
  } catch(e){
    $('benchStatus').textContent = 'Error: ' + e.message;
  }
}

$('bLoadBench').onclick = async () => {
  try { await loadBenchmark(); } catch(e) { $('benchStatus').textContent = 'Error: ' + e.message; }
};
$('bRunBench').onclick = runBenchmark;
$('bExportBench').onclick = () => {
  if(!lastBenchReport){
    $('benchStatus').textContent = 'Corré el benchmark o una prueba primero para exportar métricas.';
    return;
  }
  dl('benchmark_apex3x_metricas.json', JSON.stringify(lastBenchReport, null, 2), 'application/json');
};

$('bTestMode').onclick = () => {
  const p = $('testPanel');
  const hidden = p.classList.toggle('hidden');
  $('bTestMode').classList.toggle('active', !hidden);
  uiPrefs.testPanelOpen = !hidden;
  savePrefs();
  if(!hidden) refreshTestSymbols();
};
$('bCloseTest').onclick = () => {
  $('testPanel').classList.add('hidden');
  $('bTestMode').classList.remove('active');
  uiPrefs.testPanelOpen = false;
  savePrefs();
};

$('selBenchMode').addEventListener('change', () => {
  uiPrefs.benchSuite = $('selBenchMode').value;
  savePrefs();
});

$('tMaxSteps').addEventListener('change', () => {
  const n = Number($('tMaxSteps').value.trim());
  if (Number.isInteger(n) && n >= 1000 && n <= 50000000) {
    uiPrefs.testMaxSteps = n;
    savePrefs();
  } else {
    $('tMaxSteps').value = String(uiPrefs.testMaxSteps);
  }
});

$('lim').addEventListener('change', () => {
  const n = Number($('lim').value.trim());
  if (Number.isInteger(n) && n >= 1000 && n <= 100000000) {
    uiPrefs.stepLimit = n;
    savePrefs();
  } else {
    $('lim').value = String(uiPrefs.stepLimit);
  }
});

$('bRunTest').onclick = () => {
  if(!img){
    $('testResult').className = 'test-res fail m';
    $('testResult').textContent = 'Error: primero ensamblá sin errores o cargá un módulo válido.';
    return;
  }
  auto = false;
  $('bRun').classList.remove('on');
  $('bRun').textContent = 'Ejecutar';

  // Determinar dirección de entrada
  let entryAddr = NaN;
  let entryLabel = '';
  const custom = $('inpEntryCustom').value.trim();
  if(custom){
    const syms = collectAllSymbols();
    const matchKey = Object.keys(syms).find(k => k.toUpperCase() === custom.toUpperCase() || k.toUpperCase().endsWith(':' + custom.toUpperCase()));
    if(matchKey !== undefined){ entryAddr = syms[matchKey]; entryLabel = matchKey; }
    else entryAddr = parseNum16(custom);
  } else if($('selEntry').value !== ''){
    entryAddr = parseInt($('selEntry').value, 10);
    const selOpt = $('selEntry').options[$('selEntry').selectedIndex];
    entryLabel = selOpt ? selOpt.textContent : '';
  } else {
    entryAddr = img.origin;
  }

  if(isNaN(entryAddr) || (entryAddr & 1)){
    $('testResult').className = 'test-res fail m';
    $('testResult').textContent = 'Dirección o etiqueta de entrada inválida (debe ser par y un número válido).';
    return;
  }

  const showTestError = (msg) => {
    $('testResult').className = 'test-res m fail';
    $('testResult').textContent = 'ERROR DE ENTRADA · ' + msg;
  };

  const retAddrRaw = $('tRetAddr').value.trim();
  const retAddrParsed = retAddrRaw ? parseNum16(retAddrRaw, false) : 0xFF00;
  if(isNaN(retAddrParsed) || (retAddrParsed & 1)){
    showTestError('Dirección de retorno inválida (debe ser un valor par de 16 bits, ej. xFF00).');
    return;
  }
  const retAddr = retAddrParsed & 0xFFFE;

  const maxStepsRaw = $('tMaxSteps').value.trim();
  const maxSteps = maxStepsRaw ? Number(maxStepsRaw) : 500000;
  if(!Number.isInteger(maxSteps) || maxSteps <= 0){
    showTestError('Límite de pasos inválido (debe ser un entero positivo).');
    return;
  }

  const initRegs = new Uint16Array(7);
  for(let i=0;i<=6;i++){
    const v = parseNum16($('tr'+i).value, true);
    if(isNaN(v)){
      showTestError(`Valor inválido en R${i}: "${$('tr'+i).value.trim()}".`);
      return;
    }
    initRegs[i] = v;
  }

  const memWrites = [];
  const memSpec = $('tMemInit').value.trim();
  if(memSpec){
    for(const rawPair of memSpec.split(',')){
      const pair = rawPair.trim();
      if(!pair) continue;
      const eqIdx = pair.indexOf('=');
      if(eqIdx <= 0 || eqIdx === pair.length - 1){
        showTestError(`Formato de memoria inválido: "${pair}" (use dir=valor, ej. x4000=x000A).`);
        return;
      }
      const aStr = pair.slice(0, eqIdx).trim();
      const vStr = pair.slice(eqIdx + 1).trim();
      const addr = parseNum16(aStr, false);
      const val = parseNum16(vStr, false);
      if(isNaN(addr) || (addr & 1)){
        showTestError(`Dirección de memoria inválida en "${pair}" (debe ser par).`);
        return;
      }
      if(isNaN(val)){
        showTestError(`Valor de memoria inválido en "${pair}".`);
        return;
      }
      memWrites.push([addr, val]);
    }
  }

  const expReg = $('tExpectReg').value.trim().toUpperCase();
  const expValRaw = $('tExpectVal').value.trim();
  let hasExpected = false;
  let expectedVal = 0;
  if(expValRaw !== ''){
    if(!/^R[0-7]$/.test(expReg)){
      showTestError(`Registro esperado inválido: "${expReg}" (use R0..R7).`);
      return;
    }
    expectedVal = parseNum16(expValRaw, false);
    if(isNaN(expectedVal)){
      showTestError(`Valor esperado inválido para ${expReg}: "${expValRaw}".`);
      return;
    }
    hasExpected = true;
  }

  cpu.reset();
  cpu.load(img.origin, img.bytes);
  // Colocar HALT (TRAP x25 = 0x7825) en la dirección de retorno trampa
  cpu.mem[retAddr] = 0x25;
  cpu.mem[(retAddr + 1) & 0xFFFF] = 0x78;

  // Inicializar registros R0..R6 y R7 = retAddr
  for(let i=0;i<=6;i++) cpu.r[i] = initRegs[i];
  cpu.r[7] = retAddr;
  cpu.pc = entryAddr;

  // Inicializar memoria opcional
  for(const [addr, val] of memWrites) cpu.wr(addr, val);

  prev = Uint16Array.from(cpu.r);
  let returnedCleanly = false;
  while(!cpu.halted && !cpu.waiting && cpu.count < maxSteps){
    if(cpu.pc === retAddr){
      cpu.halted = true;
      returnedCleanly = true;
      break;
    }
    cpu.step();
  }
  if(!returnedCleanly && !cpu.halted && !cpu.waiting && cpu.pc === retAddr){
    cpu.halted = true;
    returnedCleanly = true;
  }
  if(!cpu.halted && !cpu.waiting && cpu.count >= maxSteps){
    cpu.halted = true;
    cpu.err = 'límite de ' + maxSteps + ' pasos en prueba';
  }

  render();

  const isMainProgram = entryAddr === img.origin || /^principal:MAIN\b/i.test(entryLabel);
  let verdict = '';
  let ok = false;

  const soSuffix = cpu.so > 0 ? ` (+ ${cpu.so.toLocaleString('es-AR')} SO = ${cpu.total.toLocaleString('es-AR')} total)` : '';
  if(cpu.err){
    verdict = `ERROR · ${cpu.err}`;
  } else if(cpu.waiting){
    verdict = `FAIL · La subrutina quedó esperando entrada (GETC/IN) en PC=x${hx(cpu.pc)} sin retornar`;
  } else if(!returnedCleanly && !isMainProgram){
    verdict = `FAIL · El programa ejecutó HALT en PC=x${hx(cpu.pc)} antes de retornar a x${hx(retAddr)}`;
  } else if(hasExpected){
    const rIdx = parseInt(expReg[1], 10);
    const actual = cpu.r[rIdx];
    if(actual === expectedVal){
      ok = true;
      verdict = `PASS · ${expReg} = x${hx(actual)} (${(actual<<16)>>16}) en ${cpu.count.toLocaleString('es-AR')} instr.${soSuffix}`;
    } else {
      verdict = `FAIL · Se esperaba ${expReg}=x${hx(expectedVal)}, obtuvo x${hx(actual)} (${(actual<<16)>>16})`;
    }
  } else {
    ok = true;
    verdict = returnedCleanly
      ? `OK · Retornó limpiamente en ${cpu.count.toLocaleString('es-AR')} instrucciones${soSuffix}`
      : `OK · Programa finalizado (HALT) en ${cpu.count.toLocaleString('es-AR')} instrucciones${soSuffix}`;
  }

  $('testResult').className = 'test-res m ' + (ok ? 'pass' : 'fail');
  $('testResult').textContent =
    verdict + '\n' +
    `R0=x${hx(cpu.r[0])}  R1=x${hx(cpu.r[1])}  R2=x${hx(cpu.r[2])}  R3=x${hx(cpu.r[3])}\n` +
    `R4=x${hx(cpu.r[4])}  R5=x${hx(cpu.r[5])}  R6=x${hx(cpu.r[6])}  R7=x${hx(cpu.r[7])}`;

  const stk = Apex3XCPU.STACK - cpu.minSP;
  const unitReport = {
    modo: 'prueba_unitaria',
    entrada: entryLabel || ('x' + hx(entryAddr)),
    count: cpu.count,
    so: cpu.so,
    total: cpu.total,
    instruccionesUsuario: cpu.count,
    instruccionesSO: cpu.so,
    instruccionesTotal: cpu.total,
    instrSub: entryLabel || ('PC inicial x' + hx(entryAddr)),
    size: cpu.size,
    sizeSub: img.modules ? `${img.modules.length} módulo(s) enlazados` : `Desde x${hx(img.origin)}`,
    dcnt: cpu.dcnt,
    dataSub: `${((100 * cpu.dcnt) / 65536).toFixed(2)}% de 64 KiB`,
    picoPila: stk,
    stackSub: `R6 mín: x${hx(Apex3XCPU.STACK - stk)} (base x${hx(Apex3XCPU.STACK)})`,
    hist: Object.assign({}, cpu.hist),
    out: cpu.out,
    ops: null,
    modules: img.modules || null
  };
  lastBenchReport = unitReport;
  renderMetricsPanel(unitReport);
};

$('bAsm').onclick=assemble;
const dl=(n,d,t)=>{const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([d],{type:t}));a.download=n;a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1e3)};
const rdf=f=>new Promise(ok=>{const r=new FileReader();r.onload=()=>ok(new Uint8Array(r.result));r.readAsArrayBuffer(f)});
const txt=b=>new TextDecoder().decode(b);
$('bLoad').onclick=()=>$('fLoad').click();
$('fLoad').onchange=async e=>{const f=e.target.files[0];e.target.value='';if(!f)return;
  try{const b=await rdf(f);img=/\.bin$/i.test(f.name)?Apex3XAssembler.fromBin(b):Apex3XAssembler.fromHex(txt(b))}catch(x){img=null;say('<div class="e">'+esc(x.message)+'</div>');return}
  listingByAddr.clear();reset();renderListing();say('<span class="k">Código máquina cargado: '+img.size+' bytes desde x'+hx(img.origin)+'.</span>');$('maddr').value=hx(img.origin);refreshTestSymbols();render()};
$('bBin').onclick=()=>img&&dl('programa.bin',Apex3XAssembler.toBin(img),'application/octet-stream');
$('bHex').onclick=()=>img&&dl('programa.hex',Apex3XAssembler.toHex(img),'text/plain');
$('bRep').onclick=()=>dl('informe_apex3x.json',JSON.stringify({instrucciones:cpu.count,instruccionesUsuario:cpu.count,instruccionesSO:cpu.so,instruccionesTotal:cpu.total,ciclos:cpu.cycles||cpu.total,tamanoPrograma:cpu.size,datosAccedidos:cpu.dcnt,accesosMemoria:{lecturas:memReads,escrituras:memWrites},picoPila:Apex3XCPU.STACK-cpu.minSP,estado:cpu.err||(cpu.halted?'detenida':'en curso'),registros:[...cpu.r].map(v=>'x'+hx(v)),histograma:cpu.hist,salida:cpu.out},null,2),'application/json');
$('bStep').onclick=()=>{if(img){auto=false;prev=Uint16Array.from(cpu.r);prevMem.set(cpu.mem);stepTracked();render()}};
$('bRun').onclick=()=>{if(!img)return;if(auto){auto=false;$('bRun').classList.remove('on');$('bRun').textContent='Ejecutar';render()}else if(!cpu.halted)run()};
$('bRst').onclick=()=>{reset();$('con').textContent=''};
$('bGo').onclick=mem;$('bPc').onclick=()=>{$('maddr').value=hx(cpu.pc&0xFFF0);mem()};
$('maddr').onkeydown=e=>{if(e.key==='Enter')mem()};
$('inp').onkeydown=e=>{if(e.key==='Enter'){const w=cpu.waiting;cpu.feed(e.target.value);e.target.value='';if(w&&auto)run();else render();const c=$('con');if(c)c.scrollTop=c.scrollHeight;}};
if ($('bScrollToPc')) {
  $('bScrollToPc').onclick = () => {
    const row = $('L' + cpu.pc);
    if (row) row.scrollIntoView({ block: 'center', behavior: 'smooth' });
    else {
      const first = $('lst').querySelector('.row');
      if (first) first.scrollIntoView({ block: 'start', behavior: 'smooth' });
    }
  };
}
if ($('bScrollCon')) {
  $('bScrollCon').onclick = () => {
    const c = $('con');
    if (c) c.scrollTop = c.scrollHeight;
  };
}

// ---- Etapa 4 y 5: Eventos de depuración, vistas, ejemplos, búsqueda, copiar, ayuda y atajos ----
$('src').addEventListener('keyup', updateSrcHint);
$('src').addEventListener('click', updateSrcHint);
$('src').addEventListener('input', updateSrcHint);

$('msg').addEventListener('click', e => {
  const errEl = e.target.closest('.err-jump');
  if (errEl && errEl.dataset.line) {
    jumpToSourceLine(Number(errEl.dataset.line));
  }
});

$('bLoadExample').onclick = () => {
  const key = $('selExample').value;
  if (!EXAMPLES[key]) return;
  extra = [];
  benchmarkLoaded = false;
  $('src').value = EXAMPLES[key];
  updateSrcHint();
  assemble();
};

$('bFontDec').onclick = () => {
  uiPrefs.editorFontSize = Math.max(10, Math.round((uiPrefs.editorFontSize - 1) * 2) / 2);
  savePrefs();
  applyEditorFontSize();
};
$('bFontInc').onclick = () => {
  uiPrefs.editorFontSize = Math.min(20, Math.round((uiPrefs.editorFontSize + 1) * 2) / 2);
  savePrefs();
  applyEditorFontSize();
};

document.querySelectorAll('[data-lst-view]').forEach(btn => {
  btn.onclick = () => {
    uiPrefs.lstView = btn.dataset.lstView;
    savePrefs();
    applyPrefs();
    renderListing();
    render();
  };
});

$('lst').addEventListener('click', e => {
  if (uiPrefs.lstView !== 'asm') return;
  const row = e.target.closest('.row[data-addr]');
  if (row) toggleBreakpoint(Number(row.dataset.addr));
});

$('bClearBp').onclick = () => {
  breakpoints.clear();
  bpPausedAddr = null;
  renderListing();
  render();
};

$('bCopyLst').onclick = () => {
  const text = getListingTextForView(uiPrefs.lstView);
  if (!text) return;
  copyText(text, ok => {
    if ($('lstCurInfo')) $('lstCurInfo').textContent = ok ? `Copiada vista ${uiPrefs.lstView.toUpperCase()} al portapapeles.` : 'No se pudo copiar.';
  });
};

$('execHistory').addEventListener('click', e => {
  const row = e.target.closest('[data-jump-addr]');
  if (!row) return;
  const addr = Number(row.dataset.jumpAddr);
  $('maddr').value = hx(addr & 0xFFF0);
  mem();
  const lstRow = $('L' + addr);
  if (lstRow) lstRow.scrollIntoView({ block: 'nearest' });
});

$('regs').addEventListener('click', e => {
  const card = e.target.closest('.reg[data-reg-hex]');
  if (!card) return;
  const val = card.dataset.regHex;
  const regName = card.dataset.reg || '';
  copyText(val, ok => {
    if ($('regsCopyMsg')) {
      $('regsCopyMsg').textContent = ok ? `Copiado ${regName} = ${val}` : 'No se pudo copiar.';
    }
  });
});

$('selSimClk').addEventListener('change', () => {
  const clk = Number($('selSimClk').value);
  if (VALID_CLOCKS.has(clk)) {
    uiPrefs.simClockMHz = clk;
    savePrefs();
    render();
  }
});

function runMemorySearch(advance = false) {
  const q = $('memSearch').value.trim();
  const statusEl = $('memSearchStatus');
  if (!q) {
    memSearchHits = [];
    memSearchIdx = -1;
    statusEl.textContent = '';
    mem();
    return;
  }

  if (!advance || !memSearchHits.length) {
    memSearchHits = [];
    memSearchIdx = -1;
    const syms = collectAllSymbols();
    const symKey = Object.keys(syms).find(k => k.toUpperCase() === q.toUpperCase() || k.toUpperCase().endsWith(':' + q.toUpperCase()));
    if (symKey !== undefined) {
      const addr = syms[symKey] & 0xFFFF;
      memSearchHits = [addr, (addr + 1) & 0xFFFF];
      memSearchIdx = 0;
      $('maddr').value = hx(addr & 0xFFF0);
      statusEl.textContent = `Etiqueta ${symKey} en x${hx(addr)}.`;
      mem();
      return;
    }

    const cleanStr = q.length >= 2 && q.startsWith('"') && q.endsWith('"') ? q.slice(1, -1) : null;
    const num16 = cleanStr === null ? parseNum16(q, false) : NaN;
    if (!isNaN(num16)) {
      const isByteHex = /^(?:0x|x)[0-9a-f]{1,2}$/i.test(q);
      if (isByteHex) {
        const target = num16 & 0xFF;
        for (let a = 0; a < 65536; a++) {
          if (cpu.mem[a] === target) memSearchHits.push(a);
        }
      } else {
        const lo = num16 & 0xFF, hi = (num16 >> 8) & 0xFF;
        for (let a = 0; a < 65536; a += 2) {
          if (cpu.mem[a] === lo && cpu.mem[a + 1] === hi) memSearchHits.push(a);
        }
      }
    } else {
      const needle = cleanStr !== null ? cleanStr : q;
      const bytes = [...needle].map(c => c.charCodeAt(0) & 0xFF);
      if (bytes.length) {
        for (let a = 0; a <= 65536 - bytes.length; a++) {
          let ok = true;
          for (let j = 0; j < bytes.length; j++) {
            if (cpu.mem[a + j] !== bytes[j]) { ok = false; break; }
          }
          if (ok) memSearchHits.push(a);
        }
      }
    }
    if (!memSearchHits.length) {
      statusEl.textContent = `Sin coincidencias para "${q}".`;
      mem();
      return;
    }
    memSearchIdx = 0;
  } else {
    memSearchIdx = (memSearchIdx + 1) % memSearchHits.length;
  }

  const targetAddr = memSearchHits[memSearchIdx];
  $('maddr').value = hx(targetAddr & 0xFFF0);
  statusEl.textContent = `Coincidencia ${memSearchIdx + 1}/${memSearchHits.length} en x${hx(targetAddr)}.`;
  mem();
}

$('bMemFind').onclick = () => runMemorySearch(false);
$('bMemNext').onclick = () => runMemorySearch(true);
$('memSearch').addEventListener('keydown', e => {
  if (e.key === 'Enter') runMemorySearch(memSearchHits.length > 0);
});

$('mem').addEventListener('click', e => {
  const bEl = e.target.closest('.mem-byte[data-maddr]');
  if (!bEl) return;
  const addr = Number(bEl.dataset.maddr);
  const val = cpu.mem[addr];
  const txtCopy = `x${hx(addr)}: x${hx(val, 2)}`;
  copyText(txtCopy, ok => {
    $('memSearchStatus').textContent = ok ? `Copiado ${txtCopy}` : 'No se pudo copiar.';
  });
});

$('bCopyMem').onclick = () => {
  const base = (parseInt($('maddr').value, 16) || 0) & 0xFFF0;
  const lines = [];
  for (let r = 0; r < 16; r++) {
    const a = (base + r * 16) & 0xFFFF;
    const bytes = [];
    for (let k = 0; k < 16; k++) bytes.push(hx(cpu.mem[(a + k) & 0xFFFF], 2));
    lines.push(`x${hx(a)}  ${bytes.slice(0, 8).join(' ')}  ${bytes.slice(8).join(' ')}`);
  }
  copyText(lines.join('\n'), ok => {
    $('memSearchStatus').textContent = ok ? 'Bloque de memoria copiado.' : 'No se pudo copiar.';
  });
};

$('bCopyCon').onclick = () => {
  copyText(cpu.out || '', () => {});
};
$('bClearCon').onclick = () => {
  cpu.out = '';
  $('con').textContent = '';
};

$('bmOpsFilter').addEventListener('input', renderBenchOpsTable);
$('bmOpsStatusFilter').addEventListener('change', renderBenchOpsTable);
$('bmOpsBody').addEventListener('click', e => {
  const btn = e.target.closest('[data-load-bench-op]');
  if (!btn) return;
  const opId = Number(btn.dataset.loadBenchOp);
  const op = BENCH_OPS.find(x => x.id === opId);
  if (!op) return;
  const addr = findSymAddr(`${op.mod}:${op.sym}`) ?? findSymAddr(op.sym);
  if (addr !== undefined) {
    $('selEntry').value = String(addr);
    $('inpEntryCustom').value = '';
  } else {
    $('inpEntryCustom').value = op.sym;
  }
  $('tr0').value = 'x' + hx(op.r0);
  $('tr1').value = 'x' + hx(op.r1);
  for (let i = 2; i <= 5; i++) $('tr' + i).value = '0';
  $('tr6').value = 'xFE00';
  $('tExpectReg').value = 'R0';
  $('tExpectVal').value = '';
  $('benchStatus').textContent = `Operación #${op.id} (${op.name}) cargada en prueba unitaria.`;
  if (addr !== undefined) {
    const row = $('L' + addr);
    if (row) row.scrollIntoView({ block: 'nearest' });
  }
});

// Diálogo de ayuda Apex-3X y atajos globales
function toggleHelpDialog() {
  const dlg = $('helpDialog');
  if (!dlg) return;
  if (dlg.open) dlg.close();
  else if (dlg.showModal) dlg.showModal();
  else dlg.setAttribute('open', '');
}
$('bHelp').onclick = toggleHelpDialog;
$('bCloseHelp').onclick = () => {
  const dlg = $('helpDialog');
  if (dlg && dlg.open) dlg.close();
  else if (dlg) dlg.removeAttribute('open');
};
$('helpDialog').addEventListener('click', e => {
  if (e.target === $('helpDialog')) $('helpDialog').close();
});

document.addEventListener('keydown', e => {
  if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
    e.preventDefault();
    assemble();
    return;
  }
  if (e.key === 'F1') {
    e.preventDefault();
    toggleHelpDialog();
    return;
  }
  if (e.key === 'F9') {
    e.preventDefault();
    $('bRun').click();
    return;
  }
  if (e.key === 'F10') {
    e.preventDefault();
    $('bStep').click();
    return;
  }
  if (e.key === 'F8') {
    e.preventDefault();
    $('bRst').click();
  }
});

// ---- Gestión de paneles: mostrar/ocultar, plegar, reordenar y redimensionar ----
const PANEL_KEYS = ['src', 'lst', 'regs', 'metrics', 'mem', 'con'];
const PANEL_MIN_HEIGHTS = {
  src: 200,
  lst: 160,
  regs: 160,
  metrics: 180,
  mem: 180,
  con: 150,
  test: 220
};

const LAYOUT_PRESETS = {
  estandar: {
    cols: [
      ['src', 'lst'],
      ['regs', 'metrics'],
      ['mem', 'con']
    ],
    hidden: [],
    collapsed: [],
    heights: { src: 460, lst: 460, regs: 260, metrics: 340, mem: 340, con: 260 },
    colWeights: [1.25, 0.85, 1.0]
  },
  programacion: {
    cols: [
      ['src'],
      ['lst'],
      ['con', 'regs', 'metrics', 'mem']
    ],
    hidden: ['regs', 'metrics', 'mem'],
    collapsed: [],
    heights: { src: 540, lst: 540, con: 320 },
    colWeights: [1.5, 1.15, 0.8]
  },
  depuracion: {
    cols: [
      ['lst', 'con'],
      ['regs', 'metrics'],
      ['mem', 'src']
    ],
    hidden: ['src'],
    collapsed: [],
    heights: { lst: 360, con: 220, mem: 420 },
    colWeights: [1.05, 0.9, 1.25]
  }
};

const VALID_PRESETS = new Set([...Object.keys(LAYOUT_PRESETS), 'personalizada']);

const DEFAULT_LAYOUT = () => ({
  preset: 'estandar',
  cols: LAYOUT_PRESETS.estandar.cols.map(c => [...c]),
  hidden: [],
  collapsed: [],
  heights: {},
  colWeights: [...LAYOUT_PRESETS.estandar.colWeights]
});

function clampPanelHeight(key, h) {
  const minH = PANEL_MIN_HEIGHTS[key] || 150;
  const maxH = Math.max(minH + 80, Math.min(920, Math.round((window.innerHeight || 900) * 0.85)));
  return Math.max(minH, Math.min(maxH, Math.round(h)));
}

function normalizeLayout(raw) {
  const def = DEFAULT_LAYOUT();
  if (!raw || typeof raw !== 'object') return def;

  const keySet = new Set(PANEL_KEYS);
  const seen = new Set();
  const cols = [[], [], []];

  if (Array.isArray(raw.cols) && raw.cols.length === 3) {
    for (let c = 0; c < 3; c++) {
      const list = Array.isArray(raw.cols[c]) ? raw.cols[c] : [];
      for (const k of list) {
        if (keySet.has(k) && !seen.has(k)) {
          cols[c].push(k);
          seen.add(k);
        }
      }
    }
  } else {
    for (let c = 0; c < 3; c++) {
      for (const k of def.cols[c]) {
        cols[c].push(k);
        seen.add(k);
      }
    }
  }

  for (let c = 0; c < 3; c++) {
    for (const k of def.cols[c]) {
      if (!seen.has(k)) {
        cols[c].push(k);
        seen.add(k);
      }
    }
  }

  const hidden = Array.isArray(raw.hidden)
    ? [...new Set(raw.hidden.filter(k => keySet.has(k)))]
    : [];
  const collapsed = Array.isArray(raw.collapsed)
    ? [...new Set(raw.collapsed.filter(k => keySet.has(k)))]
    : [];

  const heights = {};
  if (raw.heights && typeof raw.heights === 'object') {
    for (const [k, v] of Object.entries(raw.heights)) {
      if ((keySet.has(k) || k === 'test') && Number.isFinite(Number(v))) {
        heights[k] = clampPanelHeight(k, Number(v));
      }
    }
  }

  let colWeights = def.colWeights;
  if (Array.isArray(raw.colWeights) && raw.colWeights.length === 3) {
    colWeights = raw.colWeights.map((w, idx) => {
      const n = Number(w);
      return Number.isFinite(n) ? Math.max(0.45, Math.min(3.0, Number(n.toFixed(3)))) : def.colWeights[idx];
    });
  }

  const preset = VALID_PRESETS.has(raw.preset) ? raw.preset : 'estandar';

  return { preset, cols, hidden, collapsed, heights, colWeights };
}

let layoutState = safeStorage.getJSON(STORAGE_KEYS.layout, normalizeLayout, DEFAULT_LAYOUT());

function saveLayout() {
  safeStorage.setJSON(STORAGE_KEYS.layout, layoutState);
}

function getPanelElement(key) {
  return document.querySelector(`#workspace .panel[data-panel="${key}"]`);
}

function findPanelPos(key) {
  for (let c = 0; c < 3; c++) {
    const i = layoutState.cols[c].indexOf(key);
    if (i >= 0) return { col: c, idx: i };
  }
  return null;
}

function isMobileLayout() {
  return window.innerWidth <= 1020;
}

function applyLayout() {
  layoutState = normalizeLayout(layoutState);
  const hiddenSet = new Set(layoutState.hidden);
  const collapsedSet = new Set(layoutState.collapsed);
  const heights = layoutState.heights;
  const mobile = isMobileLayout();

  // Ubicar cada panel en su columna y orden solo si cambió su posición DOM
  for (let c = 0; c < 3; c++) {
    const colEl = $('col' + c);
    if (!colEl) continue;
    layoutState.cols[c].forEach((key, idx) => {
      const panel = getPanelElement(key);
      if (!panel) return;
      if (colEl.children[idx] !== panel) {
        colEl.insertBefore(panel, colEl.children[idx] || null);
      }
    });
  }

  document.querySelectorAll('#workspace .panel[data-panel]').forEach(panel => {
    const key = panel.dataset.panel;
    const isHidden = hiddenSet.has(key);
    const isCollapsed = collapsedSet.has(key);
    panel.classList.toggle('hidden', isHidden);
    panel.classList.toggle('collapsed', isCollapsed);

    if (!mobile && !isCollapsed && heights[key]) {
      panel.style.height = clampPanelHeight(key, heights[key]) + 'px';
    } else {
      panel.style.height = '';
    }

    const colBtn = panel.querySelector(`[data-collapse-panel="${key}"]`);
    if (colBtn) colBtn.textContent = isCollapsed ? '+' : '−';
  });

  if (!mobile && heights.test && !$('testPanel').classList.contains('collapsed')) {
    $('testPanel').style.height = clampPanelHeight('test', heights.test) + 'px';
  } else {
    $('testPanel').style.height = '';
  }

  document.querySelectorAll('[data-toggle-panel]').forEach(btn => {
    const active = !hiddenSet.has(btn.dataset.togglePanel);
    btn.classList.toggle('on', active);
    btn.setAttribute('aria-pressed', active ? 'true' : 'false');
  });

  if ($('selLayoutPreset')) {
    $('selLayoutPreset').value = layoutState.preset || 'estandar';
  }

  // Actualizar estado habilitado/deshabilitado de los botones de reordenamiento
  const flatVisible = layoutState.cols.flat().filter(k => !hiddenSet.has(k));
  for (let c = 0; c < 3; c++) {
    const visibleInCol = layoutState.cols[c].filter(k => !hiddenSet.has(k));
    visibleInCol.forEach((key, vIdx) => {
      const panel = getPanelElement(key);
      if (!panel) return;
      const btnLeft = panel.querySelector('[data-move-panel="left"]');
      const btnRight = panel.querySelector('[data-move-panel="right"]');
      const btnUp = panel.querySelector('[data-move-panel="up"]');
      const btnDown = panel.querySelector('[data-move-panel="down"]');

      if (mobile) {
        const fIdx = flatVisible.indexOf(key);
        if (btnLeft) btnLeft.disabled = true;
        if (btnRight) btnRight.disabled = true;
        if (btnUp) btnUp.disabled = fIdx <= 0;
        if (btnDown) btnDown.disabled = fIdx < 0 || fIdx >= flatVisible.length - 1;
      } else {
        if (btnLeft) btnLeft.disabled = c <= 0;
        if (btnRight) btnRight.disabled = c >= 2;
        if (btnUp) btnUp.disabled = vIdx <= 0;
        if (btnDown) btnDown.disabled = vIdx >= visibleInCol.length - 1;
      }
    });
  }

  const cols = [0, 1, 2].map(i => $('col' + i));
  const visibleIdx = cols
    .map((c, i) => ({ c, i, hasVisible: !!c.querySelector('.panel:not(.hidden)') }))
    .filter(x => {
      x.c.classList.toggle('col-empty', !x.hasVisible);
      return x.hasVisible;
    })
    .map(x => x.i);

  const emptyMsg = $('emptyWorkspace');
  if (emptyMsg) {
    emptyMsg.classList.toggle('hidden', visibleIdx.length > 0);
  }

  const split01 = $('split01');
  const split12 = $('split12');

  if (mobile) {
    split01.classList.add('hidden');
    split12.classList.add('hidden');
    $('workspace').style.gridTemplateColumns = '';
    return;
  }

  const wsWidth = $('workspace').clientWidth || window.innerWidth || 1200;
  const nCols = visibleIdx.length;
  const splitterSpace = Math.max(0, nCols - 1) * 10;
  const safeMin = nCols > 0
    ? Math.min(220, Math.max(140, Math.floor(((wsWidth - 40 - splitterSpace) / nCols) * 0.6)))
    : 200;

  const tracks = [];
  if (nCols === 0) {
    split01.classList.add('hidden');
    split12.classList.add('hidden');
  } else if (nCols === 1) {
    split01.classList.add('hidden');
    split12.classList.add('hidden');
    tracks.push(`minmax(${safeMin}px, 1fr)`);
  } else if (nCols === 2) {
    const [a, b] = visibleIdx;
    const showFirst = a === 0 && b === 1;
    split01.classList.toggle('hidden', !showFirst);
    split12.classList.toggle('hidden', showFirst);
    tracks.push(
      `minmax(${safeMin}px, ${layoutState.colWeights[a]}fr)`,
      '10px',
      `minmax(${safeMin}px, ${layoutState.colWeights[b]}fr)`
    );
  } else {
    split01.classList.remove('hidden');
    split12.classList.remove('hidden');
    tracks.push(
      `minmax(${safeMin}px, ${layoutState.colWeights[0]}fr)`,
      '10px',
      `minmax(${Math.min(200, safeMin)}px, ${layoutState.colWeights[1]}fr)`,
      '10px',
      `minmax(${safeMin}px, ${layoutState.colWeights[2]}fr)`
    );
  }
  $('workspace').style.gridTemplateColumns = tracks.join(' ');
}

function movePanel(key, dir) {
  const pos = findPanelPos(key);
  if (!pos) return;
  const hiddenSet = new Set(layoutState.hidden);

  if (isMobileLayout() && (dir === 'up' || dir === 'down')) {
    const flatVisible = layoutState.cols.flat().filter(k => !hiddenSet.has(k));
    const curIdx = flatVisible.indexOf(key);
    const targetIdx = dir === 'up' ? curIdx - 1 : curIdx + 1;
    if (curIdx < 0 || targetIdx < 0 || targetIdx >= flatVisible.length) return;
    const anchorKey = flatVisible[targetIdx];
    const anchorPos = findPanelPos(anchorKey);
    if (!anchorPos) return;
    layoutState.cols[pos.col].splice(pos.idx, 1);
    const updatedAnchor = findPanelPos(anchorKey);
    const insertAt = dir === 'up' ? updatedAnchor.idx : updatedAnchor.idx + 1;
    layoutState.cols[updatedAnchor.col].splice(insertAt, 0, key);
  } else if (dir === 'up' || dir === 'down') {
    const colArr = layoutState.cols[pos.col];
    const visibleInCol = colArr.filter(k => !hiddenSet.has(k));
    const vIdx = visibleInCol.indexOf(key);
    const targetVIdx = dir === 'up' ? vIdx - 1 : vIdx + 1;
    if (vIdx < 0 || targetVIdx < 0 || targetVIdx >= visibleInCol.length) return;
    const anchorKey = visibleInCol[targetVIdx];
    colArr.splice(pos.idx, 1);
    const anchorIdx = colArr.indexOf(anchorKey);
    colArr.splice(dir === 'up' ? anchorIdx : anchorIdx + 1, 0, key);
  } else if (dir === 'left' || dir === 'right') {
    const nextCol = dir === 'left' ? pos.col - 1 : pos.col + 1;
    if (nextCol < 0 || nextCol > 2) return;
    layoutState.cols[pos.col].splice(pos.idx, 1);
    const targetArr = layoutState.cols[nextCol];
    const insertIdx = Math.min(pos.idx, targetArr.length);
    targetArr.splice(insertIdx, 0, key);
  }

  layoutState.preset = 'personalizada';
  saveLayout();
  applyLayout();
}

function movePanelToTarget(dragKey, targetCol, beforeKey = null, after = false) {
  if (!dragKey || targetCol < 0 || targetCol > 2) return;
  if (dragKey === beforeKey) return;
  const from = findPanelPos(dragKey);
  if (!from) return;

  layoutState.cols[from.col].splice(from.idx, 1);
  const dest = layoutState.cols[targetCol];
  if (beforeKey) {
    const idx = dest.indexOf(beforeKey);
    if (idx >= 0) {
      dest.splice(after ? idx + 1 : idx, 0, dragKey);
    } else {
      dest.push(dragKey);
    }
  } else {
    dest.push(dragKey);
  }
  layoutState.preset = 'personalizada';
  saveLayout();
  applyLayout();
}

document.querySelectorAll('[data-toggle-panel]').forEach(btn => {
  btn.onclick = () => {
    const key = btn.dataset.togglePanel;
    const idx = layoutState.hidden.indexOf(key);
    if (idx >= 0) layoutState.hidden.splice(idx, 1);
    else layoutState.hidden.push(key);
    layoutState.preset = 'personalizada';
    saveLayout();
    applyLayout();
  };
});

document.querySelectorAll('[data-hide-panel]').forEach(btn => {
  btn.onclick = () => {
    const key = btn.dataset.hidePanel;
    if (!layoutState.hidden.includes(key)) layoutState.hidden.push(key);
    layoutState.preset = 'personalizada';
    saveLayout();
    applyLayout();
  };
});

document.querySelectorAll('[data-collapse-panel]').forEach(btn => {
  btn.onclick = () => {
    const key = btn.dataset.collapsePanel;
    const idx = layoutState.collapsed.indexOf(key);
    if (idx >= 0) layoutState.collapsed.splice(idx, 1);
    else layoutState.collapsed.push(key);
    layoutState.preset = 'personalizada';
    saveLayout();
    applyLayout();
  };
});

document.querySelectorAll('[data-move-panel]').forEach(btn => {
  btn.onclick = () => {
    movePanel(btn.dataset.target, btn.dataset.movePanel);
  };
});

function applyLayoutPreset(name) {
  const tpl = LAYOUT_PRESETS[name];
  if (!tpl) return;
  const nextHeights = Object.assign({}, tpl.heights);
  if (layoutState.heights && layoutState.heights.test) {
    nextHeights.test = layoutState.heights.test;
  }
  layoutState = normalizeLayout({
    preset: name,
    cols: tpl.cols.map(c => [...c]),
    hidden: [...tpl.hidden],
    collapsed: [...tpl.collapsed],
    heights: nextHeights,
    colWeights: [...tpl.colWeights]
  });
  saveLayout();
  applyLayout();
}

if ($('selLayoutPreset')) {
  $('selLayoutPreset').addEventListener('change', e => {
    applyLayoutPreset(e.target.value);
  });
}

function resetLayout() {
  layoutState = DEFAULT_LAYOUT();
  saveLayout();
  applyLayout();
}

$('bResetLayout').onclick = resetLayout;
if ($('bRestoreFromEmpty')) $('bRestoreFromEmpty').onclick = resetLayout;

// Arrastrar y soltar paneles por su cabecera
let dragPanelKey = null;
function clearDragHints() {
  document.body.classList.remove('is-dragging-panel');
  document.querySelectorAll('#workspace .panel').forEach(p => {
    p.classList.remove('is-dragging', 'drop-before', 'drop-after');
  });
  document.querySelectorAll('#workspace .col').forEach(c => {
    c.classList.remove('drop-target');
  });
}

document.querySelectorAll('#workspace .panel[data-panel]').forEach(panel => {
  const head = panel.querySelector('.panel-head');
  if (!head) return;

  head.addEventListener('dragstart', e => {
    if (e.target.closest('button, input, select, a, .panel-actions')) {
      e.preventDefault();
      return;
    }
    dragPanelKey = panel.dataset.panel;
    document.body.classList.add('is-dragging-panel');
    panel.classList.add('is-dragging');
    if (e.dataTransfer) {
      e.dataTransfer.effectAllowed = 'move';
      e.dataTransfer.setData('text/plain', dragPanelKey);
    }
  });

  head.addEventListener('dragend', () => {
    dragPanelKey = null;
    clearDragHints();
  });

  panel.addEventListener('dragover', e => {
    if (!dragPanelKey || dragPanelKey === panel.dataset.panel) return;
    e.preventDefault();
    if (e.dataTransfer) e.dataTransfer.dropEffect = 'move';
    const rect = panel.getBoundingClientRect();
    const isAfter = e.clientY > rect.top + rect.height / 2;
    document.querySelectorAll('#workspace .panel').forEach(p => {
      if (p !== panel) p.classList.remove('drop-before', 'drop-after');
    });
    panel.classList.toggle('drop-before', !isAfter);
    panel.classList.toggle('drop-after', isAfter);
  });

  panel.addEventListener('dragleave', e => {
    if (!panel.contains(e.relatedTarget)) {
      panel.classList.remove('drop-before', 'drop-after');
    }
  });

  panel.addEventListener('drop', e => {
    if (!dragPanelKey) return;
    e.preventDefault();
    e.stopPropagation();
    const targetKey = panel.dataset.panel;
    const colEl = panel.closest('.col');
    const targetCol = colEl ? Number(colEl.dataset.col) : 0;
    const rect = panel.getBoundingClientRect();
    const isAfter = e.clientY > rect.top + rect.height / 2;
    const key = dragPanelKey;
    dragPanelKey = null;
    clearDragHints();
    movePanelToTarget(key, targetCol, targetKey, isAfter);
  });
});

document.querySelectorAll('#workspace .col').forEach(colEl => {
  colEl.addEventListener('dragover', e => {
    if (!dragPanelKey) return;
    e.preventDefault();
    if (e.dataTransfer) e.dataTransfer.dropEffect = 'move';
    colEl.classList.add('drop-target');
  });

  colEl.addEventListener('dragleave', e => {
    if (!colEl.contains(e.relatedTarget)) {
      colEl.classList.remove('drop-target');
    }
  });

  colEl.addEventListener('drop', e => {
    if (!dragPanelKey) return;
    e.preventDefault();
    const key = dragPanelKey;
    const targetCol = Number(colEl.dataset.col);
    dragPanelKey = null;
    clearDragHints();
    movePanelToTarget(key, targetCol, null, false);
  });
});

// Redimensionado vertical de paneles
document.querySelectorAll('[data-resize-panel]').forEach(handle => {
  handle.addEventListener('dblclick', () => {
    const key = handle.dataset.resizePanel;
    delete layoutState.heights[key];
    if (key !== 'test') layoutState.preset = 'personalizada';
    saveLayout();
    applyLayout();
  });

  handle.addEventListener('pointerdown', e => {
    if (isMobileLayout()) return;
    e.preventDefault();
    const key = handle.dataset.resizePanel;
    const panel = handle.closest('.panel');
    if (!panel || panel.classList.contains('collapsed')) return;
    const startY = e.clientY;
    const startH = panel.getBoundingClientRect().height;
    handle.classList.add('dragging');
    handle.setPointerCapture(e.pointerId);

    const onMove = ev => {
      const nextH = clampPanelHeight(key, startH + (ev.clientY - startY));
      panel.style.height = nextH + 'px';
      layoutState.heights[key] = nextH;
      if (key !== 'test') layoutState.preset = 'personalizada';
    };
    const onUp = () => {
      handle.classList.remove('dragging');
      handle.removeEventListener('pointermove', onMove);
      handle.removeEventListener('pointerup', onUp);
      handle.removeEventListener('pointercancel', onUp);
      if (key !== 'test') applyLayout();
      saveLayout();
    };
    handle.addEventListener('pointermove', onMove);
    handle.addEventListener('pointerup', onUp);
    handle.addEventListener('pointercancel', onUp);
  });
});

// Redimensionado horizontal de columnas
document.querySelectorAll('.col-resizer').forEach(splitter => {
  splitter.addEventListener('pointerdown', e => {
    if (isMobileLayout()) return;
    e.preventDefault();
    let prevEl = splitter.previousElementSibling;
    while (prevEl && (!prevEl.classList.contains('col') || prevEl.classList.contains('col-empty'))) {
      prevEl = prevEl.previousElementSibling;
    }
    let nextEl = splitter.nextElementSibling;
    while (nextEl && (!nextEl.classList.contains('col') || nextEl.classList.contains('col-empty'))) {
      nextEl = nextEl.nextElementSibling;
    }
    if (!prevEl || !nextEl) return;

    const leftIdx = Number(prevEl.dataset.col);
    const rightIdx = Number(nextEl.dataset.col);
    const startX = e.clientX;
    const widths = [0, 1, 2].map(i => $('col' + i).getBoundingClientRect().width || 0);
    const pairTotal = widths[leftIdx] + widths[rightIdx];
    const allTotal = widths.reduce((a, b) => a + b, 0) || 1;
    const minW = Math.max(150, Math.min(230, Math.floor(allTotal * 0.18)));
    if (pairTotal < minW * 2) return;

    splitter.classList.add('dragging');
    splitter.setPointerCapture(e.pointerId);

    const onMove = ev => {
      const dx = ev.clientX - startX;
      const newLeft = Math.max(minW, Math.min(pairTotal - minW, widths[leftIdx] + dx));
      const newRight = pairTotal - newLeft;
      const nextWidths = [...widths];
      nextWidths[leftIdx] = newLeft;
      nextWidths[rightIdx] = newRight;
      for (const idx of [0, 1, 2]) {
        if (nextWidths[idx] > 0) {
          const w = (nextWidths[idx] / allTotal) * 3.1;
          layoutState.colWeights[idx] = Math.max(0.45, Math.min(3.0, Number(w.toFixed(3))));
        }
      }
      layoutState.preset = 'personalizada';
      applyLayout();
    };
    const onUp = () => {
      splitter.classList.remove('dragging');
      splitter.removeEventListener('pointermove', onMove);
      splitter.removeEventListener('pointerup', onUp);
      splitter.removeEventListener('pointercancel', onUp);
      saveLayout();
    };
    splitter.addEventListener('pointermove', onMove);
    splitter.addEventListener('pointerup', onUp);
    splitter.addEventListener('pointercancel', onUp);
  });
});

let resizeRaf = 0;
window.addEventListener('resize', () => {
  if (resizeRaf) cancelAnimationFrame(resizeRaf);
  resizeRaf = requestAnimationFrame(() => {
    resizeRaf = 0;
    applyLayout();
  });
});

applyPrefs();
applyLayout();
updateSrcHint();
assemble();

