from pathlib import Path
import hashlib,json
root=Path(__file__).resolve().parents[1]
records=json.loads(Path(__file__).with_name('optimizaciones_modulos.json').read_text(encoding='utf-8'))
for record in records:
    p=root/'benchmark/modulos'/record['archivo']
    digest=hashlib.sha256(p.read_bytes()).hexdigest()
    if digest==record['sha256_integrada']:continue
    accepted={record['sha256_base'],*record.get('sha256_anteriores',[])}
    if digest not in accepted:raise SystemExit('Modulo modificado sin reconocer: '+str(p))
    p.write_bytes(record['contenido'].encode('utf-8'))
    if hashlib.sha256(p.read_bytes()).hexdigest()!=record['sha256_integrada']:raise SystemExit('Hash inesperado: '+str(p))
print('Optimizaciones integradas: '+str(len(records))+' modulos.')
