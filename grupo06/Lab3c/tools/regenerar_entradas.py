from pathlib import Path
root=Path(__file__).resolve().parents[1]
text=(root/'benchmark/originales/MAIN_MENU_PROGRESO.asm').read_text(encoding='utf-8-sig')
import re
imports=re.findall(r'^\.EXTERNAL\s+(\w+-\w+)',text,re.M)
assert len(imports)==26,len(imports)
ops=imports[6:]
out=['.ORIG x3000','HALT']+['    .FILL '+x for x in ops]+['    .EXTERNAL '+x for x in ops]+['.END']
(root/'benchmark/funciones.asm').write_text('\n'.join(out)+'\n',encoding='utf-8')
main='; ISA3C local. Ensamblar con -I benchmark/modulos; ejecutar el .obj con simulador.\n; Comentarios historicos del Grupo 27 a continuacion.\n'+(root/'benchmark/modulos/main_g27.asm').read_text(encoding='utf-8-sig')
(root/'benchmark/calculadora.asm').write_text(main,encoding='utf-8')
main=main.replace('AND R0 R0 #0','LEA R0 programa_del_menu',1)
(root/'benchmark/calculadora_automatica.asm').write_text(main,encoding='utf-8')
print('Funciones:', '\n'.join(f'{i}: {op}' for i,op in enumerate(ops)))

