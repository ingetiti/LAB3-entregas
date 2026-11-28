; =====================================================================
;  MULTIPLICACION POR CORDIC (modo lineal) EN Q7.8 (LC-X)
; =====================================================================
;  CORDIC_MUL
;    Entrada: R0 = a, R1 = b (Q7.8 con signo)
;    Salida:  R0 = a * b en Q7.8, redondeado: (y + 128) >> 8
;             R1 = estado: 0 = bien, 1 = desbordamiento (R0 = 0),
;                  2 = b invalido, x8000 (R0 = 0)
;    Conserva R2-R7.
;
;  El mismo algoritmo que el original (CORDIC lineal, hasta 15 vueltas):
;    z = b, x = a * 2^14 (32 bits), y = 0, w = 2^14
;    mientras w > 0 y z != 0:
;      si z > 0: z = z - w, y = y + x;  si no: z = z + w, y = y - x
;      x = x / 2,  w = w / 2
;  Con LC-X, las sumas y restas de 32 bits usan ADC/SBC, y x / 2 y w / 2
;  son corrimientos (el original usaba una tabla con los pesos w).
; =====================================================================

CORDIC_MUL
        PUSH  R2, R3, R4, R5, R7
        NEG   R2, R1
        BRV   CM_B_INVALIDO     ; V solo si b = x8000
        ADD   R2, R1, #0        ; R2 = z = b
        RSHFA R4, R0, #2        ; R4:R5 = x = a * 2^14
        LSHF  R5, R0, #14
        AND   R0, R0, #0        ; R0:R1 = y = 0
        AND   R1, R1, #0
        MOVI  R3, #1
        LSHF  R3, R3, #14       ; R3 = w = 2^14

CM_LAZO ADD   R2, R2, #0        ; if (z == 0) break;
        BRz   CM_FIN_LAZO
        BRn   CM_Z_NEG
        SUB   R2, R2, R3        ; z > 0:  z = z - w
        ADD   R1, R1, R5        ;         y = y + x
        ADC   R0, R0, R4
        BR    CM_SIGUE
CM_Z_NEG
        ADD   R2, R2, R3        ; z < 0:  z = z + w
        SUB   R1, R1, R5        ;         y = y - x
        SBC   R0, R0, R4
CM_SIGUE
        LSHF  R7, R4, #15       ; x = x / 2 (32 bits, aritmetico)
        RSHFA R4, R4, #1
        RSHFL R5, R5, #1
        OR    R5, R5, R7
        RSHFL R3, R3, #1        ; w = w / 2; 15 vueltas como mucho
        BRnp  CM_LAZO
CM_FIN_LAZO

; ---- y (Q16) -> Q7.8 con redondeo, como REDUCIR_Q78 ----
        MOVI  R3, #64
        ADD   R3, R3, R3        ; R3 = 128
        ADD   R1, R1, R3        ; y + 128: palabra baja, C = acarreo
        ADC   R0, R0, #0        ; palabra alta
        ADD   R2, R0, R3        ; la alta tiene que estar entre -128 y 127:
        RSHFL R2, R2, #8        ; alta + 128 entre 0 y 255
        BRnp  CM_DESBORDA
        LSHF  R0, R0, #8
        RSHFL R1, R1, #8
        OR    R0, R0, R1        ; (y + 128) >> 8
        AND   R1, R1, #0        ; estado = 0
        BR    CM_FIN
CM_DESBORDA
        AND   R0, R0, #0
        MOVI  R1, #1            ; estado = 1
        BR    CM_FIN
CM_B_INVALIDO
        AND   R0, R0, #0
        MOVI  R1, #2            ; estado = 2
CM_FIN  POP   R2, R3, R4, R5, R7
        RET

        .END
