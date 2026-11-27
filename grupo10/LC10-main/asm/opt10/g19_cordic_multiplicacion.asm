; =====================================================================
;  MULTIPLICACION POR CORDIC (modo lineal) EN Q7.8, en LC10      Grupo 19
;  Funcion publica: CORDIC_MUL   (se importa como G19_CORDIC_MULTIPLICACION-CORDIC_MUL)
;
;  Es el algoritmo del modulo LC-3 (equivale a CORDIC_multiplicacion_Q78.c):
;     z = b;  y = 0;  x = a * 2^14   (x e y de 32 bits)
;     for (i = 0; i < 15; i++) { if (z == 0) break;
;         if (z > 0) { z -= 2^(14-i); y += x; } else { z += 2^(14-i); y -= x; }
;         x /= 2; }
;     resultado = (y + 128) >> 8, y desbordamiento si no entra en 16 bits.
;  Con LC10 las sumas y restas de 32 bits son ADD/ADC y SUB/SBC, x / 2 es SAR + RCR,
;  el peso 2^(14-i) se obtiene con SHR y a * 2^14 con SAR y SHL. No hay SUMA32, RESTA32,
;  DESP_DER_32, DESP_DER_LOG, PREPARAR_X ni REDUCIR_Q78 (eran emulaciones de esas
;  instrucciones). Tampoco esta el programa de prueba del archivo original (MAIN,
;  LEER_ENTERO, IMPRIMIR_ENTERO y sus mensajes), que nadie llamaba.
;
;  CORDIC_MUL
;     entrada : R0 = a_q8     R1 = b_q8   (Q7.8 con signo)
;     salida  : R0 = resultado en Q7.8 (solo valido si R1 = 0; en otro caso vale 0)
;               R1 = estado:  0 = ok / 1 = desbordamiento (|a*b| > 127.996) / 2 = b_q8 invalido (-32768)
;     preserva R2 a R7 (R2 a R5 y R7 en la pila con PUSH/POP; R6 vuelve igual)
;     los codigos de condicion al volver no tienen un significado definido
;
;    R0 = x.hi   R3 = x.lo   R5 = y.hi   R4 = y.lo
;    R1 = z (el multiplicador que se va vaciando)   R2 = peso de la iteracion   R7 = temporal
; =====================================================================

CORDIC_MUL
                        PUSH  R2, R3, R4, R5, R7

                        NEG   R7, R1                    ; V = 1 solo si b = x8000
                        BRV   CM_B_INVALIDO
                        SHL   R3, R0, #14               ; x.lo = (a & 3) * 2^14
                        SAR   R0, R0, #2                ; x.hi = a >> 2 (con signo)
                        CLR   R4
                        CLR   R5                        ; y = 0
                        MOVI  R2, #1
                        SHL   R2, R2, #14               ; peso = 2^14
CM_LAZO
                        TST   R1
                        BRz   CM_FIN_LAZO               ; z == 0: terminar
                        BRn   CM_Z_NEG
                        SUB   R1, R1, R2                ; z > 0:  z -= peso,  y += x
                        ADD   R4, R4, R3
                        ADC   R5, R5, R0
                        BR    CM_SIGUE
CM_Z_NEG
                        ADD   R1, R1, R2                ; z < 0:  z += peso,  y -= x
                        SUB   R4, R4, R3
                        SBC   R5, R5, R0
CM_SIGUE
                        SAR   R0, R0, #1                ; x = x / 2 (32 bits, con signo)
                        RCR   R3, R3
                        SHR   R2, R2, #1                ; siguiente peso
                        BRnp  CM_LAZO                   ; mientras peso != 0 (15 iteraciones)
CM_FIN_LAZO
                        MOVI  R2, #1
                        SHL   R2, R2, #7                ; 128
                        ADD   R4, R4, R2
                        ADC   R5, R5, #0                ; y = y + 128 (redondeo)
                        ADD   R7, R5, R2
                        SHR   R7, R7, #8                ; (y.hi + 128) & xFF00 == 0 <=> entra en 16 bits
                        BRz   CM_ENTRA
                        CLR   R0                        ; desbordamiento: estado 1, sin resultado
                        MOVI  R1, #1
                        BR    CM_FIN
CM_ENTRA
                        SHL   R0, R5, #8
                        SHR   R7, R4, #8
                        OR    R0, R0, R7                ; (y + 128) >> 8
                        CLR   R1
                        BR    CM_FIN
CM_B_INVALIDO
                        CLR   R0
                        MOVI  R1, #2                    ; estado 2
CM_FIN
                        POP   R2, R3, R4, R5, R7
                        RET


.END
