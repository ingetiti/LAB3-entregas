# Grupo 27 · Interfaz para el banco de algoritmos / calculadora

**Consigna:** Debe poder dar formato de decimal a binario con punto fijo y cambiar entre modo entrada por teclado y pasaje por memoria de los datos para calcular los resultados de cada algoritmo

## Integrantes

- Zimmermann, Miguel Angel (@ZimmerMaster26)
- Espinola, Tobias (@T0bias1)
- Gonzalez, Nahuel Sebastián (@Acelerator909)

## Archivos

- `main.asm`: Programa principal de prueba (Se usa como entrada para probar el funcionamiento).
- `main_menu.asm`: Subrutina principal de la interfaz del menú.
- `main_menu_PROGRESO.asm`: Subrutina principal de la interfaz del menú (con módulos externos incluidos).
- `subrutinas/`: Carpeta con las subrutinas esenciales.
    - `circlsh.asm`: Subrutina CIRCLSH para rotar de manera circular dos registros, hacia la izquierda.
    - `fromdec.asm`: Subrutina FROMDEC para pasaje de texto decimal a valor en binario (entero y fraccionario, 1 WORD cada uno, lo que corresponde a $Q15.16$).
    - `fromhex.asm`: Subrutina FROMHEX para pasaje de texto hexadecimal a valor en binario (1 WORD).
    - `getcfilered.asm`: Subrutina GETCFILTERED para obtención de carácter por teclado únicamente si cumple cierto filtro.
    - `getline.asm`: Subrutina GETLINE para obtención de línea (hasta encontrar '\n').
    - `pause.asm`: Subrutina PAUSE que muestra por consola un prompt y continua ejecución al pulsar una tecla.
    - `sumover.asm`: Subrutina SUMOVER para sumar dos registros teniendo en cuenta un bit de acarreo (de entrada y salida).
    - `todec.asm`: Subrutina TODEC para pasaje de valor en binario (entero y fraccionario, 1 WORD cada uno, correspondiente a $Q15.16$) a texto decimal.
- `q_cast/`: Carpeta con las subrutinas de casteo.
    - `from_qm_n.asm`: Subrutina para pasaje de valor $Qm.n$ a un $Q15.16$ (recibe como argumento un $n$ que especifica el formato).
    - `to_qm_n.asm`: Subrutina para pasaje de valor $Q15.16$ a un $Qm.n$ (recibe como argumento un $n$ que especifica el formato).
- `val_io/`: Carpeta para subrutinas de obtención y muestra de valores.
    - `getval_buffer.asm`: Buffer compartido.
    - `getval.asm`: Subrutina para obtención de valores por consola (recibe como argumento un $n$ que especifica el formato).
    - `outval.asm`: Subrutina para muestra por consola de un valor (recibe como argumento el valor y el formato con un $n$).

## Especificación de formato interno

Utilizamos un valor entre $0$ y $16$ para especificar el formato de los valores, donde este numero representa el $n$ del formato $Qm.n$, y $m$ se deduce de la compleción a 16 bits. Para el caso cuando $n$ vale $16$, se deduce de la compleción a 32 bits, osea que $16$ representa el caso especial donde es $Q15.16$ (entero y fraccionario, 1 WORD cada uno).

# Como PROBAR:

Si se quiere probar únicamente la interfaz, se puede descargar el directorio `main_menu.asm` como zip (descargando el repositorio entero o utilizando paginas como <githubfolder.com>) para cargarlo directamente en un simulador, siguiendo la guía del archivo `main.asm`.

Si se quiere probar utilizando el simulador del grupo 8, con **los módulos externos**, la manera mas sencilla es la siguiente:
- Iniciamos sesión con una cuenta (de grupo o de administrador).
- Copiar el archivo (o el contenido de) `main.asm` en el simulador.
- Cambiamos las subrutinas externas de `.EXTERNAL ...` para que utilicen archivos del propio simulador, agregando el grupo al que pertenece ese archivo (osea el `g27_` para el grupo 27). Por ejemplo:  
`.EXTERNAL MAIN_MENU_PROGRESO-MAIN_MENU` va a pasar a ser `.EXTERNAL g27_MAIN_MENU_PROGRESO-MAIN_MENU`  
`sub_main_menu .FILL MAIN_MENU_PROGRESO-MAIN_MENU` va a pasar a ser `sub_main_menu .FILL g27_MAIN_MENU_PROGRESO-MAIN_MENU`
- Compilamos (esperamos un momento que va a tardar unos segundos).
- Listo, ya se puede correr la simulación.

