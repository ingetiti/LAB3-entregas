# Informe de benchmark: `lib`

- Archivos: **37**   (OK=28, FALLA=1, EXCEPCION=1, ENTRADA=6, OMITIDO=1)
- Tiempo total: 1.2 s

## Resultado por archivo

| archivo | tipo | modo | estado | instr | detalle |
|---|---|---|---|---:|---|
| g10_division_larga.asm | modulo | clasico | OK | 209 | entrada=DIVIDIR |
| g11_CORDICLog.asm | modulo | clasico | OK | 2592 | entrada=CORDIC_LOG_BASE |
| g12_subrutina_grupo_12.asm | modulo | clasico | OK | 2098 | entrada=DIV_NEWTON |
| g14_log_borchardt_q8_7.asm | modulo | clasico | OK | 5502 | entrada=LOG_BORCHARDT_Q8_7 |
| g15_G15_Q312_Q78.asm | modulo | clasico | OK | 199 | entrada=G15_Q312_Q78 |
| g18_booth.asm | modulo | clasico | OK | 5370 | entrada=MULT_BOOTH |
| g19_cordic_multiplicacion.asm | programa | clasico | ENTRADA | 23 | se acabó la entrada: el programa pidió un carácter (GETC/IN) y no hay más (use --entrada)  [PC=x30E6] |
| g1_cordic_division.asm | modulo | clasico | OK | 142 | entrada=CORDIC_DIV |
| g20_Cordic_reduccion_de_argumento.asm | modulo | clasico | OK | 19 | entrada=Reduccion_Argumento |
| g21_senotaylor_subrutina.asm | programa | clasico | ENTRADA | 3 | se acabó la entrada: el programa pidió un carácter (GETC/IN) y no hay más (use --entrada)  [PC=x3003] |
| g22_Tabla_SIN_y_COS.asm | modulo | clasico | OK | 339 | entrada=SENO_TABLA |
| g23_modulo_sqrt_nr.asm | modulo | clasico | OK | 300 | entrada=SQRT_NR |
| g24_conversor_lc3_max.asm | modulo | clasico | OK | 174 | entrada=SUB_BASE_HEX |
| g27_circlsh.asm | modulo | clasico | OK | 13 | entrada=CIRCLSH |
| g27_from_qm_n.asm | modulo | clasico | OK | 372 | entrada=FROM_QM_N |
| g27_fromdec.asm | modulo | clasico | OK | 36 | entrada=FROMDEC |
| g27_fromhex.asm | modulo | clasico | FALLA | 24 | R0=x0000(0) esperado x001A(26) |
| g27_getcfiltered.asm | modulo | clasico | ENTRADA | 10 | se acabó la entrada: el programa pidió un carácter (GETC/IN) y no hay más (use --entrada)  [PC=x3006] |
| g27_getline.asm | modulo | clasico | ENTRADA | 12 | se acabó la entrada: el programa pidió un carácter (GETC/IN) y no hay más (use --entrada)  [PC=x3008] |
| g27_getval.asm | modulo | clasico | ENTRADA | 22 | se acabó la entrada: el programa pidió un carácter (GETC/IN) y no hay más (use --entrada)  [PC=x3074] |
| g27_getval_buffer.asm | - | clasico | OMITIDO | 0 | omitido por casos.json |
| g27_main_menu_PROGRESO.asm | programa | clasico | EXCEPCION | 38 | RET con R7=0: nadie llamó a esta rutina (¿es un módulo y no un programa? necesita un principal que haga JSR/JSRR, o use  |
| g27_outval.asm | modulo | clasico | OK | 177 | entrada=OUTVAL |
| g27_pause.asm | modulo | clasico | ENTRADA | 8 | se acabó la entrada: el programa pidió un carácter (GETC/IN) y no hay más (use --entrada)  [PC=x3004] |
| g27_sumover.asm | modulo | clasico | OK | 31 | entrada=SUMOVER |
| g27_to_qm_n.asm | modulo | clasico | OK | 26 | entrada=TO_QM_N |
| g27_todec.asm | modulo | clasico | OK | 2268 | entrada=TODEC |
| g30_seno_cheb_pade.asm | modulo | clasico | OK | 468 | entrada=SEN_CHEB_PADE |
| g3_MultiplicacionSHIFTandADD.asm | modulo | clasico | OK | 268 | entrada=MULTIPLICARSHIFTANDADD |
| g4_potencia.asm | modulo | clasico | OK | 310 | entrada=EXP_RAPIDA |
| g5_Mul_Sucesiva_POW.asm | modulo | clasico | OK | 220 | entrada=Mul_Sucesiva_POW |
| g6_EXP.asm | modulo | clasico | OK | 4894 | entrada=EXP_Q3_12 |
| g7_mcd.asm | modulo | clasico | OK | 29 | entrada=MCD |
| g7_mcm.asm | modulo | clasico | OK | 50 | entrada=MCM |
| g9_sq9_math_helpers.asm | modulo | clasico | OK | 12 | entrada=SQ9_ROTL32 |
| g9_sqrt_nr_dq16.asm | modulo | clasico | OK | 3767 | entrada=SQRT_NR_DQ16 |
| g9_sqrt_nr_q8.asm | modulo | clasico | OK | 24 | entrada=SQRT_NR_Q8 |

## Detalle de los que no corrieron

### g19_cordic_multiplicacion.asm (ENTRADA)

se acabó la entrada: el programa pidió un carácter (GETC/IN) y no hay más (use --entrada)  [PC=x30E6]

### g21_senotaylor_subrutina.asm (ENTRADA)

se acabó la entrada: el programa pidió un carácter (GETC/IN) y no hay más (use --entrada)  [PC=x3003]

### g27_fromhex.asm (FALLA)

R0=x0000(0) esperado x001A(26)

### g27_getcfiltered.asm (ENTRADA)

se acabó la entrada: el programa pidió un carácter (GETC/IN) y no hay más (use --entrada)  [PC=x3006]

### g27_getline.asm (ENTRADA)

se acabó la entrada: el programa pidió un carácter (GETC/IN) y no hay más (use --entrada)  [PC=x3008]

### g27_getval.asm (ENTRADA)

se acabó la entrada: el programa pidió un carácter (GETC/IN) y no hay más (use --entrada)  [PC=x3074]

### g27_main_menu_PROGRESO.asm (EXCEPCION)

RET con R7=0: nadie llamó a esta rutina (¿es un módulo y no un programa? necesita un principal que haga JSR/JSRR, o use benchmark.py)  [PC=x3022]

### g27_pause.asm (ENTRADA)

se acabó la entrada: el programa pidió un carácter (GETC/IN) y no hay más (use --entrada)  [PC=x3004]

