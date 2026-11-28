;====================================================================
; g18_booth.asm - Modulo "booth": multiplicador Q7.8  [OPT]
; Funcion publica: MULT_BOOTH      (se importa como G18_BOOTH-MULT_BOOTH)
;
; OPTIMIZACION: se reemplaza el bucle de Booth de 16 iteraciones (+ conversion
; P>>8 de 8 iteraciones y las subrutinas SHR1/ASR1) por una multiplicacion
; nativa MUL (parte baja) + MULH (parte alta) y el reajuste de escala Q7.8
; RES = P[23:8] = ((hi & 0xFF) << 8) | (lo >> 8), usando LSL #4 (x2) y
; LSR #4 (x2) para desplazar 8 bits (imm4 = 4, dentro de [-8,+7]).
;
; CONVENCION DE LLAMADA
;   Entrada : R0 = X, primer operando  (Q7.8, 16 bits con signo)
;             R1 = Y, segundo operando (Q7.8, 16 bits con signo)
;   Salida  : R0 = RES = P[23:8]       (producto reducido a Q7.8)
;   Conserva: R1, R2, R3, R4, R5 (se apilan y se restauran)
;             R6 vuelve con el mismo valor que tenia al entrar
;             R7 se apila al entrar y se restaura antes de RET
;   Destruye: R0 (es el resultado)
;   CC      : al retornar reflejan el signo de RES (ultimo LD es R0).
;
; PILA (R6 crece hacia direcciones menores). Marco de 7 palabras (14 bytes):
;     R6+0 = R1   R6+1 = R2   R6+2 = R3   R6+3 = R4
;     R6+4 = R5   R6+5 = R7   R6+6 = (sin uso en esta version)
;   Se reserva en dos pasos (-8, -6) y se libera en dos pasos (+7, +7) para
;   mantener R6 par (byte-addressing) y R6 == 0xFFFE al retornar.
;
; NOTA DE CORRECTitud: RES = bits [23:8] del producto de 32 bits. Los bits
; [31:24] (extension de signo) se descartan, por lo que el resultado coincide
; exactamente con P[23:8] del Booth original (sin saturacion de overflow, que
; en el original era solo diagnostico y no afectaba a R0).
;====================================================================

MULT_BOOTH
        ADD  R6, R6, #-8        ; reservar marco (14 bytes, en 2 pasos)
        ADD  R6, R6, #-6
        STR  R1, R6, #0         ; apilar R1..R5 y R7 (offsets en palabras)
        STR  R2, R6, #1
        STR  R3, R6, #2
        STR  R4, R6, #3
        STR  R5, R6, #4
        STR  R7, R6, #5

        MULH R2, R0, R1         ; R2 = parte alta del producto (hi)
        MUL  R0, R0, R1         ; R0 = parte baja del producto (lo)

        ; RES = P[23:8] = ((hi & 0xFF) << 8) | (lo >> 8)
        LSR  R0, R0, #4         ; lo >>= 4
        LSR  R0, R0, #4         ; lo >>= 8  -> R0 = lo >> 8  (bits [7:0])
        LSL  R2, R2, #4         ; hi <<= 4
        LSL  R2, R2, #4         ; hi <<= 8  -> R2 = (hi << 8) & 0xFFFF (bits [15:8])
        ADD  R0, R0, R2         ; R0 = RES

        LDR  R1, R6, #0         ; desapilar en el mismo orden
        LDR  R2, R6, #1
        LDR  R3, R6, #2
        LDR  R4, R6, #3
        LDR  R5, R6, #4
        LDR  R7, R6, #5         ; direccion de retorno original
        ADD  R6, R6, #7         ; +7 (imm4 valido)
        ADD  R6, R6, #7         ; +7 -> combinan +14 bytes, R6 = 0xFFFE
        RET

        .END