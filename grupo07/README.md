# Grupo 07 · Máximo Común Divisor (MCD) + Mínimo Común Múltiplo (MCM)

**Consigna:** Desarrollar un programa en lenguaje ensamblador LC-3 que calcule el máximo común divisor (MCD) y el mínimo común múltiplo (MCM), ambos de dos enteros.

## Integrantes
- Zabala, Álvaro Martín (@alvaromartinzabala-ing)
- Behr, Pedro Sebastián (@pedrobehr21-source)

---

## Archivos del Repositorio
- `README.md`: instrucciones breves, integrantes y descripción general del proyecto.

### lab3_a
- `programa.c`: solicita los números, realiza las conversiones Q y calcula las operaciones.
- `p3.asm`: convierte y alinea el valor Q7.8 para realizar la suma en Q3.12.
- `p4.asm`: implementa la multiplicación y el ajuste del resultado en ensamblador LC-3.

### lab3_b
- `mcd.asm`: módulo de la calculadora. Subrutina `MCD`, que calcula el máximo común divisor por restas sucesivas (Euclides).
- `mcm.asm`: módulo de la calculadora. Subrutina `MCM`, que calcula el mínimo común múltiplo (Euclides, cociente por restas sucesivas y multiplicación por sumas sucesivas). Tiene su propio Euclides y no llama al módulo `MCD`.
- `mcd_mcm_v3.asm`: programa autónomo e interactivo del que derivan los dos módulos. Lee dos enteros con signo por consola y muestra el MCD y el MCM.
- `mainv3.c`: programa en C con el modelo matemático de referencia en Q15.0, un simulador funcional de la LC-3 y un banco de pruebas (`--test`) con 63.750 casos.
- `informe_lab3_MCD_MCM.pdf`: informe con rangos, estado de simulación y bitácora.

---

## Estado en el simulador

Los módulos `mcd.asm` y `mcm.asm` funcionan en el simulador web del grupo 8 (https://lc3.lgrum.xyz/), integrados al menú de la calculadora del grupo 27. El programa autónomo `mcd_mcm_v3.asm` también se probó en otros simuladores de la LC-3.

---

## Especificaciones para verificación (formato punto fijo, rangos y precisión)

El algoritmo opera con divisores y múltiplos enteros, usando sumas y restas sucesivas.

| Parámetro | Especificación adoptada | Justificación técnica |
| :--- | :--- | :--- |
| **Formato de punto fijo** | **Q15.0** (complemento a 2, 16 bits) | 1 bit de signo y 15 bits de magnitud entera; 0 bits fraccionarios. |
| **Rango de entrada ($A, B$)** | **$[-32767, 32767]$** (`x8001` a `x7FFF`) | Se excluye `-32768` (`x8000`) porque su valor absoluto (`+32768`) no es representable en complemento a dos de 16 bits. Esa entrada no se valida. |
| **Rango de salida (MCD)** | **$[0, 32767]$** | Nunca desborda: el MCD es menor o igual que $\max(\vert{}A\vert{}, \vert{}B\vert{}) \le 32767$. Se cumple $\text{MCD}(0, B) = \vert{}B\vert{}$ y $\text{MCD}(0, 0) = 0$. |
| **Rango de salida (MCM)** | **$[0, 32767]$** (exacto) | Si el MCM real supera `32767` (*overflow*), el bucle corta de inmediato y devuelve el valor centinela **`-32768` (`x8000`)** como aviso. Si alguna entrada es 0, el MCM es 0. |
| **Precisión (mín. y máx.)** | **Exacta** (resolución $2^0 = 1$, error $= 0$) | No hay truncamiento ni redondeo, porque $\min(\vert{}A\vert{}, \vert{}B\vert{}) / \text{MCD}$ es siempre una división entera exacta. |

---

## Módulos de la calculadora

### Uso
- Entrada: R0 = a, R1 = b (enteros con signo, Q15.0).
- Salida: R0 = resultado. `MCD` devuelve MCD(|a|, |b|) y `MCM` devuelve MCM(|a|, |b|), o `x8000` si el MCM real no entra en 16 bits.
- `MCD` conserva R1 a R3 y `MCM` conserva R1 a R5. R6 y R7 no se tocan.
- Los registros se guardan en memoria con `ST` y `LD`, no en la pila, por lo que los módulos no son reentrantes.
- Los archivos no llevan `.ORIG` y terminan con `.END`.

### Conexión con el menú
En `main_menu.asm` se declaran las etiquetas externas con el formato `MODULO-ETIQUETA` y se cargan en la tabla de subrutinas con `.FILL`:

```asm
        .EXTERNAL MCD-MCD
        .EXTERNAL MCM-MCM

main_menu_sub_mcd           .FILL MCD-MCD
main_menu_sub_mcm           .FILL MCM-MCM
```

### Casos probados
Resultados calculados a mano y verificados en el menú.

| A | B | MCD | MCM |
| :--- | :--- | :--- | :--- |
| 48 | 180 | 12 | 720 |
| -84 | 36 | 12 | 252 |
| 0 | -25 | 25 | 0 |
| 217 | 4681 | 31 | 32767 |
| 1000 | 999 | 1 | -32768 (overflow) |

### Incidente de integración
Al integrar con los archivos de `val_io` del grupo 27 apareció el error `LEA GETVAL_BUFFER-BUFFER: target x3A46 is 291 words away, LEA reaches ±256`. `LEA` solo alcanza ±256 palabras y la distancia al buffer creció al sumar módulos. El grupo 27 lo resolvió en su `main`, reemplazando `LEA` por `LD` con `.FILL`. No era un problema de nuestros módulos.

---

## Limitaciones
- La entrada `-32768` no se valida.
- El valor `x8000` del MCM es ambiguo con un MCM real de 32768, que tampoco entra en Q15.0. Siempre se interpreta como aviso de overflow.
- Quien llama a los módulos debe pasar enteros Q15.0.
- Euclides por restas necesita del orden de max(|A|, |B|) pasos. El peor caso (32767 y 1) tarda unas 98.000 instrucciones.

---

### Para probar `mainv3.c`
1. `gcc -O2 mainv3.c -o mainv3`
2. `./mainv3` (modo interactivo, muestra iteraciones e instrucciones por opcode)
3. `./mainv3 --test` (ejecuta las 63.750 pruebas)

### Para probar `mcd_mcm_v3.asm`
1. Abrir `mcd_mcm_v3.asm` en el simulador de LC-3.
2. Ensamblar el programa. *(Si el simulador no inicializa el puntero de pila `R6`, descomentar la primera instrucción `LD R6, STACK_BASE`.)*
3. Ejecutar desde `x3000`.
4. Ingresar los dos enteros en el rango `[-32767, 32767]`, uno por línea:

```text
Ingresa el primer numero: 12
Ingresa el segundo numero: 18
MCD = 6
MCM = 36
```

### Para probar los módulos
Cargar `mcd.asm`, `mcm.asm` y un `main.asm` en el simulador del grupo 8 y marcar el `main.asm` como entrada. Declarar `.EXTERNAL MCD-MCD` y `.EXTERNAL MCM-MCM`, cargar `a` en R0 y `b` en R1, y llamar con `LD R5, <puntero>` y `JSRR R5`, donde el puntero es una palabra `.FILL MCD-MCD` (o `.FILL MCM-MCM`). El resultado queda en R0.
