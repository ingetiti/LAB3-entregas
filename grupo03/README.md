## Grupo 03 · Multiplicación
Consigna: Por algoritmo de shift + sumas

## Integrantes
Herrera Paulus, Diego Sebastian (@Diego11331)
Sedoff, Nicolás Alejandro (@Altrupro73)
Garcia, Franco (@Mekkii088)

## Contenidos de la carpeta
-Simulador LC3: programa actual de assembly para el simulador del grupo 8
-Web LC3: Betas del programa assembly hecho para Web LC3
-C: Codigo de Web LC3 adaptado a C para mayor comprensión de su funcionamiento
- Simulador Apex-3X: nuestro propio simulador de LC3.

## 1. Verificación de la función

La función implementada es `MULTIPLICARSHIFTANDADD`, ubicada en:

La subrutina recibe dos operandos con formato **Q8.8**:

- `R0`: primer operando.
- `R1`: segundo operando.

Cada operando es un valor de 16 bits con:

- 1 bit de signo.
- 8 bits para la parte entera.
- 8 bits para la parte fraccionaria.
- se llegaron a estos valores bajo el entendimiento de que el grupo 27 trabaja con formato Q15.16 (MSB usado para signo)
El rango aproximado de entrada es:

```text
-128.0 <= valor <= 127.99609375
```

La función devuelve el resultado en formato **Q16.16**, usando dos registros:

- `R1`: palabra alta, correspondiente a la parte entera y los bits superiores.
- `R0`: palabra baja, correspondiente a los bits fraccionarios.

El resultado completo se interpreta como:

```text
R1:R0 = resultado Q16.16
```

El rango representable del resultado de 32 bits es:

```text
-32768.0 <= resultado <= 32767.9999847412
```

La multiplicación utiliza el algoritmo **Shift-and-Add**. Como cada operando Q8.8 tiene 16 bits, se realizan como máximo 16 iteraciones.

### Caso de prueba

Para verificar la función se pueden cargar los siguientes valores:

```asm
; 1.5 en Q8.8
.FILL x0180

; 2.25 en Q8.8
.FILL x0240
```

El resultado esperado es:

```text
1.5 * 2.25 = 3.375
```

En formato Q16.16:

```text
R1 = x0003
R0 = x6000
R1:R0 = x0003:x6000
```

Los registros `R2` a `R5` son preservados por la subrutina. Los registros `R6` y `R7` no son utilizados.

## 2. Assembly subido al simulador

El módulo nuevo que debe cargarse en el simulador es:

[`Simulador LC3/MultiplicacionSHIFTandADD.asm`]

El archivo contiene la etiqueta pública:

```asm
MULTIPLICARSHIFTANDADD
```

La llamada desde un archivo principal debe cargar los operandos en `R0` y `R1`, cargar la dirección de la subrutina y utilizar `JSRR`.

Ejemplo de archivo principal:

```asm
.ORIG x3000

.EXTERNAL MultiplicacionSHIFTandADD-MULTIPLICARSHIFTANDADD

        LD      R0, OPERANDO_A
        LD      R1, OPERANDO_B
        LD      R4, DIRECCION_MULT
        JSRR    R4
        HALT

OPERANDO_A:     .FILL x0180
OPERANDO_B:     .FILL x0240
DIRECCION_MULT: .FILL MultiplicacionSHIFTandADD-MULTIPLICARSHIFTANDADD

.END
```

Los archivos de pruebas y versiones anteriores se conservarán en:

```
Web-LC3/
```

los módulos nuevos se organizarán a partir de ahora en:

```
Simulador LC3/
```

## 3. Estado de funcionamiento en los simuladores
Los archivos que definimos como viejos funcionan dentro del entorno de WEB-LC3, El nuevo archivo funciona en el simulador del grupo 8

## 4. Bitácora de avances

### Avance 1: primer programa
- se creo un algoritmo en assembly Web-LC3 para multiplicacion por shiftandadd
### Avance 2: negativos
- se implemento entrada del usuario para poder probar los cambios
- se implemento negativos
### Avance 3: formato Q
-se implemento el formato Q 
-se implemento optimizaciones pera que el codigo no sobrepase las 16 iteraciones
### Avance 5: C
-se implementaron varios formatos Q para probar rangos y presicion
-se implementaron las ultimas optimizaciones para intercambiar multiplicando y multiplicador
-se implemento el resultado en dos palabras
-se creo un programa en C para explicar la logica del programa
### Avance 6: revisión de especificaciones

- pasaje al simulador del grupo 8
- Se identificó que la subrutina debe recibir argumentos en `R0` y `R1`.
- Se estableció que el resultado de 32 bits se devuelve en `R1:R0`.
- Se respetó la restricción de no utilizar `R6` ni `R7`.

### Avance 7: adaptación del algoritmo

- Se tomó como base la multiplicación Shift-and-Add existente.
- Se eliminó la interacción por teclado y la selección de formatos.
- Se definieron operandos de entrada Q8.8.
- Se definió la salida como Q16.16.
- Se agregó soporte para signos positivos, negativos y cero.

### Avance 8: resultado de 32 bits

- Se implementó el multiplicando como un valor de 32 bits en `R4:R3`.
- Se utilizó `R1:R0` como acumulador del producto.
- Se incorporó el acarreo de la palabra baja a la palabra alta.
- Se preservaron `R2`, `R3`, `R4` y `R5`.

### Avance 9: pruebas

- Se verificaron casos representativos de operandos positivos, negativos y cero.
- Se verificó el caso `1.5 * 2.25 = 3.375`.
- Queda pendiente confirmar la ejecución dentro del simulador del grupo 8.
