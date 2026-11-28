# ISA de 16 bits para el Laboratorio 3c

Especificación ejecutable v0.2. Derivada de LC-3 y pensada para punto fijo, memoria direccionable por byte, ensamblador y simulador funcional. La definición de bits se especifica en este documento y su implementación ejecutable está en `assembler.py` y `simulator.py`.

## 1. Objetivos y decisiones

- Instrucciones de 16 bits con opcode fijo de 5 bits; ocho registros generales de 16 bits; memoria de 64 KiB direccionada por byte.
- Mantiene las operaciones de LC-3 necesarias para sus programas: aritmética, lógica, acceso a memoria, saltos, subrutinas, retornos y TRAP.
- Agrega cargas de byte, offsets PC-relativos compactos, acarreo/préstamo (*borrow*), desplazamientos, constantes y pila de múltiples registros.
- No agrega multiplicación ni división por hardware. Esas operaciones son parte del *benchmark* académico y deben seguir siendo algoritmos de software. Tampoco se implementan por hardware raíz, potencia, exponencial, logaritmo, trigonometría, hiperbólicas ni factorial.
- `MUL` y `DIV` no son instrucciones ni pseudo-instrucciones de esta ISA.
- Se usan los 32 opcodes. Los dos últimos codifican LDW/STW con offset de palabra extendido a 16..31, necesario para ciertos *frames* del *benchmark* LC-3.

Los valores de rendimiento atribuidos a prototipos anteriores de la ISA no se consideran validados por esta implementación. La ejecución diferencial del bloque automático de 23 operaciones se documenta al final; aún se requieren vectores adicionales para validar todos los valores posibles de entrada.

## 2. Estado y convenciones

### Registros y memoria

- `R0` a `R7` son registros generales. `R7` es el registro de enlace (*link register*).
- `SP` es un registro implícito separado, inicializado por `.STACK` (por defecto `xFFFE`). La pila crece hacia direcciones menores.
- La memoria es *little-endian*: en una palabra, la parte baja está en la dirección par y la parte alta en la impar. Las instrucciones y accesos de palabra requieren dirección par.
- El PC apunta a bytes y avanza normalmente `PC + 2`. Los offsets PC-relativos se miden en palabras desde `PC + 2`.
- Un salto a dirección impar o un acceso de palabra desalineado produce una excepción.

### Banderas (*Flags*)

`N`, `Z` y `P` son mutuamente excluyentes y reflejan el resultado de 16 bits. Las operaciones que escriben un registro actualizan N/Z/P; `CMP` los actualiza sin escribir un registro. `PUSHM`, `POPM` y `POPR` preservan todas las banderas.

- `ADD`, `ADDI`, `ADC`, `SUB`, `SBC`, `NEG` y `CMP` actualizan C y V.
- En suma, C es el acarreo de salida. En resta, C es préstamo (*borrow*): queda en 1 si la resta sin signo necesita préstamo.
- `ADC` suma el C de entrada; `SBC` resta el préstamo (*borrow*) de entrada.
- V indica desbordamiento (*overflow*) con signo de 16 bits.
- Los desplazamientos y rotaciones actualizan C con el último bit desplazado/rotado hacia afuera, si el conteo es distinto de cero. Las demás instrucciones preservan C y V.

### Pares de 32 bits

Un entero de 32 bits puede representarse en dos registros consecutivos `(Rh, Rl)`, con `Rh` par: parte alta en `Rh`, parte baja en `Rh+1`. El convenio de retorno de 32 bits es `R0:R1` (alta:baja). En memoria, si se almacena como dos palabras, la palabra alta va primero.

## 3. Formatos binarios

En las tablas, el bit 15 es el más significativo. Todos los campos suman exactamente 16 bits.

| Formato | Bits 15..11 | Bits 10..0 | Instrucciones |
|---|---|---|---|
| `RRR` | `opcode[4:0]` | `Rd[2:0] Rs1[2:0] Rs2[2:0] funct[1:0]` | ALU, LOG, SHIFTV |
| `UNARY` | `opcode[4:0]` | `Rd[2:0] Rs[2:0] funct[1:0] 000` | NOT, NEG |
| `RI5` | `opcode[4:0]` | `Rd[2:0] Rs[2:0] imm5` | ADDI, ANDI |
| `RI8` | `opcode[4:0]` | `Rd[2:0] imm8` | MOVI, MOVH |
| `SHL` | `opcode[4:0]` | `Rd[2:0] Rs[2:0] count[3:0] 0` | SHL |
| `SHR` | `opcode[4:0]` | `Rd[2:0] Rs[2:0] mode  count[3:0]` | LSR, ASR |
| `ROT` | `opcode[4:0]` | `Rd[2:0] Rs[2:0] dir 0000` | RRC, RLC |
| `MEM` | `opcode[4:0]` | `Rt[2:0] Rb[2:0] off5` | LDBL/S/H, STBL/H, LDW/STW |
| `PC8` | `opcode[4:0]` | `R[2:0] off8` | LDPC, STPC, LEA, LDPM, STPM |
| `BR` | `opcode[4:0]` | `cond[3:0] off7` | BR y saltos condicionales |
| `JSR` | `opcode[4:0]` | `off11` | JSR |
| `JR` | `opcode[4:0]` | `funct[1:0] Rb[2:0] 000000` | JMP, JSRR, RET |
| `STACK` | `opcode[4:0]` | `funct[1:0] mask[7:0] 0` | PUSHM, POPM, POPR |
| `TRAP` | `opcode[4:0]` | `000 vector[7:0]` | TRAP |
| `MEMJ` | `opcode[4:0]` | `off11` | JMPM, JSRM |

`imm5` es con signo (-16..15); `imm8` es con signo para MOVI y sin signo para MOVH. `off5`, `off7`, `off8` y `off11` son desplazamientos de palabra con signo en complemento a dos, excepto en las operaciones de byte de MEM, donde `off5` está en bytes. Para LDW/STW, `off5` está en palabras y se multiplica por dos.

## 4. Mapa de opcodes y campos de función

| Opcode | Mnemónico/grupo | Campo de función |
|---|---|---|
| `00000` | BR | condición en bits 10..7 |
| `00001` | ALU | `00 ADD`, `01 SUB`, `10 ADC`, `11 SBC` |
| `00010` | LOG | `00 AND`, `01 OR`, `10 XOR`, `11 CMP` |
| `00011` | ANDI | - |
| `00100` | UNARY | `00 NOT`, `01 NEG` |
| `00101` | ADDI | - |
| `00110` | MOVI | - |
| `00111` | MOVH | - |
| `01000` | SHL | - |
| `01001` | SHR | `mode=0 LSR`, `mode=1 ASR` |
| `01010` | ROT | `dir=0 RRC`, `dir=1 RLC` |
| `01011` | LDBL | - |
| `01100` | LDBS | - |
| `01101` | LDBH | - |
| `01110` | STBL | - |
| `01111` | STBH | - |
| `10000` | LDW | - |
| `10001` | STW | - |
| `10010` | LDPC | - |
| `10011` | STPC | - |
| `10100` | LEA | - |
| `10101` | JSR | - |
| `10110` | JR | `00 JMP`, `01 JSRR`, `10 RET` |
| `10111` | STACK | `00 PUSHM`, `01 POPM`, `10 POPR` |
| `11000` | TRAP | - |
| `11001` | SHIFTV | `00 SHLV`, `01 SRLV`, `10 SRAV`, `11 ROLV` |
| `11010` | JMPM | - |
| `11011` | JSRM | - |
| `11100` | LDPM | - |
| `11101` | STPM | - |
| `11110` | LDW16 | offset efectivo = 16 + signed(off5) palabras |
| `11111` | STW16 | offset efectivo = 16 + signed(off5) palabras |

La función `RRR` de ALU/LOG/SHIFTV está en los bits 1..0. `JMPM` y `JSRM` leen una dirección destino de 16 bits desde una palabra cercana en `PC+2+2*sext(off11)`. JSRM escribe `PC+2` en R7 antes de saltar. `LDPM` y `STPM` direccionan indirectamente a través de una palabra puntero cercana usando el formato PC8.

## 5. Semántica de instrucciones

### Aritmética y lógica

- `ADD/SUB/ADC/SBC Rd,Rs1,Rs2` escriben resultados de 16 bits; el acarreo/préstamo (*carry/borrow*) de entrada y salida siguen las definiciones de banderas anteriores.
- `ADDI Rd,Rs,#imm5`; `ANDI Rd,Rs,#imm5`.
- `MOVI Rd,#imm8` extiende el signo. `MOVH Rd,#imm8` reemplaza el byte alto y conserva el byte bajo. Cualquier constante de 16 bits puede formarse con `LI` (pseudo-instrucción del ensamblador).
- `NOT Rd,Rs`; `NEG Rd,Rs`; `CMP Rs1,Rs2` actualiza las banderas como `Rs1 - Rs2`, sin almacenar.
- `AND/OR/XOR Rd,Rs1,Rs2`.

### Desplazamientos

- `SHL Rd,Rs,#n`, `LSR Rd,Rs,#n`, `ASR Rd,Rs,#n`, donde `n` está entre 0..15.
- `SHLV/SRLV/SRAV/ROLV Rd,Rs,Rc` usan los cuatro bits bajos de Rc.
- `RRC/RLC Rd,Rs` desplazan un bit a través de C; el C anterior entra en el bit liberado.
- Un conteo de desplazamiento cero conserva C.

### Memoria

- `LDBL` extiende con ceros el byte direccionado a 16 bits; `LDBS` extiende su signo; `LDBH` reemplaza únicamente el byte alto del destino.
- `STBL` almacena el byte bajo; `STBH` almacena el byte alto.
- `LDW/STW` transfieren una palabra *little-endian*. Una dirección efectiva impar dispara una excepción de alineación.
- `LDW16/STW16` usan los mismos campos que MEM pero suman 16 al offset de palabra con signo de cinco bits, cubriendo offsets de palabra de 0..31 en conjunto con LDW/STW.
- `LDPC/STPC R,label` acceden a una palabra en una ubicación PC-relativa con signo. `LEA Rd,label` carga su dirección de byte.
- `LDPM/STPM R,label` usan una palabra puntero cercana para acceder a una palabra distante sin sobrescribir (*clobbering*) un registro general.

### Control de flujo

Todos los destinos PC-relativos usan `(PC+2) + 2*sign_extend(offset)`.

| Campo de condición | Significado |
|---|---|
| 0 | Siempre (`BR`, también `BRNZP`) |
| 1, 2, 3 | N, Z, P |
| 4, 5, 6 | N o Z; N o P; Z o P |
| 7 | Nunca (`NOP`) |
| 8, 9 | C; no C |
| 10, 11 | V; no V |
| 12, 13 | menor con signo (`N != V`); mayor o igual con signo (`N == V`) |
| 14, 15 | mayor con signo (`!Z && N == V`); menor o igual con signo (`Z || N != V`) |

- `JSR label` escribe PC+2 en R7. `JSRR Rb` hace lo mismo y salta a Rb.
- `JMP Rb` salta sin escribir R7; `RET` es `JMP R7`.
- `JMPM` salta a una dirección almacenada en una palabra PC-relativa. `JSRM` llama a través de esa palabra. Estas preservan todos los registros generales excepto que JSRM escribe R7.
- El ensamblador expande automáticamente BR/JSR fuera de rango a secuencias JMPM/JSRM y LDPC/STPC fuera de rango a secuencias LDPM/STPM. Un LEA distante se convierte en LI. Estas expansiones no sobrescriben un registro general.
- `TRAP` no modifica R7 ni SP.

### Pila

`PUSHM {register-list}` apila los registros seleccionados; `POPM {register-list}` los restaura. Los registros se almacenan de modo que el registro seleccionado de menor numeración quede en el SP final. `POPR {register-list}` restaura y retorna a través del R7 restaurado; su máscara debe incluir a R7. Las operaciones de pila preservan las banderas.

## 6. Convención de llamada

- Entradas: R0/R1, luego R2/R3 si es necesario.
- Resultado de 16 bits: R0. Resultado de 32 bits: R0:R1 (alto:bajo).
- El llamador (*caller*) puede asumir que R0/R1 son volátiles. Una subrutina llamada (*callee*) preserva R2..R6 al seguir el ABI del *benchmark*.
- R7 es el registro de enlace (*link register*). Las funciones hoja (*leaf*) pueden retornar con RET. Una rutina no hoja guarda R7 antes de otra llamada y lo restaura con POPR antes de retornar.
- SP está separado de R0..R7; se inicializa mediante `.STACK` (o xFFFE por defecto). El *runtime* verifica *underflow*/*overflow* de pila contra su propia profundidad de apilamiento.

## 7. Ensamblador, imagen objeto y simulador

Las herramientas son procesos separados: `assembler.py` lee ensamblador y emite código máquina; `simulator.py` carga únicamente la imagen objeto, nunca texto de ensamblador. Usan solo la biblioteca estándar de Python.

Directivas soportadas: `.ORIG`, `.END`, `.FILL`, `.BLKW` (conteo de palabras), `.BLKB`, `.BYTE`, `.STRINGZ` (bytes Latin-1 más NUL), `.STACK` y `.EXTERNAL source-SYMBOL`. Los archivos fuente externos se buscan sin distinguir mayúsculas/minúsculas junto al origen, en una carpeta `lib` o mediante `-I`; las importaciones se enlazan recursivamente en una sola imagen y las etiquetas locales de módulo tienen alcance acotado (*scoped*). Las importaciones o símbolos faltantes se reportan como errores.

Los datos de palabra y las instrucciones se alinean a direcciones pares. Si los datos de byte dejan impar la siguiente palabra/instrucción, el ensamblador inserta un byte de relleno en cero. `.FILL` se emite en *little-endian*.

El diseño del objeto binario es:

1. bytes 0..1: `.ORIG`, sin signo de 16 bits *little-endian*;
2. bytes 2..3: SP inicial, sin signo de 16 bits *little-endian* (`.STACK` o xFFFE);
3. bytes restantes: imagen contigua de memoria comenzando en `.ORIG`.

Los alias/pseudo-instrucciones incluyen `LD=LDPC`, `ST=STPC`, `LDR=LDW`, `STR=STW`, formas inmediatas de LC-3 `ADD`/`AND`, `MOV`, `CLR`, `INC`, `DEC`, `LI`, `PUSH`, `POP`, `NOP` y GETC/OUT/PUTS/IN/HALT. El ensamblador selecciona LDW16/STW16 para offsets 16..31. Un salto o llamada corta fuera de rango se relaja (*relaxed*) automáticamente. Otros offsets de memoria/PC-relativos fuera de rango y valores inmediatos inválidos son errores en lugar de truncamientos silenciosos.

Servicios TRAP: `x20` GETC (un byte de entrada, sin eco); `x21` OUT (byte bajo de R0); `x22` PUTS (bytes terminados en NUL en R0); `x23` IN (leer y hacer eco de un byte); `x25` HALT. La entrada se suministra al simulador con `--input`.

Ejecute el simulador con un objeto binario enlazado (`.bin` o `.obj`) o su representación hexadecimal separada por espacios en blanco (`.hex`). El simulador no acepta código fuente en ensamblador:

```powershell
python assembler.py programa.asm -o programa.obj -I benchmark_inspect\lib
python simulator.py programa.obj --input "123"
python simulator.py programa.hex
python -m unittest -v test_isa
```

El archivo hexadecimal contiene los mismos bytes de objeto que el archivo binario, incluyendo el origen y la cabecera del SP inicial. Para ejecutar ensamblador, ensámblelo primero; el simulador rechaza entradas `.asm`.

El simulador reporta la salida, registros finales, total de instrucciones ejecutadas, bytes de imagen cargados y máximo de bytes de pila usados. También verifica alineación de PC, alineación de palabra, codificaciones ilegales, traps no soportados y límites de instrucciones.

## 8. Alcance y validación restante

`LDI/STI` pueden expresarse como una secuencia de carga/almacenamiento indirecto; las interrupciones/RTI no se incluyen porque no las utiliza el *benchmark*. La aritmética de punteros debe traducirse de unidades de palabra de LC-3 a direcciones de byte: avanzar un puntero a una palabra cambia de `#1` a `#2`. Las cadenas ahora ocupan un byte por carácter. Las rutinas heredadas que usan R6 como pila descendente de palabras escalan esos ajustes a bytes; esto es independiente del `SP` implícito de la ISA.

## 9. Referencia rápida: qué hace cada instrucción

| Instrucción | Qué hace |
|---|---|
| `BR` (y variantes condicionales) | Evalúa la condición (`N`, `Z`, `P`, combinaciones, `C`, `V`, comparaciones con signo o siempre/nunca); si se cumple, salta a `(PC+2) + 2*sext(off7)`. |
| `ADD` | Calcula `Rs1 + Rs2` en 16 bits, guarda el resultado en `Rd` y actualiza `N`, `Z`, `P`, `C` y `V`. |
| `SUB` | Calcula `Rs1 - Rs2` en 16 bits, guarda el resultado en `Rd` y actualiza `N`, `Z`, `P`, `C` (*borrow*) y `V`. |
| `ADC` | Calcula `Rs1 + Rs2 + C_in` en 16 bits, guarda en `Rd` y actualiza banderas (`C` y `V` incluidos). |
| `SBC` | Calcula `Rs1 - Rs2 - C_in` en 16 bits, guarda en `Rd` y actualiza banderas (`C` y `V` incluidos). |
| `AND` | Aplica AND bit a bit entre `Rs1` y `Rs2`, guarda en `Rd` y actualiza `N`, `Z`, `P` (preserva `C` y `V`). |
| `OR` | Aplica OR bit a bit entre `Rs1` y `Rs2`, guarda en `Rd` y actualiza `N`, `Z`, `P` (preserva `C` y `V`). |
| `XOR` | Aplica XOR bit a bit entre `Rs1` y `Rs2`, guarda en `Rd` y actualiza `N`, `Z`, `P` (preserva `C` y `V`). |
| `CMP` | Evalúa `Rs1 - Rs2` para actualizar `N`, `Z`, `P`, `C` y `V` sin guardar el resultado en ningún registro. |
| `ANDI` | Aplica AND bit a bit entre `Rs` y `sext(imm5)`, guarda en `Rd` y actualiza `N`, `Z`, `P` (preserva `C` y `V`). |
| `NOT` | Invierte todos los bits de `Rs` (complemento a uno), guarda en `Rd` y actualiza `N`, `Z`, `P` (preserva `C` y `V`). |
| `NEG` | Niega `Rs` en complemento a dos (`-Rs`), guarda en `Rd` y actualiza `N`, `Z`, `P`, `C` y `V`. |
| `ADDI` | Suma `Rs + sext(imm5)` en 16 bits, guarda en `Rd` y actualiza `N`, `Z`, `P`, `C` y `V`. |
| `MOVI` | Carga `sext(imm8)` de 8 bits extendido a 16 bits en `Rd` y actualiza `N`, `Z`, `P`. |
| `MOVH` | Escribe `imm8` sin signo en el byte alto de `Rd` conservando su byte bajo, y actualiza `N`, `Z`, `P`. |
| `SHL` | Desplaza `Rs` a la izquierda `count` bits (`0..15`, ceros a la derecha), guarda en `Rd`; si `count > 0`, actualiza `C` con el último bit salido. |
| `LSR` | Desplaza `Rs` a la derecha `count` bits de forma lógica (`0..15`, ceros a la izquierda), guarda en `Rd`; si `count > 0`, actualiza `C`. |
| `ASR` | Desplaza `Rs` a la derecha `count` bits de forma aritmética (`0..15`, replica el signo), guarda en `Rd`; si `count > 0`, actualiza `C`. |
| `RRC` | Rota `Rs` un bit a la derecha a través de `C` (el bit 0 sale a `C` y el `C` previo entra al bit 15), guarda en `Rd` y actualiza `C`. |
| `RLC` | Rota `Rs` un bit a la izquierda a través de `C` (el bit 15 sale a `C` y el `C` previo entra al bit 0), guarda en `Rd` y actualiza `C`. |
| `SHLV` | Desplaza `Rs` a la izquierda tantos bits como indiquen los 4 bits bajos de `Rc`, guarda en `Rd` y actualiza `C` si el conteo es distinto de cero. |
| `SRLV` | Desplaza `Rs` a la derecha lógicamente según los 4 bits bajos de `Rc`, guarda en `Rd` y actualiza `C` si el conteo es distinto de cero. |
| `SRAV` | Desplaza `Rs` a la derecha aritméticamente según los 4 bits bajos de `Rc`, guarda en `Rd` y actualiza `C` si el conteo es distinto de cero. |
| `ROLV` | Rota/desplaza según `funct=11` usando `Rs` y los 4 bits bajos de `Rc`, guardando en `Rd` y actualizando `C` si el conteo es distinto de cero. |
| `LDBL` | Lee un byte desde `Rb + sext(off5)`, lo extiende con ceros a 16 bits en `Rt` y actualiza `N`, `Z`, `P`. |
| `LDBS` | Lee un byte desde `Rb + sext(off5)`, lo extiende con signo a 16 bits en `Rt` y actualiza `N`, `Z`, `P`. |
| `LDBH` | Lee un byte desde `Rb + sext(off5)` y lo coloca en el byte alto de `Rt` manteniendo su byte bajo; actualiza `N`, `Z`, `P`. |
| `STBL` | Escribe el byte bajo de `Rt` en la dirección de byte `Rb + sext(off5)`. |
| `STBH` | Escribe el byte alto de `Rt` en la dirección de byte `Rb + sext(off5)`. |
| `LDW` | Lee una palabra de 16 bits (*little-endian*) desde `Rb + 2*sext(off5)` (requiere dirección par) hacia `Rt` y actualiza `N`, `Z`, `P`. |
| `STW` | Escribe la palabra de 16 bits de `Rt` (*little-endian*) en `Rb + 2*sext(off5)` (requiere dirección par). |
| `LDW16` | Lee una palabra de 16 bits (*little-endian*) desde `Rb + 2*(16 + sext(off5))` (requiere dirección par) hacia `Rt` y actualiza `N`, `Z`, `P`. |
| `STW16` | Escribe la palabra de 16 bits de `Rt` (*little-endian*) en `Rb + 2*(16 + sext(off5))` (requiere dirección par). |
| `LDPC` | Carga en `R` la palabra de 16 bits ubicada en `(PC+2) + 2*sext(off8)` y actualiza `N`, `Z`, `P`. |
| `STPC` | Almacena la palabra de 16 bits de `R` en la dirección PC-relativa `(PC+2) + 2*sext(off8)`. |
| `LEA` | Calcula la dirección de byte `(PC+2) + 2*sext(off8)`, la carga en `R` y actualiza `N`, `Z`, `P`. |
| `LDPM` | Lee una palabra puntero en `(PC+2) + 2*sext(off8)` y carga en `R` la palabra apuntada en memoria; actualiza `N`, `Z`, `P`. |
| `STPM` | Lee una palabra puntero en `(PC+2) + 2*sext(off8)` y almacena `R` en la dirección apuntada en memoria. |
| `JSR` | Guarda `PC+2` en `R7` y salta a `(PC+2) + 2*sext(off11)`. |
| `JSRR` | Guarda `PC+2` en `R7` y salta a la dirección contenida en `Rb`. |
| `JMP` | Salta incondicionalmente a la dirección contenida en `Rb` sin modificar `R7`. |
| `RET` | Retorna de subrutina saltando a la dirección en `R7` (`JMP R7`). |
| `JMPM` | Lee una dirección de 16 bits desde `(PC+2) + 2*sext(off11)` y salta a ella sin modificar `R7`. |
| `JSRM` | Guarda `PC+2` en `R7`, lee una dirección de 16 bits desde `(PC+2) + 2*sext(off11)` y salta a ella. |
| `PUSHM` | Decrementa `SP` y apila los registros indicados en la máscara (dejando el de menor número en el `SP` final); preserva banderas. |
| `POPM` | Desapila e incrementa `SP` restaurando los registros indicados en la máscara; preserva banderas. |
| `POPR` | Restaura los registros indicados en la máscara (debe incluir `R7`) y retorna saltando al `R7` restaurado; preserva banderas. |
| `TRAP` | Invoca el servicio del sistema indicado por `vector[7:0]` (`x20` GETC, `x21` OUT, `x22` PUTS, `x23` IN, `x25` HALT) sin alterar `R7` ni `SP`. |