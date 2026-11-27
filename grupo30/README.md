# Instructivo de Uso — Simulador y Ensamblador Skynet (Grupo 30)

## 1. Requisitos

- **Python 3.10 o superior** (no requiere instalar paquetes externos con `pip`; solo utiliza la biblioteca estándar de Python).
- Para la interfaz gráfica (`gui.py`), se utiliza `tkinter` (incluido por defecto en la instalación estándar de Python en Windows).

## 2. Ubicación para ejecutar los comandos

Todos los comandos siguientes deben ejecutarse desde una terminal parada **dentro de la carpeta `grupo30/`**:

```powershell
cd grupo30
```

## 3. Cómo ensamblar el benchmark (`.asm` -> `.hex`)

El ensamblador (`assembler.py`) une el programa principal (`benchmark_opt/main_grupo27.asm`) junto con todas las subrutinas de `benchmark_opt/lib/*.asm` y genera el archivo ensamblado `benchmark_opt/benchmark.hex`:

**En PowerShell (Windows):**
```powershell
python assembler.py benchmark_opt/main_grupo27.asm (Get-ChildItem benchmark_opt/lib/*.asm | Sort-Object Name) -o benchmark_opt/benchmark.hex
```

**En Bash (Linux / macOS / Git Bash):**
```bash
python assembler.py benchmark_opt/main_grupo27.asm benchmark_opt/lib/*.asm -o benchmark_opt/benchmark.hex
```

*(También es posible generar además la imagen binaria agregando `--bin benchmark_opt/benchmark.bin` al final del comando).*

## 4. Cómo ejecutar el benchmark en el simulador

El repositorio ya incluye el benchmark ensamblado en `benchmark_opt/benchmark.hex`, listo para ejecutarse directamente.

### Opción A — Simulador por consola (`sim.py`)

**Modo estándar:**
```powershell
python sim.py benchmark_opt/benchmark.hex
```

**Modo contabilizando las rutinas del sistema operativo (`os_rutinas.asm`):**
```powershell
python sim.py benchmark_opt/benchmark.hex --contar-os
```

### Opción B — Interfaz gráfica (`gui.py`)

**Abriendo el benchmark ya ensamblado:**
```powershell
python gui.py benchmark_opt/benchmark.hex
```

**O abriendo el código fuente para ensamblarlo desde la propia interfaz:**
```powershell
python gui.py benchmark_opt/main_grupo27.asm
```

Controles principales dentro de la interfaz gráfica:
- **`F5`** (*Ensamblar y Cargar*): ensambla el archivo `.asm` abierto junto con `benchmark_opt/lib/*.asm`.
- **`F9`** (*Ejecutar*): ejecuta el programa completo hasta finalizar.
- **`F10`** (*Paso a paso*): avanza de a una instrucción.
- **`F8`** (*Reiniciar*): reinicia la ejecución al punto de partida.
- Casilla **`Contar OS`**: activa o desactiva el conteo de las rutinas de `os_rutinas.asm`.

## 5. Salida esperada que confirma el funcionamiento correcto

Al ejecutar `python assembler.py ...` sin errores, debe mostrar:
```text
Generado .hex: benchmark_opt/benchmark.hex (origen x3000, 9202 bytes de programa)
```

Al ejecutar `python sim.py benchmark_opt/benchmark.hex`, la consola imprime los resultados de las **23 operaciones** del benchmark (desde `==REDUCCION DE ARGUMENTO (CORDIC)==` hasta `==Q3.12 -> Q7.8==`) y finaliza con el bloque de métricas:

```text
--- Resultados ---
  instrucciones: 16485
  palabras_buscadas: 16485
  bytes_leidos: 9304
  bytes_escritos: 4237
  direcciones_tocadas: 5050
  direcciones_leidas: 2008
  direcciones_escritas: 262
  memoria_programa_bytes: 9202
  memoria_pila_datos_bytes: 44
  memoria_usuario_bytes: 9246
```

Con el flag `--contar-os`, al final de las 23 operaciones imprime `HALT` y el resumen reporta:

```text
--- Resultados ---
  instrucciones: 28075
  instrucciones_usuario: 16485
  instrucciones_os: 11590
  palabras_buscadas: 28075
  bytes_leidos: 14789
  bytes_escritos: 8869
  direcciones_tocadas: 5181
  direcciones_leidas: 2051
  direcciones_escritas: 286
  memoria_programa_bytes: 9202
  memoria_pila_datos_bytes: 44
  memoria_usuario_bytes: 9246
```
