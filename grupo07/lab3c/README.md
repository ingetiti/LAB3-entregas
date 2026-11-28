# - Simulador y ensamblador · Grupo 7 - 
# Nombre de la ISA: LB-3 (Little Byte)
Ensamblador multimódulo y simulador funcional implementados en HTML, CSS y JavaScript (ISA-LC3 Studio). No requieren instalación ni servidor.

## Cómo ejecutar

**En línea:** https://alvaromartinzabala-ing.github.io/LC-3_lab3c/ (preferiblemente usar esta opción).

**Local:** abrí `index.html` con un navegador. Requiere conexión a internet, al abrirlo desde disco, el navegador puede impedir la carga automática del benchmark; en ese caso usá **Cargar .zip** y seleccioná `benchmark/benchmark_g7.zip`.

Al abrir la página, el benchmark se carga automáticamente. Si no aparece, usá **Cargar .zip** y seleccioná `benchmark/benchmark_g7.zip`. También se pueden soltar los archivos `.asm` o el `.zip` sobre la página.
 
## Cómo probar el benchmark

1. Verificá que el benchmark esté cargado en el panel **Ensamblador** (pestaña `main_grupo27` y los módulos de `lib/`).
2. Presioná **Ensamblar a Hex/Bin** y revisá que no haya errores ni avisos.
3. Presioná **Cargar en Simulador**.
4. Presioná **Ejecutar (Run)** (o **Paso a Paso (Step)** para avanzar de a una instrucción).

El benchmark está configurado para correr **en modo automático**: ejecuta un caso de prueba por cada opción del menú y termina solo en `HALT`. La salida aparece en la **Consola E/S**.

### Resultados esperados (modo automático)

En el panel **Métricas de desempeño**:

| Métrica | Valor |
| --- | --- |
| Instrucciones (sin SO) | 47.306 |
| Instrucciones (con SO) | 69.380 |
| Bytes cargados | 14.006 |
| Bytes guardados | 665 |
| Lecturas de datos | 8.211 |
| Escrituras de datos | 2.933 |

### Modo menú interactivo de la calculadora

En la pestaña `main_grupo27`, dentro de `main`, comentá con `;` la línea
`LEA R0 programa_del_menu_completo`. Así queda activa solo `AND R0 R0 #0`, que muestra el menú.
Luego volvé a **Ensamblar a Hex/Bin**, **Cargar en Simulador** y **Ejecutar (Run)**.
Para volver al modo automático, quitá el `;`. La consola funciona tecla por tecla.
## Salida de ensamblado

Después de ensamblar se puede descargar el código máquina con **Descargar .hex** o **Descargar .bin** (los dos primeros bytes corresponden a la dirección de origen del programa).

## Verificación del simulador

El botón **Autotest** ejecuta la batería de pruebas integrada (108 pruebas).

## Contenido de la entrega

- `index.html`: página principal del simulador.
- `ensamblador/`: archivos del ensamblador.
- `simulador/`: interfaz y archivos del simulador.
- `benchmark/benchmark_g7.zip`: benchmark listo para cargar (37 módulos).
- `benchmark/benchmark_g7/: los archivos `.asm` extraídos del ZIP (`main_grupo27.asm` y `lib/`).
- `ejemplos/`: ejemplos de respaldo.

Conservá los nombres y la estructura de los módulos `.asm` al extraerlos, porque el ensamblador resuelve las dependencias entre módulos (`.EXTERNAL`) por nombre de archivo.
