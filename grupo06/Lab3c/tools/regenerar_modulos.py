from pathlib import Path
import re, json
root=Path(__file__).resolve().parents[1]/'benchmark'
dest=root/'modulos'; dest.mkdir(exist_ok=True)
# Numeros de linea de la copia original, para que cada cambio sea auditable.
immediate={
 'fromdec':{43,48,65,107,142}, 'fromhex':{80,85},
 'getline':{36}, 'getcfiltered':{44},
 'todec':{45,67,73,102,107,121,134,142,157,241,256,267},
 'MAIN_MENU_PROGRESO':{65,105,435,438,442,448,453},
 'g6_EXP':{196,261,262,263,310,346},
 'g19_cordic_multiplicacion':{257,349},
}
register={
 'MAIN_MENU_PROGRESO':{81,245,261,285,378,394,422},
 'g11_CORDICLog':{54,71,86},
 'g12_subrutina_grupo_12':{99},
 'g14_log_borchardt_q8_7':{219},
 'g22_Tabla_SIN_y_COS':{738,761},
}
immediate['MAIN_MENU']=set(immediate['MAIN_MENU_PROGRESO'])
register['MAIN_MENU']=set(register['MAIN_MENU_PROGRESO'])
# Menu G27 actualizado: indice unico + dos operandos + dos resultados.
immediate['MAIN_MENU_PROGRESO']={65,105,460}
register['MAIN_MENU_PROGRESO']={81,109,259,275,299,393,409,437}
changes=[]
for f in sorted((root/'originales').glob('*.asm')):
 name=f.stem; lines=f.read_text(encoding='utf-8-sig').splitlines(); out=[]
 for no,line in enumerate(lines,1):
  new=line
  # Las bibliotecas no establecen un origen propio.
  if name not in {'main_g27','bloque_g27'} and re.match(r'^\s*\.ORIG\b',line,re.I):new='; ISA3C: origen asignado por el programa principal.'
  m=re.match(r'^(.*?)\bADD\s+(R\d)[, ]+\s*(R\d)[, ]+\s*#(-?\d+)(.*)$',line,re.I)
  if m:
   prefix,d,s,value,tail=m.groups(); value=int(value)
   scale=no in immediate.get(name,set()) or (d.upper()==s.upper()=='R6' and name in {'g1_cordic_division','g5_Mul_Sucesiva_POW','g18_booth','g23_modulo_sqrt_nr'})
   if name=='getline' and no==23: # NOT end + 3 = -(end - 2)
    value=3; scale=False; new=f'{prefix}ADD {d}, {s}, #{value}{tail}'
   if scale:
    remaining=value*2; parts=[]; base=s
    while remaining:
     part=min(15,max(-16,remaining)); parts.append(f'{prefix}ADD {d}, {base}, #{part}'); base=d; remaining-=part;prefix='    '
    new='\n'.join(parts)+tail+' ; ISA3C: direccion en bytes'
  if no in register.get(name,set()):
   m=re.match(r'^(.*?)\bADD\s+(R\d)[, ]+\s*(R\d)[, ]+\s*(R\d)(.*)$',line,re.I)
   assert m,(name,no,line)
   prefix,d,s,t,tail=m.groups();assert d.upper()!=t.upper()
   new=f'{prefix}ADD {d}, {s}, {t}\n    ADD {d}, {d}, {t}{tail} ; ISA3C: indice de palabras a bytes'
  if name=='MAIN_MENU_PROGRESO' and (line.lstrip().startswith('(esta el programa') or line.lstrip().startswith('subrutinas?')):new='; ISA3C: comentario de origen: '+line
  if name=='g1_cordic_division' and line.lstrip().startswith('INI_LOOP ADD R4, R4, #0'):
   new=line.replace('ADD R4, R4, #0','AND R4, R4, #0')+' ; correccion: contador independiente del llamador'
  if new!=line:changes.append({'archivo':f.name,'linea_original':no,'antes':line,'despues':new})
  out.append(new)
 if name=='g22_Tabla_SIN_y_COS':
  # El original es un programa con dato fijo y HALT. Adaptador ABI sin alterar la tabla.
  body='\n'.join(out)
  body=body.replace('        HALT','        LD R0, ADAPT_EXIT_PTR\n        JMP R0\nADAPT_EXIT_PTR .FILL ADAPT_FIN')
  # Datos lejanos del original: literales locales, saltados por el flujo normal.
  counter=[0]
  def far_lea(m):
   counter[0]+=1; n=counter[0]; d,t=m.groups()
   return f'    LD {d}, ADAPT_PTR{n}\n    BR ADAPT_SKIP{n}\nADAPT_PTR{n} .FILL {t}\nADAPT_SKIP{n}'
  body=re.sub(r'^\s*LEA\s+(R\d)[, ]+\s*(\w+)[^\n]*',far_lea,body,flags=re.M|re.I)
  prefix='SENO_TABLA\n    ST R1, ADAPT_R1\n    AND R1, R1, #0\n    BR ADAPT_IN\nCOSENO_TABLA\n    ST R1, ADAPT_R1\n    AND R1, R1, #0\n    ADD R1, R1, #1\nADAPT_IN\n    ST R1, ADAPT_MODE\n'
  prefix+=''.join(f'    ST R{i}, ADAPT_R{i}\n' for i in range(2,8))
  prefix+='ADAPT_NORM\n    ADD R0, R0, #0\n    BRn ADAPT_NEG\n    LD R1, ADAPT_NEG_2PI\n    ADD R2, R0, R1\n    BRn ADAPT_READY\n    ADD R0, R2, #0\n    BR ADAPT_NORM\nADAPT_NEG\n    LD R1, ADAPT_2PI\n    ADD R0, R0, R1\n    BR ADAPT_NORM\nADAPT_READY\n    STI R0, ADAPT_ANGLE_PTR\n    BR INICIO\nADAPT_FIN\n    LD R0, ADAPT_MODE\n    BRp ADAPT_COS\n    ADD R0, R1, #0\n    BR ADAPT_RESTORE\nADAPT_COS\n    ADD R0, R2, #0\nADAPT_RESTORE\n'
  prefix+=''.join(f'    LD R{i}, ADAPT_R{i}\n' for i in range(1,8))
  prefix+='    RET\nADAPT_MODE .FILL #0\nADAPT_2PI .FILL #25736\nADAPT_NEG_2PI .FILL #-25736\nADAPT_ANGLE_PTR .FILL ANGULO_PRUEBA\n'
  prefix+=''.join(f'ADAPT_R{i} .FILL #0\n' for i in range(1,8))
  out=(prefix+body).splitlines()
  changes.append({'archivo':f.name,'nota':'Adaptador SENO_TABLA/COSENO_TABLA, entrada R0, retorno R0 y RET; literales locales para LEA fuera de alcance. Estas cargas internas actualizan NZP; se valida el resultado con casos de prueba.'})
 if name=='g21_senotaylor_subrutina':
  # Literales locales: LD/ST no alcanzan todas las variables de este programa.
  # LDI/STI conservan la operacion y NZP, sin usar un registro auxiliar.
  mapped=[]; literal=0
  for line in out:
   m=re.match(r'^(\s*)(LD|ST)\s+(R[0-7])[, ]+\s*(\w+)(.*)$',line,re.I)
   if m:
    literal+=1; indent,op,regname,target,tail=m.groups()
    mapped.extend([f'{indent}{op}I {regname}, SENO_PTR_{literal}{tail}',
                   f'    BR SENO_SKIP_{literal}',
                   f'SENO_PTR_{literal} .FILL {target}',
                   f'SENO_SKIP_{literal}'])
   else:mapped.append(line)
  out=mapped
 # La version sin modulos no se usa como calculadora integrada.
 body='\n'.join(out)
 if name=='g3_MultiplicacionSHIFTandADD':
  # Dos sumandos con bit 15 a cero no generan acarreo de 16 bits.
  # Que el resultado tenga signo negativo solo indica el cruce de 32767.
  old='        ADD     R0, R0, #0\n        BRn     Q8_ACARREO\n        BR      Q8_DESPLAZAR'
  assert body.count(old)==1
  body=body.replace(old,'        BR      Q8_DESPLAZAR ; sin acarreo para dos bajos positivos',1)
 if name=='MAIN_MENU_PROGRESO':body=body.replace('(se ejecutaria una subrutina...)','(opcion sin subrutina implementada en la version de origen)')
 # Rutas con la misma capitalizacion en sistemas de archivos sensibles a mayusculas.
 aliases={x.stem.lower():x.stem for x in (root/'originales').glob('*.asm')}
 def module_case(m):return aliases.get(m[1].lower(),m[1])+'-'+m[2]
 body=re.sub(r'\b([A-Za-z_][A-Za-z_0-9]*)-([A-Za-z_][A-Za-z_0-9]*)\b',module_case,body)
 (dest/f.name).write_text('; Adaptacion ISA3C; ver ../cambios_punteros.json y ../procedencia.json.\n'+body+'\n',encoding='utf-8')
(root/'cambios_punteros.json').write_text(json.dumps(changes,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(len(changes),'cambios de direccionamiento')

# Restaurar las traducciones optimizadas de esta version de ISA.
import runpy
runpy.run_path(str(Path(__file__).with_name("aplicar_optimizaciones.py")),run_name="__main__")
