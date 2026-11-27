; Modulo: cordic_division   (archivo cordic_division.asm)
;=====================================================================
; Division por CORDIC (modo lineal, vectoring) en punto fijo Q15
;
; CORDIC_DIV
;   ENTRADAS (Q15, entero con signo en complemento a 2):
;     R0 = y0  (dividendo)
;     R1 = x0  (divisor)    con x0 > 0  y  |y0| < x0
;   SALIDA:
;     R0 = y0 / x0 en Q15, rango [-1, 1)   (valor real = R0 / 32768)
;          Ejemplo: 0.5 = x4000,  -0.5 = xC000   (error tipico: 1 LSB)
;   Conserva R1-R5 y R6 (usa la pila para guardar R2, R3 y R4).
;
; Como la LC-3 no tiene desplazamiento a la derecha, en cada paso se
; duplica el residuo en vez de achicar x:
;     P' = 2P + d*x        Z' = 2Z - d
;     d = +1 si P <= 0 ;  d = -1 si P > 0
;=====================================================================
CORDIC_DIV
        ADD R6, R6, #-3 ; Apilamos R2, R3 Y R4
        STR R2, R6, #0
        STR R3, R6, #1
        STR R4, R6, #2

        ADD R2, R0, #0  ; R2 = P = y0
        AND R0, R0, #0  ; R0 = Z = 0, el resultado
        ; R3 = -x0
        NOT R3, R1
        ADD R3, R3, #1

        ; R0 -> Entra como y0 y sale como el cociente
        ; R1 -> x0
        ; R2 -> P el residuo
        ; R3 -> -x
        ; R4 -> contador del bucle
        ; R5 -> No se usa, asi que, no se toca
        ; R6 -> Puntero de la pila
        ; R7 -> Para retornar de la subrutina, como no hay que ir a otra subrutina, no se toca
        
        ; Iteraccion 0
        ADD R2, R2, #0  ; Actualizar los CC con el signo de y0 y es tambien P
        BRp INI_NEG
        ADD R2, R2, R1  ; y <= 0 : d = + 1 -> P = P + x
        ADD R0, R0, #-1 ; z = -d = -1
        BRnzp INI_LOOP
INI_NEG ADD R2, R2, R3  ; y > 0 : d = -1 -> P = P - x
        ADD R0, R0, #1  ; z = -d = +1

        ; Iteracciones 1 a 15
INI_LOOP ADD R4, R4, #0 ; Inicializamos R4 que es nuestro i del for
        ADD R4, R4, #15 ; R4 = 15; ya hicimos la iteraciion 0
LOOP    ADD R2, R2, #0  ; Actualizar los CC con el signo de P
        BRp PPOS
        ADD R2, R2, R2  ; P <= 0 : d = +1
        ADD R2, R2, R1  ; P = 2P + x
        ADD R0, R0, R0
        ADD R0, R0, #-1 ; z = 2z - 1
        BRnzp GOON
PPOS    ADD R2, R2, R2  ; P > 0 : d = -1
        ADD R2, R2, R3  ; P = 2P - x
        ADD R0, R0, R0
        ADD R0, R0, #1  ; z = 2z + x
GOON    ADD R4, R4, #-1
        BRp LOOP
        
        
        
        LDR R2, R6, #0  ; Desapilamos en el mismo orden
        LDR R3, R6, #1
        LDR R4, R6, #2
        ADD R6, R6, #3  ; Devolvemos el estado original a R6
        RET
        .END