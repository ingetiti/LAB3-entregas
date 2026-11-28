# Grupo 20 · Parte de CORDIC

**Consigna:** Reducción de argumento manual

## Integrantes
Portillo Francisco (@kuboyasu-aren)
Pauluk Thiago (@PaulukThiago)
Semelak Pablo (@pablosem)

## Archivos
- `Cordic_reduccion_de_argumento.asm`: subrutina en LC-3 que reduce un ángulo en radianes (punto fijo Q3.12) al intervalo [-π/2, π/2], sumando o restando π. Devuelve el ángulo reducido en R0 y una bandera de paridad en R3.

## Cómo probarlo
Para verificar el programa:

1. Descargar el archivo Cordic_reduccion_de_argumento.asm desde grupo20/Reduccion_CORDIC/. En GitHub, abrilo y tocá el botón de descarga  de arriba a la derecha del código.
2. Entrar a https://lc3.lgrum.xyz/ y cargar el archivo en la sección de Archivos. También pueden crear un archivo nuevo y pegar el código adentro.
3. Pulsar el botón Continuar para iniciar la ejecución. 
4. Al terminar, mirar el registro R0: contiene el ángulo reducido en formato Q3.12. Para obtener el valor real, dividirlo por 4096 y comprobar que quede entre -π/2 y π/2 y  el signo final del angulo depende de R3.

Si R3 = 0, se corrió π una cantidad par de veces (o ninguna). La etapa siguiente puede usar el ángulo reducido sin cambiar el signo.
Si R3 = 1, se corrió π una cantidad impar de veces. La etapa siguiente debe invertir el signo del seno y del coseno calculados con el ángulo reducido.
El ángulo reducido siempre queda en R0 y su valor no depende de R3.



