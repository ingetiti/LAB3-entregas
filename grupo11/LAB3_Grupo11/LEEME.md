# Grupo 11 · Simulador, ensamblador y benchmark (instructivo de uso)

Morinigo · Kelm · Gomez — Arquitectura de Computadoras, Laboratorio 3.

Herramientas en Python para ensamblar y ejecutar programas de la ISA del grupo 11, junto con el **benchmark de la
cátedra ya ensamblado** para este simulador. No hace falta instalar nada: solo **Python 3.10 o superior**.

## Contenido

| Archivo / carpeta | Para qué sirve |
| --- | --- |
| `simulador.py` | Simulador funcional: carga un programa ensamblado, lo ejecuta y muestra la salida, las instrucciones ejecutadas y el uso de memoria |
| `ensamblador.py` | Ensamblador y enlazador: archivos `.asm` → `.bin` / `.hex` / `.dec` |
| `gui.py` / `abrir_gui.bat` | Interfaz gráfica para correr el benchmark y contar las instrucciones (usuario + sistema operativo) |
| `isa.py`, `costo_so.py` | Módulos que usan los programas de arriba (no se ejecutan solos) |
| `benchmark/main_grupo27.asm` + `benchmark/lib/*.asm` | **Los `.asm` del benchmark** (programa principal + 37 módulos) |
| `benchmark/benchmark_g11.bin/.hex/.dec` | **El benchmark ensamblado**, listo para correr |
| `benchmark/main_menu.asm`, `benchmark/menu_g11.*` | La calculadora del benchmark en modo interactivo (menú por teclado) |
| `benchmark/salida_esperada.txt` | Salida del benchmark original en la LC-3, para comparar |
| `ejemplos/hola.asm` | Programa mínimo de ejemplo |

Todos los comandos se escriben desde esta carpeta. En Windows puede hacer falta `py` en lugar de `python`.

## 1. Correr el benchmark

```
python simulador.py benchmark/benchmark_g11.hex
```

Muestra por pantalla lo mismo que el benchmark original (reducción de argumento, senos, coseno, bases, raíces,
exponencial, potencias, multiplicaciones, divisiones, logaritmos, MCD, MCM y conversión Q). Al final muestra el
resumen: motivo de parada, instrucciones ejecutadas (total y por clase), memoria y servicios usados.

Resultado esperado: parada `HALT` y **135.633 instrucciones**. Con `--so` se agrega la estimación de las
instrucciones del sistema operativo (ver la sección 2): **135.633 + 22.074 = 157.707**. La LC-3 de la cátedra da
357.505 + 22.074 = 379.579.

Para comprobar que la salida es la misma que la del benchmark original:

```
python simulador.py benchmark/benchmark_g11.hex --silencio > salida.txt
fc salida.txt benchmark\salida_esperada.txt          (Windows)
diff salida.txt benchmark/salida_esperada.txt        (Linux / Mac)
```

Para volver a ensamblar el benchmark desde los `.asm`:

```
python ensamblador.py benchmark/main_grupo27.asm --lib benchmark/lib -o benchmark/benchmark_g11 --formato bin hex dec
```

## 2. Interfaz gráfica

```
python gui.py            (en Windows también: doble clic en abrir_gui.bat)
```

Se abre con el benchmark ya cargado. Con **Ejecutar benchmark** (o `F5`) lo corre y muestra:

- el total de instrucciones (usuario + sistema operativo);
- la comparación con la LC-3 de la cátedra;
- las instrucciones por clase;
- los servicios usados y la memoria;
- la salida del programa.

Otros controles:

- **Abrir programa…** carga otro `.hex`, `.bin`, `.dec`, o un `.asm` principal, que se ensambla buscando sus
  módulos en la misma carpeta y en `lib/`.
- **Guardar informe** exporta los resultados.
- `Esc` detiene una ejecución.
- El cuadro **Teclado** es el texto que el programa va a leer cuando pida caracteres.

La interfaz usa `tkinter`. Viene incluido en el instalador de Python para Windows y macOS; en Linux se instala con
`sudo apt install python3-tk`.

**Instrucciones del sistema operativo.** En este simulador, cada servicio del sistema (leer un carácter, escribir
un carácter o una cadena, terminar) cuenta como 1 instrucción, y el código del sistema operativo no se simula. La
cátedra informó la LC-3 como *usuario + SO*, así que se estima el SO a partir de lo que sí se mide: cuántas veces
se llamó a cada servicio y cuántos caracteres se imprimieron. El modelo por defecto está calibrado para dar los
22.074 de la cátedra con la secuencia de servicios del benchmark. Es una estimación: los coeficientes se editan en
*Editar coeficientes…*, y el modelo «Nativo» deja el SO en 0.

## 3. Calculadora interactiva (menú por teclado)

`benchmark_g11.hex` ejecuta el bloque automático de operaciones. Para usar la calculadora con datos propios:

```
python simulador.py benchmark/menu_g11.hex
```

Se elige la opción con su tecla y se escriben los operandos terminando con Enter. Después de cada resultado hay que
pulsar una tecla, y `d` sale del programa.

| Tecla | Operación |
| --- | --- |
| `0` | Reducción de argumento |
| `1` | Seno: `0` Taylor, `1` tabla, `2` Chebyshev-Padé |
| `2` | Coseno |
| `3` | Base: `0` hexadecimal, `1` binario |
| `4` | Raíz cuadrada: `0` non-restoring, `1` Newton-Raphson |
| `5` | Exponencial |
| `6` | Potencia: `0` multiplicaciones sucesivas, `1` exponenciación binaria |
| `7` | Multiplicación: `0` CORDIC, `1` básica, `2` Booth |
| `8` | División: `0` larga, `1` Newton-Raphson, `2` CORDIC |
| `9` | Logaritmo: `0` Borchardt, `1` CORDIC |
| `a` / `b` | MCD / MCM |
| `c` | Conversión Q3.12 → Q7.8 |

También se puede pasar la sesión escrita de antemano, por ejemplo el MCD de 12 y 18:

```
python simulador.py benchmark/menu_g11.hex --entrada "a12\n18\n \nd"
```

Para volver a ensamblarla:

```
python ensamblador.py benchmark/main_menu.asm --lib benchmark/lib -o benchmark/menu_g11 --formato bin hex dec
```

## 4. Ensamblar

```
python ensamblador.py principal.asm [modulo1.asm modulo2.asm ...] -o salida
                      [--lib CARPETA] [--formato bin hex dec] [--lst]
```

* El **primer archivo** es el programa principal (lleva `.ORIG`). Los demás son módulos (subrutinas), que se ubican
  a continuación.
* `--lib CARPETA` busca automáticamente los módulos que el programa pida con `.EXTERNAL`. La opción se puede
  repetir para indicar varias carpetas.
* Por defecto genera `salida.bin` y `salida.hex`. Con `--formato` se elige cualquier combinación de `bin`, `hex` y
  `dec`.
* Con `--lst` se agregan `salida.lst` (listado con direcciones y código) y `salida.sym` (tabla de símbolos).
* **Formato de salida:** el primer dato es la dirección de origen (los 2 primeros bytes en `.bin`, la primera línea
  en `.hex` y `.dec`). Después siguen las palabras de 16 bits.
* Al terminar informa el tamaño del programa módulo por módulo.
* Si hay un error, muestra el archivo y la línea, y termina con código 1.

Ejemplo:

```
python ensamblador.py ejemplos/hola.asm -o ejemplos/hola
python simulador.py ejemplos/hola.hex
```

### Escritura de los `.asm`

* Comentarios con `;`.
* Etiquetas al principio de la línea, opcionalmente con `:`. Una etiqueta que se llame igual que un mnemónico debe
  llevar `:`.
* Mayúsculas y minúsculas son equivalentes.
* Números: `#10`, `#-3`, `x3000`, `0x3000`, `0b101`, `'A'`.
* Directivas: `.ORIG`, `.END`, `.FILL`, `.FILLB`, `.BLKW n`, `.BLKB n`, `.STRINGZ "texto"`, `.STRINGW "texto"`,
  `.ALIGN n`, `.EXTERNAL MODULO-ETIQUETA`.
* **Módulos:** el nombre de un módulo es el de su archivo, sin extensión y en mayúsculas (`g7_mcd.asm` →
  `G7_MCD`). Desde otro archivo, una etiqueta se usa como `MODULO-ETIQUETA`, declarada antes con `.EXTERNAL`
  (ver `benchmark/main_grupo27.asm`).

## 5. Ejecutar

```
python simulador.py programa.bin|.hex|.dec [opciones]
```

| Opción | Efecto |
| --- | --- |
| `--max-instr N` | Corta después de N instrucciones (por defecto 50.000.000) |
| `--entrada "texto"` / `--entrada-archivo F` | Datos que va a leer el programa del teclado (`\n` = Enter) |
| `--so` | Agrega al resumen la estimación de instrucciones del sistema operativo |
| `--traza` | Muestra cada instrucción ejecutada |
| `--regs` | Muestra los registros al terminar |
| `--volcado DIR N` | Muestra N palabras de memoria desde la dirección DIR |
| `--json F` | Guarda las estadísticas en un archivo JSON |
| `--perfil F` | Guarda cuántas veces se ejecutó cada dirección (JSON) |
| `--silencio` | No muestra el resumen |

La salida del programa va por la salida estándar y el resumen por la de errores. Códigos de salida:

| Código | Significado |
| --- | --- |
| `0` | Terminó con `HALT` |
| `2` | Paró por una excepción o por el límite de instrucciones |
| `1` | No pudo cargar el archivo |

Si el programa pide un carácter y no queda entrada, recibe un Enter.
