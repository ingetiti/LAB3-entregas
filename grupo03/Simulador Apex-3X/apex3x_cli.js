// Uso:  node apex3x_cli.js asm salida.hex|bin principal.asm [modulo.asm ...]
//       node apex3x_cli.js run programa.hex|bin [limite_pasos] [entrada_de_teclado]
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
function loadCjs(rel) {
  const code = fs.readFileSync(path.join(__dirname, rel), 'utf8');
  const m = { exports: {} };
  new Function('module', 'exports', code)(m, m.exports);
  return m.exports;
}

const A = loadCjs('apex3x_assembler.js'), C = loadCjs('apex3x_cpu.js');
const [cmd, a, ...rest] = process.argv.slice(2);
if (cmd === 'asm') {
  const mods = rest.map(f => ({ name: f.replace(/^.*[\\/]/, '').replace(/\.\w+$/, ''), src: fs.readFileSync(f, 'utf8') }));
  const r = A.link(mods);
  if (r.errors.length) { console.error(r.errors.join('\n')); process.exit(1); }
  fs.writeFileSync(a, /\.bin$/i.test(a) ? A.toBin(r) : A.toHex(r));
  console.log(a + ': ' + r.size + ' bytes desde x' + r.origin.toString(16));
} else if (cmd === 'run') {
  const buf = fs.readFileSync(a), img = /\.bin$/i.test(a) ? A.fromBin(buf) : A.fromHex(buf.toString());
  const c = new C(); c.load(img.origin, img.bytes); if (rest[1]) c.feed(rest[1]);
  const lim = +rest[0] || 5e6; while (!c.halted && !c.waiting && c.count < lim) c.step();
  const hx = v => 'x' + v.toString(16).toUpperCase().padStart(4, '0');
  console.log(JSON.stringify({ instrucciones: c.count, instruccionesSO: c.so, instruccionesTotal: c.total, ciclos: c.cycles, tamanoPrograma: c.size, datosAccedidos: c.dcnt, picoPila: C.STACK - c.minSP,
    estado: c.err || (c.halted ? 'detenida' : c.waiting ? 'esperando entrada' : 'límite de pasos'), registros: [...c.r].map(hx), histograma: c.hist, salida: c.out }, null, 2));
} else console.log('uso: node apex3x_cli.js asm salida.hex principal.asm [mod.asm ...]  |  node apex3x_cli.js run programa.hex [limite] [entrada]');
