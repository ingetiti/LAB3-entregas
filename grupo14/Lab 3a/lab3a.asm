.ORIG x3000       ; Dirección de inicio en memoria

; =====================================================================
; 1. CARGA DE DATOS DESDE LA MEMORIA
; =====================================================================
        LD R1, NUM1       ; R1 = num1 (64 = 0.5 en Q7)
        LD R2, NUM2       ; R2 = num2 (32 = 0.25 en Q7)

; =====================================================================
; 2. SUMA (Q7 + Q7 = Q7)
; =====================================================================
        ADD R3, R1, R2    ; R3 = R1 + R2 (64 + 32 = 96)
        ST R3, RES_SUMA   ; Guardar resultado en memoria (96 = 0.75)

; =====================================================================
; 3. MULTIPLICACIÓN (Q7 * Q7 = Q14 -> Q7 con redondeo)
; =====================================================================
        AND R4, R4, #0    ; R4 = 0 (Acumulador del producto)
        ADD R0, R2, #0    ; R0 = contador (copia de num2)
        BRz MULT_DONE     ; Si num2 es 0, terminar

MULT_LOOP
        ADD R4, R4, R1    ; Acumular num1
        ADD R0, R0, #-1   ; Decrementar contador
        BRp MULT_LOOP     ; Repetir mientras contador > 0
MULT_DONE

        ; Aplicar redondeo (+64 en Q14) antes de dividir por 128
        LD R6, POS_64
        ADD R4, R4, R6    ; R4 = producto + 64

        ; Pasar de Q14 a Q7 (Dividir entre 128 por restas sucesivas)
        AND R5, R5, #0    ; R5 = 0 (Cociente)
        LD R6, MINUS_128  ; R6 = -128

DIV128_LOOP
        ADD R7, R4, R6    ; Probar restar 128
        BRn DIV128_DONE   ; Si el resto es menor a 128, salir
        ADD R4, R7, #0    ; Actualizar resto
        ADD R5, R5, #1    ; Incrementar cociente
        BR DIV128_LOOP
DIV128_DONE

        ST R5, RES_MULTI  ; Guardar resultado (16 = 0.125)

; =====================================================================
; 4. DIVISIÓN (Q7 / Q7 = Q7 con redondeo)
; =====================================================================
        ADD R4, R1, #0    ; R4 = copia de num1
        
        ; Elevar a Q14: Desplazar 7 bits a la izquierda (R4 * 128)
        ADD R4, R4, R4    ; x2
        ADD R4, R4, R4    ; x4
        ADD R4, R4, R4    ; x8
        ADD R4, R4, R4    ; x16
        ADD R4, R4, R4    ; x32
        ADD R4, R4, R4    ; x64
        ADD R4, R4, R4    ; x128 (8192)

        ; Calcular (num2 / 2) para el redondeo del dividendo
        AND R0, R0, #0    ; R0 = 0 (Mitad de num2)
        ADD R6, R2, #0    ; R6 = num2
HALF_LOOP
        ADD R6, R6, #-2   ; Restar 2
        BRn HALF_DONE
        ADD R0, R0, #1    ; Sumar 1 a la mitad
        BR HALF_LOOP
HALF_DONE
        ADD R4, R4, R0    ; Numerador = (num1 * 128) + (num2 / 2)

        ; Obtener -num2 para restar
        NOT R6, R2
        ADD R6, R6, #1    ; R6 = -num2

        AND R5, R5, #0    ; R5 = 0 (Cociente)

DIV_LOOP
        ADD R7, R4, R6    ; Probar restar num2
        BRn DIV_DONE      ; Si el resto es menor a num2, salir
        ADD R4, R7, #0    ; Actualizar resto
        ADD R5, R5, #1    ; Incrementar cociente
        BR DIV_LOOP
DIV_DONE

        ST R5, RES_DIVI   ; Guardar resultado (256 = 2.0)

        HALT              ; Fin del programa

; =====================================================================
; SECCIÓN DE DATOS Y CONSTANTES EN MEMORIA
; =====================================================================
NUM1       .FILL #64      ; 0.5 en Q7
NUM2       .FILL #32      ; 0.25 en Q7
POS_64     .FILL #64      ; Constante para redondeo de multiplicación
MINUS_128  .FILL #-128    ; Constante -128

RES_SUMA   .BLKW #1        ; Esperado: 96 (0.75 en Q7)
RES_MULTI  .BLKW #1        ; Esperado: 16 (0.125 en Q7)
RES_DIVI   .BLKW #1        ; Esperado: 256 (2.0 en Q7)

        .END
