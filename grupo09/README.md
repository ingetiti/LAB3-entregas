# Grupo 09 · SQRT

**Consigna:** Por Newton-Raphson, método de raíz cuadrada recíproca

## Integrantes
- Mantulak, Gustavo (@Gustavo-Mantu)
- Casales, Mia (@miacasales)
- Münz, Yessica (@yessi2004)

## Implementación

Se desarrolló una subrutina en Assembly LC-3 para calcular raíces cuadradas mediante el método de Newton-Raphson aplicado a la raíz recíproca.

## Características:

-Implementación en Assembly LC-3.

-Cálculo interno en punto fijo Q7.8.

-Entrada y salida en Q15.16.

-Normalización mediante potencias de 4 para ampliar el rango de entrada.

-Seis iteraciones de Newton-Raphson.

-Multiplicación MULQ optimizada mediante operaciones binarias.

-División entre 2 (HALF) optimizada.

-Rango de entrada: 0 ≤ x < 32768.

-Manejo de entradas inválidas, negativas y fuera de rango.

-Integración con la calculadora del Grupo 27.

-Los resultados son aproximados debido a la precisión limitada del formato Q7.8.

## Archivos

Subrutinas del Grupo 09

-sqrt_nr_q8.asm: núcleo Newton-Raphson en Q7.8. Contiene MULQ y HALF optimizadas.

-sqrt_nr_dq16.asm: recibe valores Q15.16, realiza la normalización, llama al núcleo SQRT y recupera la escala del resultado.

-README_SQRT_NR.md: documentación técnica de la implementación.

Archivos de integración modificados

En grupo27/main_menu/:

-main_menu.asm: integración de SQRT Newton-Raphson en la opción 4 → 1.

-val_io/getval.asm: corrección de direccionamiento LEA.

-val_io/getval_int.asm: corrección de direccionamiento LEA.

-val_io/getval_q8.asm: corrección de direccionamiento LEA.

-val_io/getval_q12.asm: corrección de direccionamiento LEA.

-val_io/outval.asm: corrección de direccionamiento LEA.

## Cómo probarlo
Opción A (Desde Git Hub): 

  -Descargar el repositorio desde GitHub.

  -Abrir el simulador LC-3: https://lc3.lgrum.xyz/

  -Cargar los archivos .asm de grupo27/main_menu/, incluyendo las subcarpetas q_cast, subrutinas y val_io.

  -Cargar también grupo09/sqrt_nr_q8.asm y grupo09/sqrt_nr_dq16.asm.

  -Seleccionar grupo27/main_menu/main.asm como programa principal.

  -Ejecutar Ensamblar → Reiniciar → Continuar.

  -Seleccionar [4] sqrt y luego [1] NEWTON-RAPHSON.

  -Ingresar un número decimal y comprobar el resultado.

Opción B (Carga Rapida):
  
  -Copiar e ingresar al link y descargar (zip con todos los archivos listos para subir en el simulador LC-3) + Guía de       Carga Rapida: 

   https://drive.google.com/drive/folders/1LdAcch1DFq27HeZzpC9q4ezxdLd3fQvj?usp=drive_link
   
  -Abrir el simulador LC-3: https://lc3.lgrum.xyz/

  -Seguir la Guía de Carga Rapida

## Validación

Se realizaron pruebas de ensamblado y ejecución en el simulador LC-3, verificando el funcionamiento del algoritmo, la ampliación de rango y su integración con el menú principal.

Las optimizaciones MULQ y HALF permiten reducir el número de instrucciones ejecutadas respecto de la implementación original, manteniendo los resultados numéricos del núcleo Q7.8.

## Rangos y formatos

Entrada: Q15.16, valores desde 0 hasta menos de 32768.

Salida: Q15.16, raíz cuadrada aproximada. Para el rango de entrada admitido, el valor matemático de la raíz se encuentra entre 0 y aproximadamente 181,02.

Cálculo interno: Q7.8, con seis iteraciones de Newton-Raphson.

Precisión: limitada por el cálculo interno en Q7.8; los resultados no son necesariamente exactos.

## Compatibilidad con el simulador

La implementación fue ensamblada y ejecutada exitosamente en el simulador LC-3 del Grupo 08: https://lc3.lgrum.xyz/

Se verificó su funcionamiento integrado con el menú principal de la calculadora, incluyendo las optimizaciones MULQ y HALF.

## Vitacora
https://docs.google.com/document/d/1y0KH7npD7WXnLNtVTXCE_g3k6S87dZBEdLG64QTJp9Q/edit?usp=sharing
