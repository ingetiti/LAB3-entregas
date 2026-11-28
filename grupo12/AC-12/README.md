# Simulador y Ensamblador — Entrega Final TP3

Herramientas de ensamblado, ejecución por consola, interfaz gráfica y pruebas automatizadas junto con el programa de benchmark (`main_grupo27.asm` y su biblioteca `lib/`).

## Contenido de la entrega

- `ensamblador.py`: ensamblador de línea de comandos para archivos `.asm` / `.txt`.
- `CPU.py`: simulador independiente para ejecutar archivos de código máquina desde consola.
- `interfaz_isa.py`: interfaz gráfica de escritorio para editar, ensamblar y ejecutar programas.
- `test_simulador.py`: batería de pruebas automatizadas.
- `main_grupo27.asm` y `lib/`: código fuente del benchmark y sus módulos externos.
- `main_grupo27.hex`: versión ya ensamblada del benchmark lista para ejecutar.

## Requisitos

- **Python 3** (no requiere dependencias externas para el uso por consola).
- **`tkinter`** únicamente para abrir la interfaz gráfica (`interfaz_isa.py`).

---

## 1. Ensamblar desde consola (`ensamblador.py`)

Para ensamblar el benchmark completo (incluyendo los módulos de `lib/`):

```bash
python3 -B ensamblador.py main_grupo27.asm -o main_grupo27.hex
```

### Opciones disponibles

- `-o ARCHIVO`, `--output ARCHIVO`: ruta del archivo de salida (por defecto toma el nombre del archivo fuente con extensión `.hex` o `.bin`).
- `-f {hex,bin}`, `--format {hex,bin}`: formato de salida (`hex` por defecto, o `bin`).
- `-q N`, `--fractional-bits N`: cantidad de bits fraccionarios para literales decimales (`0` a `15`, por defecto `0`).

### Otros ejemplos

```bash
# Generar salida en formato binario
python3 -B ensamblador.py programa.asm -f bin -o programa.bin

# Ensamblar un programa con 4 bits fraccionarios
python3 -B ensamblador.py programa.asm -q 4 -o programa.hex
```

---

## 2. Ejecutar desde consola (`CPU.py`)

Para ejecutar el benchmark ya ensamblado:

```bash
python3 -B CPU.py main_grupo27.hex
```

### Opciones disponibles

- `-i TEXTO`, `--input TEXTO`: cadena de entrada opcional para programas que solicitan caracteres interactivos.
- `-m N`, `--max-instructions N`: límite máximo de instrucciones a ejecutar (por defecto `1000000`).

### Otros ejemplos

```bash
# Pasar entrada interactiva a un programa
python3 -B CPU.py programa.hex -i "AB"

# Ajustar el límite máximo de instrucciones
python3 -B CPU.py programa.hex -m 500000
```

Al finalizar la ejecución, `CPU.py` informa el motivo de detención, la cantidad de instrucciones ejecutadas, el uso de memoria, el estado final y la salida generada por el programa.

---

## 3. Interfaz gráfica (`interfaz_isa.py`)

Para iniciar la interfaz gráfica:

```bash
python3 -B interfaz_isa.py
```

### Uso básico

1. Hacé clic en **Abrir archivo** para cargar un programa (por ejemplo, `main_grupo27.asm`) o escribí el código directamente en el editor.
2. Si el programa utiliza valores decimales de punto fijo, seleccioná la precisión deseada en el selector superior.
3. Pulsá **Ensamblar** para generar el código máquina y verificar que no haya errores.
4. Pulsá **Ejecutar** para correr el programa y ver los resultados y métricas en el panel **EJECUCIÓN** (podés usar **Detener** para interrumpir una ejecución en curso).

## 4. Sintaxis de instrucciones de la ISA

| Instrucción | Sintaxis | Operación |
|---|---|---|
| `Resta modo registro` | `SUB DR, SR1, SR2` | `DR = SR1 - SR2` |
| `Resta modo inmediato` | `SUB DR, SR1, #imm` | `DR = SR1 - imm` (`imm` de 4 bits con signo, de `-8` a `7`) |
| `Multiplicación parte baja` | `MUL DR, SR1, SR2` | `DR` = 16 bits bajos del producto con signo `SR1 * SR2` |
| `Multiplicación parte alta` | `MULH DR, SR1, SR2` | `DR` = 16 bits altos del producto con signo `SR1 * SR2` |
 
Notas:
 
- `SUB` admite como tercer operando un registro o un inmediato. Un inmediato fuera de `-8..7` produce un error de ensamblado.
- `MUL` y `MULH` solo admiten registros. Si el tercer operando es un inmediato, el ensamblador informa `solo admite registros (no inmediatos)`.
- Para obtener el producto completo de 32 bits se usan las dos instrucciones con los mismos operandos de origen (`MULH` para la palabra alta y `MUL` para la baja).

### Desplazamientos de bits
 
| Instrucción | Sintaxis | Operación |
|---|---|---|
| `Shift a la izquierda` | `LSHF DR, SR, #n` | `DR = SR << n` (desplazamiento lógico a la izquierda) |
| `Shift lógico a la derecha` | `RSHFL DR, SR, #n` | `DR = SR >> n` (desplazamiento lógico a la derecha, rellena con ceros) |
| `Shift aritmético a la derecha` | `RSHFA DR, SR, #n` | `DR = SR >> n` (desplazamiento aritmético a la derecha, conserva el signo) |
 
- La cantidad `n` es un inmediato de `0` a `15`; fuera de ese rango el ensamblador informa un error. No existe la forma con registro.

### Acceso a memoria por bytes
 
| Instrucción | Sintaxis | Operación |
|---|---|---|
| `Load byte bajo` | `LDB DR, BaseR, #offset` | `DR` = byte bajo de la palabra, con extensión de signo |
| `Load byte alto` | `LDH DR, BaseR, #offset` | `DR` = byte alto de la palabra, con extensión de signo |
| `Store byte bajo` | `STB SR, BaseR, #offset` | guarda el byte bajo de `SR` en el byte bajo de la palabra |
| `Store byte alto` | `STH SR, BaseR, #offset` | guarda el byte alto de `SR` en el byte alto de la palabra |
 
- `BaseR` contiene una dirección de palabra (se multiplica por 2 para obtener la dirección de byte) y `offset` se suma en bytes. Es un inmediato con signo de 5 bits, de `-16` a `15`; fuera de ese rango el ensamblador informa un error.
- La carga y el guardado de 16 bits siguen siendo `LDR` y `STR` (`LDR DR, BaseR, #offset`, `STR SR, BaseR, #offset`), cuyo offset se cuenta en palabras. Si el offset no entra en `-16..15`, el ensamblador usa automáticamente las formas extendidas `LDRX` y `STRX` con offset de 16 bits.

## 5. Pruebas automatizadas (`test_simulador.py`)

Para verificar el funcionamiento del ensamblador, el simulador y el benchmark completo:

```bash
python3 -B test_simulador.py
```
