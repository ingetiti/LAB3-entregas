;   ============================================================================
;   Subrutina: TODEC (LC-X)
;       Convierte un valor a cadena de texto decimal, un caracter por byte
;       (se imprime con PUTSP): el signo - si es negativo, la parte entera
;       sin ceros a izquierda y, si hay fraccion, el punto y hasta 9 cifras
;       sin ceros a derecha.
;
;   -> INPUT  [R0] Parte entera.
;   -> INPUT  [R1] Parte fraccionaria (16 bits, en 1/65536).
;   -> INPUT  [R2] Puntero al buffer (20 bytes minimo).
;   -> INPUT  [R3] Caracter que cierra el texto, antes del x00 (salto de linea), o 0.
;   <- OUTPUT [R2] Puntero a la cadena, dentro del buffer.
;   Conserva R0, R1 y R3-R7.
;
;   La version LC-3 tenia un formato en R3 (signo +, ceros a izquierda y
;   ceros a derecha) que ningun llamador usa: aqui no esta.
;   Las cifras enteras se escriben hacia atras desde buffer + 7, asi que
;   salen en orden sin pasar por la pila; la fraccion sigue desde ahi.
;   Las cifras decimales son las exactas, truncadas a 9: cada MULW por 10
;   da la siguiente cifra en la palabra alta y deja el resto en la baja.
;   (La version LC-3 sumaba un termino truncado por bit, y la ultima cifra
;   podia salir una unidad mas baja.)
;   ============================================================================

TODEC
        PUSH  R0, R1, R3, R4, R5, R7
        ADD   R4, R2, #7        ; R4 = cursor de la fraccion
        ADD   R2, R2, #7        ; R2 = cursor de la parte entera, hacia atras
        MOVI  R3, #10
        MOVI  R7, #48           ; '0'

;   ==- Signo: se trabaja con el valor absoluto -===============================
        ADD   R0, R0, #0
        BRzp  DIGITO
        NOT   R0, R0
        NEG   R1, R1            ; C = 1 solo si la fraccion es 0
        ADC   R0, R0, #0        ; [R0, R1] = -[R0, R1]

;   ==- Entero: de la cifra menor a la mayor, hacia atras -=====================
DIGITO  DIVM  R5, R0, R3        ; R5 = cifra, R0 = lo que queda (Z si es 0)
        BRz   PRIMERA
        ADD   R5, R5, R7
        STB   R5, R2, #-1
        LOOP  R2, DIGITO        ; R2 - 1, y sigue (R2 nunca llega a 0)
PRIMERA ADD   R5, R5, R7        ; la cifra mayor
        STB   R5, R2, #-1
        SUB   R2, R2, #1
        LDR   R5, R6, #0        ; R0 de entrada
        BRzp  FRACCION
        MOVI  R5, #45           ; '-'
        SUB   R2, R2, #1
        STB   R5, R2, #0

;   ==- Decimal -===============================================================
FRACCION
        ADD   R1, R1, #0
        BRz   CIERRE            ; sin fraccion
        MOVI  R5, #46           ; '.'
        STBI  R5, R4
        MOVI  R0, #4            ; 9 cifras como mucho: una y 4 pares
        MULW  R5, R1, R3        ; R5 = cifra, R1 = resto (Z si el resto es 0)
        BRz   ULTIMA
        ADD   R5, R5, R7
        STBI  R5, R4
DECIMAL MULW  R5, R1, R3
        BRz   ULTIMA
        ADD   R5, R5, R7
        STBI  R5, R4
        MULW  R5, R1, R3
        BRz   ULTIMA
        ADD   R5, R5, R7
        STBI  R5, R4
        LOOP  R0, DECIMAL
QUITA   SUB   R4, R4, #1        ; 9 cifras y sigue habiendo resto:
        LDB   R5, R4, #0        ; se quitan los 0 del final
        CMP   R5, R7
        BRz   QUITA
        ADD   R4, R4, #1
        AND   R1, R1, #0        ; R1 = 0 para el fin de cadena
        BR    CIERRE
ULTIMA  ADD   R5, R5, R7
        STBI  R5, R4
CIERRE  LDR   R3, R6, #2        ; R3 de entrada
        STBI  R3, R4            ; salto de linea o 0
        STBI  R1, R4            ; fin de cadena: R1 es 0 en todos los caminos
        POPR  R0, R1, R3, R4, R5, R7

.END
