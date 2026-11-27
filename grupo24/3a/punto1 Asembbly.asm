; =====================================================================
; Laboratorio N° 3a - Actividades en LC-3 Assembly (Puntos 3 y 4)
; =====================================================================
        .ORIG x3000

        ; -------------------------------------------------------------
        ; 1. Cargar operandos iniciales desde memoria
        ; -------------------------------------------------------------
        LD R0, NUM1_Q3_12       ; R0 <- NUM1 (Formato Q3.12)
        LD R1, NUM2_Q7_8        ; R1 <- NUM2 (Formato Q7.8)

        ; -------------------------------------------------------------
        ; PUNTO 3: Compatibilizacion (Convertir NUM1 de Q3.12 a Q7.8)
        ; Requiere desplazar R0 a la derecha 4 veces (division por 16)
        ; -------------------------------------------------------------
        ADD R2, R0, #0          ; R2 sera nuestra copia de NUM1 convertida
        AND R3, R3, #0
        ADD R3, R3, #4          ; Contador de 4 desplazamientos a la derecha

SHIFT_LOOP_4
        ; Desplazamiento aritmetico a la derecha de 1 bit en R2:
        JSR ASHR_ONE
        ADD R3, R3, #-1
        BRp SHIFT_LOOP_4

        ST R2, NUM1_Q7_8        ; Guardar NUM1 convertido a Q7.8 en memoria

        ; --- Suma en Q7.8: R4 = NUM1(Q7.8) + NUM2(Q7.8) ---
        ADD R4, R2, R1
        ST R4, RES_SUMA         ; Guardar resultado de la suma

        ; --- Resta en Q7.8: R5 = NUM1(Q7.8) - NUM2(Q7.8) ---
        NOT R5, R1
        ADD R5, R5, #1          ; R5 = -NUM2
        ADD R5, R2, R5          ; R5 = NUM1 + (-NUM2)
        ST R5, RES_RESTA        ; Guardar resultado de la resta

        ; -------------------------------------------------------------
        ; PUNTO 4: Multiplicacion de Punto Fijo
        ; Producto = NUM1_Q3_12 * NUM2_Q7_8
        ; El producto intermedio tiene escala 2^20.
        ; Se multiplica por sumas sucesivas y luego se desplaza 12 veces
        ; a la derecha para dejarlo en formato Q7.8.
        ; -------------------------------------------------------------
        LD R0, NUM1_Q3_12
        LD R1, NUM2_Q7_8

        ; Inicializar acumulador de multiplicacion
        AND R2, R2, #0          ; R2 = Acumulador del producto

        ; Si R1 (multiplicador) es 0, terminamos directo
        ADD R3, R1, #0
        BRz MULT_DONE

MULT_LOOP
        ADD R2, R2, R0          ; R2 = R2 + Multiplicando
        ADD R3, R3, #-1         ; Decrementar contador
        BRp MULT_LOOP

MULT_DONE
        ST R2, PROD_INTER       ; Guardar producto intermedio (Q10.20 truncado a 16b)

        ; --- Ajuste al formato Q7.8: Desplazar 12 bits a la derecha ---
        AND R3, R3, #0
        ADD R3, R3, #12         ; Contador = 12 desplazamientos a la derecha

SHIFT_LOOP_12
        JSR ASHR_ONE            ; Desplaza R2 un bit a la derecha manteniendo signo
        ADD R3, R3, #-1
        BRp SHIFT_LOOP_12

        ST R2, RES_MULT_Q7_8    ; Guardar resultado final de la multiplicacion en Q7.8

        HALT                    ; Detener ejecucion del procesador

; =====================================================================
; Subrutina: ASHR_ONE
; Realiza un desplazamiento aritmetico a la derecha de 1 bit sobre R2.
; Entrada: R2 (valor original)
; Salida:  R2 = R2 / 2 (con signo)
; Registros modificados: R2
; =====================================================================
ASHR_ONE
        ST R0, SAVE_R0
        ST R1, SAVE_R1
        ST R4, SAVE_R4

        AND R0, R0, #0          ; R0 acumulara el cociente (R2 / 2)
        AND R4, R4, #0          ; Flag de signo (0 = positivo, 1 = negativo)

        ADD R1, R2, #0          ; Testear signo de R2
        BRzp POS_VAL

        ; Si es negativo, lo pasamos a positivo y marcamos flag
        ADD R4, R4, #1
        NOT R1, R1
        ADD R1, R1, #1

POS_VAL
        ; Division entera positiva por 2 mediante restas de 2
ASHR_DIV2
        ADD R1, R1, #-2
        BRn ASHR_DIV_END
        ADD R0, R0, #1
        BRnzp ASHR_DIV2

ASHR_DIV_END
        ; Si era negativo, restaurar complemento a dos
        ADD R4, R4, #0
        BRz ASHR_EXIT
        NOT R0, R0
        ADD R0, R0, #1

ASHR_EXIT
        ADD R2, R0, #0          ; R2 = resultado desplazado
        LD R0, SAVE_R0
        LD R1, SAVE_R1
        LD R4, SAVE_R4
        RET

; ---------------------------------------------------------------------
; Variables auxiliares para salvar registros en la subrutina
; ---------------------------------------------------------------------
SAVE_R0     .BLKW 1
SAVE_R1     .BLKW 1
SAVE_R4     .BLKW 1

; =====================================================================
; Datos y Constantes en Memoria (Punto 1 de Assembly)
; =====================================================================
; NUM1 = 1.5 en Q3.12  -> 1.5 * 4096 = 6144 (x1800)
NUM1_Q3_12      .FILL x1800

; NUM2 = 2.0 en Q7.8   -> 2.0 * 256  = 512  (x0200)
NUM2_Q7_8       .FILL x0200

; Espacios de memoria reservados para guardar los resultados
NUM1_Q7_8       .BLKW 1     ; NUM1 convertido a Q7.8
RES_SUMA        .BLKW 1     ; Resultado de la suma en Q7.8 (3.5 -> 896 -> x0380)
RES_RESTA       .BLKW 1     ; Resultado de la resta en Q7.8 (-0.5 -> -128 -> xFF80)
PROD_INTER      .BLKW 1     ; Producto intermedio antes del escalado
RES_MULT_Q7_8   .BLKW 1     ; Producto final en Q7.8 (3.0 -> 768 -> x0300)

        .END