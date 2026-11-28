from pathlib import Path
root = Path(__file__).resolve().parents[1]
# El banco adicional tiene veinte entradas y 37 casos; el menu recorre 23 operaciones.
ops = ['g1_cordic_division-CORDIC_DIV', 'g3_MultiplicacionSHIFTandADD-MULTIPLICARSHIFTANDADD', 'g4_potencia-EXP_RAPIDA', 'g5_Mul_Sucesiva_POW-Mul_Sucesiva_POW', 'g6_EXP-EXP_Q3_12', 'g7_mcm-MCM', 'g7_mcd-MCD', 'g9_sqrt_nr_dq16-SQRT_NR_DQ16', 'g10_division_larga-DIV_LONG', 'g11_CORDICLog-CORDIC_LOG_BASE', 'g12_subrutina_grupo_12-DIV_NEWTON', 'g14_log_borchardt_q8_7-LN_GENERAL_Q8_7', 'g15_G15_Q312_Q78-G15_Q312_Q78', 'g18_booth-MULT_BOOTH', 'g19_cordic_multiplicacion-CORDIC_MUL', 'g20_Cordic_reduccion_de_argumento-Reduccion_Argumento', 'g22_Tabla_SIN_y_COS-SENO_TABLA', 'g22_Tabla_SIN_y_COS-COSENO_TABLA', 'g23_modulo_sqrt_nr-SQRT_NR', 'g30_seno_cheb_pade-SEN_CHEB_PADE']
out = ['.ORIG x3000', 'HALT'] + ['    .FILL ' + x for x in ops] + ['    .EXTERNAL ' + x for x in ops] + ['.END']
(root/'benchmark/funciones.asm').write_text('\n'.join(out)+'\n', encoding='utf-8')
received = (root/'benchmark/main_grupo27.asm').read_text(encoding='utf-8-sig')
assert received.count('AND R0 R0 #0') == 1
interactive = '; BYTEX-16: main del Grupo 27 recibido el 27/11/2026; modo interactivo.\n' + received
(root/'benchmark/calculadora.asm').write_text(interactive, encoding='utf-8')
automatic = received.replace('AND R0 R0 #0', 'LEA R0 programa_del_menu_completo', 1)
(root/'benchmark/calculadora_automatica.asm').write_text('; BYTEX-16: mismos valores .FILL del main recibido; modo automatico completo.\n' + automatic, encoding='utf-8')
print('BYTEX-16: banco adicional de 20 entradas y benchmark completo de 23 operaciones regenerados.')
