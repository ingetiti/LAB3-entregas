# Grupo 18 · Multiplicación

**Consigna:** Algoritmo de Booth

Arquitectura de Computadoras · Facultad de Ingeniería, Universidad Nacional de Misiones.

Multiplicador de números con signo en punto fijo **Q7.8** mediante el **algoritmo de Booth de 16 iteraciones**, escrito en assembly LC-3.

El trabajo tiene **dos presentaciones del mismo algoritmo**:

1. **Programa independiente** (`BOOTH16v3.ASM`): pide los números por teclado, los convierte a Q7.8, multiplica con Booth e imprime los resultados.
2. **Módulo para la calculadora de la cátedra** (`booth.asm`): sin teclado ni pantalla. Recibe los operandos **ya en Q7.8 por registros** (R0 y R1) y devuelve el resultado Q7.8 en R0, siguiendo la guía de módulos (convención de llamada, pila con R6, enlace con `.EXTERNAL`).

## Integrantes


 - Borges Nogueira, Elías Martin (@martinbng)
 - Gregorchuk, Franco Aimar
 - Olivera, Gabriel 


## Archivos

- `BOOTH16v3.ASM`: programa completo en assembly LC-3 (captura por teclado, conversión decimal → Q7.8, Booth de 16 iteraciones, conversión del producto a Q7.8, detección de overflow e impresión de resultados). Es el mismo archivo que se subió al simulador del grupo 8 (ver sección 2).
- `booth.asm`: **módulo para la calculadora** (nombre del módulo `booth`, función pública `MULT_BOOTH`). Es el archivo que se publica en la plataforma. Sin `.ORIG`, termina con `RET` y con `.END`.
- `main.asm`: programa principal de **prueba local** del módulo (`.ORIG x3000`, `.EXTERNAL BOOTH-MULT_BOOTH`, llamada con `.FILL` + `JSRR`).
- `proyecto_completo.asm`: versión **integrada en un solo archivo** (principal con autoverificación + módulo) para simuladores que no enlazan módulos.
- `README.md`: este documento.

## Cómo probarlo

### A. Programa independiente (`BOOTH16v3.ASM`, por teclado)

1. Abrir el simulador del grupo 8: <https://lc3.lgrum.xyz/> (o cualquier simulador LC-3 que soporte `TRAP x20`/`x21`/`x25`).
2. Cargar `BOOTH16v3.ASM` (origen `.ORIG x3000`) y ensamblar.
3. Ejecutar. El programa pide dos números por teclado y termina cada uno con ENTER:

   ```
   Ingrese el primer numero:
   Ingrese el segundo numero:
   ```

4. Si algún dato es inválido, el programa informa el error y **vuelve a pedir ese mismo dato**.
5. Al final muestra la pantalla de resultados: X e Y ingresados, X e Y en Q7.8 (hex), producto `PH:PL` (hex y decimal), resultado Q7.8 (hex y decimal) y `Overflow` (0/1).

**Para depurar con breakpoint:** poner un breakpoint en la etiqueta `FIN` (instrucción `TRAP x25`). Al llegar, los registros contienen:

| Registro | Contenido |
|---|---|
| R0 | PH (palabra alta del producto de 32 bits) |
| R1 | PL (palabra baja del producto de 32 bits) |
| R2 | RES (resultado Q7.8 = P[23:8]) |
| R3 | OVF (0 = sin desbordamiento, 1 = desbordamiento) |
| R4:R5 | producto completo de 32 bits |

**Variables de configuración** (`.FILL` dentro del archivo):

| Variable | Valor | Efecto |
|---|---|---|
| `DBGFLAG` | `#0` (por defecto) / `#1` | `#1` agrega el eco de lo leído y la línea de conversión de cada dato |
| `PRFLAG` | `#1` (por defecto) / `#0` | `#0` no imprime nada en consola; solo deja los registros indicados arriba |
| `KBPOLL` | `#0` (por defecto) / `#1` | `#0` lee con `TRAP x20` (GETC); `#1` lee por sondeo de KBSR/KBDR |

### B. Módulo para la calculadora (`booth.asm`, por registros)

1. En la plataforma, crear los archivos `booth.asm` y `main.asm` con el contenido de este repositorio.
2. Clic derecho sobre `main.asm` → **Usar como entrada** → **Ensamblar**. Los errores aparecen en la pestaña *Problemas* y la ubicación de cada módulo en *Mapa de enlace*.
3. Ejecutar. Al terminar (`HALT`), la posición `RESULTADO` de `main.asm` debe valer `x2EE0` (12,5 × 3,75 = 46,875). Para otros casos, cambiar `OP_X` y `OP_Y` (ver tabla 1.4).
4. Opcional, en un simulador que no enlaza módulos: cargar `proyecto_completo.asm`. Recorre 13 casos y, al llegar a `HALT`, la posición `FALLAS` vale `0` si todos pasaron. Cada fila de `TABLA` deja a la derecha lo obtenido (RES, PH, PL, OVF).
5. Para entregar: abrir `booth.asm` en la plataforma e iniciar sesión con el número de grupo y la contraseña o token asignado. Luego, clic en **Publicar**. El servidor ensambla primero el archivo y no publica código con errores. Los profesores lo llamarán `G18_BOOTH-MULT_BOOTH`.

---

## 1. Qué se pide para verificar el funcionamiento

### 1.1 Formato de punto fijo

- **Operandos: Q7.8**, 16 bits en complemento a dos: 1 bit de signo, 7 bits enteros, 8 bits fraccionarios.
- **Valor real = entero almacenado / 2⁸ (256).** Ejemplo: 12,5 × 256 = 3200 = `x0C80`.
- **Producto completo: Q15.16** en 32 bits, dividido en dos palabras `PH:PL`. **Producto real = entero de 32 bits / 2¹⁶ (65536).**
- **Resultado reducido: Q7.8**, `RES = P[23:8]`, es decir, desplazamiento aritmético de 8 posiciones a la derecha del producto de 32 bits (equivale a dividir por 256).

### 1.2 Rango de los valores de entrada

| Característica | Valor |
|---|---|
| Rango representable en Q7.8 | de −128 a 127,99609375 (`x8000` a `x7FFF`) |
| Resolución | 1/256 = 0,00390625 |
| Sintaxis aceptada por teclado | `[+\|-]` parte entera `[.` uno o dos decimales`]`, sin espacios. Ejemplos: `12.5`, `-3.75`, `+7`, `0.25` |
| Separador decimal | punto (`.`) |
| Longitud máxima de la línea | 15 caracteres |
| Cifras decimales | hasta 2 |
| Mayor valor ingresable | `127.99` (`x7FFD`) |
| Menor valor ingresable | `-128` o `-128.00` (`x8000`) |

Reglas de conversión decimal → Q7.8: `valor = parte_entera × 256 + floor(decimales_2_cifras × 256 / 100)`, truncado hacia cero, y se niega al final si hay signo `-`. Con un solo decimal, `5` equivale a `50` (por ejemplo `3.5` se toma como `3.50`). Por eso un decimal ingresado puede no coincidir exactamente con el valor almacenado.

Errores de entrada (el programa vuelve a pedir el dato):

| Error | Mensaje | Ejemplos |
|---|---|---|
| Entrada inválida | `ERROR: entrada invalida (formato: [+-]E[.D[D]])` | `abc`, `5.`, `.5`, `-`, `1.2.3` |
| Fuera de rango | `ERROR: fuera de rango (-128 a 127.99609375)` | `128`, `128.5`, `-128.01`, `300` |
| Más de dos decimales | `ERROR: mas de dos decimales` | `1.234` |
| Línea demasiado larga | `ERROR: entrada demasiado larga (maximo 15 caracteres)` | más de 15 caracteres tecleados |

### 1.3 Rango de las salidas

| Salida | Formato | Rango / significado |
|---|---|---|
| `PH:PL` | Q15.16, 32 bits con signo | Con operandos Q7.8 el producto está entre −16383,5 y 16384; resolución 1/65536 |
| `RES` | Q7.8, 16 bits | Válido solo si `OVF = 0`: producto entre −128 y 127,99609375 |
| `OVF` | indicador | `0` = representable; `1` = el producto no entra en Q7.8 |

- **Criterio de overflow:** `OVF = 1` si `PH` está fuera de [−128, 127]. Se calcula como `((PH + x0080) AND xFF00) != 0`.
- Con `OVF = 1` el producto de 32 bits sigue siendo correcto; lo que no se puede es representarlo en 16 bits Q7.8. En ese caso el programa muestra `** OVERFLOW: no representable en Q7.8 **` en lugar del decimal de `RES`.
- El desplazamiento aritmético **trunca hacia −∞**, algo a tener en cuenta con productos negativos no exactos.

### 1.4 Casos de prueba esperados

Valores **calculados matemáticamente** (producto de enteros con signo; `PH:PL` = producto de 32 bits; `RES` = P[23:8]). Los primeros siete corresponden a los ejemplos del informe; el resto son casos límite, de signos y de truncamiento agregados. Son los mismos 13 casos que recorre `proyecto_completo.asm`. No son capturas de ejecución en la plataforma.

| Operación | X | Y | PH | PL | RES (hex) | RES (dec) | OVF |
|---|---|---|---|---|---|---|---|
| 12,5 × 3,75 | `x0C80` | `x03C0` | `x002E` | `xE000` | `x2EE0` | 46,875 | 0 |
| 1 × 2 | `x0100` | `x0200` | `x0002` | `x0000` | `x0200` | 2 | 0 |
| −3,75 × 2 | `xFC40` | `x0200` | `xFFF8` | `x8000` | `xF880` | −7,5 | 0 |
| 0 × 5 | `x0000` | `x0500` | `x0000` | `x0000` | `x0000` | 0 | 0 |
| 100 × 2 | `x6400` | `x0200` | `x00C8` | `x0000` | `xC800` | no representable (producto = 200) | 1 |
| 64 × 2 | `x4000` | `x0200` | `x0080` | `x0000` | `x8000` | no representable (producto = 128) | 1 |
| −100 × 2 | `x9C00` | `x0200` | `xFF38` | `x0000` | `x3800` | no representable (producto = −200) | 1 |
| −128 × 1 *(límite)* | `x8000` | `x0100` | `xFF80` | `x0000` | `x8000` | −128 | 0 |
| −128 × −128 *(límite)* | `x8000` | `x8000` | `x4000` | `x0000` | `x0000` | no representable (producto = 16384) | 1 |
| −3,75 × −2 | `xFC40` | `xFE00` | `x0007` | `x8000` | `x0780` | 7,5 | 0 |
| 127,99609375 × 1 *(límite)* | `x7FFF` | `x0100` | `x007F` | `xFF00` | `x7FFF` | 127,99609375 | 0 |
| 0,5 × 0,5 | `x0080` | `x0080` | `x0000` | `x4000` | `x0040` | 0,25 | 0 |
| −1/256 × 1/256 *(truncamiento)* | `xFFFF` | `x0001` | `xFFFF` | `xFFFF` | `xFFFF` | −1/256 (trunca hacia −∞) | 0 |

### 1.5 Interfaz del módulo `MULT_BOOTH` (calculadora)

En el módulo los operandos **no se escriben ni se convierten**: llegan ya en Q7.8 por registros. Por eso la sintaxis y los errores de entrada de la sección 1.2 se aplican solo al programa independiente. En el módulo es válida cualquier palabra de 16 bits (`x8000` a `x7FFF`, es decir −128 a 127,99609375).

| Concepto | Detalle |
|---|---|
| Archivo / módulo | `booth.asm` / `booth` |
| Etiqueta pública | `MULT_BOOTH` (se importa como `BOOTH-MULT_BOOTH`) |
| Entrada | `R0` = X, `R1` = Y, ambos Q7.8 con signo (complemento a dos) |
| Salida | `R0` = RES = P[23:8], resultado en Q7.8 |
| Registros conservados | `R1`, `R2`, `R3`, `R4`, `R5` (se apilan y se restauran) |
| `R6` | puntero de pila: vuelve con el mismo valor que tenía al entrar; no se inicializa ni se usa como registro de trabajo |
| `R7` | se apila al entrar (las `JSR` internas a `SHR1`/`ASR1` lo sobrescriben) y se restaura antes de `RET` |
| Registro modificado | `R0` (es el resultado). Los códigos de condición reflejan el signo de RES |
| Retorno | `RET` |
| Datos auxiliares (solo diagnóstico, **no son interfaz**) | `PH`, `PL` (producto de 32 bits), `RES`, `OVFV` (0 = sin desbordamiento, 1 = desbordamiento) |

**Marco de pila** (la pila crece hacia direcciones menores; 7 palabras): `R6+0` = R1, `+1` = R2, `+2` = R3, `+3` = R4, `+4` = R5, `+5` = R7, `+6` = contador del bucle. Antes de volver se desapila todo.

**Llamada desde el programa principal** (siempre con `.FILL` + `JSRR`, porque `JSR` solo alcanza ±1024 palabras):

```asm
        .EXTERNAL BOOTH-MULT_BOOTH
        LD   R0, OP_X               ; X en Q7.8
        LD   R1, OP_Y               ; Y en Q7.8
        LD   R5, BOOTH_PTR
        JSRR R5                     ; R0 = RES
        ...
BOOTH_PTR .FILL BOOTH-MULT_BOOTH
```

**Limitaciones del módulo:**

- La interfaz oficial devuelve solo RES en `R0`. **No informa el desbordamiento:** con `OVF = 1`, el valor de `R0` es P[23:8] truncado y no representa el producto (por ejemplo 100 × 2 devuelve `xC800`). `OVFV`, `PH` y `PL` quedan en memoria del módulo solo para depuración.
- No es reentrante: sus datos internos (`MCAND`, `MNEG`, `QM1`, `Q0SAVE`, `PH`, `PL`, `RES`, `OVFV`) son fijos.
- Cada llamada ejecuta unas 5300 a 5900 instrucciones, porque los desplazamientos se hacen por software (`SHR1`/`ASR1`).

---

## 2. Assembly subido al simulador

### 2.1 Programa independiente: `BOOTH16v3.ASM`

Contenido completo de `BOOTH16v3.ASM` (1744 líneas). Hacer clic para desplegar.

<details>
<summary><code>BOOTH16v3.ASM</code></summary>

```asm
;====================================================================
; BOOTH16_PRESENTACION.ASM - Booth 16x16 en Q7.8: version con salida ordenada (Etapa 4)
; DBGFLAG = 0 (normal): pide dos numeros, informa solo los errores y muestra la pantalla de
;   resultados. DBGFLAG = 1: ademas muestra el eco de LEELIN y la conversion de cada dato.
; ETAPA 1 (teclado): LEELIN lee cada numero como cadena ASCII (BUFX, BUFY).
; ETAPA 2 (conversion): CONVQ78 pasa la cadena a Q7.8 y INFOQ la muestra.
; H2 corregido: con OVF = 1 la pantalla no muestra un decimal de RES (no representa el producto).
; H1 corregido: LEELIN cuenta TODOS los caracteres tecleados; mas de 15 -> error de longitud.
; ETAPA 3 (integracion): CAPTURA repite cada dato hasta que la conversion sea
;   correcta (codigo 0); los valores validos QX, QY son los operandos de Booth
;   (M = X, Y = Y). MVAL/YVAL ya no se usan (se conservan sin cambiar direcciones).
; LC-3 original. Hexadecimal + decimal (4 cifras, truncadas), RES y OVF.
;
; OPERANDOS: se ingresan por teclado (X = multiplicando M, Y = multiplicador).
;     Q7.8: valor real = n/256 ; rango -128 .. 127.99609375 ; errores: se pide de nuevo.
;
; Booth (sin cambios): R4 = A, R5 = Q, R6 = CNT (-16..0), R7 = enlace de JSR.
;   d = QM1 - q0 ; d=+1: A+M ; d=-1: A+MNEG ; extension E: A'>=0 -> 0,
;   A'=x8000 -> 0 (+32768), otro negativo -> 1.
; Conversion: RES = P[23:8] (8 desplazamientos conjuntos con SHR1).
; OVF = 1  <=>  ((PH + x0080) AND xFF00) != 0   <=>  PH fuera de [-128,127].
; R7: toda subrutina que usa JSR o TRAP guarda R7 en su propia celda.
;
; FINAL (visibles con un breakpoint en FIN):
;     R0 = PH   R1 = PL   R2 = RES   R3 = OVF   R4:R5 = P (32 bits)
;     PRFLAG = #0 -> no imprime en consola (solo deja los registros)
;====================================================================
        .ORIG x3000
        BRnzp INICIO            ; salta sobre los operandos
MVAL    .FILL x0180             ; (sin uso desde la etapa 3)
YVAL    .FILL x0200             ; (sin uso desde la etapa 3)

INICIO  JSR  CAPTURA            ; ETAPA 3: R0 = X, R1 = Y (Q7.8 ya validados)
        ST   R0, MCAND          ; M <- X
        ST   R1, YCOP           ; Y (para mostrarlo)
        ADD  R5, R1, #0         ; Q <- Y
        NOT  R1, R0
        ADD  R1, R1, #1         ; MNEG = NOT(M) + 1  (mod 2^16)
        ST   R1, MNEG
        AND  R4, R4, #0         ; A <- 0
        AND  R0, R0, #0
        ST   R0, QM1            ; QM1 <- 0
        AND  R6, R6, #0
        ADD  R6, R6, #-16       ; CNT <- -16

;---------------- bucle de Booth: 16 iteraciones (sin cambios) ----------------
BOOTH   AND  R0, R5, #1         ; R0 = q0 = Q[0]
        ST   R0, Q0SAVE
        NOT  R0, R0
        ADD  R0, R0, #1         ; R0 = -q0
        LD   R1, QM1
        ADD  R0, R0, R1         ; R0 = QM1 - q0 ; CC <- signo de d
        BRz  SINSUM             ; d = 0
        BRn  RESTA              ; d = -1  (BR no altera CC: el 2.o BR ve el mismo CC)
        LD   R1, MCAND          ; d = +1 : A <- A + M
        ADD  R4, R4, R1
        BRnzp SINSUM
RESTA   LD   R1, MNEG           ; d = -1 : A <- A - M = A + MNEG
        ADD  R4, R4, R1
;   aqui R4 = patron de A' (acumulador antes de desplazar)
SINSUM  AND  R3, R4, #1         ; a0 = A'[0]
        NOT  R3, R3
        ADD  R3, R3, #1         ; R3 = -a0 : negativo <=> a0 = 1
        ADD  R0, R5, #0         ; X = Q
        JSR  SHR1               ; R0 = {a0, Q[15:1]}
        ADD  R5, R0, #0         ; Q <- R0
;   extension E de A'
        ADD  R0, R4, #0         ; X = A'
        ADD  R3, R4, #0         ; R3 = A' ; CC <- signo de A'
        BRzp ECERO              ; A' >= 0 -> E = 0
        ADD  R1, R4, R4         ; con A' < 0: A'+A' = 0  <=>  A' = x8000
        BRnp ECUNO              ; distinto de x8000 -> E = 1 (R3 = A' es negativo)
ECERO   AND  R3, R3, #0         ; E = 0 (A' >= 0, o A' = x8000)
ECUNO   JSR  SHR1               ; R0 = {E, A'[15:1]}
        ADD  R4, R0, #0         ; A <- R0
        LD   R0, Q0SAVE
        ST   R0, QM1            ; QM1 <- q0 anterior
        ADD  R6, R6, #1         ; CNT <- CNT + 1 ; CC <- CNT
        BRn  BOOTH              ; repite mientras CNT < 0 (16 vueltas)

;---------------- producto bruto: PH:PL = A:Q ----------------
        ST   R4, PH
        ST   R5, PL

;---------------- Q7.8: RES = P[23:8] = P >>a 8 (etapa 2) ----------------
;   8 veces: {R4:R5} <- {R4:R5} >>a 1   (R4 = hi, R5 = lo)
;   R4:R5 se destruye; el producto sigue en PH/PL y se restaura al final
        AND  R6, R6, #0
        ADD  R6, R6, #-8        ; CNT <- -8
CONV    AND  R3, R4, #1         ; hi[0]
        NOT  R3, R3
        ADD  R3, R3, #1         ; R3 = -hi[0] : negativo <=> hi[0] = 1
        ADD  R0, R5, #0         ; X = lo
        JSR  SHR1               ; R0 = {hi[0], lo[15:1]}
        ADD  R5, R0, #0         ; lo <- R0
        ADD  R0, R4, #0         ; X = hi
        JSR  ASR1               ; R0 = hi >>a 1  (relleno = signo de hi)
        ADD  R4, R0, #0         ; hi <- R0
        ADD  R6, R6, #1         ; CNT <- CNT + 1 ; CC <- CNT
        BRn  CONV               ; 8 vueltas
        ST   R5, RES            ; RES = lo = P[23:8]
        LD   R4, PH             ; restaura R4:R5 = producto bruto
        LD   R5, PL

;---------------- OVF = ((PH + x0080) AND xFF00) != 0 ----------------
        LD   R0, PH
        LD   R1, C0080
        ADD  R0, R0, R1         ; PH + 128
        LD   R1, CFF00
        AND  R0, R0, R1         ; byte alto de (PH + 128) ; CC
        BRz  GOVF               ; 0 -> OVF = 0 (R0 ya vale 0)
        AND  R0, R0, #0
        ADD  R0, R0, #1         ; OVF = 1
GOVF    ST   R0, OVFV

        LD   R0, PRFLAG
        BRz  FINAL              ; PRFLAG = 0 -> no imprime (CC <- LD)
        JSR  IMPRIM

FINAL   LD   R4, PH             ; R4:R5 = producto
        LD   R5, PL
        LD   R0, PH             ; R0 = PH, R1 = PL, R2 = RES, R3 = OVF
        LD   R1, PL
        LD   R2, RES
        LD   R3, OVFV
FIN     TRAP x25                ; detener (breakpoint aqui para ver registros)

;---------------- variables ----------------
MCAND   .FILL x0000
MNEG    .FILL x0000
QM1     .FILL x0000
Q0SAVE  .FILL x0000
YCOP    .FILL x0000
PH      .FILL x0000
PL      .FILL x0000
RES     .FILL x0000
OVFV    .FILL x0000
PRFLAG  .FILL #1
C0080   .FILL x0080
CFF00   .FILL xFF00

;---------------- cadenas (parte A) ----------------
;   encabezado de resultados
S_RES1  .FILL x000A  ; NL
        .FILL x002D  ; '-'
        .FILL x002D  ; '-'
        .FILL x002D  ; '-'
        .FILL x002D  ; '-'
        .FILL x002D  ; '-'
        .FILL x002D  ; '-'
        .FILL x002D  ; '-'
        .FILL x002D  ; '-'
        .FILL x0020  ; ' '
        .FILL x0052  ; 'R'
        .FILL x0045  ; 'E'
        .FILL x0053  ; 'S'
        .FILL x0055  ; 'U'
        .FILL x004C  ; 'L'
        .FILL x0054  ; 'T'
        .FILL x0041  ; 'A'
        .FILL x0044  ; 'D'
        .FILL x004F  ; 'O'
        .FILL x0053  ; 'S'
        .FILL x0020  ; ' '
        .FILL x002D  ; '-'
        .FILL x002D  ; '-'
        .FILL x002D  ; '-'
        .FILL x002D  ; '-'
        .FILL x002D  ; '-'
        .FILL x002D  ; '-'
        .FILL x002D  ; '-'
        .FILL x002D  ; '-'
        .FILL x000A  ; NL
        .FILL x000A  ; NL
        .FILL x0000  ; fin de cadena

;   X ingresado (decimal)
S_XI    .FILL x0058  ; 'X'
        .FILL x0020  ; ' '
        .FILL x0069  ; 'i'
        .FILL x006E  ; 'n'
        .FILL x0067  ; 'g'
        .FILL x0072  ; 'r'
        .FILL x0065  ; 'e'
        .FILL x0073  ; 's'
        .FILL x0061  ; 'a'
        .FILL x0064  ; 'd'
        .FILL x006F  ; 'o'
        .FILL x003A  ; ':'
        .FILL x0020  ; ' '
        .FILL x0020  ; ' '
        .FILL x0020  ; ' '
        .FILL x0020  ; ' '
        .FILL x0020  ; ' '
        .FILL x0020  ; ' '
        .FILL x0020  ; ' '
        .FILL x0020  ; ' '
        .FILL x0000  ; fin de cadena

;   Y ingresado (decimal)
S_YI    .FILL x000A  ; NL
        .FILL x0059  ; 'Y'
        .FILL x0020  ; ' '
        .FILL x0069  ; 'i'
        .FILL x006E  ; 'n'
        .FILL x0067  ; 'g'
        .FILL x0072  ; 'r'
        .FILL x0065  ; 'e'
        .FILL x0073  ; 's'
        .FILL x0061  ; 'a'
        .FILL x0064  ; 'd'
        .FILL x006F  ; 'o'
        .FILL x003A  ; ':'
        .FILL x0020  ; ' '
        .FILL x0020  ; ' '
        .FILL x0020  ; ' '
        .FILL x0020  ; ' '
        .FILL x0020  ; ' '
        .FILL x0020  ; ' '
        .FILL x0020  ; ' '
        .FILL x0020  ; ' '
        .FILL x0000  ; fin de cadena

;   X en Q7.8 (hex)
S_XQ    .FILL x000A  ; NL
        .FILL x000A  ; NL
        .FILL x0058  ; 'X'
        .FILL x0020  ; ' '
        .FILL x0065  ; 'e'
        .FILL x006E  ; 'n'
        .FILL x0020  ; ' '
        .FILL x0051  ; 'Q'
        .FILL x0037  ; '7'
        .FILL x002E  ; '.'
        .FILL x0038  ; '8'
        .FILL x003A  ; ':'
        .FILL x0020  ; ' '
        .FILL x0020  ; ' '
        .FILL x0020  ; ' '
        .FILL x0020  ; ' '
        .FILL x0020  ; ' '
        .FILL x0020  ; ' '
        .FILL x0020  ; ' '
        .FILL x0020  ; ' '
        .FILL x0020  ; ' '
        .FILL x0020  ; ' '
        .FILL x0078  ; 'x'
        .FILL x0000  ; fin de cadena

;   Y en Q7.8 (hex)
S_YQ    .FILL x000A  ; NL
        .FILL x0059  ; 'Y'
        .FILL x0020  ; ' '
        .FILL x0065  ; 'e'
        .FILL x006E  ; 'n'
        .FILL x0020  ; ' '
        .FILL x0051  ; 'Q'
        .FILL x0037  ; '7'
        .FILL x002E  ; '.'
        .FILL x0038  ; '8'
        .FILL x003A  ; ':'
        .FILL x0020  ; ' '
        .FILL x0020  ; ' '
        .FILL x0020  ; ' '
        .FILL x0020  ; ' '
        .FILL x0020  ; ' '
        .FILL x0020  ; ' '
        .FILL x0020  ; ' '
        .FILL x0020  ; ' '
        .FILL x0020  ; ' '
        .FILL x0020  ; ' '
        .FILL x0078  ; 'x'
        .FILL x0000  ; fin de cadena

;---------------- IMPRIM: pantalla de resultados ----------------
IMPRIM  ST   R7, SVI
        LEA  R0, S_RES1
        JSR  PRSTR
        LEA  R0, S_XI
        JSR  PRSTR
        LD   R0, MCAND
        JSR  PRQ78              ; X ingresado, decimal con 4 cifras
        LEA  R0, S_YI
        JSR  PRSTR
        LD   R0, YCOP
        JSR  PRQ78              ; Y ingresado
        LEA  R0, S_XQ
        JSR  PRSTR
        LD   R0, MCAND
        JSR  PRHEX              ; X en Q7.8
        LEA  R0, S_YQ
        JSR  PRSTR
        LD   R0, YCOP
        JSR  PRHEX              ; Y en Q7.8
        LEA  R0, S_PHL
        JSR  PRSTR
        LD   R0, PH
        JSR  PRHEX
        LD   R0, PL
        JSR  PRHEX              ; producto de 32 bits: PH seguido de PL
        LEA  R0, S_PD
        JSR  PRSTR
        LD   R0, PH
        LD   R1, PL
        JSR  PRP32              ; producto decimal (PH:PL / 65536)
        LEA  R0, S_RQ
        JSR  PRSTR
        LD   R0, RES
        JSR  PRHEX              ; RES en Q7.8
        LEA  R0, S_RD
        JSR  PRSTR
        LD   R0, OVFV           ; con OVF = 1, RES no representa el producto
        BRp  IMPOV
        LD   R0, RES
        JSR  PRQ78              ; RES / 256
        BRnzp IMPNL
IMPOV   LEA  R0, S_OVM
        JSR  PRSTR              ; "** OVERFLOW: no representable en Q7.8 **"
IMPNL   LEA  R0, S_OV
        JSR  PRSTR
        LD   R0, OVFV
        LD   R1, C0I
        ADD  R0, R0, R1         ; '0' + OVF
        TRAP x21
        LEA  R0, S_FIN
        JSR  PRSTR
        LD   R7, SVI
        JMP  R7                 ; (RET)
SVI     .FILL x0000
C0I     .FILL x0030

;---------------- cadenas (parte B) ----------------
;   producto de 32 bits (hex)
S_PHL   .FILL x000A  ; NL
        .FILL x000A  ; NL
        .FILL x0050  ; 'P'
        .FILL x0072  ; 'r'
        .FILL x006F  ; 'o'
        .FILL x0064  ; 'd'
        .FILL x0075  ; 'u'
        .FILL x0063  ; 'c'
        .FILL x0074  ; 't'
        .FILL x006F  ; 'o'
        .FILL x0020  ; ' '
        .FILL x0050  ; 'P'
        .FILL x0048  ; 'H'
        .FILL x003A  ; ':'
        .FILL x0050  ; 'P'
        .FILL x004C  ; 'L'
        .FILL x003A  ; ':'
        .FILL x0020  ; ' '
        .FILL x0020  ; ' '
        .FILL x0020  ; ' '
        .FILL x0020  ; ' '
        .FILL x0020  ; ' '
        .FILL x0078  ; 'x'
        .FILL x0000  ; fin de cadena

;   producto decimal
S_PD    .FILL x000A  ; NL
        .FILL x0050  ; 'P'
        .FILL x0072  ; 'r'
        .FILL x006F  ; 'o'
        .FILL x0064  ; 'd'
        .FILL x0075  ; 'u'
        .FILL x0063  ; 'c'
        .FILL x0074  ; 't'
        .FILL x006F  ; 'o'
        .FILL x0020  ; ' '
        .FILL x0064  ; 'd'
        .FILL x0065  ; 'e'
        .FILL x0063  ; 'c'
        .FILL x0069  ; 'i'
        .FILL x006D  ; 'm'
        .FILL x0061  ; 'a'
        .FILL x006C  ; 'l'
        .FILL x003A  ; ':'
        .FILL x0020  ; ' '
        .FILL x0020  ; ' '
        .FILL x0020  ; ' '
        .FILL x0000  ; fin de cadena

;   RES (hex)
S_RQ    .FILL x000A  ; NL
        .FILL x000A  ; NL
        .FILL x0052  ; 'R'
        .FILL x0065  ; 'e'
        .FILL x0073  ; 's'
        .FILL x0075  ; 'u'
        .FILL x006C  ; 'l'
        .FILL x0074  ; 't'
        .FILL x0061  ; 'a'
        .FILL x0064  ; 'd'
        .FILL x006F  ; 'o'
        .FILL x0020  ; ' '
        .FILL x0051  ; 'Q'
        .FILL x0037  ; '7'
        .FILL x002E  ; '.'
        .FILL x0038  ; '8'
        .FILL x003A  ; ':'
        .FILL x0020  ; ' '
        .FILL x0020  ; ' '
        .FILL x0020  ; ' '
        .FILL x0020  ; ' '
        .FILL x0020  ; ' '
        .FILL x0078  ; 'x'
        .FILL x0000  ; fin de cadena

;   RES decimal
S_RD    .FILL x000A  ; NL
        .FILL x0052  ; 'R'
        .FILL x0065  ; 'e'
        .FILL x0073  ; 's'
        .FILL x0075  ; 'u'
        .FILL x006C  ; 'l'
        .FILL x0074  ; 't'
        .FILL x0061  ; 'a'
        .FILL x0064  ; 'd'
        .FILL x006F  ; 'o'
        .FILL x0020  ; ' '
        .FILL x0064  ; 'd'
        .FILL x0065  ; 'e'
        .FILL x0063  ; 'c'
        .FILL x0069  ; 'i'
        .FILL x006D  ; 'm'
        .FILL x0061  ; 'a'
        .FILL x006C  ; 'l'
        .FILL x003A  ; ':'
        .FILL x0020  ; ' '
        .FILL x0020  ; ' '
        .FILL x0000  ; fin de cadena

;   OVF
S_OV    .FILL x000A  ; NL
        .FILL x000A  ; NL
        .FILL x004F  ; 'O'
        .FILL x0076  ; 'v'
        .FILL x0065  ; 'e'
        .FILL x0072  ; 'r'
        .FILL x0066  ; 'f'
        .FILL x006C  ; 'l'
        .FILL x006F  ; 'o'
        .FILL x0077  ; 'w'
        .FILL x003A  ; ':'
        .FILL x0020  ; ' '
        .FILL x0020  ; ' '
        .FILL x0020  ; ' '
        .FILL x0020  ; ' '
        .FILL x0020  ; ' '
        .FILL x0020  ; ' '
        .FILL x0020  ; ' '
        .FILL x0020  ; ' '
        .FILL x0020  ; ' '
        .FILL x0020  ; ' '
        .FILL x0020  ; ' '
        .FILL x0000  ; fin de cadena

;   fin
S_FIN   .FILL x000A  ; NL
        .FILL x000A  ; NL
        .FILL x004F  ; 'O'
        .FILL x0070  ; 'p'
        .FILL x0065  ; 'e'
        .FILL x0072  ; 'r'
        .FILL x0061  ; 'a'
        .FILL x0063  ; 'c'
        .FILL x0069  ; 'i'
        .FILL x006F  ; 'o'
        .FILL x006E  ; 'n'
        .FILL x0020  ; ' '
        .FILL x0066  ; 'f'
        .FILL x0069  ; 'i'
        .FILL x006E  ; 'n'
        .FILL x0061  ; 'a'
        .FILL x006C  ; 'l'
        .FILL x0069  ; 'i'
        .FILL x007A  ; 'z'
        .FILL x0061  ; 'a'
        .FILL x0064  ; 'd'
        .FILL x0061  ; 'a'
        .FILL x002E  ; '.'
        .FILL x000A  ; NL
        .FILL x0000  ; fin de cadena

;   aviso H2 (OVF = 1)
S_OVM   .FILL x002A  ; '*'
        .FILL x002A  ; '*'
        .FILL x0020  ; ' '
        .FILL x004F  ; 'O'
        .FILL x0056  ; 'V'
        .FILL x0045  ; 'E'
        .FILL x0052  ; 'R'
        .FILL x0046  ; 'F'
        .FILL x004C  ; 'L'
        .FILL x004F  ; 'O'
        .FILL x0057  ; 'W'
        .FILL x003A  ; ':'
        .FILL x0020  ; ' '
        .FILL x006E  ; 'n'
        .FILL x006F  ; 'o'
        .FILL x0020  ; ' '
        .FILL x0072  ; 'r'
        .FILL x0065  ; 'e'
        .FILL x0070  ; 'p'
        .FILL x0072  ; 'r'
        .FILL x0065  ; 'e'
        .FILL x0073  ; 's'
        .FILL x0065  ; 'e'
        .FILL x006E  ; 'n'
        .FILL x0074  ; 't'
        .FILL x0061  ; 'a'
        .FILL x0062  ; 'b'
        .FILL x006C  ; 'l'
        .FILL x0065  ; 'e'
        .FILL x0020  ; ' '
        .FILL x0065  ; 'e'
        .FILL x006E  ; 'n'
        .FILL x0020  ; ' '
        .FILL x0051  ; 'Q'
        .FILL x0037  ; '7'
        .FILL x002E  ; '.'
        .FILL x0038  ; '8'
        .FILL x0020  ; ' '
        .FILL x002A  ; '*'
        .FILL x002A  ; '*'
        .FILL x0000  ; fin de cadena

;---------------- SHR1 (copia fiel de shift1.asm) ----------------
LSR1    AND  R3, R3, #0
        BRnzp SHR1
ASR1    ADD  R3, R0, #0
SHR1    ADD  R1, R0, #0        ; W <- X
        AND  R2, R2, #0
        ADD  R2, R2, #1        ; R <- 1 (centinela en bit 0)
SLAZO   ADD  R2, R2, R2        ; R <- 2R
        ADD  R1, R1, #0        ; CC <- signo de W (= bit 15)
        BRzp SNOBIT
        ADD  R2, R2, #1        ; bit 15 de W era 1
SNOBIT  ADD  R1, R1, R1        ; W <- 2W
        ADD  R2, R2, #0        ; CC <- signo de R (= centinela en bit 15?)
        BRzp SLAZO
        ADD  R3, R3, #0        ; CC <- relleno
        BRn  SFIN              ; relleno=1: el centinela ya es el bit 15
        LD   R3, C8000
        ADD  R2, R2, R3        ; relleno=0: borra el centinela
SFIN    ADD  R0, R2, #0
        JMP  R7                ; (RET)
C8000   .FILL x8000

;---------------- PRHEX: imprime R0 como 4 digitos hex (usa TRAP x21) ----------------
;   Entrada R0. Modifica R0-R6. Guarda R7 en SAVE7 (TRAP lo sobrescribe).
;   Barre los 16 bits desde el MSB: 4 digitos de 4 bits. El estado (W, cuenta)
;   se guarda en memoria alrededor de cada TRAP.
PRHEX   ST   R7, SAVE7
        ST   R0, PW             ; W <- palabra
        AND  R6, R6, #0
        ADD  R6, R6, #-4
        ST   R6, PCNT           ; 4 digitos
PDIG    LD   R1, PW
        AND  R2, R2, #0         ; D <- 0
        AND  R5, R5, #0
        ADD  R5, R5, #-4        ; 4 bits por digito
PBIT    ADD  R2, R2, R2         ; D <- 2D
        ADD  R1, R1, #0         ; CC <- bit 15 de W
        BRzp PB0
        ADD  R2, R2, #1         ; bit 15 = 1
PB0     ADD  R1, R1, R1         ; W <- 2W
        ADD  R5, R5, #1
        BRn  PBIT               ; 4 bits
        ST   R1, PW             ; W ya avanzo 4 bits
        ADD  R3, R2, #-10       ; D - 10 ; CC
        BRzp PLET               ; D >= 10 -> letra A-F
        LD   R0, C0
        ADD  R0, R0, R2         ; '0' + D
        BRnzp PPUT
PLET    LD   R0, CLETA
        ADD  R0, R0, R3         ; 'A' + (D - 10)
PPUT    TRAP x21                ; OUT
        LD   R6, PCNT
        ADD  R6, R6, #1
        ST   R6, PCNT
        ADD  R6, R6, #0         ; CC <- cuenta
        BRn  PDIG
        LD   R7, SAVE7
        JMP  R7                 ; (RET)
SAVE7   .FILL x0000
PW      .FILL x0000
PCNT    .FILL x0000
C0      .FILL x0030
CLETA   .FILL x0041

;---------------- PRSTR: imprime la cadena (terminada en 0) cuya direccion esta en R0 ----------------
;   Un caracter por palabra. El puntero vive en memoria (TRAP puede alterar registros).
PRSTR   ST   R7, SVS
        ST   R0, SPTR
PSLAZO  LD   R1, SPTR
        LDR  R0, R1, #0         ; caracter ; CC
        BRz  PSFIN
        TRAP x21
        LD   R1, SPTR
        ADD  R1, R1, #1
        ST   R1, SPTR
        BRnzp PSLAZO
PSFIN   LD   R7, SVS
        JMP  R7
SVS     .FILL x0000
SPTR    .FILL x0000

;---------------- PRDEC: imprime R0 (0..32767) en decimal, sin ceros a la izquierda ----------------
;   Resta sucesivas de 10000, 1000, 100, 10, 1; imprime el digito si es no nulo,
;   si ya se imprimio algun digito, o si es la ultima potencia.
PRDEC   ST   R7, SVD
        ST   R0, DV
        AND  R0, R0, #0
        ST   R0, DFL            ; DFL = 0: aun no se imprimio ningun digito
        LEA  R0, TPOT
        ST   R0, DPT
        AND  R0, R0, #0
        ADD  R0, R0, #-5
        ST   R0, DCN            ; 5 potencias
DPOT    LD   R1, DPT
        LDR  R2, R1, #0         ; R2 = -potencia
        LD   R1, DV             ; R1 = resto
        AND  R3, R3, #0         ; R3 = digito
DRES    ADD  R4, R1, R2         ; resto - potencia ; CC
        BRn  DFIN
        ADD  R1, R4, #0
        ADD  R3, R3, #1
        BRnzp DRES
DFIN    ST   R1, DV
        ADD  R3, R3, #0         ; CC <- digito
        BRp  DIMP
        LD   R5, DFL
        BRp  DIMP               ; ya se imprimio un digito
        LD   R5, DCN
        ADD  R5, R5, #1         ; = 0 solo en la ultima potencia
        BRnp DSIG               ; cero a la izquierda: omitir
DIMP    AND  R5, R5, #0
        ADD  R5, R5, #1
        ST   R5, DFL
        LD   R0, C0D
        ADD  R0, R0, R3         ; '0' + digito
        TRAP x21
DSIG    LD   R1, DPT
        ADD  R1, R1, #1
        ST   R1, DPT
        LD   R5, DCN
        ADD  R5, R5, #1
        ST   R5, DCN
        ADD  R5, R5, #0         ; CC <- DCN
        BRn  DPOT
        LD   R7, SVD
        JMP  R7
SVD     .FILL x0000
DV      .FILL x0000
DFL     .FILL x0000
DPT     .FILL x0000
DCN     .FILL x0000
C0D     .FILL x0030
TPOT    .FILL xD8F0             ; -10000
        .FILL xFC18             ; -1000
        .FILL xFF9C             ; -100
        .FILL xFFF6             ; -10
        .FILL xFFFF             ; -1

;---------------- PRFR4: 4 digitos decimales de la fraccion F/65536, F = R0:R1 (bytes alto:bajo) ----------------
;   Cada digito = floor(10*F / 65536); F <- (10*F) mod 65536. Se evita desbordar 16 bits
;   trabajando con los bytes: 10*F = A*256 + B, A = 10*Fh, B = 10*Fl (ambos <= 2550).
;   bq = B div 256 ; Fl' = B mod 256 ; C = A + bq ; digito = C div 256 ; Fh' = C mod 256.
PRFR4   ST   R7, SVF
        ST   R0, FH
        ST   R1, FL
        AND  R0, R0, #0
        ADD  R0, R0, #-4
        ST   R0, FCN            ; 4 digitos
FDIG    LD   R1, FH
        ADD  R2, R1, R1         ; 2Fh
        ADD  R3, R2, R2         ; 4Fh
        ADD  R3, R3, R3         ; 8Fh
        ADD  R2, R2, R3         ; R2 = A = 10*Fh
        LD   R1, FL
        ADD  R4, R1, R1         ; 2Fl
        ADD  R5, R4, R4         ; 4Fl
        ADD  R5, R5, R5         ; 8Fl
        ADD  R4, R4, R5         ; R4 = B = 10*Fl
        LD   R6, CM256          ; R6 = -256
        AND  R1, R1, #0         ; R1 = bq
FB256   ADD  R5, R4, R6         ; B - 256 ; CC
        BRn  FBFIN
        ADD  R4, R5, #0
        ADD  R1, R1, #1
        BRnzp FB256
FBFIN   ST   R4, FL             ; Fl' = B mod 256
        ADD  R2, R2, R1         ; R2 = C = A + bq
        AND  R3, R3, #0         ; R3 = digito
FC256   ADD  R5, R2, R6         ; C - 256 ; CC
        BRn  FCFIN
        ADD  R2, R5, #0
        ADD  R3, R3, #1
        BRnzp FC256
FCFIN   ST   R2, FH             ; Fh' = C mod 256
        LD   R0, C0F
        ADD  R0, R0, R3         ; '0' + digito
        TRAP x21
        LD   R1, FCN
        ADD  R1, R1, #1
        ST   R1, FCN
        ADD  R1, R1, #0         ; CC <- FCN
        BRn  FDIG
        LD   R7, SVF
        JMP  R7
SVF     .FILL x0000
FH      .FILL x0000
FL      .FILL x0000
FCN     .FILL x0000
CM256   .FILL xFF00             ; -256
C0F     .FILL x0030

;---------------- SPLIT: R0 (16 bits) -> R0 = byte alto, R1 = byte bajo (subrutina hoja) ----------------
;   Barre los 16 bits desde el MSB. Modifica R0-R3. No toca R7.
SPLIT   ADD  R2, R0, #0         ; W <- palabra
        AND  R0, R0, #0         ; alto <- 0
        AND  R1, R1, #0         ; bajo <- 0
        AND  R3, R3, #0
        ADD  R3, R3, #-8
SPH     ADD  R0, R0, R0
        ADD  R2, R2, #0         ; CC <- bit 15 de W
        BRzp SPH0
        ADD  R0, R0, #1
SPH0    ADD  R2, R2, R2
        ADD  R3, R3, #1
        BRn  SPH
        AND  R3, R3, #0
        ADD  R3, R3, #-8
SPL     ADD  R1, R1, R1
        ADD  R2, R2, #0
        BRzp SPL0
        ADD  R1, R1, #1
SPL0    ADD  R2, R2, R2
        ADD  R3, R3, #1
        BRn  SPL
        JMP  R7                 ; (RET)

;---------------- PRQ78: imprime R0 (Q7.8 con signo) como [-]E.FFFF  (valor = R0/256) ----------------
;   Magnitud = NOT+1 (x8000 -> x8000 = 32768 sin signo). Entera = byte alto, fraccion = byte bajo.
PRQ78   ST   R7, SVQ
        ADD  R0, R0, #0         ; CC <- signo
        BRzp QPOS
        NOT  R0, R0
        ADD  R0, R0, #1         ; magnitud
        ST   R0, QMAG
        LD   R0, CMEN
        TRAP x21                ; '-'
        LD   R0, QMAG
QPOS    JSR  SPLIT              ; R0 = parte entera (0..128), R1 = byte fraccionario
        ST   R1, QFR
        JSR  PRDEC
        LD   R0, CPTO
        TRAP x21                ; '.'
        LD   R0, QFR            ; Fh = byte fraccionario
        AND  R1, R1, #0         ; Fl = 0
        JSR  PRFR4
        LD   R7, SVQ
        JMP  R7
SVQ     .FILL x0000
QMAG    .FILL x0000
QFR     .FILL x0000
CMEN    .FILL x002D
CPTO    .FILL x002E

;---------------- PRP32: imprime PH:PL (R0:R1, 32 bits con signo) como [-]E.FFFF  (valor = P/65536) ----------------
;   Si PH < 0 se niega el par de 32 bits: lo' = NOT(PL)+1 ; hi' = NOT(PH) + (lo' == 0).
;   |P| <= 2^30, asi que hi' <= 16384 y cabe como entero positivo.
PRP32   ST   R7, SVP
        ST   R0, PHM
        ST   R1, PLM
        ADD  R0, R0, #0         ; CC <- signo de PH
        BRzp P32F
        LD   R0, CMEP
        TRAP x21                ; '-'
        LD   R1, PLM
        NOT  R1, R1
        ADD  R1, R1, #1         ; lo' = NOT(PL) + 1
        ST   R1, PLM
        LD   R0, PHM
        NOT  R0, R0             ; hi' = NOT(PH)
        ADD  R1, R1, #0         ; CC <- lo'
        BRnp P32H
        ADD  R0, R0, #1         ; lo' = 0: acarreo hacia hi'
P32H    ST   R0, PHM
P32F    LD   R0, PHM
        JSR  PRDEC              ; parte entera = |P| >> 16
        LD   R0, CPTP
        TRAP x21                ; '.'
        LD   R0, PLM
        JSR  SPLIT              ; R0 = Fh, R1 = Fl
        JSR  PRFR4
        LD   R7, SVP
        JMP  R7
SVP     .FILL x0000
PHM     .FILL x0000
PLM     .FILL x0000
CMEP    .FILL x002D
CPTP    .FILL x002E

;====================================================================
; ETAPA 1: LECTURA DE CADENAS POR TECLADO
;   CAPTURA : pide y lee X e Y (BUFX, BUFY), mostrando lo leido.
;   LEELIN  : R0 = buffer -> lee una linea; devuelve R0 = n.o de caracteres TECLEADOS.
;             Termina con ENTER (x0A o x0D). Acepta x20..x7E; ignora el resto;
;             retroceso (x08 o x7F) borra. El buffer guarda como maximo 15; si se tecleo mas,
;             R0 > 15 y CAPTURA rechaza la linea (error de longitud), sin descartar nada en silencio.
;             El buffer queda terminado en x0000. LTERM = codigo de la tecla ENTER.
;   LEECAR  : R0 <- una tecla. KBPOLL = #0: TRAP x20 (GETC) ; KBPOLL = #1: sondeo de KBSR/KBDR.
;   ECOLIN  : R0 = buffer, R1 = longitud -> imprime el eco.
;   Toda subrutina que usa JSR o TRAP guarda R7 en su propia celda.
;====================================================================
;   titulo
S_T1    .FILL x003D  ; '='
        .FILL x003D  ; '='
        .FILL x003D  ; '='
        .FILL x003D  ; '='
        .FILL x003D  ; '='
        .FILL x003D  ; '='
        .FILL x003D  ; '='
        .FILL x003D  ; '='
        .FILL x003D  ; '='
        .FILL x003D  ; '='
        .FILL x003D  ; '='
        .FILL x003D  ; '='
        .FILL x003D  ; '='
        .FILL x003D  ; '='
        .FILL x003D  ; '='
        .FILL x003D  ; '='
        .FILL x003D  ; '='
        .FILL x003D  ; '='
        .FILL x003D  ; '='
        .FILL x003D  ; '='
        .FILL x003D  ; '='
        .FILL x003D  ; '='
        .FILL x003D  ; '='
        .FILL x003D  ; '='
        .FILL x003D  ; '='
        .FILL x003D  ; '='
        .FILL x003D  ; '='
        .FILL x003D  ; '='
        .FILL x003D  ; '='
        .FILL x003D  ; '='
        .FILL x003D  ; '='
        .FILL x003D  ; '='
        .FILL x000A  ; NL
        .FILL x0020  ; ' '
        .FILL x0020  ; ' '
        .FILL x0020  ; ' '
        .FILL x0020  ; ' '
        .FILL x0020  ; ' '
        .FILL x004D  ; 'M'
        .FILL x0055  ; 'U'
        .FILL x004C  ; 'L'
        .FILL x0054  ; 'T'
        .FILL x0049  ; 'I'
        .FILL x0050  ; 'P'
        .FILL x004C  ; 'L'
        .FILL x0049  ; 'I'
        .FILL x0043  ; 'C'
        .FILL x0041  ; 'A'
        .FILL x0044  ; 'D'
        .FILL x004F  ; 'O'
        .FILL x0052  ; 'R'
        .FILL x0020  ; ' '
        .FILL x0042  ; 'B'
        .FILL x004F  ; 'O'
        .FILL x004F  ; 'O'
        .FILL x0054  ; 'T'
        .FILL x0048  ; 'H'
        .FILL x0020  ; ' '
        .FILL x0051  ; 'Q'
        .FILL x0037  ; '7'
        .FILL x002E  ; '.'
        .FILL x0038  ; '8'
        .FILL x000A  ; NL
        .FILL x003D  ; '='
        .FILL x003D  ; '='
        .FILL x003D  ; '='
        .FILL x003D  ; '='
        .FILL x003D  ; '='
        .FILL x003D  ; '='
        .FILL x003D  ; '='
        .FILL x003D  ; '='
        .FILL x003D  ; '='
        .FILL x003D  ; '='
        .FILL x003D  ; '='
        .FILL x003D  ; '='
        .FILL x003D  ; '='
        .FILL x003D  ; '='
        .FILL x003D  ; '='
        .FILL x003D  ; '='
        .FILL x003D  ; '='
        .FILL x003D  ; '='
        .FILL x003D  ; '='
        .FILL x003D  ; '='
        .FILL x003D  ; '='
        .FILL x003D  ; '='
        .FILL x003D  ; '='
        .FILL x003D  ; '='
        .FILL x003D  ; '='
        .FILL x003D  ; '='
        .FILL x003D  ; '='
        .FILL x003D  ; '='
        .FILL x003D  ; '='
        .FILL x003D  ; '='
        .FILL x003D  ; '='
        .FILL x003D  ; '='
        .FILL x000A  ; NL
        .FILL x000A  ; NL
        .FILL x0000  ; fin de cadena

;   prompt 1
S_P1    .FILL x0049  ; 'I'
        .FILL x006E  ; 'n'
        .FILL x0067  ; 'g'
        .FILL x0072  ; 'r'
        .FILL x0065  ; 'e'
        .FILL x0073  ; 's'
        .FILL x0065  ; 'e'
        .FILL x0020  ; ' '
        .FILL x0065  ; 'e'
        .FILL x006C  ; 'l'
        .FILL x0020  ; ' '
        .FILL x0070  ; 'p'
        .FILL x0072  ; 'r'
        .FILL x0069  ; 'i'
        .FILL x006D  ; 'm'
        .FILL x0065  ; 'e'
        .FILL x0072  ; 'r'
        .FILL x0020  ; ' '
        .FILL x006E  ; 'n'
        .FILL x0075  ; 'u'
        .FILL x006D  ; 'm'
        .FILL x0065  ; 'e'
        .FILL x0072  ; 'r'
        .FILL x006F  ; 'o'
        .FILL x003A  ; ':'
        .FILL x0020  ; ' '
        .FILL x0000  ; fin de cadena

;   prompt 2
S_P2    .FILL x0049  ; 'I'
        .FILL x006E  ; 'n'
        .FILL x0067  ; 'g'
        .FILL x0072  ; 'r'
        .FILL x0065  ; 'e'
        .FILL x0073  ; 's'
        .FILL x0065  ; 'e'
        .FILL x0020  ; ' '
        .FILL x0065  ; 'e'
        .FILL x006C  ; 'l'
        .FILL x0020  ; ' '
        .FILL x0073  ; 's'
        .FILL x0065  ; 'e'
        .FILL x0067  ; 'g'
        .FILL x0075  ; 'u'
        .FILL x006E  ; 'n'
        .FILL x0064  ; 'd'
        .FILL x006F  ; 'o'
        .FILL x0020  ; ' '
        .FILL x006E  ; 'n'
        .FILL x0075  ; 'u'
        .FILL x006D  ; 'm'
        .FILL x0065  ; 'e'
        .FILL x0072  ; 'r'
        .FILL x006F  ; 'o'
        .FILL x003A  ; ':'
        .FILL x0020  ; ' '
        .FILL x0000  ; fin de cadena

BUFX    .FILL x0000             ; buffer X: 15 caracteres + terminador
        .FILL x0000
        .FILL x0000
        .FILL x0000
        .FILL x0000
        .FILL x0000
        .FILL x0000
        .FILL x0000
        .FILL x0000
        .FILL x0000
        .FILL x0000
        .FILL x0000
        .FILL x0000
        .FILL x0000
        .FILL x0000
        .FILL x0000
BUFY    .FILL x0000             ; buffer Y: 15 caracteres + terminador
        .FILL x0000
        .FILL x0000
        .FILL x0000
        .FILL x0000
        .FILL x0000
        .FILL x0000
        .FILL x0000
        .FILL x0000
        .FILL x0000
        .FILL x0000
        .FILL x0000
        .FILL x0000
        .FILL x0000
        .FILL x0000
        .FILL x0000

CAPTURA ST   R7, SVK
        LEA  R0, S_T1
        JSR  PRSTR
CAPX    LEA  R0, S_P1           ; ---- X: se repite hasta que la conversion sea correcta ----
        JSR  PRSTR
        LEA  R0, BUFX
        JSR  LEELIN             ; R0 = n.o de caracteres tecleados
        ADD  R1, R0, #-15       ; tecleados - 15
        BRnz CXOK               ; <= 15: longitud permitida
        LEA  R0, S_E4
        JSR  PRSTR              ; "ERROR: entrada demasiado larga ..."
        BRnzp CAPX              ; se vuelve a pedir X
CXOK    LD   R1, DBGFLAG        ; (CC <- DBGFLAG)
        BRz  CXQ                ; modo normal: sin eco de diagnostico
        ADD  R1, R0, #0         ; R1 = longitud
        LEA  R0, BUFX           ; R0 = buffer
        JSR  ECOLIN
        LEA  R0, BUFX
        LD   R1, CHX            ; modo diagnostico: etiqueta 'X'
        BRnzp CXI
CXQ     LEA  R0, BUFX
        AND  R1, R1, #0         ; modo normal: etiqueta 0 = INFOQ solo informa errores
CXI     JSR  INFOQ              ; R0 = valor Q7.8, R1 = codigo (0 = correcto)
        ADD  R1, R1, #0         ; CC <- codigo
        BRp  CAPX               ; error: se vuelve a pedir X
        ST   R0, QX
CAPY    LEA  R0, S_P2           ; ---- Y: igual ----
        JSR  PRSTR
        LEA  R0, BUFY
        JSR  LEELIN             ; R0 = n.o de caracteres tecleados
        ADD  R1, R0, #-15       ; tecleados - 15
        BRnz CYOK               ; <= 15: longitud permitida
        LEA  R0, S_E4
        JSR  PRSTR
        BRnzp CAPY              ; se vuelve a pedir Y
CYOK    LD   R1, DBGFLAG        ; (CC <- DBGFLAG)
        BRz  CYQ
        ADD  R1, R0, #0
        LEA  R0, BUFY
        JSR  ECOLIN
        LEA  R0, BUFY
        LD   R1, CHY            ; modo diagnostico: etiqueta 'Y'
        BRnzp CYI
CYQ     LEA  R0, BUFY
        AND  R1, R1, #0         ; modo normal
CYI     JSR  INFOQ
        ADD  R1, R1, #0         ; CC <- codigo
        BRp  CAPY               ; error: se vuelve a pedir Y
        ST   R0, QY
        LD   R0, DBGFLAG
        BRz  CAPFIN             ; modo normal: sin aviso
        LEA  R0, S_NOTA
        JSR  PRSTR
CAPFIN  LD   R0, QX             ; salida: R0 = X, R1 = Y (ambos validos)
        LD   R1, QY
        LD   R7, SVK
        JMP  R7                 ; (RET)
SVK     .FILL x0000
CHX     .FILL x0058             ; 'X'
CHY     .FILL x0059             ; 'Y'
QX      .FILL x0000             ; X convertido (Q7.8)
QY      .FILL x0000             ; Y convertido (Q7.8)
DBGFLAG .FILL #0                ; 0 = salida limpia ; 1 = diagnostico (eco de LEELIN y linea de conversion)

;---------------- cadenas del eco ----------------
;   aviso antes de multiplicar
S_NOTA  .FILL x000A  ; NL
        .FILL x004F  ; 'O'
        .FILL x0070  ; 'p'
        .FILL x0065  ; 'e'
        .FILL x0072  ; 'r'
        .FILL x0061  ; 'a'
        .FILL x006E  ; 'n'
        .FILL x0064  ; 'd'
        .FILL x006F  ; 'o'
        .FILL x0073  ; 's'
        .FILL x0020  ; ' '
        .FILL x0076  ; 'v'
        .FILL x0061  ; 'a'
        .FILL x006C  ; 'l'
        .FILL x0069  ; 'i'
        .FILL x0064  ; 'd'
        .FILL x006F  ; 'o'
        .FILL x0073  ; 's'
        .FILL x003A  ; ':'
        .FILL x0020  ; ' '
        .FILL x0073  ; 's'
        .FILL x0065  ; 'e'
        .FILL x0020  ; ' '
        .FILL x0065  ; 'e'
        .FILL x006A  ; 'j'
        .FILL x0065  ; 'e'
        .FILL x0063  ; 'c'
        .FILL x0075  ; 'u'
        .FILL x0074  ; 't'
        .FILL x0061  ; 'a'
        .FILL x0020  ; ' '
        .FILL x0042  ; 'B'
        .FILL x006F  ; 'o'
        .FILL x006F  ; 'o'
        .FILL x0074  ; 't'
        .FILL x0068  ; 'h'
        .FILL x0020  ; ' '
        .FILL x0063  ; 'c'
        .FILL x006F  ; 'o'
        .FILL x006E  ; 'n'
        .FILL x0020  ; ' '
        .FILL x0058  ; 'X'
        .FILL x0020  ; ' '
        .FILL x0065  ; 'e'
        .FILL x0020  ; ' '
        .FILL x0059  ; 'Y'
        .FILL x0020  ; ' '
        .FILL x0069  ; 'i'
        .FILL x006E  ; 'n'
        .FILL x0067  ; 'g'
        .FILL x0072  ; 'r'
        .FILL x0065  ; 'e'
        .FILL x0073  ; 's'
        .FILL x0061  ; 'a'
        .FILL x0064  ; 'd'
        .FILL x006F  ; 'o'
        .FILL x0073  ; 's'
        .FILL x002E  ; '.'
        .FILL x000A  ; NL
        .FILL x000A  ; NL
        .FILL x0000  ; fin de cadena

;   inicio del eco
S_LEI   .FILL x0020  ; ' '
        .FILL x0020  ; ' '
        .FILL x004C  ; 'L'
        .FILL x0065  ; 'e'
        .FILL x0069  ; 'i'
        .FILL x0064  ; 'd'
        .FILL x006F  ; 'o'
        .FILL x003A  ; ':'
        .FILL x0020  ; ' '
        .FILL x005B  ; '['
        .FILL x0000  ; fin de cadena

;   cierre del eco
S_LON   .FILL x005D  ; ']'
        .FILL x0020  ; ' '
        .FILL x0020  ; ' '
        .FILL x006C  ; 'l'
        .FILL x006F  ; 'o'
        .FILL x006E  ; 'n'
        .FILL x0067  ; 'g'
        .FILL x0069  ; 'i'
        .FILL x0074  ; 't'
        .FILL x0075  ; 'u'
        .FILL x0064  ; 'd'
        .FILL x003A  ; ':'
        .FILL x0020  ; ' '
        .FILL x0000  ; fin de cadena

;   codigo de la tecla que termino la linea
S_ENT   .FILL x0020  ; ' '
        .FILL x0020  ; ' '
        .FILL x0045  ; 'E'
        .FILL x004E  ; 'N'
        .FILL x0054  ; 'T'
        .FILL x0045  ; 'E'
        .FILL x0052  ; 'R'
        .FILL x0020  ; ' '
        .FILL x003D  ; '='
        .FILL x0020  ; ' '
        .FILL x0000  ; fin de cadena
;   error de longitud (H1)
S_E4    .FILL x0020  ; ' '
        .FILL x0020  ; ' '
        .FILL x0045  ; 'E'
        .FILL x0052  ; 'R'
        .FILL x0052  ; 'R'
        .FILL x004F  ; 'O'
        .FILL x0052  ; 'R'
        .FILL x003A  ; ':'
        .FILL x0020  ; ' '
        .FILL x0065  ; 'e'
        .FILL x006E  ; 'n'
        .FILL x0074  ; 't'
        .FILL x0072  ; 'r'
        .FILL x0061  ; 'a'
        .FILL x0064  ; 'd'
        .FILL x0061  ; 'a'
        .FILL x0020  ; ' '
        .FILL x0064  ; 'd'
        .FILL x0065  ; 'e'
        .FILL x006D  ; 'm'
        .FILL x0061  ; 'a'
        .FILL x0073  ; 's'
        .FILL x0069  ; 'i'
        .FILL x0061  ; 'a'
        .FILL x0064  ; 'd'
        .FILL x006F  ; 'o'
        .FILL x0020  ; ' '
        .FILL x006C  ; 'l'
        .FILL x0061  ; 'a'
        .FILL x0072  ; 'r'
        .FILL x0067  ; 'g'
        .FILL x0061  ; 'a'
        .FILL x0020  ; ' '
        .FILL x0028  ; '('
        .FILL x006D  ; 'm'
        .FILL x0061  ; 'a'
        .FILL x0078  ; 'x'
        .FILL x0069  ; 'i'
        .FILL x006D  ; 'm'
        .FILL x006F  ; 'o'
        .FILL x0020  ; ' '
        .FILL x0031  ; '1'
        .FILL x0035  ; '5'
        .FILL x0020  ; ' '
        .FILL x0063  ; 'c'
        .FILL x0061  ; 'a'
        .FILL x0072  ; 'r'
        .FILL x0061  ; 'a'
        .FILL x0063  ; 'c'
        .FILL x0074  ; 't'
        .FILL x0065  ; 'e'
        .FILL x0072  ; 'r'
        .FILL x0065  ; 'e'
        .FILL x0073  ; 's'
        .FILL x0029  ; ')'
        .FILL x000A  ; NL
        .FILL x0000  ; fin de cadena

;---------------- ECOLIN: R0 = buffer, R1 = longitud ----------------
ECOLIN  ST   R7, SVE
        ST   R0, EBUF
        ST   R1, ELEN
        LEA  R0, S_LEI
        JSR  PRSTR
        LD   R0, EBUF
        JSR  PRSTR              ; la cadena leida
        LEA  R0, S_LON
        JSR  PRSTR
        LD   R0, ELEN
        JSR  PRDEC              ; longitud en decimal
        LEA  R0, S_ENT
        JSR  PRSTR
        LD   R0, LTERM
        JSR  PRHEX              ; codigo de ENTER en hexadecimal
        LD   R0, CNLK
        TRAP x21
        LD   R7, SVE
        JMP  R7
SVE     .FILL x0000
EBUF    .FILL x0000
ELEN    .FILL x0000
CNLK    .FILL x000A

;---------------- LEELIN: lee una linea en el buffer R0 ----------------
;   Estado (puntero, cuenta) en memoria: TRAP puede alterar registros.
LEELIN  ST   R7, SVL
        ST   R0, LPTR           ; puntero de escritura
        AND  R0, R0, #0
        ST   R0, LCNT           ; cuenta <- 0
LCAR    JSR  LEECAR             ; R0 = tecla
        LD   R1, CM0A
        ADD  R1, R1, R0         ; tecla - x0A
        BRz  LFIN
        LD   R1, CM0D
        ADD  R1, R1, R0         ; tecla - x0D
        BRz  LFIN
        LD   R1, CM08
        ADD  R1, R1, R0         ; tecla - x08
        BRz  LBS
        LD   R1, CM7F
        ADD  R1, R1, R0         ; tecla - x7F
        BRz  LBS
        LD   R1, CM20
        ADD  R1, R1, R0         ; tecla - x20
        BRn  LCAR               ; < x20: caracter de control, se ignora
        LD   R1, CM7F
        ADD  R1, R1, R0         ; tecla - x7F
        BRzp LCAR               ; > x7E: se ignora
        LD   R1, LCNT           ; LCNT = caracteres TECLEADOS (incluye los de sobra)
        ADD  R1, R1, #-15       ; cuenta - 15
        BRzp LEXC               ; cuenta >= 15: este caracter no cabe, no se guarda
        LD   R1, LPTR
        STR  R0, R1, #0         ; guarda el caracter
        ADD  R1, R1, #1
        ST   R1, LPTR
LEXC    LD   R1, LCNT
        ADD  R1, R1, #1
        ST   R1, LCNT           ; la cuenta aumenta SIEMPRE (tambien con caracteres de sobra)
        TRAP x21                ; eco del caracter (R0 sigue siendo la tecla)
        BRnzp LCAR
LBS     LD   R1, LCNT           ; retroceso
        BRz  LCAR               ; nada que borrar (CC <- LD)
        ADD  R1, R1, #-1
        ST   R1, LCNT           ; cuenta nueva
        ADD  R1, R1, #-15       ; cuenta nueva - 15
        BRzp LBSEC              ; >= 15: el caracter borrado era de sobra (no esta en el buffer)
        LD   R1, LPTR
        ADD  R1, R1, #-1
        ST   R1, LPTR           ; el buffer pierde su ultimo caracter
LBSEC   LD   R0, CBS
        TRAP x21
        LD   R0, CSPL
        TRAP x21
        LD   R0, CBS
        TRAP x21                ; retrocede, borra con espacio, retrocede
        BRnzp LCAR
LFIN    ST   R0, LTERM          ; guarda la tecla ENTER recibida
        LD   R1, LPTR
        AND  R0, R0, #0
        STR  R0, R1, #0         ; terminador x0000
        LD   R0, CNLL
        TRAP x21                ; salto de linea
        LD   R0, LCNT           ; salida: R0 = caracteres tecleados (puede ser > 15)
        LD   R7, SVL
        JMP  R7
SVL     .FILL x0000
LPTR    .FILL x0000
LCNT    .FILL x0000
LTERM   .FILL x0000
CM0A    .FILL xFFF6             ; -x0A
CM0D    .FILL xFFF3             ; -x0D
CM08    .FILL xFFF8             ; -x08
CM7F    .FILL xFF81             ; -x7F
CM20    .FILL xFFE0             ; -x20
CBS     .FILL x0008
CSPL    .FILL x0020
CNLL    .FILL x000A

;---------------- LEECAR: R0 <- una tecla ----------------
LEECAR  ST   R7, SVC
        LD   R0, KBPOLL
        BRp  LPOLL              ; KBPOLL = 1: sondeo
        TRAP x20                ; GETC: R0 = tecla (sin eco)
        BRnzp LRET
LPOLL   LDI  R1, PKBSR          ; KBSR
        BRzp LPOLL              ; bit 15 = 0: aun no hay tecla
        LDI  R0, PKBDR          ; KBDR: R0 = tecla
LRET    LD   R7, SVC
        JMP  R7
SVC     .FILL x0000
KBPOLL  .FILL #0
PKBSR   .FILL xFE00
PKBDR   .FILL xFE02

;====================================================================
; ETAPA 2: CONVERSION ASCII -> Q7.8
;   CONVQ78 : R0 = direccion de la cadena (terminada en 0)
;             -> R0 = valor Q7.8 (solo valido si R1 = 0) ; R1 = codigo:
;                0 = correcto, 1 = entrada invalida, 2 = fuera de rango,
;                3 = mas de dos decimales
;             Gramatica: [+|-] digitos [ . digito [digito] ]   (sin espacios)
;             Valor = parte_entera*256 + floor(decimales_2cifras*256/100),
;             truncado hacia cero; se niega al final si hay signo '-'.
;             Subrutina HOJA: no usa JSR ni TRAP, no toca R7. Modifica R0-R6.
;   INFOQ   : R0 = cadena, R1 = etiqueta ('X' o 'Y') -> imprime la linea de resultado
;             y devuelve R0 = valor Q7.8, R1 = codigo de CONVQ78.
;====================================================================
;   separador
S_IQ1   .FILL x0020  ; ' '
        .FILL x003D  ; '='
        .FILL x0020  ; ' '
        .FILL x0022  ; '"'
        .FILL x0000  ; fin de cadena

;   flecha
S_IQ2   .FILL x0022  ; '"'
        .FILL x0020  ; ' '
        .FILL x0020  ; ' '
        .FILL x002D  ; '-'
        .FILL x003E  ; '>'
        .FILL x0020  ; ' '
        .FILL x0020  ; ' '
        .FILL x0000  ; fin de cadena

;   etiqueta Q7.8
S_IQ3   .FILL x0051  ; 'Q'
        .FILL x0037  ; '7'
        .FILL x002E  ; '.'
        .FILL x0038  ; '8'
        .FILL x0020  ; ' '
        .FILL x003D  ; '='
        .FILL x0020  ; ' '
        .FILL x0000  ; fin de cadena

;   abre decimal
S_IQ4   .FILL x0020  ; ' '
        .FILL x0020  ; ' '
        .FILL x0028  ; '('
        .FILL x0000  ; fin de cadena

;   cierra decimal
S_IQ5   .FILL x0029  ; ')'
        .FILL x000A  ; NL
        .FILL x0000  ; fin de cadena

;   error 1
S_E1    .FILL x0045  ; 'E'
        .FILL x0052  ; 'R'
        .FILL x0052  ; 'R'
        .FILL x004F  ; 'O'
        .FILL x0052  ; 'R'
        .FILL x003A  ; ':'
        .FILL x0020  ; ' '
        .FILL x0065  ; 'e'
        .FILL x006E  ; 'n'
        .FILL x0074  ; 't'
        .FILL x0072  ; 'r'
        .FILL x0061  ; 'a'
        .FILL x0064  ; 'd'
        .FILL x0061  ; 'a'
        .FILL x0020  ; ' '
        .FILL x0069  ; 'i'
        .FILL x006E  ; 'n'
        .FILL x0076  ; 'v'
        .FILL x0061  ; 'a'
        .FILL x006C  ; 'l'
        .FILL x0069  ; 'i'
        .FILL x0064  ; 'd'
        .FILL x0061  ; 'a'
        .FILL x0020  ; ' '
        .FILL x0028  ; '('
        .FILL x0066  ; 'f'
        .FILL x006F  ; 'o'
        .FILL x0072  ; 'r'
        .FILL x006D  ; 'm'
        .FILL x0061  ; 'a'
        .FILL x0074  ; 't'
        .FILL x006F  ; 'o'
        .FILL x003A  ; ':'
        .FILL x0020  ; ' '
        .FILL x005B  ; '['
        .FILL x002B  ; '+'
        .FILL x002D  ; '-'
        .FILL x005D  ; ']'
        .FILL x0045  ; 'E'
        .FILL x005B  ; '['
        .FILL x002E  ; '.'
        .FILL x0044  ; 'D'
        .FILL x005B  ; '['
        .FILL x0044  ; 'D'
        .FILL x005D  ; ']'
        .FILL x005D  ; ']'
        .FILL x0029  ; ')'
        .FILL x000A  ; NL
        .FILL x0000  ; fin de cadena

;   error 2
S_E2    .FILL x0045  ; 'E'
        .FILL x0052  ; 'R'
        .FILL x0052  ; 'R'
        .FILL x004F  ; 'O'
        .FILL x0052  ; 'R'
        .FILL x003A  ; ':'
        .FILL x0020  ; ' '
        .FILL x0066  ; 'f'
        .FILL x0075  ; 'u'
        .FILL x0065  ; 'e'
        .FILL x0072  ; 'r'
        .FILL x0061  ; 'a'
        .FILL x0020  ; ' '
        .FILL x0064  ; 'd'
        .FILL x0065  ; 'e'
        .FILL x0020  ; ' '
        .FILL x0072  ; 'r'
        .FILL x0061  ; 'a'
        .FILL x006E  ; 'n'
        .FILL x0067  ; 'g'
        .FILL x006F  ; 'o'
        .FILL x0020  ; ' '
        .FILL x0028  ; '('
        .FILL x002D  ; '-'
        .FILL x0031  ; '1'
        .FILL x0032  ; '2'
        .FILL x0038  ; '8'
        .FILL x0020  ; ' '
        .FILL x0061  ; 'a'
        .FILL x0020  ; ' '
        .FILL x0031  ; '1'
        .FILL x0032  ; '2'
        .FILL x0037  ; '7'
        .FILL x002E  ; '.'
        .FILL x0039  ; '9'
        .FILL x0039  ; '9'
        .FILL x0036  ; '6'
        .FILL x0030  ; '0'
        .FILL x0039  ; '9'
        .FILL x0033  ; '3'
        .FILL x0037  ; '7'
        .FILL x0035  ; '5'
        .FILL x0029  ; ')'
        .FILL x000A  ; NL
        .FILL x0000  ; fin de cadena

;   error 3
S_E3    .FILL x0045  ; 'E'
        .FILL x0052  ; 'R'
        .FILL x0052  ; 'R'
        .FILL x004F  ; 'O'
        .FILL x0052  ; 'R'
        .FILL x003A  ; ':'
        .FILL x0020  ; ' '
        .FILL x006D  ; 'm'
        .FILL x0061  ; 'a'
        .FILL x0073  ; 's'
        .FILL x0020  ; ' '
        .FILL x0064  ; 'd'
        .FILL x0065  ; 'e'
        .FILL x0020  ; ' '
        .FILL x0064  ; 'd'
        .FILL x006F  ; 'o'
        .FILL x0073  ; 's'
        .FILL x0020  ; ' '
        .FILL x0064  ; 'd'
        .FILL x0065  ; 'e'
        .FILL x0063  ; 'c'
        .FILL x0069  ; 'i'
        .FILL x006D  ; 'm'
        .FILL x0061  ; 'a'
        .FILL x006C  ; 'l'
        .FILL x0065  ; 'e'
        .FILL x0073  ; 's'
        .FILL x000A  ; NL
        .FILL x0000  ; fin de cadena
;   sangria
S_SP2   .FILL x0020  ; ' '
        .FILL x0020  ; ' '
        .FILL x0000  ; fin de cadena

;---------------- INFOQ ----------------
INFOQ   ST   R7, SVQI
        ST   R1, IQLAB
        ST   R0, IQBUF
        ADD  R1, R1, #0         ; CC <- etiqueta
        BRz  IQSIL              ; etiqueta 0: modo normal (solo se informan errores)
        LD   R0, IQLAB
        TRAP x21                ; etiqueta
        LEA  R0, S_IQ1
        JSR  PRSTR              ; ' = "'
        LD   R0, IQBUF
        JSR  PRSTR              ; la cadena ingresada
        LEA  R0, S_IQ2
        JSR  PRSTR              ; '"  ->  '
        LD   R0, IQBUF
        JSR  CONVQ78            ; R0 = valor, R1 = codigo
        ST   R0, IQVAL
        ST   R1, IQCOD
        ADD  R1, R1, #0         ; CC <- codigo
        BRp  IQERR
        LEA  R0, S_IQ3
        JSR  PRSTR              ; 'Q7.8 = '
        LD   R0, IQVAL
        JSR  PRHEX
        LEA  R0, S_IQ4
        JSR  PRSTR
        LD   R0, IQVAL
        JSR  PRQ78              ; valor decimal interpretado
        LEA  R0, S_IQ5
        JSR  PRSTR
        BRnzp IQFIN
IQSIL   LD   R0, IQBUF
        JSR  CONVQ78            ; R0 = valor, R1 = codigo
        ST   R0, IQVAL
        ST   R1, IQCOD
        ADD  R1, R1, #0         ; CC <- codigo
        BRz  IQFIN              ; correcto: no se imprime nada
        LEA  R0, S_SP2
        JSR  PRSTR              ; sangria de dos espacios antes del mensaje
IQERR   LD   R1, IQCOD
        ADD  R1, R1, #-2        ; codigo - 2
        BRz  IQE2
        BRp  IQE3
        LEA  R0, S_E1           ; codigo 1
        BRnzp IQMSG
IQE2    LEA  R0, S_E2
        BRnzp IQMSG
IQE3    LEA  R0, S_E3
IQMSG   JSR  PRSTR
IQFIN   LD   R0, IQVAL          ; salida: R0 = valor (0 si hubo error)
        LD   R1, IQCOD          ;         R1 = codigo (0 = correcto)
        LD   R7, SVQI
        JMP  R7                 ; (RET)
SVQI    .FILL x0000
IQLAB   .FILL x0000
IQBUF   .FILL x0000
IQVAL   .FILL x0000
IQCOD   .FILL x0000

;---------------- CONVQ78 ----------------
;   R0 = puntero al caracter actual ; R2 = I (parte entera, recortada a 129 si pasa de 128)
;   R4 = F (decimales como entero 0..99) ; R5 = n.o de decimales ; R1,R3,R6 = temporales
CONVQ78 AND  R1, R1, #0
        ST   R1, CVNEG          ; negativo = 0
        ST   R1, CVPT           ; punto visto = 0
        ST   R1, CVNI           ; n.o de digitos enteros = 0
        ST   R1, CVOV           ; parte entera > 128 = 0
        AND  R2, R2, #0         ; I = 0
        AND  R4, R4, #0         ; F = 0
        AND  R5, R5, #0         ; ndec = 0
        LDR  R1, R0, #0         ; primer caracter
        LD   R3, CMMIN
        ADD  R3, R3, R1         ; c - '-'
        BRnp CVNOMEN
        AND  R6, R6, #0
        ADD  R6, R6, #1
        ST   R6, CVNEG          ; negativo = 1
        ADD  R0, R0, #1
        BRnzp CVLAZO
CVNOMEN LD   R3, CMPLU
        ADD  R3, R3, R1         ; c - '+'
        BRnp CVLAZO
        ADD  R0, R0, #1         ; se salta el '+'
CVLAZO  LDR  R1, R0, #0         ; caracter ; CC
        BRz  CVFIN              ; fin de cadena
        LD   R3, CMPTO
        ADD  R3, R3, R1         ; c - '.'
        BRnp CVDIG
        LD   R3, CVPT           ; es '.'
        BRp  CVE1               ; segundo punto
        LD   R3, CVNI
        BRz  CVE1               ; sin parte entera
        AND  R3, R3, #0
        ADD  R3, R3, #1
        ST   R3, CVPT
        ADD  R0, R0, #1
        BRnzp CVLAZO
CVDIG   LD   R3, CM30
        ADD  R1, R1, R3         ; d = c - '0'
        BRn  CVE1               ; < '0'
        ADD  R3, R1, #-9        ; d - 9
        BRp  CVE1               ; > '9'
        LD   R3, CVPT
        BRp  CVDEC              ; ya hay punto: digito decimal
        ADD  R3, R2, R2         ; 2I
        ADD  R6, R3, R3         ; 4I
        ADD  R6, R6, R6         ; 8I
        ADD  R2, R3, R6         ; 10I
        ADD  R2, R2, R1         ; I = 10I + d
        LD   R3, CM128
        ADD  R3, R2, R3         ; I - 128
        BRnz CVNI1              ; I <= 128
        LD   R2, C129           ; recorta I = 129 ...
        AND  R3, R3, #0
        ADD  R3, R3, #1
        ST   R3, CVOV           ; ... y marca desborde
CVNI1   LD   R3, CVNI
        ADD  R3, R3, #1
        ST   R3, CVNI           ; un digito entero mas
        ADD  R0, R0, #1
        BRnzp CVLAZO
CVDEC   ADD  R3, R5, #-2        ; ndec - 2
        BRzp CVE3               ; ya habia 2 decimales: este es el tercero
        ADD  R5, R5, #1         ; ndec++
        ADD  R3, R5, #-1        ; ndec - 1
        BRz  CVD1               ; primer decimal
        ADD  R4, R4, R1         ; segundo decimal: F = F + d
        BRnzp CVSIG
CVD1    ADD  R3, R1, R1         ; 2d
        ADD  R6, R3, R3         ; 4d
        ADD  R6, R6, R6         ; 8d
        ADD  R4, R3, R6         ; F = 10d  (un solo decimal: 5 -> 50)
CVSIG   ADD  R0, R0, #1
        BRnzp CVLAZO
CVFIN   LD   R3, CVNI
        BRz  CVE1               ; "", "-", "+": sin parte entera
        LD   R3, CVPT
        BRz  CVSINP
        ADD  R3, R5, #0         ; ndec
        BRz  CVE1               ; "5." (punto sin decimales)
CVSINP  LD   R3, CVOV
        BRp  CVE2               ; parte entera > 128
        LD   R3, CM128
        ADD  R3, R2, R3         ; I - 128
        BRn  CVMAG              ; I <= 127: siempre representable
        LD   R3, CVNEG          ; I = 128
        BRz  CVE2               ; +128.xx: fuera de rango
        ADD  R4, R4, #0         ; CC <- F
        BRnp CVE2               ; -128.01 o menos: fuera de rango
        LD   R0, C8000V         ; -128.00 = x8000
        BRnzp CVOK
CVMAG   ADD  R3, R4, #0         ; V = F
        ADD  R3, R3, R3
        ADD  R3, R3, R3
        ADD  R3, R3, R3
        ADD  R3, R3, R3
        ADD  R3, R3, R3
        ADD  R3, R3, R3
        ADD  R3, R3, R3
        ADD  R3, R3, R3         ; V = F*256 (<= 25344)
        AND  R6, R6, #0         ; q = 0
        LD   R1, CM100
CVDIV   ADD  R3, R3, R1         ; V - 100 ; CC
        BRn  CVDFIN
        ADD  R6, R6, #1         ; q++
        BRnzp CVDIV
CVDFIN  ADD  R2, R2, R2         ; I*256 (8 duplicaciones, I <= 127)
        ADD  R2, R2, R2
        ADD  R2, R2, R2
        ADD  R2, R2, R2
        ADD  R2, R2, R2
        ADD  R2, R2, R2
        ADD  R2, R2, R2
        ADD  R2, R2, R2
        ADD  R0, R2, R6         ; magnitud = I*256 + q  (<= 32765)
        LD   R3, CVNEG
        BRz  CVOK
        NOT  R0, R0
        ADD  R0, R0, #1         ; negativo: -magnitud
CVOK    AND  R1, R1, #0         ; codigo 0
        JMP  R7                 ; (RET)
CVE1    AND  R0, R0, #0
        AND  R1, R1, #0
        ADD  R1, R1, #1         ; codigo 1
        JMP  R7
CVE2    AND  R0, R0, #0
        AND  R1, R1, #0
        ADD  R1, R1, #2         ; codigo 2
        JMP  R7
CVE3    AND  R0, R0, #0
        AND  R1, R1, #0
        ADD  R1, R1, #3         ; codigo 3
        JMP  R7
CVNEG   .FILL x0000
CVPT    .FILL x0000
CVNI    .FILL x0000
CVOV    .FILL x0000
CMMIN   .FILL xFFD3             ; -'-'
CMPLU   .FILL xFFD5             ; -'+'
CMPTO   .FILL xFFD2             ; -'.'
CM30    .FILL xFFD0             ; -'0'
CM128   .FILL xFF80             ; -128
CM100   .FILL xFF9C             ; -100
C129    .FILL x0081
C8000V  .FILL x8000

        .END

```

</details>

### 2.2 Módulo para la calculadora: `booth.asm` y `main.asm`

`booth.asm` es el archivo que se publica en la plataforma. Conserva el algoritmo de `BOOTH16v3.ASM` (bucle de Booth, extensión E, `SHR1`/`ASR1`, conversión P>>8 y cálculo de OVF) y solo cambia la interfaz. `main.asm` es el programa de prueba local.

<details>
<summary><code>booth.asm</code></summary>

```asm
;====================================================================
; booth.asm - Modulo "booth": multiplicador Booth 16x16 en Q7.8
; Funcion publica: MULT_BOOTH      (se importa como BOOTH-MULT_BOOTH)
;
; Derivado de BOOTH16v3.ASM. El algoritmo (bucle de Booth, extension E,
; SHR1/ASR1, conversion P>>8 y calculo de OVF) es el mismo del original.
; Solo se cambio la interfaz: sin teclado ni pantalla, sin TRAP, sin
; HALT, sin .ORIG, y con la convencion de llamada de la calculadora.
;
; CONVENCION DE LLAMADA
;   Entrada : R0 = X, primer operando  (Q7.8, 16 bits con signo)
;             R1 = Y, segundo operando (Q7.8, 16 bits con signo)
;   Salida  : R0 = RES = P[23:8]       (producto reducido a Q7.8)
;   Conserva: R1, R2, R3, R4, R5 (se apilan y se restauran)
;             R6 vuelve con el mismo valor que tenia al entrar
;             R7 se apila al entrar y se restaura antes de RET
;   Destruye: R0 (es el resultado)
;   CC      : al retornar reflejan el signo de RES (ultimo LD es R0).
;
; PILA (R6 crece hacia direcciones menores). Marco de 7 palabras:
;     R6+0 = R1   R6+1 = R2   R6+2 = R3   R6+3 = R4
;     R6+4 = R5   R6+5 = R7   R6+6 = CNT (contador del bucle)
;   CNT reemplaza al uso de R6 como contador del original, porque R6 es
;   ahora el puntero de pila. R6 solo se usa como base de STR/LDR y para
;   reservar/liberar el marco; nunca se inicializa ni se usa como
;   registro de trabajo. Al retornar no queda nada apilado.
;
; R7: se apila al entrar porque las JSR internas (SHR1/ASR1) lo
;   sobrescriben; el RET final usa el R7 original restaurado.
;
; DATOS AUXILIARES (solo diagnostico; NO forman parte de la interfaz):
;   PH   = palabra alta del producto de 32 bits (Q15.16)
;   PL   = palabra baja del producto de 32 bits
;   RES  = copia de P[23:8]
;   OVFV = 0 sin desbordamiento, 1 si PH esta fuera de [-128,127]
;          (con OVFV = 1 el valor de R0 no representa el producto)
;   El programa principal de la calculadora no necesita leerlos.
;   Son datos del modulo, por lo tanto NO es reentrante.
;
; ENLAZADOR: sin .ORIG, sin direcciones absolutas, todo es relativo al
;   PC dentro de este archivo. Las JSR a SHR1/ASR1 son internas y
;   cortas. Ninguna etiqueta contiene '-'.
;====================================================================

MULT_BOOTH
        ADD  R6, R6, #-7        ; reservar marco en la pila
        STR  R1, R6, #0         ; apilar R1..R5 y R7
        STR  R2, R6, #1
        STR  R3, R6, #2
        STR  R4, R6, #3
        STR  R5, R6, #4
        STR  R7, R6, #5

        ST   R0, MCAND          ; M <- X
        ADD  R5, R1, #0         ; Q <- Y
        NOT  R1, R0
        ADD  R1, R1, #1         ; MNEG = NOT(M) + 1  (mod 2^16)
        ST   R1, MNEG
        AND  R4, R4, #0         ; A <- 0
        AND  R0, R0, #0
        ST   R0, QM1            ; QM1 <- 0
        ADD  R0, R0, #-16
        STR  R0, R6, #6         ; CNT <- -16 (en la pila)

;---------------- bucle de Booth: 16 iteraciones (sin cambios) ----------------
BOOTH   AND  R0, R5, #1         ; R0 = q0 = Q[0]
        ST   R0, Q0SAVE
        NOT  R0, R0
        ADD  R0, R0, #1         ; R0 = -q0
        LD   R1, QM1
        ADD  R0, R0, R1         ; R0 = QM1 - q0 ; CC <- signo de d
        BRz  SINSUM             ; d = 0
        BRn  RESTA              ; d = -1  (BR no altera CC: el 2.o BR ve el mismo CC)
        LD   R1, MCAND          ; d = +1 : A <- A + M
        ADD  R4, R4, R1
        BRnzp SINSUM
RESTA   LD   R1, MNEG           ; d = -1 : A <- A - M = A + MNEG
        ADD  R4, R4, R1
;   aqui R4 = patron de A' (acumulador antes de desplazar)
SINSUM  AND  R3, R4, #1         ; a0 = A'[0]
        NOT  R3, R3
        ADD  R3, R3, #1         ; R3 = -a0 : negativo <=> a0 = 1
        ADD  R0, R5, #0         ; X = Q
        JSR  SHR1               ; R0 = {a0, Q[15:1]}
        ADD  R5, R0, #0         ; Q <- R0
;   extension E de A'
        ADD  R0, R4, #0         ; X = A'
        ADD  R3, R4, #0         ; R3 = A' ; CC <- signo de A'
        BRzp ECERO              ; A' >= 0 -> E = 0
        ADD  R1, R4, R4         ; con A' < 0: A'+A' = 0  <=>  A' = x8000
        BRnp ECUNO              ; distinto de x8000 -> E = 1 (R3 = A' es negativo)
ECERO   AND  R3, R3, #0         ; E = 0 (A' >= 0, o A' = x8000)
ECUNO   JSR  SHR1               ; R0 = {E, A'[15:1]}
        ADD  R4, R0, #0         ; A <- R0
        LD   R0, Q0SAVE
        ST   R0, QM1            ; QM1 <- q0 anterior
        LDR  R0, R6, #6
        ADD  R0, R0, #1         ; CNT <- CNT + 1 ; CC <- CNT
        STR  R0, R6, #6         ; (STR no altera CC)
        BRn  BOOTH              ; repite mientras CNT < 0 (16 vueltas)

;---------------- producto bruto: PH:PL = A:Q ----------------
        ST   R4, PH
        ST   R5, PL

;---------------- Q7.8: RES = P[23:8] = P >>a 8 ----------------
;   8 veces: {R4:R5} <- {R4:R5} >>a 1   (R4 = hi, R5 = lo)
;   R4:R5 se destruye; el producto sigue en PH/PL
        AND  R0, R0, #0
        ADD  R0, R0, #-8
        STR  R0, R6, #6         ; CNT <- -8
CONV    AND  R3, R4, #1         ; hi[0]
        NOT  R3, R3
        ADD  R3, R3, #1         ; R3 = -hi[0] : negativo <=> hi[0] = 1
        ADD  R0, R5, #0         ; X = lo
        JSR  SHR1               ; R0 = {hi[0], lo[15:1]}
        ADD  R5, R0, #0         ; lo <- R0
        ADD  R0, R4, #0         ; X = hi
        JSR  ASR1               ; R0 = hi >>a 1  (relleno = signo de hi)
        ADD  R4, R0, #0         ; hi <- R0
        LDR  R0, R6, #6
        ADD  R0, R0, #1         ; CNT <- CNT + 1 ; CC <- CNT
        STR  R0, R6, #6
        BRn  CONV               ; 8 vueltas
        ST   R5, RES            ; RES = lo = P[23:8]

;---------------- OVF = ((PH + x0080) AND xFF00) != 0 ----------------
        LD   R0, PH
        LD   R1, C0080
        ADD  R0, R0, R1         ; PH + 128
        LD   R1, CFF00
        AND  R0, R0, R1         ; byte alto de (PH + 128) ; CC
        BRz  GOVF               ; 0 -> OVF = 0 (R0 ya vale 0)
        AND  R0, R0, #0
        ADD  R0, R0, #1         ; OVF = 1
GOVF    ST   R0, OVFV

;---------------- epilogo: restaurar registros y volver ----------------
        LDR  R1, R6, #0         ; desapilar en el mismo orden
        LDR  R2, R6, #1
        LDR  R3, R6, #2
        LDR  R4, R6, #3
        LDR  R5, R6, #4
        LDR  R7, R6, #5         ; direccion de retorno original
        ADD  R6, R6, #7         ; R6 vuelve a su valor de entrada
        LD   R0, RES            ; R0 = RES (salida) ; CC <- signo de RES
        RET

;---------------- datos del modulo ----------------
;   diagnostico (no forman parte de la interfaz)
PH      .FILL x0000
PL      .FILL x0000
RES     .FILL x0000
OVFV    .FILL x0000
;   internos del algoritmo
MCAND   .FILL x0000
MNEG    .FILL x0000
QM1     .FILL x0000
Q0SAVE  .FILL x0000
C0080   .FILL x0080
CFF00   .FILL xFF00
C8000   .FILL x8000

;---------------- SHR1 / ASR1 (de SHR1 del original; sin cambios) ----------------
;   Entrada: R0 = X ; R3 = relleno (negativo -> 1, cero -> 0).
;            ASR1 toma el relleno de X (R3 <- X), o sea desplazamiento aritmetico.
;   Salida : R0 = {relleno, X[15:1]}. Destruye R1, R2, R3 (R7 lo fija la JSR).
;   (LSR1 del original no se usa en Booth y se omitio.)
ASR1    ADD  R3, R0, #0
SHR1    ADD  R1, R0, #0         ; W <- X
        AND  R2, R2, #0
        ADD  R2, R2, #1         ; R <- 1 (centinela en bit 0)
SLAZO   ADD  R2, R2, R2         ; R <- 2R
        ADD  R1, R1, #0         ; CC <- signo de W (= bit 15)
        BRzp SNOBIT
        ADD  R2, R2, #1         ; bit 15 de W era 1
SNOBIT  ADD  R1, R1, R1         ; W <- 2W
        ADD  R2, R2, #0         ; CC <- signo de R (= centinela en bit 15?)
        BRzp SLAZO
        ADD  R3, R3, #0         ; CC <- relleno
        BRn  SFIN               ; relleno=1: el centinela ya es el bit 15
        LD   R3, C8000
        ADD  R2, R2, R3         ; relleno=0: borra el centinela
SFIN    ADD  R0, R2, #0
        RET                     ; vuelve por R7 (fijado por la JSR interna)

        .END
```

</details>

<details>
<summary><code>main.asm</code></summary>

```asm
;====================================================================
; main.asm - Programa principal de PRUEBA LOCAL para el modulo booth
; En la plataforma: crear booth.asm y main.asm, clic derecho sobre
; main.asm -> "Usar como entrada", Ensamblar, Ejecutar.
; Calcula 12.5 x 3.75 (cambiar OP_X / OP_Y para otros casos).
; No toca R6: lo deja como lo inicializa el simulador.
;====================================================================
        .ORIG x3000
        .EXTERNAL BOOTH-MULT_BOOTH      ; etiqueta MULT_BOOTH de booth.asm

        LD   R0, OP_X                   ; R0 = X en Q7.8
        LD   R1, OP_Y                   ; R1 = Y en Q7.8
        LD   R5, BOOTH_PTR              ; direccion completa de 16 bits
        JSRR R5                         ; llamada entre archivos
        ST   R0, RESULTADO              ; R0 = RES en Q7.8
        HALT                            ; fin del programa principal

OP_X      .FILL x0C80                   ; 12.5   en Q7.8
OP_Y      .FILL x03C0                   ; 3.75   en Q7.8
RESULTADO .FILL x0000                   ; esperado x2EE0 (= 46.875)
BOOTH_PTR .FILL BOOTH-MULT_BOOTH        ; .FILL + JSRR en toda llamada externa
        .END
```

</details>

`proyecto_completo.asm` (programa principal con autoverificación + módulo en un solo archivo) está disponible en el repositorio y no se repite aquí.

---

## 3. Estado en el simulador del grupo 8

| Pregunta | Respuesta |
|---|---|
| ¿Funciona en el simulador del grupo 8 (<https://lc3.lgrum.xyz/>)? | **Sí.** fue probado en ese simulador y funciona. |
| ¿Se probó en otros simuladores? | **Sí**, en varios simuladores web, donde también funciona. |

---

## 4. Bitácora de avances

**Multiplicador Booth en formato Q7.8 – LC-3**

- **Proyecto:** Implementación de un multiplicador mediante el algoritmo de Booth.
- **Arquitectura:** LC-3.
- **Período de trabajo:** 27/10/2026 al 07/11/2026 (fechas estimadas).

#### Registro de actividades

| Fecha | Actividad realizada |
|---|---|
| 27/10/2026 | Inicio del laboratorio. Investigación del formato de punto fijo Q7.8, su representación binaria y el funcionamiento del algoritmo de Booth. |
| 28/10/2026 | Análisis de las operaciones necesarias para multiplicar números con signo y obtener el resultado completo de 32 bits. |
| 29/10/2026 | Desarrollo de una primera versión del algoritmo en lenguaje C, incorporando el ingreso de operandos y su conversión a Q7.8. |
| 30/10/2026 | Implementación del algoritmo de Booth en ensamblador LC-3. Desarrollo de las rutinas auxiliares para realizar desplazamientos de bits. |
| 02/11/2026 | Adaptación del programa para convertirlo en una subrutina reutilizable, definiendo registros de entrada, salida y preservación. |
| del 03/11/2026 al 04/11/2026 | Organización del programa principal de prueba y de la subrutina en archivos separados. Preparación de una versión completa para el simulador del grupo 8. |
| 05/11/2026 | Revisión de una nueva versión del código y detección de un posible error en el desplazamiento aritmético para el valor x8000. Definición de casos de prueba. |
| 06/11/2026 | Adaptación del multiplicador a **módulo de la calculadora** (`booth.asm`) según la guía oficial: operandos en R0 y R1, resultado en R0, R1–R5 conservados mediante la pila con R6, R7 apilado por las llamadas internas, sin `.ORIG`, `HALT` ni `TRAP`. Armado de `main.asm` y `proyecto_completo.asm`. |
| 07/11/2026 | Fecha prevista de finalización: corrección, pruebas en el simulador, comparación de resultados y preparación de los archivos definitivos para GitHub. |

#### Objetivos alcanzados

- Comprensión de la representación Q7.8.
- Desarrollo del algoritmo de Booth en lenguaje C.
- Implementación del multiplicador en ensamblador LC-3.
- Adaptación del código a una subrutina reutilizable.
- Conversión a módulo (`booth.asm`) según la guía de la calculadora: convención de llamada, pila con R6, llamada externa con `.FILL` + `JSRR`.
- Definición de las entradas, salidas y registros utilizados.
- Organización del programa principal y la subrutina.
- Revisión de posibles errores y preparación de casos de prueba.

#### Problemas y dificultades

- Una de las principales dificultades fue implementar los desplazamientos aritméticos, ya que LC-3 no dispone de una instrucción directa para realizarlos.
- También fue necesario adaptar el programa original a las convenciones de subrutinas, especialmente en la preservación de registros y el retorno al programa principal.
- Durante la revisión final se detectó un posible error en el tratamiento del valor x8000, por lo que se propuso una modificación que deberá verificarse mediante pruebas. La comparación posterior de la lógica de Booth con el producto exacto (modelo del algoritmo, todas las combinaciones de operandos de 16 bits) y la verificación auxiliar del módulo no mostraron diferencias, incluso con `x8000` como operando.
