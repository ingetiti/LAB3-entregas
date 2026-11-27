# Grupo 06 · EXP

**Consigna:** Algoritmo multiplicativo de alta radix

## Integrantes
<!-- Completar en el primer Pull Request -->
- Diaz, Agustina (@agustinadiiiaz)
- Feltan, Shaquel (@FeltanShaquel)
- Pires, Facundo (@facundopires23)

## Prueba de la función EXP

La versión en Assembly está disponible en el simulador del **Grupo 8**, donde puede ejecutarse directamente.

Para comprobar su funcionamiento, se puede evaluar $e^3$. El valor esperado en la salida es **`x1416`** en hexadecimal, que equivale a **5142** como entero. La salida está en formato Q7.8, por lo que se divide ese entero por 256 para obtener **20,0859375**.

### Representación en punto fijo

La entrada y la salida se almacenan en palabras de **16 bits con signo**. La entrada usa **Q3.12**, con 12 bits fraccionarios, y la salida usa **Q7.8**, con 8 bits fraccionarios.

### Rango de entrada y salida

El exponente $x$ se puede representar desde **−8** hasta **7,999755859375**. El mayor valor de entrada que se puede procesar sin saturar la salida es **4,851806640625**.

Aunque Q7.8 con signo abarca desde **−128** hasta **127,99609375**, la función EXP utiliza la parte no negativa de ese rango. Los resultados muy pequeños pueden redondearse a **0**, mientras que los que superan el límite se saturan en **127,99609375**.

### Resolución

La resolución indica cuánto cambia el valor al pasar de un número representable al siguiente. Se obtiene mediante $2^{-n}$, donde $n$ es la cantidad de bits fraccionarios.

- **Entrada Q3.12:** $2^{-12}=1/4096=0,000244140625$.
- **Salida Q7.8:** $2^{-8}=1/256=0,00390625$.
