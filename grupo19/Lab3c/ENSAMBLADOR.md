# Ensamblador de la nueva ISA

`assembler.py` recibe código fuente de la ISA descrita en [NUEVA_ISA.md](./NUEVA_ISA.md), resuelve `.EXTERNAL` recursivamente y genera un objeto o listado enlazado. El ensamblador es independiente del simulador y utiliza solamente la biblioteca estándar de Python.

## Uso

```powershell
python assembler.py programa.asm
python assembler.py programa.asm --format bin -o programa.bin
python assembler.py programa.asm --format hex -o programa.hex
python assembler.py programa.asm --format asm -o programa_listado.asm
python assembler.py programa.asm -f bin -I biblioteca
```

`--format` (`-f`) acepta:

- `bin`: objeto binario. Los primeros dos bytes son `.ORIG` en little-endian; los siguientes dos son el valor inicial de `.STACK` (por defecto `xFFFE`); el resto es la imagen enlazada desde `.ORIG`.
- `hex`: los mismos bytes del objeto binario, representados como pares hexadecimales separados por espacios. Se conserva el orden exacto del archivo binario, incluido el encabezado.
- `asm`: listado legible del programa enlazado. Muestra direcciones byte, bytes emitidos, el módulo de origen y las líneas de la ISA nueva; no es un archivo de entrada reensamblable.

Sin `-o`, la salida queda junto al fuente y usa su nombre base con extensión `.bin`, `.hex` o `.asm`. `-I DIR` puede repetirse para buscar módulos externos.

## Fuentes y enlazado

- Cada archivo raíz debe declarar exactamente un `.ORIG xNNNN`, con dirección par.
- `.EXTERNAL archivo-SIMBOLO` busca `archivo.asm` junto al fuente, en una carpeta `lib` o en las rutas `-I`. Las etiquetas se mantienen locales a cada módulo; el símbolo importado se puede referenciar por su nombre.
- Los `.ORIG` de módulos importados no cambian su ubicación: el enlazador los ubica después del módulo que los importa.
- Las instrucciones y los datos de palabra se alinean a direcciones pares. Se inserta un byte `00` cuando un dato de byte deja desalineada la siguiente instrucción o palabra.
- `.FILL` y `.BLKW` contienen palabras little-endian; `.BYTE`, `.BLKB` y `.STRINGZ` contienen bytes. `.STRINGZ` agrega NUL y acepta caracteres Latin-1.
- `.STACK xNNNN` configura el SP inicial guardado en el encabezado del objeto.

Se admiten las instrucciones y pseudo-operaciones de `NUEVA_ISA.md`, incluyendo `.ORIG`, `.END`, `.EXTERNAL`, `.FILL`, `.BLKW`, `.BLKB`, `.BYTE`, `.STRINGZ`, `.STACK`, instrucciones de carga/almacenamiento, ramas, ALU, pila, TRAP y alias como `LI`, `MOV`, `CLR`, `INC`, `DEC`, `PUSH`, `POP` y `NOP`. Los desplazamientos de ramas y cargas PC-relativas que exceden el alcance corto se relajan automáticamente a secuencias indirectas cuando la ISA lo permite; los valores que no caben en un campo se reportan como error, no se truncan.

## Pruebas

```powershell
python -m unittest -v test_assembler
```

## Ejecutar un objeto

El ensamblador produce objetos que se ejecutan con `simulator.py`. El simulador
solo acepta `.bin`, `.obj` o `.hex` (representacion hexadecimal del mismo
objeto); no acepta archivos ASM.

```powershell
python assembler.py programa.asm -o programa.bin -I biblioteca
python simulator.py programa.bin
```
