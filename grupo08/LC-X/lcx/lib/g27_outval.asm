.EXTERNAL g27_getval_buffer-BUFFER
ext_buffer      .FILL g27_getval_buffer-BUFFER

.EXTERNAL g27_todec-TODEC

;   ============================================================================
;   Subrutina: OUTVAL (LC-X)
;       Muestra por consola un valor, en un formato especifico.
;
;       El formato es la cantidad de bits fraccionarios (n de Qm.n), de 0 a 16.
;       Con 0 el valor es entero; con 16 es un Q15.16, con la parte entera en
;       R0 y la fraccionaria en R1.
;
;   -> INPUT  [R0] Qm.n, o parte entera (depende del formato).
;   -> INPUT  [R1] cero, o parte fraccionaria (depende del formato).
;   -> INPUT  [R2] n.
;   Conserva todos los registros.
;   El salto de linea final va en el mismo texto que imprime PUTSP.
;   ============================================================================
OUTVAL
        PUSH  R0, R1, R2, R3, R7
        LSHF  R3, R2, #11       ; N: n = 16, Z: n = 0
        BRn   OUTVAL_OUT        ; n = 16: ya viene en [R0, R1]
        BRz   OUTVAL_N0
        NEG   R3, R2            ; 16 - n, en los 4 bits bajos
        LSHF  R1, R0, R3        ; fraccion = Qm.n << (16 - n)
        RSHFA R0, R0, R2        ; entero = Qm.n >> n, con signo
OUTVAL_OUT
        LD    R2, ext_buffer
        MOVI  R3, #10           ; salto de linea al final
        JSR   g27_todec-TODEC
        PUTSP R2                ; print(todec(valor) + salto de linea)
        POPR  R0, R1, R2, R3, R7
OUTVAL_N0
        AND   R1, R1, #0        ; n = 0: entero, sin fraccion
        BR    OUTVAL_OUT

.END
