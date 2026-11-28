Benchmark de la calculadora adaptado a la ISA del Grupo 7 (direccionamiento por byte + MUL/MULH/DIV/REM/SHL/SHR/SAR) - VERSION 2
Resultado: 47.306 instrucciones de usuario (+ 22.074 del SO = 69.380 con SO), 14.006 bytes cargados, salida identica al original.
(LC-3 original: 357.505 instr de usuario + 22.074 del SO = 379.579 con SO; 15.792 B).

Reglas aplicadas (confirmadas por la catedra): solo se optimizaron sumas, multiplicaciones y desplazamientos,
sin cambiar los algoritmos principales; los textos se almacenan a 1 byte por caracter.

Modulos reescritos con las instrucciones nuevas (misma interfaz y mismos registros):
  lib/g21_senotaylor_subrutina.asm  conversion de angulo y potencias con MUL/MULH/DIV/REM (3606 angulos verificados)
  lib/g27_todec.asm                 digitos por DIV/REM en vez de restas sucesivas y sumas de potencias (+290.000 casos verificados)
  lib/g27_circlsh.asm               giro de 32 bits con SHL/SHR de una sola vez, en vez de un bucle de a 1 bit.
                                    Igual al original para cualquier n (n <= 0 no hace nada; n > 31 gira n mod 32).
                                    Guarda R2, R3 y R4 en la pila (R6 vuelve al mismo valor). 78.606 casos, 0 diferencias.
  lib/g27_from_qm_n.asm             conversion Qm.n -> Q15.16 con SAR/SHL directos (ya no llama a circlsh ni toca R7):
                                    entero = Qm.n >> n (con signo); fraccion = Qm.n << (16-n).
                                    Igual al original para todo n >= 0: 1.376.256 casos (todos los Qm.n x n=0..20)
                                    + 16.676 casos con n = 21..32767, 0 diferencias. (n negativo no es valido.)
  lib/g27_to_qm_n.asm               SIN CAMBIOS; usa el nuevo circlsh (648.960 casos comparados, 0 diferencias).
Unificado: lib/g7_mcd_mcm.asm (MCD y MCM en un solo modulo).
g27_sumover.asm y g27_fromdec.asm quedan igual (el benchmark automatico no los llama).
El resto de los modulos solo se adapto a direccionamiento por bytes (sin cambiar su algoritmo).

Verificacion de punta a punta: 260 sesiones del menu interactivo (opciones 0..c, valores positivos, negativos, chicos y
grandes) comparadas contra la version anterior: 0 diferencias en la salida. Salida del modo automatico: identica byte a byte.

Medicion (modo automatico, simulador ISA-LC3 Studio con conteo del SO):
                         G7 (V2)   Original LC-3
  instr. de usuario      47.306    357.505
  instr. del SO          22.074     22.074
  instr. con SO          69.380    379.579
  bytes cargados         14.006     15.792
