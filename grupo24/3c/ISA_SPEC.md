# ISA Extendida LC-3 de 16 bits

## 1. Modelo general

- Longitud de instruccion: 16 bits.
- Banco de registros: 8 registros generales de 16 bits (`R0` a `R7`).
- Memoria: 65536 bytes, direccionable por byte, little-endian.
- Contador de programa: 16 bits. Las instrucciones clasicas ocupan 2 bytes y `PC <- PC + 2`; las instrucciones `EXT` ocupan 4 bytes y `PC <- PC + 4`.
- Palabras cargadas o almacenadas: 16 bits little-endian.
- Enteros: complemento a dos de 8 o 16 bits segun la operacion.
- Punto fijo: software. No existen instrucciones SQRT, POW, EXP, LOG, SIN, COS, TAN, ASIN, ACOS, ATAN, SINH, COSH, TANH ni factorial.
- `HALT` termina la ejecucion.
- Direcciones impares y sobrecarga fuera del espacio de 16 bits son errores definidos por el simulador.

## 2. Convencion de registros

| Registro | Uso recomendado |
|---|---|
| R0 | Retorno primario y operando |
| R1 | Segundo operando y mitad baja de una operacion de 32 bits |
| R2-R5 | Operandos y temporales |
| R6 | Puntero de pila; la pila crece hacia direcciones menores |
| R7 | Direccion de retorno JSR |

Los modulos deben declarar si conservan o destruyen registros. Las rutinas de benchmark deben preservar R2-R6 salvo un contrato contrario documentado.

## 3. Flags

- `N`: resultado negativo.
- `Z`: resultado cero.
- `P`: resultado positivo.
- `C`: carry/sin borrow fuera del rango sin signo.
- `V`: overflow aritmetico con signo.

La semantica de `CMP` establece N/Z/P y C/V segun la resta. Las operaciones logicas y desplazamientos actualizan N/Z/P. C y V quedan indefinidos salvo que la instruccion los calcule expresamente.

## 4. Campos comunes

Los primeros 5 bits son el opcode:

```text
15 14 13 12 11 | 10 9 8 | 7 6 5 | 4 3 2 | 1 0
 opcode          d/s1      s2       s3       modo/aux
```

No todos los campos existen en todas las instrucciones. Los formatos siguientes son los unicos admitidos:

- `RRR`: `opcode[15:11] | Rd[10:8] | Rs1[7:5] | Rs2[4:2] | 00[1:0]`.
- `RR`: `opcode[15:11] | Rd[10:8] | Rs[7:5] | 00000[4:0]`.
- `RI`: `opcode[15:11] | Rd[10:8] | imm7[7:1] | 1[0]`. El bit de modo `bit[0]=1` distingue RI de RRR; `imm7` es con signo en `-64..63` para `ADD`, `SUB`, `CMP`, `TEST` y sin signo en `0..127` para `AND`, `OR`, `XOR`. En RI el registro fuente es el mismo `Rd`; la sintaxis `ADD Rd, Rs, #n` solo es válida si `Rs` es `Rd`.
- `RRR` con `bit[1]=1`: modo extendido de 3 operandos para `CMP Rd, Rs1, Rs2`. En `CMP` de tres registros se comparan `Rs1` y `Rs2`; las formas de dos operandos siguen usando `bit[1]=0`.
- `EXT`: `opcode[15:11]=11111 | Rd[10:8] | func[7:0] |payload[15:0]`; dos palabras contiguas, `Rd` no se usa en `BR16`.
- `RM`: `opcode[15:11] | Rt[10:8] | Rb[7:5] | imm5[4:0]`.
- `BR`: `opcode[15:11] | cond[10:8] | PCoffset8[7:0]` (offset relativo con signo expresado en bytes desde `PC + 2`).
- `JMP`: `opcode[15:11] | 000[10:8] | Rb[7:5] | 00000[4:0]`.
- `JSR`: `opcode[15:11] | 0[10] | PCoffset10[9:0]` para llamada directa relativa en bytes desde `PC + 2`; rango `-512..511` bytes.
- `JSRR`: `opcode[15:11] | 1[10] | Rb[7:5] | 00000[4:0]`.
- `TRAP`: `opcode[15:11] | vector[10:0]`.

Si una sintaxis no puede representarse en 16 bits, el ensamblador debe rechazarla.

## 5. Mapa completo de opcodes

| Opcode | Mnemonico | Formato | Implementacion del benchmark |
|---:|---|---|---|
| 00000 | ADD | RRR / RI | Aritmetica base y inmediatos |
| 00001 | SUB | RRR / RI | Resta de punto fijo, comparaciones y multiplicadores |
| 00010 | AND | RRR / RI | Mascaras y bits |
| 00011 | OR | RRR | Union de mascara |
| 00100 | XOR | RRR | Diferencia de bits |
| 00101 | NOT | RR | Complemento a uno |
| 00110 | CMP | RRR / RI | Comparaciones y signos |
| 00111 | MOV | RR / RI | Copias e inmediatos |
| 01000 | SHL | RRR / RI | Multiplicacion por potencias de dos |
| 01001 | SHR | RRR / RI | Desplazamiento logico |
| 01010 | ASR | RRR / RI | Desplazamiento aritmetico para punto fijo |
| 01011 | SWAP | RR | Intercambio de bytes |
| 01100 | MUL | RRR | Producto bajo 16 bits |
| 01101 | MULH | RRR | Parte alta con signo |
| 01110 | DIV | RRR | Cociente entero con signo |
| 01111 | REM | RRR | Resto entero con signo |
| 10000 | LOADL | RM | Carga byte en bits 7:0 |
| 10001 | LOADH | RM | Carga byte en bits 15:8 |
| 10010 | LOAD | RM | Carga palabra 16 bits |
| 10011 | STOREL | RM | Almacena bits 7:0 |
| 10100 | STOREH | RM | Almacena bits 15:8 |
| 10101 | STORE | RM | Almacena palabra 16 bits |
| 10110 | BR | Bcc | Ramificaciones condicionales |
| 10111 | JSR | JSR / JSRR | Llamada relativa o indirecta |
| 11000 | JMP | JMP | Salto indirecto sin retorno |
| 11001 | RET | RR | Retorno desde subrutina |
| 11010 | TRAP | TRAP | Servicio de sistema / HALT |
| 11011 | NOP | ninguno | Instruccion sin efecto |
| 11100 | SIGN | RR | Extension de signo de 8 bits |
| 11101 | SE | RI/RR | Limita o convierte un entero en base fija |
| 11110 | TEST | RR / RI | Solo actualiza flags sin escribir |
| 11111 | EXT | EXT | Prefijo de instrucciones de 4 bytes: LI16, MOVU, LDABS, STABS, ZEXT8, SEXT8, SHLV, ADDI16, SUBI16, ANDI16, ORI16, XORI16, CMP16, BR16 |

## 6. Semantica exacta

### 6.1 Aritmetica

- `ADD Rd, Rs1, Rs2`: `Rd <- Rs1 + Rs2`; actualiza N/Z/P/C/V.
- `ADD Rd, Rs, #n`: `Rd <- Rd + n`, con `Rs == Rd` y `n` en `-64..63`.
- `SUB Rd, Rs1, Rs2`: `Rd <- Rs1 - Rs2`; actualiza N/Z/P/C/V.
- `SUB Rd, Rs, #n`: `Rd <- Rd - n`, con `Rs == Rd` y `n` en `-64..63`.
- `AND Rd, Rs1, Rs2`: `Rd <- Rs1 & Rs2`.
- `AND Rd, Rs, #n`: `Rd <- Rd & n`, con `Rs == Rd` y `n` en `0..127`.
- `OR Rd, Rs1, Rs2`: `Rd <- Rs1 | Rs2`.
- `OR Rd, Rs, #n`: `Rd <- Rd | n`, con `Rs == Rd` y `n` en `0..127`.
- `XOR Rd, Rs1, Rs2`: `Rd <- Rs1 XOR Rs2`.
- `XOR Rd, Rs, #n`: `Rd <- Rd XOR n`, con `Rs == Rd` y `n` en `0..127`.
- `NOT Rd, Rs`: complemento a uno bit a bit.
- `CMP Rs1, Rs2`: calcula `Rs1 - Rs2` sin escribir, actualiza N/Z/P/C/V. Es alias del modo RRR clásico y usa `bit[1]=0`.
- `CMP Rd, Rs1, Rs2`: calcula `Rs1 - Rs2` sin escribir, usa `bit[1]=1` y mantiene `Rd` como campo libre compatible.
- `CMP Rs, #n`: calcula `Rs - n` sin escribir, con `n` en `-64..63`.
- `MOV Rd, imm8`: carga un inmediato con signo de 8 bits. Las copias registro-registro se realizan con `OR Rd, Rs, R0`, con R0 a cero. `MOVU Rd, imm16` es el alias sin signo basado en `LI16`.
- `TEST Rs`: actualiza flags según `Rs`.
- `TEST Rs1, Rs2`: actualiza flags según `Rs1 & Rs2` sin escribir.
- `TEST Rs, #n`: actualiza flags según `Rs & n` sin escribir, con `n` en `-64..63`.

### 6.2 Desplazamientos

- `SHL Rd, Rs, count`: desplazamiento logico izquierdo por 0..15.
- `SHR Rd, Rs, count`: desplazamiento logico derecho por 0..15.
- `ASR Rd, Rs, count`: desplazamiento aritmetico derecho por 0..15.
- `SWAP Rd`: invierte los bytes de `Rd`.
- `SWAP Rd, Rs`: `Rd[15:8] <- Rs[7:0]`, `Rd[7:0] <- Rs[15:8]`; se codifica con `bit[0]=1` y `Rs[3:1]`.
- Los `count` se toman de un inmediato de 5 bits o de un registro, segun el formato ensamblado.
- Desplazar por mas de 15 genera error de ensamble o simulacion segun la codificacion.

### 6.3 Multiplicacion y division

- `MUL Rd, Rs1, Rs2`: resultado con signo de 32 bits; las 16 partes bajas quedan en `Rd` y las 16 partes altas quedan en `R1` si `Rd=R0`, o bien `MUL Rd, Rs1, Rs2` escribe solo el resultado 16 bits truncado. En el assembler/simulator se usa el contrato fijo siguiente: `MUL` escribe la palabra baja en `Rd`; `MULH` escribe la parte alta con signo en `Rd`.
- `MULH Rd, Rs1, Rs2`: parte alta del producto con signo.
- `DIV Rd, Rs1, Rs2`: cociente truncado hacia cero.
- `REM Rd, Rs1, Rs2`: resto con signo del dividendo.
- Division por cero genera excepcion configurable; no puede producirse por una instruccion encubierta de otro modulo.

### 6.4 Memoria byte-addressable

El formato comun es `LOADx Rt, offset(Rb)` o `STOREx Rt, offset(Rb)`.

- `LOADL Rt, imm5(Rb)`: EA = Rb + sign_extend(imm5); carga 8 bits en `Rt[7:0]` y pone `Rt[15:8] <- 0`.
- `LOADH Rt, imm5(Rb)`: EA = Rb + sign_extend(imm5); carga 8 bits en `Rt[15:8]` y pone `Rt[7:0] <- 0`.
- `LOAD Rt, imm5(Rb)`: EA = Rb + sign_extend(imm5); exige EA par y carga dos bytes little-endian.
- `STOREL Rt, imm5(Rb)`: EA = Rb + sign_extend(imm5); almacena `Rt[7:0]`.
- `STOREH Rt, imm5(Rb)`: EA = Rb + sign_extend(imm5); almacena `Rt[15:8]`.
- `STORE Rt, imm5(Rb)`: EA = Rb + sign_extend(imm5); exige EA par y almacena dos bytes little-endian.

`imm5` es solo un desplazamiento corto. Los modulos grandes usan registros base cargados con ADDI/MOV y direcciones absolutas ensambladas mediante pseudo-instrucciones.

### 6.5 Control de flujo

- `BRcc label`: si la condicion de `cond` se cumple, `PC <- PC_destino`; de lo contrario `PC <- PC + 2`. `PC_destino = PC + 2 + sign_extend(PCoffset8)`.
- Condiciones: 000 nunca, 001 P, 010 Z, 011 NZ, 100 N, 101 NP, 110 NZP, 111 siempre.
- El offset relativo se expresa en bytes dentro de la codificacion y no en palabras. El PC destino debe ser par.
- `JSR label`: `R7 <- PC + 2`; `PC <- destino`; destino relativo en bytes.
- `JSRR Rb`: `R7 <- PC + 2`; `PC <- Rb`; exige destino par.
- `JMP Rb`: `PC <- Rb`; exige destino par; no guarda retorno.
- `RET`: alias de `JMP R7` y no modifica R7 salvo que el registro sea cambiado por la operacion; si R7 vale `0`, no hay marco de llamada activo y el simulador termina la ejecucion.
- En todo salto, si destino < 0 o destino >= 65536 se lanza excepcion fuera de rango.

### 6.6 Conversiones y sistema

- `SIGN Rd, Rs`: extension de signo del byte bajo de Rs a 16 bits.
- `SE Rd, imm8`: definida como movimiento con extension de signo para inmediatos de 8 bits.
- `NOP`: `PC <- PC + 2`, sin modificar registros ni flags.
- `TRAP vector`: llama al servicio indicado por vector, sin escribir registros salvo por el servicio especificado.
- `TRAP 0x000`: HALT.
- `TRAP 0x020`: GETC.
- `TRAP 0x021`: OUT.
- `TRAP 0x022`: PUTS.
- `TRAP 0x023`: IN.
- `TRAP 0x025`: finaliza modo batch.

## 7. Codificacion de operaciones RRR

Formato usado:

```text
RRR: [15:11] opcode | [10:8] Rd | [7:5] Rs1 | [4:2] Rs2 | [1:0] 00
RI:  [15:11] opcode | [10:8] Rd | [7:1] imm7 | [0] 1
```

Las operaciones RRR dejan los dos bits menos significativos en cero. RR deja `[7:5]` como origen y `[4:0]` en cero. RI usa el bit menos significativo como bit de modo, de modo que un inmediato cuyos bits bajos antes eran cero ya no se confunde con una instrucción RRR.

Ejemplos:

- `ADD R1, R2, R3`: bits = ADD(00000)<<11 | R1(001)<<8 | R2(010)<<5 | R3(011)<<2.
- `ADD R0, R0, #3`: opcode ADD 00000, `Rd=R0`, `imm7=3`, `bit[0]=1`.
- `ASR R0, R0, #3`: opcode ASR 01010, `Rd=R0`, inmediato=3.
- `LOAD R2, 4(R6)`: LOAD 10010, Rt=R2, Rb=R6, imm5=4.

## 8. Directivas del ensamblador

Sintaxis prevista:

- `.ORIG direccion`: establece origen del modulo y origen de carga.
- Si no hay `.ORIG` antes de la primera linea efectiva, el ensamblador usa `x3000` como origen implicito; los `.ORIG` posteriores cambian el LC desde esa punto.
- `.END`: termina el modulo.
- `.FILL valor`: reserva una palabra alineada de 16 bits.
- `.BLKW cantidad`: reserva cantidad palabras.
- `.STRINGZ "texto"`: bytes UTF-8/ASCII y byte nulo final.
- `.BYTE valor`: un byte sin signo o con signo representable.
- `.EXTERNAL simbolo-modulo-simbolo`: declara relacion externa para el enlazador.
- `.GLOBAL simbolo`: exporta un simbolo.
- `.ALIGN2`: alineacion explicita de la siguiente instruccion o dato.

Cada instruccion se almacena a direccion par. `.STRINGZ` y `.BYTE` pueden dejar LC impar; el ensamblador agrega automaticamente un byte `0x00` antes de la siguiente instruccion, registrando el ajuste. `.BLKW` inicia solo si LC es par y avanza 2 bytes por palabra.

## 9. Endianness y formato de salida

- El cargador carga las palabras como dos bytes little-endian.
- El archivo hexadecimal contiene 16 bits por linea o bytes separados por espacio; el formato binario incluye los dos bytes de la direccion `.ORIG` al inicio en little-endian.
- Para binario: `[LO_ORIG][HI_ORIG][imagen desde ORIG...]`.
- Para hexadecimal: cada palabra se representa `HHLL` o se documenta little-endian para evitar ambiguedad.

## 10. Motivos de optimizacion respecto al benchmark

- `MUL` y `MULH` eliminan bucles manuales de multiplicacion shift-and-add y Booth.
- `DIV`/`REM` sustituyen bucles extensos de division larga y Newton en casos de 16 bits exactos.
- `SHL`, `SHR` y `ASR` reemplazan rutinas locales de corrimiento y normalizacion.
- `SWAP` sustituye intercambios manuales de bytes usados por conversiones Q.
- `LOADH/LOADL/STOREH/STOREL` permiten operaciones sobre componentes de palabras y valores DQ16 sin leer palabras completas.
- `CMP` permite terminar bucles sin secuencias ADD/BR manuales.
- JSR/JSRR/RET conservan la direccion de retorno sin usar secuencias de TRAP ni saltos relativos LC-3.

Ninguna instruccion nueva calcula funciones trascendentes. Todas las rutinas matematicas deben descomponerse en operaciones primitivas y bucles visibles en el programa ensamblado.

## 11. Extensiones EXT y alias de optimizacion

El opcode 31, antes reservado, es ahora prefijo `EXT`. Todas las operaciones EXT tienen dos palabras:

```text
palabra 0: [15:11]=11111 | [10:8]=Rd | [7:0]=func
palabra 1: payload de 16 bits
```

| func | Mnemonico | Operandos | Semantica |
|---:|---|---|---|
| 0x00 | `LI16`, `MOVU` | `Rd, imm16` | `Rd <- imm16`; actualiza N/Z/P |
| 0x01 | `LDABS` | `Rd, addr16` | `Rd <- M[addr16]`; exige direccion par |
| 0x02 | `STABS` | `Rd, addr16` | `M[addr16] <- Rd` |
| 0x03 | `ZEXT8` | `Rd, Rs` | `Rd <- cero(Rs[7:0])` |
| 0x04 | `SEXT8` | `Rd, Rs` | `Rd <- signo(Rs[7:0])` |
| 0x05 | `SHLV` | `Rd, Rs1, Rs2` | `Rd <- Rs1 << (Rs2 & 15)` |
| 0x06 | `ADDI16` | `Rd, imm16` | `Rd <- Rd + imm16`; actualiza N/Z/P/C/V |
| 0x07 | `SUBI16` | `Rd, imm16` | `Rd <- Rd - imm16`; actualiza N/Z/P/C/V |
| 0x08 | `ANDI16` | `Rd, imm16` | `Rd <- Rd & imm16`; actualiza N/Z/P |
| 0x09 | `ORI16` | `Rd, imm16` | `Rd <- Rd | imm16`; actualiza N/Z/P |
| 0x0A | `XORI16` | `Rd, imm16` | `Rd <- Rd XOR imm16`; actualiza N/Z/P |
| 0x0B | `CMP16` | `Rd, imm16` | compara `Rd - imm16` sin escribir |
| 0x0C | `BR16` | `label` | salto incondicional absoluto a `label` |

Compatibilidad y alias:

- Las instrucciones clasicas conservan su codificacion y semantica.
- `MOV Rd, imm8` sigue aceptando `-128..127` y ahora rechaza `128..255`; use `MOVU Rd, imm16` para esos valores.
- `SE Rd, imm8` permanece como alias de movimiento con signo.
- `CMP Rd, Rs1, Rs2` es una forma compatible del modo RRR con `bit[1]=1`; `CMP Rs1, Rs2` sigue siendo la forma de dos operandos.
- `TEST Rd, #n` signa el inmediato de 7 bits antes de aplicar la máscara.
- `TRAP` y `HALT` permanecen como alias del opcode 26.

El ensamblador calcula longitudes en la primera pasada, por lo que las etiquetas después de una instrucción EXT quedan desplazadas 4 bytes. El simulador avanza `PC <- PC + 4` solo cuando el opcode es 31 y `func` pertenece a la tabla anterior.

El peephole es opcional (`--peephole` en el CLI o `Assembler(peephole=True)`) y solo reemplaza secuencias del mismo tamaño: `MOV+SHL` pasa a `LI16`, y `MOV+SHL+NOT` pasa a `LI16+NOP`. No cambia offsets ni direcciones de etiquetas.
