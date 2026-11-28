/*
 * app.js - Interfaz del simulador (Grupo 7, Lab 3c). Une assembler.js con cpu.js.
 * =============================================================================
 * El núcleo (cpu.js) solo recibe la imagen hexadecimal/binaria; esta capa es
 * la única que conoce al ensamblador y a la CPU, y administra el DOM.
 * Todo texto insertado con innerHTML se escapa (&, <, >).
 */
(function () {
  'use strict';
  const $ = id => document.getElementById(id);
  const hex4 = CPU.hex4, hex2 = CPU.hex2;
  const s16 = v => (v << 16) >> 16;
  const esc = s => String(s).replace(/[&<>]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]));

  const DEFAULT_BLOCKS = {
    asmPanel: true,
    runPanel: true,
    memPanel: true,
    registros: true,
    disasm: true,
    consola: true,
    memgrid: true,
    watch: true,
    metrics: true
  };

  /* ---------- estado ---------- */
  const state = {
    modules: [],          // { name, source }
    active: 0,
    asm: null,            // último resultado de assemble() (o null si la imagen viene de un archivo)
    image: null,          // Uint8Array: origen (2 bytes) + programa
    imageName: 'programa',
    outView: 'hex',
    cpu: null,
    loaded: false,
    running: false,
    prevRegs: null,
    prevWatch: {},
    blocks: Object.assign({}, DEFAULT_BLOCKS),
    asmTall: false,
    asmWide: false,
    keyMode: true,
    addrMap: new Map()
  };

  const store = {
    get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
    set(k, v) { try { localStorage.setItem(k, v); return true; } catch (e) { return false; } }
  };

  const MODULES_KEY = 'lc3g7.modules.v3';
  const BENCHMARK_ZIP = 'benchmark/benchmark_g7.zip';

  /* ---------- módulos y editor ---------- */
  function loadFallbackModules() {
    state.modules = Object.keys(window.EJEMPLOS).map(name => ({ name, source: window.EJEMPLOS[name] }));
    state.active = 0;
  }

  async function initModules() {
    let saved = null;
    try { saved = JSON.parse(store.get(MODULES_KEY) || 'null'); } catch (e) { saved = null; }
    if (Array.isArray(saved) && saved.length && saved.every(m => m && typeof m.name === 'string' && typeof m.source === 'string')) {
      state.modules = saved;
      state.active = 0;
      return { fallback: false };
    }
    try {
      const parsed = await fetchBenchmark();
      state.modules = parsed.modules.map(m => ({ name: m.name, source: m.source }));
      state.active = 0;
      saveModules();
      return { fallback: false };
    } catch (_err) {
      loadFallbackModules();
      return { fallback: true };
    }
  }
  function saveModules() {
    const ok = store.set(MODULES_KEY, JSON.stringify(state.modules));
    return ok;
  }

  /* ---------- disposición de bloques y expansión del editor ---------- */
  function initLayout() {
    try {
      const b = JSON.parse(store.get('lc3g7.blocks') || 'null');
      if (b && typeof b === 'object') {
        for (const k of Object.keys(DEFAULT_BLOCKS)) {
          if (typeof b[k] === 'boolean') state.blocks[k] = b[k];
        }
      }
      const ex = JSON.parse(store.get('lc3g7.asmExpand') || 'null');
      if (ex && typeof ex === 'object') {
        state.asmTall = !!ex.tall;
        state.asmWide = !!ex.wide;
      }
      const km = store.get('lc3g7.keyMode');
      if (km === 'false') state.keyMode = false;
      else if (km === 'true') state.keyMode = true;
    } catch (_e) { /* sin almacenamiento */ }
  }

  function keyEventToChar(e) {
    if (!e || e.ctrlKey || e.metaKey || e.altKey) return null;
    if (e.key === 'Enter') return '\n';
    if (e.key === 'Backspace') return String.fromCharCode(8);
    if (typeof e.key === 'string' && e.key.length === 1) return e.key;
    return null;
  }

  function updateKeyModeUI() {
    const chk = $('inKeyMode');
    if (chk) chk.checked = state.keyMode;
    const inp = $('inText');
    if (inp) {
      inp.placeholder = state.keyMode
        ? 'Tecla por tecla (cada tecla se envía al instante)'
        : 'Entrada por línea (GETC / IN)';
    }
    const btn = $('btnSendIn');
    if (btn) btn.disabled = state.keyMode;
  }

  function sendSingleChar(ch) {
    const inp = $('inText');
    if (inp) inp.value = '';
    if (!state.cpu || !ch) return;
    state.cpu.pushInput(ch);
    if (state.cpu.status === 'WAIT_INPUT') {
      state.cpu.status = 'RUNNING';
      startRun();
    }
  }

  function saveLayout() {
    store.set('lc3g7.blocks', JSON.stringify(state.blocks));
    store.set('lc3g7.asmExpand', JSON.stringify({ tall: state.asmTall, wide: state.asmWide }));
  }

  function applyLayout() {
    const panels = ['asmPanel', 'runPanel', 'memPanel'];
    let visiblePanels = 0;
    for (const id of panels) {
      const show = !!state.blocks[id];
      $(id).hidden = !show;
      if (show) visiblePanels++;
    }
    document.querySelectorAll('.blk[data-blk]').forEach(el => {
      el.hidden = !state.blocks[el.dataset.blk];
    });

    const asm = $('asmPanel');
    asm.classList.toggle('asm-tall', state.asmTall);
    asm.classList.toggle('asm-wide', state.asmWide);
    const bTall = $('btnAsmTall'), bWide = $('btnAsmWide');
    bTall.textContent = state.asmTall ? 'Alto normal' : 'Ampliar alto';
    bTall.classList.toggle('on', state.asmTall);
    bTall.setAttribute('aria-pressed', String(state.asmTall));
    bWide.textContent = state.asmWide ? 'Contraer' : 'Expandir';
    bWide.classList.toggle('on', state.asmWide);
    bWide.setAttribute('aria-pressed', String(state.asmWide));

    const grid = $('mainGrid');
    grid.classList.remove('cols-1', 'cols-2', 'cols-3');
    const nonAsmVisible = (state.blocks.runPanel ? 1 : 0) + (state.blocks.memPanel ? 1 : 0);
    if (visiblePanels <= 1) grid.classList.add('cols-1');
    else if (state.asmWide && state.blocks.asmPanel) grid.classList.add(nonAsmVisible >= 2 ? 'cols-2' : 'cols-1');
    else grid.classList.add(visiblePanels === 2 ? 'cols-2' : 'cols-3');

    $('emptyState').hidden = visiblePanels > 0;
    grid.hidden = visiblePanels === 0;

    document.querySelectorAll('.blk-btn[data-block]').forEach(btn => {
      const on = !!state.blocks[btn.dataset.block];
      btn.classList.toggle('on', on);
      btn.setAttribute('aria-pressed', String(on));
    });
  }

  function renderTabs() {
    const t = $('tabs');
    t.innerHTML = '';
    state.modules.forEach((m, i) => {
      const b = document.createElement('button');
      b.type = 'button';
      b.className = 'tab' + (i === state.active ? ' on' : '');
      b.textContent = m.name;
      b.setAttribute('role', 'tab');
      b.setAttribute('aria-selected', String(i === state.active));
      b.onclick = () => { state.active = i; renderTabs(); loadEditor(); };
      t.appendChild(b);
    });
    $('btnDelMod').disabled = state.modules.length <= 1;
  }

  function loadEditor() {
    $('editor').value = state.modules[state.active].source;
    renderGutter();
  }

  let errByModule = {};
  let warnByModule = {};
  function badLines(name) { return errByModule[name] || new Set(); }
  function warnLines(name) { return warnByModule[name] || new Set(); }
  function renderGutter() {
    const n = $('editor').value.split('\n').length;
    const modName = state.modules[state.active].name;
    const bad = badLines(modName);
    const wrn = warnLines(modName);
    let h = '';
    for (let i = 1; i <= n; i++) {
      if (bad.has(i)) h += `<span class="bad">${i}</span>\n`;
      else if (wrn.has(i)) h += `<span class="warn">${i}</span>\n`;
      else h += `${i}\n`;
    }
    $('gutter').innerHTML = h;
    $('gutter').scrollTop = $('editor').scrollTop;
  }

  function uniqueName(base) {
    let n = base, k = 2;
    const stem = base.replace(/\.asm$/i, '');
    while (state.modules.some(m => m.name === n)) n = `${stem}${k++}.asm`;
    return n;
  }

  function jumpToModLine(modName, line) {
    const i = state.modules.findIndex(m => m.name === modName);
    if (i >= 0) {
      state.active = i;
      renderTabs();
      loadEditor();
      focusLine(line);
    }
  }

  function appendStorageWarning(box) {
    const d = document.createElement('div');
    d.className = 'm w';
    d.textContent = 'Aviso: no se pudieron guardar todos los módulos en el almacenamiento local (espacio lleno o bloqueado). Seguís trabajando en memoria en esta sesión.';
    box.appendChild(d);
  }

  function buildAddrMap(asmRes) {
    const map = new Map();
    if (!asmRes || !Array.isArray(asmRes.listing)) return map;
    for (const it of asmRes.listing) {
      if (it.kind === 'instr' || !map.has(it.addr)) {
        map.set(it.addr, { module: it.module, line: it.line, text: it.text });
      }
    }
    return map;
  }

  /* ---------- ensamblado ---------- */
  function assemble() {
    state.modules[state.active].source = $('editor').value;
    const savedOk = saveModules();
    const res = Assembler.assemble(state.modules);
    const box = $('asmMsgs');
    box.innerHTML = '';
    errByModule = {};
    warnByModule = {};
    const addMsg = (cls, html, onclick) => {
      const d = document.createElement('div');
      d.className = 'm ' + cls;
      d.innerHTML = html;
      if (onclick) d.onclick = onclick;
      box.appendChild(d);
    };
    const jump = e => () => jumpToModLine(e.module, e.line);
    res.errors.forEach(e => {
      (errByModule[e.module] = errByModule[e.module] || new Set()).add(e.line);
      addMsg('', `<b>${esc(e.module)}:${e.line}</b> ${esc(e.message)}`, jump(e));
    });
    if (res.warnings.length) {
      const nW = res.warnings.length;
      addMsg('w-hd', `${nW} ${nW === 1 ? 'aviso' : 'avisos'} (no impiden ensamblar — clic para ir a la línea)`);
      res.warnings.forEach(e => {
        (warnByModule[e.module] = warnByModule[e.module] || new Set()).add(e.line);
        addMsg('w', `<b>${esc(e.module)}:${e.line}</b> ${esc(e.message)}`, jump(e));
      });
    }
    if (!savedOk) appendStorageWarning(box);
    renderGutter();

    if (!res.ok) {
      state.asm = null; state.image = null; state.addrMap = new Map();
      $('btnDlHex').disabled = $('btnDlBin').disabled = $('btnExportListing').disabled = true;
      $('btnLoad').disabled = true;
      $('outView').textContent = `Hay ${res.errors.length} error(es). Corregilos y volvé a ensamblar.`;
      return;
    }
    state.asm = res; state.image = res.bytes; state.imageName = 'programa';
    state.addrMap = buildAddrMap(res);
    addMsg('ok', `Ensamblado correcto: ${res.size} bytes desde x${hex4(res.origin)} hasta x${hex4(res.endAddr - 1)}.`);
    $('btnDlHex').disabled = $('btnDlBin').disabled = $('btnExportListing').disabled = false;
    $('btnLoad').disabled = false;
    renderOut();
  }

  function focusLine(line) {
    const ed = $('editor');
    const lines = ed.value.split('\n');
    let pos = 0;
    for (let i = 0; i < line - 1 && i < lines.length; i++) pos += lines[i].length + 1;
    ed.focus();
    ed.setSelectionRange(pos, pos + (lines[line - 1] || '').length);
    ed.scrollTop = Math.max(0, (line - 4) * 18.75);
  }

  function renderOut() {
    const o = $('outView');
    if (!state.image) { o.textContent = 'Todavía no se ensambló nada.'; return; }
    if (state.outView === 'hex') {
      o.textContent = '; Los 2 primeros bytes = origen (little-endian)\n' + Assembler.toHex(state.image);
    } else if (!state.asm) {
      o.textContent = 'Este programa se cargó desde un archivo .hex/.bin: no hay listado ni símbolos.';
    } else if (state.outView === 'listing') {
      o.textContent = state.asm.listingText;
    } else {
      o.textContent = state.asm.symbols.map(s => `x${hex4(s.addr)}  ${s.name.padEnd(22)} ${s.module}`).join('\n') || '(sin símbolos)';
    }
  }

  /* ---------- descargas, exportación y carga .zip / .asm ---------- */
  function download(name, data, type) {
    const blob = data instanceof Blob ? data : new Blob([data], { type });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob); a.download = name;
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  }

  function formatTraceText(c) {
    if (!c || c.status !== 'FAULT' || !c.fault) return '';
    const fLoc = state.addrMap.get(c.fault.pc);
    const lines = [
      '',
      '=== DEPURACIÓN DE FALLO (FAULT) ===',
      `Falta: ${c.fault.kind} — ${c.fault.message}`,
      `PC: x${hex4(c.fault.pc)}`,
      `Ubicación: ${fLoc ? `${fLoc.module}:${fLoc.line}` : '(sin mapa de fuentes — imagen .hex/.bin)'}`,
      '',
      'Últimas instrucciones ejecutadas (hasta 15, de la más antigua a la más reciente):'
    ];
    const trace = c.getTrace();
    if (!trace.length) {
      lines.push('  (sin instrucciones ejecutadas)');
    } else {
      trace.forEach((tr, idx) => {
        const loc = state.addrMap.get(tr.pc);
        const locTxt = (loc ? `${loc.module}:${loc.line}` : '-').padEnd(22);
        const regsTxt = tr.regs.map((v, r) => `R${r}=${hex4(v)}`).join(' ');
        const mark = idx === trace.length - 1 ? '>>' : '  ';
        lines.push(`${mark} ${String(idx + 1).padStart(2, ' ')}. ${locTxt} x${hex4(tr.pc)}  ${tr.disasm.padEnd(20)}  ${regsTxt}`);
      });
    }
    return lines.join('\n') + '\n';
  }

  function exportListing() {
    const parts = [];
    if (state.asm) {
      parts.push(`; Listado ensamblado (${state.asm.size} bytes, x${hex4(state.asm.origin)}..x${hex4(state.asm.endAddr - 1)})`);
      parts.push(state.asm.listingText);
      if (state.asm.warnings && state.asm.warnings.length) {
        parts.push('\n=== AVISOS DEL ENSAMBLADOR ===');
        parts.push(Assembler.formatMessages(state.asm.warnings));
      }
    } else if (state.image) {
      parts.push('; Imagen cargada desde archivo .hex/.bin (sin listado fuente)');
      parts.push(Assembler.toHex(state.image));
    }
    if (state.cpu && state.cpu.status === 'FAULT') {
      parts.push(formatTraceText(state.cpu));
    }
    if (!parts.length) return;
    download(state.imageName + '_listado.txt', parts.join('\n') + '\n', 'text/plain;charset=utf-8');
  }

  function askImportMode(parsed, sourceLabel) {
    return new Promise(resolve => {
      const dlg = $('importDialog');
      $('impSummary').textContent = `${sourceLabel}: ${parsed.modules.length} módulo(s) .asm` +
        (parsed.main ? ` (principal: ${parsed.main.name})` : '') +
        `, ${parsed.ignored} archivo(s) ignorado(s).`;
      const wBox = $('impWarnings');
      wBox.innerHTML = parsed.warnings.map(w => `<div class="m w">${esc(w)}</div>`).join('');

      const finish = choice => {
        closeDialog(dlg);
        $('btnImpReplace').onclick = null;
        $('btnImpAdd').onclick = null;
        $('btnImpCancel').onclick = null;
        dlg.oncancel = null;
        resolve(choice);
      };
      $('btnImpReplace').onclick = () => finish('replace');
      $('btnImpAdd').onclick = () => finish('add');
      $('btnImpCancel').onclick = () => finish(null);
      dlg.oncancel = e => { e.preventDefault(); finish(null); };

      if (typeof dlg.showModal === 'function') dlg.showModal();
      else dlg.setAttribute('open', '');
    });
  }

  async function applyImportedEntries(entries, sourceLabel) {
    state.modules[state.active].source = $('editor').value;
    const parsed = Assembler.processModuleEntries(entries);
    const box = $('asmMsgs');
    if (!parsed.modules.length) {
      box.innerHTML = `<div class="m w">0 módulos cargados, ${parsed.ignored} archivo(s) ignorado(s) (${esc(sourceLabel)}). No se encontraron archivos .asm válidos.</div>`;
      parsed.warnings.forEach(w => {
        const d = document.createElement('div'); d.className = 'm w'; d.textContent = w; box.appendChild(d);
      });
      return;
    }
    const mode = await askImportMode(parsed, sourceLabel);
    if (!mode) return;

    const merged = Assembler.mergeModuleLists(state.modules, parsed, mode);
    state.modules = merged.modules;
    state.active = merged.activeIndex;
    errByModule = {};
    warnByModule = {};
    const savedOk = saveModules();
    renderTabs();
    loadEditor();

    box.innerHTML = '';
    const sum = document.createElement('div');
    sum.className = 'm ok';
    sum.textContent = `${parsed.modules.length} módulos cargados, ${parsed.ignored} archivos ignorados` +
      (parsed.main ? ` (principal: ${parsed.main.name}).` : '.');
    box.appendChild(sum);
    if (parsed.warnings.length) {
      const hd = document.createElement('div');
      hd.className = 'm w-hd';
      hd.textContent = `${parsed.warnings.length} ${parsed.warnings.length === 1 ? 'aviso' : 'avisos'} al importar`;
      box.appendChild(hd);
      parsed.warnings.forEach(w => {
        const d = document.createElement('div');
        d.className = 'm w';
        d.textContent = w;
        box.appendChild(d);
      });
    }
    if (!savedOk) appendStorageWarning(box);
  }

  async function readZipEntries(buffer) {
    if (typeof window.JSZip === 'undefined') {
      throw new Error('No se pudo cargar JSZip (verificá tu conexión a internet para abrir archivos .zip).');
    }
    const zip = await window.JSZip.loadAsync(buffer);
    const entries = [];
    const jobs = [];
    zip.forEach((relPath, entry) => {
      if (entry.dir) return;
      jobs.push(entry.async('string').then(text => entries.push({ path: relPath, text })));
    });
    await Promise.all(jobs);
    return entries;
  }

  async function fetchBenchmark() {
    const resp = await fetch(BENCHMARK_ZIP, { cache: 'no-cache' });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const entries = await readZipEntries(await resp.arrayBuffer());
    const parsed = Assembler.processModuleEntries(entries);
    if (!parsed.modules.length) throw new Error('El benchmark no contiene módulos .asm válidos');
    return parsed;
  }

  async function restoreBenchmark() {
    if (!confirm('¿Reemplazar los módulos actuales con el benchmark del Grupo 7?')) return;
    const btn = $('btnRestoreBench');
    const box = $('asmMsgs');
    if (btn) btn.disabled = true;
    try {
      const parsed = await fetchBenchmark();
      state.modules = parsed.modules.map(m => ({ name: m.name, source: m.source }));
      state.active = 0;
      errByModule = {};
      warnByModule = {};
      const savedOk = saveModules();
      renderTabs();
      loadEditor();
      box.innerHTML = '';
      const ok = document.createElement('div');
      ok.className = 'm ok';
      ok.textContent = `Benchmark restaurado: ${parsed.modules.length} módulos cargados` +
        (parsed.main ? ` (principal: ${parsed.main.name}).` : '.');
      box.appendChild(ok);
      if (!savedOk) appendStorageWarning(box);
    } catch (_err) {
      box.innerHTML = '<div class="m w">No se pudo cargar el benchmark; usá Cargar .zip</div>';
    } finally {
      if (btn) btn.disabled = false;
    }
  }

  async function loadZipFile(file) {
    const box = $('asmMsgs');
    try {
      const entries = await readZipEntries(await file.arrayBuffer());
      await applyImportedEntries(entries, file.name);
    } catch (err) {
      box.innerHTML = `<div class="m">Error al leer el archivo .zip: ${esc(err.message || String(err))}</div>`;
    }
  }

  async function loadAsmFiles(fileList) {
    const files = Array.from(fileList || []);
    if (!files.length) return;
    const entries = [];
    for (const f of files) {
      const text = await f.text();
      entries.push({ path: f.webkitRelativePath || f.name, text });
    }
    const label = files.length === 1 ? files[0].name : `${files.length} archivos`;
    await applyImportedEntries(entries, label);
  }

  async function downloadZip() {
    const box = $('asmMsgs');
    if (typeof window.JSZip === 'undefined') {
      box.innerHTML = '<div class="m">No se pudo cargar JSZip (verificá tu conexión a internet para exportar .zip).</div>';
      return;
    }
    state.modules[state.active].source = $('editor').value;
    const zip = new window.JSZip();
    const mainIdx = state.modules.findIndex(m => /^main/i.test(m.name.replace(/\.asm$/i, '')));
    const rootIdx = mainIdx >= 0 ? mainIdx : 0;
    const ensureAsm = n => /\.asm$/i.test(n) ? n : n + '.asm';

    state.modules.forEach((m, i) => {
      const fname = ensureAsm(m.name);
      const path = i === rootIdx ? fname : `lib/${fname}`;
      zip.file(path, m.source);
    });
    const blob = await zip.generateAsync({ type: 'blob' });
    download('isa-5b-modulos.zip', blob, 'application/zip');
  }

  /* ---------- simulador ---------- */
  function newCpu() {
    state.cpu = new CPU({
      onOutput: s => appendConsole(s),
      maxInstructions: Math.max(1, parseInt($('limit').value, 10) || 5000000)
    });
  }

  function loadSim() {
    if (!state.image) return;
    stopRun();
    try {
      newCpu();
      state.cpu.load(state.image);
    } catch (e) {
      $('asmMsgs').innerHTML = `<div class="m">${esc(e.message)}</div>`;
      return;
    }
    state.loaded = true;
    state.prevRegs = null; state.prevWatch = {};
    $('console').textContent = '';
    $('copyStatus').textContent = '';
    $('copyFallback').hidden = true;
    ['btnRun', 'btnStep', 'btnReset'].forEach(id => $(id).disabled = false);
    $('memAddr').value = hex4(state.cpu.pc);
    refresh();
  }

  function resetSim() {
    if (!state.cpu) return;
    stopRun();
    state.cpu.maxInstructions = Math.max(1, parseInt($('limit').value, 10) || 5000000);
    state.cpu.reset();
    state.prevRegs = null; state.prevWatch = {};
    $('console').textContent = '';
    $('copyStatus').textContent = '';
    $('copyFallback').hidden = true;
    refresh();
  }

  function stepOnce() {
    if (!state.cpu) return;
    state.cpu.maxInstructions = Math.max(1, parseInt($('limit').value, 10) || 5000000);
    state.cpu.step();
    refresh();
    if (state.cpu.status === 'WAIT_INPUT') $('inText').focus();
  }

  let raf = 0;
  function startRun() {
    if (!state.cpu || state.running) return;
    const c = state.cpu;
    if (c.status === 'HALTED' || c.status === 'FAULT' || c.status === 'LIMIT') return;
    c.maxInstructions = Math.max(1, parseInt($('limit').value, 10) || 5000000);
    state.running = true;
    $('btnRun').textContent = 'Pausar';
    const tick = () => {
      if (!state.running) return;
      const n = parseInt($('speed').value, 10);
      const s = c.run(n);
      refresh(n > 200);
      if (s === 'RUNNING') { raf = requestAnimationFrame(tick); return; }
      state.running = false;
      $('btnRun').textContent = 'Ejecutar (Run)';
      refresh();
      if (s === 'WAIT_INPUT') $('inText').focus();
    };
    raf = requestAnimationFrame(tick);
  }
  function stopRun() {
    state.running = false;
    cancelAnimationFrame(raf);
    $('btnRun').textContent = 'Ejecutar (Run)';
  }

  function appendConsole(s) {
    const c = $('console');
    c.textContent += s;
    c.scrollTop = c.scrollHeight;
  }

  /* ---------- render del estado ---------- */
  const STATUS = {
    READY: ['LISTO', 'ready'],
    RUNNING: ['EJECUTANDO', 'running'],
    WAIT_INPUT: ['ESPERANDO ENTRADA', 'wait'],
    HALTED: ['HALT', 'halted'],
    FAULT: ['FALTA', 'fault'],
    LIMIT: ['LÍMITE ALCANZADO', 'limit']
  };

  function renderFaultTrace(c) {
    const box = $('faultTrace');
    if (!c || c.status !== 'FAULT' || !c.fault) {
      box.hidden = true;
      return;
    }
    box.hidden = false;
    const fLoc = state.addrMap.get(c.fault.pc);
    $('faultTitle').textContent = `${c.fault.kind}: ${c.fault.message}`;
    $('faultPc').textContent = `PC = x${hex4(c.fault.pc)}`;
    const locEl = $('faultLoc');
    if (fLoc) {
      locEl.innerHTML = `Instrucción que falló: <button type="button" class="ghost" id="btnJumpFault">${esc(fLoc.module)}:${fLoc.line}</button>`;
      $('btnJumpFault').onclick = () => jumpToModLine(fLoc.module, fLoc.line);
    } else {
      locEl.textContent = 'Ubicación: (sin mapa de fuentes — imagen cargada desde archivo .hex/.bin)';
    }

    const trace = c.getTrace();
    const list = $('faultTraceList');
    if (!trace.length) {
      list.innerHTML = '<div class="trace-row">(sin instrucciones previas)</div>';
      return;
    }
    list.innerHTML = trace.map((tr, idx) => {
      const loc = state.addrMap.get(tr.pc);
      const isLast = idx === trace.length - 1;
      const regsTxt = tr.regs.map((v, r) => `R${r}=${hex4(v)}`).join(' ');
      const dataAttr = loc ? ` data-mod="${esc(loc.module)}" data-line="${loc.line}"` : '';
      return `<div class="trace-row${isLast ? ' last' : ''}${loc ? ' clickable' : ''}"${dataAttr}>` +
        `<div class="trace-top"><span class="trace-idx">${idx + 1}.</span>` +
        `<span class="trace-loc">${loc ? esc(`${loc.module}:${loc.line}`) : '—'}</span>` +
        `<span class="trace-pc">x${hex4(tr.pc)}</span>` +
        `<span class="trace-dis">${esc(tr.disasm)}</span></div>` +
        `<div class="trace-regs">${regsTxt}</div></div>`;
    }).join('');
    list.onclick = e => {
      const row = e.target.closest('.trace-row[data-mod]');
      if (!row) return;
      jumpToModLine(row.dataset.mod, parseInt(row.dataset.line, 10));
    };
  }

  function refresh(light) {
    const c = state.cpu;
    const pill = $('statusPill'), fm = $('faultMsg');
    if (!c || !state.loaded) {
      pill.textContent = 'SIN CARGAR'; pill.className = 'pill idle'; fm.hidden = true;
      $('faultTrace').hidden = true;
      return;
    }
    const st = c.status;
    const [txt, cls] = STATUS[st] || [st, 'idle'];
    pill.textContent = state.running && st === 'RUNNING' ? 'EJECUTANDO' : txt;
    pill.className = 'pill ' + cls;
    if (st === 'FAULT') {
      const fLoc = state.addrMap.get(c.fault.pc);
      fm.hidden = false;
      fm.textContent = `${c.fault.kind} en x${hex4(c.fault.pc)}${fLoc ? ` (${fLoc.module}:${fLoc.line})` : ''}: ${c.fault.message}`;
    } else if (st === 'LIMIT') {
      fm.hidden = false;
      fm.textContent = `Se alcanzó el límite de ${c.maxInstructions} instrucciones (¿bucle infinito?). Subí el límite para seguir.`;
    } else {
      fm.hidden = true;
    }

    $('vPC').textContent = 'x' + hex4(c.pc);
    $('vIR').textContent = c.instrCount ? 'x' + hex4(c.ir) : '----';
    $('fN').classList.toggle('on', c.n);
    $('fZ').classList.toggle('on', c.z);
    $('fP').classList.toggle('on', c.p);
    renderRegs(c);
    renderMetrics(c);
    if (!light) { renderFaultTrace(c); renderDisasm(c); renderMem(c); renderWatch(c); }
    else if (st === 'FAULT') { renderFaultTrace(c); }
  }

  function renderRegs(c) {
    const tb = document.querySelector('#regs tbody');
    if (!tb.children.length) {
      for (let i = 0; i < 8; i++) tb.insertAdjacentHTML('beforeend', `<tr><td>R${i}</td><td></td><td></td><td class="bin"></td></tr>`);
    }
    for (let i = 0; i < 8; i++) {
      const v = c.regs[i], tr = tb.children[i];
      tr.children[1].textContent = 'x' + hex4(v);
      tr.children[2].textContent = s16(v);
      tr.children[2].className = s16(v) < 0 ? 'neg' : '';
      tr.children[3].textContent = v.toString(2).padStart(16, '0').replace(/(.{4})(?=.)/g, '$1 ');
      tr.classList.toggle('chg', !!state.prevRegs && state.prevRegs[i] !== v);
    }
    state.prevRegs = Array.from(c.regs);
  }

  function renderDisasm(c) {
    const lines = [];
    let a = c.pc;
    for (let i = 0; i < 8; i++) {
      const w = c.peek16(a);
      lines.push(`${i === 0 ? '▶' : ' '} x${hex4(a)}  ${hex4(w)}  ${c.disasm(w, a)}`);
      a = (a + 2) & 0xFFFF;
    }
    $('disasm').innerHTML = lines.map((l, i) => i === 0 ? `<span class="cur">${esc(l)}</span>` : esc(l)).join('\n');
  }

  function renderMem(c) {
    let base;
    if ($('follow').checked) base = c.pc & 0xFFF0;
    else base = (parseInt($('memAddr').value, 16) || 0) & 0xFFF0;
    if ($('follow').checked) $('memAddr').value = hex4(c.pc);
    base = Math.min(base, 0x10000 - 16 * 12);
    let h = '<div class="hd"><span></span>' + Array.from({ length: 16 }, (_, i) => `<span class="b">+${i.toString(16).toUpperCase()}</span>`).join('') + '<span class="asc">ASCII</span></div>';
    for (let r = 0; r < 12; r++) {
      const a0 = base + r * 16;
      let cells = '', asc = '';
      for (let i = 0; i < 16; i++) {
        const a = a0 + i, v = c.mem[a], t = c.touch[a];
        let cls = 'b' + (v === 0 ? ' z' : '');
        if (t & 8) cls += ' l';
        if (t & 1) cls += ' f';
        if (t & 2) cls += ' rd';
        if (t & 4) cls += ' w';
        if (a === c.pc || a === c.pc + 1) cls += ' pc';
        cells += `<span class="${cls}" title="x${hex4(a)}">${hex2(v)}</span>`;
        asc += v >= 32 && v < 127 ? esc(String.fromCharCode(v)) : '·';
      }
      h += `<div class="r"><span class="a">${hex4(a0)}</span>${cells}<span class="asc">${asc}</span></div>`;
    }
    $('mem').innerHTML = h;
  }

  function renderWatch(c) {
    const box = $('watch');
    if (!state.asm) { box.textContent = 'Sin símbolos (imagen cargada desde archivo).'; return; }
    let h = '', cur = {};
    state.asm.symbols.filter(s => s.kind !== 'instr' && s.kind !== 'string' && s.kind !== 'end').forEach(s => {
      const v = c.peek16(s.addr);
      const k = s.module + ':' + s.name + ':' + s.addr;
      cur[k] = v;
      const chg = state.prevWatch[k] !== undefined && state.prevWatch[k] !== v;
      h += `<div data-a="${s.addr}" class="${chg ? 'chg' : ''}" title="${esc(s.module)}"><span class="n">${esc(s.name)}</span><span class="h">x${hex4(s.addr)}</span><span class="v">${s16(v)}</span><span class="h">x${hex4(v)}</span></div>`;
    });
    state.prevWatch = cur;
    box.innerHTML = h || '(sin símbolos)';
  }

  function renderMetrics(c) {
    const m = c.metrics();
    $('mInstr').textContent = m.instructions.toLocaleString('es-AR');
    $('mInstrOS').textContent = m.instructionsWithOS.toLocaleString('es-AR');
    $('mLoaded').textContent = m.loadedBytes;
    $('mWritten').textContent = m.writtenBytes;
    $('mRd').textContent = m.memReads.toLocaleString('es-AR');
    $('mWr').textContent = m.memWrites.toLocaleString('es-AR');
    const ops = $('ops');
    if (!ops.children.length) {
      for (let i = 0; i < 32; i++) ops.insertAdjacentHTML('beforeend', `<div class="z"><span class="oc">${i.toString(2).padStart(5, '0')}</span><span class="nm"></span><span class="ct">0</span></div>`);
    }
    for (let i = 0; i < 32; i++) {
      const d = ops.children[i];
      d.className = m.byOpcode[i] ? '' : 'z';
      d.children[1].textContent = m.opNames[i].replace('(libre)', '—');
      d.children[1].title = m.opNames[i];
      d.children[2].textContent = m.byOpcode[i];
    }
  }

  function formatMetricsReport(c) {
    const m = c.metrics();
    const lines = [
      `Instrucciones sin SO: ${m.instructions}`,
      `Instrucciones del SO: ${m.osInstructions}`,
      `Instrucciones con SO: ${m.instructionsWithOS}`,
      `Bytes cargados: ${m.loadedBytes}`,
      `Bytes guardados: ${m.writtenBytes}`,
      `Lecturas de datos: ${m.memReads}`,
      `Escrituras de datos: ${m.memWrites}`,
      'Opcodes ejecutados (> 0):'
    ];
    let any = false;
    for (let i = 0; i < 32; i++) {
      if (m.byOpcode[i] > 0) {
        any = true;
        lines.push(`  ${i.toString(2).padStart(5, '0')} ${m.opNames[i]}: ${m.byOpcode[i]}`);
      }
    }
    if (!any) lines.push('  (ninguno)');
    return lines.join('\n');
  }

  async function copyMetrics() {
    const c = state.cpu || new CPU();
    const text = formatMetricsReport(c);
    $('copyStatus').textContent = '';
    if (navigator.clipboard && typeof navigator.clipboard.writeText === 'function') {
      try {
        await navigator.clipboard.writeText(text);
        $('copyFallback').hidden = true;
        $('copyStatus').textContent = 'Métricas copiadas al portapapeles.';
        return;
      } catch (_e) { /* usar fallback manual */ }
    }
    $('copyText').value = text;
    $('copyFallback').hidden = false;
    $('copyText').focus();
    $('copyText').select();
  }

  /* ---------- referencia ISA y Autotest ---------- */
  const PDF_DOCS = [
    ['ISA Pasos 1 y 2 (tablas definitivas)', 'ISA_Grupo_7___Pasos_1_y_2__tablas_definitivas__.pdf'],
    ['Guía paso a paso Lab 3c (V2)', 'Guia_Paso_a_Paso_Lab3c_Grupo7_V2.pdf'],
    ['Enunciado Lab 3 (2026)', 'Lab3_2026.pdf'],
    ['Enunciado Lab 3c (2026)', 'Lab3_2026_c.pdf']
  ];

  function openRefDialog() {
    const d = $('refDialog');
    const list = $('refList');
    if (!d || !list) return;
    const prefix = 'documentacion/informacion%20utilizada%20en%20el%20proyecto/';
    list.innerHTML = PDF_DOCS
      .map(([title, file]) => `<li><a href="${esc(prefix + file)}" target="_blank" rel="noopener">${esc(title)}</a></li>`)
      .join('');
    if (typeof d.showModal === 'function') d.showModal();
    else d.setAttribute('open', '');
  }

  function runAndRenderAutotest() {
    const res = window.Autotest.runAll();
    const sum = $('atSummary');
    sum.textContent = `${res.passed}/${res.total} correctas` + (res.failed ? ` (${res.failed} fallidas)` : '');
    sum.className = 'dlg-sum ' + (res.failed ? 'err' : 'ok');
    $('atList').innerHTML = res.results.map(r =>
      `<div class="at-row ${r.ok ? 'ok' : 'err'}"><span class="st">${r.ok ? '✓' : '✗'}</span><div><div class="sec">${esc(r.section)}</div><div>${esc(r.name)}</div><div class="det">${esc(r.detail)}</div></div></div>`
    ).join('');
  }

  function openAutotestDialog() {
    runAndRenderAutotest();
    const d = $('autotestDialog');
    if (typeof d.showModal === 'function') d.showModal();
    else d.setAttribute('open', '');
  }

  function closeDialog(d) {
    if (typeof d.close === 'function' && d.open) d.close();
    else d.removeAttribute('open');
  }

  /* ---------- eventos ---------- */
  function bind() {
    $('editor').addEventListener('input', () => {
      state.modules[state.active].source = $('editor').value;
      renderGutter(); saveModules();
    });
    $('editor').addEventListener('scroll', () => { $('gutter').scrollTop = $('editor').scrollTop; });
    $('editor').addEventListener('keydown', e => {
      if (e.key === 'Tab') {
        e.preventDefault();
        const ed = e.target, s = ed.selectionStart;
        ed.setRangeText('        ', s, ed.selectionEnd, 'end');
        ed.dispatchEvent(new Event('input'));
      }
    });
    $('btnAddMod').onclick = () => {
      state.modules.push({ name: uniqueName('modulo.asm'), source: '; Nuevo módulo\n\n.END\n' });
      state.active = state.modules.length - 1; saveModules(); renderTabs(); loadEditor();
    };
    $('btnRenameMod').onclick = () => {
      const cur = state.modules[state.active];
      const n = prompt('Nombre del módulo:', cur.name);
      if (!n || !n.trim() || n === cur.name) return;
      if (state.modules.some(m => m.name === n.trim())) {
        $('asmMsgs').innerHTML = `<div class="m">Ya existe un módulo llamado ${esc(n.trim())}.</div>`;
        return;
      }
      cur.name = n.trim(); saveModules(); renderTabs();
    };
    $('btnDelMod').onclick = () => {
      if (state.modules.length <= 1) return;
      if (!confirm(`¿Quitar el módulo ${state.modules[state.active].name}?`)) return;
      state.modules.splice(state.active, 1);
      state.active = Math.max(0, state.active - 1); saveModules(); renderTabs(); loadEditor();
    };
    $('fileAsm').onchange = async e => {
      await loadAsmFiles(e.target.files);
      e.target.value = '';
    };
    $('fileZip').onchange = async e => {
      const f = e.target.files[0];
      e.target.value = '';
      if (f) await loadZipFile(f);
    };
    $('btnDlZip').onclick = downloadZip;
    $('btnRestoreBench').onclick = restoreBenchmark;

    // Arrastrar y soltar un .zip o archivos .asm sobre cualquier parte de la página
    let dragDepth = 0;
    const hasFiles = e => e.dataTransfer && Array.from(e.dataTransfer.types || []).includes('Files');
    window.addEventListener('dragenter', e => {
      if (!hasFiles(e)) return;
      e.preventDefault();
      dragDepth++;
      $('dropOverlay').hidden = false;
    });
    window.addEventListener('dragover', e => {
      if (!hasFiles(e)) return;
      e.preventDefault();
      e.dataTransfer.dropEffect = 'copy';
    });
    window.addEventListener('dragleave', e => {
      if (!hasFiles(e)) return;
      dragDepth = Math.max(0, dragDepth - 1);
      if (dragDepth === 0) $('dropOverlay').hidden = true;
    });
    window.addEventListener('drop', async e => {
      if (!hasFiles(e)) return;
      e.preventDefault();
      dragDepth = 0;
      $('dropOverlay').hidden = true;
      const files = Array.from(e.dataTransfer.files || []);
      if (!files.length) return;
      const zipFile = files.find(f => /\.zip$/i.test(f.name));
      if (zipFile) await loadZipFile(zipFile);
      else await loadAsmFiles(files);
    });

    $('btnAssemble').onclick = assemble;
    document.querySelectorAll('.subtab').forEach(b => b.onclick = () => {
      document.querySelectorAll('.subtab').forEach(x => {
        x.classList.remove('on');
        x.setAttribute('aria-selected', 'false');
      });
      b.classList.add('on');
      b.setAttribute('aria-selected', 'true');
      state.outView = b.dataset.view;
      renderOut();
    });
    $('btnDlHex').onclick = () => download(state.imageName + '.hex', Assembler.toHex(state.image) + '\n', 'text/plain');
    $('btnDlBin').onclick = () => download(state.imageName + '.bin', state.image, 'application/octet-stream');
    $('btnExportListing').onclick = exportListing;
    $('fileImg').onchange = async e => {
      const f = e.target.files[0]; if (!f) return;
      try {
        let bytes;
        if (/\.bin$/i.test(f.name)) bytes = new Uint8Array(await f.arrayBuffer());
        else bytes = CPU.parseHex(await f.text());
        if (bytes.length < 2) throw new Error('El archivo no tiene datos (faltan los 2 bytes de origen)');
        const origin = bytes[0] | (bytes[1] << 8);
        if (origin & 1) throw new Error(`Origen impar x${hex4(origin)}: debe empezar en dirección par`);
        if (origin + (bytes.length - 2) > CPU.MEM_SIZE) throw new Error('La imagen excede los 64 KB de memoria');
        state.image = bytes; state.asm = null; state.addrMap = new Map(); state.imageName = f.name.replace(/\.[^.]+$/, '');
        $('asmMsgs').innerHTML = `<div class="m ok">Imagen cargada desde ${esc(f.name)}: origen x${hex4(origin)}, ${bytes.length - 2} bytes.</div>`;
        $('btnDlHex').disabled = $('btnDlBin').disabled = $('btnExportListing').disabled = false; $('btnLoad').disabled = false;
        renderOut();
      } catch (err) {
        $('asmMsgs').innerHTML = `<div class="m">${esc(err.message)}</div>`;
      }
      e.target.value = '';
    };

    $('btnLoad').onclick = loadSim;
    $('btnRun').onclick = () => state.running ? (stopRun(), refresh()) : startRun();
    $('btnStep').onclick = () => { stopRun(); stepOnce(); };
    $('btnReset').onclick = resetSim;
    $('btnGo').onclick = () => { $('follow').checked = false; if (state.cpu) renderMem(state.cpu); };
    $('memAddr').addEventListener('keydown', e => { if (e.key === 'Enter') $('btnGo').click(); });
    $('follow').onchange = () => { if (state.cpu) renderMem(state.cpu); };
    $('watch').onclick = e => {
      const d = e.target.closest('div[data-a]'); if (!d || !state.cpu) return;
      $('follow').checked = false; $('memAddr').value = hex4(+d.dataset.a); renderMem(state.cpu);
    };
    $('inKeyMode').onchange = () => {
      state.keyMode = $('inKeyMode').checked;
      store.set('lc3g7.keyMode', String(state.keyMode));
      updateKeyModeUI();
      $('inText').focus();
    };
    $('inText').addEventListener('keydown', e => {
      if (!state.keyMode) return;
      const ch = keyEventToChar(e);
      if (ch === null) return;
      e.preventDefault();
      sendSingleChar(ch);
    });
    $('inText').addEventListener('input', () => {
      if (!state.keyMode) return;
      const val = $('inText').value;
      if (!val) return;
      $('inText').value = '';
      if (!state.cpu) return;
      for (const ch of val) state.cpu.pushInput(ch);
      if (state.cpu.status === 'WAIT_INPUT') { state.cpu.status = 'RUNNING'; startRun(); }
    });
    $('inForm').onsubmit = e => {
      e.preventDefault();
      if (!state.cpu) return;
      if (state.keyMode) {
        const t = $('inText').value;
        $('inText').value = '';
        if (!t) return;
        for (const ch of t) state.cpu.pushInput(ch);
      } else {
        const t = $('inText').value;
        state.cpu.pushInput(t + '\n');
        $('inText').value = '';
      }
      if (state.cpu.status === 'WAIT_INPUT') { state.cpu.status = 'RUNNING'; startRun(); }
    };
    $('btnClearCon').onclick = () => { $('console').textContent = ''; };
    $('btnCopyMetrics').onclick = copyMetrics;

    if ($('btnRefIsa')) $('btnRefIsa').onclick = openRefDialog;
    if ($('btnCloseRef')) $('btnCloseRef').onclick = () => closeDialog($('refDialog'));
    $('btnAutotest').onclick = openAutotestDialog;
    $('btnRunAutotest').onclick = runAndRenderAutotest;
    $('btnCloseAutotest').onclick = () => closeDialog($('autotestDialog'));

    document.querySelectorAll('.blk-btn[data-block]').forEach(btn => {
      btn.onclick = () => {
        const key = btn.dataset.block;
        state.blocks[key] = !state.blocks[key];
        if (state.blocks[key]) {
          if (key === 'registros' || key === 'disasm' || key === 'consola') state.blocks.runPanel = true;
          if (key === 'memgrid' || key === 'watch' || key === 'metrics') state.blocks.memPanel = true;
        }
        saveLayout();
        applyLayout();
      };
    });
    $('btnAsmTall').onclick = () => { state.asmTall = !state.asmTall; saveLayout(); applyLayout(); };
    $('btnAsmWide').onclick = () => { state.asmWide = !state.asmWide; saveLayout(); applyLayout(); };

    window.addEventListener('keydown', e => {
      if (e.target.matches('input, textarea, select')) return;
      if (e.key === 'F10') { e.preventDefault(); $('btnStep').click(); }
    });
  }

  /* ---------- inicio ---------- */
  async function startApp() {
    initLayout();
    applyLayout();
    updateKeyModeUI();
    renderRegs(new CPU());
    renderMetrics(new CPU());
    const initRes = await initModules();
    bind();
    renderTabs();
    loadEditor();
    if (initRes && initRes.fallback) {
      $('asmMsgs').innerHTML = '<div class="m w">No se pudo cargar el benchmark; usá Cargar .zip</div>';
    }
    $('limit').addEventListener('change', () => {
      if (state.cpu) state.cpu.maxInstructions = Math.max(1, parseInt($('limit').value, 10) || 5000000);
    });
    window.__sim = { state, assemble, loadSim, startRun, stepOnce, resetSim, keyEventToChar, restoreBenchmark }; // para pruebas
  }
  startApp();
}());
