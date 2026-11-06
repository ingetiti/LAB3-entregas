# Grupo 09 — SQRT por Newton-Raphson (LC-3)

## Archivos

- `sqrt_nr_q8.asm`: nucleo Newton-Raphson con raiz reciproca y punto fijo Q7.8; usa multiplicacion binaria `SQ9_MULQ` y division por 2 `SQ9_HALF` optimizadas.
- `sqrt_nr_dq16.asm`: adaptador de entrada/salida Q15.16 (dos palabras de 16 bits) que normaliza la entrada al intervalo [4, 16] mediante potencias de cuatro, invoca el nucleo y restaura la escala.

## Contrato de `SQRT_NR_DQ16`

- Entrada: `R0` palabra alta y `R1` palabra baja de un numero Q15.16 no negativo.
- Salida: `R0:R1` raiz aproximada expresada en Q15.16.
- Dominio admitido de entrada: `0 <= x < 32768` (los errores de entrada se reportan en el menu).
- Conserva `R2` a `R7`; no utiliza `R6`.
- No reentrante; utiliza memoria estatica interna.
- Retorna con `RET` (no detiene el simulador).

## Contrato de `SQRT_NR_Q8`

- Entrada: `R0` en Q7.8, con `4 <= x <= 16`.
- Salida: `R0` en Q7.8, raiz aproximada. Fuera de rango devuelve cero.
- Conserva `R1` a `R7`; no usa `R6`.
- Se ejecutan 6 iteraciones de Newton-Raphson sobre la raiz reciproca.

## Dependencias de integracion (existentes en la calculadora)

`SQRT_NR_DQ16` invoca las etiquetas externas:

- `SQRT_NR_Q8`
- `CIRCLSH`
- `DQ16_TO_Q8`
- `Q8_TO_DQ16`

La opcion de menu invoca `GETLINE`, `FROMDEC`, `OUTVAL` y `PAUSE`, ademas de la rutina anterior. Deben cargarse los modulos de interfaz/conversion necesarios al ensamblar. **No** deben duplicarse sus definiciones si ya existen en el proyecto compartido.

## Pruebas de referencia (simulador LC-3)

| Entrada | Salida aproximada |
|---:|---:|
| 0 | 0 |
| 0.5 | 0.7109375 |
| 9 | 2.98828125 |
| 36 | 5.9765625 |
| 100 | 10.046875 |
| 1000 | 31.25 |

La precision **no** se incrementa mediante las optimizaciones. El nucleo Q7.8 redondea/trunca cantidades intermedias. No es correcto esperar `sqrt(9) == 3` exacto.

## Rendimiento del nucleo aislado

En las mediciones locales del nucleo para `sqrt(9)`: 8234 instrucciones en version inicial y 3626 instrucciones con ambas optimizaciones (~56% menos). Este conteo excluye entrada/salida, menu y normalizacion; **no representa el tiempo total de la calculadora**.

## Integracion y atribucion

Consultar `../GUIA_PUBLICACION_GITHUB.md` en el paquete de entrega. La version original de la interfaz y las rutinas de otros grupos deben conservarse. Solo son propios del Grupo 09 los dos modulos SQRT.
