# LC10: ISA del Grupo 10 (Laboratorio 3c)

Versión 2. Es una ISA nueva, sin compatibilidad hacia atrás con la LC-3, que cumple la funcionalidad obligatoria del enunciado y usa los 32 opcodes. La versión 2 agrega el opcode 31, que estaba libre en la versión 0: `PUSH`/`POP` de varios registros a la vez y `DIVREMU`/`DIVREM` (cociente y resto en una instrucción); ver la sección 3 y la decisión 4. La fuente única de verdad es `lc10/isa.py`: el ensamblador, el desensamblador y el simulador leen esa misma tabla.

## 1. Estado de la máquina

| Elemento | Definición |
| --- | --- |
| Registros | R0 a R7, de 16 bits. R7 es el registro de enlace (lo escribe `JSR`/`JSRR`). Ningún otro registro tiene función fija. |
| PC | 16 bits, avanza de a 2. Siempre es par: un salto a dirección impar es una excepción. |
| Memoria | 64 KiB (2^16 direcciones), direccionable por byte, little-endian (el byte de la dirección par es el menos significativo de la palabra). |
| Banderas | N, Z, P (signo del resultado) y C (acarreo), V (desborde con signo). |
| Instrucción | 16 bits, opcode fijo de 5 bits en [15:11]. Siempre empieza en dirección par. |
| Datos | Enteros con signo de 16 bits (registro completo) y de 8 bits (`LDL` extiende el signo, `STL` guarda el byte bajo). |

Las instrucciones aritméticas operan sobre 16 bits. Las cargas de byte (`LDL`/`LDH`) y las escrituras de byte (`STL`/`STH`) mueven un byte entre memoria y una mitad del registro.

## 2. Formatos de instrucción

Todos usan `opcode[15:11]`. Los campos de registro son de 3 bits.

| Formato | Instrucciones | [10:8] | [7:5] | [4:0] |
| --- | --- | --- | --- | --- |
| ALU | ADD SUB AND OR XOR ADC SBC | DR | SR1 | `0 0 SR2` (registro) o `1 imm4` (inmediato, −8 a 7) |
| CMP | CMP | 000 | SR1 | igual que ALU |
| UN | NOT NEG | DR | SR | 00000 |
| SH | SHL SHR SAR | DR | SR1 | `0 imm4` (cantidad 0 a 15) o `1 0 SR2` (cantidad = R[SR2] & 31) |
| ROTC | ROTC | DR | SR | `dir 0000` (dir = 0 izquierda, 1 derecha) |
| MD | MUL MULH MULHU (op 29), DIV DIVU REM REMU (op 30) | DR | SR1 | `fn SR2`: fn (2 bits) en [4:3] elige la variante (ver sección 3) y SR2 en [2:0] |
| X | PUSH POP DIVREMU DIVREM (op 31) | `fn` en [10:9] | | `PUSH`/`POP`: [8] = 0 y máscara de registros en [7:0] (bit r = Rr). `DIVREMU`/`DIVREM`: DR en [8:6], SR1 en [5:3], SR2 en [2:0] |
| MEMW | LDW STW | reg | BaseR | offset5 con signo, en palabras (el assembly lo escribe en bytes, par) |
| MEMB | LDL LDH STL STH | reg | BaseR | offset5 con signo, en bytes |
| PCREL | LD ST | reg | offset8 con signo, en palabras (bits [7:0]) |
| PCREL | LEA | reg | offset8 con signo, **en bytes** (bits [7:0]) |
| MOVI | MOVI | DR | imm8 con signo (bits [7:0]) |
| BR | BR | `n z p` | offset8 con signo, en palabras (bits [7:0]) |
| BRX | BRX | cond | offset8 con signo, en palabras (bits [7:0]) |
| JSR | JSR | offset11 con signo, en palabras (bits [10:0]) |
| JR | JR | `link 0 0` | BaseR | 00000 |
| TRAP | TRAP | 000 | trapvect8 (bits [7:0]) |

Destinos relativos: `destino = (dirección de la instrucción + 2) + 2 × offset` (en `LEA`, `+ offset` en bytes). Alcances: BR/BRX/LD/ST ±256 bytes, JSR ±2 KiB, LEA ±128 bytes. Para llegar más lejos se carga la dirección con `LD` desde un `.FILL` y se salta con `JSRR`/`JMP`.

## 3. Conjunto de instrucciones

Opcodes (en decimal) y efecto. "Banderas" indica lo que modifica; lo que no se nombra no cambia.

| Op | Instrucción | Efecto | Banderas |
| --- | --- | --- | --- |
| 0 | `BR[n][z][p] dest` | salta si se cumple alguna de las banderas pedidas; `BR` sin letras salta siempre; la palabra `0x0000` es un NOP | ninguna |
| 1 | `BRC` `BRNC` `BRV` `BRNV` `BRLT` `BRGE` `BRGT` `BRLE` `dest` | salto condicional (ver sección 4) | ninguna |
| 2 | `ADD DR, SR1, SR2\|#imm4` | DR = SR1 + op2 | N Z P C V |
| 3 | `SUB DR, SR1, SR2\|#imm4` | DR = SR1 − op2 | N Z P C V |
| 4 | `AND` | DR = SR1 & op2 | N Z P |
| 5 | `OR` | DR = SR1 \| op2 | N Z P |
| 6 | `XOR` | DR = SR1 ^ op2 | N Z P |
| 7 | `NOT DR, SR` | DR = ~SR | N Z P |
| 8 | `NEG DR, SR` | DR = −SR | N Z P C V |
| 9 | `ADC DR, SR1, SR2\|#imm4` | DR = SR1 + op2 + C | N Z P C V |
| 10 | `SBC DR, SR1, SR2\|#imm4` | DR = SR1 − op2 − (1 − C) | N Z P C V |
| 11 | `CMP SR1, SR2\|#imm4` | como SUB pero no guarda el resultado | N Z P C V |
| 12 | `SHL DR, SR1, #n\|Rn` | desplazamiento lógico a la izquierda; C = último bit que sale | N Z P C |
| 13 | `SHR DR, SR1, #n\|Rn` | desplazamiento lógico a la derecha; C = último bit que sale | N Z P C |
| 14 | `SAR DR, SR1, #n\|Rn` | desplazamiento aritmético a la derecha (conserva el signo) | N Z P C |
| 15 | `RCL DR, SR` / `RCR DR, SR` | rota 1 bit a través del acarreo (nuevo C = bit que sale) | N Z P C |
| 16 | `LDW DR, BaseR[, #off]` | DR = palabra en BaseR + off (off par, en bytes) | N Z P |
| 17 | `LDL DR, BaseR[, #off]` | DR = byte en BaseR + off, con extensión de signo | N Z P |
| 18 | `LDH DR, BaseR[, #off]` | DR[15:8] = byte; DR[7:0] no cambia | N Z P |
| 19 | `STW SR, BaseR[, #off]` | palabra en BaseR + off = SR | ninguna |
| 20 | `STL SR, BaseR[, #off]` | byte en BaseR + off = SR[7:0] | ninguna |
| 21 | `STH SR, BaseR[, #off]` | byte en BaseR + off = SR[15:8] | ninguna |
| 22 | `LD DR, etiqueta` | DR = palabra en PC+2 + 2·off | N Z P |
| 23 | `ST SR, etiqueta` | palabra en PC+2 + 2·off = SR | ninguna |
| 24 | `LEA DR, etiqueta` | DR = PC+2 + off (off en bytes) | ninguna |
| 25 | `MOVI DR, #imm8` | DR = imm8 con extensión de signo | N Z P |
| 26 | `JSR etiqueta` | R7 = PC+2; salta | ninguna |
| 27 | `JSRR Rn` / `JMP Rn` / `RET` | salta a Rn; `JSRR` guarda antes PC+2 en R7; `RET` es `JMP R7` | ninguna |
| 28 | `TRAP #vect` | llamada al sistema (sección 5) | depende |
| 29 | `MUL DR, SR1, SR2` (fn 0) | DR = parte baja (16 bits) del producto SR1 × SR2; es la misma con y sin signo | N Z P, V = 1 si el producto con signo no entra en 16 bits |
| 29 | `MULH DR, SR1, SR2` (fn 1) | DR = parte alta (bits 31..16) del producto con signo | N Z P |
| 29 | `MULHU DR, SR1, SR2` (fn 2) | DR = parte alta del producto sin signo | N Z P |
| 29 | (fn 3) | variante reservada: ejecutarla es una excepción | |
| 30 | `DIV DR, SR1, SR2` (fn 0) | DR = SR1 / SR2 con signo, truncado hacia cero | N Z P V |
| 30 | `DIVU DR, SR1, SR2` (fn 1) | DR = SR1 / SR2 sin signo | N Z P V |
| 30 | `REM DR, SR1, SR2` (fn 2) | DR = resto con signo, con el signo del dividendo: SR1 = (SR1 DIV SR2) × SR2 + REM | N Z P V |
| 30 | `REMU DR, SR1, SR2` (fn 3) | DR = resto sin signo | N Z P V |
| 31 | `PUSH lista` (fn 0) | guarda en la pila los registros de la lista: por cada uno, de R7 a R0, R6 −= 2 y palabra en R6 = Rr | ninguna |
| 31 | `POP lista` (fn 1) | los vuelve a cargar: por cada uno, de R0 a R7, Rr = palabra en R6 y R6 += 2 | ninguna |
| 31 | `DIVREMU DR, SR1, SR2` (fn 2) | DR = SR1 / SR2 y SR1 = SR1 % SR2, sin signo | N Z P según el cociente, V |
| 31 | `DIVREM DR, SR1, SR2` (fn 3) | lo mismo con signo (cociente truncado hacia cero, resto con el signo del dividendo) | N Z P según el cociente, V |

Multiplicación y división (opcodes 29 y 30). Son enteros de 16 bits: no hay punto flotante en ninguna parte. La ISA no conoce los formatos Q; la posición de la coma la fija el programa con desplazamientos, como en los módulos originales. Por ejemplo, Q7.8 × Q7.8 → Q7.8 truncado es `MUL` + `MULH`, `SHR` por 8, `SHL` por 8 y `OR` (5 instrucciones), y el producto completo de 32 bits sale de `MUL` (parte baja) más `MULH` o `MULHU` (parte alta). La interfaz de cada subrutina (qué formato recibe y devuelve) no cambia: solo cambia cómo se resuelve por dentro. Casos especiales, sin excepciones:

* División por cero: el cociente da 0xFFFF (todos unos), el resto es el dividendo y V = 1.
* −32768 / −1 con signo: el cociente da 0x8000, el resto 0 y V = 1.
* `MULH`, `MULHU` y todas las divisiones dejan C sin cambios; las divisiones ponen V = 0 en el caso normal.
* Cada una cuenta como una instrucción ejecutada.

Opcode 31 (versión 2). Sale del perfil del benchmark: lo más repetido eran las rachas de `ST` y `LD` con que cada subrutina guarda y restaura registros, y los pares `DIVU` + `REMU` de `TODEC` (decisión 4).

* **Lista de registros.** En el assembly se escribe con comas y rangos: `PUSH R1-R5, R7`, `POP R0, R2`. No puede estar vacía ni incluir R6, que es el puntero de pila; un registro repetido es un error. Cada `PUSH` o `POP` cuenta como una instrucción, sea cual sea la cantidad de registros (igual que `MUL` o `DIV`).
* **La pila.** Crece hacia direcciones menores y R6 apunta a la última palabra guardada. El registro más bajo de la lista queda en la dirección más baja (R6+0), así que un `POP` con la misma lista deshace un `PUSH` y deja R6 como estaba. Es el mismo marco que ya armaban a mano los módulos que usaban R6 (`ADD R6, R6, #-n` y `STW`). R6 arranca en 0, como en el simulador de la cátedra: el primer `PUSH` escribe en xFFFE. Con R6 impar, `PUSH` y `POP` son una excepción (acceso a palabra en dirección impar).
* **`DIVREMU` y `DIVREM`.** Dan exactamente lo mismo que `DIVU DR, SR1, SR2` seguida de `REMU SR1, SR1, SR2` (o `DIV` + `REM`), incluidos la división por cero y −32768 / −1. DR y SR1 tienen que ser distintos (uno recibe el cociente y el otro el resto); SR2 puede ser cualquiera.
* **Combinaciones reservadas** (son una excepción, como un opcode reservado): `PUSH`/`POP` con la máscara en 0, con R6 en la máscara o con el bit 8 en 1, y `DIVREMU`/`DIVREM` con DR = SR1.

Notas:

* La resta es `a + ~b + 1`, así que **C = 1 significa que no hubo préstamo** (a ≥ b sin signo). `SBC` usa ese mismo C. `ADC`/`SBC` permiten sumas y restas de 32 bits o más con dos o más instrucciones.
* Las operaciones lógicas, los desplazamientos de cantidad 0, `MOV`, `MOVI`, las cargas y los saltos no tocan C ni V (salvo los desplazamientos con cantidad mayor que 0, que fijan C). Esto permite llevar el acarreo a través de otras instrucciones.
* En desplazamientos por registro la cantidad es `R[SR2] & 31`. Con 16 o más, `SHL`/`SHR` dan 0 y `SAR` rellena con el signo.
* `NEG`: C = 1 solo si el operando es 0; V = 1 solo para x8000.
* `LDW`/`STW` en dirección impar es una excepción. `LDL`/`LDH`/`STL`/`STH` aceptan cualquier dirección.
* `PUSH`, `POP` y `DIVREM*` no tocan C. `PUSH` y `POP` no tocan ninguna bandera.
* Pseudo-instrucciones del ensamblador: `NOP` (`0x0000`), `MOV DR, SR` (= `OR DR, SR, SR`), `CLR DR` (= `MOVI DR, #0`), `TST SR` (= `OR SR, SR, SR`, solo fija N Z P), `RET`, `JMP`, `JSRR`, `RCL`, `RCR` y los alias de TRAP.

## 4. Condiciones

`BR` mira N, Z, P (como la LC-3). `BRX` elige una condición con el campo [10:8]:

| Código | Mnemónico | Se cumple si | Uso típico |
| --- | --- | --- | --- |
| 0 | `BRC` (`BRHS`) | C = 1 | sin signo, mayor o igual (tras `CMP`); acarreo |
| 1 | `BRNC` (`BRLO`) | C = 0 | sin signo, menor |
| 2 | `BRV` | V = 1 | desborde con signo |
| 3 | `BRNV` | V = 0 | |
| 4 | `BRLT` | N ≠ V | con signo, menor (correcto aun con desborde) |
| 5 | `BRGE` | N = V | con signo, mayor o igual |
| 6 | `BRGT` | Z = 0 y N = V | con signo, mayor |
| 7 | `BRLE` | Z = 1 o N ≠ V | con signo, menor o igual |

## 5. TRAP y sistema operativo

`TRAP vv` hace **R7 = PC** (la dirección de la instrucción que sigue) y **PC = la palabra de la tabla de vectores en xFB00 + 2·vv**; la rutina termina con `RET`. Un vector sin rutina (palabra en 0) es una excepción: "TRAP xvv no implementado". Las rutinas son un sistema operativo mínimo escrito en LC10, `lc10/os_lc10.asm`, que el simulador instala al crear la máquina (como la ROM de la LC-3) y ejecuta **como cualquier otro código**: sus instrucciones se cuentan, aparte de las del usuario. Las cadenas son de bytes, terminadas en 0.

**Mapa de la zona del sistema** (todo lo demás es del usuario: los programas empiezan en x3000 y la pila de R6 baja desde xFFFE, de modo que no llega hasta acá salvo con una recursión de más de 400 bytes)

| Direcciones | Qué hay |
| --- | --- |
| xFB00–xFCFF | tabla de vectores TRAP: 256 palabras, una por vector (0 = sin rutina) |
| xFD40–xFDFF | rutinas del SO y sus palabras de datos (`SAVE0`..`SAVE2`) |
| xFE00 / xFE02 | `KBSR` (bit 15 = hay una tecla) / `KBDR` (el carácter; xFFFF si no quedan) |
| xFE04 / xFE06 | `DSR` (bit 15 = pantalla lista; siempre lo está) / `DDR` (se escribe el byte bajo) |
| xFE08 | `MCR`: escribir con el bit 15 en 0 detiene la máquina |

Los dispositivos son registros mapeados en memoria, como en la LC-3, y se leen y escriben con `LD`/`ST` relativos al PC (por eso el SO está pegado a ellos: el alcance es de ±256 bytes). Un programa también puede escribir `DDR` o `MCR` directamente.

| Vector | Alias | Efecto | Instrucciones del SO |
| --- | --- | --- | --- |
| x20 | `GETC` | R0 = siguiente carácter de la entrada (xFFFF si no quedan; ver la nota de abajo) | 4 |
| x21 | `OUT` | escribe el carácter R0[7:0] | 6 |
| x22 | `PUTS` | escribe la cadena de bytes que empieza en la dirección R0 | 9 + 6 por carácter |
| x23 | `IN` | como `GETC` y además lo muestra (sin eco si no quedan) | 10 (5 sin entrada) |
| x25 | `HALT` | termina la ejecución (`MOVI R7, #0` y `ST R7, MCR`) | 2 |

Convenciones (las de la LC-3): R7 queda con la dirección de retorno (el usuario lo guarda si lo necesita); las rutinas conservan R0 a R6 (salvo R0 como resultado en `GETC` e `IN`) y no usan la pila del usuario: guardan lo que necesitan en sus propias palabras. Las banderas N, Z, P quedan como las dejó la última instrucción de la rutina; tras `HALT`, R7 vale 0.

**Cuenta.** El simulador cuenta una instrucción por cada una que ejecuta, la del usuario (el `TRAP` es una) o la del SO (el PC está en la zona del sistema), y muestra `usuario + SO = total`, igual que el contador que actualizó el grupo 8 para la LC-3 (`357.505 usuario + 22.074 SO = 379.579`). Las métricas de memoria (bytes leídos, escritos, instrucciones leídas, extremos) son solo las del usuario: la zona del sistema se deja afuera, como la ROM. Un paso de la ventana (F10) sobre un `TRAP` ejecuta la rutina entera.

Fin de la entrada: el simulador de línea de comandos (y `benchmark.py`), como el simulador de la cátedra, detiene la ejecución con el aviso "no hay más caracteres disponibles en la entrada": el `GETC`/`IN` queda esperando en la lectura de `KBSR` (esa lectura no se cuenta como ejecutada) y se puede seguir dándole teclas. Con `--fin-entrada menos1` el teclado lee xFFFF (-1) y sigue; es lo que hace también la ventana cuando se vacía el cuadro de entrada.

## 6. Ensamblador

Comando: `python -m lc10.assembler principal.asm modulo1.asm ... -o salida.hex [--format bin|hex|dec|bits] [--listing] [--map]`.

* Sintaxis: una instrucción por línea; la etiqueta va al principio (con o sin `:`); `;` inicia un comentario; los operandos se separan con coma o espacio; los números son `#-5`, `12`, `x1F`, `0x1F` o `0b101`. No sirven como etiqueta los nombres de instrucciones ni de TRAP (`OUT`, `IN`, ...).
* Directivas: `.ORIG` (solo el programa principal), `.END`, `.FILL` (palabra o dirección), `.BLKW n`, `.BYTE v, ...`, `.BLKB n`, `.STRINGZ "..."` (bytes), `.ALIGN`, `.EXTERNAL MODULO-ETIQUETA`.
* Módulos y `.EXTERNAL`: el primer archivo es el programa principal; los demás son módulos sin `.ORIG`, con `.END`, ubicados uno detrás de otro. El nombre del módulo es el del archivo en mayúsculas. Los símbolos de otro módulo se declaran con `.EXTERNAL MODULO-ETIQUETA` y se usan con ese mismo nombre (`JSR DIVISION-DIV_LONG`, `.FILL DIVISION-DIV_LONG`). Es el mismo esquema que usa el simulador del curso.
* Alineación: las instrucciones y las palabras empiezan siempre en dirección par. Si un `.BYTE`, `.STRINGZ` o `.BLKB` deja el contador impar, el ensamblador inserta un byte de relleno (0x00) antes de la siguiente instrucción o palabra, y la etiqueta apunta a la instrucción y no al relleno. El simulador, además, corta con una excepción si se salta a una dirección impar.
* Salida: los dos primeros bytes (o la primera palabra, en los formatos de texto) son la dirección de origen. Formatos: `.bin` (binario), `.hex`, `.dec` y `.bits` (texto).

## 7. Simulador funcional

Comando: `python -m lc10.simulator programa.hex [--input TEXTO | --input-file ARCHIVO] [--fin-entrada detener|menos1] [--max N] [--dump DIR:BYTES] [--trace]`. Recibe un archivo ya ensamblado (nunca assembly), lo ejecuta desde la dirección de origen y devuelve:

* los resultados: salida por consola, registros, banderas, y los volcados de memoria pedidos con `--dump`;
* la cantidad de instrucciones ejecutadas, las del usuario más las del SO (las rutinas de los TRAP, sección 5), y cuántas veces se ejecutó cada una;
* un resumen con el formato de la barra del simulador de la cátedra con el contador actualizado: `LC10 · 15.822 usuario + 10.901 SO = 26.723 instrucciones · 4963 palabras · x3000–x56C5` (palabras = bytes de la imagen / 2, con el relleno; el rango va del primer al último byte de la imagen; el SO no cuenta como palabras del programa). La ventana muestra lo mismo en su barra de estado;
* el uso de memoria: bytes y palabras de la imagen cargada y su rango; bytes distintos usados (leídos como instrucción, leídos como dato o escritos), cuántos dentro de la imagen y cuántos fuera, con los rangos de afuera (por ejemplo la pila); y el detalle de instrucciones leídas, datos leídos y datos escritos.

Las excepciones (PC impar, palabra en dirección impar, combinación reservada del opcode 29 o 31, fin de la entrada) terminan la ejecución con un mensaje y código de salida 2; llegar al límite de `--max` termina con código 3.

**Ventana gráfica (no forma parte de la ISA).** `python lc10_gui.pyw` abre un editor con ensamblador y simulador integrados (ver `README.md`). Llama a las mismas funciones que los comandos de arriba; para conservar el esquema del enunciado, puede exportar la imagen ensamblada (`.hex`, `.bin`, `.dec`, `.bits`) y simular una imagen ya ensamblada sin pasar por el fuente. Estructura de código: `isa.py` (definición), `image.py` (formatos de archivo), `assembler.py`, `simulator.py` (núcleo), `system.py` y `os_lc10.asm` (el SO: rutinas de los TRAP y tabla de vectores). El ensamblador no depende del simulador.

## 8. Cumplimiento del enunciado del Lab 3c

| Requisito | Cómo se cumple | Pruebas |
| --- | --- | --- |
| Carga/guardado por byte: parte baja, alta y palabra | `LDL`, `LDH`, `LDW`, `STL`, `STH`, `STW` | `test_byte_and_word_access_little_endian` |
| Enteros con signo de 8 y 16 bits | `LDL` extiende el signo; registros y aritmética de 16 bits | `test_ldl_sign_extends_and_sets_flags`, `test_int8_array_sum_uses_signed_bytes` |
| Instrucciones de 16 bits con opcode fijo de 5 bits | campo [15:11] en todos los formatos | `test_encode_decode_roundtrip` |
| Registros de 16 bits | R0 a R7 | todas |
| 2^16 direcciones | memoria de 64 KiB con dirección que da la vuelta | `test_address_wraps_at_64k` |
| Salto condicional con N, Z, P y adicionales | `BR` (N Z P) y `BRX` (C, V, comparaciones con signo) | `test_nzp_branch_taken_matches_flags`, `test_signed_and_unsigned_conditions_after_cmp` |
| Salto a subrutina con guardado de PC+2 | `JSR`, `JSRR` guardan PC+2 en R7 | `test_jsr_saves_pc_plus_2_and_ret_returns` |
| Salto incondicional sin guardar, que sirva para volver | `JMP Rn`, `RET` (`JMP R7`) | `test_jsrr_and_jmp` |
| TRAP | `TRAP` con GETC, OUT, PUTS, IN, HALT: tabla de vectores, rutinas del SO, costo y dispositivos | `test_traps`, `tests/test_os.py` |
| Simulador: archivo de entrada binario, hex o decimal | `.bin`, `.hex`, `.dec` y `.bits` | `test_run_from_file_formats` |
| Simulador: resultados, instrucciones ejecutadas y uso de memoria | `Result` y salida de la línea de comandos | `test_loop_counts_instructions_and_stats` |
| PC de a 2; excepción por salto impar | `step()`, `jump()` | `test_odd_jump_target_is_a_fault` |
| Ensamblador separado, salida binaria o hexadecimal con origen en los 2 primeros bytes | `assembler.py`, `image.py` | `TestImageFormats` |
| `.EXTERNAL` y operaciones básicas de la LC-3 | módulos enlazados por nombre; `.ORIG`, `.END`, `.FILL`, `.BLKW`, `.STRINGZ` | `test_external_linking_between_modules` |
| Instrucciones en dirección par, con relleno | relleno automático de un byte 0x00 antes de instrucciones y palabras en dirección impar | `test_alignment_padding_and_label_binding` |

## 9. Resultados: división larga Q7.8 en LC-3 y en LC10

Rutina `DIV_LONG` (a y b en Q7.8, resultado en Q7.8, con `ESTADO` y registros R1 a R5 preservados en memoria, igual que en la plantilla de subrutinas). Mismos 20.361 casos para las dos (bordes y aleatorios), con el resultado y `ESTADO` verificados contra la división exacta en cada caso.

| | LC-3 (`grupo10/division.asm`) | LC10 (`asm/division.asm`) |
| --- | --- | --- |
| Instrucciones por llamada: mínimo, promedio, máximo | 27, 227,9, 327 | 19, 122,7, 175 |
| Tamaño del módulo | 212 bytes (106 palabras, con `DIVIDIR` general incluida) | 120 bytes (60 palabras, solo `DIV_LONG`) |

Con casos típicos (|a| entre 256 y 20000 y |b| entre 128 y 20000) el promedio es 281,0 en LC-3 y 151,5 en LC10. La reducción promedio es del 46 % en instrucciones.

De dónde sale el ahorro: el dividendo se alinea con `SHR`/`SHL` por 8 (2 instrucciones, en vez de un lazo de 8 vueltas), el desplazamiento de 32 bits es `SHL` + `RCL` (en vez de 5 a 6 instrucciones por vuelta), la comparación usa el acarreo (`CMP` + `BRC`/`BRNC`), el signo del cociente sale de un `XOR`, y el valor absoluto es `NEG`. Aclaración sobre la memoria: la versión LC-3 también contiene `DIVIDIR` general, que aquí no existe; la comparación de instrucciones sí es entre las mismas llamadas.

Control de las cifras de LC-3: se corrieron 3361 casos de `DIV_LONG` también con el simulador de la cátedra (`simulador.py`) y el emulador propio de `bench/lc3sim.py`: mismo resultado y misma cantidad de instrucciones en los 3361. Las cifras de LC10 salen del simulador de este repositorio (el de la cátedra no ejecuta LC10).

Las instrucciones nuevas con las que se obtiene esto: `SUB`, `XOR`, `NEG`, `SHL`/`SHR`/`SAR`, `RCL`/`RCR`, `CMP`, `BRX` (C/V), `MOVI`. Es una primera versión sin optimizar a fondo.

## 10. Decisiones abiertas

1. **Multiplicación y división por hardware.** Resuelta: Carballo las permite siempre que el resultado sea idéntico al de la subrutina original (hay que modelar sus cuentas; si no se logra, se documenta la prueba) y que la interfaz de cada módulo respete su formato (si recibe Q7.8 y espera Q7.8, por dentro se resuelve como se quiera). Quedaron como `MUL`/`MULH`/`MULHU` (opcode 29) y `DIV`/`DIVU`/`REM`/`REMU` (opcode 30), enteras de 16 bits. Medido en el benchmark completo (sección 12): una multiplicación con escala Q es `MUL` + `MULHU` + `SHR` + `SHL` + `OR` (5 instrucciones) y no hizo falta una versión que ya escale.
2. **Convención de llamada.** La plantilla de subrutinas obliga a guardar y restaurar R1 a R5 en memoria. En la versión 0 eso costaba 10 instrucciones por llamada en la división (5 `ST` y 5 `LD`); con `PUSH`/`POP` (versión 2) son 2, y los registros siguen guardados en memoria, en la pila. Una convención distinta (registros "temporales" que la rutina puede usar) ahorraría también esas 2, pero cambia el contrato con el resto del benchmark.
3. **Enteros de 8 bits.** Hoy se cargan con extensión de signo y se operan en 16 bits. Si hace falta detectar desborde a 8 bits, habría que agregar una extensión de signo de byte o banderas de 8 bits.
4. **Opcode 31.** Resuelta en la versión 2. En la versión 0 quedó libre porque no se veía un candidato que pesara. Al medir el benchmark instrucción por instrucción (17.791 en la versión 0), lo más repetido eran los pares `LD, LD` (1.069) y `ST, ST` (795): las subrutinas guardando y restaurando registros uno por uno. Ahorro máximo medido para cada candidata:

   | Candidata | Patrón que reemplaza | Ahorro máximo |
   | --- | --- | ---: |
   | `PUSH`/`POP` con máscara | rachas de `ST`/`LD` al entrar y salir de las subrutinas | 1.864 |
   | `DIVREMU` (cociente y resto) | `DIVU` + `REMU` con los mismos operandos | 367 |
   | división por una constante | `MOVI Rx, #10` o `#100` antes de `DIVU` | 551, pero 100 no entra en el campo |
   | comparar y saltar | `CMP` + `BRxx` | 440, pero el desplazamiento quedaría muy corto |
   | decrementar y saltar | `ADD Rx, Rx, #-1` + `BRp` | unas 200 |

   Las dos primeras entran juntas en el opcode 31 con un campo fn de 2 bits. El ahorro real fue de 1.969 instrucciones (17.791 → 15.822) y 389 palabras (5.352 → 4.963); ver la sección 12. Algunas rachas no se pudieron cambiar porque el módulo vuelve a leer como dato un registro guardado (en `TODEC`, R3 se lee de la pila con `LDW R5, R6, #6`) o porque no eran guardados sino cargas de constantes (el menú).
5. **Alcances cortos.** `BR` y `LD`/`ST` llegan a ±256 bytes y `LEA` a ±128; si los módulos del benchmark crecen, quizás convenga ampliar offsets a costa de otros campos.

## 11. Línea base: el benchmark del curso en LC-3

Carpeta de la cátedra `lc3-project`: `main_grupo27.asm` (programa principal), `lib/` (37 módulos de todos los grupos), `assembler_LC3.py`, `simulador.py` y `programa.obj`. `python bench/lc3_baseline.py RUTA\lc3-project` la reproduce con el ensamblador y el simulador de la cátedra sin cambios: la imagen ensamblada es idéntica a `programa.obj`, y el programa automático `programa_del_menu_completo` (modo verboso, las 23 operaciones del menú) ejecuta **357.505 instrucciones** y ocupa **7896 palabras**, las cifras que informó Carballo. La salida impresa queda guardada en `bench/lc3_baseline_salida.txt`: es lo que el puerto a LC10 tiene que reproducir.

**El SO en la línea base.** El simulador de `lc3-project` resuelve cada TRAP en Python y lo cuenta como una instrucción. La cátedra pidió que los simuladores cuenten también las instrucciones que usa el SO para resolver los TRAP; el grupo 8 actualizó el contador del simulador de la LC-3 y dio este resultado: **357.505 usuario + 22.074 SO = 379.579 instrucciones**. Ese simulador no es el que tenemos, y no tenemos el código de su SO; lo que sí se puede medir (`python bench/lc3_baseline.py RUTA\lc3-project`) es qué TRAP pide el programa: 133 `PUTS` (1.541 caracteres), 76 `OUT` y 1 `HALT`, que son los que el SO tiene que resolver (unas 13,6 instrucciones de SO por carácter escrito, con el criterio del grupo 8).

**Cómo funciona.** El menú del grupo 27 es una máquina de estados con nodos (texto, filtro, siguientes, subrutina). Con un puntero a un vector de operaciones en R0 corre sin teclado: bandera de verbosidad, y por cada operación su índice, dos operandos y dos palabras de resultado. Cada operación llama a la subrutina de un grupo y `OUTVAL` imprime los valores con `TODEC`.

**Qué hay en las 7896 palabras:** 4017 instrucciones, 2247 de texto (una palabra por carácter; el menú solo tiene 2010), 1402 constantes y 230 de reserva (`.BLKW`). Las ocho piezas de lectura por teclado (`fromdec`, `fromhex`, `getval`, `getline`, `getcfiltered`, `getval_buffer`, `pause`, `to_qm_n`, 559 palabras) no se ejecutan en modo automático, pero hacen falta en el modo interactivo, así que forman parte de la funcionalidad que hay que conservar.

**Dónde se gastan las instrucciones:**

| Módulo | Instrucciones ejecutadas | % | Qué hace que sea caro |
| --- | --- | --- | --- |
| `g21_senotaylor` (seno de Taylor) | 221.428 | 61,9 | multiplica y divide con bucles de sumas y restas (un bucle por cada x², x³, x⁵, /4096, /6, /120, /42) |
| `g27_sumover` | 49.625 | 13,9 | suma de 16 bits con acarreo emulada; en LC10 es `ADC` |
| `g27_todec` | 44.757 | 12,5 | pasa a decimal con aritmética de 32 bits emulada y restas sucesivas |
| `g27_circlsh` | 6.390 | 1,8 | rotación de 32 bits emulada; en LC10 es `SHL` + `RCL` |
| los otros 26 módulos | 35.305 | 9,9 | |

Cuatro módulos concentran el 90 % de las instrucciones, y los cuatro compensan carencias de la LC-3 (multiplicar, dividir, acarreo, desplazar). El módulo de memoria que más pesa es el menú (2605 palabras, casi todo texto).

**Observaciones sobre los resultados de la LC-3** :

* `MULTIPLICACION (BASIC)` imprime −101,09185791 y el producto exacto de 13,828125 × −7,23828125 es −100,09185791: la parte entera está corrida en 1,0 (parece un error de préstamo con negativos en `g3`). Las versiones Booth y CORDIC dan −100,09375.
* `DIVISION (LONG DIVISION)` (nuestra) trunca (1,96484375) y `DIVISION (NEWTON-RAPHSON)` redondea (1,96875), con el mismo dato. Si una instrucción de división por hardware trunca, reproduce la primera y no la segunda.
* `TODEC` imprime 9 decimales calculados como suma de aproximaciones truncadas de 10⁹·2ᵏ/2¹⁶. Un cálculo exacto, `floor(f·10⁹/2¹⁶)`, da otro noveno decimal en 52.736 de las 65.536 fracciones (80 %). Reproducir el texto idéntico se puede con `1953125·(f>>7)` más una tabla de 7 constantes para los bits bajos (verificado con las 65.536 fracciones).
* `g21` trae un programa de prueba propio (64 palabras con lectura de teclado y `HALT`) pegado antes de la subrutina `CALCULAR_SENO`, y recibe el ángulo en décimas de grado.

**Qué cambia al portar a LC10** (además de usar las instrucciones nuevas):

* El texto pasa de una palabra a un byte por carácter, y `PUTS` lee bytes: 2247 palabras de texto se reducen a unas 1124. El código del menú que arma buffers de una palabra por carácter (por ejemplo `STR` de un carácter y un 0 para llamar a `FROMHEX`) hay que reescribirlo con `STL`/`LDL`.
* No hay `LDI`/`STI` (cada uno son dos instrucciones) y los saltos y cargas relativas llegan a ±256 bytes, contra ±256 palabras de la LC-3: los módulos grandes (menú, tablas) necesitan direcciones en `.FILL` + `JSRR`.
* Las convenciones de guardado de registros (`ST`/`LD` de R1 a R7 en cada subrutina) se pueden conservar o cambiar; eso cuesta o ahorra instrucciones por llamada (ver decisión 2).

**Criterio de Carballo para MUL/DIV.** Se pueden usar si el resultado es el mismo que el de la subrutina original, lo que obliga a modelar cómo computa (orden de las operaciones, dónde trunca, qué ancho tienen los intermedios). Si no se logra el resultado exacto, se documentan las pruebas y se aclara que no dio porque no se pudo reproducir cómo la subrutina llega a las cuentas. Cada sustitución se prueba contra el módulo real en el simulador de la cátedra:

| Módulo | Prueba | Resultado |
| --- | --- | --- |
| Seno de Taylor (`g21`) | `bench/equivalencia_seno.py`: los 3700 ángulos de 0 a 3699 (décimas de grado) y 4 fuera de rango, módulo real contra un modelo con enteros exactos (mismo orden de productos y truncados) | 0 diferencias en 3704 casos; R1 a R5 preservados. Instrucciones LC-3 por llamada: mín 22, prom 179.932, máx 641.686 |
| `TODEC` (`g27`) | `bench/equivalencia_todec.py`: 5011 casos (bordes como x8000 y aleatorios de entero, fracción y formato) contra un modelo de sus cuentas | 0 diferencias. La fórmula cerrada de la fracción coincide con el original en las 65.536 fracciones |

Conclusión provisoria: en estos dos módulos las cuentas se pueden reproducir exactamente con multiplicación y división de 16 bits, así que usar MUL/DIV cumple el criterio. En el seno hay que mantener los truncados intermedios (por ejemplo `floor(floor(p/4096)/42)`) y no reemplazarlos por una sola división. Los demás módulos se evalúan igual a medida que se portan.

## 12. Puerto del benchmark a LC10

El programa automático del menú del grupo 27 (las 23 operaciones, modo verboso) se porta completo a LC10 y tiene que imprimir exactamente lo que imprime en LC-3 (`bench/lc3_baseline_salida.txt`). Los 38 módulos del benchmark (el programa principal y los 37 de `lib/`) se portaron; los de lectura por teclado (`fromdec`, `fromhex`, `getval`, `getline`, `getcfiltered`, `getval_buffer`, `pause`, `to_qm_n`) también, porque el modo interactivo los necesita.

**Qué hay y cómo se reproduce**

| Carpeta o herramienta | Qué es |
| --- | --- |
| `tools/lc3_to_lc10.py` y `tools/port_hints.py` | traducen línea a línea el programa y los módulos de la cátedra (usa el enlazador de la cátedra solo para resolver `.EXTERNAL`; no lo modifica). El informe de lo que hubo que revisar queda en `asm/bench10/informe.txt` |
| `asm/bench10/` | **puerto directo**: lo que sale del traductor, sin editar a mano. Misma lógica, mismas subrutinas, mismo orden de cuentas |
| `asm/opt10/` | **puerto optimizado**: 12 módulos reescritos con las instrucciones de LC10 (misma interfaz y mismo resultado) y el pase `tools/peephole_lc10.py` sobre los demás |
| `tools/peephole_lc10.py` | cambia tres modismos por la instrucción equivalente: `AND Rx,Rx,#0` + `ADD` por `MOVI`, `NOT` + `ADD #1` por `NEG`, sumas de un registro consigo mismo por `SHL`. Deja el mismo valor y las mismas banderas N Z P |
| `bench/lc10_bench.py [carpeta] [--por-modulo]` | arma la carpeta, ejecuta el programa automático en el simulador LC10, compara la salida con la línea base y reparte las instrucciones por módulo |

**Resultados** (el mismo programa, la misma salida impresa en las cuatro filas). Instrucciones como las cuenta el simulador actualizado: usuario + SO.

| Versión | Usuario | SO | **Total** | Palabras | Salida idéntica a la de LC-3 |
| --- | ---: | ---: | ---: | ---: | --- |
| LC-3 (línea base de la cátedra; SO según el grupo 8) | 357.505 | 22.074 | **379.579** | 7.896 | (es la referencia) |
| LC10, puerto directo (`asm/bench10`) | 358.481 | 10.901 | **369.382** (−2,7 %) | 6.896 | sí |
| LC10 versión 0, optimizado, sin el opcode 31 | 17.791 | 10.901 | **28.692** (−92,4 %) | 5.352 | sí |
| LC10 versión 2, optimizado (`asm/opt10`) | 15.822 | 10.901 | **26.723** (−93,0 %) | **4.963** (−37,1 %) | sí |

Contando solo las instrucciones del usuario (lo que se informó antes de que la cátedra pidiera sumar el SO) la reducción de la versión 2 es de 95,6 % (versión 0: 95,0 %). Cómo se cuenta: las instrucciones son las que ejecuta el simulador de este repositorio, el programa y las rutinas de TRAP del SO (`MUL`, `DIV` y el propio `TRAP` cuentan una instrucción cada uno); las palabras son los bytes de la imagen ensamblada sobre 2, con el relleno de alineación incluido, sin el SO (como la ROM de la LC-3). El puerto directo ejecuta casi lo mismo que la LC-3 en el usuario (+976 instrucciones, sobre todo por las cadenas de `ADD` que reemplazan inmediatos de −16 a 15 y los saltos intermedios que exige el alcance corto) y ahorra memoria solo porque el texto pasa de una palabra a un byte por carácter.

**El costo del SO.** Las 10.901 instrucciones del SO de LC10 salen de 133 `PUTS` (9 + 6 por carácter: 133 · 9 + 1.541 · 6 = 10.443), 76 `OUT` (6 cada uno: 456) y el `HALT` (2). Son las mismas en todas las versiones porque imprimen el mismo texto con las mismas llamadas, y son el 41 % del total de la versión 2: al reducir tanto el código del usuario, imprimir pasa a ser lo que más cuesta. No tenemos el SO del grupo 8, así que la comparación entre los dos SO no es de uno a uno: el de LC10 es el que se escribió para esta ISA y se puede leer entero en `lc10/os_lc10.asm`. Como cota conservadora, si el SO de LC10 costara lo mismo que el de la LC-3 (22.074), la versión 2 daría 15.822 + 22.074 = 37.896 instrucciones, 90,0 % menos que 379.579.

**Módulo por módulo** (solo los que ejecutan instrucciones o cambian de tamaño; los dos puertos dan la misma salida). Las instrucciones son las del usuario; las del SO van aparte (`--por-modulo` las muestra en la fila "SO (rutinas de TRAP)")

| Módulo | Palabras LC-3 | Palabras LC10 | Instrucciones LC-3 | Instrucciones LC10 |
| --- | ---: | ---: | ---: | ---: |
| `g21_senotaylor_subrutina` | 377 | 51 | 221.428 | 45 |
| `g27_sumover` | 39 | 5 | 49.625 | 0 |
| `g27_todec` | 236 | 130 | 44.757 | 5.552 |
| `g27_circlsh` | 21 | 20 | 6.390 | 0 |
| `g18_booth` | 115 | 29 | 5.714 | 184 |
| `g19_cordic_multiplicacion` | 670 | 42 | 5.107 | 180 |
| `g6_exp` | 505 | 449 | 4.888 | 1.100 |
| `g9_sqrt_nr_q8` | 125 | 62 | 3.521 | 265 |
| `g11_cordiclog` | 156 | 120 | 2.511 | 483 |
| `g14_log_borchardt_q8_7` | 456 | 302 | 2.403 | 197 |
| `g12_subrutina_grupo_12` | 221 | 76 | 2.244 | 93 |
| `g27_main_menu_progreso` | 2605 | 1600 | 2.093 | 2.294 |
| `g27_outval` | 40 | 24 | 1.518 | 965 |
| `g27_from_qm_n` | 33 | 39 | 996 | 456 |
| `g30_seno_cheb_pade` | 181 | 173 | 909 | 901 |
| `g22_tabla_sin_y_cos` | 515 | 439 | 668 | 498 |
| `g5_mul_sucesiva_pow` | 115 | 94 | 471 | 415 |
| `g3_multiplicacionshiftandadd` | 84 | 69 | 331 | 321 |
| `g24_conversor_lc3_max` | 105 | 106 | 307 | 332 |
| `g23_modulo_sqrt_nr` | 58 | 47 | 300 | 273 |
| `division_larga` | 106 | 83 | 289 | 276 |
| `g9_sq9_math_helpers` | 55 | 38 | 238 | 226 |
| `g4_potencia` | 67 | 64 | 218 | 215 |
| `g15_g15_q312_q78` | 46 | 45 | 214 | 213 |
| `g1_cordic_division` | 36 | 37 | 143 | 144 |
| `g7_mcm` | 72 | 53 | 123 | 109 |
| `g7_mcd` | 44 | 32 | 41 | 34 |
| `g9_sqrt_nr_dq16` | 81 | 69 | 30 | 23 |
| `g20_cordic_reduccion_de_argumento` | 32 | 32 | 22 | 22 |
| `main_grupo27` | 141 | 141 | 6 | 6 |
| `g27_fromdec` | 241 | 238 | 0 | 0 |
| `g27_fromhex` | 79 | 67 | 0 | 0 |
| `g27_getval` | 75 | 73 | 0 | 0 |
| `g27_pause` | 47 | 25 | 0 | 0 |
| `g27_getval_buffer` | 33 | 17 | 0 | 0 |
| `g27_getcfiltered` | 32 | 30 | 0 | 0 |

**Qué se cambió en los módulos reescritos y por qué da lo mismo.** En todos se conserva la interfaz (formato de entrada y de salida, registros preservados) y el cómputo del original (truncado o redondeo, orden de las cuentas); se reemplaza lo que la LC-3 tenía que emular:

* `g21` (seno de Taylor): los lazos de sumas y restas de los productos y las divisiones pasan a `MUL`/`MULHU`/`DIVU`, conservando cada truncado intermedio. Identidades exactas: `floor(a·b/4096) = MULHU(4a, 4b)` mientras 4a y 4b entren en 16 bits, y `floor(r·12868/1800) = 7r + floor(67r/450)`.
* `g27_sumover`: `SHR` + `ADC` (5 instrucciones). `g27_circlsh`: el giro de 32 bits se resuelve sin lazo con `SHL`/`SHR` (girar n veces es girar n mod 32). `g27_from_qm_n`: para 1 ≤ n ≤ 15 el original (dos giros de 32 bits) equivale a `entero = qm SAR n` y `fracción = qm SHL (16−n)`; para cualquier otro n se sigue con el camino original.
* `g27_todec`: la parte entera usa `DIVU`/`REMU` en lugar de restar potencias de 10; la fracción del original es la suma de `(10^9 << k) >> 16` truncados por cada bit k encendido, que no es `floor(f·10^9/2^16)`, y se reproduce exactamente con `5^9·(f>>7) + 15258·(f&127) + ((f&127)>>1) + ((f&127)>>2) + ((f&127)>>5)`, calculada en cuatro "limbos" de base 100.
* `g18_booth` y `g19_cordic_multiplicacion`: se conserva el algoritmo (16 pasos de Booth, iteraciones de CORDIC) con el desplazamiento aritmético y el acarreo de la ISA; en Booth se reproduce a propósito la rareza de su bit E con A' = x8000.
* `g12` (Newton-Raphson): los corrimientos bit a bit pasan a `SHR`/`SHL` y `MULT_MODULO` a `MUL`/`MULHU` con el ajuste Q3.12, con la misma aritmética módulo 2^16 que el original.
* `g6_EXP`: las palabras de 15 bits (con las que la LC-3 representa enteros de hasta 45 bits) pasan a pares de 16 bits, porque E < 2^32 y E·d < 2^36; el producto E·d es `MUL`/`MULHU`, el redondeo es `SHR`/`SHL`/`ADC`, y el dígito se busca con `CMP`/`SBC`. La tabla de constantes, el orden de los pasos y el redondeo (mitad hacia arriba) son los del original.
* `g11` (el desplazamiento aritmético que redondea hacia cero, no `SAR`), `g14` y `g9` (rutinas auxiliares y producto Q8): las subrutinas de apoyo pasan a `SHR`/`SHL`/`MUL`/`DIVU`, con la división por cero de `DIV_UNSIGNED` devolviendo 0 como antes.
* **Versión 2 (opcode 31).** En 35 subrutinas de 23 módulos, las rachas de `ST`/`LD` a celdas fijas (o los marcos armados a mano con `ADD R6` y `STW`/`LDW`) pasan a un `PUSH` y un `POP` con la misma lista, y las celdas de guardado desaparecen. Solo se cambió donde cada salida de la subrutina restaura todos los registros guardados y ninguna otra instrucción usa esas celdas; donde un registro guardado se vuelve a leer como dato (R3 en `TODEC`), se lee de la pila con `LDW`. En `TODEC`, los 9 pares `DIVU` + `REMU` con los mismos operandos pasan a `DIVREMU`. No cambia ninguna cuenta: solo dónde se guardan los registros.

**Verificación.** Cada sustitución se comparó con el módulo real de la cátedra ejecutado en su simulador, sin modificarlo:

| Prueba | Alcance | Resultado |
| --- | --- | --- |
| `bench/equivalencia_modulos.py RUTA asm/opt10 --casos 150` | las 39 subrutinas del benchmark (una por cada etiqueta con interfaz propia), 5.801 casos comparados con los registros R1 a R5 inicializados con valores centinela (para que una rutina que no preserve un registro quede en evidencia) y los bordes mezclados con valores al azar; además **17 sesiones interactivas** completas del menú con teclado simulado | 0 diferencias en registros R0 a R5, texto impreso y cadenas escritas; las 17 sesiones imprimen el mismo texto |
| `bench/lc10_bench.py asm/opt10` | el programa automático completo | salida idéntica a la línea base |
| `bench/equivalencia_seno_lc10.py` | los 65.536 valores de R0 de `CALCULAR_SENO`, contra las cuentas exactas del original (que `equivalencia_seno.py` contrasta con el módulo real en 3.704 casos) | 0 diferencias; R1 a R7 preservados |
| `bench/equivalencia_todec_lc10.py` | 328.160 llamadas: las 65.536 fracciones con entero positivo, negativo y 0, los 65.536 enteros y los 8 formatos | 0 diferencias; R0 a R5 y R7 preservados; no escribe fuera del buffer |
| `bench/equivalencia_chicos_lc10.py` | `SUMOVER` y `CIRCLSH`: unas 400.000 llamadas, todos los n de 16 bits | 0 diferencias |
| `bench/equivalencia_div_lc10.py` | `DIV_NEWTON` contra el módulo real: 12.210 casos en una cuadrícula de divisores por longitud de bit (potencias, vecinos y aleatorios, de ambos signos, 0, ±1, x8000) y dividendos | 0 diferencias; R1 a R5 preservados |
| `bench/equivalencia_entradas.py RUTA` | el `main_grupo27.asm` de la cátedra con otras entradas: una operación por programa con dos operandos de 16 bits al azar, en LC-3 (simulador de la cátedra) y en LC10; 52 casos por cada una de las 23 operaciones, más 150 por seno y coseno con tabla dentro de su dominio (`--rango dominio`) | igual texto y misma forma de terminar en las 21 operaciones restantes; en seno y coseno con tabla, iguales dentro del dominio y 16 de 104 distintos fuera de él (ver "Dominio de las tablas") |
| `bench/equivalencia_exp_lc10.py` | `EXP_Q3_12`: las 65.536 entradas posibles, contra el puerto directo (que `equivalencia_modulos.py` ya contrastó con el módulo real), y también EST_EXP y NUM_ITER | 0 diferencias en las 65.536 entradas (registros R0 a R5 y R7 y las dos palabras de estado). Instrucciones por llamada, promedio sobre todas las entradas: 4.020 en el puerto directo y 894 en el optimizado |

**Salvedades que conviene decir tal cual.**

* **Memoria: de dónde sale el ahorro.** De las 2.933 palabras menos que la LC-3 (7.896 → 4.963): unas 1.000 son por guardar el texto en bytes (una característica de la ISA: memoria direccionable por byte); unas 540 son de las rutinas de apoyo de `g19` y `g21` que emulaban desplazamientos, sumas de 32 bits, multiplicaciones y divisiones y que en LC10 son instrucciones; y unas 400 son código que el benchmark nunca ejecuta y que no se portó: los programas de prueba propios de `g19` (354 palabras: `MAIN`, `LEER_ENTERO`, `IMPRIMIR_ENTERO`, `NUEVA_LINEA` y sus mensajes) y de `g21` (unas 44: lectura del ángulo y `HALT`); y 389 son del opcode 31 de la versión 2 (cada guardado y cada restauración de registros pasa a ser una palabra y desaparecen las celdas fijas donde se guardaban). **El Carballo confirmó que esos códigos de prueba se pueden sacar porque son innecesarios**, así que las 4.963 palabras son la cifra válida; el desglose se deja para que se vea de dónde sale cada parte (sin las ~400 palabras de código de prueba quitado, la reducción sería de aproximadamente 32 % en lugar de 37 %). También se descartaron unas pocas palabras de diagnóstico (en `g18_booth` y `g19`) que ningún otro módulo lee.
* **Instrucciones: el recuento de MUL y DIV.** **Carballo confirmó que cuentan como una instrucción** (`MUL`, `MULHU`, `DIVU`, `REMU` y las demás, igual que cualquier otra), que es como se cuentan las 15.822 del usuario. Con el mismo criterio, `PUSH` y `POP` cuentan una instrucción cada una, sin importar cuántos registros muevan. El perfil por módulo (`--por-modulo`) permite recalcular el total si el criterio cambiara.
* **Lo que el original hace mal, se conserva.** El error de 1,0 de la multiplicación BASIC (`g3`) y las diferencias de truncado y redondeo entre módulos (división larga trunca, Newton-Raphson redondea) siguen igual, como indicó Carballo; `g3` y la división larga no se reescribieron.
* **Dominio de las tablas.** `SENO_TABLA` y `COSENO_TABLA` (grupo 22) documentan ángulos de 0 a 2π (0 a 25.736 en Q3.12). Con un ángulo negativo o mayor que 2π el original calcula un índice que se sale de su tabla y lee la memoria que sigue (en LC-3, el código del módulo que el enlazador puso a continuación). El puerto lee también fuera de su tabla, pero ahí la memoria es otra (otra codificación, direcciones de byte), así que el resultado sale distinto. Medido con `bench/equivalencia_entradas.py`: con operandos de 16 bits al azar, 16 de 104 casos de esas dos operaciones dieron distinto, todos con el ángulo fuera de 0..2π; con el ángulo dentro del dominio, 300 de 300 iguales. Las otras 21 operaciones dieron igual en todos los casos. Reproducir también esos resultados obligaría a copiar en LC10 las palabras de LC-3 que hay después de la tabla, que dependen del orden de enlace; no se hizo.
* **Reentrantes.** Los módulos que en la versión 0 guardaban registros en celdas fijas ahora los guardan en la pila con `PUSH`/`POP`. Los que además trabajan con celdas fijas de datos siguen sin ser reentrantes, como los originales.
* **La pila.** Con el opcode 31 todos los módulos que guardan registros usan la pila de R6. Se comprobó en el benchmark completo que cada `POP` encuentra exactamente el marco de su `PUSH`, que ninguna otra instrucción escribe dentro de un marco abierto y que R6 termina en 0 (`tests/test_benchmark.py`).
* **`EXP_Q3_12` contra el módulo real.** Las 65.536 entradas se comparan con el puerto directo, no con el módulo LC-3 (cada llamada cuesta unas 4.900 instrucciones y el simulador de la cátedra es lento); el puerto directo se comparó con el módulo real en miles de entradas al azar, incluidas en el recuento de arriba.
* **Qué queda caro.** `TODEC` ejecuta 5.552 instrucciones (35 % del total, 54 llamadas de unas 103 cada una) y el menú 2.294 (14 %). Bajar `TODEC` más allá de esto exigiría una tabla de 100 pares de dígitos (unas 100 palabras más) y se dejó así.
