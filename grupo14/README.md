Grupo 14 · Calculadora de Logaritmos Q8.7
Consigna: Calculadora de logaritmos en cualquier base por algoritmo de Borchardt en LC-3

Integrantes
Agú, Alejandro Valentín (@AleValen11)
Hoet, Gabriel Alejandro (@GabrielHoet)
Sosa, Sofia Azul Esmeralda (@sosasofiaazul-png)

Contenidos de la carpeta
- log_borchardt_q8_7.asm: Código principal de assembly adaptado para el algoritmo de Borchardt en formato Q8.7.
- README.md: Documentación técnica del funcionamiento, formato y pruebas del módulo.

1. Verificación de la función
La función implementada calcula el logaritmo en cualquier base resolviendo la identidad:
log_b(x) = ln(x) / ln(b)

El cálculo del logaritmo natural se realiza mediante el algoritmo de Borchardt con reducción de rango (ln(x) = ln(m) + k * ln(2)) y una tabla de búsqueda (LUT) de 128 elementos para las raíces cuadradas.

Formatos y rangos:
- Formato de punto fijo: Q8.7 (1 bit de signo, 8 bits de parte entera y 7 bits de parte fraccionaria).
- Factor de escala: 1.0 = 128 (#128 decimal o x0080 hexadecimal).
- Rango de entradas: x > 0 y base b > 0 (con b diferente de 1, protegido contra división por cero).
- Rango de salidas: Almacenado en formato Q8.7 en la dirección designada.
- Precisión alcanzada: Resolución fraccionaria limitada a 7 bits (1/128 aprox 0.0078125).

Caso de prueba:
- INPUT_X (x300D): #256 (x = 2.0)
- INPUT_BASE (x300E): #1280 (b = 10.0)
- Resultado esperado log_10(2.0): 39 / 128 aprox 0.3046

2. Assembly subido al simulador
El archivo fuente assembly se encuentra cargado en el simulador y documentado en esta carpeta:
- log_borchardt_q8_7.asm

3. Estado de funcionamiento en los simuladores
- Estado: Código probado y verificado exitosamente sin errores de ensamblado ni de ejecución en el simulador oficial de LC-3.

4. Bitácora de avances

Avance 1: diseño inicial
- Estructuración de las subrutinas de multiplicación, división y manejo de signos.

Avance 2: algoritmo de Borchardt
- Implementación de la reducción de rango y la tabla de búsqueda (LUT) de 128 elementos para el cálculo de ln(x).

Avance 3: cambio de base
- Integración de la fórmula de cambio de base con redondeo adaptativo según el signo del cociente.

Avance 4: pruebas y verificación
- Verificación completa con casos de prueba en formato Q8.7 en el simulador y validación de ausencia de errores.
