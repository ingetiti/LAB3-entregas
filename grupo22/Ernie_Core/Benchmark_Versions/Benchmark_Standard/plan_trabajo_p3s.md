# plan_trabajo_p3s.md — Seguimiento P3S v3 / P8E v4 — `main_grupo27.asm`

> **Archivo objetivo:** `Benchmark_Versions/Benchmark_Standard/main_grupo27.asm`
> **Módulo:** `G27_MAIN_GRUPO27` (entry point del benchmark LGRUM)
> **Plan autoritativo:** `Docs_Benchmark/PLAN_MAIN_GRUPO27.md`
> **Herramientas reales:** `Implementacion_ISA/ernie_assembler.py`, `Implementacion_ISA/ernie_simulator.py`
> **Fecha:** 2026-11-27

---

## Corrección del Programador ante Arquitecto

### A. Diagnóstico de compatibilidad (P8E v4 / P3S v3)

| Aspecto | Estado | Detalle |
|---------|--------|---------|
| `.ORIG x3000` | ✅ | Único `.ORIG`, par, base del enlazador (M4). |
| `.END` | ✅ | Presente al final (L214). |
| `BR main` (L2) | ❌ → corregido | `BR` sin sufijo **rechazado por P8E v4 `--strict`** (§strict-a). El plan asumía P7E v4 (BR = incondicional). |
| `.EXTERNAL G27_MAIN_MENU_PROGRESO-MAIN_MENU` | ✅ | Coincide exactamente con la etiqueta `MAIN_MENU` exportada por `lib/g27_main_menu_PROGRESO.asm`. |
| `LEA R0 programa_del_menu_completo` (L36) | ✅ | PCoffset8 ≈ +25 palabras ≪ 128. |
| `LD R1 sub_main_menu` (L38) / `JSRR R1` (L39) | ✅ | `sub_main_menu` = `.FILL G27_MAIN_MENU_PROGRESO-MAIN_MENU` (dirección absoluta). |
| `HALT` (L40) | ✅ | TRAP x25, detención limpia. |
| Vectores `.FILL` (L46-211) | ✅ | Datos tras `HALT`; no se ejecutan como código. |
| Byte-addressing | ✅ | `main_grupo27.asm` no hace aritmética de punteros; delega en `MAIN_MENU` (ya byte-addressed: `ADD #2` por palabra, indexado `base+2*idx`). |
| `imm4` / `offset5` fuera de rango | ✅ | No hay `imm4` 8..15 ni `offset5` fuera de rango en el módulo. |
| Uso de R6 | ✅ | No inicializa R6; el simulador lo fija en `0xFFFE`. |

### B. Cambio quirúrgico aplicado (único)

- **Archivo:** `Benchmark_Versions/Benchmark_Standard/main_grupo27.asm`
- **Línea 2:** `BR main` → `BRnzp main` (salto incondicional equivalente, nzp=111).
- **Justificación:** P8E v4 `--strict` prohíbe `BR` sin sufijo; `BRnzp` es semánticamente idéntico.
- **Sin cambios cosméticos** ni reescritura. No se tocaron 3A/3B ni otras dependencias.

### C. Ensamblado y enlazado

- **Modo normal** (`strict=False`): **OK** — `main_grupo27.asm` + **37 dependencias reales** de `lib/` → `main_grupo27_linked.bin` (16152 bytes).
- **Modo `--strict` (enlace completo)**: falla por **dependencias legacy** ajenas (BR sin sufijo / imm4 8..15 en módulos de otros grupos). `main_grupo27.asm` en sí es **strict-clean** (0 BR sin sufijo, 0 imm4 8..15, 0 incremento +1 sobre puntero). No se modifican dependencias (fuera de alcance).
- **Binario de verificación:** `Pruebas_ISA/G27_MAIN_GRUPO27/main_grupo27_linked.bin`.

### D. Integración en el oráculo

- `Implementacion_ISA/suite_oraculo_benchmark.py`: nuevo módulo `g27_main_grupo27`
  - Runner cacheado `_run_main_grupo27()` (1 sola corrida del flujo automático).
  - Oráculo `tc_main_grupo27(nombre, esperados)` + 8 escenarios `g27_main_grupo27_cases`.
  - Filtros `--modulo g27_main_grupo27` y alias `--modulo main_grupo27` (más `g27_main`, `grupo27`, …).
  - Persistencia: `Pruebas_ISA/G27_MAIN_GRUPO27/g27_main_grupo27_resultados.json`.

### E. Resultados del oráculo (`tc_main_grupo27`)

- **8/8 PASS**, **0 excepciones fatales**, **0 fallas transversales**.
- Flujo automático completo: **23 operaciones** preprogramadas (vector `programa_del_menu_completo`), cada una imprime título + operandos + resultado por consola.
- Consola validada por presencia exacta de los 23 banners (`==REDUCCION...==` … `==Q3.12 -> Q7.8==`).
- **Métricas:** `instrucciones_ejecutadas = 356666`, `bytes_ocupados = 53248`, `R6 = 0xFFFE`, `excepciones_fatales = 0`, HALT limpio (TRAP x25, sin timeout).

### F. Conclusión

`main_grupo27.asm` queda **compatible con P8E v4 / P3S v3** tras la corrección `BR → BRnzp`. El oráculo end-to-end del entry point queda integrado en la suite principal y valida el flujo automático del benchmark completo (23 operaciones, 37 dependencias enlazadas) con 100 % PASS.