# Guía de uso del toolchain ISA-NZP

Este documento reúne los comandos y flujos de trabajo principales para ensamblar, simular, probar módulos individuales y generar informes ordenados.

## Estructura de carpetas recomendada

```text
proyecto/
├── isa.py
├── isa_lc3.py
├── ensamblador.py
├── simulador.py
├── benchmark.py
├── casos.json
├── lib/                        # Módulos (.asm) de la librería
├── principales/                # Programas principales (p. ej., main_grupo27.asm)
├── build/
│   ├── modulos/
│   │   ├── bin/
│   │   ├── hex/
│   │   ├── lst/
│   │   └── sym/
│   └── principales/
│       ├── bin/
│       ├── hex/
│       ├── lst/
│       └── sym/
└── informes/
    └── informe_benchmark.md
```

---

## 1. Benchmark completo (`benchmark.py`)

Ejecuta el ensamblado y la simulación de los `.asm` de `lib/` (armando arneses automáticamente para los módulos que terminan en `RET`) y también ensambla y simula programas principales.

```bash
# Ejecución estándar (usa casos.json si existe y busca main*.asm en la carpeta madre o en principales/)
python benchmark.py lib --main principales/main_grupo27.asm

# Incluir subcarpetas dentro de lib/ (-r), exportar CSV y mostrar detalle verboso (-v)
python benchmark.py lib -r --main principales/main_grupo27.asm --csv informes/resultados.csv -v

# Ejecutar solo los módulos (sin programas principales)
python benchmark.py lib --sin-principal

# Forzar modo de ISA (clasico o nuevo), registros iniciales y límite de instrucciones
python benchmark.py lib --modo clasico --regs R0=5,R1=0x0180 --max 5000000

# Pasar entrada por texto (admite secuencias escapadas como \n) para GETC/IN
python benchmark.py lib --entrada "1A\n"

# Guardar salidas de forma plana en <salida-dir> en lugar de separar por tipo y formato
python benchmark.py lib --sin-organizar
```

---

## 2. Ensamblador (`ensamblador.py`)

Permite ensamblar un programa principal junto con sus dependencias `.EXTERNAL` o procesar una carpeta completa por lotes.

```bash
# Ensamblar un programa principal resolviendo .EXTERNAL en lib/ y organizando por formato
python ensamblador.py principales/main_grupo27.asm --lib lib -o build/principales/main_grupo27 --organizar

# Ensamblar cada .asm de una carpeta por separado
python ensamblador.py --carpeta lib -d build/modulos -r --organizar

# Habilitar SQR si el grupo la utiliza (deshabilitada por defecto)
python ensamblador.py principales/main_grupo27.asm --lib lib --permitir-sqr
```

---

## 3. Simulador (`simulador.py`)

Ejecuta archivos `.bin` o `.hex` (detecta automáticamente si el binario es LC-3 clásico por su cabecera o pertenece a la ISA-NZP byte-addressable).

```bash
# Simular un binario con traza paso a paso y perfil por etiqueta (usa el .sym correspondiente)
python simulador.py build/principales/bin/main_grupo27.bin --traza --perfil

# Simular indicando registros iniciales, entrada, límite de instrucciones y volcado de memoria (DIR:CANT)
python simulador.py programa.bin --regs R0=5,R1=0x180 --entrada "hola\n" --max 10000000 --volcar 0x4000:8

# Simular todos los .bin de una carpeta en modo lote
python simulador.py --carpeta build/modulos
```

---

## 4. Cómo trabajar con un módulo específico

### Opción A: Probarlo aislado con arnés mediante `casos.json`

En `casos.json` podés omitir el resto con `"omitir": true` en `"*"` y habilitar solo el módulo que querés evaluar (recordando poner `"omitir": false` en la clave del módulo):

```json
{
  "*": {
    "omitir": true
  },
  "mi_modulo": {
    "omitir": false,
    "tipo": "modulo",
    "entry": "MI_ETIQUETA",
    "regs": {
      "R0": 6,
      "R1": 3
    },
    "esperado": {
      "R0": "0x0012"
    }
  }
}
```

Luego ejecutá:

```bash
python benchmark.py lib --sin-principal
```

### Opción B: Ensamblar y simular el módulo directamente

Si simulás una subrutina que termina en `RET` (`JMP R7`) sin arnés, recordá inicializar `R7` con una dirección válida que apunte a `HALT` para evitar un error de retorno con `R7=0`:

```bash
# 1. Ensamblar el módulo
python ensamblador.py lib/mi_modulo.asm --lib lib -o build/mi_modulo

# 2. Simular pasando registros iniciales y dirección de retorno en R7
python simulador.py build/mi_modulo.bin --regs R0=6,R1=3,R7=0x4000 --traza
```

### Opción C: Llamarlo desde un programa principal

Declará la etiqueta con `.EXTERNAL` en el archivo principal (por ejemplo, `principales/main_grupo27.asm`), cargá su dirección e invocala con `JSRR`. Después ensamblá y simulá el principal:

```bash
python ensamblador.py principales/main_grupo27.asm --lib lib -o build/principales/main_grupo27 --organizar
python simulador.py build/principales/bin/main_grupo27.bin --perfil
```