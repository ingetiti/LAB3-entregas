.EXTERNAL g27_getval_buffer-BUFFER
.EXTERNAL g27_getval_buffer-BUFFER_END
.EXTERNAL g27_getline-GETLINE
.EXTERNAL g27_fromdec-FROMDEC
.EXTERNAL g27_todec-TODEC
.EXTERNAL g27_to_qm_n-TO_QM_N
.EXTERNAL g27_from_qm_n-FROM_QM_N

;   ============================================================================
;   Subrutina: GETVAL (LC-X)
;       Obtiene un valor por teclado en un formato especifico, mostrando el valor
;       que se obtubo realmente.
;
;       El fomrato se especifica con un valor numerico que representa la cantidad
;       de bits fraccionarios a tomar (Para Qm.n sera el valor de n).
;       Si el valor es 0, se considera totalmente entero (16 bits enteros), y si
;       el valor es 16, se considera un Q15.16 (Que tendra en R0 el entero, y en
;       R1 el fraccionario).
;
;   -> INPUT  [R0] n .
;   <- OUTPUT [R0] Qn.m obtenido, o parte entera obtenida (depende del formato).
;   <- OUTPUT [R1] cero, o parte fraccionaria obtenida (depende del formato).
;   Conserva R2-R7.
;   ============================================================================
GETVAL
        PUSH  R2, R3, R4, R5, R7
        ADD   R4, R0, #0        ; [R4] n
        LD    R0, GETVAL_BUF
        LD    R1, GETVAL_BUF_END
        JSR   g27_getline-GETLINE   ; [R0] buffer = getline()
        JSR   g27_fromdec-FROMDEC   ; [R0, R1] = [entero, fraccion]
        ADD   R2, R4, #0
        BRnp  GETVAL_NO_INT     ; if n == 0:
        ADD   R1, R1, #0
        BRzp  GETVAL_INT
        ADD   R0, R0, #1        ;     redondeo
GETVAL_INT
        AND   R1, R1, #0        ;     fraccion = 0
GETVAL_DQ16
        PUSH  R0, R1            ; valor = el que se muestra
        BR    GETVAL_OUT
GETVAL_NO_INT
        CMP   R2, #16
        BRz   GETVAL_DQ16       ; elif n == 16: valor = [entero, fraccion]
        JSR   g27_to_qm_n-TO_QM_N   ; else: [R0] qm_n = to_Qm_n(entero, fraccion, n)
        AND   R1, R1, #0
        PUSH  R0, R1            ;     valor = [qm_n, 0]
        ADD   R1, R2, #0
        JSR   g27_from_qm_n-FROM_QM_N ;   [R0, R1] = from_Qm_n(qm_n, n)
GETVAL_OUT
        LD    R2, GETVAL_BUF
        AND   R3, R3, #0        ; formato 0
        JSR   g27_todec-TODEC       ; buffer = todec(valor)
        LEA   R0, GETVAL_LBRAKET
        PUTSP
        ADD   R0, R2, #0
        PUTSP
        LEA   R0, GETVAL_RBRAKET
        PUTSP                   ; print("[ " + buffer + " ]\n")
        POP   R0, R1            ; valor
        POPR  R2, R3, R4, R5, R7

GETVAL_BUF      .FILL g27_getval_buffer-BUFFER
GETVAL_BUF_END  .FILL g27_getval_buffer-BUFFER_END
GETVAL_LBRAKET  .STRINGP "[ "
GETVAL_RBRAKET  .STRINGP " ]\n"

.END
