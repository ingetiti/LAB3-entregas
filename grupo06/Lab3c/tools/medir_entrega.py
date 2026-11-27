"""Reúne métricas después de ejecutar probar.bat; no altera la ISA."""
from pathlib import Path
import csv
import hashlib
import json
import math
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/mediciones_finales'
OUT.mkdir(exist_ok=True)

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

bank = list(csv.DictReader((ROOT / 'build/benchmark.csv').open(encoding='utf-8')))
previous = list(csv.DictReader((ROOT / 'docs/comparacion_rendimiento.csv').open(encoding='utf-8')))
assert len(bank) == len(previous) == 37
by_name = {r['caso']: r for r in previous}
comparison = []
for row in bank:
    ref = by_name[row['caso']]
    assert row['resultado'] == 'OK'
    assert row['salida_R0'] == ref['salida_R0'] and row['salida_R1'] == ref['salida_R1']
    assert int(row['instrucciones']) == int(ref['integrada'])
    comparison.append({**row, 'instrucciones_estable': ref['estable'],
                       'instrucciones_experimental': ref['experimental']})
with (OUT / 'banco_comparado.csv').open('w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=list(comparison[0])); w.writeheader(); w.writerows(comparison)

programs = {}
for name, obj in [('menu_automatico', 'calculadora_automatica.obj'),
                  ('exp_demo', 'exp_isa3c.obj')]:
    run = subprocess.run([str(ROOT / 'build/simulador.exe'), str(ROOT / 'build' / obj)],
                         cwd=ROOT, capture_output=True, text=True, timeout=30, check=True)
    (OUT / (name + '.txt')).write_text(run.stdout, encoding='utf-8')
    metric = re.search(r'METRICAS (.+)', run.stdout).group(1)
    traffic = re.search(r'TRAFICO (.+)', run.stdout).group(1)
    programs[name] = {k: int(v) for k, v in re.findall(r'(\w+)=(\d+)', metric + ' ' + traffic)}
    programs[name]['objeto_bytes'] = (ROOT / 'build' / obj).stat().st_size
assert programs['menu_automatico']['instrucciones'] == 12706
assert programs['exp_demo']['instrucciones'] == 2204

rows = list(csv.DictReader((ROOT / 'build/exp_comparacion.csv').open(encoding='utf-8')))
assert len(rows) == 65536
assert {int(r['entrada_cruda']) for r in rows} == set(range(-32768, 32768))
maximum = None; minimum = None; relative = None
saturated = 0; ordinary = 0
for row in rows:
    raw = int(row['entrada_cruda']); x = raw / 4096.0
    y = int(row['salida_cruda']) / 256.0
    assert 0 <= int(row['salida_cruda']) <= 32767
    if int(row['estado']) == 1:
        saturated += 1
        continue
    ordinary += 1
    reference = math.exp(x)
    error = abs(y - reference)
    sample = {'entrada_cruda': raw, 'x': x, 'salida': y, 'referencia_exp_double': reference,
              'error_absoluto': error, 'error_relativo': error / reference}
    if maximum is None or error > maximum['error_absoluto']: maximum = sample
    if minimum is None or error < minimum['error_absoluto']: minimum = sample
    if relative is None or sample['error_relativo'] > relative['error_relativo']: relative = sample

summary = {
    'fecha': '2026-11-26',
    'version': 'ISA3C integrada 1.1 con EXP optimizada e interfaz Windows',
    'criterio': 'Misma entrada y salida binaria. Banco: solo llamada, sin impresión ni HALT del llamador. Menú: incluye sistema. No son ciclos físicos.',
    'banco': {'casos': len(bank), 'instrucciones_estable': sum(int(r['estable']) for r in previous),
              'instrucciones_experimental': sum(int(r['experimental']) for r in previous),
              'instrucciones_integrada': sum(int(r['instrucciones']) for r in bank),
              'imagen_bytes': (ROOT / 'build/funciones.obj').stat().st_size - 2},
    'programas': programs,
    'exp': {'entradas': len(rows), 'instrucciones_antes': sum(int(r['antes']) for r in rows),
            'instrucciones_despues': sum(int(r['despues']) for r in rows),
            'dominio_sin_saturacion': ordinary, 'entradas_saturadas_excluidas': saturated,
            'error_minimo': minimum, 'error_maximo': maximum, 'error_relativo_maximo': relative,
            'resolucion_entrada': 1 / 4096, 'resolucion_salida': 1 / 256,
            'referencia': 'math.exp de doble precisión sobre el x cuantizado; no incluye error de conversión de una entrada real anterior ni mide saturación como error de aproximación.',
            'vueltas_ruta_general': 6, 'vueltas_rutas_rapidas': 0},
    'sha256_evidencia': {str(p.relative_to(ROOT)).replace('\\', '/'): digest(p) for p in [
        ROOT / 'build/funciones.obj', ROOT / 'build/calculadora_automatica.obj',
        ROOT / 'build/exp_comparacion.csv', ROOT / 'build/benchmark.csv',
        ROOT / 'benchmark/modulos/g6_EXP.asm', ROOT / 'tests/test_exp_optimized.c']}
}
assert summary['banco']['instrucciones_integrada'] == 25206
assert summary['exp']['instrucciones_despues'] == 68450717
(OUT / 'resumen.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps(summary, ensure_ascii=False, indent=2))
