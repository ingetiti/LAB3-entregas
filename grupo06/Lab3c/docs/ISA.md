# ISA3C integrada, versión 1.1

Diseño para Laboratorio 3c. Conserva la funcionalidad de LC-3 y sus ocho registros de 16 bits, con una codificación nueva. Los objetos de LC-3 original no son compatibles con esta ISA.

## Estado y memoria

- R0–R7: 16 bits. R7 contiene la dirección de retorno de JSR/JSRR; R6 se usa como pila.
- PC, IR y PSR: 16 bits. PSR[2:0] contiene N, Z y P; PSR[15] indica usuario.
- Memoria de 65.536 direcciones de **un byte**, de x0000 a xFFFF.
- Una palabra ocupa dos bytes, con el byte alto primero: xBEEF en x3100 se guarda como BE en x3100 y EF en x3101.
- Enteros de 16 bits en complemento a dos. LDBS extiende el signo de un entero de 8 bits. El punto fijo lo interpreta el programa, no la CPU.
- Las instrucciones tienen 16 bits y comienzan en direcciones pares. La búsqueda incrementa PC en dos; los cálculos PC relativos usan ese PC actualizado. Las sumas de direcciones se reducen módulo 65.536.

El núcleo almacena la RAM en `uint8_t memory[65536]`. El mapa adicional de accesos sirve para medir uso de memoria; no amplía la RAM de la máquina simulada.

## Códigos de operación

Siempre se decodifican **los bits 15 a 11**, sin excepciones. Hay 32 códigos posibles; el 31 contiene la familia SHIFT y su submodo 11 queda reservado. Las variantes de inmediato y desplazamiento negativo tienen códigos separados para conservar ocho registros y alcances útiles dentro de 16 bits.

| Decimal | Bits 15..11 | Operación |
|---:|:---:|---|
| 0 | 00000 | BR condicional / NOP |
| 1 | 00001 | Familia ADD/SUB/MUL/MULU entre registros |
| 2 | 00010 | ADD con inmediato |
| 3 | 00011 | Familia AND/DIVU/CLZ/MOV entre registros |
| 4 | 00100 | AND con inmediato |
| 5 | 00101 | NOT |
| 6 | 00110 | LD, desplazamiento no negativo |
| 7 | 00111 | ST, desplazamiento no negativo |
| 8 | 01000 | LDI, desplazamiento no negativo |
| 9 | 01001 | STI, desplazamiento no negativo |
| 10 | 01010 | LEA, desplazamiento no negativo |
| 11 | 01011 | LDR, desplazamiento no negativo |
| 12 | 01100 | LDR, desplazamiento negativo |
| 13 | 01101 | STR, desplazamiento no negativo |
| 14 | 01110 | STR, desplazamiento negativo |
| 15 | 01111 | JSR |
| 16 | 10000 | JSRR |
| 17 | 10001 | JMP / RET |
| 18 | 10010 | RTI |
| 19 | 10011 | TRAP |
| 20 | 10100 | LDBL: cargar byte en la parte baja de un registro |
| 21 | 10101 | LDBH: cargar byte en la parte alta de un registro |
| 22 | 10110 | STBL: guardar parte baja del registro |
| 23 | 10111 | STBH: guardar parte alta del registro |
| 24 | 11000 | LDBS: cargar byte con extensión de signo |
| 25 | 11001 | LD, desplazamiento negativo |
| 26 | 11010 | ST, desplazamiento negativo |
| 27 | 11011 | LDI, desplazamiento negativo |
| 28 | 11100 | STI, desplazamiento negativo |
| 29 | 11101 | LEA, desplazamiento negativo |
| 30 | 11110 | BRL: salto incondicional relativo largo |
| 31 | 11111 | SHL/SHR/SAR (ASR es alias), submodo 11 reservado |

Los sufijos «negativo» de la tabla son decisiones de codificación. En assembly se escribe siempre LD, ST, LDR, etc.; el ensamblador elige la variante.

## Formatos

`op` ocupa 5 bits; `d`, `s` y `t` son registros de 3 bits. Los bits sin uso se emiten en cero. `sext` significa extensión de signo.

| Familia | Bits 10..0 | Efecto |
|---|---|---|
| ALU registro | d[10:8], s[7:5], función[4:3], t[2:0] | Familia según opcode y función |
| ADD/AND inmediato | d[10:8], s[7:5], imm5[4:0] | Rd = Rs operación sext(imm5) |
| NOT | d[10:8], s[7:5], ceros[4:0] | Rd = NOT Rs |
| LD/ST/LDI/STI/LEA | d[10:8], desplazamiento[7:0] | Desplazamiento de 9 bits: el signo lo identifica el opcode |
| LDR/STR | d[10:8], s[7:5], desplazamiento[4:0] | Desplazamiento de 6 bits: el signo lo identifica el opcode |
| Bytes | d[10:8], s[7:5], off5[4:0] | Dirección = Rs + sext(off5), en bytes |
| BR condicional | NZP[10:8], off8[7:0] | Si coincide alguna condición: PC += 2 × sext(off8) |
| BRL/JSR | off11[10:0] | PC += 2 × sext(off11); JSR guarda antes R7 = PC |
| JMP/JSRR | 000[10:8], s[7:5], ceros[4:0] | PC = Rs; JSRR guarda antes R7 = PC |
| TRAP | ceros[10:8], vector8[7:0] | Transfiere al servicio del vector |
| RTI | ceros[10:0] | Recupera PC y PSR de la pila supervisora |

Alcances:

- Inmediato de ADD/AND: −16 a 15.
- LD/ST/LDI/STI/LEA: −256 a 255 **palabras** desde PC+2, equivalentes a −512 a 510 bytes.
- LDR/STR: −32 a 31 **palabras** desde el registro base, equivalentes a −64 a 62 bytes.
- LDBL/LDBH/STBL/STBH/LDBS: −16 a 15 **bytes** desde el registro base.
- BR condicional: −128 a 127 palabras desde PC+2. El ensamblador amplía automáticamente los saltos simbólicos lejanos a un BR inverso que salta un BRL. No usa registros auxiliares ni cambia NZP.
- BRL/JSR: −1024 a 1023 palabras desde PC+2. Fuera de alcance se usa una dirección en memoria y JMP/JSRR.

Las etiquetas representan direcciones **en bytes**. Los desplazamientos numéricos escritos en BR, LD y LDR se expresan en palabras. Es una elección del modo de direccionamiento; la memoria continúa siendo byte addressable.

## Semántica de memoria y condiciones

LD/LDR leen una palabra completa; ST/STR la escriben. LDI/STI leen primero el puntero de 16 bits y luego acceden a la dirección apuntada. LEA calcula la dirección sin leer datos y conserva NZP, siguiendo el comportamiento del prototipo de partida.

LDBL conserva los ocho bits altos de Rd y reemplaza los bajos. LDBH conserva los bajos y reemplaza los altos. STBL/STBH escriben un único byte y conservan el byte vecino. LDBS convierte x80 en xFF80 y x7F en x007F. ADD, AND, NOT y las cargas de datos actualizan NZP sobre el resultado completo de 16 bits. Los stores y los saltos no actualizan NZP.

RET es JMP R7. NOP se codifica como x0000: máscara de condiciones nula. BR sin condiciones escritas usa BRL. GETC, OUT, PUTS, IN, PUTSP y HALT son alias de TRAP x20–x25.

## Servicios y excepciones

Se conserva la convención del prototipo entregado: TRAP apila PC y PSR en modo supervisor y el servicio vuelve mediante RTI. **TRAP no usa R7 como enlace**; JSR/JSRR sí. El vector v está en la dirección byte 2 × v. Los servicios usan el sistema mínimo de `ejemplos/sistema.asm`, preensamblado al compilar; el núcleo no ensambla durante la ejecución.

R6 inicial de usuario: xFE00. Pila supervisora inicial: x3000. Cada elemento de pila ocupa dos bytes. Una llamada TRAP/interrupción apila cuatro bytes; RTI los recupera. Las rutinas de usuario con llamadas anidadas deben conservar R7 y los registros que su contrato exige.

La memoria del usuario va de x3000 a xFDFF con la protección predeterminada. KBSR=xFE00, KBDR=xFE02, DSR=xFE04, DDR=xFE06, PSR=xFFFC y MCR=xFFFE. Se admite interrupción de teclado en el vector x180, con prioridad 4. Los servicios supervisores acceden a E/S.

Excepciones: x100 por RTI en usuario, x101 por codificación reservada, x102 por acceso protegido y x103 por dirección impar para una palabra o instrucción. Las excepciones quedan registradas y el ejecutable devuelve código 4 aunque el manejador termine con HALT. Un byte puede tener dirección impar; una palabra, instrucción o destino de salto no.

## Objeto binario

Los dos primeros bytes contienen el origen big-endian. El resto es la imagen exacta de bytes que se copiará a memoria. No se añade un encabezado privado ni marcas de texto. Por ejemplo, `.ORIG x3000`, `ADD R0,R0,#1`, `HALT` produce los bytes:

```
30 00 10 01 98 25
```

El origen es par. El tamaño del contenido puede ser impar si termina con un dato byte. El cargador comprueba que la imagen entre en memoria y el núcleo valida el origen de ejecución. El archivo no guarda símbolos; el depurador conserva etiquetas solamente si abrió el fuente.

## Directivas y enlace

Se admiten `.ORIG`, `.END`, `.FILL`, `.BLKW` y `.STRINGZ`. `.BLKW` reserva palabras de dos bytes; `.STRINGZ` mantiene un carácter por palabra más el terminador cero para reutilizar los servicios de la calculadora. `.BYTE` emite un byte, `.BLKB` reserva bytes y `.ALIGN #2` alinea al siguiente límite de palabra.

Antes de instrucciones, `.FILL`, `.BLKW` o `.STRINGZ` se agrega automáticamente un byte cero si hace falta. Es relleno de alineación, **no una instrucción ejecutable de ocho bits**: todas las instrucciones de la ISA siguen teniendo 16 bits. El flujo debe saltar por encima de los datos intercalados.

`.EXTERNAL archivo-SIMBOLO` incorpora módulos recursivamente; el archivo principal establece `.ORIG`, los módulos lo omiten y todos cierran con `.END`. Se busca primero junto al archivo que importa y luego en los directorios `-I`. Un módulo se enlaza una sola vez por ruta; sus etiquetas locales se renombran para evitar colisiones. Se validan los símbolos exportados y se informa el archivo y la línea del error. En sistemas sensibles a mayúsculas, el nombre de archivo debe coincidir con su capitalización real. Las importaciones usan nombres simples de archivo, sin rutas, y pueden agregar `.asm` explícitamente.

No hay instrucciones matemáticas de EXP/SIN/SQRT dentro de la CPU: esas funciones se ejecutan como programas assembly del benchmark.

## Familias aritmeticas integradas

El opcode sigue siendo los cinco bits [15:11]. Los bits [4:3] seleccionan la suboperacion:

| Bits [4:3] | Opcode 1 | Opcode 3 | Opcode 31 |
|---|---|---|---|
| 00 | ADD Rd,Rs,Rt | AND Rd,Rs,Rt | SHL Rd,Rs,Rc |
| 01 | SUB Rd,Rs,Rt | DIVU Rd,Rs,Rt | SHR Rd,Rs,Rc |
| 10 | MUL Rd,Rs,Rt | CLZ Rd,Rs | SAR Rd,Rs,Rc |
| 11 | MULU Rd,Rs,Rt | MOV Rd,Rs | Reservado |

CLZ/MOV codifican t=0; otros valores en ese campo son ilegales. SHL/SHR/SAR toman el conteo de los cuatro bits bajos de Rc, rango 0..15. ASR se ensambla como SAR. Conteos 16,32,etc. se interpretan como cero. Estas instrucciones actualizan NZP sobre el resultado de 16 bits y no agregan C ni V.

SUB conserva la resta modulo 65536. MUL conserva los bits bajos del producto con signo (que coinciden con los bajos de la multiplicacion sin signo). MULU devuelve los bits 31..16 del producto sin signo. DIVU usa division sin signo y devuelve cero si el divisor es cero. CLZ(0)=16; MOV copia los 16 bits completos.

Las operaciones nuevas son de registros; no admiten inmediatos, salvo ADD/AND que conservan sus formatos previos de cinco bits. Las codificaciones canonicas anteriores de ADD/AND registro tenian [4:3]=00 y conservan su significado. Palabras que antes usaban bits no definidos pueden ahora significar otra operacion; las pruebas de opcode ilegal usan el submodo reservado de SHIFT.

Ejemplos de codificacion: SUB R0,R1,R2 = x082A; MUL = x0832; MULU = x083A; DIVU = x182A; CLZ R0,R1 = x1830; MOV R0,R1 = x1838. SHL R0,R1,R2 = xF822, SHR = xF82A, SAR = xF832.

Las nuevas operaciones se cuentan como instrucciones de la ISA. No se afirma que cada una requiera un unico ciclo de hardware: el modelo es funcional.
